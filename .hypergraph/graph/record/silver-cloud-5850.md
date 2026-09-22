---
node_id: c07ebba8-5be5-5090-ab94-83c553c6120f
slug: silver-cloud-5850
title: 'ot9 charter: train Robin to balance'
created_at: '2026-09-22T14:56:10+00:00'
parents:
- stormy-sand-3570
- rough-ridge-4729
summary: ''
---
## What

The owner directed ot9 to train Robin to balance. The charter at `.ouroboros/goal.md` and run configuration at `.ouroboros/config.yml` now define that experiment; ADR-404 records the direction change.

## Why

ot8 measured Robin's zero-command fall and found adequate actuator authority but missing feedback [rec: stormy-sand-3570]. Its closing report separated that control-blocked outcome from the arm and biped successes [rec: rough-ridge-4729]. The owner selected trained policy control, the declared eight-second episode, ten reset seeds, and permission for the product agent to change mechanics, task and reward without weakening the behavioral bar.

## Method

Read the ot8 report and G4 diagnosis, the prior charter/configuration, the product vision and training contract. The owner selected Fable 5.1 with Codex fallback for Ouroboros roles, retaining the 48-hour ceiling and two accepted done verdicts. Wrote five measurable criteria (baseline, policy, ten-seed behavior, mechanical review, regression/report), a three-rung ladder, constraints, question and exhaustion policies. The headless product CLI uses Claude alone, so product calls remain on Fable 5.1; the role fallback does not silently change product-model evidence. Updated `.ouroboros/AGENTS.md` to reflect the new setup.

## Result

Charter and config committed at `c7aea2db` with ADR-404. No ot9 loop was launched or training run performed. Success is an accepted witness-verified policy that completes all ten fixed 8-second evaluations within the existing 30-degree and `fallen` limits; a completed training job by itself is insufficient.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: c7aea2db70269d2d4e5a55f277856e39e2564324

## State Impact

- target: NEW ot9-robin-trained-balance — Owner-directed ot9 will train Robin under the accepted eight-second task and measure ten fixed reset seeds against the existing 30-degree and fallen limits; charter and configuration are committed, run not launched.
