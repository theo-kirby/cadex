---
node_id: 35557736-25a5-5cd3-b58b-7dc802aa3279
slug: mellow-garden-0940
title: Compose the rack and pinion as a library value with real-kernel mesh and clearance tests
created_at: '2026-09-07T06:03:20+00:00'
parents:
- wild-beacon-4213
summary: ''
---
## What

Composed the rack and pinion as a library value (ADR-234): `CadexCatalog.rack_and_pinion_spec(module, pinion_teeth, rack_teeth, backlash=0)` derives the meshing numbers from `gear_spec` (centre distance, backlash as a radial shift of `backlash/(2 tan 20°)`, root clearance, travel per revolution and per degree, rack length, nested member specs), and `lib.rack_and_pinion(module, pinion_teeth, rack_teeth, face_width, backlash=0, bore=None, rack_height=None, rotation_degrees=0, ...)` builds the pinion through `lib.spur_gear` rolled so tooth 0 points at the rack and the rack through `lib.rack` with its pitch line at Y = −centre distance and a tooth space under the axis, returning one two-solid compound placed like every other library value. `rotation_degrees` turns the pinion and slides the rack by the matching travel, so one value publishes at any phase. Stubbed tests pin the spec, refusals and recipe; a real-kernel driver measures the mesh and the clearances; cadexd publishes a canonical and a placed composition; ADR-234, PROVENANCE §8g, L3-COVERAGE, ROADMAP, XSCRIPT and INTEGRATION carry it.

## Why

Short-plan rank 2 (`placid-delta-6677`), dispatched by the overseer after rank 1's record closed; it serves mission 4's compound-mechanisms criterion (`idle-tower-1624`) and the parts-library node (`brave-stone-9609`). Assumptions taken without a human: the signature gained `bore`, `rack_height` and `rotation_degrees` keywords beyond the plan's `(module, pinion_teeth, rack_teeth, face_width, *, backlash=0)` because a composition needs a rack height, the pinion's bore is the only way to mount it, and the mesh test needs phases — all default to the plan's shape. Backlash is bounded to 0.1 module and realised as a radial shift rather than tooth thinning, because that reuses the ADR-233 generator unchanged; the `gears` family notes name the composition rather than a new catalog family, so the `describe_api` golden does not move.

## Method

1. Read the ADR-233 generator, `LibraryPart`, `_place` and the joint's compound pattern; wrote the catalog spec, the composition and the tests.
2. Stubbed tests (`test_rack_and_pinion_spec_numbers`, `_spec_refusals`, `_recipe_and_spec`) plus two publication rows in `_KERNEL_SCRIPT` as compounds.
3. `test_rack_and_pinion_real_kernel_mesh_and_clearance`: the actual part worker builds m2z20r10 (backlash 0), m1z24r12 (backlash 0.05, bore 4) and m2z20r10 (backlash 0.2, bore 6) at nine phases each (seven across one pitch angle, plus 2.5 and −1.3 pitches), asserting pinion∩rack common volume < 1e-6 mm³, tip-to-root clearance 0.25 m plus the shift both ways, and the flank gap in [backlash·cos 20°/2, that + 1e-3·m]. Negative controls: the rack slid half a pitch must collide, and an unshifted m2z12 pinion must interfere.
4. Full engine suite on the source tree, then one `pixi run build-engine`, `pixi run stage-engine` to completion, then the packaged lifecycle/library gate with `CADEX_ENGINE_ROOT` on the fresh payload.

## Result

Mesh: max common volume 0.0 mm³ at all 27 phase builds; flank gaps [0, 0.00045], [0.02349, 0.02408], [0.09397, 0.09442] mm against expected 0, 0.02349, 0.09397 (the excess is the inscribed chord's sag, at most 4.5e-4·m). Controls: half-pitch collision 182.0 mm³; z12 undercut interference 0.061 mm³ at phase 0 — the ADR-233 warning now has a number behind it. Two test mistakes were fixed before the run (a valid module in the refusal rows, a sign on the rack-tip clearance) and are not in the tree. Library suite minus the cadexd test: 103 passed. Full engine suite before the build: 1 failed, 2061 passed, 52 skipped, 315.82 s — the one failure being the cadexd publication test against the not-yet-rebuilt installed engine, which passed alone after the build. `pixi run build-engine` exit 0; `pixi run stage-engine` exit 0 (2.4 GB payload). Fresh packaged lifecycle/library gate with `CADEX_ENGINE_ROOT` on that payload: 119 passed, no skips, 80.77 s. Not verified: `pixi run gate` (no `shell/` line changed) and ctest (no C++ changed). The unreconciled tail is now three nodes (the bet, rank 1's record, this one); a maintainer pass is due before rank 3, the planetary gearbox, which needs an internal ring from the same generator.

Dispatch closed: 1 unit — rack and pinion composed as a library value with real-kernel mesh and clearance evidence, documented and gated.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: fb09c52125422fd37612bcaa642f5c1f9da7cb96

## State Impact

- target: idle-tower-1624 — lib.rack_and_pinion composes the ADR-233 gear and rack as a two-solid compound at the standard centre distance with backlash as a radial shift and any phase by rotation_degrees; real-kernel mesh test shows zero common volume at nine phases for three configurations, 0.25 m plus shift root clearance both ways and the flank gap equal to backlash·cos 20°/2 within chord sag, with two negative controls (ADR-234; 2061/52 pre-build, 119/0 packaged). The planetary gearbox is the last open half of the criterion
- target: brave-stone-9609 — The gears family gains the rack_and_pinion composition over CadexCatalog.rack_and_pinion_spec (centre distance, travel per revolution, datums, nested member specs), verified on the fresh staged payload; geometric mesh only, no load, stiffness or efficiency
