---
node_id: 32a1444d-3d99-57c2-a648-5da32370d5cf
slug: chilly-reef-5960
title: S1. A grounded sensor reads a free body's position
created_at: '2026-10-07T17:58:00+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion for run orun5: **S1. A grounded sensor reads a free body's position.** The human owns the checkbox; roles report results and do not tick it [rec: honest-bay-2056].

- A new sensor kind measures a body's position, and optionally its
  velocity, in the frame of a named component: for example a touch panel
  on a plate reading a ball's x and y, or a camera on a mast reading a
  marker. It declares range, resolution, rate and noise (A1), and the
  trainer applies them. [rec: honest-bay-2056]
- A body outside the sensor's range reads as out of range, which the
  task can terminate on. It never reads as a stale or a clamped value. [rec: honest-bay-2056]
- `describe_api`, `docs/XSCRIPT.md` and `docs/MUJOCO.md` describe it. [rec: honest-bay-2056]
- Tests: the channel matches the body's true position in the
  component's frame through a tilt and a turn; out of range is reported;
  noise and quantisation follow the declaration; a task naming the
  channel trains without the "ungrounded" refusal. [rec: honest-bay-2056]

Not started: no record yet claims work against this criterion [rec: honest-bay-2056].

## Negative knowledge

None yet.

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-s1-grounded-sensor-reads-free)
