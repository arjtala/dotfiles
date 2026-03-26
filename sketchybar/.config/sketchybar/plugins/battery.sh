#!/bin/sh

source "$CONFIG_DIR/colors.sh"

PERCENTAGE="$(pmset -g batt | grep -Eo "\d+%" | cut -d% -f1)"
CHARGING="$(pmset -g batt | grep 'AC Power')"

if [ "$PERCENTAGE" = "" ]; then
  exit 0
fi

case "${PERCENTAGE}" in
  9[0-9]|100) ICON="" ;;
  [6-8][0-9]) ICON="" ;;
  [3-5][0-9]) ICON="" ;;
  [1-2][0-9]) ICON="" ;;
  *)          ICON="" ;;
esac

if [ -n "$CHARGING" ]; then
  ICON=""
fi

# Match waybar: warning=yellow at 20%, critical=red at 12%
if [ "$PERCENTAGE" -le 12 ]; then
  sketchybar --set "$NAME" icon="$ICON" label="${PERCENTAGE}%" icon.color=$BR_RED label.color=$BR_RED
elif [ "$PERCENTAGE" -le 20 ]; then
  sketchybar --set "$NAME" icon="$ICON" label="${PERCENTAGE}%" icon.color=$BR_YELLOW label.color=$BR_YELLOW
else
  sketchybar --set "$NAME" icon="$ICON" label="${PERCENTAGE}%" icon.color=$BR_GREEN label.color=$BR_GREEN
fi
