#!/usr/bin/env python3
"""Root helper for setup-yubikey; isolated key test precedes live PAM edits."""
import datetime
import os
import pathlib
import pwd
import re
import shutil
import subprocess
import sys


def render(original, username, mode, module):
    marker = '# dotfiles YubiKey (managed by setup-yubikey)'
    if marker in original or 'pam_u2f.so' in original:
        raise ValueError('Existing YubiKey PAM configuration: inspect it before replacing it.')
    control = 'sufficient' if mode == 'passwordless' else 'required'
    # Other users retain their existing authentication policy.
    block = (f'{marker}\n'
             f'auth [success=1 default=ignore] pam_succeed_if.so user != {username} quiet\n'
             f'auth {control} {module}\n')
    lines = original.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if re.match(r'^\s*auth\s', line):
            lines.insert(i, block)
            return ''.join(lines)
    raise ValueError('No auth rules found; refusing to modify PAM.')


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run via setup-yubikey (requires root).')
    mode, username, registration = sys.argv[1:]
    if mode not in ('passwordless', 'two-factor') or not re.fullmatch(r'[a-z_][a-z0-9_-]*', username):
        raise SystemExit('Invalid mode or username')
    pwd.getpwnam(username)
    data = pathlib.Path(registration).read_text().strip()
    if not data.startswith(username + ':') or '\n' in data or ',' not in data:
        raise SystemExit('Invalid enrollment; PAM unchanged')
    mapping = pathlib.Path('/etc/u2f_mappings')
    if mapping.exists() or mapping.is_symlink():
        raise SystemExit('Existing /etc/u2f_mappings: preserve it and review enrollment manually.')
    module = ('pam_u2f.so authfile=/etc/u2f_mappings '
              'origin=pam://dotfiles-local appid=pam://dotfiles-local '
              'userpresence=1 cue')
    targets = [pathlib.Path('/etc/pam.d') / name for name in ('sudo', 'swaylock')]
    originals = {}
    rendered = {}
    for path in targets:
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f'Unexpected PAM file: {path}')
        originals[path] = path.read_text()
        rendered[path] = render(originals[path], username, mode, module)
    test = pathlib.Path('/etc/pam.d/dotfiles-yubikey-test')
    if test.exists() or test.is_symlink():
        raise SystemExit('Test PAM service already exists; refusing to overwrite it.')
    backup = pathlib.Path('/var/backups') / ('dotfiles-pam-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(mode=0o700, parents=True)
    for path in targets:
        shutil.copy2(path, backup / path.name)
    changed = []
    try:
        with mapping.open('x') as f:
            f.write(data + '\n')
        mapping.chmod(0o644)  # public registration, readable by unprivileged swaylock
        with test.open('x') as f:
            f.write(f'auth required {module}\naccount required pam_permit.so\n')
        test.chmod(0o644)
        subprocess.run(['restorecon', str(mapping), str(test)], check=True)
        print('Touch the key again: verifying authentication before changing sudo/Swaylock.', flush=True)
        subprocess.run(['pamtester', test.name, username, 'authenticate'], check=True)
        for path in targets:
            # A failed write must restore this file too.
            changed.append(path)
            path.write_text(rendered[path])
        print(f'PAM originals saved in {backup}')
    except BaseException:
        for path in changed:
            shutil.copy2(backup / path.name, path)
        mapping.unlink(missing_ok=True)
        raise
    finally:
        test.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
