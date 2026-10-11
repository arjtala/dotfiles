import importlib.util
from datetime import datetime, date
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location(
    'popup', Path(__file__).resolve().parents[1] / '.config/waybar/scripts/popup.py')
popup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(popup)


class PrayerStateTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            'date': '2026-10-11',
            'prayers': [dict(name=name, time=time) for name, time in zip(
                popup.PRAYER_NAMES, ['05:42', '12:58', '16:12', '18:39', '19:54'])],
        }

    def state(self, hour, minute):
        return popup.prayer_state(self.data, datetime(
            2026, 10, 11, hour, minute, tzinfo=ZoneInfo('America/Los_Angeles')))

    def test_before_fajr_marks_yesterdays_isha(self):
        current, day, following = self.state(5, 41)
        self.assertEqual((current, day), ('Isha', date(2026, 10, 10)))
        self.assertEqual(following, 'Next: Fajr in 1 min')

    def test_exact_start_switches_current(self):
        self.assertEqual(self.state(16, 12)[0], 'Asr')
        self.assertEqual(self.state(16, 11)[0], 'Dhuhr')

    def test_sunrise_does_not_replace_fajr(self):
        self.assertEqual(self.state(7, 8)[0], 'Fajr')

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
