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

**D6 is repeated on the third fresh project, Lark.** Save/reopen through two fresh engine processes in place, with restore, kept the accepted revision, digest, attempt, contract and all 28 retained accepted-attempt files byte-identical (`matches_accepted: true`); the open persistent page and a fresh visit showed identical components, meshes, placements, parameters and documents, with viewport PNGs hash-equal before and after. Same-machine private-address check, no training involved [rec: honest-rain-3132].

**Wren dashboard restart during real GPU training passes.** Restart changed the service PID while exactly one trainer retained its PID/start ticks through every recovery sample; new telemetry reached the existing page after 0.957 s and seven observed commits arrived in 0.240–1.423 s. Historical `wren66-final` kept its same advancing video and hash-matching download without navigation. The bounded `wren71` attempt completed 240 GPU updates, preserving all 15 older run records. This closes the concurrency limit of the earlier retained-artifact proof; it does not establish an engine restart during active training or a second-device test [rec: odd-pebble-9529].

**Wren saved-project reopen and persistent dashboard restart pass on retained real artifacts.** Two fresh engine processes preserve accepted revision `de9692bd4ee5…`, digest, contract, attempt and accepted bytes; of 2,004 inventoried files only normal candidate rotation and manifest timestamp change; dashboard restart changes no project file. All 15 run views plus ACCEPTED NOW retain identities, specs/decisions and histories; current and historical videos play/download with recorded hashes [rec: sunny-canyon-4438]. In-place restore preserves accepted tessellation (ADR-303): identical revision/digest replay without an explicit display request retains the accepted artifact attempt and its pruning pin [rec: late-walrus-6383].

**Reed evidence remains recorded with its scope.** Two real `cadexd` processes restore the saved accepted project with `matches_accepted=true` and all 255 checked retained files byte-identical; browser history, specs, curves and playback survive restart and fresh-page reopen [rec: simple-quartz-9812]. During foot90 GPU training the dashboard restarted while the single trainer advanced iterations 35–43 and the browser document recovered without navigation [rec: candid-forest-9800]. The automated lifecycle fixture checks restart under a separate telemetry producer [rec: shady-bay-0771]; a 257-video synthetic browser regression shows early/late run identities, histories and download digests surviving a real process restart, with explicit small-file limits [rec: weathered-sage-2750].

Judgement: `working`. Save/reopen and restart preservation is demonstrated on real artifacts across Reed, Wren and Lark, and restart during real training on Reed and Wren. Engine restart during active training and any second-device test remain undemonstrated [rec: odd-pebble-9529] [rec: honest-rain-3132].

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
- honest-rain-3132 — Lark save/reopen through two fresh engine processes keeps identity and all 28 retained files byte-identical; page views hash-equal
