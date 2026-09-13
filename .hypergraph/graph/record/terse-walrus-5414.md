---
node_id: e04ab009-d434-5c49-94af-cd30cb635401
slug: terse-walrus-5414
title: Verify current 90 mm Wren viewport and video against the visual reference
created_at: '2026-09-13T04:49:57+00:00'
parents:
- crisp-stream-4743
summary: ''
artifacts:
- docs/probes/review-style/README.md
- docs/probes/review-style/wren90.json
---
## What

Closed the current 90 mm Wren D11 comparison evidence gap using existing wren71-final policy/video on the persistent private-network dashboard. Added docs/probes/review-style/wren90.json and a user-facing visual assessment; updated the lifecycle D11 index and operator status. No product renderer, accepted project, historical recording, dependency or training changed.

## Why

The critic requested a matched pose/camera comparison of the current viewport and decoded video with identified neural-whoop references, including close/wide framing and orbit. This follows crisp-stream-4743's explicit current-design evidence limit. I performed that comparison and found no mismatch requiring a renderer fix. The critic also requested reconciliation afterward; I did not reconcile because this dispatch explicitly forbids reconciliation or state edits and permits exactly one work unit. Two unreconciled records on arrival become three after this record; the separate reconcile pass can fold them.

## Method

Read the actor skill, repo/loop/hypergraph contracts, STATE.md, VISION.md, previous record, reference environment.js/scene.js/geometry.js, capture source and render-examples README. Inspected actual rendered images, not an inferred visual match. The sibling reference stayed read-only and the existing operator server was never stopped.

```bash
PYTHONPATH=cli pixi run python docs/probes/review-style/compare.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" \
  "$HOME/neural-whoop" wren71-final wren57-retry style73
PYTHONPATH=cli pixi run python \
  "$HOME/cadex-projects/ot5-wren-copy54/evidence/style73/check_current.py" \
  "http://$(tailscale ip -4):8765/"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest \
  cli/tests/test_wren_lifecycle_report.py -q
```

The first command verifies persistent project/default/revision identity, captures matched viewport/capture PNGs and decoded video frame zero, restages the actual reference modules with the same geometry at fit/0.7x close/3x wide cameras, decodes the shipped orbit-policy reference at 4 s, exercises real pointer orbit/zoom and underside, and plays/downloads/polls historical wren57-retry before returning to current. The supplemental project-local script fully decodes current video, extracts frames 40/80, checks displayed 90 mm parameter/revision and current playback/download through three polls. Its source remains beside comparison.json and the images under project evidence/style73; the final portable receipt is committed as wren90.json. All committed image/video hashes were checked against their retained files.

Viewed side-by-side.png and full-size close, reference-close, pointer-near and underside captures, plus decoded current frames 40 and 80. Reference commit is 31caeb28abb3bdab8d9030bfc91f0c3f48ffa63a, shipped orbit_maneuver_policy.mp4 SHA-256 cbb4a98684bcc96ac9a85d4fa53e74522ac66684c94c62e401ef04a3b1bae26f. This shipped clip is dark-themed; the light reference uses its unmodified scene/environment modules with Wren geometry. Probe filenames reference-light-reed are historical generic names, not evidence of a Reed subject.

## Result

D11 now has a current 90 mm comparison. Persistent ot5-wren-copy54 remains on wren71-final at e9dee22bc90c428942562eeadf150ef4bcd4ab03d8e9ed96e0f959272cfa22bb with 18 runs. Server PID 3308131 remains active on private port 8765. Viewport and capture 512-square PNGs are byte-identical at the video pose/camera; decoded frame-zero mean absolute RGB error is 1.500579833984375/255, below the 3/255 tolerance. Video a2fde70a223941d18096dc08d3559ab2cae8e0b834ad3b2cc6920487074bdcc5 identifies policy fa7b28b8732a6a5d7b86f3157ecfa81ab531d374c5c53a38415edde0da71b343, seed 0, 8 s simulation, 81 frames/10 fps and 8.1 s encoded. Current and historical downloads match the records; playback survives polling and historical browsing returns to current.

Visual assessment: matching grey prototype-grid floor, honest metre labels/subdivisions, seamless fog/sky, rough component palette, steep key and grounded shadows at equivalent occupancy. Cadex's close shadow edge is slightly crisper than the reference, consistent with ADR-301's fitted frustum/bias; no correction is justified. Close and wide framing show no stage edge or wall/ceiling seam. The visible finite blue plate is model geometry. Real pointer drag changes yaw 0.8 to 2.6 and pitch 0.5 to 0.8; zoom spans 647.46 to 3916.90 mm. The stage expands 62.22 to 219.35 m and fog far 15.55 to 54.84 m; model coverage remains 50,553/130,069/4,138 pixels for drag/near/far. The underside view exposes the real plate without a presentation-floor obstruction. Later decoded frames hold a bent standing pose; no walking claim.

Verification: browser comparison and supplemental playback/decode probe exit 0; receipt hashes match; report guard 3 passed; git diff --check passes. No product code/test change, build, engine suite or full CLI suite was needed for this documentation/evidence-only unit. A diagnostic attempted bare python, which is unavailable; rerunning via pixi succeeded and no verification relied on that failed invocation. All evidence is same-machine via the private address, no second-device or fresh training claim. No new dependency, renderer change, charter/state/plan edit or experiment was introduced. The Wren-specific missing/partial-video fault repeat remains an explicitly separate acceptance limit. Hypergraph export/check follows minting.

Dispatch closed: 1 unit — current 90 mm Wren visual comparison and persistent playback evidence retained

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: ed3ddeca6e09303731ff7033cd7a6ea6e73a0e45

## State Impact

- target: fair-wolf-4645 — Current 90 mm wren71-final now has identified reference fit/close/wide comparison, same-pose/camera lossless parity, decoded-video RGB error 1.50058/255, real orbit/zoom and retained visual assessment; no renderer mismatch demonstrated
- target: deep-clover-6012 — Persistent ot5-wren-copy54 remains on wren71-final with 18 runs; current and historical playback/download/polling pass and server stays active without restart or new training
