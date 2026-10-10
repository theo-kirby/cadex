---
node_id: 41bf097e-b08a-599f-a1eb-6f7b047df603
slug: staid-harvest-9652
title: Machine drives and parts as data for the first-wave machines (ADR-640..646)
created_at: '2026-10-10T14:21:50+00:00'
parents:
- tidy-aspen-4976
summary: ''
---
## What

Removed the dynamics and catalog blockers docs/ARCHITECTURE-REVIEW.md names for the docs/MACHINES.md first wave (recommendations 3, 4 and the tool half of 8), as ADR-640..646:

- ADR-640: a slider or cylindrical joint on a closed loop is taken into the spanning tree (second growth only when the first would refuse), so a hydraulic cylinder between two pins builds; a loop of sliders alone is still refused.
- ADR-641: `rack_pinion` is supported, by OndselSolver's own `x + R*theta` law (read from `RackPinConstraintIJ`/`getRackPinionMarkers`) over the tree path from rack to pinion (travelling-pinion gantries work); component-origin connectors accepted.
- ADR-642: `assembly.coupling([(joint, ratio), ...])` in `assembly.assembly(couplings=)`: n-joint linear couplings as MuJoCo fixed tendons + `equality/tendon` (two terms: `equality/joint`). CoreXY, differentials.
- ADR-643: `assembly.actuator(kind='cylinder', bore_mm, rod_mm, pressure_bar)`: a position servo with asymmetric force range.
- ADR-644: the fit sweep moves every coordinate a coupling ties to the swept joint (`coupled_sweep`); coupled joints and unlimited followers are `passive`.
- ADR-645: `assembly.tool(...)` + `workspace` block (reach box vs work area); `CadexEvaluation.path_metrics` / `coverage_metrics` (not yet wired into `assembly.success`).
- ADR-646: `CadexParts.json` + `CadexMachineParts.py` + `lib.part(sku, ...)`: 46 machine parts in 14 families as data, one generator per interface; M10/M12 fasteners.

## Why

The first-wave machines (CoreXY printer, mower, tractor hitch, CNC router, loader, rover, Strandbeest, liquid handler) were blocked by the slider-closure and rack_pinion refusals, two-joint-only couplings, symmetric joint actuators, uncoupled sweeps, and a catalog with no rails, belts, screws, steppers, extrusion, cylinders or spindles.

## Method

Pure-model tests on forward-built fixtures (`cadex_tests/test_dynamics_machines.py`, 18 tests), API tests (`test_machine_api.py`, 8), parts data tests (`test_parts_data.py`, 11), updated `test_dynamics_tree.py`, `test_dynamics_coupled.py`, `test_dynamics_task_api.py`. Three live proof projects built through `./cadex script --set` in the scratch directory (not committed): `proof-corexy` (2020 frame, MGN12 rails, NEMA17+GT2, CoreXY couplings, nozzle tool), `proof-loader` (boom + ISO 6020-2 40/18 cylinder in a closed loop), `proof-axis` (T8 leadscrew Z axis, m1 rack-and-pinion X axis with a travelling pinion). Each was swept, exported to MJCF and simulated, and rendered with `cadex render`.

## Result

- proof-corexy: builds; sweep complete (x, y each turn both motors and hold the other axis); workspace covers the 220x220 bed (reach box 240x230, exact); 0.5 s of motor A at 361 deg/s moves the head (9.93, 9.87) mm, belt tendons hold to 0.015 mm.
- proof-loader: builds; loop closes on the rod pin; sweep drives the stroke through [-61.2, 188.8] mm, residual 2e-13 mm; with a 5 kg stroke armature the boom rises smoothly, closure 0.0004 mm, peak ram force 378 N of 15.1 kN. Without the armature the rod rings and the loop opens 4.6 mm (measured hazard, documented).
- proof-axis: builds; sweep complete; 720 deg/s of screw lowers Z 16.2 mm/s (lead 8); a 90 deg/s pinion moves X -15.7 mm/s; coupling residual 0.16 mm.
- Measured hazard: a coupled motor needs its rotor inertia (armature) or a velocity gain stretches the tendon (20 mm open with none, 0.008 mm with 5.4 kg*mm^2).
- describe_api pages held under budget: library 21,462 and assembly 21,479 of 21,500 characters (gears/QDD notes and the policy passage compressed to pay for it).
- Not done: success-spec wiring for path/coverage, terrain/workpieces, MJX check of tendon equalities, converting the old catalog dicts to rows.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: worktree-agent-ad63f04eb22dd5fc2
- commit: d28bf16ceaf1cc6fabfeb7b8151e2e178f64ea50

## State Impact

- target: salty-isle-4063 — dynamics now closes a loop on a slider (tree takes it), supports rack_pinion (Ondsel law over the tree path), n-joint assembly.coupling as fixed tendons, a cylinder actuator (bore x pressure, asymmetric forcerange), coupled fit sweeps and an assembly.tool workspace block; negative knowledge: a coupled motor needs its rotor inertia and a cylinder stroke a few kg of armature or the soft equality opens by mm (ADR-640..645)
- target: brave-stone-9609 — machine parts as data: CadexParts.json + one generator per interface behind lib.part (MGN rails/carriages, GT2, T8/SFU1204, NEMA17/23, 2020/2040, ISO cylinders, ER spindles, casters, tyres, springs), M10/M12 fasteners; old dict tables not yet converted (ADR-646)
- target: NEW machine-task-vocabulary — open: path/coverage readings exist in CadexEvaluation but are not wired into assembly.success; no terrain/workpiece world, odometry or cycle time (ADR-645)
