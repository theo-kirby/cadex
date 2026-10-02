---
node_id: 8df81017-0f4a-557b-b5a4-4bf6f89779aa
slug: polished-shade-7671
title: 'orun1 D1 baseline (iterations 4-5, recorded late): runner and 10 of 26 held-out scores'
created_at: '2026-10-02T20:40:48+00:00'
parents:
- forest-sun-0304
summary: ''
---
## What

Catch-up record for Ouroboros iterations 4 and 5 of orun1, which committed
work (`97ca4c14`, `c432146d`) but wrote no record. The work was the first
half of the D1 baseline: ot10's frozen judge run unchanged over the orun1
held-out set.

- `docs/probes/orun1/runner/baseline.py` (new, commit `c432146d`): for each
  held-out design without `baseline/<id>-score.json`, copies
  `~/cadex-projects/sweep-<id>` to `orun1-ho-<id>` (originals read-only),
  draws ot10's input set with `render_set.py`, scores it with
  `docs/probes/ot10/runner/judge.py` unchanged, and writes the score with the
  render receipt. A scored design is never re-judged; a harness failure
  writes nothing and is re-run on the next invocation.
- `runner/render_set.py`: when `cadex render` exits non-zero, the error now
  carries the envelope's `error` field instead of empty stderr (diagnostic
  only; no change to what is rendered or judged).
- `.gitignore`: `__pycache__/`.
- 10 of 26 held-out designs scored (ot10 total 0–21): arm3-a-servo-joint 16,
  arm3-d-product-shell 16, arm5-d-product-shell 16, arm5-h-free 13,
  balancer-d-product-shell 18, balancer-e-hard-surface 16,
  balancer-f-creature 17, biped-c-exposed-mechanism 12,
  biped-d-product-shell 15, biped-e-hard-surface 14.

## Why

The critic's message for iteration 6 required this record before any
further scoring: unrecorded work is invisible to the project.

## Method

Read from git (`git show --stat 97ca4c14 c432146d`, the render_set diff
against `582f5237`) and the committed score files. No new measurement.

## Result

D1's baseline is in progress: 10 of 26 held-out designs scored once each by
ot10's frozen judge. No metric has been computed yet, and none should be read
from a partial set. Already visible, and not a result: the one held-out Love
in this set so far (`biped-c-exposed-mechanism`) scores 12, the lowest of the
ten — ot10's rubric rewards the finish the owner rejected.

Dispatch closed: 1 unit — catch-up record for the D1 baseline runner and its first 10 scores (iterations 4–5)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: c432146d55e400e1127bb203c2075049744e84ca

## State Impact

- target: idle-ledge-8635 — Baseline in progress: baseline.py runs ot10's frozen judge once per held-out design; 10 of 26 scored (commits 97ca4c14, c432146d); no metric yet
