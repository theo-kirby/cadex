---
node_id: 6f32bb78-5df4-5e3c-a80f-a54474d0a639
slug: polished-lodge-7956
title: 'orun2 D2 item 6: export STEP and STL from the dashboard through cadex export, and download the concept sheet (ADR-509)'
created_at: '2026-10-03T19:32:00+00:00'
parents:
- calm-falcon-6751
summary: ''
---
## What

orun2 D2 item 6: export STEP and STL, and download a concept sheet, from the
dashboard (ADR-509). A fifth dashboard write, `POST api/export`
(`review_server.write_export`), runs `cadex export --project <root> --out
<root>/review/export/<revision> --format step,stl --json` as a child behind
the per-launch token and `Origin` check. `api/project` gains an `exports` block
(`review_server.export_listing`) that lists the accepted revision's exported
files. The route `export/<revision>/<name>` serves only the files that listing
names. The page gains `#export-panel` (button, status, `#export-list
li[data-name]` download links). The concept sheet was already a download
(`#concept-download`, ADR-430); this unit proves it in the browser.

## Why

The critic's message named this unit: D2 item 6, the last D2 item not yet
started, with writes through the CLI export path (A3), behind the token, and
proved by a headless-Chromium test against a real engine that checks the
downloaded bytes. I did that unit and nothing else.

## Method

- Server: `write_export` checks the formats (a list drawn from step/stl/brep,
  no duplicates) and needs an accepted revision (409 otherwise). It names the
  output directory by the revision accepted at the moment of the request and
  runs the CLI through `run_leg`, the way `write_params` does. If the child's
  envelope reports a different `accepted_revision` (a write landed before it
  took the lock), the directory is removed and the reply is 409 "export
  again". The output lives under `/review/`, which the project's own
  `.gitignore` already excludes from project commits. Suffix allowlist:
  .step .stl .brep .xml .json .ply. CONTENT_TYPES gains `.step` and `.brep`.
- Page: `renderExports` / `writeExport` follow the revision panel's idiom;
  `window.cadexReview.exportModel` and `lastExport` are exposed for tests.
- Docs: DASHBOARD.md §23 and the hierarchy row 0d; SHELL-PARITY.md
  (`cadex_backend.py` export → ported D2.6; `topbar.py` Export Printable
  Parts → ported as whole-design export, with the printable-only filter
  dropped under ADR-509); ADR-509 in DECISIONS.md.
- Tests: `cli/tests/test_dashboard_export.py` (4 tests). Without an engine
  they cover the token/Origin/body guard, the exact argv, the listing
  allowlist, 404s for unlisted, other-revision and traversal names, the
  moved-revision cleanup, and the no-accepted-revision case. One headless
  Chromium test runs against the real dev-tree engine: `cadex render`, then
  a click on Export, then real browser downloads (CDP `Browser.downloadWillBegin`)
  of `plate.step` (ISO-10303-21 header and trailer, B-rep entity),
  `plate.stl` (12 facets, extents exactly 30×20×6 mm) and the concept sheet
  (PNG signature and IHDR, byte-identical to `review/render/sheet.png`).
  `test_review_design.py`'s pinned heading list gains "Export".

## Result

Verified: `pixi run test-engine` 2592 passed, 56 skipped; `pixi run python -m pytest cli/tests` with the GPU hidden, 1339 passed, 1 skipped (the browser and real-engine tests ran; the first full run caught `test_review_design.py`'s pinned heading list, which was fixed and rerun green). The new file is 4 passed against the dev-tree engine with headless Chromium.

D2 item 6 now has its browser-driven proof against a real engine. Of D2's
items, only item 5's section view, exploded view and rollout playback remain,
one per unit (per the critic). Concerns for the next iteration:

- Exports for earlier revisions stay on disk under `review/export/` until the
  project is cleaned. They are git-ignored and not served.
- The printable-only export filter is dropped (ADR-509). The owner can
  reverse that with a `printable` format on `cadex export`.
- Stored blueprint sheets as outputs (the blueprint-composer owner note) are
  still "to port" in the ledger. That is a separate unit.
- No protocol, payload or engine change, so the packaged gate was not rerun.
- The tail now holds 3 unreconciled records (sweet-mist-9111,
  calm-falcon-6751, this one), which meets the charter's three-record
  reconcile trigger. A reconcile pass is due; this work iteration did not run
  one.

Dispatch closed: 1 unit — dashboard Export (STEP/STL via `cadex export`) and concept-sheet download, browser-proved against a real engine (ADR-509)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: fd1f9f5c15d9f11b9c56ea8d0910563b66358c9c

## State Impact

- target: twilight-aspen-1541 — item 6 proved: the dashboard's Export runs cadex export (ADR-509) into the ignored review/export/<revision>/, behind the token; a real-engine headless-Chromium test downloads a valid STEP, a 12-facet 30x20x6 mm STL and the concept-sheet PNG (test_dashboard_export.py). Remaining D2 work: item 5's section, exploded and rollout-playback views.
