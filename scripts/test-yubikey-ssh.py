import ctypes
import importlib.util
from pathlib import Path
import unittest
import tempfile
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location('yubikey_ssh', Path(__file__).with_name('yubikey-ssh.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
ORIGINAL = ('#%PAM-1.0\n' + helper.MARKER
            + 'auth [success=1 default=ignore] pam_succeed_if.so user != alice quiet\n'
            + 'auth sufficient pam_u2f.so authfile=/etc/u2f_mappings cue\n'
            + 'auth include system-auth\naccount include system-auth\n')


class PolicyTests(unittest.TestCase):
    def test_real_pam_dispatch_never_falls_back_to_key_after_wrong_ssh_password(self):
        pam = ctypes.CDLL('libpam.so.0')
        class Conversation(ctypes.Structure):
            _fields_ = [('conv', ctypes.c_void_p), ('data', ctypes.c_void_p)]
        pam.pam_start_confdir.argtypes = [ctypes.c_char_p, ctypes.c_char_p,
            ctypes.POINTER(Conversation), ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
        pam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
        pam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]
        # The real PAM engine evaluates our jump controls. Only authentication
        # mechanisms are replaced with deterministic allow/deny modules.
        for owner, ssh, password_ok, key_ok, expected in (
                (True, True, True, False, True),
                (True, True, False, True, False),
                (True, False, False, True, True),
                (True, False, True, False, False),
                (False, True, True, True, False)):
            text = helper.render(ORIGINAL)
            guard = 'pam_succeed_if.so user != alice quiet'
            text = text.replace(guard, 'pam_exec.so quiet quiet_log /usr/bin/' + ('false' if owner else 'true'))
            text = text.replace(f'{helper.HELPER} --check', '/usr/bin/' + ('true' if ssh else 'false'))
            text = text.replace('pam_env.so', 'pam_permit.so')
            text = text.replace('pam_faildelay.so delay=2000000', 'pam_permit.so')
            text = text.replace('pam_unix.so', 'pam_permit.so' if password_ok else 'pam_deny.so')
            text = text.replace('pam_u2f.so authfile=/etc/u2f_mappings cue', 'pam_permit.so' if key_ok else 'pam_deny.so')
            with tempfile.TemporaryDirectory() as directory:
                Path(directory, 'probe').write_text(text)
                Path(directory, 'system-auth').write_text('auth requisite pam_deny.so\n')
                handle = ctypes.c_void_p()
                conv = Conversation()
                result = pam.pam_start_confdir(b'probe', b'alice', ctypes.byref(conv), directory.encode(), ctypes.byref(handle))
                self.assertEqual(result, 0)
                try:
                    result = pam.pam_authenticate(handle, 0)
                    self.assertEqual(result == 0, expected, (owner, ssh, password_ok, key_ok, result))
                finally:
                    pam.pam_end(handle, result)

    def test_remote_password_branch_for_both_modes(self):
        for control in ('sufficient', 'required'):
            original = ORIGINAL.replace('auth sufficient', 'auth ' + control)
            rendered = helper.render(original)
            rules = [line for line in rendered.splitlines() if line.startswith('auth ')]
            self.assertIn('success=4', rules[0])
            self.assertEqual(rules[1], helper.RULE.strip())
            self.assertEqual(rules[4], 'auth [success=done default=die] pam_unix.so')
            # Both non-owner and non-SSH branches jump to the original guard.
            self.assertIn('success=1', rules[5])
            self.assertIn('pam_u2f.so', rules[6])
            self.assertEqual(rules[7], 'auth include system-auth')
            self.assertEqual(rendered.replace(helper.remote_rules('alice'), ''), original)
            self.assertEqual(helper.render(rendered), rendered)

    def test_upgrade_legacy_skip(self):
        legacy = ORIGINAL.replace(helper.MARKER, helper.MARKER + helper.LEGACY_RULE)
        self.assertEqual(helper.render(legacy), helper.render(ORIGINAL))

    def test_unknown_required_password_policy_rejected(self):
        actual = ('auth required pam_env.so\n'
                  'auth required pam_faildelay.so delay=2000000\n'
                  'auth sufficient pam_u2f.so cue\n'
                  'auth sufficient pam_unix.so nullok\n'
                  'auth required pam_deny.so\n')
        helper.validate_password_policy(actual)
        with self.assertRaises(ValueError):
            helper.validate_password_policy(actual + '\nauth required pam_faillock.so\n')

    def test_unknown_rules_rejected(self):
        for original in (ORIGINAL.replace(helper.MARKER, ''),
                         ORIGINAL.replace('auth include system-auth', 'auth optional pam_permit.so\nauth include system-auth'),
                         ORIGINAL + 'auth required pam_u2f.so\n'):
            with self.assertRaises(ValueError):
                helper.render(original)

    def test_only_remote_sshd_session_matches(self):
        for remote, service, pid_result, service_result, expected in (
                (1, b'sshd', 0, 0, True), (0, b'sshd', 0, 0, False),
                (1, b'tailscaled', 0, 0, True), (0, b'tailscaled', 0, 0, False),
                (1, b'login', 0, 0, False), (1, b'gdm-password', 0, 0, False),
                (-1, b'sshd', 0, 0, False), (1, b'sshd', -6, 0, False),
                (1, b'sshd', 0, -6, False)):
            lib, libc = MagicMock(), MagicMock()
            buffers = [ctypes.create_string_buffer(b'42'), ctypes.create_string_buffer(service)]
            def session(pid, output):
                self.assertEqual(pid, 0)
                ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.addressof(buffers[0])
                return pid_result
            def get_service(sid, output):
                ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.addressof(buffers[1])
                return service_result
            lib.sd_pid_get_session.side_effect = session
            lib.sd_session_get_service.side_effect = get_service
            lib.sd_session_is_remote.return_value = remote
            with patch.object(ctypes, 'CDLL', side_effect=[lib, libc]):
                self.assertEqual(helper.session_is_ssh(), expected)
            self.assertEqual(libc.free.call_count, 2)


if __name__ == '__main__':
    unittest.main()
