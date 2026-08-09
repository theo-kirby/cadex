---
node_id: e958634f-6903-5fe9-97e9-f37282ee3637
slug: solemn-chart-6274
title: 'Prehistory: the organic vertical — a robot wolf and the section cage'
created_at: '2026-08-09T15:16:12+00:00'
parents:
- open-dew-7293
summary: 'Phase 15 in a day: the agent gets eyes, blends that survive, mounts, clearance, and the section cage that answered VISION''s mesh-editing question.'
---
## What

Phase 15 — slices O0 through O3b in a single day (20 commits), ADR-123…ADR-130.
Making the shapes a person actually asks for — a body, a limb, a skin over a
mechanism — buildable by the agent and shapeable by the user without a chat
turn.

## Why

Follows from ADR-123, which closed by asking for a robot wolf to be rebuilt
against the repaired API surface. It was, and the result **sized the phase**:
the agent builds the wolf **entirely in `part`** — sixteen lofted solids, no
mesh op — so the gap is not "CAD is the wrong paradigm for organic shapes". It
is four specific things, one per slice.

## Method and Result

- **O0** (ADR-124) — the agent could not see what it built. `render_views` fits
  four cameras to the Model collection (front, right, top, three-quarter) and
  composites them 2×2 into one image, with the user's session isolated out of it.
  Verified by driving the built application, because the gate runs
  `--background` and `draw_view3d` needs a real VIEW_3D — the ADR says so rather
  than implying coverage the gate does not have.
- **O1 / O1b** (ADR-125, ADR-128) — blends that survive. `part.fillet` bisects a
  failing edge set and reports what it found (`on_failure` = refuse / skip /
  reduce); `part.fuse(blend=…)` names the seam edges *because it made them*. The
  wolf's weld lands: 25 of 48 seams at 8 mm, 25.04 s against a 13.61 s baseline.
  O1b then took the three things O1 parked, including a real kernel `scale_law`
  via a new `setLaw` on `BRepOffsetAPI_MakePipeShell` — two C++ additions that
  open `docs/FREECAD.md` §2a, the engine's own ledger of delta against upstream.
- **O2 / O2b** (ADR-126, ADR-130) — mounts as a declared interface with a static
  interference check that refuses in cubic millimetres (251.327 mm³ for a 4 mm
  peg seated 5 mm in, which is π·4²·5), and swept-volume clearance held over a
  whole trace.
- **O3** (ADR-127) — **the section cage**, which is what answers
  `docs/VISION.md`'s long-standing open question about interactive mesh editing.
  A shape is a `cage(...)` of superellipse rings the script declares,
  `part.loft_cage` builds and `set_params(cages=[…])` sets; the shell draws the
  rings as an edge-only overlay and supplies only the **gesture** — drag a ring,
  press Apply. Nothing is authored outside the script, the mesh domain gained no
  editing surface, and **no new space type was spent**.
- **O3b** (ADR-129) — rebuilding the wolf found that **one of its thirteen lofts
  enclosed 4.5× the volume of a straight loft through the identical sections**.
  `part.loft` and `part.loft_cage` now measure how far the surface escapes the
  sections they were built from and refuse past a quarter of their span. The
  wolf's half-width fell from ±150.2 mm to ±73.0 mm.

**O4 (subD) is parked and unscheduled** — and because the cage has now been used
in anger, what it still cannot do is known: a **curved spine** (the wolf's neck
and tail are the two bodies that stayed hand-written) and **closing an end**.
Neither is subdivision, and both come first.

The wolf (`~/arch/woof.cadex`) is the standing benchmark, with a per-slice
benchmark log in `docs/ORGANIC.md` §4. Those project files are **live**: copy to
a scratch directory before building or probing.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: NEW organic-modelling — cages, surviving blends, mounts and clearance; the wolf is the standing benchmark and O4 is parked with its two blockers named.
- target: NEW shell — `render_views` gives the agent its own eyes; the cage overlay supplies the gesture and nothing else.
