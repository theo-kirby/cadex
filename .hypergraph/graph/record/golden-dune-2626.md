---
node_id: ee2d22e2-777b-592f-a36f-0db8d4a8bd5b
slug: golden-dune-2626
title: 'ADR-575: a project reads found from its agent''s first tool call, not its first script'
created_at: '2026-10-06T21:57:07+00:00'
parents:
- candid-walrus-1021
summary: ''
---
## What
Fixed the orun3 defect where a project being worked on read "not found" until its first script (ADR-575, commit `807cfdfa`). `ProjectsDirectory` in `cli/cadex_cli/review_server.py` now counts a subdirectory as a project when it holds any of `PROJECT_MARKERS`: `script.json`, `review/activity.jsonl`, `.cadex-cli.lock` or `agent.json`. Test `cli/tests/test_app.py::test_a_project_being_worked_on_is_listed_before_its_first_script` (parametrised over the three CLI markers), `docs/CLI.md`'s `cadex app` row, ADR-575 in `docs/DECISIONS.md`, and `docs/probes/orun4/REPORT.md` §6/§7 updated.

## Why
The critic asked for two things in order: (1) run the hypergraph-reconcile pass to fold `candid-walrus-1021`, then (2) fix the "not found until first script" defect test-first, then measure the 37–39 s pre-checkpoint stall. **I did not run the reconcile pass.** This iteration's dispatch forbids it outright in a work iteration ("hypergraph-reconcile skill … no exceptions"), so it remains for a reconcile/housekeeping pass; the tail is now two records (`candid-walrus-1021` and this one). I did (2), the goal's long-term rung 2 first item. The stall measurement is the next unit (one unit per iteration).

## Method
Root cause, read from source: `ProjectsDirectory._names` required `script.json`, which the engine's `CadexProjectScriptStore` writes only with the first script. `McpSession.call` writes `review/activity.jsonl` (`begin_activity`) at the agent's first tool call, and `_engine_session` takes `.cadex-cli.lock` (`project_lock`) when the engine opens; `cadex budgets`/`cadex style` write `agent.json`. So a directory with any of those is a project whose agent has started.
Test first: on the `test_app.py` fixture, an `orun4-fresh` directory is given only one marker (written by the real `begin_activity`, `project_lock` and `write_agent_budgets`); asserts no `script.json`, the project in `/api/projects`, `/p/orun4-fresh/api/project` 200 with `accepted.available: false`, the page 200, and `p/notes/api/project` (a bare dir) still 404. Before the fix all 3 cases failed (`assert 'orun4-fresh' in ['biped', 'empty']`); after, `test_app.py` 12 passed.

## Result
A project is on `cadex app`'s index and its page answers from the agent's first tool call. No route, response schema, engine module, protocol op or tool changed; the server still writes nothing.
Gates (foreground, GPU hidden, `-rf`): CLI thirds 395 passed (152 s); 324 passed, 1 skipped (344 s); 489 passed (234 s). `pixi run test-engine` 2611 passed, 58 skipped (343 s). The third-1 flake did not recur.
Concern: the reconcile the critic asked for is still owed (tail: `candid-walrus-1021` plus this record). Next: measure the trainer's 37–39 s pre-checkpoint stall before changing anything; then the `checkpoint_every` guidance defect.

Dispatch closed: 1 unit — ADR-575, a project is listed and served from its agent's first tool call, not its first script

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 807cfdfaaab84a62b1fcf2c99807bce2fc9501fa

## State Impact

- target: jolly-loom-0622 — cadex app lists and serves a project from the agent's first tool call (activity log, CLI lock or agent.json), not only once script.json exists (ADR-575); orun3's 'not found until first script' defect is fixed
