#!/bin/sh

userresources=$HOME/.Xresources
usermodmap=$HOME/.Xmodmap
sysresources=/etc/X11/xinit/.Xresources
sysmodmap=/etc/X11/xinit/.Xmodmap

# merge in defaults and keymaps
if [ -f $sysresources ]; then
    xrdb -merge $sysresources
fi
if [ -f $sysmodmap ]; then
    xmodmap $sysmodmap
fi
if [ -f "$userresources" ]; then
    xrdb -merge "$userresources"
fi
if [ -f "$usermodmap" ]; then
    xmodmap "$usermodmap"
fi

source ~/.config/i3/monitor.sh
VAR='GNU/Linux is an operating system'
if [[ ($MONITOR == "eDP1") || ($MONITOR == "eDP-1") ]]; then
	xrandr --newmode 1920x1200_60 154 1920 1968 2000 2080 1200 1203 1209 1235 -hsync +vsync
	xrandr --addmode $MONITOR 1920x1200_60
	xrandr --output $MONITOR --mode 1920x1200_60
else
	LAPTOP=$(xrandr | grep connected | grep -v disconnected | grep eDP | /usr/bin/awk '{print $1}')
	xrandr -s 1 --output $MONITOR
	xrandr --output $LAPTOP --same-as DP-2
fi

sh ~/.config/polybar/launch.sh &
sh ~/.config/i3/reset.sh &

# start some nice programs
if [ -d /etc/X11/xinit/xinitrc.d ] ; then
 for f in /etc/X11/xinit/xinitrc.d/?*.sh ; do
  [ -x "$f" ] && . "$f"
 done
 unset f
fi

exec nitrogen --restore &

# ----------
# i3
# ----------
exec i3 --shmlog-size=26214400


# ----------
# dwm
# ----------
# Statusbar loop
# while true ; do xsetroot -name "`date '+%Y-%m-%d %H:%M.%S'` `uptime |sed 's/.*,//'`"; sleep 1 ; done &
# exec dwl
