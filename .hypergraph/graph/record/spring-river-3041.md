---
node_id: 5eeb4f0d-a58f-5f64-8333-0b3b8b36e28a
slug: spring-river-3041
title: 'ADR-594: smoke measures loop closures; a rod-ended four-bar driven and smoked live (L1)'
created_at: '2026-10-07T22:27:06+00:00'
parents:
- civic-sun-5811
summary: ''
---
## What

L1 closed in the real engine as far as one unit reaches (ADR-594). `cadex smoke`
gained a fifth check, `closure`: every site-to-site `equality` (connect or weld)
the MJCF export writes for a loop closure is measured at every solver step, its
worst gap compared with the MJCF pose contract (0.01 mm, ADR-584), and a failure
names `suggested_step_s`, the 1-2-5 step under `step × sqrt(0.01 / worst)`. A
scratch project `~/cadex-projects/orun5-fourbar` builds a crank-rocker four-bar
(200/80/220/120 mm) through the engine, drives it with a crank servo through
`assembly.dynamics`, exports it and smokes it.

## Why

The critic's message: close L1 by building a scratch `orun5-fourbar`, running it
through the real engine and `cadex smoke`, making smoke report the worst closure
residual against `MJCF_POSE_TOLERANCE_MM` with the step that fixes it, and adding
at most one real-engine e2e test. Done as asked, with one deviation forced by a
measurement: a four-bar of four parallel revolute pins cannot be built live (see
Result), so the scratch four-bar uses a rod-ended (ball-ball) coupler. P2 was not
started this iteration: one unit.

## Method

- `cli/cadex_cli/smoke_runner.py`: closures found from `model.eq_objtype == SITE`
  and `eq_type in {CONNECT, WELD}`; gap = |site_xpos1 − site_xpos2| at t=0, after
  every `mj_step`, and at every sample; `checks.closure` = {pass, tolerance_mm,
  closures (worst first, with time), worst_mm, solver_step_s, suggested_step_s,
  note}. `closure_step_s()` rounds down to 1/2/5 of a decade.
- Scratch project, real engine (dev tree): `cadex script --set`, `cadex params
  --set step_ms=...`, `cadex smoke --mode hold|zero`; rocker angle checked against
  circle intersection from the trace.
- Tests in `cli/tests/test_smoke.py`: swinging vertical four-bar fixture (export
  closure settings, solref = 2 steps) fails at 2 ms naming 0.0005 and passes at
  0.5 ms; loopless model passes with a note; rounding cases; one real-engine e2e
  (`test_a_four_bar_built_live_is_driven_round_and_holds_its_loop_shut`). Mutation:
  with the runner reverted to HEAD, 4 tests fail.
- Docs: `docs/CLI.md` smoke checks, `docs/XSCRIPT.md` and `docs/MUJOCO.md` live
  route, `docs/DECISIONS.md` ADR-594.

## Result

What is true now:
- **A planar four-bar of four `revolute` pins is refused live** by the native
  assembly solver ("redundant constraints, partially redundant constraints",
  `cadex_assembly_worker._diagnostics_conflict`), before any model is built. One
  ball at the rocker end (R-R-R-S) is still refused. A coupler with a ball at both
  ends (rod ends) is accepted.
- The rod-ended coupler's idle spin is undamped (ball joints take no
  `joint_dynamics`). With the coupler mass on the ball line it toppled 9° in 2 s of
  holding into crank and rocker (smoke failed on exact overlap, 646/749 mm³); with
  the balls 4 mm above the coupler's mid-plane and 1 mm clearance, smoke passes.
- Driven 225 °/s through `assembly.dynamics` (crank swept 447.6°): worst closure
  residual 0.70 mm at the 2 ms default, 0.0061 mm at 0.5 ms, 0.0013 mm at 0.25 ms.
  At 0.5 ms the rocker pin is within 0.0066 mm of the analytic answer at every frame.
  The gap falls faster than step² (115× for a 4× step), so the named step is
  conservative.
- Held (smoke `hold`, 2 ms), the live loop stays within 0.00094 mm; smoke passes
  with `checks.closure.closures = [j_c]`.
- Gates: `pixi run python -m pytest cli/tests` (GPU hidden) — 1222 passed, 1 skipped (a first run alongside the engine suite failed one 390px browser layout test once; it passes alone with and without this change, and the full foreground rerun is green).
  `pixi run test-engine` — 2670 passed, 60 skipped (no engine file changed).

Concerns for the next iteration:
- Smoke holds still, so it sees a loop at rest; the driven gap (0.70 mm at 2 ms)
  lives only in `assembly.dynamics`'s `worst_closure_residual_mm`, with no contract
  beside it. An agent on the default step is told by smoke only if the held loop
  sags open.
- L1 still open: planar four-pin four-bar live (would need accepting the native
  solver's redundancy where ADR-593's mobility rank proves it benign — its own
  unit), and the fit sweep solving a loop instead of refusing.
- xscript has no `math` (no sin/cos/atan2): the scratch script uses `** 0.5`
  only; the reference excavator wrote a Taylor series. Worth a defect node.
- Scratch project left accepted at `step_ms=0.5`.

Dispatch closed: 1 unit — smoke closure check (ADR-594) and a live rod-ended four-bar driven and smoked through the real engine

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 06a8964df51afe079294a817d3475cc188c74095

## State Impact

- target: wise-vale-2522 — smoke's closure check measures every site-to-site equality against 0.01 mm and names the 1-2-5 step that holds it; a rod-ended (ball-ball) four-bar is built through the engine, driven 447.6° at 0.5 ms (residual 0.0061 mm, rocker within 0.0066 mm of analytic; 0.70 mm at 2 ms) and smoked to a pass; a planar loop of four revolute pins is refused live by the native solver's redundancy rule. Still open: four-pin planar loop live, fit sweep solving loops, driven-gap contract in dynamics evidence.
