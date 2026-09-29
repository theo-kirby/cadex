---
node_id: b08d0f3a-1fa1-54a8-9570-dd493a6b6afd
slug: calm-mesa-1063
title: 'ot10: W1 closed on ot10-quadruped-3 w2-1 — studio rollout video 72.8 s/300 s, ADR-432 fixes rollout-tessellation refusal and floating floor'
created_at: '2026-09-28T15:48:08+00:00'
parents:
- bold-reef-1724
summary: ''
---
## What
W1 is closed on an A5 design. `python -m cadex_cli.video` rendered the studio-style rollout video of W2 run `w2-1`'s installed policy on its own model: the W2 copy of `ot10-quadruped-3`, revision `f6d32a586ecc…`, policy `d8b87d2e1215…`. It is 45 frames and took **72.8 s** against the declared 300 s bound, headless on the CPU. The video is stored in the copy's `runs/w2-1/` (`rollout-bdd0da27ec4e….webm`, 153,574 bytes), not in git. The dashboard plays it.

Two real defects blocked this, and ADR-432 fixes both in `cli/cadex_cli/video.py`:
- The first attempt refused before drawing: `artifact size/type refused`. The rollout leg's solids are 2,528,456 triangles in 611 MB of ASCII STL, with `deck.stl` alone 172 MB, far past the scene style's 32 MB/500k caps. The studio style now streams them under its own input caps (256 MB a file, 4M triangles) and clusters them, like `render`'s snapshot, to at most 120,000 drawn triangles.
- The render summary names `c_floor` as environment and gives it no appearance, which also refused. Environment is now omitted from the drawing, and the studio floor is its top face. Before this, the floor sat at the lowest reach, −18.5 mm, because tipping solids pass through the floor (the rollout collides on proxies, ADR-281), so the robot floated about 18 mm above its shadow.

## Why
The critic's message asked me to close W1: render the studio video of w2-1's installed policy on the ot10-quadruped-3 copy within the 300 s bound, store it in the project, confirm the dashboard plays it, and pin its identity in a test. I did that. The existing studio identity test already pins revision, digest, policy, task, seed, trace and the name from the file digest. The two new tests pin what this project exposed: input bounds and the drawn budget, and the environment floor. The message's second item, pre-registering the warm-start `--init-from` run, is the next unit and was not started. I held to one unit.

## Method
- Ran `PYTHONPATH=cli pixi run python -m cadex_cli.video --project ~/cadex-projects/ot10-quadruped-3-w2 --run w2-1` under `/usr/bin/time -v`. Logs are in `~/cadex-projects/ot10-notes/w1/`, outside git.
- Refused on size; counted the facets per STL (deck 680,616; hood 253,440; caps 162,272 each …). A streaming parse of all 611 MB took about 4 s.
- Implemented `stl_stream`, `_clustered` and `studio_meshes`. The cell starts at extent/(4·512) and doubles until the budget fits. Every drawn corner is a source corner. The result is recorded as `geometry`.
- Second refusal (`c_floor` has no appearance): environment omitted, and the floor set to the top of the environment. `floor_z_mm`, `lowest_reach_z_mm` and `floor_source` are recorded.
- Rendered three times. The first successful render (floor at −18.5 mm) is kept in the project's video history and is the committed "before" strip; the final one is the "after". Strips are frames 0, 22 and 44, decoded from each webm with ffmpeg `tile=3x1`.
- Dashboard: `serve()` on the copy; `api/run/w2-1` lists the video first (style studio); `video/run/w2-1/0` serves `video/webm` whose sha256 equals the listed one. In headless Chromium I clicked the run; the `<video>` reached readyState ≥ 2 and played past `currentTime` 1.0 of a 4.5 s, 512×512 clip, with the revision prefix `f6d32a586ecc` and the policy prefix `d8b87d2e1215` in `#videos`.
- Tests: two new ones in `cli/tests/test_video.py`, each checked to fail on the ADR-431 source (`artifact size/type refused`; `render summary gives shin no valid appearance`). The materials test now expects `environment_omitted: []`.

## Result
- **What is true now.**
  - W1 has its A5 evidence: a studio rollout video of the accepted policy on the accepted model of `ot10-quadruped-3` (W2 copy, run w2-1). It took 72.8 s against 300 s, with 357 MB peak RSS, and drew 86,200 of 2,528,456 triangles at a 0.586 mm cell. Materials are declared from `review/render/<revision>/summary.json`, and `c_floor` is omitted as environment.
  - The video is identity-stamped (revision, model digest `7d7f0c2e…`, policy, task `b0913fa0…`, trace `2a779212…`), stored in the project and played by the dashboard. This also publishes W2's missing video.
  - Committed strips: `docs/probes/ot10/w1-quadruped-rollout-reach-floor.png` (284 KB, before) and `…-studio.png` (289 KB, after). Docs: ADR-432, REVIEW-DESIGN §15, and the ot10 README's W1 section. The README also corrects the W2 notes' "no further decimation" prediction.
  - Suites: `pixi run python -m pytest cli/tests` 1039 passed, 1 skipped; `pixi run test-engine` 2242 passed, 53 skipped. There was no engine, protocol or payload change, so no packaged gate was run.
- **Concerns.**
  - The rollout seed is `null` in both `run.json` and the trace, and the video records it as found. W2's pre-registration said seed 0 for training; the roll-out seed comes from the script. This is not a defect of this unit, but W2's publication should say it.
  - The tessellated solids reach 18.5 mm below the floor at the tip. That is proxy collision (ADR-281), not a render bug, and it is now a recorded number in every studio video.
  - The engine's rollout tessellation is about 30× finer than the render's. Reading it is 5 s of the 73 s; the engine was not changed.
  - No new dependency.
- **Next.** Pre-register W2 run 2: a warm start with `--init-from` from w2-1's policy on the unchanged task digest, with the same thresholds and `--stop-on-collapse`.

Dispatch closed: 1 unit — W1 closed on ot10-quadruped-3's w2-1 policy: studio rollout video in 72.8 s / 300 s, played by the dashboard, after ADR-432 fixed the rollout-tessellation refusal and the floating floor

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: d7e2d5389f5f5b917bbf21670dc8ad1ea8a107cc

## State Impact

- target: hollow-fern-8032 — W1 met on an A5 design: studio rollout video of w2-1's installed policy on ot10-quadruped-3 (W2 copy, revision f6d32a58, policy d8b87d2e), 45 frames in 72.8 s against the 300 s bound, CPU, headless; stored in the project (rollout-bdd0da27….webm), played by the dashboard (listed, served byte-identical as video/webm, played in headless Chromium); ADR-432 lets the studio style read the rollout's 2.5M-triangle tessellation under its own caps and draw 86,200 within a 120k budget, omits declared environment and puts the floor on its top face; tests pin both
- target: golden-garden-8501 — W2's W1 video is published for run w2-1 (walked=false stands); rollout seed is null in run.json and trace; next is the pre-registered warm-start --init-from run
