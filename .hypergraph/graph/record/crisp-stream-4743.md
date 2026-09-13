---
node_id: 5e128570-cf2b-577e-ba0b-cd63c895d4b4
slug: crisp-stream-4743
title: Complete Wren's lifecycle report and verify retained designs on the persistent dashboard
created_at: '2026-09-13T04:45:20+00:00'
parents:
- odd-pebble-9529
summary: ''
artifacts:
- docs/probes/wren-fresh/LIFECYCLE.md
- docs/probes/wren-fresh/lifecycle72-evidence.json
---
## What

Completed Wren's user-facing lifecycle report at docs/probes/wren-fresh/LIFECYCLE.md, with D1–D11 evidence links, the ordered creation/reopen/train/review/copy/interruption/revision/retrain/restart history, the two historical common-seed comparisons and the current wren71 repeat explicitly separated. Added a read-only persistent-browser report probe, compact portable receipt, evidence consistency tests, and discovery links from the Wren, operator and headless-biped documentation. Updated the published operator status.

## Why

The critic selected exactly this D9 unit after iteration 71 closed the real-training dashboard-restart gap. I followed that request rather than starting another training repeat. The original 85 mm product-agent design, caller-authored 105/110 mm steps and product-agent 90 mm revision have different authorship and evidence; an indexed report is needed to interpret them without mistaking current wren71 for the five-seed experiment. Important qualification found in the actual run record: wren57-retry trained only 12 updates while wren66 trained 240. The evaluation seeds/episode limits match, but the training budgets do not. The report discloses that limitation rather than interpreting revision66-evidence.json's protocol.training_iterations=240 as describing both policies.

## Method

From the checkout, against the existing private-network service on port 8765:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/report.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" lifecycle72-final
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests/test_wren_lifecycle_report.py -q
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python -m pytest cli/tests -q
setsid env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run test-engine
```

The first real-browser pass also succeeded in evidence/lifecycle72. The final pass adds the full style digest to the receipt and is committed as lifecycle72-evidence.json. Both original screenshots and final screenshots/raw receipts remain project-local. I inspected the 90 mm and 110 mm dashboard screenshots: each is identified as its own historical revision and draws all eight components on the delivered grid scene. This is not a new D11 reference comparison.

The probe checks six playback runs on one headless Chromium page: original wren1-final (85 mm), wren2-final (105), wren57-retry (110), wren66-checkpoint20 and wren66-final (90), plus current wren71-final (90). It compares revision/digest and parameters to the server's records, opens every retained document and compares exact displayed text and stored hashes, exercises real pointer orbit/zoom, matches all three curve lengths, plays and downloads each video with matching record/disk/browser SHA-256, preserves playback/selection through three refreshes, returns to current, and hashes all run/asset files before/after. No server restart, engine acceptance, training or new policy/video was performed by the probe.

The new evidence tests resolve report links, require D1–D11 coverage, recompute the table from committed per-seed rows, compare historical browser model/policy/video identities with the prior receipts, and separate the current repeat. Initial focused execution exposed a wrong relative documentation link and a test assumption that style was an object; both were corrected (the actual schema has style and style_sha256 separately). Final focused execution passed all three tests. No product behavior or dependency changed; no build, protocol/payload or shell gate was needed.

## Result

The persistent service stays active on ot5-wren-copy54, PID 3308131, 18 runs; a fresh visit selects wren71-final at revision e9dee22bc90c428942562eeadf150ef4bcd4ab03d8e9ed96e0f959272cfa22bb with 90 mm feet. All 703 run/asset files stayed byte-identical. All six views have eight components and hash-matching playable/downloadable videos. The retry has 12 points per curve, checkpoint20 its frozen 19-point snapshot labelled stale, and the four finals 240 each. The same style digest 27893221b3c6cf784d62c16fdaa5c88d1beb031bcb195e5f34e1598ea56e5b0c is retained across them. Historical 110 mm documents contain architecture/decisions/progress; the agent-revised snapshots additionally contain docs/design-specs.md. Missing historical domain documents are not substituted from current state.

Same-seed historical results remain: 85 mm final mean X -10.357 mm, mean/min survival 4.98/0.44 s, 2/5 falls; 105 mm final +52.647 mm and 0/5 falls; 110 mm retry +40.137 mm, 90 mm checkpoint +42.724 mm, and 90 mm final +55.147 mm, each surviving 8 s with 0/5 falls. The last three mean rewards are 214.882/213.622/144.877. The 12-versus-240 training budgets and single training seed preclude a causal geometry conclusion. wren71's +61.241 mm is seed 0 only, not another five-seed comparison or gait claim.

Acceptance limits explicitly retained: missing/partial-video injection has real historical Reed plus shared regression evidence, not a Wren-specific repeat; the full Wren reference comparison is historical at 110 mm, not a new 90 mm same-camera/pose comparison. Current videos reuse the proven style contract. All browser evidence is same-machine through the private address, with no second-device claim. No new training was started, no dependency added, no charter/state/plan edited, no deviation from the critic's request. The next unit can close one of those evidence limits without another training repeat.

Verification: full CLI suite 419 passed, one skipped in 412.96 s; isolated engine rerun 2,110 passed, 53 skipped in 262.33 s; final focused evidence guard 3 passed. The initial non-isolated engine invocation ended with signal 15 (exit 143) at test_cadexd_lifecycle.py, without a pytest failure report; its termination cause is not established. The isolated rerun passed. All suite logs are retained under the project's evidence/lifecycle72-final directory. The full CLI and engine suites overlapped each other, with no new experiment trainer. Final HTTP identity still matches the successful persistent browser receipt. git diff --check passed. Hypergraph export/check must be run after minting this node. The unreconciled tail was one record on arrival; this adds a second without reconciling.

Dispatch closed: 1 unit — Wren lifecycle report links D1–D11 evidence and verifies original, revised and current recordings on the persistent dashboard

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 3028d0dd151a31abd1207f3778295af2da5ab0b3

## State Impact

- target: silent-river-6649 — Wren now has a user-facing D1–D11 lifecycle report, per-seed 85/105/110/90 mm comparisons, verified historical/current recordings and explicit unequal 12-versus-240 training budgets; current wren71 is distinguished as seed-0 restart repeat
- target: deep-clover-6012 — Persistent port 8765 still serves ot5-wren-copy54 with wren71-final default and 18 runs; six model/document/curve/playback/download views pass, all 703 run/asset files unchanged, no server restart or new training
- target: crisp-sun-1239 — Wren report explicitly retains acceptance limits: missing/partial-video injection relies on historical Reed/shared regressions and full D11 visual comparison is historical at 110 mm rather than current 90 mm; neither needs another training repeat
