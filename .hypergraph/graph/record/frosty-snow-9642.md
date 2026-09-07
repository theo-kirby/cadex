---
node_id: 136972f6-7b89-5809-ac5b-9018affe3358
slug: frosty-snow-9642
title: Ship bounded nominal L12 catalog geometry with packaged verification
created_at: '2026-09-06T22:03:39+00:00'
parents:
- long-heron-6915
summary: ''
---
## What

Ship lib.linear_actuator("l12-50-210-12-s", extension=...) over CadexCatalog and the existing LibraryPart/part-domain recipe contract. The only supported variant has bounded geometric extension [0,50] mm, nominal mounting centres, supplied-clevis approximation and qualified specifications. Add discovery golden, source pins/refusals, actual worker interface and placed-geometry tests, cadexd publication, provenance, XSCRIPT documentation, ADR-207 follow-up and the narrow ROADMAP implementation checkbox. Full L3 remains open.

## Why

Iteration 14 follows long-heron-6915 and short-plan unit 2, serving mission 4 and rising-banner-4325 / brave-stone-9609. The prior geometry experiment resolves the construction contract; expose that same bounded approximation without inventing installation fit or a dynamics abstraction. Use datasheet nominal spacing rather than the older STEP's 0.5 mm longer spacing, and retain the discrepancy and explicit approximation limits in spec. No further source audit is needed: the manufacturer evidence and operating points were already read and recorded in PROVENANCE section 8d and the causal records.

The overseer requests reconciliation when the tail reaches three records, but this contributor dispatch explicitly forbids reconciliation without exception. Leave the resulting three-record tail to the separate maintainer/planner pass. No STATE, PLAN, state nodes or charter files are edited.

## Method

Compose ordinary boxes, cylinders, common/fuse/cut and existing placement. Datum is rear bore centre, travel +Z, both 4.25 mm mounting bores along X; canonical spec centres remain canonical after placement. Refuse unsupported stroke, gearing, voltage or switch variant, nonfinite/non-numeric/bool extension and extension outside [0,50]. Spec separates 12 V maximum lifted force 80 N, unloaded speed 6.5 mm/s, peak-power point 62 N at 3.2 mm/s, at most 20% duty and -10 to +50 C. S switches stop within 0.5 mm of stroke ends; geometric endpoints do not promise powered reachability.

Probe actual worker BREP for all three extensions, independent of returned spec: valid single solids, measured cylindrical bore surfaces and bounds, bore void/material near walls, lug flats, sleeve/shaft material, translated cyclic rotation with independently computed point mapping. Publish canonical/placed library values through cadexd. No manufacturer CAD, artwork or code is redistributed. No dependency, shell, protocol operation, training, cloud or remote change.

Run pixi run python -m pytest src/Mod/cadex/cadex_tests; then one pixi run build-engine, rerun the full suite, complete pixi run stage-engine, then CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py. Build, source suites, staging and packaged tests were sequential; staging never overlapped any test suite.

## Result

Actual library geometry passes 180 canonical/placed material/void probes at 0/23.5/50 mm extension; measured bore spacing is 102/125.5/152 mm, valid single solids and expected bounds. Source refusal/spec/discovery tests and freshly staged actual worker/publishing tests pass. Exterior geometry remains an approximation: filled internals, simplified housing/clevis transitions and omitted installation details establish no conservative collision envelope, installation fit, physical inertia, load or dynamics guarantee.

Initial focused library suite: 61 passed in 2.56 s before adding the publication outputs. First full suite: 2001 passed, 52 skipped, one failed in 263.66 s, exit 1. The publication test reported "'LibraryAPI' object has no attribute 'linear_actuator'" because its sandbox worker loaded the stale installed engine library. Single build/install exited 0. Post-build full suite: 2002 passed, 52 skipped in 258.23 s, exit 0. Staging exited 0 and produced the 2.4 GB local unrelocated payload, with expected external-path diagnostics: this is not a distributable release-bundle claim. Packaged lifecycle/library suite: 76 passed, no skips in 19.80 s, exit 0. git diff --check passes. Graph export/check run after minting and before the single commit.

Next: maintainer/planner can reconcile the now-three-record tail and choose the next L3 family (solenoid/joints per the current medium horizon). This closes only the L12 implementation item; wider L3, catalog breadth and physical installation/dynamics claims remain open. No known failing test remains.

Dispatch closed: 1 unit — ship and verify the bounded nominal L12 catalog variant with qualified specifications and explicit geometry limits.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 21b18b397c6f8eb712497dda0dc8f30a9a8cc25b

## State Impact

- target: rising-banner-4325 — L12-50-210-12-S now ships through lib.linear_actuator with bounded extension, qualified specs and canonical/placed worker and packaged evidence; full L3 remains open.
- target: brave-stone-9609 — Linear-actuator discovery and LibraryPart recipe added with nominal bore geometry, explicit older-CAD discrepancy and approximation limits; post-build full suite 2002 passed/52 skipped and packaged gates 76 passed.
