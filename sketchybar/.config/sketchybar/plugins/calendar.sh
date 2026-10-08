#!/usr/bin/env bash

source "$CONFIG_DIR/colors.sh"

# Character-aware ${title:0:N} truncation for non-ASCII titles.
export LC_ALL=en_US.UTF-8

# ── Upcoming calendar events (Eames-style) ─────────────────────────────────
# The bar shows the current or next event; clicking it pops up the rest of
# today. Clicking an event opens its meeting link, or Calendar if it has none.
#
# Reading events needs Calendars authorization, which TCC only grants to a
# bundled app, so events come from calendar.app (see helpers/). It must be
# launched via `open` so TCC attributes it to the bundle; it writes today's
# remaining events to a cache file that we read here. Relative times are
# recomputed from the cache every tick; the helper itself is throttled.
CAL_APP="$CONFIG_DIR/helpers/calendar.app"
CAL_CACHE="$HOME/.cache/sketchybar-calendar"
CAL_MAX_AGE=300   # seconds
SOON=600          # seconds; prefer and highlight an event starting this soon
# Max label chars in the bar. This item is the innermost on the right, so it
# grows leftward into the notch; 23 chars (~7.8pt each in JetBrains Mono 13pt)
# keeps it clear on the built-in display with a char of slack for the CPU
# label widening. Lower it if it creeps under again.
LABEL_MAX=23

if [ "$SENDER" = "mouse.exited.global" ]; then
  sketchybar --set "$NAME" popup.drawing=off
  exit 0
fi

refresh_events() {
  [ -d "$CAL_APP" ] || return
  now=$(date +%s)
  mtime=$(stat -f %m "$CAL_CACHE" 2>/dev/null || echo 0)
  # Refresh on wake/reload, when the cache is missing, or when stale.
  if [ "$SENDER" = "system_woke" ] || [ "$SENDER" = "forced" ] \
     || [ ! -f "$CAL_CACHE" ] || [ $((now - mtime)) -ge "$CAL_MAX_AGE" ]; then
    open -g "$CAL_APP" 2>/dev/null   # async; updates cache for the next tick
  fi
}

# 300 -> "5m", 3900 -> "1h 5m", 7200 -> "2h" (rounded up to the minute)
duration() {
  local m=$(( ($1 + 59) / 60 ))
  if [ "$m" -lt 60 ]; then
    echo "${m}m"
  elif [ $((m % 60)) -eq 0 ]; then
    echo "$((m / 60))h"
  else
    echo "$((m / 60))h $((m % 60))m"
  fi
}

# fit TITLE SUFFIX — "TITLE SUFFIX" in at most LABEL_MAX chars, shortening
# the title (never the time) to make room.
fit() {
  local room=$(( LABEL_MAX - ${#2} - 1 ))
  local title=$1
  if [ "${#title}" -gt "$room" ]; then title="${title:0:$((room - 1))}…"; fi
  echo "$title $2"
}

refresh_events
now=$(date +%s)

ongoing="" upcoming="" upcoming_start=0
args=(--remove "/$NAME\.event\..*/")
i=0

if [ -f "$CAL_CACHE" ]; then
  while IFS=$'\t' read -r start end title url; do
    [ -n "$start" ] && [ "$end" -gt "$now" ] || continue

    if [ "$start" -le "$now" ]; then
      [ -z "$ongoing" ] && ongoing=$(fit "$title" "· $(duration $((end - now))) left")
      color=$BR_YELLOW
    else
      if [ -z "$upcoming" ]; then
        upcoming=$(fit "$title" "in $(duration $((start - now)))")
        upcoming_start=$start
      fi
      color=$FG
    fi

    if [ -n "$url" ]; then
      click="open $(printf '%q' "$url")"
      link="  "
    else
      click="open -a Calendar"
      link=""
    fi

    item="$NAME.event.$i"
    args+=(--add item "$item" "popup.$NAME" \
           --set "$item" \
             icon="$(date -r "$start" +%H:%M)" \
             icon.color=$FG2 \
             label="$title$link" \
             label.color=$color \
             click_script="$click; sketchybar --set $NAME popup.drawing=off")
    i=$((i + 1))
  done < "$CAL_CACHE"
fi

# Show what's on now, unless the next event is about to start.
color=$FG
if [ -n "$upcoming" ] && { [ -z "$ongoing" ] || [ $((upcoming_start - now)) -le "$SOON" ]; }; then
  label=$upcoming
  [ $((upcoming_start - now)) -le "$SOON" ] && color=$BR_ORANGE
else
  label=$ongoing
  color=$BR_YELLOW
fi

if [ -n "$label" ]; then
  args+=(--set "$NAME" drawing=on label="$label" icon.color=$color label.color=$color)
else
  args+=(--set "$NAME" drawing=off popup.drawing=off)
fi

sketchybar "${args[@]}" >/dev/null 2>&1
