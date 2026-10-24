# orun19 X1b: x1b-warm judged at 50 and 150 — a new top, 5.72 m/s tracked at 6.0

Verified against source: 2026-10-24. Frozen evidence (orun19, iteration 22).
Charter X1's second screen, `x1b-warm` (`x1b-warm.md`: s2a-hold's task with
`track_speed` paying in full at and above the command, 0.75 → 0.5, and the
judged range to 6.5 m/s; warm from s2a-hold-150 `efe7f96b`, seed 0, 4096
envs, 150 iterations), judged at its midpoint and end at S's commands plus
4.23, 4.63, 5.5, 6.0 and 6.5 m/s, beside X1's previous top, `s2a-hold-150`
(4.57 m/s held at 4.63, Fr 5.38; `s2a-hold-150-top.md`) and X1a
(`x1a-cold-150.md`).

```
R=~/cadex-projects/leo/runs/x1b-warm/train; E=~/cadex-projects/leo/evaluations
cp $R/speed.000050.cxpolicy ~/orun19-queue/x1b-warm-50.cxpolicy                     # 6debc30e
cp $R/speed.000150.cxpolicy ~/orun19-queue/x1b-warm-150.cxpolicy                    # 10f197e1 = speed.cxpolicy
for N in 50 150; do
  CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
      ~/cadex-projects/leo $R ~/orun19-queue/x1b-warm-$N.cxpolicy x1b-warm-$N \
      --cmd 700 1500 2400 3500 4230 4630 5000 5500 6000 6500
done
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun19/o3_reread.py $E x1b-warm-50 x1b-warm-150 s2a-hold-150
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py $E/x1b-warm-150-<cmd> ...
python3 docs/probes/orun19/s1_tables.py $E/x1b-warm-150-<cmd> ...
```

Froude numbers use v06's hip height, 0.396 m (`froude.py`, as in
`s2a-hold-150-top.md`).

## The checkpoints

- **50:** `speed.000050.cxpolicy`, **`6debc30e`**. Judged on the CPU beside
  the live trainer, 6 min 14 s for 100 seeds.
- **150:** `speed.000150.cxpolicy` = the final `speed.cxpolicy`,
  **`10f197e1`**; trained task `f070a89b`, model `f9b8ab82` (leo v06,
  unchanged). 150/150 iterations in 3,014 s of trainer wall, inside the
  3,600 s budget; witness agrees to 1.4e-7. Judged on the CPU with the GPU
  idle, 6 min 4 s for 100 seeds.
- **Curve** (reward per step at each checkpoint's first iteration, which
  sits low after the checkpoint rollout's reset; σ): 9.18 at 0 (0.510),
  9.76 at 25, 10.97 at 50 (0.526), 11.52 at 75, 12.06 at 100 (0.481), 12.60
  at 125 (0.448). Between checkpoints it rose from ~19.2 (iterations 10–24)
  to 22.75 at 146, the best, still climbing; σ 0.419 at 149.

## Speed, and O3

**0 falls on 200 seeds** (C2_SEEDS 1001–1010 per command; upright 100/100
at 50 and 100/100 at 150).

| command m/s | 0.7 | 1.5 | 2.4 | 3.5 | 4.23 | 4.63 | 5.0 | 5.5 | 6.0 | 6.5 |
|---|---|---|---|---|---|---|---|---|---|---|
| x1b-warm-50, last 2 s m/s, median (min / max) | 2.97 (2.94 / 2.98) | 3.51 (3.47 / 3.57) | 4.05 (4.02 / 4.13) | 4.71 (4.61 / 4.74) | 4.83 (4.81 / 4.84) | 4.84 (4.81 / 4.85) | 4.84 (4.83 / 4.86) | 4.83 (4.82 / 4.83) | 4.72 (4.72 / 4.74) | 4.52 (4.50 / 4.54) |
| x1b-warm-50 tracks (O3) | yes | yes | yes | yes | yes | yes | **yes** | no | no | no |
| **x1b-warm-150**, median (min / max) | **2.01** (2.01 / 2.02) | **2.38** (2.38 / 2.41) | **2.95** (2.93 / 2.96) | **3.89** (3.89 / 3.90) | **4.71** (4.70 / 4.71) | **5.08** (5.08 / 5.11) | **5.33** (5.32 / 5.36) | **5.62** (5.59 / 5.64) | **5.72** (5.69 / 5.74) | **5.84** (5.82 / 5.89) |
| x1b-warm-150 seeds ≥ 0.9 × command | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 3/10 |
| x1b-warm-150 tracks (O3) | yes | yes | yes | yes | yes | yes | yes | yes | **yes** | no |
| s2a-hold-150 (previous top), median | 0.86 | 1.80 | 2.95 | 4.08 | 4.55 | **4.57** | 4.53 | – | – | – |
| x1a-cold-150, median | 1.03 | 1.93 | 3.07 | 3.96 | **4.12** | 4.11 | 4.15 | 4.14 | 4.10 | 4.03 |
| v05 b1-s2-180, median | 1.84 | 2.59 | 1.85 | 1.80 | – | – | 1.62 | – | – | – |

(v05's row from `../orun18/b1-s2-180.md`.)

Per seed at 150, last 2 s m/s:

| command | seeds 1001–1010 |
|---|---|
| 700 | 2.01 2.01 2.01 2.01 2.01 2.01 2.02 2.01 2.01 2.01 |
| 1500 | 2.38 2.38 2.39 2.39 2.38 2.38 2.38 2.41 2.40 2.38 |
| 2400 | 2.95 2.96 2.96 2.95 2.95 2.94 2.95 2.95 2.93 2.96 |
| 3500 | 3.90 3.89 3.89 3.89 3.89 3.89 3.90 3.89 3.89 3.90 |
| 4230 | 4.71 4.71 4.71 4.71 4.71 4.71 4.71 4.71 4.70 4.71 |
| 4630 | 5.08 5.08 5.09 5.09 5.09 5.09 5.08 5.08 5.11 5.08 |
| 5000 | 5.33 5.34 5.33 5.35 5.33 5.36 5.33 5.32 5.35 5.32 |
| 5500 | 5.62 5.60 5.63 5.59 5.63 5.63 5.62 5.62 5.64 5.61 |
| 6000 | 5.70 5.72 5.74 5.72 5.72 5.69 5.70 5.71 5.72 5.69 |
| 6500 | 5.88 5.83 5.84 5.83 5.84 5.84 5.82 5.89 5.82 5.89 |

- **At 50 it already raises the top**: it tracks seven commands, 0.7 to
  5.0 m/s, with 0 falls, and holds 4.84 m/s at 5.0 (4.83 the slowest seed),
  Fr 6.03, against s2a-hold-150's 4.57 (Fr 5.38). It runs ~4.8 m/s from
  4.23 up, and 3.0–4.7 m/s below that whatever it is commanded.
- **At 150 it tracks nine commands, 0.7 to 6.0 m/s, with 0/100 falls. Its
  top tracked is 5.72 m/s held at 6.0 (5.69 the slowest seed), Fr 8.42.**
  The fastest it holds on any judged command, with 0 falls, is **5.84 m/s at
  6.5 (5.82–5.89 on all ten seeds), Fr 8.78**; 6.5 is not tracked (seven
  seeds hold 0.895–0.898 of it).
- Its speed follows the command at every judged command above 2.4 m/s,
  over it by 6–11% at 3.5–5.0 and 2% at 5.5, and under it at 6.0 (−5%)
  and 6.5 (−10%). Below 2.4 it runs over the command (2.0 m/s at 0.7, 2.4
  at 1.5), which O3 never counts as a miss.
- **It runs past its training goal.** The goal it trained on stops at
  5.0 m/s (`x1b-warm.md`); commanded 5.5–6.5, which it never saw, it keeps
  running faster. The speed spec stops at 6.5, so `speed_judge.py` judges
  no higher; whether it holds more above 6.5 is not tested.
- Beside the others: v05's B1 2.59 m/s at most (Fr 1.73), Go1's tracked
  1.53 m/s (Fr 0.80), orun10's 4.64 m/s, the best on any earlier cat.

## Gait and O6 at 150

| command m/s | 3.5 | 5.0 | 6.0 | 6.5 |
|---|---|---|---|---|
| touchdown phase of RH / LF / RF in LH's stride | 0.38 / 0.38 / 0.87 | 0.43 / 0.43 / 0.87 | 0.38 / 0.38 / 0.88 | 0.37 / 0.37 / 0.88 |
| engine footfall stride Hz (seed median) | 6.25 | 6.25 | 6.25 | 6.25 |
| touchdown Hz LF / RF; LH / RH | 6.3 / 6.2; 6.2 / 6.3 | 6.3 / 6.2; 6.2 / 6.3 | 6.3 / 6.2; 6.2 / 6.3 | 6.3 / 6.2; 5.8 / 6.3 |
| step advance mm LF / RF; LH / RH | 616 / 616; 623 / 610 | 853 / 854; 843 / 852 | 905 / 913; 913 / 912 | 931 / 932; 932 / 930 |
| flight share; flight s | 1.00; 0.080 | 1.00; 0.100 | 1.00; 0.100 | 1.00; 0.100 |
| heel pad share of hind stance LH / RH | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| worst RMS / rated (drive); peak margin | 1.45 (`j_spine_yaw`); 0.00 | 1.60 (`j_spine_yaw`); 0.00 | 1.76 (`j_hip_r`); 0.00 | 1.87 (`j_hip_r`); 0.00 |
| drives at their clamp ≥ 0.05 of frames | `j_tail2` 0.13 | `j_tail2` 0.42, `j_elbow_l` 0.12, `j_hock_r` 0.11, `j_elbow_r` 0.08, `j_knee_r` 0.08 | `j_tail2` 0.48, `j_elbow_l` 0.13, `j_knee_r` 0.13, `j_hock_r` 0.13, `j_elbow_r` 0.11, `j_hip_r` 0.08, `j_hip_l` 0.07 | `j_tail2` 0.48, `j_hock_r` 0.14, `j_elbow_l` 0.13, `j_knee_r` 0.13, `j_elbow_r` 0.11, `j_hip_l` 0.09 |
| hind rod loop gap max mm; tail cable gap max ° | 0.9; 2.9 | 1.5; 3.6 | 1.7; 3.4 | 1.8; 4.0 |
| max tilt ° median | – | 5.7 | 5.6 | 5.7 |
| falls; non-finite seeds | 0; 0 | 0; 0 | 0; 0 | 0; 0 |

Left against right, RMS over rated (seed median, L / R):

| drive | 5.0 | 6.0 | 6.5 |
|---|---|---|---|
| fore abduction | 0.40 / 0.45 | 0.42 / 0.49 | 0.41 / 0.48 |
| scapula | 1.29 / 1.21 | 1.43 / 1.35 | 1.46 / 1.40 |
| shoulder | 1.00 / 0.72 | 1.06 / 0.77 | 1.11 / 0.73 |
| elbow | 1.29 / 1.21 | 1.35 / 1.29 | 1.35 / 1.31 |
| hind abduction | 0.74 / 0.51 | 0.72 / 0.55 | 0.70 / 0.56 |
| hip | 1.37 / 1.41 | 1.74 / 1.75 | 1.83 / 1.85 |
| knee | 0.66 / 1.10 | 0.57 / 1.12 | 0.51 / 1.12 |
| hock | 0.92 / 1.09 | 1.06 / 1.21 | 1.11 / 1.27 |
| `j_spine` / `j_spine_yaw` | 0.77 / 1.60 | 0.73 / 1.70 | 0.73 / 1.71 |

At 50 (4.63 / 5.0 / 6.5): an 8.33 Hz stride with 543–578 mm steps (s2a-hold's
gait), 0.06 s of flight every stride, worst RMS 1.44–1.46× (`j_spine_yaw`,
then `j_elbow_l` at 6.5), hips 1.03–1.29, loops within 1.9 mm, no
non-finite seed, heel pad never down.

- **One gait at every speed from 3.5 up**: a 6.25 Hz stride with a flight
  every stride (0.08–0.10 s), the hinds touching down together-ish (RH at
  0.37–0.43 of LH's stride, LF with it, RF at 0.87–0.88). Speed rises with
  step length alone, 616 mm at 3.5 to 931 mm at 6.5 m/s, at a fixed
  frequency. That is between s2a-hold's 8.33 Hz short steps and X1a's
  4.55 Hz long ones.
- **What binds is the hind hips, then the spine's yaw**: both hips at
  1.74–1.85× rated at 6.0–6.5 (1.37–1.41 at 5.0), `j_spine_yaw` at
  1.60–1.71×, the scapulae at 1.40–1.46×. Peak margin is 0.00 at every
  command, as on every v06 policy. The hip's RMS rises fastest with speed,
  so a faster policy on this body pays at the hips first.
- **Left against right**: the hips are even (within 2%); the fore shoulder
  still leans left (1.4–1.5× the right's), and the hind knee and hock lean
  right, as on every v06 policy.
- It is a toe gait on every command: the heel pad never touches. Loops
  within 1.8 mm; no NaN.

## What it says for X1

**X1b raises the top.** Taking out the tent's give-back past the command,
warm from s2a-hold-150 with nothing else changed, moves the top tracked
speed from 4.57 m/s (Fr 5.38) to **5.72 m/s at 6.0 (Fr 8.42)**, and the
fastest held from 4.57 to **5.84 m/s (Fr 8.78)**, with 0/200 falls across
both checkpoints. The streak of X1 screens without a new top is reset to 0.

The reward was still climbing at 150 (22.75 at 146, the best) and the
policy runs faster than its 5 m/s training goal ever asked. The next lever
is the critic's: a `track_speed` that keeps paying past the command, warm
from `10f197e1`, with the speed spec's range raised above 6.5 m/s so the
judge can read it. The hind hips at 1.8× rated are the drive to watch.
