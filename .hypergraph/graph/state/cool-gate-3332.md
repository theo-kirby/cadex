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

**A successful new GPU attempt now follows the retained real interruption, with both outcomes readable in the browser.** Probe3 exits 0 after 240 iterations; the browser shows `ok`/done with 240-point reward/loss histories alongside failed probe2's stale telemetry and the preserved prior/new videos. The final browser harness formatting failure is corrected using existing artifacts and separately recorded from successful training [rec: light-brook-2640].

Probe2's external collector previously sent SIGTERM after a faulty browser assertion, leaving iteration 38 and no final policy. Its explicit failed/interrupted record explains the harness failure and next action; failed status, stale telemetry and prior video access passed browser checks [rec: merry-star-6951]. Fixture fault-injection covers final-policy publication failures and retained metrics/checkpoints; missing/partial and stale telemetry have separate coverage [rec: long-cove-3626] [rec: kind-fountain-5086].

Judgement: mark `working` because the successful retry closes this node's declared remaining gap. This does not claim checkpoint resume or an encoder-crash test: the real interruption was harness-induced, and probe3's render failure test covers missing-trace refusal with the trainer still active [rec: light-brook-2640].

**Missing or damaged retained video is refused with CLI recovery guidance, and restoring the recorded bytes recovers same-page playback/download.** A real copied-Reed probe exposed the former existence-only check and verified the digest fix for missing/partial files while keeping prior foot90 playback available, all 418 protected copy files unchanged and all 1,206 source files matching. Recorded hashes govern UI, full and range requests; legacy video entries without hashes retain existence-only behavior [rec: icy-pond-7346].

Integrity checks now reuse a bounded process-local digest cache keyed by resolved path, device, inode, size and nanosecond modification/change timestamps, with current path/digest checks and post-hash mutation refusal. Regression coverage rejects same-size corruption with restored mtime, atomic replacement, changed record hashes, escaping symlinks and mutation during verification. Real-copy missing/truncated/restored playback recovery still passes and preserves all 418 protected files [rec: young-cedar-2719].

During delayed verification the browser shows loading without playback, refuses corrupt bytes on release and resumes status polling [rec: neat-vine-2517]. Two-client coverage verifies one shared cold hash, corruption refusal in both pages and fresh verification after atomic byte replacement; a 257-file reader test proves 256-entry eviction. Real Reed-copy recovery still preserves all 418 protected files [rec: dusty-oak-7376].

A 257-path synthetic browser lifecycle additionally refuses same-size corruption with restored mtime after cache churn and dashboard-process restart, including full/range HTTP requests. The intact late video remains playable; atomic restoration recovers early playback/download and all 4,122 project files match their original content. These small repeated video fixtures establish correctness, not large-video throughput or new GPU evidence [rec: weathered-sage-2750].

Charter criterion: **D8. Interrupted and failed runs remain understandable** A controlled training interruption, a failed run, and missing/partial review output are tested; the dashboard distinguishes interrupted/failed/stale states from success, preserves prior completed results and explains the next CLI action. Evidence: fault-injection tests and one real interrupted biped training run followed by a successful new attempt; checkpoint resume is not required. Declared target `gap-d8-interrupted-failed-runs-remain` [rec: lucky-comet-0031].

## Negative knowledge

- [scope: the ot5-biped quota-refused creation attempts | confidence: high | evidence: zesty-star-7710] The provider refusal is absent from dashboard run history and has no automatic PROGRESS row; only accepted runs receive those rows. Readable empty-state guidance does not expose the provider error.
- [scope: the offboard trainer's progress snapshot | confidence: high | evidence: long-cove-3626] A hard kill, or a failure to write the progress file itself, produces no `failed` snapshot; observers see a stale training state instead.

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
