#!/usr/bin/env python3
"""What macOS is playing, from any app, for the nowplaying item.

    nowplaying.py update                     the item's script
    nowplaying.py toggle                     its click: the popup
    nowplaying.py control back|play-pause|forward
    nowplaying.py watch                      the watcher, run in the background

The bar shows the title, clipped, and elapsed/duration, with the playing
app's icon; the popup shows the whole title, the artist or show and the
album, a progress bar, and the controls.  For a podcast, back and forward
skip fifteen seconds, as the Podcasts app's own buttons do; otherwise
they change track.

State comes from macOS's Now Playing -- what Control Center shows -- read
with media-control (`brew install media-control'): Podcasts, Music,
Safari, and spotify_player once its media control is on.  `media-control
stream' reports every change, so nothing polls.  One watcher process runs
it, keeps the merged state in a cache file, and triggers nowplaying_update;
the item's script only draws from the cache, counting elapsed time from
the position Now Playing last reported, and starts the watcher again if
it has died.

macOS keeps the last thing played in Now Playing for as long as its app
runs, so a paused item is hidden once it has played to the end or been
paused for `STALE' seconds, as the Emacs mode line's is (my-nowplaying.el).
"""
from datetime import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import popup as p  # noqa: E402  (shares the popups' helpers and layout)

SELF = str(Path(__file__).resolve())
ITEM = p.NOWPLAYING
PLAY = f'{ITEM}.c.play'
CACHE_FILE = p.CACHE / 'sketchybar-nowplaying.json'
LOCK_FILE = p.CACHE / 'sketchybar-nowplaying.lock'  # held by the one watcher
IDLE_TICK = 30  # seconds between checks on the watcher while nothing plays
STALE = 600  # seconds paused after which an item is hidden
BAR_TITLE = 18  # characters of title in the bar
WIDTH = 34  # characters across the popup
LABEL_WIDTH = math.ceil(WIDTH * p.CHAR) + 2
ROW = p.PAD + p.LABEL_PAD + LABEL_WIDTH + p.PAD
INFO_ROWS = ['title', 'artist', 'progress']
ROW_HEIGHT = 31  # a popup row is as tall as the bar
INFO_HEIGHT = ROW_HEIGHT * len(INFO_ROWS)
ICONS = {'previous': '\U000F04AE', 'play': '\U000F040A', 'pause': '\U000F03E4',
         'next': '\U000F04AD'}  # Nerd Font: skip-previous, play, pause, skip-next
APP_ICONS = {'com.spotify.client': '\uf1bc', 'com.apple.podcasts': '\uf2ce'}  # Nerd Font: spotify, podcast
DEFAULT_APP_ICON = '\uf001'  # Nerd Font: a note, for Music, browsers and the rest
CONTROLS = {  # (back, forward) commands, by kind of media
    'podcast': ('go-back-fifteen-seconds', 'skip-fifteen-seconds'),
    'music': ('previous-track', 'next-track'),
}
LABELS = {'podcast': ('-15s', '+15s'), 'music': (ICONS['previous'], ICONS['next'])}
DROPPED = ('artworkData', 'artworkMimeType')  # large, and not drawn


# ---- Pure parts, covered by sketchybar/tests/test_nowplaying.py ----

def merge(state, message):
    """Return STATE updated by one line of `media-control stream', MESSAGE.
    A message with diff false replaces the state; with diff true it changes
    only the keys it names, and a key set to null is removed."""
    if not isinstance(message, dict) or message.get('type') != 'data':
        return state
    payload = message.get('payload') or {}
    merged = dict(state) if message.get('diff') else {}
    merged.update(payload)
    return {key: value for key, value in merged.items()
            if value is not None and key not in DROPPED}


def seconds_since(timestamp, now):
    """Return seconds from TIMESTAMP, ISO 8601 as media-control writes it, to NOW."""
    try:
        moment = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except (AttributeError, ValueError):
        return 0.0
    return max(0.0, now - moment.timestamp())


def parse(data):
    """Return Now Playing DATA as a flat dict, or None with nothing loaded."""
    if not isinstance(data, dict) or not data.get('title'):
        return None
    podcast = data.get('mediaType') == 'MRMediaRemoteMediaTypePodcast'
    return {
        'title': data['title'],
        'by': data.get('artist') or '',
        'source': data.get('album') or '',
        'playing': bool(data.get('playing')),
        'elapsed': float(data.get('elapsedTime') or 0),
        'rate': float(data.get('playbackRate') or 0),
        'timestamp': data.get('timestamp'),
        'duration': float(data.get('duration') or 0),
        'kind': 'podcast' if podcast else 'music',
        'app': data.get('bundleIdentifier') or '',
    }


def position(info, now):
    """Return INFO's position in seconds at NOW: the reported position, plus
    the time since it was reported at the reported rate while playing."""
    pos = info['elapsed']
    if info['playing']:
        pos += seconds_since(info['timestamp'], now) * (info['rate'] or 1.0)
    return min(pos, info['duration']) if info['duration'] else pos


def stale(info, now):
    """Return whether INFO is paused and left there: played to the end, or
    paused for STALE seconds since Now Playing last reported it."""
    if info['playing']:
        return False
    ended = info['duration'] and info['elapsed'] >= info['duration'] - 1
    return bool(ended) or seconds_since(info['timestamp'], now) >= STALE


def clock(seconds):
    """Return SECONDS as m:ss, or h:mm:ss from an hour."""
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours}:{minutes:02}:{secs:02}' if hours else f'{minutes}:{secs:02}'


def clip(text, length):
    """Return TEXT cut to LENGTH characters, ending in an ellipsis if cut."""
    return text if len(text) <= length else text[:length - 1].rstrip() + '…'


def bar_label(info, pos):
    if not info['duration']:  # a live stream has no length
        return clip(info['title'], BAR_TITLE)
    return f"{clip(info['title'], BAR_TITLE)} {clock(pos)}/{clock(info['duration'])}"


def progress_text(pos, duration, width=WIDTH):
    """Return `1:23 ━━━━──── 5:55', WIDTH characters across."""
    left, right = clock(pos), clock(duration)
    cells = max(0, width - len(left) - len(right) - 2)
    filled = round(cells * pos / duration) if duration else 0
    return f"{left} {'━' * filled}{'─' * (cells - filled)} {right}"


def app_icon(app):
    return APP_ICONS.get(app, DEFAULT_APP_ICON)


def command(kind, action):
    """Return the media-control command for ACTION on media of KIND."""
    if action == 'play-pause':
        return 'toggle-play-pause'
    back, forward = CONTROLS[kind]
    return back if action == 'back' else forward


# ---- media-control and SketchyBar ----

def media_control():
    return shutil.which('media-control') or '/opt/homebrew/bin/media-control'


def cached():
    try:
        return json.loads(CACHE_FILE.read_text())
    except (OSError, ValueError):
        return None


def write_cache(state):
    p.CACHE.mkdir(exist_ok=True)
    temporary = CACHE_FILE.with_suffix('.tmp')
    temporary.write_text(json.dumps({'data': state}))
    temporary.replace(CACHE_FILE)  # atomic: the item never reads half a file


def watching():
    """Return whether a watcher holds the lock."""
    try:
        with open(LOCK_FILE, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(lock, fcntl.LOCK_UN)
        return False
    except BlockingIOError:
        return True
    except OSError:
        return True  # cannot tell; do not start another


def ensure_watcher():
    if not watching():
        subprocess.Popen([sys.executable, SELF, 'watch'], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)


def watch():
    """Run `media-control stream', keeping the cache and the bar current.
    Exits if another watcher holds the lock, or once SketchyBar has gone."""
    p.CACHE.mkdir(exist_ok=True)
    lock = open(LOCK_FILE, 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    while True:
        state = {}
        process = subprocess.Popen([media_control(), 'stream'], stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True)
        for line in process.stdout:
            try:
                state = merge(state, json.loads(line))
            except ValueError:
                continue
            write_cache(state)
            if subprocess.run(['sketchybar', '--trigger', 'nowplaying_update'],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode != 0:
                process.terminate()
                return
        process.wait()
        time.sleep(5)  # media-control ended; start it again


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
    buttons = (('back', side, ICONS['previous']),
               ('play', ROW + p.GRID_SLACK - 2 * side, ICONS['play']),
               ('forward', side, ICONS['next']))
    for name, width, label in buttons:
        item = f'{ITEM}.c.{name}'
        action = 'play-pause' if name == 'play' else name
        args += ['--add', 'item', item, f'popup.{ITEM}',
                 '--set', item, 'icon.drawing=off', f'label.width={width}', 'label.align=center',
                 'label.padding_left=0', 'label.padding_right=0', 'padding_left=0', 'padding_right=0',
                 'label.font=JetBrainsMono Nerd Font:Regular:16.0', f'label.color={palette["FG"]}',
                 f'label={label}', f'click_script={SELF} control {action}']
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
    if not info or stale(info, now):
        p.bar('--set', ITEM, 'drawing=off', f'update_freq={IDLE_TICK}')
        if popup_open:
            p.close(ITEM)
        return
    pos = position(info, now)
    color = palette['BR_GREEN'] if info['playing'] else palette['FG2']
    args = ['--set', ITEM, 'drawing=on', f'icon={app_icon(info["app"])}',
            f'label={bar_label(info, pos)}', f'icon.color={color}', f'label.color={color}',
            # Tick every second only while there is a second to count.
            f'update_freq={1 if info["playing"] else IDLE_TICK}']
    if popup_open:
        bold = 'JetBrainsMono Nerd Font:Bold:13.0'
        by = ' · '.join(part for part in (info['by'], info['source']) if part)
        back, forward = LABELS[info['kind']]
        args += p.show(f'{ITEM}.i.title', clip(info['title'], WIDTH), palette['FG'],
                       **{'label.font': bold})
        args += p.show(f'{ITEM}.i.artist', clip(by, WIDTH), palette['FG2'])
        if info['duration']:
            args += p.show(f'{ITEM}.i.progress', progress_text(pos, info['duration']), color)
        else:
            args += p.hide(f'{ITEM}.i.progress')
        args += ['--set', PLAY, f'label={ICONS["pause" if info["playing"] else "play"]}',
                 '--set', f'{ITEM}.c.back', f'label={back}',
                 '--set', f'{ITEM}.c.forward', f'label={forward}']
    p.bar(*args)


def update():
    if os.environ.get('SENDER') == 'mouse.exited.global':
        p.close(ITEM)
        return
    ensure_watcher()
    render(cached(), time.time(), p.is_open(ITEM))


def toggle():
    p.toggle(ITEM, create, lambda: render(cached(), time.time(), True))


def control(action):
    info = parse((cached() or {}).get('data'))
    kind = info['kind'] if info else 'music'
    subprocess.run([media_control(), command(kind, action)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'update'
    if action == 'update':
        update()
    elif action == 'toggle':
        toggle()
    elif action == 'watch':
        watch()
    elif action == 'control' and sys.argv[2:3] and sys.argv[2] in ('back', 'play-pause', 'forward'):
        control(sys.argv[2])


if __name__ == '__main__':
    main()
