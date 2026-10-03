---
node_id: 88ba958a-25aa-5ca5-a6b2-71e6334426c5
slug: sweet-arrow-0695
title: 'orun2: the blueprint composer, headless — draw_blueprint and a Drawings panel (ADR-516)'
created_at: '2026-10-03T23:44:15+00:00'
parents:
- placid-glade-3519
summary: ''
---
## What

The blueprint composer, kept by the owner as a headless tool (orun2 owner
notes, 2026-10-03), is re-derived in the engine's renderer and given to the
product agent as the bridge tool `draw_blueprint` (ADR-516).

- `src/Mod/cadex/CadexStudio.py`: `blueprint_recipe` (validated recipe:
  name, views, callouts, dimensions, notes), `blueprint_sheet` and
  `blueprint_report`. The sheet is a 1536×1024 PNG on the dark floor. It has
  up to four line views on **one shared scale**; the default is top, iso,
  front, right, the third-angle arrangement. Each orthographic view shows
  the overall extents. Each declared `part.measurement` record is drawn once,
  in the first orthographic view where it reads, or only listed when the
  design places components. Numbered balloons go on the three-quarter view
  and are keyed in a parts list. The sheet also has notes and a title block:
  name and version, project, revision, digest, date, scale and units.
  `Canvas.line` and `line_view(bounds=...)` support it.
- `cli/cadex_cli/bridge.py` / `tools.py`: `draw_blueprint` draws from the
  same accepted reply `look` uses and stores the sheet through the existing
  `put_blueprint` op, versioned by name, with the recipe in `meta`. A redraw
  under a stored name is the next version and takes any omitted key from the
  stored recipe. The rebuild-once logic is factored into `_accepted_reply`
  and shared with `look`.
- Dashboard: `review_server.blueprint_listing` adds `drawings` to
  `/api/project` and a `blueprint/<file>` route that serves only the files
  the index names. The page has a **Drawings** panel listing every version
  newest first, with the newest shown and each one downloadable.
- Docs: ADR-516; `docs/CLI.md` (tool section, limits, `--blueprints`);
  `docs/DASHBOARD.md` §2 row 0e and §28; `docs/ARCHITECTURE.md`. In
  `docs/SHELL-PARITY.md`, the `cadex_sheet.py`, `make_blueprint` and
  `save_blueprint` rows are **ported**, and the `cadex_drawings.py` and
  Blueprint editor rows are **ported** as stored sheets shown as outputs.
  `cadex_blueprint.py` themes are dropped (one dark-floor theme), and
  `capture.py` sheet rendering is ported. The `inspect scope=blueprint` note
  now names `draw_blueprint`, not the shell's `make_blueprint`.
- `docs/probes/orun2/blueprint-bored-plate.png` (21 KB) is the
  real-engine sheet.

## Why

The critic's message and the owner's iteration-32 note both said to land
the blueprint composer as its own unit before any more D3 work. This unit
does exactly that. It serves W1 (`shady-clover-5534`): the parity ledger's
blueprint rows needed a tested "ported". The project-budgets unit is next,
as the owner note orders.

## Method

- Read `v1-blender-shell:shell/scripts/startup/mesh_agent/cadex_sheet.py`
  as reference only: its docstring, the shape of the spec, the dimension and
  callout logic, and the title lines. No line was copied, and every layout,
  placement and title-block decision is new code.
- Reused the engine's existing store (`CadexBlueprints`, ADR-150/157),
  `put_blueprint`, `inspect scope=blueprint` and `export --blueprints`
  unchanged, so `OP_ARG_SPECS` and `docs/INTEGRATION.md` do not move.
- Engine-side so the sheet shares the concept sheet's palette, 5×7 face
  and line pass; pure standard library.
- Inspected the rendered sheets by eye. That inspection found and fixed a
  `?` for the engine's `Ø` sign and declared dimensions drawn over the
  outline; they are now lifted above or left of it.

## Result

- **True now:** the agent can compose a dimensioned multi-view drawing sheet
  headlessly. It is versioned with the project in `blueprints/` and shown in
  the dashboard under Drawings.
- **Tests:** `cli/tests/test_blueprint.py`, 7 tests:
  - recipe refusals;
  - shared scale and overall extents;
  - declared measurements drawn or listed;
  - a placed design lists its measurements;
  - the bridge stores and revises by name;
  - the listing allowlist;
  - **headless Chromium against a real engine**: a bored plate with 60/40/10
    mm extents and both measurements drawn, revised to v2, listed newest
    first, the newest shown at 1536 px and downloaded byte-identical.
  
  `test_project_tool_surface.py` pins `draw_blueprint` in `BRIDGE_TOOLS`
  and its schema. `test_review_design.py` HEADINGS gains "Drawings".
- **Gates:** `pixi run test-engine` gave 2593 passed and 56 skipped.
  `pixi run build-engine` ran and synced the built tree. The full `pixi run python -m pytest cli/tests` (GPU hidden, after the build) gave 1371 passed and 1 skipped. The skip is `test_review_server.py:851`, which needs `CADEX_REVIEW_HOST`, an environmental setting. On the first run, `test_review_design` failed until
  "Drawings" was added; that file then passed, 135 tests.
- **Packaged gate not run:** no protocol or payload change. `CadexStudio.py`
  is staged by `stage-engine` like any engine module.
- **Assumptions:**
  - Measurements on a placed design are listed, not drawn, because the
    record does not name its part.
  - Layouts are only 1, 2 and 2×2.
  - The agent overlay (`CLI_OVERLAY`) was left unchanged; the tool
    description carries the guidance.
- **Unreconciled tail:** one record (this one), not fat.

Dispatch closed: 1 unit — the blueprint composer, ported headlessly as `draw_blueprint` with a Drawings panel (ADR-516)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 2731e163cc129fb769ed2e1a90a40eeba23fc04c

## State Impact

- target: shady-clover-5534 — the parity ledger's blueprint rows are ported with tests: cadex_sheet.py, make_blueprint and save_blueprint as the agent's draw_blueprint (CadexStudio.blueprint_sheet, stored through put_blueprint and versioned by name); cadex_drawings.py and the Blueprint editor as stored sheets shown under the dashboard's Drawings (ADR-516, cli/tests/test_blueprint.py incl. a real-engine headless-Chromium test)
