---
node_id: f5b7827f-94be-5674-9bf1-327e24538d1c
slug: damp-flame-5523
title: P2. The product evaluates any policy against its task's spec
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **P2. The product evaluates any policy against its task's spec.** - The success spec is declared in xscript alongside the task, and is documented in `docs/XSCRIPT.md`. - One command evaluates an accepted policy on its frozen seeds. It writes a report into the project with: - pass or fail per seed and per predicate; - the reward decomposed term by term; - termination causes; - behaviour metrics; - the video and a filmstrip, on the dark floor. - The behaviour metrics include at least: - **gait:** step count, foot clearance, foot slip, duty factor and commanded-velocity tracking; - **reach:** final error, time to target and overshoot; - **balance:** tilt, drift from the start position, heading and the time to recover from a shove. - The review dashboard shows the report. Tests pin every metric on fixtures that pass and fail, and the w2-2 shuffle is one of the failing fixtures. [rec: kind-spire-3578]

Declared target: `gap-p2-product-evaluates-any-policy`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
