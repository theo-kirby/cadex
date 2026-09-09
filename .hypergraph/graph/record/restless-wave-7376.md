---
node_id: 1a873c5d-35f8-5515-aeb1-5502e7ced66a
slug: restless-wave-7376
title: Project model continuity survives a refused override
created_at: '2026-09-09T01:24:57+00:00'
parents:
- silent-anchor-7513
summary: ''
---
## What

Prompt and walk design turns now resolve their model in order: explicit flag,
nonblank CADEX_MODEL, project agent.json model, built-in default. A failed
provider turn with the same session ID preserves the entire prior agent record;
a changed locator still persists with its attempted model. ADR-276 narrows
ADR-247. CLI docs, project scaffold and ROADMAP describe the same contract.

## Why

Advances the charter criterion **The walk exists and is tested headlessly**
and mission 2's project continuity, targeting crisp-reef-5607 and
chilly-union-8972. The overseer explicitly selected the model-continuity unit
(the plan lists its content first despite the message's item number).
A provider refusal had overwritten a project's remembered model, and the next
turn ignored that record anyway. The reversible choice preserves failed
same-session metadata without suppressing resumable new session locators.
No provider probe, alternate-model campaign, remote dispatch or engine edit.

## Method

Remove parser defaults, resolve against the record in command_prompt, and
let walk forward a model flag only when supplied. Keep the attempted model
in the report. Gate persistence on provider success or a changed session ID.
Extend offline real-engine walk refusals to check a changed model on the same
locator, changed model with a new locator, and omitted model; the fake executable
asserts the actual --model it receives. Pin bytes, inode and mtime for preserved
records. Ten stub-turn cases exercise flag/environment/project/default precedence
with and without resume; existing successful resumed edits pin model updates.

## Result

Validation: `pixi run python -m pytest cli/tests` exited 0: 280 passed,
0 skipped in 227.62 s, including real-engine offline refusals, training and
walk coverage. Output: `/tmp/cadex-iteration49-cli.log` (local, uncommitted).
`git diff --check` passed. No build required for this CLI-only change.
The provider's capacity remains untested after the prior refusal, and this
unit adds no fresh design-from-empty mixed-joint walk evidence. Earlier
successful lifecycle evidence remains valid. Before that additional coverage
can land, the fresh mixed-joint invocation must reach geometry and every later
leg; this offline fix makes no claim to have done that. Next unit: join section
misses to rollout movement using stable identities, preserving unknown matches.
Dispatch closed: 1 unit — preserve project model continuity across refused turns

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 55f2c4f3ed9ae4344c2d6f1153aec87a3989e108

## State Impact

- target: chilly-union-8972 — ADR-276 resolves flag, environment, project model, default; failed provider turns with an unchanged locator preserve agent.json, while new locators still persist. CLI gate 280 passed, 0 skipped.
- target: crisp-reef-5607 — Model continuity fix protects walk design turns after refusal; offline real-engine coverage passes, no new provider probe or fresh mixed-joint walk evidence.
