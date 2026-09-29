---
node_id: bfbfe3b2-29bc-51b5-836c-1f5b26d3fcbe
slug: restless-fjord-9059
title: The app's Training editor lists the project's runs (ADR-450)
created_at: '2026-09-29T12:17:21+00:00'
parents:
- rough-water-0848
summary: ''
---
## What
GUI-parity slice 5 (ADR-450): a Runs panel in the app's Training editor lists every `cadex walk` run under `<project>/runs/` with status, design relation, live progress, video state, and on click identity, error, policy, reward and parameters.

## Why
The owner asked for dashboard parity for monitoring long agent runs (warm-spire-8762), via native panels that read the same on-disk files.

## Method
- New `mesh_agent/cadex_runs.py`: a second, smaller reader of `run.json` / legacy `review.json`, `train/progress.json`, `video.json` and `script.json`, written against docs/CLI.md; stat-keyed cache; symlinked run dirs outside `runs/` listed, never opened; 2 s timer redraws the editor.
- Considered and rejected: moving `cli/cadex_cli/review_record.py` into the engine and running it per poll as a child process. Its video/snapshot digest cache is process-local, so each poll would re-hash every video; CLI tests also monkeypatch its internals. Digest checks and `problems` stay the dashboard's.
- Also fixed slice 4's registry test in the no-engine suite (amended into the slice 4 commit): the view list now starts with `roles`.

## Result
- No-engine suite (`build_app.sh gate tests/python/bl_mesh_agent.py`): exit 0, 1245 ok, incl. 14 new checks.
- `pixi run gate`: only the 8 pre-existing restore-lockout failures.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: gui/runs-panel
- commit: ba56bf0ba33803665c23a55ac2dfe37df8cdb17b

## State Impact

- target: shy-crane-2573 — the app's Training editor has a Runs panel reading runs/*/run.json (or legacy review.json), train/progress.json and video.json, as the review dashboard does, without digest checks (ADR-450)
