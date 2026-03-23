#!/bin/sh

CPU=$(top -l 1 -n 0 | grep "CPU usage" | awk '{printf "%2.0f", $3}')
sketchybar --set "$NAME" label="${CPU}%"
