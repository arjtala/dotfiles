#!/bin/sh
# dwl autostart script
# Launch with: dwl -s '~/.config/dwl/autostart.sh'

# Client environment
export MOZ_ENABLE_WAYLAND=1
export QT_QPA_PLATFORM=wayland

# D-Bus
dbus-update-activation-environment --all &
dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP &

# GTK/QT theming
gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark' &
gsettings set org.gnome.desktop.interface gtk-theme 'adw-gtk3-dark' &
gsettings set org.gnome.desktop.interface icon-theme 'Papirus-Dark' &
gsettings set org.gnome.desktop.interface cursor-theme 'Bibata-Modern-Classic' &
gsettings set org.gnome.desktop.interface font-name 'Inter Variable 11' &

# Services
/usr/libexec/polkit-mate-authentication-agent-1 &
/usr/libexec/xdg-desktop-portal &
/usr/libexec/xdg-desktop-portal-gtk &
pkill dunst; dunst &
fcitx5 &
nm-applet --indicator &
wl-paste -p -t text --watch clipman store -P --histpath="$HOME/.local/share/clipman-primary.json" &
wl-paste -t text --watch clipman store &

# Wallpaper
swaybg -i ~/.wallpapers/inuse.png -m fill -o '*' &

# Bar
waybar -c ~/.config/dwl/waybar/config -s ~/.config/dwl/waybar/style.css >"$XDG_RUNTIME_DIR/dwl-waybar.log" 2>&1 &

# Close stdin so we don't block dwl's status pipe
exec <&-
