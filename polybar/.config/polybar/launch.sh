#!/usr/bin/env sh

MONITOR=$(/usr/bin/xrandr | /usr/bin/grep connected | /usr/bin/grep -v disconnected | /usr/bin/grep -v eDP1 | /usr/bin/awk '{print $1}')
echo "Monitor ${MONITOR}"

DEFAULT_NETWORK_INTERFACE=$(ip route | grep '^default' | awk '{print $5}' | head -n1)
echo "Network interface: ${DEFAULT_NETWORK_INTERFACE}"

# Terminate already running bar instances
killall -q polybar

# Wait until the processes have been shut down
while pgrep -u $UID -x polybar >/dev/null; do sleep 1; done

# Launch bar1 and bar2
/usr/local/bin/polybar -c ${HOME}/.config/polybar/config.ini Bar &
echo "Bars launched..."
