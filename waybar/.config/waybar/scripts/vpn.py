#!/usr/bin/env python3
"""Local VPN status from NetworkManager and Tailscale; never changes connections."""
import html
import json
import subprocess


def output(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=4)
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def describe(nm, tailscale):
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
    if tailscale is not None:
        state = tailscale.get('BackendState', 'Unknown')
        if state == 'Running':
            connected.append('Tailscale')
            exit_node = tailscale.get('ExitNodeStatus')
            if exit_node:
                ips = ', '.join(exit_node.get('TailscaleIPs') or [])
                health = 'online' if exit_node.get('Online') else 'offline'
                details.append(f'Tailscale · exit node selected ({health})' + (f': {ips}' if ips else ''))
            else:
                details.append('Tailscale · tailnet connected · no exit node')
            ips = ', '.join(tailscale.get('TailscaleIPs') or [])
            if ips:
                details.append(f'Tailscale IP: {ips}')
            details.extend(tailscale.get('Health') or [])
        else:
            details.append(f'Tailscale · {state}')
    else:
        details.append('Tailscale status unavailable')
    return {
        'text': '󰦝' if connected else '󰦞',
        'class': 'con' if connected else 'discon',
        'tooltip': html.escape('\n'.join(details) or 'No active VPN'),
    }


def main():
    nm = output(['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show', '--active'])
    raw = output(['tailscale', 'status', '--json'])
    try:
        tailscale = json.loads(raw) if raw else None
        if not isinstance(tailscale, dict):
            tailscale = None
    except ValueError:
        tailscale = None
    print(json.dumps(describe(nm, tailscale)))


if __name__ == '__main__':
    main()
