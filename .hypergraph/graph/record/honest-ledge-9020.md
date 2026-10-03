---
node_id: fc98d377-0ebe-5154-bcd7-816437fc4353
slug: honest-ledge-9020
title: 'orun1 D3: ADR-488 a bolt holds only if it fits its hole; catalog M1.6 fasteners'
created_at: '2026-10-03T04:16:01+00:00'
parents:
- first-eagle-0836
summary: ''
---
## What
D3 product change (ADR-488, commit `c2fcecc5`): the mounting check now requires a bolt to fit the hole it sits on, and the catalog gains M1.6 fasteners so the N20 gearmotor (`pololu-2367`) can be screwed down by its face.

## Why
This is the critic's next unit, done as asked, with one exception. The critic asked for (1) a thread-match rule with a fixture that fails and one that passes, shown failing before the fix, and (2) M1.6 screws, a gearmotor `.bay()`, or both. I did (1) and the M1.6 half of (2). I did not build a gearmotor `.bay()`: an M1.6 screw holds the N20 by its face, the way its datasheet intends, and a bay would be a second route to the same verdict. That reasoning is in the ADR. The wheel model and balancer trial 3 are the next units.

## Method
- `cadex_library_api._size_facts`: each mount axis in `library_mount_facts()` carries one size fact. A bolt gets `bolt_dia_mm`; a part with `mount_thread` gets `thread_dia_mm`, parsed from "M<n>"; any other part gets `hole_dia_mm`, the first of mount_hole_dia / hole_dia / mount_bore_dia. These are stamped beside the definition, so no digest moves.
- `CadexFitReport.mounting_summary`: a new `_misfit()`. A tapped hole takes only its own thread; a clearance hole takes any bolt no larger than itself. A bolt that does not fit holds nothing and goes into the row's `misfits` and its detail. When either side has no size fact (revisions accepted before ADR-488), the hole is judged by axis alone, as before. MOUNTING_NOTE says the rule.
- `CadexCatalog`: m1.6 is added to METRIC_THREADS (ISO 261/273), SOCKET_HEAD_SCREWS (ISO 4762), HEX_NUTS (ISO 4032) and FLAT_WASHERS (ISO 7089). Countersunk, nyloc and insert tables do not get it and still refuse it.
- Overlay `CadexAgentGuidance.md` HOLD EVERY PART: a bolt must fit; the N20 takes `lib.bolt("m1.6", ...)` through `lib.clearance_hole("m1.6")`; wrong bolts are listed under `misfits`. Docs updated: `docs/CLI.md` (ADR-486 section) and `docs/XSCRIPT.md` (catalog sizes).
- Tests in `test_mounting_check.py`, three new on published values:
  - M2 in M1.6 tapped holes fails; M1.6 passes.
  - M3 through a 2.5 mm hole is reported; M2 and M2.5 pass.
  - Missing size facts are judged by axis alone.
- Plus a real-kernel parametrised pair: an N20 under a plate with `m1.6` bolts is held 2 of 2; with `m2` it is contact only with 2 misfits. The library-facts test was extended to check the board's hole_dia, the N20's thread 1.6 and the STS3215's 2.0.
- Fail-before: with the three source files stashed, 5 of 19 failed. The M2 cases came back `held`, and m1.6 was an unknown thread. With the change and `pixi run build-engine`, which the real-kernel workers need, 19 of 19 passed.

## Result
- `pixi run test-engine` at the change: **2579 passed, 61 skipped** (5 m 45 s). The CLI suite was not run because `cli/` was not touched. There was no protocol or payload change: the op args are unchanged, and the new keys are inside the existing `mount_axes` rows. So the packaged gate was not run, and the bundled payload is not restaged.
- What is true now: an M2 bolt in N20 M1.6 holes no longer counts as held. Trial 1's "9 of 9" would rebuild to 7 of 9. The agent can now hold an N20 with catalog M1.6 socket screws.
- Concern: the check still does not test bolt engagement length or strength. Designs accepted before ADR-488 keep the axis-only judgement until they are rebuilt.
- Next, per the critic: model the 1430 wheel's rim, hub and tyre, then balancer trial 3. The tail is now 3 unreconciled records, so a reconcile is due.

Dispatch closed: 1 unit — mounting check requires bolt to fit its hole (thread/clearance) + catalog M1.6 fasteners, ADR-488, fail-before shown, engine suite green

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: c2fcecc5283289f96d308a0fd9d154687e095832

## State Impact

- target: brave-stone-9609 — mounting check (ADR-488, c2fcecc5) now counts a bolt only if it fits the hole: equal to a tapped hole's mount_thread, no larger than a clearance hole; misfits listed per part. Catalog gains M1.6 thread, ISO 4762 socket head, ISO 4032 nut, ISO 7089 washer, so an N20 can be screwed by its face. No gearmotor .bay().
