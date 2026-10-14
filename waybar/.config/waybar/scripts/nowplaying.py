#!/usr/bin/env python3
"""MPRIS watcher: Waybar JSON on stdout, shared snapshot for the media popup."""
import html
import json
import os
from pathlib import Path
import time

import gi
gi.require_version('Playerctl', '2.0')
from gi.repository import GLib, Playerctl


def cache_path():
    return Path(os.environ['XDG_RUNTIME_DIR']) / 'waybar-nowplaying.json'


def clock(seconds):
    minutes, seconds = divmod(max(0, int(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f'{hours}:{minutes:02}:{seconds:02}' if hours else f'{minutes}:{seconds:02}'


def position(info, now=None):
    elapsed = info['elapsed']
    if info['playing']:
        elapsed += max(0, (time.monotonic() if now is None else now) - info['sampled'])
    return min(elapsed, info['duration']) if info['duration'] else elapsed


def bar_output(info):
    if not info:
        return {'text': '', 'class': 'idle'}
    title = info['title']
    title = title if len(title) <= 18 else title[:17].rstrip() + '…'
    icon = '\uf1bc' if 'spotify' in info['player'].lower() else '\uf001'
    text = f'{icon} {title}'
    if info['duration']:
        text += f" {clock(position(info))}/{clock(info['duration'])}"
    return {'text': html.escape(text), 'class': 'playing' if info['playing'] else 'paused'}


def read_snapshot():
    try:
        snapshot = json.loads(cache_path().read_text())
        if 0 <= time.monotonic() - snapshot['updated'] < 15:
            return snapshot['media']
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def select_player(states):
    candidates = [state for state in states if state.get('title') and state['status'] != 'Stopped']
    return max(candidates, key=lambda state: (state['playing'], state['activity'], state['player']), default=None)


class Watcher:
    def __init__(self):
        self.players = {}
        self.activity = {}
        self.last_output = None
        self.manager = Playerctl.PlayerManager()
        self.manager.connect('name-appeared', lambda _, name: self.add(name))
        self.manager.connect('player-vanished', self.remove)
        for name in self.manager.props.player_names:
            self.add(name)
        self.publish()
        GLib.timeout_add_seconds(1, self.publish)

    def add(self, name):
        try:
            player = Playerctl.Player.new_from_name(name)
            key = player.props.player_instance
            if key in self.players:
                return
            self.players[key] = player
            self.activity[key] = time.monotonic()
            for event in ('metadata', 'playback-status', 'seeked'):
                player.connect(event, self.changed)
            self.manager.manage_player(player)
            self.publish()
        except GLib.Error:
            pass

    def remove(self, _manager, player):
        key = player.props.player_instance
        self.players.pop(key, None)
        self.activity.pop(key, None)
        self.publish()

    def changed(self, player, *_):
        self.activity[player.props.player_instance] = time.monotonic()
        self.publish()

    def state(self, player):
        metadata = player.props.metadata.unpack()
        title = metadata.get('xesam:title') or ''
        artist = metadata.get('xesam:artist') or []
        if isinstance(artist, list):
            artist = ', '.join(artist)
        status = player.props.status
        try:
            elapsed = max(0, player.get_position() / 1_000_000)
        except GLib.Error:
            elapsed = 0
        return {
            'player': player.props.player_instance,
            'title': str(title), 'artist': str(artist),
            'album': str(metadata.get('xesam:album') or ''),
            'status': status, 'playing': status == 'Playing',
            'duration': max(0, int(metadata.get('mpris:length') or 0) / 1_000_000),
            'elapsed': elapsed,
            'sampled': time.monotonic(),
            'activity': self.activity[player.props.player_instance],
            'can_play': player.props.can_control and (player.props.can_pause if status == 'Playing' else player.props.can_play),
            'can_seek': player.props.can_control and player.props.can_seek,
            'can_previous': player.props.can_control and player.props.can_go_previous,
            'can_next': player.props.can_control and player.props.can_go_next,
        }

    def publish(self):
        states = []
        for player in list(self.players.values()):
            try:
                states.append(self.state(player))
            except (GLib.Error, ValueError, TypeError):
                continue
        info = select_player(states)
        path = cache_path()
        temporary = path.with_name(f'{path.name}.{os.getpid()}.tmp')
        temporary.write_text(json.dumps({'updated': time.monotonic(), 'media': info}))
        temporary.replace(path)
        output = json.dumps(bar_output(info))
        if output != self.last_output:
            print(output, flush=True)
            self.last_output = output
        return True


if __name__ == '__main__':
    try:
        Watcher()
        GLib.MainLoop().run()
    except BrokenPipeError:
        os._exit(0)
