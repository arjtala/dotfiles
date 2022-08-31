#!/bin/zsh

wal -R

feh --bg-fill ~/.wallpapers/inuse.png

killall -q compton
while pgrep -u $UID -x compton >/dev/null; do sleep 1; done
compton --config /dev/null --backend glx &
echo "Compton relaunched..."
