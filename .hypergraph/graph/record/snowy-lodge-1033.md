---
node_id: 127bc9e1-eb34-571f-9815-50b5498c7019
slug: snowy-lodge-1033
title: 'V1: the 3D viewport''s stage overlay (ADR-542)'
created_at: '2026-10-05T09:22:55+00:00'
parents:
- golden-snow-6627
summary: ''
---
## What

V1, the 3D viewport's training and stage overlay (ADR-542), as one unit: the read, the hooks, the data block, the page, the tests, the docs.

**Hooks and data sources, written down before the code (short rung 1).** I read `docs/DASHBOARD.md`, `review.js`, `layout.js`, `review_server.training_telemetry` / `default_run` / `ReviewProject.review`, `evaluate.run_evaluation` and the trainer's `progress.json` writer (`training/cadex_train.py` around line 2850). `loop.py`'s `supervise` is not needed until V2.
- Hooks, now in DASHBOARD.md §2 and pinned by a new `test_review_design.py` test that fails when a §2 id is missing from `index.html`: `#overlay[data-stage][data-collapsed]`, `#overlay-toggle`, `#overlay-stage`, `#overlay-line`, `#overlay-detail`, `#overlay-run`, `#overlay-stats`, `#overlay-reward-now`, `#overlay-best`, `#overlay-loss-now`, `#overlay-eta`, `#overlay-sparks`, `#overlay-reward`, `#overlay-loss`, `#overlay-warning`.
- Data. Everything is in `GET /api/project` `stage`, from `review_server.project_stage`:
  - the stage comes from the run record's `status` and `recorded_at`, the telemetry state (`starting`/`training`/`stale`/`failed`), `script_history/history.json`'s newest `saved_at` (designing within 600 s), and `evaluations/<name>/` with no `evaluation.json` written in the last 120 s (evaluating);
  - the numbers come from `progress.json`'s `iteration`, `total`, `eta_s`, `wall_time_s`, `reward_per_step`, `loss`, `best_iteration`, `best_reward_per_step` and `warning`;
  - the sparklines are `curve` and `loss_curve`, cut to at most 64 points each (`_spark`, last point kept).

**Files.**
- Code: `cli/cadex_cli/review_server.py`, the summary scalars plus `project_stage`; `review_static/index.html`, `review.css` and `review.js`, with `renderOverlay` and `setOverlayCollapsed` on the existing poll and `localStorage` `cadex.overlay`.
- Tests and fixture: the new `cli/tests/test_review_overlay.py` (8 tests), and `cli/tests/fixtures/biped-progress.json`, the real `ot5-biped` `probe3-final` curves (240 iterations) with checkpoints, digests and times dropped, 17 KB.
- Docs: `docs/DASHBOARD.md` §2 row, `docs/CLI.md` `stage` paragraph, `docs/DECISIONS.md` ADR-542.

## Why

The charter ranks V1 first, and the critic named it as this unit. I followed the critic's deliverables list: biped fixture, browser test rewriting `progress.json`, the 390 px measurement, the §2 rows pinned, ADR-542, and both suites with the GPU hidden.

**Deviation from the critic's brief: "reads only what /api/project already carries".** The run summary in `/api/project` carried no curves, best reward, ETA or warning (ADR-321 strips histories). The alternative was fetching `/api/run/<name>` on each poll, which sha256-hashes every retained checkpoint per call. I added one bounded `stage` block to `/api/project` instead. It is the same request on the same poll, and no new polling loop.

**The critic's plan fix.** The critic asked to replace the plan's orun2-era short horizon. A work iteration may not write view or state nodes, so I declared it as an impact on `plan/young-crane-9546` for the next reconcile to fold. I did not edit the plan.

## Method

- Stage rules, in order: evaluating > training (incl. stale) > failed (only if no revision accepted after the failed run) > designing > idle.
- The read run is the newest `running`/`pending` run whose telemetry is `starting`/`training`/`stale`, else `default_run` (unchanged). Without that, a stale trainer fell back to `default_run`, which ignores stale runs, and the test caught it.
- The page writes text and attributes only when they change, so an idle poll adds no nodes.
- Measured in headless Chromium at 390 × 844 with mobile and touch emulation, by `test_the_overlay_collapses_per_browser_and_covers_a_quarter_at_390px`. It prints the receipt.

## Result

**V1 is met on fixture evidence. The live half, the overlay updating during a real 5090 run, is W1's.**

- `stage` on `/api/project` and the overlay in the 3D viewport. Chromium checks that the line (`iteration 40 / 240` → `iteration 160 / 240`), the reward sparkline, the best reward, the ETA (`5 min`) and the collapse warning (computed colour equals `--warn`) all follow rewrites of `progress.json` on the page's own 2 s poll, with no reload. When the run finishes, the stage leaves `training` and the run line reads `· done`.
- **390 px measurement: expanded 280 × 171 px on a 390 × 724 viewport = 16.95% (bound 25%); collapsed 40 px tall.** Collapsed survives a reload (per browser).
- A project with no runs: `stage == {state: idle, reason: "", since: null, run: null, runs: 0, training: null}`, and the page shows one line, `nothing accepted yet` or `revision N accepted <ago>`.
- Suites, with the GPU hidden (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`): `pixi run test-engine` 2585 passed, 58 skipped; `pytest cli/tests` 1129 passed, 1 skipped (17 min). The overlay suite alone: 8 passed, both browser tests ran (Chromium present).
- Screenshots were checked by eye at 1400 × 900 and 390 × 844 (dark theme) and not committed. C1/W1 take the committed ones.

**Concerns for the next iteration.**
- At phone width, while no model is loaded, the overlay covers the right part of `#model-status`. This is cosmetic, and belongs to the long-term phone/light-theme rung.
- `docs/CLI.md` around line 1464 still describes the pre-ADR-533 telemetry panel ("the page fetches both on each poll …"). That is stale prose from ADR-533, outside this unit, and should go into a doc pass.
- `stage.training.state == stale` on a dead walk whose record stays `running` keeps the stage at `training`, with the warning showing "no telemetry update for over 30 s". That is what the files say, and it is not inferred further.
- The light theme was not measured for the overlay. It uses theme tokens only.

Next unit by the ladder: short rung 3, the V2 baseline. That is a `cadex walk` leg on `orun3-biped` with checkpoints on, measuring mean iteration wall time with no rollouts.

Dispatch closed: 1 unit — V1 stage overlay in the 3D viewport (ADR-542), browser-tested on the biped fixture, 16.95% of the viewport at 390 px.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: e3b1ffa4dd11b8b110a548a0511432127b26e192

## State Impact

- target: vast-ivy-6277 — met on fixture evidence: stage overlay in the 3D viewport (ADR-542, commit e3b1ffa4); /api/project stage block; browser test follows progress.json rewrites on the existing poll; 16.95% of the viewport at 390 px; §2 hooks pinned; live 5090 demonstration left to W1
- target: plan/young-crane-9546 — replace the orun2-era short horizon (swept clearance, section planes) with the orun3 ladder: V2 baseline iteration wall time on orun3-biped, then P1 relative URLs, then V2 checkpoint rollouts; V1 has landed
