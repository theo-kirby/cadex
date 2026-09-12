---
node_id: 94b5abb0-d87f-5b7b-85e4-6df4e380fce6
slug: cool-gate-3332
title: D8. Interrupted and failed runs remain understandable
created_at: '2026-09-12T14:51:25+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

**A real harness-induced training interruption is retained and browser-readable; a subsequent successful new attempt remains open.** Probe2's collector sent SIGTERM after an erroneous browser time-format assertion. Last committed iteration was 38; telemetry remains `training` and becomes stale, final policy absent. Its explicit failed/interrupted run record identifies the harness failure and next action. Browser checks passed for failed status, stale telemetry and continued access to the prior final-policy and checkpoint20 videos [rec: merry-star-6951].

Probe1 trained and stored its policy but failed at declaration; its original failed record remains unchanged [rec: lucid-journey-6875]. ADR-289 preserves run identity and specs from walk start through failure, with browser coverage [rec: lively-gate-6535]. ADR-288's trainer failure handler publishes failed telemetry for final-policy publication errors, with four browser fault-injection cases preserving metrics, identity and checkpoints [rec: long-cove-3626]. Missing/partial output and stale-state coverage comes from the telemetry work [rec: kind-fountain-5086].

Keep `open`: no successful new training attempt followed the real interruption. The external harness failure is not a product-renderer failure; browser/render failure must not stop training. The historical collector briefly wrote an empty progress snapshot, restored by the trainer's next update; future collectors must only read telemetry [rec: merry-star-6951].

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
