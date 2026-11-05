# Pi

Extensions, skills and prompt templates for the [Pi](https://pi.dev) coding
agent, linked into `~/.pi/agent/{extensions,skills,prompts}/` by `stow pi`
(part of `./setup` on every OS).

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

## pr-review

[`skills/pr-review`](.pi/agent/skills/pr-review) is a four-lens pull-request
review, invoked as `/pr-review` (template:
[`prompts/pr-review.md`](.pi/agent/prompts/pr-review.md)) or directly:

```sh
python3 ~/.pi/agent/skills/pr-review/scripts/pr_review.py --latest-pr
```

Four reviewers (`security`, `architect`, `python`, `qa`) each run in their own
`pi --print` process with their own context, in parallel, writing one findings
report each. A fifth process (the lead) re-reads the code and confirms,
downgrades, merges or rejects every finding. Results land in
`~/.pi/reviews/<repo>-<base7>-<head7>-<ts>/`: `final.md` is the verified
report, `prompts/` is exactly what each agent was told.

Reviewers get `read,bash,grep,find,ls` and no `edit`/`write`; the script
compares `git status --porcelain` before and after the run and warns if the
checkout changed. The lens instructions are plain Markdown in
`skills/pr-review/references/` — edit them there, not in `~/.pi/agent`.

It needs `pi` on `PATH`, `python3`, and `gh` only for `--pr/--latest-pr`.
`stow pi` links the skill and the template; run `/reload` in a running session
to pick them up.
