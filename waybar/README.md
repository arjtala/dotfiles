# Waybar popups

Click the clock for a month calendar, athan for today's prayer times, or
now playing for media details and controls.
Click again or press Escape to close; clicking the other module switches panels.
Clicking outside the panel dismisses it (the dismissal click is consumed).
The popup opens above the click location on that output, clamped away from
the screen edges. A brief transparent Wayland surface locates the pointer;
this also works when module widths change and when switching between panels.
On Sway, a zero-distance cursor command refreshes pointer focus without moving
the cursor. Other compositors may require pointer motion to deliver the event.
If pointer location is unavailable (for example, a keyboard-only launch),
the popup retains its last position or defaults to bottom center.
Both the Sway and dwl Waybar configurations use the shared helper.

Requires Python 3, PyGObject, GTK3, gtk-layer-shell, and Playerctl with introspection support.
The helper runs only while a popup is open. Its private socket and launch lock
live in `XDG_RUNTIME_DIR`. No additional service is needed.

The layout follows SketchyBar: workspaces, compact app name (Sway), clock,
athan, and now playing on the left; system/network indicators on the right.
Sway's app label uses `app_id` with friendly rewrites for common applications,
rather than exposing the full window title. The Linux bar stays at the bottom.

Now playing uses MPRIS through Playerctl. Waybar starts the watcher; metadata
and playback changes arrive through MPRIS signals, and a one-second tick reads
position and keeps the shared runtime snapshot fresh. The bar is hidden without
loaded playing/paused media, green while playing, and muted while paused.
Playing players take priority over paused players; the most recently changed
player wins within each group. The popup controls the exact player in that
snapshot. Previous/next and ±15-second seeking are separate buttons, disabled
when unsupported; podcast type detection is not assumed. Missing durations
are displayed without a fake progress percentage. Requires an MPRIS-enabled
player (browser support depends on the browser and media site).

VPN status comes from NetworkManager. Tailscale has a separate dot-grid icon,
matching SketchyBar: green when connected, aqua with an exit node selected,
yellow while connecting, orange for login/approval, and dim when off or the
daemon is unavailable. It is hidden when the CLI is not installed.

Click Tailscale for an anchored popup with an on/off button, device/IP, tailnet,
exit node, peer counts, and health warnings. Both views refresh every five
seconds; status queries and button actions run without blocking the popup.
Only the button changes the connection, using `tailscale up --timeout=15s` or
`tailscale down`. Login opens the HTTPS authentication URL supplied by Tailscale.
The popup reports permission failures; it never runs sudo automatically.
To allow your user to operate the daemon, run once in a terminal:

```sh
sudo tailscale set --operator="$USER"
```

If the daemon is unavailable, inspect `systemctl status tailscaled`. A green
icon indicates tailnet connectivity, not that all internet traffic uses an
exit node. The separate VPN indicator does not count the Tailscale connection.

The calendar uses America/Los_Angeles, matching the clock configuration.
The prayer panel uses the timezone returned by `~/.cargo/bin/athan --all --json`.
This requires athan's full-day `prayers` output, rather than the older `upcoming`
output. The highlight starts with Fajr at midnight, moves to Sunrise at sunrise,
then follows each prayer from Dhuhr onward. The countdown always targets the
next prayer, skipping Sunrise. Before Fajr, the countdown still shows
how long until it starts; no previous-day row is displayed. After Isha the footer says
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

MPRIS integration smoke test (uses its own fake player and private session bus):
`dbus-run-session -- python3 waybar/tests/run_mpris_smoke.py`.

Placement integration check: `python3 waybar/tests/run_placement_smoke.py`.
This launches a private headless Sway display and virtual pointer, checking
stationary-pointer anchoring, switching panels, and resizing at the right edge.
