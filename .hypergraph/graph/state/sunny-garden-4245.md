---
node_id: b2e4c757-55b0-5ec0-aa43-641f631c0318
slug: sunny-garden-4245
title: R2. An arm reaches targets placed at random
created_at: '2026-09-30T07:04:58+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **R2. An arm reaches targets placed at random.** - Under a goal-sampling task (P3), the final pre-registered confirmation evaluation meets the frozen reach spec on every seed, and meets the judge's bar. - The spec covers tolerance, time and overshoot, over targets the policy never trained on. - The mechanism may be an earlier arm (Heron, ot6–ot8) or a new one designed by the product agent. [rec: kind-spire-3578]

Declared target: `gap-r2-arm-reaches-targets-placed`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

**The reach loop exists; the best policy passes 9 of 10 seeds; R2 is not claimed** [rec: silver-harvest-8970].

- **Project.** `ot11-heron-1`, a `cp -a` copy of `ot8-heron-b` (which stays read-only); model `183fabff…` (ot8's accepted MJCF), arm length 144.0 mm. The mechanism is fixed for the session, since a changed mechanism would move the held-out targets [rec: silver-harvest-8970].
- **Held-out targets.** Twenty targets drawn before any training by `runner/goals.py` (names no behaviour; uses the evaluation's own goal draw), committed in `retained/r2-heron-1-targets.json` with the session pre-registration (`02603727`). All four evaluations drew targets equal to the receipt within its rounding; no seed void [rec: silver-harvest-8970].
- **Frozen spec handed over byte for byte** through `prompts/reach.loop.prompt.txt`; `rounds.py` has no reach-specific path [rec: silver-harvest-8970].
- **Best policy** `3270ce26…` (round 4) passes 9 of 10 seeds; seed 1106 fails Q2 at 0.055 vs 0.05 arm lengths (0.7 mm) [rec: silver-harvest-8970].

**Still needed**: a policy that passes every seed, then a pre-registered confirmation evaluation and the blind judge's bar. [rec: silver-harvest-8970]

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- silver-harvest-8970 — reach loop on ot11-heron-1: twenty held-out targets pre-drawn, four rounds, best policy 3270ce26 passes 9 of 10 seeds
