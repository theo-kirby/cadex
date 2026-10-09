---
node_id: 469a31d8-a40f-5616-aa4e-a10e919b1258
slug: small-brook-2395
title: Creature re-runs measured; owner chooses Claude Code / Opus 5.5 over Codex / GPT-6-Astra
created_at: '2026-10-09T19:11:30+00:00'
parents:
- grand-ember-9404
summary: ''
---
## What

Measured where the creature re-runs stopped: six Claude Code / Opus 5.5 `cfix-*` projects (paused at the usage limit, then closed) and three Codex / GPT-6-Astra `castra-*` projects (one per animal; the owner stopped one early). The owner reviewed both sets and chose Opus 5.5 for Cadex work from now on.

## Why

To see whether ADR-608..627 changed what agents build, and whether a different agent and model does better on the same briefs.

## Method

For each project, a read-only script opened the accepted revision through cadexd (`open_project`, 900 s budget) and read `inspect scope=anatomy` and the clearance scope through `cadex_cli.clearance.read_fit`. castra-deinonychus's restore ran at full CPU for 36 minutes and was stopped unread.

## Result

| project | anatomy | actuated DOF | fit | sweep |
|---|---|---|---|---|
| cfix-deinonychus-a | complete: legs, claws, arms, neck, head, jaw, tail | 20 | fail (16) | fail |
| cfix-deinonychus-b | complete: arms, neck, head, jaw, tail; toes rigid | 19 | fail (3) | fail |
| cfix-heron-a | undeclared | 15 | fail (208) | fail |
| cfix-heron-b | complete: neck, head, jaw; toes rigid | 10 | fail (26) | fail |
| cfix-leopard-a | complete: spine, neck, head, jaw, tail; paws rigid | 19 | pass | pass |
| cfix-leopard-b | undeclared | 0 | pass | unavailable |
| castra-heron | complete: wings, toes, neck, head, tail; jaw rigid | 12 | pass | pass |
| castra-leopard | complete: spine, neck, head, tail; toes rigid | 18 | fail (124) | fail |
| castra-deinonychus | unread (restore did not finish) | | | |

Against the baseline, where no design jointed a head, jaw, tail, arm or wing, every declared design now does. Most runs stopped before the design was done, so the fit failures are unfinished work, not finished designs. Both castra drafts that stopped mid-build (deinonychus, leopard) recorded 300 s build, inspect and look timeouts at 18-21 QDDs. The owner judged the Opus results much better.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: c2bc1e29a865ce3204cda2b3e116d1a8e9a82b24

## State Impact

- target: NEW agent-model-choice — the owner chose Claude Code with Opus 5.5 for Cadex design runs after comparing it with Codex / GPT-6-Astra on the same creature briefs (2026-10-09)
