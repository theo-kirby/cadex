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

- **Evaluating line (ADR-555, `29b63e45`)**: while a `cadex mcp` `evaluate` call is in flight, the reason is "the agent's evaluate call is running · <duration>" for the whole call, with the call's start as `since`, even after the evaluation writes its directory; a fresh evaluation directory with no call in flight reads "an evaluation is running". No directory id is ever shown. Chromium test in `test_review_overlay.py`; REPORT §5 defect 2 fixed [rec: empty-jasper-3681].
- **Phone width, both themes (ADR-556, `5dfa1f33`)**: at 390 px both scrubber sliders keep a 160 px floor (`--scrub`), `--tool` tall, with the label wrapping under: 287 px checkpoint and 303 px revision slider, measured in light and dark [rec: careful-lantern-1462].
- **Model status line (ADR-557, `e49f0394`)**: `#model-status` heads the viewport's bottom column (`.timelines`) on an opaque `--surface`, sized to its text. At 390 px with the overlay expanded it sits wholly below the overlay, at 5.04:1 contrast in light and 13.35:1 in dark. At desk width it moved from top left to bottom left. This closes the earlier open end where the overlay covered it and the light-theme `--warn` read about 3.3:1 on the dark floor [rec: lawful-delta-1655].
- Suites at `e49f0394` with the GPU hidden: `cli/tests` 1178 passed, 1 skipped; `test-engine` 2585 passed, 58 skipped [rec: lawful-delta-1655].

**Open ends**: ADR-555 is proved on a fixture, not re-walked on `orun3-biped` [rec: empty-jasper-3681]. A dead walk whose record stays `running` keeps the stage at `training`, with the stale warning showing [rec: snowy-lodge-1033]. Outside V1 but named in REPORT §5: the trainer's own 37–39 s progress stalls before each checkpoint (defect 3), and binary meshes, not started [rec: lawful-delta-1655].

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v1-3d-viewport-has-training)
- snowy-lodge-1033 — stage overlay landed (ADR-542); fixture browser test, 16.95% at 390 px, suites green
- forest-jasper-1180 — docs/CLI.md stage paragraph corrected to the ADR-542 overlay
- empty-jasper-3681 — ADR-555: evaluating line names the agent's evaluate call, never a directory id
- careful-lantern-1462 — ADR-556 recorded: 160 px scrubber floor at 390 px in both themes
- lawful-delta-1655 — ADR-557: model status line opaque, below the overlay, readable in both themes at 390 px
