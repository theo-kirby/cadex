---
node_id: d3b01ec6-0b52-5b40-b919-08c2dabd5ba3
slug: spring-ivy-9833
title: 'orun1 D4: plain prompts frozen; balancer trial 1 (9/9 held, v2 3 of 5, sweep blocked by catalog shaft)'
created_at: '2026-10-03T03:15:49+00:00'
parents:
- gentle-badger-9718
summary: ''
---
## What
D4's first step for orun1. The seven plain prompts are frozen in `docs/probes/orun1/runner/prompts.py` (sha256 `f69ab5c8…`). `README.md` § "D4: the plain prompts" quotes them, and `runner/test_prompts.py` holds the two copies equal. This landed in commit `bd3bbb0d`, before any generation. The same commit added `runner/versus.py`, which judges a new design with frozen v2 against the sweep designs of its type rated Like or Love, and refuses to run unless the opponent heroes hash to the ones D1 judged. Then one supervised **trial** (commit following `bd3bbb0d`): `orun1-t1-balancer`.

## Why
Following the critic's message, D4 is the highest-ranked open criterion with work available. The prompts had to be frozen before any generation. I picked the balancer for the trial: highest type mean (1.75), and it has a Love. **Deviation:** the critic asked me to reconcile in this iteration. The dispatch rules forbid reconcile in a work iteration, with no exceptions, so I did not. The tail is now three records (solemn-arbor-0802, gentle-badger-9718 and this one), and a reconcile is due next.

## Method
- Prompts: each names the type, a joint count and "Design only: no training task, policy or rollout". There are no style words (test-checked against a list). The wildcard is fixed as an 8-joint snake. The turn settings are frozen as `claude-opus-5-5`, effort `medium`, the sweep's.
- Trial: `CADEX_EFFORT=medium ./cadex -p "<frozen balancer prompt>" --project ~/cadex-projects/orun1-t1-balancer --model claude-opus-5-5 --json`. The turn took about 6 minutes and ended on its own.
- Hero via `runner/render_set.py`, run on a copy `orun1-t1-balancer-render`, because render re-accepts. Then `runner/versus.py balancer …`.
- Tests: `pixi run python -m pytest docs/probes/orun1/runner` gives 18 passed.

## Result
- Accepted revision `8dd43825…`. The design is faceless: chamfered side plates, decks, ESP32 in a bay, IMU, regulator and VL53L1X screwed in, N20 motors screwed to the plates, Pololu 1430 wheels.
- **Mounting `pass`: 9 of 9 held.** All purchased parts come from the catalog. **Static fit:** 861 pairs, 0 failing.
- **Swept fit `incomplete`, which does not meet D4.** The wheel joints are continuous. The agent measured 4.26 mm³ between the turning wheel bore and the catalog gearmotor's static D-shaft at ±180°. That is a product defect: no catalog wheel on its catalog motor can pass a sweep.
- **Frozen v2: 3 of 5 wins (majority).** It beat the d, f and h Likes and lost to c (Love) and e (Like). Both losing reasons cite "plain, featureless disc wheels with no visible hub". `WHEELS["pololu-1430"]` is a solid disc by declared approximation. Cost $0.19. Published in `docs/probes/orun1/d4/t1-balancer/` (hero 131 KB, pairs, summary).
- It is a trial, not a confirmation, and it counts for nothing toward D4.
- Next units (product changes, never prompt changes): (1) the motor shaft must turn with the wheel, or the sweep must exclude the wheel–shaft pair, so a wheeled design can pass a sweep; (2) model the 1430 wheel's rim, hub and tyre from its STEP or drawing so it is not a slab.
- The reconcile is overdue: 3 unreconciled records.
- Assumption: held-out sweep designs used as D4 opponents is what the charter prescribes, and it tunes nothing.

Dispatch closed: 1 unit — D4 prompts frozen and pinned; balancer trial 9/9 held, static clean, sweep incomplete (catalog D-shaft), v2 3 of 5

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: dbc0c544d8745badd661c6f2dc73365c5f2d7b88

## State Impact

- target: salty-fox-7376 — the seven plain prompts are frozen and hash-pinned (runner/prompts.py, f69ab5c8…) with runner/versus.py as the frozen-v2 bar; trial 1 orun1-t1-balancer: mounting 9/9, static fit 0 failing, swept fit incomplete because the catalog gearmotor's static D-shaft meets the turning wheel, v2 3 of 5 with both losses citing the solid-disc catalog wheel
