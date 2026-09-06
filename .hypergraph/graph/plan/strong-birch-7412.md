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

1. **Foreign-revision mutation safety (missions 1 and 2; witty-spark-2613, simple-willow-8989).** The concrete fix is promoted to short. Keep this runtime gap until work supplies regression and headless shell-gate evidence; if blocked, retain the exact missing leg here. Shared locking remains an alternative only if evidence requires it, not a separate mandatory project. [rec: grand-fjord-0624] [rec: nimble-glade-6200]
2. **L3 motors and mechanisms (mission 4; rising-banner-4325).** L2's packaged evidence has landed and one N20 family is promoted to short. Remaining common BLDC sizes with sourced kV/torque data, linear actuator, solenoid and joints follow in bounded family units, each with provenance, real-kernel and packaged verification. Retain unfinished N20 gates here if blocked; never close the whole L3 criterion from one family. Gears and rack-and-pinion need involute profiles and remain the long horizon's compound-mechanism slice. This continues the prior family order before reductions. [rec: stormy-quill-5350] [rec: nimble-glade-6200]
3. **Phase 8 src/Gui deletion (mission 3; civic-sand-2641).** Audit the existing disable evidence and residual dependencies before planning the delete commit; require the two-commit protocol, ADR, zone gate and honest manifest. Never treat BUILD_GUI=OFF alone as deletion permission or proof. [rec: empty-wolf-3962] [rec: lone-wood-3732]
4. **Two engine-side Phase 13b removals (mission 3; windy-pebble-4630, round-glacier-2865).** Audit candidates, then separate disable and delete units with build/test evidence and ADRs. Measure inherited delta against the run-start manifest as part of this work; retain green-sea-3991 until measured smaller, without concealing touched files. No replacement engine or shell. [rec: empty-wolf-3962] [rec: lone-wood-3732]
5. **The hide_render shell defect (mission 1 maintenance; wild-comet-8096).** Follow the current ladder after reductions unless evidence makes it an active lifecycle regression. Pin old behaviour with a failing test, fix the owned shell surface and run `pixi run gate` headlessly; keep inherited changes within the manifest contract. [rec: empty-wolf-3962] [rec: lone-wood-3732]
## Negative knowledge

- [scope: promotion order | confidence: medium | evidence: golden-mist-0498] The lifecycle rung's first two units landed in two iterations, so conditional promotion by evidence, not by clock, is working; medium is order, not a promise about the run.

## Provenance

- lone-wood-3732 — preserve gaps with conditional promotion
- empty-wolf-3962 — fold pending medium seed from the ladder
- golden-mist-0498 — L2 boards and the second mechanism promoted to short; L3 leads medium
- humble-bell-9017 — defer one explicit foreign-revision safety follow-up ahead of other medium gaps; preserve promotion gate

- nimble-glade-6200 — L2 and second mechanism landed; promote safety and N20 while retaining multi-unit gaps
