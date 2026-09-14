---
node_id: 02f9a989-8616-549c-95e7-c9d943b99a0b
slug: stormy-aspen-5433
title: F5. The arm is designed unassisted
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**The frozen Heron create attempt was dispatched once and refused by the provider session limit in 1.917 seconds (CLI exit 1).** There were zero completed design turns, zero continuations, no accepted revision and no actor design edits. Static fit, swept fit and inventory are unavailable. Smoke exited 1 because `script.json` does not exist; no simulation ran. The collector's exit 0 means evidence retention succeeded. The provider reported reset at 20:20 America/New_York [rec: quiet-dew-5243].

The portable receipt at `docs/probes/ot7/attempts/heron-refusal.json` retains transcript and artifact hashes; all eleven artifact hashes and sizes were verified, and 33 focused runner tests passed. This attempt must remain in closing-report accounting. There is no geometry to compare with ot6's accepted Heron. No retry or alternate provider was used [rec: quiet-dew-5243].

**A tested bounded evidence collector is ready at `docs/probes/ot7/runner/` (ADR-354).** It validates frozen prompt hashes, permits one create and at most three ordered continuations, refuses restart and automatic unfrozen follow-ups, and retains per-turn measured static fit, raw swept coverage, inventory, transcript hashes and one final bounded smoke. Provider errors/timeouts stop prompting; missing evidence and unavailable sweeps remain explicit. CLI validation passed 693 tests/1 skipped. At collector implementation, no design attempt had run [rec: peaceful-hill-3013].

**Heron's create prompt is frozen** at `docs/probes/ot7/prompts/heron.create.prompt.txt` (sha256 `bcda5af5…`), byte-identical to its ot6 prompt, with three ordered continuation prompts. No design turn has completed; F5 remains open [rec: silent-union-5108].

Charter criterion: **F5. The arm is designed unassisted.** Heron's ot6 create prompt, in a fresh project, reaches an accepted design with zero failing static and swept fit checks, zero actor edits, at most three frozen continuation prompts, catalog hardware for every purchased part, and a passing smoke rollout. Evidence: prompts and continuation count, per-turn fit failure counts, final fit report, inventory, smoke result, and the comparison with ot6. Declared target `gap-f5-arm-designed-unassisted-heron`; a record may say "ticks F5" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The ot6 comparison point is Heron (`civic-creek-8215`): one 9,648-byte prompt, a 24-minute turn, three measured corrections fed back by hand before acceptance. Prompts are frozen and committed under `docs/probes/ot7/prompts/` before the first design turn; a changed prompt starts a new attempt, and every attempt is reported. No policy training this run — smoke rollouts only, bounded to five minutes (F8). [rec: kind-dusk-1609]

Reconcile judgement: retain `open`; the actual refusal is evidence of an attempted dispatch, with no completed design, fit or smoke result. Zero measured pairs and zero failure count do not establish a pass [rec: quiet-dew-5243].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f5-arm-designed-unassisted-heron`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
- peaceful-hill-3013 — tested bounded frozen-design collector; no design attempt or fit/smoke success
- quiet-dew-5243 — single frozen Heron create refused; no accepted design or simulation, portable evidence retained
