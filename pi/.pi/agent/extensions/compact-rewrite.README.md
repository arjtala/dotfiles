# compact-rewrite — Pi compaction extension

A Pi extension that takes over session compaction. Instead of Pi's built-in
summarizer, it generates a fresh, self-contained summary with your session model and
returns it as the compaction, so each summary **replaces** the previous one — folding
in only what is still relevant from the prior summary rather than appending to it.

## Supported Pi version

Verified against **Pi 1.4.0** (`@earendil-works/pi-coding-agent`). It relies on the
`session_before_compact` hook, `modelRegistry.streamSimple`, `convertToLlm`, and
`serializeConversation`. That surface is small but not frozen — after a Pi upgrade,
re-run the test suite below before trusting it.

## Install / reload

Lives at `~/.pi/agent/extensions/compact-rewrite.ts` (a symlink into
`~/dotfiles/pi/.pi/agent/extensions/`). It loads automatically at Pi start; to load it
in an already-running session, run `/reload`. No per-session config is required — it is
opt-**out** by default (it only acts when Pi is about to compact).

## Word ceiling vs. token allowance

These are two different things and the extension treats them differently:

- **Word ceiling** — enforced on the *summary text*. `PI_SUMMARY_MAX` (default **1500**).
  The first attempt targets ~70% of the ceiling; if that attempt still exceeds the
  ceiling, exactly **one** rewrite is requested at ~85% of it, operating on the oversized
  draft alone (the conversation is **not** resent, so the rewrite does not consume the
  remaining context space). Both targets are derived from the ceiling, so prompts are
  never negative or impossible. The ceiling is a hard limit on the returned summary's
  word count.
- **Token allowance** — the *generation* call requests the model's full configured output
  allowance (`model.maxTokens`), **not** a fixed 4096, so a long, code-heavy summary is
  not truncated before the word check can run. Note `streamSimple` may clamp the *actual*
  allowance down to the remaining context space when the session is already near its
  limit; the extension's word ceiling is the real guard against an over-long result.

## Failure behavior

A generation is rejected as invalid if it aborts, errors, hits the model output cap
(`stopReason: "length"`), is empty, or contains any tool-call block. On any failure:

- `PI_SUMMARY_FAIL=cancel` (**default**) — keep Pi's existing context; no compaction runs.
- `PI_SUMMARY_FAIL=fallback` — defer to Pi's default compaction. **Caveat: default
  compaction has no word limit, so the ceiling is forfeited in fallback mode.**

You are never silently handed a truncated or over-limit summary; a warning is shown on
the status line describing what happened.

The handler **never throws**. A `session_before_compact` handler that throws is swallowed
by the extension runner and Pi falls through to default (unrestricted) compaction — which
would defeat `PI_SUMMARY_FAIL=cancel`. So every error (model rejection, provider error,
abrupt abort) is caught and routed through the failure policy above.

## Split turns

When compaction fires in the middle of a turn, Pi hands over the dropped history plus the
earlier part of the in-progress turn (`turnPrefixMessages`, with `isSplitTurn` set). The
extension folds both into the summary under a clearly-labelled split-turn prefix section,
so work already shown in the interrupted turn is not lost.

## Manual compaction instructions

When compaction is triggered manually with instructions (e.g. `/compact <text>`), Pi passes
them as `event.customInstructions`. The extension threads them into both the generation and
rewrite prompts and asks the model to follow and restate them in the summary — so they are
not silently dropped by the summarizer.

## Model override / disabling

- `PI_SUMMARY_MODEL="provider/modelId"` — summarize with a different model (e.g. a fast
  local model) instead of the current session model. If the id cannot be resolved, the
  extension fails safely (see above).
- `PI_SUMMARY_REWRITE=off` (also `0` / `disabled` / `false`) — disable the extension
  entirely; Pi's default compaction runs.

## Environment variables

| Variable           | Default          | Meaning                                                        |
| ------------------ | ---------------- | -------------------------------------------------------------- |
| `PI_SUMMARY_MAX`   | `1500`           | Word ceiling. Integer clamped to `[300, 20000]`; invalid → 1500. |
| `PI_SUMMARY_FAIL`  | `cancel`         | `cancel` (keep context) \| `fallback` (default compaction).    |
| `PI_SUMMARY_MODEL` | *session model*  | `"provider/modelId"` override.                                 |
| `PI_SUMMARY_REWRITE` | *enabled*      | `off`/`0`/`disabled`/`false` disables the extension.           |

## Return contract

Verified against the hook consumer in Pi 1.4.0: the handler returns a
`SessionBeforeCompactResult` — `{ compaction: {...} }` on success, `{ cancel: true }` to
keep the context, or `undefined` to defer to default compaction. A bare `CompactionResult`
is **not** consumed and is never returned. `estimatedTokensAfter` is omitted because the
consumer recomputes it (and the built-in `compact()` doesn't set it either). Tokens/cost
from every generation call are accumulated (mirroring Pi's `combineUsage`) into
`compaction.usage`.

## Testing

Behavior is covered by a jiti-based harness sitting next to the extension,
`compact-rewrite.test.cjs`. It loads the **real** extension (the bare
`@earendil-works/pi-coding-agent` import is aliased to Pi's installed entry, so the actual
`convertToLlm`/`serializeConversation` run) and mocks only the model. It asserts **63**
cases:

- success + return contract (wrapper present, `estimatedTokensAfter` absent, file metadata)
- stream/options policy (requested `maxTokens`, `cacheRetention: none`, signal, reasoning pin)
- over-ceiling rewrite: fits, still-over → cancel/fallback, empty rewrite, rewrite sees the draft
- rewrite is draft-only (does **not** resend the conversation)
- manual compaction instructions (`event.customInstructions` in both prompts; absent when none)
- tool-call / output-cap / empty / error rejection; abort handling
- model override (hit, miss, no-slash) and model-unavailable
- cancel vs. fallback failure behavior
- ceiling clamping (down, up, invalid, default)
- the disabled opt-out (all four spellings)
- previous-summary folding
- split-turn prefix serialization (and its absence)
- usage accumulation across calls
- error safety: a sync throw **or** an async-rejected `result()`, on the first **or** second
call, returns the policy sentinel, never a throw

Run it from the extensions directory:

```
cd ~/.pi/agent/extensions
~/.local/share/pi-node/current/bin/node compact-rewrite.test.cjs
```
