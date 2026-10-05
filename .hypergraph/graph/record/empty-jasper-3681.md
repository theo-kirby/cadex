---
node_id: fd4674fa-4270-5c45-a61d-a9c0a0a7d049
slug: empty-jasper-3681
title: Evaluating line names the agent's evaluate call, never an evaluation directory id (ADR-555); REPORT defect 2 fixed
created_at: '2026-10-05T16:46:30+00:00'
parents:
- easy-grove-4224
summary: ''
---
## What
Fixed orun3 REPORT §5 remaining defect 2 (ADR-555, commit `29b63e45`). While a `cadex mcp` `evaluate` call is in flight, the overlay's evaluating line now reads "the agent's evaluate call is running · <duration>" for the whole call, even after the evaluation writes its directory. If an evaluation directory is fresh and no such call is in flight, the line reads "an evaluation is running". It never shows the directory's id.

## Why
The critic named this as the next unit under the exhaustion policy: remaining defect 2, with a browser test, and REPORT §5 updated in the same commit. The critic also asked to "reconcile easy-grove-4224 first". I did **not** do that. This dispatch forbids the hypergraph-reconcile skill in a work iteration, with no exceptions. The tail is now two records (easy-grove-4224 and this one), and they are left for the reconcile pass. The critic did not ask for three new directions in the plan this time beyond naming the unit, so the plan was not edited.

## Method
`project_stage` (`cli/cadex_cli/review_server.py`) checked the evaluation directory before the in-flight call. Once the directory existed part-way through the call, its reason, `evaluation <dir> is running`, won, and `since` reset to the directory's last write. I swapped the order: the in-flight `evaluate` (ADR-553) wins, with its start as `since`. The directory-only reason drops the id. The page is unchanged; no route, key or poll was added.

Tests in `cli/tests/test_review_overlay.py`:
- A new Chromium test drives the page through `browser.py`. An `evaluate` call in flight for 65 s reads "the agent's evaluate call is running · 1 min". The directory `evaluations/dc0af1158165-…` then appears, and over two polls the line is unchanged and has no id. When the call returns, the line reads "an evaluation is running".
- The server-side directory test now pins that reason exactly.

Docs: `docs/CLI.md`'s stage `reason`, the `docs/DASHBOARD.md` overlay row, the ADR-555 entry in `docs/DECISIONS.md`, and REPORT §4 (ADR row) and §5 (defect 2 marked fixed).

## Result
- Without the fix, the new browser test and the directory test both fail; with it, they pass (4 passed, Chromium ran, not skipped).
- Full suites at `29b63e45`:
  - `pixi run python -m pytest cli/tests` with the GPU hidden: 1174 passed, 1 skipped.
  - `pixi run test-engine`: 2585 passed, 58 skipped.
- The protocol and payload were not touched, so the packaged gate was not needed.

Not yet re-walked on `orun3-biped`; ADR-554's fix is in the same position.

Remaining from REPORT §5:
- Defect 3, the 37–39 s progress stalls before each checkpoint, is the trainer's own, measured with rollouts on and off.
- The long-term rungs: phone width and the light theme for the overlay and scrubbers, and binary meshes.

Concern: the unreconciled tail is two records. The critic asked for a reconcile and it was not done here, because a work iteration forbids it.

Dispatch closed: 1 unit — evaluating line names the agent's evaluate call, not the evaluation directory id (ADR-555)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 29b63e452a66f94856619332e95304444584e7fd

## State Impact

- target: vast-ivy-6277 — the evaluating stage reason is the in-flight agent evaluate call for the whole call, else 'an evaluation is running'; no directory id is shown (ADR-555, 29b63e45); REPORT §5 defect 2 fixed
