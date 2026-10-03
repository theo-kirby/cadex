---
node_id: 60ba3c72-b2fa-5de9-8961-1638ed4bf4a7
slug: floral-horizon-1217
title: 'orun1 D3: ADR-493 board.mounting() threads every board screw (0/3 → 3/3)'
created_at: '2026-10-03T08:35:19+00:00'
parents:
- icy-willow-3129
summary: ''
---
## What
ADR-493, commit `f78f1e8f`. `BoardPart.mounting(standoff=3.0, *, screw=None, diameter=None, length=None)` returns a `BoardMounting` with three lists, one solid per mounting hole, placed in the board's frame:
- `standoffs`: bosses 2.5 screw diameters across, from the PCB bottom down `standoff` + 1 mm, so they fuse into the carrier;
- `holes`: `lib.tap_drill` pilots from the PCB down to 1 mm past the screw tip;
- `screws`: `lib.bolt` parts seated on the PCB's top face, on each hole axis.

`screw` defaults to the largest metric size the hole passes: M2 for the D36V50F6 and VL53L1X, M2.5 for the BNO085 and Pi 5. `length` defaults to ceil(PCB + 2.5 d). It refuses a board with no holes (ESP32 DevKitC), a screw larger than the hole, a wall under 0.8 mm, and a screw that doesn't pass the PCB. The overlay (`CadexAgentGuidance.md`) and `docs/XSCRIPT.md` teach it, and the overlay forbids board screw holes at the screw's own diameter. The engine is installed with `pixi run build-engine`.

## Why
The critic asked why board bolts land in clearance holes or in air, and for a helper, bay feature or rule, pinned 0-of-N → N-of-N. Diagnosis from `orun1-t3-balancer/script.py`:
- All nine board bolts (regulator 3, ToF 2, IMU 4) sit in bores at the M2 **major** diameter (`m2t = 1.0005`). The script's comment says the bore was meant to let "the unmodelled thread bite". Before ADR-492 the fit failed any bolt/print overlap, so this was the only hole that passed.
- The product had no way to screw a board down. `board.bay()` only said "standoffs ... go in after the cut", so the agent derived the screw, standoff, pilot and seat by hand in a rotated frame.

The ADR-492 rule alone fixes the first cause, and the helper removes the second. I chose a helper over a rule alone because servos (`bay(ledge=)`) and foot pads (`bay(screw_depth=)`) already get their screw holes from the product. The hexapod change and hexapod trial 2 that the critic queued after this were not done: one unit per iteration.

## Method
- `cadex_library_api.py`: `BoardPart.mounting` and the frozen `BoardMounting`. I tried fusing the disjoint bosses into one solid first. The kernel produced a compound ("declared solid but ... Compound containing 3 solids"), so they are lists, used as `part.cut(part.fuse([carrier, *m.standoffs]), m.holes)`.
- Fail-first real-kernel fixture `test_mounting_check.py::test_a_board_on_its_own_mounting_threads_every_screw_on_the_real_kernel`. The D36V50F6 is on a vertical web, rolled `direction=(1,0,0), roll 90` as in trial 3:
  - **Trial 3's own hold** (major-diameter bores, M2×6 bolts at the trial's seat): `contact only`, 3 `unthreaded`, so 0 of 3.
  - **`.mounting(standoff=3)`**: `held` by `screws`, `3 of 3`, no unthreaded, no misfits, no intersection, `fit.threaded_count` 3.
  - Before the change, the mounted half failed on the installed engine with `'BoardPart' object has no attribute 'mounting'`.
  - The fixture declares no welds, so its touching pairs read `below clearance`. The test asserts only that no row is an intersection.
- Headless `test_library.py::test_board_mounting_sizes_standoffs_taps_and_screws_from_the_board` pins boss and pilot sizes and origins, the screw seat in the rotated frame (matches trial 3's `(7+1.57, y, z)`), the screw-size choice and every refusal.
- `pixi run test-engine`: 2598 passed, 61 skipped. `pixi run python -m pytest cli/tests` with `CUDA_VISIBLE_DEVICES=""`: 1291 passed, 1 skipped. No packaged gate was run, because no protocol op, response shape, digest or payload structure moved.

## Result
- True now: a board with mounting holes is screwed down by `board.mounting()`, and its screws thread printed material by construction. The fixture reads 0 of 3 the trial-3 way and 3 of 3 with the helper. The product agent reads this in the overlay.
- Not re-measured: `orun1-t3-balancer` stays at **8 of 11**. It is an accepted product-agent design and is not hand-edited. Only a new balancer turn at ≥ `f78f1e8f` shows whether the agent uses the helper.
- Assumptions:
  - A 3 mm default standoff matches `board.bay()`'s default underside + clearance.
  - Screw length is PCB + 2.5 d whatever the standoff, so on a standoff shorter than 2.5 d the tip relies on solid carrier below the boss. The design's own fit and mounting still measure that.
- No new dependency.
- Next, in the critic's queue: the hexapod change for leg proportion and joint clutter, then hexapod trial 2. Tail: one unreconciled record (this one).

Dispatch closed: 1 unit — ADR-493 board.mounting() gives boards standoffs, tap-drill holes and seated screws; trial-3-style board hold 0/3 threaded → 3/3 held by screws on the real kernel

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: f78f1e8ffe26b7173d6337de3abf13103efba937

## State Impact

- target: loyal-ocean-0768 — boards gain BoardPart.mounting() (ADR-493, f78f1e8f): standoffs, tap-drill holes and seated lib.bolt screws per mounting hole; D36V50F6 rolled as in balancer t3 reads 0 of 3 threaded with the trial's major-diameter bores, 3 of 3 held by screws with .mounting(); overlay teaches it
