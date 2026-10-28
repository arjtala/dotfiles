#!/usr/bin/env bash
#
# Bootstrap a Fedora machine for this sway config:
#   - installs the packages from sway/README.md
#   - installs ghostty from COPR (not in Fedora repos)
#   - builds + installs way-shell from source (provides way-sh)
#   - registers a sway session entry (with --unsupported-gpu on NVIDIA)
#
# Safe to re-run. Run as your normal user; it sudos where needed.
# NOTE: deploying the dotfiles themselves (symlinking ~/.config/sway, ~/.config/waybar,
# ~/.config/environment.d, …) is separate — see the repo README.

set -euo pipefail

command -v dnf >/dev/null || { echo "This script is for Fedora (dnf not found)." >&2; exit 1; }
[ "$(id -u)" -ne 0 ] || { echo "Run as your normal user; it will sudo when needed." >&2; exit 1; }

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }

# 1. Packages (mirrors the Dependencies table in sway/README.md) ---------------
log "Installing packages from the Fedora repos"
# Notes: `mako` is the notification daemon; `libnotify` provides `notify-send` (used by the
# OSD/screenshot/recorder scripts). `pulseaudio-utils` provides `pactl` (volume/mute keys)
# and `light` drives the brightness keys — both referenced by keybindings.conf. matugen is
# handled separately below (not carried by every Fedora release). --skip-unavailable
# tolerates remaining repo/version gaps.
sudo dnf install -y --skip-unavailable \
  sway swaybg swaylock swayidle sway-systemd \
  waybar mako libnotify gammastep wlogout jq htop pavucontrol \
  xdg-desktop-portal xdg-desktop-portal-wlr xdg-desktop-portal-gtk \
  rofi grimshot grim slurp wf-recorder \
  wl-clipboard clipman \
  mate-polkit network-manager-applet blueman bind-utils net-tools \
  playerctl pulseaudio-utils light \
  pipewire wireplumber \
  python3-i3ipc Thunar \
  fcitx5 fcitx5-configtool \
  adw-gtk3-theme papirus-icon-theme \
  qgnomeplatform-qt6 qgnomeplatform-qt5 qt6-qtwayland qt5-qtwayland

# Register the login entry before optional installs/builds can fail. This can also
# be run independently on a machine whose packages are already installed.
bash "$(dirname "$0")/../scripts/sway-session-setup"

log "Installing desktop fonts"
sudo dnf install -y fontconfig curl tar xz rsms-inter-vf-fonts
bash "$(dirname "$0")/../scripts/install-sway-fonts"

# matugen (Super+t wallpaper selector) — in Fedora repos only on recent releases (absent
# on e.g. F42), so handle it on its own: try the repo, then cargo, else leave a note.
if command -v matugen >/dev/null; then
  log "matugen already installed — skipping"
else
  log "Installing matugen (wallpaper selector)"
  sudo dnf install -y --skip-unavailable matugen || true
  if ! command -v matugen >/dev/null; then
    if command -v cargo >/dev/null; then
      # --root ~/.local so the binary lands in ~/.local/bin, which environment.d/90-sway.conf
      # adds to the session PATH (cargo's default ~/.cargo/bin is not on a clean session PATH).
      cargo install --root "$HOME/.local" matugen
    else
      echo "  ! matugen not in your repos and cargo is unavailable. Install it later via"
      echo "    'cargo install --root ~/.local matugen' or a prebuilt binary from"
      echo "    https://github.com/InioX/matugen/releases (drop in ~/.local/bin)."
      echo "    Only needed for the Super+t wallpaper selector — the rest of sway works without it."
    fi
  fi
fi

# 2. ghostty (terminal) — not in Fedora repos, packaged on COPR ---------------
if ! command -v ghostty >/dev/null; then
  log "Installing ghostty from COPR (mineiro/ghostty)"
  sudo dnf copr enable -y mineiro/ghostty
  sudo dnf install -y ghostty
else
  log "ghostty already installed — skipping"
fi

# 3. way-shell (provides way-sh) — build from source -------------------------
if ! command -v way-sh >/dev/null; then
  log "Building way-shell from source"
  sudo dnf install -y git gcc make pkgconf-pkg-config glib2-devel \
    libadwaita-devel gtk4-layer-shell-devel upower-devel wireplumber-devel \
    json-glib-devel NetworkManager-libnm-devel pulseaudio-libs-devel \
    wayland-devel wayland-protocols-devel
  build="$(mktemp -d)"; trap 'rm -rf "$build"' EXIT
  # Pinned revision; bump deliberately after testing.
  way_shell_rev=96b7dd9487e19961d28f1efeb745a49740e295f6
  git clone https://github.com/ldelossa/way-shell "$build/way-shell"
  git -C "$build/way-shell" checkout --quiet "$way_shell_rev"
  make -C "$build/way-shell"
  sudo make -C "$build/way-shell" install
  sudo glib-compile-schemas /usr/share/glib-2.0/schemas
else
  log "way-shell already installed — skipping"
fi

log "Checking session readiness"
bash "$(dirname "$0")/../scripts/sway-doctor" || true

log "Done. Deploy the dotfiles symlinks (see repo README), then select Sway (NVIDIA) or Sway at login."
