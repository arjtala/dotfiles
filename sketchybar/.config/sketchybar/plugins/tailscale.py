#!/usr/bin/env python3
"""Tailscale's state and an on/off switch, for the tailscale item.

    tailscale.py update     the item's script
    tailscale.py toggle     its click: the popup
    tailscale.py switch     the popup's switch: turn Tailscale on or off
    tailscale.py open       the popup's last row: open the Tailscale app
    tailscale.py status     print what it found and draw nothing, to debug

The bar shows a 3 x 3 dot grid, like Tailscale's logo: green when connected,
aqua when the traffic goes through an exit node, yellow while it starts,
orange when it needs a login, dim when it is off.  The popup has the switch,
the device and tailnet, the exit node, how many peers are online, and a line
for whatever Tailscale is complaining about.  The item is hidden when
Tailscale is not installed.

Two sources are read.  macOS's VPN list (`scutil --nc list') says whether the
Tailscale tunnel is up and answers even when Tailscale is off.  The Tailscale
CLI (`status --json') adds the details, but it may not answer while the
tunnel is down, so "off" comes from the VPN list.

The switch turns Tailscale off with `tailscale down', and stops the tunnel with
`scutil --nc stop' if that did not do it.  To turn it on it runs `tailscale up',
first starting the tunnel with `scutil --nc start' and waiting for the CLI to
answer if nothing does.  A click while Tailscale needs a login
opens the login page, or the app.

Runs under whichever python3 SketchyBar's PATH finds, which may be the
system's 3.9, so nothing newer than 3.9 is used.
"""
import fcntl
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import popup as p  # noqa: E402  (shares the popups' helpers and layout)

SELF = str(Path(__file__).resolve())
ITEM = p.TAILSCALE
# The app's own binary first: /usr/local/bin/tailscale is a wrapper around it,
# and Homebrew's would talk to a different daemon.
CLI_CANDIDATES = ('/Applications/Tailscale.app/Contents/MacOS/Tailscale',
                  '/usr/local/bin/tailscale', '/opt/homebrew/bin/tailscale')
SCUTIL = '/usr/sbin/scutil'
OPEN = '/usr/bin/open'
APP = 'Tailscale'
LOCK_FILE = p.CACHE / 'sketchybar-tailscale.lock'  # held while a click is handled
STATUS_TIMEOUT = 5  # seconds the CLI or scutil has to answer a question
UP_TIMEOUT = 20  # seconds `tailscale up' may wait to be connected
START_WAIT = 15  # seconds to wait for the CLI after starting the tunnel
POLL = 0.5  # seconds between those checks
ICON = '\U000F15FC'  # Nerd Font: md-dots_grid
GLYPHS = {'on': '\U000F0521', 'off': '\U000F0522', 'open': '\U000F03CC'}  # toggle on, toggle off, open-in-new
WIDTH = 34  # characters across the popup
LABEL_WIDTH = math.ceil(WIDTH * p.CHAR) + 2
ROWS = ['title', 'switch', 'device', 'tailnet', 'exit', 'peers', 'note', 'more', 'app']
CLICKS = {'switch': 'switch', 'app': 'open'}  # popup row -> the action its click runs
# Palette colour by kind of state; an exit node in use gets its own.
COLORS = {'on': 'BR_GREEN', 'exit': 'BR_AQUA', 'off': 'FG2', 'busy': 'BR_YELLOW',
          'login': 'BR_ORANGE', 'down': 'FG2'}
# BackendState -> (kind, what the popup says)
BACKEND = {
    'Running': ('on', 'Connected'),
    'Stopped': ('off', 'Off'),
    'Starting': ('busy', 'Starting…'),
    'NoState': ('busy', 'Starting…'),
    'NeedsLogin': ('login', 'Needs login'),
    'NeedsMachineAuth': ('login', 'Waiting for approval'),
}
# A line of `scutil --nc list':  * (Disconnected)  UUID VPN (bundle id) "Name"  [VPN:bundle id]
SERVICE = re.compile(r'^\*?\s*\((?P<state>[^)]*)\)\s+(?P<uuid>[0-9A-Fa-f-]{36})\s+VPN\s+'
                     r'\((?P<bundle>[^)]*)\)\s+"(?P<name>.*)"\s+\[VPN:[^\]]*\]\s*$')


# ---- Pure parts, covered by sketchybar/tests/test_tailscale.py ----

def tailscale_service(text):
    """Return {state, name} for Tailscale's entry in `scutil --nc list' TEXT, or None."""
    for line in text.splitlines():
        match = SERVICE.match(line.strip())
        if match and match.group('bundle').startswith('io.tailscale.'):
            return {'state': match.group('state'), 'name': match.group('name')}
    return None


def mapping(value):
    return value if isinstance(value, dict) else {}


def strings(value):
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def first_ip(addresses):
    """Return the first IPv4 address of ADDRESSES (a 100.x one, in practice), else the first."""
    addresses = [a.split('/')[0] for a in strings(addresses)]  # an exit node's come as 100.1.2.3/32
    return next((a for a in addresses if '.' in a), addresses[0] if addresses else None)


def short_name(node):
    """Return NODE's name on the tailnet: the first label of its DNSName, else its HostName."""
    dns = node.get('DNSName')
    label = dns.split('.')[0] if isinstance(dns, str) else ''
    host = node.get('HostName')
    return label or (host if isinstance(host, str) and host else None)


def summarize(data):
    """Return what the popup shows from the CLI's `status --json' DATA, a flat dict."""
    me = mapping(data.get('Self'))
    peers = [peer for peer in mapping(data.get('Peer')).values() if isinstance(peer, dict)]
    tailnet = mapping(data.get('CurrentTailnet'))
    in_use = mapping(data.get('ExitNodeStatus'))
    exit_peer = next((peer for peer in peers if peer.get('ExitNode')), None)
    exit_node = None
    if in_use or exit_peer:
        exit_node = {'name': (short_name(exit_peer) if exit_peer else None) or first_ip(in_use.get('TailscaleIPs')),
                     'online': bool((exit_peer or in_use).get('Online'))}
    return {
        'backend': data['BackendState'],
        'device': short_name(me),
        'ip': first_ip(me.get('TailscaleIPs') or data.get('TailscaleIPs')),
        'tailnet': tailnet.get('Name') or tailnet.get('MagicDNSSuffix') or data.get('MagicDNSSuffix') or None,
        'peers': len(peers),
        'online': sum(1 for peer in peers if peer.get('Online')),
        'exit': exit_node,
        'health': strings(data.get('Health')),
        'auth_url': data.get('AuthURL') or None,
    }


def resolve(service, summary):
    """Return (kind, headline) from the VPN list's SERVICE and the CLI's SUMMARY.

    The CLI knows best when it answers.  Without it the VPN list says whether
    the tunnel is up; with neither, Tailscale is not running.
    """
    if summary:
        return BACKEND.get(summary['backend'], ('busy', summary['backend']))
    state = service['state'] if service else None
    if state == 'Connected':
        return 'on', 'Connected'
    if state in ('Connecting', 'Reasserting'):
        return 'busy', 'Connecting…'
    if state == 'Disconnecting':
        return 'busy', 'Turning off…'
    if state in ('Disconnected', 'Invalid'):
        return 'off', 'Off'
    return 'down', 'Not running'


def color_name(snap):
    exit_node = snap['summary'] and snap['summary']['exit']
    return COLORS['exit' if snap['kind'] == 'on' and exit_node else snap['kind']]


def clip(text, length):
    """Return TEXT cut to LENGTH characters, ending in an ellipsis if cut."""
    return text if len(text) <= length else text[:length - 1].rstrip() + '…'


def switch_label(kind, headline):
    """Return the switch row's text for a state of KIND."""
    return {'on': f"{GLYPHS['on']}  Turn off",
            'off': f"{GLYPHS['off']}  Turn on",
            'busy': f"{GLYPHS['on']}  {headline}",
            'login': f"{GLYPHS['open']}  Log in…",
            'down': f"{GLYPHS['open']}  Open Tailscale"}[kind]


def rows(snap, note=None):
    """Return the popup's rows as (item name, text or None, palette colour name).
    A row with no text is hidden.  NOTE, if given, replaces Tailscale's own warning;
    a message too long for one row goes on over a second."""
    kind, headline, summary = snap['kind'], snap['headline'], snap['summary']
    key = color_name(snap)
    result = [('title', f'Tailscale · {headline}', key),
              ('switch', switch_label(kind, headline), key)]
    device = tailnet = exit_text = peers = warning = None
    if summary:
        device = ' · '.join(part for part in (summary['device'], summary['ip']) if part) or None
        tailnet = summary['tailnet']
        if kind == 'on':
            node = summary['exit']
            exit_text = ('none' if node is None
                         else f"{node['name'] or 'unknown'}{'' if node['online'] else ' (offline)'}")
            peers = f"{summary['online']} of {summary['peers']} online"
            warning = summary['health'][0] if summary['health'] else None
    lines = textwrap.wrap(note or warning or '', WIDTH)
    first = lines[0] if lines else None
    rest = clip(' '.join(lines[1:]), WIDTH) if len(lines) > 1 else None
    message_color = 'BR_ORANGE' if note else 'FG2'
    result += [('device', device and f'Device   {device}', 'FG'),
               ('tailnet', tailnet and f'Tailnet  {tailnet}', 'FG'),
               ('exit', exit_text and f'Exit     {exit_text}', 'FG'),
               ('peers', peers and f'Peers    {peers}', 'FG'),
               ('note', first, message_color),
               ('more', rest, message_color),
               ('app', None if kind in ('login', 'down') else 'Open Tailscale…', 'FG2')]
    return [(name, text and clip(text, WIDTH), color) for name, text, color in result]


# ---- Tailscale, macOS and SketchyBar ----

def run(command, timeout):
    """Run COMMAND; return (status, stdout, stderr), or None if it did not start or ran too long."""
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.returncode, done.stdout, done.stderr


def find_cli():
    for path in CLI_CANDIDATES:
        if os.access(path, os.X_OK):
            return path
    return shutil.which('tailscale')


def vpn_service():
    result = run([SCUTIL, '--nc', 'list'], STATUS_TIMEOUT)
    return tailscale_service(result[1]) if result and result[0] == 0 else None


def fetch_status(cli):
    """Return the CLI's `status --json' as a dict, or None if it cannot answer.
    The exit status is not looked at: some states print the JSON and still exit 1."""
    result = run([cli, 'status', '--json'], STATUS_TIMEOUT) if cli else None
    if result is None:
        return None
    try:
        data = json.loads(result[1])
    except ValueError:
        return None
    return data if isinstance(data, dict) and isinstance(data.get('BackendState'), str) else None


def take():
    """Return the state as {kind, headline, summary, service, cli, auth_url}, or None
    if Tailscale is not installed."""
    service, cli = vpn_service(), find_cli()
    if service is None and cli is None:
        return None
    data = fetch_status(cli)
    summary = summarize(data) if data else None
    kind, headline = resolve(service, summary)
    return {'kind': kind, 'headline': headline, 'summary': summary, 'service': service, 'cli': cli}


def wait_for(check, seconds):
    """Return CHECK()'s first true value within SECONDS, else None."""
    deadline = time.time() + seconds
    while True:
        value = check()
        if value or time.time() >= deadline:
            return value or None
        time.sleep(POLL)


def first_line(result):
    """Return the first line of what a failed command said, for the popup."""
    text = (result[2] or result[1]).strip() if result else ''
    return text.splitlines()[0] if text else None


def open_app(url=None):
    run([OPEN, url] if url else [OPEN, '-a', APP], STATUS_TIMEOUT)


def turn_off(snap):
    """Turn Tailscale off.  Return a message if it did not work, else None.
    What counts is the state afterwards, not the exit status: a CLI that cannot
    start says so and still exits 0.  If `down' did not do it, stop the tunnel."""
    def still_on():
        now = take()
        return now is not None and now['kind'] == 'on'

    result = run([snap['cli'], 'down'], STATUS_TIMEOUT * 3) if snap['cli'] else None
    if result and result[0] == 0 and not still_on():
        return None
    said = first_line(result)
    if snap['service']:
        result = run([SCUTIL, '--nc', 'stop', snap['service']['name']], STATUS_TIMEOUT * 3)
        if not still_on():
            return None
        said = first_line(result) or said
    return said or "Couldn't turn Tailscale off"


def turn_on(snap):
    """Turn Tailscale on.  Return a message if it did not work, else None."""
    cli = snap['cli']
    if cli is None:
        return 'The Tailscale command is missing; open the app'
    data = fetch_status(cli)
    if data is None:  # nothing answers: start the tunnel, which starts the backend
        if snap['service'] is None:
            return 'No Tailscale VPN service; open the app'
        run([SCUTIL, '--nc', 'start', snap['service']['name']], STATUS_TIMEOUT * 3)
        data = wait_for(lambda: fetch_status(cli), START_WAIT)
        if data is None:
            service = vpn_service()
            if service and service['state'] in ('Connected', 'Connecting'):
                return "Started, but the Tailscale command isn't answering"
            return "Tailscale didn't start"
    backend = data['BackendState']
    if backend == 'Running':
        return None
    if backend in ('NeedsLogin', 'NeedsMachineAuth'):
        open_app(data.get('AuthURL') or None)
        return 'Log in to Tailscale'
    result = run([cli, 'up', f'--timeout={UP_TIMEOUT}s'], UP_TIMEOUT + STATUS_TIMEOUT)
    return None if result and result[0] == 0 else (first_line(result) or "Couldn't turn Tailscale on")


def create():
    palette = p.colors()
    args = ['--remove', f'/{ITEM}\\.i\\..*/',
            '--set', ITEM, 'popup.align=right', f'popup.background.color={palette["BG1"]}',
            f'popup.background.corner_radius={p.RADIUS}', 'popup.background.border_width=0']
    for name in ROWS:
        item = f'{ITEM}.i.{name}'
        args += ['--add', 'item', item, f'popup.{ITEM}',
                 '--set', item, 'icon.drawing=off', f'label.width={LABEL_WIDTH}',
                 f'label.padding_left={p.LABEL_PAD}', 'label.padding_right=0',
                 f'padding_left={p.PAD}', f'padding_right={p.PAD}']
        if name in CLICKS:
            args.append(f'click_script={SELF} {CLICKS[name]}')
    p.bar(*args)


def render(snap, popup_open, note=None):
    palette = p.colors()
    if snap is None:  # not installed: not drawn, and no popup left open
        p.bar('--set', ITEM, 'drawing=off', 'popup.drawing=off')
        return
    color = palette[color_name(snap)]
    args = ['--set', ITEM, 'drawing=on', f'icon={ICON}', f'icon.color={color}', 'label.drawing=off']
    if popup_open:
        bold = 'JetBrainsMono Nerd Font:Bold:13.0'
        for name, text, key in rows(snap, note):
            item = f'{ITEM}.i.{name}'
            if not text:
                args += p.hide(item)
            else:
                extra = {'label.font': bold} if name == 'title' else {}
                args += p.show(item, text, palette[key], **extra)
    p.bar(*args)


def update():
    if os.environ.get('SENDER') == 'mouse.exited.global':
        p.close(ITEM)
        return
    snap = take()
    render(snap, snap is not None and p.is_open(ITEM))


def toggle():
    p.toggle(ITEM, create, lambda: render(take(), True))


def switch():
    """The popup's switch.  One click is handled at a time: the lock is held until
    Tailscale has finished, which can be a while when it has to start."""
    LOCK_FILE.parent.mkdir(exist_ok=True)
    with open(LOCK_FILE, 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        snap = take()
        if snap is None or snap['kind'] == 'busy':
            return
        kind, summary = snap['kind'], snap['summary']
        if kind in ('login', 'down'):
            open_app(summary['auth_url'] if kind == 'login' and summary else None)
            return
        busy = 'Turning off…' if kind == 'on' else 'Turning on…'
        p.bar('--set', f'{ITEM}.i.switch', f"label={GLYPHS['on']}  {busy}")
        message = turn_off(snap) if kind == 'on' else turn_on(snap)
        after = take()
        if message is None and after is not None and after['kind'] == kind:
            message = f"Still {'on' if kind == 'on' else 'off'}; try again"
        render(after, True, message)


def status():
    service, cli = vpn_service(), find_cli()
    print('VPN list   :', service or 'no Tailscale service')
    print('CLI        :', cli or 'not found')
    if cli:
        result = run([cli, 'status', '--json'], STATUS_TIMEOUT)
        if result is None:
            print(f'status     : no answer within {STATUS_TIMEOUT} s')
        elif fetch_status(cli) is None:
            print('status     : no usable JSON:', first_line(result) or '(no output)', f'(exit {result[0]})')
        else:
            print('status     : JSON ok')
    snap = take()
    if snap is None:
        print('the item   : hidden (Tailscale is not installed)')
        return
    print(f"the item   : {snap['kind']} ({snap['headline']})")
    for name, text, _ in rows(snap):
        if text:
            print(f'  {name:<8} {text}')


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'update'
    {'update': update, 'toggle': toggle, 'switch': switch, 'open': open_app,
     'status': status}.get(action, lambda: None)()


if __name__ == '__main__':
    main()
