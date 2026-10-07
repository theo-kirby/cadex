---
node_id: cfe43b0c-94ab-54e9-8ef4-343fa1c75ac7
slug: wise-lodge-1163
title: 'ADR-586: evaluate survives early-ended reach episodes; reward lessons for any task'
created_at: '2026-10-07T17:45:47+00:00'
parents:
- windy-badger-4166
summary: ''
---
## What
`cadex evaluate` crashed with `max() arg is an empty sequence` when an episode terminated before a reach segment's final window; now that segment's final error is None and a spec bounding it fails as "not measured". The base guidance gains a reward-shaping section for any task (ADR-586, commit f49be9c3).

## Why
Found by a ball-balancing plate project (circle-2 policy, an early-ended seed) and confirmed on main at `CadexEvaluation.py:604`. The guidance lessons cost the ball-plate and excavator agents one to four training runs each: bell-shaped costs flat at the start state collapsed training; an `abs(v-V)` cost passed a rocking policy; two sharper precision terms left a ~20 mm reach floor unchanged; slew reaction skated a floor-resting base until `command_slew_deg` limited it.

## Method
`reach_metrics`: `max(final) if final else None`. Test `test_an_episode_that_ends_before_the_final_window_is_not_measured` raises the old ValueError without the fix. `cli/cadex_cli/guidance.py` section SHAPE A REWARD THE POLICY CAN CLIMB, pinned by `test_the_reward_shaping_lessons_are_for_any_task`; project-name patterns extended.

## Result
Engine suite 2619 passed / 59 skipped; CLI suite 1217 passed / 1 skipped (GPU hidden). The capability gaps the projects exposed (free-body position sensor, actuator load sensor, closed linkages, motion predicates, body-frame goals) are chartered as orun5, not done here.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: f49be9c36b2cfeb4f4caddf6d1e43245d1b6696e

## State Impact

- target: damp-flame-5523 — evaluate marks a reach seed that ended before its final window as unmeasured and failing instead of crashing (ADR-586)
- target: pale-arrow-4660 — base guidance carries reward-shaping lessons for any task (ADR-586)
