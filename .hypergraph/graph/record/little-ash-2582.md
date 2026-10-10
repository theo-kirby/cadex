---
node_id: 8e9520fd-c7f5-5d46-9b81-348953cdf1f5
slug: little-ash-2582
title: 'First breadth wave launched: eight machine briefs on Opus 5.5'
created_at: '2026-10-10T20:08:28+00:00'
parents:
- nimble-walrus-8367
- staid-harvest-9652
- true-basin-5562
summary: ''
---
## What

The first breadth wave from docs/MACHINES.md is launched. These are eight design-only Claude Code / Opus 5.5 sessions on today's main (886db504): wave1-printer, mower, tractor, cnc, loader, rover, jansen-walker (the Strandbeest) and liquid-handler, each in `~/cadex-projects/<name>` and the tmux window `cadex:<name>`.

## Why

The owner asked to test the system's breadth on unconventional machines once the panel rebuild (ADR-633..638), the machine breadth (ADR-640..647) and the guidance rewrite (ADR-650..655) landed.

## Method

Each project has:
- the same brief tail as the creature runs (design only, no policy training, owner watching the dashboard);
- a deny list covering its siblings, the cfix-* and castra-* projects, docs/probes, reference/, MACHINES.md and ARCHITECTURE-REVIEW.md;
- allow rules for mcp__cadex__*, the cadex CLI and its own tree;
- a stored engine budget of timeout_seconds=1200, because a panel probe build took 430 s;
- MCP_TOOL_TIMEOUT=1800000 at launch.

Each session waits at the folder-trust prompt for the owner to accept it.

## Result

Pending. To do: inspect the eight designs, then render and blind-rate them.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 886db5041d6fb6741ca99dc98275d6e3258170ac

## State Impact

- target: NEW machine-breadth-wave1 — open: eight design-only first-wave machine runs launched on 886db504; outcomes await inspection and blind rating
