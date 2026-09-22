---
node_id: 7c7ccb52-7ffc-59bd-b7bd-ea94b6131478
slug: shy-fjord-4367
title: 'ot9 model policy: Opus 5.5 without fallback'
created_at: '2026-09-22T17:28:31+00:00'
parents:
- silver-cloud-5850
summary: ''
---
## What

Before ot9's first launch, the owner changed its model policy from Fable 5.1 with Codex fallback to Opus 5.5 with no fallback.

## Why

This directly supersedes the model choice in the ot9 charter decision [rec: silver-cloud-5850]. The experiment target, evidence bar, 48-hour ceiling and two accepted done verdicts remain unchanged.

## Method

Updated `.ouroboros/config.yml` so actor, critic, disabled maintainer/planner, and reporter all name `claude-opus-5-5` and carry no fallback. Updated `.ouroboros/goal.md`, `.ouroboros/AGENTS.md`, and ADR-404 so product-agent calls use the same model and provider unavailability causes waiting rather than model substitution.

## Result

The launch configuration is committed at `cfecf283`. ot9 had not been launched, so no in-flight work or evidence changed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cfecf283ed2d147d1bd7b566e5f09c2a2195ffde

## State Impact

- target: NEW ot9-robin-trained-balance — Before first launch, owner superseded Fable-plus-Codex selection with claude-opus-5-5 for all roles and product calls, with no fallback; experiment and stop bars unchanged.
