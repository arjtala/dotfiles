import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

PLUGINS = Path(__file__).resolve().parents[1] / '.config/sketchybar/plugins'
sys.path.insert(0, str(PLUGINS))
import agent_registry as registry  # noqa: E402
spec = importlib.util.spec_from_file_location('agents', PLUGINS / 'agents.py')
agents = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agents)

START = 'Fri Oct 23 09:52:32 2026'  # local time, as `ps -o lstart' prints it
START_EPOCH = time.mktime(time.strptime(START, registry.LSTART))
PS = f'''  1614  1600 {START} claude
  3279  3000 {START} node /opt/homebrew/bin/pi
  4000  3999 {START} /opt/homebrew/bin/codex
  4001  4000 {START} /opt/homebrew/bin/codex
  4100  4099 {START} node /usr/lib/node_modules/@openai/codex/bin/codex.js
  4101  4100 {START} /usr/lib/node_modules/@openai/codex/vendor/codex-x86_64-unknown-linux-musl
  4200  4101 {START} codex-linux-sandbox
garbage line
'''


def utc(epoch):
    return time.strftime(registry.LSTART, time.gmtime(epoch))


def agent(state, harness='Claude', name='x', detail=None):
    return {'harness': harness, 'pid': 1, 'cwd': '/w/' + name, 'name': name,
            'state': state, 'detail': detail, 'since': None}


class ProcessTableTests(unittest.TestCase):
    def test_parses_ps_and_skips_garbage(self):
        table = registry.parse_processes(PS)
        self.assertEqual(table[1614], {'ppid': 1600, 'start': START_EPOCH, 'command': 'claude'})
        self.assertEqual(table[3279]['command'], 'node')
        self.assertEqual(len(table), 7)

    def test_codex_matches_the_binary_once_per_session(self):
        # The npm wrapper is node, a nested codex is its parent's, the sandbox helper is not codex.
        self.assertEqual(registry.codex_processes(registry.parse_processes(PS)), [4000, 4101])


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.table = registry.parse_processes(PS)

    def claude(self, **changes):
        data = {'pid': 1614, 'sessionId': 's', 'cwd': '/Users/me/dotfiles', 'name': 'dotfiles-2f',
                'status': 'busy', 'entrypoint': 'cli', 'procStart': utc(START_EPOCH),
                'statusUpdatedAt': 1792774384791}
        data.update(changes)
        return registry.claude_agent(data, self.table)

    def pi(self, **changes):
        data = {'version': 1, 'pid': 3279, 'procStart': int(START_EPOCH * 1000) + 400,
                'cwd': '/Users/me/dotfiles', 'title': 'what model are you ?',
                'status': 'waiting', 'waitingFor': 'confirm: Run rm?', 'updatedAt': 1}
        data.update(changes)
        return registry.pi_agent(data, self.table)

    def test_claude_statuses(self):
        self.assertEqual(self.claude()['state'], 'working')
        self.assertEqual(self.claude(status='waiting')['state'], 'waiting')
        self.assertEqual(self.claude(status='idle')['state'], 'idle')
        self.assertIsNone(self.claude(status='thinking')['state'])
        # SDK sessions' status never moves, so it means nothing.
        self.assertIsNone(self.claude(entrypoint='sdk-ts')['state'])

    def test_claude_needs_its_process(self):
        self.assertIsNone(self.claude(pid=999))
        self.assertIsNone(self.claude(procStart=utc(START_EPOCH - 3600)))  # pid reused
        self.assertIsNotNone(self.claude(procStart=None))

    def test_pi(self):
        found = self.pi()
        self.assertEqual((found['state'], found['name'], found['detail']),
                         ('waiting', 'what model are you ?', 'confirm: Run rm?'))
        self.assertEqual(self.pi(status='busy', name='named')['name'], 'named')
        self.assertIsNone(self.pi(procStart=int(START_EPOCH - 60) * 1000))
        self.assertIsNone(self.pi(version=2))


class CodexTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def event(self, kind, turn='turn', started=START_EPOCH + 10):
        return {'type': 'event_msg', 'timestamp': '2026-10-23T17:00:00Z',
                'payload': {'type': kind, 'turn_id': turn, 'started_at': started}}

    def rollout(self, events, name='root', parent=None):
        source = {'subagent': {'thread_spawn': {'parent_thread_id': parent}}} if parent else 'cli'
        meta = {'type': 'session_meta',
                'payload': {'id': name, 'cwd': '/w/' + name, 'source': source,
                            'timestamp': registry.datetime.fromtimestamp(
                                START_EPOCH, registry.timezone.utc).isoformat()}}
        path = self.directory / f'rollout-{name}.jsonl'
        path.write_text(''.join(json.dumps(r) + '\n' for r in [meta] + events))
        return path

    def read(self, path, start=START_EPOCH):
        return registry.read_rollout(path, start)

    def test_quiet_turn_stays_working_without_recent_writes(self):
        path = self.rollout([self.event('task_started')])
        os.utime(path, (START_EPOCH, START_EPOCH))
        self.assertEqual(self.read(path)['state'], 'working')

    def test_completion_and_interruption_become_idle_immediately(self):
        for kind in ('task_complete', 'turn_aborted'):
            with self.subTest(kind=kind):
                path = self.rollout([self.event('task_started'), self.event(kind)])
                self.assertEqual(self.read(path)['state'], 'idle')

    def test_followup_restarts_completed_turn(self):
        path = self.rollout([self.event('task_started'), self.event('task_complete'),
                             self.event('task_started', 'followup')])
        self.assertEqual(self.read(path)['state'], 'working')

    def test_previous_turn_completion_does_not_finish_current_turn(self):
        path = self.rollout([self.event('task_started', 'new'),
                             self.event('task_complete', 'old', START_EPOCH - 60)])
        self.assertEqual(self.read(path)['state'], 'working')

    def test_old_unfinished_turn_is_not_active_after_process_restart(self):
        path = self.rollout([self.event('task_started')])
        self.assertEqual(self.read(path, START_EPOCH + 100)['state'], 'idle')
        with path.open('a') as f:
            f.write(json.dumps(self.event('task_started', 'resumed', START_EPOCH + 110)) + '\n')
        self.assertEqual(self.read(path, START_EPOCH + 100)['state'], 'working')

    def test_subagent_ignores_copied_parent_metadata_and_history(self):
        copied = {'type': 'session_meta', 'payload': {'id': 'parent', 'source': 'cli'}}
        path = self.rollout([copied, self.event('task_started', started=START_EPOCH - 60)],
                             name='child', parent='parent')
        result = self.read(path)
        self.assertEqual((result['id'], result['parent'], result['state']),
                         ('child', 'parent', 'idle'))
        with path.open('a') as f:
            f.write(json.dumps(self.event('task_started', 'own')) + '\n')
        self.assertEqual(self.read(path)['state'], 'working')

    def test_child_and_grandchild_keep_process_working_in_other_directories(self):
        root = self.read(self.rollout([self.event('task_started'), self.event('task_complete')]))
        child = self.read(self.rollout([self.event('task_started'), self.event('task_complete')],
                                      name='child', parent='root'))
        grandchild_path = self.rollout([self.event('task_started')], name='grandchild', parent='child')
        found = registry.codex_agent(4000, '/w/root', [root, child, self.read(grandchild_path)])
        self.assertEqual(found['state'], 'working')
        self.assertEqual(found['detail'], '1 active subagent')
        with grandchild_path.open('a') as f:
            f.write(json.dumps(self.event('task_complete')) + '\n')
        self.assertEqual(registry.codex_agent(4000, '/w/root',
                                             [root, child, self.read(grandchild_path)])['state'], 'idle')

    def test_partial_or_malformed_append_does_not_erase_active_turn(self):
        path = self.rollout([self.event('task_started')])
        with path.open('ab') as f:
            f.write(b'not json\n[]\n{"type":"event_msg","payload":null}\n')
            # Even valid JSON is not committed until the line is complete.
            f.write(json.dumps(self.event('task_complete')).encode())
        self.assertEqual(self.read(path)['state'], 'working')
        with path.open('a') as f:
            f.write('\n')
        self.assertEqual(self.read(path)['state'], 'idle')

    def test_reverse_reader_handles_large_records_and_partial_tail(self):
        large = ('\u00e9' * 100000).encode()
        data = b'first\n' + large + b'\nlast\n' + b'x' * 100000
        self.assertEqual(list(registry.reverse_lines(io.BytesIO(data))), [b'last', large, b'first'])
        self.assertEqual(list(registry.reverse_lines(io.BytesIO(b'unfinished'))), [])

    def test_unavailable_or_unsupported_logs_are_unknown(self):
        self.assertIsNone(self.read(self.directory / 'missing'))
        for invalid in ('[]\n', 'null\n', 'bad json\n'):
            path = self.directory / 'invalid'
            path.write_text(invalid)
            self.assertIsNone(self.read(path))
        unknown = self.read(self.rollout([self.event('new_unknown_event')]))
        self.assertIsNone(unknown['state'])
        for rollouts in (None, [None], [unknown]):
            self.assertIsNone(registry.codex_agent(4000, '/w/root', rollouts)['state'])

    def test_sessions_in_same_directory_are_associated_by_open_file(self):
        working = self.rollout([self.event('task_started')], name='working')
        idle = self.rollout([self.event('task_started'), self.event('task_complete')], name='idle')
        paths = {4000: [working], 4101: [idle]}
        with mock.patch.object(registry, 'process_rollouts', side_effect=paths.get), \
                mock.patch.object(registry, 'process_cwd', return_value='/shared'):
            found = registry.codex(registry.parse_processes(PS))
        self.assertEqual([(a['pid'], a['state']) for a in found], [(4000, 'working'), (4101, 'idle')])

    def test_exited_process_does_not_leave_a_working_entry(self):
        self.rollout([self.event('task_started')])
        with mock.patch.object(registry, 'process_rollouts') as discover:
            self.assertEqual(registry.codex({}), [])
            discover.assert_not_called()

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux descriptor integration')
    def test_linux_discovers_live_open_rollouts(self):
        path = self.rollout([self.event('task_started')])
        with path.open('rb'):
            self.assertIn(path, registry.process_rollouts(os.getpid()))
        self.assertNotIn(path, registry.process_rollouts(os.getpid()))

    def test_macos_discovers_rollouts_via_lsof(self):
        path = self.rollout([self.event('task_started')])
        output = f'p4000\nn/usr/bin/codex\nn{path}\nn{path}\nn/dev/ttys001\n'
        with mock.patch.object(registry.sys, 'platform', 'darwin'), \
                mock.patch.object(registry.subprocess, 'run',
                                  return_value=subprocess.CompletedProcess([], 0, output)) as run:
            self.assertEqual(registry.process_rollouts(4000), [path])
            self.assertEqual(run.call_args[0][0], ['lsof', '-a', '-p', '4000', '-Fn'])

    def test_discovery_failure_is_unknown_on_both_platforms(self):
        with mock.patch.object(registry.sys, 'platform', 'linux'), \
                mock.patch.object(Path, 'iterdir', side_effect=PermissionError):
            self.assertIsNone(registry.process_rollouts(4000))
        with mock.patch.object(registry.sys, 'platform', 'darwin'):
            with mock.patch.object(registry.subprocess, 'run', side_effect=FileNotFoundError):
                self.assertIsNone(registry.process_rollouts(4000))
            with mock.patch.object(registry.subprocess, 'run',
                                   return_value=subprocess.CompletedProcess([], 1, '')):
                self.assertIsNone(registry.process_rollouts(4000))


class SummaryTests(unittest.TestCase):
    def test_overall_puts_waiting_before_working(self):
        self.assertEqual(registry.overall([]), 'sleeping')
        self.assertEqual(registry.overall([agent('idle'), agent(None)]), 'sleeping')
        self.assertEqual(registry.overall([agent('idle'), agent('working')]), 'working')
        self.assertEqual(registry.overall([agent('working'), agent('waiting')]), 'waiting')

    def test_order_and_counts(self):
        found = registry.ordered([agent('idle', name='b'), agent(None, name='a'),
                                  agent('working', 'Pi', 'c'), agent('waiting', 'Pi', 'd')])
        self.assertEqual([a['name'] for a in found], ['d', 'c', 'b', 'a'])
        self.assertEqual(registry.counts(found), '1 waiting · 1 working · 1 idle · 1 unknown')
        self.assertEqual(registry.counts([]), 'none running')

    def test_label_falls_back_to_directory_then_pid(self):
        self.assertEqual(registry.label({'name': None, 'cwd': '/w/proj/', 'pid': 7}), 'proj')
        self.assertEqual(registry.label({'name': None, 'cwd': None, 'pid': 7}), 'pid 7')


class PopupTests(unittest.TestCase):
    def test_rows(self):
        found = [agent('waiting', 'Pi', 'notes', 'confirm: Allow?')] + [agent('idle')] * 13
        result = agents.rows(found)
        self.assertEqual(result[0], ('title', 'Agents · 1 waiting · 13 idle', 'BR_ORANGE'))
        self.assertEqual(result[1][1:], ('Pi     notes                  waiting · confirm: Allow?',
                                         'BR_ORANGE'))
        self.assertEqual(len(result), agents.MAX_AGENTS + 2)
        self.assertEqual(result[-1], ('more', 'and 2 more', 'FG2'))
        self.assertFalse(agents.rows([])[-1][1])
        self.assertTrue(all(len(text) <= agents.WIDTH for _, text, _ in result if text))

    def test_popup_registers_agents_so_the_other_popups_close_it(self):
        source = (PLUGINS / 'popup.py').read_text()
        self.assertIn('TOKENS, TAILSCALE, AGENTS):', source)

    def test_render_sets_the_overall_icon(self):
        with mock.patch.object(agents.p, 'bar') as bar:
            agents.render([agent('working')], False)
        args = bar.call_args[0]
        self.assertIn('icon=' + agents.ICONS['working'][0], args)
        self.assertFalse(any(arg.startswith('--add') for arg in args))


if __name__ == '__main__':
    unittest.main()
