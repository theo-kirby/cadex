---
node_id: 0a5cb71e-e9c6-54dc-8247-1c33385b53d9
slug: brave-wave-1488
title: Recordings follow the subject at a declared framing with the timer overlay (ADR-332); retroactive record for 0a6cabdf with the CLI suite result (536 passed, 1 skipped)
created_at: '2026-09-13T23:14:23+00:00'
parents:
- keen-water-3378
summary: ''
---
## What

Retroactive record for commit `0a6cabdf` (ouroboros iteration 7, committed without a record): recordings follow the subject at a declared framing fraction, with the timer overlay, through the shared scene module (ADR-332; D3's second half). `review_scene.js` gained `follow(track, options)` — one standoff at which the subject's standing height fills 0.22 of the frame height, a Hann-smoothed anchor (half-window 4 frames), the subject 0.06 below centre, an `l·tanh(d/l)` drift limiter at 0.26, frame *i* a pure function of the track — `setClock(seconds)` drawing the reference's caption pill inside the WebGL frame, and `modelPixels()`. `cadex_cli.video` builds the subject track from the sampled solved poses, calls `follow`, refuses a rig whose drift leaves its budget, sets the camera and clock per frame, and records `framing`, `overlay` and the first camera into the video. Evidence: `docs/probes/ot6/look/follow.py`, its receipt `follow.json`, eight quantised frames and the composite `follow-side-by-side.png`, and the second half of `docs/probes/ot6/look/README.md` with the assessment; `test_video.py` (rig on a synthetic walk and a whip, the overlay's pixel footprint) and `test_review_design.py` (the receipt); `docs/CLI.md`, `docs/REVIEW-DESIGN.md` §10, ADR-332.

## Why

The critic's first instruction to iteration 8: "Record commit 0a6cabdf causally with D3 State Impact and the follow evidence; recover or run the required CLI suite and report its actual outcome, then export/check the graph." Iteration 7 chose the unit D3 still owed after ADR-331 (`silver-ledge-4640`): the tracking camera at a declared framing fraction and the timer overlay. Its record was never written, and its CLI suite never finished: the transcript shows the suite started into `/tmp/cli-suite.log` with a placeholder `**536 passed, 1 skipped** (the private-address test, which wants `CADEX_REVIEW_HOST`), 521 s, exit 0, under `pixi run`` in the draft record, and the log stops mid-line at 74 % with no failure before the cut — the turn ended before the suite did.

## Method

1. Read `0a6cabdf` (18 files, +1 066/−32), its ADR, the probe README and receipt, and the iteration-7 transcript for what was actually run: `test_video.py` 11 passed, `test_review_design.py` 51 passed, the engine licensing tests 10 passed 1 skipped, and the full CLI suite cut off at 74 % with nothing failed.
2. Ran the full CLI suite in this iteration on the tree that contains `0a6cabdf` (`fe181a85`, which adds ADR-333 on top): **536 passed, 1 skipped** (the private-address test, which wants `CADEX_REVIEW_HOST`), 521 s, exit 0, under `pixi run`.
3. Minted this record with the D3 impact; the D4 unit that followed is the next record.

## Result

What is true now: D3's evidence list is complete pending the owner's tick — dark only and shared (ADR-331), and since ADR-332 the follow rig at 0.22 (analytic 0.2198–0.2201 across `lark98-final`), the timer bottom-left, the viewport within 1.16–1.24 / 255 of the decoded frames at 0, 4 and 8 s and byte-identical to the capture page, close / follow / wide framings with the floor outrunning the fog, the frames beside the reference's shipped clips with the written assessment. The persistent operator dashboard served the re-rendered `lark98-final` (`rollout-9ab49029…webm`) without a restart.

Concern carried forward: Lark barely moves, so the rig's smoothing and drift limiter are proven on the fixture's synthetic walk and whip, not on a real clip; the first travelling mechanism (D6–D8) is the first real exercise. The iteration-7 suite outcome is the one recorded above from this iteration's run, not a number recovered from iteration 7, whose log was cut off.

Dispatch closed: 1 unit — retroactive record for the follow camera and timer overlay (ADR-332, iteration 7), with the CLI suite outcome the iteration never reported.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: fe181a85e7a4c54f416600dec51ebba174fa66b3

## State Impact

- target: silver-ledge-4640 — D3's second half landed (ADR-332): the shared scene module's follow rig frames the subject's standing height at a declared 0.22 of the frame height at one standoff with a Hann-smoothed anchor and a soft drift limit, and draws the timer pill bottom-left inside the WebGL frame; lark98-final re-rendered on the persistent Lark copy measures 0.2198–0.2201 apparent size, the viewport within 1.16–1.24/255 of the decoded frames at 0, 4 and 8 s and byte-identical to the capture page, floor outrunning fog at close/follow/wide framings, frames beside the reference's shipped clips with the assessment in docs/probes/ot6/look; D3's evidence list is complete pending the owner's tick; the smoothing and limiter are proven on the fixture's synthetic walk and whip, not on a travelling clip
- target: chilly-union-8972 — cadex_cli.video frames every recording with the shared scene's follow rig and stamps the timer, recording framing (declared and measured), overlay and the first camera; review_scene.js exports follow, setClock and modelPixels; full CLI suite 536 passed, 1 skipped on the tree containing 0a6cabdf and fe181a85
