---
node_id: 48aeb71d-352a-574e-ae14-b240d0f5d9ab
slug: southern-otter-5999
title: The swept clearance check measures a component where the assembly puts it
created_at: '2026-09-08T02:40:05+00:00'
parents:
- simple-raven-2485
summary: ''
---
## What

The swept clearance check now measures a component where the assembly puts it
(ADR-242), closing the sibling defect ADR-241 named and deliberately left
open. `_clearance_at_frame` read `App::Link.Shape`, which *replaces* the
linked object's placement with the link's own instead of composing the two, so
every body whose transform rides on the shape — which is every `lib.*` part,
because `lib._place` moves a canonical body with one `part.transform` — was
swept in the frame it was authored in rather than the frame the assembly put
it in.

Landed as one commit: `_clearance_prepare` composes one re-placeable copy per
component **before** the frame loop and the loop writes only its placement;
`_component_world_shape` and it share a new `_linked_source_shape`; a
real-kernel regression in `test_swept_clearance.py`; the ADR-242 entry with
the before/after measurement table. The engine was rebuilt, installed and
staged, so the payload now carries both clearance fixes.

## Why

Charter criterion **"The agent can see its work without a screen"**
(`damp-moon-9297`): a clearance and intersection check that names the
offending pairs is one of its four calls, and until this landed the swept half
of it was not to be believed for catalog parts — ADR-241 said so in writing.
This was the overseer's named next unit and the second selected unit of the
short plan (`young-crane-9546`).

Assumption written down rather than asked: the plan's conditional said to
leave the installed bundle stale by one Python file; the overseer's later
message asked for `build-engine && stage-engine` folded in. The overseer wins,
and the one allowed build went there. The `.app` bundle in `/Applications` is
**not** refreshed — that belongs to the other selected unit (the pan-tilt
rerun), which is untouched.

## Method

1. **Measured before deciding**, as asked. A three-component sweep under
   `FreeCADCmd` with placements moved every frame the way `updateForFrame`
   moves them, world-authored throughout so pre- and post-fix source see
   identical geometry and spend identical distance queries, both modules
   loaded into one process (the pre-fix one from `git show HEAD:`). Three runs
   each. Box-rejected case (2000 frames, 286 queries): 0.429 / 0.422 ms/frame
   before, 0.374 / 0.378 after. Distance-queried case (300 frames, 900
   queries): 2.999 / 3.015 before, 3.043 / 3.044 after. Noise ~3% and ~1%.
   The sweep is *faster* where box rejection dominates — a `Link.Shape` read
   builds a shape, and the fix reads one composed copy per component instead
   of one per pair — and inside the noise where a real query dominates. The
   cost ADR-241 was worried about is not there, given the copy is hoisted.
2. **Fixed** with the cheap shape: `_clearance_prepare` before the loop,
   `component.Placement * shape.Placement` written per frame
   (`TopLoc_Location`, not geometry). A container source has no readable shape
   and is read live, exactly as ADR-241 decided.
3. **Regression first in shape, verified against pre-fix source.** A driver in
   the ADR-241 style: an arm whose geometry stands 20–50 mm out along its own
   +X (what `part.transform` produces) swung in 5° steps through 180° past a
   post authored in world coordinates at y 36–44. Post-fix: 36.674 mm at rest
   (`sqrt(16² + 33²)`, the arm's near corner to the post's) and 0.0 mm across
   frames 16–20. The identical driver against the pre-fix module: **33.0 mm at
   rest and an empty breach list** — the arm sweeps straight through the post
   and the promise reads as kept. The committed test asserts the post-fix
   truth without compat scaffolding; the pre-fix numbers are recorded here and
   in ADR-242.
4. **Gates.** Engine suite 2077 passed / 52 skipped (2076 before, plus the new
   regression). CLI 195 passed, no skips. `pixi run build-engine` and
   `stage-engine` both clean; the installed and staged workers carry
   `_clearance_prepare`. Packaged lifecycle gate against the fresh payload
   (`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64`): 15
   passed; both clearance suites against the same root: 14 passed. No `shell/`
   diff, so no shell gate. Staging reprinted its known external-rpath warnings
   (mujoco wheel, `tsp_solver.so`) — pre-existing, unchanged by this.

## Result

Landed as `79d40404`. A swept clearance breach on a catalog-placed part is now
a verdict a reader can believe: the surface that used to report a straight-
through collision as 33 mm of clear air reports it at 0.0 mm at the frame it
happens, and the check got slightly *cheaper* in the case it is designed
around.

Honest failure on the way: the first full engine run failed 34 tests and
errored 5 because the new helper was named `_component_local_shape`, which
already existed in the same module with a different signature and is used by
the MJCF export — the suite caught the shadowing in the live dynamics tests.
Renamed to `_linked_source_shape` and re-run clean. Nothing was committed in
between.

What is still missing before `damp-moon-9297` can be ticked: the four review
calls exist and the clearance one is now trustworthy in both its static and
swept halves, but the walk's review step has not been re-run end to end
against a bundle carrying these fixes — the `.app` bundle is still stale, and
the pan-tilt rerun that would exercise it is the other selected unit and was
not taken here. The unreconciled tail is now 2 nodes.

Dispatch closed: 1 unit — the swept clearance check composes the component and
shape frames (ADR-242), measured before and after, with a real-kernel
regression that reports no breach at all on the pre-fix source.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 79d404041bb2dc198c3cad1f7caff9e3437058a6

## State Impact

- target: damp-moon-9297 — The clearance and intersection review call is now trustworthy in both halves: ADR-242 fixes the swept check's frame the way ADR-241 fixed the static one, composing one re-placeable copy per component outside the frame loop. Measured before and after on identical geometry: 0.429 -> 0.374 ms/frame where box rejection dominates, 3.00 -> 3.04 where a distance query does (inside noise). A real-kernel regression swings a shape-placed arm past a world-authored post: 36.674 mm at rest and 0.0 mm across the quarter turn, where the pre-fix source reports 33.0 mm and no breach at all. The engine is rebuilt, installed and staged, so the payload carries both clearance fixes; the .app bundle is still stale.
- target: forest-wind-0342 — cadex_assembly_worker gains _clearance_prepare and _linked_source_shape; _component_world_shape and the swept check now share one reader for a linked body's own shape. No published field, protocol op, payload contract or content digest changed.
