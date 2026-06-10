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
| `prefix + "` | Split pane — new pane below (tmux calls this "vertical") |
| `prefix + %` | Split pane — new pane to the right (tmux calls this "horizontal") |
| `prefix + o` | Focus next pane |
| `prefix + ;` | Toggle last active pane |
| `prefix + { / }` | Swap pane with previous / next |
| `prefix + z` | Toggle pane zoom |
| `prefix + x` | Kill pane |
| `prefix + arrow` | Focus pane in direction |
| `prefix + Ctrl + arrow` | Resize pane by 1 |
| `prefix + T` | Set the current pane title |

## Copy mode and clipboard

`mode-keys` is emacs (tmux's default). Relevant bindings:

| Key | Action |
| --- | --- |
| `prefix + [` | Enter copy mode |
| `C-Space` (in copy mode) | Start selection |
| `y` (in copy mode) | Yank selection to system clipboard (tmux-yank) |
| Mouse drag | Select + copy to system clipboard |
| Double / triple click | Copy word / line |
| `prefix + ]` | Paste from tmux buffer |
| `prefix + y` | Copy the current command line (tmux-yank) |
| `prefix + Y` | Copy the current pane's working directory (tmux-yank) |

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

## Theme

Local sessions use `tmux-oasis`; remote (SSH) sessions fall back to
`tmux-power` — branched on `$SSH_CONNECTION` at the bottom of `.tmux.conf`.

Window labels auto-follow the current repo or directory, and pane borders show
either the pane title (`prefix + T`) or a repo-aware shortened path/command
fallback.

Swap the local oasis flavor (and regenerate a matching Ghostty theme in one
shot) with:

```sh
./scripts/oasis-theme canyon_dark     # or abyss_dark, mirage_dark, sol_dark, ...
./scripts/oasis-theme                 # lists all available flavors
```

The script unsets stale `@thm_*` options and reloads `.tmux.conf` in place —
no server restart needed. For Ghostty to pick up the new palette, `Cmd+Shift+,`
(reload config).

## Dependencies

| Needed for | mac (brew) | Fedora (dnf) | Arch (pacman) |
| --- | --- | --- | --- |
| tmux itself | `tmux` | `tmux` | `tmux` |
| tmux-fzf-url, tmux-fuzzback | `fzf` | `fzf` | `fzf` |
| tmux-autoreload (file watcher) | `entr` | `entr` | `entr` |
| tmux-autoreload (bash 4+ `declare -g`) | `bash` | built-in | built-in |
| tmux-thumbs (cargo build) | `rust` | `rust cargo` | `rust` |

Manual one-off (TPM — not a package):

```sh
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
```

Then in a tmux session, `<prefix> I` to install plugins.
