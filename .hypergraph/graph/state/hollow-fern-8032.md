---
node_id: e52bb297-10b8-5f92-b49f-ab30240f04fa
slug: hollow-fern-8032
title: W1. A walk can be watched
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot10: **W1. A walk can be watched.** The walk review includes a rollout video (or an animated image) of the accepted policy on the accepted model, in A2's style. It is rendered headless on this machine within a stated bound and committed to the project, never to git. The review dashboard plays it, and a test pins the artifact and its identity [rec: damp-dusk-8045].

**First half has evidence** [rec: golden-falcon-9792] (ADR-431, commit `1230f8cf`):

- `python -m cadex_cli.video` renders in a `studio` style by default (`--style studio|scene`). Each frame is `render.studio` in the hero view, with components moved rigidly per trace pose, in the design's materials, on a contact shadow at the rollout's floor. It shares the identity checks (revision, model digest, policy, task, seed, trace), VP9 encoding with decode-verification, and `video.json`/`rollout-<sha>.webm` with the scene style. The dashboard's Videos tab plays it unchanged. The video lives in the command rather than in `cadex render`, because a video must not need an engine. [rec: golden-falcon-9792]
- Declared bound: 300 s for the whole render. On a /tmp copy of ot6 Finch `finch1-final` it took 117.5 s for 81 frames at 512 px (385 MB RSS), stored in the project's run directory and not in git. Before/after strips are committed as `docs/probes/ot10/w1-finch-rollout-{scene,studio}.png` (259 KB, 219 KB). [rec: golden-falcon-9792]
- `cli/tests/test_video.py` pins identity and bound, declared materials reaching decoded pixels, refusals, and dashboard playback. [rec: golden-falcon-9792]

**Remaining:** a video of an A5 design's own accepted policy. W2 run `w2-1` now provides one on ot10-quadruped-3, and it has not been rendered yet. The quadruped draws 78,419 triangles, below Finch's 95,212, so the 512 px, 300 s bound applies with no extra decimation [rec: bold-reef-1724].

## Negative knowledge

- [scope: studio-style rollout video cost | confidence: medium | evidence: golden-falcon-9792] The studio style is pure-Python CPU work proportional to triangles × frames. A ~590k-triangle hexapod on a 10 s rollout is estimated at ~6× Finch, which would exceed 300 s at 512 px. It refuses ("render exceeded 300 seconds") rather than running long. Measure before rendering a hexapod.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- golden-falcon-9792 — ADR-431 studio-style rollout video on the CPU, measured on Finch at 117.5 s against a 300 s bound
- bold-reef-1724 — quadruped-3's triangle count, measured for W1's bound
