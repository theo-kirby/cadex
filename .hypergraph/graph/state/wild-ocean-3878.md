---
node_id: 3a551f68-0fc8-5168-bbdb-c3b7f37699de
slug: wild-ocean-3878
title: C1. Closing report (orun2)
created_at: '2026-10-03T10:54:47+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Open charter criterion for run orun2: **C1. Closing report.** - `docs/probes/orun2/REPORT.md` covers: - D1's before and after numbers; - the parity ledger summary; - every removal and its ADR; - D2's latencies; - screenshots of the dashboard (PNG, ≤300 KB each, on the dark floor); - the remaining defects. - Reconcile, then claim done for critic review without ticking the owner boxes. [rec: winter-stone-5109]

**Draft exists (`90556e24`, iteration 52).** `docs/probes/orun2/REPORT.md` covers D1 before and after, the ledger summary, removals, latencies, the dark-floor dashboard screenshots (≤300 KB each, from `report_shots.py` / `report-shots.json`) and the defects. The critic graded it as having measured numbers and stated defects [rec: clear-current-6218].

**Defect 1 fixed (ADR-525).** The robot was a speck after **Fit**. The cause was that `review_scene.js::updateBounds` unioned the task floor `c_floor`, a 1200 × 1200 × 2 mm slab. The fix:
- `review_server.world_components` reads the engine's `world_geometry` rows from the accepted `result.json`, and each `api/model/accepted` component carries `world: bool`. There is no name inference. [rec: clear-current-6218]
- Fit and `modelPixels()` coverage leave out world meshes, unless world meshes are all there is. World parts are still drawn. [rec: clear-current-6218]

`cli/tests/test_dashboard_fit.py` covers it with a real engine in headless Chromium: bounds [−30,−20,0]..[30,20,30], coverage 0.313. The browser test fails with the viewer change stashed. On `orun2-w1-quad`, Fit now frames the robot alone, 178 × 151 × 123 mm, at **20.3%** coverage, up from 14.5% when it framed the floor. `dashboard-model.png` (116,749 B) was re-shot and REPORT.md §5–§6 updated. Suites on that tree: `test-engine` 2607 passed / 56 skipped; CLI with the GPU hidden, 1415 passed / 1 skipped [rec: clear-current-6218].

**Open defects in the report** [rec: clear-current-6218]:
- 3: a CLI turn's transcript and `look` images do not appear on the project page. This is the next unit, not started [rec: clear-current-6218].
- 4: the preview lane's NDJSON bar [rec: clear-current-6218].
- 5: the W1 5090 leg is waiting on the owner's driver (see `shady-clover-5534`) [rec: clear-current-6218].
- 6: the installed footprint is unchanged [rec: clear-current-6218].

Known gap in the ADR-525 fix: run views built from rollout meshes alone (older runs with no retained training view) carry no `world` flag and still frame the floor. New walks copy the accepted manifest, so they are covered [rec: clear-current-6218].

Reconcile judgement: flipped `open` → `working`, since the criterion now has measured evidence. It is not claimed. The report still carries defects 3–6, and the "claim done for critic review" step has not been taken. This pass is the reconcile the criterion asks for before that claim [rec: clear-current-6218]. Declared target: `gap-c1-closing-report-docs-probes`. The human owns the charter checkbox, and every orun2 gap title carries the run [rec: winter-stone-5109].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- clear-current-6218 — REPORT.md draft (90556e24) recorded; defect 1 fixed by ADR-525 (Fit/coverage skip world geometry), report re-shot
