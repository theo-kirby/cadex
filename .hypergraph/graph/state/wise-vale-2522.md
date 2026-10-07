---
node_id: 22629834-b0cb-5d7e-9773-a7f0cf4afef3
slug: wise-vale-2522
title: L1. A closed linkage exports and is driven
created_at: '2026-10-07T17:58:13+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun5: **L1. A closed linkage exports and is driven.** A loop closure exports to MJCF as an equality constraint and an actuator on one loop joint drives the chain (A2); the fit sweep solves the loop or refuses naming it; smoke holds a linkage within the MJCF pose tolerance (ADR-584); tests: a crank-driven four-bar and a slider-crank reach the analytic output, an over-constrained loop is refused. The human owns the checkbox [rec: honest-bay-2056].

**Implemented, every listed piece of evidence present** (ADR-593; ADR-594 `06a8964d`; ADR-595 `8e9529a4`) [rec: civic-sun-5811] [rec: spring-river-3041] [rec: young-aspen-5297]. Reconcile judgement: status `working`, not closed. There is no `met` status in the vocabulary, the human owns the box, and young-aspen-5297 leaves the "is the refusal enough" call to the critic.

- **Declaration**: no new surface. A closure is the ordinary joint that closes a chain, exported since M2 (ADR-077) as `equality/connect`/`weld` between sites. A grounded crank is always a tree edge, so it can be driven. A `closes_loop=` flag was rejected as restating the graph [rec: civic-sun-5811].
- **Export guards**: `CadexDynamics._loop_mobility` ranks the closure Jacobian at the solved pose twice: once for what the export pins, once for what the joints pin. `build_model` refuses `overconstrained_loop` (the closure is named, with a correction offered) and `actuator_locked_by_loop` [rec: civic-sun-5811].
- **Live solver**: the native assembly solver's code-0 "redundant" verdict is accepted only when four conditions hold. The loop joints' screw rank at the solved pose (`loop_screw_mobility`, `_loop_redundancy`) must leave exactly one freedom. Every loop joint must close within 0.01 mm. Hinge tilt must be ≤ 1e-6. Only redundancy flags may be set. The verdict is published as `diagnostics.loop_redundancy`. A four-pin planar four-bar therefore builds live (freedoms 4, rank 3, mobility 1). A pinned triangle, a 30°-tilted closing pin and a 0.1 mm open closure are still refused [rec: young-aspen-5297]. Before ADR-595 the four-pin loop was refused live, and only a rod-ended (ball-ball) coupler was accepted [rec: spring-river-3041].
- **Driven to analytic**: headless fixtures (a 200/80/220/120 mm crank-rocker and an 80/200 mm slider-crank) match analytic outputs within 0.01 mm at a 0.5 ms step. The closure residual scales with step and speed: at 225°/s it is 0.045, 0.0062 and 0.0012 mm at 2, 1 and 0.5 ms [rec: civic-sun-5811]. Live, the four-pin four-bar was driven 447.6° at 225°/s and 0.5 ms. The rocker stayed within 0.0032° of analytic (0.0066 mm at the tip), and the residual was 0.0061 mm [rec: young-aspen-5297]. The live rod-ended rig gave 0.70, 0.0061 and 0.0013 mm at 2, 0.5 and 0.25 ms [rec: spring-river-3041]. Dynamics evidence records `worst_closure_residual_mm` beside `closure_tolerance_mm` (0.01) and `closure_within_tolerance` [rec: young-aspen-5297].
- **Smoke**: a fifth check, `closure`, measures every site-to-site connect/weld after every step against 0.01 mm. A failure names `suggested_step_s`, the 1-2-5 step under `step × sqrt(0.01/worst)`, which is conservative because the gap falls faster than step². A held live four-bar stays within 0.00094 mm and passes [rec: spring-river-3041].
- **Fit sweep**: every joint on a closure's cycle is reported `incomplete`, naming the loop's joints, components and closing joint. The sweep refuses the loop; it does not solve it [rec: civic-sun-5811].
- **Tests**: `test_dynamics_linkages.py` covers drive, refusal and acceptance cases [rec: civic-sun-5811] [rec: young-aspen-5297]. `cli/tests/test_smoke.py` covers closure pass/fail, step rounding, and one real-engine e2e: a four-pin four-bar driven round and smoked to a pass [rec: spring-river-3041] [rec: young-aspen-5297]. Mutation checks were run for each [rec: civic-sun-5811] [rec: spring-river-3041] [rec: young-aspen-5297].
- **Gates** (latest): `pixi run test-engine` 2673 passed, 60 skipped. CLI suite (GPU hidden) 1222 passed, 1 skipped [rec: young-aspen-5297].
- **Docs**: `docs/XSCRIPT.md`, `docs/MUJOCO.md` (step/speed table, live route), `docs/CLI.md`, ADR-593..595, and a `describe_api` loop sentence [rec: civic-sun-5811] [rec: spring-river-3041] [rec: young-aspen-5297].
- **Open**: the fit sweep refuses a loop rather than solving it. The charter allows this [rec: civic-sun-5811] [rec: young-aspen-5297]. Loops of two or more freedoms (e.g. a planar five-bar) are still refused as redundant, by choice. The live e2e no longer covers a ball-ball coupler; a headless test still does [rec: young-aspen-5297].

## Negative knowledge

- [scope: live rod-ended (ball-ball) coupler | confidence: high | evidence: spring-river-3041] Ball joints take no `joint_dynamics`, so the coupler's idle spin is undamped. With its mass on the ball line it toppled 9° in 2 s of hold, and smoke failed on overlap. Raising the balls 4 mm off the mid-plane with 1 mm clearance made it pass [rec: spring-river-3041].
- [scope: rod-end variants under the native solver | confidence: high | evidence: spring-river-3041] One ball at the rocker end (R-R-R-S) is still refused as redundant live; only a coupler with balls at both ends was accepted before ADR-595 [rec: spring-river-3041].

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-l1-closed-linkage-exports-driven)
- civic-sun-5811 — ADR-593: loops driven from the crank against analytic kinematics; over-constrained and actuator-locked loops refused; fit sweep names the loop
- spring-river-3041 — ADR-594: smoke closure check with suggested step; rod-ended four-bar built, driven and smoked live; four-pin loop refused live
- young-aspen-5297 — ADR-595: one-freedom redundancy accepted by screw rank; four-pin four-bar built and driven live; closure tolerance in dynamics evidence
