---
node_id: 428b3875-b9f0-5c08-b84f-93ee53f35967
slug: late-walrus-6383
title: Preserve accepted meshes across in-place engine restore
created_at: '2026-09-12T23:44:04+00:00'
parents:
- mild-river-8224
summary: ''
artifacts:
- docs/probes/wren-fresh/restore-evidence.json
- docs/probes/wren-fresh/README.md
---
## What

Fix the D6 in-place restore tessellation loss at accepted-artifact publication (ADR-303). An identical revision/digest replay without a display request retains the existing accepted attempt if its result is present. Its saved meshes remain pinned against pruning. Changed identities, explicit display requests and missing retained results still publish a new attempt.

## Why

Follow mild-river-8224 and the critic's requested D6 fix before Wren training. A restore rebuilt valid ephemeral geometry but replaced the project's artifact locator with a display-less replay, leaving the persistent browser without meshes. This unit fixes preservation itself; it does not use a post-restore rebuild workaround. It advances clever-field-7845 and verifies deep-clover-6012. No scope deviation or training start.

## Method

Added a real-engine regression creating a disposable accepted solid with standard display and reopening its directory through two fresh engine processes. It asserts accepted revision/digest/attempt equality and every retained artifact byte, including the mesh and sidecar. Before the fix it failed specifically on accepted_attempt; afterward it passed. The existing CLI refusal test now asserts retained accepted_attempt plus a distinct latest_candidate replay, preserving its session/document checks. Five source unit cases cover unchanged replay, changed digest, changed revision, explicit display and absent retained result, including pruning with keep_recent=0. Acceptance keeps live execution, validation and publication; no protocol fields change.

Ran pixi run build-engine once and pixi run stage-engine. Ran the full engine suite and the staged-payload lifecycle gate with CADEX_ENGINE_ROOT pointing to build/engine/cadex-engine-0.0.0-linux-x64, as well as the full CLI suite. The staged payload is a local development stage, not a relocated distribution claim.

Ran the documented docs/probes/wren-fresh/restore.py against ot5-wren: two fresh in-place opens kept revision 5309bebc6597f7f792edea73265591480228f0ffb7e0b756b8fb755d9aa28f46, digest dbd02d7c12a0553b9ffadb3466e73da4055521264dd52e0bea40b2cc16588714, accepted contract/attempt, and all 28 retained files unchanged. The committed reusable probe was also run successfully after extracting it from the initial invocation. No rebuild command was used on Wren. Then docs/probes/wren-fresh/lifecycle.py loaded the unchanged private port 8765 in headless Chromium: eight solids, twelve parameter defaults, pointer orbit/zoom, polling and accepted identity passed. The page loaded in 1.19 seconds; inspected its saved screenshot. Full receipts/screenshots stay in Wren's evidence/restore48 and evidence/restore48-browser directories; the compact combined receipt is committed. This is a same-machine private-network check, not a second-device visit. Operator status is updated and the persistent service remains active on Wren with no runs. Charter-reload log records the owner revision adopted before iteration 38; this actor follows the supplied charter.

## Result

The demonstrated D6 mesh-preservation defect is fixed with failing-before/passing-after regression and real in-place Wren evidence. This does not complete Wren's second lifecycle: training, recordings, design revision and retraining remain. Existing missing or corrupt artifacts are not reconstructed by this retention rule; a missing retained result selects the fresh attempt. No new dependency, browser state authority, protocol change, Wren training or shell edit. The required CLI suite exercises its own bounded training fixtures. STATE.md and state nodes are untouched.

Validation: full engine suite 2110 passed, 53 skipped in 314.64 s; staged packaged lifecycle gate 16 passed in 18.41 s; final full CLI suite 395 passed, 1 skipped in 371.44 s. The first CLI run had 390 passed, 1 skipped and five failures in the refusal test because it explicitly expected accepted_attempt to be replaced on restore. Updated those assertions for preservation; focused rerun passed all five in 3.34 s before the green full rerun. The focused store suite passed 19 tests. Build, stage, persistent browser probe and git diff --check passed. Logs remain in /tmp/iteration48-{build,stage,engine,packaged,cli,cli-final,browser}.log on this machine.

Dispatch closed: 1 unit — preserve accepted tessellation across identical in-place restore and verify Wren on the persistent dashboard.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 4c0815882b1416e6eed3489dff9e4ad49beba52b

## State Impact

- target: clever-field-7845 — Fixed in-place restore tessellation loss: identical replay retains the accepted artifact attempt and pruning pin; failing-before regression, full engine and packaged gates, and real Wren retained-byte checks pass. Wren training lifecycle remains unfinished.
- target: deep-clover-6012 — Persistent Wren URL remains active with eight solids and twelve defaults after two in-place engine restores; browser orbit, zoom, polling and accepted identity pass, with compact evidence and operator status updated.
