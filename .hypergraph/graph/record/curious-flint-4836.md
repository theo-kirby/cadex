---
node_id: 8e08ee38-1594-5c3d-8d45-836809f581f4
slug: curious-flint-4836
title: 'orun2: engine budgets belong to the project — cadex budgets, --engine-timeout, --engine-memory (ADR-517; record for iteration 35)'
created_at: '2026-10-04T00:33:39+00:00'
parents:
- sweet-arrow-0695
summary: ''
---
## What

The record for iteration 35 (commit `b1041597`, ADR-517), which that
iteration did not write; minted in iteration 36 at the critic's fix-first.

Engine budgets belong to the project, per the owner's orun2 note
(2026-10-03):

- **Stored** in the project's `agent.json` as `budgets: {timeout_seconds,
  memory_limit_mb}`, absent when unset, never 0. `cadex budgets --set
  NAME=VALUE` stores (`=0` unsets); with no `--set` it reports. No engine,
  no `PROGRESS.md` row, no commit. A turn rewriting the conversation
  identity keeps them; an out-of-range hand edit reads as unset.
- **Overridden per call** by `--engine-timeout S` / `--engine-memory MB`
  (shared flags; `walk` passes them to every leg). Out of range is exit 2
  before an engine starts. The store is never changed by an override.
- **Sent** by `_engine_session` as `open_project`'s existing `budgets`
  argument, so the dashboard's CLI-child writes use the same budgets (A3).
  Every engine envelope carries `budgets`: `in_force`, `stored`, and each
  budget's `source` (`override`, `project`, `engine`).
- **Engine:** `CadexEngineSettings.resolve_budgets` now takes each positive
  caller value per field and fills the other from preferences (it used to
  require both or drop both). `OP_ARG_SPECS` and the reply shape unchanged.
- **Dashboard:** Identity's last row, `#view-budgets`, read-only.
- Docs: ADR-517, `docs/CLI.md`, `docs/ARCHITECTURE.md`,
  `docs/DASHBOARD.md`, `docs/INTEGRATION.md`; `docs/SHELL-PARITY.md`'s
  `prefs.py` row now says the budgets were ported to the project (ADR-517),
  closing its "owner to confirm".

## Why

The owner's iteration-32 note ordered two units before more D3: the
blueprint composer (`sweet-arrow-0695`) and project budgets. This is the
second. It serves W1 (`shady-clover-5534`): the parity ledger's `prefs.py`
row carried the last budget "owner to confirm". Iteration 35 committed the
work (loop commit `b1041597`, `recorded: false`) without a record; the
critic's fix-first asked for this one, causally parented, with both
suites' evidence.

## Method

- Read the work as committed: `git show b1041597` (17 files, +592/−33),
  ADR-517, and `cli/tests/test_project_budgets.py`.
- Ran both full suites in iteration 36 on a tree containing `b1041597`
  (plus iteration 36's own dashboard change, which touches no budgets
  code): `pixi run test-engine` and `pixi run python -m pytest cli/tests`
  with the GPU hidden. Iteration 35's own transcript records no suite run
  that this record could cite, so these are the receipts.

## Result

- **True now:** engine budgets are project state with per-call overrides,
  shown read-only on the dashboard; the engine resolves them per field.
- **Tests:** `cli/tests/test_project_budgets.py` (store, unset, ranges,
  hand-edit nonsense, override precedence, `open_project` arguments, `walk`
  pass-through, `cadex budgets` with no row and no repo, usage errors;
  against a real engine: engine defaults, a stored 901 s timeout with the
  engine's memory filled per field, `--engine-timeout 77 --engine-memory
  5000` for one call leaving the store unchanged, `-1` exit 2; headless
  Chromium: Identity's read-only row before and after `cadex budgets
  --set`). `test_engine_defaults_and_envelopes.py::test_caller_budgets_win_per_field`
  pins the engine half.
- **Gates (run in iteration 36):** `pixi run test-engine`: 2594 passed, 56 skipped, exit 0. `pixi run python -m pytest cli/tests` (GPU hidden, run alongside the engine suite): 1394 passed, 1 skipped (`test_review_server.py`, needs `CADEX_REVIEW_HOST`), 1 failed — `test_review_lifecycle.py::test_restarting_the_dashboard_keeps_the_review_and_leaves_training_alone` (default run read `RUN sample`, not `RUN second`), which passed alone both with and without iteration 36's change and passed with its whole file (2 passed); a load-dependent flake in a test that touches no budgets code, not a pass.
- **Packaged gate not run:** `OP_ARG_SPECS` and the reply shape did not
  change; `CadexEngineSettings.py` changed in behaviour only, and reaches a
  payload through `stage-engine` like any engine module. Not run is not
  passed.
- **Concern:** iteration 35 left no record; it is written late, by a
  different session, from the commit and the ADR.

Written late, for iteration 35; iteration 36's own unit is recorded separately as its child.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: b1041597235d379cd45bdf8c1ba39774728fd2dc

## State Impact

- target: shady-clover-5534 — the parity ledger's prefs.py row closes its last 'owner to confirm': the shell's engine timeout and memory budgets are ported to the project (agent.json budgets, cadex budgets, --engine-timeout/--engine-memory per call, engine resolve_budgets per field, read-only on the dashboard; ADR-517, cli/tests/test_project_budgets.py incl. real-engine and headless-Chromium tests)
