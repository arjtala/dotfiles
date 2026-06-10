#!/bin/sh

TOTAL=$(sysctl -n hw.memsize)
TOTAL_MB=$((TOTAL / 1024 / 1024))

# Get pages from vm_stat and convert to MB (page size = 4096)
STATS=$(vm_stat)
ACTIVE=$(echo "$STATS" | awk '/Pages active/ {gsub(/\./,"",$3); print $3}')
WIRED=$(echo "$STATS" | awk '/Pages wired/ {gsub(/\./,"",$4); print $4}')
COMPRESSED=$(echo "$STATS" | awk '/Pages occupied by compressor/ {gsub(/\./,"",$5); print $5}')

USED_MB=$(( (ACTIVE + WIRED + COMPRESSED) * 4096 / 1024 / 1024 ))
PERCENT=$(( USED_MB * 100 / TOTAL_MB ))

sketchybar --set "$NAME" label="${PERCENT}%"
