---
node_id: 291d3251-1c3e-555a-b9ff-7d5c514657f0
slug: scarlet-hill-8037
title: G4. The balancer's failed smoke has an actionable measured diagnosis
created_at: '2026-09-20T18:48:22+00:00'
parents:
- ancient-vine-9908
summary: ''
---
Status: open

## Current

**Open — declared by the ot8 charter, unattempted at the run's start [rec: keen-stone-1720].** On an **independent ot8 copy** of Robin, the ordinary holding smoke is reproduced and its cause distinguished between a geometry/export mismatch, a design defect, and missing feedback control, using published measurements and the MJCF/task contract. If a design defect is actionable, it is repaired using only the frozen product prompts and the allowed turns, and remeasured. If the required behavior needs feedback that this charter does not authorize, the **exact missing control contract** is recorded and that experiment stops [rec: keen-stone-1720].

The charter is explicit about the failure mode it is guarding against: a no-feedback inverted pendulum need not pass, and it may never be called a success, nor may a controller or any training be introduced quietly to make it one. Grounding the base, adding stabilizers, suppressing joints, weakening tolerances or shortening the declared smoke are all barred [rec: keen-stone-1720]. It inherits ot7's measured fact that a two-wheeled balancer given no torque falls over in under half a second, which is why `cadex smoke`'s support check reads attitude against the accepted keyframe since ADR-377 (`mild-ledge-7157`) [rec: humble-fox-6370].

## Negative knowledge

None yet.

## Provenance

- keen-stone-1720 — the criterion as the ot8 charter declares it, including the bars on hiding the failure
- humble-fox-6370 — the balancer's failed holding smoke as an ot7 outcome carried forward
