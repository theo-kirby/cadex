# orun14 P1: ps-sole at 25, the sole clip with the pin observed

Verified against source: 2026-10-21. Follows `s1-sole-50.md` (the
bundle check and paw_flat's offset) and `p1-flat-50.md`.

## The run and the judging

- **The run:** ps-sole is p1-flat's task (pin encoders observed, 122
  channels; `paw_flat` w10, 19 terms) on ADR-784's `flat_feet="sole"`
  clip. Revision `6caadfaa`, model unchanged, cold, 4096 envs, seed 0,
  budget 4,800 s. Launched 10:10:04.
- **Timing (O8):**
  - iteration 10 landed 983 s after launch, compile included (s1-sole: 917
    s);
  - checkpoint 25 at about 2,097 s, so 74 s an iteration from 10 to 25;
  - 50 iterations come to about 3,950 s, inside the budget, ending near
    11:16.
- **The curve:** reward per step 20.5 / 13.5 / 15.8 at iterations 0 / 10 /
  24, with episodes 2,214 steps long at 24. That is s1-sole's shape.
- **The checkpoint:** `gallop.000025.cxpolicy`, sha256 `dbd441d2`.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010, on
  the CPU, evaluation `ps-sole-25`, then `orun12/legs.py`,
  `orun13/p2_lag.py`, `orun13/spine_foot.py`, `paw_floor.py`,
  `rod_gap.py`, `wrist_peak.py` and `paw_flat.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off | heel stance height mm | no_tap | every_stride | straight | overreach mm LH / RH | stride mm | touchdown Hz | flight strides / s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| p1-flat-25 | 0/10 | 0.36 / 0.41 / 0.57 | 0.00 / 0.01 (0/10, 0.000) | 0.00 / 0.00 | 9 / 10 | 0/10 (3.50) | 7/10 | 5/10 | −206 / −144 | 188 / 150 | 2.50 / 1.78 | 0.00 / 0.000 | 2.25 (j_tail1) | 0.00 | 1.9 |
| h1-meta-25 | 0/10 | 0.61 / 0.73 / 0.85 | 0.07 / 0.04 (0/10) | 0.04 / 0.00 | 10 / 10 | 0/10 (2.10) | 9/10 | 2/10 | −222 / −177 | 173 / 192 | 2.78 / 3.00 | 0.10 / 0.000 | 1.86 (j_tail1) | 0.00 | 2.1 |
| s1-sole-25 | 0/10 | 0.93 / 1.02 / 1.17 | 0.06 / 0.06 (0/10, 0.055) | 0.00 / 0.03 | 16 / 14 | 0/10 (1.93) | 10/10 | 9/10 | −162 / −279 | 247 / 212 | 3.56 / 4.67 | 0.63 / 0.040 | 1.53 (j_spine) | 0.00 | 2.5 |
| **ps-sole-25** | 0/10 | 0.79 / **0.96** / 1.10 | **0.03 / 0.17** (0/10, 0.028) | 0.00 / 0.00 | 20 / 9 | 0/10 (2.03) | 10/10 | 6/10 (24.4) | −224 / −244 | 251 / 223 | 3.44 / 3.11 | 0.54 / 0.020 | 1.56 (j_wrist_l) | 0.00 | 2.6 |

- **Passing:** `completes`, `no_fall` and `upright` 10/10 (17.7°).
- **Left and right (O5):** heels 0.03 / 0.17 (84% apart); stride 251 /
  223 mm (11%); touchdowns 3.44 / 3.11 Hz (10%).

### The hind paws (`paw_floor.py`, `paw_flat.py`, medians over 10 seeds)

| evaluation | leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | lifts toes-up of floor | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|---|
| s1-sole-25 | LH | 0.01 / 0.58 / 0.01 / 0.41 | 0.06 | +2.6 | +34.0 | 0.16 | 432 / 1314 | 143 | 0.00 |
| s1-sole-25 | RH | 0.05 / 0.77 / 0.01 / 0.16 | 0.06 | +1.2 | +21.4 | 0.10 | 401 / 922 | 156 | 0.00 |
| **ps-sole-25** | LH | 0.00 / 0.72 / 0.07 / **0.18** | 0.03 | +0.5 | +29.9 | 0.07 | 438 / 979 | 179 | 0.00 |
| **ps-sole-25** | RH | 0.11 / 0.49 / 0.00 / **0.38** | 0.17 | +4.2 | +22.2 | 0.23 | 366 / 861 | 109 | 0.00 |

- The pin observation and `paw_flat` turned LH's fold around against
  s1-sole-25 (U 0.41 → 0.18, pin +34 → +30°).
- RH carries the heel (0.17, flat on 0.93 of its heel-down frames by
  `spine_foot.py`), but folds toes-up on 0.38 of its ground frames.
- The pin's p95 rate is under O9's 900 °/s on both legs, and nothing flaps
  in swing.
- paw_flat's refit offset on this run is C = +1.50 against the term's
  +1.9. F tracks the geometric floor pitch within 2.4° p10–p90.

### Gait, spine, O9

- **Pair lag (`p2_lag.py`):**
  - fore 0.372 of the stride, hind 0.195;
  - together on 0.05 / 0.16 of strides;
  - rotary on 0/10 seeds (68 of 136 strides), because every LH-first
    stride is transverse and every RH-first one rotary, as on s1-sole-25;
  - a flight on 0.54 of strides, 20 ms median.
- **Spine (`spine_foot.py`):**
  - 40.3° a stride (both joints), the widest on v03 so far;
  - 0.04 of frames at a stop;
  - the cable gap is at most 0.65°.
- **Rod loops (`rod_gap.py`):**
  - `j_frodbot_l` reaches 2.61 mm on 14 frames, every one at wrist peak;
  - the other three loops stay under 1.9 mm.
- **The wrist (`wrist_peak.py`):** at peak on 0.41 / 0.30 of fore stance,
  up to 16° past the carpus stop.

## The decision: not kept at 25; runs to 50

**Keep rule:** heel share above h1-meta-25's (0.07 / 0.04) on both legs,
with U share under 0.2. It fails:
- LH: heel 0.03 against 0.07, U 0.18;
- RH: heel 0.17 against 0.04, U 0.38.

**Against p1-flat-25, the same task on the old clip at the same
checkpoint:**
- heels 0.03 / 0.17 against 0.00 / 0.01;
- 0.96 m/s against 0.41;
- flight on 0.54 of strides against none;
- U is no worse (p1-flat-25: 0.03 / 0.23 at its slower, shuffling gait).

p1-flat went from 0.00 / 0.01 at 25 to 0.31 / 0.52 at 50. ps-sole is
ahead of it at 25, so its measure is moving, and O8's early stop does not
apply. It runs to 50, about 11:16, and is kept only if its 50 checkpoint
passes the keep rule.

**If ps-sole-50 stalls (the critic's ask), the next lever is not a clip.**
- Four clips have now been screened on v03: the plain clip, the
  pad-in-floor clip, the sole clip, and the sole clip with the pin
  observed.
- Across them, heel share has tracked how long the screen ran (p1-flat
  0.01 → 0.31 / 0.52 at 25 → 50), not the clip.
- The lever is the weight that pays the heel. `heel_pitch` is w10 (`orun14-ps.py`). The next screen doubles it to w20 on
  ps-sole's task, cold. It is one literal, and judged against ps-sole at
  the same checkpoint.
- A warm start from p1-flat-50 is not possible on the sole clip: the
  trainer refuses a policy whose task digest differs (`orun13/queue_run.py`,
  `--init-from`).
