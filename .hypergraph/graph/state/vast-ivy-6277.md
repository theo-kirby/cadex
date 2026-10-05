---
node_id: 08ae7ed9-504c-52d2-be6a-f83e8d0a067a
slug: vast-ivy-6277
title: V1. The 3D viewport has a training and stage overlay
created_at: '2026-10-05T08:57:45+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun3: **V1. The 3D viewport has a training and stage overlay.** It shows stage (idle / designing / training with iteration, total and ETA / evaluating / failed), reward and loss sparklines from `progress.json`, the best reward and its iteration, `progress.json`'s `warning`, and which run it is reading. It updates on the existing poll, collapses per browser, covers ≤ ¼ of the viewport at 390 px, has hooks in `docs/DASHBOARD.md` §2 pinned by `test_review_design.py`, and an ADR as the first panel back after ADR-533 [rec: golden-snow-6627]. The human owns the checkbox.

**Met on fixture evidence; live 5090 demonstration is W1's** [rec: snowy-lodge-1033] (ADR-542, commit `e3b1ffa4`). Reconcile judgement: status `working`, because every listed criterion has evidence. The live run on the 5090 is the charter's W1, not part of V1.

- `/api/project` gains one bounded `stage` block, on the same request and the same poll. This departs from "reads only what /api/project already carries", because the run summary had no curves, best reward, ETA or warning (ADR-321), and `/api/run/<name>` hashes every checkpoint per call [rec: snowy-lodge-1033].
- Stage precedence: evaluating > training (incl. stale) > failed (only if no revision accepted since) > designing > idle. The read run is the newest running/pending run with telemetry `starting`/`training`/`stale`, else `default_run` [rec: snowy-lodge-1033].
- A Chromium test follows `progress.json` rewrites on the page's 2 s poll with no reload. It covers the iteration line (40/240 → 160/240), the reward sparkline, the best reward, the ETA, and the warning in `--warn`. When the run finishes, the run line reads `· done` [rec: snowy-lodge-1033].
- **390 px: expanded 280 × 171 on 390 × 724 = 16.95%** (bound 25%). Collapsed it is 40 px tall and survives a reload [rec: snowy-lodge-1033].
- Suites with the GPU hidden: `test-engine` 2585 passed, 58 skipped; `cli/tests` 1129 passed, 1 skipped [rec: snowy-lodge-1033].
- `docs/CLI.md` §`/api/project` now describes the ADR-542 overlay reading `stage`, not ADR-533's removed telemetry panel. `/api/run/<name>` is fetched only for the 2D viewport's curve [rec: forest-jasper-1180].

**Open ends** [rec: snowy-lodge-1033]: at phone width with no model loaded, the overlay covers part of `#model-status` (cosmetic, phone/light rung). The light theme is unmeasured (tokens only). A dead walk whose record stays `running` keeps the stage at `training`, with the stale warning showing.

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v1-3d-viewport-has-training)
- snowy-lodge-1033 — stage overlay landed (ADR-542); fixture browser test, 16.95% at 390 px, suites green
- forest-jasper-1180 — docs/CLI.md stage paragraph corrected to the ADR-542 overlay
