#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

ATHAN=$("$HOME/.cargo/bin/athan" 2>/dev/null)

if [ -n "$ATHAN" ]; then
  sketchybar --set "$NAME" label="$ATHAN"
else
  sketchybar --set "$NAME" label=""
fi
