# orun19 X1a: x1a-cold judged at 50 and 150 — the ceiling at 6.5 m/s does not raise the top

Verified against source: 2026-10-23. Frozen evidence (orun19, iteration 20).
Charter X1's first screen, `x1a-cold` (`x1a-cold.md`: s2a-hold's task with
the command ceiling 5000 → 6500 mm/s and nothing else, cold, seed 0, 4096
envs, 150 iterations), judged at its midpoint and end at S's commands plus
5.5, 6.0 and 6.5 m/s, beside X1's starting top, `s2a-hold-150` (`efe7f96b`,
4.57 m/s held at 4.63, Fr 5.38; `s2a-hold-150-top.md`).

```
R=~/cadex-projects/leo/runs/x1a-cold/train; E=~/cadex-projects/leo/evaluations
cp $R/speed.000050.cxpolicy ~/orun19-queue/x1a-cold-50.cxpolicy                     # 564e85bc
cp $R/speed.000150.cxpolicy ~/orun19-queue/x1a-cold-150.cxpolicy                    # 3eb2927f = speed.cxpolicy
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
    ~/cadex-projects/leo $R ~/orun19-queue/x1a-cold-50.cxpolicy x1a-cold-50 \
    --cmd 700 1500 2400 3500 4630 5500 6000 6500
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
    ~/cadex-projects/leo $R ~/orun19-queue/x1a-cold-150.cxpolicy x1a-cold-150 \
    --cmd 700 1500 2400 3500 4230 4630 5000 5500 6000 6500
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py $E/x1a-cold-150-<cmd> ...
python3 docs/probes/orun19/s1_tables.py $E/x1a-cold-150-<cmd> ...
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun19/o3_reread.py $E x1a-cold-50 x1a-cold-150
```

## The checkpoints

- **50:** `speed.000050.cxpolicy`, **`564e85bc`**. Reward per step 4.79 at
  25, 9.15 at 50 (s2a-hold 10.33 at 50), σ 0.66. Judged on the CPU beside
  the live trainer, 4 min 54 s for 80 seeds.
- **150:** `speed.000150.cxpolicy` = the final `speed.cxpolicy`,
  **`3eb2927f`** (the evaluations' `policy_sha256`; the status file's
  receipt, witness error 1.5e-7), trained task `1e513e8b`, model `f9b8ab82`
  (leo v06, unchanged). 150/150 iterations, 3,117 s of trainer wall, inside
  the 3,600 s budget. Reward per step 13.67 at 100, 15.58 at 125, 16.56 at
  150 (best 16.97 at 143), σ 0.52. Its reward is not comparable with
  s2a-hold's 18.92: the command distribution differs. Judged on the CPU,
  6 min 4 s for 100 seeds.

## Speed, and O3

**0 falls on 180 seeds** (C2_SEEDS 1001–1010 per command; upright 80/80 at
50 and 100/100 at 150).

| command m/s | 0.7 | 1.5 | 2.4 | 3.5 | 4.23 | 4.63 | 5.0 | 5.5 | 6.0 | 6.5 |
|---|---|---|---|---|---|---|---|---|---|---|
| x1a-cold-50, last 2 s m/s, median (min / max) | 1.97 (1.83 / 2.11) | 1.99 (1.81 / 2.08) | 2.12 (1.07 / 2.21) | 1.66 (1.10 / 2.32) | – | 2.17 (1.07 / 2.34) | – | 2.19 (1.09 / 2.42) | 1.66 (0.99 / 2.30) | 2.31 (1.04 / 2.45) |
| **x1a-cold-150**, median (min / max) | **1.03** (1.01 / 1.09) | **1.93** (1.89 / 1.95) | **3.07** (2.96 / 3.14) | **3.96** (3.84 / 4.03) | **4.12** (4.07 / 4.13) | **4.11** (1.40 / 4.18) | **4.15** (4.09 / 4.20) | **4.14** (4.08 / 4.20) | **4.10** (4.07 / 4.17) | **4.03** (4.01 / 4.07) |
| x1a-cold-150 seeds ≥ 0.9 × command | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 2/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| x1a-cold-150 tracks (O3) | yes | yes | yes | yes | **yes** | no | no | no | no | no |
| **s2a-hold-150**, median | 0.86 | 1.80 | 2.95 | 4.08 | 4.55 | **4.57** | 4.53 | – | – | – |
| s2a-hold-150 tracks | yes | yes | yes | yes | yes | **yes** | no | – | – | – |
| v05 b1-s2-180, median | 1.84 | 2.59 | 1.85 | 1.80 | – | – | 1.62 | – | – | – |

(v05's row from `../orun18/b1-s2-180.md`.)

Per seed at 150, last 2 s m/s:

| command | seeds 1001–1010 |
|---|---|
| 700 | 1.04 1.06 1.03 1.03 1.08 1.01 1.04 1.01 1.09 1.01 |
| 1500 | 1.94 1.89 1.93 1.91 1.91 1.94 1.93 1.93 1.94 1.95 |
| 2400 | 2.96 3.06 3.07 3.10 3.07 3.06 3.11 3.07 3.14 3.12 |
| 3500 | 3.99 3.84 3.92 3.90 3.95 3.98 3.97 3.97 3.86 4.03 |
| 4230 | 4.12 4.13 4.12 4.08 4.07 4.09 4.12 4.11 4.12 4.11 |
| 4630 | 4.18 1.40 4.16 4.11 4.18 4.08 4.14 4.10 4.12 4.11 |
| 5000 | 4.13 4.15 4.09 4.13 4.16 4.14 4.20 4.15 4.20 4.14 |
| 5500 | 4.16 4.13 4.08 4.13 4.16 4.20 4.19 4.09 4.15 4.10 |
| 6000 | 4.10 4.17 4.11 4.09 4.09 4.11 4.11 4.14 4.08 4.07 |
| 6500 | 4.04 4.04 4.02 4.07 4.07 4.03 4.03 4.03 4.02 4.01 |

- **At 50 it does not track** (top 1.5 m/s commanded, by overshoot): it
  runs ~1.7–2.3 m/s whatever it is commanded, as s2a-hold-50 did
  (1.05–2.23). Raising the ceiling did not change the midpoint.
- **At 150 it tracks five commands, 0.7 to 4.23 m/s, with 0 falls; its
  top is 4.12 m/s held at 4.23 (4.07 the slowest seed), Fr 4.37** (hip
  height 0.396 m). That is **below s2a-hold-150's 4.57 m/s (Fr 5.38)**.
- **Its ceiling is ~4.1 m/s**, 0.4 m/s lower than s2a-hold-150's ~4.55: from
  4.23 to 6.5 m/s commanded it holds 4.03–4.15 m/s, and slightly less at
  6.5 than at 5.0. The fastest it holds on any judged command with 0 falls
  is 4.15 m/s at 5.0 (Fr 4.43).
- At 4.63 seed 1002 stumbled (max tilt 28.6°, not a fall) and held 1.40 m/s
  over the last 2 s, so 4.63 is not tracked even before the ceiling.
- Below the ceiling it runs over the command as s2a-hold does (+47% at 0.7,
  +13–29% at 1.5–3.5), a little more at every command than s2a-hold-150.

## Gait and O6 at 150

| command m/s | 3.5 | 4.23 | 5.0 | 6.5 |
|---|---|---|---|---|
| touchdown phase of RH / LF / RF in LH's stride | 0.60 / 0.73 / 0.60 | 0.50 / 0.23 / 0.83 | 0.55 / 0.33 / 0.83 | 0.60 / 0.71 / 0.45 |
| engine footfall stride Hz (seed median) | 3.10 | 4.55 | 4.55 | 4.55 |
| touchdown Hz LF / RF; LH / RH | 10.0 / 9.9; 7.7 / 7.6 | 9.7 / 9.4; 6.8 / 6.5 | 9.4 / 9.3; 6.4 / 6.0 | 9.4 / 9.2; 5.9 / 5.6 |
| step advance mm LF / RF; LH / RH | 224 / 450; 815 / 756 | 495 / 491; 846 / 824 | 497 / 496; 866 / 846 | 487 / 481; 844 / 844 |
| heel pad share of hind stance LH / RH | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| worst RMS / rated (drive); peak margin | 1.38 (`j_hip_r`); 0.00 | 1.49 (`j_hip_r`); 0.00 | 1.47 (`j_hip_r`); 0.00 | 1.36 (`j_elbow_l`); 0.00 |
| drives at their clamp ≥ 0.05 of frames | `j_tail2` 0.44, `j_shoulder_l` 0.07, `j_elbow_r` 0.07, `j_knee_r` 0.07 | `j_tail2` 0.44, `j_elbow_l` 0.10, `j_elbow_r` 0.09, `j_shoulder_l` 0.09, `j_knee_r` 0.07 | `j_tail2` 0.44, `j_elbow_l` 0.12, `j_elbow_r` 0.10, `j_shoulder_l` 0.07, `j_knee_r` 0.07 | `j_tail2` 0.43, `j_elbow_l` 0.12, `j_elbow_r` 0.09, `j_knee_r` 0.07, `j_shoulder_l` 0.05 |
| hind rod loop gap max mm | 1.7 | 1.8 | 1.7 | 1.7 |
| falls; non-finite seeds | 0; 0 | 0; 0 | 0; 0 | 0; 0 |

Left against right, RMS over rated (seed median, L / R):

| drive | 4.23 | 5.0 | 6.5 |
|---|---|---|---|
| scapula | 1.10 / 0.87 | 1.12 / 0.89 | 1.08 / 0.85 |
| shoulder | 1.27 / 0.96 | 1.20 / 0.96 | 1.13 / 0.90 |
| elbow | 1.32 / 1.27 | 1.37 / 1.27 | 1.36 / 1.23 |
| hip | 1.41 / 1.49 | 1.40 / 1.47 | 1.24 / 1.30 |
| knee | 0.67 / 0.96 | 0.72 / 0.96 | 0.78 / 0.96 |
| hock | 0.76 / 1.04 | 0.80 / 1.09 | 0.86 / 0.91 |
| `j_spine` / `j_spine_yaw` | 0.78 / 1.16 | 0.79 / 1.16 | 0.67 / 1.11 |

- It found a different gait from s2a-hold-150: a 4.55 Hz footfall stride
  (s2a-hold 8.33 Hz) with ~845 mm hind steps (s2a-hold ~543 mm), set at
  4.23 and kept to 6.5. The fores touch down ~9.4 times a second against
  the hinds' ~6, so the fores double-step each hind stride.
- The bound moves from the fore elbow to the **hind hips**, 1.41–1.49×
  rated on both sides above 4.2 m/s (s2a-hold-150: hips 0.96–1.29, left
  elbow 1.41–1.43). The left elbow is still 1.32–1.37×. `j_spine_yaw` is
  above rated (1.11–1.16×), which no s2a-hold command showed.
- It is a toe gait on every command: the heel pad never touches.
- The fores still lean left (scapula, shoulder); the hinds lean right at
  knee and hock. Loops within 1.8 mm; no non-finite seed.
- The engine's `flight` reading at 4.23–6.5 is 0.34–0.56 s, which cannot be
  a per-stride flight at 4.55 Hz; it is not interpreted here.

## What it says for X1

**X1a does not raise the top.** Asked for up to 6.5 m/s, the same task
learned a slower ceiling (~4.1 against ~4.55 m/s) in a longer, slower
stride, bound at the hind hips. Raising the command alone is not enough.
The bundle's `track_speed` (weight 20) is `up · (v − 0.75·(v − cmd +
|v − cmd|)) / cmd`: below the command it pays `v / cmd`, so a metre per
second more pays 20 / cmd (4.0 at 5 m/s, 3.1 at 6.5), while torque and
energy cost more the faster it runs. Past the command it pays
`1 − 0.5·(v − cmd) / cmd`, so it penalises the overshoot that O3 now counts
as a hit. Neither shape was changed by X1a. This is the first X1 screen in a
row that fails to raise the top, which stays s2a-hold-150's 4.57 m/s
(Fr 5.38).

The next screen, per the critic, changes the reward only, so it can go
warm from s2a-hold-150 on s2a-hold's 5 m/s goal: `track_speed` rewarding
speed past the command (a one-sided shape, full pay at or above the
command: drop the `0.75·(…)` term past it, or make it pay `v / cmd` on
both sides), with nothing else changed.
