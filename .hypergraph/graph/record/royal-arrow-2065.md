---
node_id: 1fa2daa0-f64f-506c-a284-b54d8f95aeeb
slug: royal-arrow-2065
title: Share the reference scene between live review and recorded policy videos
created_at: '2026-09-12T21:44:20+00:00'
parents:
- modest-journey-2059
summary: ''
artifacts:
- docs/probes/review-style/implementation.json
- docs/probes/review-style/compare.py
---
## What

Implemented the shared reference environment for the live review viewport and headless policy-video capture (ADR-301). Replaced the separate review WebGL shader / CPU video rasterizer with one shipped browser scene. Rendered real Reed final and retained intermediate policies, preserving earlier video references. Added a repeatable persistent-dashboard/reference/decoded-frame comparison and browser regression, updated product/provenance/operator docs and the landed roadmap item.

## Why

Advances D11 / fair-wolf-4645 and maintains the D10 / deep-clover-6012 operator surface. This is the critic's requested implementation unit following modest-journey-2059, not another baseline or contract-only pass. Exact retained geometry and poses remain authoritative. A common renderer lets a pixel comparison establish viewport/video agreement instead of independently tuning two pictures. The active project remains Reed copy29/copy100; no project switch or new training experiment was needed for this rendering unit.

## Method

Read the actor, Ouroboros and hypergraph contracts, VISION and prior reference record; inspected the specified neural-whoop scene/environment/geometry/capture sources and decoded dark policy frames. Adapted its MIT environment and floor-only code at reference commit 31caeb28abb3bdab8d9030bfc91f0c3f48ffa63a, carrying full notices. Added the pinned upstream Three.js r160 module (SHA-256 3e690ac7d180b0aadf0891bea39eec643e29e2d3e75c99b18689518665f69ba6). Written dependency reason: shared ACES colour management, rough materials, antialiasing and fitted shadow maps, locally available without CDN/npm, avoid reimplementing those mechanisms in our shader. Promoted the existing DevTools pipe driver from tests into the CLI; no Python dependency added. Chromium and FFmpeg are video prerequisites. No shell/GPL code was copied, sibling writes made, or engine/protocol/payload/trainer changes introduced.

Python retains policy/model/task/seed verification, bounded geometry, solved-pose validation, per-project render lock, fixed whole-trajectory camera, 10 fps sample hold plus final pose, encode and complete decode. The shared scene uses uniform mm-to-m conversion and keeps public metadata in mm/Z-up/xyzw. The presentation floor sits just below bounds, is front-sided for underside inspection, and never replaces the finite model slab. New video records include style source digest, renderer version, projection, camera, bounds and resolution; older records/files survive, including references originally in run.json.

Ran PYTHONPATH=cli pixi run python -m cadex_cli.video against operator-projects/ot5-biped-copy29 for copy100 and probe3-checkpoint20. Ran docs/probes/review-style/compare.py against the persistent private-network URL on port 8765, working project and read-only sibling reference; also ran docs/probes/operator-review/verify.py there. Only the reference-light harness is temporary: the operator check and comparison use the real persistent server. The reference frame uses the actual unmodified reference modules with Reed's identical geometry/camera/materials, supplementing the prior actual dark drone frames. Inspected reference, persistent and decoded final frame side by side, plus default/close/wide/under orbits and the decoded checkpoint frame. Bulk PNG/HTML/video artifacts remain project-local under evidence/style40 and runs; compact evidence is docs/probes/review-style/implementation.json.

## Result

Shared-scene D11 evidence now exists. Persistent viewport and capture page at the same solved pose/camera/resolution produce byte-identical 512-square PNGs; decoded final video has mean absolute RGB error 1.6423/255 (threshold 3). Side-by-side reference/Cadex floor/grid, fog/horizon, light palette and camera occupancy agree. No environment edge/wall/ceiling appears in fit, 0.7x close or 3x wide orbit; close retains torso/feet, underside remains inspectable. Shadows are grounded and filtered; Cadex's tighter shadow frustum and scale-derived bias differ deliberately from the reference's 1 m minimum / 2 mm bias. Neither simulates area-light penumbrae. The README states this assessment rather than treating pixel coverage as visual acceptance.

Final copy100: revision 25d9b6ab7472b968a3a72691ca44113ea86beda85802af3e22d9270952cb71fc, policy 9e1674abf4dd70317dd6e3de32dd25164d09e2619fdde6c418c538e39a900903, video c0723e47c6c73c4662a7a6aef20fbdbab462c3fcee8e7428ba0ee5dc17a9f293, 8 frames / 0.62 simulated seconds / 2.313 render seconds. Checkpoint20: video 3709db0d97f7c9771b4c4d004f98c59b872a904acfffce64b3bb19049f2f2998, 81 frames / 8 simulated seconds / 20.025 render seconds. Both use style digest 27893221b3c6cf784d62c16fdaa5c88d1beb031bcb195e5f34e1598ea56e5b0c, Three.js r160 / Chrome 152.0.7977.64. Both decode, play and download; polling preserves playback, historical selection and return-to-current work. Legacy recordings remain referenced. The operator service is active after tests, still serving Reed copy29/copy100 at the stable private port 8765. No second-device or new live-GPU-overhead claim; D10's real experiment-spanning observation remains open. Visual owner acceptance and the broader D9 lifecycle frontier remain with their existing evidence/gaps.

Verification: pixi run python -m pytest cli/tests: 373 passed, 1 skipped, 395.85 s. pixi run test-engine: 2103 passed, 54 skipped, 307.43 s. Focused browser review/video suite: 40 passed, 1 skipped; final video suite including legacy-run.json preservation and decoded parity: 10 passed, 34.42 s. git diff --check passes. No full build because no engine binary, shell or payload changed. Early checks caught and fixed the circular module initialization, missed DOMContentLoaded, and metre-float rounding of displayed bounds. Probe failures were also recorded: a border reduced the first comparison canvas to 510 px, a DOM node predicate was false after CDP serialization, and Chromium suspended playback in a background tab. The final comparison fixes those harness conditions, including bringing the persistent page to front before playback, and passes. No red product tree remains. Hypergraph export/check are the closing gates; no state, charter, generated view or reconcile edit.

Dispatch closed: 1 unit — deliver and verify the shared reference viewport/video scene

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: b36fb9e2d1e011f301acb4af1a3c937752f7ca55

## State Impact

- target: fair-wolf-4645 — Shared reference renderer delivered with real Reed checkpoint/final videos, byte-identical viewport/capture PNGs, decoded-frame comparison, actual light-reference frame and close/wide/underside assessment; full CLI and engine suites pass. Owner visual acceptance remains explicit.
- target: deep-clover-6012 — Persistent port 8765 remains on Reed copy29/copy100 after the shared-scene update; final/checkpoint playback/download and polling/history checks pass. No new training experiment; experiment-spanning evidence remains open.
