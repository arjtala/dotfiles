from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.config/waybar/scripts'))
import agents  # noqa: E402


def agent(state, name='proj', detail=None):
    return {'harness': 'Claude', 'pid': 1, 'cwd': '/w/' + name, 'name': name,
            'state': state, 'detail': detail, 'since': None}


class AgentsTests(unittest.TestCase):
    def test_bar_output(self):
        output = agents.bar_output([agent('waiting', 'a<b>'), agent('working')])
        self.assertEqual((output['text'], output['class']), (agents.ICONS['waiting'], 'waiting'))
        self.assertIn('a&lt;b&gt;', output['tooltip'])
        self.assertEqual(agents.bar_output([])['class'], 'sleeping')

    def test_row_prefers_the_dialog_to_the_directory(self):
        self.assertEqual(agents.row(agent('waiting', detail='confirm: Allow?'))[3], 'confirm: Allow?')
        self.assertEqual(agents.row(agent(None)), ('Claude', 'proj', 'unknown', '/w/proj'))


if __name__ == '__main__':
    unittest.main()
