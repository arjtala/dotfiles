#!/bin/sh

export wlan_ip="$(ip route | /usr/bin/grep -v vpn | /usr/bin/grep '^default' | /usr/bin/awk '{print $5}' | head -n1)"
export eth_ip="$(ifconfig enp1s0 | grep 'inet ' | awk '{ print $2 }')"

if [ -n "$eth_ip" ]; then
	echo "%{F#aec795}[%{F-}%{F#fAA} $eth_ip %{F-} %{F#aec795}]%{F-}"
elif [ -n "$wlan_ip" ]; then
	echo "%{F#aec795}[%{F-}%{F#fAA} $wlan_ip %{F-} %{F#aec795}]%{F-}"
else
	echo "%{F#aec795}[%{F-}%{F#fAA} disconnected %{F-} %{F#aec795}]%{F-}"
fi
