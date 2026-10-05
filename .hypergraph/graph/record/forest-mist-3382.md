---
node_id: 62572e14-8af4-5c23-8c6d-44cea04a9398
slug: forest-mist-3382
title: 'V2 page half: checkpoint rollouts loop in the 3D viewport with a follow/pin scrubber (ADR-545)'
created_at: '2026-10-05T11:57:19+00:00'
parents:
- snowy-water-3502
summary: ''
---
## What

The page half of V2 (ADR-545). The 3D viewport now loops each checkpoint's engine rollout as it lands, with a scrubber.
- **Server.** `GET /api/project`'s `stage` gains `checkpoints` (`checkpoint_rollouts` in `review_server.py`). It lists the read run's rolled-out numbered checkpoints, oldest first, at most 64. Each is `ready` or `failed` with its iteration, reward, sha256 and reason, and `pending` counts the rest. Each trace is parsed once per file identity.
- **Route.** One new read route, `GET /api/playback/checkpoint/<run>/<stem>`, which goes through the existing `trace_playback`. A failed checkpoint answers `available: false` with its reason, and any other name answers 404.
- **Page.** `#checkpoints` holds the scrubber (`#checkpoint-pick`, `#checkpoint-label`, `#checkpoint-status`). It sits above the playback timeline, and both are now inside a `.timelines` stack.
  - The newest checkpoint loops, labelled "iteration N · reward R · i/n · newest".
  - A picked stop is kept while newer ones land. Back at the newest end, the page follows again.
  - A failed stop shows `rollout failed: <reason> — <error>` in `--bad`, with the model at rest.
  - While the read run is training, the viewport turns to it on its own unless a source was picked by hand.
  - The run's own rollout is the last stop once it exists.
- **Docs.** DASHBOARD.md §2's 3D viewport row has the new hooks and behaviour (pinned by `test_review_design.py`). CLI.md documents `stage.checkpoints` and the route. ADR-545 is added.

## Why

The critic named this unit: serve each checkpoint's trace through the existing `trace_playback`, loop the newest labelled with its iteration and reward, add a scrubber that follows newer checkpoints unless one was picked, show a failed rollout with its reason, add the DASHBOARD.md rows and hooks, write a browser test against a real engine with a fake trainer still running, and write an ADR and a record. All of it was done as asked.

One choice was mine and is not in the brief. While the run is training, the viewport turns to it on its own. Otherwise, a dashboard left on the accepted model (the default) would never show the checkpoints. That is the charter's one-thing goal and W1's "never reloaded".

## Method

- I read the playback, stage and run-model paths. During training, a walk's run model is its frozen `training-view.json`, and its components carry the `*_link` names the checkpoint traces use (checked on `orun3-biped/runs/probe3`). So the poses go onto the run's own model, not the accepted one.
- Tests: `cli/tests/test_review_checkpoints.py`, 5 tests.
  - 3 server tests with no engine: order, failure, pending, route refusals, the 64-item bound, no reparse on an unchanged poll, and absence.
  - 2 Chromium tests. The main one runs against the real engine with a stepped fake trainer driven by `run_trainer` and the ADR-544 watcher, which holds after each checkpoint.
    1. While the trainer thread is alive, the page turns to the run and loops `walk.000020`, then `walk.000040` replaces it.
    2. A hand-picked `walk.000020` stays while a third lands.
    3. That third checkpoint's real engine failure is shown: `policy_not_a_container — the checkpoint does not begin with the cadex-policy-v1 magic line.`
    4. Then the page follows to `walk.000080`.
  - The second test checks that a hand-picked source is not taken over.
  - Result: 5 passed, 0 skipped.
- Measurement on the 11 real biped checkpoint traces from ADR-544's run (copied to /tmp, never committed): the block is 3,357 bytes; listing takes 10.2 ms the first time and 0.17 ms cached; the newest playback is 22,107 bytes.
- Full suites: see Result. Commit `802b265e`.

## Result

What is true now: V2's whole page half has landed with a real-engine browser test. With this, V2's bullets each have evidence:
- rollout during training (ADR-544);
- cost under 5 % (ADR-544);
- served through `trace_playback`, with the newest looping, labelled, and a scrubber with follow and pin (ADR-545);
- a real-engine browser test where a second checkpoint replaces the first while training runs (ADR-545);
- a failed rollout shown with its reason, without stopping training (ADR-544, ADR-545);
- traces never committed, with disk measured (ADR-544).

The critic decides whether V2 is closed. It has not been shown on a real 5090 `cadex walk` in a live browser; that is W1's job.

Suites, at commit `802b265e`:
- `pixi run python -m pytest cli/tests` with the GPU hidden: 1143 passed, 1 skipped. The first run stopped on one failure my own change caused: `test_review_overlay.py::test_a_project_with_no_runs_has_a_stage_and_no_training` asserted the whole `stage` dict, which now has a `checkpoints: None` key. I updated the assertion to the new shape and reran the whole suite.
- `pixi run test-engine`: 2585 passed, 58 skipped.
- The protocol and payload are untouched, so the packaged gate was not needed.

Concerns for the next iteration:
- The automatic turn to the training run is one-way. When training ends, the page stays on the run until the owner picks another source (ADR-545 states the assumption).
- The new route enters P1's API contract when that contract exists. The page still uses the root-absolute `BASE + '/api/…'` pattern, like every other fetch; that is P1's to change.
- The scrubber appears only when the shown run is the one the stage reads. An older finished run picked by hand plays its own rollout without checkpoint stops.
- No new dependency. The tail now has two unreconciled records.

Dispatch closed: 1 unit — V2 page half: checkpoint rollouts loop in the 3D viewport with a follow/pin scrubber and failure reasons (ADR-545), real-engine browser test

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 802b265ecee768e0bfc23cf565b01f346e60642b

## State Impact

- target: dry-rain-5997 — Page half landed (ADR-545, commit 802b265e): stage.checkpoints + /api/playback/checkpoint/<run>/<stem> through trace_playback; the 3D viewport loops the newest checkpoint on the run's frozen model labelled iteration and reward, a scrubber pins an older one and follows at the newest end, a failed rollout shows its reason; Chromium test against the real engine shows walk.000040 replacing walk.000020 while a stepped trainer runs. Every V2 bullet now has evidence; a live 5090 walk in a browser is W1's.
