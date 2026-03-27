#!/bin/sh

source "$CONFIG_DIR/colors.sh"

# Prefer IPv6 (non-link-local), fall back to IPv4
IP=$(ifconfig en0 2>/dev/null | grep "inet6" | grep -v "fe80" | awk '{print $2}' | head -1)
[ -z "$IP" ] && IP=$(ipconfig getifaddr en0 2>/dev/null)

WIFI=$(ipconfig getsummary en0 2>/dev/null | awk -F' : ' '/^ *SSID/{print $2}' | head -1)

if [ -n "$WIFI" ] && [ "$WIFI" != "<redacted>" ]; then
  sketchybar --set "$NAME" icon="󰤨" label="${IP:-No IP}" icon.color=$BR_AQUA label.color=$BR_AQUA
elif [ -n "$IP" ]; then
  # Connected but SSID redacted or on ethernet
  ICON="󰤨"
  ipconfig getsummary en0 2>/dev/null | grep -q "SSID" || ICON="󰈀"
  sketchybar --set "$NAME" icon="$ICON" label="$IP" icon.color=$BR_AQUA label.color=$BR_AQUA
else
  sketchybar --set "$NAME" icon="󰤭" label="Off" icon.color=$BR_RED label.color=$BR_RED
fi
