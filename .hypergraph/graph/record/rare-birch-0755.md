---
node_id: 82815b08-6204-5db7-9ff5-7e1aab2b953d
slug: rare-birch-0755
title: 'F4: the frozen repair prompt reached the model on a fresh seed copy and timed out at the 30-minute bound with no submission'
created_at: '2026-09-15T05:41:07+00:00'
parents:
- vast-river-7582
summary: ''
---
## What

The first F4 product-agent call that reached a model. With Claude available (a one-word probe with the runner's model name `claude-fable-5` answered in 5.4 s), the frozen repair prompt (`5d846901…`, 830 bytes) was dispatched once through `docs/probes/ot7/runner/run.py repair` on `ot7-heron-repair-b`, a fresh copy of the seed `ot7-heron-repair` with its `evidence/`, `agent.json` and CLI lock excluded, validated by the runner's `validate_seed` before dispatch. The turn was killed by the runner at its 30-minute bound with **no submission, no design edit, no revision and no acceptance**. Committed: the receipt `docs/probes/ot7/retained/repair-timeout-b.json` (11,180 bytes), and the closing report, the retained index and the runner README written forward. No product code changed; no design was edited by the actor.

## Why

The critic asked for exactly this: run the F4 measurements-only repair on a fresh suffixed seed copy with the frozen prompt, only while Claude is available, preserving per-turn fit reports, timings and transcript digests. Claude was available (this actor was running on it and the probe answered), so the design turn was dispatched rather than a tooling unit. Advances F4 (`polished-forest-0215`): F4 now has its first measured product-agent result instead of only void calls.

## Method

1. Read the runner (`run.py`), its README, the frozen prompts and the iteration 39 receipt; confirmed the repair mode needs an existing `evidence/` directory and refuses an existing `evidence/f4-repair/`.
2. `rsync` the seed to `ot7-heron-repair-b` excluding `evidence/`, `agent.json`, `.cadex-cli.lock`; created an empty `evidence/`; ran `seed_identity` + `validate_seed` from the runner module: script `3339a178…`, accepted revision `7e9eff5c…`, digest `ce35f4d3…`, empty overrides — valid.
3. Probed `claude -p "Reply with the single word ok." --model claude-fable-5 --max-turns 1`: answered in 5.4 s, no limit. The probe is not a frozen prompt and spent no slot.
4. Dispatched `pixi run python docs/probes/ot7/runner/run.py repair ~/cadex-projects/ot7-heron-repair-b --model claude-fable-5` at 05:07:22 UTC; watched its tool-call log; the runner exited 0 at 05:37:22 UTC.
5. The runner's `transcript.jsonl` was missing and the envelope empty (the child was killed before either was written), so the provider stream was recovered unmodified from the Claude Code session store for the project directory and copied to `evidence/f4-repair/recovered/session-e813a990.jsonl` (698,175 bytes, SHA-256 `56e8101172d23fa3d6beafc4a2718592ceae62071fb6fe1d6ac94b5c413d25ca`). The receipt names it as recovered, not as the runner's capture.
6. Built the committed receipt from `attempt.json` plus the recovered stream; wrote REPORT.md, `retained/README.md` and `runner/README.md` forward; ran `cli/tests/test_ot7_prompts.py`, `test_ot7_runner.py`, `test_retained_fit.py`.

## Result

**What is true now.**

- The guarded before-read on the fresh copy reproduced the retained baseline exactly: 105 pairs, **15 failures**, `comp_horn_shoulder`/`comp_upper_arm` at 0.19999999999999732 mm and `comp_horn_elbow`/`comp_forearm` at 0.19999999999993 mm (missed contact under the collector's attachment assessment), the 248.20162986795066 mm³ servo/cheek overlap, the collision plane on `comp_base`. Seed unchanged by the read (0.164 s).
- The model saw the prompt and used **17 tool calls, all reads**: clearance (summary, then pairs in three pages of 50), script, `describe_api`, seven pages of the assembly and library API, the script source in two pages, the library and part exports. It read the measured fit first, which is the F1 behaviour the run built. It **never called submit** and emitted no text.
- After the fifteenth read (05:12:25 UTC) it produced one message of **64,000 output tokens, 63,999 of them thinking**, ending on the provider's output cap (`stop_reason: max_tokens`) at 05:29:03 with no text and no tool call; then two more reads; then it was generating again when the runner killed the process group at **1,800.0 s**. Usage over 16 API messages: 82,904 output tokens, 746,388 cache-read and 94,540 cache-write input tokens.
- After the call: script SHA-256 `3339a178…` unchanged, accepted revision `7e9eff5c…` unchanged, after-read 105 pairs / 15 failures byte-for-byte the same verdict; only `latest_candidate` and `updated_at` changed in metadata (ordinary restore). Attachment assessment `fail` before and after. Zero completed design turns, zero actor design edits, zero continuations.
- **Not a void call**: no usage, session or credit limit appears anywhere in the stream, envelope or stderr; the runner's `void_reason` returned null. Under the runner's documented rule the turn is `interrupted` with `slot_consumed: true` and `slots_spent: 1`; `void_calls: 0`.
- Tests: `test_ot7_prompts.py`, `test_ot7_runner.py`, `test_retained_fit.py` green (see the commit's verification line). No engine, CLI, protocol or payload code changed, so no build or packaged gate ran.

**Concerns and assumptions the next iteration must know.**

1. **Slot accounting is an owner ruling, not decided here.** The runner's rule (tested, documented) counts a timeout as a consumed slot. The charter voids only provider usage, session or credit limits and counts "a turn that reached the model and ended on its own"; a runner-bound kill is neither. I did not re-dispatch on `ot7-heron-repair-c`, because a retry spends provider budget irreversibly while treating the slot as spent is reversible by a ruling. If the owner or critic rules the timeout a non-turn, the same frozen prompt goes to `ot7-heron-repair-c`, a fresh copy of the seed, only while Claude is available.
2. **Two collector defects, named and not fixed (one unit):** (a) `CapturedTurn.run` writes `transcript.jsonl` only after `ClaudeTurn.run` returns, so a timeout kill loses the stream; write frames as they arrive. (b) The CLI passes no thinking or output bound to Claude (`cli/cadex_cli/agent.py` `_command`), so one silent 64k thinking burst can eat 16.5 of 30 minutes; a per-message bound (e.g. a thinking budget) or a longer turn bound is a product decision to make **before the next design turn**, F5–F7 included, or they will meet the same wall. The recovered-stream fallback is a stopgap, not a rule.
3. **Assumption:** the Claude Code session store under the harness's projects directory is an unmodified copy of the provider stream; it was copied after the kill and its digest is in the receipt. Its `thinking` blocks are redacted to signatures by the harness, so the content of the 63,999 tokens is not recoverable.
4. Charter compliance: the actor edited no design; the probe was not a frozen prompt; no role stopped or started the run; committed receipt under 16 KB; no machine paths in committed files (the project is cited by name).
5. The unreconciled tail is now three records (`narrow-wave-7452`, `vast-river-7582`, this one): the critic's message says reconcile is next.

Dispatch closed: 1 unit — F4's frozen repair prompt reached the model once on a fresh seed copy and timed out at the 30-minute bound after 17 reads and a 64k thinking burst with no submission; seed unrepaired at 15 failures; receipt, report and READMEs written forward; slot ruling left to the owner.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: a5aa712511c9ddcb4c1c8d2f7135a12f1da7ffe9

## State Impact

- target: polished-forest-0215 — F4 now has one call that reached the model: ot7-heron-repair-b, killed at the runner's 30-minute bound after 17 reads and one 63,999-token thinking burst capped at the output limit, with no submit call; script, revision and the 15-failure fit are unchanged; not void (no limit seen); the runner counts the repair slot consumed, the owner rules whether a runner-bound kill is a turn that ended on its own; two collector defects named: stream lost on kill, no thinking or output bound
- target: mild-ledge-7157 — the agent half of the run has its first measured result: the repair turn ran out of time thinking rather than submitting; before any further design turn (F4 retry or F5–F7) the CLI needs a per-message thinking or output bound and the collector must write frames as they arrive
