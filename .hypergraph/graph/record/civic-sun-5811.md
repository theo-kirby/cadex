---
node_id: 1ede3f39-8f45-5f6c-9599-d6aa55ffac91
slug: civic-sun-5811
title: 'ADR-593: closed linkages driven from the crank; over-constrained loops refused (L1)'
created_at: '2026-10-07T21:58:48+00:00'
parents:
- long-cabin-6279
summary: ''
---
## What

ADR-593: a closed linkage driven from its crank, measured against analytic
kinematics, and the two ways a loop could mean something different in MuJoCo
than on the bench refused. Commit on `ouroboros/orun5`.

- `CadexDynamics._loop_mobility` (called from `build_model`): central-difference
  Jacobian of every closure residual over all dofs at the solved pose, ranked in
  pure Python (`_matrix_rank`, no numpy), once with what the export pins
  (connect pin / weld frame) and once with what the joint pins (revolute pin +
  axis). `built["loop_mobility"]` = `{dof, export_mobility, mechanism_mobility,
  closures}`. Export mobility > mechanism mobility -> `overconstrained_loop`
  (names the closure; correction: planar loop or a ball end). An actuated dof
  whose unit vector lies in the joint Jacobian's row space ->
  `actuator_locked_by_loop`.
- `cadex_assembly_worker._closed_loops` + `_measure_joint_sweeps`: every joint
  on a closure's cycle (same spanning tree as the export) is reported
  `incomplete` with the loop's joints, components and closing joint named.
- `describe_api` assembly note: one sentence on loops; two older sentences
  trimmed to stay under `API_VIEW_CHAR_BUDGET` (21,500).
- `docs/XSCRIPT.md`, `docs/MUJOCO.md` (with the step/speed table), ADR-593.
- `test_dynamics_linkages.py` (6 headless tests).

## Why

The critic named L1, the highest-ranked open capability. Read against source,
loops already exported (M2, ADR-077: `equality/connect`/`weld` against sites)
and tree joints were already drivable (M4, ADR-080). So the gap the reference
project hit was not the export itself. What was missing: evidence that a drive
on the crank moves the chain correctly, a check that a connect means what its
joint means, and a sweep refusal that names the loop.

**Deviation from the critic's message:** the critic asked to "add an
assembly-level loop closure". I added no new declaration. A closure is the
ordinary joint that closes a chain, as it has been since M2. A grounded crank
is always a tree edge, so it can always be driven. A `closes_loop=` flag would
have to be threaded through the FreeCAD joint object, the publication and the
worker's joint schema, only to restate what the graph already says (ADR-593,
Alternatives). Fit sweep: refused with the loop named, which the critic
allowed; solving the loop per sample was not attempted.

## Method

Built fixtures (four-bar 200/80/220/120 mm, Grashof crank-rocker; slider-crank
80/200 mm; pinned triangle) with `dynamics_fixtures.build` +
`closing_joint`. Drove each crank with a position servo (500 N·mm/deg,
5 N·mm·s/deg) at 225 deg/s for 2 s. At every frame I compared the output with
the analytic answer at the crank angle the run actually reached, so PD lag is
not counted as kinematic error. Probed closure error against solver step and
crank speed on the four-bar (worst closure residual, mm):

| speed | 2 ms | 1 ms | 0.5 ms |
|---|---|---|---|
| 90 deg/s | 0.0179 | 0.00245 | 0.00035 |
| 225 deg/s | 0.0448 | 0.00624 | 0.00120 |
| 450 deg/s | 0.0899 | 0.0179 | 0.00476 |

Mutation checks: the refusal tests fail without `_loop_mobility`. With
`loops = []` in the sweep, the sweep test fails (run and confirmed).

## Result

What is true now:
- Four-bar: the crank turned >400 deg. The rocker's far pin stayed within 0.01 mm
  (`MJCF_POSE_TOLERANCE_MM`) of the circle-intersection answer at every frame,
  and the worst closure residual was below 0.01 mm. Slider-crank: the full
  160 mm stroke (±0.5 mm), the slider within 0.01 mm of
  `r cos θ + sqrt(l² − r² sin² θ)`. Both at `solver_step_s = 0.0005`.
- Four-bar with its closing hinge tilted 30°: refused `overconstrained_loop`,
  export mobility 1, mechanism 0. The same loop with a ball closure builds,
  with both mobilities equal. An undriven pinned triangle builds (mobility 0).
  Driven, it is refused `actuator_locked_by_loop`.
- The fit sweep reports every four-bar joint `incomplete` with
  "closed loop ['b', 'a', 'd', 'c'] ... closed by 'c'".
- Gates: `pixi run test-engine` 2670 passed, 60 skipped. That run started before the describe_api note trims; after them, the four note-reading suites plus the linkage tests were rerun: 93 passed. Then `pixi run build-engine` and `pytest cli/tests` with the GPU hidden: 1218 passed, 1 skipped, including the describe_api budget test (the assembly page is at most 21,500 chars). `test_joint_fit_sweep.py` against real OCCT: 12 passed.

Concerns for the next iteration:
- At the default 2 ms step, a driven loop sits 0.02–0.09 mm open at 90–450 deg/s,
  which is above the 0.01 mm pose contract. That is documented, not refused.
  Nothing warns an agent who keeps the default step.
- L1 is not fully met: `cadex smoke` has not been measured on a real linkage
  project, and the fit sweep refuses a loop rather than solving it. Both are
  named in ADR-593's Consequences. A real-engine end-to-end (a scratch
  four-bar project through `cadex smoke`) is the natural next L1 unit, or P1's
  optional pushrod plate.
- No new dependency. No protocol, op or tool-surface change.
- Tail: this is the first record after the reconcile at `long-cabin-6279`.

Dispatch closed: 1 unit — L1: driven closed linkages proved analytically, over-constrained and locked loops refused, fit sweep names the loop (ADR-593)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 1e0ed93564766252fbc1fc508ab7de9308e1878e

## State Impact

- target: wise-vale-2522 — Driven four-bar and slider-crank match analytic outputs within 0.01 mm at a 0.5 ms step (ADR-593). build_model refuses overconstrained_loop and actuator_locked_by_loop. The fit sweep names the loop. Still open: cadex smoke on a real linkage project, and a sweep that solves the loop.
