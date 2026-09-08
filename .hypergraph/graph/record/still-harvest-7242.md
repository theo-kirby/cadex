---
node_id: 108ab0b5-8884-5117-a350-6a786be3720e
slug: still-harvest-7242
title: Correct the lifecycle guide's progress-row contract
created_at: '2026-09-08T15:16:44+00:00'
parents:
- frosty-wolf-4770
summary: ''
---
## What

Corrected docs/CLI.md's obsolete assertion that the lifecycle walk writes no PROGRESS.md row. Child legs retain reward/delta rows, and a successful walk adds the clearance review row already described above. Failed legs retain earlier rows without adding a walk review row. Logged the removal in ADR-238 and ticked the specific ROADMAP maintenance item; verified dates already read 2026-09-08. The guide loses one line.

## Why

Selected short-plan unit 1 from frosty-wolf-4770: bounded standing maintenance for missions 2 and 6, advancing the accuracy of the charter's “The walk exists and is tested headlessly” and “The agent can see its work without a screen” documentation. The contradiction was concrete: the same guide both denied and described the walk's clearance row. Assumption: existing behavior is authoritative; no runtime or scaffold change is needed because the scaffold already documents its own clearance row. No parked criterion is opened, and no new walk is commissioned.

## Method

Read _record_progress and its success-only caller in cli/cadex_cli/__main__.py, the existing walk tests' progress assertions and failure checks, project_docs.py's scaffold, ADR-238 and the durable iterate evidence in mellow-quartz-8093. Replace only the contradictory paragraph, referring to the guide's existing review explanation. Preserve failure reporting and operational flags. Run pixi run python -m pytest cli/tests with output at /tmp/ot4-progress-guide-cli.log. The initial edit helper used an unavailable python command and changed nothing; reran it successfully with python3.

## Result

CLI gate: 223 passed, no skips, 227.53 s, exit 0, including real engine/trainer walk coverage. git diff --check passed. Documentation-only correction; no behavior, scaffold, protocol, payload or shell change, so no build required. The existing scaffold remains accurate and unmodified. No new source-string test or generated output is committed.

The cited criteria remain working in reconciled state; no missing runtime leg was identified by this correction, and human-owned charter boxes remain unchanged. Next is the already-selected short-plan unit 2: compress only the model-free carriage iterate rehearsal, preserving its command, lower reward, baseline and limitations. One unreconciled record preceded this unit; this adds the second, without performing reconciliation or editing the plan.

Dispatch closed: 1 unit — corrected the walk progress-row guide against existing tested behavior.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 502f6febc7b5af7eb478ecaa8e41d9cccc57de06

## State Impact

- target: calm-peak-5247 — Guide now distinguishes child reward/delta rows from the successful walk clearance row and preserves failed-leg behavior; existing CLI gate 223 passed.
- target: damp-moon-9297 — Removed the guide's denial of its own review row; documentation agrees with the existing clearance review and scaffold without changing runtime.
