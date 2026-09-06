---
node_id: e6bede66-d7c6-5ef0-b1fd-13a6797d0162
slug: floral-stone-2866
title: HOBBYWING BLDC mounting envelope joins the catalog with explicit fit limits
created_at: '2026-09-06T21:32:27+00:00'
parents:
- strong-grotto-8980
summary: ''
---
## What

Added lib.bldc("hobbywing-30415200"), a manufacturer-specific HOBBYWING Skywalker 2820 SL 550KV rear-mount envelope over CadexCatalog and the ordinary LibraryPart. Catalog discovery, the describe_api response golden, XSCRIPT, INTEGRATION, PROVENANCE section 8c, ADR-206 and a narrow ROADMAP subitem describe its fidelity. L3 remains open.

## Why

Iteration 11 follows strong-grotto-8980 and its refreshed short-horizon BLDC bet, serving mission 4 and frontier nodes rising-banner-4325 and brave-stone-9609. The injected overseer request to reconcile refers to an older three-record tail: the current state is reconciled through idle-dawn-5426 and the plan through strong-grotto-8980. Export confirms only that planner bet was unreconciled on arrival. The explicit contributor prohibition on reconciliation takes precedence; no state, plan or charter was edited.

Choose the reversible envelope representation where source detail is missing. The drawing dimensions the shaft collar diameter but not its axial length: reserving that diameter across the full projection avoids inventing a coupling-fit interface. It intentionally cannot answer free-shaft-length or coupling-fit questions. Keep current/power duration qualifications instead of turning a marketing column heading into a continuous robot-joint rating. No new actuator abstraction or runtime dependency.

## Method

Read the manufacturer specifications at https://www.hobbywing.com/en/products/skywalker2814.html and visually inspect the single-page 2820SL drawing at https://www.hobbywing.com/en/uploads/file/20231121/6ce36297af7f04e8e0c41c3b28a36dbd.pdf. Web screenshot retrieval failed; an isolated uv PyMuPDF run rendered the downloaded PDF for inspection. No source artwork, CAD or code was copied into the repository.

The case is diameter 35.1 by length 40 mm; a diameter-11 rear boss extends 2 mm behind the mounting plane. A conservative diameter-10.5 shaft/collar reservation projects 18 mm forward, for overall length 60 mm. The actual shaft diameter is 5 mm, retained as metadata, not misrepresented as available coupling length. Rear M3 pairs span 19 and 25 mm in the canonical XY frame. Bore depth is an explicit 1 mm assumption, not engagement permission; X/Y do not claim cable clocking. Filled rotor/stator space is not physical inertia. Leads, connectors and supplied adapters/plate are omitted, so no full installation clearance claim is made.

Metadata carries 550 rpm/V, 6S supply, 144.5 g, and no-load 1.38 A at 22.2 V. The manufacturer's 40.9 A / 910.2 W entries are limited to 46 seconds and omit full cooling conditions; they remain explanatory notes, not numeric control limits. No torque rating or torque constant is inferred.

Tests pin source dimensions and qualifications, nested-row isolation and rejection of generic sizes/unsourced windings. Real OCCT tests check one valid solid, bounds, mounting-bore voids and surrounding material, rear boss and collar reservation, then the same probes under nontrivial roll, direction and translation. The library integration accepts canonical and placed BLDC solids through cadexd. Both kernel tests resolve modules from the selected payload when CADEX_ENGINE_ROOT is set.

Commands: pixi run build-engine (one full build); pixi run install-release (refresh final Python help text, no second build); pixi run stage-engine; pixi run python -m pytest src/Mod/cadex/cadex_tests; after staging exits, CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py. Final catalog and library modules compare byte-equal to their staged copies.

## Result

Focused BLDC checks: 7 passed. One engine build and final Python installation: exit 0. Staging: exit 0, 2.4 GB development payload; its relocation audit reports the same 248 external-path violations as the preceding N20 unit, so this is not a portable release. Packaged lifecycle/library: 61 passed, no skips, in 19.51 s.

The first full engine run was incorrectly overlapped with staging: 1986 passed, 52 skipped, one failure in test_nothing_from_the_analysis_tree_reaches_a_staged_payload (265.91 s). It saw bin/ccx in the temporary unpruned copy. After staging completed, that same isolation check passed (1 passed in 2.26 s). This is a scheduling error in this dispatch, not a pre-existing test failure or a change to packaging policy. The complete stable rerun passed: 1987 passed, 52 skipped in 254.81 s, exit 0. Future engine suites must not overlap payload staging.

Final git diff --check and graph export/check: exit 0, no graph violations or warnings (rechecked after minting).

Next: the refreshed plan's linear-actuator family is the next bounded L3 unit. BLDC torque, coupling fit and additional sizes remain unsupported; solenoids, joints and compound gearing also remain open. No GUI, remote execution, training, inherited-tree edit or lifecycle change occurred. The development-only payload limitation is preserved. This unit adds one contributor record; reconciliation belongs to the separate maintainer role.

Dispatch closed: 1 unit — source, implement and verify a BLDC rear-mount catalog envelope with explicit shaft-fit and rating limits.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: e1ac654d7cd5889b0a6da00960932a462d66b619

## State Impact

- target: rising-banner-4325 — Added lib.bldc(hobbywing-30415200), a sourced 550KV rear-mount envelope; real-kernel interface and packaged gates pass. L3 stays open: torque, shaft coupling fit, more sizes and remaining families are not supplied.
- target: brave-stone-9609 — Catalog now includes HOBBYWING 30415200 mounting dimensions, conservative shaft/collar reservation and qualified no-load data. Engine 1987 passed/52 skipped; packaged lifecycle/library 61 passed.
- target: early-arbor-7123 — Do not overlap the engine suite with payload staging: isolation checks can observe transient bin/ccx before pruning. Stable rerun passes; local development payload retains 248 relocation audit violations and is not portable.
