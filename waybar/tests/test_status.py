import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / '.config/waybar/scripts'
sys.path.insert(0, str(SCRIPTS))
import nowplaying
import vpn


class VpnTests(unittest.TestCase):
    def test_tailnet_without_exit_node_is_connected(self):
        state = vpn.describe('', {'BackendState': 'Running'})
        self.assertEqual(state['class'], 'con')
        self.assertIn('no exit node', state['tooltip'])

    def test_exit_node_status_is_not_assumed_online(self):
        state = vpn.describe('', {'BackendState': 'Running', 'ExitNodeStatus': {'Online': False}})
        self.assertIn('exit node selected (offline)', state['tooltip'])

    def test_stopped_tailscale_is_not_connected(self):
        self.assertEqual(vpn.describe('', {'BackendState': 'Stopped'})['class'], 'discon')

    def test_networkmanager_vpn_and_wireguard(self):
        for kind in ('vpn', 'wireguard'):
            state = vpn.describe(f'work\\: office:{kind}\nwifi:802-11-wireless', None)
            self.assertEqual(state['class'], 'con')
            self.assertIn('work: office', state['tooltip'])

    def test_unavailable_services_and_escaped_markup(self):
        self.assertEqual(vpn.describe(None, None)['class'], 'discon')
        self.assertIn('&amp;', vpn.describe('work & home:vpn', None)['tooltip'])


class MediaTests(unittest.TestCase):
    def state(self, **overrides):
        data = dict(player='test', title='Song <3 & more', status='Playing', playing=True,
                    activity=1, duration=300, elapsed=20, sampled=10)
        data.update(overrides)
        return data

    def test_playing_wins_over_recent_paused_player(self):
        playing = self.state()
        paused = self.state(player='other', playing=False, status='Paused', activity=100)
        self.assertEqual(nowplaying.select_player([paused, playing]), playing)

    def test_recent_playing_wins(self):
        first = self.state()
        last = self.state(player='new', activity=2)
        self.assertEqual(nowplaying.select_player([first, last]), last)

    def test_stopped_and_empty_players_are_hidden(self):
        self.assertIsNone(nowplaying.select_player([self.state(status='Stopped'), self.state(title='')]))
        self.assertEqual(nowplaying.bar_output(None)['text'], '')

    def test_position_freezes_on_pause_and_clamps_at_end(self):
        self.assertEqual(nowplaying.position(self.state(), now=30), 40)
        self.assertEqual(nowplaying.position(self.state(playing=False), now=30), 20)
        self.assertEqual(nowplaying.position(self.state(), now=900), 300)

    def test_bar_escapes_metadata_and_shows_pause(self):
        data = nowplaying.bar_output(self.state(playing=False))
        self.assertIn('&lt;3 &amp;', data['text'])
        self.assertEqual(data['class'], 'paused')
        self.assertIn('0:20/5:00', data['text'])


if __name__ == '__main__':
    unittest.main()
