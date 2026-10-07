---
node_id: 21a356cf-e6da-5acc-86d4-413d06a1cc66
slug: light-dusk-7651
title: 'ADR-578: the minute-boundary flake in the idle-stage test fixed and pinned'
created_at: '2026-10-06T23:11:41+00:00'
parents:
- peaceful-haven-5485
summary: ''
---
## What

ADR-578: the minute-boundary flake in
`cli/tests/test_review_status.py::test_designing_turns_idle_once_the_window_passes`
is fixed and pinned. The test wrote `saved_at` from one reading of the clock
and asserted `stage["since"]` started with the minute of a second reading; it
failed whenever a minute turned in between. It now asserts `since` equals the
one string it wrote, to the second, and runs a second time (parametrized
`across_a_minute`) with the test's `_clock` replaced by a ticking clock whose
2nd and 3rd readings straddle a minute. The server (`project_stage`) is
unchanged: it was right. The orun4 report's defect 4 now reads fixed, ADR-578
is in its ADR table, and its done claim is withdrawn until the CLI suite is
under 480 s and a reconcile has run.

## Why

The critic's next unit: "fix the minute-boundary flake. Freeze or inject the
clock, and pin the fix with a test that fails without it." Deviation: the
critic also asked for a reconcile pass first. This dispatch forbids reconcile
in a work iteration ("no exceptions"), so it was not run; the tail is now
three records (loyal-glacier-3687, peaceful-haven-5485, this one), which
meets the charter's three-unreconciled-records trigger for the separate
reconcile pass.

## Method

- Injected clock: module-level `_clock = time.time` read by the test's
  `_iso`; `_ticking_across_a_minute()` starts at floor(now/60)*60 - 1.5 and
  advances 1 s per reading. Windows widened to DESIGNING_WINDOW_S ± 120 s so
  a test clock up to 60 s behind the server's lands each case on the same
  side.
- Fails without the fix: a scratch copy with the old minute-prefix assertion
  under the crossing clock failed:
  `'2026-10-06T22:45:59+00:00'.startswith('2026-10-06T22:46')` → 1 failed,
  1 passed (the `wall` case). With the fix: 2 passed. The scratch copy was
  deleted.
- `test_review_status.py` whole: 19 passed in 28.6 s.
- CLI suite in three foreground thirds with the GPU hidden: see Result.

## Result

The flake is gone and a test fails on its return. No product code, protocol,
tool surface or doc other than the ADR log and the orun4 report changed, so
`pixi run test-engine` was not rerun (no engine file touched).

CLI suite, three foreground thirds with `CUDA_VISIBLE_DEVICES=`: NR%3==0 395 passed in 148.9 s; NR%3==1 324 passed, 1 skipped in 340.8 s; NR%3==2 491 passed in 230.8 s. Green: 1210 passed, 1 skipped (720.5 s of pytest time across the thirds).

Next unit (the critic's): cut the CLI suite below 480 s as one foreground
command under the owner note's keep/cut rules, one ADR with before and after
wall times (before: 614 s, the orun4 report §6). Then reconcile (a separate
pass), then claim done again.

Dispatch closed: 1 unit — ADR-578 fixes the idle-stage test's minute-boundary flake with an injected clock that fails the old assertion every time

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 26ef7350bd16f785739f0b7a816b33732dae51f4

## State Impact

- target: early-arbor-7123 — the CLI suite's known minute-boundary flake (test_designing_turns_idle_once_the_window_passes) is fixed by ADR-578: the test compares the one saved_at it wrote, and a parametrized case with an injected clock crossing a minute fails the old assertion every time; the orun4 done claim is withdrawn until the CLI suite is under 480 s and a reconcile has run
