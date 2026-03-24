#!/bin/sh

# Only show the focused workspace; hide all others.

source "$CONFIG_DIR/colors.sh"

SID="$1"

if [ "$SID" = "$FOCUSED_WORKSPACE" ] || [ "$SID" = "$AEROSPACE_FOCUSED_WORKSPACE" ]; then
  sketchybar --set "$NAME" icon.color=$BR_YELLOW drawing=on
else
  sketchybar --set "$NAME" drawing=off
fi
