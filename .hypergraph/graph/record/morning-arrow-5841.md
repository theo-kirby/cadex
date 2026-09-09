---
node_id: 35293196-0d10-5094-b876-39ce622b0af1
slug: morning-arrow-5841
title: Recent project decisions survive bounded prompt context
created_at: '2026-09-08T21:22:58+00:00'
parents:
- restless-cabin-9629
summary: ''
---
## What

Kept recent DECISIONS.md entries in bounded project prompt context using the existing tail helper. Updated lifecycle documentation, the project scaffold, ADR-265 and a completed ROADMAP item. Added overflow coverage by extending existing document and turn regressions.

## Why

Follows restless-cabin-9629, short-plan unit 1. Advances mission 2's Project as codebase contract and maintains the tested headless lifecycle criterion (crisp-reef-5607): newest-last decisions beyond 8,000 characters were invisible on revisit. Assumption: recent constraints take priority over older ADRs within the existing budget. No supplied capacity signal reopens the live provider iterate; no quota probe or provider attempt was made.

## Method

Before changing selection, ran `pixi run python -m pytest cli/tests/test_project_docs.py cli/tests/test_turn_loop.py -k 'read_keeps_architecture or reads_current_project_history' -q`: all four cases failed. Two pin exact 4,000/8,000-character selection and omission counts with byte-preserved source files, architecture head and domain-note tail. Two use a real engine and scripted agent turns to demonstrate missing newest ADR delivery on fresh/resumed visits and preserve appended history. Replaced only the decisions head selection with the existing tail selection. Ran `pixi run python -m pytest cli/tests` after the repair. Local logs: `/tmp/cadex-36-before.log`, `/tmp/cadex-36-cli.log`; generated output is not committed.

## Result

Full CLI gate: 253 passed, no skips, in 228.35 seconds. `git diff --check` passed. Limits and omission markers are unchanged; full source documents remain on disk. Old decisions outside the tail are omitted, not summarized. No engine, payload or shell code changed, so no build or packaged/shell gate was required. The walk criterion already has working graph evidence; this repair supports its project-history contract and does not claim a new end-to-end run. What remains unmeasured is a real provider using that history to choose and train an iterate; only supplied capacity permitting that existing task should reopen it. No additional seed runs, new frontier or general context campaign follows this unit.

Dispatch closed: 1 unit — retained recent project decisions in fresh and resumed prompts.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 4b115d9e69006b22a2ee627173953abd5bbaf082

## State Impact

- target: chilly-union-8972 — ADR-265 retains DECISIONS.md tail within existing prompt limits; four before-failing regression cases and full CLI gate 253 passed.
- target: calm-peak-5247 — Project-as-codebase revisits receive recent overflowing ADRs on fresh and resumed scripted turns; complete history stays on disk, live provider understanding remains unmeasured.
