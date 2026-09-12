---
node_id: a98e106a-de6d-51ef-b0ff-a4fa9bffcba3
slug: modest-journey-2059
title: Measure the reference environment against the live Reed review
created_at: '2026-09-12T21:24:53+00:00'
parents:
- modest-dawn-3706
summary: ''
artifacts:
- docs/probes/review-style/evidence.json
- docs/probes/review-style/operator.json
---
## What

Completed a D11 reference/baseline experiment and user-facing shared-scene contract (ADR-300). Added a reproducible read-only browser/frame probe and compact hashed evidence. Kept persistent port 8765 serving Reed copy29/copy100; verified real playback/download, poll preservation, historical selection and return to current.

## Why

Advances fair-wolf-4645 under the current owner charter. Adoption is confirmed by the runner log: charter reloaded before iteration 38, ce445e64a458. The critic requested a complete shared environment implementation and real-biped visual comparison. This unit deliberately narrows that request to a completed baseline experiment and architectural decision: source inspection revealed independent perspective-WebGL and orthographic-CPU renderers, neither with floor/fog/shadows. Replacing both and proving the complete visual/lifecycle surface is larger than this bounded unit. No partial renderer or cosmetic approximation was landed. The measurements also expose two implementation-critical distinctions: shipped reference clips use dark theme despite the owner's light request, and Reed's apparent stage is authoritative ground-slab geometry.

## Method

Read the specified neural-whoop studio environment/scene/geometry sources, capture implementation/options and README. Identified reference commit 31caeb28abb3bdab8d9030bfc91f0c3f48ffa63a and hashed source files and licence. Decoded actual frame zero of flip/swing/orbit policy examples with FFmpeg; visually inspected them and real Reed viewport fit/close-orbit/wide-orbit screenshots and saved video frame zero. The reference was read-only; no implementation or dependency imported.

Ran PYTHONPATH=cli:cli/tests pixi run python docs/probes/review-style/baseline.py with the persistent private URL, operator-projects/ot5-biped-copy29 and the sibling reference checkout. Browser checks compare project/run/revision against retained records and exercise mouse zoom/orbit. Bulk screenshots and receipt are project-local evidence/style39; compact identities are docs/probes/review-style/evidence.json. Ran docs/probes/operator-review/verify.py against the same URL/project and copy100; results are operator.json beside the baseline. No temporary server, training, engine restore or run-file mutation. Updated published operator status.

## Result

Baseline probe and persistent browser checks pass. Current accepted revision is 25d9b6ab7472b968a3a72691ca44113ea86beda85802af3e22d9270952cb71fc; downloaded video SHA-256 is 2308fe3baa4d0a5a2256a37deadfa798256ab6cca978ff8daeacc56c76a2ab24. The dashboard service remains active. Docs explicitly assess floor/grid, fog/horizon, palette, material/lighting/shadow and framing gaps. Close orbit clips the torso; wide orbit leaves the model slab floating in empty background. Equivalent framing, same-pose/camera parity and the light reference remain unproven. D11 is open; this does not tick it. D10 real-experiment spanning evidence also remains open.

ADR-300 chooses one browser scene for viewport and explicit video frames, retaining Python validation/locking/sampling/encoding and a fixed trajectory camera. It calls out the current video publication replacing metadata references, which must be addressed when new styled videos are published; no old recordings were changed. Ground slab dimensions remain truthful. Assumption: the owner's explicit light palette wins over dark shipped examples. No new dependency, product code, engine/protocol/payload/shell change, build, generated-view edit or state edit. Consequently no full CLI/engine suite rerun. The initial bare python compilation command failed because that executable is absent; rerunning through pixi succeeds. git diff --check passes. Hypergraph export/check are the closing gates.

Dispatch closed: 1 unit — measure the D11 reference gap and specify the shared review scene

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: f82d34326f4c0a2e4b0e6fca9ff1135ab9b81045

## State Impact

- target: fair-wolf-4645 — D11 baseline and shared-scene decision recorded; actual dark reference frames and live Reed screenshots expose projection, environment, shadow and colour mismatches. Light-reference capture and shared implementation remain open; no D11 acceptance claim.
