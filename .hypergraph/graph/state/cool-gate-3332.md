---
node_id: 94b5abb0-d87f-5b7b-85e4-6df4e380fce6
slug: cool-gate-3332
title: D8. Interrupted and failed runs remain understandable
created_at: '2026-09-12T14:51:25+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**D8 is repeated on the third fresh project, Lark, on its working copy `ot5-lark-copy85` and the persistent port 8765 page, never restarted.** A real GPU attempt `lark86-interrupt` (1,024 envs, seed 0, systemd scope with `MemoryMax=20G`) was sent SIGINT at iteration 5 after three page-observed updates; the page showed `failed`, the controlled-interruption note, `start a new cadex walk` guidance, six-sample curves and no substituted video without a reload, and a fresh visit selected it. A successful new attempt `lark86-retry` completed 40 updates (exit 0, `done` at 39/40, policy `074e22f1070c…`, witness 8.4e-8); that policy was declared through the public CLI, rolled out on seed 0 and rendered as `lark86-retry-video` (81 frames, 8.0 s), which decoded, played through polls and downloaded hash-equal. The historical interruption stays selectable after a refresh with return-to-current selecting the video run; the four earlier videos were re-checked after each outcome; the copy's 246 prior run files and 4 assets stayed byte-identical. Both suites ran to completion before any trainer (CLI 437/1 skipped, engine 2110/53 skipped) under the ADR-305 exclusion guard, and the driver `docs/probes/lark-fresh/interruption.py` is project-agnostic with its receipt test-guarded in `cli/tests` (ADR-315). One seed and 40 updates: no gait claim [rec: scarlet-ocean-2381].

**Wren's working copy has a clean real GPU interruption followed by a successful retry, with both outcomes readable on the persistent dashboard.** `wren57-interrupt` receives SIGINT at iteration 5 and retains failed/KeyboardInterrupt telemetry with six samples per curve; sequential `wren57-retry` exits 0 with completed/done status and twelve samples per curve. Browser checks verify explicit interruption/retry guidance, historical selection, return to current, and all four older videos [rec: fair-garden-6418]. ADR-305's repeat runs both suites to completion before training and guards against Python CPU/GPU trainers and pytest before launch and during browser waits; both sampled monitors observe at most one trainer — sampled observation, not a host-wide scheduler lock [rec: fair-garden-6418]. The first Wren probe retained two corrected harness defects and disclosed overlapping CLI CPU toy training [rec: small-wind-0172].

**Wren-specific browser evidence covers missing, partial and failed video output on an isolated full project copy.** Each fault refuses playback/download and media requests with CLI recovery guidance while historical `wren66-final` plays through polling; restoring the original files recovers `wren71-final` on the same page; all 3,769 original files and the restored copy inventory match [rec: fresh-timber-6139]. Video lists lead with verified current availability and retained/recorded counts, separately labelling the historical render outcome (ADR-310) [rec: blue-forest-5016].

Earlier Reed probe2 retained a harness-induced SIGTERM failure with stale telemetry and next-action guidance; probe3 subsequently completed 240 updates with retained videos. Checkpoint resume and encoder-crash coverage are not claimed here [rec: merry-star-6951] [rec: light-brook-2640]. Fault injection covers final-policy publication failures and missing/partial/stale telemetry [rec: long-cove-3626] [rec: kind-fountain-5086].

**Missing or damaged retained video is refused with CLI recovery guidance, and restoring the recorded bytes recovers same-page playback/download.** A real copied-Reed probe exposed the former existence-only check and verified the digest fix for missing/partial files while keeping prior foot90 playback available, all 418 protected copy files unchanged and all 1,206 source files matching. Recorded hashes govern UI, full and range requests; legacy video entries without hashes retain existence-only behavior [rec: icy-pond-7346]. Integrity checks reuse a bounded process-local digest cache keyed by resolved path, device, inode, size and nanosecond timestamps, with post-hash mutation refusal; regressions reject same-size corruption with restored mtime, atomic replacement, changed record hashes, escaping symlinks and mutation during verification [rec: young-cedar-2719]. During delayed verification the browser shows loading without playback, refuses corrupt bytes on release and resumes polling [rec: neat-vine-2517]; two-client coverage verifies one shared cold hash and a 257-file reader test proves 256-entry eviction [rec: dusty-oak-7376]; a 257-path synthetic lifecycle refuses same-size corruption across dashboard-process restart with all 4,122 project files matching [rec: weathered-sage-2750].

Judgement: `working`. Reed, Wren and Lark each have one real interrupted training attempt followed by a successful new one, readable on the persistent page, plus fault-injection coverage; Lark's retry additionally has a verified video. Same-machine private-address browser checks only; the owner's checkbox is not edited [rec: scarlet-ocean-2381].

Charter criterion: **D8. Interrupted and failed runs remain understandable** A controlled training interruption, a failed run, and missing/partial review output are tested; the dashboard distinguishes interrupted/failed/stale states from success, preserves prior completed results and explains the next CLI action. Evidence: fault-injection tests and one real interrupted biped training run followed by a successful new attempt; checkpoint resume is not required. Declared target `gap-d8-interrupted-failed-runs-remain` [rec: lucky-comet-0031].

## Negative knowledge

- [scope: the ot5-biped quota-refused creation attempts | confidence: high | evidence: zesty-star-7710] The provider refusal is absent from dashboard run history and has no automatic PROGRESS row; only accepted runs receive those rows. Readable empty-state guidance does not expose the provider error.
- [scope: the offboard trainer's progress snapshot | confidence: high | evidence: long-cove-3626] A hard kill, or a failure to write the progress file itself, produces no `failed` snapshot; observers see a stale training state instead.
- [scope: `docs/probes/lark-fresh/check_video.py` as of ADR-315 | confidence: high | evidence: scarlet-ocean-2381] It hard-codes eight components and the `-final`/`-checkpoint20` run-name pairing, which is why the retry's playback run is named `lark86-retry-video` rather than `-final`.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d8-interrupted-failed-runs-remain`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- zesty-star-7710 — empty-project browser regression and real refused-creation evidence
- kind-fountain-5086 — ADR-287 stale/failed/terminal telemetry labelling that these states render through
- long-cove-3626 — ADR-288: final policy publication failures publish failed telemetry; four browser fault-injection cases
- lucid-journey-6875 — the real failed `probe1` run and how the page reads it
- lively-gate-6535 — ADR-289: failed-run identity persists and is browser-covered through failure
- merry-star-6951 — real harness-induced interruption, explicit failed record and stale-state browser verification; subsequent success absent
- light-brook-2640 — successful real retry after interruption, with failed/stale and successful/done browser distinction
- icy-pond-7346 — ADR-295: damaged-video refusal and real copied-biped same-page recovery with histories preserved
- young-cedar-2719 — ADR-296: bounded digest cache retains integrity checks and real-copy recovery
- neat-vine-2517 — delayed-verification loading, corrupt-video refusal and subsequent polling regression
- dusty-oak-7376 — two-client integrity, changed-byte verification, cache eviction and real-copy recovery
- weathered-sage-2750 — beyond-cache corruption refusal across restart and restoration with 4,122 files preserved
- small-wind-0172 — Wren interruption/retry with retained probe defects and disclosed suite overlap
- fair-garden-6418 — ADR-305 guarded sequential repeat establishes clean interruption/retry evidence
- fresh-timber-6139 — Wren-only missing/partial/failed output recovery and historical playback with original files preserved
- blue-forest-5016 — ADR-310 separates current availability from recorded outcome; regressions and Wren recovery pass
- scarlet-ocean-2381 — Lark's D8 on the working copy: SIGINT-interrupted real attempt shown failed with guidance, successful retry with a verified video, history preserved (ADR-315)
