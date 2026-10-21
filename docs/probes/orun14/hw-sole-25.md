# orun14 P1: hw-sole at 25, heel_pitch w20 on the sole clip

Verified against source: 2026-10-21. Follows `ps-sole-50.md`; the same
iteration wrote `leo-v03.1.md` (the pin stop change, refused at build).

## The run and the judging

- **The run:** hw-sole is ps-sole's task with `heel_pitch` w20 (from w10),
  one literal (`~/orun14-hw.py`), revision `9820961f`, model unchanged,
  cold, 4096 envs, seed 0, budget 4,800 s, launched 11:15:05.
- **The checkpoint:** `gallop.000025.cxpolicy`, sha256 `d385f86b`, landed
  11:50 (74 s an iteration from 10, as ps-sole). Reward per step 16.9 at
  iteration 24 (ps-sole 15.8), episodes 3,277 steps.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010, on
  the CPU, evaluation `hw-sole-25`; then `orun12/legs.py`,
  `orun13/p2_lag.py`, `orun13/spine_foot.py` and `paw_floor.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off | heel stance height mm | no_tap | every_stride | straight | overreach mm LH / RH | stride mm | touchdown Hz | flight strides / s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ps-sole-25 | 0/10 | 0.79 / 0.96 / 1.10 | 0.03 / 0.17 (0/10, 0.028) | 0.00 / 0.00 | 20 / 9 | 0/10 (2.03) | 10/10 | 6/10 (24.4) | −224 / −244 | 251 / 223 | 3.44 / 3.11 | 0.54 / 0.020 | 1.56 (j_wrist_l) | 0.00 | 2.6 |
| **hw-sole-25** | 0/10 | 0.38 / **0.49** / 0.58 | **0.02 / 0.01** (0/10, 0.009) | 0.00 / 0.00 | 7 / 9 | 1/10 (1.79) | 10/10 | 0/10 (31.8) | −190 / −100 | 148 / 155 | 2.67 / 2.22 | 0.00 / 0.000 | 2.29 (j_tail1) | 0.00 | 1.8 |

- **Passing:** `completes`, `no_fall` and `upright` 10/10 (16.3°).
- **Left and right (O5):** heels 0.02 / 0.01; stride 148 / 155 mm (5%);
  touchdowns 2.67 / 2.22 Hz (17%).

### The hind paws (`paw_floor.py`, medians over 10 seeds)

| evaluation | leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | taps | pin ° / floor ° at lift | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|---|---|
| ps-sole-25 | LH | 0.00 / 0.72 / 0.07 / 0.18 | 0.03 | +0.5 | +29.9 | — | — | 438 / 979 | 179 | 0.00 |
| ps-sole-25 | RH | 0.11 / 0.49 / 0.00 / 0.38 | 0.17 | +4.2 | +22.2 | — | — | 366 / 861 | 109 | 0.00 |
| **hw-sole-25** | LH | 0.02 / **0.93** / 0.00 / **0.05** | 0.02 | +1.2 | +13.8 | 0.88 | +20.2 / +0.6 | 215 / 699 | 97 | 0.00 |
| **hw-sole-25** | RH | 0.01 / **0.94** / 0.01 / **0.04** | 0.01 | +1.3 | +15.8 | 0.89 | +19.7 / +1.0 | 256 / 482 | 93 | 0.00 |

- **The paw is flat, but the heel is up.** 0.93–0.94 of ground frames are
  `R`: the paw flat on the floor (+1° of floor pitch), the pin 14–16°
  toes-up of the metatarsus, the heel off. That is the digitigrade-pad
  stance O2a asks for when slow, not P1's.
- U is 0.05 / 0.04, the lowest of any v03 screen, and the pin's p95 rate
  is under 900 °/s with no flapping (O9).

### Gait, spine, O9

- **Pair lag (`p2_lag.py`):** fore 0.294 of the stride, hind 0.343
  (together on 0.10 / 0.00); no flight; rotary on 1/10 seeds (56 of 80
  ordered strides).
- **Spine (`spine_foot.py`):** 12.7° a stride (both joints), 0.07 of
  frames at a stop, cable gap at most 0.21°.
- **Drives (O6):** the worst RMS over rated is 2.29 on `j_tail1`; the
  peak margin is 0.

## The decision: keep rule fails at 25; runs to 50

**Keep rule** (heel share over ps-sole-25 on both legs, U under 0.2): U
passes (0.05 / 0.04), heel share fails (0.02 / 0.01 against 0.03 / 0.17).

**The critic's test:** U is under 0.2 on both legs, so this does not rule
the heel weight out. At 25 it has not moved the heel either: the doubled
`heel_pitch` bought a flat paw on a raised heel at half ps-sole-25's speed.

**Why it runs on, not stopped (O8):** p1-flat, the other slow screen, went
from heels 0.00 / 0.01 at 25 to 0.31 / 0.52 at 50 with U 0.22 / 0.38. hw-sole
at 25 has the same shape (slow, flat paw, heel up). The question it was
launched for is whether the heel comes down at 50 without the fold
(ps-sole-50: U 0.86 / 0.78). The pin-stop screen it was to hand the GPU to
was refused at build (`leo-v03.1.md`), so nothing else is queued. It ends
near 12:21 and is judged at 50 against ps-sole-50, kept only if heel share
reaches ps-sole-50's with U under 0.2 on both legs.
