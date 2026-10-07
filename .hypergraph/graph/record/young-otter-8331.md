---
node_id: c461a379-57be-574d-9853-6310f93f27c9
slug: young-otter-8331
title: 'ADR-584: smoke''s first frame agrees to the MJCF pose precision'
created_at: '2026-10-07T17:45:46+00:00'
parents:
- windy-badger-4166
summary: ''
---
## What
`cadex smoke` judged the first frame against the MJCF with a float-noise tolerance, so a design exported at the MJCF's 0.01 mm pose precision could be refused at frame 0. The initial-pose tolerance is now derived from that precision: `INITIAL_POSE_TOLERANCE_MM = 2√3 × MJCF_POSE_TOLERANCE_MM` (ADR-584, commit 39ef9abf).

## Why
Found by a fresh design agent on a tracked excavator project: smoke refused a design whose disagreement was pure rounding.

## Method
`cli/cadex_cli/smoke_geometry.py` derives the bound; `_disagreement()` reports the measured gap. Test `cli/tests/test_smoke_geometry_bound.py`; docs/CLI.md updated.

## Result
Rounding-level disagreements pass; a real overlap (the excavator's tracks into the floor at 0.02 s) is still reported. Tests green at 39ef9abf.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: f49be9c36b2cfeb4f4caddf6d1e43245d1b6696e

## State Impact

- target: salty-isle-4063 — cadex smoke no longer refuses a design at frame 0 for MJCF rounding (ADR-584)
