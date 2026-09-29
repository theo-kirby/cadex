---
node_id: 30fa82d1-2b98-511a-9f75-faf67fc3a6b3
slug: scarlet-crane-7693
title: 'ot10: touching pairs'' common run on the solids cut to their shared region, zero only — refused-build fit 702 → 600 CPU-s, rows identical; box-separation proof a dead end (ADR-438)'
created_at: '2026-09-29T02:12:49+00:00'
parents:
- flat-tower-6825
summary: ''
---
## What

ot10: a touching pair's `common` in the static fit is first run on the two solids cut to the region they can share (ADR-438, commit `2e63b5b6`, `cadex_tests/test_touching_fit_common.py`).
- `_clipped_common_is_zero` (`cadex_assembly_worker.py`) sets the region to the overlap of the two exact boxes, grown by 1 mm (`_CLIP_MARGIN_MM`). Every point of the common lies inside it, so the common of the cut solids is the same set.
- A side is cut only when fewer than half of its faces' exact boxes meet the region.
- **The cut decides only a zero.** A non-zero answer, a failed cut, or no side worth cutting falls back to the whole `common`, exactly as before. Every non-zero volume the fit publishes is still the uncut boolean's.
- The swept fit is unchanged.

## Why

The critic named this unit: "an exact zero-volume proof for touching pairs that skips `common` (tub/visor 53.7 CPU-s)", measured the way ADR-437 was, or else a recorded dead end with nothing loosened.

**Deviation, stated plainly.** The proof the critic asked for was tried first, and it did not hold. The attempt was a separating axis from the exact boxes, on the axes and on the contact faces' planes:
- The kernel's boxes carry their own inflation of about 1e-7 mm each, and 3.8e-7 on the B-spline dome against the flat deck.
- So the method bounds a touching pair's common only to a slab of that thickness. For deck/tub that is about 4e-3 mm³, above the fit's 1e-6 mm³ intersection line.
- It proves nothing at all for tub/visor or hip_servo/tub, which meet along walls and pockets that no plane separates.

That half is a **measured dead end**, recorded in ADR-438. What shipped instead is not a proof. It is the same boolean, restricted exactly to the region where volume can exist, and trusted only when it answers zero. So `common` is not skipped. It is made cheap, and no verdict or row moves.

I did not reconcile. The critic said "After that, reconcile the three records", but the dispatch forbids reconcile in a work iteration. The tail now holds three unreconciled records (`mellow-light-0451`, `flat-tower-6825` and this one), so the reconcile is due next.

## Method

1. **Proof attempt.** Worked on `/tmp/ot10-cull`, ADR-437's dumped world shapes: the refused build has 76 shapes and 2,850 pairs, and the accepted build has 52 shapes and 1,326 pairs.
   - For every touching pair (distance ≤ 0.001 mm: 118 refused, 58 accepted), I measured the tight-box overlap on each axis.
   - I also measured the overlap along the normals of the planar faces at the `distToShape` supports, using rotated exact boxes.
   - The results are above.
2. **Equivalence before any rule.** For all 176 touching pairs, I compared a cut `common` (both sides cut to the grown overlap) with the whole `common`. **All 176 were identical to the last digit**, including the twelve screws that really overlap the tub (0.29839… mm³).
3. **Rule.** Cutting everything slowed the accepted build's touching pairs from 43 to 63 CPU-s.
   - Rules I evaluated and rejected: face count, the ratio of box volumes, and the pair's distance CPU (not deterministic).
   - What shipped: cut a side only when fewer than half of its faces meet the region.
4. **Harness, final code, run sequentially.** This is the same `_measure_clearance` as ADR-437, with per-pair CPU.
   - Refused shapes: 701.7 → 600.3 CPU-s (586.7 on the first run). tub/visor 102.9 → 33.2, deck/tub 63.4 → 49.8, hip_servo/tub about 20 → 6–13 each.
   - The twelve screw/tub pairs are about 3 s slower each: the cut answers non-zero, so the whole boolean runs after it.
   - Accepted shapes: 111.7 → 120.5 CPU-s (117.3 on the first run). That is a small loss on cheap pairs (foot/tibia, coxa/hip_horn), and still below the 120.4 measured before ADR-437.
   - **All 4,176 rows are identical to ADR-437's and to the original worker's.**
5. **Accepted rebuild through the CLI** (`cadex script --set` on a `/tmp` copy of `ot10-hexapod-10`, which stays read-only):
   - all 1,326 static rows identical;
   - the swept fit complete and identical with timings stripped;
   - 143.7 user CPU-s and 86 s wall (ADR-437's: 142 and 84).
6. **Refused 12:40 replay** on a `/tmp` copy: still refused, now at 292 CPU-s in `static fit c_dome / c_pca9685`, further along the pairs than before.
   - `c_tub / c_visor` is no longer among the five costliest stages. It was 53.7 CPU-s.
   - The five are now: `output tub` 72.9, deck/dome 24.7, tub/deck 20.6, `output dome` 19.9, dome/visor 13.9.
7. **Regression.** `test_touching_fit_common.py` has four tests:
   - A fake tub (8 of 10 faces outside the region) touching a visor, in both orders, through `_measure_clearance`: the tub is cut, and the whole boolean never runs.
   - A cut that answers non-zero publishes the whole boolean's volume.
   - No side worth cutting, and the sweep's call with no boxes, both run whole.
   - Real OCCT: a drilled hollow tub with a visor on its rim and a screw through its wall, in both orders. Every volume equals the whole `common` exactly. The visor's 0.0 is decided on the cut; the screw's 70.69 mm³ is not.

   On the previous worker the first three fail with `['whole common']`, and the OCCT test fails because the helper is missing.
   - The helper runs entirely inside `try`, so a stub with no `Faces` or no `Part` falls back to the whole boolean. `test_cpu_ledger.py` is unchanged and passes.

## Result

What is true now:
- The static fit no longer pays the whole tub for a visor's zero.
- On hexapod-10's refused build, the static fit's CPU fell by about 15% (701.7 → 600.3). On its accepted build it rose by 5–8% (111.7 → 117–121).
- Not one of 4,176 rows or verdicts changed.
- `docs/XSCRIPT.md` (fit section), ADR-438 (including the dead-end proof attempt) and remaining defect 1 in `docs/probes/ot10/REPORT.md` say so.

Suites at this revision:
- `pixi run test-engine`: 2263 passed, 53 skipped.
- `pytest cli/tests`: 1068 passed, 1 skipped.
- Engine rebuilt and staged, with the packaged lifecycle gate (`CADEX_ENGINE_ROOT=<payload> test_cadexd_lifecycle.py`) 23/23, against a payload whose worker is cmp-identical to source.

Concerns for the next iteration:
- **No exact zero-volume proof that skips the boolean exists here.** The box route is blocked by the kernel's box inflation against the 1e-6 mm³ line. Do not retry it without a tighter extent primitive.
- **hexapod-10's refused build is still over 300 CPU-s.** Geometry alone is about 110 CPU-s (`output tub` 73). The fit's remaining cost is spread thinly: deck/dome 25 (its cut only brought 29 → 25), tub/deck 21, dome/visor 14.
- The accepted build is a few CPU-s slower, on cheap touching pairs where the cut is a second boolean. This is measured and stated, not hidden.
- The twelve screws through the tub pay about 3 s each for a cut that cannot decide a real overlap.
- No probe has run since, so the CPU-refusal class is still not shown smaller in a transcript.
- No new dependency. No rubric, bar, judge or prompt changed, and no probe is re-scored.
- **The reconcile is due**: three unreconciled records.

Dispatch closed: 1 unit — touching pairs' `common` run on the solids cut to their shared region, zero-only (ADR-438): refused-build static fit 701.7 → 600.3 CPU-s (tub/visor 103 → 33), accepted 111.7 → 120.5, all 4,176 rows identical; the exact box-separation proof the critic asked for was measured and is a dead end.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 2e63b5b6f2dbe6ed881d5f33489a9b0f8cef557a

## State Impact

- target: forest-wind-0342 — The static fit runs a touching pair's common first on the two solids cut to their box overlap grown by 1 mm (a side cut only when fewer than half its faces meet it), and takes only a 0.0 from the cut; anything else runs the whole boolean (ADR-438). On ot10-hexapod-10's refused build the static fit fell from 701.7 to 600.3 CPU-s (tub/visor 103 to 33), on the accepted build it rose from 111.7 to 117-121, and all 4,176 rows are identical; the accepted rebuild reproduces 1,326 rows and the sweep. An exact box-separation proof of zero volume was measured and fails on the kernel's ~1e-7 mm box inflation against the 1e-6 mm3 intersection line.
- target: loyal-fountain-8709 — hexapod-10's refused 12:40 build now gets past tub/visor (no longer a top-five stage) and dies at 292 CPU-s in dome/pca9685; geometry (output tub 73) and deck/dome 25 are the named remainder (ADR-438). No A5 probe has run since.
