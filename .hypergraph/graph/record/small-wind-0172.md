---
node_id: a266a203-8a2f-5802-8a81-de6e21a5fabb
slug: small-wind-0172
title: Wren copy GPU interruption and successful retry with persistent review
created_at: '2026-09-13T01:27:14+00:00'
parents:
- crimson-bell-5375
summary: ''
artifacts:
- docs/probes/wren-fresh/INTERRUPTION.md
- docs/probes/wren-fresh/interruption.py
- docs/probes/wren-fresh/interruption-evidence.json
---
## What

Exercised real GPU interruption and successful sequential retry on Wren's 110 mm-foot working copy through the persistent private-network dashboard. Added an executable browser lifecycle probe, compact evidence and user-facing experiment/status documentation. Port 8765 remains serving ot5-wren-copy54 with wren56c-retry selected; no trainer remains active.

## Why

Advances cool-gate-3332 (D8), deep-clover-6012 (D10), and cold-vale-4232 (D7 copy training isolation), following crimson-bell-5375 and the critic's requested interruption/recovery experiment. Did not perform the critic's requested reconciliation: this dispatch explicitly forbids reconciliation, state/view edits and hypergraph update, and mandates a contributor record. The supplied tail was empty after the previous checkpoint, but the short plan still names out-of-charter clearance/section work. Declare its replacement as a plan impact for the next authorized reconcile; no planner or state mutation is used here. Provider capacity is irrelevant to this unit. The existing 110 mm caller-authored copy edit is used unchanged; no product-agent revision authorship is inferred.

## Method

Ran `PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python docs/probes/wren-fresh/interruption.py "$HOME/cadex-projects/ot5-wren-copy54" "http://$(tailscale ip -4):8765/" wren56c`. Each public CLI export retained its model/task, source, docs, params and assembled eight-component view before a run record and direct offboard trainer launch. Existing venv, 1024 environments, seed 0, 900-second timeout with 20-second forced-stop grace and MemoryMax=20G per GPU attempt. Requested 60 iterations then sent SIGINT to the uniquely identified Python trainer after iteration 5 and multiple real browser updates; waited for exit before any retry. The retry requested 12 iterations and saved a policy. Neither probe writes progress.json nor launches/stops the dashboard.

Browser checks use the persistent private address, asserting fresh current selection, revision, 110 mm feet and eight components at starts; failed telemetry plus explicit controlled-interruption note and CLI retry guidance after SIGINT; done telemetry after retry; no substituted video. After each outcome, all four existing videos decode completely, play through three refreshes and download with matching hashes. Historical interruption remains selectable after success and returns to current. The final check_terminal helper waits independently for run badge and telemetry publication and was re-executed on both real retained outcomes, asserting failed/failed and completed/done. Current.py independently verified experiment boundaries and completion. Screenshots were visually inspected. Inventoried original Wren files excluding .git and all prior copied run files before/after; those checks pass. Evidence and generated files remain project-local under evidence/wren56, evidence/wren56b, evidence/wren56c and their distinct runs; the compact receipt is docs/probes/wren-fresh/interruption-evidence.json.

## Result

wren56c-interrupt exits on SIGINT (supervisor return -2), state failed with KeyboardInterrupt at iteration 5, retaining six samples in each reward/loss/episode-estimate history. Launch-to-browser time 96.717 s; sampled peak host memory 5,004,201,984 bytes. wren56c-retry exits 0, state done at iteration 11 with 12 samples in each history; 153.874 s and 5,488,803,840 bytes sampled peak. Both report gpu and run with enforced 21,474,836,480-byte host caps. The retry policy is 49,137 bytes, SHA-256 f96f80229e9c85e7a4f219da992f221d403527026c95922658143b82e7993042, retained under runs/wren56c-retry/train. Its trainer-local witness self-check passes, but no new engine rollout verification or video is claimed. Final batch reward/step 0.136326, loss 8.231127 and episode estimate 99.9024 are not survival or gait measurements. Known JAX cast and optional Warp import notices appeared without preventing exit 0.

All eight historical video checks pass. All 294 prior run files, including earlier probe attempts, and 963 original Wren files excluding .git remain byte-identical. Persistent default is wren56c-retry at accepted revision 5b61ef31ff134f0f31b079347d9e5d3fd6aec236f12ad9c7b45910640388d7e6 and digest b04439061b0278903fca11079ff0937dac12425a5a8b767e675e24542c7a4ea4; service active after completion. This supplies Wren's D8 interruption-followed-by-success evidence and repeats D10 on a copy. It adds D7 training isolation evidence; it does not claim training while the original path was unavailable, new D11 similarity, second-device observation or Wren D9 product-agent revision authorship.

Two failed probe drafts remain retained. wren56-interrupt's PID assertion matched /usr/bin/timeout and Python; no ambiguous signal was sent. Inspected the actual processes, then sent SIGINT to Python at iteration 23 and recorded failed status. wren56b-interrupt sent SIGINT correctly at iteration 5 but raced the run-note publication; later browser verification confirmed failure and retry guidance. The corrected full probe passes. Its retry completion screenshot also caught done telemetry before the completed badge, so check_terminal now waits for both and its real-outcome recheck passes. Original transitional screenshots remain retained. No project/telemetry history was rewritten to hide these probe defects.

Constraint breach: the CLI suite was initially launched concurrently with GPU training and includes three real 1-iteration, 4-environment CPU toy-training invocations. Thus there was a brief CPU/GPU trainer overlap, although no two GPU experiments overlapped. Discovered by process inspection; those toy runs had already finished. Future actors must run CLI suites separately from live training. No throughput/zero-overlap claim is made from those windows. Required suites passed: engine 2110 passed, 53 skipped in 268.29 s; CLI 397 passed, 1 skipped in 401.77 s. Logs retained under evidence/wren56. Browser experiment and terminal recheck, py_compile and git diff --check pass. No new dependency, product behavior, engine/protocol/payload/shell change or build; no state/generated views edited. Hypergraph export/check is run before commit. The next authorized reconcile must fold the plan impact below rather than leave the old horizon current.

Dispatch closed: 1 unit — Wren working-copy controlled interruption, successful GPU retry and persistent browser preservation evidence.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: db88c6761a4b0f47bc92c1cfb8118bd5329e6116

## State Impact

- target: cool-gate-3332 — Wren working copy now has real SIGINT interruption at iteration 5 followed by successful 12-update GPU retry; persistent browser shows explicit failed/interruption guidance then completed/done, preserves curves and all four older videos. Two probe defects fixed and retained; initial CLI CPU test overlap disclosed.
- target: deep-clover-6012 — Persistent port 8765 remains on ot5-wren-copy54; browser verifies wren56c-interrupt then current wren56c-retry at accepted 110 mm revision, historical interruption selection and return to current; service remains active.
- target: cold-vale-4232 — Training the independent 110 mm Wren copy preserves all 294 prior run files and 963 original Wren non-git files; saved retry policy remains copy-local. Original path was available during training, unlike prior copy edit/reopen test.
- target: plan/young-crane-9546 — Replace the stale clearance/section/scaffold short horizon with ot5 mission work: assemble Wren D1-D8 lifecycle evidence including copy/interruption receipts, exercise any remaining Wren restart preservation gap, and pursue the documented product-agent revision authorship gap only when provider available. Keep persistent port 8765 current throughout. This contributor dispatch forbids reconciliation; fold this impact at the next authorized reconcile, with no separate planner required.
