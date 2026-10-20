# orun12 P1 (O2a): what holds the right heel up, heel4-s1 at 25, and heel5-s1

Verified against source: 2026-10-19. Frozen evidence (orun12, iteration 9).

## The stance proxy was wrong

`hock_stance.py` (iteration 7) took a hind paw's lowest quarter of frames as
its stance. `stance_pose.py` (new) uses the engine's own stance instead:
the frames after 1 s where the paw's collision capsules are within
`STANCE_MM` (1 mm) of the floor, posed with `CadexEvaluation.foot_series`.
Its frame counts and heel shares equal the engine's `detail.heels` on every
evaluation read here, for example heel3-s1-100 at 1011 / 1307 frames and
0.26 / 0.02. Only 29–67% of the proxy's frames are real stance frames.

```
python3 docs/probes/orun12/stance_pose.py RUN/train/cat_model-model.xml \
    ~/cadex-projects/feline-v07/evaluations/{v07-g1-100,heel2-s1-75,heel3-s1-50,heel3-s1-75,heel3-s1-100,heel4-s1-25}
```

In the table, angles are in degrees, with the right leg folded onto the left.
Segment pitch is measured from horizontal; the pelvis is positive nose-down.

| evaluation | leg | heel down | heel mm | hip / knee / hock | pelvis / thigh / shin / metatarsus / paw pitch |
|---|---|---|---|---|---|
| v07-g1-100 | LH | 0.00 | 31 | −5 / −19 / −15 | −25 / 35 / 122 / 39 / 36 |
| v07-g1-100 | RH | 0.00 | 75 | 5 / −45 / −9 | −26 / 41 / 154 / 80 / 39 |
| heel2-s1-75 | LH | 0.00 | 35 | −3 / −20 / −15 | −19 / 41 / 129 / 43 / 36 |
| heel2-s1-75 | RH | 0.00 | 82 | 0 / −40 / 1 | −19 / 43 / 146 / 88 / 39 |
| heel3-s1-50 | LH | 0.16 | 12 | 22 / −7 / −50 | −13 / 72 / 138 / 26 / −2 |
| heel3-s1-50 | RH | 0.07 | 26 | 27 / −22 / −54 | −21 / 68 / 151 / 38 / −4 |
| heel3-s1-75 | LH | 0.25 | 8 | 22 / −11 / −54 | −20 / 66 / 135 / 18 / 34 |
| heel3-s1-75 | RH | 0.09 | 29 | 26 / −28 / −55 | −26 / 62 / 152 / 37 / 10 |
| heel3-s1-100 | LH | 0.26 | 5 | 21 / −12 / −55 | −21 / 63 / 135 / 14 / 33 |
| heel3-s1-100 | RH | 0.02 | 35 | 26 / −35 / −53 | −29 / 60 / 156 / 43 / 37 |
| clip, heel down | both | 1 | 0 | −16 / 7 / −21 | −1 / 46 / 102 / 20 / −51 |

- **The right heel puzzle at heel3-s1-100.** In real stance the right hock
  is at −53°, beside the left's −55°. Both are 32° *past* the clip's −21°
  and 5–7° from the hock's −60° stop. So the hock is not short of the clip's
  angle, as iteration 7 read from the proxy; it is over-flexed.
- **The knee holds the heel up.** The right knee folds 23° more than the
  left (−35° against −12°). That leans the right shin 21° further back (156°
  against 135°) and leaves the metatarsus at 43° against 14°. The same
  pattern holds on every policy judged: the right knee folds 15–26° more
  than the left. That is the handedness `mirror-policy.md` found
  policy-learned.
- **The pelvis is nose-up** by 13–29° in hind stance, against the clip's
  −1°.

## What lays the heel: the metatarsus's world pitch

Both legs' stance frames on heel3-s1-75 and 100, binned by metatarsus pitch:

| pitch deg | 5–10 | 10–15 | 15–20 | 20–45 | ≥ 45 |
|---|---|---|---|---|---|
| heel down (heel3-s1-100) | 0.72 | 0.28 | 0.00 | 0.00 | 0.00 |
| heel down (heel4-s1-25) | 0.78 | 0.55 | 0.47 | 0.13–0.16 | 0.00 |

The bar moves with the paw's angle on its sprung pin: flat on heel3-s1-100
(33–37°), toes-up on heel4-s1-25's left paw (−14°). Either way, the heel
comes down only at a low metatarsus pitch, and never above 30°.

**The clip cannot lay the heel when tracked.** On its four heel-down
samples, the clip's metatarsus sits at 18–22°, and its paw pin at −1…−20°.
The paw stands on its rear pad, with the toes about 85° off the sim's flat
paw. In the sim the sprung paw lies flat in stance (pin about +77°). So the
clip's heel-down pose is not the sim's. On heel3-s1-100, frames at the
clip's 20° never have the heel down.

**The pitch is exact from observed channels.** A least-squares fit over
heel3-s1-100's frames gives coefficients of ±1.00 (±0.02) and a 0.3–0.4°
RMS residual:

```
pitch_l = chest + q_spine + q_hip_l - q_knee_l + q_hock_l + 63.9
pitch_r = chest + q_spine - q_hip_r + q_knee_r - q_hock_r + 63.9
chest   = 57.2958 * asin(2 * (imu_qw * imu_qy - imu_qx * imu_qz))     (nose-down)
```

The hock carries into the pitch 1:1, as the parallelogram should. Written
in `stance_pose.py`'s `metatarsus_pitch`, the closed form's mean error
against the geometric pitch is under 1.4°. Its largest error is 2.8° on
heel3-s1-100 and 7.5° on heel4-s1-25. Hip abduction and roll are left out.

## heel4-s1 at 25

heel4-s1 (`5bcadba8`, which is heel3-s1 plus `track_ankle`) was judged at
iteration 25 on the bundle's `gallop_spec`, seeds 1001–1010, on the CPU
(`judge.py` as in `heel3-final.md`):

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | stance hock LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | stride mm LH / RH | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| heel3-s1-25 | 0/10 | 0.07 / 0.07 | 0.00 / 0.03 | 41 / 50 | −21 / −20 | 1.41 / 1.55 / 1.71 | 3.67 / 3.67 | 537 / 547 | 1.54 (j_spine) | 0.00 | 3.4 |
| heel4-s1-25 | 0/10 | 0.07 / 0.01 | 0.00 / 0.00 | 34 / 64 | −16 / −13 | 1.22 / 1.52 / 1.64 | 4.44 / 5.33 | 388 / 384 | 1.57 (j_spine) | 0.00 | 2.7 |

Other predicates at heel4-s1-25: completes 9/10, every_stride 9/10, no_tap
0/10 (median 2.01), and overreach 0/10 (median −329 mm). No seed fell.

`track_ankle` did what it pays for: on the proxy, the stance hock gap fell
from +24/+30° to +12/+16°. But the heel did not come down: 0.07 / 0.01
against heel3-s1's 0.07 / 0.07, with the right heel 14 mm higher. The real
stance hock moved *away* from heel-down, to −16 / −13°. The term points the
hock at the clip's angle, and that angle cannot lay the heel.

## heel4-s1 at 50: stopped, a dead end

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | stance hock LH / RH | metatarsus pitch LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | stride mm LH / RH | overreach mm LH / RH | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel3-s1-50 | 0/10 | 0.17 / 0.07 | 0.00 / 0.00 | 12 / 25 | −50 / −54 | 26 / 38 | 2.92 / 3.02 / 3.10 | 2.50 / 2.78 | 1195 / 1188 | 283 / 221 | 2.15 (j_spine) | 0.00 | 3.6 |
| heel4-s1-50 | 0/10 | 0.14 / 0.07 | 0.15 / 0.06 | 28 / 40 | −29 / −29 | 39 / 49 | 2.83 / 3.21 / 3.33 | 4.28 / 5.17 | 676 / 663 | −278 / −277 | 1.66 (j_tail1) | 0.00 | 3.4 |

Other predicates at heel4-s1-50: overreach 0/10, no_tap 1/10 (median
1.19), every_stride 9/10, completes 9/10, and no fall. Every stride has
flight (0.10 s).

Both heels are under 0.15, so heel4-s1 was stopped at 50 by the stop rule
(`loop.request_stop`, 3,752 s). The heels are no better than heel3-s1's,
they sit higher (28 / 40 mm against 12 / 25), and the gait is worse:

- the hind paws land behind the fore prints;
- the touchdown rate is 1.7–1.9× heel3-s1's;
- the strides are half as long.

`track_ankle` is cut (O5). heel3-s1's 50 is the better base. At 50 its
metatarsus is 13 / 11° lower than heel4's, because its hock is free to
over-flex.

## heel5-s1: pay the metatarsus pitch, not the clip's angle

The heel5 build is heel3-s1's task (`ac32d3b0`) with one change.
`track_ankle` is cut, and the plantigrade group gets one new term:

```
heel_pitch = (ref_lh_down * sat01((45 - pitch_l) / 35)
            + ref_rh_down * sat01((45 - pitch_r) / 35)) / 2          weight 10
```

- The term pays in the clip's hind stance. It is full at 10° or less and
  nothing at 45°. It is a literal, as the script is at the 64-parameter
  cap.
- It is posture-agnostic. The policy may lower the metatarsus with the knee,
  the hip, the pelvis or the hock, and only the knee and the pelvis have
  room.
- Evaluated per step on the paw's real stance frames (the traces carry no
  clip phase), it pays heel3-s1-100 0.66 / 0.27 of full, v07-g1-100 0.19 /
  0.00, and heel4-s1-25 0.22 / 0.09. So it has most of its weight to give,
  most of all on the right leg.
- Everything else is heel3-s1's: `plant_w` 10, speed pay capped at 2 m/s,
  the chest box, 18 terms.

heel5 is feline-v07 revision `44411418`, digest `e4327e17`. It kept
revision 13's model with no new tessellation bytes. Its retained gallop
task has 18 terms, `heel_pitch` among them and `track_ankle` gone, and the
trainer's expression table carries `asin`.

heel5-s1 is cold, 100 iterations, 4096 envs, seed 0, with `budget_s` 9,000
(heel3-s1 took 7,072 s for the same shape). It was queued with
`queue_run.py --expect-revision 44411418 --envs 4096` and launched at
23:56:49, as soon as heel4-s1 stopped. The first-ten-iterations timing (O8)
and its checkpoints are still to come.

If heel5-s1 moves the right heel share while the left holds heel3-s1's, the
term stays (O5). The stop rule at 50 is the same: under 0.15 on both heels.
