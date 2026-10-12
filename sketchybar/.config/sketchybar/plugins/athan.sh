#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

# The prayer times popup (plugins/popup.py) closes when the pointer leaves.
if [ "$SENDER" = "mouse.exited.global" ]; then
  sketchybar --set "$NAME" popup.drawing=off
  exit 0
fi

ATHAN=$("$HOME/.cargo/bin/athan" 2>/dev/null)

if [ -n "$ATHAN" ]; then
  sketchybar --set "$NAME" label="$ATHAN"
else
  sketchybar --set "$NAME" label=""
fi

# Keep an open popup's highlight and countdown current.
"$CONFIG_DIR/plugins/popup.py" prayers refresh
