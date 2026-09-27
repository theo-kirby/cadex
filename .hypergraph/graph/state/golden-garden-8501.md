---
node_id: 57ef9ebf-21ac-59dc-8596-2d58e433ff5a
slug: golden-garden-8501
title: W2. The ADR-410 walking task is measured end to end
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot10: **W2. The ADR-410 walking task is measured end to end.** - One A5 design goes through `cadex walk` training with the unchanged ADR-410 overlay and `--stop-on-collapse`. Its settings and stop rule are recorded before it starts. - The policy is installed through the supported path, and its gait verdict, W1 video and training curve are published. - The bar is `walked = true`. - A policy that misses it is an honest incomplete result, with a diagnosis and a recorded next step. Do not weaken the gait thresholds to pass it. [rec: damp-dusk-8045]

Declared target: `gap-w2-adr-410-walking-task`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: damp-dusk-8045].

## Negative knowledge

None yet.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
