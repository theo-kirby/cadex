---
node_id: e849d528-e05a-5133-bd7d-919d1f81e69c
slug: strong-birch-7412
title: medium
created_at: '2026-09-06T19:21:31+00:00'
parents:
- fond-ember-4937
summary: ''
---
Status: open

## Current

1. **L3 motors and mechanisms (mission 4; rising-banner-4325).** N20, the bounded HOBBYWING BLDC envelope and nominal L12 have source, real-kernel and packaged evidence. Joint qualification and conditional delivery move to short because the solenoid audit landed and delivery is blocked on its source contract. Retain solenoid implementation as an open deferred leg: restart only with new revision-matched mounting/travel evidence, a qualified alternative, or a separately justified narrower contract and decision; do not repeat the same searches or silently weaken the bar. After joint work lands or is evidenced blocked, qualify remaining L3 scope against ROADMAP, including common BLDC sizes and kV/torque/coupling limitations, before choosing the next bounded unit; full L3 is not closed. Each delivery requires provenance, real-kernel tests and packaged verification. L12's nominal 102–152 mm centres establish no powered reachability, physical inertia, fit or conservative collision envelope. Compound gearing stays long; reductions remain next after this family sequence resolves or is blocked. [rec: idle-dawn-5426] [rec: floral-stone-2866] [rec: frosty-snow-9642] [rec: frosty-creek-6723] [rec: open-pine-9349] [rec: clever-falcon-0085]
2. **Phase 8 src/Gui deletion (mission 3; civic-sand-2641).** Audit the existing disable evidence and residual dependencies before planning the delete commit; require the two-commit protocol, ADR, zone gate and honest manifest. Never treat BUILD_GUI=OFF alone as deletion permission or proof. [rec: empty-wolf-3962] [rec: lone-wood-3732]
3. **Two engine-side Phase 13b removals (mission 3; windy-pebble-4630, round-glacier-2865).** Audit candidates, then separate disable and delete units with build/test evidence and ADRs. Measure inherited delta against the run-start manifest as part of this work; retain green-sea-3991 until measured smaller, without concealing touched files. No replacement engine or shell. [rec: empty-wolf-3962] [rec: lone-wood-3732]
4. **The hide_render shell defect (mission 1 maintenance; wild-comet-8096).** Follow the current ladder after reductions unless evidence makes it an active lifecycle regression. Pin old behaviour with a failing test, fix the owned shell surface and run `pixi run gate` headlessly; keep inherited changes within the manifest contract. [rec: empty-wolf-3962] [rec: lone-wood-3732]
## Negative knowledge

- [scope: deferred solenoid delivery | confidence: high | evidence: open-pine-9349] The 412 proof is partial; older TAU mounting separation conflicts (20 versus 18.2 mm), and Ledex B7 lacks sourced engagement depth and maximum mechanical travel. Do not transplant slots or use the force-plot endpoint as a travel stop. No solenoid API shipped; these bounded searches do not disprove other variants. Resume only on new source evidence or a separately justified contract, not another identical partial model.

- [scope: foreign-revision safety follow-up | confidence: high | evidence: still-badger-2386] The dispatched defensive refusal fix and refresh recovery have gate evidence; it is no longer queued work. Real-engine overwrite was not reproduced. Concurrent acceptance and rebuilds still require sequential use; this is not a general locking guarantee.

- [scope: promotion order | confidence: medium | evidence: golden-mist-0498] The lifecycle rung's first two units landed in two iterations, so conditional promotion by evidence, not by clock, is working; medium is order, not a promise about the run.

## Provenance

- lone-wood-3732 — preserve gaps with conditional promotion
- empty-wolf-3962 — fold pending medium seed from the ladder
- golden-mist-0498 — L2 boards and the second mechanism promoted to short; L3 leads medium
- humble-bell-9017 — defer one explicit foreign-revision safety follow-up ahead of other medium gaps; preserve promotion gate

- nimble-glade-6200 — L2 and second mechanism landed; promote safety and N20 while retaining multi-unit gaps

- strong-grotto-8980 — fold completed safety/N20 units; preserve broader L3 and all reduction gaps

- western-water-1442 — retain L12 delivery after sourced BLDC; preserve all remaining charter gaps

- sunny-lily-7639 — both L12 units landed; promote bounded solenoid work and preserve all broader gaps

- clever-falcon-0085 — promote joints after solenoid source follow-up; preserve deferred delivery and all charter gaps
