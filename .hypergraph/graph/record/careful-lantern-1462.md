---
node_id: b2494245-2924-5ae8-a33e-9100a6394eb4
slug: careful-lantern-1462
title: 'ADR-556: scrubber sliders keep a 160 px floor at phone width in both themes (record for 5dfa1f33)'
created_at: '2026-10-05T16:59:00+00:00'
parents:
- empty-jasper-3681
summary: ''
---
## What
Records ADR-556 (commit `5dfa1f33`, which landed as "ouroboros #25: no record"). At phone width a scrubber's slider keeps a 160 px floor (`--scrub`), is `--tool` tall, and its label wraps under it. CSS only: `review.css`, `docs/DASHBOARD.md` §5, the ADR, REPORT §5, and a two-theme phone test in `cli/tests/test_review_checkpoints.py`.

## Why
The critic's fix-first: commit `5dfa1f33` carried no record, and unrecorded work did not happen. The critic accepted ADR-556 itself. The critic also asked for a reconcile. That was **not** done: this dispatch forbids the hypergraph-reconcile skill in a work iteration, with no exceptions.

## Method
Re-ran the ADR's own test at the current HEAD: `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests/test_review_checkpoints.py -k 390 -s`. Chromium drove the page through `browser.py` at 390 × 844 with touch emulation, in the light and dark themes.

## Result
2 passed, with Chromium running and nothing skipped. The measured slider widths match the ADR and REPORT: 287 px for the checkpoint slider and 303 px for the revision slider, in both themes. Without the change the checkpoint slider was 0.03 px (from the ADR's own before-measurement). Still open at that commit, as REPORT §5 says: in the light theme `#model-status` (`--warn` #8a6100) sits on the dark viewport floor and partly under the expanded overlay. The next record takes that up.

Dispatch closed: 1 unit — ADR-556 recorded after the fact (scrubber 160 px floor at phone width)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun3
- commit: 5dfa1f3340509f12ec07eee78e04475e7879f38c

## State Impact

- target: vast-ivy-6277 — at 390 px both scrubber sliders keep a 160 px floor (287/303 px measured, both themes), label wraps under (ADR-556, 5dfa1f33)
