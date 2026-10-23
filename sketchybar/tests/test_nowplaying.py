from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import unittest

PLUGINS = Path(__file__).resolve().parents[1] / '.config/sketchybar/plugins'
sys.path.insert(0, str(PLUGINS))
spec = importlib.util.spec_from_file_location('nowplaying', PLUGINS / 'nowplaying.py')
nowplaying = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nowplaying)

# What `media-control get` printed for a Podcasts episode on macOS 27.
EPISODE = {
    'playbackRate': 1, 'album': 'October 3, 2026',
    'mediaType': 'MRMediaRemoteMediaTypePodcast', 'playing': True,
    'elapsedTime': 1720.004, 'timestamp': '2026-10-13T18:49:48Z',
    'bundleIdentifier': 'com.apple.podcasts',
    'title': '‘There’s no such thing as democracy’: Yanis Varoufakis',
    'duration': 3298.27, 'artist': 'Today in Focus', 'genre': '',
}
REPORTED = datetime(2026, 10, 13, 18, 49, 48, tzinfo=timezone.utc).timestamp()


class MergeTests(unittest.TestCase):
    def test_a_full_message_replaces_the_state(self):
        state = nowplaying.merge({'title': 'Old', 'stale': 1},
                                 {'type': 'data', 'diff': False, 'payload': EPISODE})
        self.assertEqual(state['title'], EPISODE['title'])
        self.assertNotIn('stale', state)

    def test_a_diff_changes_only_what_it_names(self):
        state = nowplaying.merge(EPISODE, {'type': 'data', 'diff': True,
                                           'payload': {'playing': False, 'playbackRate': 0}})
        self.assertFalse(state['playing'])
        self.assertEqual(state['title'], EPISODE['title'])

    def test_a_diff_to_null_removes_the_key(self):
        state = nowplaying.merge(EPISODE, {'type': 'data', 'diff': True, 'payload': {'artist': None}})
        self.assertNotIn('artist', state)

    def test_artwork_is_not_kept(self):
        state = nowplaying.merge({}, {'type': 'data', 'diff': True,
                                      'payload': {'artworkData': 'AAAA', 'artworkMimeType': 'image/jpeg'}})
        self.assertEqual(state, {})

    def test_an_empty_payload_means_nothing_is_playing(self):
        state = nowplaying.merge(EPISODE, {'type': 'data', 'diff': False, 'payload': {}})
        self.assertIsNone(nowplaying.parse(state))

    def test_other_messages_change_nothing(self):
        self.assertEqual(nowplaying.merge(EPISODE, {'type': 'other'}), EPISODE)


class PositionTests(unittest.TestCase):
    def test_playing_counts_on_from_the_report(self):
        info = nowplaying.parse(EPISODE)
        self.assertAlmostEqual(nowplaying.position(info, REPORTED + 10), 1730.004, places=3)

    def test_at_double_speed_it_counts_twice_as_fast(self):
        info = nowplaying.parse(dict(EPISODE, playbackRate=2))
        self.assertAlmostEqual(nowplaying.position(info, REPORTED + 10), 1740.004, places=3)

    def test_paused_stands_still(self):
        info = nowplaying.parse(dict(EPISODE, playing=False, playbackRate=0))
        self.assertAlmostEqual(nowplaying.position(info, REPORTED + 600), 1720.004, places=3)

    def test_it_stops_at_the_end(self):
        info = nowplaying.parse(EPISODE)
        self.assertEqual(nowplaying.position(info, REPORTED + 100000), EPISODE['duration'])


class StaleTests(unittest.TestCase):
    def test_playing_is_never_stale(self):
        info = nowplaying.parse(EPISODE)
        self.assertFalse(nowplaying.stale(info, REPORTED + 100000))

    def test_paused_goes_stale_after_ten_minutes(self):
        info = nowplaying.parse(dict(EPISODE, playing=False, playbackRate=0))
        self.assertFalse(nowplaying.stale(info, REPORTED + nowplaying.STALE - 1))
        self.assertTrue(nowplaying.stale(info, REPORTED + nowplaying.STALE))

    def test_finished_is_stale_at_once(self):
        info = nowplaying.parse(dict(EPISODE, playing=False, elapsedTime=EPISODE['duration']))
        self.assertTrue(nowplaying.stale(info, REPORTED))

    def test_a_paused_stream_without_a_time_stays(self):
        info = nowplaying.parse(dict(EPISODE, playing=False, duration=0, timestamp=None))
        self.assertFalse(nowplaying.stale(info, REPORTED + 100000))

    def test_clock(self):
        self.assertEqual(nowplaying.clock(83), '1:23')
        self.assertEqual(nowplaying.clock(3298.27), '54:58')
        self.assertEqual(nowplaying.clock(3723), '1:02:03')


class ParseTests(unittest.TestCase):
    def test_a_podcast_episode(self):
        info = nowplaying.parse(EPISODE)
        self.assertEqual((info['by'], info['source'], info['kind'], info['app']),
                         ('Today in Focus', 'October 3, 2026', 'podcast', 'com.apple.podcasts'))

    def test_a_song_is_music(self):
        self.assertEqual(nowplaying.parse(dict(EPISODE, mediaType='MRMediaRemoteMediaTypeMusic'))['kind'],
                         'music')

    def test_nothing_loaded(self):
        for data in (None, {}, {'artist': 'No title'}):
            self.assertIsNone(nowplaying.parse(data))


class ControlTests(unittest.TestCase):
    def test_podcasts_skip_fifteen_seconds(self):
        self.assertEqual(nowplaying.command('podcast', 'back'), 'go-back-fifteen-seconds')
        self.assertEqual(nowplaying.command('podcast', 'forward'), 'skip-fifteen-seconds')

    def test_music_changes_track(self):
        self.assertEqual(nowplaying.command('music', 'back'), 'previous-track')
        self.assertEqual(nowplaying.command('music', 'forward'), 'next-track')

    def test_play_pause_toggles_for_both(self):
        for kind in ('podcast', 'music'):
            self.assertEqual(nowplaying.command(kind, 'play-pause'), 'toggle-play-pause')

    def test_app_icons(self):
        self.assertEqual(nowplaying.app_icon('com.apple.podcasts'), '\uf2ce')
        self.assertEqual(nowplaying.app_icon('com.apple.Music'), nowplaying.DEFAULT_APP_ICON)


class TextTests(unittest.TestCase):
    def test_bar_label_clips_the_title_not_the_time(self):
        info = nowplaying.parse(EPISODE)
        label = nowplaying.bar_label(info, 1720)
        self.assertTrue(label.endswith('… 28:40/54:58'))
        # At most the limit: a space at the cut is trimmed before the ellipsis.
        self.assertLessEqual(len(label.split(' 28:40')[0]), nowplaying.BAR_TITLE)

    def test_a_stream_without_a_length_shows_no_time(self):
        info = nowplaying.parse(dict(EPISODE, duration=0, title='Live radio'))
        self.assertEqual(nowplaying.bar_label(info, 100), 'Live radio')

    def test_progress_keeps_its_width(self):
        for pos in (0, 1720, 3298.27):
            self.assertEqual(len(nowplaying.progress_text(pos, 3298.27)), nowplaying.WIDTH)


if __name__ == '__main__':
    unittest.main()
