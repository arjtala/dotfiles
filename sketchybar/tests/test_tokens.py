from datetime import datetime, timezone
import http.server
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

PLUGINS = Path(__file__).resolve().parents[1] / '.config/sketchybar/plugins'
sys.path.insert(0, str(PLUGINS))
spec = importlib.util.spec_from_file_location('tokens', PLUGINS / 'tokens.py')
tokens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tokens)

NOW = datetime(2026, 10, 19, 21, 0, tzinfo=timezone.utc)

# What GET /api/quota on Apple Claude Code's proxy returns, shortened (the
# real reply also carries a long price list), with round numbers.
QUOTA = {
    'status': 'success', 'timestamp': '2026-10-19T21:00:00.000Z',
    'quota': {
        'usage': {'calls': 2400, 'spend': 150.0, 'inputTokens': 296000000, 'outputTokens': 4000000},
        'limits': {'budgetSpend': 300, 'rateTokens': 1000000000},
        'percentages': {'budgetUsed': 50, 'tokensUsed': 30},
        'rateLimit': {'limit': 40, 'remaining': 24, 'windowSeconds': 240,
                      'source': 'default_account_limit'},
        'budgetResetTime': '2026-10-20T12:00:00Z',
        'usageByModel': {
            'aws:anthropic.claude-opus-5-5': {'calls': 1283, 'spend': 120.0},
            'aws:anthropic.claude-sonnet-5': {'calls': 40, 'spend': 20.0},
            'aws:anthropic.claude-haiku-4-5-20251001-v1:0': {'calls': 900, 'spend': 10.0},
        },
    },
}


def quota(**spend_and_more):
    reply = json.loads(json.dumps(QUOTA))
    reply['quota']['usage'].update(spend_and_more)
    return reply


class InstancesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def pid_file(self, name, text, mtime=None):
        path = self.dir / name
        path.write_text(text)
        if mtime:
            os.utime(path, (mtime, mtime))
        return path

    def test_only_live_proxies_count(self):
        self.pid_file('acc-port-111.pid', '4242')
        self.pid_file('acc-port-222.pid', '4343')
        self.assertEqual(tokens.instances(self.dir, alive=lambda pid: pid == 4343), [222])

    def test_newest_first(self):
        self.pid_file('acc-port-111.pid', '1001', mtime=1000)
        self.pid_file('acc-port-222.pid', '1002', mtime=2000)
        self.assertEqual(tokens.instances(self.dir, alive=lambda pid: True), [222, 111])

    def test_files_that_are_not_proxies_are_ignored(self):
        self.pid_file('acc-port-abc.pid', '4242')
        self.pid_file('acc-port-333.pid', 'not a pid')
        self.pid_file('acc-port-99999.pid', '4242')  # not a port
        self.pid_file('acc-port-444.log', '4242')
        self.pid_file('other.pid', '4242')
        self.assertEqual(tokens.instances(self.dir, alive=lambda pid: True), [])

    def test_no_directory_means_no_proxies(self):
        self.assertEqual(tokens.instances(self.dir / 'missing', alive=lambda pid: True), [])


class PidAliveTests(unittest.TestCase):
    def test_this_process_is_alive(self):
        self.assertTrue(tokens.pid_alive(os.getpid()))

    def test_a_finished_process_is_not(self):
        child = subprocess.Popen([sys.executable, '-c', 'pass'])
        child.wait()
        self.assertFalse(tokens.pid_alive(child.pid))

    def test_a_process_of_another_user_still_exists(self):
        with mock.patch('os.kill', side_effect=PermissionError):
            self.assertTrue(tokens.pid_alive(4242))

    def test_pids_that_would_signal_a_group_are_refused(self):
        with mock.patch('os.kill') as kill:
            self.assertFalse(tokens.pid_alive(0))
            self.assertFalse(tokens.pid_alive(-1))
            self.assertFalse(tokens.pid_alive(1))
        kill.assert_not_called()


class ParseTests(unittest.TestCase):
    def test_the_meter(self):
        meter = tokens.parse(QUOTA)
        self.assertEqual((meter['spend'], meter['budget'], meter['percent']), (150.0, 300.0, 50))
        self.assertEqual((meter['tokens'], meter['token_limit'], meter['token_percent']),
                         (300000000, 1000000000.0, 30))
        self.assertEqual(meter['calls'], 2400)
        self.assertEqual((meter['rate_remaining'], meter['rate_limit'], meter['rate_window']),
                         (24, 40, 240))
        self.assertEqual(meter['resets'], datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc))

    def test_the_costliest_model_and_its_share(self):
        self.assertEqual(tokens.parse(QUOTA)['model'],
                         {'name': 'Opus 5.5', 'spend': 120.0, 'share': 80})

    def test_percent_is_worked_out_not_taken_from_the_reply(self):
        self.assertEqual(tokens.parse(quota(spend=227.65))['percent'], 76)
        self.assertEqual(tokens.parse(quota(spend=224.01))['percent'], 75)
        self.assertEqual(tokens.parse(quota(spend=1.4))['percent'], 0)

    def test_a_reply_that_is_not_a_success_is_nothing(self):
        self.assertIsNone(tokens.parse(dict(QUOTA, status='error')))
        self.assertIsNone(tokens.parse({}))
        self.assertIsNone(tokens.parse(None))
        self.assertIsNone(tokens.parse([QUOTA]))

    def test_without_a_spend_or_a_budget_there_is_nothing_to_show(self):
        for key, section in (('spend', 'usage'), ('budgetSpend', 'limits')):
            broken = json.loads(json.dumps(QUOTA))
            del broken['quota'][section][key]
            self.assertIsNone(tokens.parse(broken), key)
        broken = json.loads(json.dumps(QUOTA))
        broken['quota']['limits']['budgetSpend'] = 0
        self.assertIsNone(tokens.parse(broken))

    def test_wrong_types_are_nothing_not_a_crash(self):
        broken = json.loads(json.dumps(QUOTA))
        broken['quota']['usage']['spend'] = 'a lot'
        self.assertIsNone(tokens.parse(broken))
        broken['quota'] = 'gone'
        self.assertIsNone(tokens.parse(broken))

    def test_optional_parts_may_be_missing(self):
        sparse = {'status': 'success',
                  'quota': {'usage': {'spend': 12.5}, 'limits': {'budgetSpend': 100}}}
        meter = tokens.parse(sparse)
        self.assertEqual(meter['percent'], 13)  # 12.5 rounds up
        for key in ('tokens', 'calls', 'rate_limit', 'resets', 'model', 'token_percent'):
            self.assertIsNone(meter[key], key)

    def test_a_reset_time_without_a_zone_is_taken_as_utc(self):
        reply = json.loads(json.dumps(QUOTA))
        reply['quota']['budgetResetTime'] = '2026-10-20T12:00:00'
        self.assertEqual(tokens.parse(reply)['resets'].utcoffset().total_seconds(), 0)

    def test_a_bad_reset_time_is_dropped(self):
        reply = json.loads(json.dumps(QUOTA))
        reply['quota']['budgetResetTime'] = 'tomorrow'
        self.assertIsNone(tokens.parse(reply)['resets'])


class FormatTests(unittest.TestCase):
    def test_model_names(self):
        for model_id, name in (('aws:anthropic.claude-opus-5-5', 'Opus 5.5'),
                               ('aws:anthropic.claude-opus-4-8', 'Opus 4.8'),
                               ('aws:anthropic.claude-sonnet-5', 'Sonnet 5'),
                               ('aws:anthropic.claude-sonnet-4-20250514', 'Sonnet 4'),
                               ('aws:anthropic.claude-haiku-4-5-20251001-v1:0', 'Haiku 4.5'),
                               ('aws:anthropic.claude-3-5-sonnet-20241022', 'claude-3-5-sonnet-20241022'),
                               ('plain', 'plain')):
            self.assertEqual(tokens.model_name(model_id), name, model_id)

    def test_compact_counts(self):
        for count, text in ((0, '0'), (999, '999'), (1234, '1.2K'), (12345, '12K'),
                            (999960, '1.0M'), (4504313, '4.5M'), (297341768, '297M'),
                            (1000000000, '1.0B'), (12500000000, '12B')):
            self.assertEqual(tokens.compact(count), text, count)

    def test_time_until(self):
        for seconds, text in ((54000, '15h 00m'), (54180, '15h 03m'), (2520, '42m'),
                              (30, '<1m'), (0, '<1m'), (-500, '<1m')):
            moment = datetime.fromtimestamp(NOW.timestamp() + seconds, timezone.utc)
            self.assertEqual(tokens.until(moment, NOW), text, seconds)

    def test_colour_runs_from_green_to_red(self):
        for share, name in ((0, 'BR_GREEN'), (49, 'BR_GREEN'), (50, 'BR_YELLOW'), (74, 'BR_YELLOW'),
                            (75, 'BR_ORANGE'), (89, 'BR_ORANGE'), (90, 'BR_RED'), (140, 'BR_RED')):
            self.assertEqual(tokens.level(share), name, share)

    def test_every_colour_is_in_the_palette(self):
        palette = tokens.p.colors()
        for _, name in tokens.LEVELS:
            self.assertIn(name, palette)
        self.assertIn('BG1', palette)

    def test_bar_label(self):
        self.assertEqual(tokens.bar_label(tokens.parse(quota(spend=227.65))), '$228 · 76%')

    def test_clip(self):
        self.assertEqual(tokens.clip('short', 10), 'short')
        self.assertEqual(tokens.clip('a very long line', 8), 'a very…')


class PopupRowsTests(unittest.TestCase):
    def rows(self, reply=QUOTA):
        return {name: (text, color) for name, text, color in tokens.popup_rows(tokens.parse(reply), NOW)}

    def test_every_row_has_an_item_name_the_popup_creates(self):
        self.assertEqual([name for name, _, _ in tokens.popup_rows(tokens.parse(QUOTA), NOW)], tokens.ROWS)

    def test_the_rows(self):
        rows = self.rows()
        self.assertEqual(rows['today'][0], 'Today   $150.00 of $300 · 50%')
        self.assertEqual(rows['tokens'][0], 'Tokens  300M of 1.0B · 30%')
        self.assertEqual(rows['calls'][0], 'Calls   2,400')
        self.assertEqual(rows['limit'][0], 'Limit   24 of 40 per 4 min')
        self.assertTrue(rows['resets'][0].startswith('Resets  in 15h 00m · '))
        self.assertEqual(rows['model'][0], 'Model   Opus 5.5 $120 · 80%')

    def test_today_takes_the_level_colour(self):
        self.assertEqual(self.rows()['today'][1], 'BR_YELLOW')
        self.assertEqual(self.rows(quota(spend=290))['today'][1], 'BR_RED')

    def test_a_budget_with_cents_keeps_them(self):
        reply = json.loads(json.dumps(QUOTA))
        reply['quota']['limits']['budgetSpend'] = 250.5
        self.assertIn('of $250.50 ·', self.rows(reply)['today'][0])

    def test_nothing_is_wider_than_the_popup(self):
        big = quota(spend=1234567.89, calls=123456789)
        big['quota']['limits']['budgetSpend'] = 99999999
        for reply in (QUOTA, big):
            for name, text, _ in tokens.popup_rows(tokens.parse(reply), NOW):
                self.assertLessEqual(len(text or ''), tokens.WIDTH, name)

    def test_what_the_proxy_did_not_report_is_hidden(self):
        sparse = {'status': 'success',
                  'quota': {'usage': {'spend': 12.5}, 'limits': {'budgetSpend': 100}}}
        rows = self.rows(sparse)
        self.assertIsNotNone(rows['today'][0])
        for name in ('tokens', 'calls', 'limit', 'resets', 'model'):
            self.assertIsNone(rows[name][0], name)


class RenderTests(unittest.TestCase):
    def draw(self, meter, popup_open=False):
        calls = []
        with mock.patch.object(tokens.p, 'bar', lambda *args: calls.append(list(args))):
            tokens.render(meter, popup_open, NOW)
        return calls

    def test_with_no_proxy_the_item_and_its_popup_are_gone(self):
        self.assertEqual(self.draw(None), [['--set', 'tokens', 'drawing=off', 'popup.drawing=off']])

    def test_with_a_proxy_the_item_is_drawn_in_its_level_colour(self):
        palette = tokens.p.colors()
        (args,) = self.draw(tokens.parse(QUOTA))
        self.assertEqual(args[:4], ['--set', 'tokens', 'drawing=on', f'icon={tokens.ICON}'])
        self.assertIn('label=$150 · 50%', args)
        self.assertIn(f'label.color={palette["BR_YELLOW"]}', args)
        self.assertIn(f'icon.color={palette["BR_YELLOW"]}', args)
        self.assertFalse([a for a in args if a.startswith('tokens.i.')])  # popup closed: not touched

    def test_an_open_popup_is_filled_in(self):
        (args,) = self.draw(tokens.parse(QUOTA), popup_open=True)
        items = [args[i + 1] for i, a in enumerate(args) if a == '--set' and i > 0]
        self.assertEqual(items, [f'tokens.i.{name}' for name in tokens.ROWS])
        self.assertIn('label=Calls   2,400', args)

    def test_an_open_popup_hides_rows_with_nothing_to_say(self):
        sparse = {'status': 'success',
                  'quota': {'usage': {'spend': 12.5}, 'limits': {'budgetSpend': 100}}}
        (args,) = self.draw(tokens.parse(sparse), popup_open=True)
        hidden = [args[i + 1] for i, a in enumerate(args[:-2]) if a == '--set' and args[i + 2] == 'drawing=off']
        self.assertEqual(hidden, [f'tokens.i.{name}' for name in tokens.ROWS if name != 'today'])


class ServerTests(unittest.TestCase):
    """The real fetch, against a server of our own on loopback."""

    def serve(self, status=200, body=None, path='/api/quota'):
        payload = json.dumps(QUOTA).encode() if body is None else body

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != path:
                    self.send_error(404)
                    return
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        try:
            server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        except OSError as error:
            self.skipTest(f'cannot listen on loopback here: {error}')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(5)))
        return server.server_address[1]

    def test_fetch_reads_the_quota(self):
        self.assertEqual(tokens.fetch(self.serve())['quota']['usage']['spend'], 150.0)

    def test_fetch_ignores_an_http_proxy(self):
        port = self.serve()
        dead = 'http://127.0.0.1:9'
        with mock.patch.dict(os.environ, {'http_proxy': dead, 'HTTP_PROXY': dead,
                                          'all_proxy': dead, 'ALL_PROXY': dead}):
            self.assertIsNotNone(tokens.fetch(port))

    def test_fetch_gives_none_for_errors_and_rubbish(self):
        self.assertIsNone(tokens.fetch(self.serve(status=500)))
        self.assertIsNone(tokens.fetch(self.serve(body=b'<html>not json</html>')))
        self.assertIsNone(tokens.fetch(self.serve(path='/elsewhere')))

    def test_fetch_gives_none_when_nothing_listens(self):
        with socket.socket() as probe:  # a free port, released at the end of the block
            probe.bind(('127.0.0.1', 0))
            free = probe.getsockname()[1]
        self.assertIsNone(tokens.fetch(free, timeout=0.5))

    def test_read_works_end_to_end_from_a_pid_file(self):
        port = self.serve()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / f'acc-port-{port}.pid').write_text(str(os.getpid()))  # a live process
            original = tokens.instances
            with mock.patch.object(tokens, 'instances', lambda: original(Path(tmp))):
                self.assertEqual(tokens.read()['spend'], 150.0)


class ReadTests(unittest.TestCase):
    def test_no_proxy_means_nothing(self):
        with mock.patch.object(tokens, 'instances', lambda: []):
            self.assertIsNone(tokens.read())

    def test_a_proxy_that_does_not_answer_means_nothing(self):
        with mock.patch.object(tokens, 'instances', lambda: [1234]), \
                mock.patch.object(tokens, 'fetch', lambda port: None):
            self.assertIsNone(tokens.read())

    def test_the_largest_spend_wins_so_the_meter_never_under_reports(self):
        replies = {1: quota(spend=224.01), 2: quota(spend=227.65), 3: None}
        with mock.patch.object(tokens, 'instances', lambda: [1, 2, 3]), \
                mock.patch.object(tokens, 'fetch', lambda port: replies[port]):
            self.assertEqual(tokens.read()['spend'], 227.65)


if __name__ == '__main__':
    unittest.main()
