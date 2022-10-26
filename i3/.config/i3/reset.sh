#!/bin/zsh

feh --bg-fill ~/.wallpapers/inuse.png
wal -R
killall -q compton
while pgrep -u $UID -x compton >/dev/null; do sleep 1; done
compton --config /dev/null --backend glx &
echo "Compton relaunched..."
