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
MATUGEN_ARGS=(-m "$MODE" -v -t "$SCHEME_TYPE" --show-colors --debug)

INTERFACE="org.gnome.desktop.interface"
WM_PREFERENCES="org.gnome.desktop.wm.preferences"

# SWAYBG_ARGS=
# SWWW_ARGS=
# HYPRPAPER_ARGS=
# MPVPAPER_ARGS=

# Rofi command
ROFI_COMMAND=(rofi -dmenu -theme "$ROFI_THEME")

# Function to generate the menu
menu() {
	printf "Random\n"
	for pic in "${PICS[@]}"; do
		# Display .gif to indicate animated images
		if [[ ! "${pic}" =~ \.gif$ ]]; then
			printf '%s\x00icon\x1f%s\n' "$(basename "${pic%.*}")" "$pic"
		else
			printf '%s\n' "$(basename "${pic%.*}")"
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
	if [[ "$choice" == "Random" ]]; then
		selected_file="${PICS[RANDOM % ${#PICS[@]}]}"
	else
		selected_file=""
		for file in "${PICS[@]}"; do
			if [[ "$(basename "${file%.*}")" == "$choice" ]]; then
				selected_file="$file"
				break
			fi
		done
	fi

	if [[ -z "$selected_file" ]]; then
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
