---
node_id: b14b865f-bebf-54e0-ab42-a8ae32bfcbcd
slug: fresh-orchard-6718
title: 'ot10 A3a: appearance roles and palette in xscript (ADR-413), recorded late'
created_at: '2026-09-27T17:11:48+00:00'
parents:
- happy-garden-2470
summary: ''
---
## What
ot10 A3, first half: xscript now declares each part's appearance role and the assembly's palette (ADR-413, commit `b8d61de0`). That commit landed in iteration 4 without a record ("ouroboros #4: no record"). This record is written in iteration 5, at the critic's request, so the work is visible to the graph.
- `assembly.component(..., appearance="shell"|"mechanism"|"accent")` and `assembly.assembly(..., palette={role: "#RRGGBB"})`, validated at declaration: an unknown role, a malformed colour and an empty palette are refused with the fix named. The palette is normalised to upper case in role order.
- Undeclared keys stay out of the definition, so no existing script's content digest moves.
- `inspect scope="inventory"` rows carry `appearance` when declared, and the value carries `palette`. The CLI inventory block, `docs/inventory.md`, `render.declared`, `cadex render` and the bridge's `look` all use them. `render`'s summary records each object's role, colour and `source` (`declared`, `supplier`, `index`).

## Why
The critic named A3 after A2 (short rung 3). Roles are the input the A3 proxies and the renderer need. Serves `warm-basin-7003`.

## Method
Engine: `cadex_assembly_api.py` (validation, definition keys), `cadex_project_api.py` (the project script's `component` wrapper passes `appearance`; a real-kernel test caught that it did not), `CadexInspection.py` (inventory row and value). CLI: `inventory.py`, `render.py`, `bridge.py`, `tools.py`, `agent.py`. Tests in `cadex_tests/test_inventory_scope.py`, `cli/tests/test_inventory.py` and `cli/tests/test_look.py`. Docs: `docs/XSCRIPT.md`, `docs/CLI.md`, `docs/DESIGN-LANGUAGE.md`, ADR-413.

## Result
- Suites at `b8d61de0`, run in iteration 5: `pixi run test-engine` **2212 passed, 53 skipped**; `pixi run python -m pytest cli/tests` **980 passed, 1 skipped**.
- No protocol op changed (`inspect` already takes `scope`; new fields are inside its value). The engine Python did change. The packaged lifecycle gate was **not** run for this commit in iteration 4 and has not been run since; the next engine or payload unit should rebuild, stage and run it.
- Reconcile: the critic asked for a reconcile with this record. Work iterations are forbidden to reconcile by the dispatch rules, so it is not run here. The tail is now four records (`terse-falcon-8320`, `happy-garden-2470`, this one, and the proxies record that follows), past the three-record trigger; the next reconcile pass should take it.

Dispatch closed: 1 unit — the missing record for ADR-413 (appearance roles and palette in xscript, carried into inventory, render and look)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: b8d61de0b88c4fd9a3f0ceb707b2a8671c1f2f9e

## State Impact

- target: warm-basin-7003 — xscript declares appearance roles (shell/mechanism/accent) per component and a palette per assembly, validated at declaration and absent from the digest when undeclared; inventory, render, look and review's render block carry them (ADR-413, b8d61de0); suites 2212/53 skipped and 980/1 skipped; packaged gate not yet run; the proxies remain
