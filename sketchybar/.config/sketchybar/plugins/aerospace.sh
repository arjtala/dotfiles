#!/bin/sh

# Highlights the active AeroSpace workspace.
# Colors match waybar: active=br_yellow, visible=fg2, empty=bg2

source "$CONFIG_DIR/colors.sh"

# The workspace ID this item represents (passed as $1 at config time)
SID="$1"

if [ "$SID" = "$FOCUSED_WORKSPACE" ] || [ "$SID" = "$AEROSPACE_FOCUSED_WORKSPACE" ]; then
  sketchybar --set "$NAME" icon.color=$BR_YELLOW
elif aerospace list-windows --workspace "$SID" 2>/dev/null | grep -q .; then
  sketchybar --set "$NAME" icon.color=$FG2
else
  sketchybar --set "$NAME" icon.color=$BG2
fi
