# Pi

Extensions for the [Pi](https://pi.dev) coding agent, linked into
`~/.pi/agent/extensions/` by `stow pi` (part of `./setup` on every OS).

## agent-muster-registry

[`agent-muster-registry.ts`](.pi/agent/extensions/agent-muster-registry.ts)
publishes each running Pi session's state to `~/.pi/agent/registry/<pid>.json`:
`busy` while a turn runs, `waiting` while a dialog is open, `idle` otherwise.
That is the file Claude Code already keeps for itself in `~/.claude/sessions/`,
in the same words, so anything that lists Claude sessions can list Pi's too.

Two readers use it:

- **The bar's agents item** — SketchyBar on macOS, Waybar on Linux. See
  [Agent status](../README.md#agent-status).
- **agent-muster** in Emacs, where this extension comes from. Its copy lives
  in `~/src/agent-muster/pi/`; keep the two the same.

Pi loads extensions when it starts. In a session already running, `/reload`
picks up a change.

To check it, start Pi and look for its entry:

```sh
ls ~/.pi/agent/registry/
```
