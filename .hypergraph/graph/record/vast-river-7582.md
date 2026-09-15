---
node_id: f7700321-13a1-5aaf-88c9-b650556fc1f1
slug: vast-river-7582
title: 'ot7 runner: a synthetic frame alone is not a usage limit; auth failures spend their slot (ADR-355 correction)'
created_at: '2026-09-15T05:05:13+00:00'
parents:
- narrow-wave-7452
summary: ''
---
## What

Corrected `void_reason` in `docs/probes/ot7/runner/run.py` (ADR-355): a synthetic assistant frame is no longer classified as a usage limit by its `<synthetic>` model name alone. The frame now counts as limit evidence only when it is tagged `error: rate_limit` or its text content matches the limit-text pattern. A synthetic frame never counts as a model message either, so `model_messages_before_limit` cannot be inflated by CLI-authored frames. `cli/tests/test_ot7_runner.py` gains a negative fixture: an `authentication_failed` synthetic frame with a 401 result and matching envelope text classifies as not void, and through `runner.run` it spends its slot (`slots_spent == 1`, `void_calls == 0`, no retry). The same test pins that an untagged synthetic frame carrying limit text is still a limit. The runner README's fixture list and ADR-355 carry a correction paragraph.

## Why

The critic rejected iteration 42: `model == '<synthetic>'` alone returned `usage_limit` and refunded the slot for an `authentication_failed` frame, which it reproduced directly. This is the fix the critic asked for, done as asked: explicit limit evidence required, negative synthetic-error fixture added beside the rate-limit case, CLI suite run, correction recorded before R2. Serves the ot7 charter root `mild-ledge-7157`: R2 (dispatching F4–F7) must not rest on a classifier that could void a non-limit failure. Targets the frontier nodes F4–F7 indirectly by keeping their slot accounting honest.

## Method

Read the retained signal shapes in `docs/probes/ot7/attempts/void-calls.json`: all six pre-restart calls carry `error: rate_limit` on their synthetic frame, so the tightened rule loses nothing. Changed the assistant-frame branch to `error == 'rate_limit' or (synthetic and LIMIT_TEXT matches the frame's text)`, with a small `frame_text` helper joining text blocks; synthetic frames are excluded from the `spoke` count. Verified the new test fails on the old code (stashed `run.py`: 1 failed), passes on the new (47 passed in the file). Reclassified all six retained calls from `~/cadex-projects` with the new code: transcript digests and `void` blocks identical to the committed receipt, so `void-calls.json` needs no change. Full CLI suite: 733 passed, 1 skipped in 525.74 s (the skip is the pre-existing engine-needing case).

## Result

The runner now voids a call only on explicit limit evidence: a rejected `rate_limit_event`, an assistant frame tagged `error: rate_limit` or a synthetic frame whose text names a limit, a 429 or limit-text error result, or limit text in the envelope or stderr. Authentication and other synthetic errors are ordinary provider failures: slot spent, status `interrupted`, no retry named. The six retained void calls classify unchanged. Docs match code: README fixture list and ADR-355 correction paragraph. No new dependency. No design turn was dispatched; R2 remains next, and only while Claude is available. The unreconciled tail is now two records (`narrow-wave-7452` and this one).

Dispatch closed: 1 unit — void_reason requires explicit limit evidence; synthetic auth failures spend their slot; negative fixture pinned; six retained calls unchanged.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 29605b5769e4f46a3e3647f5e3bbe202a8c0b309

## State Impact

- target: mild-ledge-7157 — The ot7 runner voids a call only on explicit limit evidence (a rejected rate_limit_event, an assistant frame tagged error: rate_limit or a synthetic frame whose text names a limit, a 429 or limit-text result, or limit text in the envelope or stderr); a synthetic authentication_failed frame is an ordinary provider failure that spends its slot, pinned by a negative fixture that fails on the old code. The six retained pre-restart calls classify unchanged. CLI suite 733 passed, 1 skipped. R2 remains next, dispatched only while Claude is available.
