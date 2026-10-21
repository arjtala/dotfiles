import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.config/waybar/scripts'))
import tailscale_status as ts


class TailscaleTests(unittest.TestCase):
    def test_connected_details_and_offline_exit(self):
        state = ts.summarize({'BackendState': 'Running',
                              'Self': {'DNSName': 'laptop.example.ts.net.', 'TailscaleIPs': ['100.64.0.1']},
                              'CurrentTailnet': {'Name': 'home & work'},
                              'Peer': {'x': {'DNSName': 'nas.example.ts.net.', 'ExitNode': True, 'Online': False}},
                              'Health': ['Check DNS']})
        self.assertEqual(state['kind'], 'exit')
        self.assertIn(('Exit node', 'nas (offline)'), state['rows'])
        self.assertIn(('Peers', '0 of 1 online'), state['rows'])
        self.assertIn('home &amp; work', ts.bar_output(state)['tooltip'])

    def test_state_mapping_and_absent_cli(self):
        for backend, kind in [('Running', 'on'), ('Stopped', 'off'), ('Starting', 'busy'),
                              ('NeedsLogin', 'login'), ('NeedsMachineAuth', 'approval')]:
            self.assertEqual(ts.summarize({'BackendState': backend})['kind'], kind)
        with patch.object(ts.shutil, 'which', return_value=None):
            self.assertEqual(ts.bar_output(ts.snapshot())['text'], '')

    def test_valid_status_is_accepted_even_on_nonzero_exit(self):
        result = subprocess.CompletedProcess([], 1, json.dumps({'BackendState': 'NeedsLogin'}), '')
        with patch.object(ts.shutil, 'which', return_value='/bin/tailscale'), \
                patch.object(ts.subprocess, 'run', return_value=result):
            self.assertEqual(ts.snapshot()['kind'], 'login')

    def test_permission_failure_never_tries_sudo(self):
        result = subprocess.CompletedProcess([], 1, '', 'Access denied')
        with patch.object(ts.subprocess, 'run', return_value=result) as run:
            error = ts.switch(ts.summarize({'BackendState': 'Running'}))
            self.assertIn('--operator', error)
            self.assertEqual(run.call_args.args[0], ['tailscale', 'down'])
            self.assertEqual(run.call_count, 1)

    def test_state_change_is_verified(self):
        off = ts.summarize({'BackendState': 'Stopped'})
        with patch.object(ts.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run, \
                patch.object(ts, 'snapshot', return_value=off):
            self.assertIn('not confirmed', ts.switch(off))
            self.assertEqual(run.call_args.args[0], ['tailscale', 'up', '--timeout=15s'])

    def test_unsafe_login_urls_are_not_opened(self):
        state = ts.summarize({'BackendState': 'NeedsLogin', 'AuthURL': 'file:///etc/passwd'})
        with patch.object(ts.subprocess, 'Popen') as popen:
            self.assertIn('terminal', ts.switch(state))
            popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
