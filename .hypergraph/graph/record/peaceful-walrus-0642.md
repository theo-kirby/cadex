---
node_id: 72994191-bb17-58d2-bdb8-abe8802df82b
slug: peaceful-walrus-0642
title: Prove Lark dashboard restart during real GPU training preserves trainer identity and historical playback
created_at: '2026-09-13T09:58:04+00:00'
parents:
- light-orchard-1402
summary: ''
artifacts:
- docs/probes/lark-fresh/RESTART96.md
- docs/probes/lark-fresh/restart96-evidence.json
- docs/probes/lark-fresh/restart_training.py
---
## What

D6 experiment: restart the persistent Lark dashboard during real GPU training and retain evidence of trainer continuity, automatic live-page recovery, historical playback and terminal current-run identity. Added the bounded reusable driver and RESTART96 report/receipt; updated the lifecycle report and published operator status.

## Why

The critic explicitly requested the missing Lark D6 restart-during-training experiment instead of another D8 audit. This unit fills that named acceptance gap. Bet: a restart of the independent inspection service leaves the real trainer's PID/start identity and advancing telemetry intact. The experiment used the existing accepted 90 mm-foot copy, with no design change, extra trainer or new dependency. The stale general plan was not pursued.

## Method

Ran PYTHONPATH=cli:cli/tests pixi run python docs/probes/lark-fresh/restart_training.py PROJECT PRIVATE_URL lark96-restart lark86-retry-video. Public CLI export retained accepted model/task inputs, script, specs and training view. One GPU trainer ran 100 PPO iterations, 1024 environments, seed 0, with timeout 900 seconds plus 20-second kill grace and systemd MemoryMax=20G. The existing exclusion guard sampled trainer/pytest processes throughout; the full CLI suite ran only after this trainer exited.

The initial observer failed before restart because lark86-retry-video has the accepted revision and is labelled CURRENT. Preserved that failure, then ran docs/probes/wren-fresh/restart_training.py PRIVATE_URL PROJECT lark96-restart lark2-final during the same trainer. This observer passed. The driver now refuses same-revision historical input before creating a run; direct execution verified that refusal with no run directory created. The supervisor retained the initial observer failure even though training completed successfully; separate completion collection joined both receipts honestly. No full before/after inventory pass is claimed because that supervisor assertion was not reached.

## Result

D6's missing Lark-specific live restart evidence exists: dashboard PID 4073466 to 4173669, restart command 0.164 seconds; trainer PID 4168235 and start ticks 102226219 unchanged, telemetry 24 to 34. First resumed page update 0.585 seconds after restart, seven observed commits shown in 0.400–1.324 seconds. Historical lark2-final kept its revision/video element and playing state without navigation, downloaded hash-equal, and returned to the current run. Fresh visits before/after restart selected lark96-restart. Same-machine Chromium over the private address, no second-device claim.

Training exited 0 at iteration 99 on GPU, saved policy f7a152ff9c545716a37ee2a740c25895e154d9efaf2dbf3d3e155fcbe339b980. 4944 exclusion scans saw one trainer, no violation, maximum gap 0.0593 seconds. Peak host memory 5491826688 bytes below enforced 21474836480 bytes. Fresh completion page shows lark96-restart/completed, done telemetry, the accepted revision, and explicit no-recorded-video status. Port 8765 remains active on ot5-lark-copy85; no experiment trainer remains. No new video rendered or engine restart during training is claimed. Existing Lark save/reopen receipts supply the rest of D6; checkbox authority remains with the owner.

Handoff: attempted and corrected a same-revision historical observation, completed the requested D6 experiment, and did not repeat D8. Next bet is D4: exercise a real renderer failure during bounded Lark training, prove training survives, then produce a verified recording. That Lark-specific gap still relies on Wren. Three records now follow the checkpoint; no state nodes or generated views were edited and no reconcile was run, per this dispatch's explicit prohibition.

Final-source verification: pixi run python -m pytest cli/tests exited 0: 446 passed, 1 skipped in 435.57 seconds, including browser lifecycle/review/video coverage. Real observer and completion browser assertions passed; historical preflight refusal checked directly. git diff --check passed. No engine/payload/shell source changed; builds, engine suite and packaged gate were not run. docs/probes/lark-fresh/RESTART96.md and restart96-evidence.json retain compact evidence; large artifacts remain project-local.

Dispatch closed: 1 unit — prove persistent dashboard restart preserves real Lark training and historical playback.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 0aec45221882c0d9c0dcb6460bdbb32f18e46dd6

## State Impact

- target: clever-field-7845 — D6 now has Lark-specific real-training dashboard restart evidence: unchanged trainer PID/start ticks, advancing telemetry, preserved historical playback, terminal completion and bounded resources; initial same-revision observer failure disclosed.
- target: deep-clover-6012 — Persistent port 8765 remains active on ot5-lark-copy85, now defaulting to completed lark96-restart with explicit no-recorded-video state, verified before/after restart and on completion.
