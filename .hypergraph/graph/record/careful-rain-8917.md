---
node_id: ba904d04-ac34-5abc-b079-ecd3d89b5757
slug: careful-rain-8917
title: 'orun2 R1 part 2: README, ARCHITECTURE, INTEGRATION, ROADMAP (iteration 11 catch-up record)'
created_at: '2026-10-03T15:27:48+00:00'
parents:
- smooth-cedar-5324
summary: ''
---
## What

Retroactive record for commit `06bdb19a` ("ouroboros #11: no record"): orun2 R1 part 2. `README.md` and `docs/ARCHITECTURE.md` §1 name Cadex's three parts (engine, dashboard, agent). `docs/INTEGRATION.md` became the contract between the engine and its one client (`cli/`): how that client resolves an engine (`--engine`, `CADEX_ENGINE_ROOT`, the build tree) and how the dashboard's trace reader plays a rollout; the options and decision-gate sections are marked historical. `docs/ROADMAP.md` got exactly the three changes R1 names: Phase 12 superseded by a desktop app that copies the dashboard, Phase 13b's shell box closed by deletion, Phase 6 marked historical. ADR-500 gained an "applied to README, ARCHITECTURE, INTEGRATION and ROADMAP" paragraph. New test `test_readme_architecture_and_integration_describe_the_three_parts` in `cli/tests/test_project_docs.py` pins all of it.

## Why

The critic accepted iteration 11's change but rejected it for the missing record, and asked for this record first. Iteration 11's unit was the next R1 piece after `smooth-cedar-5324` (ADR-500, AGENTS.md, VISION).

## Method

Read from `git show 06bdb19a`: the six changed files, the ADR-500 paragraph and the new test. No code was re-run for this record; iteration 11's commit was accepted by the critic as green.

## Result

What is true now: README, ARCHITECTURE, INTEGRATION and ROADMAP describe the three-part product, pinned by a test. Two inconsistencies left by iteration 11 and named by the critic: `docs/ARCHITECTURE.md` links `docs/DASHBOARD.md`, which did not exist yet, and README's DASHBOARD link pointed at `docs/REVIEW-DESIGN.md`. The next record (iteration 12's unit) fixes both. R1 still needs DASHBOARD.md and frontier pruning.

Dispatch closed: 1 unit — retroactive record for iteration 11 (R1 part 2: README, ARCHITECTURE, INTEGRATION, ROADMAP)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 06bdb19a35c877e7d7906b48753fc259861eab44

## State Impact

- target: eager-sea-3906 — README, ARCHITECTURE §1 and INTEGRATION frame the engine, dashboard and agent; ROADMAP Phase 12 superseded, Phase 13b shell half closed, Phase 6 historical (commit 06bdb19a), pinned by test_readme_architecture_and_integration_describe_the_three_parts. Open: DASHBOARD.md, frontier pruning
