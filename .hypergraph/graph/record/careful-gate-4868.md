---
node_id: 18592d16-40ef-516f-87f9-582de2eece3d
slug: careful-gate-4868
title: Verify copied project review without the original path
created_at: '2026-09-12T19:20:42+00:00'
parents:
- clear-shore-7806
summary: ''
---
## What

Added a headless-browser copy-isolation regression and documented the stopped-writer whole-directory copy procedure. This is one D7 fixture verification unit, not a real biped retraining experiment.

## Why

D7 (`cold-vale-4232`) had no browser copy-isolation evidence. The existing D6 fixture and retained-video fixture make this an unblocked, bounded next lifecycle check. No critic instruction was supplied. Adopted the supplied live headless review charter and explicit contributor-only dispatch; did not reconcile the tail or touch the owner charter. The run log records continuation after iteration 22 at 19:13:35 UTC; no separate live `charter reloaded` event was observed for this restart.

## Method

`cli/tests/test_review_lifecycle.py::test_copied_project_reopens_without_source_and_keeps_edits_isolated` runs `cp -R` with an absent destination, hashes all project files, opens two actual `cadex review` processes in headless Chromium, changes only the copy's synthetic accepted revision, and checks the original remains byte-identical. It stops the source server and renames the source out of its original path. A new page on the copy then asserts revision C current / revision A historical identity, parameters, 24 model triangles, all three retained metric histories, video playback beyond 0.1 seconds, and downloaded/served video hashes. Historical runs, review artifacts and assets retain their original hashes. This uses synthetic geometry and telemetry and invokes no engine acceptance or training. The copied source remains available under a renamed test-only path, but no project reference knows that path.

`docs/CLI.md` now gives the explicit copy and second-server commands, requires authoring/training/rendering to finish before copying, and states the non-atomic and external-symlink limitations. No production behavior changed, no removal or direction change, no dependency added, and no build needed.

## Result

Targeted browser lifecycle suite: `pixi run python -m pytest cli/tests/test_review_lifecycle.py -q` — 2 passed in 9.86 seconds, no skips. D7 advances with portable artifact and independent-reader fixture evidence; it does not tick D7. Real biped copy/retraining isolation remains open. Tests use disposable pytest directories, not new product-agent projects or the retired mechanism. No existing project or offboard training was touched.

Full verification: `pixi run python -m pytest cli/tests -q` — 362 passed, 1 skipped in 316.98 seconds; `pixi run test-engine` — 2103 passed, 54 skipped in 278.81 seconds. Both exited 0. `git diff --check` passed. No protocol, payload, or shell changes required their additional gates. Hypergraph export/check are run with this record before committing.

The unreconciled tail gains one record; this dispatch explicitly forbids reconciliation. No new dependency or unresolved test failure.

Dispatch closed: 1 unit — verify independent copied-project review in a headless browser.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: c2e1be4316dd31987df510482864f27487d11056

## State Impact

- target: cold-vale-4232 — D7 fixture evidence: whole-directory copy retains historical models, three metric histories and playable/downloadable video after the original path becomes unavailable; changing the copy's accepted fixture leaves the source byte-identical. Real biped copy/edit/retraining remains open.
