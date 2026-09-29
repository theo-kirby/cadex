---
node_id: 2e8dd3a1-c227-5490-91ee-c12cd5132d32
slug: brave-rain-8039
title: 'ot10: servo bay — lib.servo carries .bay(), limbs grow around it (ADR-443)'
created_at: '2026-09-29T06:44:04+00:00'
parents:
- rapid-spark-0680
summary: ''
---
## What

The lib servo now carries its own `.bay()` keep-out (ADR-443, commit `a382b520`), matching what ADR-442 gave boards and batteries. The CLI overlay's ENCLOSE rule now teaches the agent to grow a limb around the servo's bay and then cut it, so the case ends up inside the limb. The measurement was taken read-only on the three 16/21 designs.

## Why

The critic named this unit: the servo-case half of A7's gap ("servo cases hanging outside the shell", with T4 never reaching 3). It asked for a servo `.bay()` or shroud keep-out parallel to ADR-442, overlay teaching for limb shells that enclose the servo, a regression test that fails before the fix, and a read-only measurement on the 16/21 designs. All four were done as asked. I built `.bay()` only, not a separate shroud helper. The wall around the servo is still authored by the agent and taught in the overlay, and the measurement uses a shroud (the bay grown by 2 mm) only as a diagnostic. No confirmation turn was run.

## Method

- **Product.** `cadex_library_api.py`:
  - `_bay_allowance` and `_BayPart` moved above `ServoPart`, which now subclasses `_BayPart`.
  - `ServoPart.bay(clearance=0.5, lead_room=6.0)` is the fuse of four pieces in the servo frame, placed with `_place_frame`:
    - the case box grown by `clearance`;
    - the tab plate grown by `clearance`;
    - the spline column, radius plus clearance, from the case top to the spline top;
    - a lead box beyond the −X back face, below the tabs, left out when `lead_room` is 0.
  - The −X lead exit is a stated convention, not a datasheet dimension.
  - The `lib.servo` docstring and `library_listing` note were updated.
- **Overlay.** The ENCLOSE rule in `cli/cadex_cli/agent.py` now:
  - names the servo's, board's and battery's `.bay()`;
  - says a limb wraps the servo's `.bay()` with a 1.6–2.4 mm wall on every side except the spline's, then cuts it, "never a case hanging beside the limb it drives";
  - says to split the limb where the servo drops in, and to screw the tabs down at `spec["mount_holes"]`.
- **Docs.** `docs/XSCRIPT.md` gained the servo row in its bay table, `docs/DECISIONS.md` gained ADR-443, and `docs/probes/ot10/REPORT.md` item 7 was extended.
- **Tests.** Added to `test_library.py`:
  - case, tabs, lead and column extents for sg90, mg90s and ds3218;
  - the bay contains the body;
  - the bay follows the placement;
  - three refusal cases.
  All 8 cases fail with the old `cadex_library_api.py` and pass with the new one. `test_turn_loop.py` gained `test_the_overlay_grows_a_limb_around_the_servo_bay`.
- **Measurement (read-only).**
  - `ot10-quadruped-2`, `ot10-hexapod-5` and `ot10-quadruped-4` were copied to a scratch dir outside the repo and exported with `cadex export --format brep`.
  - Solved `component_placements` matrices came from each accepted attempt's `result.json`.
  - Each servo's frame was recovered from its own solid: the spline cylinder gives the axis and the case top, and the centre of mass gives −X. At zero allowance the bay holds 100.00% of all 28 servo solids.
  - Two numbers were computed in FreeCADCmd:
    - the share of a 2 mm shroud outside a 0.5 mm clearance around case and tabs that is printed material;
    - the printed volume inside the default bay.
  - Printed and purchased parts were told apart by source-name pattern, which gives 23, 28 and 23 printed components respectively.
  - The originals are untouched.

## Result

- **What is true now:** every catalogued servo has `.bay()`. The overlay teaches the agent to wrap it and to cut the bay rather than the body.
- **Measured shroud share (read-only):**

  | design | hip servos | knee servos |
  |---|---|---|
  | `ot10-quadruped-2` | **0.198** | 0.734 |
  | `ot10-quadruped-4` | **0.390** | 0.763 |
  | `ot10-hexapod-5` | 0.847 | 0.714–0.719 |

  The quadrupeds' hip cases are the ones hanging beside the body.
- **Printed volume inside the default bay:** 273–2,814 mm³ per servo. In all three designs every hand-cut pocket is tighter than 0.5 mm somewhere or has no lead exit.
- **Gates at `a382b520`:** `pixi run test-engine` 2282 passed, 53 skipped. `cli/tests` 1077 passed, 1 skipped. After `build-engine` and `stage-engine`, the packaged lifecycle gate passed 23 of 23, and the staged `cadex_library_api.py` carries `servo.bay`.
- **Concerns and assumptions:**
  - The shroud share is a diagnostic, not an A1 proxy. It measures local wrap, not visibility: `ot10-quadruped-2`'s hero `hardware_silhouette_share` is 0.004 while its hip shroud share is 0.198. Nothing is re-scored.
  - Defaults were chosen by judgement and are reversible: 0.5 mm is a printed servo pocket, and 6 mm is room for the lead to turn.
  - The 25T standard servos' bay passes only the spline, because no horn is dimensioned for them.
  - `.ouroboros/goal.md` has an operator modification in the working tree. I left it unstaged and untouched.
  - No new dependency.
- **Next:** a confirmation turn may test this only after its pre-registration is committed. A shroud helper, if one is wanted, would be a separate unit.

Dispatch closed: 1 unit — servo `.bay()` and overlay limb-wrapping (ADR-443), measured read-only on the three 16/21 designs

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: a382b52014bb5e62c2fec8f37edd19ee0e9761ec

## State Impact

- target: brave-stone-9609 — lib.servo parts carry .bay() (case+tabs+spline column+lead room, ADR-443, commit a382b520), like battery/board
- target: chilly-union-8972 — overlay ENCLOSE rule teaches wrapping a servo's .bay() with a 1.6-2.4 mm wall and cutting it (ADR-443)
- target: rough-vale-0587 — servo-case half of the A7 gap now has a product surface; read-only wall-share on 16/21 designs: quadruped hips 0.198/0.390 vs 0.71-0.85 elsewhere; no confirmation turn run yet
