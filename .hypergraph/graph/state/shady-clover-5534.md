---
node_id: 0d1755fd-e113-53fb-9393-31d06b2ce68d
slug: shady-clover-5534
title: W1. Nothing the product could do headlessly was lost (orun2)
created_at: '2026-10-03T10:54:47+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run orun2: **W1. Nothing the product could do headlessly was lost.** - On a copy of an existing robot project, the whole walk runs and every step is visible in the dashboard: 1. prompt; 2. accepted design; 3. params sweep; 4. `look` and render; 5. STEP/STL export; 6. MJCF export; 7. a short training run on the 5090; 8. `evaluate`. - Both full suites pass, and so does the packaged lifecycle gate. - The CLI and dashboard have no feature the shell parity ledger below marks "ported" without a test. - **The parity ledger is complete:** `docs/SHELL-PARITY.md` gives each of these one row: - every `mesh_agent` module; - each of its 23 tools; - each of the seven Cadex editors. Each row says one of three things: **ported** (where, and the test), **already covered** (where), or **dropped** (why, and the ADR). No row is blank. [rec: winter-stone-5109]

**Parity ledger skeleton exists (commit `94b5be8f`).** `docs/SHELL-PARITY.md` has one row for each of the 47 `mesh_agent` entries (44 Python modules + `pi_tools.js`), each of the 23 shell tools and each of the 7 Cadex editors — no row blank [rec: old-arrow-4088].

**Rows closed with tests since** [rec: sweet-arrow-0695] [rec: curious-flint-4836]:

- **Blueprint rows → ported.** `cadex_sheet.py`, `make_blueprint` and `save_blueprint` are the agent's `draw_blueprint` (`CadexStudio.blueprint_sheet`, stored through `put_blueprint`, versioned by name); `cadex_drawings.py` and the Blueprint editor become stored sheets shown under the dashboard's **Drawings** panel. Test: `cli/tests/test_blueprint.py`, including a real-engine headless-Chromium test (ADR-516) [rec: sweet-arrow-0695].
- **`prefs.py` row → ported; its last "owner to confirm" closed.** The shell's engine timeout and memory budgets now belong to the project: `agent.json` budgets, `cadex budgets`, `--engine-timeout`/`--engine-memory` per call, the engine resolving budgets per field, read-only on the dashboard. Test: `cli/tests/test_project_budgets.py`, including real-engine and headless-Chromium tests (ADR-517) [rec: curious-flint-4836].

**Walk steps 1–6 evidenced, each seen in the dashboard** on `orun2-w1-quad`, a whole copy of `ot11-quad-1`, driven in headless Chromium by `docs/probes/orun2/w1/walk_dashboard.py` (measurements in `walk-steps.json`, commit `9d487b65`) [rec: red-loom-2239]:

- **1. Prompt:** `cadex -p` 335 s, accepted `a7d487ae`; listed on the index and under CLI agent turns [rec: red-loom-2239]
- **2. Accepted design:** **Accept** verdict; model loaded, 62 components; page and index agree [rec: red-loom-2239]
- **3. Params sweep:** `shin` slider 3/3 at ~116 s each; 55 mm returns to digest `25984e70` [rec: red-loom-2239]
- **4. Render:** `cadex render` 155 s, shown on the Concept tab [rec: red-loom-2239]
- **5. STEP/STL:** page Export 62 STEP + 62 STL in 116.8 s [rec: red-loom-2239]
- **6. MJCF:** `model-model.xml` (8 actuators) and the task JSON downloaded [rec: red-loom-2239]

**Gates:** both full suites green at `21d130f5` — engine 2594 passed / 56 skipped; CLI 1398 passed / 1 skipped (GPU hidden), after the dashboard-restart flake (fixture `recorded_at` ties) and a viewer-settle race in four dashboard-write browser tests were fixed in test logic, with no retry and no weakened assertion [rec: amber-moon-9415]. The packaged gate has not been run this run.

**Not yet evidenced:** walk step 7 (a short training run on the 5090; `orun2-w1-quad` stores `policy_on` 0, and `nvidia-smi` could not reach the driver in that iteration) and step 8 (`evaluate`); the row-by-row ledger audit; final full suites and the packaged gate [rec: red-loom-2239]. **Against "nothing lost":** a robot project trained before ADR-469 cannot be opened at all — see `brisk-rock-9862` [rec: red-loom-2239]. Minor findings from the walk: the Model tab opens with the robot as a speck until **Fit** and in debug colours; a CLI turn's transcript and `look` images do not appear on the project page [rec: red-loom-2239].

Reconcile judgement: stays `open` — steps 7–8, the ledger audit, the packaged gate and the lock defect stand between this and the criterion [rec: red-loom-2239].

Declared target: `gap-w1-nothing-product-could-do`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun2 gap title carries the run [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- old-arrow-4088 — SHELL-PARITY.md skeleton: 47 module / 23 tool / 7 editor rows, none blank, statuses interim
- sweet-arrow-0695 — blueprint ledger rows ported: draw_blueprint and the Drawings panel, tested (ADR-516)
- curious-flint-4836 — prefs.py ledger row ported: engine budgets belong to the project, tested (ADR-517)
- amber-moon-9415 — both full suites green at 21d130f5; restart flake and viewer-settle race fixed in test logic
- red-loom-2239 — W1 walk steps 1–6 on orun2-w1-quad, each seen in the dashboard; pre-ADR-469 trained projects unopenable
