---
node_id: 1e404883-5947-580c-a9a2-737e0eb363f9
slug: mild-crest-2685
title: 'ot9 B1: frozen Robin baseline, seeds 0-9 and the balance bar'
created_at: '2026-09-22T17:44:46+00:00'
parents:
- curious-branch-9704
summary: ''
---
## What

B1 of the ot9 charter: the frozen baseline and evaluation contract for training Robin to balance, written before any training run. `docs/probes/ot9/README.md` and its machine-readable twin `docs/probes/ot9/contract.json`, pinned by `cli/tests/test_ot9_contract.py` (commit `a80484a2`).

## Why

The critic named B1 as the next unit and the first rung of the short-term ladder (`twilight-flint-8205`). Done as asked, with one design choice the critic did not specify: the ten evaluation seeds are **0–9**, because the baseline script already declares `rollout_seed=num(0.0, min=0.0, max=9.0, step=1.0)` feeding `assembly.rollout(pol, seed=int(p.rollout_seed))`. Seeds inside that range make every evaluation episode the design's own declared rollout, run by the engine's `CadexDynamics.rollout_policy`, reached with `cadex params --set rollout_seed=S` — no actor script edit and no second rollout path. Seeds outside it (a first draft used 9001–9010) would have been refused by the parameter range. Deviation from the critic's message: the evaluation *command* is exact, but the reader that turns each seed's exported trace into peak tilt / min chassis height is declared in the README as its own unit with its own test, not written here, to keep this iteration one unit. The README says no evaluation is reported before it exists.

## Method

Read `ot8-robin` read-only (`/home/theo/cadex-projects/ot8-robin`; its git status was unchanged by this unit). Hashed `script.py`; read `script.json`; copied the accepted attempt's `result.json` and `outputs/` to /tmp and recomputed there: `CadexGeometryDigest.project_digest` reproduced accepted digest `b933d905…`; `staged_geometry_digest` under `build/release/bin/FreeCADCmd` gave `34898ebc…` identically in two processes. MJCF `933b1ac6…` and task `1f8c1040…` hashed from the accepted outputs, equal to the ot8 smoke receipt's. Read the task bundle for episode (400 steps, 50 Hz, 0.002 s × 10), actions (±92.18251 N·mm), termination (`fallen`: chassis_pos_z < 75.25 mm), reset variation (0–3° tilt, 3–5 mm) and reward. Checked `training/cadex_train.py`: training resets draw from split `jax.random` keys, not `random.Random(seed)`, and the task has no `randomisation`, so trainer runs never replay the evaluation seeds. Checked `assembly.rollout` defaults `frames_per_second` to `control_hz`. Wrote the contract and test; mutated one seed in the JSON and saw the test fail, then restored it.

## Result

B1's contract exists and is test-pinned. Baseline: `ot8-robin`, script `f805fdc2…`, accepted revision `0b438561…` = working, attempt `1789860047622-6f21a6af7553`, accepted digest `b933d905…`, geometry digest `34898ebc…`, MJCF `933b1ac6…`, task `1f8c1040…`, project git head `b75dd2d5…`. Evaluation seeds 0–9, frozen before any training. The bar: all ten seeds run 400 steps / 8.0 s at 50 Hz to truncation, never fire `fallen`, and stay within 30° of the accepted solved chassis attitude; one failed seed fails the candidate. Commands for copy, `cadex train … --put`, installation via the walk's digest edit (the script already has `policy_on` and a single `assembly.policy(weights="robin.cxpolicy", sha256="0…0")` with inline literals), and per-seed `cadex params --set rollout_seed=S`. Accounting table for completed / failed / interrupted / void training and evaluation runs. Tests: `cli/tests/test_ot9_contract.py` 5 passed; `test_licensing_compliance.py`, `test_ot8_runner.py`, `test_ot8_report.py` 44 passed, 1 skipped. Full suites not run (docs + one test file only).

Concerns for the next iteration: (1) `script.json`'s learned `accepted_geometry` in ot8-robin is stale (`4c75ff53…` keyed on `0a6fe0f5…`); the README records it as not the pin. (2) The trace reader (peak tilt, peak-tilt time, min chassis height per seed from `comp_chassis` poses) must land, with a fixture whose answers are stated first, before any B3 evaluation. (3) The tilt reference is the accepted solved attitude, not the post-variation reset pose; the reader must take it from the accepted assembly, as smoke's support check does. (4) The script's `pitch_penalty` reads `asin(qy)`; whether that is the topple axis is untested and belongs to the first training diagnosis, not B1. Next rung: prepare `ot9-robin`, reproduce the no-policy fall on it and export its training bundle. No new dependency.

Dispatch closed: 1 unit — B1 contract frozen: ot8-robin pins, seeds 0–9, 8 s/50 Hz/30°/no-fallen bar, commands and run accounting, test-pinned.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot9
- commit: a80484a2e0cd261b6143db14a4cc28c25d557e6f

## State Impact

- target: twilight-flint-8205 — B1's contract exists (docs/probes/ot9/README.md, contract.json, commit a80484a2): ot8-robin pinned from its own artifacts (script f805fdc2, revision 0b438561, digest b933d905, geometry 34898ebc, MJCF 933b1ac6, task 1f8c1040); evaluation seeds 0-9 frozen before training; 8 s/400 steps/50 Hz, 30 deg, no-fallen bar on every seed; train/install/evaluate commands; completed/failed/interrupted/void accounting; pinned by cli/tests/test_ot9_contract.py. The per-seed trace reader is still to land before any evaluation.
