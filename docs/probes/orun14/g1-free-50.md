# orun14: g1-free at its end, and heel_pitch on the free paw

Verified against source: 2026-10-21. Follows `g1-free-25.md`.

## g1-free at 50 (`gallop.cxpolicy`, sha256 `8ded5f68`)

- **The run:** leo v03 `bc287c9c`, g4-peak's task, cold, 4096 envs, seed
  0. It ran all 50 iterations in 3,781 s (76 s an iteration). The trainer
  read 30.2 reward/step at iteration 49, still rising about 0.5 an
  iteration.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010,
  on the CPU, evaluation `g1-free-50`. Then `orun12/legs.py`,
  `orun13/p2_lag.py`, `orun13/spine_foot.py`, `paw_floor.py` and
  `heel_meta.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off LH / RH | heel mm in stance | no_tap | every_stride | overreach mm LH / RH (spec) | stride mm | touchdown Hz | flight stride share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g4-peak-50 (v02) | 0/10 | 2.40 / 2.43 / 2.49 | 0.44 / 0.22 (0/10, 0.218) | 0.43 / 0.21 | 2 / 14 | 0/10 (1.68) | 10/10 | 416 / 141 | 978 / 868 | 2.33 / 4.00 | 1.00, 0.160 | 1.80 (j_spine) | 0.00 | 3.8 |
| g7-hock75-50 (v02.1) | 0/10 | 2.51 / 2.60 / 2.67 | 0.46 / 0.41 (6/10, 0.406) | 0.36 / 0.67 | 2 / 3 | 0/10 (2.01) | 10/10 | 396 / 7 | 1045 / 1035 | 2.44 / 2.44 | 1.00, 0.180 | 2.07 (j_spine) | 0.00 | 4.6 |
| g1-free-25 (v03) | 0/10 | 0.43 / 0.53 / 0.66 | 0.02 / 0.02 (0/10, 0.0145) | 0.00 / 0.00 | 6 / 10 | 0/10 (5.88) | 10/10 | −200 / −117 | 397 / 393 | 2.67 / 2.56 | 0.06, 0.000 | 2.42 (j_tail1) | 0.00 | 2.2 |
| **g1-free-50 (v03)** | 0/10 | 2.19 / **2.24** / 2.49 | **0.30 / 0.16** (0/10, 0.164) | 0.15 / 0.29 | 4 / 7 | 0/10 (2.31) | 10/10 | 451 / 47 (**10/10**, 47.1) | 895 / 475 | 2.44 / 5.50 | 1.00, 0.160 | 1.67 (j_spine) | 0.00 | 3.9 |

orun12's heel5c-s1 on feline v07 passed P1 on 8 of 10 seeds, with heels
0.60 / 0.61, at 2.91 m/s.

- **Passing:** `completes`, `no_fall`, `upright` (19.6°), `straight`
  (15.3°), `every_stride` (1.02) and, for the first time on leo,
  `overreach` (10/10, median 47 mm).
- **Failing medians:** `top_speed` 2.24 m/s, `hock_down` 0.164,
  `hock_at_toeoff` 0.155, `no_tap` 2.31.
- **Left and right differ (O5).**
  - RH touches down at 5.50 Hz against LH's 2.44: two contacts a stride.
  - Its stride is 475 mm against LH's 895, and its overreach 47 mm
    against 451.
  - Q1's 20% bar fails on all three measures.

### The hind paws: heel down, toes up

`paw_floor.py`, medians over 10 seeds:

| leg | on-ground F / R / T / U | heel share (engine) | pin ° in stance | toe-offs | taps | roll ≥3 | lifts toes-up of floor | pin rate p95 / max °/s | swing p95 °/s | swing > 900 | flapping swings |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LH | 0.02 / 0.21 / 0.00 / 0.77 | 0.02 (0.30) | +43.8 | 22 | 0.09 | 0.74 | 0.50 | 614 / 1185 | 219 | 0.000 | 0.00 |
| RH | 0.03 / 0.19 / 0.01 / 0.77 | 0.03 (0.16) | +38.1 | 49 | 0.38 | 0.06 | 0.63 | 589 / 1326 | 327 | 0.000 | 0.00 |

Seed 1001, 2.0–3.0 s:

    LH  ......UUUUR................UUUURRR.............UUUR
    RH  .....UUU.....UUU........UUU.......U.U............U.

- **Each hind stance starts with the paw toes-up.**
  - The policy lands for 3–4 frames on the heel and the rear of the pad,
    with the pin 38–48° toes-up of the metatarsus. Then it rolls onto the
    flat paw (`R`) and lifts.
  - Split of the `U` frames:

    | leg | paw and heel down | paw down, heel up | heel down, paw up | median pin ° |
    |---|---|---|---|---|
    | LH | 354 | 603 | 83 | 45–52 |
    | RH | 137 | 599 | 288 | 26–46 |

  - Most `U` frames have the paw's contact down. The paw sensor is one
    body, so the engine's `hock_down` counts those frames as heel and paw
    down.
- **This is O2's fault, back on the free pin.** It is orun12's paw folded
  toes-up behind a heel.
  - The 0.30 / 0.16 heel share is not a flat foot.
  - Of the heel-and-paw-down frames, 4 of 377 (LH) and 8 of 171 (RH) have
    the pin within 5° of its flat stop.
- **Caution on one reading:** `paw_floor.py`'s floor-pitch median reads
  +146° / +78°. At a pin of about 45° that is not a believable pitch, so
  that column is left out above. The pin angle is a direct relative
  reading. Fix the floor-pitch reading before using that column again.
- **Pin speed (O9):**
  - 614 / 589°/s p95 at the 20 ms frame rate, up from 230 / 262 at 25;
  - in swing, 219 / 327°/s p95, with no swing frame over 900°/s and no
    flapping;
  - single frames peak at 1,185 / 1,326°/s, at the landing slap.
  - The step-rate check still waits for a passing policy.

### Gait, spine, torque

- **A gallop at 2.24 m/s:**
  - flight on every stride, 0.160 s;
  - stride 2.44 Hz.
- **Pair lag (`p2_lag.py`):**
  - the fore lag is 0.151 of the stride, about 62 ms;
  - the hind lag is 0.326 of the stride, about 134 ms, with the hinds
    together on 0.21 of strides;
  - 3/10 seeds read rotary on 8 of 10 strides. Every ordered stride on
    every seed is rotary from RH; none is transverse.
- **Spine (`spine_foot.py`):**
  - 26.4° a stride (sum of the two joints);
  - 0.00 of frames at a stop;
  - the cable gap at most 0.51° (O9: 1°).
- **Torque:**
  - the worst RMS drive is `j_spine`, at 1.67× rated;
  - the peak margin is 0.00: a drive touches peak, as on every leo
    policy so far;
  - rod loops are open to 3.9 mm (O9: 2 mm).

## Stop rule for g1x-free

The rule from `g1-free-25.md`: stop g1x-free if g1-free's end reads under
1.5 m/s or heels under 0.10. g1-free-50 reads 2.24 m/s, with heels 0.30 /
0.16. The rule does not fire, so **g1x-free runs** (registered 06:34,
warm, critic warmup 5, 50 iterations).

## heel_pitch on v03 (`heel_meta.py`, O7)

`heel_meta.py` first checks the reward's metatarsus angle, `_META`.

- **Calibration:** on the bundle's 21 clip samples, `_META` equals
  `c_meta_h*`'s world pitch + 63.90° on both legs, with 0.00° spread. So
  a trace's metatarsus pitch gives the reward's angle exactly.
- **Where v03 is flat:**
  - frames with heel and paw down and the pin within 5° of its stop sit at
    `_META` +5.9 / +5.8 (g1-free-25, 52 frames) and +5.7 / +4.5
    (g1-free-50, 12 frames);
  - v02's welded sole was flat at +4.5. The 3 mm heel trim moved it.

`_META` on paw-down frames:

| evaluation | leg | heel-down share | `_META` heel down | `_META` heel up, median (p25–p75) |
|---|---|---|---|---|
| g1-free-25 | LH | 0.02 | +5.8 | +11.3 (+9.6–+13.4) |
| g1-free-25 | RH | 0.02 | +6.1 | +16.5 (+12.7–+20.2) |
| g1-free-50 | LH | 0.30 | +2.8 | +13.5 (+6.2–+27.4) |
| g1-free-50 | RH | 0.17 | +5.1 | +14.0 (+8.8–+25.1) |

Each shape's pay (0–1, before weight 10) and its slope towards flat at
the heel-up median:

| shape | g1-free-25 LH: heel down / heel up / slope | g1-free-25 RH | g1-free-50 LH | g1-free-50 RH |
|---|---|---|---|---|
| g4-peak's (0.3 g20 + 0.7 g3, centre +4.5) | 0.83 / 0.27 / 0.015 | 0.80 / 0.21 / 0.013 | 0.76 / 0.24 / 0.011 | 0.78 / 0.24 / 0.011 |
| **cubic, half-width 16, centre +6** | **0.86 / 0.30 / 0.083** | **0.87 / 0.04 / 0.022** | 0.52 / 0.15 / 0.052 | 0.70 / 0.13 / 0.047 |
| Gaussian width 6, centre +6 | 0.97 / 0.45 / 0.134 | 0.98 / 0.05 / 0.028 | 0.73 / 0.21 / 0.086 | 0.87 / 0.17 / 0.075 |
| Gaussian width 8, centre +6 | 0.98 / 0.64 / 0.107 | 0.99 / 0.18 / 0.059 | 0.83 / 0.41 / 0.097 | 0.92 / 0.37 / 0.092 |

- **The pick for h1-meta:** `(max(0, 1 - |_META - 6| / 16)) ** 3`.
  - It pays a heel-up stance no more than now, or less: 0.30 / 0.04
    against 0.27 / 0.21 on g1-free-25.
  - It slopes towards flat 5.5× and 1.7× as steeply, and 4.7× and 4.3×
    on g1-free-50.
  - Being two-sided, it pays g1-free-50's toes-up heel stances
    (`_META` +2.8) less, 0.52 against 0.76.
  - The Gaussians pay heel-up stances more, so they are out.
- **The bundle (`orun13/reward_terms.py`):** the same g1-free bundle with
  only heel_pitch swapped. heel_pitch pays 0.27 / 0.00 / 0.44 per step
  (hold / keyframe / clip), against 0.40 / 0.00 / 0.54 before. Every other
  term and every termination is unchanged.
- **The clip is heel-up in stance on v03.**
  - `orun13/heel_expr.py` on the bundle's clip samples: stance holds
    `_META` +8.6…+23 (LH) and +9.5…+16.6 (RH), 3–17° heel-up of v03's
    flat.
  - The kinematic replay pays `plantigrade` 0.000.
  - The clip's "heel on 0.8 of stance" (`g1-free-25.md`) is the
    generator's flag, not its geometry: `track_pose` pulls against the
    heel.

**What the metatarsus term cannot see.** g1-free-50's fault is the paw
toes-up on its pin under a down heel. `_META` reads the metatarsus, not
the paw, and the task does not observe the pin. A screen on this term
alone answers whether it lifts the heel share. The likely next levers for
the toes-up paw, neither one screened yet:

- observe the paw pin and pay it at its flat stop in stance;
- a clip whose stance metatarsus sits at v03's flat.
