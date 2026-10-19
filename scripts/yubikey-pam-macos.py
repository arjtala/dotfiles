#!/usr/bin/python3 -I
"""Root helper for setup-yubikey-macos; isolated key test precedes live PAM edits."""
import ctypes
import datetime
import os
import pathlib
import pwd
import re
import shutil
import signal
import subprocess
import sys
import tempfile

MARKER = '# dotfiles YubiKey pam_u2f rule (managed by setup-yubikey-macos)'
ORIGIN = 'pam://dotfiles-local'
PAM_DIR = pathlib.Path('/etc/pam.d')
SUDO = PAM_DIR / 'sudo'
SUDO_LOCAL = PAM_DIR / 'sudo_local'
MAPPING = pathlib.Path('/etc/u2f_mappings')
BACKUP_ROOT = pathlib.Path('/var/backups')
TEST_SERVICE = 'dotfiles-yubikey-test'
PENDING = '.sudo_local.dotfiles-new'
# Apple's sudo_local.template header, kept when this helper creates the file.
HEADER = '# sudo_local: local config file which survives system update and is included for sudo\n'
COSE_TYPES = ('es256', 'eddsa', 'rs256')
BASE64 = re.compile(r'[A-Za-z0-9+/=_-]+')
STOP_SIGNALS = (signal.SIGHUP, signal.SIGTERM, signal.SIGQUIT)

# OpenPAM (macOS) values; Linux-PAM numbers some of these differently.
PAM_SUCCESS, PAM_BUF_ERR, PAM_CONV_ERR = 0, 5, 6
PAM_ERROR_MSG, PAM_TEXT_INFO = 3, 4

caught = []


def on_signal(signum, _frame):
    """Turn a hang-up or terminate into SystemExit once, so rollback and cleanup run."""
    caught.append(signum)
    hold_signals()
    raise SystemExit(128 + signum)


def hold_signals():
    """Nothing may interrupt a restore once it has started."""
    for s in STOP_SIGNALS + (signal.SIGINT,):
        signal.signal(s, signal.SIG_IGN)


def raise_if_signalled():
    # A handler that ran inside the PAM callback could not raise through C.
    if caught:
        raise SystemExit(128 + caught[0])


def auth_rules(text):
    """Active auth rules as [control, module, args...]; pam.conf ignores text after '#'."""
    rules = (line.split('#', 1)[0].split() for line in text.splitlines())
    return [rule[1:] for rule in rules if rule and rule[0] == 'auth']


def check_sudo_stack(text, mode):
    rules = auth_rules(text)
    if not rules or rules[0] != ['include', 'sudo_local']:
        raise ValueError(f'{SUDO} must start its auth rules with "auth include sudo_local" '
                         '(stock macOS); refusing to guess where the rule belongs.')
    if any('pam_u2f' in ' '.join(rule) for rule in rules):
        raise ValueError(f'{SUDO} already references pam_u2f; review it before running this.')
    if mode == 'passwordless':
        # A sufficient touch ends the chain. It may replace the stock password
        # check, but must not skip anything else that is required.
        skipped = [rule for rule in rules[1:] if rule[0] not in ('sufficient', 'optional')
                   and rule[:2] != ['required', 'pam_opendirectory.so']]
        if skipped:
            raise ValueError('A passwordless touch would skip these sudo rules: '
                             + '; '.join(' '.join(rule) for rule in skipped)
                             + '. Use two-factor or review /etc/pam.d/sudo.')


def module_args(module, authfile, mode):
    args = [module, f'authfile={authfile}', f'origin={ORIGIN}', f'appid={ORIGIN}', 'userpresence=1', 'cue']
    if mode == 'two-factor':
        # Users without a mapping keep their policy. Never use nouserok with
        # "sufficient": unmapped users would then pass sudo with no credential.
        args.append('nouserok')
    return ' '.join(args)


def render(original, mode, rule):
    """Put the key rule ahead of any existing auth rules in sudo_local."""
    if MARKER in original or 'pam_u2f' in original:
        raise ValueError('sudo_local already contains a YubiKey rule; review it before replacing it.')
    if mode == 'passwordless':
        blocking = [rule for rule in auth_rules(original) if rule[0] not in ('sufficient', 'optional')]
        if blocking:
            raise ValueError('sudo_local has auth rules a passwordless touch would skip: '
                             + '; '.join(' '.join(rule) for rule in blocking)
                             + '. Use two-factor or review the file.')
    control = 'sufficient' if mode == 'passwordless' else 'required'
    block = f'{MARKER}\nauth       {control:<15}{rule}\n'
    if not original.strip():
        return HEADER + block
    lines = original.splitlines(keepends=True)
    if not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    for i, line in enumerate(lines):
        if re.match(r'\s*auth\s', line):
            lines.insert(i, block)
            return ''.join(lines)
    return ''.join(lines) + block


def strip_managed(text):
    """Remove this script's marker and the rule after it; keep every other line."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.rstrip('\n') == MARKER:
            following = lines[i + 1] if i + 1 < len(lines) else ''
            if following.split()[:1] != ['auth'] or 'pam_u2f' not in following:
                raise ValueError('Unexpected line after the managed marker; review sudo_local by hand.')
            return ''.join(lines[:i] + lines[i + 2:])
    raise ValueError('sudo_local has no rule managed by setup-yubikey-macos.')


def validate_registration(data, username):
    """Accept one pamu2fcfg line for this user: user:handle,key,cose,options[:...]."""
    data = data.strip()
    prefix = username + ':'
    if '\n' in data or not data.startswith(prefix):
        raise ValueError('Invalid enrollment')
    for credential in data[len(prefix):].split(':'):
        fields = credential.split(',')
        if (len(fields) != 4 or not all(BASE64.fullmatch(field) for field in fields[:2])
                or fields[2] not in COSE_TYPES or not re.fullmatch(r'(\+[a-z]+)*', fields[3])):
            raise ValueError('Invalid enrollment')
    return data


def final_check(mode, username):
    """Command that makes sudo itself authenticate the user with the new rules."""
    check = ['/usr/bin/sudo', '-u', username]
    if mode == 'passwordless':
        # The touch rule is sufficient, so a PIN or password would also pass.
        # An askpass that returns nothing cancels those prompts; only the key can pass.
        return check + ['/usr/bin/env', 'SUDO_ASKPASS=/usr/bin/false', '/usr/bin/sudo', '-A', '-k', '-v']
    return check + ['/usr/bin/sudo', '-k', '-v']


def mapping_in_use():
    return any('u2f_mappings' in path.read_text(errors='ignore')
               for path in PAM_DIR.iterdir() if path.is_file() and not path.is_symlink())


def remove_stale_test_service():
    # Only this helper creates it; a hard kill can leave one behind.
    test = PAM_DIR / TEST_SERVICE
    if test.exists() or test.is_symlink():
        test.unlink()
        print(f'Removed {test}, left by an interrupted run.')


def new_backup(kind):
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = BACKUP_ROOT / f'dotfiles-pam-{kind}{stamp}'
    backup.mkdir(mode=0o700, parents=True)
    return backup


def write_sudo_local(text):
    pending = PAM_DIR / PENDING
    pending.write_text(text)
    pending.chmod(0o644)
    os.replace(pending, SUDO_LOCAL)  # sudo never reads a half-written file


class PamMessage(ctypes.Structure):
    _fields_ = [('msg_style', ctypes.c_int), ('msg', ctypes.c_char_p)]


class PamResponse(ctypes.Structure):
    _fields_ = [('resp', ctypes.c_char_p), ('resp_retcode', ctypes.c_int)]


CONVERSE = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.POINTER(PamMessage)),
                            ctypes.POINTER(ctypes.POINTER(PamResponse)), ctypes.c_void_p)


class PamConv(ctypes.Structure):
    _fields_ = [('conv', CONVERSE), ('appdata_ptr', ctypes.c_void_p)]


def libc():
    lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
    lib.calloc.restype = ctypes.c_void_p
    lib.calloc.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
    lib.free.argtypes = [ctypes.c_void_p]
    return lib


def converse(count, messages, responses, _data):
    """Print informational messages and refuse prompts, so a typed password or
    PIN cannot stand in for the key."""
    try:
        for i in range(count):
            message = messages[i].contents
            if message.msg_style not in (PAM_TEXT_INFO, PAM_ERROR_MSG):
                return PAM_CONV_ERR
            print((message.msg or b'').decode(errors='replace'), flush=True)
        # PAM frees the responses, so they must come from the C allocator.
        block = libc().calloc(max(count, 1), ctypes.sizeof(PamResponse))
        if not block:
            return PAM_BUF_ERR
        responses[0] = ctypes.cast(block, ctypes.POINTER(PamResponse))
        return PAM_SUCCESS
    except BaseException:  # nothing, not even SystemExit, may unwind through C
        return PAM_CONV_ERR


def pam_library():
    pam = ctypes.CDLL('/usr/lib/libpam.dylib')
    pam.pam_start.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(PamConv),
                              ctypes.POINTER(ctypes.c_void_p)]
    pam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
    pam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]
    pam.pam_strerror.argtypes = [ctypes.c_void_p, ctypes.c_int]
    pam.pam_strerror.restype = ctypes.c_char_p
    return pam


def authenticate(service, username):
    """Run one PAM authentication in this process (macOS has no pamtester)."""
    pam = pam_library()
    callback = CONVERSE(converse)  # must stay referenced while PAM can call it
    conversation = PamConv(callback, None)
    handle = ctypes.c_void_p()
    result = pam.pam_start(service.encode(), username.encode(), ctypes.byref(conversation), ctypes.byref(handle))
    if result != PAM_SUCCESS:
        return result, pam.pam_strerror(None, result).decode()
    try:
        result = pam.pam_authenticate(handle, 0)
        return result, pam.pam_strerror(handle, result).decode()
    finally:
        pam.pam_end(handle, result)


def check_username(username):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*', username):
        raise SystemExit('Invalid username')
    pwd.getpwnam(username)


def check_not_symlinks():
    for path in (SUDO, SUDO_LOCAL, MAPPING):
        if path.is_symlink():
            raise SystemExit(f'Unexpected symlink: {path}')


def install(mode, username, registration, module):
    if mode not in ('passwordless', 'two-factor'):
        raise SystemExit('Invalid mode')
    check_username(username)
    module_path = pathlib.Path(module)
    if (not module_path.is_absolute() or re.search(r'\s', module)
            or module_path.name != 'pam_u2f.so' or not module_path.is_file()):
        raise SystemExit(f'Unexpected PAM module path: {module}')
    try:
        data = validate_registration(pathlib.Path(registration).read_text(), username)
    except ValueError:
        raise SystemExit('Invalid enrollment; sudo unchanged')
    check_not_symlinks()
    if MAPPING.exists():
        if mapping_in_use():
            raise SystemExit(f'Existing {MAPPING} is used by a PAM rule: review it manually.')
        raise SystemExit(f'{MAPPING} is left over from an earlier run (no PAM rule uses it). '
                         'Run "setup-yubikey-macos remove", then rerun.')
    if not SUDO.is_file():
        raise SystemExit(f'Missing {SUDO}')
    existed = SUDO_LOCAL.exists()
    original = SUDO_LOCAL.read_text() if existed else ''
    try:
        check_sudo_stack(SUDO.read_text(), mode)
    except ValueError as error:
        raise SystemExit(str(error))
    try:
        rendered = render(original, mode, module_args(module, MAPPING, mode))
    except ValueError as error:
        raise SystemExit(f'{error}\nCurrent {SUDO_LOCAL}:\n{original}')
    remove_stale_test_service()

    backup = new_backup('')
    if existed:
        shutil.copy2(SUDO_LOCAL, backup / 'sudo_local')
    else:
        (backup / 'sudo_local.absent').write_text('sudo_local did not exist before setup-yubikey-macos.\n')
    print(f'Originals saved in {backup}', flush=True)

    test = PAM_DIR / TEST_SERVICE
    staging = pathlib.Path(tempfile.mkdtemp(prefix='dotfiles-yubikey-'))  # 0700, root only
    installed = []
    try:
        staged = staging / 'u2f_mappings'
        staged.write_text(data + '\n')
        staged.chmod(0o644)
        with test.open('x') as f:
            # "required" and no nouserok: only a real touch passes this test.
            f.write(f'auth       required       {module_args(module, staged, "passwordless")}\n'
                    'account    required       pam_permit.so\n')
        test.chmod(0o644)
        print('Touch the key again: verifying it before changing sudo.', flush=True)
        result, message = authenticate(TEST_SERVICE, username)
        raise_if_signalled()
        if result != PAM_SUCCESS:
            raise SystemExit(f'Key test failed ({message}); sudo unchanged.')

        installed.append(MAPPING)
        with MAPPING.open('x') as f:
            f.write(data + '\n')
        MAPPING.chmod(0o644)  # public keys; root-owned, so no other process can add one
        installed.append(SUDO_LOCAL)
        write_sudo_local(rendered)

        # The isolated test ran in this process; this one runs sudo itself, as the user.
        then = ', then enter your password or smart-card PIN' if mode == 'two-factor' else ''
        print(f'Touch the key a third time{then}: confirming that sudo itself accepts it.', flush=True)
        try:
            subprocess.run(final_check(mode, username), check=True)
        except subprocess.CalledProcessError:
            raise SystemExit('sudo did not accept the key.')
        print('sudo accepts the key.')
    except BaseException:
        hold_signals()
        if SUDO_LOCAL in installed:
            if existed:
                shutil.copy2(backup / 'sudo_local', SUDO_LOCAL)
            else:
                SUDO_LOCAL.unlink(missing_ok=True)
        if MAPPING in installed:
            MAPPING.unlink(missing_ok=True)
        if installed:
            print('Restored the previous sudo configuration.', file=sys.stderr)
        raise
    finally:
        test.unlink(missing_ok=True)
        (PAM_DIR / PENDING).unlink(missing_ok=True)
        shutil.rmtree(staging, ignore_errors=True)


def remove(username):
    check_username(username)
    check_not_symlinks()
    remove_stale_test_service()
    original = SUDO_LOCAL.read_text() if SUDO_LOCAL.exists() else ''
    managed = MARKER in original
    if not managed and 'pam_u2f' in original:
        raise SystemExit(f'{SUDO_LOCAL} has a pam_u2f rule this script did not create; edit it by hand.')
    if not managed and not MAPPING.exists():
        print('Nothing to remove.')
        return
    try:
        rest = strip_managed(original) if managed else original
    except ValueError as error:
        raise SystemExit(str(error))
    backup = new_backup('remove-')
    for path in (SUDO_LOCAL, MAPPING):
        if path.exists():
            shutil.copy2(path, backup / path.name)
    done = []
    if managed:
        if rest.strip() in ('', HEADER.strip()):
            SUDO_LOCAL.unlink()
        else:
            write_sudo_local(rest)
        done.append('removed the key rule from sudo; it uses your password or smart-card PIN again')
    if MAPPING.exists():
        if mapping_in_use():
            done.append(f'kept {MAPPING}: another PAM rule still uses it')
        else:
            MAPPING.unlink()
            done.append(f'deleted {MAPPING}, which revokes the registered key')
    summary = '; '.join(done)
    print(summary[:1].upper() + summary[1:] + f'. Copies saved in {backup}')


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run via setup-yubikey-macos (requires root).')
    for s in STOP_SIGNALS:
        signal.signal(s, on_signal)
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == 'remove':
        remove(args[1])
    elif len(args) == 4:
        install(*args)
    else:
        raise SystemExit('Usage: yubikey-pam-macos.py {passwordless|two-factor} USER REGISTRATION MODULE '
                         '| remove USER')


if __name__ == '__main__':
    main()
