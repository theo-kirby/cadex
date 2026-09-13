---
node_id: 41fbb836-c199-529a-9818-5ebddfe170f5
slug: scarlet-ocean-2381
title: 'Complete Lark''s D8 on the working copy: interrupted attempt, successful retry and its video on the persistent dashboard (ADR-315)'
created_at: '2026-09-13T08:22:09+00:00'
parents:
- warm-falcon-0420
summary: ''
---
## What

Lark's D8 evidence, on the working project `ot5-lark-copy85` and the persistent private-network port 8765 (never restarted): a real GPU attempt `lark86-interrupt` sent SIGINT at iteration 5 after three page-observed updates and shown `failed` with the controlled-interruption note, `start a new cadex walk` guidance, six-sample curves and no substituted video; a successful new attempt `lark86-retry` (40 updates, exit 0, policy `074e22f1070c…`, witness 8.4e-8); and that policy declared through the public CLI, rolled out on seed 0 and rendered as `lark86-retry-video` (81 frames, 8.0 s, revision `7f6c23913d55…`), which decoded, played through polls and downloaded hash-equal on the persistent URL. All four earlier videos re-checked after each outcome, the historical interruption selectable after a refresh with return-to-current selecting the video run, the copy's 246 prior run files and 4 assets byte-identical, and the original `ot5-lark` (1,419 files excluding `.git`) byte-identical after the copy's retraining — D7's retraining-isolation half. ADR-315; commit `2fbe6940`.

## Why

The critic asked for exactly this: complete Lark's D8 on `ot5-lark-copy85` (interrupt one bounded real attempt, verify the dashboard identifies it and preserves earlier results, complete a successful new attempt with a verified playable/downloadable video), re-check the original inventory after copy retraining for D7, keep port 8765 current at each transition, and record. Lark's D8 was the one criterion without third-project evidence. Nothing deviates from the message; the reconcile is not due at two unreconciled records before this one, so it is left to the next pass now that the tail is three.

## Method

Both gate suites ran to completion before any trainer (CLI 437 passed/1 skipped 07:54–08:00 UTC; engine 2110 passed/53 skipped 08:00–08:05 UTC), because the ADR-305 exclusion guard refuses a concurrent pytest or trainer. `docs/probes/lark-fresh/interruption.py` is the Wren interruption driver with nothing project-named: model/task bundle found by kind in the public `cadex export` envelope, the browser held to every accepted-manifest parameter, component count from the frozen training view, retained videos by presence, the original project as an argument, the retry's iteration count as an argument, plus `train.py`'s final-policy playback branch (asset put, script declare, `params --set policy_on=1`, render, `cadex_cli.video`, `check_video.py`). Each attempt: systemd scope with `MemoryMax=20G` and a 900 s timeout, 1,024 envs, seed 0, run record frozen before launch, page identity checked at start, SIGINT to the one Python trainer in the scope for the first attempt, terminal telemetry/badge/note waited for without a reload, fresh visit checked, then all old videos re-checked. After the video: historical selection, refresh, return-to-current, inventories compared; the original was compared once more independently afterwards, and a fresh visit was recorded with `current.py`. The compact receipt `interruption86-evidence.json` is guarded by a new test in `cli/tests/test_lark_fresh_evidence.py`; the Wren guard regression was run against this driver's guard (5 passed). Docs: `INTERRUPTION86.md`, the probe README, the operator status README, `docs/HEADLESS-BIPED-REVIEW.md`, `docs/CLI.md`, `docs/ROADMAP.md`, ADR-315.

## Result

Port 8765 serves `ot5-lark-copy85` with `lark86-retry-video` selected by default at accepted revision `7f6c23913d55…` (digest `7f0d98163e84…`, `foot_len` 90, `policy_on` 1); nine runs are browsable; no trainer is active; the service was not restarted. Interruption: exit −2, `failed` at iteration 5, 6 samples per curve, 1,655 guard scans, one trainer PID, peak host memory 5.00 GB, 90.7 s to browser completion. Retry: exit 0, `done` at 39/40, 40 samples per curve, 3,515 scans, one PID, 5.48 GB, 190.8 s. Retry video: witness 8.4e-8, render 12.3 s, 81 frames, time-limit reached on seed 0 (total reward 194.66) — one seed and 40 updates, so no gait claim. Gates on the committed tree: CLI `438 passed, 1 skipped` (415 s), guard regression 5 passed; engine suite unchanged from the pre-launch run (no engine change).

Concerns and limits: same-machine private-address browser checks, not a second-device test; the driver duplicates the Wren guard rather than importing it (the two probe directories are peers, and the regression runs against both); `check_video.py` still hard-codes eight components and the `-final`/`-checkpoint20` pairing, which is why the playback run is named `lark86-retry-video` rather than `-final`; no product-agent authorship and no new D11 comparison. The unreconciled tail is now three records (`brave-water-4060`, `warm-falcon-0420`, this one), so the next unit is the reconcile pass.

Dispatch closed: 1 unit — Lark's D8 completed on the working copy: SIGINT-interrupted real attempt shown failed with guidance and preserved history, a successful 40-update retry with a verified playable/downloadable video on the persistent dashboard, and the original byte-identical after the copy's retraining (ADR-315).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 2fbe69403f839b69d989febe6bec6dea350c9ed7

## State Impact

- target: cool-gate-3332 — D8 repeated on the third fresh project: on ot5-lark-copy85 a real GPU attempt (lark86-interrupt) was sent SIGINT at iteration 5 and the persistent page showed failed, the controlled-interruption note, retry guidance, six-sample curves and no substituted video without a reload; lark86-retry completed 40 updates with a saved policy and lark86-retry-video is its verified, playable, downloadable rollout; the historical interruption stays selectable with a route back to current; driver docs/probes/lark-fresh/interruption.py is project-agnostic; receipt interruption86-evidence.json guarded in cli/tests.
- target: cold-vale-4232 — D7's retraining half on Lark: after the copy's two training attempts, policy declaration and video, the original ot5-lark (1,419 files excluding .git) is byte-identical to its pre-experiment inventory, checked by the driver and once more independently.
- target: candid-harvest-2614 — a fourth Lark video, lark86-retry-video (81 frames, 8.0 s, seed 0, revision 7f6c23913d55…, policy 074e22f1070c…, witness 8.4e-8), decoded, played through polls and downloaded hash-equal on the persistent URL; the four earlier videos re-checked after each outcome.
- target: deep-clover-6012 — D10 across a real experiment: port 8765 stayed on ot5-lark-copy85 without restart while a fresh visit selected the failed lark86-interrupt, then the active/completed lark86-retry, then lark86-retry-video; the operator status README identifies the new default.
- target: crisp-sun-1239 — Lark now has D1–D11 evidence of its own including D8; gates CLI 438 passed/1 skipped on commit 2fbe6940, engine 2110/53 before launch; unreconciled tail three records, reconcile due next.
