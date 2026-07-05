#!/bin/sh

source "$CONFIG_DIR/colors.sh"

# The default route usually runs through a VPN tunnel (utunN), so detect
# connectivity from the physical interfaces' link status instead of the route.

WIFI_DEV=$(networksetup -listallhardwareports 2>/dev/null \
  | awk '/Wi-Fi/{getline; print $2}' | head -1)
ETH_DEVS=$(networksetup -listallhardwareports 2>/dev/null \
  | awk '/(Ethernet|Thunderbolt Bridge)/{getline; print $2}')

is_up() {
  # $1 = interface; up if link active AND has a non-link-local IPv4
  ifconfig "$1" 2>/dev/null | grep -q "status: active" || return 1
  ifconfig "$1" 2>/dev/null | grep -q "inet "
}

# ── SSID lookup ────────────────────────────────────────────────────────────
# macOS redacts the SSID from every unauthorized tool (even root wdutil), so we
# read it via ssid.app — a Location-authorized helper bundle (see helpers/).
# It must be launched via `open` so TCC attributes it to the bundle; it writes
# the SSID to a cache file that we read here. Refresh is throttled to avoid
# spawning the helper on every tick.
SSID_APP="$CONFIG_DIR/helpers/ssid.app"
SSID_CACHE="$HOME/.cache/sketchybar-ssid"
SSID_MAX_AGE=60   # seconds

refresh_ssid() {
  [ -d "$SSID_APP" ] || return
  now=$(date +%s)
  mtime=$(stat -f %m "$SSID_CACHE" 2>/dev/null || echo 0)
  # Refresh on Wi-Fi change events, when cache is missing/empty, or when stale.
  if [ "$SENDER" = "wifi_change" ] || [ ! -s "$SSID_CACHE" ] \
     || [ $((now - mtime)) -ge "$SSID_MAX_AGE" ]; then
    open -g "$SSID_APP" 2>/dev/null   # async; updates cache for the next tick
  fi
}

if [ -n "$WIFI_DEV" ] && is_up "$WIFI_DEV"; then
  refresh_ssid
  SSID=$(cat "$SSID_CACHE" 2>/dev/null)
  [ -z "$SSID" ] && SSID="Wi-Fi"
  sketchybar --set "$NAME" icon="󰤨" label="$SSID" icon.color=$BR_AQUA label.color=$BR_AQUA

else
  WIRED=""
  for dev in $ETH_DEVS; do
    if is_up "$dev"; then WIRED="$dev"; break; fi
  done

  if [ -n "$WIRED" ]; then
    sketchybar --set "$NAME" icon="󰈀" label="Ethernet" icon.color=$BR_AQUA label.color=$BR_AQUA
  else
    sketchybar --set "$NAME" icon="󰤭" label="Off" icon.color=$BR_RED label.color=$BR_RED
  fi
fi
