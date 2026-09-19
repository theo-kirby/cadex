---
node_id: 76270571-8b4c-5d8f-8f83-c202bd7c7160
slug: cool-grotto-2512
title: The turn bound is an hour, a dead runner finalises, and F7 is live on plover-d
created_at: '2026-09-19T18:57:29+00:00'
parents:
- strong-hollow-7483
summary: ''
---
## What

Two measured gaps in ot7's evidence collector closed (ADR-388), and F7's
frozen create prompt dispatched into `ot7-plover-d` on Opus under the result.

1. **`TURN_BOUND_SECONDS` 1800 → 3600 s.** Create turns cost more the larger
   the design: Heron 1,530.4 s at 120 static pairs, Robin 1,676.4 s at 276,
   Plover 1,800.0 s at 435 — and the last *is* the old bound, reached
   mid-repair. A ceiling just above the largest measurement buys another
   interruption, so it doubles. `dispatch` now stamps the bound onto the
   receipt and every row at each invocation, and `classify`/`interruption`
   read the row's own bound, so a pre-ADR-388 kill is still ruled against
   1,800 s and cross-design timings stay comparable.
2. **`reclassify` finalises a runner that died.** `dispatch` persists a row as
   `started` before launching the child and rewrites it when the child
   returns; a runner killed in between leaves `status: running` with no
   outcome, which is what iteration 154 left on `ot7-plover-b`. New
   `abandoned()` rules such a row an ADR-356 interruption with
   `kind: runner_died` from the receipt's own mtime — silence longer than the
   turn's whole budget (its bound + measurement + a 600 s grace) is proof no
   live runner holds it. A row that could still be in flight is untouched.
   Since finalisation happens late, `retry_project_name` now takes the parent
   directory and skips the letters already taken.

Also, per the critic: one paragraph added to record `silent-rose-4316` naming
the authorisation for ADR-387's dashboard work.

## Why

The critic's named unit. F7 is the last unattempted design criterion, its
retry project was `ot7-plover-d`, and iteration 155 measured that a retry at
the same 30-minute bound had no reason to end differently. The stale
`ot7-plover-b` receipt was the other thing blocking a clean F7 row in the
closing report: it read `status: running` and counted nothing.

On the critic's first item: the charter reserves the dashboard,
`docs/REVIEW-DESIGN.md` and the operator review service for the owner, and
ADR-387 touched all three. I checked before writing rather than asserting an
authorisation. Commit `b5194827` landed at 18:12:31 UTC, between iteration 154
(which committed nothing; its sha stayed `406835d5`) and iteration 155's two
commits, and neither `0154-actor.json` nor `0155-actor.json` mentions
`operator_review`. So it was the owner's own session outside the loop, acting
on their own request — the reservation is intact for unattended roles, and the
record now says so with that evidence.

## Method

`docs/probes/ot7/runner/run.py`: the constant, `STALE_GRACE_SECONDS`,
`abandoned()`, `turn_bound()`, a sibling-aware `retry_project_name()`, the
per-row bound in `dispatch` and `classify`, and the stale-row branch in
`reclassify`. Three fixtures in `cli/tests/test_ot7_runner.py`: the bound
pinned against the three measured create turns and threaded to the child
timeout and both receipt levels; the `ot7-plover-b` shape reproduced by an
executor that raises mid-turn, asserting a fresh receipt is left alone and a
backdated one finalises, is idempotent, and names its retry; and the retry
naming past taken letters. ADR-388 in `docs/DECISIONS.md`; both README
sections and the REPORT's F7 section updated with the measurements.

Then `run.py reclassify ~/cadex-projects/ot7-plover-b` on the real project,
and the committed receipt `docs/probes/ot7/attempts/plover-b-runner-died.json`
(2.7 KB). Then a window probe, then the dispatch.

## Result

`ot7-plover-b` is finalised: `interrupted`, `kind: runner_died`, silent
2,769.2 s against a 2,700 s budget (the 1,800 s bound *it* ran under), 10
model messages before the kill, 0 slots spent, retry `ot7-plover-d`. Its
stale copy is kept as `attempt.superseded.json`. F7 still holds its create
prompt and all three continuations.

**F7's create prompt is dispatched and live** in `ot7-plover-d` on
`claude-opus-5`, effort `medium`, detached: the probe read `allowed` at 33 %
of the five-hour window against the unchanged 45 % gate, and the receipt
records `turn_bound_seconds: 3600` at both levels. Logs: `/tmp/plover-d-run.json`,
`/tmp/plover-d-run.err`. **Its outcome is for the next iteration to collect** —
read `~/cadex-projects/ot7-plover-d/evidence/attempt.json`.

A new measurement the next iteration should keep: an Opus create turn costs
far less window than the Fable turns the 45 % gate was calibrated on.
`ot7-plover-c` started at 14–15 %, ran the full 1,800 s, and the window read
31 % after — about 17 points per half hour, against 49 for one Fable turn. So
a 3,600 s Opus turn from 33 % projects to roughly 67 %, and the window resets
at 21:10 UTC. The gate is left at 45 % on that evidence rather than lowered
for the doubled bound; if a 3,600 s turn ever *is* cut off by the session
limit it is void under ADR-355 and costs no slot.

Verification: `pixi run python -m pytest cli/tests` — **842 passed, 1
skipped** in 533 s (the whole suite, run while the design turn competed for
CPU); `test_ot7_runner.py` alone is 92 passed. No engine, CLI, protocol or
acceptance behaviour changed, so no engine suite or packaged gate applies.
`git diff --check` clean. Committed as `ab3a2f12`.

Concern for the next iteration: the tail is now three unreconciled records
(`silent-rose-4316`, `strong-hollow-7483`, this one) and the reconcile trigger
is three. But the live F7 turn's collection outranks it — collect first.

Dispatch closed: 1 unit — the turn bound is an hour, a dead runner finalises, and F7's create prompt is live on `ot7-plover-d` (ADR-388).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: ab3a2f124b3cfbb5bc92f59c6820ef6eee4c681e

## State Impact

- target: rapid-grove-9687 — F7's retry is dispatched: the frozen create prompt is live on ot7-plover-d (claude-opus-5, effort medium, probe allowed at 33 %) under the raised 3600 s turn bound; ot7-plover-b is finalised as an ADR-356 runner_died interruption with 0 slots spent, so F7 still holds its create prompt and all three continuations
- target: chilly-union-8972 — The ot7 collector's turn bound is 3600 s and stamped onto the receipt and every row at each invocation, so classify rules a pre-ADR-388 kill against the bound it ran under; reclassify now finalises a row left at started when the runner itself died, ruled from the receipt's own mtime against the turn's whole budget, and retry_project_name skips letters already taken (ADR-388)
