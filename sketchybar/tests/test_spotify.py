import importlib.util
from pathlib import Path
import sys
import unittest

PLUGINS = Path(__file__).resolve().parents[1] / '.config/sketchybar/plugins'
sys.path.insert(0, str(PLUGINS))
spec = importlib.util.spec_from_file_location('spotify', PLUGINS / 'spotify.py')
spotify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spotify)

TRACK = {
    'is_playing': True,
    'progress_ms': 83_000,
    'item': {
        'name': 'Bohemian Rhapsody',
        'duration_ms': 355_000,
        'artists': [{'name': 'Queen'}],
        'album': {'name': 'A Night at the Opera'},
    },
}


class ParseTests(unittest.TestCase):
    def test_a_track(self):
        self.assertEqual(spotify.parse(TRACK), {
            'title': 'Bohemian Rhapsody', 'by': 'Queen', 'source': 'A Night at the Opera',
            'playing': True, 'progress': 83_000, 'duration': 355_000})

    def test_several_artists_are_joined(self):
        data = dict(TRACK, item=dict(TRACK['item'], artists=[{'name': 'A'}, {'name': 'B'}]))
        self.assertEqual(spotify.parse(data)['by'], 'A, B')

    def test_an_episode_is_by_its_show(self):
        data = dict(TRACK, item={'name': 'Ep', 'duration_ms': 1, 'show': {'name': 'Pod'}})
        self.assertEqual((spotify.parse(data)['by'], spotify.parse(data)['source']), ('Pod', ''))

    def test_nothing_loaded(self):
        for data in (None, {}, {'is_playing': False, 'item': None}, 'null'):
            self.assertIsNone(spotify.parse(data))


class TimeTests(unittest.TestCase):
    def test_elapsed_counts_on_while_playing(self):
        info = spotify.parse(TRACK)
        self.assertEqual(spotify.elapsed(info, 100.0, 110.0), 93_000)

    def test_elapsed_stands_still_while_paused(self):
        info = spotify.parse(dict(TRACK, is_playing=False))
        self.assertEqual(spotify.elapsed(info, 100.0, 110.0), 83_000)

    def test_elapsed_stops_at_the_end(self):
        info = spotify.parse(TRACK)
        self.assertEqual(spotify.elapsed(info, 100.0, 10_000.0), 355_000)

    def test_clock(self):
        self.assertEqual(spotify.clock(83_000), '1:23')
        self.assertEqual(spotify.clock(5_000), '0:05')
        self.assertEqual(spotify.clock(3_723_000), '1:02:03')

    def test_stale_after_the_poll_or_a_finished_track(self):
        state = {'fetched': 100.0, 'data': TRACK}
        self.assertFalse(spotify.stale(state, 105.0))
        self.assertTrue(spotify.stale(state, 100.0 + spotify.POLL))
        # 1s left in the track: past it, read again without waiting.
        self.assertTrue(spotify.stale(dict(state, data=dict(TRACK, progress_ms=354_000)), 103.0))
        self.assertTrue(spotify.stale(None, 0))


class ClientIdTests(unittest.TestCase):
    def test_reads_the_configured_client_id(self):
        config = 'theme = "dracula"\n# client_id = "commented"\nclient_id = "abc123"\n'
        self.assertEqual(spotify.client_id(config), 'abc123')

    def test_falls_back_to_spotify_players_default(self):
        self.assertEqual(spotify.client_id('theme = "dracula"\n'), spotify.DEFAULT_CLIENT_ID)


class TextTests(unittest.TestCase):
    def test_bar_label_clips_the_title_not_the_time(self):
        info = spotify.parse(TRACK)
        self.assertEqual(spotify.bar_label(info, 83_000), 'Bohemian Rhapsody 1:23/5:55')
        long = dict(info, title='A' * 40)
        label = spotify.bar_label(long, 83_000)
        self.assertTrue(label.endswith('… 1:23/5:55'))
        self.assertEqual(len(label.split(' ')[0]), spotify.BAR_TITLE)

    def test_progress_fills_in_proportion_and_keeps_its_width(self):
        for position in (0, 83_000, 355_000):
            text = spotify.progress_text(position, 355_000)
            self.assertEqual(len(text), spotify.WIDTH)
        self.assertNotIn('━', spotify.progress_text(0, 355_000))
        self.assertNotIn('─', spotify.progress_text(355_000, 355_000))
        half = spotify.progress_text(177_500, 355_000)
        self.assertEqual(half.count('━'), half.count('─'))


if __name__ == '__main__':
    unittest.main()
