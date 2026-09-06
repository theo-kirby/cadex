---
node_id: 313fd837-4f31-5d4b-8906-21ef0a8008e0
slug: wild-marsh-9611
title: 'Project docs state the training mode: scaffold Training section, (remote) rows, pinned to docs/CLI.md (ADR-200 follow-up)'
created_at: '2026-09-06T19:50:21+00:00'
parents:
- green-delta-7130
summary: ''
---
## What

The project-doc scaffold caught up with the remote walk (ADR-200 follow-up, commit 8c1ff05f). `cli/cadex_cli/project_docs.py`'s `ARCHITECTURE.md` template now carries a `## Training` section for the agent to fill in: the mode (the trainer's venv on this machine, or `cadex train --remote` / `cadex walk --remote` on the box `training/remote_train.sh` names), the statement that the artifacts land at the same project-relative paths in both modes (`runs/<name>/train/`, `runs/<name>/rollout/`, `runs/<name>/review.json`, the `PROGRESS.md` row), and the cold-run limit (a warm start trains locally). A `train --remote` run's `PROGRESS.md` row ends in `(remote)` (`_progress_what` in `cli/cadex_cli/__main__.py`), so the numbers say where they came from. `docs/CLI.md` §2's remote paragraph names the section; `docs/DECISIONS.md` ADR-200 gets a follow-up paragraph, not a rewrite.

## Why

The critic rejected iteration 3: the walk changed but the scaffold did not, and the charter's quality bar says a change to the lifecycle walk updates its doc and the project-doc scaffold in the same commit. The overseer asked for this exact unit, fixed forward. It serves mission 2 (the project as a codebase; three modes, one shape) and the frontier node `witty-spark-2613`. Assumption written here rather than asked: the section is a template the agent fills in (mode line in parentheses), not a value the CLI writes, because the scaffold is written once on first visit and never overwritten, and a project can be trained both ways over its life; the per-row `(remote)` marker is what records which mode a given number came from.

## Method

Edited the template and the module docstring; added the `(remote)` suffix to the train row's What column, only with `--remote`. Two tests in `cli/tests/test_project_docs.py`: one asserts the scaffold's facts (both modes, the shared paths, `cold runs only`, `--init-from`, the `(remote)` marker) and reads `docs/CLI.md` to require the sentence that names the scaffold's section, so the doc and the scaffold are one ticket; one pins the row text local versus remote. Ran `cli/tests/test_project_docs.py` (14 passed) and the full CLI suite with the real engine and trainer venv.

## Result

Full CLI suite: 136 passed in 113 s, no skips (was 134). No engine, shell or payload change, so no other gate applies. Nothing dispatched; the GPU box untouched. The unreconciled tail is now four nodes, past the three-node trigger; the maintainer pass is due before short unit 3 (document the GUI-attached walk).

Dispatch closed: 1 unit — the project-doc scaffold states the training mode, the shared artifact paths and the cold-run limit, pinned to docs/CLI.md; CLI suite 136 passed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 8c1ff05fe21e6b94588995a78336f77816f23375

## State Impact

- target: witty-spark-2613 — the project-doc scaffold now names the training mode (venv or --remote), the same project-relative artifacts in both modes and the cold-run limit; train --remote rows are marked (remote); the walk doc and the scaffold are held together by a test (commit 8c1ff05f)
- target: calm-peak-5247 — ARCHITECTURE.md scaffold carries a Training section; PROGRESS.md train rows say (remote) when trained on the box
