---
node_id: f6461aa2-c36f-56cd-849d-1aca8d4ad908
slug: narrow-wave-7452
title: 'R1: usage-limit calls are void in the ot7 runner; six pre-restart calls classified, report fixed forward (ADR-355)'
created_at: '2026-09-15T04:51:51+00:00'
parents:
- keen-wing-6569
summary: ''
---
## What

R1 of the restarted ot7 charter (ADR-355): the frozen-design evidence runner now recognises a provider usage, session or credit limit and treats the call as **void** — no slot spent, receipts preserved, no further dispatch from that project — and the run's documents are rewritten forward so the six pre-restart calls are listed apart from design attempts and nothing is called exhausted.

- `docs/probes/ot7/runner/run.py`: `void_reason(transcript, envelope, stderr)` classifies a turn from what the runner already retains: a `rate_limit_event` frame with status `rejected`, a synthetic assistant frame tagged `error: rate_limit` (the shape of the two hand-copied F4 transcripts), an error result frame with HTTP 429 or limit text, or limit text in the CLI envelope's `error` field (stderr only when no envelope was written, so progress output can never void a completed turn). A limit that lands after the model has spoken is still void, flagged `cut_off_mid_turn` with the count of model messages before it. Classification ignores the child's exit code. In `run()`, a void row gets status `void`, `slot_consumed: false`, `continuations_used` held at the prior count, its measurement still read and hashed, no smoke, and the receipt gets status `void`, `slots_spent`, `void_calls` and a `retry` naming the fresh suffixed project (`retry_project_name`: `ot7-heron` → `ot7-heron-b`, `ot7-heron-repair` → `ot7-heron-repair-b`). The seeded-repair collector goes through the same loop, so a void repair leaves the seed untouched and points at a fresh seed copy. `run.py --classify TRANSCRIPT [ENVELOPE] [STDERR]` applies the rule read-only.
- `docs/probes/ot7/attempts/void-calls.json` (8,089 bytes): the six pre-restart calls classified by that rule from their retained transcripts, envelopes and stderr in the external projects; transcript digests match the report's table; none cut off mid-turn.
- `cli/tests/test_ot7_runner.py`: 13 new known-answer cases — a void create spends nothing and is not resumed; a void mid-turn continuation with exit code 0 keeps the two completed slots and stops; a void repair preserves the seed; a near-limit `allowed_warning` is not void and an unrelated provider error is still `interrupted`; the stream, legacy, envelope-only and stderr-only shapes; retry naming; and the six-call receipt.
- Docs rewritten forward, old wording kept and marked superseded: `runner/README.md` (new "Void calls (ADR-355)" section), `attempts/README.md`, `REPORT.md` (amendment section with a per-design table of void calls, attempts, unspent slots and retry project; F4–F7 rows; closing section), and an "Implemented in the runner" addendum to ADR-355 in `docs/DECISIONS.md`.

## Why

The critic's message for this iteration asked for exactly this: classify provider usage, session and credit limits, including mid-turn ones, as void; preserve receipts; consume no slot; stop further dispatch; fixtures; README and REPORT forward; include the seeded-repair collector. It is horizon rung R1 and the precondition for R2. It serves `mild-ledge-7157` (the ot7 charter) and the open F4–F7 and F10 nodes, whose recorded "exhausted" and "terminal incomplete" claims ADR-355 supersedes. No design turn was dispatched: R2 waits for the product agent's harness, and no role touches the loop lifecycle.

## Method

Read the six retained void calls in the operator's `cadex-projects` directory before writing any rule, and found two transcript shapes: the four collector runs carry `rate_limit_event {status: rejected}`, a `<synthetic>` assistant frame with `error: rate_limit`, and a result with `is_error`, `api_error_status: 429`; the two earlier hand-copied F4 session files carry only the synthetic assistant frame. The CLI envelope carries the limit text in `error` in all six. The classifier reads all three sources so either shape and a text-only failure classify the same way. Retry naming reuses the runner's existing `ot7-*` project rule, so `ot7-heron-b` already passes its checks; the runner still refuses an existing project, so a retry is never a resume (documented). Verified with the focused runner + prompt suites (51 passed) and the full CLI suite: 732 passed, 1 skipped in 526 s. A first `-x` pass stopped on `test_video.py::test_browser_revisits_history_beyond_video_cache_across_process_restart`; rerun alone it passes on this tree and on the stashed unchanged tree (32 s and 34 s), so it is a load-sensitive flake in the owner's dashboard area, untouched here, and the complete pass without `-x` was green. No engine, protocol, payload or shell change, so no build and no packaged gate; nothing under the dashboard paths was touched.

## Result

True now: a usage-limit call cannot spend a slot in the runner, the six pre-restart calls are classified void by code and listed apart from attempts, and every F4–F7 design has its create or repair prompt and all three continuations unspent. REPORT.md, the runner README and the attempts narrative say so and keep their 2026-09-14 text as superseded history. Ticks nothing; advances F4–F7 by unblocking R2 and F10 by fixing the report forward.

Assumptions: a rejected `rate_limit_event`, a `<synthetic>` rate-limit assistant frame, or an HTTP 429 error result is a usage limit even when the CLI exited 0; a transient 429 that ends a turn is treated the same way, because the turn did not end on its own. The runner cannot see the provider window, so "dispatch only while Claude is available" remains an operator rule, not a runner check.

Concern: a void continuation forces the design's retry to start again from its create prompt in a fresh project, because the runner refuses existing projects; the completed turns before the void remain that attempt's evidence. This is what the charter's "fresh project" retry rule says and is documented, but it makes a mid-attempt limit expensive. No new dependency.

Next: R2 — when the product agent's harness has room, dispatch the F4 repair on `ot7-heron-repair-b` (a fresh copy of the seed), then `ot7-heron-b`, `ot7-robin-b`, `ot7-plover-b` through their continuations as each fit report requires.

Dispatch closed: 1 unit — runner treats usage-limit calls as void (no slot, receipts kept, dispatch stopped), six pre-restart calls classified void by code, REPORT/README fixed forward under ADR-355.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 4505e21ffeb59fe217516cb1351d2564cb7082bd

## State Impact

- target: mild-ledge-7157 — the runner classifies usage/session/credit limits as void (no slot, receipts kept, dispatch stopped, retry project named); the six pre-restart calls are classified void by code in docs/probes/ot7/attempts/void-calls.json; REPORT.md, runner README and attempts README are rewritten forward with 2026-09-14 wording marked superseded; R1 done, R2 waits for the product agent's harness
- target: polished-forest-0215 — the three F4 calls are void, not attempts: repair prompt and all continuations unspent; retry is ot7-heron-repair-b on a fresh seed copy
- target: stormy-aspen-5433 — the one F5 call is void, not an attempt: create prompt and three continuations unspent; retry is ot7-heron-b
- target: narrow-dune-9454 — the one F6 call is void, not an attempt: create prompt and three continuations unspent; retry is ot7-robin-b
- target: rapid-grove-9687 — the one F7 call is void, not an attempt: create prompt and three continuations unspent; retry is ot7-plover-b
- target: first-snow-5587 — REPORT.md now opens with the ADR-355 amendment and a per-design table of void calls, attempts and unspent slots; its exhausted/terminal wording is kept and marked superseded; done acceptance still unmet
