---
node_id: 4fe3c842-c371-5046-8170-2af815454b15
slug: upright-glacier-1185
title: 'GUI parity slice 3a: the fit and inventory blocks are engine code, built beside the service (ADR-447)'
created_at: '2026-09-29T10:57:47+00:00'
parents:
- strong-sail-2579
summary: ''
---
## What

GUI-parity slice 3a (ADR-447): the pure functions that turn the published `inspect scope=clearance` and `scope=inventory` values into the `fit` and `inventory` blocks every build reply carries — `fit_summary` (with `sweep_summary`, `attachment_summary`, `pair_status`), `inventory_summary`, `printed_edges`, their thresholds and source notes — and the bounded model views of both blocks (`fit_view`, `inventory_view`, `_cut`, `_worst_first`, ADR-435), moved unchanged from `cli/cadex_cli/{clearance,inventory,bridge}.py` into `src/Mod/cadex/CadexFitReport.py`. `CadexStudio`'s process entry accepts the raw values (`clearance`, `inventory_value`) and gains `kind: "blocks"`.

## Why

The app's agent gets no `fit` block: the CLI bridge builds it, not the engine. ADR-346 made that block the evidence that a design fits; a second implementation in the GPL shell would be a second source of that truth. The shell already reads paged inspect values (`cadex_backend._inspect_full`) but may not import engine code, so it gets the blocks through slice 1's child process. An `inspect scope=fit` served by cadexd was rejected: a protocol scope, and the loss of the CLI's read-time thresholds.

## Method

Moved by script; the CLI binds the same names from the engine module it loads by path (`studio.FIT_REPORT`), so every CLI caller and test is unchanged. `outputs_view` stays in the bridge (it is the CLI's reply shape). A malformed raw value is refused as a result (`blocks: malformed inspect value: KeyError …`). New process tests in `cadex_tests/test_studio_process.py`: blocks from raw values equal the in-process blocks and views; a look from raw values leaves the floor out and returns its blocks; a malformed value is refused; neither module is in the service closure; both are installed.

## Result

Payload ships `Mod/cadex/CadexFitReport.py`; its `bin/python` answers `kind: "blocks"`. Engine suite 2292 passed, 54 skipped. CLI suite 52 failed / 1026 passed / 2 skipped / 7 errors, failure list identical to slice 2's (browser tests only).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: gui/fit-in-engine
- commit: 391caf4f65252ca51d908148749bfb73649ed24c

## State Impact

- target: forest-wind-0342 — the engine owns the fit and inventory blocks and their bounded model views (CadexFitReport.py, ADR-447); a client that cannot import engine code gets them from CadexStudio's process entry (kind blocks, or raw values on a look)
- target: chilly-union-8972 — the CLI's fit/inventory blocks and their model views are the engine's CadexFitReport, bound by name; the CLI keeps the paged reads and markdown reports
