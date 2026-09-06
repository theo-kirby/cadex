---
node_id: 999fdcfa-5583-5c63-9835-3e49484ba8f3
slug: long-heron-6915
title: Nominal L12 mounting geometry passes headless OCCT probes
created_at: '2026-09-06T21:47:39+00:00'
parents:
- western-water-1442
summary: ''
artifacts:
- docs/experiments/l12_nominal_probe.py
---
## What

Proved a bounded nominal L12-50-210-12-S exterior construction in the existing headless OCCT engine. Added docs/experiments/l12_nominal_probe.py, detailed dimensions, source measurements and approximation limits in PROVENANCE section 8d, an ADR-207 follow-up and a checked ROADMAP geometry-experiment subitem. No public catalog API changed; linear-actuator implementation remains open.

## Why

Iteration 13 follows western-water-1442 short-plan unit 1, serving mission 4 and frontier rising-banner-4325 / brave-stone-9609. The reversible decision is to establish geometry separately before exposing a product family. The overseer requests reconciliation and implementation, but the explicit contributor prohibition forbids reconciliation, and the newer plan separates geometry proof from implementation. STATE.md, PLAN.md, state nodes and the charter were untouched. The supplied checkpoint already includes the previous three source records; the visible unreconciled tail was one planner record, not the older overseer's three-record tail.

Datasheet nominal mounting centres take precedence over the older CAD's 0.5 mm longer spacing. No hardware tolerance or blanket surface correction is inferred. A simplified exterior with declared omitted details is supportable; installation fit, physical inertia and a conservative collision envelope are not established.

## Method

Read the root contract, STATE.md, PLAN.md, VISION, ADR-207, PROVENANCE section 8d and southern-moss-9142. Read the manufacturer revision F datasheet at https://www.actuonix.com/assets/images/datasheets/ActuonixL12Datasheet.pdf and inspect its previously downloaded drawing. Additional targeted measurements use l12_50mm_in.stp from the previously identified manufacturer archive https://www.actuonix.com/assets/images/datasheets/L12_STP.zip; source hashes remain in PROVENANCE. No manufacturer CAD or artwork is redistributed and no manufacturer code is imported.

The supplied clevis's solid 10 has planar flats X = +/-3 mm; at source Y=-67,Z=3, material is present at X=2.9 and absent at 3.1. Rear lug solid 2 has material at X=3.9 and none at 4.1 at source Y=35.5,Z=3. These measure local CAD widths of 6/8 mm, not tolerance. The drawing sets the nominal bore diameter and spacing. PROVENANCE records every primitive axial extent, the simplified housing/clevis transitions and omitted installation details.

Run build/release/bin/FreeCADCmd -c 'exec(open("docs/experiments/l12_nominal_probe.py").read())'. Independently authored boxes/cylinders/booleans construct the housing, rear lug, sleeve, shaft and supplied-clevis approximation. Measure the resulting cylindrical surfaces, probe void/material near both bore walls and flats, and check a translated 120-degree rotation against the explicit mapping (x,y,z) to (100+z,30+x,20+y). No build, staging, GUI, training or remote dispatch occurred.

Baseline gate: CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py. The prior completed payload was used without concurrent staging. Engine source files were not edited and the full engine suite was not run for this documentation/geometry experiment.

## Result

The probe completed with L12-NOMINAL-OK. At extension 0/23.5/50 mm it measures bore spacing 102/125.5/152 mm. All three shapes are valid single solids. All 180 canonical/placed material/void probes pass. Approximation volumes are 18730.103513/20225.108917/21910.966075 mm3; X bounds [-7.45,7.45], Y [-7.5,10.5], Z [-4.5,106.5+extension] mm. Filled exterior volume increases with exposed shaft and must not become a physical inertia claim.

The existing packaged lifecycle/library baseline passed 61 tests, no skips, in 15.30 s, exit 0. This is not packaged actuator verification: there is no catalog implementation to stage. Git diff --check passed. Graph export/check are required after minting this node and before committing. No known regression was introduced.

Next is short-plan unit 2: expose this nominal geometry through the existing LibraryPart contract with explicit approximation metadata, unsupported-selection and extension refusal, qualified operating points and S-switch limits. Pin actual worker geometry and placement, run the full engine suite, at most one full build, completed staging and packaged gates. L3 and broader catalog breadth remain open. No additional source audit is needed for the bounded approximation; any stronger fit or collision claim needs additional evidence.

Dispatch closed: 1 unit — prove nominal L12 mounting geometry and placement while retaining explicit exterior-model limits.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 3773f47f748a5169f091bcd5920193784494677f

## State Impact

- target: rising-banner-4325 — Nominal L12 geometry experiment passes at 0/23.5/50 mm extension with 102/125.5/152 mm bore spacing and 180 canonical/placed probes; family implementation and full L3 remain open.
- target: brave-stone-9609 — PROVENANCE section 8d and an independent OCCT construction now specify the bounded L12 geometry, local CAD bore widths and omitted installation details; no catalog API or fit/dynamics guarantee shipped.
