---
node_id: d44289dc-a999-5028-9663-e5b1c3a61cf4
slug: eager-sage-0150
title: 'C1: closing report and one screenshot per layout preset'
created_at: '2026-10-06T20:53:08+00:00'
parents:
- cold-mist-9459
summary: ''
---
## What

C1's closing report, `docs/probes/orun4/REPORT.md`, and one PNG screenshot per D3 layout preset (`docs/probes/orun4/d3-preset-*.png`, eight files), commit `89e4cadd`.

## Why

The critic named C1 next: preset screenshots scripted through the layout presets, then REPORT.md from the existing records. **Deviation:** the critic also asked to reconcile first (fold `neat-isle-1523` and `cold-mist-9459`). This iteration's dispatch forbids the reconcile skill and state writes in a work iteration without exception, so I did not reconcile; the tail is now three records and a reconcile pass is due.

## Method

- A throwaway script outside the repo served `~/cadex-projects/orun4-biped-sts` (scratch copy) on 127.0.0.1 with `review_server.serve`, opened it in headless Chromium through `cadex_cli/browser.py` at 1280 × 800 in the dark theme, waited for the model to load, and for each of the eight presets clicked View → Layout → the preset button, waited 2.5 s and took a screenshot. It reset the layout at the end. The area editors were read back per preset: single [3D], side and stacked [3D, Status], 2-over-1, 1-over-2, columns and rows [3D, Status, 2D], quad [3D, Status, 2D, empty].
- I inspected the screenshots by eye. Every one is on the dark floor, and the sizes are 187,109 to 273,640 bytes, all ≤ 300 KB.
- I wrote REPORT.md in orun3's report form from these records: `loyal-path-4209` (F1), `true-ridge-9252` (F2), `lucky-peak-7846` (G1), the G2 chain, `tiny-ash-6709` (H1), `noble-vale-4742`, `peaceful-nest-6589` (H2), `frosty-cabin-1461` (H3), `glad-basin-7496`, `neat-isle-1523`, `cold-mist-9459` (D1 to D3) and the suite cuts (ADR-562 to ADR-564). It also uses `LESSONS.md`'s rows, recounted from the file, and ADR-558 to ADR-573's titles from `docs/DECISIONS.md`.
- I checked the run directory behind a defect seen in the screenshots: `runs/walk-r13` in the scratch copy.

## Result

What is true now:

- REPORT.md covers:
  - F1's before and after on the alpha-0.5 policy;
  - the G2 ledger summary: 25 rows. 16 went to the base, 7 to the style, 1 to a tool and 1 was not adopted. L4 and W1 are owner to confirm, and so is L5's reading.
  - both fresh-session checks;
  - H1's six before/after images, with pixel counts;
  - the H2 hero and print-bed stills and the H3 shove still with the push numbers;
  - D3's eight screenshots;
  - ADR-558 to ADR-573;
  - the remaining defects.
- The report claims no criterion, and it does **not** make the done claim. It names two things still due: the reconcile, and defect 1 below.
- **New defect found (report §7, defect 1):** a run recorded before ADR-559 still reads **failed**. In `orun4-biped-sts/runs/walk-r13`, `training-status.json` has `state: stopped` with the stop reason. But `run.json`, written 2026-10-06 01:35 by the pre-ADR-559 `loop._record`, has `status: failed`, and the Status editor shows the `failed` chip. It also shows "no telemetry update for over 30 s; process state unknown" under a run that ended long ago. ADR-559 fixed how new endings are written, but old records are neither re-read nor migrated. This is visible in every D3 screenshot. A candidate next unit: let the reader prefer a `stopped` `training-status.json` over a legacy `failed` `run.json`, with a test that fails without it.
- Gates: this is a docs-only change, so neither `test-engine` nor the full CLI suite was required or run. `test_project_docs.py`, `test_agent_guidance.py` and the licensing tests gave 53 passed and 1 skipped.
- No new dependency. No code, route, protocol op or tool schema changed.
- The tail is now three unreconciled records (`neat-isle-1523`, `cold-mist-9459`, this one), so a reconcile pass is due. It should fold D2 and D3 to working, and C1's report as written.

Dispatch closed: 1 unit — C1 closing report written and eight preset screenshots committed; a legacy stopped run reading failed found and named

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 89e4cadd5a91585fe00e5b93ecf4481bbc9f2349

## State Impact

- target: grand-ember-8938 — docs/probes/orun4/REPORT.md exists (commit 89e4cadd) covering F1 before/after, G2 ledger and both fresh sessions, H1 images, H2/H3 stills, eight D3 preset screenshots (≤300 KB, dark floor), ADR-558–573 and remaining defects; done not yet claimed — reconcile due and a legacy pre-ADR-559 run still reads failed
