---
node_id: 5ce7b0e3-2bd1-524c-8be0-1905f119f713
slug: neat-grove-1406
title: 'orun2 W1/D2: declared dimensions drawn in the viewer (ADR-524); last to-port ledger row ported'
created_at: '2026-10-04T04:53:33+00:00'
parents:
- copper-cliff-1990
summary: ''
---
## What

The missing record for ADR-524 (commit `9fc13812`, iteration 50, which landed
as "ouroboros #50: no record"): the dashboard's viewer draws the script's
declared `part.measurement` dimensions over the solids. This ports the last
"to port" row of the shell parity ledger, `cadex_dimension.py`'s in-viewer
overlay (D2.5). The drawing-sheet half was already ported by ADR-516.

## Why

The critic's verdict on iteration 50 asked for it first. The change was
accepted, but no record was minted and the actor's final message was empty, so
W1 (`shady-clover-5534`) still listed the row as blocking.

## Method

- **Code (`9fc13812`):**
  - `review_server.declared_measurements` reads the records from the accepted
    `result.json`. Nothing is measured or rebuilt. It attaches each record to
    the component that shows its output, and `api/model/accepted` carries
    them as `measurements`.
  - `review_static/dimensions.js` draws them as an SVG over the canvas.
    Anchors go through the new `viewer.toScreen(component, point_mm)`.
    Everything else is laid out in pixels: a leader under a 12 px span, the
    widest on-screen diameter for a circle, and an arc for an angle.
  - A `setOnDraw` hook redraws the overlay every frame, so it follows the part
    through explode and playback.
  - A record on an undeclared intermediate is listed and not drawn, the same
    rule the sheet uses.
  - Spec in `docs/DASHBOARD.md` §31. Ledger row and summary in
    `docs/SHELL-PARITY.md`.
- **Licensing:** read from `v1-blender-shell` as a description only. Nothing
  copied, and no new dependency.
- **Tests:** `cli/tests/test_dashboard_dimensions.py`, three tests:
  - attaching records to components (pure);
  - the manifest carries the engine's numbers in the part's frame (real
    engine);
  - `test_browser_draws_each_declared_dimension_where_the_solid_is` (real
    engine and headless Chromium).
  - The same commit made `test_dashboard_inspect.py`'s rollout-playback test
    wait until `#play-toggle` is enabled, which fixes the timing flake
    copper-cliff-1990 reported.
- **Suites, run this iteration on `9fc13812` (tree unchanged since):**
  - `pixi run test-engine`: **2607 passed, 56 skipped**, exit 0;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests -x`: **1412
    passed, 1 skipped**, exit 0, in 21 min. That includes the
    rollout-playback test that flaked on `2f40027d`.

## Result

- The parity ledger has **no "to port" row**. The summary is:
  - §1: 47 rows, 0 still to port, 2 owner to confirm;
  - §2: 23 rows, 0 still to port;
  - §3: 7 rows, 0 still to port.
- The two "owner to confirm" rows are face-level pins and the face-ID channel.
  They stay with the owner. The critic's "pick two faces and show the
  distance" framing belongs to that row, not to this port (ADR-524 Context).
- The rollout-playback flake did not recur in a full CLI run.

Dispatch closed: 1 unit — ADR-524 recorded with suite evidence; W1's ledger has no open "to port" row

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 9fc1381218c7b96234baba408dab29debd9c6271

## State Impact

- target: shady-clover-5534 — cadex_dimension.py viewer overlay ported (ADR-524, cli/tests/test_dashboard_dimensions.py incl. a browser test); ledger has 0 'to port' rows (2 owner-to-confirm face rows remain); rollout-playback flake fixed by waiting for #play-toggle; suites on 9fc13812: test-engine 2607 passed/56 skipped, CLI (GPU hidden) 1412 passed/1 skipped
