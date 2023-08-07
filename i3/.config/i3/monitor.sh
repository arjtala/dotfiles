FOUND=$(xrandr | grep connected | grep -v disconnected | grep -v eDP | /usr/bin/awk '{print $1}')
export MONITOR=$FOUND
echo "Monitor ${MONITOR}"
