export MONITOR=$(xrandr | grep connected | grep -v disconnected | grep -v eDP1 | /usr/bin/awk '{print $1}')
