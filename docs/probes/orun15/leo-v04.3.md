# orun15 P1: leo-v04.3, the paw spring's rate 8 → 12 (O1 write-up)

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 16).
Written before the build, as O1 asks. Follows `ssw-sole.md` (`hind_place`
a dead end cold and warm) and `leo-v04.2.md` (the 4 → 8 step, kept).

## The measurement

- **The rate is the one lever that has moved U at speed.** U (the share
  of on-ground frames with the paw toes-up of the floor past 5°,
  `orun14/paw_floor.py`), every v04/v04.2 policy at 50 or warm +25:

| policy | lever | U LH / RH | m/s |
|---|---|---|---|
| sf-sole-50 | v04 coil (4 N·mm/deg), `paw_fold` | 0.29 / 0.29 | 2.37 |
| sfp-sole-50 | preload 30° (leo-v04.1) | 0.23 / 0.28 | 2.35 |
| **k8-sole-50** | **rate 4 → 8 (leo-v04.2)** | **0.11 / 0.20** | 2.58 |
| hlk8-sole-50 | v04.2 + `hind_lag` (hinds split, RH first) | 0.29 / 0.02 | 2.17 |
| fl-sole-50 | hlk8 + `fore_lag` | – (not kept, `fl-sole.md`) | – |
| ssw-sole-25 | hlk8 + `hind_place` w −10, warm | 0.39 / 0.03 | 2.23 |

- With the hinds split (the rotary gait P2 needs), the second hind to
  land folds (`hlk8-mirror.md`: it follows the order, not the side), and
  neither `hind_place` cold nor warm moved it (`ss-sole.md`,
  `ssw-sole.md`). The 4 → 8 step cut U by 0.18 / 0.09 on the tied gait;
  this asks whether 12 takes the second hind's fold under 0.2 on the
  split one.

## The change

- **`PAW_K` 8 → 12 N·mm/deg**, `PAW_PRELOAD` stays 10°. Nothing else: the
  coil's part reads neither number, so geometry and clearance should be
  v04.2's, and the bundled model should differ from hlk8-sole's only in
  the two pins' `stiffness` (0.458366 → 0.687549 N·m/rad).
- **The script:** hlk8-sole's (`~/orun15-queue/orun15-hlk8.py`, project
  `e11bd4f`, 21 terms with `hind_lag`, `fore_sync_w` 2 as stored) with
  that one line and its comment (`~/orun15-queue/orun15-v043.py`), so the
  screen against hlk8-sole has the rate as its one change.

## Still easy (O1)

| pin toes-up of the metatarsus | v04.2 N·mm | **v04.3 N·mm** | share of a ~3.2 N·m pad push, v04.3 |
|---|---|---|---|
| 0° (flat, on the stop) | 80 | **120** | 3.8% |
| 8.4° (the clip's swing pin) | 147 | 221 | 6.9% |
| 17 / 26° (v04 stance medians) | 216 / 288 | 324 / 432 | 10–14% |
| **30°** | 320 | **480** | **15%** |
| 60° (the toes-up stop) | 560 | 840 | 26% |

- **It cannot hold the paw off the floor**: the coil pushes toes-down
  onto the flat stop, so at flat it only presses the paw onto that stop,
  120 N·mm, about 3× the paw's own ~36 N·mm.
- **The stand, measured before the build** (`orun14/stand_pin.py` on
  hlk8-sole's bundle model with only the two pins' `stiffness` set to
  0.687549, `/tmp/orun15-k12`, not committed), against the same model at
  8:

| | k 8 (hlk8-sole's model) | k 12 |
|---|---|---|
| NaN | no | no |
| pins at 3 s, deg (l / r) | 0.3 / −0.3 (on the flat stop) | 0.3 / −0.3 |
| pin peak while settling, °/s | 92 / 92 | 85 / 85 |
| chest z at 3 s / pitch | −11.6 mm / 1.0° | −11.6 mm / 1.0° |
| paw / heel lowest, mm | −0.3 / 64.1 | −0.3 / 64.1 |

- **Still overdamped:** with the pin inertia `leo-v04.2.md` measured
  (1.51e-4 kg·m²) and damping 0.1719 N·m·s/rad, f_n = 10.7 Hz and
  ζ = 8.4 (10.3 at 8), so it cannot ring; the return time constant c/k
  falls 0.38 → 0.25 s, returning a paw from 30° at 160 °/s (107 at 8).
- **The risk:** at 30° the coil is 15% of a pad push and at the toes-up
  stop 26%, against 10% / 17.5% on v04.2. Where the heel lifts furthest
  on a flat paw it pushes hardest, so the heel's share at toe-off is the
  check that it has not stopped the heel lifting (k8 already cut toe-off
  0.38 / 0.15 → 0.13 / 0.09 on the tied gait).

## The build, the gates and the screen

- **Build** through `orun13/queue_run.py --after hlk8-sole --build
  orun15-v043.py` (hlk8-sole is registered long since, so it builds at
  once), then `~/orun15-queue/v043-chain.sh`: `cadex clearance` and
  `--sweep`, `orun13/clearance_diff.py` against v04's reports, and the tag
  `leo-v04.3` only if no pair is new.
- **The screen, hk12-sole: cold.** The critic asked for warm from
  hlk8-sole-50; the trainer refuses a warm start across a change of robot
  (`check_curriculum_change`: "A warm start may move the robot onto
  another course, never change the robot"; orun14 hit the same refusal,
  `orun14/g1-free-25.md`), and a stiffness is a change of robot. So it
  runs cold, like k8-sole on v04.2, against hlk8-sole's cold run: 50
  iterations, 4,096 envs, seed 0, `budget_s` 5,500 (50 × ~90 s and
  start-up, +20%).
- **Stop rule at 25** (a cold run at 25 is a shuffle, hlk8-sole-25 0.69
  m/s, so the critic's ≥ 2.0 m/s applies at 50): stop if the hinds have
  tied (together on > 0.2 of strides, hlk8-sole-25 0.00) or either hind's
  U is ≥ 0.25 (hlk8-sole-25 0.01 / 0.19).
- **Keep rule at 50:** the second hind's U under 0.2 and the first's ≤
  0.05; ≥ 2.0 m/s; the hinds ≥ 40 ms apart on ≥ 5 seeds; the heel's
  stance share ≥ 0.3 each leg; pins p95 under 900 °/s, no flapping in
  swing; the heel at toe-off reported against hlk8-sole-50's 0.18 / 0.72.

## Built (after the write-up above)

- **The build:** `cadex script --set` from `queue_run.py --after hlk8-sole
  --build`, project commit `3ae1853`, accepted revision **`7a69ad4a`**,
  3.6 min (23:59:12 → 00:02:46).
  - Every verdict in the attempt's `result.json` equals v04.2's revision
    `29298667` (ss-sole's; 560 verdict fields compared, 0 differ).
  - The bundled `cat_model-model.xml` (`3783175d`) differs from
    hlk8-sole's only in the two pins' `stiffness`: 0.458366 → 0.687549
    N·m/rad; the task bundle differs from hlk8-sole's only in its `model`
    key.
- **Clearance** (`~/orun15-queue/v043-chain.sh`): `cadex clearance` rc 0,
  `--sweep` rc 0, `orun13/clearance_diff.py` against v04's reports:
  **static 14 → 14, swept 8 → 8, 0 new**, leo's baseline.
- **The stand on the built model** (`orun14/stand_pin.py`): no NaN, both
  pins 0.3° into the flat stop, pin peak 85 °/s while settling, paws at
  −0.3 mm, heels 64.1 mm, the clip's `j_spine2` equal to `j_spine`.
- **Tagged `leo-v04.3`** at project `3ae1853`. `leo-v02` … `leo-v04.2`
  are untouched.
- **hk12-sole** launched cold on `7a69ad4a` at 00:02:49
  (`~/orun15-queue/hk12-sole.log`).

## Timed (hk12-sole)

- Iteration 10 by 00:19:26, **16.6 min after launch** (hlk8-sole 16.8),
  about 90 s an iteration with start-up; the trainer's ETA at 10 was
  3,275 s more, so about 4,270 s in all, inside `budget_s` 5,500.
- Reward per step 20.3 / 13.8 at 0 / 10 (hlk8-sole 20.3 / 13.8).
- +25 is due near 00:42 and 50 near 01:13; judged by the rules above.
