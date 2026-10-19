import contextlib
import ctypes
import getpass
import importlib.util
import io
from pathlib import Path
import platform
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('yubikey_pam_macos', Path(__file__).with_name('yubikey-pam-macos.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
MODULE = '/opt/homebrew/opt/pam-u2f/lib/pam/pam_u2f.so'
USER = getpass.getuser()
TEMPLATE = Path('/etc/pam.d/sudo_local.template')
STOCK_SUDO = ('# sudo: auth account password session\n'
              'auth       include        sudo_local\n'
              'auth       sufficient     pam_smartcard.so\n'
              'auth       required       pam_opendirectory.so\n'
              'account    required       pam_permit.so\n'
              'password   required       pam_deny.so\n'
              'session    required       pam_permit.so\n')
TOUCH_ID = '# local\nauth       sufficient     pam_tid.so\n'
SIGNALS = helper.STOP_SIGNALS + (signal.SIGINT,)
REAL_MKDTEMP = tempfile.mkdtemp  # helper.tempfile is this same module, and gets patched


def key(user=USER):
    return f'{user}:owBYtfE0Za+fake/handle==,pLcWFsGi4kWl8Hj+fake/key==,es256,+presence'


def rule(mode='passwordless', authfile=None):
    return helper.module_args(MODULE, authfile or helper.MAPPING, mode)


def auth_rules(text):
    return [line.split() for line in text.splitlines() if line.lstrip().startswith('auth')]


class Sandbox:
    """Temporary /etc/pam.d, mapping and backup root, patched into the helper."""

    def __init__(self, sudo_local=None, sudo=STOCK_SUDO, mapping=None):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.pam = root / 'pam.d'
        self.pam.mkdir()
        (self.pam / 'sudo').write_text(sudo)
        self.sudo_local = self.pam / 'sudo_local'
        if sudo_local is not None:
            self.sudo_local.write_text(sudo_local)
        self.mapping = root / 'u2f_mappings'
        if mapping is not None:
            self.mapping.write_text(mapping)
        self.backups = root / 'backups'
        self.module = root / 'keg' / 'pam_u2f.so'
        self.module.parent.mkdir()
        self.module.write_text('')
        self.registration = root / 'registration'
        self.registration.write_text(key() + '\n')
        self.staging = []
        self.patches = [patch.object(helper, 'PAM_DIR', self.pam), patch.object(helper, 'SUDO', self.pam / 'sudo'),
                        patch.object(helper, 'SUDO_LOCAL', self.sudo_local), patch.object(helper, 'MAPPING', self.mapping),
                        patch.object(helper, 'BACKUP_ROOT', self.backups),
                        patch.object(helper.tempfile, 'mkdtemp', side_effect=self.mkdtemp)]

    def mkdtemp(self, **kwargs):
        path = REAL_MKDTEMP(**kwargs)
        self.staging.append(Path(path))
        return path

    def __enter__(self):
        self.handlers = {s: signal.getsignal(s) for s in SIGNALS}
        for p in self.patches:
            p.start()
        helper.caught.clear()
        return self

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()
        for s, handler in self.handlers.items():  # the helper ignores signals while restoring
            signal.signal(s, handler)
        helper.caught.clear()
        self.tmp.cleanup()

    def install(self, mode='passwordless', authenticate=(0, 'success'), final=None):
        auth = patch.object(helper, 'authenticate', side_effect=authenticate if callable(authenticate) else None,
                            return_value=None if callable(authenticate) else authenticate)
        run = patch.object(helper.subprocess, 'run', side_effect=final)
        out = io.StringIO()
        with auth as self.authenticate, run as self.run, contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(out):
            try:
                helper.install(mode, USER, str(self.registration), str(self.module))
            finally:
                self.output = out.getvalue()

    def remove(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            helper.remove(USER)
        return out.getvalue()

    def backup(self):
        (backup,) = self.backups.iterdir()
        return backup


class RenderTests(unittest.TestCase):
    def test_new_file_keeps_apple_header_and_adds_one_rule(self):
        text = helper.render('', 'passwordless', rule())
        self.assertTrue(text.startswith(helper.HEADER))
        self.assertIn(helper.MARKER, text)
        rules = auth_rules(text)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0][:3], ['auth', 'sufficient', MODULE])
        self.assertIn('authfile=/etc/u2f_mappings', rules[0])

    def test_key_rule_goes_before_existing_rules(self):
        original = ('# local\nauth       optional       /opt/homebrew/lib/pam/pam_reattach.so\n'
                    'auth       sufficient     pam_tid.so')  # no trailing newline
        text = helper.render(original, 'passwordless', rule())
        self.assertEqual([r[2] for r in auth_rules(text)], [MODULE, '/opt/homebrew/lib/pam/pam_reattach.so', 'pam_tid.so'])
        self.assertTrue(text.endswith('\n'))

    def test_comment_only_file_gets_rule_appended(self):
        original = '# sudo_local: header\n#auth       sufficient     pam_tid.so\n'
        text = helper.render(original, 'passwordless', rule())
        self.assertTrue(text.startswith(original))  # the commented Touch ID line is kept as is
        self.assertEqual([r[2] for r in auth_rules(text)], [MODULE])

    def test_existing_key_rules_stop_for_review(self):
        for original in ('auth sufficient /opt/homebrew/lib/pam/pam_u2f.so cue\n', helper.MARKER + '\n'):
            with self.assertRaises(ValueError):
                helper.render(original, 'passwordless', 'pam_u2f.so')

    def test_marker_names_pam_u2f_so_handover_grep_and_sed_catch_it(self):
        self.assertIn('pam_u2f', helper.MARKER)
        self.assertIn('managed by setup-yubikey-macos', helper.MARKER)

    def test_passwordless_refuses_rules_a_touch_would_skip(self):
        for control in ('required', 'requisite', 'include', 'binding'):
            original = f'auth       {control}       pam_corp.so  # policy\n'
            with self.assertRaises(ValueError, msg=control):
                helper.render(original, 'passwordless', rule())
            helper.render(original, 'two-factor', rule('two-factor'))  # the touch does not end the chain

    def test_nouserok_only_with_required(self):
        # nouserok with "sufficient" would let unmapped users skip authentication.
        self.assertNotIn('nouserok', helper.render('', 'passwordless', rule()))
        two_factor = auth_rules(helper.render('', 'two-factor', rule('two-factor')))[0]
        self.assertEqual(two_factor[1], 'required')
        self.assertIn('nouserok', two_factor)

    def test_rule_uses_fixed_origin_and_user_presence(self):
        args = rule().split()
        self.assertEqual(args[0], MODULE)
        for option in ('origin=pam://dotfiles-local', 'appid=pam://dotfiles-local', 'userpresence=1', 'cue'):
            self.assertIn(option, args)


class StackTests(unittest.TestCase):
    def test_stock_stack_passes_both_modes(self):
        for mode in ('passwordless', 'two-factor'):
            helper.check_sudo_stack(STOCK_SUDO, mode)
        helper.check_sudo_stack(STOCK_SUDO.replace('sudo_local\n', 'sudo_local  # local rules\n'), 'passwordless')

    def test_include_must_be_the_first_auth_rule(self):
        smartcard_first = STOCK_SUDO.replace('auth       include        sudo_local\n', '') + 'auth include sudo_local\n'
        touch_id_first = STOCK_SUDO.replace('auth       include', 'auth sufficient pam_tid.so\nauth       include')
        for text in (smartcard_first, touch_id_first, STOCK_SUDO.replace('include        sudo_local', 'include  other')):
            with self.assertRaises(ValueError):
                helper.check_sudo_stack(text, 'two-factor')

    def test_existing_pam_u2f_in_sudo_stops(self):
        with self.assertRaises(ValueError):
            helper.check_sudo_stack(STOCK_SUDO + 'auth sufficient /x/pam_u2f.so\n', 'two-factor')

    def test_passwordless_refuses_extra_required_rules_after_include(self):
        extra = STOCK_SUDO.replace('auth       required       pam_opendirectory.so\n',
                                   'auth       required       pam_opendirectory.so\nauth required pam_duo.so\n')
        with self.assertRaises(ValueError):
            helper.check_sudo_stack(extra, 'passwordless')
        helper.check_sudo_stack(extra, 'two-factor')

    @unittest.skipUnless(Path('/etc/pam.d/sudo').exists() and platform.system() == 'Darwin', 'macOS only')
    def test_this_macs_sudo_rules_pass(self):
        helper.check_sudo_stack(Path('/etc/pam.d/sudo').read_text(), 'passwordless')


class StripTests(unittest.TestCase):
    def test_round_trip_restores_other_lines(self):
        self.assertEqual(helper.strip_managed(helper.render(TOUCH_ID, 'passwordless', rule())), TOUCH_ID)
        self.assertEqual(helper.strip_managed(helper.render('', 'two-factor', rule('two-factor'))), helper.HEADER)

    def test_refuses_without_marker_or_with_unexpected_line(self):
        with self.assertRaises(ValueError):
            helper.strip_managed(TOUCH_ID)
        with self.assertRaises(ValueError):
            helper.strip_managed(helper.MARKER + '\nauth sufficient pam_tid.so\n')


class RegistrationTests(unittest.TestCase):
    def test_accepts_pamu2fcfg_output(self):
        self.assertEqual(helper.validate_registration(key('alice') + '\n', 'alice'), key('alice'))
        two = key('alice') + ':' + key('alice').split(':', 1)[1].replace('+presence', '+presence+pin')
        self.assertEqual(helper.validate_registration(two, 'alice').count(':'), 2)

    def test_rejects_other_users_and_malformed_lines(self):
        good = key('alice')
        for data in (good.replace('alice', 'bob'), good + '\nalice:x', 'alice:', 'alice:onlyone',
                     good.replace('es256', 'md5'), good.replace('+presence', 'presence'),
                     good.replace('owBYtfE0Za', 'owB YtfE0Za')):
            with self.assertRaises(ValueError, msg=data):
                helper.validate_registration(data, 'alice')


class FinalCheckTests(unittest.TestCase):
    def test_passwordless_check_refuses_pin_and_password_prompts(self):
        command = helper.final_check('passwordless', 'alice')
        self.assertEqual(command[:3], ['/usr/bin/sudo', '-u', 'alice'])
        self.assertIn('SUDO_ASKPASS=/usr/bin/false', command)
        self.assertEqual(command[-4:], ['/usr/bin/sudo', '-A', '-k', '-v'])

    def test_two_factor_check_is_interactive(self):
        self.assertEqual(helper.final_check('two-factor', 'alice'),
                         ['/usr/bin/sudo', '-u', 'alice', '/usr/bin/sudo', '-k', '-v'])


class InstallTests(unittest.TestCase):
    def test_success_without_sudo_local(self):
        with Sandbox() as box:
            def check_test_service(service, user):
                text = (box.pam / service).read_text()
                self.assertEqual((service, user), (helper.TEST_SERVICE, USER))
                self.assertIn('required', text.split())
                self.assertIn(f'authfile={box.staging[0] / "u2f_mappings"}', text)
                self.assertNotIn('nouserok', text)
                return 0, 'success'
            box.install(authenticate=check_test_service)
            self.assertEqual(box.sudo_local.read_text(),
                             helper.render('', 'passwordless', helper.module_args(str(box.module), box.mapping, 'passwordless')))
            self.assertEqual(box.mapping.read_text(), key() + '\n')
            box.run.assert_called_once_with(helper.final_check('passwordless', USER), check=True)
            self.assertFalse((box.pam / helper.TEST_SERVICE).exists())
            self.assertFalse((box.pam / helper.PENDING).exists())
            self.assertFalse(box.staging[0].exists())
            self.assertTrue((box.backup() / 'sudo_local.absent').exists())
            self.assertIn(str(box.backup()), box.output)

    def test_success_keeps_existing_rules_after_the_key(self):
        with Sandbox(sudo_local=TOUCH_ID) as box:
            box.install()
            self.assertEqual([r[2] for r in auth_rules(box.sudo_local.read_text())], [str(box.module), 'pam_tid.so'])
            self.assertEqual((box.backup() / 'sudo_local').read_text(), TOUCH_ID)

    def assert_restored(self, box, original):
        if original is None:
            self.assertFalse(box.sudo_local.exists())
        else:
            self.assertEqual(box.sudo_local.read_text(), original)
        self.assertFalse(box.mapping.exists())
        self.assertFalse((box.pam / helper.TEST_SERVICE).exists())
        self.assertTrue(all(not path.exists() for path in box.staging))

    def test_failed_key_test_changes_nothing(self):
        for original in (None, TOUCH_ID):
            with Sandbox(sudo_local=original) as box:
                with self.assertRaisesRegex(SystemExit, 'Key test failed'):
                    box.install(authenticate=(9, 'authentication error'))
                self.assert_restored(box, original)
                box.run.assert_not_called()

    def test_failed_sudo_check_restores_everything(self):
        for original in (None, TOUCH_ID):
            with Sandbox(sudo_local=original) as box:
                with self.assertRaisesRegex(SystemExit, 'sudo did not accept the key'):
                    box.install(final=subprocess.CalledProcessError(1, 'sudo'))
                self.assert_restored(box, original)
                self.assertIn('Restored the previous sudo configuration', box.output)

    def test_hang_up_during_sudo_check_restores_everything(self):
        # on_signal turns SIGHUP into SystemExit(129); subprocess.run passes it on.
        for original in (None, TOUCH_ID):
            with Sandbox(sudo_local=original) as box:
                with self.assertRaises(SystemExit) as raised:
                    box.install(final=SystemExit(129))
                self.assertEqual(raised.exception.code, 129)
                self.assert_restored(box, original)

    def test_signal_swallowed_by_the_pam_callback_still_aborts(self):
        with Sandbox() as box:
            def interrupted(service, user):
                helper.caught.append(signal.SIGHUP)
                return 0, 'success'
            with self.assertRaises(SystemExit) as raised:
                box.install(authenticate=interrupted)
            self.assertEqual(raised.exception.code, 128 + signal.SIGHUP)
            self.assert_restored(box, None)

    def test_left_over_or_shared_mapping_stops(self):
        with Sandbox(mapping=key() + '\n') as box:
            with self.assertRaisesRegex(SystemExit, 'left over'):
                box.install()
        with Sandbox(mapping=key() + '\n', sudo_local='auth sufficient pam_u2f.so authfile=/etc/u2f_mappings\n') as box:
            with self.assertRaisesRegex(SystemExit, 'used by a PAM rule'):
                box.install()

    def test_stale_test_service_is_removed_first(self):
        with Sandbox() as box:
            (box.pam / helper.TEST_SERVICE).write_text('auth required /x/pam_u2f.so authfile=/tmp/gone\n')
            box.install()
            self.assertIn('left by an interrupted run', box.output)
            self.assertFalse((box.pam / helper.TEST_SERVICE).exists())

    def test_refuses_symlinks_bad_modules_and_bad_registrations(self):
        with Sandbox() as box:
            box.sudo_local.symlink_to(box.pam / 'sudo')
            with self.assertRaisesRegex(SystemExit, 'symlink'):
                box.install()
        with Sandbox() as box:
            box.module.rename(box.module.with_name('other.so'))
            with self.assertRaisesRegex(SystemExit, 'module path'):
                box.install()
        with Sandbox() as box:
            box.registration.write_text(key('someone-else'))
            with self.assertRaisesRegex(SystemExit, 'Invalid enrollment'):
                box.install()
            self.assertFalse(box.backups.exists())


class RemoveTests(unittest.TestCase):
    def test_remove_undoes_an_install(self):
        for original in (None, TOUCH_ID):
            with Sandbox(sudo_local=original) as box:
                box.install()
                output = box.remove()
                if original is None:
                    self.assertFalse(box.sudo_local.exists())
                else:
                    self.assertEqual(box.sudo_local.read_text(), original)
                self.assertFalse(box.mapping.exists())
                self.assertIn('revokes the registered key', output)
                backup = max(box.backups.glob('dotfiles-pam-remove-*'))
                self.assertEqual((backup / 'u2f_mappings').read_text(), key() + '\n')

    def test_remove_refuses_hand_made_rules(self):
        with Sandbox(sudo_local='auth sufficient /opt/homebrew/lib/pam/pam_u2f.so cue\n') as box:
            with self.assertRaisesRegex(SystemExit, 'did not create'):
                box.remove()

    def test_remove_cleans_left_overs_and_is_idempotent(self):
        with Sandbox(mapping=key() + '\n') as box:
            self.assertIn('revokes', box.remove())
            self.assertFalse(box.mapping.exists())
            self.assertIn('Nothing to remove', box.remove())


class SignalTests(unittest.TestCase):
    def setUp(self):
        self.handlers = {s: signal.getsignal(s) for s in SIGNALS}
        helper.caught.clear()

    def tearDown(self):
        for s, handler in self.handlers.items():
            signal.signal(s, handler)
        helper.caught.clear()

    def test_first_signal_exits_and_later_ones_are_ignored(self):
        with self.assertRaises(SystemExit) as raised:
            helper.on_signal(signal.SIGHUP, None)
        self.assertEqual(raised.exception.code, 128 + signal.SIGHUP)
        self.assertEqual(helper.caught, [signal.SIGHUP])
        for s in SIGNALS:
            self.assertEqual(signal.getsignal(s), signal.SIG_IGN)
        with self.assertRaises(SystemExit):
            helper.raise_if_signalled()

    def test_conversation_refuses_prompts_and_never_raises(self):
        prompt = helper.PamMessage(1, b'Password:')  # PAM_PROMPT_ECHO_OFF
        messages = (ctypes.POINTER(helper.PamMessage) * 1)(ctypes.pointer(prompt))
        response = ctypes.POINTER(helper.PamResponse)()
        self.assertEqual(helper.converse(1, messages, ctypes.pointer(response), None), helper.PAM_CONV_ERR)
        self.assertFalse(response)
        info = helper.PamMessage(helper.PAM_TEXT_INFO, b'Please touch the device.')
        messages = (ctypes.POINTER(helper.PamMessage) * 1)(ctypes.pointer(info))
        with patch('builtins.print', side_effect=SystemExit(129)):
            self.assertEqual(helper.converse(1, messages, ctypes.pointer(response), None), helper.PAM_CONV_ERR)

    @unittest.skipUnless(platform.system() == 'Darwin', 'macOS libSystem')
    def test_conversation_allocates_responses_with_the_c_allocator(self):
        info = helper.PamMessage(helper.PAM_TEXT_INFO, b'Please touch the device.')
        messages = (ctypes.POINTER(helper.PamMessage) * 1)(ctypes.pointer(info))
        response = ctypes.POINTER(helper.PamResponse)()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(helper.converse(1, messages, ctypes.pointer(response), None), helper.PAM_SUCCESS)
        self.assertEqual(out.getvalue(), 'Please touch the device.\n')
        self.assertTrue(response)
        self.assertIsNone(response[0].resp)
        helper.libc().free(ctypes.cast(response, ctypes.c_void_p))


@unittest.skipUnless(platform.system() == 'Darwin', 'macOS OpenPAM only')
class OpenPamTests(unittest.TestCase):
    def test_bindings_start_and_end_a_real_session(self):
        pam = helper.pam_library()
        conversation = helper.PamConv(helper.CONVERSE(lambda *args: helper.PAM_CONV_ERR), None)
        handle = ctypes.c_void_p()
        result = pam.pam_start(b'sudo', b'root', ctypes.byref(conversation), ctypes.byref(handle))
        self.assertEqual(result, helper.PAM_SUCCESS)
        self.assertEqual(pam.pam_strerror(handle, helper.PAM_CONV_ERR), b'conversation failure')
        self.assertEqual(pam.pam_end(handle, result), helper.PAM_SUCCESS)

    @unittest.skipUnless(TEMPLATE.exists(), 'no sudo_local.template')
    def test_header_matches_apples_template(self):
        self.assertEqual(TEMPLATE.read_text().splitlines()[0] + '\n', helper.HEADER)


if __name__ == '__main__':
    unittest.main()
