# orun19 S2a: s2a-hold judged at 50; the same plateau as s1-v06-50, the held command has not yet moved speed

Verified against source: 2026-10-23. Frozen evidence (orun19, iteration 7).
Charter S2's first O3 screen, `s2a-hold` (`s1-v06-180.md` § S2a's launch:
s1-v06's task with the speed command held per episode, resample 3 s → 12 s,
nothing else changed, cold, 150 iterations), judged at its midpoint beside
`s1-v06-50` (same task, same iteration, command resampled every 3 s),
`s1-v06-180` and v05's `b1-s2-180` (`../orun18/b1-s2-180.md`).

```
R=~/cadex-projects/leo/runs/s2a-hold/train; E=~/cadex-projects/leo/evaluations
cp $R/speed.000050.cxpolicy ~/orun19-queue/s2a-hold-50.cxpolicy                     # 80f97755
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
    ~/cadex-projects/leo $R ~/orun19-queue/s2a-hold-50.cxpolicy s2a-hold-50 --cmd 700 1500 2400 3500 5000
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py $E/s2a-hold-50-{700,1500,2400,3500,5000}
python3 docs/probes/orun19/s1_tables.py $E/s2a-hold-50-{700,1500,2400,3500,5000}
```

## The checkpoint

`speed.000050.cxpolicy`, **`80f97755`** (the evaluations' `policy_sha256`),
trained task `d5b25b15` (the evaluations' `task_sha256` is the judged task,
`4ae65191`), model `f9b8ab82` (leo v06, unchanged). Reward per step 5.88 at
25, **10.33 at 50** (s1-v06: 9.96 at 50), σ 0.69, episode 479 steps. The
judge ran on the CPU beside the live trainer, 3 min 8 s for 50 seeds. The
trainer then ran ~19 s an iteration (1,456 s of wall at 61), so its 3,600 s
budget covers the 150 iterations (~3,150 s).

## Speed, and O3

**0 falls on 50 seeds** (C2_SEEDS 1001–1010 per command, upright 50/50).

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| **s2a-hold-50, last 2 s m/s, median (min / max)** | **1.80** (1.69 / 2.00) | **1.95** (1.67 / 2.15) | **1.63** (0.92 / 2.27) | **2.23** (0.96 / 2.47) | **1.05** (0.76 / 1.96) |
| seeds within 10% of the command (O3) | 0/10 | 0/10 | 1/10 | 0/10 | 0/10 |
| mean forward m/s over the episode, median | 1.77 | 1.96 | 1.97 | 2.21 | 1.61 |
| max tilt °, median | 18.7 | 16.1 | 20.6 | 12.1 | 27.8 |
| seeds with max heading > 10° | 0 | 1 | 5 | 4 | 9 |
| duty factor max, median; cost of transport, median | 0.35; 1.65 | 0.36; 1.57 | 0.36; 1.61 | 0.37; 1.40 | 0.38; 2.09 |
| s1-v06-50, last 2 s m/s, median | 1.62 | 1.70 | 1.76 | 1.82 | 1.04 |
| s1-v06-180, last 2 s m/s, median | 0.75 | 2.17 | 3.07 | 3.77 | 4.24 |
| **v05 b1-s2-180, last 2 s m/s, median** | 1.84 | 2.59 | 1.85 | 1.80 | 1.62 |

Per seed, last 2 s m/s:

| command | seeds 1001–1010 |
|---|---|
| 700 | 1.86 1.80 1.71 1.89 1.69 2.00 1.83 1.72 1.80 1.73 |
| 1500 | 1.93 2.07 1.97 1.91 2.15 1.94 2.11 1.97 1.67 1.87 |
| 2400 | 0.93 1.01 2.12 1.07 1.99 2.13 2.27 2.10 1.27 0.92 |
| 3500 | 2.47 2.31 2.20 0.97 1.94 0.96 2.26 1.07 2.30 2.26 |
| 5000 | 1.03 1.10 1.09 0.76 1.07 0.94 0.86 1.96 1.06 0.79 |

- **It does not track (O3)**: one seed in 50 within 10% (2400, seed 1007,
  2.27 m/s). It runs **~1.7–2.3 m/s whatever it is commanded**, as
  `s1-v06-50` ran 1.6–1.8: the held command lifted the plateau by ~0.2–0.4
  m/s at 700–3500 but did not make speed follow the command.
- **Above ~2 m/s it veers and slows**, as at `s1-v06-50`: the seeds at
  ~0.8–1.3 m/s are the ones that turned (max heading 14–35°, final heading
  −10 to −34°, always to the right); those that held a 4–6° line ran
  1.9–2.5 m/s.
- So at 50 iterations **the screen reads no better than its parent at the
  same point**, and the parent only separated its speeds between 50 and 180.
  S2a's verdict on the held command is its end judgement at 150, beside
  `s1-v06-180`; this midpoint does not decide it.

## Footfall, flight, the heel pad

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| touchdown phase of RH / LF / RF in LH's stride (pooled median, t ≥ 4 s) | 0.27 / 0.47 / 0.58 | 0.30 / 0.42 / 0.50 | 0.30 / 0.27 / 0.50 | 0.29 / 0.36 / 0.33 | 0.35 / 0.37 / 0.47 |
| engine footfall stride Hz (seed median) | 3.71 | 3.64 | 3.85 | 3.85 | 3.85 |
| touchdown Hz LF / RF; LH / RH | 9.2 / 6.9; 6.3 / 9.4 | 9.3 / 6.6; 6.3 / 8.2 | 8.8 / 6.9; 6.3 / 6.8 | 8.8 / 6.8; 6.2 / 6.4 | 7.7 / 6.8; 5.3 / 5.1 |
| step advance mm LF / RF; LH / RH | 298 / 323; 373 / 296 | 319 / 370; 401 / 326 | 275 / 355; 378 / 346 | 368 / 405; 437 / 405 | 176 / 248; 342 / 341 |
| flight share; flight s | 1.00; 0.060 | 1.00; 0.090 | 0.95; 0.080 | 1.00; 0.090 | 0.95; 0.050 |
| **heel pad share of hind stance LH / RH** | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| heel pad stance height mm LH / RH | 137 / 136 | 138 / 136 | 137 / 136 | 137 / 137 | 120 / 120 |

- **One gait at every command**: a 3.6–3.9 Hz bound-like stride with a short
  flight (50–90 ms) on nearly every stride, the hinds 0.27–0.35 apart, even
  at 700 (s1-v06-180 walks there). No walk has been learned yet.
- **The fores are uneven**: the left fore touches down 8.8–9.3 Hz against
  the right's 6.6–6.9 at 700–3500 (a double tap on the left), and the right
  hind outpaces the left at 700–1500 (9.4 / 6.3 Hz).
- **The heel pad never touches**, at any command (rides 120–138 mm up).

## O6: torque, left against right, a clean simulation

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| worst RMS / rated (drive); peak margin | 1.73 (`j_spine`); 0.00 | 1.59 (`j_spine`); 0.00 | 1.57 (`j_spine`); 0.00 | 1.36 (`j_spine`); 0.00 | 1.54 (`j_shoulder_l`); 0.00 |
| drives at their clamp ≥ 0.05 of frames (seed median) | `j_spine` 0.18, `j_tail2` 0.17, `j_knee_r` 0.11, `j_shoulder_l` 0.08, `j_elbow_l` 0.06 | `j_tail2` 0.20, `j_spine` 0.13, `j_knee_r` 0.10, `j_shoulder_l` 0.09, `j_elbow_l` 0.08 | `j_tail2` 0.22, `j_shoulder_l` 0.14, `j_knee_r` 0.08, `j_elbow_l` 0.08, `j_shoulder_r` 0.07, `j_spine` 0.06, `j_elbow_r` 0.06 | `j_tail2` 0.21, `j_shoulder_l` 0.11, `j_knee_r` 0.09, `j_elbow_l` 0.07 | `j_tail2` 0.20, `j_shoulder_r` 0.17, `j_shoulder_l` 0.17, `j_elbow_r` 0.08, `j_elbow_l` 0.06 |
| hind rod loop gap max mm; tail cable gap max ° (`coupling/cable_tail4`) | 1.6; 5.1 | 1.6; 6.1 | 1.7; 5.5 | 1.7; 5.2 | 1.6; 5.0 |
| falls; non-finite seeds | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |

RMS over rated, seed median, left / right (`b1_summary.py`; v06 has no
wrist, and `j_tail2` has no rating):

| drive | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| fore abduction | 0.48 / 0.38 | 0.59 / 0.38 | 0.56 / 0.39 | 0.61 / 0.38 | 0.59 / 0.48 |
| scapula | 0.58 / 0.48 | 0.62 / 0.53 | 0.73 / 0.65 | 0.68 / 0.56 | 1.07 / 0.89 |
| shoulder | 1.17 / 0.88 | 1.24 / 0.92 | 1.38 / 1.02 | 1.28 / 0.96 | 1.54 / 1.46 |
| elbow | 1.20 / 1.01 | 1.24 / 1.04 | 1.27 / 1.09 | 1.23 / 1.05 | 1.22 / 1.19 |
| hind abduction | 0.57 / 0.47 | 0.59 / 0.49 | 0.62 / 0.53 | 0.63 / 0.56 | 0.61 / 0.59 |
| hip | 0.52 / 0.70 | 0.61 / 0.71 | 0.67 / 0.73 | 0.67 / 0.72 | 0.65 / 0.70 |
| knee | 0.76 / 1.30 | 0.75 / 1.23 | 0.71 / 1.11 | 0.73 / 1.11 | 0.63 / 0.83 |
| hock | 0.39 / 0.50 | 0.41 / 0.48 | 0.48 / 0.49 | 0.43 / 0.49 | 0.59 / 0.52 |
| `j_spine`, `j_spine_yaw`, `j_tail1` | 1.73, 0.43, 0.85 | 1.59, 0.49, 0.87 | 1.35, 0.63, 0.86 | 1.24, 0.62, 0.88 | 1.12, 0.88, 0.90 |

- **Torque.** Over rated at every command: the spine pitch drive 1.12–1.73×
  (at its clamp on 0.18 of frames at 700), the **left** fore shoulder
  1.17–1.54× and elbow 1.20–1.27×, the right knee 0.83–1.30×. Peak margin
  0.00 everywhere (`j_tail2`, unrated, at its clamp on 0.17–0.22 of frames).
- **Left against right.** The fores lean left (shoulder 1.2–1.4× the
  right's, abduction 1.3–1.6×), matching the left fore's extra touchdowns;
  the hinds lean right at the knee (1.3–1.7× the left's at 700–3500), as on
  s1-v06 at both judgements.
- **Clean.** No NaN; **hind rod loops within 2 mm** (1.6–1.7 mm max); tail
  cable couplings open 5.0–6.1° at most (`cable_tail4`), as on s1-v06.

## Read at 50

S2a at 50 is s1-v06 at 50 again: 0/50 falls, a single ~1.7–2.3 m/s gait at
every command, veering and slowing above ~2 m/s, toe stance, the spine and
the left fore over rated. Holding the command per episode has not yet
separated speeds. The screen runs on, cold and unchanged, to 150; its end
judgement against `s1-v06-180` (tracked at 700 6/10 and 3500 10/10; 1.45×
over at 1500, 1.28× at 2400, 0.85× at 5000) is what decides O3's first
lever.
