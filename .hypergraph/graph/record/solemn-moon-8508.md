---
node_id: 3d65c52c-9464-5c28-9eda-a51560dffb7e
slug: solemn-moon-8508
title: 'ADR-581: smoke''s first-frame agreement measures pairs as the engine published them'
created_at: '2026-10-07T00:55:02+00:00'
parents:
- curious-trail-5191
summary: ''
---
## What

ADR-581, commit `8a8d7cff`. `cadex smoke`'s first-frame agreement check (`cli/cadex_cli/smoke_geometry.py`) now measures each pair the way the engine published it:
- a culled row by the exact-box gap (ADR-423);
- any other row by the distance between the two shells' compounds (ADR-425).

Before, both used a solid's `distToShape`. That call answers 0 whenever OCCT's point classifier calls a vertex of one solid inside the other. A new regression test nests a sphere in a box; it fails without the change and passes with it.

## Why

The critic accepted done and asked for three new directions, the most valuable one, and one unit of it. It also asked to keep the gates green and to open no new scope or style.
- **What I did instead of writing to the plan.** The plan is a state node, and a work iteration may not write one. The three directions are therefore here, for the planner or reconcile to fold.
- **Why this direction.** It is the open `cadex smoke` defect in the orun4 report (defect 2), found by the G2 fresh-session check. It is existing scope, not a new feature. It also serves the mission: a fresh agent's legged design should pass the product's own smoke check.

The three directions, ranked:
1. **Smoke reads true on an agent's first design** (chosen). Three blockers, one unit each:
   - (a) the first-frame refusal (this unit);
   - (b) threaded bolt engagement counted as overlap;
   - (c) the exact stage's per-frame cost on 60+ components.
2. **Fix the style's `first_contact` roll-limit procedure.** The second fresh session found it gives a limit inside the collision when inward is the negative direction (`docs/probes/orun4/FRESH-SESSION-2.md`).
3. **Widen the CLI suite's margin.** It runs 474 s against the 480 s target, about 5 s of margin.

## Method

1. Copied `~/cadex-projects/orun4-fresh-legged-2` (an orun4 scratch project) to `/tmp` and ran `cadex smoke`. It reproduced: `initial pose disagrees with published clearance: ('foot_l', 'shin_r')`.
2. Instrumented the check temporarily (since reverted). The measured distance was 0.0 against a published culled bound of 60.995594590128576 mm. The boxes are 61 mm apart on Y.
3. Probed with FreeCADCmd. `shin_r.isInside((-18.25, 65.63, 11.0))` is True, although the shin's box ends at y = -23.7. The `distToShape` support is ('Vertex', -1), the inner solution. Shell-to-shell distance is 67.10 mm, and the exact-box gap equals the published bound to the last digit.
4. Fixed the check to measure the engine's way. Added the nested-sphere test and confirmed it fails with the old file stashed and passes with the new one.
5. Re-ran the child on the real 2,080-pair plan, frame 0 only, then 3 frames. The full `cadex smoke` run on the copy then hit the 300 s bound.

## Result

What is true now:
- The first-frame agreement passes on the real design: no error, 2,080 pairs, frame 0 in 64.7 s.
- `test_smoke_geometry_bound.py` has 2 tests, both green. The new one fails without the fix.
- The design still does not pass smoke, and that result is now honest. There are two causes, both measured:
  - (b) 33 failing pairs, every one a bolt against the part it threads into, at 4.5–10.3 mm³. The per-frame check ignores the static row's fit intent.
  - (c) each later frame costs about 5.5 s on 66 components. The default 101-frame trace needs about 10 minutes against the shared 300 s bound, so the whole command reports `exact smoke geometry exceeded the shared wall-time bound`.
- Next unit: (b) or (c). (c) likely reuses ADR-436's rule, that a positive shell distance proves zero common volume.
- The fresh session's own description, "a sub-1e-5 mm mismatch", was wrong. The real mismatch was 61 mm. `REPORT.md` §7 and its ADR table are updated.
- Engine code is untouched; the change is under `cli/` only.
- Gates at `8a8d7cff`: the CLI suite as one foreground command with the GPU hidden passed, 1212 passed and 1 skipped in 473.3 s (still under 480 s). `pixi run test-engine` passed, 2611 passed and 59 skipped in 345.3 s. No engine rebuild or packaged gate was needed, since nothing under `src/` or the payload changed.
- The reconcile tail is one record (this one).

Dispatch closed: 1 unit — smoke's first-frame agreement measures pairs as the engine published them (ADR-581)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 8a8d7cffdb028c3d8c66a3f5cacb6e55962420e1

## State Impact

- target: salty-isle-4063 — cadex smoke's first-frame agreement measures each pair the way the engine published it: culled rows by exact-box gap, others shell to shell (ADR-581). OCCT's solid distToShape had answered 0 mm for a pair published at a 61 mm bound. Still open: threaded bolts counted as overlap, and about 5.5 s per frame on 66 components, past the 300 s bound
