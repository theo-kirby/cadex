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

**Lark dashboard restart during real GPU training passes, closing the last Lark-only D6 gap.** `docs/probes/lark-fresh/restart_training.py` (bounded, reusable) exported the accepted 90 mm-foot copy's model/task inputs, script, specs and training view through the public CLI, then ran one GPU trainer for 100 PPO iterations, 1,024 environments, seed 0 (timeout 900 s, 20 s kill grace, systemd `MemoryMax=20G`). Mid-run the persistent `cadex-operator-review` service was restarted: dashboard PID 4073466 → 4173669 in 0.164 s while the trainer's PID 4168235 and start ticks 102226219 were unchanged and telemetry advanced 24 → 34; the open page received its first resumed update 0.585 s after restart and seven observed commits in 0.400–1.324 s. Historical `lark2-final` kept its revision, video element and playing state without navigation, downloaded hash-equal and returned to the current run; fresh visits before and after selected `lark96-restart`. Training exited 0 at iteration 99, saving policy `f7a152ff9c54…`; 4,944 exclusion scans saw exactly one trainer (max gap 0.0593 s); peak host memory 5.49 GB under the 21.47 GB limit. The completion page shows `lark96-restart` completed with done telemetry, the accepted revision and an explicit no-recorded-video state. Disclosed: the initial observer failed before the restart because `lark86-retry-video` shares the accepted revision and is labelled CURRENT, so it could not serve as the HISTORICAL observation; the run was observed instead with `lark2-final` (that observer passed), the driver now refuses same-revision historical input before creating a run, the supervisor retained the initial failure, and no full before/after inventory pass is claimed because that assertion was never reached. No new video, no engine restart during training and no second-device claim. Evidence: `RESTART96.md`, `restart96-evidence.json`; CLI suite 446 passed/1 skipped after the trainer exited [rec: peaceful-walrus-0642].

**Lark save/reopen** through two fresh engine processes in place, with restore, kept the accepted revision, digest, attempt, contract and all 28 retained accepted-attempt files byte-identical (`matches_accepted: true`); the open persistent page and a fresh visit showed identical components, meshes, placements, parameters and documents, with viewport PNGs hash-equal before and after [rec: honest-rain-3132].

**Wren dashboard restart during real GPU training passes.** Restart changed the service PID while exactly one trainer retained its PID/start ticks through every recovery sample; new telemetry reached the existing page after 0.957 s and seven observed commits arrived in 0.240–1.423 s. Historical `wren66-final` kept its same advancing video and hash-matching download without navigation; the bounded `wren71` attempt completed 240 GPU updates, preserving all 15 older run records [rec: odd-pebble-9529]. Wren saved-project reopen and dashboard restart pass on retained real artifacts: two fresh engine processes preserve accepted revision `de9692bd4ee5…`, digest, contract, attempt and accepted bytes; of 2,004 inventoried files only normal candidate rotation and manifest timestamp change; all 15 run views plus ACCEPTED NOW retain identities and histories; current and historical videos play/download with recorded hashes [rec: sunny-canyon-4438]. In-place restore preserves accepted tessellation (ADR-303) [rec: late-walrus-6383].

**Reed evidence remains recorded with its scope.** Two real `cadexd` processes restore the saved accepted project with `matches_accepted=true` and all 255 checked retained files byte-identical; browser history, specs, curves and playback survive restart and fresh-page reopen [rec: simple-quartz-9812]. During foot90 GPU training the dashboard restarted while the single trainer advanced iterations 35–43 and the browser document recovered without navigation [rec: candid-forest-9800]. The automated lifecycle fixture checks restart under a separate telemetry producer [rec: shady-bay-0771]; a 257-video synthetic browser regression shows run identities, histories and download digests surviving a real process restart, with explicit small-file limits [rec: weathered-sage-2750].

Judgement: `working`. Save/reopen and restart preservation is demonstrated on real artifacts across Reed, Wren and Lark, and dashboard restart during real training on all three. Engine restart during active training and any second-device test remain undemonstrated [rec: odd-pebble-9529] [rec: peaceful-walrus-0642].

Charter criterion: **D6. Save, reopen and restart preserve the project** Save/reopen and restarting the dashboard and engine preserve accepted identity, specs, run history, curves and video access; restarting the dashboard during training neither stops nor duplicates that training. Evidence: an automated lifecycle test and a recorded pass on the fresh biped with real artifacts. Declared target `gap-d6-save-reopen-restart-preserve` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330].

## Negative knowledge

- [scope: identical accepted-artifact replay after ADR-303 | confidence: high | evidence: late-walrus-6383] Retention does not reconstruct missing or corrupt artifacts. Changed identities, explicit display requests and missing retained results publish a fresh attempt.
- [scope: the restart-during-training observers' historical-run argument (`wren-fresh/restart_training.py`, `lark-fresh/restart_training.py`) | confidence: high | evidence: peaceful-walrus-0642] A historical run that shares the accepted revision is labelled CURRENT, not HISTORICAL, so the observer's historical-playback assertion fails on it; the Lark driver now refuses such input before creating a run.

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
- peaceful-walrus-0642 — Lark dashboard restart during real 100-iteration GPU training: trainer PID/start ticks unchanged, telemetry advancing, historical playback preserved, terminal completion, bounded resources; same-revision observer failure disclosed (`RESTART96.md`)
