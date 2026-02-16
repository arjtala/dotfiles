#! /bin/bash

DEVICES=$(route | awk '/^default/{print $NF}')
IPV4=$(dig +short txt ch whoami.cloudflare @1.0.0.1 | tr -d '"')
IPV6=$(dig TXT +short o-o.myaddr.l.google.com @ns1.google.com | tr -d '"')
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
