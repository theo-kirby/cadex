---
node_id: 79d007fe-c870-500a-9467-a4144fa528d6
slug: odd-pebble-9529
title: Prove Wren dashboard restart during real GPU training
created_at: '2026-09-13T04:31:05+00:00'
parents:
- sunny-canyon-4438
summary: ''
artifacts:
- docs/probes/wren-fresh/RESTART-TRAINING.md
- docs/probes/wren-fresh/restart71-evidence.json
- docs/probes/wren-fresh/training71-evidence.json
---
## What

Completed Wren's real-GPU dashboard-restart proof, with a finished bounded training attempt, verified checkpoint/final videos, a reusable Linux browser observer, strengthened restart regression, compact evidence receipts, and lifecycle/operator documentation. Port 8765 stays on ot5-wren-copy54, default wren71-final.

## Why

The critic selected the concurrency gap expressly excluded by sunny-canyon-4438: restart the persistent dashboard while real training continues, verify no trainer stop or duplication, automatic telemetry recovery within five seconds, and historical playback preservation. This unit follows that request directly and advances D6/D10, with D3/D4 evidence retained on the same attempt. Assumption: repeat the product agent's existing 90 mm Wren design and existing experiment settings; no new design turn or gait study is needed. This is not another completed-artifact audit and does not claim an engine restart during active training.

## Method

From the checkout, ran the existing experiment:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/train.py \
  "$HOME/cadex-projects/ot5-wren-copy54" wren71 "http://$(tailscale ip -4):8765/" \
  'product-agent-authored 90 mm Wren revision; repeat for real-training dashboard restart proof'
```

Alongside it, ran the new observer (exit 0):

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/restart_training.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren-copy54" wren71 wren66-final
```

It waited for real updates, opened a live page plus a historical playing page on the persistent private URL, and restarted only cadex-operator-review. It never manually refreshed either page after restart and never wrote trainer telemetry or signalled the trainer. Linux /proc counts actual cadex_train.py interpreters and records PID plus process start ticks. It checks these before/after restart and on every subsequent observation, seven committed-to-page samples, fresh-page current selection, historical selection/revision, same advancing unpaused video element, matching download hash, one navigation per page and return-to-current. Failure writes a receipt and leaves independently bounded training running.

The experiment ran 240 updates, 1024 environments, seed 0, checkpoints every 20, a 1800-second timeout and MemoryMax=20G. It engine-verified and rendered checkpoint20 during training and the final policy afterward, decoded every video frame and checked playback/download on the persistent URL. An additional current.py check at update 234 confirmed active-run selection after checkpoint publication; the completion check confirmed the final default. summarize_training.py generated the compact experiment evidence, augmented with those current.py receipts, history lengths and scope/overlap explanations. Source logs, screenshots, policies, videos and traces stay project-local under evidence/wren71-*, runs/wren71* and assets; no large outputs or machine paths are committed.

The existing fixture browser regression now actually plays video before restart, requires it to remain unpaused and advance afterward, and requires a newer telemetry update within five seconds. Receipt guards verify process continuity, timings, histories, witness/policy/model/video identities and completion. RESTART-TRAINING.md documents the lifecycle evidence and limitations; the prior restart proof, Wren overview, CLI docs and published operator status link it.

## Result

The real service changed PID 3255404 to 3308131; restart command returned in 0.114 s. Exactly one trainer interpreter was sampled, PID 3303026/start tick 100242161, unchanged across restart and every recovery sample. Live telemetry advanced from update 4 to 14, first newer update after 0.957 s, seven observed commits reaching the page in 0.240–1.423 s. Historical wren66-final retained revision de9692bd4ee5..., its same playing video and matching download hash 802baa759c98e52ba1067cab1f39e28dc72d3fee7c82b073b285bffe0a82470a. Fresh and return-to-current selected wren71. The screenshot was inspected.

Training completed exit 0 in 729.671 s, GPU, 240 points in all three histories. Sampled scope host peak 7,395,639,296 bytes was below its 20 GiB limit. Whole-GPU peak was 31,525 MiB including concurrent tests/browser processes: not trainer-attributed. Final reward/step 0.317777, loss 0.168609, estimated episode length 353.103. Optional Warp import diagnostics did not prevent MJX training or policy verification. No trainer remained at completion. All 15 old run records were hash-preserved. The exported model/task bytes match wren66; the different training revision 062e927c0196... reflects a different retained policy asset declaration, not a new geometry design.

Checkpoint20 was published at updates 18→35, with training still active after browser playback/download; video render spanned updates 23→33 in 14.039 s. Final render took 12.682 s. Engine witness errors were 2.80e-08 and 7.88e-08 against tolerance 0.0001. Both videos decode 81 differing frames at 10 fps, encode 8.1 s for eight simulation seconds, and play/download with their recorded hashes. Video digests are 3fef14c9cde01bffb632c500a7bde061bd00c72e18a0fe550989fde802c53d37 and a2fde70a223941d18096dc08d3559ab2cae8e0b834ad3b2cc6920487074bdcc5. Same-seed torso displacement is +49.094/+61.241 mm with no threshold falls and full eight-second survival; these are not alternating-gait or multi-seed comparison claims.

The persistent service remains active on port 8765 with 18 runs; fresh visits select wren71-final, revision e9dee22bc90c428942562eeadf150ef4bcd4ab03d8e9ed96e0f959272cfa22bb, 90 mm feet. The final browser selected checkpoint history and returned to current; the completion screenshot was inspected. Published operator status is current.

Verification: with OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1, pixi run test-engine passed 2110 tests, 53 skipped in 268.14 s; pixi run python -m pytest cli/tests -q passed 415, one skipped in 414.17 s. The final completion-receipt test was added after that suite and all 14 evidence tests passed in 0.05 s; the strengthened lifecycle browser tests passed 2 in 13.64 s. No unresolved failures. No build required: probes, tests and documentation only, no engine/protocol/payload/shell edits. git diff --check passed. No new dependency, direction change or removal. This is same-machine private-address evidence, not a second-device test or new D11 similarity comparison. Engine/CLI suites overlapped training and checkpoint rendering: measured before/during/after ordinary iteration medians 1.435/1.356/1.304 s cannot isolate renderer overhead. One unit, no state edits or reconcile.

Dispatch closed: 1 unit — prove persistent dashboard restart during real Wren GPU training with continued telemetry, historical playback and retained checkpoint/final videos

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 398b39e24338d0372573ff53afe3a2135715f6fd

## State Impact

- target: clever-field-7845 — Real Wren GPU restart proof passes: unchanged trainer PID/start time, automatic telemetry recovery in 0.957 s, historical playback/download preserved; completes concurrency evidence excluded by retained-artifact proof
- target: deep-clover-6012 — Persistent port 8765 remains on ot5-wren-copy54 through wren71 training and completion; fresh visits now select wren71-final with 18 retained runs and verified videos
- target: candid-harvest-2614 — Wren71 checkpoint20 published during active training and final video retained; both engine-verified, 81 decoded frames, eight simulation seconds, browser playback/download passed
