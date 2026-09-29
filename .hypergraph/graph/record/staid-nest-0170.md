---
node_id: 8b71f327-a056-5804-9dc4-4b64f6198fef
slug: staid-nest-0170
title: A selected run's curve is drawn in the Training editor (ADR-451)
created_at: '2026-09-29T12:20:48+00:00'
parents:
- restless-fjord-9059
summary: ''
---
## What
GUI-parity slice 6 (ADR-451): selecting a run in the Runs panel points the Training panel's numbers and the reward-curve plot at that run's own `runs/<name>/train/progress.json`; deselecting returns to the live mirror.

## Why
Per-run curves in the app, as the review dashboard draws them (warm-spire-8762).

## Method
`cadex_training.progress_path` reads the selection (`cadex_run_selected`) off the WindowManager by name; import closure stays `{json, os, bpy}`. Names that are not one path component are ignored; a run without a report keeps the live mirror. The Training panel names its source (`live` / `run <name>`).

## Result
- No-engine suite: exit 0, 5 new checks (mirror kept, selection followed, numbers and curve are the run's, bad name ignored).
- `pixi run gate`: only the 8 pre-existing restore-lockout failures; the training panel and plot checks pass.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: gui/run-curves
- commit: 2eae4908e4aafd7445e5775b68d9005355804198

## State Impact

- target: shy-crane-2573 — the Training editor's numbers and reward curve follow the run selected in the Runs panel (runs/<name>/train/progress.json), else the live mirror (ADR-451)
