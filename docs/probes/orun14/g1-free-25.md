# orun14: the v03 probes, the clip, and g1-free judged at 25

Verified against source: 2026-10-21. Frozen evidence (orun14, iteration 2).

## The probes on the free paw pin

`paw_floor.py` is new. It adapts orun13's `foot_frames.py` and `lh_roll.py`,
and orun12's `paw_pin.py`, to v03's paw pin. The hind paw has two lateral
capsules, the pad (r 17 mm) and the toe bulbs (r 9.1 mm). Its **floor
pitch** is the pad-to-toes line in world, less that line's angle when both
capsules' lowest points are level. 0 is flat, positive is toes up of the
floor. The **pin** is the paw's rotation in the metatarsus's frame, toes-up
positive, 0 at the flat stop. Letters: `F` heel and paw down; `R` heel up,
paw down and within 10° of flat (the pin's roll, or a digitigrade stance
on the pad); `T` heel up on the toe bulbs; `U` toes up of the floor; `.` off
the floor.

**Check on the welded paw (g4-peak-50, v02):**

- the heel shares equal the engine's (0.44 / 0.22);
- the first `F` frames read −2.3° / −0.6° of floor pitch, so flat reads
  flat;
- LH rolls 3 frames or more on 0.52 of its toe-offs, which is orun13's
  "half its toe-offs";
- the pin reads 0.0 throughout.

`stance_gate.py`, `p2_lag.py` and `spine_foot.py` read only the paw and heel
geoms and the engine's metrics, so they run on v03 unchanged. A copy would
add nothing.

**Limits:**

- The pin rate is a central difference over the 20 ms trace frames. It is
  a lower bound on the step-rate speed that O9 bounds at 900°/s p95.
- `spine_foot.py`'s flat and toes-up columns are the welded foot's. Use
  `paw_floor.py`'s for v03.

```
pixi run python docs/probes/orun14/paw_floor.py RUN/train/cat_model-model.xml EVALDIR [...] [--seed N FROM TO]
```

## The clip (rung 4)

Read from the bundled reference with `orun13/p2_lag.py`'s clip block and the
reference's `heels`:

- rotary gallop, 0.70 m at 2.40 Hz, so **1.68 m/s**, over a 417 ms cycle;
- duty 0.2: hind stance 5 of 21 samples, fore 4;
- **pair lag 0.150 of the cycle on both pairs, 62.5 ms**, which passes O3's
  40 ms;
- order LH LF RF RH, rotary;
- **two flights a cycle, 60 ms each**;
- **heel down on 4 of 5 hind stance samples (0.8)**, `heel_from` 0.2;
- **spine ±7° a joint (`spine_amplitude_deg` 7), 28° in all a cycle**, with
  `j_spine2` equal to `j_spine` (`b1-ready.md`);
- body drop 60 mm, pitch 6° ± 2°, stance shift 120 mm on the hinds.

The clip is slower than every judged policy so far (2.4–2.9 m/s). orun13's
policies ran past it, with longer strides than its 0.70 m. This reading does
not say whether the generator holds the 40 ms lag at a longer stride and a
higher speed. That is for the S1 step.

## g1-free at 25 (`gallop.000025.cxpolicy`, sha256 `ffd4860f`)

- **The run:** leo v03 `bc287c9c`, task `a9817c5e`, cold, 4096 envs, seed
  0, judged at its first checkpoint. The trainer read 16.98 reward/step at
  iteration 24, rising about 0.5 an iteration. g4-peak read 15.85 at the
  same point.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010,
  on the CPU, evaluation `g1-free-25`.
- **The tools:** `orun12/legs.py`, `orun13/p2_lag.py`,
  `orun13/spine_foot.py` and `paw_floor.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off LH / RH | heel mm in stance | no_tap | every_stride | overreach mm LH / RH | stride mm | touchdown Hz | flight stride share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g4-peak-25 (v02) | 0/10 | 0.81 / 0.94 / 1.16 | 0.13 / 0.14 (0/10, 0.102) | 0.10 / 0.00 | 9 / 10 | 1/10 (1.93) | 9/10 | −168 / −198 | 203 / 199 | 2.89 / 4.28 | 0.69, 0.040 | 1.88 (j_tail1) | 0.00 | 2.1 |
| g4-peak-50 (v02) | 0/10 | 2.40 / 2.43 / 2.49 | 0.44 / 0.22 (0/10, 0.218) | 0.43 / 0.21 | 2 / 14 | 0/10 (1.68) | 10/10 | 416 / 141 | 978 / 868 | 2.33 / 4.00 | 1.00, 0.160 | 1.80 (j_spine) | 0.00 | 3.8 |
| g7-hock75-50 (v02.1) | 0/10 | 2.51 / 2.60 / 2.67 | 0.46 / 0.41 (6/10, 0.406) | 0.36 / 0.67 | 2 / 3 | 0/10 (2.01) | 10/10 | 396 / 7 | 1045 / 1035 | 2.44 / 2.44 | 1.00, 0.180 | 2.07 (j_spine) | 0.00 | 4.6 |
| **g1-free-25 (v03)** | 0/10 | 0.43 / **0.53** / 0.66 | **0.02 / 0.02** (0/10, 0.0145) | 0.00 / 0.00 | 6 / 10 | 0/10 (5.88) | 10/10 | −200 / −117 | 397 / 393 | 2.67 / 2.56 | 0.06, 0.000 | 2.42 (j_tail1) | 0.00 | 2.2 |

orun12's heel5c-s1 on feline v07, the third comparison, passed P1 on 8 of
10 seeds with heels 0.60 / 0.61, at 2.91 m/s. It was judged at its end.

**Readings:**

- `completes`, `no_fall`, `upright`, `straight` (21.3°) and `every_stride`
  pass 10/10.
- **Failing medians:** `top_speed` 0.53 m/s, `hock_down` 0.0145,
  `hock_at_toeoff` 0.00, `no_tap` 5.88 and `overreach` −201 mm. These come
  from the engine's own `summary`.

### The hind paws (`paw_floor.py`, medians over 10 seeds)

| leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | toe-offs | taps | pin ° / floor ° at lift | lifts toes-up of floor | pin rate p95 / max °/s | swing p95 °/s | swing > 900 | flapping swings |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LH | 0.02 / 0.96 / 0.00 / 0.02 | 0.02 (0.02) | +0.7 | +10.7 | 24 | 0.81 | +12.9 / +0.3 | 0.00 | 230 / 727 | 114 | 0.000 | 0.00 |
| RH | 0.02 / 0.95 / 0.00 / 0.03 | 0.02 (0.02) | +1.9 | +17.3 | 24 | 0.81 | +21.1 / +1.4 | 0.00 | 262 / 604 | 122 | 0.000 | 0.00 |

Seed 1001, 1.0–2.0 s, one letter a 20 ms frame:

    LH  RRRRRR.......URRRRRR.....UFRRRRRRRRRRRRRRRRRR.RRRRR
    RH  RRRRRRRRRRRRRRRRR....URRRR.FRRRRRRRRRRRRRRFRRRRRRRR

- **The free paw lies flat with the heel up.**
  - 0.95–0.96 of on-ground frames are `R`: the paw flat on the floor
    (+0.7° / +1.9°), the pin turned 11° / 17° toes-up of the metatarsus,
    and the heel 6 / 10 mm up.
  - No stance is on the toe bulbs (`T` 0.00), and no paw is toes-up of the
    floor (`U` 0.02–0.03, single frames at landing).
  - That is O2a's slow digitigrade posture, on flat pads. It is not the
    plantigrade stance P1 asks for.
- **The heel almost never comes down:** 0.02 of stance on both legs,
  against g4-peak-25's 0.13 / 0.14 at the same iteration.
  - On the welded paw, keeping the heel up meant standing on the toes.
  - On the pin, the paw lies flat whatever the heel does, so a heel-up
    stance is easy to hold.
  - heel_pitch's narrow peak (0.7 within ~3° of the flat metatarsus)
    pays only its tail at 11–17°. That would explain it, but no screen has
    tested it yet.
- **The pin is quiet:**
  - 230 / 262°/s p95 at the frame rate;
  - in swing, 114 / 122°/s p95, with no frame over 900°/s and no flapping
    swing.
  - At 25 it is clean at the frame rate (O9). The step-rate check waits
    for a passing policy.
- **Left and right agree.** Heel share 0.02 / 0.02, stride 397 / 393 mm,
  touchdown 2.67 / 2.56 Hz (4%). Mirror tests are not needed yet (O5).

### Gait, spine, torque

- **No gallop yet.**
  - 0.53 m/s on 0.40 m strides.
  - Flight on 0.06 of strides, 0 s at the median.
  - The fore paws tap: fore rate 5.48 against the hind stride, and
    `no_tap` 5.88 (bar 1.10).
- **Pair lag (`p2_lag.py`):**
  - folded medians: fore 0.276 and hind 0.114 of the stride;
  - at the 2.25 Hz stride (444 ms), about **123 ms fore and 51 ms hind**;
  - 0/10 seeds rotary (10 rotary strides of 17 ordered; 151 unordered).
- **Spine (`spine_foot.py`):**
  - 26.9° a stride (sum of both joints);
  - 0.15 of frames within 1° of a stop;
  - cable gap at most 0.14° (O9: 1°).
- **Torque (O6):**
  - The worst RMS drive is `j_tail1`, 2.37–2.48× rated on every seed.
  - Peak margin is 0.00: a fore drive (`j_elbow_l`, `j_scap_l` or
    `j_wrist_l`) touches its clamp on 0.2–5% of frames.
  - Both hocks touch theirs on 2–7% of frames.
- **Rod loops:** worst gap 2.2 mm (`j_frodbot_r`), against O9's 2 mm. The
  tail cable couplings open by up to 3.6°.

## Verdict at 25, and what runs next

g1-free at 25 has not formed a gallop. It runs **behind g4-peak at the same
iteration**: 0.53 against 0.94 m/s, heels 0.02 against 0.13. g4-peak went
from 0.94 to 2.43 m/s between 25 and 50. The curve still climbs. It is
**not stopped**, and runs on to 50 (about 06:45).

**No warm start from orun13's policies.** `training/cadex_train.py` refuses
a warm start whose model differs except on the course
(`check_curriculum_change`: "A warm start may move the robot onto another
course, never change the robot"). The v02-to-v03 paw pin is a change of
robot, so a warm start from g4-peak-50 cannot run without a trainer change.
The charter assumed it could. Every v03 screen starts cold, or warm from a
v03 policy.

**Queued behind it: g1x-free.**

- g1-free's final policy, warm, on the same bundle (`bc287c9c`), critic
  warmup 5, default learning rate, 50 more iterations, 4096 envs.
- `budget_s` 5,600: 55 iterations at 85 s/it, plus 20%.
- Queued through `orun13/queue_run.py` with `--expect-revision bc287c9c`,
  in its own `systemd-run --user --scope -p MemoryMax=30G`.
- **The question it asks:** does the free-pin gallop form, and does the
  heel come down, by iteration 100?
- **Its stop rule:** if g1-free at 50 does not climb, the next iteration
  stops g1x-free before it spends its budget. "Not climbing" means a top
  speed under 1.5 m/s, or heels still under 0.10.
