#!/usr/bin/env bash
# Make bash more sane
set -euo pipefail

# This script is for selecting wallpapers (Modifier + whatever)
ROFI_THEME="$HOME/.config/rofi/wallpaper-selector.rasi"

# Path to wallpapers
# WALLPAPER_DIR="$HOME/Pictures/Wallpapers/beautiful-wallpapers"
WALLPAPER_DIR="$HOME/.wallpapers"

# Retrieve image files (including subdirectories)
mapfile -d '' -t PICS < <(
	find "$WALLPAPER_DIR" -type f \
		\( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.gif' \) \
		-print0
)
if ((${#PICS[@]} == 0)); then
	printf 'No wallpapers found in %s\n' "$WALLPAPER_DIR" >&2
	exit 1
fi

# Basename of every picture, for duplicate detection when building the menu.
NAMES=()
for pic in "${PICS[@]}"; do
	NAMES+=("$(basename "${pic%.*}")")
done
NAMES_TEXT=$(printf '%s\n' "${NAMES[@]}")

# List of all types:
# scheme-content
# scheme-expressive
# scheme-fidelity
# scheme-fruit-salad
# scheme-monochrome
# scheme-neutral
# scheme-rainbow
# scheme-tonal-spot

MODE="dark"
SCHEME_TYPE="scheme-fidelity"
MATUGEN_ARGS=(-m "$MODE" -v -t "$SCHEME_TYPE" --show-colors)

INTERFACE="org.gnome.desktop.interface"
WM_PREFERENCES="org.gnome.desktop.wm.preferences"

# SWAYBG_ARGS=
# SWWW_ARGS=
# HYPRPAPER_ARGS=
# MPVPAPER_ARGS=

# Rofi command
# -no-custom keeps the prompt from submitting free text (only menu lines).
ROFI_COMMAND=(rofi -dmenu -no-custom -theme "$ROFI_THEME")

# Function to generate the menu.
# Each line carries a 1-based index so the selection identifies the picture
# exactly, even when basenames collide.
menu() {
	local i=0 pic label
	printf '00  Random\n'
	for pic in "${PICS[@]}"; do
		i=$((i + 1))
		label="${NAMES[i-1]}"
		# Disambiguate duplicate names with the path relative to WALLPAPER_DIR
		if [[ $(grep -cxF "$label" <<<"$NAMES_TEXT") -gt 1 ]]; then
			label="${pic#"$WALLPAPER_DIR"/}"
		fi
		# Display .gif to indicate animated images
		if [[ ! "${pic}" =~ \.gif$ ]]; then
			printf '%02d  %s\x00icon\x1f%s\n' "$i" "$label" "$pic"
		else
			printf '%02d  %s\n' "$i" "$label"
		fi
	done
}

# Main function
main() {
	choice=$(menu | "${ROFI_COMMAND[@]}")

	# Exit if no choice is made
	if [[ -z $choice ]]; then
		exit 0
	fi

	# Handle random choice
	if [[ "$choice" == "00  Random" ]]; then
		selected_file="${PICS[RANDOM % ${#PICS[@]}]}"
	# The index is the first field of the chosen line; anything that is not
	# "number + space" is not a menu line (e.g. typed free text).
	elif [[ $choice =~ ^([0-9]+)[[:space:]] ]]; then
		index=$((10#${BASH_REMATCH[1]}))
		((index >= 1 && index <= ${#PICS[@]})) || {
			echo "Wallpaper not found."
			exit 1
		}
		selected_file="${PICS[index-1]}"
	else
		echo "Wallpaper not found."
		exit 1
	fi

	if [[ -z "$selected_file" || ! -f "$selected_file" ]]; then
		echo "Wallpaper not found."
		exit 1
	fi

	relative_target="${selected_file#"$WALLPAPER_DIR/"}"
	ln -sfn "$relative_target" "$WALLPAPER_DIR/inuse.png"
	if command -v matugen >/dev/null; then
		matugen image "$selected_file" "${MATUGEN_ARGS[@]}"
	fi
	gsettings set "$INTERFACE" gtk-theme adw-gtk3-dark
	gsettings set "$WM_PREFERENCES" theme 'adw-gtk3-dark'
	swaymsg reload
}

# Check if rofi is already running
if pgrep -u "$UID" -x rofi >/dev/null; then
	pkill -u "$UID" -x rofi
	exit 0
fi

main
