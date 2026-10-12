#!/usr/bin/env python3
"""Month calendar and prayer-time popups for the clock and athan items.

    popup.py calendar toggle|today|scroll
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
import time
from zoneinfo import ZoneInfo

SELF = str(Path(__file__).resolve())
CONFIG_DIR = Path(os.environ.get('CONFIG_DIR') or Path(__file__).resolve().parent.parent)
CACHE = Path.home() / '.cache'
MONTH_FILE = CACHE / 'sketchybar-month'
SCROLL_FILE = CACHE / 'sketchybar-month-scroll'
SCROLL_GAP = 0.3  # seconds; one trackpad swipe sends a burst of events
ATHAN = Path.home() / '.cargo/bin/athan'
PRAYER_NAMES = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
WEEKS = 6  # the most a month can span
GAP = 3  # columns between days, which today's brackets sit in; 39pt apart, as in Waybar
WIDTH = 7 * 2 + 8 * GAP  # columns of popup text: one calendar row
# JetBrains Mono advances 0.6 em, so 7.8pt at the 13pt label font.  Every
# popup label is given this width outright: SketchyBar leaves leading
# spaces out of a label's measured width but still draws them, so a label
# that starts with spaces is clipped at the right.
LABEL_WIDTH = math.ceil(WIDTH * 13 * 0.6) + 2
CAL = 'clock'
PRAYERS = 'athan'
CAL_ITEMS = ['header', 'weekdays'] + [f'week{i}' for i in range(WEEKS)] + ['hint']
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
    """Return one week as monospace text, with TODAY bracketed in place.

    DAYS is seven day numbers, 0 for a day outside the month.  Each number
    takes two columns and each gap `GAP', so the brackets take the gap
    columns touching today and every row stays `WIDTH' columns wide.
    """
    gaps = [' ' * GAP] * 8
    cells = []
    for index, day in enumerate(days):
        cells.append(f'{day:>2}' if day else '  ')
        if day and day == today:
            gaps[index] = gaps[index][:-1] + '['
            gaps[index + 1] = ']' + gaps[index + 1][1:]
    return ''.join(gap + cell for gap, cell in zip(gaps, cells)) + gaps[7]


def weekday_text():
    """Return the weekday names, aligned over `week_text's columns."""
    return week_text([0] * 7)[:GAP] + (' ' * GAP).join(
        ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'])


def month_rows(first, today):
    """Return the weeks of FIRST's month as (text, holds_today) pairs, Monday first."""
    current = today.day if (today.year, today.month) == (first.year, first.month) else None
    return [(week_text(week, current), current in week)
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


def create(parent, names, scroll=False):
    """Replace PARENT's popup items with fresh, empty ones called NAMES."""
    args = ['--remove', f'/{parent}\\.p\\..*/']
    for name in names:
        item = f'{parent}.p.{name}'
        args += ['--add', 'item', item, f'popup.{parent}',
                 '--set', item, 'icon.drawing=off', f'label.width={LABEL_WIDTH}',
                 'padding_left=12', 'padding_right=12']
        if scroll:
            args += [f'script={SELF} calendar scroll',
                     '--subscribe', item, 'mouse.scrolled']
    bar(*args)


def show_label(parent, name, text, color, **extra):
    args = ['--set', f'{parent}.p.{name}', 'drawing=on', f'label={text}', f'label.color={color}']
    return args + [f'{key}={value}' for key, value in extra.items()]


def hide(parent, name):
    return ['--set', f'{parent}.p.{name}', 'drawing=off']


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
    title = first.strftime('%B %Y').center(WIDTH).rstrip()
    args = show_label(CAL, 'header', title, palette['BR_YELLOW'],
                      click_script=f'{SELF} calendar today')
    args += show_label(CAL, 'weekdays', weekday_text(), palette['FG2'])
    weeks = month_rows(first, today)
    for index in range(WEEKS):
        if index < len(weeks):
            text, holds_today = weeks[index]
            args += show_label(CAL, f'week{index}', text,
                               palette['BR_YELLOW'] if holds_today else palette['FG'])
        else:
            args += hide(CAL, f'week{index}')
    hint = 'scroll for months' if first == today.replace(day=1) else 'click title: today'
    args += show_label(CAL, 'hint', hint.center(WIDTH).rstrip(), palette['BG2'])
    bar(*args)


def render_prayers():
    palette = colors()
    args = show_label(PRAYERS, 'heading', 'Prayer times', palette['BR_PURPLE'])
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
        args += hide(PRAYERS, 'date')
        args += [arg for i in range(len(PRAYER_NAMES) + 1) for arg in hide(PRAYERS, f'row{i}')]
        args += hide(PRAYERS, 'overnight') + hide(PRAYERS, 'next')
        args += show_label(PRAYERS, 'error', str(error), palette['FG2'])
        bar(*args)
        return
    args += show_label(PRAYERS, 'date', now.strftime('%A, %B ') + str(now.day), palette['FG2'])
    style_colors = {'current': palette['BR_PURPLE'], 'muted': palette['FG2'], None: palette['FG']}
    for index in range(len(PRAYER_NAMES) + 1):
        if index < len(rows):
            text, style = rows[index]
            args += show_label(PRAYERS, f'row{index}', text, style_colors[style])
        else:
            args += hide(PRAYERS, f'row{index}')
    if current_date != now.date():
        args += show_label(PRAYERS, 'overnight', '● Isha · yesterday', palette['BR_PURPLE'])
    else:
        args += hide(PRAYERS, 'overnight')
    args += show_label(PRAYERS, 'next', following, palette['FG2'])
    args += hide(PRAYERS, 'error')
    bar(*args)


def toggle(parent, other, names, render, scroll=False):
    if is_open(parent):
        bar('--set', parent, 'popup.drawing=off')
        return
    create(parent, names, scroll)
    render()
    bar('--set', other, 'popup.drawing=off', '--set', parent, 'popup.drawing=on')


def scroll():
    """Move one month per swipe, however many events the swipe sends."""
    if os.environ.get('SENDER') != 'mouse.scrolled':
        return
    delta = int(os.environ.get('SCROLL_DELTA') or 0)
    try:
        last = float(SCROLL_FILE.read_text())
    except (OSError, ValueError):
        last = 0.0
    now = time.time()
    if not delta or now - last < SCROLL_GAP:
        return
    CACHE.mkdir(exist_ok=True)
    SCROLL_FILE.write_text(str(now))
    # Natural scrolling: swiping up (a positive delta) reveals what comes later.
    first = shift_month(read_month(date.today()), 1 if delta > 0 else -1)
    write_month(first)
    render_calendar(first)


def main():
    panel, action = sys.argv[1:3]
    if panel == 'calendar':
        if action == 'toggle':
            def render():
                first = date.today().replace(day=1)
                write_month(first)
                render_calendar(first)
            toggle(CAL, PRAYERS, CAL_ITEMS, render, scroll=True)
        elif action == 'today':
            first = date.today().replace(day=1)
            write_month(first)
            render_calendar(first)
        elif action == 'scroll':
            scroll()
    elif panel == 'prayers':
        if action == 'toggle':
            toggle(PRAYERS, CAL, PRAYER_ITEMS, render_prayers)
        elif action == 'refresh' and is_open(PRAYERS):
            render_prayers()


if __name__ == '__main__':
    main()
