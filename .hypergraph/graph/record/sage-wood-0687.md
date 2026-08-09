---
node_id: 13ca5c53-058a-59c4-b058-6d1ae6785359
slug: sage-wood-0687
title: 'Prehistory: MJC — dynamics on MuJoCo, on a permanent branch'
created_at: '2026-08-09T15:16:12+00:00'
parents:
- open-dew-7293
summary: 'Slices M0-M8 on a branch of its own: dynamics, contact, actuators, MJCF export, declarative tasks, offboard training and a policy rolled out in the viewport.'
---
## What

89 commits over two days on a branch called `MJC`: slices M0–M8, ADR-075…ADR-085.
Rigid-body dynamics, collision and contact, actuators, MJCF export, declarative
training tasks, offboard training, and a trained policy rolled out in the
viewport.

## Why

Branches from the standalone era. It depends on nothing after Phase 9 and
nothing depends on it, which is exactly what made it a separable vertical rather
than a fork in the roadmap.

The author wanted simulation, and deliberately did **not** build it out of
FreeCAD's native simulation or Blender's armature-based one. MuJoCo is a free,
robust platform for physics, robotics and reinforcement learning, and it is kept
**upstream and unmodified** — a kernel in the OCCT category, not a tree we fork
(ADR-075).

It started life as a *permanent* branch (ADR-078), on the argument that a
bracket modeller should not have to pay for a physics engine.

## Method

`CadexDynamics.py` — 7,296 lines and the largest module in the tree — does every
arithmetic operation **including every unit conversion**; the worker does every
FreeCAD read and nothing else, and a test greps to keep that true. The
dependency is `mujoco == 3.10.0`, exactly pinned for the same reason
`occt == 7.8.1` is, and it arrives as a **pypi wheel** carried by name through
`CARRIED_PYPI_PACKAGES` because the conda manifest has not been re-solvable
since conda-forge moved past the `occt` pin (ADR-076).

Slices are `M0`…`M8`, each a resting place, each with four test files: `*_api`
(the authoring surface and its refusals), `*_model` (what reaches the compiled
`mjSpec`), `*_measured` (numbers checked against a reference rather than against
ourselves) and `*_live` (the whole path through a real worker).

## Result

The arc closed at M8 (ADR-085): "design me a quadruped and teach it to walk" is
a sequence of chat turns that terminates in a viewport playing a learned gait.
The whole arc M0–M8 landed with an **empty `shell/` diff**.

**What each slice's own written plan got wrong is the most transferable part of
this record**, and the ADRs say so in as many words:
- **M3** — convex decomposition was not needed and is not in it: a concave part
  is *refused*, naming its volume error, because MuJoCo hulls a collision mesh
  silently. "Forced single-threaded" was never a flag; islands are a *disable*
  bit that was on by default, and the risk was constraint ordering, not threads.
- **M4** — there is no control callback. MuJoCo's position actuator *is* the PD
  loop, closed in C, so a script supplies a setpoint (a whitelisted formula of
  `time`). And joint damping was not a later slice: a stiff gain on an undamped
  joint rings at sixty degrees peak to peak for ever.
- **M5** — `to_xml()` writes six significant figures with no precision knob, so
  inertia round-trips to 2.4e-6 and "matches the in-engine simulation" is a
  measured tolerance, not an identity. The export reloads and diffs its own file
  before returning it, and refuses rather than writing.
- **M6** — MuJoCo's frame sensors take an `objtype` that reads as one thing and
  is two: `body` is the inertial frame and `xbody` the frame the assembly solver
  placed, a half turn apart on a plain box. A reward naming a component's
  position would silently have been handed its centre of mass.
- **M7** — `np.savez` *is* byte-deterministic (contradicting the plan outright),
  and a pure-Python forward pass runs at **4,564 Hz** against a 50 Hz control
  rate, so numpy stayed out of the engine entirely.

Three invariants came out of the arc and are all test-pinned: nothing in
`shell/` imports mujoco; `CadexDynamics.py` is reachable from the sandboxed
worker and **never** from `cadexd`; and no `jax` or `mjx` anywhere under
`src/Mod/cadex` or in a staged payload.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW dynamics-and-control — the whole arc from a solved assembly to a played-back policy, engine-side, behind the unchanged protocol.
