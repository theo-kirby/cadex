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

**Defect 3 fixed (ADR-526).** A turn started at a terminal now shows its stored transcript and `look` images on the project page, through the turn store; a real-engine Chromium test covers a terminal turn. Suites with the GPU hidden: engine 2607 passed / 56 skipped, CLI 1420 passed / 1 skipped [rec: lively-beacon-5538].

**Defect 4 closed (ADR-527).** A preview skips the static and swept fit: preview median 0.0435 s against the 0.10 s bar, `ok: true`, pinned by `test_preview_skips_fit.py`. Engine 2608 passed / 56 skipped, CLI 1420 passed / 1 skipped, packaged gate 24 passed / 0 skipped [rec: clever-sky-3211].

**Refreshed at `37733eec`.** Each criterion in REPORT.md names its evidence records. S1, R1, D1, D2, D3 and A1 have recorded evidence, and W1 now does too, the GPU half of step 7 included [rec: rough-bell-4055]; D1/D2 numbers stand from `13c660cf` (no later commit touches build, setup or slider path). Docs-only change: CPU-only `cli/tests -k "doc or report or probe or fit"` 326 passed, `test-engine -k doc` 19 passed [rec: hidden-glacier-9870].

**Defect 5 cleared (`a320a489`).** The W1 5090 leg ran: `w1-gpu-1` trained on the GPU, and evaluate passed 10/10 seeds (see `shady-clover-5534`). REPORT's W1 row, defect 5, §7 and its header carry the measured result [rec: rough-bell-4055].

**Done claimed for critic review (`fd71b598`, branch `ouroboros/orun2`).** After reconcile `3d0c6faa` folded `rough-bell-4055`, `snowy-beacon-2710` and `empty-heron-1077`, REPORT §7 claims done again and re-checks each criterion against its folded state node; the C1 row says done is claimed; no owner box is ticked. Checks at the claim: `git ls-files shell` empty, all eight orun2 criterion nodes `working`, `hypergraph check` exit 0, `test_project_docs.py` 40 passed (docs-only change) [rec: civic-prairie-1265]. An earlier claim had been withdrawn because it came before this reconcile [rec: snowy-beacon-2710] [rec: empty-heron-1077].

**Open defects in the report:** 6, the installed `.pixi` footprint is unchanged, deferred by the owner to the next run [rec: clear-current-6218] [rec: civic-prairie-1265]; 7, plan bet `young-crane-9546` rank 1 still says "the shell client", pending `light-path-5130`'s plan impact — planner-owned, not a criterion [rec: civic-prairie-1265].

Known gap in the ADR-525 fix: run views built from rollout meshes alone (older runs with no retained training view) carry no `world` flag and still frame the floor. New walks copy the accepted manifest, so they are covered [rec: clear-current-6218].

Reconcile judgement: status stays `working`. Done is claimed for the critic; the owner holds the charter checkbox. Neither open defect holds a criterion [rec: civic-prairie-1265]. `snowy-beacon-2710` had declared its impact on orun1's `gentle-bramble-6120`; `empty-heron-1077` corrected it to this node, and `gentle-bramble-6120` keeps its claims [rec: empty-heron-1077]. Declared target: `gap-c1-closing-report-docs-probes` [rec: winter-stone-5109]. Later the same day the owner took Ouroboros out of the product (ADR-536), which retires D2, D3 and part of A1 rather than ticking them; REPORT.md predates that [rec: still-ivy-2146].

## Negative knowledge

None yet.

## Provenance

- winter-stone-5109 — orun2 operator-declared charter gap
- clear-current-6218 — REPORT.md draft (90556e24) recorded; defect 1 fixed by ADR-525 (Fit/coverage skip world geometry), report re-shot
- lively-beacon-5538 — defect 3 fixed by ADR-526 (terminal turns keep transcript and looks on the page)
- clever-sky-3211 — defect 4 closed by ADR-527 (preview skips static and swept fit); open defects now 5 and 6
- hidden-glacier-9870 — REPORT.md refreshed at 37733eec with per-criterion records; defect 5 re-checked as sole blocker; done claimed for critic review
- rough-bell-4055 — defect 5 cleared: W1 5090 leg trained and evaluate passed 10/10
- snowy-beacon-2710 — REPORT §7 withdrew the done claim pending the reconcile (impact misnamed gentle-bramble-6120; folded here)
- empty-heron-1077 — corrected the C1 target to this node; re-claim follows this reconcile
- civic-prairie-1265 — done re-claimed for critic review at fd71b598; defects 6 and 7 remain
- still-ivy-2146 — Ouroboros out of the product the same day; D2/D3/A1 retired, not ticked
