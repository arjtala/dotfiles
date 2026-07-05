#!/bin/sh

source "$CONFIG_DIR/colors.sh"

# Check Cisco Secure Client first, then system VPNs
CISCO=$(/opt/cisco/secureclient/bin/vpn state 2>/dev/null | grep ">> state: Connected" | head -1)

if [ -n "$CISCO" ]; then
  sketchybar --set "$NAME" icon="󰦝" label.drawing=off icon.color=$BR_GREEN
else
  # Fallback: check macOS native VPNs (NordVPN, etc.)
  VPN=$(scutil --nc list 2>/dev/null | grep "Connected" | head -1)
  if [ -n "$VPN" ]; then
    sketchybar --set "$NAME" icon="󰦝" label.drawing=off icon.color=$BR_GREEN
  else
    sketchybar --set "$NAME" icon="󰦞" label.drawing=off icon.color=$BR_RED
  fi
fi
