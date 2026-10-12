import importlib.util
from datetime import datetime, date
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

spec = importlib.util.spec_from_file_location(
    'popup', Path(__file__).resolve().parents[1] / '.config/sketchybar/plugins/popup.py')
popup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(popup)


class MonthTests(unittest.TestCase):
    def test_labels_are_wide_enough_for_a_full_row(self):
        # 7.8pt per column at the 13pt label font; a narrower label clips.
        self.assertGreaterEqual(popup.LABEL_WIDTH, popup.WIDTH * 7.8)

    def test_today_is_left_blank_without_moving_the_columns(self):
        plain = popup.week_text([5, 6, 7, 8, 9, 10, 11])
        marked = popup.week_text([5, 6, 7, 8, 9, 10, 11], today=8)
        self.assertEqual(plain, '    5    6    7    8    9   10   11   ')
        self.assertEqual(marked, '    5    6    7         9   10   11   ')
        self.assertEqual(len(plain), popup.WIDTH)
        self.assertEqual(len(marked), popup.WIDTH)

    def test_today_column_is_where_its_digits_start(self):
        days = [12, 13, 14, 15, 16, 17, 18]
        text = popup.week_text(days)
        for day in days:
            self.assertEqual(popup.today_column(days, day), text.index(str(day)))
        self.assertIsNone(popup.today_column(days, 19))
        self.assertIsNone(popup.today_column([0, 0, 0, 1, 2, 3, 4], 0))

    def test_today_padding_puts_the_digits_in_their_column(self):
        for column in (3, 8, 33):
            icon_pad, label_pad = popup.today_padding(column)
            # The label starts where an unmarked row's does.  A fixed-width
            # icon advances the row by its width alone (seen on screen: also
            # counting its padding put the label 27pt too far left)...
            self.assertEqual(popup.TODAY_WIDTH + label_pad, popup.LABEL_PAD)
            # ...and the icon within half a point of its column.
            self.assertLessEqual(abs(icon_pad - popup.LABEL_PAD - column * 7.8), 0.5)

    def test_weekday_names_sit_over_their_days(self):
        names = popup.weekday_text()
        week = popup.week_text([12, 13, 14, 15, 16, 17, 18])
        for name, day in zip(names.split(), week.split()):
            self.assertEqual(names.index(name), week.index(day))

    def test_days_outside_the_month_are_blank(self):
        self.assertEqual(popup.week_text([0, 0, 0, 1, 2, 3, 4]),
                         '                   1    2    3    4   ')

    def test_month_starts_on_monday_and_locates_today(self):
        rows = popup.month_rows(date(2026, 10, 1), date(2026, 10, 12))
        self.assertEqual(rows[0], ('                   1    2    3    4   ', None))
        self.assertEqual(rows[2], ('        13   14   15   16   17   18   ', 3))
        self.assertEqual(sum(column is not None for _, column in rows), 1)

    def test_another_month_marks_nothing(self):
        rows = popup.month_rows(date(2026, 11, 1), date(2026, 10, 12))
        self.assertTrue(all(column is None for _, column in rows))

    def test_shift_month_crosses_years(self):
        self.assertEqual(popup.shift_month(date(2026, 12, 1), 1), date(2027, 1, 1))
        self.assertEqual(popup.shift_month(date(2026, 1, 1), -1), date(2025, 12, 1))


class PrayerStateTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            'date': '2026-10-11',
            'sunrise': '06:58',
            'prayers': [dict(name=name, time=time) for name, time in zip(
                popup.PRAYER_NAMES, ['05:42', '12:58', '16:12', '18:39', '19:54'])],
        }

    def at(self, hour, minute):
        return datetime(2026, 10, 11, hour, minute, tzinfo=ZoneInfo('America/Los_Angeles'))

    def test_before_fajr_marks_yesterdays_isha(self):
        current, day, following = popup.prayer_state(self.data, self.at(5, 41))
        self.assertEqual((current, day), ('Isha', date(2026, 10, 10)))
        self.assertEqual(following, 'Next: Fajr in 1 min')

    def test_exact_start_switches_current(self):
        self.assertEqual(popup.prayer_state(self.data, self.at(16, 12))[0], 'Asr')
        self.assertEqual(popup.prayer_state(self.data, self.at(16, 11))[0], 'Dhuhr')

    def test_after_isha_does_not_guess_tomorrow(self):
        self.assertEqual(popup.prayer_state(self.data, self.at(23, 59))[2],
                         'Next: Fajr tomorrow')

    def test_stale_schedule_rejected(self):
        self.data['date'] = '2026-10-10'
        with self.assertRaisesRegex(ValueError, 'out of date'):
            popup.prayer_state(self.data, self.at(0, 0))

    def test_incomplete_schedule_rejected(self):
        self.data['prayers'].pop(0)
        with self.assertRaisesRegex(ValueError, 'all five'):
            popup.prayer_state(self.data, self.at(16, 0))

    def test_rows_mark_the_current_prayer_and_dim_sunrise(self):
        rows = popup.prayer_rows(self.data, self.at(13, 0))
        self.assertEqual([text.split()[-2] if '●' in text else text.split()[0]
                          for text, _ in rows],
                         ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Maghrib', 'Isha'])
        self.assertEqual(rows[2], ('● Dhuhr'.ljust(popup.WIDTH - 5) + '12:58', 'current'))
        self.assertEqual(rows[1], ('  Sunrise'.ljust(popup.WIDTH - 5) + '06:58', 'muted'))
        self.assertEqual({len(text) for text, _ in rows}, {popup.WIDTH})

    def test_rows_before_fajr_mark_nothing_today(self):
        rows = popup.prayer_rows(self.data, self.at(5, 0))
        self.assertNotIn('current', [style for _, style in rows])


if __name__ == '__main__':
    unittest.main()
