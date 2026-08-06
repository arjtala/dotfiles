#!/bin/sh

export VPN="$(nmcli -t -f name,type connection show --order name --active 2>/dev/null | grep vpn | head -1 | cut -d : -f 1)"
if [ -n "$VPN" ]; then
	VPN="  $VPN"
	# echo "%{F#aec795} %{F-}[%{F#fAA} $VPN %{F-}]"
else
	VPN="🌐 N/A"
	# echo %{F#f00} %{F-}
fi

external="$("$HOME/.config/waybar/scripts/pub-ip.sh")"
jq -cn --arg text "$VPN" --arg tooltip "$external" \
    '{text: $text, tooltip: $tooltip}'
