# orun14 P1: ps-sole at 50, not kept; why LH-first strides are transverse

Verified against source: 2026-10-21. Follows `ps-sole-25.md`.

## The run and the judging

- **The run:** ps-sole, p1-flat's task (pin encoders observed, 122
  channels; `paw_flat` w10, `heel_pitch` w10, 19 terms) on ADR-784's
  `flat_feet="sole"` clip. Revision `6caadfaa`, cold, 4096 envs, seed 0.
  It ran all 50 iterations in 3,765 s (exit 0, witness error 1.8e-7).
- **The checkpoint:** the final `gallop.cxpolicy` (iteration 49, the
  best), sha256 `4131fa85`. Reward per step 31.1 against 15.8 at
  iteration 24; episodes 987 steps.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010, on
  the CPU, evaluation `ps-sole-50`, then `orun12/legs.py`,
  `orun13/p2_lag.py`, `lead_order.py` (new, below),
  `orun13/spine_foot.py`, `paw_floor.py`, `paw_flat.py`, `rod_gap.py` and
  `wrist_peak.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off | heel stance height mm | no_tap | every_stride | straight | overreach mm LH / RH | stride mm | touchdown Hz | flight strides / s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ps-sole-25 | 0/10 | 0.79 / 0.96 / 1.10 | 0.03 / 0.17 (0/10, 0.028) | 0.00 / 0.00 | 20 / 9 | 0/10 (2.03) | 10/10 | 6/10 (24.4) | −224 / −244 | 251 / 223 | 3.44 / 3.11 | 0.54 / 0.020 | 1.56 (j_wrist_l) | 0.00 | 2.6 |
| s1-sole-50 | 0/10 | 2.68 / 2.80 / 2.90 | 0.17 / 0.08 (0/10, 0.080) | 0.04 / 0.13 | 10 / 16 | 0/10 (1.96) | 9/10 | 10/10 (12.6) | 512 / −323 | 1071 / 568 | 2.89 / 4.56 | 1.00 / 0.170 | 1.60 (j_spine) | 0.00 | 4.1 |
| **ps-sole-50** | 0/10 | 2.50 / **2.60** / 2.66 | **0.37 / 0.19** (0/10, 0.192) | 0.33 / 0.21 | 4 / 14 | 0/10 (1.64) | 10/10 | 9/10 (20.7) | 526 / 191 | 1042 / 984 | 2.44 / 3.22 | **1.00 / 0.160** | 1.82 (j_spine) | 0.00 | 3.4 |

- **Passing:** `completes`, `no_fall` and `upright` 10/10 (18.5°);
  `overreach` 10/10 (191 mm), the first v03 policy to pass it.
- **Left and right (O5):** heels 0.37 / 0.19 (49% apart); stride 1,042 /
  984 mm (6%); touchdowns 2.44 / 3.22 Hz (24%).

### The hind paws (`paw_floor.py`, `paw_flat.py`, medians over 10 seeds)

| evaluation | leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | lifts toes-up of floor | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|---|
| ps-sole-25 | LH | 0.00 / 0.72 / 0.07 / 0.18 | 0.03 | +0.5 | +29.9 | 0.07 | 438 / 979 | 179 | 0.00 |
| ps-sole-25 | RH | 0.11 / 0.49 / 0.00 / 0.38 | 0.17 | +4.2 | +22.2 | 0.23 | 366 / 861 | 109 | 0.00 |
| **ps-sole-50** | LH | 0.00 / 0.12 / 0.01 / **0.86** | 0.37 | **+36.9** | **+46.8** | 0.61 | 490 / 1102 | 204 | 0.00 |
| **ps-sole-50** | RH | 0.00 / 0.14 / 0.06 / **0.78** | 0.19 | **+37.7** | **+59.0** | 0.45 | 284 / 1199 | 230 | 0.00 |

- **Every heel-down frame is on a paw toes-up of the floor.**
  - `paw_floor.py` counts no `F` frame on either leg: heel down and paw
    flat never coincide.
  - The paw sits about 37° toes-up of the floor in stance.
  - RH's pin is at +59° in stance, on its 60° toes-up stop; LH's is at
    +47°.
- **This is s1-sole-50's habit, which `paw_flat` w10 did not stop.**
  - The term pays 0.10–0.11 a paw-down frame on average.
  - It reads the floor pitch within 1.2° p10–p90 of the geometry
    (C = +1.67 against the term's +1.7), so it sees the fold and the
    policy accepts the loss.
- **`spine_foot.py`'s sole check is blind to this fold on v03.**
  - It calls 0.87 / 1.00 of heel-down frames flat.
  - It reads the paw's lowest point. A paw folded toes-up still rests its
    pad on the floor, so that point is down.
  - On v03, `paw_floor.py`'s floor pitch is the flat-foot check, and
    `spine_foot.py`'s flat column is not.
- **O9's pin rate holds:** the p95 rate is under 900 °/s on both legs, and
  nothing flaps in swing.

### Gait, spine, O9

- **Pair lag (`p2_lag.py`):**
  - fore 0.240 of the stride, together on none;
  - hind 0.048, together on 0.67: the hinds land as a pair, as on
    s1-sole-50;
  - rotary on 0/10 seeds (78 rotary of 92 ordered strides, 73 tied);
  - a flight on every stride, 0.160 s median.
- **Spine (`spine_foot.py`):**
  - 32.3° a stride (both joints), 0.00 of frames at a stop;
  - the cable gap is at most 0.57°;
  - peak flexion at 0.80 of the stride, extension at 0.40.
- **Rod loops (`rod_gap.py`):**
  - `j_frodbot_l` reaches 3.41 mm and `j_frodbot_r` 3.16 mm, on 30 / 31
    frames over 2 mm across all 10 seeds;
  - every one is at wrist peak, with the carpus up to 27.7° past its stop
    (`wrist_peak.py`), as in `wrist-peak.md`.
- **Drives (O6):** the worst RMS over rated is 1.82 on `j_spine`. The
  front wrists reach peak on 0.76 / 0.90 of fore stance, so the peak
  margin is 0.

## The decision: not kept

**Keep rule:** heel share above h1-meta-25's (0.07 / 0.04) on both legs,
with U share under 0.2. The heel shares pass (0.37 / 0.19), but the U
shares fail (0.86 / 0.78). By O2 this is a fault, not P1: the heel is
down only on a folded paw.

**What the four v03 screens past 50 iterations show:**

| checkpoint | top 2 s m/s (median) | heel LH / RH | U LH / RH |
|---|---|---|---|
| g1-free-50 | 2.24 | 0.30 / 0.16 | 0.76 / 0.77 |
| g1x-free-75 | 2.85 | 0.36 / 0.18 | 0.84 / 0.80 |
| s1-sole-50 | 2.80 | 0.17 / 0.08 | 0.51 / 0.81 |
| p1-flat-50 | 1.46 | 0.31 / 0.52 | 0.22 / 0.38 |
| ps-sole-50 | 2.60 | 0.37 / 0.19 | 0.86 / 0.78 |

- Every policy that reached 2.2 m/s or more folded its paw toes-up behind
  the heel. That happened with and without the pin observed, and with and
  without `paw_flat`.
- The only one with U under 0.4 on both legs, p1-flat-50, ran at 1.46
  m/s.
- The fold is not on the clip, which holds the paw within 4° of flat in
  stance (`paw_flat.py`, clip rows), so tracking does not pay it.

**A measurement for O1, not acted on here.**
- In stance RH's pin sits on its 60° toes-up stop (+59° median), and LH's
  near it (+47°).
- The fold is a joint stop the policy stands on. The stop makes the
  metatarsus and the folded paw one rigid foot, which is what the welded
  v02 paw was.
- A shorter toes-up travel would bound the fold. With the stop at 30°,
  the paw can fold at most about 30° of the metatarsus.
- The charter names 60° of travel as the owner's choice (O1, "the free,
  unsprung paw pin"). Any change needs a write-up before its build, and a
  note for the owner in R1.

## Why LH-first strides are transverse (P2, the critic's question)

`lead_order.py` (new) crosses each stride's hind order with its fore order,
over every settled stride of an evaluation. `legs.footfall_kind` calls a
stride rotary when the fore paw that lands right after the hind pair is on
the same side as the second hind.

**The clip asks RH, LH, LF, RF.** Its phase offsets are LH 0.000, RH 0.850,
LF 0.350 and RF 0.500, so RH lands 0.15 of the cycle before LH.
`p2_lag.py`'s "LH LF RF RH" is the same cycle read from LH. The clip label's "RH lead" is the generator's word
for the hind that lands first.

| evaluation | LH first, LF next | LH first, RF next | RH first, LF next | RH first, RF next | fores LF-first | hinds RH-first | tied |
|---|---|---|---|---|---|---|---|
| s1-sole-25 | 58 transverse | 2 rotary | 85 rotary | 1 transverse | 0.98 | 0.59 | 34 |
| ps-sole-25 | 68 transverse | 2 rotary | 66 rotary | 0 | 0.99 | 0.49 | 9 |
| s1-sole-50 | 4 transverse | 0 | 90 rotary | 0 | 1.00 | 0.96 | 75 |
| p1-flat-50 | 19 transverse | 0 | 170 rotary | 0 | 1.00 | 0.90 | 12 |
| g1x-free-75 | 0 | 0 | 91 rotary | 0 | 1.00 | 1.00 | 112 |
| ps-sole-50 | 13 transverse | 4 rotary | 74 rotary | 1 transverse | 0.95 | 0.82 | 73 |

**The answer:**
- Every policy keeps the clip's fore order, LF before RF, on 0.95–1.00 of
  strides.
- A stride whose hinds land LH-first has the hind pair reversed against the
  clip. Followed by LF, it is LH RH LF RF, transverse by definition.
- So "LH-first is transverse" is not a left-leg fault. It is the hind
  pair's order slipping while the fore pair's holds.
- The hinds slip when their lag is near zero. ps-sole-25's hinds split
  0.49 / 0.51 in order, and at 50 the policies land them as a pair (hind
  lag 0.048, together on 0.67).

**For P2:**
- The lever is the hind pair's lag, not the fore order and not the left
  leg.
- If the hinds land at least 40 ms apart and RH first, as the clip asks,
  every stride reads rotary.
- The rotary failures are today's tied strides (73 of 165 on ps-sole-50),
  not transverse ones.

## hw-sole, launched

- **The bundle:** `~/orun14-hw.py` is `orun14-ps.py` with `heel_pitch`
  w20 (from w10), one literal. Built as revision `9820961f`, with the
  model unchanged.
- **The queue:** `orun13/queue_run.py hw-sole 4800 50 --envs 4096 --after
  ps-sole --build ~/orun14-hw.py`, cold. The build ran 10:54–11:02, and
  hw-sole launched at 11:15:05 as ps-sole ended.
- **The judging:** at 25 against ps-sole-25 (heels 0.03 / 0.17, U 0.18 /
  0.38). It answers whether the heel weight moves the heel share, and
  whether it moves it on a flat paw (U under 0.2) or a folded one.
- **Timing (O8):** iteration 10 landed at 11:31:30, about 985 s after
  launch with the compile included (ps-sole: 983 s). Checkpoint 25 falls
  near 11:50, and 50 iterations end near 12:21, inside the 4,800 s budget.
