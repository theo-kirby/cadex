---
node_id: ccc20b9c-115a-5c8a-be27-36385e02dbdd
slug: open-pine-9349
title: Solenoid mounting follow-up defers delivery and advances joints
created_at: '2026-09-06T22:17:18+00:00'
parents:
- frosty-creek-6723
summary: ''
---
## What

Completed the mounting-source follow-up to frosty-creek-6723. PROVENANCE section 8e now records incompatible older TAU-0730TM dimensions and manufacturer Ledex B7 evidence, download hashes, missing interfaces and search limits. ADR-209 defers solenoid catalog delivery and selects joints source qualification next. A narrow ROADMAP follow-up checkbox closes; solenoid implementation and full L3 stay open. No geometry, API or source assets added.

## Why

Iteration 16 is one bounded source-audit/decision unit serving mission 4, rising-banner-4325 and brave-stone-9609, following the overseer's instruction to seek missing mounting evidence or qualify an alternative, then advance joints if neither path resolves the gap. The reversible assumption is to retain the planned complete-interface bar instead of silently weakening it to fit the available drawing. The older drawing is not evidence for the newer revision. A graph axis endpoint is not a mechanical travel stop. This avoids inventing source dimensions or another partial model.

The tail reaches three records with this node. The overseer's reconciliation suggestion conflicts with the explicit work-dispatch prohibition: no reconcile, state writes, PLAN.md edits or .ouroboros edits were performed. A separate maintainer/planner pass owns reconciliation and plan projection.

## Method

Read STATE.md, PLAN.md, VISION.md, .hypergraph/AGENTS.md, config, actor/record/PDF skills and the previous audit. Searched exact TAU0730TM-14 and manufacturer Ledex alternatives. The BC Robotics product page links https://bc-robotics.com/datasheets/TAU-0730TM.pdf; this unversioned drawing lacks manufacturer identification and cannot establish current 412 mounting dimensions. https://www.jameco.com/Jameco/Products/ProdDS/2219330.pdf failed with HTTP 403 and was not treated as inspected evidence.

Downloaded https://www.johnsonelectric.com/pub/media/image/tmp/metric-imperial/B7_20210611.pdf and https://www.johnsonelectric.com/pub/media/image/tmp/metric-imperial/20200212_Open_Frame_DC_in_2_.pdf outside the repository. Rendered both B7 pages and the older TAU page at 2x with uv run --with pymupdf python and visually inspected them. Computed SHA-256 hashes recorded in PROVENANCE. Extracted text from all 39 open-frame catalog pages: no B7 matches; its selection table does not supply a B7 travel limit. Located the older tubular catalog through https://www.relayspec.com/suppliers/j/johnson_electric/news/2018/09_20b/09_20b.php, but did not qualify a tubular variant. This is not an exhaustive survey of solenoids.

Ran CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py against the existing completed payload. No runtime changes, build or staging. Git diff --check passed. Graph export/check runs after minting before the single commit.

## Result

Older TAU mounting separation is 20 mm versus the current drawing's 18.2 mm; its body/overall lengths also differ. Do not transplant its slot geometry. Ledex B7-212-B-4 provides a manufacturer coil identity, qualified ratings and dimensioned M3x0.5 mounting-plane centres, but the examined sources do not state engagement depth or maximum mechanical travel. The 0.4-inch force-plot limit cannot fill the latter. B7 supports nominal planar interface study, not the planned complete contract. No new OCCT construction, endpoint probes or packaged solenoid implementation are claimed; the original 412 remains explicitly partial.

Existing packaged baseline: 76 passed, no skips, 16.12 seconds, exit 0. Full engine suite not run for this documentation-only unit. No known regression introduced. Three unreconciled nodes now need the separate maintainer pass.

Next: planner should advance the existing medium L3 joints source-qualification unit, not repeat this solenoid audit. Solenoids remain open for new manufacturer evidence or a separately justified narrower contract; other variants were not disproved. No human step, GUI, training, remote dispatch or provisioning occurred.

Dispatch closed: 1 unit — record incompatible and incomplete solenoid interface evidence, defer delivery and advance joints source qualification.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 389e60e9efbd7098a5744aa741567d3ab8e20b89

## State Impact

- target: rising-banner-4325 — Older TAU mounting dimensions conflict with current 412; Ledex B7 provides planar mounting evidence but lacks engagement/travel limits. Solenoid delivery remains open; next bounded L3 source unit is joints per ADR-209.
- target: brave-stone-9609 — PROVENANCE section 8e records source hashes and exact remaining solenoid interface gaps; retain the partial model and no solenoid API. Existing packaged lifecycle/library baseline passes 76 tests.
