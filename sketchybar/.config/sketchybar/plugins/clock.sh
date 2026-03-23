#!/bin/sh

# Format matches waybar: "Mon, 23 Mar 2026   14:30"
sketchybar --set "$NAME" label="$(date '+%a, %d %b %Y   %H:%M')"
