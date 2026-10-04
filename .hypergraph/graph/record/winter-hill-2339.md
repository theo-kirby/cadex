---
node_id: 759d8e2d-9b72-5bfe-8794-2359937c484a
slug: winter-hill-2339
title: 'orun2 A1/W1: appearance roles and printable roster in the dashboard (ADR-522), record for iteration 47'
created_at: '2026-10-04T03:52:52+00:00'
parents:
- autumn-rose-7173
summary: ''
---
## What
Iteration 47's unit, committed as `63bcead7` ("ouroboros #47: no record") without a record; this node records it. The dashboard's viewer paints each part by its appearance role, and its parts list says which parts are printed, purchased and printable (ADR-522). `review_server.part_looks` colours each component with `CadexStudio.materials` — the same rule `look` and the concept sheet use: the declared role, else mechanism if purchased and shell if printed, in the assembly's palette. `api/model/accepted` gives each component `role`, `color`, `role_source`, `supplier` and `printable`, plus an `appearance` block. `CadexPrintables` is loaded beside `CadexStudio` in `cli/cadex_cli/studio.py`. The shell's printable ticks are dropped, because the printable-only export filter they fed was already dropped (ADR-509).

## Why
The critic's fix_first for iteration 48: write the missing record for ADR-522, parented to autumn-rose-7173, with both suites' results from the run that produced the diff. The unit itself closed the `cadex_roles.py`, `cadex_print.py` and Parameters-editor rows of the parity ledger, which serves A1 (printable-part and appearance-role display) and W1 (no row may still say "to port").

## Method
- Diff as committed: `review_server.py` +64, `review.js` +28, `review_scene.js`, `studio.py`, the new `cli/tests/test_dashboard_parts.py` (122 lines), `test_review_server.py`, `docs/DASHBOARD.md` §30, `docs/DECISIONS.md` ADR-522, and `docs/SHELL-PARITY.md`.
- Iteration 47 kept no suite output, so iteration 48 re-ran both suites on exactly the `63bcead7` tree before changing anything, with the existing engine build: `pixi run test-engine`, and `pixi run python -m pytest cli/tests -x` with `CUDA_VISIBLE_DEVICES=""`.

## Result
True now: the appearance-role and printable-part display is ported, with a test against a real engine (`cli/tests/test_dashboard_parts.py`). It checks roles, colours, suppliers and the roster against `inspect scope=inventory` and the script's printable roster, and headless Chromium shows each part's role, swatch and status.

Suite results on `63bcead7`, re-run in iteration 48: `pixi run test-engine` 2607 passed, 56 skipped (7 min). `pixi run python -m pytest cli/tests -x` with the GPU hidden: 1404 passed, 1 skipped (21 min).

Concern: these numbers come from a re-run of the committed tree, not from iteration 47's own run, because that run left no output.

Dispatch closed: 1 unit — missing record for iteration 47's ADR-522 (appearance roles and printable roster in the dashboard), with re-run suite results

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 63bcead7ef51cd48667148670ae716c1fb9df1a1

## State Impact

- target: shady-clover-5534 — the cadex_roles.py, cadex_print.py and Parameters-editor parity rows are ported (ADR-522, cli/tests/test_dashboard_parts.py, a real engine plus headless Chromium); on 63bcead7 test-engine gave 2607 passed/56 skipped and cli/tests gave 1404 passed/1 skipped; still to port: agent.py cost/text-tool-call warning, cadex_dimension.py viewer overlay
