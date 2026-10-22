# orun16 SG: a command-scheduled heel target, scored per step before it is built

Verified against source: 2026-10-22. Frozen evidence (orun16, iteration 11).
Follows `sg-s3-25.md`.

## Why a new lever

Two shaped terms have failed to schedule the heel. `heel_pitch` (a cubic on
the metatarsus' +6° flat) has no slope where the paws stand, and
`heel_tail` (a 90° tent, w 3) gave it one, 0.009 a degree, which 25 warm
iterations did not follow (`sg-s3-25.md`). Both pay only towards the flat,
and both are gated by the command's share of 1.0–2.4 m/s, so at the slow end
they pay nothing either way: the slow heel is free, and it drifted down
(sg-s3-25 1000: 0.21 / 0.32). On sg-s3-25's traces the metatarsus sits in
the same place at every command, heel down at +3…+6°, heel up at +23…+28°
(`heel_tail.py`): the heel follows the gait, not the command.

## The candidate: `heel_sched`

A target that is a function of the command, paid both ways, ungated, in the
clip's hind stance:

    heel_sched = (ref_lh_down * tent_l + ref_rh_down * tent_r) / 2
    tent_k     = max(0, 1 - |_META_k - T(cmd)| / W)
    T(cmd)     = 6 + D (2400 - cmd) / 1400

`D` degrees toes-down of the flat (heel up, on the toes) at 1.0 m/s, the
flat itself at 2.4, linear between; the speed goal keeps `cmd` within
1000–2400, so the gate needs no clamp. It reuses `heel_pitch`'s `_META`
(the metatarsus angle from the IMU and the joints).

## Scored on sg-s3-25 (O7)

```
E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/heel_sched.py \
    ~/cadex-projects/leo/runs/v05-s1/train/gallop-task.json $E/sg-s3-25-{1000,1700,2400}
```

Per hind paw-down frame (from 1 s on), the pay times the weight, on heel-down
and heel-up frames; the contrast is heel-up minus heel-down (positive pushes
the heel up); the slope is per degree towards `T` at the heel-up median.

| cmd | leg | heel share | `_META` down / up | D 24 W 30 w 6: T; down / up; contrast | D 30 W 30 w 6 | D 30 W 45 w 6 | D 36 W 45 w 6 |
|---|---|---|---|---|---|---|---|
| 1000 | LH | 0.20 | +2.9 / +27.7 | +30; 0.60 / 2.67; **+2.07** | +36; 0.00 / 2.36; **+2.36** | +36; 1.60 / 3.49; +1.89 | +42; 0.80 / 3.24; +2.44 |
| 1000 | RH | 0.32 | +3.8 / +23.2 | +30; 0.81 / 2.76; +1.95 | +36; 0.02 / 2.36; **+2.34** | +36; 1.74 / 3.53; +1.80 | +42; 0.94 / 3.17; +2.24 |
| 1700 | LH | 0.21 | +3.2 / +28.5 | +18; 3.07 / 2.73; −0.34 | +21; 2.47 / 2.72; +0.26 | +21; 3.64 / 3.46; −0.18 | +24; 3.24 / 3.48; +0.24 |
| 1700 | RH | 0.21 | +4.8 / +25.4 | +18; 3.36 / 3.27; −0.09 | +21; 2.76 / 3.31; +0.55 | +21; 3.84 / 4.07; +0.23 | +24; 3.44 / 4.11; +0.67 |
| 2400 | LH | 0.25 | +3.3 / +24.1 | +6; 5.43 / 2.54; **−2.89** | +6; 5.43 / 2.54; **−2.89** | +6; 5.62 / 3.20; −2.42 | +6; 5.62 / 3.20; −2.42 |
| 2400 | RH | 0.18 | +5.8 / +23.7 | +6; 5.66 / 2.45; −3.21 | +6; 5.66 / 2.45; **−3.21** | +6; 5.77 / 3.28; −2.49 | +6; 5.77 / 3.28; −2.49 |

Slope at the heel-up median: 0.200 a degree for W 30, 0.133 for W 45, at
every command (`heel_tail`: 0.009; `heel_pitch`: 0).

**Read.**
- The contrast **changes sign with the command**, the property neither
  `heel_pitch` nor `heel_tail` has: every candidate pays the heel-up frames
  more at 1.0 m/s (+1.8…+2.4) and the heel-down frames more at 2.4
  (−2.4…−3.2), and sits near zero at 1.7, between the two postures.
- **D 30, W 30, w 6 is chosen**: it pays the slow heel-down frames nothing
  (0.00 / 0.02), the strongest digitigrade push of the four at 1000, ties
  for the strongest flat push at 2400, and keeps the 0.2-a-degree slope.
  Its slow target (+36°) is 8–13° toes-down of where the heel-up frames sit
  now, inside the pin's 60° of travel.
- The contrast is per hind stance frame; per control step it is about half
  of it (two legs averaged, a hind down ~0.4 of the time), ~0.5–0.6 of a
  reward per step of ~37, against `heel_tail`'s ~0.1.
- Expression: 310 syntax nodes, 721 characters (cap 512 / 2,048).

## Written, not built

`~/orun16-queue/orun16-sg5.py` is sg-s4's script with `heel_tail`
replaced by `heel_sched` (D 30, W 30, w 6): the same term count (23). It
is built only after sg-s4 is judged at 25, so that sg-s4's outcome decides
whether sg-s5 keeps the overrun term and which checkpoint it warms from.
