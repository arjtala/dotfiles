#!/usr/bin/env bash
# Make bash more sane
set -euo pipefail

theme="$HOME/.config/rofi/screen-recorder.rasi"
rofi_command=(rofi -theme "$theme")
dir="$HOME/Videos/Screen-Recorder"
mkdir -p "$dir"

# Define the filename format
time=$(date +%Y-%m-%d-%I-%M-%S)
file="Recording_${time}.mp4"
pid_file="$dir/record.pid"

# Icons
icon1="media-record"
icon2="alarm-symbolic"

# Buttons
screen=" Record Desktop"
area=" Record A Area"
infive="靖 Record in 3s"
inten="福 Record in 10s"
stop=" Stop Recording"

# Print the PID only when it still belongs to the recorder started here.
recording_pid() {
	local pid command
	[[ -r "$pid_file" ]] || return 1
	read -r pid <"$pid_file"
	[[ "$pid" =~ ^[0-9]+$ ]] || return 1
	kill -0 "$pid" 2>/dev/null || return 1
	command=$(ps -p "$pid" -o comm=)
	[[ "${command##*/}" == "wf-recorder" ]] || return 1
	printf '%s\n' "$pid"
}

check_recording() {
	recording_pid >/dev/null
}

# Notify function
notify_view() {
	notify-send -u low -h string:x-canonical-private-synchronous:recorder -i "$icon1" "Recording started."
}

# Stop recording function
stop_recording() {
	local pid
	if pid=$(recording_pid); then
		kill -INT "$pid"
		rm -f "$pid_file"
		notify-send -u low -h string:x-canonical-private-synchronous:recorder -i "$icon1" "Recording stopped."
	else
		rm -f "$pid_file"
		notify-send -u low -h string:x-canonical-private-synchronous:recorder -i "$icon1" "No recording in progress."
	fi
}

# countdown
countdown() {
	for sec in $(seq "$1" -1 1); do
		notify-send -t 1000 -h string:x-canonical-private-synchronous:recorder -i "$icon2" "Recording starts in : $sec"
		sleep 1
	done
}

# Start recording functions
recordnow() {
	if check_recording; then
		# Recording is already active, offer to stop
		chosen="$(printf '%s\n' "Stop Recording" | "${rofi_command[@]}" -p 'Recording in progress' -dmenu)"
		case $chosen in
		"Stop Recording")
			stop_recording
			;;
		esac
	else
		# Start new recording
		wf-recorder -f "$dir/$file" &
		echo $! >"$pid_file"
		notify_view
	fi
}

record5() {
	countdown '3'
	recordnow
}

record10() {
	countdown '10'
	recordnow
}

recordarea() {
	if check_recording; then
		# Recording is already active, offer to stop
		chosen="$(printf '%s\n' "Stop Recording" | "${rofi_command[@]}" -p 'Recording in progress' -dmenu)"
		case $chosen in
		"Stop Recording")
			stop_recording
			;;
		esac
	else
		wf-recorder -f "$dir/$file" -g "$(slurp)" &
		echo $! >"$pid_file"
		notify_view
	fi
}

# Variable passed to rofi
options="$screen\n$area\n$infive\n$inten\n$stop"

chosen="$(printf '%b\n' "$options" | "${rofi_command[@]}" -p 'Start Recording' -dmenu -selected-row 0)"
case $chosen in
$screen)
	recordnow
	;;
$area)
	recordarea
	;;
$infive)
	record5
	;;
$inten)
	record10
	;;
$stop)
	stop_recording
	;;
esac
