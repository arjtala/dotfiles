# sway keybindings

Tiling Wayland compositor for Linux. Mirrors the AeroSpace / i3 scheme —
same mod-key layout so muscle memory carries across machines.

See also: [aerospace/README.md](../aerospace/README.md),
[i3/README.md](../i3/README.md).

`$super` = `Mod4` (the Super / Windows / Cmd key).

## Focus

| Key | Action |
| --- | --- |
| `Super + ← / ↓ / ↑ / →` | Focus window in that direction |
| `Super + Tab` | Swap focus between tiling and floating area |
| `Super + Shift + Tab` | Workspace switcher overlay |
| `Super + o` / `Super + p` | Focus parent / child container |
| `Super + slash` | Focus previous workspace (back-and-forth) |

## Move windows

| Key | Action |
| --- | --- |
| `Super + Shift + ← / ↓ / ↑ / →` | Move focused window |

## Workspaces

| Key | Action |
| --- | --- |
| `Super + 1 … 9` | Switch to workspace 1-9 |
| `Super + Shift + 1 … 9` | Move window to workspace 1-9 |
| `Super + Ctrl + → / ←` | Next / previous workspace |
| `Super + Alt + ScrollUp / ScrollDown` | Cycle workspaces by mouse wheel |

## Layout

| Key | Action |
| --- | --- |
| `Super + v` | Split vertical |
| `Super + h` | Split horizontal |
| `Super + z` | Stacking layout |
| `Super + x` | Tabbed layout |
| `Super + a` | Toggle split layout |
| `Super + Shift + f` | Toggle fullscreen |
| `Super + Space` | Toggle floating / tiling |

## Resize

| Key | Action |
| --- | --- |
| `Shift + Ctrl + h / j / k / l` | Resize window ±5px |
| `Super + r` | Enter resize mode (`Return` / `Esc` to exit) |

## Scratchpad

| Key | Action |
| --- | --- |
| `Super + minus` | Move window to scratchpad |
| `Super + equal` | Show scratchpad |

## Apps

| Key | Action |
| --- | --- |
| `Super + Return` | Terminal |
| `Super + d` | Launcher |
| `Super + c` | Window overview |
| `Super + Shift + f` | File manager (Thunar) |
| `Super + q` | Power menu (wlogout) |
| `Super + t` | Wallpaper selector |
| `Super + y` | Toggle waybar |

## Screenshots and lock

| Key | Action |
| --- | --- |
| `Print` | Screenshot (default tool) |
| `Shift + Print` | Save full-screen PNG to ~/Pictures/Screenshots |
| `Ctrl + Print` | Copy area to clipboard |
| `Super + Shift + s` | Copy area to clipboard (grimshot) |
| `Ctrl + Shift + r` | Screen recorder |
| `Super + Shift + l` | Lock screen (swaylock) |

## Media / brightness

| Key | Action |
| --- | --- |
| `XF86Audio Raise / Lower` | Volume ±10% |
| `XF86AudioMute` | Toggle mute |
| `XF86AudioMicMute` | Toggle mic mute |
| `XF86MonBrightness Up / Down` | Brightness ±5 |
| `XF86Audio Play / Next / Prev` | Media control (playerctl) |

## Modes and misc

| Key | Action |
| --- | --- |
| `Super + Alt + p` | Passthrough mode (release shortcuts to guest VM etc.) |
| `Super + Shift + q` | Kill focused window |
| `Super + F4` | Kill window under cursor |
| `Super + Shift + r` | Reload config |
| `Super + Shift + e` | Exit sway (with confirm dialog) |
