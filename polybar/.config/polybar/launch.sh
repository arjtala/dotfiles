#!/usr/bin/env sh
export MONITOR=$(/usr/bin/xrandr | /usr/bin/grep connected | /usr/bin/grep -v disconnected | /usr/bin/grep -v eDP1 | /usr/bin/awk '{print $1}')
echo "Found monitor ${MONITOR}"

# Terminate already running bar instances
killall -q polybar

# Wait until the processes have been shut down
while pgrep -u $UID -x polybar >/dev/null; do sleep 1; done

# Launch bar1 and bar2
polybar -c ${HOME}/.config/polybar/config.ini Bar &

echo "Bars launched..."
