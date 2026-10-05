---
node_id: 51b9e291-00a3-505a-b224-ed28984761ad
slug: dry-rain-5997
title: V2. Each checkpoint becomes motion in the viewport
created_at: '2026-10-05T08:57:45+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open orun3 charter criterion: **V2. Each checkpoint becomes motion in the viewport.** [rec: golden-snow-6627]

- When a new checkpoint lands during a `cadex walk` training leg, the CLI rolls it out through the engine. It writes a `cadex-assembly-simulation-trace-v1` trace beside the checkpoint, tagged with the checkpoint's iteration, reward and sha256. [rec: golden-snow-6627]
- The rollout happens while training continues. **Measured:** mean iteration wall time with checkpoint rollouts on, against off, on the same task and seed. The cost is reported, and it is under 5% or an ADR explains why the owner should accept more. [rec: golden-snow-6627]
- The server serves each checkpoint's playback through the existing `trace_playback`. The 3D viewport loops the newest one, labelled with its iteration and reward. A checkpoint scrubber selects older ones, and switching to a newer checkpoint is automatic unless the owner has picked one. [rec: golden-snow-6627]
- A browser test against a real engine shows a second checkpoint's playback replacing the first one while the run is still training. [rec: golden-snow-6627]
- A failed rollout is shown with its reason. It never stops or slows the training run. [rec: golden-snow-6627]
- The traces are run outputs. They are never committed, and their disk cost per checkpoint is measured and reported. [rec: golden-snow-6627]

Declared target: `gap-v2-each-checkpoint-becomes-motion`. This node tracks the criterion as a gap; it becomes working only with measured evidence, in a causally parented record, that the criterion is met. The owner ticks the charter box; roles do not. Truncated impact wording is resolved from the full charter in the same record [rec: golden-snow-6627].

## Negative knowledge

None yet.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v2-each-checkpoint-becomes-motion)
