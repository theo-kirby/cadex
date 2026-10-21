# orun15 P1: leo-v04.1, a larger paw-spring preload at the same rate (O1 write-up)

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 3).
Written before the build, as O1 asks.

## The measurement

- **sp-sole-50** (leo v04, `e560f053`; `sp-sole.md`) still folds the hind
  paws toes-up of the floor in stance: **U 0.32 / 0.29** (LH / RH), at
  2.18 m/s. P1 needs U under 0.2.
- Against tr-sole-50 on the unsprung pin, the 4 N·mm/deg coil took RH
  from 0.63 to 0.29 and its median fold from +35° to +23° of the floor.
  LH did not move (0.34 → 0.32, +25° median either way).
- **Where the coil stands in the fold:** the pin in stance has a median
  of +18 / +26° toes-up of the metatarsus, and +42 / +46° at lift. At
  v04's 4 × (θ + 10) the coil returns 112 / 144 N·mm in stance and
  208 / 224 N·mm at lift. In the build comment, a stance push at the pad
  is about 3.2 N·m, so that is 3.5–7% of it.
- **The rate has no room:** the pin's p95 rate is 748 / 775 °/s against
  O9's 900, and v06's stiffer sprung pin flapped at 900 °/s. A higher
  `PAW_K` would raise the spring's natural rate (and its swing
  overshoot) with the stiffness.
- **The preload adds torque without raising the rate:** it adds
  `PAW_K × ΔPRELOAD` at every angle, so the curve's slope, and the
  pin's spring-mass rate, stay as they are. The pin's damping
  (3.0 N·mm·s/deg) limits the extra 80 N·mm to about 27 °/s of
  terminal speed.
- **The stand, measured before the build** (`orun14/stand_pin.py` on
  sp-sole's bundle model with only `springref` moved from ±10° to ±30°,
  `/tmp`, not committed): no NaN, both pins seat 0.3° into the flat stop
  as on v04, pin peak 85 °/s while settling (v04: 99), chest and pitch
  equal to 0.1 mm and 0.1°, paws at −0.3 mm, heels 64 mm up.

## The change

- **`PAW_PRELOAD` 10 → 30°** toes-down past the flat stop. `PAW_K` stays
  4 N·mm/deg. Nothing else changes: the coil's part does not read
  `PAW_PRELOAD` (it is used only on the hinge's `spring_rest_deg`), so the
  geometry, and every clearance pair, is v04's.
- **The curve:**

| pin toes-up of the metatarsus | v04 (rest 10°) N·mm | v04.1 (rest 30°) N·mm | share of a 3.2 N·m pad push, v04.1 |
|---|---|---|---|
| 0° (flat, on the stop) | 40 | 120 | 3.8% |
| 8.4° (the clip's swing pin) | 74 | 154 | 4.8% |
| 18 / 26° (stance median, LH / RH) | 112 / 144 | 192 / 224 | 6–7% |
| 30° | 160 | 240 | 7.5% |
| 42 / 46° (at lift) | 208 / 224 | 288 / 304 | 9–9.5% |
| 60° (the toes-up stop) | 280 | 360 | 11% |

- **Still easy (O1):** at most 11% of a pad push at the toes-up stop, so
  the floor still lays the paw flat and the heel can still lift on a
  flat paw. At flat it presses the paw on its stop with 120 N·mm, about
  3.3 times the paw's own weight (~36 N·mm), where v04 pressed 40. It
  pushes the paw onto its stop and does not hold it off the floor, since
  the stop is at flat.

## Expected effect

- The fold is a pin held toes-up against the coil by the policy's own
  stance. A coil that returns 50–80% more torque across stance (+80 N·mm
  on 112–224) makes each folded frame dearer.
- **The expected result:**
  - U falls on both legs, most on LH, where v04 did nothing. The aim is
    under 0.2.
  - Speed stays within sp-sole-50's spread (2.08–2.29 m/s).
  - The heel share stays near 0.41 / 0.26.
  - The pin's p95 stays under 900 °/s, since the rate is unchanged.
- **The hypothesis it tests:** that the fold is a torque balance the
  coil can move. If it is a posture the policy holds whatever the coil
  costs, U will not move. Then the lever is the task (`paw_fold`,
  sf-sole), not the spring.

## The build, the gates and the screen

- **The script:** `~/orun15-v041.py` changes one line of the project's
  `script.py`: `PAW_K, PAW_PRELOAD = 4.0, 30.0`, with its comment.
  - The copy was taken after the fold screen's build had already
    accepted, so its base is `orun15-fd.py` (project `5ae71fd`), not
    `leo-v04`. The task therefore carries `paw_fold`: it is sf-sole's
    20 terms (`fd-sole.md`), not sp-sole's 19.
  - So **the screen to compare against is sf-sole**, which has the
    same task on the v04 coil. The preload is still the one change. The
    write-up first planned sp-sole's task. This is what was built.
- **The build:** `cadex script --set`, project commit `ed7d5ca`, accepted
  revision **`f3482223`**, digest `38343559`, 3.5 min.
  - Every verdict in the attempt's `result.json` equals v04's
    (`e560f053`): 129 satisfied, 10 redundant, 32 true, assembly
    `solved`.
  - The bundled `cat_model-model.xml` differs from sp-sole's only in
    `springref`: ±0.523599 rad (30°). The stiffness stays 0.229183
    N·m/rad, and damping, friction and range are v04's.
  - Bundle model `51bcac0e`.
- **Clearance:** `cadex clearance`, then `--sweep` (project `0d455b7`,
  `489f9b1`), then `orun13/clearance_diff.py` against v04's reports
  (`35cf83d`). The result is **static 14 → 14 and swept 8 → 8, 0 new**,
  leo's baseline.
- **The stand on the built model** (`orun14/stand_pin.py`): no NaN. Both
  pins seat 0.3° into the flat stop, as on v04. The pin peaks at
  85 °/s while settling (v04: 99). Chest, pitch, paws (−0.3 mm) and heels
  (64.1 mm) are v04's. In the clip, `j_spine2` equals `j_spine` (0.000°),
  and the pin runs −8.4..0 / 0..7.4°.
- **Tagged `leo-v04.1`** at project `ed7d5ca`. `leo-v02`, `leo-v03` and
  `leo-v04` are untouched.
- **The screen, sfp-sole:** sf-sole's task on v04.1. Cold, 50 iterations,
  4096 envs, seed 0, `budget_s` 5,100. It is queued with
  `--expect-revision f3482223` behind sf-sole, and starts when sf-sole
  frees the machine lock. It is judged at 25 and 50 with
  `orun14/paw_floor.py`.
- **Keep rule:**
  - U falls by at least 0.1 on LH against sf-sole-50, with RH no worse,
    or U is under 0.2 on both legs.
  - The speed is within 10% of sf-sole-50's median.
  - The pin's p95 stays under 900 °/s.
  - If sf-sole is stopped early as a dead end, sfp-sole is read against
    sp-sole-50 instead, and the two levers stay confounded. The report
    must say so.
