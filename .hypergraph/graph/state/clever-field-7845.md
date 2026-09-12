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

**Real biped save/reopen, engine restore and dashboard restart now have completed-artifact and active-training evidence.** Two real `cadexd` processes restore the saved accepted project with `performed=true` and `matches_accepted=true`; accepted identity and non-cache manifest fields match, and all 255 checked retained files remain byte-identical. Browser history, specs, curves and video playback/download survive restart and fresh-page reopen; cache timestamps, attempt and staging legitimately regenerate [rec: simple-quartz-9812].

During foot90 GPU training the private-address dashboard restarted while the same single trainer PID/start-tick identity advanced iterations 35–43. The same browser document labelled the outage stale, recovered without navigation, and displayed growing loss histories. Together with the completed-artifact restore evidence this closes the missing restart requirement: status is `working`; it does not establish D7 copy isolation [rec: candid-forest-9800].

The automated lifecycle fixture also checks restart under a separate telemetry producer, preserving identities and video bytes; the real-training observation now supplies the evidence that fixture alone could not [rec: shady-bay-0771] [rec: candid-forest-9800].

Beyond-cache history has a 257-video synthetic browser regression: early and late run identities, distinct training histories, model/spec identity, playback and download digests survive a real dashboard-process restart. The original page observes stale then live without navigation. The fixtures repeat one historical model and 5,402-byte video across independent paths; this supplements real-biped evidence without claiming 257 policies, large-video throughput or a five-second bound. Eviction can still force all video bytes to be rehashed on each full scan [rec: weathered-sage-2750].

Charter criterion: **D6. Save, reopen and restart preserve the project** Save/reopen and restarting the dashboard and engine preserve accepted identity, specs, run history, curves and video access; restarting the dashboard during training neither stops nor duplicates that training. Evidence: an automated lifecycle test and a recorded pass on the fresh biped with real artifacts. Declared target `gap-d6-save-reopen-restart-preserve` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330].

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d6-save-reopen-restart-preserve`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- shady-bay-0771 — handoff record for the D6 restart test (commit 38c35f6a): dashboard restart under independent telemetry, and its stated limits
- simple-quartz-9812 — two real engine restores, dashboard restart and exact completed-artifact/browser preservation
- candid-forest-9800 — real dashboard restart preserves the single active GPU trainer and browser document; closes D6 restart gap
- weathered-sage-2750 — 257-video browser history survives process restart with explicit synthetic small-file limits
