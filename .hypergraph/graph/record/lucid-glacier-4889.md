---
node_id: 2b3de9e0-6543-5309-bf06-5d08c906ec4b
slug: lucid-glacier-4889
title: 'ot10: ADR-423 static clearance bounds far pairs; hexapod-4 worker CPU 83→28 s, refused accent-feet candidate 417→115 s, no verdict changed'
created_at: '2026-09-28T04:29:05+00:00'
parents:
- rustic-ivy-4753
summary: ''
---
## What
ADR-423 (commit `02f0754f`), an engine change located by measurement. `_measure_clearance` now bounds far pairs instead of measuring them.
- A pair whose exact-geometry boxes are more than 10 mm apart, or more than its declared `clearances=` minimum when that is larger, carries `culled: true`. Its `distance_mm` is the box gap, a lower bound, and its common volume is 0.0.
- The joint sweep carries a static bound onto a rigid row with `culled: true`. It checks a bounded moving pair against the bound rather than for equality.
- The sweep gates `common()` with the exact-geometry boxes it already carries.
- `smoke_geometry.py` accepts a bounded first-frame row when the exact distance reaches the bound.
- `cadex clearance` reads a bounded row under a larger floor as `unknown`.
- `docs/XSCRIPT.md` and `docs/INTEGRATION.md` are updated, with their dates.

## Why
The critic named this unit: profile the accepted `ot10-hexapod-4` build read-only, find where its CPU seconds go, and make the smallest tool-side fix that lets about 46 components keep separate accents and caps, with a regression test that fails before it. No prompt or language changed.

Deviation: the critic's first line asked for a reconcile of tiny-dusk-3648 and rustic-ivy-4753 before the unit. This dispatch forbids the reconcile skill in a work iteration, with no exceptions, so I did not run it. The tail is now three unreconciled nodes, and the next reconcile pass should fold all three.

## Method
- Copied the accepted attempt's `request.json` to /tmp, lifted `cpu_limit_seconds`, and ran the project worker under FreeCADCmd with cProfile and rusage. The project was never written.
- Worker: 83 CPU-s. `_measure_clearance` took 25 s wall, 21 s of it in `distToShape` over 1,035 pairs. Geometry took about 2.4 s and tessellation 2.1 s.
- The 12 joint sweeps took 41 s wall and 104 CPU-s in child processes, each with its own RLIMIT, so the limit that binds is the parent's static clearance.
- Rebuilt the refused candidate from the transcript (script_history `0008` with the skip removed, the accent-feet variant the agent gave up). The old code ran it at 416.6 CPU-s, reproducing the refusal.
- Implemented the cull. The first replay showed sweep children 30% dearer. A BREP diff traced this to pcurves the old parent's `common()` calls on loosely boxed far pairs had stored on the serialised tray and hood. The fix was to gate the child's `common()` on exact boxes.
- A replay also caught a real bug before commit: rigid culled rows published null. It is fixed.
- Compared old and new outputs row by row.
- Ran `pixi run test-engine`, `pytest cli/tests`, `build-engine` + `stage-engine`, and the packaged lifecycle gate.

## Result
**The 300 CPU-second limit is no longer bound by the static clearance check at hexapod scale.** Same requests on this machine, before → after:
- Accepted `ot10-hexapod-4` (46 components, sweep on):
  - worker CPU 83.3 → 28.2 s; wall 71 → 56 s; sweep children 104 → 105 CPU-s;
  - 857 of 1,035 pairs bounded; 0 fit verdicts changed; 0 exact rows changed;
  - attachments and world geometry identical; every sweep row identical or a valid bound; sweep complete.
- The refused 51-component candidate with separate accent feet (no sweep declared): **416.6 → 114.5 CPU-s**, now inside the limit. 1,099 of 1,275 pairs bounded, 0 verdicts changed.

Tests:
- `test_static_clearance_bounds_far_pairs_and_the_sweep_still_measures_them` and the updated ADR-419 test fail on the old worker and pass on the new one.
- `test_smoke_geometry_bound.py` fails on the old `smoke_geometry.py`.
- A new `pair_status` test covers the CLI reading.
- Engine suite: 2,237 passed, 53 skipped. CLI suite: 1,004 passed, 1 skipped. Packaged lifecycle gate: 23 passed on the restaged payload.

Concerns:
- Sweep children are unchanged in cost (about 105 CPU-s, 41 s wall against the 180 s sweep budget), so a much larger robot may meet the sweep wall budget next.
- The static near-pair `common` gate still uses the looser `BoundBox`.
- Whether the agent now keeps its accents and caps is the next measurement, not a claim made here. Next unit: the quadruped A5 rerun on a new `ot10-*` project with the frozen prompt and flags. The hero-camera concern stays a separate renderer unit.

The tail is fat (three unreconciled nodes), and a reconcile pass is due.

Dispatch closed: 1 unit — profiled ot10-hexapod-4's CPU (static clearance, 21 of 25 s in distToShape); ADR-423 bounds far pairs, taking the accepted build from 83 to 28 CPU-s and the refused accent-feet candidate from 417 to 115, with no verdict changed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 02f0754f26608460903b2b99952ed34dce987d91

## State Impact

- target: forest-wind-0342 — ADR-423: solved-pose clearance bounds pairs whose exact boxes are >10 mm apart (or beyond a larger declared floor) with culled: true and a box-gap lower bound; sweep carries static bounds and gates common() by exact boxes; ot10-hexapod-4 worker CPU 83.3→28.2 s with zero verdict changes
- target: loyal-fountain-8709 — the 300 CPU-second limit that cost hexapod-4 its accent feet is located (static clearance distToShape, 21 of 25 s) and lifted: the refused 51-component accent-feet candidate replays at 114.5 CPU-s (was 416.6); the quadruped rerun is next
