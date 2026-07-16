FOUND=$(xrandr | /usr/bin/awk '
  $2 == "connected" {
    if ($1 !~ /^eDP/) {
      print $1
      found = 1
      exit
    }
    laptop = $1
  }
  END {
    if (!found && laptop) {
      print laptop
    }
  }
')
export MONITOR=$FOUND
echo "Monitor ${MONITOR}"
