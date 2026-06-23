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
| `Super + q` | Power menu (wlogout) |
| `Super + Shift + n` | File manager (Thunar) |
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

## Dependencies

Linux / Wayland only. Package names verified on **Fedora**; Arch is best-effort.

| Needed for | Fedora (dnf) | Arch (pacman) |
| --- | --- | --- |
| sway itself | `sway swaybg` | `sway swaybg` |
| lock / idle | `swaylock swayidle` | `swaylock swayidle` |
| portals + session¹ | `sway-systemd xdg-desktop-portal xdg-desktop-portal-wlr xdg-desktop-portal-gtk` | `xdg-desktop-portal xdg-desktop-portal-wlr xdg-desktop-portal-gtk` |
| notifications | `mako` | `mako` |
| night light | `gammastep` | `gammastep` |
| status bar | `waybar` | `waybar` |
| launcher | `rofi` | `rofi-wayland` |
| logout menu | `wlogout` | `wlogout` |
| terminal² | `ghostty` | `ghostty` |
| file manager | `Thunar` | `thunar` |
| screenshots | `grimshot grim slurp` | `grim slurp` |
| screen recorder | `wf-recorder` | `wf-recorder` |
| clipboard | `wl-clipboard clipman` | `wl-clipboard clipman` |
| polkit agent | `mate-polkit` | `mate-polkit` |
| network applet | `network-manager-applet` | `network-manager-applet` |
| media keys | `playerctl` | `playerctl` |
| brightness | `brightnessctl` (or `light`) | `brightnessctl` |
| audio | `pipewire wireplumber` | `pipewire wireplumber` |
| autotiling | `python3-i3ipc` | `python-i3ipc` |
| wallpaper theming | `matugen` | `matugen` (AUR) |
| input method (opt) | `fcitx5 fcitx5-configtool` | `fcitx5` |
| GTK dark theme | `adw-gtk3-theme` | `adw-gtk3` |
| icons | `papirus-icon-theme` | `papirus-icon-theme` |
| Qt dark + wayland | `qgnomeplatform-qt6 qgnomeplatform-qt5 qt6-qtwayland qt5-qtwayland` | `qt6ct qt6-wayland` |

¹ `sway-systemd` starts `graphical-session.target` via `exec /usr/libexec/sway-systemd/session.sh`
(in `exec.conf`). Without it the XDG portal never comes up — which breaks **dark mode in
libadwaita apps**, screen-sharing, file pickers, and leaves new terminals without
`WAYLAND_DISPLAY` / `SWAYSOCK`.

² ghostty isn't in Fedora's repos:
`sudo dnf copr enable mineiro/ghostty && sudo dnf install ghostty`
(or point `$term` in `apps.conf` at `alacritty` / `kitty` / `foot`).

### Not packaged / per-machine

- **way-shell** (`way-sh` workspace switcher): build from source —
  <https://github.com/ldelossa/way-shell> (`make && sudo make install`, then
  `glib-compile-schemas /usr/share/glib-2.0/schemas`).
- **NVIDIA**: the session entry must launch `sway --unsupported-gpu` (edit `sway.desktop`), and
  `environment.d/90-sway.conf` carries the wlroots/NVIDIA vars (`GBM_BACKEND=nvidia-drm`, …).
  Do **not** set `WLR_DRM_NO_MODIFIERS` on the open driver — it blanks the display.
- **Cursor** `Bibata-Modern-Classic` (set in `config`) isn't in Fedora repos — install
  separately or change it.

Keybindings reference `way-sh`, `$screen-recorder`, `$launcher`, `$screenshot` — defined in
`apps.conf`; adjust to your installed binaries.
