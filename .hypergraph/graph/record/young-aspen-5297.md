---
node_id: f3cdf3a3-01de-520c-a069-5b4296f07e1b
slug: young-aspen-5297
title: 'ADR-595: four-pin four-bar built live; redundancy accepted only for one-freedom loops (L1)'
created_at: '2026-10-07T22:48:00+00:00'
parents:
- spring-river-3041
summary: ''
---
## What

ADR-595 (commit `8e9529a4`): a planar four-bar on four ordinary `revolute`
pins now builds live and is driven by its crank. The native solver's code-0
"redundant / partially redundant" verdict is accepted only when the loops have
exactly one degree of freedom, by ADR-593's rank taken of the loop joints'
screws at the solved pose (`CadexDynamics.loop_screw_mobility`,
`cadex_assembly_worker._loop_redundancy`). Otherwise the refusal stands, and it
names the count. A dynamics run with a loop now records `closure_tolerance_mm`
(0.01) and `closure_within_tolerance` beside `worst_closure_residual_mm`. The
`smoke_runner.closure_step_s` docstring now cites both measurements: ADR-593's
fixture (0.045/0.0062/0.0012 mm at 2/1/0.5 ms) and ADR-594's live run
(0.70/0.0061/0.0013 mm at 2/0.5/0.25 ms).

## Why

The critic named this unit: accept the native "redundant" verdict only where
the mobility rank shows exactly one degree of freedom, gated by one real-engine
four-pin crank-rocker test, plus the driven residual beside its 0.01 mm
tolerance and the smoke_runner docstring fix. All of it is done.

**Deviation:** the critic also asked me to reconcile first, folding
civic-sun-5811 and spring-river-3041 into wise-vale-2522. This dispatch's own
rules forbid reconcile in a work iteration ("no exceptions"), so I did not
reconcile. The tail is now three records (civic-sun-5811, spring-river-3041,
this one), and a reconcile pass is due.

A second deviation: ADR-593's `_loop_mobility` ranks the exported MuJoCo model,
and that model does not exist at solve time. The new function ranks the same
closure Jacobian in closed form, built from the joint screws (w, p×w) / (0, v)
in the solved connector frames. One MuJoCo-model ranking cannot be reused
verbatim.

## Method

- Six rows per loop, one column per joint freedom, each column signed by the
  direction the loop walks the joint. Positions are centred and scaled by the
  loop size. Rank uses `_matrix_rank` with a new optional tolerance (1e-6 for
  solver-placed frames). Each loop joint's connector gap is measured off-axis
  for sliding kinds, and each hinge's axis tilt is measured. Kinds outside
  revolute, slider, cylindrical, ball and fixed are not judged (`None`).
- Acceptance requires: code 0, only redundancy flags, mobility == 1,
  redundancy > 0, gap ≤ `MJCF_POSE_TOLERANCE_MM`, tilt ≤ 1e-6. The result is
  published as `diagnostics.loop_redundancy`.
- Live scratch run (`/tmp`, not committed): the `orun5-fourbar` script with its
  balls changed to pins, at 0.5 ms. The rocker was checked against circle
  intersection at the crank angle reached.
- Tests: 3 headless tests in `test_dynamics_linkages.py` (four-bar and
  slider-crank accepted; tilted closing pin, pinned triangle and a 0.1 mm open
  closure refused; conflicting flag, non-zero code and `distance` kind not
  judged). `cli/tests/test_smoke.py`'s real-engine four-bar is now four pins.
  It asserts the accepted count (1, 3), the rocker within 0.01 mm at its tip of
  analytic, and the new evidence keys, then smokes the four-bar. Mutation check:
  with the acceptance disabled, the e2e test fails at `cadex script`.
- Docs: `docs/XSCRIPT.md`, `docs/MUJOCO.md` (the live section, plus the M5 note
  that said this could not reach a gate), `docs/CLI.md`, and ADR-595 in
  `docs/DECISIONS.md`.

## Result

What is true now:
- The native solver's verdict on the live four-pin four-bar (200/80/220/120 mm)
  is accepted: `loop_redundancy` = {freedoms 4, rank 3, mobility 1,
  redundancy 3, worst_gap_mm 0.0, worst_axis_tilt 0.0, accepted true}.
- Driven at 225 °/s and 0.5 ms through `assembly.dynamics`, the crank swept
  447.6°. The rocker stayed within 0.0032° of analytic (0.0066 mm at its
  120 mm tip). The worst closure residual was 0.0061 mm, with
  `closure_within_tolerance` true. The e2e test also smokes this rig to a pass.
- Refused as before: a pinned triangle (mobility 0), a four-bar with its
  closing pin tilted 30° (mobility 0), and a closure left 0.1 mm open.
- Gates: `pixi run test-engine` 2673 passed, 60 skipped. `pixi run
  build-engine`, then `pytest cli/tests` with the GPU hidden: 1222 passed,
  1 skipped.

Concerns for the next iteration:
- The reconcile is overdue: three unreconciled records.
- L1's remaining gap: the fit sweep still refuses a loop with the loop named.
  It does not solve the loop. The charter allows a refusal, so L1's evidence
  list may now be complete. The critic should judge. P2 is next by charter
  order.
- Accepting a loop of two or more freedoms (for example a planar five-bar) is
  deliberately left out. Such a loop is still refused as redundant.
- The live e2e test no longer covers a rod-ended (ball-ball) coupler. ADR-593's
  headless ball-closure test still covers ball closures.

Dispatch closed: 1 unit — ADR-595: native redundancy accepted for one-freedom loops by screw rank; four-pin four-bar built live and driven to the analytic rocker; driven residual beside its tolerance

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 8e9529a4efe7a89589b324313cf6d03a60657a48

## State Impact

- target: wise-vale-2522 — a planar four-bar on four revolute pins builds live: the native solver's code-0 redundancy is accepted only when the loop joints' screw rank at the solved pose leaves exactly one freedom and every loop joint closes within 0.01 mm (ADR-595); driven 447.6° at 0.5 ms its rocker stays within 0.0032° of analytic, residual 0.0061 mm, now stated in dynamics evidence beside closure_tolerance_mm. Truss, tilted pin and open closure stay refused. Still open: fit sweep solving a loop (it refuses, naming it).
