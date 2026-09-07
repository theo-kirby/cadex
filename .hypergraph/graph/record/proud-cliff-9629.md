---
node_id: d7a7c342-363b-507d-be83-bdc327f6cdc4
slug: proud-cliff-9629
title: Stop planetary qualification at measured planet-ring interference
created_at: '2026-09-07T06:26:45+00:00'
parents:
- flat-river-8853
summary: ''
artifacts:
- docs/experiments/planetary_mesh_probe.py
---
## What

Qualified the proposed planetary mesh as one bounded experiment and stopped
at its first failing phase. Added a standalone real-kernel probe and ADR-235,
with matching ROADMAP, L3-COVERAGE and PROVENANCE section 8g notes. Did not
publish a planetary API or change engine source.

## Why

This follows flat-river-8853's first short-plan unit and targets
idle-tower-1624 and brave-stone-9609 (mission 4). The overseer explicitly said
to stop and record if the mesh failed. The work-iteration prohibition on
reconcile overrides the older request for a maintainer pass; state and plan
files are untouched. Assumption: preserve the three pre-existing uncommitted
planetary files rather than adopt or discard an unqualified implementation.

## Method

On arrival, git status already showed edits to CadexCatalog.py,
cadex_library_api.py and cadex_tests/test_library.py. Read their proposed
planetary composition and tested its first sun–planet and planet–ring pair
through build_part_shape in build/release/bin/FreeCADCmd. Configuration:
module 1, sun18/planet18/ring54, three planets, width 6 mm, centre distance
18 mm, sun phase 0, first planet roll 170 degrees, ring roll 180*17/54.

Reproduction independent of the proposed public API:
`build/release/bin/FreeCADCmd -c 'exec(open("docs/experiments/planetary_mesh_probe.py").read())'`.
The probe uses the existing spur generator, with a virtual external gear
cutting the ring's tooth spaces (root radius 26, tip radius 28.25 mm).
It measures common volumes, minimum gaps, root-circle clearances and a
half-tooth-pitch negative control in both meshes. Probe process exit 0
requires valid single solids, the four 0.25 mm clearances and both negative
controls; mesh qualification is explicitly reported as a JSON boolean.

Also ran `pixi run python -m pytest src/Mod/cadex/cadex_tests/test_library.py
-k 'planetary or internal_gear or ring_gear' -q` on the proposal already in
the working tree. No build or stage was performed after mesh failure.

## Result

The proposed recipe has sun–planet common volume 0 and planet–ring common
volume 0.0003548057457830585 mm³. The independent probe reproduces
0.0003548057457972328 mm³ against the 1e-6 bound: qualified=false.
Sun–planet minimum gap 0.002413754511754493 mm; planet–ring gap 0.
All four root-circle clearances are 0.25 mm within 6e-15. Negative controls
collide at 23.461757751818354 and 41.85943815714032 mm³, so the collision
measurement detects bad meshes. An additional run with engine source exported by `git archive HEAD
src/Mod/cadex` produces identical probe JSON, confirming the reproduction
does not require the uncommitted planetary patch. No later phase was qualified. Chordal
cutout error is only a candidate cause, not a proved diagnosis.

Targeted existing tests: 12 passed, 1 failed, 104 deselected in 0.08 s.
The existing test_planetary_spec_numbers expects one "radial line" warning
but gets three (both undercut warnings contain that phrase). This is a
pre-existing uncommitted failure, preserved with the three original edits.
No full engine suite, full build, staged payload, packaged lifecycle gate,
shell gate or multi-phase qualification was run; this commit changes only
experiment/documentation/record files and claims no published behavior.

Next: compound mechanisms stays open. Per the overseer's failure policy,
replan toward headless review; flat-river-8853 already specifies assembly
inventory. Before resuming planetary implementation, explicitly resolve the
preserved uncommitted proposal and its test failure. Do not loosen the mesh
tolerance or claim the current ring profile is qualified.
Dispatch closed: 1 unit — recorded the planetary mesh failure with a reproducible probe.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 8b855815357151646c108e01aab84b51c14c65c6

## State Impact

- target: idle-tower-1624 — Remains open: m1 sun18/planet18/ring54 fails phase-zero planet-ring mesh at 0.000354806 mm³ versus 1e-6 tolerance; standalone probe and negative controls in ADR-235. No planetary published; replan toward headless inventory.
- target: brave-stone-9609 — ADR-235 records a failed internal-ring composition experiment; existing spur generator gives correct 0.25 mm root-circle clearances but overlapping ring mesh. Uncommitted planetary proposal and its pre-existing test failure remain unqualified.
