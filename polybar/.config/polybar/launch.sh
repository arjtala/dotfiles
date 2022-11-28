#!/usr/bin/env sh

export MONITOR=$(/usr/bin/xrandr | /usr/bin/grep connected | /usr/bin/grep -v disconnected | /usr/bin/grep -v eDP1 | /usr/bin/awk '{print $1}')
echo "Monitor ${MONITOR}"

export DEFAULT_NETWORK_INTERFACE=$(ip route | /usr/bin/grep -v vpn | /usr/bin/grep '^default' | /usr/bin/awk '{print $5}' | head -n1)
echo "Network interface: ${DEFAULT_NETWORK_INTERFACE}"

IS_DWM=$(pgrep dwm)
IS_I3=$(pgrep i3)
IS_DESKTOP=0
if ! [ -x "$(command -v xbacklight)" ]; then
	IS_DESKTOP=1
fi

if [[ ! -z "$IS_DWM" ]]; then
	BIN="/usr/local/bin/polybar"
	if [[ "$IS_DESKTOP" -eq 1 ]]; then
		BAR="dwmBar";
	else
		BAR="dwmBarLaptop";
	fi
fi
if [[ ! -z "$IS_I3" ]]; then
	BIN="/usr/bin/polybar"
	if [[ "$IS_DESKTOP" -eq 1 ]]; then
		BAR="i3Bar";
	else
		BAR="i3BarLaptop";
	fi
fi
echo $BAR


# Terminate already running bar instances
killall -q polybar

# Wait until the processes have been shut down
while pgrep -u $UID -x polybar >/dev/null; do sleep 1; done

# Launch bar1 and bar2
$BIN -c ${HOME}/.config/polybar/config.ini ${BAR} &
echo "Bars launched..."
