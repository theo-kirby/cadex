---
node_id: b8e3ad7d-b3a9-5113-9b5f-7f91ae951f11
slug: shady-bay-0771
title: 'D6 restart test recorded: dashboard restart under independent telemetry (commit 38c35f6a)'
created_at: '2026-09-12T17:00:05+00:00'
parents:
- ready-orchard-4806
summary: ''
---
## What

Handoff record for the D6 restart test that landed as commit `38c35f6a`
("Test the review dashboard across a restart under independent training
telemetry") without a record node. `cli/tests/test_review_lifecycle.py` runs
the real `cadex review` command against a fixture project, opens it in
headless Chromium, selects a run whose telemetry an independent producer
process commits every 0.3 s, stops the command with SIGINT, checks the open
page reads stale with its identities and video element intact, restarts on
the same port and checks the page returns to live without reloading with the
same run, revision, advancing curves and a decodable, byte-identical video.
A fresh page against the restarted server reads the same accepted revision,
run list, historical label, parameters, telemetry and downloadable video.
The producer keeps its PID, never resets its iteration sequence and is the
only process carrying its marker; every project file other than its own
snapshot has the same digest afterwards. `docs/CLI.md` and `docs/ROADMAP.md`
say what this proves and what remains open.

## Why

The critic asked for this causal handoff record before any new unit: the
previous iteration committed the test but stopped without recording it, so
D6 (`clever-field-7845`) had evidence on the branch that the graph could not
see. Recording it now makes the fixture half of D6 visible and states its
limits, so the next reconcile folds a true claim rather than "no evidence".

That iteration also made one more product-agent creation attempt on the
fresh biped (`ot5-biped/evidence/retry-8.*`, 12:14 local), refused again
before authoring with the same `claude-fable-5` session-limit message; it is
recorded here because the record it belonged to was never written.

## Method

Re-ran the landed test and the suites it sits in, in this iteration:

- `pixi run python -m pytest cli/tests/test_review_lifecycle.py -q`:
  1 passed in 7.40s (headless Chromium and FFmpeg present, so it did not skip).
- `pixi run python -m pytest cli/tests -q`: 353 passed, 1 skipped in 286.78s (the previous 340 + 1 plus the tests the D6 commit and the intervening telemetry work added; no failure).
- `git show --stat 38c35f6a`: four files, 296 insertions, 4 deletions; the
  only non-test changes are the two doc paragraphs.

No product code changed in this iteration for D6; no dependency added.

## Result

D6 now has its automated fixture half: restarting the dashboard during
training neither stops nor duplicates the training it observes, and the
restarted server serves identical identity, specs, run history, curves and
video. What the criterion still requires and this does not give:

- No engine runs anywhere in the test, so "restarting the engine" is only
  argued (the reader opens none), not exercised against a real project.
- Save/reopen of a project a real walk wrote, and the recorded pass on the
  fresh biped with real training artifacts, remain open. The biped itself
  has no accepted revision yet (three quota refusals: `create`, `retry-7`,
  `retry-8`).
- The stale-then-live transition is asserted against the page's own poll,
  at the fixture's 0.3 s producer cadence; no measurement of the recovery
  time at a real trainer's cadence exists.

Dispatch closed: 1 unit — record the D6 restart test (commit 38c35f6a) and its limits.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 38c35f6a7fd4af3b002c72ea1e55e00f29f1bc38

## State Impact

- target: clever-field-7845 — The automated fixture half of D6 exists: cli/tests/test_review_lifecycle.py (commit 38c35f6a) restarts the real cadex review command during independent telemetry writes and proves the open page recovers without reload, a fresh page reads the same identity/specs/runs/curves/video, the producer is neither stopped nor duplicated, and no project file changes. Still open: engine restart is only argued (no engine runs in the test), save/reopen of a real walk's project, and the required pass on the fresh biped with real training artifacts. Suite: 353 passed, 1 skipped.
