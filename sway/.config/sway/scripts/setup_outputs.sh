#!/usr/bin/env bash
set -euo pipefail

# Run on startup/reload after Sway has applied the output scale settings.
for ((i = 0; i < 20; i++)); do
  if outputs=$(swaymsg -r -t get_outputs); then break; fi
  sleep 0.25
done

command_sway() {
  swaymsg -r "$1" | jq -e 'all(.[]; .success == true)' >/dev/null
}

primary=HDMI-A-2
workspace_one=$primary
hdmi_x=0
if jq -e 'any(.[]; .name == "DP-3")' <<< "$outputs" >/dev/null; then
  command_sway 'output DP-3 enable transform 90 pos 0 0'
  # rect.width already accounts for both rotation and scale.
  hdmi_x=$(swaymsg -r -t get_outputs | jq -er '.[] | select(.name == "DP-3" and .active) | .rect.width')
  workspace_one=DP-3
fi

if jq -e 'any(.[]; .name == "HDMI-A-2" and .active)' <<< "$outputs" >/dev/null; then
  command_sway "output $primary pos $hdmi_x 0"
else
  # Leave workspaces alone if the destination monitor is unavailable.
  exit 0
fi

workspaces=$(swaymsg -r -t get_workspaces)
focused=$(jq -r '.[] | select(.focused) | .name | @json' <<< "$workspaces")
while IFS= read -r workspace; do
  name=$(jq -r '.name | @json' <<< "$workspace")
  target=$primary
  if [[ $(jq -r '.num' <<< "$workspace") == 1 ]]; then
    target=$workspace_one
  fi
  command_sway "workspace $name output $target"
  if [[ $(jq -r '.output' <<< "$workspace") != "$target" ]]; then
    command_sway "workspace --no-auto-back-and-forth $name; move workspace to output $target"
  fi
done < <(jq -c '.[]' <<< "$workspaces")

# Ensure workspace 1 exists even if it was not open before the reload.
command_sway "workspace --no-auto-back-and-forth number 1; move workspace to output $workspace_one"
if [[ -n $focused ]]; then
  command_sway "workspace --no-auto-back-and-forth $focused"
fi
