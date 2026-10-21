# orun14 P1: tr-sole at 25 and 50 (ADR-785's trailing paw), and fd-sole

Verified against source: 2026-10-21. Follows `hw-sole-50.md`, which
launched tr-sole.

## The run and the judging

- **The run:** tr-sole is ps-sole's task (19 terms: pin encoders,
  `paw_flat` w10, `heel_pitch` w10) on the sole clip with `trail_feet`
  (ADR-785), so the clip's swing pin peaks at 8.4 / 7.4° (was 57.7 /
  56.0). `~/orun14-tr.py`, revision `32890126`, leo v03 unchanged. It was
  cold, ran 50 iterations at 4096 envs (seed 0), launched 12:20:28 and
  finished 13:24, inside its 4,800 s budget.
- **The checkpoints:**
  - `gallop.000025.cxpolicy` (reward per step 16.6 at 24);
  - the final `gallop.cxpolicy`, iteration 49, sha256 `3f899cab`, reward
    per step 30.5 and still climbing. The trainer's `best` (`0f703b7f`)
    is an earlier iteration; the final one is the one judged.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010, on
  the CPU (evaluations `tr-sole-25` and `tr-sole-50`); then
  `orun11/summarize.py`, `orun12/legs.py`, `orun13/p2_lag.py`,
  `orun13/spine_foot.py`, `paw_floor.py` and `fold_term.py` (new).

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH | heel stance height mm | no_tap | every_stride | straight | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight share / s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ps-sole-25 | 0/10 | 0.79 / 0.96 / 1.10 | 0.03 / 0.17 (0.028) | 0.00 / 0.00 | 20 / 9 | 0/10 (2.03) | 10/10 | 6/10 | −224 / −244 | 251 / 223 | 3.44 / 3.11 | 0.54 / 0.020 | 1.56 (j_wrist_l) | 0.00 | 2.6 |
| **tr-sole-25** | 0/10 | 0.47 / **0.59** / 0.71 | 0.14 / 0.01 (0.012) | 0.00 / 0.00 | 5 / 8 | 0/10 (4.8) | 10/10 | 9/10 | −183 / −95 | 378 / 153 | 2.67 / 3.28 | 0.00 / 0.000 | 2.60 (j_tail1) | 0.00 | 1.9 |
| ps-sole-50 | 0/10 | 2.50 / 2.60 / 2.66 | 0.37 / 0.19 | 0.33 / 0.21 | 4 / 14 | 0/10 (1.64) | 10/10 | 9/10 | 526 / 191 | 1042 / 984 | 2.44 / 3.22 | 1.00 / 0.160 | 1.82 (j_spine) | 0.00 | 3.4 |
| **tr-sole-50** | 0/10 | 2.14 / **2.40** / 2.59 | **0.34 / 0.19** (0.192) | 0.27 / 0.38 | 3 / 6 | 0/10 (2.08) | 9/10 | 10/10 (15.6) | **+440 / +144 (10/10)** | 896 / 542 | 2.61 / 5.28 | 1.00 / 0.135 | 1.61 (j_hip_r) | 0.00 | 3.2 |

- **Passing at 50:** `no_fall`, `upright`, `straight` and `overreach` 10/10;
  `completes` and `every_stride` 9/10.
- **Left and right (O5), at 50:** heels 0.34 / 0.19 (44%), stride 896 /
  542 mm (40%), touchdowns 2.61 / 5.28 Hz (51%): the right hind steps short
  and twice as often, as on hw-sole-50.

### The hind paws (`paw_floor.py`, medians over 10 seeds)

| evaluation | leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | taps | pin ° / floor ° at lift | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|---|---|
| tr-sole-25 | LH | 0.13 / 0.79 / 0.00 / **0.07** | 0.13 (0.14) | +1.3 | +11.7 | 0.34 | +18.6 / +1.8 | 251 / 559 | 141 | 0.00 |
| tr-sole-25 | RH | 0.01 / 0.83 / 0.00 / **0.16** | 0.01 (0.01) | +1.9 | +15.9 | 0.95 | +20.9 / +1.8 | 271 / 519 | 108 | 0.00 |
| tr-sole-50 | LH | 0.17 / 0.46 / 0.01 / **0.34** | 0.17 (0.34) | +3.3 | +20.6 | 0.17 | +34.7 / +0.4 | 674 / 1313 | 249 | 0.00 |
| tr-sole-50 | RH | 0.02 / 0.33 / 0.02 / **0.63** | 0.02 (0.19) | +19.4 | +34.2 | 0.47 | +37.5 / +4.6 | 658 / 1291 | 355 | 0.00 |

- At 25 the paw is flat on both legs (U 0.07 / 0.16), but at 0.59 m/s, as
  hw-sole-25 was at 0.49. Every slow v03 policy has stood flat.
- At 50, at 2.40 m/s, the fold is back: U 0.34 / 0.63, against ps-sole-50's
  0.86 / 0.78 on the old clip. The trailing paw took some of the fold off,
  not most of it. The RH's paw is +19° toes-up of the floor in stance,
  with the pin at +34°.
- The pin's p95 rate stays under 900 °/s with no flapping (O9).

### Gait and spine at 50

- **Pair lag (`p2_lag.py`):** fore 0.209 of the stride (together on 0.05),
  hind 0.278 (together on 0.23); flight 0.135 s, every stride; **rotary on
  0/10 seeds** (18 rotary of 18 ordered strides, 57 tied, 123 unordered).
- **Spine (`spine_foot.py`):** 25.3° a stride (both joints), 0.00 of
  frames at a stop, cable gap at most 0.48°.
- **Drives (O6):** the worst RMS over rated is 1.61 on `j_hip_r`; the peak
  margin is 0.
- **Loops (O9):** the largest push-rod gap is 3.2 mm (`j_frodbot_r`, front),
  over the 2 mm bound: the Q2 item the critic deferred.

## The decision: not kept

**Keep rule** (`hw-sole-50.md`): U under 0.2 on both legs, and heel share
over ps-sole-25's 0.03 / 0.17 at a speed within ps-sole's spread at the
same checkpoint.

- At 25: U passes (0.07 / 0.16). The heel fails on RH (0.01 < 0.17), and
  the speed (0.59) is under ps-sole-25's spread (0.79–1.10).
- At 50: U fails (0.34 / 0.63). The heel is ps-sole-50's (0.34 / 0.19) at a
  speed just under its spread (2.40 against 2.50–2.66).

So the clip's swing was not what taught the fold: with the swing pin
under 8.4°, the policy still folds the paw in stance once it runs.

## Where the fold is (`fold_term.py`, O7)

Scored per step on four judged evaluations, from the settle on. Each
candidate is gated on contact the policy observes: the paw or the heel
down (`chX_down`, `khX_down`).

| evaluation | leg | U frames: paw down / heel only | U floor pitch ° q1 / med / q3 | U past `paw_flat`'s 15° | `pin30` on F / R / T / U | `pin30` charges U | `fold` on F / R / T / U | `fold` charges U |
|---|---|---|---|---|---|---|---|---|
| tr-sole-50 | LH | 422 / 2 | +18 / +25 / +35 | 0.87 | 0.000 / 0.065 / 0.501 / 0.186 | 0.50 | 0.016 / 0.005 / 0.000 / 0.733 | 1.00 |
| tr-sole-50 | RH | 669 / 86 | +23 / +35 / +44 | 0.89 | 0.000 / 0.124 / 0.156 / 0.420 | 0.77 | 0.024 / 0.011 / 0.000 / 0.959 | 0.99 |
| ps-sole-50 | LH | 841 / 54 | +29 / +40 / +48 | 0.96 | 0.000 / 0.285 / 0.586 / 0.564 | 0.88 | 0.017 / 0.015 / 0.000 / 1.108 | 1.00 |
| ps-sole-50 | RH | 775 / 5 | +31 / +43 / +52 | 0.97 | 0.000 / 0.765 / 0.853 / 0.872 | 0.99 | 0.000 / 0.011 / 0.000 / 1.191 | 1.00 |
| hw-sole-50 | LH | 455 / 0 | +15 / +21 / +30 | 0.73 | 0.000 / 0.046 / 0.013 / 0.186 | 0.48 | 0.009 / 0.009 / 0.000 / 0.596 | 1.00 |
| hw-sole-50 | RH | 728 / 564 | +16 / +29 / +42 | 0.78 | 0.000 / 0.044 / 0.466 / 0.246 | 0.42 | 0.018 / 0.013 / 0.000 / 0.816 | 0.96 |

- **The fold is a paw down, folded far.** 93% of tr-sole-50's U frames
  have the paw on the floor, and 87–97% of every fast policy's U frames are
  past 15° toes-up. There, `paw_flat` (a 15°-wide band) pays nothing and
  has no slope back to flat. Folding costs the policy only the band's
  pay, and buys speed.
- **`pin30`** (the pin past 30° toes-up of the metatarsus, the critic's
  candidate) charges only half of tr-sole-50's U frames. It charges the
  heel-up roll (R, which O2 allows) nearly as hard as U on ps-sole-50
  (0.765 against 0.872), because a folded paw and a rolling one can have
  the same pin. It is not screened.
- **`fold`** (the paw's floor pitch past 5° toes-up, `paw_flat`'s
  observed-channel estimate) charges 96–100% of U frames, 0.6–1.2 a frame.
  It charges F and R at most 0.024, and T not at all.

## fd-sole: tr-sole's task plus `paw_fold`

- **The term:** `paw_fold`, weight −10. Per hind leg, (paw or heel down) ×
  max(0, floor pitch − 5°) / 30, averaged over the two legs, where floor
  pitch is `paw_flat`'s estimate (pin toes-up less the metatarsus's
  observed pitch, + 1.9). It is gated on contact, not on the clip's
  stance, so a fold outside the clip's stance is charged too. The task
  goes to 20 terms. The weight mirrors `paw_flat`'s 10: a fold at +35°
  costs about 5 a leg-frame against `track_speed`'s 20 at full speed.
- **The run:** `~/orun14-fd.py` is `orun14-tr.py` with the term (a
  literal; leo is at the 64-parameter cap). It is queued by
  `orun13/queue_run.py --after tr-sole --build ~/orun14-fd.py`, so it
  builds and then launches cold: 50 iterations, 4096 envs, seed 0, budget
  4,800 s. The model is unchanged (leo v03), so nothing is tagged.
- **Keep rule:** U under 0.2 on both legs at 50, at a speed within
  tr-sole-50's spread (2.14–2.59 m/s), with heel share no lower than
  tr-sole-50's (0.34 / 0.19).

## Stopped

The owner stopped orun14 at 7.6 h, before fd-sole finished: its trainer
was stopped about four minutes in, so `paw_fold` was never judged. The next
run (leo v04) puts a soft toes-down return spring on the paw pin instead.
