#!/usr/bin/python3 -I
"""Install an SSH-session-only skip for the managed sudo YubiKey rule."""
import ctypes
import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HELPER = Path('/usr/local/libexec/dotfiles-yubikey-ssh')
MARKER = '# dotfiles YubiKey (managed by setup-yubikey)\n'
LEGACY_RULE = f'auth [success=2 default=ignore] pam_exec.so quiet quiet_log seteuid {HELPER} --check\n'
RULE = f'auth [success=ignore default=3] pam_exec.so quiet quiet_log seteuid {HELPER} --check\n'


def remote_rules(username):
    # A separate password branch is necessary: Fedora's system-auth and
    # password-auth both contain pam_u2f when with-pam-u2f is selected.
    return (f'auth [success=4 default=ignore] pam_succeed_if.so user != {username} quiet\n'
            + RULE
            + 'auth required pam_env.so\n'
            + 'auth required pam_faildelay.so delay=2000000\n'
            + 'auth [success=done default=die] pam_unix.so\n')


def session_is_ssh(pid=0, diagnostic=False):
    """Use logind's process session, never caller-supplied SSH environment vars."""
    systemd = ctypes.CDLL('libsystemd.so.0')
    libc = ctypes.CDLL('libc.so.6')
    libc.free.argtypes = [ctypes.c_void_p]
    systemd.sd_pid_get_session.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    systemd.sd_session_get_service.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    systemd.sd_session_is_remote.argtypes = [ctypes.c_void_p]
    session, service = ctypes.c_void_p(), ctypes.c_void_p()
    try:
        result = systemd.sd_pid_get_session(pid, ctypes.byref(session))
        if diagnostic:
            print(f'sd_pid_get_session({pid})={result}')
        if result < 0:
            return False
        remote = systemd.sd_session_is_remote(session)
        if diagnostic:
            print(f'session={ctypes.string_at(session).decode()} remote={remote}')
        if remote != 1:
            return False
        if systemd.sd_session_get_service(session, ctypes.byref(service)) < 0:
            return False
        if diagnostic:
            print(f'service={ctypes.string_at(service).decode()}')
        # Tailscale SSH registers its PAM sessions as tailscaled, not sshd.
        return ctypes.string_at(service) in (b'sshd', b'tailscaled')
    finally:
        libc.free(service)
        libc.free(session)


def render(original):
    # Upgrade our old skip and keep installation idempotent. Only the
    # enrolled user receives the remote password branch.
    original_clean = original.replace(LEGACY_RULE, '')
    users = re.findall(r'auth \[success=1 default=ignore\] pam_succeed_if\.so user != ([a-z_][a-z0-9_-]*) quiet\n', original_clean)
    if len(users) != 1:
        raise ValueError('Unexpected sudo user guard.')
    remote = remote_rules(users[0])
    original_clean = original_clean.replace(remote, '')
    pattern = (re.escape(MARKER)
               + r'auth \[success=1 default=ignore\] pam_succeed_if\.so user != [a-z_][a-z0-9_-]* quiet\n'
               + r'auth (?:sufficient|required) pam_u2f\.so [^\n]+\n'
               + r'(?=auth\s+include\s+system-auth\s*\n)')
    matches = list(re.finditer(pattern, original_clean))
    if len(matches) != 1 or original_clean.count('pam_u2f.so') != 1:
        raise ValueError('Unexpected sudo PAM rules; refusing to change them.')
    match = matches[0]
    block = match.group()
    return original_clean[:match.start()] + block.replace(MARKER, MARKER + remote, 1) + original_clean[match.end():]


def validate_password_policy(contents):
    # This branch implements this host's local-password profile. Refuse an
    # installation that would omit additional required authentication policy.
    rules = [' '.join(line.split()) for line in contents.splitlines()
             if line.strip().startswith('auth ')]
    expected = ['auth required pam_env.so',
                'auth required pam_faildelay.so delay=2000000',
                'auth sufficient pam_u2f.so cue',
                'auth sufficient pam_unix.so nullok',
                'auth required pam_deny.so']
    if rules != expected:
        raise ValueError('Password authentication policy changed; review before installing the SSH password branch.')


def install():
    if os.geteuid() != 0:
        raise SystemExit('Run: sudo python3 -I scripts/yubikey-ssh.py --install')
    pam = Path('/etc/pam.d/sudo')
    if pam.is_symlink() or not pam.is_file() or HELPER.is_symlink():
        raise SystemExit('Unexpected installation paths; refusing to overwrite.')
    original = pam.read_text()
    validate_password_policy(Path('/etc/pam.d/password-auth').read_text())
    updated = render(original)
    payload = Path(__file__).read_bytes()
    if updated == original and HELPER.is_file() and HELPER.read_bytes() == payload:
        print('SSH sudo skip is already installed.')
        return
    backup = Path('/var/backups') / ('dotfiles-yubikey-ssh-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(mode=0o700, parents=True)
    shutil.copy2(pam, backup / 'sudo')
    had_helper = HELPER.exists()
    if had_helper:
        shutil.copy2(HELPER, backup / 'helper')
    try:
        HELPER.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        HELPER.write_bytes(payload)
        HELPER.chmod(0o755)
        os.chown(HELPER, 0, 0)
        subprocess.run(['restorecon', str(HELPER)], check=True)
        pam.write_text(updated)
        subprocess.run(['restorecon', str(pam)], check=True)
    except BaseException:
        shutil.copy2(backup / 'sudo', pam)
        if had_helper:
            shutil.copy2(backup / 'helper', HELPER)
        else:
            HELPER.unlink(missing_ok=True)
        raise
    print(f'Installed SSH sudo skip. Original sudo PAM file: {backup / "sudo"}')
    print('Test sudo -k; sudo true locally and in a fresh SSH shell.')


if __name__ == '__main__':
    if sys.argv[1:] == ['--check']:
        try:
            remote = session_is_ssh()
        except (OSError, ValueError, AttributeError):
            remote = False
        sys.exit(0 if remote else 1)
    elif sys.argv[1:] == ['--diagnose']:
        print(f'pid={os.getpid()} parent={os.getppid()} uid={os.getuid()} euid={os.geteuid()}')
        print(Path('/proc/self/cgroup').read_text().strip())
        print(f'SSH match={session_is_ssh(diagnostic=True)}')
    elif sys.argv[1:] == ['--install']:
        install()
    else:
        raise SystemExit('Usage: yubikey-ssh.py --install | --check | --diagnose')
