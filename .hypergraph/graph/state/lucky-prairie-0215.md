---
node_id: 56c3b7df-f631-5bd3-a580-a8bac365847e
slug: lucky-prairie-0215
title: W1. The whole lifecycle is watchable, on a real robot
created_at: '2026-10-05T08:57:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open orun3 charter criterion: **W1. The whole lifecycle is watchable, on a real robot.** [rec: golden-snow-6627]

- On `orun3-biped`, a copy of `~/cadex-projects/ot5-biped`: 1. the agent accepts at least two new design revisions through `cadex mcp`; 2. a short `cadex walk` training leg runs on the 5090 with checkpoints on; 3. `evaluate` runs on the result. [rec: golden-snow-6627]
- The dashboard, opened before step 1 and never reloaded, shows each stage in the overlay, the revisions on the timeline, and at least three checkpoint rollouts. Screenshots are taken at each stage. [rec: golden-snow-6627]
- Both full suites pass, and so does the packaged lifecycle gate if the run touched the protocol or the payload. [rec: golden-snow-6627]

Declared target: `gap-w1-whole-lifecycle-watchable-real`. This node tracks the criterion as a gap; it becomes working only with measured evidence, in a causally parented record, that the criterion is met. The owner ticks the charter box; roles do not. Truncated impact wording is resolved from the full charter in the same record [rec: golden-snow-6627].

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-w1-whole-lifecycle-watchable-real)
