---
node_id: dcdc33ff-2ae8-5d3d-85d2-6403f90fdd78
slug: flat-tower-6825
title: 'ot10: static fit searches a housing''s faces best first against the part''s box — refused-build fit 1,143 → 702 CPU-s, rows identical (ADR-437)'
created_at: '2026-09-29T01:05:03+00:00'
parents:
- mellow-light-0451
summary: ''
---
## What

ot10: the static fit made cheap for a hollow shell whose box overlaps the parts it houses (ADR-437, commit `4305b805`, `cadex_tests/test_housed_fit_distance.py`).
- `_shell_distance` (`cadex_assembly_worker.py`) searches the housing's faces best first when the static fit measures a pair and the part with the smaller box has more than six faces.
  - Each face is first keyed by the gap between its exact box and the part's box. Face boxes are cached per component for the whole fit.
  - A face at the front is refined once, to its distance from the part's box as a solid, and re-queued.
  - A refined face at the front is measured against the part's shells, with the pair's argument order kept.
  - The search stops when the front bound is not below the best distance.
- Shells measured exactly 0.0 apart are no longer re-measured on the solids, because the solids contain their shells.
- The swept fit is unchanged. Tried there, the bounds cost more than they saved.

## Why

The critic named this unit: make the static fit cheap for a hollow shell whose box encloses the parts it houses, for example by culling sub-shapes before the exact distance. They asked for:
- a before/after CPU ledger of hexapod-10's refused 12:40 script;
- all 1,326 accepted rows and verdicts reproduced;
- the 10 mm cull and thresholds unchanged;
- a regression that fails before the fix, and an ADR.

All of that was done. **Deviation:** the critic also said "Then fold the reconcile". This dispatch forbids the hypergraph-reconcile skill in a work iteration, so I did not reconcile. The tail is left for the reconcile pass.

## Method

1. **Before.** Took the 12:40 `write_script` source from the product transcript and replayed it with `cadex script --set --replace` on `/tmp/ot10-cull/base`, a copy of `ot10-hexapod-10` (earlier projects stay read-only). It was refused at 299 CPU-s in `static fit c_tub / c_hip_screw_lr0`. The top stages were:
   - `output tub` 75.77;
   - tub/visor 53.59, tub/deck 24.7, tub/pca9685 23.97;
   - `output dome` 20.78.
2. **Diagnosis.** A temporary dump in the worker (removed before commit) wrote every world shape as BREP. Timed face by face, tub vs pca9685 cost 117 CPU-s (55 s whole) for 12.4 mm. 111 s went on three tub faces 28–30 mm away: a 6-edge plane, a 430×7-pole B-spline and an offset surface. Each face's distance to the board's box, taken as a solid, cost about 0.3 s and equalled its true distance. Touching pairs re-measured solids after an exact 0.0 shell distance: 21 and 33 CPU-s.
3. **Harness.** Ran `_measure_clearance` from the old and new workers over the dumped shapes, with per-pair CPU from the stage hook. Used the refused build's 76 shapes (2,850 pairs) and the accepted build's 52 (1,326 pairs). Five designs were tried and measured:
   - v1, cull only when one box encloses the other: exact, but slower overall (180 vs 129 s on the enclosed pairs), and it missed pca9685, which pokes out of the tub's box.
   - v2, bound every face: 1,143 → 744 CPU-s, but 5 rows differed by about 1e-14 mm. The fix was keeping `distToShape`'s argument order. The accepted fit was also slower (120 → 138), because cheap pairs paid the bounds.
   - v3, ordered by face box gap: an unbounded costly face was measured first (1,198).
   - v4, overlapping faces bounded and the rest in one call: accepted 108, but refused only 1,110.
   - v5, best-first with lazy refinement: shipped.
   - In the sweep, the v2 bounds made per-joint time about 25 s instead of about 5 s, and five joints ran out of budget. So only the static fit passes boxes.
4. **Final measurements (v5).**
   - Harness, refused shapes: 1,143.4 → 701.7 CPU-s.
     - tub/pca9685 157.3 → 1.3; tub/esp32 62.9 → 1.1; tub/bno085 61.9 → 2.5.
     - tub/regulator 46.0 → 1.9; tub/dome 44.8 → 10.2; dome/bno085 48.6 → 22.9.
   - Harness, accepted shapes: 120.4 → 111.7 CPU-s.
   - Some pairs got slower: 55 on the refused shapes (at most 2.8 s each, 36.8 s in total), and 59 on the accepted shapes (at most 1.3 s each).
   - **All 4,176 rows are identical to the old worker's, to the last digit.**
5. **Accepted rebuild through the CLI**, on a `/tmp` copy with the final code: all 1,326 static rows identical, and the swept fit complete and identical with timings stripped. It took 142 user CPU-s and 84 s wall. The old worker on another copy took 151 and 93.
6. **Refused replay after**, on `/tmp/ot10-cull/after`: still refused, now at 293 CPU-s in `static fit c_deck / c_dome`. It got through every tub pair. The top stages are:
   - `output tub` 75.17;
   - tub/visor 53.67, tub/deck 24.71;
   - `output dome` 20.59, `output visor` 13.43.

   No board-in-housing pair is among them any more.
7. **Regression.** `test_housed_fit_distance.py` has four tests:
   - A five-face fake tub reaches 12.4 mm by measuring only two faces, through `_measure_clearance`, in both orders.
   - The sweep path (no boxes) and a part of six faces or fewer are measured whole.
   - Shells at exactly 0.0 do not call the solids.
   - On real OCCT, a board in a hollow tub and under a hemispherical dome, in both orders, equals the whole-shell distance exactly (25.0 and 19.687… mm).

   Against the old worker, all four fail. The two core ones fail on substance: it measured `['whole']`, and it called `['whole', 'solid']`. `test_cpu_ledger.py`'s stub now accepts the new arguments.

## Result

What is true now:
- A static fit no longer pays for housing faces that cannot be nearest.
- On hexapod-10's refused build, the static fit's CPU fell by 39%, and on its accepted build by 7%. Not one row or verdict changed.
- The 10 mm cull, the 0.001 mm recheck, the thresholds, the sweep, `OP_ARG_SPECS` and the 300 CPU-s limit are unchanged.
- `docs/XSCRIPT.md` (fit section and sweep paragraph), ADR-437 and remaining defect 1 in `docs/probes/ot10/REPORT.md` say so.

Suites at this revision:
- `pixi run test-engine`: 2259 passed, 53 skipped.
- `pytest cli/tests`: 1068 passed, 1 skipped.
- The engine was rebuilt and staged. The payload carries the new worker (cmp-checked), and the packaged lifecycle gate (`CADEX_ENGINE_ROOT=<payload> test_cadexd_lifecycle.py`) passed 23/23.

Concerns for the next iteration:
- **hexapod-10's refused build still does not fit 300 CPU-s.** Geometry takes about 110 CPU-s: `output tub` 75 s is the tub's own construction, with a `part.offset` inner. Touching pairs need `common`: tub/visor about 54 s, of which offline `common` was 78 s. Neither can be culled without changing a verdict. The ledger now names these stages to the agent.
- The largest fit cost left is `common` on touching lofted shells. A cheaper exact zero-volume proof for a pair that only touches would be a separate unit.
- Cheap pairs got slightly slower (at most 2.8 s each). The measured net is a saving on both builds.
- No probe has run since, so the CPU-refusal class is not yet shown smaller in a transcript.
- No new dependency (`heapq` is the standard library). No rubric, bar, judge or prompt changed, and no probe is re-scored.
- **Not done as asked:** the reconcile fold, which a work iteration may not run. The tail now holds two unreconciled records (`mellow-light-0451` and this one).

Dispatch closed: 1 unit — static fit searches a housing's faces best first against the part's box (ADR-437): hexapod-10 refused-build fit 1,143 → 702 CPU-s, accepted 120 → 112, all 4,176 rows identical, accepted rebuild reproduces 1,326 rows and the sweep.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 4305b80583942a2f6d2504677a0c49ee910280b2

## State Impact

- target: forest-wind-0342 — The static fit searches a housing's faces best first, bounded by face-box gap then by distance to the part's box, and shells exactly 0.0 apart skip the solid recheck (ADR-437). On ot10-hexapod-10's refused build the static fit fell from 1,143 to 702 CPU-s (tub/pca9685 157 to 1.3), and on the accepted build from 120 to 112, with all 4,176 rows identical. The accepted rebuild reproduces 1,326 static rows and the complete sweep. The sweep is unchanged. The refused build is still over 300 CPU-s, from geometry (tub 75 s) and common on touching shells.
- target: loyal-fountain-8709 — The CPU-refusal class lost its static-fit housing cost: hexapod-10's refused 12:40 build now gets through every tub pair and dies at 293 CPU-s in deck/dome, with geometry and touching-pair common the named remainder (ADR-437). No A5 probe has run since.
