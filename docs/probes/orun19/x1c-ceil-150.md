# orun19 X1c: x1c-ceil judged at 50 and 150 — no new top

Verified against source: 2026-10-24. Frozen evidence (orun19, iteration 24).
Charter X1's third screen, `x1c-ceil` (`x1c-ceil.md`: x1b-warm's task with
the training goal's ceiling 5000 → 7500 mm/s and the judged range to
8000; warm from x1b-warm-150 `10f197e1` by ADR-791, seed 0, 4096 envs, 150
iterations). It is judged at its midpoint and end at S's commands plus
4.23, 4.63, 5.5, 6.0, 6.5, 7.0, 7.5 and 8.0 m/s, beside X1's top,
`x1b-warm-150` (5.72 m/s tracked at 6.0, Fr 8.42; 5.84 m/s held at 6.5, Fr
8.78; `x1b-warm-150.md`).

```
R=~/cadex-projects/leo/runs/x1c-ceil/train; E=~/cadex-projects/leo/evaluations
cp $R/speed.000050.cxpolicy ~/orun19-queue/x1c-ceil-50.cxpolicy                     # 443f2928
cp $R/speed.000150.cxpolicy ~/orun19-queue/x1c-ceil-150.cxpolicy                    # 56182229 = speed.cxpolicy
for N in 50 150; do
  CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
      ~/cadex-projects/leo $R ~/orun19-queue/x1c-ceil-$N.cxpolicy x1c-ceil-$N \
      --cmd 700 1500 2400 3500 4230 4630 5000 5500 6000 6500 7000 7500 8000
done
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun19/o3_reread.py $E x1c-ceil-50 x1c-ceil-150 x1b-warm-150
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py $E/x1c-ceil-150-<cmd> ...
python3 docs/probes/orun19/s1_tables.py $E/x1c-ceil-150-<cmd> ...
```

Froude numbers use v06's hip height, 0.396 m (`froude.py`), Fr = v² / (g h).

## The checkpoints

- **50:** `speed.000050.cxpolicy`, **`443f2928`**. Judged on the CPU beside
  the live trainer, 7 min 53 s for 130 seeds.
- **150:** `speed.000150.cxpolicy` = the final `speed.cxpolicy`,
  **`56182229`**; trained task `ab9e023e`, model `f9b8ab82` (leo v06,
  unchanged). 150/150 iterations in 3,008 s of trainer wall (3,084 s with
  the supervisor), inside the 3,620 s budget; witness agrees to 1.6e-7.
  Judged on the CPU with the GPU idle, 7 min 47 s for 130 seeds.
- **Curve** (reward per step; checkpoints' first iterations sit low after
  the checkpoint rollout's reset; σ): 8.43 at 0 (0.411), 8.63 at 25, 10.10
  at 50 (0.458), 11.01 at 75, 11.69 at 100 (0.454), 12.04 at 125. Between
  checkpoints it went from ~20.25 (iterations 10–24) to ~20.6 (135–148);
  best 21.23 at 110, 20.95 at 149, σ 0.463. x1b-warm climbed from ~19.2 to
  22.75 over the same span, with σ falling to 0.419. A higher goal pays
  less per step at the same speed under `min(v, cmd) / cmd`, so the two
  curves are not on one scale; σ did not fall in x1c.

## Speed, and O3

**0 falls on 260 seeds** (C2_SEEDS 1001–1010 per command, 13 commands, at
both checkpoints; upright 130/130 at each).

| command m/s | 0.7 | 1.5 | 2.4 | 3.5 | 4.23 | 4.63 | 5.0 | 5.5 | 6.0 | 6.5 | 7.0 | 7.5 | 8.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| x1c-ceil-50, last 2 s m/s, median (min / max) | 4.19 (4.16 / 4.21) | 4.40 (4.38 / 4.40) | 4.72 (4.71 / 4.73) | 5.05 (5.05 / 5.06) | 5.23 (5.22 / 5.24) | 5.29 (5.28 / 5.33) | 5.35 (5.33 / 5.36) | 5.41 (5.38 / 5.42) | 5.44 (5.44 / 5.46) | 5.57 (5.55 / 5.67) | 5.76 (5.71 / 5.76) | 5.72 (5.67 / 5.74) | 5.74 (5.70 / 5.75) |
| x1c-ceil-50 tracks (O3) | yes | yes | yes | yes | yes | yes | yes | yes | **yes** | no | no | no | no |
| **x1c-ceil-150**, median (min / max) | 3.55 (3.51 / 3.59) | 3.61 (3.57 / 3.66) | 3.98 (3.97 / 3.99) | 4.67 (4.66 / 4.68) | 5.03 (5.02 / 5.03) | 5.21 (5.20 / 5.21) | 5.32 (5.32 / 5.33) | 5.48 (5.47 / 5.48) | **5.61** (5.60 / 5.62) | 5.68 (5.68 / 5.68) | 5.74 (5.74 / 5.75) | 5.77 (5.77 / 5.80) | **5.82** (5.79 / 5.87) |
| x1c-ceil-150 seeds ≥ 0.9 × command | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| x1c-ceil-150 tracks (O3) | yes | yes | yes | yes | yes | yes | yes | yes | **yes** | no | no | no | no |
| x1b-warm-150 (the top), median | 2.01 | 2.38 | 2.95 | 3.89 | 4.71 | 5.08 | 5.33 | 5.62 | **5.72** | 5.84 | – | – | – |

Per seed at 150, last 2 s m/s:

| command | seeds 1001–1010 |
|---|---|
| 700 | 3.54 3.57 3.54 3.51 3.51 3.59 3.55 3.55 3.57 3.54 |
| 1500 | 3.61 3.57 3.63 3.66 3.66 3.60 3.60 3.61 3.59 3.62 |
| 2400 | 3.99 3.98 3.98 3.97 3.97 3.97 3.99 3.98 3.97 3.99 |
| 3500 | 4.66 4.67 4.67 4.67 4.67 4.67 4.67 4.67 4.68 4.66 |
| 4230 | 5.03 5.03 5.03 5.03 5.03 5.02 5.03 5.03 5.02 5.03 |
| 4630 | 5.21 5.21 5.21 5.21 5.21 5.21 5.21 5.21 5.21 5.20 |
| 5000 | 5.32 5.32 5.32 5.33 5.32 5.33 5.32 5.32 5.33 5.32 |
| 5500 | 5.47 5.48 5.48 5.48 5.48 5.48 5.47 5.47 5.48 5.47 |
| 6000 | 5.60 5.61 5.61 5.61 5.61 5.62 5.60 5.61 5.61 5.60 |
| 6500 | 5.68 5.68 5.68 5.68 5.68 5.68 5.68 5.68 5.68 5.68 |
| 7000 | 5.74 5.74 5.74 5.74 5.74 5.75 5.74 5.74 5.75 5.74 |
| 7500 | 5.77 5.77 5.78 5.77 5.77 5.78 5.77 5.78 5.80 5.77 |
| 8000 | 5.84 5.84 5.83 5.79 5.80 5.83 5.82 5.81 5.87 5.79 |

- **At 150 it tracks nine commands, 0.7 to 6.0 m/s, with 0/130 falls: top
  tracked 5.61 m/s at 6.0 (5.60 the slowest seed), Fr 8.10**, under
  x1b-warm-150's 5.72 (Fr 8.42). The fastest it holds is **5.82 m/s at 8.0
  (5.79–5.87), Fr 8.72**, against x1b's 5.84 at 6.5 (Fr 8.78). 6.5 is
  missed by every seed (0.873 of it).
- At 50 it tracked the same nine, top 5.44 m/s at 6.0 (Fr 7.62), fastest
  held 5.76 at 7.0 (Fr 8.54).
- **Asking for more bought nothing at the top.** Commanded 6.0 → 8.0 m/s,
  its held speed rises only 5.61 → 5.82, 0.21 m/s for 2 m/s more command
  (8.0 is past its 7.5 training goal). Its slow end
  moved up instead: 3.55 m/s at 0.7 (x1b 2.01), so the speed range it
  covers narrowed to 3.5–5.8 m/s. O3 never counts running over a command
  as a miss.
- **The streak without a new top is now 1** (X1c's is the first failed
  screen in a row since X1b).

## Gait and O6 at 150

| command m/s | 3.5 | 5.0 | 6.0 | 6.5 | 7.0 | 8.0 |
|---|---|---|---|---|---|---|
| touchdown phase of RH / LF / RF in LH's stride | 0.50 / 0.50 / 0.00 | 0.50 / 0.50 / 0.00 | 0.50 / 0.50 / 0.00 | 0.50 / 0.50 / 0.00 | 0.50 / 0.50 / 0.00 | 0.50 / 0.50 / 0.00 |
| engine footfall stride Hz (seed median) | 6.25 | 6.25 | 6.25 | 6.25 | 6.25 | 6.25 |
| step advance mm LF / RF; LH / RH | 734 / 735; 730 / 730 | 850 / 850; 833 / 834 | 894 / 895; 877 / 877 | 906 / 905; 889 / 888 | 917 / 917; 900 / 901 | 930 / 931; 914 / 913 |
| flight share; flight s | 1.00; 0.080 | 1.00; 0.080 | 1.00; 0.080 | 1.00; 0.080 | 1.00; 0.080 | 1.00; 0.080 |
| heel pad share of hind stance LH / RH | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| worst RMS / rated (drive); peak margin | 1.42 (`j_spine_yaw`); 0.00 | 1.45 (`j_spine_yaw`); 0.00 | 1.62 (`j_hip_r`); 0.00 | 1.68 (`j_hip_r`); 0.00 | 1.71 (`j_hip_r`); 0.00 | 1.81 (`j_hip_r`); 0.00 |
| drives at their clamp ≥ 0.05 of frames | `j_tail2` 0.31 | `j_tail2` 0.26, `j_elbow_l` 0.12, `j_elbow_r` 0.11, `j_hock_r` 0.11 | `j_tail2` 0.14, `j_elbow_l` 0.12, `j_elbow_r` 0.11, `j_hock_r` 0.11 | `j_tail2` 0.14, `j_elbow_l` 0.12, `j_elbow_r` 0.11, `j_hock_r` 0.08 | `j_tail2` 0.18, `j_elbow_l` 0.12, `j_elbow_r` 0.11, `j_hock_l` 0.10 | `j_tail2` 0.20, `j_elbow_l` 0.12, `j_hock_r` 0.12, `j_hip_r` 0.12, `j_hock_l` 0.11, `j_elbow_r` 0.10, `j_shoulder_l` 0.06 |
| hind rod loop gap max mm; tail cable gap max ° | 1.0; 3.4 | 1.2; 3.9 | 1.2; 3.9 | 1.1; 4.0 | 1.3; 4.5 | 1.4; 4.5 |
| max tilt ° median | – | 10.6 | 10.5 | 10.4 | 10.2 | 9.3 |
| falls; non-finite seeds | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |

Left against right, RMS over rated (seed median, L / R):

| drive | 5.0 | 6.0 | 6.5 | 7.0 | 8.0 |
|---|---|---|---|---|---|
| fore abduction | 0.46 / 0.37 | 0.44 / 0.37 | 0.44 / 0.35 | 0.43 / 0.35 | 0.41 / 0.31 |
| scapula | 1.15 / 1.19 | 1.23 / 1.29 | 1.26 / 1.32 | 1.28 / 1.35 | 1.30 / 1.38 |
| shoulder | 1.09 / 0.77 | 1.14 / 0.83 | 1.15 / 0.85 | 1.15 / 0.88 | 1.22 / 0.82 |
| elbow | 1.24 / 1.23 | 1.24 / 1.26 | 1.24 / 1.27 | 1.24 / 1.29 | 1.24 / 1.29 |
| hind abduction | 0.70 / 0.61 | 0.77 / 0.73 | 0.81 / 0.77 | 0.83 / 0.81 | 0.86 / 0.83 |
| hip | 1.27 / 1.39 | 1.42 / 1.62 | 1.50 / 1.68 | 1.56 / 1.71 | 1.63 / 1.81 |
| knee | 0.63 / 0.95 | 0.64 / 0.94 | 0.64 / 0.92 | 0.62 / 0.94 | 0.60 / 1.00 |
| hock | 0.91 / 1.05 | 1.03 / 1.14 | 1.12 / 1.13 | 1.15 / 1.09 | 1.17 / 1.20 |
| `j_spine` / `j_spine_yaw` | 0.54 / 1.45 | 0.58 / 1.47 | 0.62 / 1.49 | 0.64 / 1.51 | 0.68 / 1.53 |

At 50 (6.0 / 7.0 / 8.0): the same 6.25 Hz stride, 874–915 mm steps, 0.085–
0.10 s of flight every stride, worst RMS 1.62 / 1.79 / 1.90× (the hips),
`j_spine_yaw` 1.54, loops within 2.0 mm, no non-finite seed, heel pad never
down. Its footfall at 7.0 and 8.0 was still x1b's (RH and LF at 0.38 of LH's
stride, RF at 0.88); at 6.0 it was already the diagonal pairing below.

- **A different footfall at the same frequency.** x1b-warm-150 put RH and
  LF at 0.37–0.43 of LH's stride and RF at 0.87–0.88. x1c-ceil-150 pairs the
  diagonals at every command from 3.5 up: RF with LH, LF and RH half a
  stride later, with a flight of 0.08 s each stride. It is a flying trot at
  6.25 Hz, with steps 730 → 930 mm.
- **The trot costs less at the hips and the spine at the same speed.** At
  6.0 commanded the hips are 1.42 / 1.62× rated (x1b 1.74 / 1.75) and
  `j_spine_yaw` 1.47× (x1b 1.70); at 8.0, the right hip reaches 1.81×.
  It holds 0.11 m/s less at 6.0. It tilts more: 10.5° median against x1b's
  5.6°.
- **Left against right**: the hips now lean right (1.11–1.14×), the fore
  shoulder still leans left (1.3–1.5×), the hind knee right (1.5–1.7×).
- Peak margin 0.00 at every command, as on every v06 policy; loops within
  1.4 mm; no NaN; the heel pad never touches.

## What it says for X1

**X1c does not raise the top.** Raising the training goal's ceiling to
7.5 m/s under X1b's one-sided reward, warm from the top with nothing else
changed, ends at 5.61 m/s tracked at 6.0 (Fr 8.10) and 5.82 m/s held at
8.0 (Fr 8.72), against x1b-warm-150's 5.72 (Fr 8.42) and 5.84 (Fr 8.78).
It is the first failed X1 screen in a row. The top stays `x1b-warm-150`
(`10f197e1`).

What it shows: commands past ~6 m/s are not what holds the speed back.
The policy saw goals to 7.5 m/s for 150 iterations, kept its 6.25 Hz
stride, moved to a trot that loads the hips less, and held ~5.8 m/s
whatever it was asked. σ stayed at ~0.46 (x1b's fell to 0.42). The hips
still lead the drives at the top (1.8× rated at 8.0) with peak margin
0.00, so the next single change is on what the task charges for torque,
not on the command: the regularisers' weights (O3's third lever), warm from
`10f197e1` on x1b's task, or the command draw weighted toward the top.
