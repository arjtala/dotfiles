#!/bin/sh

# The month calendar popup (plugins/popup.py) closes when the pointer leaves,
# and its month arrows with it.
if [ "$SENDER" = "mouse.exited.global" ]; then
  sketchybar --set "$NAME" popup.drawing=off
  sketchybar --set "$NAME.p.title" popup.drawing=off 2>/dev/null
  exit 0
fi

sketchybar --set "$NAME" label="$(date "+%a, %d %b %Y    %H:%M")"
