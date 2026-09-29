---
node_id: 4ac4fba0-ce4b-5d92-8d6e-2d3142dd4376
slug: honest-stream-0109
title: 'ot10: hip_pitch gap closed — hex2''s refusal at 48 was MJCF writer-zero round-off read as drift 1.0 (ADR-441)'
created_at: '2026-09-29T05:56:32+00:00'
parents:
- copper-dusk-1149
summary: ''
---
## What

Closed the open hex gap "`hip_pitch` ranges" at the engine (ADR-441). hex2's
`hip_pitch` parameter was refused at 48 mm, inside its declared 46–52 range,
with "The MJCF exported for assembly output 'hexapod' changed body_pos by 1
relative". This was an MJCF export-check defect, not a design limit.
`_field_drift` now compares values below `MJCF_WRITER_ZERO = 1e-12` as the
zero that MuJoCo's XML writer emits for them.

## Why

The critic named long-term rung 2, first unit, "`hip_pitch` ranges". Source
disagrees with the critic's framing: `hip_pitch` in hex2 is not a joint limit
checked against the swept fit. It is the hip spacing along X in mm.
`docs/probes/hex/README.md` lists the open gap as "`hip_pitch=48` … fails
MJCF export verification … suspected engine defect, not yet reproduced in
isolation". I took the gap as the logs record it: reproduce it, add a
regression that fails before the fix, fix it at the source, and write an ADR.
No teaching or reference change was needed, because the agent had done
nothing wrong. No A5 turns were run, as the critic asked.

## Method

- Copied `~/cadex-projects/hex2` read-only to `/tmp/hp48`, then ran
  `./cadex params --set hip_pitch=48`. It reproduced in 23 s on the current
  engine as `mjcf_field_drift` on `body_pos`.
- Temporarily instrumented the refusal with the differing elements, then
  reverted. The field was zero everywhere except three entries of
  −7.105e-18 m. The reload had 0 there, and the scale was the round-off
  itself, so the drift was exactly 1.0.
- Measured the MuJoCo 3.10.0 writer on `body_pos`, `body_quat` and
  `geom_pos`: |v| < 1e-12 is written as 0 (9.99e-13 → 0, 1e-12 kept).
- Fix: snap sub-1e-12 values to 0 on both sides inside `_field_drift`. This
  models the representation and is not a new tolerance. ADR-134's 1e-9
  `body_ipos` floor in `model_differences` is unchanged.
- Three regressions in `cadex_tests/test_dynamics_mjcf_model.py`, all of
  which fail on the old source (3 failed) and pass on the new (3 passed):
  - the pendulum fixture with its bodies at the origin, one at −7.1e-18 m,
    now exports;
  - the writer's zero threshold is re-measured on the installed MuJoCo;
  - 1e-9 m and 2e-6 m against zero are still refused.
- Docs:
  - ADR-441;
  - MUJOCO.md hazard 12 (ADR-092 had documented this dust hazard with a
    modelling workaround) is marked fixed at the source;
  - the hex README moves the item from "Still open" to the fixed table;
  - REPORT.md item 7 is updated.

## Result

What is true now:

- On the hex2 copy, `hip_pitch=48` and `hip_pitch=52` with `policy_on=0`
  are accepted (revisions `6361778985d6`, `6b71f3809860`).
- With `policy_on=1`, the next refusal is the stored policy's task-digest
  mismatch, which is correct for a changed design.
- Any model whose field should be zero but carries float dust (for example,
  all components at the identity) no longer refuses at export.

Verification:

- `pixi run test-engine`: 2266 passed, 53 skipped.
- `cli/tests`: 1075 passed, 1 skipped.
- `build-engine` and `stage-engine` were rerun. The staged
  `CadexDynamics.py` carries the fix.
- The packaged lifecycle gate (`CADEX_ENGINE_ROOT=<payload>`
  `test_cadexd_lifecycle.py`): 23 passed.
- The doc and report tests were rerun after the doc edits: 84 passed.

Assumption: the 1e-12 threshold is MuJoCo 3.10.0's. The writer-zero test
fails if an upgrade moves it.

Next per the critic: electronics bays shaped around their parts.

Dispatch closed: 1 unit — hex2 `hip_pitch=48` refusal reproduced, fixed as MJCF writer-zero round-off in `_field_drift` (ADR-441), three failing-before regressions

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: f95b1595634959b40bcfa2f487e7b77e4d574699

## State Impact

- target: salty-isle-4063 — MJCF export verification no longer refuses float dust: _field_drift compares values below MJCF_WRITER_ZERO=1e-12 (MuJoCo 3.10.0's measured writer zero) as 0, fixing MUJOCO.md hazard 12 at the source; hex2 hip_pitch=48/52 now accepted (ADR-441)
- target: loyal-fountain-8709 — long-term rung 2 started: the hip_pitch gap from hex is closed as an engine defect (ADR-441); no A5 turn run, nothing re-scored
