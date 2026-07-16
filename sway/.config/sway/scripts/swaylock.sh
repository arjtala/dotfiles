#!/bin/bash
pgrep -u "$UID" -x swaylock >/dev/null && exit 0
wallpapers="$HOME/.wallpapers"
swaylock -e -f -i "$wallpapers/lock1.jpg"
