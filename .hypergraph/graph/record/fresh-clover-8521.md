---
node_id: 8bc1c2bf-1e18-5cc8-a4f8-c1a0b4b0fa02
slug: fresh-clover-8521
title: Lifecycle history instructions respect repository ownership
created_at: '2026-09-08T21:30:54+00:00'
parents:
- morning-arrow-5841
summary: ''
---
## What

Corrected stale lifecycle project-history promises in docs/MUJOCO.md §7c and
clarified the PROGRESS.md scaffold's commit-success signal (ADR-266).

## Why

The overseer selected standing file-lifecycle maintenance after the decisions-tail
repair. This unit maintains mission 2's project-as-codebase contract and charter
criterion “The walk exists and is tested headlessly” (crisp-reef-5607): operators
must distinguish recorded measurements from successfully versioned history.
The source contradicts the audit's unconditional first-visit initialization and
per-accepted-run commit promises. The reversible choice is to correct instructions,
not change Git ownership or make accepted modelling depend on a successful commit.
The bounded subtractive bet was written in ADR-266 before the doc/scaffold edits.

## Method

Read ensure_project_repo and commit_project in cli/cadex_cli/project_docs.py and
the existing docs/CLI.md ownership contract. Removed the duplicate unconditional
instructions and linked to that contract; retained the historical measured commits.
The scaffold now says a row alone does not prove a commit. Updated ROADMAP.
No runtime Git logic, protocol, payload, shell, or training behavior changed.
The first edit command used unavailable `python`; it changed nothing. Applied the
edit with python3 and launched a fresh complete gate against the final source.
Logs remain outside Git under /tmp/cadex-iteration-37-cli-{gate,final}.log.

## Result

`pixi run python -m pytest cli/tests`: 253 passed, no skips, in 239.45 s
on the final source; the earlier run also passed 253 tests in 239.94 s.
`git diff --check` passed. No build or packaged gate required: only docs and
scaffold wording changed. No new regression was added for this wording correction;
the existing full CLI gate exercises project ownership and commit behavior.
This closes the stale-instruction defect; it supplies no new live-provider or
mechanism evidence. The walk criterion is already working in STATE.md; the human
owns its charter checkbox. Live history iteration still requires newly supplied
capacity and was not attempted or probed. Next: another source-demonstrated
lifecycle maintenance unit if capacity remains closed; no context campaign or
parked criterion is opened. There are now three unreconciled work/bet records;
reconciliation remains the scheduled maintainer's work.
Dispatch closed: 1 unit — align lifecycle history instructions with repository ownership.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 220c55af798838f5e047aa1e6a2268a6e8ea5a19

## State Impact

- target: calm-peak-5247 — Lifecycle audit no longer promises unconditional repository initialization or commits; historical measurements retained and CLI ownership rules linked.
- target: chilly-union-8972 — Project progress scaffold explicitly distinguishes a progress row from confirmed commit success; full CLI gate 253 passed.
