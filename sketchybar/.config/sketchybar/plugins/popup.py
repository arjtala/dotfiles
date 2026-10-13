#!/usr/bin/env python3
"""Month calendar and prayer-time popups for the clock and athan items.

    popup.py calendar toggle|today|prev|next
    popup.py prayers toggle|refresh

The SketchyBar counterpart of waybar/.config/waybar/scripts/popup.py.
SketchyBar draws, places and dismisses the popups itself, so this only
fills them in.  Popup items are created when a popup opens and updated in
place afterwards: removing items from under the pointer would end the
hover that keeps the popup open.

Runs under whichever python3 SketchyBar's PATH finds, which may be the
system's 3.9, so nothing newer than 3.9 is used.
"""
import calendar
from datetime import date, datetime, timedelta
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

SELF = str(Path(__file__).resolve())
CONFIG_DIR = Path(os.environ.get('CONFIG_DIR') or Path(__file__).resolve().parent.parent)
CACHE = Path.home() / '.cache'
MONTH_FILE = CACHE / 'sketchybar-month'
ATHAN = Path.home() / '.cargo/bin/athan'
PRAYER_NAMES = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
WEEKS = 6  # the most a month can span
GAP = 3  # columns between days; day columns 39pt apart, as in Waybar
WIDTH = 7 * 2 + 8 * GAP  # columns of popup text: one calendar row
# JetBrains Mono advances 0.6 em, so 7.8pt at the 13pt label font, in bold
# as in regular.  Every popup label is given its width outright: SketchyBar
# leaves leading spaces out of a label's measured width but still draws
# them, so a label that starts with spaces is clipped at the right.
CHAR = 13 * 0.6
LABEL_WIDTH = math.ceil(WIDTH * CHAR) + 2
LABEL_PAD = 4  # label.padding_left on every popup row
TODAY_WIDTH = math.ceil(2 * CHAR)  # icon.width holding today's two digits
PAD = 12  # padding either side of every popup row
ROW = PAD + LABEL_PAD + LABEL_WIDTH + PAD  # a popup row's full width
ARROW = 36  # width of each month arrow
# SketchyBar lays a vertical popup out 4pt wider than its rows add up to;
# measured, not documented.  The title row is widened to match the grid.
GRID_SLACK = 4
RADIUS = 6  # popup corner radius
# A popup is a single row or a single column, and every click target is an
# item of its own.  So the calendar is two popups: the clock's is one
# horizontal row, `‹ October 2026 ›', and the title's opens below it with
# the grid.  They are the same width and colour, and overlap by the corner
# radius, so they read as one panel.
CAL = 'clock'
TITLE = f'{CAL}.p.title'
GRID_ITEMS = ['weekdays'] + [f'week{i}' for i in range(WEEKS)] + ['hint']
PRAYERS = 'athan'
SPOTIFY = 'spotify'  # filled in by plugins/spotify.py
# Each popup's second level, opened and closed with it.
CHILDREN = {CAL: TITLE, SPOTIFY: f'{SPOTIFY}.c.play'}
PRAYER_ITEMS = (['heading', 'date'] + [f'row{i}' for i in range(len(PRAYER_NAMES) + 1)]
                + ['overnight', 'next', 'error'])


def colors():
    """Return the palette from colors.sh, which the shell plugins source."""
    text = (CONFIG_DIR / 'colors.sh').read_text()
    return dict(re.findall(r'^export (\w+)=(0x[0-9a-fA-F]+)', text, re.M))


# ---- Pure parts, covered by sketchybar/tests/test_popup.py ----

def shift_month(first, delta):
    """Return the first day of the month DELTA months from FIRST."""
    year, month = divmod(first.year * 12 + first.month - 1 + delta, 12)
    return date(year, month + 1, 1)


def week_text(days, today=None):
    """Return one week as monospace text, with TODAY's cell left blank.

    DAYS is seven day numbers, 0 for a day outside the month.  Each number
    takes two columns and each gap `GAP', so every row is `WIDTH' columns.
    Today is blank because it is drawn separately, in red; see
    `today_padding'.
    """
    cells = [f'{day:>2}' if day and day != today else '  ' for day in days]
    gap = ' ' * GAP
    return gap + gap.join(cells) + gap


def today_column(days, today):
    """Return the column TODAY's two digits start at in DAYS' row, or None."""
    if today not in days or not today:
        return None
    return GAP + days.index(today) * (2 + GAP)


def today_padding(column):
    """Return (icon.padding_left, label.padding_left) for today at COLUMN.

    A popup row has one label colour, so today's number is the row's icon,
    drawn in red, and the label holds the rest of the week.  The icon is
    pushed right to today's column, and the label pulled back left by the
    icon's width, so it starts where every other row's does.  Only by the
    width: an icon with a fixed width advances the row by that width
    alone, its padding moving the digits within it.
    """
    return LABEL_PAD + round(column * CHAR), LABEL_PAD - TODAY_WIDTH


def weekday_text():
    """Return the weekday names, aligned over `week_text's columns."""
    return week_text([0] * 7)[:GAP] + (' ' * GAP).join(
        ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'])


def month_rows(first, today):
    """Return FIRST's month as (text, today's column or None) pairs, Monday first."""
    current = today.day if (today.year, today.month) == (first.year, first.month) else None
    return [(week_text(week, current), today_column(week, current))
            for week in calendar.Calendar().monthdayscalendar(first.year, first.month)]


def prayer_state(data, now):
    """Return the current prayer, the day it started, and the countdown line.

    The same rules as the Waybar popup: current means most recently
    started, so before Fajr it is yesterday's Isha, and after Isha the
    footer does not guess at tomorrow's Fajr.
    """
    today = date.fromisoformat(data['date'])
    if today != now.date():
        raise ValueError('Schedule is out of date')
    prayers = data['prayers']
    if [p['name'] for p in prayers] != PRAYER_NAMES:
        raise ValueError('Expected all five prayers; update athan first')
    current = 'Isha'
    current_date = today - timedelta(days=1)
    following = None
    for prayer in prayers:
        hour, minute = map(int, prayer['time'].split(':'))
        start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if start <= now:
            current, current_date = prayer['name'], today
        elif following is None:
            minutes = max(1, int((start - now).total_seconds() + 59) // 60)
            hours, remainder = divmod(minutes, 60)
            delay = f'{hours}h {remainder:02}m' if hours else f'{remainder} min'
            following = f"Next: {prayer['name']} in {delay}"
    return current, current_date, following or 'Next: Fajr tomorrow'


def prayer_rows(data, now):
    """Return today's rows as (text, style) pairs, Sunrise included.

    Style is 'current', 'muted' or None.  Names are padded so the times
    line up at the right edge, `WIDTH' columns in.
    """
    current, current_date, _ = prayer_state(data, now)
    rows = list(data['prayers'])
    if data.get('sunrise'):
        rows.insert(1, {'name': 'Sunrise', 'time': data['sunrise']})
    result = []
    for prayer in rows:
        active = prayer['name'] == current and current_date == now.date()
        style = 'current' if active else ('muted' if prayer['name'] == 'Sunrise' else None)
        name = f"{'●' if active else ' '} {prayer['name']}"
        result.append((name.ljust(WIDTH - len(prayer['time'])) + prayer['time'], style))
    return result


# ---- SketchyBar ----

def bar(*args):
    subprocess.run(['sketchybar', *args], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def is_open(item):
    result = subprocess.run(['sketchybar', '--query', item], capture_output=True, text=True)
    try:
        return json.loads(result.stdout).get('popup', {}).get('drawing') == 'on'
    except ValueError:
        return False


def row_settings(item, parent):
    """Return the arguments adding ITEM as an empty full-width row of PARENT's popup."""
    return ['--add', 'item', item, f'popup.{parent}',
            '--set', item, 'icon.drawing=off', f'label.width={LABEL_WIDTH}',
            f'label.padding_left={LABEL_PAD}', 'label.padding_right=0',
            f'padding_left={PAD}', f'padding_right={PAD}']


def create_prayers():
    args = ['--remove', f'/{PRAYERS}\\.p\\..*/']
    for name in PRAYER_ITEMS:
        args += row_settings(f'{PRAYERS}.p.{name}', PRAYERS)
    bar(*args)


def create_calendar():
    palette = colors()
    panel = [f'popup.background.color={palette["BG1"]}',
             f'popup.background.corner_radius={RADIUS}', 'popup.background.border_width=0']
    args = ['--remove', f'/{CAL}\\.[pg]\\..*/',
            '--set', CAL, 'popup.horizontal=on', *panel]
    for name, glyph, width in (('prev', '‹', ARROW), ('title', '', ROW + GRID_SLACK - 2 * ARROW),
                               ('next', '›', ARROW)):
        item = f'{CAL}.p.{name}'
        args += ['--add', 'item', item, f'popup.{CAL}',
                 '--set', item, 'icon.drawing=off', f'label={glyph}', f'label.width={width}',
                 'label.align=center', 'label.padding_left=0', 'label.padding_right=0',
                 'padding_left=0', 'padding_right=0', f'label.color={palette["FG"]}',
                 f'click_script={SELF} calendar {"today" if name == "title" else name}']
    # Centred under the title is centred under the row, the arrows being
    # equal; raised by the corner radius to hide the seam.
    args += ['--set', TITLE, 'popup.align=center', f'popup.y_offset=-{RADIUS}', *panel]
    for name in GRID_ITEMS:
        args += row_settings(f'{CAL}.g.{name}', TITLE)
    bar(*args)


def close(parent):
    bar('--set', parent, 'popup.drawing=off')
    if parent in CHILDREN:
        # Its own call: before a popup first opens its second level does
        # not exist, and an unknown item would fail the whole command.
        bar('--set', CHILDREN[parent], 'popup.drawing=off')


def show(item, text, color, **extra):
    args = ['--set', item, 'drawing=on', f'label={text}', f'label.color={color}']
    return args + [f'{key}={value}' for key, value in extra.items()]


def hide(item):
    return ['--set', item, 'drawing=off']


def read_month(today):
    try:
        return date.fromisoformat(MONTH_FILE.read_text().strip() + '-01')
    except (OSError, ValueError):
        return today.replace(day=1)


def write_month(first):
    CACHE.mkdir(exist_ok=True)
    MONTH_FILE.write_text(first.strftime('%Y-%m'))


def render_calendar(first):
    palette = colors()
    today = date.today()
    bold = 'JetBrainsMono Nerd Font:Bold:13.0'
    grid = f'{CAL}.g'
    args = show(TITLE, first.strftime('%B %Y'), palette['BR_YELLOW'], **{'label.font': bold})
    args += show(f'{grid}.weekdays', weekday_text(), palette['BR_YELLOW'])
    weeks = month_rows(first, today)
    for index in range(WEEKS):
        if index >= len(weeks):
            args += hide(f'{grid}.week{index}')
            continue
        text, column = weeks[index]
        if column is None:
            extra = {'icon.drawing': 'off', 'label.padding_left': LABEL_PAD,
                     'label.width': LABEL_WIDTH}
        else:
            icon_pad, label_pad = today_padding(column)
            # SketchyBar sizes the panel counting the icon's width but not
            # the label's negative padding, so the label gives the width
            # back.  It only loses trailing spaces: a row ends in a gap.
            extra = {'icon.drawing': 'on', 'icon': f'{today.day:>2}',
                     'icon.font': bold, 'icon.color': palette['BR_RED'],
                     'icon.width': TODAY_WIDTH, 'icon.padding_left': icon_pad,
                     'icon.padding_right': 0, 'label.padding_left': label_pad,
                     'label.width': LABEL_WIDTH - TODAY_WIDTH}
        args += show(f'{grid}.week{index}', text, palette['FG'], **extra)
    if first == today.replace(day=1):
        args += hide(f'{grid}.hint')
    else:
        args += show(f'{grid}.hint', 'click title for today'.center(WIDTH).rstrip(), palette['FG2'])
    bar(*args)


def render_prayers():
    palette = colors()
    args = show(f'{PRAYERS}.p.heading', 'Prayer times', palette['BR_PURPLE'])
    try:
        result = subprocess.run([str(ATHAN), '--all', '--json'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise ValueError('Unable to load prayer times')
        data = json.loads(result.stdout)
        now = datetime.now(ZoneInfo(data['timezone']))
        rows = prayer_rows(data, now)
        _, current_date, following = prayer_state(data, now)
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        args += hide(f'{PRAYERS}.p.date')
        args += [arg for i in range(len(PRAYER_NAMES) + 1) for arg in hide(f'{PRAYERS}.p.row{i}')]
        args += hide(f'{PRAYERS}.p.overnight') + hide(f'{PRAYERS}.p.next')
        args += show(f'{PRAYERS}.p.error', str(error), palette['FG2'])
        bar(*args)
        return
    args += show(f'{PRAYERS}.p.date', now.strftime('%A, %B ') + str(now.day), palette['FG2'])
    style_colors = {'current': palette['BR_PURPLE'], 'muted': palette['FG2'], None: palette['FG']}
    for index in range(len(PRAYER_NAMES) + 1):
        if index < len(rows):
            text, style = rows[index]
            args += show(f'{PRAYERS}.p.row{index}', text, style_colors[style])
        else:
            args += hide(f'{PRAYERS}.p.row{index}')
    if current_date != now.date():
        args += show(f'{PRAYERS}.p.overnight', '● Isha · yesterday', palette['BR_PURPLE'])
    else:
        args += hide(f'{PRAYERS}.p.overnight')
    args += show(f'{PRAYERS}.p.next', following, palette['FG2'])
    args += hide(f'{PRAYERS}.p.error')
    bar(*args)


def toggle(parent, create, render):
    """Close PARENT's popup if open, else fill it in and open it, closing the others."""
    if is_open(parent):
        close(parent)
        return
    create()
    render()
    for other in (CAL, PRAYERS, SPOTIFY):
        if other != parent:
            close(other)
    bar('--set', parent, 'popup.drawing=on')
    if parent in CHILDREN:
        bar('--set', CHILDREN[parent], 'popup.drawing=on')


def show_month(first):
    write_month(first)
    render_calendar(first)


def main():
    panel, action = sys.argv[1:3]
    if panel == 'calendar':
        today = date.today()
        if action == 'toggle':
            toggle(CAL, create_calendar, lambda: show_month(today.replace(day=1)))
        elif action == 'today':
            show_month(today.replace(day=1))
        elif action in ('prev', 'next'):
            show_month(shift_month(read_month(today), -1 if action == 'prev' else 1))
    elif panel == 'prayers':
        if action == 'toggle':
            toggle(PRAYERS, create_prayers, render_prayers)
        elif action == 'refresh' and is_open(PRAYERS):
            render_prayers()


if __name__ == '__main__':
    main()
