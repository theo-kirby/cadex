---
node_id: 8a60fcd0-c289-5d08-ac5d-a60b0ea3ed53
slug: modest-banner-8771
title: Owner restored Fable access and authorized the remaining ot7 experiments (ADR-383)
created_at: '2026-09-17T14:52:42+00:00'
parents:
- fair-badger-6443
summary: ''
artifacts:
- docs/probes/ot7/retained/fable-restart-availability.json
---
## What

Prepared the owner-authorized continuation of ot7 on its existing branch,
with every configured role and every product experiment selecting
`claude-fable-5` (ADR-383). Removed other-model fallbacks and automatic
rotation, cleared the expired absolute deadline for a fresh 48-hour budget,
and preserved the two accepted done verdicts as the completion stop.

## Why

The previous owner directive finished the correction and reconciled the
rejected claims, then held F6/F7 while product access remained unproven.
The owner now reports restored capacity, explicitly authorizes resumption,
and asks for everything to use Fable. This supersedes the hold condition;
it does not reopen exhausted F4/F5 or declare a design successful.

## Method

Read the stopped run's log, archive and operator instructions. A no-tool
Claude call requested `claude-fable-5` and returned READY with exit 0.
Then `pixi run python docs/probes/ot7/runner/run.py window --model
claude-fable-5` returned allowed, room=true, five-hour usage 0% and weekly
usage 6%. The sanitized receipt retains the auxiliary model-usage keys and
window metadata rather than claiming that the CLI reported only one model.
Updated config, charter, operator instructions and ADR-383. Archived the
prior run and recorded the lesson that repeated actor/critic waiting turns
still spend subscription capacity. No frozen design prompt was dispatched
by this preparation and no test project's design was edited.

## Result

The prior organisation-level refusal is no longer reproduced by either
availability check. The next substantive work is Robin F6 then Plover F7,
with frozen prompts and existing slots, followed by final regression and
closing-report evidence. Further refusal invokes the existing waiting rule,
not unrelated tooling work. This record prepares launch; it does not assert
that the process is already running or that any experiment passed.

Baseline verification before launch: `pixi run test-engine` — 2169 passed,
53 skipped in 318.18 seconds; `pixi run python -m pytest cli/tests` — 831
passed, 1 skipped in 553.32 seconds. This is an operator configuration and
charter change, with no product, protocol or payload edit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 76ba571044001292e0934472d8f0bdc5c22c8e5a

## State Impact

- target: mild-ledge-7157 — owner authorized continuation on Fable for all roles, with fresh 48-hour budget; previous hold is superseded after successful availability checks; frozen F6/F7 experiments precede any further tooling
- target: narrow-dune-9454 — provider block no longer reproduced by launch-time Fable and window probes; F6 remains unattempted with all slots unspent, now available for dispatch
- target: rapid-grove-9687 — shared provider block no longer reproduced; F7 remains unattempted with all slots unspent, next after F6
