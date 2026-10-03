---
node_id: 247c90ae-5401-5612-8e34-f3b333ef0f7f
slug: calm-quill-0693
title: 'orun1 D4: ADR-487 round wheel bore so a catalog wheel sweeps clean on its motor'
created_at: '2026-10-03T03:56:52+00:00'
parents:
- spring-ivy-9833
summary: ''
---
## What
The record for ADR-487 (commit `9eac2291`, iteration 18, which landed without one). `lib.wheel` (`src/Mod/cadex/cadex_library_api.py`) now cuts its bore round at `bore_dia_mm` and leaves the D flat out of the geometry. The flat stays in the spec as `bore_flat_to_opposite_mm`, and `CadexCatalog.WHEELS["pololu-1430"]` gains an `approximate` entry saying it is not modelled. The docstring and the overlay's wheel line (`CadexAgentGuidance.md`) now say to place the wheel at least `boss_height_mm` out from the shaft datum and to declare `angle_limits_degrees=(-180, 180)` on the wheel revolute, because a joint with no limits is never swept. The motor keeps its sourced D shaft.

## Why
The critic asked for this record before the next unit. Trial 1 (`spring-ivy-9833`) showed that a catalog wheel on its catalog gearmotor could not pass a sweep: the turning D bore met the motor's static D shaft (4.26 mm³), so the agent fell back to continuous joints and the sweep came back `incomplete`. ADR-487 says why a round bore beats the two alternatives: a separate shaft solid would change every accepted gearmotor body, and a drive-pair sweep exemption would also excuse a rim that really hits the case.

## Method
- Regression `test_library.py::test_a_catalog_wheel_sweeps_clean_round_its_catalog_motor` runs the engine's `_measure_joint_sweeps` on the real kernel. The wheel sits 1 mm out on the shaft axis and a hinge turns from −180° to 180° in 15° steps (25 samples). ADR-487 records 6.97 mm³ on the old source (fail) and under `MAXIMUM_COMMON_VOLUME_MM3` with the fix.
- Gates run in this iteration at `9eac2291`: `pixi run python -m pytest src/Mod/cadex/cadex_tests/test_library.py -q` gave **140 passed in 62 s, 0 skipped**, so the real-kernel test ran. I did not repeat the fail-before run on the old source here: the dev tree was serving a live design turn, so I did not touch it. The 6.97 mm³ figure is ADR-487's, from iteration 18. The full `pixi run test-engine` result goes in the next record (balancer trial 2), which ran it at the same revision.
- The engine resolves from the dev tree (`module_dir` `src/Mod/cadex`, source `dev-tree`), and `build/release/Mod/cadex/{cadex_library_api.py,CadexCatalog.py,CadexAgentGuidance.md}` match the source byte for byte. So D4 turns at this revision see the fix.

## Result
- True now: a catalog wheel on its catalog motor can pass a limited-joint sweep, if it is on the shaft axis and clear of the boss. The wheel is still a solid disc. Trial 1's two judge losses cited exactly that, and modelling the rim, hub and tyre is a separate open unit.
- Concern: the fail-before evidence comes from the iteration that made the change, not from a re-run here.

Dispatch closed: 1 unit — ADR-487 (round wheel bore, limits and boss clearance in the overlay) recorded with its gate

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 9eac2291ae6390fb42be4c44ff04e412cd5ed971

## State Impact

- target: salty-fox-7376 — ADR-487 (commit 9eac2291): lib.wheel's bore is round, the overlay tells the agent to clear the boss and limit the wheel joint ±180°, so a balancer's swept fit is no longer blocked by the catalog D-shaft; the wheel is still a solid disc
