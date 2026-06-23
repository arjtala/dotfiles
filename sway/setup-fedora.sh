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
sudo dnf install -y \
  sway swaybg swaylock swayidle sway-systemd \
  waybar mako gammastep wlogout \
  xdg-desktop-portal xdg-desktop-portal-wlr xdg-desktop-portal-gtk \
  rofi grimshot grim slurp wf-recorder \
  wl-clipboard clipman \
  mate-polkit network-manager-applet \
  playerctl brightnessctl \
  pipewire wireplumber \
  python3-i3ipc matugen Thunar \
  fcitx5 fcitx5-configtool \
  adw-gtk3-theme papirus-icon-theme \
  qgnomeplatform-qt6 qgnomeplatform-qt5 qt6-qtwayland qt5-qtwayland

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
  git clone --depth 1 https://github.com/ldelossa/way-shell "$build/way-shell"
  make -C "$build/way-shell"
  sudo make -C "$build/way-shell" install
  sudo glib-compile-schemas /usr/share/glib-2.0/schemas
else
  log "way-shell already installed — skipping"
fi

# 4. Sway session entry ------------------------------------------------------
# On NVIDIA, sway refuses to start without --unsupported-gpu. Put the override in
# /usr/local/share (takes precedence over /usr/share and survives package updates).
if lsmod | grep -q '^nvidia' || lspci 2>/dev/null | grep -qi nvidia; then
  log "NVIDIA detected — registering sway session with --unsupported-gpu"
  sudo install -d /usr/local/share/wayland-sessions
  sudo tee /usr/local/share/wayland-sessions/sway.desktop >/dev/null <<'EOF'
[Desktop Entry]
Name=Sway
Comment=An i3-compatible Wayland compositor
Exec=sway --unsupported-gpu
Type=Application
DesktopNames=sway;wlroots
EOF
  if ! grep -qs 'nvidia.drm.modeset=1' /proc/cmdline \
     && ! grep -rqs 'modeset=1' /etc/modprobe.d/*nvidia* 2>/dev/null; then
    echo "  ! nvidia-drm.modeset=1 not detected — enable it (kernel cmdline or modprobe.d) or sway may not start."
  fi
else
  log "No NVIDIA GPU detected — stock sway.desktop is fine (no --unsupported-gpu needed)"
  echo "  Note: environment.d/90-sway.conf carries NVIDIA-specific vars (GBM_BACKEND=nvidia-drm, …);"
  echo "  remove/adjust them on non-NVIDIA hardware or sway may fail to start."
fi

log "Done. Deploy the dotfiles symlinks (see repo README), then log out and pick 'Sway' at the GDM gear menu."
