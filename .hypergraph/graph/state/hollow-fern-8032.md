---
node_id: e52bb297-10b8-5f92-b49f-ab30240f04fa
slug: hollow-fern-8032
title: W1. A walk can be watched
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot10: **W1. A walk can be watched.** The walk review includes a rollout video (or an animated image) of the accepted policy on the accepted model, in A2's style. It is rendered headless on this machine within a stated bound and committed to the project, never to git. The review dashboard plays it, and a test pins the artifact and its identity [rec: damp-dusk-8045].

**Met on an A5 design; the owner ticks it** [rec: calm-mesa-1063]. The studio-style video of W2 run `w2-1`'s installed policy on its own model (the W2 copy of `ot10-quadruped-3`, revision `f6d32a58…`, policy `d8b87d2e…`) rendered 45 frames in **72.8 s** against the 300 s bound, CPU and headless. It is stored in the project as `runs/w2-1/rollout-bdd0da27….webm`, not in git. The dashboard lists it, serves it byte-identical as `video/webm`, and plays it in headless Chromium [rec: calm-mesa-1063]. W2's walking run `w2-2` has its own W1 video, rendered in 153.9 s of 300 s [rec: kind-loom-7489].

- **ADR-432** made this possible [rec: calm-mesa-1063]. The studio style now reads the rollout's ~2.5M-triangle tessellation under its own caps and draws 86,200 triangles within a 120k budget. It omits declared environment geometry and puts the floor on its top face instead of leaving it floating. Tests pin both.
- The tool itself is ADR-431 [rec: golden-falcon-9792]. `python -m cadex_cli.video` renders `studio` by default (`--style studio|scene`). Each frame is `render.studio` in the hero view, with components moved rigidly per trace pose, in the design's materials, on a contact shadow at the rollout's floor. Identity checks cover revision, model digest, policy, task, seed and trace. Output is VP9 with decode verification, as `video.json` plus `rollout-<sha>.webm`. It lives in the command rather than in `cadex render`, because a video must not need an engine. Finch measured 117.5 s for 81 frames at 512 px; strips are in `docs/probes/ot10/w1-finch-rollout-{scene,studio}.png`. `cli/tests/test_video.py` pins identity, bound, materials, refusals and dashboard playback.
- Loose end: the rollout seed is `null` in `run.json` and in the trace. It is recorded as-is, not fixed [rec: calm-mesa-1063].

## Negative knowledge

- [scope: studio-style rollout video cost | confidence: medium | evidence: golden-falcon-9792] The studio style is pure-Python CPU work proportional to drawn triangles × frames. A ~590k-triangle hexapod on a 10 s rollout was estimated at ~6× Finch, over 300 s at 512 px. It refuses ("render exceeded 300 seconds") rather than running long. Measure before rendering a hexapod. ADR-432's 120k draw budget [rec: calm-mesa-1063] bounds the drawn count, but it has not been measured on a hexapod.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- golden-falcon-9792 — ADR-431 studio-style rollout video on the CPU, measured on Finch at 117.5 s against a 300 s bound
- bold-reef-1724 — quadruped-3's triangle count, measured for W1's bound
- calm-mesa-1063 — W1 met: w2-1's studio video on ot10-quadruped-3, 72.8 s/300 s, stored in the project and played by the dashboard; ADR-432 rollout-tessellation budget and floor fix
- kind-loom-7489 — w2-2's W1 video rendered in 153.9 s/300 s
