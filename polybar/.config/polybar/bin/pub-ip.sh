#! /bin/bash

WCONNECTED=" "
ECONNECTED="🌐"
DEVICES=$(route | awk '/^default/{print $NF}')
IPV4=$(dig +short txt ch whoami.cloudflare @1.0.0.1 2>/dev/null \
  | tr -d '"' | awk -F. '
      NF == 4 {
        for (i = 1; i <= 4; i++) {
          if ($i !~ /^[0-9]+$/ || $i > 255) next
        }
        print
        exit
      }
    ')
IPV6=$(dig TXT +short o-o.myaddr.l.google.com @ns1.google.com 2>/dev/null \
  | tr -d '"' | awk '
      function valid_ipv6(value, fields, count, i, explicit, copy, compressed) {
        if (value !~ /^[0-9A-Fa-f:]+$/ || value ~ /:::/) return 0
        copy = value
        compressed = gsub(/::/, "", copy)
        if (compressed > 1) return 0
        count = split(value, fields, ":")
        explicit = 0
        for (i = 1; i <= count; i++) {
          if (fields[i] == "") continue
          if (length(fields[i]) > 4) return 0
          explicit++
        }
        if (compressed == 1) return explicit < 8
        return explicit == 8 && count == 8
      }
      valid_ipv6($0) {
        print
        exit
      }
    ')
if [ -n "$IPV6" ]; then
	IP_ADDRESS="$IPV6"
elif [ -n "$IPV4" ]; then
	IP_ADDRESS="$IPV4"
else
	IP_ADDRESS="N/A"
fi;

for nic in $DEVICES; do
  if [[ $nic == *"vpn"* ]]; then
	  DEVICE="%{F#2ab7ca} $ECONNECTED %{F-}"
	  LOCAL_ADDRESS="%{F#6497b1}$(ifconfig $nic | grep 'inet ' | awk '{ print $2 }' | tr -d '\n')%{F-} | "
  elif [[ $nic == *"en"* ]]; then
	  DEVICE="%{F#2ab7ca} $ECONNECTED %{F-}"
	  LOCAL_ADDRESS="%{F#6497b1}$(ifconfig $nic | grep 'inet ' | awk '{ print $2 }' | tr -d '\n')%{F-} | "
  elif [[ $nic == *"wl"* ]]; then
	  DEVICE="%{F#2ab7ca} $WCONNECTED %{F-}"
	  LOCAL_ADDRESS="%{F#6497b1}$(ifconfig $nic | grep 'inet ' | awk '{ print $2 }' | tr -d '\n')%{F-} | "
  else
 	  DEVICE="%{F#C06C84} $ECONNECTED %{F-}"
	  LOCAL_ADDRESS=""
  fi;
done;

VPN="%{F#f00} %{F-}[ N/A ]"
if pgrep -x openconnect > /dev/null; then
	VPN="%{F#aec795} %{F-}[%{F#fAA} $(nmcli -t -f name,type connection show --order name --active 2>/dev/null | grep vpn | head -1 | cut -d : -f 1) %{F-}]"
fi
CONNECTION="$DEVICE$VPN $LOCAL_ADDRESS%{F#54b2a9}$IP_ADDRESS%{F-}";
printf "%s" "$CONNECTION"
