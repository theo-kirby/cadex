---
node_id: fa7ac01b-e754-59b1-b8bf-094bf68ebef1
slug: first-wind-9707
title: SKF GE 6 C joint source and nominal geometry qualified
created_at: '2026-09-06T22:26:04+00:00'
parents:
- clever-falcon-0085
summary: ''
artifacts:
- docs/experiments/ge6c_joint_probe.py
- docs/PROVENANCE.md
---
## What

Qualified SKF GE 6 C nominal spherical plain bearing geometry from the identified manufacturer catalog. Added PROVENANCE §8f, ADR-210, a narrow completed ROADMAP qualification item and an open implementation item, and a reproducible standalone headless OCCT probe. No catalog API ships.

## Why

Iteration 17 follows clever-falcon-0085 and serves mission 4, rising-banner-4325 and brave-stone-9609. Choose a small linkage bearing whose manufacturer supplies both spherical and mounting/abutment dimensions, avoiding guessed essential interfaces. Reversible assumption: qualify the nominal two-ring approximation before delivery, with omitted chamfers/liner/clearance explicit. The injected overseer asks for reconciliation, but this work dispatch expressly forbids it with no exceptions; no maintainer or planner mutations were performed. The existing planned joints unit remains applicable.

## Method

Read STATE.md, PLAN.md, VISION.md, graph contract/config and actor, PDF and record skills. Downloaded SKF BU/P1 06116/1 EN (May 2013) from the manufacturer URL cited in PROVENANCE §8f; SHA-256 df51e55192dc9ce138e371e2f5047cfbceeba7f2ac6246f92e5bd3d7f24930cb. Rendered and inspected printed pages 132–133 (PDF 134–135), matching the second row across both tables. pdftotext was unavailable and pixi lacked fitz; used temporary uv --with pymupdf without changing repository dependencies. No manufacturer assets or code committed.

Ran build/release/bin/FreeCADCmd -c 'exec(open("docs/experiments/ge6c_joint_probe.py").read())'. Checked analytic volumes, actual bore/OD/sphere surfaces, ring and test-shaft intersections, limiting shoulders on both sides, invalid tilt rejection, material/void points and oblique placement. Ran CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py. Git diff --check passed; graph export/check follows minting before the single commit.

## Result

GE6C-NOMINAL-OK: -13/0/6.5/13 degrees, two valid single solids each, outer/inner volume 318.348056/245.044227 mm3, zero overlap, 96 canonical/placed material/void probes, 16 clear limiting-shoulder checks. Bore 6, OD 14, inner/outer width 6/4, spherical diameter 10 mm; shaft shoulders 7.4–8, housing openings 9.5–12.7 mm from source. The nominal contract is supportable for conditional delivery, not a fit, tolerance, physical inertia or load guarantee. Existing packaged baseline: 76 passed, no skips, 16.23 s. No runtime changes, full engine suite, build or staging; no packaged joint claim.

Next: deliver this same GE 6 C variant through existing catalog/LibraryPart recipes with qualified metadata and real-worker/discovery/fresh packaged evidence. Full L3 remains open. Solenoid delivery remains deferred: current 412 mounting is incomplete; older TAU has incompatible dimensions; Ledex B7 lacks engagement depth and maximum mechanical travel. Do not transplant older slots or use a force-plot endpoint as a stop. Separate maintainer handles the tail; this unit does not reconcile or edit STATE/PLAN/charter.

Dispatch closed: 1 unit — SKF GE 6 C source and nominal geometry qualification.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 4e197b49bff8520e7646945e25cacfdd4bea7423

## State Impact

- target: rising-banner-4325 — SKF GE 6 C source and nominal two-ring OCCT qualification pass; conditional catalog delivery next, full L3 and exact solenoid interface gaps remain open.
- target: brave-stone-9609 — GE 6 C manufacturer datums, shoulder limits, qualified ratings and approximation contract recorded in PROVENANCE §8f; no public joint API yet.
