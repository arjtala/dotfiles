#!/bin/sh
# Builds ssid.app — a tiny Location-authorized helper that prints the current
# Wi-Fi SSID. macOS (Sonoma+) redacts the SSID from every unauthorized tool,
# including root-run wdutil/ipconfig; only a Location-authorized, *bundled*
# app can read it. TCC won't prompt for a bare Mach-O, hence the .app wrapper.
#
# Run once after checkout (or after editing ssid.swift):
#   sh build.sh
# then launch the app once to approve the Location prompt:
#   open -W ssid.app        # or: ./ssid.app/Contents/MacOS/ssid
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

APP="ssid.app"
BIN="$APP/Contents/MacOS/ssid"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cp Info.plist "$APP/Contents/Info.plist"

swiftc -O ssid.swift -o "$BIN" \
  -framework CoreWLAN -framework CoreLocation

# Ad-hoc sign the bundle so TCC can attribute it (stable identifier via plist).
codesign --force --deep --sign - "$APP"

echo "Built $APP"
echo "Approve Location once:  open -W $DIR/$APP"
