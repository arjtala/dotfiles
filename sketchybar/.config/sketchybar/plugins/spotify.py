#!/usr/bin/env python3
"""Now playing on Spotify, through spotify_player, for the spotify item.

    spotify.py update                       the item's script
    spotify.py toggle                       its click: the popup
    spotify.py control play-pause|next|previous
    spotify.py fetch                        a read, run in the background

The bar shows the track, clipped, and elapsed/duration; the popup shows
the whole title, the artist and album, a progress bar, and the controls.

State comes from `spotify_player get key playback', the Web API's
playback object.  It is read on spotify_player's player events (see
plugins/spotify_hook.sh), on a click, and every `POLL' seconds otherwise,
since music playing on another device sends no events here.  In between,
elapsed time is counted locally rather than asking the API every second.

A read can take seconds, so it never happens in the item's script, which
runs every second while a track plays: a detached `spotify.py fetch',
one at a time, writes the cache and triggers spotify_refresh, and the
script only ever draws from the cache.
"""
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import popup as p  # noqa: E402  (shares the popups' helpers and layout)

SELF = str(Path(__file__).resolve())
ITEM = p.SPOTIFY
PLAY = f'{ITEM}.c.play'
CACHE_FILE = p.CACHE / 'sketchybar-spotify.json'
LOCK_FILE = p.CACHE / 'sketchybar-spotify.lock'  # a read is under way
READ_TIMEOUT = 10
PLAYER_CONFIG = Path.home() / '.config/spotify-player/app.toml'
PLAYER_CACHE = Path.home() / '.cache/spotify-player'
DEFAULT_CLIENT_ID = 'd420a117a32841c2b3474932e49fb54b'  # spotify_player's own default
POLL = 15  # seconds between reads when no event says something changed
BAR_TITLE = 18  # characters of title in the bar
WIDTH = 34  # characters across the popup
LABEL_WIDTH = math.ceil(WIDTH * p.CHAR) + 2
ROW = p.PAD + p.LABEL_PAD + LABEL_WIDTH + p.PAD
INFO_ROWS = ['title', 'artist', 'progress']
ROW_HEIGHT = 31  # a popup row is as tall as the bar
INFO_HEIGHT = ROW_HEIGHT * len(INFO_ROWS)
ICONS = {'previous': '\U000F04AE', 'play': '\U000F040A', 'pause': '\U000F03E4',
         'next': '\U000F04AD'}  # Nerd Font: skip-previous, play, pause, skip-next


# ---- Pure parts, covered by sketchybar/tests/test_spotify.py ----

def parse(data):
    """Return the playback object DATA as a flat dict, or None with nothing loaded."""
    if not isinstance(data, dict) or not isinstance(data.get('item'), dict):
        return None
    item = data['item']
    if item.get('artists'):
        by = ', '.join(artist['name'] for artist in item['artists'])
        source = (item.get('album') or {}).get('name', '')
    else:  # a podcast episode
        by = (item.get('show') or {}).get('name', '')
        source = ''
    return {
        'title': item.get('name', ''),
        'by': by,
        'source': source,
        'playing': bool(data.get('is_playing')),
        'progress': data.get('progress_ms') or 0,
        'duration': item.get('duration_ms') or 0,
    }


def elapsed(info, fetched, now):
    """Return INFO's position in milliseconds at NOW, having been read at FETCHED."""
    position = info['progress'] + (max(0, now - fetched) * 1000 if info['playing'] else 0)
    return min(position, info['duration']) if info['duration'] else position


def clock(ms):
    """Return MS as m:ss, or h:mm:ss from an hour."""
    minutes, seconds = divmod(int(ms // 1000), 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes}:{seconds:02}'


def clip(text, length):
    """Return TEXT cut to LENGTH characters, ending in an ellipsis if cut."""
    return text if len(text) <= length else text[:length - 1].rstrip() + '…'


def bar_label(info, position):
    return f"{clip(info['title'], BAR_TITLE)} {clock(position)}/{clock(info['duration'])}"


def progress_text(position, duration, width=WIDTH):
    """Return `1:23 ━━━━──── 5:55', WIDTH characters across."""
    left, right = clock(position), clock(duration)
    cells = max(0, width - len(left) - len(right) - 2)
    filled = round(cells * position / duration) if duration else 0
    return f"{left} {'━' * filled}{'─' * (cells - filled)} {right}"


def client_id(config):
    """Return the client ID spotify_player's CONFIG text sets, or its default."""
    match = re.search(r'^client_id\s*=\s*"([^"]+)"', config, re.M)
    return match.group(1) if match else DEFAULT_CLIENT_ID


def stale(state, now):
    """Return whether STATE, a cached read, should be read again at NOW."""
    if not state:
        return True
    age = now - state.get('fetched', 0)
    info = parse(state.get('data'))
    # A track that has run out has changed, whether or not an event said
    # so; but not more than every couple of seconds while it settles.
    ended = info and info['playing'] and info['duration'] and \
        elapsed(info, state['fetched'], now) >= info['duration']
    return age >= POLL or bool(ended and age >= 2)


# ---- spotify_player and SketchyBar ----

def player():
    return shutil.which('spotify_player') or '/opt/homebrew/bin/spotify_player'


def logged_in():
    """Return whether spotify_player has a saved login for its client ID.

    Without one, any spotify_player command opens a browser window to log
    in, and this runs in the background every `POLL' seconds: a window,
    stealing focus, every fifteen seconds.  Log in once by hand instead,
    with `spotify_player authenticate'.  (A config that sets
    client_id_command rather than client_id is read as the default.)
    """
    try:
        config = PLAYER_CONFIG.read_text()
    except OSError:
        config = ''
    return (PLAYER_CACHE / f'{client_id(config)}_token.json').exists()


def fetch(now):
    state = {'fetched': now, 'data': read_playback() if logged_in() else None}
    try:
        p.CACHE.mkdir(exist_ok=True)
        CACHE_FILE.write_text(json.dumps(state))
    except OSError:
        pass
    return state


def read_playback():
    try:
        result = subprocess.run([player(), 'get', 'key', 'playback'],
                                capture_output=True, text=True, timeout=READ_TIMEOUT)
        return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def fetch_later():
    """Start a background read, unless one is already under way."""
    try:
        if time.time() - LOCK_FILE.stat().st_mtime < READ_TIMEOUT + 5:
            return
    except OSError:
        pass
    try:
        p.CACHE.mkdir(exist_ok=True)
        LOCK_FILE.touch()
        subprocess.Popen([sys.executable, SELF, 'fetch'], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError:
        pass


def fetch_now():
    """The background read: fetch, release the lock, and have the item redraw."""
    try:
        fetch(time.time())
    finally:
        try:
            LOCK_FILE.unlink()
        except OSError:
            pass
        p.bar('--trigger', 'spotify_refresh')


def cached():
    try:
        return json.loads(CACHE_FILE.read_text())
    except (OSError, ValueError):
        return None


def create():
    palette = p.colors()
    panel = [f'popup.background.color={palette["BG1"]}',
             f'popup.background.corner_radius={p.RADIUS}', 'popup.background.border_width=0']
    # The controls are the item's popup, one horizontal row, moved down to
    # make room above them; the track is the middle button's popup, which
    # opens below it and is moved up into that room.  Both move as whole
    # windows, so the buttons stay clickable where they are drawn.
    args = ['--remove', f'/{ITEM}\\.[ci]\\..*/',
            '--set', ITEM, 'popup.horizontal=on', 'popup.align=left',
            f'popup.y_offset={INFO_HEIGHT - p.RADIUS}', *panel]
    side = (ROW + p.GRID_SLACK) // 3
    buttons = (('prev', side, 'previous', 'previous'),
               ('play', ROW + p.GRID_SLACK - 2 * side, 'play', 'play-pause'),
               ('next', side, 'next', 'next'))
    for name, width, icon, action in buttons:
        item = f'{ITEM}.c.{name}'
        args += ['--add', 'item', item, f'popup.{ITEM}',
                 '--set', item, 'icon.drawing=off', f'label.width={width}', 'label.align=center',
                 'label.padding_left=0', 'label.padding_right=0', 'padding_left=0', 'padding_right=0',
                 'label.font=JetBrainsMono Nerd Font:Regular:16.0', f'label.color={palette["FG"]}',
                 f'label={ICONS[icon]}',
                 f'click_script={SELF} control {action}']
    args += ['--set', PLAY, 'popup.align=center',
             f'popup.y_offset=-{INFO_HEIGHT + ROW_HEIGHT - p.RADIUS}', *panel]
    for name in INFO_ROWS:
        item = f'{ITEM}.i.{name}'
        args += ['--add', 'item', item, f'popup.{PLAY}',
                 '--set', item, 'icon.drawing=off', f'label.width={LABEL_WIDTH}',
                 f'label.padding_left={p.LABEL_PAD}', 'label.padding_right=0',
                 f'padding_left={p.PAD}', f'padding_right={p.PAD}']
    p.bar(*args)


def render(state, now, popup_open):
    palette = p.colors()
    info = parse(state.get('data')) if state else None
    if not info:
        p.bar('--set', ITEM, 'drawing=off', 'update_freq=' + str(POLL))
        if popup_open:
            p.close(ITEM)
        return
    position = elapsed(info, state['fetched'], now)
    color = palette['BR_GREEN'] if info['playing'] else palette['FG2']
    args = ['--set', ITEM, 'drawing=on', f'label={bar_label(info, position)}',
            f'icon.color={color}', f'label.color={color}',
            # Tick every second only while there is a second to count.
            f'update_freq={1 if info["playing"] else POLL}']
    if popup_open:
        bold = 'JetBrainsMono Nerd Font:Bold:13.0'
        by = ' · '.join(part for part in (info['by'], info['source']) if part)
        args += p.show(f'{ITEM}.i.title', clip(info['title'], WIDTH), palette['FG'],
                       **{'label.font': bold})
        args += p.show(f'{ITEM}.i.artist', clip(by, WIDTH), palette['FG2'])
        args += p.show(f'{ITEM}.i.progress', progress_text(position, info['duration']),
                       palette['BR_GREEN'] if info['playing'] else palette['FG2'])
        args += ['--set', PLAY, f'label={ICONS["pause" if info["playing"] else "play"]}']
    p.bar(*args)


def update():
    if os.environ.get('SENDER') == 'mouse.exited.global':
        p.close(ITEM)
        return
    now = time.time()
    state = cached()
    if os.environ.get('SENDER') in ('spotify_update', 'forced', 'system_woke') or stale(state, now):
        fetch_later()
    render(state, now, p.is_open(ITEM))


def toggle():
    now = time.time()
    p.toggle(ITEM, create, lambda: render(cached(), now, True))
    fetch_later()


def control(action):
    if not logged_in():
        return
    try:
        subprocess.run([player(), 'playback', action], capture_output=True, timeout=READ_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        pass
    time.sleep(0.6)  # let the API catch up before reading it back
    fetch_later()


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'update'
    if action == 'update':
        update()
    elif action == 'toggle':
        toggle()
    elif action == 'fetch':
        fetch_now()
    elif action == 'control' and sys.argv[2:3] and sys.argv[2] in ('play-pause', 'next', 'previous'):
        control(sys.argv[2])


if __name__ == '__main__':
    main()
