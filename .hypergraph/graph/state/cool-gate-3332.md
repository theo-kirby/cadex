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

**Lark now has its own missing/partial/failed-video recovery receipt, so D8's retained-output evidence no longer rests on Wren alone.** The existing assertion-bearing `docs/probes/wren-fresh/video_recovery.py` gained optional current/prior run-name arguments (Wren defaults preserved) and was run against the persistent port 8765 URL with `ot5-lark-copy85`, current `lark86-retry-video` and historical `lark2-final`. It copied all 2,517 project files to a temporary sibling, verified the inventory, served that copy on the private address, then removed the current WebM, truncated it to 64 bytes and injected a failed-render receipt. Automatic polling observed each fault; every state refused direct and range video access with 404, removed the playback/download controls and displayed CLI repair guidance, with labels distinguishing a historical ready receipt from unavailable retained files and the failed receipt naming the injected encoder failure. Each time historical `lark2-final` actually played through two refreshes and downloaded hash-equal; restoring video and receipt recovered current playback on the same page (restored SHA-256 `1f53d43d1c18…`, prior `af610491bedf…`), the copy inventory was restored and the source inventory stayed identical. The temporary copy was removed; the persistent service was verified before and after and never restarted. The real-video browser regression now covers missing/truncated current files, full/range refusal, historical playback during damage and restoration while history plays, on two open pages. Evidence: `docs/probes/lark-fresh/VIDEO95.md` and `video95-evidence.json`. Suites: engine 2110 passed/53 skipped; the full CLI run loaded the pre-correction test (445 passed, 1 skipped, 1 failed on the background readyState assertion), and the corrected browser tests passed selected (2/2) and alone; no clean full-suite rerun claimed. No product-code defect, no actual encoder-failure isolation, no new training or recording [rec: light-orchard-1402].

**D8 is repeated on Lark's working copy `ot5-lark-copy85` and the persistent port 8765 page, never restarted.** A real GPU attempt `lark86-interrupt` (1,024 envs, seed 0, systemd scope with `MemoryMax=20G`) was sent SIGINT at iteration 5 after three page-observed updates; the page showed `failed`, the controlled-interruption note, `start a new cadex walk` guidance, six-sample curves and no substituted video without a reload, and a fresh visit selected it. A successful new attempt `lark86-retry` completed 40 updates (exit 0, policy `074e22f1070c…`, witness 8.4e-8); that policy was declared through the public CLI, rolled out on seed 0 and rendered as `lark86-retry-video` (81 frames, 8.0 s), which decoded, played through polls and downloaded hash-equal. The historical interruption stays selectable after a refresh; the four earlier videos were re-checked after each outcome; the copy's 246 prior run files and 4 assets stayed byte-identical. Both suites ran to completion before any trainer under the ADR-305 exclusion guard, and the project-agnostic driver `docs/probes/lark-fresh/interruption.py` has its receipt test-guarded in `cli/tests` (ADR-315). One seed and 40 updates: no gait claim [rec: scarlet-ocean-2381].

**Wren's working copy has a clean real GPU interruption followed by a successful retry, both readable on the persistent dashboard.** `wren57-interrupt` receives SIGINT at iteration 5 and retains failed/KeyboardInterrupt telemetry with six samples per curve; sequential `wren57-retry` exits 0 with twelve samples per curve. Browser checks verify interruption/retry guidance, historical selection, return to current, and all four older videos. ADR-305's repeat runs both suites to completion before training and guards against Python trainers and pytest before launch and during browser waits — sampled observation, not a host-wide lock [rec: fair-garden-6418]; the first Wren probe retained two corrected harness defects and disclosed overlapping CLI CPU toy training [rec: small-wind-0172]. Wren's own missing/partial/failed video receipt refuses playback/download and media requests with CLI recovery guidance while historical `wren66-final` plays, and restoring the original files recovers `wren71-final` with all 3,769 original files matching [rec: fresh-timber-6139]. Video lists lead with verified current availability and separately label the historical render outcome (ADR-310) [rec: blue-forest-5016].

Earlier Reed probe2 retained a harness-induced SIGTERM failure with stale telemetry and next-action guidance; probe3 subsequently completed 240 updates with retained videos. Checkpoint resume and encoder-crash coverage are not claimed here [rec: merry-star-6951] [rec: light-brook-2640]. Fault injection covers final-policy publication failures and missing/partial/stale telemetry [rec: long-cove-3626] [rec: kind-fountain-5086].

**Missing or damaged retained video is refused with CLI recovery guidance, and restoring the recorded bytes recovers same-page playback/download.** A real copied-Reed probe exposed the former existence-only check and verified the digest fix for missing/partial files while keeping prior foot90 playback available. Recorded hashes govern UI, full and range requests; legacy video entries without hashes retain existence-only behavior [rec: icy-pond-7346]. Integrity checks reuse a bounded process-local digest cache keyed by resolved path, device, inode, size and nanosecond timestamps, with post-hash mutation refusal; regressions reject same-size corruption with restored mtime, atomic replacement, changed record hashes, escaping symlinks and mutation during verification [rec: young-cedar-2719]. During delayed verification the browser shows loading without playback, refuses corrupt bytes on release and resumes polling [rec: neat-vine-2517]; two-client coverage verifies one shared cold hash and a 257-file reader test proves 256-entry eviction [rec: dusty-oak-7376]; a 257-path synthetic lifecycle refuses same-size corruption across dashboard-process restart with all 4,122 project files matching [rec: weathered-sage-2750].

Judgement: `working`. Reed, Wren and Lark each have one real interrupted training attempt followed by a successful new one, readable on the persistent page, and each now has its own missing/partial/failed-output recovery receipt on an isolated copy; Lark's retry additionally has a verified video. Same-machine private-address browser checks only; the owner's checkbox is not edited [rec: scarlet-ocean-2381] [rec: light-orchard-1402].

Charter criterion: **D8. Interrupted and failed runs remain understandable** A controlled training interruption, a failed run, and missing/partial review output are tested; the dashboard distinguishes interrupted/failed/stale states from success, preserves prior completed results and explains the next CLI action. Evidence: fault-injection tests and one real interrupted biped training run followed by a successful new attempt; checkpoint resume is not required. Declared target `gap-d8-interrupted-failed-runs-remain` [rec: lucky-comet-0031].

## Negative knowledge

- [scope: the ot5-biped quota-refused creation attempts | confidence: high | evidence: zesty-star-7710] The provider refusal is absent from dashboard run history and has no automatic PROGRESS row; only accepted runs receive those rows. Readable empty-state guidance does not expose the provider error.
- [scope: the offboard trainer's progress snapshot | confidence: high | evidence: long-cove-3626] A hard kill, or a failure to write the progress file itself, produces no `failed` snapshot; observers see a stale training state instead.
- [scope: `docs/probes/lark-fresh/check_video.py` as of ADR-315 | confidence: high | evidence: scarlet-ocean-2381] It hard-codes eight components and the `-final`/`-checkpoint20` run-name pairing, which is why the retry's playback run is named `lark86-retry-video` rather than `-final`.
- [scope: the real-video browser regression's background page under headless Chromium | confidence: high | evidence: light-orchard-1402] Chromium defers media readiness on a background page, so asserting `readyState` there fails spuriously; the test awaits the recovered player element in the background and verifies media readiness only in the foreground page.

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
- light-orchard-1402 — Lark's own missing/truncated/failed-video probe on a disposable full copy with historical playback preserved; expanded real-video browser regression (`VIDEO95.md`)
