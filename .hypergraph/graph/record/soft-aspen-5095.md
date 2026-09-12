---
node_id: 4276ddf5-f88c-5f80-b7bb-41da5431da83
slug: soft-aspen-5095
title: Repeat the D11 viewport/video comparison on shin55-final over the persistent URL with pointer orbit
created_at: '2026-09-12T22:56:33+00:00'
parents:
- lucky-bramble-8274
summary: ''
---
## What

Repeated D11's same-pose, same-camera viewport/video comparison on the run the persistent operator page selects by default, `shin55-final`, through the private-network URL on port 8765. `docs/probes/review-style/compare.py` now takes the run, the historical clip and the evidence directory as arguments (defaults keep the iteration-40 `copy100` command true), derives the reference harness's floor height from the video's bounds instead of a hard-coded value, and adds a real left-button drag orbit, a wheel zoom-in and a 3.5× wheel zoom-out on the persistent canvas with screenshots, camera values, model pixel counts and the restaged environment recorded. Ran it with `shin55-final shin55-checkpoint20 style44`; the images, `side-by-side.html` and screenshot, plus a decoded last final-clip frame and a mid-clip checkpoint frame, are retained in the project's `evidence/style44/`; the compact receipt is committed as `docs/probes/review-style/shin55.json`. The review-style README carries the explicit assessment, the lifecycle report's D11 table drops the "not repeated on shin55" limit, the operator-review README records the iteration-44 revisit, ADR-301 gains the repeat, and `cli/tests/test_review_style_evidence.py` (8 tests over both receipts) holds the receipts to their claims and the documents to the receipts.

## Why

The critic asked for exactly this: repeat the D11 comparison on shin55-final through the persistent URL, retain decoded frames and screenshots, assess similarity explicitly, exercise close/wide framing, orbit, polling, playback and download, fix any demonstrated defect, and otherwise declare D11 satisfied through State Impact. It also asked to verify the reconcile count first: `hypergraph check` and STATE.md agree that iteration 42's reconcile folded through `fair-crow-5108` and exactly one record (`lucky-bramble-8274`) sat unreconciled; with this record the tail is two, below the three-record trigger, and two work iterations have run since that reconcile, so no reconcile pass is due next. Advances `fair-wolf-4645` (D11) and revisits `deep-clover-6012` (D10).

## Method

Read the charter, `.ouroboros/AGENTS.md`, the last three records and the iteration-40 probe. Confirmed the persistent service (`python -m cadex_cli review --project ~/cadex-projects/ot5-biped-copy29 --host 100.104.232.88 --port 8765`) was the same process, and that `shin55-final`'s trace has solver-output frames with component placements. Generalised `compare.py` and ran it against the persistent URL, the working project and the read-only `neural-whoop` checkout at `31caeb28…`; the first run's drag lowered the pitch below the presentation floor, duplicating the underside case, so the drag direction was changed to stay above the floor and the probe rerun (both runs exit 0; the second is the retained receipt). Decoded frame 5 of the final clip and frame 40 of the checkpoint clip with the pixi FFmpeg. Inspected side-by-side, close, wide, under, drag, zoom-in, zoom-out, final-frame and checkpoint-frame images and wrote the assessment from what was seen. Verification: focused tests (`test_review_style_evidence.py`, `test_lifecycle_report.py`) 14 passed; full CLI suite — see Result; `git diff --check` clean. No engine, protocol, payload, shell, renderer or trainer change, so no engine suite, packaged gate or build.

## Result

On `shin55-final` at accepted revision `67b5000f3de1…`: persistent viewport and capture page at the video's fixed camera are byte-identical 512² PNGs (`3bd31fe2d227…`); FFmpeg's decoded frame zero differs by mean absolute RGB error 1.6732/255 (tolerance 3, copy100 was 1.6423). The reference-module light frame on Reed's exact shin55 geometry, the persistent viewport and the decoded frame show the same fogged grey prototype grid with tile labels and subdivisions, the same floor-to-sky fade, palette, rough materials, steep key and grounded filtered shadow on the orange slab, at identical framing; the only differences are ADR-301's deliberate tighter shadow frustum and bias. Close 0.7×, wide 3× and underside match the copy100 findings. A real drag moved the camera to yaw 2.6 / pitch 0.8 at unchanged distance with the grid restaged; zoom-in to 400 mm kept the contact shadow; zoom-out to 2423 mm restaged to a 136 m room with fog far 33.9 m and no edge, wall or ceiling seam; the model stayed drawn (46 134 / 117 678 / 3 763 pixels). `shin55-checkpoint20` is labelled HISTORICAL with both revisions named, played, downloaded with digest `89bfc9ecde0e…` matching its record, survived a poll, and the current-run control returned to `shin55-final`. The final clip's last frame and the checkpoint's frame 40 keep the environment with the recorded falls unaltered. No visual defect was demonstrated, so no renderer change was made; D11's charter evidence list now has an artifact behind every item on the current design as well as on copy100. The persistent service was not restarted, no training was active, no project switch occurred, and published status stays `ot5-biped-copy29 / shin55-final`.

Concerns and assumptions: every observation is same-machine over the private address; the checkout ships no light-themed clip, so the light reference is the reference renderer on our geometry; `shin55-checkpoint20` and `shin55-final` share their first frame because they share geometry, initial pose, bounds and camera. The reference harness still needs the checkout's pinned Three.js cache (probe prerequisite, not a runtime dependency). No new dependency. The checkbox edit remains the owner's for every criterion; whole-goal completion is not claimed. Unreconciled tail after this record: two (`lucky-bramble-8274`, this one).

Verification: `pixi run python -m pytest cli/tests -q --basetemp=/tmp/it44/pytest-full` — 388 passed, 1 skipped in 373.69 s (380 before this unit plus the 8 new); focused `test_review_style_evidence.py` + `test_lifecycle_report.py` 14 passed; `git diff --check` clean. A first full-suite attempt errored at setup because the basetemp parent directory did not exist; that was the harness, not the tree, and the rerun above is the result.

Dispatch closed: 1 unit — D11 comparison repeated on shin55-final over the persistent URL with pointer orbit, retained frames and explicit assessment; no defect found

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 030237cac17b4599c3b3be3f15d9250681552a48

## State Impact

- target: fair-wolf-4645 — D11's charter evidence list is now met on the current design as well as copy100: on shin55-final over the persistent private-network URL the viewport and capture page are byte-identical at the video's camera, the decoded final frame is within 1.67/255, the reference-module light frame on the same geometry matches floor/grid, fog/horizon, palette, lighting/shadows, materials and framing, close/wide/underside plus real drag orbit and wheel zoom-in/out show no stage edge with the model drawn and contact shadows kept, and the historical checkpoint clip plays, downloads and survives a poll. No visual defect was demonstrated and no renderer change was needed. Receipt docs/probes/review-style/shin55.json, guarded by cli/tests/test_review_style_evidence.py. Remaining limits: same-machine observations only; no light-themed reference clip ships, so the light reference is the reference renderer on Reed geometry; the checkbox edit stays the owner's as for every criterion
- target: deep-clover-6012 — Persistent port 8765 reverified on 2026-09-12 (iteration 44) without restart: shin55-final selected by default at the accepted revision, real pointer orbit on the canvas, shin55-checkpoint20 played/downloaded/polled as HISTORICAL with both revisions named, return to current; published status unchanged at ot5-biped-copy29 / shin55-final
