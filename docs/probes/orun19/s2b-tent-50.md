# orun19 S2b: s2b-tent judged at 50; a slower plateau than s2a-hold-50, the symmetric tent has not yet moved speed with the command

Verified against source: 2026-10-23. Frozen evidence (orun19, iteration 11).
Charter S2's second O3 screen, `s2b-tent` (`s2a-hold-150.md` § S2b's launch:
s2a-hold's task with `track_speed`'s tent made symmetric, overshoot slope
−0.5 → −1 /cmd, nothing else changed, cold, 150 iterations), judged at its
midpoint beside its parent at the same point, `s2a-hold-50`
(`s2a-hold-50.md`), the parent's end `s2a-hold-150` and v05's `b1-s2-180`
(`../orun18/b1-s2-180.md`).

```
R=~/cadex-projects/leo/runs/s2b-tent/train; E=~/cadex-projects/leo/evaluations
cp $R/speed.000050.cxpolicy ~/orun19-queue/s2b-tent-50.cxpolicy                     # 43cbe2ef
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
    ~/cadex-projects/leo $R ~/orun19-queue/s2b-tent-50.cxpolicy s2b-tent-50 --cmd 700 1500 2400 3500 5000
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py $E/s2b-tent-50-{700,1500,2400,3500,5000}
python3 docs/probes/orun19/s1_tables.py $E/s2b-tent-50-{700,1500,2400,3500,5000}
```

Per-seed speeds are `b1_summary.last_window_speed` on each evaluation's
seeds; headings are the engine's `max_heading_deg` / `final_heading_deg`.

## The checkpoint

`speed.000050.cxpolicy`, **`43cbe2ef`** (the evaluations' `policy_sha256`),
trained task `c5e8223c` (the evaluations' `trained_task_sha256`; the judged
task is `04042bc3`), model `f9b8ab82` (leo v06, unchanged). Reward per step
4.65 at 25, **8.75 at 50** (s2a-hold: 5.73 and 10.20; the symmetric tent
pays less for any overshoot, so the scales are not equal), σ 0.68, episode
394 steps. The checkpoint landed 1,319 s after launch (~26 s an iteration
with the build's start); the trainer then read 2,044 s to go at 63, inside
its 3,600 s budget. The judge ran on the CPU beside the live trainer, 3 min
8 s for 50 seeds.

## Speed, and O3

**0 falls on 50 seeds** (C2_SEEDS 1001–1010 per command, upright 50/50).

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| **s2b-tent-50, last 2 s m/s, median (min / max)** | **1.27** (1.17 / 1.40) | **1.43** (1.27 / 1.72) | **1.49** (1.21 / 1.75) | **1.23** (1.16 / 1.95) | **1.16** (1.14 / 1.77) |
| seeds within 10% of the command (O3) | 0/10 | 6/10 | 0/10 | 0/10 | 0/10 |
| mean forward m/s over the episode, median | 1.25 | 1.41 | 1.55 | 1.55 | 1.40 |
| max tilt °, median | 16.2 | 14.0 | 13.6 | 26.7 | 27.3 |
| seeds with max heading > 10°; median max heading ° | 0; 4.0 | 0; 4.2 | 2; 5.2 | 6; 11.4 | 8; 11.7 |
| duty factor max, median; cost of transport, median | 0.43; 2.06 | 0.40; 1.97 | 0.40; 1.86 | 0.40; 2.07 | 0.40; 2.19 |
| s2a-hold-50, last 2 s m/s, median | 1.80 | 1.95 | 1.63 | 2.23 | 1.05 |
| s2a-hold-150, last 2 s m/s, median | 0.86 | 1.80 | 2.95 | 4.08 | 4.53 |
| **v05 b1-s2-180, last 2 s m/s, median** | 1.84 | 2.59 | 1.85 | 1.80 | 1.62 |

Per seed, last 2 s m/s:

| command | seeds 1001–1010 |
|---|---|
| 700 | 1.27 1.19 1.25 1.40 1.26 1.39 1.31 1.40 1.17 1.22 |
| 1500 | 1.48 1.72 1.49 1.66 1.27 1.41 1.45 1.37 1.39 1.31 |
| 2400 | 1.52 1.21 1.23 1.44 1.61 1.46 1.75 1.61 1.43 1.59 |
| 3500 | 1.18 1.22 1.67 1.77 1.74 1.18 1.16 1.23 1.95 1.18 |
| 5000 | 1.15 1.15 1.16 1.77 1.14 1.15 1.18 1.19 1.15 1.20 |

- **It does not track (O3)**: it runs **~1.2–1.5 m/s whatever it is
  commanded**. The six seeds within 10% at 1500 are that plateau crossing
  the command, not tracking: 700 runs 1.8× over, 2400–5000 at 0.23–0.62×.
- **The plateau is ~0.4–0.5 m/s slower than s2a-hold-50's** (1.6–2.2 m/s)
  at 700–3500. Reading the tent alone, a symmetric penalty on overshoot
  should pull the slow end down, and it has (700: 1.80 → 1.27), but at 50
  the whole plateau dropped with it; whether the fast end separates, as
  s2a-hold's did between 50 and 150, is its end judgement's question.
- **Above ~3 m/s it veers** (6/10 and 8/10 seeds past 10° at 3500 / 5000,
  final heading −10 to +4°), about as often as s2a-hold-50 (4/10 and 9/10),
  and the slow seeds there are not only the turners: at 5000 nine seeds sit
  at 1.14–1.20 m/s.

## Footfall, flight, the heel pad

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| touchdown phase of RH / LF / RF in LH's stride (pooled median, t ≥ 4 s) | 0.30 / 0.33 / 0.47 | 0.43 / 0.28 / 0.43 | 0.39 / 0.30 / 0.50 | 0.25 / 0.33 / 0.61 | 0.33 / 0.29 / 0.75 |
| engine footfall stride Hz (seed median) | 4.17 | 4.01 | 3.85 | 4.20 | 5.05 |
| touchdown Hz LF / RF; LH / RH | 8.3 / 6.6; 6.1 / 8.0 | 7.9 / 6.5; 6.8 / 7.7 | 8.3 / 6.4; 6.7 / 7.2 | 7.7 / 6.6; 5.7 / 5.9 | 7.4 / 6.7; 5.6 / 5.2 |
| step advance mm LF / RF; LH / RH | 221 / 242; 250 / 242 | 242 / 276; 281 / 272 | 266 / 296; 316 / 327 | 200 / 248; 315 / 362 | 191 / 196; 256 / 319 |
| flight share; flight s | 0.78; 0.020 | 0.87; 0.030 | 0.88; 0.040 | 0.91; 0.040 | 0.90; 0.040 |
| **heel pad share of hind stance LH / RH** | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| heel pad stance height mm LH / RH | 132 / 132 | 134 / 133 | 134 / 133 | 134 / 131 | 123 / 118 |

- **One gait at every command**, as at s2a-hold-50: a ~4 Hz stride (5.05
  at 5000) with a short flight (20–40 ms, shorter than s2a-hold-50's 50–90)
  on 0.78–0.91 of strides, and shorter steps than s2a-hold-50's at
  700–3500.
  No walk yet.
- **The left fore double-taps** (7.4–8.3 Hz against the right's 6.4–6.7),
  as on s2a-hold-50; the right hind outpaces the left at 700–1500.
- **The heel pad never touches** (rides 118–134 mm up).

## O6: torque, left against right, a clean simulation

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| worst RMS / rated (drive); peak margin | 1.55 (`j_spine`); 0.00 | 1.49 (`j_spine`); 0.00 | 1.50 (`j_spine`); 0.00 | 1.57 (`j_shoulder_l`); 0.00 | 1.59 (`j_shoulder_l`); 0.00 |
| drives at their clamp ≥ 0.05 of frames (seed median) | `j_tail2` 0.14, `j_spine` 0.14, `j_shoulder_r` 0.07, `j_elbow_l` 0.07, `j_knee_r` 0.05 | `j_tail2` 0.17, `j_spine` 0.11, `j_shoulder_r` 0.08, `j_elbow_l` 0.07, `j_shoulder_l` 0.07, `j_knee_r` 0.06 | `j_tail2` 0.18, `j_spine` 0.11, `j_shoulder_r` 0.10, `j_shoulder_l` 0.08, `j_elbow_l` 0.07, `j_knee_r` 0.06 | `j_shoulder_l` 0.19, `j_tail2` 0.18, `j_shoulder_r` 0.18, `j_elbow_l` 0.09, `j_elbow_r` 0.06, `j_spine` 0.06 | `j_shoulder_l` 0.20, `j_shoulder_r` 0.19, `j_tail2` 0.16, `j_elbow_r` 0.08, `j_elbow_l` 0.07 |
| hind rod loop gap max mm; tail cable gap max ° (`coupling/cable_tail4`) | 1.3; 4.1 | 1.3; 4.3 | 1.3; 4.8 | 1.3; 4.7 | 1.5; 4.8 |
| falls; non-finite seeds | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |

RMS over rated, seed median, left / right (`b1_summary.py`; v06 has no
wrist, and `j_tail2` has no rating):

| drive | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| fore abduction | 0.39 / 0.41 | 0.42 / 0.40 | 0.45 / 0.42 | 0.51 / 0.44 | 0.54 / 0.46 |
| scapula | 0.63 / 0.57 | 0.66 / 0.60 | 0.72 / 0.61 | 0.94 / 0.94 | 1.02 / 1.02 |
| shoulder | 1.15 / 1.11 | 1.20 / 1.14 | 1.26 / 1.18 | 1.56 / 1.51 | 1.58 / 1.58 |
| elbow | 1.20 / 0.91 | 1.25 / 0.94 | 1.25 / 0.99 | 1.33 / 1.14 | 1.28 / 1.20 |
| hind abduction | 0.47 / 0.41 | 0.50 / 0.44 | 0.53 / 0.45 | 0.55 / 0.59 | 0.55 / 0.64 |
| hip | 0.50 / 0.68 | 0.51 / 0.71 | 0.52 / 0.72 | 0.54 / 0.70 | 0.57 / 0.64 |
| knee | 0.67 / 1.09 | 0.62 / 1.11 | 0.59 / 1.11 | 0.55 / 0.91 | 0.51 / 0.81 |
| hock | 0.42 / 0.52 | 0.42 / 0.52 | 0.43 / 0.52 | 0.49 / 0.47 | 0.56 / 0.47 |
| `j_spine`, `j_spine_yaw`, `j_tail1` | 1.55, 0.37, 1.07 | 1.49, 0.39, 1.14 | 1.48, 0.42, 1.18 | 1.30, 0.92, 1.14 | 1.23, 1.02, 1.08 |

- **Torque.** Over rated at every command though it runs slower than
  s2a-hold-50: the spine pitch drive 1.23–1.55×, the fore shoulders
  1.11–1.58× (both at their clamp on ~0.2 of frames at 3500–5000), the left
  elbow 1.20–1.33×, `j_tail1` 1.07–1.18×, the right knee 0.81–1.11×. Peak
  margin 0.00 everywhere (`j_tail2`, unrated, at its clamp on 0.14–0.18).
- **Left against right.** The fore shoulders are now even (within 6%,
  s2a-hold-50: 1.2–1.4× left); the left elbow still carries 1.07–1.32× the
  right's, matching its extra touchdowns; the hinds lean right at the knee
  (1.6–1.9× the left's at 700–2400) and hip (1.1–1.4×).
- **Clean.** No NaN; **hind rod loops within 2 mm** (1.3–1.5 mm max); tail
  cable couplings open 4.1–4.8° at most (`cable_tail4`).

## Read at 50

S2b at 50 is a slower copy of s2a-hold at 50: 0/50 falls, one ~1.2–1.5 m/s
gait at every command, veering above ~3 m/s, toe stance, the spine and fore
shoulders over rated. The symmetric tent cut the slow end's overshoot by
pulling the whole plateau down, not by separating speeds, which no screen
on v06 has done by 50 (s1-v06 and s2a-hold separated between 50 and
150–180). The screen runs on, cold and unchanged, to 150; its end judgement
beside `s2a-hold-150` (0.86 / 1.80 / 2.95 / 4.08 / 4.53 m/s, +17–23% over,
tracked at 5000 only) decides lever 2. If it then tracks fewer than four
commands, the next screen is O3's third lever, one regulariser weight, alone.

## M1, ready for the GPU

The M1 bundle is built and unchanged (`m1-retarget.md` § The M1 bundle,
`~/mocap/acinoset/m1-bundle/mocap_gallop-task.json`, sha256 `c3c099af`, model
`f9b8ab82`, the same model s2b-tent trains). `queue_bundle.py` registers at
once and takes no `--after`, so it launches by hand when s2b-tent's
supervisor reports done (~17:20 by its ETA) and s2b-tent-150 is judged on
the CPU beside it:

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun18/queue_bundle.py ~/cadex-projects/leo m1-cheetah \
    ~/mocap/acinoset/m1-bundle/mocap_gallop-task.json 3600 150 \
    "orun19 M1: leo v06 on AcinoSet cheetah52/59/61 (tracking + speed + O2 regularisers), cold" \
    --base-task speed --seed 0 --envs 4096
```

The budget is s2a-hold's measured 150-iteration wall (3,118 s) + 15%, to be
re-set from M1's own first ten iterations per O5.
