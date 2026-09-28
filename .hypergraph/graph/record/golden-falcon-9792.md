---
node_id: 7d3b3922-fbfa-53db-8219-caf7774e43d7
slug: golden-falcon-9792
title: 'ot10: ADR-431 studio-style rollout video on the CPU; Finch measured at 117.5 s against a 300 s bound'
created_at: '2026-09-28T14:21:39+00:00'
parents:
- hidden-tooth-3627
summary: ''
---
## What

ot10 W1, first half: a policy rollout video in A2's studio look, rendered headless on the CPU. ADR-431 adds a `studio` style to `cadex_cli.video.render(project, run, style)`, and `python -m cadex_cli.video` now defaults to it (`--style studio|scene`). Each frame is `render.studio` in the hero view. Each component is prepared once and moved rigidly per trace pose, in the design's materials (from the render summary at the run's own revision), with a contact shadow on the rollout's lowest floor, a follow window and a timer. Identity checks, 10 fps sampling, FFmpeg VP9 encoding with decode-verification, `video.json` and `rollout-<sha>.webm` are shared with the existing scene style, so the dashboard's Videos tab plays it unchanged. `render._contact_shadow` takes an optional floor (default behaviour unchanged).

## Why

The critic named W1 as the next unit, with A6 accepted. None of the ot10 projects has a trained policy yet (`ot10-hexapod-10` has no `runs/`), and `hex3/runs/walk1` stopped after its design leg. ot7–ot9 walks use a run layout the video reader does not read (no `run.json`). So, within the critic's allowance for an existing walk from a /tmp copy, I measured on a /tmp copy of ot6 Finch's `finch1-final`, which does have an accepted policy and a verified rollout. The critic's wording was "`cadex render` should render a rollout video". I put it in the existing video command instead. That command already holds the policy/trace identity checks and the dashboard contract, and `cadex render` needs an engine while a video must not. ADR-431 records this.

## Method

- Stated the bound before rendering: `RENDER_SECONDS = 300` for the whole render. A prototype measured ~1.8 s per 512 px frame on 95k triangles.
- Copied `~/cadex-projects/ot6-finch` to `/tmp/w1-finch`. Ran `./cadex render --project /tmp/w1-finch`, which rebuilt revision `b6862234…` with digest `232c4cd1…` (the same as the run) and wrote supplier-derived appearance (2 materials).
- Then ran `PYTHONPATH=cli pixi run python -m cadex_cli.video --project /tmp/w1-finch --run finch1-final`.
- Checked the new frames against the old scene-style video of the same trace: re-drawing the 8 s pose from the scene camera's yaw/pitch reproduces the scene's pose. The views differ by ~100° of azimuth; the geometry agrees.
- Added four tests in `cli/tests/test_video.py`:
  - identity and bound, with no browser looked up;
  - declared materials reaching decoded pixels, and undeclared ones recorded as such;
  - refusal of an unknown style and an invalid declared role;
  - the dashboard lists the video and serves its exact bytes as video/webm.
- Parametrised the five-fault refusal test over both styles.

## Result

- The Finch studio video took 117.5 s for 81 frames at 512 px (bound 300 s; process wall 117.7 s, 385 MB RSS). It records:
  - `rollout-3d042632….webm` in `/tmp/w1-finch/runs/finch1-final/`, not in git;
  - accepted_revision `b6862234…`, policy `0f0997e1…`, seed 0;
  - `materials.declared = true` from `review/render/summary.json`.
- The before/after strips are committed as `docs/probes/ot10/w1-finch-rollout-{scene,studio}.png` (259 KB and 219 KB).
- Docs changed: ADR-431, REVIEW-DESIGN §15, the ot10 README's W1 section, and HEADLESS-BIPED-REVIEW, whose historical commands are now pinned to `--style scene`.
- `cli/tests/test_video.py`: 23 passed (browser tests included). Full-suite results: `pixi run python -m pytest cli/tests` 1037 passed, 1 skipped (started before the doc-only edits); `pixi run test-engine` 2242 passed, 53 skipped (after them). No engine, protocol or payload change, so no packaged gate.

Concerns for the next iteration:
- W1 is not complete. Its "accepted policy on the accepted model" should be an A5 design's own policy, which needs W2's training run. Before any GPU run, W2 must record its settings and stop rule.
- The studio style is pure-Python CPU work proportional to triangles × frames. A hexapod with ~590k triangles and a 10 s rollout would run ~6× Finch and exceed 300 s at 512 px. It then refuses with "render exceeded 300 seconds" rather than running long. Measure the A5 hexapod before W2's video, and decide the size or decimation there.
- No new dependency.
- The unreconciled tail is now two nodes (hidden-tooth-3627 and this one). The critic asked for a fold into spring-glade-6801 when the cadence comes due, and that is a reconcile pass, not this work iteration.

Dispatch closed: 1 unit — W1 studio-style rollout video (ADR-431), measured on a /tmp Finch copy at 117.5 s against a 300 s bound, with tests pinning identity, materials, refusals and dashboard playback.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 1230f8cfddd7eb7fbb4741ece27a5743b3e3cfad

## State Impact

- target: hollow-fern-8032 — W1's first half has evidence: python -m cadex_cli.video renders an accepted policy's rollout in the studio look on the CPU (ADR-431, style studio by default), identity-pinned (revision, model digest, policy, task, seed, trace), within a declared 300 s bound (ot6 Finch finch1-final, 81 frames, 117.5 s), stored in the project and played by the dashboard's Videos tab; tests pin identity, materials, refusals and playback. Remaining: a video of an A5 design's own policy, which needs W2's training run; hexapod-scale triangle counts may exceed the bound at 512 px.
