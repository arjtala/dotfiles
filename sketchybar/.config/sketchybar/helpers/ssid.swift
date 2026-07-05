// ssid.swift — print the current Wi-Fi SSID (and cache it for the status bar).
//
// macOS (Sonoma+) redacts the SSID from every tool that lacks Location
// Services authorization — including root-run `wdutil`/`ipconfig`. The only
// way to read it is a process that (a) holds Location authorization and
// (b) queries CoreWLAN itself. TCC only reliably prompts for a *bundled*
// app, so this is shipped as ssid.app (see build.sh).
//
// Behavior:
//   - Prints the SSID to stdout (exit 0), or nothing (exit 1) if
//     unavailable/unauthorized.
//   - Also writes it to ~/.cache/sketchybar-ssid so the shell plugin can read
//     a cached value instantly instead of waiting on Location each tick.

import CoreLocation
import CoreWLAN
import Foundation

let cachePath = ("~/.cache/sketchybar-ssid" as NSString).expandingTildeInPath

func emit(_ ssid: String) {
    print(ssid)
    try? ssid.write(toFile: cachePath, atomically: true, encoding: .utf8)
}

func currentSSID() -> String? {
    guard let ssid = CWWiFiClient.shared().interface()?.ssid(),
          !ssid.isEmpty else { return nil }
    return ssid
}

final class Locator: NSObject, CLLocationManagerDelegate {
    let manager = CLLocationManager()
    private var settled = false

    func start() {
        manager.delegate = self
        evaluate(manager.authorizationStatus)
    }

    func locationManagerDidChangeAuthorization(_ m: CLLocationManager) {
        evaluate(m.authorizationStatus)
    }

    private func evaluate(_ status: CLAuthorizationStatus) {
        switch status {
        case .authorizedAlways, .authorized:
            finish(authorized: true)
        case .notDetermined:
            manager.requestAlwaysAuthorization()   // triggers the one-time prompt
        default:
            finish(authorized: false)
        }
    }

    private func finish(authorized: Bool) {
        guard !settled else { return }
        settled = true
        if authorized, let ssid = currentSSID() {
            emit(ssid)
            exit(0)
        }
        exit(1)
    }
}

let locator = Locator()
locator.start()

// Bail out if authorization never resolves (e.g. run headless with no prompt).
DispatchQueue.main.asyncAfter(deadline: .now() + 10) { exit(1) }
RunLoop.main.run()
