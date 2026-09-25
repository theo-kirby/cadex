---
node_id: e550e75f-09e8-5284-84f4-bd971572e860
slug: windy-tide-4050
title: 'ot9 rung 2: ot9-robin prepared, balance reader, no-policy fall reproduced'
created_at: '2026-09-22T18:08:23+00:00'
parents:
- mild-crest-2685
summary: ''
---
## What

Short-ladder rung 2 of ot9, with the per-seed trace reader folded in as the critic asked (commit `9bba56cf`). `ot9-robin` was prepared as a mechanical copy of `ot8-robin` and checked against every B1 pin; `docs/probes/ot9/runner/balance_eval.py` reads a seed's trace against the bar and is pinned by `cli/tests/test_ot9_balance_eval.py`; the no-policy fall was reproduced on the copy and read by the reader as the agreement gate; the accepted training bundle was exported and its digests recorded. Receipt: `docs/probes/ot9/retained/r2-robin-no-policy.json`. No training, no product turn.

## Why

The critic's message named this unit: rung 2 plus the reader, gated on `ot9-robin`'s no-policy rollout matching ot8's G4 receipt, then the bundle export, and no training. Done as asked. One choice to state: the "no-policy rollout" is an 8 s `cadex smoke` (hold = zero torque on Robin's two wheel motors), not `assembly.rollout`, because the rollout path needs a policy and installing a placeholder one would touch accepted state. So the reader reads two dialects: the rollout trace the ten seeds will produce, and the smoke trace this gate used. The rollout dialect is pinned only by fixtures until the first real evaluation.

## Method

Copied `ot8-robin` → `$PROJECTS/ot9-robin` with the README's tar command (evidence/, agent.json, .cadex-cli.lock excluded). `ot8-robin` HEAD stayed `b75dd2d5` with the same four pre-existing dirty paths. On the copy: `script.py` sha256; `script.json` accepted/working revision and attempt; MJCF and task sha256 from the accepted attempt's outputs; `CadexGeometryDigest.project_digest` → `b933d905…`; `staged_geometry_digest` under `build/release/bin/FreeCADCmd` → `34898ebc…`. All equal to `contract.json`. Then `./cadex smoke --seconds 8 --mode hold --timeout 300` (exit 0, 4m56s wall, project commit `78331a5`) and `./cadex export --out bundle` (exit 0, commit `9eee743`, rebuilt digest `b933d905…`).

The reader computes tilt as the angle between the base's +Z and its +Z in the model's `solved` keyframe (from MuJoCo, so an empty `<key>` is qpos0). That is smoke's ADR-377 reference, so yaw is not tilt. The reference never comes from the trace, because a rollout's first frame is the post-variation reset pose. Height is the base frame's world Z, which is what `fallen` reads. A seed fails on: no policy, a control rate other than 50 Hz, not one frame per control step, steps ≠ 400, a fired termination, no truncation, or peak tilt > 30°. It is void if the trace's model sha is not the model read, or not the expected MJCF/task pin. The candidate verdict is `pass` only for seeds 0–9 exactly once, each passing; otherwise `fail`, `incomplete` or `void`. The fixtures state their answers first: 12.5° at 2.74 s and 101.25 mm at 5.0 s under a 90° yaw; a 99° fall at 0.66 s failing four named rules; 30.00° passes and 30.01° fails; void on a foreign model or task; a dropped frame; a smoke trace that never passes; the ten-seed aggregation; the keyframe reference on a lying body. A test also holds the retained receipt equal to the contract pins and to G4's numbers. Mutating the tilt comparison to `>=` and the up-vector formula made 5 of 9 fixtures fail.

## Result

- `ot9-robin` exists, and every B1 pin reproduces on it: script `f805fdc2`, revision `0b438561` (accepted = working), attempt `1789860047622-6f21a6af7553`, digest `b933d905`, geometry `34898ebc`, MJCF `933b1ac6`, task `1f8c1040`.
- **The agreement gate passes.** The reader, on the copy's 8 s no-policy trace, gives `fallen` at 0.66 s with chassis z 66.73278932091965 mm, the same as G4's fired value. It reads 102.23396705927158° at 1.0 s against G4's 102.23396705927162°, which was the end tilt of G4's 1 s smoke, not a peak. Over the full 8 s it peaks at 108.12° at 0.74 s (the floor impact), reaches its minimum chassis height of 8.94 mm at 0.74 s, and lies at 102.23° at 8 s, matching smoke's own support value to 2e-13. Verdict: fail on no policy, `fallen` and tilt.
- **Training bundle:** `ot9-robin/bundle/robin_model-model.xml` `933b1ac6…` and `balance_task-task.json` `1f8c1040…`, both equal to the pins.
- **Tests:** `pixi run python -m pytest cli/tests` gave 929 passed and 1 skipped. `test_licensing_compliance.py` gave 10 passed and 1 skipped. The engine suite was not run: nothing under `src/` changed.

Concerns for the next iteration:
1. The rollout dialect is exercised only by fixtures. The first real policy's `assembly-simulation-trace.json` must be read and its frame count checked (401 solver_output frames for 400 steps). If the trace's layout differs, fix the reader before reporting any seed.
2. `ot9-robin` inherited ot8's git history. Its first CLI commit (`78331a5`) also recorded the deletion of the excluded `evidence/` files. That is the same mechanics ot8 used.
3. `pitch_penalty` reads `asin(qy)`. Robin falls about Y (the final quat is about Y), so it looks like the right axis. That still belongs to the first training diagnosis.
4. The tail now holds 2 unreconciled records.

The next rung is the first bounded training run. Its settings and stop rule must be written in the record before it starts. No new dependency.

Dispatch closed: 1 unit — ot9-robin prepared and pin-checked, per-seed balance reader landed and test-pinned, no-policy fall reproduced against G4, training bundle exported at the pinned digests.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot9
- commit: 9bba56cff1dc00ee933dc4632219bcbbdc4d6077

## State Impact

- target: tidy-arbor-3203 — ot9-robin prepared as a mechanical copy of ot8-robin with every B1 pin reproduced; the accepted training bundle is exported (bundle/, MJCF 933b1ac6, task 1f8c1040, rebuilt digest b933d905); no policy trained yet (commit 9bba56cf, docs/probes/ot9/retained/r2-robin-no-policy.json)
- target: early-rain-5934 — the per-seed reader exists (docs/probes/ot9/runner/balance_eval.py, pinned by cli/tests/test_ot9_balance_eval.py): peak tilt from the solved keyframe and its time, min chassis height, termination, digests, void on unpinned artifacts, and an all-ten-seeds candidate verdict; its agreement gate on ot9-robin's no-policy smoke reproduces G4 (fallen 0.66 s, 102.234 deg at 1 s). No policy has been evaluated
