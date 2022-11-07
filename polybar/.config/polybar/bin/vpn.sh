#!/bin/sh

export VPN="$(nmcli -t -f name,type connection show --order name --active 2>/dev/null | grep vpn | head -1 | cut -d : -f 1)"


if [ -n "$VPN" ]; then
	echo "%{F#aec795} %{F-}[%{F#fAA} $VPN %{F-}]"
else
	echo %{F#f00} %{F-}[ N/A ]
fi
