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

**Heron's create prompt is frozen** at `docs/probes/ot7/prompts/heron.create.prompt.txt` (sha256 `bcda5af5…`), byte-identical to its ot6 prompt, with three ordered continuation prompts. No design turn has run; F5 remains open [rec: silent-union-5108].

Charter criterion: **F5. The arm is designed unassisted.** Heron's ot6 create prompt, in a fresh project, reaches an accepted design with zero failing static and swept fit checks, zero actor edits, at most three frozen continuation prompts, catalog hardware for every purchased part, and a passing smoke rollout. Evidence: prompts and continuation count, per-turn fit failure counts, final fit report, inventory, smoke result, and the comparison with ot6. Declared target `gap-f5-arm-designed-unassisted-heron`; a record may say "ticks F5" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The ot6 comparison point is Heron (`civic-creek-8215`): one 9,648-byte prompt, a 24-minute turn, three measured corrections fed back by hand before acceptance. Prompts are frozen and committed under `docs/probes/ot7/prompts/` before the first design turn; a changed prompt starts a new attempt, and every attempt is reported. No policy training this run — smoke rollouts only, bounded to five minutes (F8). [rec: kind-dusk-1609]

Reconcile judgement: the prompt prerequisite is evidenced, but the design or repair result is not; retain `open` [rec: silent-union-5108].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f5-arm-designed-unassisted-heron`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
