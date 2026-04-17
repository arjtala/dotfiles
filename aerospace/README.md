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
| `Cmd + /` | Focus previous workspace (back-and-forth) |

## Move windows

| Key | Action |
| --- | --- |
| `Cmd + Shift + ← / ↓ / ↑ / →` | Move focused window |
| `Cmd + Shift + h / j / k / l` | Move focused window (vi-style) |

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
| `Cmd + Ctrl + Z` | Accordion layout, horizontal |
| `Cmd + Ctrl + X` | Accordion layout, vertical |
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
