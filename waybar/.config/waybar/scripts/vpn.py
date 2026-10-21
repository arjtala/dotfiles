#!/usr/bin/env python3
"""NetworkManager VPN status; Tailscale has its own module."""
import html
import json
import subprocess


def output(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=4)
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def describe(nm):
    connected = []
    details = []
    if nm is not None:
        for line in nm.splitlines():
            name, _, kind = line.rpartition(':')
            if kind in ('vpn', 'wireguard'):
                name = name.replace('\\:', ':').replace('\\\\', '\\')
                connected.append(name)
                details.append(f'{name} ({kind})')
    else:
        details.append('NetworkManager status unavailable')
    return {
        'text': '󰦝' if connected else '󰦞',
        'class': 'con' if connected else 'discon',
        'tooltip': html.escape('\n'.join(details) or 'No active VPN'),
    }


def main():
    nm = output(['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show', '--active'])
    print(json.dumps(describe(nm)))


if __name__ == '__main__':
    main()
