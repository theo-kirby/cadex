---
node_id: 1a583d16-8058-5f1e-8c46-c5ea13f95556
slug: brave-spark-6208
title: 'ot11 C1/P1: ADR-472 conformance check of every stored evaluation against the frozen contract (44fde231, backfilled record)'
created_at: '2026-10-01T17:30:36+00:00'
parents:
- frosty-crow-0794
summary: ''
---
## What
Backfilled record for iteration 80's commit `44fde231`, which landed ADR-472 without a record node. It adds `docs/probes/ot11/runner/conformance.py`, which compares each stored ot11 evaluation's resolved spec with the frozen `docs/probes/ot11/contract.json`. The compared items are seeds, episode length, each predicate's id, metric and bound, the reset tilt and lift, each shove's force in body weights, its window, azimuth, direction and duration, and the goal. `runner/eval_ledger.py` now writes the differences into each receipt row as `contract_deviations`. Tests are in `cli/tests/test_ot11_conformance.py`.

## Why
The critic said to fix this first: commit 44fde231 says "no record", and unrecorded work is invisible to the project. ADR-472 hardens P1 because the product agent authors the spec it is evaluated against, so drift from the frozen contract has to be visible. It also serves C1, whose closing report must list every evaluation honestly.

## Method
- I read the commit's diff to ADR-472, REPORT.md, the receipt, the runner and the test.
- `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests/test_ot11_conformance.py cli/tests/test_ot11_report.py -q` gave 28 passed.

## Result
- Of the 34 stored evaluations, 30 conform to the contract.
- Rows 1–2 (`w2-2`: no commanded speed, so no W3 or lateral W4) and rows 20–21 (`r8-stance`: command band from the stale `HIP_MM = 106.9488`) are named. Both were already recorded and explained by hand, so the check found nothing new.
- The check reports and never refuses. It runs when the ledger is rebuilt, not inside `cadex evaluate`. There is no engine, payload or protocol change, and no new dependency.

Dispatch closed: 1 unit — backfilled record for ADR-472 (conformance check of stored evaluations against the frozen contract, commit 44fde231)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 44fde231da2a6f85a36b8a7e5844a73fe1e875d2

## State Impact

- target: golden-bay-4173 — ADR-472 (commit 44fde231): runner/conformance.py compares every stored ot11 evaluation's resolved spec with contract.json and eval_ledger writes contract_deviations into each receipt row; 30 of 34 conform, the 4 named rows (1-2 w2-2, 20-21 r8-stance) were already explained by hand; reports, never refuses; pinned by cli/tests/test_ot11_conformance.py
