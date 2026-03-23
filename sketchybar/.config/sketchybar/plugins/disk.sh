#!/bin/sh

# Show free disk space — matches waybar disk module format
FREE=$(df -h / | awk 'NR==2 {print $4}')
sketchybar --set "$NAME" label="${FREE}B"
