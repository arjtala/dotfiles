# AeroSpace keybindings

Tiling WM for macOS. This config mirrors the sway/i3 scheme: `Cmd` plays the
role of i3's `$super`, except on keys that macOS reserves for system
shortcuts (`v`/`z`/`x`/`a`/`Space`/`r`), which use `Cmd+Ctrl` instead.
`Option` is left free for Emacs `Meta`.

See also: [sway/README.md](../sway/README.md), [i3/README.md](../i3/README.md).

## Focus

| Key | Action |
| --- | --- |
| `Cmd + ← / ↓ / ↑ / →` | Focus window in that direction |
| `Cmd + /` | Previous workspace (back-and-forth) |

## Move windows

| Key | Action |
| --- | --- |
| `Cmd + Shift + ← / ↓ / ↑ / →` | Move focused window in that direction |

These bindings override macOS's "select to start/end of line/document"
shortcuts system-wide. `Cmd + Shift + h / j / k / l` are unbound.

## Workspaces

| Key | Action |
| --- | --- |
| `Cmd + 1 … 9 / 0` | Switch to workspace 1-10 |
| `Cmd + Shift + 1 … 9 / 0` | Move window to workspace 1-10 and follow |
| `Cmd + Ctrl + → / ←` | Next / previous workspace |
| `Cmd + Shift + Ctrl + → / ←` | Move workspace to next / previous monitor |

## Layout

| Key | Action |
| --- | --- |
| `Cmd + Ctrl + V` | Split: vertical (join-with down) |
| `Cmd + \` | Split: horizontal (join-with right) |
| `Cmd + Ctrl + Z` | Accordion vertical (= i3/sway "stacking") |
| `Cmd + Ctrl + X` | Accordion horizontal (= i3/sway "tabbed") |
| `Cmd + Ctrl + A` | Toggle tiles layout, horizontal / vertical |
| `Cmd + Shift + F` | Toggle fullscreen |
| `Cmd + Ctrl + Space` | Toggle floating / tiling |
| `Cmd + Ctrl + F` | Flatten workspace tree |

## Resize

| Key | Action |
| --- | --- |
| `Ctrl + Shift + h / j / k / l` | Resize directly (width/height ±50) |
| `Cmd + Ctrl + R` | Enter resize mode (`Esc` / `Enter` to exit) |

## Misc

| Key | Action |
| --- | --- |
| `Cmd + Enter` | New Ghostty window |
| `Cmd + Shift + Q` | Close focused window |
| `Cmd + Shift + R` | Reload AeroSpace config |

## Workspace recovery

`scripts/aerospace-workspace-guard` is started with AeroSpace. It remembers
window placement from AeroSpace's focus events and restores a live window when
the same CGWindowID is detected again on the wrong workspace. This works around
transient macOS Accessibility failures without polling the Accessibility API.

Use `scripts/aerospace-workspace-guard show` to inspect the current boot's
remembered placement. Corrections and reconnects are logged in
`~/.local/state/aerospace/workspace-guard.log`.

## Dependencies

macOS only. See the root [Brewfile](../Brewfile) for a full one-shot:

```sh
brew bundle install --file=~/dotfiles/Brewfile
```

Key packages (subset):

| Needed for | Homebrew |
| --- | --- |
| AeroSpace itself | `cask nikitabobko/tap/aerospace` |
| `Cmd + Enter` → Ghostty | `cask ghostty` |
| Status bar hooks | `sketchybar` (tap: `FelixKratz/formulae`) |
| Bar text and icons | `cask font-jetbrains-mono-nerd-font` |

## Starting on a new Mac

Run `bash ~/dotfiles/scripts/macos-desktop-setup` to apply menu-bar auto-hide
and remap area screenshots to `Ctrl+Shift+4`. These are macOS system preferences,
so Stow alone does not transfer them. If macOS asks, allow the terminal to
control System Events. `Cmd+Shift+4` then remains available for moving a window
to workspace 4. Other screenshot shortcuts are unchanged.

After installing dependencies and stowing `aerospace` and `sketchybar`, open
AeroSpace with `open -a AeroSpace`. Approve its Accessibility permission in
System Settings → Privacy & Security → Accessibility. This config starts
AeroSpace at login and launches SketchyBar and the workspace guard on startup;
a separate SketchyBar Homebrew service is unnecessary.

The guard path assumes this checkout is at `~/dotfiles`. It uses `$HOME` and
finds the AeroSpace CLI through PATH, so it does not depend on your username.

Set System Settings → Menu Bar → Automatically hide and show the menu
bar to **Always** on macOS Tahoe (look under Control Center or Desktop & Dock
on older macOS). If changing `_HIHideMenuBar` with `defaults`, run `killall Dock`
to apply it, then `sketchybar --reload` to refresh the bar's position.
The top gaps assume a hidden menu bar and a notched built-in display.
Keep **Displays have separate Spaces** enabled for SketchyBar. The bar uses
`topmost=window` to sit at the display's top edge without adding a native
menu-bar inset, while allowing the revealed Apple menu bar to appear above it.

`aerospace reload-config` applies config changes, but startup commands require
quitting and reopening AeroSpace. Opening an already running AeroSpace does
not restart it. To check or refresh the bar:

```sh
sketchybar --query bar
sketchybar --reload
```

If the query cannot connect, run `sketchybar` in a terminal to start it and see
errors. Only the focused workspace indicator is shown by this configuration.

Optional widgets:

- To display the Wi-Fi SSID instead of "Wi-Fi", run
  `sh ~/.config/sketchybar/helpers/build.sh`, then
  `open ~/.config/sketchybar/helpers/ssid.app` and approve Location permission.
  Building requires Xcode Command Line Tools (`xcode-select --install`).
- Prayer times require `~/.cargo/bin/athan`; the label stays empty without it.
- `sketchybar-app-font` and Symbols Only Nerd Font are not required by this bar;
  its text and icons use JetBrainsMono Nerd Font.
