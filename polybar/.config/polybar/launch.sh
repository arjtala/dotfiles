#!/usr/bin/env sh
FOUND=$(polybar -m|tail -1|sed -e 's/:.*$//g')
export MONITOR=${1:FOUND}
echo "Found monitor ${MONITOR}"

# Terminate already running bar instances
killall -q polybar

# Wait until the processes have been shut down
while pgrep -u $UID -x polybar >/dev/null; do sleep 1; done

# Launch bar1 and bar2
polybar -c ${HOME}/.config/polybar/config.ini Bar &

echo "Bars launched..."
