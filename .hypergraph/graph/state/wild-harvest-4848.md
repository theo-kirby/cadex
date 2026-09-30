---
node_id: 2fd26bda-3024-5527-9ba3-9a6aaa3e2b9f
slug: wild-harvest-4848
title: P4. The product agent runs the loop, and it is the same loop for every behaviour
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **P4. The product agent runs the loop, and it is the same loop for every behaviour.** - Through the ordinary product path, the agent can: - author or revise a task, its reward and its spec; - start bounded training; - read the progress, the evaluation report and the filmstrip; - decide the next revision. - This run chooses the architecture and records it in an ADR. Whatever it is, the loop takes no walking-specific branch. `cadex walk` becomes one use of it, or is retired in its favour, and the ADR says which. - The transcripts must show, for at least one behaviour, three or more rounds of design, train, evaluate and revise. Each revision must be motivated by a measurement from the previous evaluation, and the next evaluation must show whether it helped. [rec: kind-spire-3578]

Declared target: `gap-p4-product-agent-runs-loop`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
