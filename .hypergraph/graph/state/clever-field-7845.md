---
node_id: c7376b1b-a383-509c-a933-2a8e3b25dcea
slug: clever-field-7845
title: D6. Save, reopen and restart preserve the project
created_at: '2026-09-12T14:51:25+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**Wren dashboard restart during real GPU training now passes.** Restart changed the service PID while exactly one trainer retained its PID/start ticks through every recovery sample. New telemetry reached the existing page after 0.957 s; seven observed commits arrived in 0.240–1.423 s. Historical `wren66-final` kept its same advancing, unpaused video and hash-matching download without page navigation. The bounded `wren71` attempt completed 240 GPU updates, preserving all 15 older run records. Reconcile judgement: this closes the concurrency limit of the earlier retained-artifact proof; it does not establish an engine restart during active training or a second-device test. Engine 2110 passed/53 skipped and CLI 415 passed/1 skipped, followed by 14 evidence tests and two strengthened lifecycle browser tests [rec: odd-pebble-9529].

**Current Wren saved-project reopen and persistent dashboard restart pass on retained real artifacts.** Two fresh engine processes preserve accepted revision `de9692bd4ee5…`, digest `cd99e3be1555…`, contract, attempt and accepted bytes. Of 2,004 inventoried files, only normal candidate rotation (42 added/42 pruned) and manifest timestamp change; dashboard restart changes no project file. All 15 run views plus ACCEPTED NOW retain identities, specs/decisions and three histories; current and historical videos play/download with recorded hashes. The open playing page recovers without navigation, and fresh visits select `wren66-final` with 90 mm feet and 240 points per history. That earlier proof had no active real trainer; the separate concurrency proof below supplies that evidence. Same-machine private-address and headless persisted-save scope only [rec: sunny-canyon-4438].

Verification for this proof: engine 2110 passed/53 skipped; full CLI invocation had 413 passed/1 skipped/1 failed on an incorrect fixture selection expectation. After correction, 14 focused tests and the failed-case rerun passed; no unresolved failure remains, but the original full invocation was not green [rec: sunny-canyon-4438].

**In-place restore now preserves accepted tessellation (ADR-303); D6 returns to `working`.** Identical revision/digest replay without an explicit display request retains the accepted artifact attempt and its pruning pin. A failing-before/passing-after real-engine regression, full engine suite (2110 passed, 53 skipped), staged lifecycle gate (16 passed) and full CLI suite (395 passed, 1 skipped) support the fix. Two fresh in-place Wren opens preserved accepted identity, attempt and all 28 retained files without a rebuild; persistent-browser identity, eight solids, twelve defaults, orbit/zoom and polling passed. Reconcile judgement: the demonstrated defect is resolved; Wren's remaining training lifecycle is a separate obligation [rec: late-walrus-6383].

**Earlier Reed save/reopen and restart evidence remains recorded with its scope.** Two real `cadexd` processes restore the saved accepted project with `performed=true` and `matches_accepted=true`; accepted identity and non-cache manifest fields match, and all 255 checked retained files remain byte-identical. Browser history, specs, curves and video playback/download survive restart and fresh-page reopen; cache timestamps, attempt and staging legitimately regenerate [rec: simple-quartz-9812].

During foot90 GPU training the private-address dashboard restarted while the same single trainer PID/start-tick identity advanced iterations 35–43. The same browser document labelled the outage stale, recovered without navigation, and displayed growing loss histories. Together with the completed-artifact restore evidence this closes the missing restart requirement: that observation establishes the training-restart requirement, separately from the repaired Wren restore defect and D7 copy isolation [rec: candid-forest-9800].

The automated lifecycle fixture also checks restart under a separate telemetry producer, preserving identities and video bytes; the real-training observation now supplies the evidence that fixture alone could not [rec: shady-bay-0771] [rec: candid-forest-9800].

Beyond-cache history has a 257-video synthetic browser regression: early and late run identities, distinct training histories, model/spec identity, playback and download digests survive a real dashboard-process restart. The original page observes stale then live without navigation. The fixtures repeat one historical model and 5,402-byte video across independent paths; this supplements real-biped evidence without claiming 257 policies, large-video throughput or a five-second bound. Eviction can still force all video bytes to be rehashed on each full scan [rec: weathered-sage-2750].

Charter criterion: **D6. Save, reopen and restart preserve the project** Save/reopen and restarting the dashboard and engine preserve accepted identity, specs, run history, curves and video access; restarting the dashboard during training neither stops nor duplicates that training. Evidence: an automated lifecycle test and a recorded pass on the fresh biped with real artifacts. Declared target `gap-d6-save-reopen-restart-preserve` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330].

## Negative knowledge

- [scope: identical accepted-artifact replay after ADR-303 | confidence: high | evidence: late-walrus-6383] Retention does not reconstruct missing or corrupt artifacts. Changed identities, explicit display requests and missing retained results publish a fresh attempt.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d6-save-reopen-restart-preserve`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- shady-bay-0771 — handoff record for the D6 restart test (commit 38c35f6a): dashboard restart under independent telemetry, and its stated limits
- simple-quartz-9812 — two real engine restores, dashboard restart and exact completed-artifact/browser preservation
- candid-forest-9800 — real dashboard restart preserves the single active GPU trainer and browser document; closes D6 restart gap
- weathered-sage-2750 — 257-video browser history survives process restart with explicit synthetic small-file limits
- mild-river-8224 — demonstrated in-place restore tessellation loss reopens D6; copy reopen evidence is explicitly narrower
- late-walrus-6383 — accepted-attempt retention repairs D6 with real in-place Wren byte preservation and source/packaged regressions
- sunny-canyon-4438 — current Wren retained-artifact engine reopen and measured service restart, with all histories/videos preserved and explicit test/concurrency limits
- odd-pebble-9529 — real Wren training continues through dashboard restart, with sub-five-second telemetry recovery and preserved historical playback
