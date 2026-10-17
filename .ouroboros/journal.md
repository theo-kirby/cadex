# Journal

(append-only. one block per iteration.)

## Iterations 35–36 (2026-10-16, handoff written by iteration 37)
- Both actor turns failed at once with an API SSL error (UNABLE_TO_VERIFY_LEAF_SIGNATURE). No code changed, no record was written, and HEAD stayed at ee94acec (ADR-724, joint-limit stiffness).
- State carried forward from staid-spring-2417: orun7-cat 8a065097 has a 0.004 s stop on j_pawpin_*. The fold is fixed, but in stance the paw rests on its +45° toes-down stop (sole median −53°, 32% within 15°). A3 is still not met. Next: narrow the toes-down travel. r1-t3 is a preview only; start no new R1 run until A3 passes.

## orun8 iteration 33 (2026-10-17, handoff written at the start)
- c1-t8 (warm from c1-t7 under ADR-753, per-drive over-rated price off at speed) is still training: iteration 104 of 150, reward/step 5.77 and climbing, episodes ~1,070 steps, ETA ~12 min. Not collapsed. It gets judged on the 10 frozen seeds once it finishes (next iteration if this one runs out of time).
- This unit is G3's one missing piece of evidence: the stock-vs-MJX tip comparison so far used rough-c4's actor on the old model `18d5657e`. This iteration re-runs it with c1-t7's frozen actor (newest model `0f036864`, actor height scan) on every course kind (`docs/probes/orun8/g3/`).
- What G1 and G2 lack, for the record: nothing in their criterion text. G1 has the 1,000-point test, a screenshot and a film frame; G2 has the 50 m trace test and the flat run-out. Their caveats are taste (dark walls) and the heightfield course, which does not train (O5).
