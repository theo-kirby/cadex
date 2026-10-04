---
node_id: 314baeed-5890-5875-b364-9874f3281ac2
slug: careful-glacier-8772
title: 'App speed: cached, ETagged, gzipped model delivery; resilient loads; crisp hairlines (ADR-535)'
created_at: '2026-10-04T13:10:28+00:00'
parents:
- cool-road-8381
summary: ''
---
## What
Fixed two problems the owner reported in the app draft: it was "suuuuper slow" to load, switch and rebuild, and "a lot of times the model fails to load". Also made the hairline render crisp, after the owner found its lines blurry.

## Why
On the owner's report, a 45-part accepted model was 28 MB of uncompressed STL, served `no-store`. Every mesh request re-derived the whole model manifest, hashing every BREP, which cost about 2 s of server CPU per load. The page's poll waited on the download, and nothing retried or aborted a load. The hairline pass thresholded softly at 1× resolution, which gave grey halos and jaggies.

## Method
- `review_server.py`:
  - memoizes `accepted_model`, keyed by the content of script.json and result.json plus the stat of the display directory and the trace;
  - keeps converted STL by the tessellation's sha256, which is also its ETag (`no-cache`, 304 on a match);
  - gzips JSON, text and STL of 1 KB or more when the client accepts it.
- `review.js`:
  - aborts a superseded load (AbortController);
  - retries a failed request twice, and a failed load with backoff;
  - keeps the last model drawn;
  - stops the poll waiting on the model.
- `review_scene.js` hairline: normals and depth go to an offscreen target at 2× resolution (capped at 16 Mpx). A hard edge pass inks the nearer side only, and a linear-filtered 2×2 resolve smooths the steps.
- The operator proxy (`~/cadex-dash/proxy.py`, not in the repo) now forwards Accept-Encoding and passes gzip through, recompressing text it rewrites.
- New test: `test_review_server.py::test_an_accepted_mesh_is_tagged_by_content_compressed_and_revalidated`.
- Measured with Chromium Network.emulateNetworkConditions (30 Mbit/s, 40 ms) through the public tailscale URL.

## Result
- First load 9.1 s → 3.9 s; reopening the same model 8.2 s → 0.8 s.
- On the wire: 28 MB → 9.3 MB; `/api/projects` 1.1 MB → 100 KB.
- Server time for the 45 meshes (loopback, warm): 2.1 s → 0.13 s.
- 23 of 246 projects have no model to show: 20 retained no tessellation, 2 name no attempt, 1 has its staging deleted. That is data, not the page.
- Not fixed: a slider rebuild is 80–150 s of `cadex params`. The build is about 10 s, then about 60 s of post-build work (the fit checks of ADR-346 and the assembly pass) and about 4 s of tessellation. Left to the owner (ADR-535).
- `cli/tests`: the full suite is green (recorded in the merge commit).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: app-shell
- commit: ff15e6112400438d9a4c0fefc5ff0e426ac2b4f1

## State Impact

- target: twilight-aspen-1541 — remote use is practical: the model loads in ~4 s and reopens in under 1 s over a 30 Mbit link (was ~9 s each), loads retry and never freeze the page (ADR-535); open: a parameter rebuild still takes 80-150 s in the engine's post-build fit checks
