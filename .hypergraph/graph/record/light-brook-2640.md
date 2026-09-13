---
node_id: 1664933e-e256-529f-a3b2-399888d4be89
slug: light-brook-2640
title: Complete bounded biped retry with active checkpoint and final video evidence
created_at: '2026-09-12T19:04:38+00:00'
parents:
- quiet-arbor-0259
summary: ''
artifacts:
- docs/HEADLESS-BIPED-REVIEW.md
---
## What

Ran one bounded fresh-biped GPU retry using the retained assembled training-view contract. Retained and browser-verified an intermediate checkpoint video while training remained active, collected real telemetry/model interaction and historical snapshot checks, and documented the experiment in docs/HEADLESS-BIPED-REVIEW.md. Detailed artifacts remain in the external ot5-biped project.

## Why

This follows quiet-arbor-0259 and performs the critic's requested successful-retry experiment for D4, D8 and the baseline needed by D9; the real assembled snapshot also advances D2/D5. No design revision or second training experiment is included. This contributor dispatch explicitly forbids reconcile/state edits, so no reconciliation was performed despite the charter's cadence. The historical clearance-first plan did not guide this unit.

## Method

The external evidence/probe3-experiment.py exports the unchanged model/task through cadex params policy_on=0, generates current tessellation through cadex render, calls retain_training_view under project_lock, and records the original training identity before invoking the offboard trainer. This directly exercises the new snapshot contract, not the cadex walk orchestration. It uses 240 iterations, 1024 environments, seed 0, checkpoint-every 20, XLA_PYTHON_CLIENT_MEM_FRACTION=0.45, systemd MemoryMax=20G and an independent 1800-second timeout. One trainer at a time; renderers run sequentially. A browser failure does not terminate training. No warm start, task edit, new dependency, engine/protocol/payload/shell change or build.

Training revision c26c92b09dbb3142c973d9807024373cf8d7c5b0f080a5c21ba8f66d3badf49e, digest 850acf23a05ade2fa76275a6484caaefc9e2d22230fb002ead681c533e530697. Model sha256 973dbfc260a4268a1e97817d7846a8302325b7a6b823f70f274bb8723e557756 and task 59508724bb6aef368fac7cc2c6cdfa11c342d8e1bec9d56c7698405b9376bfad equal prior probes byte-for-byte. Eight components, declared placements, specs and documents are snapshotted before training.

The real private-address Chromium observer passed orbit/zoom, seven iterations 3,5,6,7,9,10,12 over 11.78 seconds, one navigation and committed-to-page delays 0.18–1.33 seconds. Reward/loss histories grew 4 to 13 samples. The initial model_state field was captured before its subsequent successful loaded-state assertion; it is not a failed model test. After checkpoint playback changed the accepted script, historical probe3 retained its original model identity and passed rendered-pixel/camera checks. Its first external assertion used the wrong snapshot key accepted_revision; correcting it to revision passed without a product change. The initial helper invocation found no python command; python3 generated the harness before training started.

Checkpoint 20 policy 74750cc6d8e7f9817481e08e94ee01978120bbafe3edca5b25f53cabfe1b3c78 passed engine witness error 3.996235200531828e-08 < 0.0001. Playback revision 0fb4ffb59c69f646897d5c4464876b954ad3531e807313d6163244f648dcad15, digest 9c6f79478f4d8acfce28bd33e9f56f622e891ef621a2cbe512839730d830872a. Seed 0 reached 400 steps/eight seconds with no fall termination, truncated=true, total reward 333.02443433799135 and torso-link displacement [45.940988,1.898436,-29.309025] mm. The first video had 81 frames, 8.1 encoded seconds, rendered in 16.536 seconds and passed decoding/playback/three refreshes/download/digest/identity labels while training remained active. A sequential repeat took 27.675 seconds and produced different container bytes; the currently referenced c479457f48ad7217cfa4d69f79925d8f4c35add98b0ed8fa17d9580020674f8f video also passed while active. Original 757a0c4ed104a9238b26412d8a1570e3a5588a5e2cf78a6f6e8a340532218e74 bytes remain on disk, and its browser receipt is preserved separately. Both render windows overlapped checkpoint publication (committed iteration stayed 18, then 58); the second also overlapped the engine suite. These are coexistence measurements, not a causal throughput overhead estimate.

A render request for training-only probe3 exited 1 with no successful recorded rollout at this identity; the scope remained active. This tests missing-trace refusal, not an encoder crash. Browser checks bind the existing Tailscale address on this machine; no second-device claim. Prior probe1/probe1-playback/probe2/probe2-checkpoint20 run records remain byte-identical to external commit 73611af. Full project copying must include ignored traces, policies and videos; Git alone is not the retained project.

## Result


Training exited 0 on GPU with 240 iterations (last index 239), trainer-reported wall time 1003.681 seconds, final reward/step 7.442540, loss 899.636 and episode estimate 25.409 steps. Host cgroup sampled peak 9,321,664,512 bytes; GPU peak 15,152 MiB. Final policy a06b4bf489529d6cd119576131b778a02789cf30e1bf3793ab5a5e5d4ea04911 is 82,008 bytes and passed engine witness error 7.370347304913593e-08 < 0.0001. Retained final playback revision a7ee956cafc8de6b1732bc83cb3f59d832a6fe46b5406f3624e88267f479fa2d, digest 14d56ed42ef87185db899cb2485180a81f8eb0959aaf2f8356c7031760a6ebb1. Video 59724f619c5540468f8fd6e109aa319507be6a449eafcc8ef9f3259af6046853 has seven decoded frames/0.7 encoded seconds at 10 fps; rendered in 1.407 seconds. Seed 0 fell after 26 steps/0.52 seconds (termination fell, terminated_step 25, truncated false), total reward 198.204299, torso-link displacement [210.535718,-0.018994,-83.103159] mm. Training completion is not successful walking.

The initial experiment harness exited 1 after final rendering because its string assertion expected 0.52 rather than the correctly formatted 0.52000. Parsing the visible numeric time passed decoding, browser playback across three refreshes, matching-byte download and identity labels. Collection reused the existing final policy/rollout/video; no extra training, import or rendering. The result records training_exit 0, initial_experiment_exit 1 and collection_exit 0 separately. A final browser test confirmed successful probe3/done telemetry/240-point reward and loss histories, failed probe2/stale telemetry and all four prior/new playback videos at their recorded identities. Its initial assertion confused live page polling with stale run telemetry; the corrected telemetry-panel assertion passed. These harness mistakes are preserved in this account, and the original final-browser failure remains in the experiment log.

D4 gains successful active intermediate and retained final playback/download evidence; D8 gains the successful new attempt following the recorded real interruption; D2/D5 gain real retained historical training-model evidence, not a geometry-change lifecycle. D9 has a complete baseline ready for a review-driven design change. The project's PROGRESS.md now carries the seed-0 comparison and warns that rising reward did not improve survival. Seeds 1–9, actual design revision/retraining, copy/restart lifecycle and encoder-crash behavior remain unclaimed. Renderer throughput overhead remains unisolated. New training history is local and portable only when the full project (including ignored artifacts) is copied. No new dependency. The unfinished state/plan reconciliation is still separate work.

Validation: pixi run test-engine — 2103 passed, 54 skipped, 428.49 seconds, exit 0; focused CLI browser/record suite — 48 passed, 1 skipped, 51.46 seconds, exit 0. The engine suite overlapped training after the initial checkpoint video; MJX training tests skip in pixi. The full CLI suite starts only after the training scope exits, preventing test trainers from overlapping this experiment.

Full serial CLI gate: pixi run python -m pytest cli/tests -q — 361 passed, 1 skipped, 297.44 seconds, exit 0. Both product and external-project git diff --check passed. External project commit 7a597cc closes the evidence/progress entry; preceding CLI commits retain accepted policy imports and rollouts. docs/HEADLESS-BIPED-REVIEW.md is the compact committed evidence index. Hypergraph export/check passed before recording; the final recorded graph is checked again before commit. The contributor tail now contains this unit and quiet-arbor-0259; the stale plan remains for an authorized reconcile pass.

Dispatch closed: 1 unit — bounded successful biped retry with active checkpoint video, retained final video and honest seed-0 fall comparison.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 2f8d536f98237b159d61ce557b442d062a469e75

## State Impact

- target: candid-harvest-2614 — Probe3 checkpoint20 played/downloaded while training remained active; successful final policy/video decoded and browser-verified. Missing-trace render refusal leaves training active. Renderer throughput cost remains unisolated; no encoder-crash claim.
- target: cool-gate-3332 — Real probe3 training exited 0 following interrupted probe2; browser confirms new ok/done run and 240-point curves alongside prior failed/stale run and preserved videos. Initial final-browser harness formatting failure recovered using existing artifacts.
- target: shy-meadow-0959 — Real eight-component training snapshot retained declared placements/specs/documents; live and historical browser orbit/zoom and exact revision/digest checks pass after accepting checkpoint playback.
- target: sharp-union-6036 — Probe3 supplies a real immutable training snapshot and preserved earlier records across policy playback revisions; actual design-change/retraining lifecycle remains open.
- target: silent-river-6649 — Successful 240-iteration baseline now has intermediate and final verified playable videos. Same seed-0 eight-second task: checkpoint survives 8 seconds with 45.94 mm forward displacement; final falls at 0.52 seconds with 210.54 mm. Design revision and seeds 1-9 remain unmeasured.
