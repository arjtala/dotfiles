# tmux keybindings

Prefix is the default `Ctrl + b`. Defaults below are the commonly-used ones
— `prefix + ?` in a running tmux prints the full table.

## Session

| Key | Action |
| --- | --- |
| `prefix + d` | Detach from session |
| `prefix + s` | Tree view of sessions |
| `prefix + $` | Rename session |
| `prefix + (` / `prefix + )` | Previous / next session |

## Window

| Key | Action |
| --- | --- |
| `prefix + c` | New window |
| `prefix + ,` | Rename window |
| `prefix + &` | Kill window |
| `prefix + n` / `prefix + p` | Next / previous window |
| `prefix + 0 … 9` | Go to window N |
| `prefix + w` | Tree view of windows |
| `prefix + f` | Find window by name |

## Pane

| Key | Action |
| --- | --- |
| `prefix + "` | Split pane horizontally |
| `prefix + %` | Split pane vertically |
| `prefix + o` | Focus next pane |
| `prefix + ;` | Toggle last active pane |
| `prefix + { / }` | Swap pane with previous / next |
| `prefix + z` | Toggle pane zoom |
| `prefix + x` | Kill pane |
| `prefix + arrow` | Focus pane in direction |
| `prefix + Ctrl + arrow` | Resize pane by 1 |

## Copy mode and clipboard

| Key | Action |
| --- | --- |
| `prefix + [` | Enter copy mode |
| `v` (in copy mode) | Start selection (vi mode) |
| `y` (in copy mode) | Yank to system clipboard (tmux-yank) |
| Mouse drag | Select + copy to system clipboard |
| `prefix + ]` | Paste from tmux buffer |

## Plugin keys

| Key | Action | Plugin |
| --- | --- | --- |
| `prefix + u` | fzf pick URL from visible pane | tmux-fzf-url |
| `prefix + F` | On-screen copy hints (vimium-style) | tmux-thumbs |
| `prefix + /` | fzf scrollback search with preview | tmux-fuzzback |
| — | Auto-reload on `.tmux.conf` save (needs `entr`) | tmux-autoreload |

## TPM (plugin manager)

| Key | Action |
| --- | --- |
| `prefix + I` | Install plugins declared in config |
| `prefix + U` | Update plugins |
| `prefix + Alt + u` | Remove plugins no longer in config |

## Custom

| Key | Action |
| --- | --- |
| `prefix + b` | Toggle status bar visibility |
