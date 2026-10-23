# Local and SSH tmux colors

The status label identifies each attached client: LOCAL uses the green shared
palette, while SSH uses a gray status bar. The helper reads SSH_CONNECTION from
each client's process environment, rather than the server/session environment,
which can be stale when local and SSH clients share a server.

Pane backgrounds require literal window options: local windows use the palette
background (currently #1b2a1e), and SSH windows use #32302f. A window viewed from
both kinds of client uses the SSH background because window options are shared;
its status label remains specific to each client.

The helper runs in the background on attach, detach, focus, session changes and
window creation. Cached identities/styles avoid repeated writes. Status formats
run no shell commands, refresh every 15 seconds, and use a minute-resolution clock.
Theme previews preserve the connection cues.

During the 2026-10-23 stall investigation, tmux command responses stayed below
5 ms across 120 samples; no timeouts or host CPU/memory pressure were observed.
The user reported no recurrence after the changes. This does not establish the
original freeze's cause. No server restart or pane termination was required.
