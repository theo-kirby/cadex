---
node_id: 93712047-8855-5235-ba1e-0939a4b755bb
slug: light-orchard-1402
title: Prove Lark missing and partial video recovery without losing historical playback
created_at: '2026-09-13T09:44:04+00:00'
parents:
- windy-walrus-6950
summary: ''
---
## What

Exercised D8 missing/partial-video recovery on a disposable full Lark copy. Made the existing assertion-bearing video_recovery.py accept optional current/prior run names while preserving its Wren defaults. Extended the real-video browser regression to cover missing/truncated current files, full/range refusal, historical playback during damage, and restoration while history is playing. Published VIDEO95.md and compact video95-evidence.json; updated the lifecycle gap and operator status.

## Why

D8 is the selected criterion and the explicit new bet: retained-output damage must remain understandable and recoverable without losing historical playback. This implements the critic's requested experiment, replacing the banned audit/report-only bet. No training is needed to inject artifact faults into existing real Lark outputs. Disposable full copy is the reversible choice; the persistent operator project stays authoritative and untouched. This contributor dispatch prohibits reconcile, so no state/generated views or charter were edited.

## Method

Ran PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/video_recovery.py with the persistent private port 8765 URL, ot5-lark-copy85, a new external lark-video95-evidence directory, current lark86-retry-video and historical lark2-final. The script copied all 2,517 project files to a temporary sibling, verified their inventory, served that copy on the private address, then removed the current WebM, truncated it to 64 bytes and injected a failed-render receipt. Automatic polling observed each fault. Every state refused direct video access with 404, removed playback/download controls and displayed CLI repair guidance. Each time, historical lark2-final actually played through two refreshes and downloaded hash-equal. Restoring video and receipt recovered current playback in the same page, with the full copy inventory restored. The source inventory also stayed identical. Temporary copy removed by the probe; external screenshots/receipt retained. Persistent operator URL checked before and after, current identity and playback/download verified, service never restarted.

The browser regression uses actual renderer-produced videos and two open pages: current file damage/recovery plus historical playback preserved during restoration, including range-request refusal and return-to-current without navigation. Initial targeted test failed because background Chromium deferred media readiness; fixed the test to await the recovered player element in the background and verify media readiness in the foreground. No product code defect found. An initial shell edit used unavailable python; reran with python3 before any successful mutation/probe.

## Result

Lark now has its own D8 missing/partial-output recovery receipt, complementing iteration 86's real interrupted training and successful retry. Fault labels explicitly distinguish historical ready receipt from unavailable retained files; failed receipt names injected encoder failure and CLI recovery. Restored current video SHA-256 1f53d43d1c187de363eadae51931e90d91e8a7928e25ce5ebdb70df46322ca01; prior video af610491bedf8ed8d13b8bbc7c05c94954747d95f86514b387256148c84cf826. Operator still serves ot5-lark-copy85 / lark86-retry-video, revision 7f6c23913d55…, policy 074e22f1070c…, seed 0, 8 simulated seconds. No second-device check, new training, actual encoder-failure isolation or new recording claimed. No dependency, product behavior or inherited-tree change.

Handoff: this D8 experiment is now exercised, not an audit. Next distinct bet is D6: restart the persistent dashboard during one bounded real Lark training run, record the same trainer PID/start identity and increasing telemetry across restart, and retain operator current-run checks. Do not repeat provenance review. Remaining Lark-only real encoder-failure isolation is a separate D4 unit.

Validation: real Lark browser probe passed; pixi run test-engine: 2110 passed, 53 skipped (292.12 s). Full pixi run python -m pytest cli/tests -q loaded the pre-correction test: 445 passed, 1 skipped, 1 failed (460.02 s), solely the known background readyState assertion. Corrected final-source browser tests selected by 'current_run_gains_video or refuses_damaged_video': 2 passed, 45 deselected (26.33 s); the corrected expanded test also passed alone (16.10 s). No clean full-suite rerun claimed. No product, protocol or payload change, so no build or packaged gate required. git diff --check passed. Raw suite logs are external /tmp files; concise evidence committed in VIDEO95.md. Hypergraph export/check and record commit follow.
Dispatch closed: 1 unit — prove Lark D8 missing/partial-video recovery with historical playback and browser regression coverage

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 15b082b3406b1f26284498fd3ae075b2fffef667

## State Impact

- target: cool-gate-3332 — Lark full-copy missing/truncated/failed video probe now passes automatic fault guidance, historical playback/download and restored same-page access; expanded real-video browser regression passes.
- target: deep-clover-6012 — Persistent private dashboard verified before and after D8 faults, remains ot5-lark-copy85 / lark86-retry-video; all 2517 source files unchanged and service active.
