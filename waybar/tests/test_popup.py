import importlib.util
from datetime import datetime, date
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location(
    'popup', Path(__file__).resolve().parents[1] / '.config/waybar/scripts/popup.py')
popup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(popup)


class PlacementTests(unittest.TestCase):
    def test_centered_above_click(self):
        self.assertEqual(popup.panel_left(450, 300, 1920), 300)

    def test_left_and_right_edges(self):
        self.assertEqual(popup.panel_left(40, 300, 1920), 8)
        self.assertEqual(popup.panel_left(1900, 300, 1920), 1612)

    def test_content_width_change_keeps_anchor(self):
        self.assertEqual(popup.panel_left(450, 400, 1920), 250)


class PrayerStateTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            'date': '2026-10-11',
            'sunrise': '07:08',
            'prayers': [dict(name=name, time=time) for name, time in zip(
                popup.PRAYER_NAMES, ['05:42', '12:58', '16:12', '18:39', '19:54'])],
        }

    def state(self, hour, minute):
        return popup.prayer_state(self.data, datetime(
            2026, 10, 11, hour, minute, tzinfo=ZoneInfo('America/Los_Angeles')))

    def test_before_fajr_highlights_todays_fajr(self):
        current, day, following = self.state(5, 41)
        self.assertEqual((current, day), ('Fajr', date(2026, 10, 11)))
        self.assertEqual(following, 'Next: Fajr in 1 min')

    def test_midnight_starts_new_day_with_fajr(self):
        self.assertEqual(self.state(23, 59)[0], 'Isha')
        self.data['date'] = '2026-10-12'
        now = datetime(2026, 10, 12, 0, 0, tzinfo=ZoneInfo('America/Los_Angeles'))
        self.assertEqual(popup.prayer_state(self.data, now), (
            'Fajr', date(2026, 10, 12), 'Next: Fajr in 5h 42m'))

    def test_exact_start_switches_current(self):
        self.assertEqual(self.state(16, 12)[0], 'Asr')
        self.assertEqual(self.state(16, 11)[0], 'Dhuhr')

    def test_sunrise_highlight_lasts_until_dhuhr(self):
        self.assertEqual(self.state(7, 7)[0], 'Fajr')
        self.assertEqual(self.state(7, 8)[0], 'Sunrise')
        self.assertEqual(self.state(12, 57)[0], 'Sunrise')
        self.assertEqual(self.state(12, 58)[0], 'Dhuhr')

    def test_countdown_skips_sunrise(self):
        self.assertEqual(self.state(7, 7)[2], 'Next: Dhuhr in 5h 51m')
        self.assertEqual(self.state(7, 8)[2], 'Next: Dhuhr in 5h 50m')

    def test_after_isha_keeps_todays_schedule(self):
        self.assertEqual(self.state(23, 59), (
            'Isha', date(2026, 10, 11), 'Next: Fajr tomorrow'))

    def test_stale_schedule_rejected(self):
        self.data['date'] = '2026-10-10'
        with self.assertRaisesRegex(ValueError, 'out of date'):
            self.state(0, 0)

    def test_incomplete_schedule_rejected(self):
        self.data['prayers'].pop(0)
        with self.assertRaisesRegex(ValueError, 'all five'):
            self.state(16, 0)


if __name__ == '__main__':
    unittest.main()
