---
description: Four-lens PR review (security, architect, python, qa) in parallel, then a lead verification pass
argument-hint: "[--pr N | --latest-pr | --base REF] [--worktree PATH] [--lenses a,b] [--focus TEXT]"
---
Run the four-lens PR review now, using the `pr-review` skill (script: `$HOME/.pi/agent/skills/pr-review/scripts/pr_review.py`, lens prompts in `$HOME/.pi/agent/skills/pr-review/references/`).

Arguments for this run: ${@:-none}

Steps:
1. With bash, run `python3 "$HOME/.pi/agent/skills/pr-review/scripts/pr_review.py"` from the repository to review, passing the arguments above (ignore them if they read `none`). Use `--dry-run` first only if the base or the diff range is unclear. If no arguments were given and the user named a PR earlier in the conversation, pass that `--pr N`.
2. When it finishes, read `<out>/final.md` and report the confirmed and downgraded findings, most severe first, one or two lines each (severity, `path:line`, claim). State how many findings were rejected and give the report path.
3. Do not fix anything, do not commit, and do not add findings of your own.
