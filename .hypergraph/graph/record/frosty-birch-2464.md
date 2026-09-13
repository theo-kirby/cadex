---
node_id: 97464a78-b04d-5c5d-a3ee-78817acd5f48
slug: frosty-birch-2464
title: Retrain Wren's revised feet and compare retained policies
created_at: '2026-09-13T00:48:37+00:00'
parents:
- honest-path-3451
summary: ''
artifacts:
- docs/probes/wren-fresh/COMPARISON.md
- docs/probes/wren-fresh/comparison-evidence.json
- docs/probes/wren-fresh/retraining-evidence.json
---
## What

Completed Wren's bounded 105 mm foot retraining and the declared original/revised checkpoint/final comparison. The persistent private-network dashboard stays on ot5-wren and now defaults to wren2-final, accepted revision 26332a5955e3…, with its model, curves and verified video. Added the comparative lifecycle report, reproducible public-CLI evaluation/current-view probes and evidence regressions; preserved all 114 original run files byte-for-byte.

## Why

Follows honest-path-3451's review-driven 85→105 mm foot hypothesis and implements the critic's requested experiment. Advances D3/D4 real retraining and live checkpoint publication, D5 retained history, D10 experiment-boundary operator identity, and D9's common-seed comparison. The original Wren was product-agent authored; the foot revision was a public CLI parameter edit, not a product-agent design turn. This record does not claim Wren's full D9 authorship/copy/interruption lifecycle or replace Reed's earlier evidence.

## Method

From the checkout, ran `PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/train.py "$HOME/cadex-projects/ot5-wren" wren2 "http://$(tailscale ip -4):8765/"`. The existing offboard GPU environment ran 240 iterations, 1024 environments, seed 0, checkpoint interval 20, independent timeout 1800 s, MemoryMax=20G. No other experiment training ran. Browser start check matched a90b84033ced… and 105 mm feet; observe.py spanned real committed updates. Engine witness verification preceded each saved rollout/video. check_video.py decoded and played/downloaded them through the persistent server; current.py checked completion, and historical rechecks verified original videos without overwriting their earlier evidence.

`compare.py` replayed wren1-checkpoint20, wren1-final, wren2-checkpoint20 and wren2-final in fresh project-local scratch projects under the operator's cadex-projects directory. It uses each retained run's script/effective parameters and verified asset, never today's accepted parameters for an old model. Every seed checks policy/model/task digests; seed zero must reproduce the retained trace exactly. Seeds 0–4, eight seconds at 50 Hz; all twenty rows contain actual simulated survival, torso X displacement, falls/termination, reward and trace hash. Completed evaluation evidence was copied into Wren's evidence/comparison52/{c1,f1,c2,f2}/evidence, making scratch projects unnecessary for review. report_comparison.py asserts the original 114-file inventory and task difference only in model reference.

User-facing report: docs/probes/wren-fresh/COMPARISON.md; compact comparison-evidence.json and retraining-evidence.json beside it. Large videos, policies, raw traces, browser screenshots, logs and decoded seven-second frames remain inside Wren. Published status is docs/probes/operator-review/README.md; project PROGRESS.md/DECISIONS.md also record the comparison. ADR-304 documents methodology and probe correction. No dependencies or product engine/protocol/payload/trainer/shell changes; no build.

Verification: bounded-BLAS engine suite 2110 passed, 53 skipped (260.55 s). Initial unrestricted-BLAS run was interrupted after 76 passes due CPU oversubscription, then rerun with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1. Full CLI suite 396 passed, 1 skipped, 1 failed (374.75 s): my new test confused zero-based final iteration 239 with 240 completed updates. Corrected the test to iteration+1==240 and state done; all nine Wren evidence tests then passed. Other CLI tests were not repeated after this test-only correction. Real browser, decoded media and twenty CLI rollouts all passed. An early old-video recheck raced checkpoint publication and failed its frozen initial-current-target assumption; the probe now checks the route shown at click time, and terminal rechecks pass. The failure log remains project-local.

## Result

Training exited 0 on GPU: harness wall 750.302 s, trainer internal 681.823 s, 240 reward/loss/episode-estimate history points. Sampled host peak 7,385,264,128 bytes; whole-device GPU peak 15,120 MiB. Seven browser observations across iterations 3–11, no reload; measured committed-to-page delays 0.50–1.53 s. Initial compilation was correctly labelled stale. Checkpoint publication/playback spans iterations 18–34 with training still active; render spans 23–32 and costs 12.731 s. Ordinary iteration medians before/during/after 1.466/1.352/1.323 s are descriptive, not controlled overhead: CPU evaluation/suites shared the machine. Final video render 12.18 s.

Mean X displacement / mean survival / minimum survival / falls over five seeds:
- Original checkpoint20 (85 mm): +43.078 mm / 8 s / 8 s / 0.
- Original final (85 mm): -10.357 mm / 4.98 s / 0.44 s / 2.
- Revised checkpoint20 (105 mm): +41.782 mm / 8 s / 8 s / 0.
- Revised final (105 mm): +52.647 mm / 8 s / 8 s / 0.

The revised final has better measured survival on this seed set, not a demonstrated repeatable gait or isolated causal geometry effect. Only one training seed per design; small displacement includes resets and falling motion. Falls mean the declared torso threshold. Decoded seven-second revised frames show standing poses. Original final video is 6 frames / 0.6 encoded s for 0.46 simulated s; the other three are 81 frames / 8.1 encoded s for 8 simulated s. Padding is not survival. All four play/download with their recorded hashes, model/parameter/curve identity and historical playback preserved through polling. New videos retain cadex-prototype-light-v1 and its style digest; no new full D11 similarity assessment. Evidence is same-machine private-address, never a second-device claim.

Persistent port 8765 remains running on Wren, wren2-final current, no experiment training active. All original run bytes remain intact. Wren-specific product-agent revision authorship, independent-copy and controlled-interruption repetition are not established by this experiment; the report links and distinguishes earlier Reed evidence. No broken product tree or new dependency is known. Assumption: the critic authorized the already-declared CLI revision experiment; original authorship is not retroactively credited to that edit.

Dispatch closed: 1 unit — Wren revised-foot retraining, retained videos and honest common-seed lifecycle comparison.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 55dd5b0fdbebf0cd8876e267dc0e9684252dcad5

## State Impact

- target: sharp-union-6036 — Wren's revised-foot retraining retains all 114 original run files and four distinct model/policy/video histories; twenty common-seed rollouts match retained identities.
- target: silent-river-6649 — Wren comparison measures final falls 2/5 to 0/5 on declared seeds; CLI parameter revision explicitly distinguished from product-agent authorship, with Wren-specific copy/interruption scope still unproven.
- target: deep-clover-6012 — Persistent Wren dashboard verified across wren2 start, live checkpoint publication and wren2-final completion; server remains running with revised final selected.
- target: candid-harvest-2614 — Revised Wren checkpoint20 and final videos witness-verified, decoded and browser-played/downloaded; intermediate published while GPU training remained active.
- target: dawn-delta-4361 — Revised Wren GPU run completes 240 updates; persistent browser observes seven updates without reload at 0.50–1.53 s measured latency.
