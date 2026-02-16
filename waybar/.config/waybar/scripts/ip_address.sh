#!/bin/sh

get_active_ip() {
  # Try to get IP from various common network interfaces
  # First check for wireless connections (typically wlan0, en0 on Mac)
  local ip=""
  # For Linux systems
  if command -v ip &> /dev/null; then
    # Get the default route interface
    local interface=$(ip route | grep default | awk '{print $5}' | head -n 1)
    if [[ -n "$interface" ]]; then
      ip=$(ip addr show $interface | grep -oP 'inet \K[\d.]+' | head -n 1)
    fi
  # For macOS and some BSD systems
  elif command -v ifconfig &> /dev/null; then
    # First try to find the default active interface
    local interface=$(route -n get default 2>/dev/null | grep interface | awk '{print $2}')
    if [[ -n "$interface" ]]; then
      ip=$(ifconfig $interface | grep 'inet ' | awk '{print $2}')
    else
      # Try common wireless interfaces if default route doesn't work
      for iface in en0 wlan0 wifi0 eth0 en1; do
        if ifconfig $iface &>/dev/null; then
          local temp_ip=$(ifconfig $iface | grep 'inet ' | awk '{print $2}')
          if [[ -n "$temp_ip" ]]; then
            ip=$temp_ip
            break
          fi
        fi
      done
    fi
  fi

  # If still no IP found, try a different approach for Linux
  if [[ -z "$ip" ]]; then
    # Try to find an active interface with an IP address
    for iface in $(ls /sys/class/net 2>/dev/null || echo "eth0 wlan0"); do
      # Skip loopback and virtual interfaces
      [[ "$iface" == "lo" || "$iface" == "veth"* || "$iface" == "docker"* || "$iface" == "br-"* ]] && continue
      local test_ip=""
      if command -v ip &> /dev/null; then
        test_ip=$(ip addr show $iface 2>/dev/null | grep -oP 'inet \K[\d.]+' | head -n 1)
      elif command -v ifconfig &> /dev/null; then
        test_ip=$(ifconfig $iface 2>/dev/null | grep 'inet ' | awk '{print $2}')
      fi
      if [[ -n "$test_ip" && "$test_ip" != "127.0.0.1" ]]; then
        ip=$test_ip
        break
      fi
    done
  fi

  # Output the IP or an error message
  if [[ -n "$ip" ]]; then
    echo "$ip"
    return 0
  else
    echo "disconnected"
    return 0
  fi
}



my_ip=$(get_active_ip)
echo "%{F#aec795}[%{F-}%{F#fAA} $my_ip %{F-} %{F#aec795}]%{F-}"
