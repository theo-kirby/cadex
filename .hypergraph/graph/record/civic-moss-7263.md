---
node_id: a442c762-4925-56ea-893c-6ee75d721653
slug: civic-moss-7263
title: Hide instanced assembly sources from camera renders
created_at: '2026-09-07T03:58:33+00:00'
parents:
- sunny-canyon-1138
summary: ''
---
## What

Hide instanced source solids and edge companions from camera renders with
independent ownership in cadex_hydrate. Add actual hydration/EEVEE regression
and update BLENDER, IDEAS, visibility audit, ADR-228 and ROADMAP checkbox.

## Why

Follow sunny-canyon-1138 and short item 2, targeting wild-comet-8096 as
mission 1 maintenance. Acquire ownership only for render flags changed from
false to true; preserve pre-hidden sources and unrelated explicit visibility.
The reversible assumption is to leave the legacy viewport policy unchanged.
Contributor rules forbid reconciliation despite the overseer's generic
request; leave the now-three-record tail for the separate maintainer pass.

## Method

Run the permanent test through a temporary runpy driver in the built Cadex
with build_app.sh exec, --background --factory-startup --python-exit-code 1.
Before editing the hydrator it exits 1 with raw-source camera pixels and
source render-hide failures; after editing it exits 0. Real sidecar buffers
hydrate source/ordinary/posed squares and their edges. Assert repeat hydration,
component removal, restored rendering, unrelated viewport/render/hide_set
choices and pre-hidden sources with/without legacy viewport markers.
Run full pixi run gate against changed source startup code and bundled engine.
Logs and PNG fixtures remain temporary outside git. No full build, GUI,
remote work, inherited changes, protocol or payload changes.

## Result

Old assembled camera source/ordinary/posed bands: 1024/1024/1024; fixed:
0/1024/1024. After removal and explicit ordinary hiding: 1024/0/0.
Full gate exit 0, ok true, engine_from_bundle true, 372/372 picks, slider
median 0.527 s against 0.65 s bar, model_objects_on_open 1. Regression covers
solid/edge flags and renderable posed components. Installed startup copy is
not refreshed; suite explicitly reloads source application code. Manual
render hiding while the hydrator already owns a true flag remains ambiguous;
legacy viewport restoration is unchanged. General headless review, video and
broader mission criteria remain open. Next: maintainer/planner consumes this
third unreconciled record and selects the next frontier unit; actor does not
reconcile or alter plan/state/charter. Git diff --check passes.
Dispatch closed: 1 unit — fix assembly source camera visibility with independent render ownership

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 9258f84d3f9b0486cfa1800d0e3857eba13d4cde

## State Impact

- target: wild-comet-8096 — Render visibility fix and old-source-failing hydration/EEVEE regression landed; full headless gate passes, qualifying criterion as working.
- target: shy-crane-2573 — Source render hiding owns false-to-true changes independently, preserving pre-hidden sources and unrelated visibility; full bundled-engine product gate green.
