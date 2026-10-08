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

1. Syncs and initializes submodules (Emacs config, tmux plugins).
2. Installs packages:
   - **macOS:** `brew bundle install` from the [Brewfile](Brewfile).
   - **Fedora:** `stow zsh tmux fzf emacs`, then
     [`sway/setup-fedora.sh`](sway/setup-fedora.sh) for the sway stack.
   - **Arch / other:** nothing — install the deps listed in each README's
     `## Dependencies` section, including GNU Stow.
3. Clones `oh-my-zsh` into `~/.oh-my-zsh` if missing (directly, so its
   installer does not replace `.zshrc`).
4. Links packages into `$HOME` with GNU Stow:
   - **macOS:** `zsh tmux emacs ghostty aerospace sketchybar`
   - **Linux:** `zsh tmux emacs ghostty sway waybar rofi way-shell gtk3 gtk4 Thunar`

   Pass package names to link a different set, e.g. `./setup zsh tmux`.
5. **macOS only:** builds any missing SketchyBar helper apps, applies the
   desktop preferences in [`scripts/macos-desktop-setup`](scripts/macos-desktop-setup),
   and starts AeroSpace if it isn't running (it then starts at login and launches
   SketchyBar). Approve AeroSpace under System Settings → Privacy & Security →
   Accessibility on first launch.

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

### Stow notes

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
