---
node_id: d9f779e6-6c12-531c-bc94-5d7c6dd013a0
slug: swift-trail-3183
title: 'ot10: ADR-425 swept fit measures boundary shells; hexapod-5''s accepted sweep 9/12 at 180 s -> 12/12 in 125 s, rows identical'
created_at: '2026-09-28T08:06:19+00:00'
parents:
- patient-banner-4052
summary: ''
---
## What

ADR-425: the swept fit's exact distance is measured on the two parts' boundary shells whenever no solid of either can sit inside the other. On the accepted `ot10-hexapod-5` request, replayed on this machine, the sweep went from **9/12 joints at 180.0 s (incomplete)** to **12/12 joints in 125.1 s (complete)**, under the unchanged 180 s budget. All 14,877 rows the two runs share are identical. `_boundary_distance` is in `cadex_assembly_worker.py`, `_sweep_joint` uses it, and there are two regressions, an ADR and one paragraph in `docs/XSCRIPT.md`.

## Why

The critic named this unit: profile where the swept fit spends its wall time on a `/tmp` copy of `ot10-hexapod-5`, then fix the dominant cost so that 12/12 joints fit inside the unchanged 180 s. Add a regression test that fails on the old source, write an ADR, and run the packaged gate. Change no prompt, language or budget constant. Then run hexapod attempt 6. It serves A5 (`loyal-fountain-8709`): the hexapod's only miss on attempt 5 was the incomplete sweep. **Deviation, stated:** hexapod attempt 6 was not run in this iteration. The fix is this iteration's one unit, and a design turn takes about 85 minutes plus render and judging, so attempt 6 is the next unit, run on the rebuilt engine.

## Method

1. **Replay.** Replayed the accepted revision's own worker request (`attempt-1790579554303`, rev `d2198144`), from a `/tmp` copy of the project, through the project worker under `FreeCADCmd`. The CPU limit was lifted, and a scratch copy of the worker saved each joint child's `input.json`. The old code reproduced the miss: 9/12 in 180.0 s. Hip children took 18–31 s and knee children 10–17 s, each with two samples at 80°.
2. **Profile.** Ran cProfile on the `hip_fr` child, first standalone, then pinned to four CPUs as the worker pins it (ADR-418; the pin explains 14 s standalone against 31 s in the worker).
   - The named candidates were cheap: `FreeCADCmd` spawn 0.06 s, deserialising 58 BREPs 0.03 s, `optimalBoundingBox` preparation 1.1 s.
   - **`distToShape` took 25.5 s of 28.5 s wall over 93 calls:** 31 solved-pose agreement checks and 62 sample measurements.
   - Per-pair timing showed no single dominant pair. The BSpline dome led, at up to 1.8 s a call.
3. **Hypothesis.** Measuring shells instead of solids gave identical distances to 1e-6 mm, at 0.876 → 0.083 s, 0.335 → 0.005 s and 0.477 → 0.022 s on non-dome pairs, and 1.3× faster on the dome. A solid distance differs from a shell distance only when one solid lies inside the other. So the shells are used only when each solid of each side has a vertex strictly outside the other (`isInside`, faces counting as inside), and never within the 0.001 mm contact threshold. The first draft without that recheck changed one touching floor row from 0.0 to 2.9e-14; the recheck restored it.
4. **Full replay with the fix.** 12/12 joints complete in 125.1 s. The nine joints both runs reached went from 176 to 112 s, `hip_fr` 31.1 → 18.6 s, and worker CPU 826 → 574 s. The 14,877 rows are identical, including all 233 exactly measured moving rows. The project itself was never written.
5. **Tests.**
   - `test_a_sweep_measures_boundaries_unless_a_solid_may_sit_inside_the_other` is a stub test of the routing: apart pairs use shells; a vertex inside, a solid with no vertex, or one buried solid of two uses solids; touching boundaries recheck on solids. **It fails on the previous source** with an AttributeError.
   - `test_a_swept_bead_in_a_cavity_and_one_buried_in_a_solid_read_true` runs on real OCCT: a bead in a hollow sphere's cavity reads 4.0 mm through its inner shell, and a bead buried in a torus reads 0.0 mm with its whole volume, first contact at 20°. It passes on both sources, pinning correctness rather than the change.

## Result

- **What is true now:** the engine's swept fit on the accepted hexapod-5 design completes 12/12 joints in 125 s against the 180 s budget, with bit-identical rows. No budget constant, cull margin, prompt or language changed. No op argument or response shape changed, so `docs/INTEGRATION.md` is unchanged. `docs/XSCRIPT.md` documents the rule.
- **Verification:**
   - `pixi run test-engine`: 2,239 passed, 53 skipped.
   - `build-engine` and `stage-engine` done, and the staged payload carries `_boundary_distance`.
   - Packaged lifecycle gate (`CADEX_ENGINE_ROOT=<payload>`): 23 passed.
   - `pytest cli/tests`: 1,007 passed, 1 skipped.
- **Concerns for the next iteration:**
   - The margin is 55 s at the agent's 80° step. At finer steps, say 30° with three samples, the same design would cost about 4/3 as much (roughly 167 s), which is close to the budget.
   - What remains is mostly the dome's BSpline faces, plus the solved-pose agreement measurement repeated in every joint child (a third of the exact calls at two samples). Both are named in ADR-425 as not taken.
   - The static `_measure_clearance` still measures solids; it is not binding since ADR-423.
- **Next unit:** hexapod attempt 6 on a new `ot10-hexapod-6` project, with the frozen prompt, flags, model `claude-opus-5-5` and `CADEX_EFFORT=medium`, on this rebuilt engine.
- **No new dependency.**

Dispatch closed: 1 unit — ADR-425: swept fit measures boundary shells when no solid can nest; ot10-hexapod-5's accepted sweep replays 9/12 at 180 s → 12/12 in 125 s with identical rows; regression fails on old source; packaged gate 23 passed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 46e81e4f51aedf5b3a7b4008fdbb55778986444d

## State Impact

- target: loyal-fountain-8709 — the hexapod's attempt-5 miss (swept fit 10/12 under the 180 s budget) is fixed at the source: ADR-425 measures swept exact distances on boundary shells when no solid can nest; the accepted ot10-hexapod-5 request replays 12/12 joints in 125.1 s (was 9/12 at 180 s) with all 14,877 shared rows identical; budget, prompt and language unchanged; hexapod attempt 6 is next
- target: forest-wind-0342 — _sweep_joint's exact distance goes through _boundary_distance (ADR-425): shells when each solid of each side has a vertex strictly outside the other, solids otherwise or within 0.001 mm; sweep rows unchanged, 30-40% less sweep wall time on the hexapod; packaged gate 23 passed
