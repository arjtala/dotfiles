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

## Display scaling

Find connected output names with `swaymsg -t get_outputs`. For example, to make
the UI 150% on this workstation's 4K monitor:

```sh
swaymsg output HDMI-A-2 scale 1.5
```

Use `1` for 100%, `1.25` for 125%, or `2` for 200%. This applies immediately;
to persist it, add `output HDMI-A-2 scale 1.5` to `~/.config/sway/config` and
reload with Super+Shift+r. The current `output * scale 1.5` applies to every
output. Higher scale makes UI elements larger; fractional scales
may make some XWayland apps look softer.

## Dependencies

Linux / Wayland only. Package names verified on **Fedora**; Arch is best-effort.

On Fedora, run [`setup-fedora.sh`](setup-fedora.sh) to install most of this automatically
(packages + ghostty COPR + way-shell build + sway session entry). matugen is best-effort: if
it's absent from your repos and `cargo` is unavailable, the script skips it and the `Super+t`
wallpaper selector needs a manual matugen install (see notes below). Or install manually:

| Needed for | Fedora (dnf) | Arch (pacman) |
| --- | --- | --- |
| sway itself | `sway swaybg` | `sway swaybg` |
| lock / idle | `swaylock swayidle` | `swaylock swayidle` |
| portals + session¹ | `sway-systemd xdg-desktop-portal xdg-desktop-portal-wlr xdg-desktop-portal-gtk` | `xdg-desktop-portal xdg-desktop-portal-wlr xdg-desktop-portal-gtk` |
| notifications³ | `mako libnotify` | `mako libnotify` |
| night light | `gammastep` | `gammastep` |
| status bar | `waybar` | `waybar` |
| status scripts | `jq bind-utils net-tools` | `jq bind net-tools` |
| status actions | `htop pavucontrol blueman` | `htop pavucontrol blueman` |
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
| brightness | `light` | `light` |
| audio + `pactl` | `pipewire wireplumber pulseaudio-utils` | `pipewire wireplumber libpulse` |
| autotiling | `python3-i3ipc` | `python-i3ipc` |
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

³ `mako` is the notification daemon; `libnotify` provides `notify-send`, which the OSD /
screenshot / recorder scripts use to post notifications (the volume/brightness OSD updates
in place via the `x-canonical-private-synchronous` hint).

### Not packaged / per-machine

- **matugen** (`Super+t` wallpaper selector): in Fedora repos only on recent releases
  (absent on e.g. F42). `setup-fedora.sh` tries the repo, then `cargo install --root ~/.local matugen`;
  otherwise grab a prebuilt binary from <https://github.com/InioX/matugen/releases>.
- **way-shell** (`way-sh` workspace switcher): build from source —
  <https://github.com/ldelossa/way-shell> (`make && sudo make install`, then
  `glib-compile-schemas /usr/share/glib-2.0/schemas`).
- **NVIDIA**: run `../scripts/sway-session-setup --nvidia` to register **Sway (NVIDIA)**, and
  `environment.d/90-sway.conf` carries the wlroots/NVIDIA vars (`GBM_BACKEND=nvidia-drm`, …).
  Do **not** set `WLR_DRM_NO_MODIFIERS` on the open driver — it blanks the display.
- **Cursor** `Bibata-Modern-Classic` (set in `config`) isn't in Fedora repos — install
  separately or change it.

Keybindings reference `way-sh`, `$screen-recorder`, `$launcher`, `$screenshot` — defined in
`apps.conf`; adjust to your installed binaries.

### Fonts and Rofi

All Rofi themes use **JetBrainsMono Nerd Font**, also the first font in Waybar's
font stack. The launcher inherits its font and Papirus-Dark icons from
`rofi/config.rasi` instead of overriding them with Hack. Install fonts independently:

```sh
# From the repository root; downloads a pinned, checksum-verified Nerd Fonts release:
./scripts/install-sway-fonts
stow --target="$HOME" --restow rofi
# Sway's GTK interface font (Fedora):
sudo dnf install rsms-inter-vf-fonts
```

`setup-fedora.sh` runs both steps automatically. The Nerd Font is installed under
`~/.local/share/fonts` (or `$XDG_DATA_HOME/fonts`) and includes the icon glyphs used
by Waybar. Papirus-Dark application icons come from `papirus-icon-theme`, not the
font. The Rofi themes and their `colors.rasi` imports are tracked in this repo.
Reopen Rofi after installation; reload Sway to pick up launcher-command changes
and restart Waybar to refresh its font cache. Bibata remains a separate optional
cursor installation; `sway-doctor` reports it when absent.

## Fedora / NVIDIA recovery

Run these from the repository root. Registering the session is independent of the
package installer, so a failed optional build doesn't require repeating setup:

```sh
./scripts/sway-session-setup --nvidia
./scripts/sway-doctor
```

The session helper installs `/usr/share/wayland-sessions/sway-nvidia.desktop`,
leaving the distro's `sway.desktop` alone. Select **Sway (NVIDIA)** at GDM's gear
menu. It launches `sway --unsupported-gpu`; the flag belongs in the session launch
command, not in the Sway config. The helper is safe to rerun.

### RTX 5090 and boot settings

The RTX 5090 (Blackwell) requires NVIDIA's **open kernel modules**, together with
the matching NVIDIA userspace driver. “Open” here does not mean Nouveau. See
[NVIDIA's kernel-module documentation](https://download.nvidia.com/XFree86/Linux-x86_64/570.144/README/kernel_open.html).
Use the Fedora driver packaging appropriate to your configured repository.
Check `nvidia-smi` before debugging Sway; it should list the GPU.

The boot arguments that recovered this workstation were:

```text
3 nvidia-drm.modeset=1 nvidia-drm.fbdev=1
```

The standalone `3` deliberately boots into text mode. Once logged in, start the
graphical login screen with `sudo systemctl start graphical.target`. For normal
boots, remove `3` and keep the two NVIDIA arguments. To persist this on Fedora
with grubby (changes boot entries, taking effect on subsequent boots):

```sh
sudo grubby --update-kernel=ALL --remove-args="rhgb quiet 3 systemd.unit=multi-user.target nvidia-rtx.modeset nvidia-rtx.fbdev nvidia-drm.modeset=0 nvidia-drm.fbdev=0" --args="nvidia-drm.modeset=1 nvidia-drm.fbdev=1"
systemctl get-default
# Only if the default above is not graphical.target:
sudo systemctl set-default graphical.target
```

Setup does not change boot entries automatically. The doctor inspects the current
boot, so it will continue reporting `3` until you boot without it.

### GNOME works but Sway returns to the login screen

Log out, switch to a TTY with Ctrl+Alt+F3, and run as your normal user (no sudo):

```sh
sway --unsupported-gpu -d > ~/sway.log 2>&1
# After Sway exits:
tail -n 80 ~/sway.log
journalctl -b -u gdm --no-pager -n 80
```

Avoid `WLR_DRM_NO_MODIFIERS=1` and `WLR_DRM_NO_ATOMIC=1` on this workstation;
the former previously broke NVIDIA scan-out. The legacy `sway/environment` file
and `environment.d/90-sway.conf` must agree about these overrides.
