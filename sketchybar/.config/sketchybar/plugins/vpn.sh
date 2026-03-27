#!/bin/sh

source "$CONFIG_DIR/colors.sh"

# Check Cisco Secure Client first, then system VPNs
CISCO=$(/opt/cisco/secureclient/bin/vpn state 2>/dev/null | grep ">> state: Connected" | head -1)

if [ -n "$CISCO" ]; then
  LABEL=$(/opt/cisco/secureclient/bin/vpn state 2>/dev/null | grep ">> notice:" | sed 's/.*Connected to //' | sed 's/\.$//' | head -1)
  [ -z "$LABEL" ] && LABEL="Cisco"
  sketchybar --set "$NAME" icon="󰦝" label="$LABEL" icon.color=$BR_GREEN label.color=$BR_GREEN
else
  # Fallback: check macOS native VPNs (NordVPN, etc.)
  VPN=$(scutil --nc list 2>/dev/null | grep "Connected" | sed 's/.*"\(.*\)".*/\1/' | head -1)
  if [ -n "$VPN" ]; then
    sketchybar --set "$NAME" icon="󰦝" label="$VPN" icon.color=$BR_GREEN label.color=$BR_GREEN
  else
    sketchybar --set "$NAME" icon="󰦞" label="Off" icon.color=$BR_RED label.color=$BR_RED
  fi
fi
