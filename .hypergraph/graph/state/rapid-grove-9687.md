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

**The frozen Plover create attempt was dispatched once and refused by the provider session limit in 3.273 seconds (CLI exit 1).** Zero completed design turns, zero continuations and no accepted revision. Static fit, swept fit and inventory are unavailable; zero measured pairs is not a pass. Smoke exited before simulation because `script.json` does not exist. The portable receipt at `docs/probes/ot7/attempts/plover-refusal.json` retains transcript and artifact hashes; collector exit 0 means evidence retention succeeded. No actor design edit occurred [rec: red-hawk-4600].

Plover's create prompt is frozen at `docs/probes/ot7/prompts/plover.create.prompt.txt` (sha256 `b95f98b7…`) [rec: silent-union-5108]. The tested bounded collector retains per-turn fit, swept coverage, inventory, transcript hashes and a final bounded smoke, stopping on provider errors [rec: peaceful-hill-3013].

Charter criterion: **F7. The biped is designed unassisted.** The same bar as F5 on a biped prompt written and committed in this run's first unit, before any design turn: four MG90S servos from `lib.servo`, hip and knee pitch per leg, catalog horns, bearings and fasteners, modelled printable mounts, no world geometry. ot6 has no biped baseline, because Finch had no model turn. Declared target `gap-f7-biped-designed-unassisted-same`; a record may say "ticks F7" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

Finch (`cool-hill-9617`) is the buildable reference for what the hardware looks like — four MG90S, horns, MR128 bearings, M2 fasteners, five printed mounts, no world geometry — but it was written by the actor, so there is no agent turn to compare against. The prompt is the run's first unit, frozen before any design turn. [rec: kind-dusk-1609]

Reconcile judgement: the refusal supplies no unassisted design, fit or smoke success; retain `open`. ot6 has no product-agent biped baseline because Finch was actor-authored [rec: red-hawk-4600].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f7-biped-designed-unassisted-same`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
- peaceful-hill-3013 — tested bounded frozen-design collector; no design attempt or fit/smoke success
- red-hawk-4600 — single frozen biped dispatch refused; no accepted geometry or simulation; F7 remains open
