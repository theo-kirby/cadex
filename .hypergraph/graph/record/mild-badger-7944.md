---
node_id: 13c4752e-24c9-5948-bb9e-2485458598cb
slug: mild-badger-7944
title: 'progress.json learns the curve: 512 pairs, additive, schema unchanged'
created_at: '2026-08-29T12:21:30+00:00'
parents:
- stormy-cedar-1763
summary: ''
---
## What

Phase 2 of the local-training-loop round (commit 7c10192c): the trainer's
`progress.json` now carries the reward curve itself — compact
`[iteration, reward_per_step]` pairs, decimated to `CURVE_POINTS_CAP`
(512) with the endpoints always kept — as an additive field under the
unchanged `cadex-training-progress-v1` schema.

## Why

The Training panel showed numbers, never a shape. `report()` in
`training/cadex_train.py` already received the full curve every iteration
and discarded all but the last point; publishing a capped copy is what
lets the shell draw a plot (Phase 3) with zero protocol or engine change.

## Method

- `decimated_curve(curve, cap)` — pure stdlib, uniform stride via
  `round(index * last / (cap - 1))`, first/last always kept, empty → `[]`,
  under-cap curves pass through verbatim. ~12 KB of JSON at the cap.
- Additive on the exact precedent of `episode_steps` (ADR-101) and
  `action_std` (ADR-103): the shell's `read_progress` validates only the
  schema string, and no existing test pins the payload key set (verified
  before writing).
- Tests in `test_dynamics_policy_trainer.py`: a static half unit-testing
  `decimated_curve` (runs under pixi, no jax), and a venv-gated half that
  trains 3 real iterations and asserts the pairs land in order with the
  last equal to `reward_per_step`.
- `training/README.md` example payload updated, dates bumped.

## Result

- pixi trainer suite: 29 passed / 8 skipped. Venv trainer suite: 37
  passed. Full engine suite: 1910 passed / 46 skipped.
- The ADR for this lands with Phase 3 (the plot), which is the
  user-visible half of the same change.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: local-training-loop
- commit: 7c10192c5dc727f6c93a836165d3fa1fad60f496

## State Impact

- target: late-pond-2851 — progress.json now publishes the decimated reward curve (curve field, cap 512, schema unchanged), the data the Training editor's plot draws.
