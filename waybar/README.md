# Waybar popups

Click the clock for a month calendar, or athan for today's prayer times.
Click again or press Escape to close; clicking the other module switches panels.
Clicking outside the panel dismisses it (the dismissal click is consumed).
The popup sits at bottom center on the output chosen by the compositor.
Both the Sway and dwl Waybar configurations use the shared helper.

Requires Python 3, PyGObject, GTK3, and gtk-layer-shell with introspection support.
The helper runs only while a popup is open. Its private socket and launch lock
live in `XDG_RUNTIME_DIR`. No additional service is needed.

The calendar uses America/Los_Angeles, matching the clock configuration.
The prayer panel uses the timezone returned by `~/.cargo/bin/athan --all --json`.
This requires athan's full-day `prayers` output, rather than the older `upcoming`
output. Sunrise is shown separately and does not change the current prayer.
“Current” means most recently started: before Fajr, yesterday's Isha is marked
separately rather than highlighting tonight's time. After Isha the footer says
“Next: Fajr tomorrow”; it does not estimate tomorrow's time using today's Fajr.

Prayer data is fetched in a background thread every minute while open. The
highlight/countdown refresh every 15 seconds. Same-day data remains visible on
fetch failures with a warning; yesterday's schedule is not shown as today's.

Appearance lives in `.config/waybar/popup.css`. The click commands use a default
bar height of 31 pixels; pass `--bar-height N` if that changes. The transparent
dismissal surface covers the selected output above the bar while open.

Validation: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s waybar/tests`
(from the dotfiles root). Live Wayland testing is needed for placement, outside
clicks, Escape, and toggling between modules.
