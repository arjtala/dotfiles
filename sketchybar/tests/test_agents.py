import importlib.util
from pathlib import Path
import sys
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

    def test_codex_works_while_its_rollout_is_written(self):
        process = self.table[4000]
        now = START_EPOCH + 100
        rollouts = [(now - 2, '/w/a'), (now - 1, '/w/b'), (START_EPOCH - 60, '/w/a')]
        self.assertEqual(registry.codex_agent(4000, process, '/w/a', rollouts, now)['state'], 'working')
        self.assertEqual(registry.codex_agent(4000, process, '/w/a', rollouts, now + 30)['state'], 'idle')
        # A rollout from before the process started is an earlier session's.
        self.assertEqual(registry.codex_agent(4000, process, '/w/c', [(START_EPOCH - 60, '/w/c')],
                                              START_EPOCH - 59)['state'], 'idle')


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
