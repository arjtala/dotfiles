# dotfiles

Personal config for macOS and Linux. Each tool's keybindings live in its own
README:

| Tool | README |
| --- | --- |
| AeroSpace (macOS tiling WM) | [aerospace/README.md](aerospace/README.md) |
| sway (Linux/Wayland tiling WM) | [sway/README.md](sway/README.md) |
| i3 (Linux/X11 tiling WM) | [i3/README.md](i3/README.md) |
| tmux | [tmux/README.md](tmux/README.md) |
| Emacs | [emacs/.config/emacs/README.md](emacs/.config/emacs/README.md) (submodule) |

AeroSpace, sway, and i3 share the same window-management scheme so muscle
memory carries across platforms — see each file for the small deltas.

## Branches

`main` is the personal setup and pins the Emacs submodule's `simplify` branch.
The `meta` branches in both repositories preserve the company workstation
setup separately. The dotfiles `meta` branch tracks the Emacs `meta` branch.

To restore that setup in this checkout:

```sh
git switch meta
git submodule update --init --recursive
git -C emacs/.config/emacs switch meta
```

To return to the personal setup, use `main` and `simplify`, respectively.
Stowed files follow the checked-out branch; restart affected apps afterward.

## New machine setup

```sh
git clone --recurse-submodules git@github.com:arjtala/dotfiles.git ~/dotfiles
cd ~/dotfiles
./setup
```

The recursive clone requires GitHub SSH access because the Emacs submodule is
private. On macOS, install [Homebrew](https://brew.sh) first.

`./setup` is safe to re-run. Run it as your normal user; package steps use
`sudo` where needed. It:

1. Syncs and initializes submodules (Emacs config, tmux plugins), then selects
   Emacs's branch from `.gitmodules` (`simplify` on `main`). Existing Emacs
   checkouts are preserved without pulling or resetting; conflicting local edits
   cause setup to stop. Other submodules use their pinned commits.
2. Installs packages:
   - **macOS:** `brew bundle install` from the [Brewfile](Brewfile).
   - **Fedora:** `stow zsh tmux fzf emacs`, then
     [`sway/setup-fedora.sh`](sway/setup-fedora.sh) for the sway stack.
   - **Arch / other:** nothing — install the deps listed in each README's
     `## Dependencies` section, including GNU Stow.
3. Clones `oh-my-zsh` into `~/.oh-my-zsh` if missing (directly, so its
   installer does not replace `.zshrc`).
4. Links packages into `$HOME` with GNU Stow:
   - **macOS:** `zsh tmux emacs ghostty aerospace sketchybar spotify-player`
   - **Linux:** `zsh tmux emacs ghostty sway waybar rofi way-shell gtk3 gtk4 Thunar`

   Pass package names to link a different set, e.g. `./setup zsh tmux`.
5. **macOS only:** builds any missing SketchyBar helper apps, applies the
   desktop preferences in [`scripts/macos-desktop-setup`](scripts/macos-desktop-setup),
   and starts AeroSpace if it isn't running (it then starts at login and launches
   SketchyBar). Approve AeroSpace under System Settings → Privacy & Security →
   Accessibility on first launch.

### Fedora / NVIDIA recovery

The Sway installer registers **Sway (NVIDIA)** before attempting optional tool
installs and builds. To repair just the login entry without reinstalling packages:

```sh
./scripts/sway-session-setup --nvidia
./scripts/sway-doctor
```

The doctor is read-only and reports missing tools, text-only boot overrides,
NVIDIA DRM settings, and session-entry problems. See the
[Sway recovery guide](sway/README.md#fedora--nvidia-recovery) for boot arguments,
the RTX 5090 driver requirement, and troubleshooting commands.

### SketchyBar helpers (macOS)

The Wi-Fi name and calendar items read their data through small helper apps
(`sketchybar/.config/sketchybar/helpers/`), because macOS only grants
Location and Calendars access to bundled apps. They are built per machine and
not tracked. `./setup` builds missing ones (needs `swiftc`, from
`xcode-select --install`) and then lists them; approve each one's permission
prompt once:

```sh
open -W ~/.config/sketchybar/helpers/ssid.app       # Location
open -W ~/.config/sketchybar/helpers/calendar.app   # Calendars
sketchybar --reload
```

To rebuild after editing a helper, run
`sh ~/.config/sketchybar/helpers/build.sh <ssid|calendar>`. Rebuild only the
one you changed: rebuilding re-signs the app, so macOS may ask to approve it
again.

### SketchyBar popups (macOS)

Click the clock for a month calendar, or athan for today's prayer times, as in
Waybar (`waybar/README.md`). Clicking an item again closes its popup, clicking
the other switches, and clicking away closes it. The `‹` and `›` either side
of the calendar's title change month, and clicking the title returns to today. A popup
row has one label colour, so today's number is drawn in red as the row's icon.

`plugins/popup.py` fills both in, using SketchyBar's own popups, so nothing
else runs and no permission is needed. The prayer rules match the Waybar
popup, from `~/.cargo/bin/athan --all --json`; the open popup refreshes with
the athan item each minute. Tests:
`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s sketchybar/tests`.

The Now Playing item shows what macOS is playing, from any app — Podcasts,
Music, Safari, spotify_player — with its title and elapsed/duration; click it
for the whole title, the artist or show, a progress bar and the controls. For a
podcast, back and forward skip fifteen seconds; otherwise they change track. It
reads macOS's Now Playing with
[media-control](https://github.com/ungive/media-control) (`brew install
media-control`), whose stream reports every change, so nothing polls. The Emacs
mode line shows the same, from `my-nowplaying.el`. spotify_player reports to Now
Playing because its config, the `spotify-player` package, turns on
`enable_media_control`.

The Tokens item shows Apple Claude Code's spend meter, as Claude Code's status
line does: today's spend and the share of the budget, going from green through
yellow and orange to red as it runs down (at 50, 75 and 90%). It is drawn only
while a Claude Code session is running and hidden otherwise. Click it for the
tokens, calls, rate limit, when the budget resets and the model that cost most.
`plugins/tokens.py` finds each session's proxy from
`~/.claude/apple/logs/acc-port-<port>.pid`, checks that the process is alive,
and reads `GET /api/quota` from it on loopback, so nothing is written to
`~/.claude`. The proxies can differ by a few dollars, so it shows the largest.
It depends on those two details of Apple Claude Code; if an update changes
them, `plugins/tokens.py status` shows what was found.

### YubiKey for sudo and Swaylock (Fedora)

Run in a local terminal as your normal user, with the key plugged in:

```sh
./scripts/setup-yubikey passwordless
# Alternatively, require both the key and your password:
# ./scripts/setup-yubikey two-factor
```

The script installs Fedora's FIDO PAM tools, registers the key, and requires a
second touch to test it before changing `sudo` and `swaylock`. Other users keep
their existing policy. `passwordless` allows touch instead of a password, with
the original password authentication as fallback; `two-factor` requires both.
Existing key mappings or YubiKey PAM rules cause the helper to stop for review.
It uses a fixed `pam://dotfiles-local` origin so hostname changes do not break it.

Original PAM files are saved under `/var/backups/dotfiles-pam-TIMESTAMP/`.
Test `sudo -k; sudo true` in another terminal before testing the lock screen.
For touch-only Swaylock, press Enter, then touch the key; the helper removes
Swaylock's ignore-empty-password flag. Unplug the key to use password fallback.
GNOME/GDM authentication is not modified. To restore the previous policy, copy
the saved `sudo` and `swaylock` files back into `/etc/pam.d/` with sudo.

To skip the physical key for sudo in SSH sessions, after enrollment run:

```sh
sudo python3 -I scripts/yubikey-ssh.py --install
```

This uses local Unix-password authentication for SSH, and leaves local sudo,
Swaylock, and SSH login authentication unchanged. The helper uses systemd's
process-session metadata (`Remote=yes`, service `sshd` or `tailscaled`), not spoofable SSH
environment variables. If detection fails, the existing YubiKey rule applies.
A tmux server retains the session where it started; use a fresh SSH shell to
test, or start a separate tmux server inside SSH. Test `sudo -k; sudo true`
both locally and over SSH. Backups are in `/var/backups/dotfiles-yubikey-ssh-*/`;
restore the saved `sudo` file to `/etc/pam.d/sudo` to undo the skip.
The remote branch bypasses both the custom key rule and authselect's shared
`pam_u2f` rule. It retains PAM environment setup, authentication failure delay,
and the existing account/session checks; a wrong password fails immediately.
Installation validates this machine's local-password profile and refuses
unrecognized authentication policy. Re-review it if that policy changes.

### Stow notes

Emacs uses `~/.config/emacs` only when the legacy `~/.emacs`, `~/.emacs.el`, and
`~/.emacs.d` paths are absent. Even a cache-only `.emacs.d` takes precedence.
Close Emacs and rename any legacy paths to backups before restarting; setup
warns about them but does not move your existing files automatically. To verify
in Emacs, evaluate `user-init-file` and `user-emacs-directory` with `M-:`.
For an explicit one-off launch, use `emacs --init-directory="$HOME/.config/emacs"`.

The repository's `.stowrc` supplies common ignore rules when Stow traverses
package directories. Stow refuses to replace existing real files; `./setup`
stops with Stow's conflict list, so move those files aside and re-run. Stow may
fold an entire source directory into one symlink, in which case files already
inside it remain visible. To link packages by hand, use
`stow --target="$HOME" --restow <packages...>` from `~/dotfiles`.

tmux plugins are included in the recursive submodule checkout; start tmux or
reload `.tmux.conf` after linking the package. See
[tmux/README.md](tmux/README.md#plugin-management) before updating plugins.

The legacy Vim config uses Vundle, which is not a tracked submodule. To use it:

```sh
git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim
vim +PluginInstall +qall
```
