#!/usr/bin/env python3
"""Linux Tailscale status and explicit popup actions (no automatic connection changes)."""
import html
import json
import shutil
import subprocess
from urllib.parse import urlparse

ICON = '\U000f15fc'
STATES = {
    'Running': ('on', 'Connected'),
    'Stopped': ('off', 'Off'),
    'Starting': ('busy', 'Starting…'),
    'NoState': ('busy', 'Starting…'),
    'NeedsLogin': ('login', 'Needs login'),
    'NeedsMachineAuth': ('approval', 'Waiting for approval'),
}


def mapping(value):
    return value if isinstance(value, dict) else {}


def name(node):
    return str(node.get('DNSName') or node.get('HostName') or '').split('.')[0]


def summarize(data):
    kind, headline = STATES.get(data.get('BackendState'), ('down', 'Status unavailable'))
    me = mapping(data.get('Self'))
    peers = [p for p in mapping(data.get('Peer')).values() if isinstance(p, dict)]
    selected = mapping(data.get('ExitNodeStatus'))
    exit_peer = next((p for p in peers if p.get('ExitNode')), {})
    addresses = me.get('TailscaleIPs') or data.get('TailscaleIPs') or []
    addresses = addresses if isinstance(addresses, list) else []
    tailnet = mapping(data.get('CurrentTailnet'))
    exit_node = 'None'
    if selected or exit_peer:
        exit_node = name(exit_peer) or ', '.join(selected.get('TailscaleIPs') or []) or 'Selected'
        if not (exit_peer or selected).get('Online'):
            exit_node += ' (offline)'
        if kind == 'on':
            kind = 'exit'
    rows = [('Device', name(me) or 'Unknown'),
            ('IP', ', '.join(str(ip) for ip in addresses) or 'Unavailable'),
            ('Tailnet', str(tailnet.get('Name') or tailnet.get('MagicDNSSuffix') or 'Unknown'))]
    if kind in ('on', 'exit'):
        rows += [('Exit node', exit_node),
                 ('Peers', f"{sum(bool(p.get('Online')) for p in peers)} of {len(peers)} online")]
    health = data.get('Health')
    return {'kind': kind, 'headline': headline, 'rows': rows,
            'health': '\n'.join(s for s in health if isinstance(s, str)) if isinstance(health, list) else '',
            'auth_url': data.get('AuthURL')}


def snapshot():
    cli = shutil.which('tailscale')
    if not cli:
        return None
    try:
        result = subprocess.run([cli, 'status', '--json'], capture_output=True, text=True, timeout=4)
        # Logged-out/stopped states may return valid JSON with a nonzero exit code.
        data = json.loads(result.stdout)
        if isinstance(data, dict) and isinstance(data.get('BackendState'), str):
            return summarize(data)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return {'kind': 'down', 'headline': 'Daemon unavailable', 'rows': [],
            'health': 'Check tailscaled: systemctl status tailscaled', 'auth_url': None}


def bar_output(state):
    if state is None:
        return {'text': '', 'tooltip': '', 'class': 'missing'}
    tooltip = ['Tailscale · ' + state['headline']]
    tooltip += [f'{key}: {value}' for key, value in state['rows']]
    if state['health']:
        tooltip.append(state['health'])
    return {'text': ICON, 'class': state['kind'], 'tooltip': html.escape('\n'.join(tooltip))}


def action_label(state):
    if not state:
        return 'Tailscale is not installed'
    return {'on': 'Turn off', 'exit': 'Turn off', 'off': 'Turn on',
            'login': 'Log in…', 'approval': 'Awaiting approval',
            'busy': 'Connecting…', 'down': 'Daemon unavailable'}[state['kind']]


def switch(state):
    """Called only by a popup button; return an actionable error or None."""
    if not state or state['kind'] not in ('on', 'exit', 'off', 'login'):
        return 'Tailscale is not ready to change state'
    if state['kind'] == 'login':
        url = state.get('auth_url')
        if not isinstance(url, str) or urlparse(url).scheme != 'https' or not urlparse(url).netloc:
            return 'Run tailscale up in a terminal to log in'
        try:
            subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return 'Complete login in your browser'
        except OSError:
            return 'Could not open a browser; run tailscale up in a terminal'
    enabled = state['kind'] in ('on', 'exit')
    command = ['tailscale', 'down'] if enabled else ['tailscale', 'up', '--timeout=15s']
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return 'Tailscale did not respond; check its status in a terminal'
    if result.returncode:
        error = (result.stderr or result.stdout).strip()
        if any(s in error.lower() for s in ('access denied', 'permission denied', 'not permitted')):
            return 'Allow your user to manage Tailscale: sudo tailscale set --operator="$USER"'
        return error[:500] or 'Tailscale could not change state'
    after = snapshot()
    expected = ('off',) if enabled else ('on', 'exit')
    if not after or after['kind'] not in expected:
        return 'State change is not confirmed; check tailscale status'
    return None


if __name__ == '__main__':
    print(json.dumps(bar_output(snapshot())))
