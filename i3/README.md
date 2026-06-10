# i3 keybindings

Tiling WM for Linux/X11. Mirrors the AeroSpace / sway scheme; this is the
older X11 variant, so some apps and the screenshot/lock tooling differ.

See also: [sway/README.md](../sway/README.md),
[aerospace/README.md](../aerospace/README.md).

`$super` = `Mod4` (Super / Windows key). `$alt` = `Mod1`.

## Focus

| Key | Action |
| --- | --- |
| `Super + ← / ↓ / ↑ / →` | Focus window in that direction |
| `Super + Shift + Space` | Swap focus tiling ↔ floating |

## Move windows

| Key | Action |
| --- | --- |
| `Super + Shift + ← / ↓ / ↑ / →` | Move focused window |
| `Super + Shift + p` | Move workspace to output to the right |

## Workspaces

| Key | Action |
| --- | --- |
| `Super + 1 … 9` | Switch to workspace 1-9 |
| `Super + Shift + 1 … 9` | Move window to workspace 1-9 |
| `Alt + Ctrl + → / ←` | Next / previous workspace |

## Layout

| Key | Action |
| --- | --- |
| `Super + v` | Split vertical |
| `Super + h` | Split horizontal |
| `Super + s` | Toggle split layout |
| `Super + Shift + f` | Toggle fullscreen |
| `Super + Space` | Toggle floating / tiling |

## Resize

| Key | Action |
| --- | --- |
| `Super + r` | Enter resize mode (`Return` to exit) |

## Apps

| Key | Action |
| --- | --- |
| `Super + Return` | Terminal (Alacritty) |
| `Super + Shift + Return` | Alacritty + ranger |
| `Super + d` | rofi run launcher |
| `Super + c` | rofi window switcher |
| `Super + Shift + w` | Chrome |
| `Super + Shift + g` | Emacs |

> `Super + Shift + f` → fullscreen (see Layout). The Thunar binding earlier
> in the config is shadowed by the later fullscreen binding (last write wins).

## System

| Key | Action |
| --- | --- |
| `Print` | Screenshot (scrot → viewnior) |
| `Super + Shift + l` | Lock (betterlockscreen) |
| `Super + Shift + q` / `Alt + F4` | Kill focused window |
| `Super + Shift + r` | Restart i3 in place |
| `Super + q` | Exit i3 (with confirm) |

## Media / brightness

| Key | Action |
| --- | --- |
| `XF86Audio Raise / Lower / Mute` | Volume control (amixer) |
| `XF86Audio Next / Prev / Play / Stop` | Media control (mpc) |
| `XF86MonBrightness Up / Down` | Brightness ±20 (xbacklight) |

## Dependencies

Linux / X11 only.

| Needed for | Fedora (dnf) | Arch (pacman) |
| --- | --- | --- |
| i3 itself | `i3` | `i3-wm` |
| terminal | `alacritty` | `alacritty` |
| launcher / window switcher | `rofi` | `rofi` |
| file manager | `thunar` | `thunar` |
| ranger (`Super+Shift+Return`) | `ranger` | `ranger` |
| lock screen | `betterlockscreen` (COPR) | `betterlockscreen` (AUR) |
| auto-lock on suspend | `xss-lock` | `xss-lock` |
| network tray | `NetworkManager-gnome` | `network-manager-applet` |
| screenshots | `scrot` | `scrot` |
| screenshot viewer | `viewnior` | `viewnior` |
| brightness | `xbacklight` | `xorg-xbacklight` |
| volume | `alsa-utils` | `alsa-utils` |
| music control | `mpd mpc` | `mpd mpc` |
| polybar | `polybar` | `polybar` |
| wallpaper | `feh` | `feh` |
