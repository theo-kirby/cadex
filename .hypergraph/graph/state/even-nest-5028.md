---
node_id: 5a295c7f-6d18-5f80-999d-8c78ba06074f
slug: even-nest-5028
title: P3. A task can say where to go
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **P3. A task can say where to go.** - A task can sample a goal per episode (and optionally change it during the episode), such as a reach target or a commanded velocity. The policy observes the goal, the reward and the spec can name it, and it is recorded in the trace. - The trainer and the engine's rollout agree on it exactly, and a test fails if they drift apart. - Training stays offboard: nothing in the engine imports JAX or MJX. [rec: kind-spire-3578]

Declared target: `gap-p3-task-can-say-where`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
