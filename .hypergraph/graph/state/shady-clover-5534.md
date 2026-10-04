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

Not yet evidenced: a row-by-row audit that every remaining row carries a final ported/covered/dropped verdict, and the eight-step walk run against the dashboard. Reconcile judgement: stays `open` — the folded records close individual ledger rows, not the criterion's whole-ledger and walk conditions [rec: curious-flint-4836].

Declared target: `gap-w1-nothing-product-could-do`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun2 gap title carries the run [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- old-arrow-4088 — SHELL-PARITY.md skeleton: 47 module / 23 tool / 7 editor rows, none blank, statuses interim
- sweet-arrow-0695 — blueprint ledger rows ported: draw_blueprint and the Drawings panel, tested (ADR-516)
- curious-flint-4836 — prefs.py ledger row ported: engine budgets belong to the project, tested (ADR-517)
