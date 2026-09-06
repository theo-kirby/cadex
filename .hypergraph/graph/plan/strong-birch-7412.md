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

1. **Foreign-revision mutation safety (missions 1 and 2; witty-spark-2613, simple-willow-8989).** After current short work lands or is evidenced blocked, pin the shell stale-revision retry overwriting foreign accepted script/parameter values with a regression test, then remove blind replay or otherwise refuse the stale mutation within the owned shell surface. Prefer the smallest correction preserving accepted work; shared locking is an alternative to evaluate, not a requirement to hold a lock for the whole GUI session. Keep GUI documentation and the project scaffold true to the result, append the removal/direction ADR and update ROADMAP where applicable; run the shell gate headlessly. The documented sequential mode is evidence already landed, not proof of runtime concurrency safety. [rec: grand-fjord-0624] [rec: humble-bell-9017]
2. **L3 motors and mechanisms (mission 4; rising-banner-4325).** After L2 lands with its packaged gate: common BLDC sizes with kV and torque data, the N20 gearmotor, a linear actuator, a solenoid, joints — several family-sized units in L2's provenance, real-kernel and packaged verification shape, not a broad catalog rewrite. Gears and rack-and-pinion need involute profiles and stay their own slice under the long horizon's compound-mechanism item. [rec: golden-mist-0498] [rec: empty-wolf-3962] [rec: lone-wood-3732]
3. **Phase 8 src/Gui deletion (mission 3; civic-sand-2641).** Audit the existing disable evidence and residual dependencies before planning the delete commit; require the two-commit protocol, ADR, zone gate and honest manifest. Never treat BUILD_GUI=OFF alone as deletion permission or proof. [rec: empty-wolf-3962] [rec: lone-wood-3732]
4. **Two engine-side Phase 13b removals (mission 3; windy-pebble-4630, round-glacier-2865).** Audit candidates, then separate disable and delete units with build/test evidence and ADRs. Measure inherited delta against the run-start manifest as part of this work; retain green-sea-3991 until measured smaller, without concealing touched files. No replacement engine or shell. [rec: empty-wolf-3962] [rec: lone-wood-3732]
5. **The hide_render shell defect (mission 1 maintenance; wild-comet-8096).** Follow the current ladder after reductions unless evidence makes it an active lifecycle regression. Pin old behaviour with a failing test, fix the owned shell surface and run `pixi run gate` headlessly; keep inherited changes within the manifest contract. [rec: empty-wolf-3962] [rec: lone-wood-3732]
6. **Carry-over from short when evidenced blocked (missions 2 and 4).** Retain L2 boards or second-mechanism work here with the precise blocker and missing verification leg; do not retire their criteria. The completed GUI documentation dispatch does not return. Promotion still waits until remaining short work lands or is evidenced blocked. [rec: grand-fjord-0624] [rec: humble-bell-9017]

## Negative knowledge

- [scope: promotion order | confidence: medium | evidence: golden-mist-0498] The lifecycle rung's first two units landed in two iterations, so conditional promotion by evidence, not by clock, is working; medium is order, not a promise about the run.

## Provenance

- lone-wood-3732 — preserve gaps with conditional promotion
- empty-wolf-3962 — fold pending medium seed from the ladder
- golden-mist-0498 — L2 boards and the second mechanism promoted to short; L3 leads medium
- humble-bell-9017 — defer one explicit foreign-revision safety follow-up ahead of other medium gaps; preserve promotion gate
