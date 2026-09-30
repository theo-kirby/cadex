---
node_id: de11b110-e5bb-5b0a-9481-031028136fa0
slug: staid-tooth-3475
title: R3. A balancer balances in place and recovers from a shove
created_at: '2026-09-30T07:04:58+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **R3. A balancer balances in place and recovers from a shove.** - The final pre-registered confirmation evaluation passes the frozen balance spec on every seed: upright, within position and heading bounds, and recovering from the declared shoves. - The judge's bar is met. - Robin (ot8/ot9) or a new balancer is copied into an `ot11-*` project. Robin's baseline policy is the ot9 one, and it stays read-only. [rec: kind-spire-3578]

Declared target: `gap-r3-balancer-balances-place-recovers`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

**A training round passes the frozen balance spec; R3 is not yet claimed** [rec: southern-quartz-3293]. Robin's new policy `8919a22d…` on `ot11-robin-1` (accepted revision `cbf14e3c…`; the iteration-400 checkpoint of the 900 s run `bal-1`, trained by the product agent through the loop) passes on 10 of 10 seeds, none void. Worst seed per predicate: B2 11.5° (limit 30), B3 0.92 COM heights (limit 2.0), B4 0.97° (limit 20), B5 0.42 s (limit 2.0); B1 all ten ran the full 10 s. The ot9 baseline drifted about 16 COM heights and turned 131°; it stays read-only in `ot9-robin` and undeclared in the copy's store. Filmstrips of seed 1101 are `docs/probes/ot11/p4-robin-1-bal-1-seed-1101-{overview,detail}.png`; the actor looked at the detail sheet (upright again 0.2 s after the 2.4 s shove), which is not the blind judge.

**Still needed**: a pre-registered confirmation evaluation at the final revision, and the blind judge's bar on seeds 1101, 1105 and 1110 (`runner/judge.py`). **Concern**: the policy reads an IMU declared on the Pi Zero board's component and encoders declared on the gearmotors; no IMU part is modelled and the catalog gearmotor has no encoder. ADR-408 accepts the declaration; whether R3's "supported path, accepted design" wants the parts modelled is for the confirmation unit [rec: southern-quartz-3293].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- southern-quartz-3293 — a training round: policy 8919a22d passes the frozen balance spec on 10 of 10 seeds; confirmation and judge still needed; undeclared-part sensor concern
