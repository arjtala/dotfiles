#!/bin/bash
wallpapers="$HOME/.wallpapers"
themes="$HOME/.local/share/swaylock/themes"
swaylock --config "$themes/catppuccin/mocha.conf" -e -f -i $wallpapers/lock1.jpg
