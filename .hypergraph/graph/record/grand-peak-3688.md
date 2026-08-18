---
node_id: 9ea30d86-0d12-535f-a540-54491079b283
slug: grand-peak-3688
title: 'The section view: a capped boolean cut, and the clip plane it is not'
created_at: '2026-08-17T16:42:54+00:00'
parents:
- forest-wind-3489
summary: ''
---
## What

The shell can cut the model open (ADR-148). A **section view**: a plane
through the hydrated model, the near half taken away, and the cut face
**capped** so what you see is material rather than the inside of an empty
shell. New module `shell/scripts/addons_core/mesh_agent/cadex_section.py`
(~560 lines), one operator and one header button beside Collision and
Dimensions, a control box in the parameters editor (axis / offset in mm /
flip), and one agent tool, `section_view`.

Zero engine change, zero protocol change, and no line outside
`mesh_agent/` + `shell/tests/python/`.

## Why

Nothing on the outside of a solid says what is inside it: a bore that did
not break through, a wall left thinner than asked for, a pocket that missed
the boss it was meant to clear. Before this the only tools for that class of
question were `inspect` plus arithmetic — the same shape of blind spot the
collision overlay was built for (ADR-091), where two shipped bugs were found
by arithmetic after the fact.

The agent is a first-class user of this: it is the caller of
`viewport_screenshot`, and it could not see inside its own work.

## Method

**The mechanism was chosen by measurement, not by taste.** Blender already
has a half-space clip (`rv3d.clip_planes`, what Alt+B sets) and it is free.
Three probes against the real bundle (Blender 5.3.0 Alpha) settled it
against:

- a clip cannot fill what it opens — the cut reads as a hollow shell;
- clip planes are per-region view state, so `capture`'s
  `GPUOffScreen.draw_view3d` renders would not carry the cut at all;
- `pixi run gate` runs `--background`, where no `RegionView3D` exists, so
  nothing about it could be gated.

A Boolean DIFFERENCE modifier against one hidden, scaled unit-cube cutter
was probed instead and does cap: 8 verts / 6 polys / **1 polygon lying in
the cutting plane** on a cut 20 mm cube, with the cutter hidden by the eye,
by the monitor icon, or visible — visibility does not affect a boolean
operand, which is what lets the cutter be invisible to `scene.ray_cast` and
therefore unable to steal a face pick.

The edge wires needed a second mechanism (a boolean has nothing to say about
a mesh with no faces): an eight-node geometry-nodes group that deletes
points past the plane, with the plane converted into each object's own frame
in Python, since geometry nodes read `Position` locally and a component
instance's wire child sits at its solved placement. Blender 5.3 moved a
nodes modifier's inputs to a generated RNA interface — four probes to find
that `modifier.properties.inputs.<Socket_N>.value` is the assignment path
(`modifier["Socket_N"] = …` now raises `id properties not supported for this
type`).

**One premise did not survive.** `obj.bound_box` reflects *evaluated*
geometry: with the cut on, the model's measured top **is** the cut (a 20 mm
cube cut at z = 5 reports a top of 5). Every number derived from the model —
the centre of the axis, the cutter's size, the range the panel reports —
would have fed back on the cut that produced it, so
`cadex_section.model_bounds` reads the mesh datablocks with numpy instead,
and `capture.render_views` suspends the section *before* it measures.

Verification: `test_the_section_view_cuts_the_model_open` in
`shell/tests/python/bl_mesh_agent_cadex.py`, against the bundled engine on a
blind-bore part (40×30×20 block, 10 mm deep bore that does not break
through), plus a scratch smoke of 31 assertions over the module's own API.

## Result

The full gate is green (`CADEX-BLENDER-GATE … "ok": true`, exit 0), with
nothing else moved: picking fidelity 1.0 (372/372), slider-drag median
0.494 s against the 0.65 s bar.

New evidence in the gate report:

- `"section": {"caps": 1, "bore_wall_points": 17}` — the cut face is capped,
  and the blind bore's wall appears **in** that cut face, which is the thing
  a person turns a section on to see. A clip plane can produce neither.
- `"section_cut_seconds": 0.0062` — **6.3 ms** per offset change, end to
  end, on that part. The slider it shares a viewport with is budgeted at
  650 ms.

Also asserted, and each of these is a claim that could have gone the other
way:

- **the accepted revision is unchanged** either side of switching the
  section on — it is a view, not a feature (`docs/VISION.md`: nothing
  happens outside the script);
- **a rebuild under the cut keeps it**, and the cut applies to the shape
  that came back — modifiers ride on the object while `cadex_hydrate` swaps
  the mesh datablock, so hydration needed no change at all; the only hook
  `cadex_backend.hydrate` gained is a `refresh` call, because a brand-new
  output is a new object with no modifier on it;
- a ray cast still finds the part and never the cutter;
- `suspend()` / restore round-trips, which is what keeps `render_views`
  answering "what did I build";
- off leaves no modifier, no cutter and no node group anywhere.

Deliberately not done: the plane is never clamped to the model. A slider
that refuses to leave the part lies about where the part is, so the panel
and the tool say "the plane is clear of the model" instead.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: be7ff63d8766f3cede9545152af00a5e01c06fe8

## State Impact

- target: shy-crane-2573 — The shell gains a section view (ADR-148): a hidden cutter box plus a capped Boolean DIFFERENCE modifier on each hydrated solid and a geometry-nodes clip on each edge wire, aimed by axis/offset/flip in the parameters editor and by a section_view agent tool. Chosen over rv3d.clip_planes because a clip cannot cap, is per-region view state no offscreen render carries, and cannot be seen at all from --background where the gate runs. Measured 6.3 ms per offset change; the gate asserts the cut face is capped, that the blind bore's wall appears in it, that a rebuild under the cut keeps it, and that the accepted revision is unchanged either side of switching it on -- it is a view, not a feature. cadex_hydrate needed no change; obj.bound_box reflects evaluated geometry, so the section measures mesh datablocks rather than bounds.
