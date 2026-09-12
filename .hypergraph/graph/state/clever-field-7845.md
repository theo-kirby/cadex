---
node_id: c7376b1b-a383-509c-a933-2a8e3b25dcea
slug: clever-field-7845
title: D6. Save, reopen and restart preserve the project
created_at: '2026-09-12T14:51:25+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

**Real completed biped artifacts survive engine restores and dashboard restart; restart during actual training remains open.** Two real `cadexd` processes restore the saved accepted project with `performed=true` and `matches_accepted=true`. Accepted revision/digest and all non-cache manifest fields stay equal, and all 255 checked retained files are byte-identical. Cache `updated_at`, `attempt_id` and `staging` legitimately regenerate [rec: simple-quartz-9812].

Before/after browser observations match run history, historical model identities, parameters/document links and loaded model statistics. Probe3 retains 240 reward/loss/episode-length samples; checkpoint and final videos advance playback and download at their recorded hashes. The original page recovers stale-to-live without navigation across dashboard restart, and a fresh page reopens the same saved project. This tests previously durable acceptance, not a new authoring transaction; no trainer, render or policy import ran [rec: simple-quartz-9812].

The automated lifecycle fixture independently exercises restart while a separate telemetry producer keeps its PID and sequence, preserving identities and video bytes [rec: shady-bay-0771]. Keep `open`: that producer is not a real trainer. Dashboard restart during actual biped training without stopping or duplicating it remains required, as does no claim here of copy isolation [rec: simple-quartz-9812].

Charter criterion: **D6. Save, reopen and restart preserve the project** Save/reopen and restarting the dashboard and engine preserve accepted identity, specs, run history, curves and video access; restarting the dashboard during training neither stops nor duplicates that training. Evidence: an automated lifecycle test and a recorded pass on the fresh biped with real artifacts. Declared target `gap-d6-save-reopen-restart-preserve` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330].

## Negative knowledge

None yet.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d6-save-reopen-restart-preserve`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- shady-bay-0771 — handoff record for the D6 restart test (commit 38c35f6a): dashboard restart under independent telemetry, and its stated limits
- simple-quartz-9812 — two real engine restores, dashboard restart and exact completed-artifact/browser preservation
