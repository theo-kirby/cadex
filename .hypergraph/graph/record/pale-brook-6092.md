---
node_id: 7c021a6f-1762-5a8c-b3f2-86e2b79fd4d0
slug: pale-brook-6092
title: 'ADR-596: base guidance — choose a real sensor, close a linkage, state a motion as a predicate'
created_at: '2026-10-08T01:14:53+00:00'
parents:
- misty-water-8806
summary: ''
---
## What

ADR-596 (commit `67c15256`): three rules join the domain-neutral base guidance, each with its reason.

- **CHOOSE A SENSOR A REAL PART COULD BE** (`src/Mod/cadex/CadexAgentGuidance.md`): a free object's position via `position_tracker` on the reader's mount with datasheet figures, its `_in_range` flag as a termination (ADR-588); effort via `lib.servo(sku).load_sensor` only on an actuator that reports it, PWM refused (ADR-591); a goal on a moving base held in that base's frame (ADR-592); anything no market part measures is privileged, with the grounding part recorded in docs/sensors.md.
- **CLOSE A LINKAGE WHERE THE BUILT MACHINE WOULD HAVE ONE** (same file): why a serial stand-in is a different machine; when to close a chain vs stay serial (frame-mounted actuator, ratio/path, coupled outputs vs independent wide-range axes, dead point); a loop closes with an ordinary joint, drive on the grounded crank, the two refusals (ADR-593); motion proved by the smoke check (ADR-594), never the fit sweep.
- **STATE THE MOTION AS A PREDICATE, NOT AS WHERE IT ENDS** (`cli/cadex_cli/guidance.py`, after the reward rules): `assembly.success(body=, centre_mm=, centre=, centre_axis=)` bounding `turns`/`laps` and the distance metrics (ADR-587), no goal declared for a distance, early end fails. Replaces ADR-586's "count it in the evaluation's traces".

Also, first, per the critic: LESSONS.md W3 → "replaced (ADR-593..595)"; W12 → open, L1 landed but the bucket four-bar was not built (P2's optional item).

## Why

The critic's message: fix W3/W12, then long-term rung 1 (base guidance on sensor choice, linkage vs serial, motion predicates), phrased for any machine (A4). Done as asked; I also folded R1's goal frame into the sensor rule because it is the same question (what the policy can know), one sentence.

## Method

Read the existing base (`CadexAgentGuidance.md`, the overlay in `guidance.py`) and ADR-587..595 for the exact API, checked names against the orun5-ball-plate script (`position_tracker`, `tracked_position`, `b_in_range` termination, `final_distance_mm`). The engine guidance may not name a `cadex ` command (`test_the_guidance_carries_the_design_language_and_the_proof_rules` caught "`cadex smoke`" on the first engine run) — rephrased to "the smoke check". New tests in `cli/tests/test_agent_guidance.py`: one per rule pinning its claims and reason, plus that the hand-count sentence is gone; the reward-lessons test drops that sentence. `pixi run build-engine` after the md change.

## Result

True now: an agent with no style chosen is told how to ground a position and a load on real parts, when to build a closed linkage and how it is proved, and how to state a motion as a turns/laps/distance predicate. Gates at `67c15256`: `pixi run test-engine` 2673 passed, 60 skipped; `pixi run python -m pytest cli/tests` (CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu) 1225 passed, 1 skipped. No API, op, tool or protocol change.

The unreconciled tail is now 3 records (hidden-sand-7542, misty-water-8806, this one): the reconcile threshold is reached, and the critic asked for a reconcile next, then C1.

Dispatch closed: 1 unit — ADR-596 base guidance on sensor choice, closed linkages and motion predicates; ledger W3/W12 updated.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 67c152565bf9b99c0ffb0c67e8937dc4642aeabd

## State Impact

- target: chilly-union-8972 — the base guidance gains three rules (ADR-596, commit 67c15256): ground a position with a position_tracker and a load only on an actuator that reports it, privileged when no part measures it; close a linkage where the built machine has one, proved by smoke not the sweep; state a motion as turns/laps/distance predicates, replacing the hand-count sentence
