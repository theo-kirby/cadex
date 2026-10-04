---
node_id: 47aabeba-c41a-5b90-adc7-caa7b9f2bd2f
slug: clear-current-6218
title: 'orun2 C1: report draft recorded; Fit and coverage leave world geometry out (ADR-525)'
created_at: '2026-10-04T05:32:08+00:00'
parents:
- solemn-birch-8260
summary: ''
---
## What

Two things, one record. (1) The record the critic asked for: iteration 52
drafted the C1 closing report (`docs/probes/orun2/REPORT.md`, commit
`90556e24`) with four dashboard screenshots, `report_shots.py` and
`report-shots.json`, and wrote no record. This record covers that draft.
(2) The unit: the report's defect 1 is fixed (ADR-525). The Model tab's Fit
now frames the design and leaves out the task floor. The model-pixel
coverage check leaves the floor out too. A browser test against a real
engine pins it. `dashboard-model.png` was re-taken and REPORT.md §5–§6
updated.

## Why

Target: `wild-ocean-3878` (C1), as the critic named. The critic asked for, in
order: a record for the C1 draft, then a reconcile, then defect 1, then
defect 3. **What I did instead of the reconcile and why:** this iteration's
dispatch rules say "Forbidden in a work iteration, no exceptions: the
hypergraph-reconcile skill". The dispatch's rules outrank a critic message,
so I did not reconcile. The tail is now three records (`neat-grove-1406`,
`solemn-birch-8260`, this one). That meets the charter's "three unreconciled
records" trigger, so the next pass should be the reconcile. The C1-draft
record is folded into this iteration's one record, not minted separately,
because the dispatch allows one record node. Defect 3 (a CLI turn's
transcript and `look` images on the project page) is the next unit and is
not started.

## Method

- Cause, re-measured: `c_floor` (a 1200 × 1200 × 2 mm slab) is a drawn
  component, and `review_scene.js::updateBounds` unioned every mesh. The
  engine already classifies it: the assembly output's `world_geometry` rows
  (`status: "world geometry"`) name it, the same source `film.py` and
  `CadexStudio.world` use.
- `review_server.world_components(result)` reads those rows from the
  accepted `result.json`. Each `api/model/accepted` component carries
  `world: bool`. No name inference.
- Viewer: `install` stores `userData.world`. `updateBounds` skips world
  meshes unless they are all there is. `modelPixels()` hides world meshes in
  the model render (only when a non-world mesh exists), then restores them.
  `stats().world` lists them. World parts are still drawn.
- `cli/tests/test_dashboard_fit.py`: a unit test of the row filter; a real
  engine builds a 60 × 40 × 30 body on a `world=True` floor; the manifest
  marks only `c_floor`; in headless Chromium after Fit, the bounds are
  [−30,−20,0]..[30,20,30], coverage is between 0.05 and 0.6 (measured 0.313),
  the box is inside the canvas and spans more than a quarter of it. With the
  viewer change stashed, the browser test fails.
- Re-ran `report_shots.py` on `orun2-w1-quad` (read-only).
- Docs: ADR-525, `docs/DASHBOARD.md` (the Fit paragraph), REPORT.md (§5 and
  defect 1), and the docstring of `report_shots.py`.

## Result

- Fit on `orun2-w1-quad` frames 178 × 151 × 123 mm (bounds min
  [−97.5, −75.5, 0.0], max [80, 75.5, 122.7]), the robot alone. Coverage is
  20.3% of an 822 × 723 canvas, box [169,196]–[652,627]. Before the fix it
  was 14.5%, and the box was the floor slab. `dashboard-model.png` (116,749
  B, dark floor) shows the quadruped filling the stage.
- The C1 draft stands as the critic graded it: measured numbers, images
  ≤300 KB, defects stated. Its open defects are now 3 (the CLI turn's
  transcript and `look` images on the page), 4 (preview lane NDJSON bar),
  5 (the W1 5090 leg is waiting on the owner's driver) and 6 (the
  installed footprint is unchanged).
- Suites: `pixi run test-engine` 2607 passed, 56 skipped. The CLI suite
  with the GPU hidden: 1415 passed, 1 skipped (22 min).
- Concern: run views built from rollout meshes alone (older runs with no
  retained training view) carry no `world` flag and still frame the floor.
  New walks copy the accepted manifest, so they are covered.
- No new dependency. The tail is 3 unreconciled records, so a reconcile is due.

Dispatch closed: 1 unit — Fit and the coverage check leave world geometry out (ADR-525), C1 draft recorded, report re-shot

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 90556e24cdf7b728699fd5c9a2839d2146ca09e9

## State Impact

- target: wild-ocean-3878 — C1 REPORT.md draft exists (iteration 52, 90556e24): D1 before/after, ledger summary, removals, latencies, dark-floor screenshots ≤300 KB, defects; defect 1 (robot a speck after Fit) fixed by ADR-525 and re-shot (20.3% coverage, bounds = robot); remaining defects 3–6
