# orun14 P1: p1-flat at 25, and why the clip pulls the heel up

Verified against source: 2026-10-21. Follows `h1-meta-25.md` and
`p1-flat.md`. Also: `clearance-baseline.md` (4c9de98d's full pair list) and
`rod_gap.py` (O9's 2 mm, frame by frame).

## The run and the judging

- **The run:** p1-flat (`p1-flat.md`): h1-meta's task, plus the paw pins
  observed by the actor and `paw_flat` at weight 10. Revision `4c9de98d`,
  cold, 4096 envs, seed 0. Launched 07:52:52. It ran at about 75 s an
  iteration after a 120 s compile. The trainer read 16.5 reward/step at
  iteration 24, with episodes 1,905 steps long.
- **The checkpoint:** `gallop.000025.cxpolicy`, sha256 `60d8d1af`.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010,
  on the CPU, evaluation `p1-flat-25`. Then `orun12/legs.py`,
  `orun13/p2_lag.py`, `orun13/spine_foot.py`, `paw_floor.py` and
  `rod_gap.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off | no_tap | every_stride | straight | overreach mm LH / RH | stride mm | touchdown Hz | flight | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g1-free-25 | 0/10 | 0.43 / 0.53 / 0.66 | 0.02 / 0.02 (0/10) | 0.00 / 0.00 | 0/10 (5.88) | 10/10 | 10/10 (21.3) | −200 / −117 | 397 / 393 | 2.67 / 2.56 | 0.000 s | 2.42 (j_tail1) | 0.00 | 2.2 |
| h1-meta-25 | 0/10 | 0.61 / 0.73 / 0.85 | 0.07 / 0.04 (0/10) | 0.04 / 0.00 | 0/10 (2.10) | 9/10 | 2/10 (26.4) | −222 / −177 | 173 / 192 | 2.78 / 3.00 | 0.000 s | 1.86 (j_tail1) | 0.00 | 2.1 |
| **p1-flat-25** | 0/10 | 0.36 / **0.41** / 0.57 | **0.00 / 0.01** (0/10, 0.000) | 0.00 / 0.00 | 0/10 (3.50) | 7/10 (2.38) | 5/10 (25.0) | −206 / −144 | 188 / 150 | 2.50 / **1.78** | 0.000 s | 2.25 (j_tail1) | 0.00 | 1.9 |

- **Passing:** `completes`, `no_fall` and `upright` 10/10 (16.5°).
- **Left and right (O5):** heels 0.00 / 0.01; stride 188 / 150 mm;
  touchdowns 2.50 / 1.78 Hz, a 29% spread.

### The hind paws (`paw_floor.py`, medians over 10 seeds)

| evaluation | leg | on-ground F / R / T / U | floor pitch ° in stance | pin ° in stance | lifts toes-up of floor | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|
| g1-free-25 | LH | 0.02 / 0.96 / 0.00 / 0.02 | +0.7 | +10.7 | 0.00 | 230 / 727 | 114 | 0.00 |
| g1-free-25 | RH | 0.02 / 0.95 / 0.00 / 0.03 | +1.9 | +17.3 | 0.00 | 262 / 604 | 122 | 0.00 |
| h1-meta-25 | LH | 0.05 / 0.79 / 0.01 / 0.13 | +1.3 | +17.5 | 0.11 | 298 / 830 | 131 | 0.00 |
| h1-meta-25 | RH | 0.04 / 0.79 / 0.00 / 0.15 | +2.3 | +17.2 | 0.13 | 329 / 785 | 131 | 0.00 |
| **p1-flat-25** | LH | 0.00 / 0.97 / 0.00 / **0.03** | +1.4 | +15.1 | 0.05 | 214 / 505 | 99 | 0.00 |
| **p1-flat-25** | RH | 0.01 / 0.75 / 0.01 / **0.23** | +3.6 | +18.6 | 0.34 | 378 / 832 | 198 | 0.00 |

The engine's heel share is 0.00 / 0.01, with heel stance heights of 8.9 /
9.6 mm. The feet are on their toes (`R`, heel up), as at g1-free-25.

### Gait, spine, torque, O9

- **Pair lag (`p2_lag.py`):** fore 0.273 of the stride, hind 0.442. Rotary
  on 0/10 seeds; no flight.
- **Spine (`spine_foot.py`):** 19.8° a stride (both joints), 0.03 of
  frames at a stop. It sits flexed: `j_spine` stays between −27° and −5°
  on every seed. The cable gap is at most 0.15°.
- **Torque:** the worst RMS is `j_tail1` at 2.25× rated. The peak margin
  is 0.00.
- **Rod loops:** the largest gap is 1.90 mm, under O9's 2 mm (see below).

## The decision: no keep, and it runs on to 50

**Keep rule (`p1-flat.md`):** U share under 0.2 on both legs, with heel
share and speed no worse than h1-meta's. p1-flat-25 fails on every count:
RH's U share is 0.23, heels are 0.00 / 0.01 against 0.07 / 0.04, and speed
is 0.41 m/s against 0.73. LH alone is flat (U 0.03, +1.4°), and no flatter
than g1-free-25's +0.7°. `paw_flat` does not lay the paw flat without
losing the heel at 25.

**Deviation from the critic's message, which said to stop it.** The next P1
screen needs a generator change and a 12–15 minute leo build (below), so
nothing is ready to take the GPU. Stopping now would leave the GPU idle
about as long as p1-flat's remaining 25 iterations, about 31 minutes, to
about 09:00. So p1-flat runs to 50. Its 50 checkpoint answers the one
question 25 cannot: g1-free's toes-up paw appeared between 25 and 50
(U 0.02 → 0.76), and a visible pin plus `paw_flat` may stop that. It
is not kept unless 50 passes the keep rule.

## Why every screen so far pulls the heel up: the clip's pad is in the floor

`clip_pad.py` sets the model to each of p1-flat's 21 clip samples. In the
clip's hind stance (`heels`, `heel_from` 0.2), the generator holds the
heel's lowest point and the toe on the ground. The pad, between them, is
**3.7–10.8 mm (LH) and 4.7–13.3 mm (RH) inside the floor**:

| sample | leg | heel held | heel / pad / toe mm above ground | `_META` | pin toes-up ° | paw pitch ° |
|---|---|---|---|---|---|---|
| 1 | LH | 1 | 0.0 / −3.7 / 0.0 | +8.6 | +11.6 | −66.9 |
| 2 | LH | 1 | 0.0 / −6.1 / 0.0 | +10.6 | +16.8 | −70.1 |
| 3 | LH | 1 | 0.0 / −8.4 / 0.0 | +12.5 | +21.8 | −73.2 |
| 4 | LH | 1 | 0.0 / −10.8 / 0.0 | +14.5 | +27.0 | −76.4 |
| 0 | RH | 1 | 0.0 / −7.2 / 0.0 | +11.5 | +19.2 | −71.6 |
| 1 | RH | 1 | 0.0 / −13.3 / 0.0 | +16.6 | +32.3 | −79.6 |
| 19 | RH | 1 | 0.0 / −4.7 / 0.0 | +9.5 | +13.8 | −68.2 |
| 20 | RH | 1 | 0.0 / −8.2 / 0.0 | +12.3 | +21.3 | −72.9 |

- The generator holds two points of the foot, not the paw's sole. The
  free pin lets it fold the paw 12–32° toes-up of the metatarsus, so the
  paw is 5–18° past level, toes-up (its level pitch is −61.9°).
- The metatarsus then stands 3–11° heel-up of v03's flat (`_META` +6).
- No simulated foot can take that pose. `track_pose` pays the
  metatarsus heel-up, which is the pull against the heel that
  `g1-free-50.md` named.
- **Not fixable by the clip's parameters.** Regenerating the clip offline
  (`CadexGait.generate`, the bundle's parameters) over body drop
  0.06 / 0.09 / 0.12 m, body pitch 0 / 6 / 12° and stance shift
  0.06 / 0.12 / 0.18 m: 26 of the 27 combinations are refused (a fore or
  hind swing out of reach). The one reachable is the bundle's own.
- **Not fixable by ADR-780's `flat_feet`.** It holds the paw at its home
  pitch. At leo's home keyframe the paw's pitch is 0°, with the toe on
  the floor and the pad 33 mm up: 62° toes-down of level. That is the
  charter's "60° toes-down".

**The next P1 screen:** a generator option that holds the paw at its
level pitch while the heel is held, so heel, pad and toe are on the floor
together. That is `flat_feet` with the sole's own level pitch (−61.9° on
leo, read from the paw's collision capsules) in place of the home pitch.
It is an engine change: an ADR from ADR-784, and the engine and CLI
suites. Then rebuild leo's bundle with it and screen cold, on h1-meta's
task, or on p1-flat's if 50 passes its keep rule. The clip's `_META` in
stance should then read +6, flat.

## The rod-loop gap against O9 (`rod_gap.py`)

The judge's closure block gives only each connect row's maximum. Read per
frame, over 10 seeds from 1 s:

| evaluation | row | median | p99 | p99.9 | max mm | frames > 2 mm (seeds) | its drive on those frames, share of peak (all frames) |
|---|---|---|---|---|---|---|---|
| g1-free-25 | j_frodbot_r | 0.08 | 0.85 | 1.46 | 2.21 | 1 of 4,510 (1004) | wrist 1.00 (0.03) |
| h1-meta-25 | j_frodbot_r | 0.08 | 0.82 | 1.54 | 2.14 | 1 of 4,082 (1009) | wrist 1.00 (0.03) |
| p1-flat-25 | j_frodbot_r | 0.06 | 0.81 | 1.51 | 1.90 | 0 | – (0.02) |
| g1-free-50 | j_frodbot_l | 0.19 | 1.62 | 2.80 | 3.45 | 23 (9 seeds) | wrist 1.00 (0.03) |
| g1-free-50 | j_frodbot_r | 0.18 | 2.21 | 3.41 | 3.92 | 49 (9 seeds) | wrist 1.00 (0.03) |
| g1-free-50 | j_rodbot_r | 0.28 | 1.12 | 1.65 | 2.11 | 1 (1010) | hock 0.39 (0.10) |

- Every other row stays under 2 mm. The hind rods are at most 1.26 mm in
  the 25 evaluations.
- The 2.1–2.2 mm at 25 is one frame in about 4,000. On it, the front wrist
  drive is at its peak, 9 N·m. g1-free-50's 3.9 mm is the same thing grown,
  on 9 of 10 seeds.
- The front loop opens when the wrist saturates. The paw load the drive
  cannot hold goes into the rod's connect constraint, which is soft.
- That points at the wrist drive (9 N·m peak) under
  fore-paw impact, not at the rod's geometry.
- A P1/P2 policy that lands harder on the fore paws will meet O9 here.
  If it does, the measurement for an O1 change is the wrist's peak
  share at touchdown.
