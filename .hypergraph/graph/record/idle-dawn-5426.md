---
node_id: 50f7946e-f882-56c5-8ce1-a2837b1507da
slug: idle-dawn-5426
title: Pololu N20 gearmotor joins the catalog with packaged verification
created_at: '2026-09-06T21:12:21+00:00'
parents:
- still-badger-2386
summary: ''
---
## What

Added lib.gearmotor("pololu-2367"), the first L3 motor over CadexCatalog: Pololu's N20-size 100:1 MP 6 V variant without encoder. The ordinary LibraryPart carries a BREP envelope, D shaft, mounting bores and independently copied spec rows. Catalog discovery, response golden, XSCRIPT, INTEGRATION, PROVENANCE, ROADMAP and ADR-205 describe the same surface. Only the N20 subitem is checked; broader L3 remains open.

## Why

Iteration 10 follows still-badger-2386 and the selected short-horizon N20 bet, serving rising-banner-4325 and brave-stone-9609 (mission 4). The incoming tail contained two records, so proceed without reconciliation. Generic N20 dimensions do not determine performance: choose one specific manufacturer variant rather than inventing interchangeable ratings. The reversible fidelity choice is a documented external envelope with no actuator helper or physical inertia claim. Previous stale-shell work does not prove general concurrency safety; concurrent project acceptance/rebuilds still require sequential use.

## Method

Read Pololu's https://www.pololu.com/product/2367/specs and product details https://www.pololu.com/product/2367; visually rendered page 4 of https://www.pololu.com/file/0J949/micro-metal-gearmotors-dimensions.pdf (drawing date 2024-04-03). Poppler was unavailable; an isolated uv PyMuPDF run rendered the drawing. No repository dependency or manufacturer artwork/code was added. PROVENANCE section 8b retains sources and the dimension conflict: the page says 25 mm, its footnote 26 mm, and the drawing specifies rear OL maximum 25.6 mm, which the envelope uses.

The model has a 12 by 10 mm rear section, a shaft tip 10 mm forward of the gearbox face, 3 mm shaft diameter, 2.5 mm flat-to-opposite dimension, 4 mm boss diameter and 0.7 mm boss height; M1.6 centres lie at X = +/-4.5 mm. The filled rear box, assumed 1 mm bore depth and flat start/transition are explicitly approximate; bore depth is not screw engagement permission. Ratings at 6 V: no-load 220 RPM (+/-20%), 0.07 A (+/-50%), extrapolated stall 0.67 A and 92.18251 N mm. Manufacturer mass is 9.5 g; no continuous torque, thermal model, density or inertia is inferred.

Verification commands: pixi run build-engine (one full build); pixi run python -m pytest src/Mod/cadex/cadex_tests; pixi run install-release (refresh Python help text after its correction, no second build); pixi run stage-engine; after staging exited, CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py. Final catalog and generator files compare byte-equal to the staged copies. Tests pin dimensions/ratings, nested-row isolation, rejection of unsourced variants, placement and discovery; the real-kernel library integration builds canonical and rotated motors as valid solid outputs.

## Result

Initial focused tests caught an incorrectly transcribed expected gear ratio in the new test; corrected the expectation to the manufacturer's exact tooth-count formula (100.37004662004662). Final non-kernel library checks: 38 passed. Engine suite: 1980 passed, 52 skipped in 265.37 s. One engine build and installation: exit 0. Stage: exit 0, 2.4 GB local development payload. Its relocation audit reports 248 external-path violations: this stage-only payload deliberately retains local dependencies and is not a portable release. Packaged lifecycle/library: 54 passed, no skips, in 18.89 s. Graph export/check and git diff --check: exit 0 with no graph violations or warnings, checked again after recording.

Next: L3 retains BLDC, linear actuator, solenoid, joints and compound gearing; select the next bounded family in the separate planner pass. This record brings the tail to three; maintainer/replanning is due in its own role. No state or plan nodes were changed, no lifecycle scaffold needed changes, no GUI or remote training was run, and no inherited files were touched.

Dispatch closed: 1 unit — source, implement and verify the first N20 gearmotor catalog family.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 7d62272def1b8629306bbc00f20c417124a093af

## State Impact

- target: rising-banner-4325 — First L3 motor shipped as lib.gearmotor(pololu-2367), with manufacturer dimensions and qualified 6 V ratings; real-kernel and packaged gates pass. Broader L3 stays open.
- target: brave-stone-9609 — Catalog discovery now includes the sourced Pololu #2367 N20 envelope, D shaft and mounting bores with explicit approximations; no continuous torque or inertia claim. Engine 1980 passed/52 skipped; packaged lifecycle/library 54 passed.
