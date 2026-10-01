---
node_id: 16f127c5-100d-5ccf-956c-2c3aae0734aa
slug: keen-walrus-1609
title: 'ADR-468: success spec may state its scale; engine refuses a stale HIP_MM-class constant at declaration'
created_at: '2026-10-01T04:55:28+00:00'
parents:
- rough-bell-4381
summary: ''
---
## What

Built the spec-versus-rig guard from rough-bell-4381's first concern (ADR-468, commit `d410b098`).
- `assembly.success(..., scale={...})` lets a spec state the scale its own numbers were written for. The keys are `mass_kg`, `weight_n`, `com_height_mm`, `hip_height_mm` and `arm_length_mm`, the same keys as the bundle's `success.scale`.
- When the task is declared (`CadexDynamics._success_records`), each stated value is compared with the measured one. If any differs by more than 1 ppm, or the mechanism has no measure of that key, the script is refused with `success_scale_mismatch`, which names the stated and the measured values.
- A statement that agrees is kept in the block as `stated_scale`. With no statement, the block is byte-identical to before.
- Docs updated: XSCRIPT.md and DECISIONS.md (ADR-468).

## Why

The critic said to check the supervisor first.
- Walk session 3's driver (`rounds.py`) was alive at 04:25Z, with turn 1 still running.
- `r9-steelfoot` had **failed at start**: 52 s, 0 iterations. The trainer refused the warm start from r6: "A curriculum step may change the task the network is being trained AGAINST. It may not change what the network reads or emits".
- `r10-steelfoot-fresh` was training.
- No run had finished and been evaluated, so there was nothing to publish against the frozen spec. The critic's third branch applied: do the guard unit now and leave the job alone. I did that, and touched no process.

**One deviation from the critic's wording.** The critic asked that `evaluate` flag the mismatch. The check is at declaration instead.
- `evaluate` plays the bundle of an accepted revision, and a spec that disagrees with its mechanism can now never be accepted.
- A check at evaluation time would find the same thing one GPU run later. That late discovery is the failure this guard exists to prevent.
- The evaluation report copies the bundle's spec block, so `stated_scale` is visible in every report that has one.

**Why a declaration, not detection.** The engine cannot know which script constants are scale: `HIP_MM` is just a Python name. The script also cannot read the measured scale before the model is built. Stating the scale is the only task-agnostic route; nothing in it is walking-specific.

## Method

- Traced the existing path: API → worker `_success_input` → `_success_records`, which already computed `scale` from `evaluation_rig`. Confirmed r8's report rig gives `hip_height_mm` = 106.949.
- **Tolerance.** One part in a million catches r8's error (1.9 ppm), and a value copied from the rig still agrees, since the MJCF writes hip anchors to six significant figures.
- **Tests added.**
  - `test_success_spec_api`: carried and absent cases, plus five malformed refusals.
  - `test_success_spec_model`: key tuple equal on both sides, an agreeing statement carried, a 2 ppm hip-height digit refused with the measured values, an unmeasured `arm_length_mm` refused.
  - `test_success_spec_live`: through `cadexd` and the worker, agreement carried and a stale digit refused.
- With the three source files stashed, the 10 new API/model tests failed; restored, they pass.
- **Full suites:**
  - `pixi run test-engine`: 2521 passed, 60 skipped.
  - `pixi run python -m pytest cli/tests`: 1261 passed, 1 skipped.
- No protocol op, payload file list, shell file or dependency changed, so no packaged gate was needed.

## Result

**The guard exists, but it is opt-in.**
- A spec that states `scale={"hip_height_mm": HIP_MM, "weight_n": WEIGHT_N}` cannot be accepted with a stale constant.
- The ot11 walk script does not state one, so nothing changes for it unless the product agent adopts the option.
- The development `cadexd` imports the engine from the source tree, so the option became available to the running session when the source changed (the same route as ADR-467). It is backward compatible. Neither the driver nor any job was touched.

**Concerns for the next iteration:**
1. **Publish `r9-steelfoot` and `r10-steelfoot-fresh` when r10 ends.**
   - r9 is a trainer refusal at start: 0 iterations, 52 s supervised, warm start from r6 across a task change the trainer rejects. Publish it as a refused start, not a trained attempt.
   - r10 is a fresh run; it was training at 04:25Z.
   - Session 3's mechanism change is steel-ball feet (foot density 1150 → 7850). The script now reads `HIP_MM = 96.7006` (back to the hip 30/knee −60 stance) and `WEIGHT_N = 5.05069617762`. Check both against the r10 evaluation's `rig` under the mechanism rule, and publish as void if either differs at the printed precision.
2. **Possible pre-registration effect.** The steel-ball-feet comment and the reverted stance mean HIP_MM may now be right by construction. Verify it; do not assume it.
3. **Write this down in the contract.** Whether the frozen ot11 walk spec block should adopt `scale=` is a contract change (README §P1 "changing a frozen item"). It is not the actor's to make mid-session. The actor may propose it after session 3 ends, as a recorded decision.
4. The tail is now three unreconciled records (red-mountain-4965, rough-bell-4381 and this one), so a reconcile is due per the charter's three-record rule.

Dispatch closed: 1 unit — ADR-468 spec scale guard: assembly.success(scale=...) refused at declaration when it disagrees with the measured rig by >1 ppm (catches r8's HIP_MM digit); r9 refused at start, r10 training, left alone

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: d410b098d7d17a0d81750be4a139744b9b7397cc

## State Impact

- target: damp-flame-5523 — assembly.success(scale={...}) states the scale a spec was written for; the engine refuses the script (success_scale_mismatch, >1 ppm, measured values named) when the mechanism measures otherwise, and carries an agreeing statement as stated_scale (ADR-468, commit d410b098); opt-in, closes the class of void evaluation round 8 hit
- target: smooth-fountain-9832 — walk session 3: r9-steelfoot refused at start by the trainer (warm start across a channel-changing task change, 0 it, 52 s); r10-steelfoot-fresh training at 04:25Z; both unpublished
