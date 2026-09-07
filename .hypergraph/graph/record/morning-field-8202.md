---
node_id: 24297fe9-11ce-578f-8265-953dc2f845cc
slug: morning-field-8202
title: Deliver qualified SKF GE 6 C joint catalog value
created_at: '2026-09-06T22:43:24+00:00'
parents:
- first-wind-9707
summary: ''
artifacts:
- src/Mod/cadex/cadex_tests/test_library.py
- docs/PROVENANCE.md
---
## What

Delivered lib.joint("skf-ge-6-c", tilt_degrees=...) through CadexCatalog and LibraryPart using existing part recipes. The body is a two-solid compound; unsupported variants and nonfinite, boolean, nonnumeric or out-of-range tilt are refused. Added sourced dimensions, revision/hash, abutment limits, qualified ratings, copy-isolated metadata, discovery golden, actual worker geometry and cadexd publication tests. Updated XSCRIPT, PROVENANCE, ADR-211 and the narrow ROADMAP implementation checkbox.

## Why

Iteration 18 follows first-wind-9707 and the overseer's short-horizon delivery instruction, serving mission 4 and real frontier targets rising-banner-4325 and brave-stone-9609. Reversible assumption: deliver exactly the qualified nominal two-ring contract, with inner tilt about canonical Y before placement, using a compound to preserve both rings. Do not invent running clearance, fit, load capacity, dynamics or physical inertia from geometry. The work-dispatch prohibition on reconciliation overrides the overseer's request to reconcile at three records; a separate maintainer owns that next pass.

## Method

Read STATE, PLAN, VISION, graph contract/config and actor/record skills, then prior qualification and existing catalog/LibraryPart precedents. Reused sphere/common/cut/compound/transform; no new worker op, protocol op, assembly solver, shell change or dependency. Source identity and nominal geometry derive from the previously rendered SKF publication in PROVENANCE §8f; no new external source or downloaded asset.

Focused joint tests: 14 passed. Actual worker checks construct all four tilts (-13/0/6.5/13) and independently check analytic ring volumes, actual bore/OD/sphere surfaces, non-overlap, test-shaft clearance, limiting shoulders on both sides and 96 canonical/placed material/void probes. Placed recipe checks additionally read cylinder axes/radii and sphere centres after cyclic rotation and translation. Publication requires compound for both canonical and placed joint outputs.

Ran pixi run python -m pytest src/Mod/cadex/cadex_tests, then one pixi run build-engine (completed exit 0), then pixi run stage-engine (completed exit 0), then CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py. Fixed the publication test's old blanket single-solid assertion, reran the packaged gate, then reran the full engine suite. Build/staging/gates did not overlap. Git diff --check passes; graph export/check runs after minting before the single commit.

## Result

Final full engine suite: 2016 passed, 52 skipped, 259.29 s. Final fresh packaged lifecycle/library: 90 passed, no skips, 16.30 s. Nominal outer/inner ring volumes remain 318.348056/245.044227 mm3. The initial pre-build suite had 2015 passed, 52 skipped and one failure because the installed worker lacked joint. First packaged run had 89 passed and one assertion failure because joint correctly published as compound; fixed the test, no further runtime edits or build.

One full build/install exited 0 with CMake policy and duplicate-rpath install messages. Completed staging produced a 2.4 GB local development payload and the same 248 external-path relocation violations documented by prior catalog units (idle-dawn-5426/floral-stone-2866); this is not a portable release. No GUI, remote training, state/plan/charter edits or second full build.

Next: the short joint qualification/delivery pair is now supported by source, real-worker and fresh packaged evidence. Full L3, additional common BLDC scope, solenoid source gaps and compound mechanisms remain open; planner should qualify the remaining L3 scope before selecting another delivery. Tail reaches three unreconciled records including this unit; separate maintainer should reconcile. No whole-goal completion claim.

Dispatch closed: 1 unit — qualified SKF GE 6 C catalog delivery with worker and packaged verification.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 458f68d3693a5b1d06ed7b67c7ba2c400fd90e56

## State Impact

- target: rising-banner-4325 — SKF GE 6 C joint delivery passes actual worker and fresh packaged verification; full L3 and solenoid delivery remain open.
- target: brave-stone-9609 — lib.joint exposes one sourced nominal two-ring variant with bounded tilt, qualified metadata and discovery/publication tests; no fit or dynamics guarantee.
