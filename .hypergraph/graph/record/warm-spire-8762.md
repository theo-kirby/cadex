---
node_id: 1eca9805-2e77-5ed5-8b72-91796d770837
slug: warm-spire-8762
title: 'Owner direction: bring the GUI app up to the CLI and the review dashboard'
created_at: '2026-09-29T10:04:59+00:00'
parents:
- light-hill-1224
summary: ''
---
## What

The owner set a new direction on 2026-09-29: bring the GUI app (the Blender shell) up to the headless CLI, and give it parity with the web review dashboard for watching long agent runs — renders, training curves, rollout videos, run history, agent session progress.

## Why

The runs ot5–ot10 (2026-09-12..29) were driven headless on a GPU server. In that window `shell/` changed in 0 files while `src/Mod/cadex` changed in 47 and `cli/` in 78. What the CLI gained — `look` (ADR-406), the design-language overlay (ADR-411, ADR-417), studio render and concept sheet (ADR-412, ADR-430), measured fit in every build reply (ADR-346, ADR-366), the review dashboard (ADR-286) — the app agent and app UI do not have. The owner now works at a Mac mini with a monitor, in the app.

## Method

Two survey agents mapped the CLI/dashboard surface and the shell surface (tools, overlay, panels, training UI, materials). The owner then chose between options, asked directly:

- Dashboard parity: **native Blender panels** reading the same on-disk files the dashboard reads (chosen over launching the web dashboard, and over both-staged).
- Agent parity: **move the shared code into the engine**, one implementation for both clients (chosen over a native Blender re-implementation, and over the shell shelling out to `./cadex`).
- Commits: one local commit per slice, stacked branches, no push until asked.

## Result

Eight slices, each its own PR: (1) studio renderer into the engine; (2) shared design/fit guidance text into the engine; (3) shell agent gets `look`, the guidance, and fit/inventory blocks in build replies (today only the CLI bridge adds them); (4) viewport materials by appearance role; (5) runs panel; (6) curves per run; (7) renders and videos in the app; (8) agent session monitor.

Constraints carried: the shell imports no cadex code (`docs/INTEGRATION.md`), `shell/` is GPL and `cli/` LGPL, every shell line stays under `mesh_agent/` or `shell/tests/python/`, and cadexd dispatches serially so nothing slow goes into an op.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: gui/studio-in-engine
- commit: 680a217c09255649f6642d2b02b9cdf212458c8b

## State Impact

- target: NEW gui-app-parity-with-cli-and-dashboard — open: the app agent lacks look, the design language and measured fit; the app UI lacks run history, per-run curves, renders and videos. Owner chose native panels over the same on-disk files, and engine-side shared code; 8 slices planned (studio renderer, guidance text, shell agent look+fit, role materials, runs, curves, renders+videos, session monitor).
