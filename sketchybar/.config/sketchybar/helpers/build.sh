#!/bin/sh
# Builds the tiny TCC-authorized helper apps the plugins rely on. TCC won't
# prompt for a bare Mach-O, hence the .app wrappers.
#
#   ssid.app      Prints the current Wi-Fi SSID. macOS (Sonoma+) redacts the
#                 SSID from every unauthorized tool, including root-run
#                 wdutil/ipconfig; only a Location-authorized, *bundled* app
#                 can read it.
#   calendar.app  Caches today's upcoming events for plugins/calendar.sh.
#                 Needs Calendars access.
#
# Run once after checkout (or after editing a helper's .swift):
#   sh build.sh               # all helpers
#   sh build.sh calendar      # just one (ssid | calendar)
# then launch each app once to approve its permission prompt:
#   open -W ssid.app          # or: ./ssid.app/Contents/MacOS/ssid
#   open -W calendar.app
# Rebuilding changes the ad-hoc signature, so macOS may ask to approve again;
# rebuild only the helper you changed.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# build NAME [swiftc flags...] — NAME.swift + NAME.plist -> NAME.app
build() {
  name=$1
  shift
  app="$name.app"

  rm -rf "$app"
  mkdir -p "$app/Contents/MacOS"
  cp "$name.plist" "$app/Contents/Info.plist"

  swiftc -O "$name.swift" -o "$app/Contents/MacOS/$name" "$@"

  # Ad-hoc sign the bundle so TCC can attribute it (stable identifier via plist).
  codesign --force --deep --sign - "$app"

  echo "Built $app"
  echo "Approve once:  open -W $DIR/$app"
}

case "${1:-all}" in
  ssid)     build ssid -framework CoreWLAN -framework CoreLocation ;;
  calendar) build calendar -framework EventKit ;;
  all)
    build ssid -framework CoreWLAN -framework CoreLocation
    build calendar -framework EventKit
    ;;
  *)
    echo "usage: sh build.sh [ssid|calendar]" >&2
    exit 1
    ;;
esac
