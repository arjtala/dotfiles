#! /bin/bash

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
	  LOCAL_ADDRESS="$(ifconfig $nic | grep 'inet ' | awk '{ print $2 }' | tr -d '\n') | "
  elif [[ $nic == *"en"* ]]; then
	  LOCAL_ADDRESS="$(ifconfig $nic | grep 'inet ' | awk '{ print $2 }' | tr -d '\n') | "
  elif [[ $nic == *"wl"* ]]; then
	  LOCAL_ADDRESS="$(ifconfig $nic | grep 'inet ' | awk '{ print $2 }' | tr -d '\n') | "
  else
	  LOCAL_ADDRESS=""
  fi;
done;

CONNECTION="$LOCAL_ADDRESS $IP_ADDRESS";
printf "%s" "$CONNECTION"
