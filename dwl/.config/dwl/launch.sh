#!/bin/sh
# Start dwl as the real compositor from a TTY.

export GBM_BACKEND=nvidia-drm
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export WLR_NO_HARDWARE_CURSORS=1
export XDG_CURRENT_DESKTOP=dwl
export XDG_SESSION_TYPE=wayland

unset DISPLAY
unset WAYLAND_DISPLAY

exec dbus-run-session dwl -s "$HOME/.config/dwl/autostart.sh"
