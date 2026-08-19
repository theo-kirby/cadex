---
node_id: f8bc1fc9-e569-5a9a-9c9a-f07d2ff2d7e2
slug: windy-wolf-5012
title: 'ADR-150: blueprint mode — the view, the sheet, the store, and the view registry'
created_at: '2026-08-19T18:41:52+00:00'
parents:
- zesty-cove-4881
summary: ''
---
## What

Blueprint mode (ADR-150), end to end, in two mechanisms plus the refactor
that carried them. (1) `mesh_agent/cadex_views.py` — a registry for the
five presentation views (collision 20, section 30, explode 40, dimensions
50, blueprint 60) replacing five copies of hand wiring at
`cadex_backend.hydrate`, `_finish_preview` and `capture.render_views`;
per-record try/except preserves each view's stated failure terms, and
`suspend_for_render()` returns one undo unwinding in reverse order. (2)
`mesh_agent/cadex_blueprint.py` — the model as white outlines on a
blueprint-blue / cutting-mat-green / grey ground, live in the viewport:
one field table (`shading_values`, 31 dotted RNA fields) written to
`space.shading`/`space.overlay`, the replaced look captured on the scene
and restored exactly on toggle off; layers over section and explode by
construction. (3) The sheet: `capture.render_blueprint` renders the four
fitted views in that style — deliberately NOT suspending section/explode
(it draws the current presentation; the contrast with `render_views`) —
and `make_blueprint` stores the PNG through a new `put_blueprint` op.
`CadexBlueprints.py` files it as `blueprints/{ordinal:04d}-{rev[:12]}.png`
+ `blueprints.json` (schema cadex-blueprint-v1, newest 25 kept), each
entry attached to the accepted `(revision, digest)` pair; `inspect
scope=blueprint` lists entries and serves a containment-checked store
path, never pixels. The CLI serves the scope and `export --blueprints`
copies sheets out; `put_blueprint` stays out of `CLI_TOOL_OPS` (nothing
headless can render one).

## Why

The user asked for a blueprint view mode and an agent-makeable blueprint
sheet stored as a first-class project artifact — never inside `script.py`.
Everything the view needs survived the Blender fork ON (Workbench flat
shading, `background_type='VIEWPORT'`, `show_object_outline`, the true-BREP
`… Edges` children), so white outlines cost zero inherited-tree lines;
Freestyle/EEVEE were rejected as slow, offline-only, deletion-candidate
code. The registry exists because a sixth hand-wired view is how the sixth
one gets wired wrong.

## Method

Five slices, each verified before the next: registry refactor proven
no-behavior-change by the untouched gate; the view module in the ADR-148
template (pure half / bpy half); the engine store on
`store_project_asset`/`record_history` idioms; the sheet renderer; the CLI
reach. Two load-bearing facts verified in source first:
`overlay_wireframe.hh:54` (the Edges wires only draw with overlays ON, so
the blueprint pins every sub-overlay explicitly) and
`CadexdProtocol.py` store ops transfer by path, not bytes (8 MB frame cap).
Verification: `pixi run test-engine` (1869 passed, 33 skipped), packaged
lifecycle gate against the staged payload
(`CADEX_ENGINE_ROOT=… pytest test_cadexd_lifecycle.py`, 14 passed —
ADR-023), `pytest cli/tests` (83 passed), the pure shell suite and
`pixi run gate` (ok, `"blueprint": {"fields": 31}`), a windowed visual
probe against the launched bundle (12/12 checks: sheet rendered and
stored, entry attached to the accepted revision, exact viewport restore,
accepted revision unchanged — probe not committed, the ADR-124 precedent),
and a manual `./cadex export --blueprints` copying the probe's sheet.

## Result

Shipped and green everywhere. Membership calls: `put_blueprint` is
MODELING (store write, serial with rebuilds) but does NOT invalidate
resident workers — a blueprint documents a run, never feeds one;
`make_blueprint` is `_ENGINE_TOOLS`-only; `blueprint_view` is in neither
set. One bug the gate's exact-restore assertion caught: the first
`clear()` restored the fallback product look even when the blueprint had
never been applied, so a theme write with the view off stomped the
viewport and the toggle-on captured the stomp as "the look to restore" —
a clear with neither scene flag now touches nothing. One cosmetic noted:
the Edges wires render faintly warm under the view transform; accepted.
`_present_model` also gained the `background_type` restore it always
saved and never applied. ADR-150 in docs/DECISIONS.md; INTEGRATION (both
test-enforced tables), ARCHITECTURE, CLI, BLENDER, ROADMAP updated.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 14605eb53a0601686d802eb3e40e2f0183118831

## State Impact

- target: shy-crane-2573 — mesh_agent's presentation views are registry-wired (cadex_views.py: collision/section/explode/dimensions/blueprint in order 20..60, one suspend-for-render undo) and gain the blueprint view (ADR-150): white outlines on a blueprint/cutting-mat/grey ground as pure per-space shading+overlay state with exact capture/restore, layering over section and explode; blueprint_view and make_blueprint agent tools; render_blueprint draws the current presentation where render_views reassembles
- target: forest-wind-0342 — the project store gains blueprints/ (CadexBlueprints.py, cadex-blueprint-v1): put_blueprint stores a shell-rendered PNG sheet attached to the accepted (revision, digest) pair, MODELING but invalidating no resident worker, path-not-bytes; inspect scope=blueprint serves entries plus a containment-checked path, never pixels; newest 25 kept
- target: chilly-union-8972 — the CLI serves inspect scope=blueprint and export --blueprints copies stored sheets out under store names; put_blueprint deliberately absent from CLI_TOOL_OPS because nothing headless can render a sheet
