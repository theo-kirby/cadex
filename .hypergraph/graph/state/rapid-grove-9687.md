---
node_id: 6eaf1262-e730-5dc4-93ff-9851660b5796
slug: rapid-grove-9687
title: F7. The biped is designed unassisted
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**A tested bounded evidence collector is ready at `docs/probes/ot7/runner/` (ADR-354).** It validates frozen prompt hashes, permits one create and at most three ordered continuations, refuses restart and automatic unfrozen follow-ups, and retains per-turn measured static fit, raw swept coverage, inventory, transcript hashes and one final bounded smoke. Provider errors/timeouts stop prompting; missing evidence and unavailable sweeps remain explicit. CLI validation passed 693 tests/1 skipped. No design attempt ran, so this criterion remains open [rec: peaceful-hill-3013].

**Plover's biped create prompt is written and frozen** at `docs/probes/ot7/prompts/plover.create.prompt.txt` (sha256 `b95f98b7…`): four MG90S, hip and knee pitch per leg, catalog hardware, five printable parts, a free base and no world geometry. No design turn has run; F7 remains open [rec: silent-union-5108].

Charter criterion: **F7. The biped is designed unassisted.** The same bar as F5 on a biped prompt written and committed in this run's first unit, before any design turn: four MG90S servos from `lib.servo`, hip and knee pitch per leg, catalog horns, bearings and fasteners, modelled printable mounts, no world geometry. ot6 has no biped baseline, because Finch had no model turn. Declared target `gap-f7-biped-designed-unassisted-same`; a record may say "ticks F7" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

Finch (`cool-hill-9617`) is the buildable reference for what the hardware looks like — four MG90S, horns, MR128 bearings, M2 fasteners, five printed mounts, no world geometry — but it was written by the actor, so there is no agent turn to compare against. The prompt is the run's first unit, frozen before any design turn. [rec: kind-dusk-1609]

Reconcile judgement: frozen prompts and collector fixtures establish readiness, but no unassisted design, fit or smoke result; retain `open` [rec: peaceful-hill-3013].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f7-biped-designed-unassisted-same`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
- peaceful-hill-3013 — tested bounded frozen-design collector; no design attempt or fit/smoke success
