// calendar.swift — cache today's remaining calendar events for the status bar.
//
// Reading events needs Calendars authorization, and TCC only reliably prompts
// for a *bundled* app, so this is shipped as calendar.app (see build.sh).
//
// Behavior:
//   - Writes the rest of today's timed events to ~/.cache/sketchybar-calendar,
//     one per line, sorted by start, tab-separated:
//       start_epoch  end_epoch  title  meeting_url
//     All-day, cancelled, and declined events are skipped. meeting_url is the
//     first Webex/Zoom/Teams/Meet/FaceTime link found, or empty.
//   - Exits 0 on success (including "no events"), 1 if unauthorized.

import EventKit
import Foundation

let cachePath = ("~/.cache/sketchybar-calendar" as NSString).expandingTildeInPath
let cacheDirectory = (cachePath as NSString).deletingLastPathComponent

let meetingHosts = ["webex", "zoom.us", "teams.microsoft", "meet.google", "facetime"]

let store = EKEventStore()

// Tabs and newlines would break the line/field format.
func clean(_ text: String) -> String {
    let flat = text.components(separatedBy: .newlines).joined(separator: " ")
        .replacingOccurrences(of: "\t", with: " ")
        .trimmingCharacters(in: .whitespaces)
    return flat.isEmpty ? "Untitled" : flat
}

func meetingURL(_ event: EKEvent) -> String {
    var candidates: [URL] = []
    if let url = event.url { candidates.append(url) }
    if let detector = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue) {
        for text in [event.location, event.notes].compactMap({ $0 }) {
            let range = NSRange(text.startIndex..., in: text)
            for match in detector.matches(in: text, range: range) {
                if let url = match.url { candidates.append(url) }
            }
        }
    }
    let meeting = candidates.first { url in
        let link = url.absoluteString.lowercased()
        return meetingHosts.contains { link.contains($0) }
    }
    return meeting?.absoluteString ?? ""
}

func declined(_ event: EKEvent) -> Bool {
    event.attendees?.contains { $0.isCurrentUser && $0.participantStatus == .declined } ?? false
}

func writeEvents() -> Never {
    let now = Date()
    let calendar = Calendar.current
    let endOfDay = calendar.date(byAdding: .day, value: 1, to: calendar.startOfDay(for: now))!
    let predicate = store.predicateForEvents(withStart: now, end: endOfDay, calendars: nil)

    let lines = store.events(matching: predicate)
        .filter { !$0.isAllDay && $0.status != .canceled && !declined($0) && $0.endDate > now }
        .sorted { $0.startDate < $1.startDate }
        .map { event in
            [
                String(Int(event.startDate.timeIntervalSince1970)),
                String(Int(event.endDate.timeIntervalSince1970)),
                clean(event.title ?? ""),
                meetingURL(event),
            ].joined(separator: "\t")
        }

    try? FileManager.default.createDirectory(
        atPath: cacheDirectory,
        withIntermediateDirectories: true,
        attributes: nil
    )
    let contents = lines.map { $0 + "\n" }.joined()
    guard (try? contents.write(toFile: cachePath, atomically: true, encoding: .utf8)) != nil else {
        exit(1)
    }
    exit(0)
}

switch EKEventStore.authorizationStatus(for: .event) {
case .fullAccess:
    writeEvents()
case .notDetermined:
    store.requestFullAccessToEvents { granted, _ in   // triggers the one-time prompt
        DispatchQueue.main.async {
            if granted { writeEvents() }
            exit(1)
        }
    }
default:
    exit(1)
}

// Bail out if authorization never resolves (e.g. run headless with no prompt).
DispatchQueue.main.asyncAfter(deadline: .now() + 60) { exit(1) }
RunLoop.main.run()
