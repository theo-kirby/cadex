---
node_id: 03e7860b-bc85-58da-bd08-493de20454fe
slug: shady-spring-8493
title: The 2D viewport shows each evaluation's film (ADR-541)
created_at: '2026-10-04T18:28:42+00:00'
parents:
- warm-shore-1092
summary: ''
---
## What

The dashboard's 2D viewport lists each evaluation's film (ADR-541, commit HEAD). Each filmed seed adds three sources: its rollout video, played in place, and its filmstrip and detail sheets as images. The project summary's `evaluations[].film` gains `sheets`.

## Why

During the quad-qdd run the owner asked whether any videos were viewable in the 2D viewport. None were: since ADR-533 the page listed no evaluations, although the server served their files.

## Method

- Edited `review_server.py` (the summary), `review.js` (sources and a `video` kind) and `review.css`.
- Added a Chromium test in `test_review_evaluation.py`.
- Restarted the live dashboard on :8766 and loaded quad-qdd's stand evaluation in headless Chromium.

## Result

- 198 dashboard tests passed, 1 skipped.
- Live: three sources for the stand evaluation, and the video decodes at 512×512 for 7.1 s.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: qdd-and-docs
- commit: 32fa5767ba6f58e848e02cf094bb789496092581

## State Impact

- target: candid-harvest-2614 — evaluation rollout videos and filmstrips are now listed and played in the dashboard's 2D viewport (ADR-541); before this, since ADR-533, they were reachable only by URL.
