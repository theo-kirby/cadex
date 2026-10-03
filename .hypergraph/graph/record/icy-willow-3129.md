---
node_id: cd8c71b8-fc6d-5ea5-9f31-9e4a21e42aa1
slug: icy-willow-3129
title: 'orun1 D3: ADR-492 a bolt holds only by its thread; fit allows the thread'
created_at: '2026-10-03T07:56:47+00:00'
parents:
- hidden-grove-0337
summary: ''
---
## What
ADR-492, commit `ec6782ad`. Two changes:
- **Mounting check.** A screw holds only if its shank threads into something. That is a common volume of at least 0.1 mm³ with a printed part, which becomes the holder. Or the head clamps the printed part while the shank reaches the held part's own tapped hole, the part itself, a nut or a heat-set insert. A bolt on the axis that threads nothing is listed in the row's `unthreaded` and holds nothing.
- **Static and swept fit.** A `lib.bolt` and a printed part may share up to `π/4 (d² − minor²) L`, the ring its thread can cut. That overlap is `clear` and counted in `fit.threaded_count`; it is not an `intersection`. The sweep keeps this allowance only for pairs already threaded at the solved pose. `cadex clearance` writes these rows as `threaded`.
- The overlay (`CadexAgentGuidance.md`) now teaches `lib.tap_drill` holes into solid material, and `docs/CLI.md` documents both rules. The change is installed with `pixi run build-engine`.

## Why
This is the critic's unit: make a `screws` hold require shank/print volume, use the no-ledge MG90S block as the fixture that fails first (2 of 2 → 1 of 2, ledge=4 stays 2 of 2), then re-measure hexapod trial 1 and balancer trial 3. **Deviation (widened, not narrowed):** I added the fit allowance. Re-measuring showed the critic's rule alone makes the product contradict itself. The static fit failed **any** bolt/print overlap above 1e-6 mm³ as an intersection, so a screw in a tap-drill hole could never pass fit. Both trial agents had worked around this by boring at the nominal diameter. The hexapod defined `TAP = lib.tap_drill("m2")` and cut radius 1.0 instead. The balancer wrote "modelled at the thread's major diameter". With only the mounting rule, every screw fails one check or the other. The allowance is bounded by the thread's minor diameter, so a bolt through solid still fails. Quadruped trial 1 is left for the next iteration, as the critic ordered.

## Method
- `CadexFitReport.py` gains `THREAD_ENGAGEMENT_MM3`, `THREADED_FAMILIES`, `thread_allowances`, `_threaded` and `THREAD_MINOR_DIAMETER_MM`. The minor diameters are an ISO 261 copy, because the module is loaded by path; a test holds the copy equal to `CadexCatalog`. The reader was already the fit verdict, so no protocol op, response key or digest moves. The worker's `fit_failures` is unchanged.
- Tests in `test_mounting_check.py`, all failing on the old source:
  - unit fixtures: a head over a cavity (unthreaded), and a printed thread, a tapped hole and a nut (each held);
  - fit allowance: a tap drill passes, solid and a pilot below the minor diameter fail;
  - sweep: the allowance holds at rest and does not cover a swinging link;
  - the catalog-equality pin;
  - the real-kernel servo block: plain bay **1 of 2** (`unthreaded: [component_2]`), `ledge=4` **2 of 2**, and no bolt/block intersection in fit.
- N20 real-kernel check: the catalog N20 models its M1.6 face holes as open bores, so bolt/motor volume is 0.0. That is why a tapped hole the bolt reaches counts as thread.
- Re-measure: I dumped `inspect scope=clearance` from `orun1-t1-hexapod-render` and `orun1-t3-balancer-render` (opened through cadexd, both reopened fine) and ran the HEAD-version and new `CadexFitReport` over the same values. Neither design has any bolt/printed-part common volume (max 0.0 over 18 and 25 touching pairs).
- `pixi run test-engine`: 2596 passed, 61 skipped. `pixi run python -m pytest cli/tests`, GPU hidden: 1290 passed, 1 skipped, 1 failed. The failure was `test_review_design.py::test_rendered_page_follows_the_spec[phone]` (run picker read "broken" for "second"). That file re-run alone gives 135 passed, so it is a load flake, not this change. No packaged gate, since no protocol or payload-structure change.

## Result
- True now: the mounting check reads thread engagement, and the fit allows it. The critic's fixture reads plain bay 1 of 2 and ledge=4 2 of 2.
- **Hexapod trial 1** (`orun1-t1-hexapod` @ `35193b3e`): fit 0/3655 and sweep pass, unchanged. Mounting **still 49/49**, but all 18 servo bolts (one per MG90S) are `unthreaded`, so the servos now read `held by bay`, not by screws. Its "screws" never threaded anything.
- **Balancer trial 3** (`orun1-t3-balancer`): fit 0/561 and sweep pass, unchanged. Mounting goes **pass 11/11 → reported 8/11**. The BNO085, the D36V50F6 and the VL53L1X become `contact only` (9 unthreaded bolts). The two N20s are still held by screws in their own M1.6 tapped faces.
- Concerns for the next iteration:
  - A servo counts as held by its bay alone, with no screw. The charter names "a bay" as a valid hold, so I left it. It is a candidate tightening: a tabbed servo that the bay seats but nothing screws can lift out of a pocket.
  - Published D4 mounting receipts before `ec6782ad` overstate screws. Trial 3's "pass" is now "reported".
  - The overlay changed, but accepted projects still reopen. ADR-491 showed overlay edits do not touch recipes; this was not re-measured.
- Next: quadruped trial 1 at HEAD (`ec6782ad`), supervised, as the critic ordered. Tail: three unreconciled records (deep-cove-1130, hidden-grove-0337 and this one), which hits the reconcile rule's threshold.

Dispatch closed: 1 unit — ADR-492: a screw holds only by thread engagement (fixture 2/2→1/2, ledge 2/2), fit allows the thread's ring; re-measured hexapod t1 49/49 (servos now by bay, 18 bolts unthreaded) and balancer t3 11/11→8/11

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: ec6782ad2fde70955d9a2ee4b36c0abe6c729562

## State Impact

- target: loyal-ocean-0768 — mounting check requires thread engagement (ADR-492, ec6782ad): a screw holds only if its shank shares ≥0.1 mm³ with a printed part or reaches the part's tapped hole, a nut or an insert, else listed unthreaded; fit allows a bolt/print overlap up to the thread ring π/4(d²−minor²)L (threaded_count). No-ledge MG90S fixture 1 of 2, ledge=4 2 of 2
- target: salty-fox-7376 — re-measured under ADR-492: hexapod t1 mounting 49/49 but all 18 servo bolts unthreaded (servos held by bay); balancer t3 mounting 11/11 → reported 8/11 (BNO085, D36V50F6, VL53L1X contact only); fits unchanged
