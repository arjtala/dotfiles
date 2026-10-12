#!/bin/sh

# The month calendar popup (plugins/popup.py) closes when the pointer leaves.
if [ "$SENDER" = "mouse.exited.global" ]; then
  sketchybar --set "$NAME" popup.drawing=off
  exit 0
fi

sketchybar --set "$NAME" label="$(date "+%a, %d %b %Y    %H:%M")"
