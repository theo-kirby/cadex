---
node_id: 3254c4b8-1257-59b1-beaf-936345a4ab9f
slug: light-timber-5868
title: Clearance measures a component where the assembly puts it
created_at: '2026-09-08T02:09:04+00:00'
parents:
- empty-banner-7438
summary: ''
---
## What

**Fixed the clearance frame for `lib.*`-placed components**, regression first.
`_measure_clearance` read `component.Shape`; an `App::Link` *replaces* the linked
object's placement with its own instead of composing the two, so any body whose
transform rides on the shape was measured back in the frame it was authored in.
Every `lib.*` part is exactly that body — `lib._place` moves a canonical
origin-and-+Z part with one `part.transform`, and `Shape.translate`/`rotate` write
a placement rather than moving geometry.

Two commits: `cf3b77a6` (the failing-then-fixed real-kernel regression, the fix and
ADR-241) and `0a1a1fbe` (the corrected numbers on the assembly that found it).

## Why

The overseer's ordered directive for this dispatch, and the plan's short rung rank 2
(`young-crane-9546`): the previous unit's pan-tilt walk (`empty-banner-7438`) ran
clean but proved the review leg's clearance numbers false for catalog parts. It sits
on **`damp-moon-9297`** — *the agent can see its work without a screen* — which the
lifecycle walk's review step depends on and which could not be ticked while an
"intersection" verdict was a lie. Charter criterion advanced: `damp-moon-9297`.

The diagnosis in `empty-banner-7438` was a hypothesis fitted to two arithmetic
coincidences; this unit read the failing line and confirmed it in the kernel before
changing anything.

## Method

Ordered as the overseer asked.

**1. Confirm the mechanism, in the kernel.** Under `FreeCADCmd`: a box translated
+50 mm keeps its placement through a BREP round-trip and through `Part::Feature`
(the placement moves onto the object); an `App::Link` at identity to that feature
reports the box back at **0–10 mm**, and at +100 mm reports **100–110** rather than
the composed **150–160**. `Part.getShape(link)` does the same. A link to an
`App::Part` *container* composes correctly, because the group applies the child's
placement. That is the whole defect and its one exception.

**2. The regression, failing first.** `test_clearance_scope.py::
test_a_shape_placed_component_is_measured_where_it_is` — a `FreeCADCmd` driver in
the `test_boards.py` pattern (skipped without a binary), driving `_measure_clearance`
over four real `App::Link` components: shape-placed at +50, world-authored at
identity, both-frames-placed (+50 shape, +100 component), and a genuine 2 mm overlap.
No `SimpleNamespace`. **On the pre-fix source it fails**, reporting the shape-placed
pair 0.0 mm apart sharing 999.999… mm³ where the truth is 40.0 mm and nothing.

**3. The fix, smallest diff.** One helper, `_component_world_shape`: the linked
object's shape with `component.Placement * shape.Placement`. That is the composition
the MJCF export already uses (body frame from the component, geometry from the source
shape), so the review surface now agrees with the physics. A container source keeps
`component.Shape`, and a component with no readable linked shape falls through to the
same error path as before, so the existing stub tests are untouched.

**4. Rerun.** `pixi run build-engine`, then the pan-tilt project rebuilt through
`cadex params --set base_size=50.0` (its current value) and re-reported with
`cadex clearance`, with the engine environment overrides unset.

## Result

**The regression fails on the old source and passes on the new**, with the numbers
that discriminate: pre-fix `AB` = 0.0 mm / 999.999… mm³, post-fix 40.0 mm / 0.0 mm³;
the both-frames body at 150–160 mm rather than 100–110 (`BC` 140.0, `CD` 132.0); and
a real 2 mm overlap at its true **200 mm³** instead of the whole 1000 mm³.

**Engine gate: 2076 passed, 52 skipped, no failures** (321 s). **CLI gate: 195
passed, no skips** (219 s) — the same count as the recorded baseline. No shell,
payload or protocol change, so no shell gate was required or run.

**On the assembly that found it**, every number `empty-banner-7438` predicted from
the four independent surfaces came back:

| pair | before | after | the independent surfaces said |
|---|---|---|---|
| servo_pan / servo_tilt | intersection, 8240.943 mm³ | **clear, 25.9 mm** | disjoint, ~26 mm apart |
| base / servo_tilt | intersection, 1112.640 mm³ | **clear, 57.9 mm** | the exported STL's own lower bound is 57.9 |
| base / servo_pan | intersection, 1112.640 mm³ | **intersection, 111.264 mm³** | real, a 0.4 mm sink ≈ 111.3 mm³ |

Exactly a tenth of the old figure, and the two containment lies gone. **Three
contacts the wrong frame had hidden now appear**: pan servo in the yoke
(18.857 mm³), tilt servo in the yoke arm (75.430 mm³) and in the head plate
(73.500 mm³) — all previously reported "clear" at 27, 27 and 46.5 mm because the
servos were being measured at the origin. So the frame error was not only inflating
false positives, it was suppressing true ones. Those interferences are the pan-tilt
project's design business, not this fix's.

**Left undone, deliberately, and named in ADR-241 and the commit message:**
`_clearance_at_frame` — the swept clearance check inside the simulation trace —
reads the same link shape and has the same defect. It runs per pair per frame over
thousands of frames, so composing a shape copy in that loop is a cost that needs its
own measurement before it is paid. **Until it lands, a swept breach distance for a
`lib.*`-placed body is not to be believed either.** That is the next unit on this
thread.

Also not claimed: the *installed bundle* still carries the old behaviour — it was
not rebuilt or staged, so a walk run against `--engine <bundle>` would still report
the old numbers. `cadex params`/`clearance` above resolved the development tree
(`"source": "dev-tree"`), which is what carried the fix. Clearance remains
initial-pose only, and the pan-tilt walk itself was not re-run end to end: the
review leg's own report was regenerated instead, which is the leg the defect was in
and costs no tokens. No GUI launch, no remote dispatch.

**`damp-moon-9297` is closer but not tickable**: its render, section and inventory
calls are verified, and clearance now measures where the assembly puts a part, but
the swept sibling is still wrong and the walk has not been re-run end to end against
a staged bundle carrying the fix.

The unreconciled tail is now three nodes (`salty-nest-8235`, `empty-banner-7438`,
this one), which is the maintainer's threshold; that pass is not mine to run.

Dispatch closed: 1 unit — clearance now composes the component and shape frames, proved by a real-kernel regression that fails on the old source and by the pan-tilt assembly's corrected numbers.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 0a1a1fbed5f91440ba0ab9f9216806b38bcb9988

## State Impact

- target: damp-moon-9297 — Pair clearance now composes the component placement with the shape's own, so lib.*-placed catalog parts are measured where the assembly puts them; two false intersections and a 10x-inflated volume corrected on the pan-tilt assembly and three hidden contacts revealed, pinned by a real-kernel regression. The swept per-frame check keeps the same defect.
