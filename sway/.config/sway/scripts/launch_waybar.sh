#!/usr/bin/env bash

set -euo pipefail

if pgrep -u "$UID" -x waybar >/dev/null; then
	pkill -u "$UID" -x waybar || true
	while pgrep -u "$UID" -x waybar >/dev/null; do
		sleep 0.1
	done
fi

waybar -c "$HOME/.config/waybar/config" -s "$HOME/.config/waybar/style.css" &
