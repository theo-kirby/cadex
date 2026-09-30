---
node_id: 9caf8458-637b-5a76-910b-ab872b7f9681
slug: rough-shore-6557
title: P1. Each behaviour has a frozen evaluation contract, and it catches the known failures
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **P1. Each behaviour has a frozen evaluation contract, and it catches the known failures.** - `docs/probes/ot11/README.md` freezes the following for walk, reach and balance, before any ot11 training run: - **a success spec:** measurable predicates on a rollout trace, independent of the reward; - **ten or more evaluation seeds**, with the reset variation and disturbances; - **a pass rule:** every seed must pass, unless the spec states a per-seed rate with its reason; - **a blind video judge:** a fresh model call that sees the frozen rubric, the task's one-paragraph intent and filmstrip frames of the rollout on the dark prototype floor, and nothing else; - **the judge's pass bar.** - **Known negatives are measured before anything new is trained:** - ot10's `w2-2` shuffle must fail the walk spec, and must fail it for the right reason (stepping, foot clearance or slip), not by accident. - ot9's Robin policy is measured against the balance spec. If it wanders, the spec must say so. - Changing a frozen item later is a recorded decision that re-evaluates every earlier policy. [rec: kind-spire-3578]

Declared target: `gap-p1-each-behaviour-has-frozen`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
