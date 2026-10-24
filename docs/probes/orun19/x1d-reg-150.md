# orun19 X1d: x1d-reg judged at 50 and 150 — no new top, slower

Verified against source: 2026-10-24. Frozen evidence (orun19, iteration 26).
Charter X1's fourth screen, `x1d-reg` (`x1d-reg.md`: x1b-warm's task with
the torque, energy and action-rate weights to a quarter, O3's third lever,
and the judged range to 8.0 m/s; warm from x1b-warm-150 `10f197e1`, seed 0,
4096 envs, 150 iterations). It is judged at its midpoint and end at S's
commands plus 4.23, 4.63, 5.5, 6.0, 6.5, 7.0, 7.5 and 8.0 m/s, beside X1's
top, `x1b-warm-150` (5.72 m/s tracked at 6.0, Fr 8.42; 5.84 m/s held at
6.5, Fr 8.78; `x1b-warm-150.md`).

```
R=~/cadex-projects/leo/runs/x1d-reg/train; E=~/cadex-projects/leo/evaluations
cp $R/speed.000050.cxpolicy ~/orun19-queue/x1d-reg-50.cxpolicy                      # 834908be
cp $R/speed.000150.cxpolicy ~/orun19-queue/x1d-reg-150.cxpolicy                     # a57ca0d2 = speed.cxpolicy
for N in 50 150; do
  CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
      ~/cadex-projects/leo $R ~/orun19-queue/x1d-reg-$N.cxpolicy x1d-reg-$N \
      --cmd 700 1500 2400 3500 4230 4630 5000 5500 6000 6500 7000 7500 8000
done
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun19/o3_reread.py $E x1d-reg-50 x1b-warm-150
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun19/o3_reread.py $E x1d-reg-150
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py $E/x1d-reg-150-4230 $E/x1d-reg-150-5000 $E/x1d-reg-150-6000
python3 docs/probes/orun19/s1_tables.py $E/x1d-reg-150-3500 $E/x1d-reg-150-4230 $E/x1d-reg-150-5000 $E/x1d-reg-150-6000 $E/x1d-reg-150-8000
python3 docs/probes/orun19/s1_tables.py $E/x1d-reg-50-5500 $E/x1d-reg-50-6000 $E/x1d-reg-50-7000 $E/x1d-reg-50-8000
```

The hips' peak margins are read from each evaluation's
`detail.drives.channels[]` (`effort_peak_ratio`, peak over the drive's
limit; `effort_clamp_share`), seeds pooled. Froude numbers use v06's hip
height, 0.396 m (`../orun18/froude.py`), Fr = v² / (g h).

## The checkpoints

- **50:** `speed.000050.cxpolicy`, **`834908be`**. Judged on the CPU beside
  the live trainer, 7 min 47 s for 130 seeds.
- **150:** `speed.000150.cxpolicy` = the final `speed.cxpolicy`,
  **`a57ca0d2`**; trained task `3ced6ed6`, model `f9b8ab82` (leo v06,
  unchanged). 150/150 iterations in 3,023 s of trainer wall, inside the
  3,620 s budget; witness agrees to 1.6e-7. Judged on the CPU with the GPU
  idle, 6 min 40 s for 130 seeds.
- **Curve** (reward per step; the first iteration after each checkpoint
  sits low after the checkpoint rollout's reset; σ): 10.77 at 0 (0.411),
  11.37 at 25, 12.54 at 50 (0.462), 13.09 at 75, 13.80 at 100 (0.456),
  14.70 at 125. Between checkpoints it peaked at **22.94 at iteration 82**
  (the trainer's best) and 22.87 at 7, then fell to ~20.5 at 145–149, with σ
  rising 0.411 → **0.493**. x1b-warm climbed to 22.75 with σ falling to
  0.419 over the same span, under the higher penalties.

## Speed, and O3

A seed "falls" here as `o3_reread.py` counts it: the engine's `falls` or an
episode that did not complete. Every one of this policy's is a tip past
the 30° tilt termination (max tilt 32–36°, ended at 1.8–8.5 s); the
engine's own `falls` metric is 0 on all of them.

| command m/s | 0.7 | 1.5 | 2.4 | 3.5 | 4.23 | 4.63 | 5.0 | 5.5 | 6.0 | 6.5 | 7.0 | 7.5 | 8.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| x1d-reg-50, last 2 s m/s, median (min / max) | 3.46 (3.45 / 3.47) | 3.77 (3.75 / 3.77) | 4.06 (4.05 / 4.07) | 4.44 (4.43 / 4.46) | 4.86 (4.82 / 4.86) | 5.03 (5.02 / 5.04) | 5.19 (5.18 / 5.20) | **5.31** (5.30 / 5.32) | 5.37 (5.36 / 5.38) | 5.40 (5.37 / 5.45) | 5.49 (5.45 / 5.53) | 5.01 (4.57 / 5.38) | 4.46 (3.59 / 5.37) |
| x1d-reg-50 falls (tips); tracks (O3) | 0; yes | 0; yes | 0; yes | 0; yes | 0; yes | 0; yes | 0; yes | 0; **yes** | 0; no | 0; no | 0; no | 3; no | 7; no |
| **x1d-reg-150**, median (min / max) | 2.20 (2.19 / 2.24) | 2.59 (2.57 / 2.61) | 3.08 (3.07 / 3.14) | 3.66 (3.61 / 3.73) | **3.95** (3.92 / 4.00) | 4.04 (3.98 / 4.11) | 4.09 (4.04 / 4.15) | 4.06 (4.00 / 4.14) | 3.96 (3.88 / 4.05) | 4.11 (3.87 / 4.18) | 4.15 (3.92 / 4.22) | 4.13 (3.79 / 4.19) | 4.13 (1.79 / 4.20) |
| x1d-reg-150 seeds ≥ 0.9 × command | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| x1d-reg-150 falls (tips); tracks (O3) | 0; yes | 0; yes | 0; yes | 0; yes | 0; **yes** | 0; no | 0; no | 0; no | 4; no | 10; no | 10; no | 10; no | 10; no |
| x1b-warm-150 (the top), median | 2.01 | 2.38 | 2.95 | 3.89 | 4.71 | 5.08 | 5.33 | 5.62 | **5.72** | 5.84 | – | – | – |

- **At 150 it tracks five commands, 0.7 to 4.23 m/s: top tracked 3.95 m/s
  at 4.23 (3.92 the slowest seed), Fr 4.02**, against x1b-warm-150's 5.72
  (Fr 8.42). Above 4.23 it holds ~4.0–4.15 m/s whatever it is commanded;
  the fastest it holds with no tip is **4.09 m/s at 5.0 (Fr 4.31)**. From
  6.0 up it tips: 4/10 at 6.0 and 10/10 at each of 6.5–8.0, **44/130 in
  all**.
- **At 50 it was faster but still under the top**: eight commands to 5.5,
  top tracked 5.31 m/s (Fr 7.26), fastest held with no tip 5.49 m/s at 7.0
  (Fr 7.76); 10/130 tips, at 7.5 and 8.0.
- **The extra 100 iterations lost speed**: 5.31 → 3.95 m/s top tracked
  and 5.19 → 4.09 at 5.0, while the slow end came down (3.46 → 2.20 at 0.7).
- **The streak without a new top is now 2** (X1c, then X1d).

## Gait and O6 at 150

| command m/s | 3.5 | 4.23 | 5.0 | 6.0 | 8.0 |
|---|---|---|---|---|---|
| touchdown phase of RH / LF / RF in LH's stride | 0.38 / 0.33 / 0.78 | 0.37 / 0.33 / 0.78 | 0.38 / 0.33 / 0.80 | 0.33 / 0.44 / 0.80 | 0.44 / 0.56 / 0.89 |
| engine footfall stride Hz (seed median) | 5.56 | 5.56 | 5.56 | 5.56 | 5.26 |
| touchdown Hz LF / RF; LH / RH | 5.8 / 6.9; 5.8 / 6.2 | 5.6 / 6.8; 5.6 / 6.0 | 5.4 / 6.5; 5.4 / 6.3 | 5.3 / 6.4; 4.8 / 6.4 | 5.3 / 6.0; 4.7 / 6.6 |
| step advance mm LF / RF; LH / RH | 611 / 618; 620 / 618 | 687 / 678; 685 / 682 | 739 / 734; 745 / 730 | 753 / 746; 766 / 724 | 714 / 690; 729 / 695 |
| flight share; flight s | 1.00; 0.060 | 1.00; 0.080 | 1.00; 0.080 | 1.00; 0.080 | 1.00; 0.100 |
| heel pad share of hind stance LH / RH | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| worst RMS / rated (drive); peak margin | 1.36 (`j_spine_yaw`); 0.00 | 1.44 (`j_spine_yaw`); 0.00 | 1.50 (`j_spine_yaw`); 0.00 | 1.46 (`j_spine_yaw`); 0.00 | 1.40 (`j_spine_yaw`); 0.00 |
| drives at their clamp ≥ 0.05 of frames | `j_tail2` 0.19, `j_hock_l` 0.09, `j_elbow_r` 0.05 | `j_tail2` 0.13, `j_hock_l` 0.12, `j_elbow_r` 0.10 | `j_tail2` 0.18, `j_elbow_r` 0.12, `j_hock_l` 0.10, `j_elbow_l` 0.06 | `j_tail2` 0.35, `j_elbow_r` 0.13, `j_hock_l` 0.11, `j_hock_r` 0.09, `j_shoulder_r` 0.08, `j_elbow_l` 0.06 | `j_tail2` 0.51, `j_elbow_r` 0.16, `j_hock_l` 0.14, `j_hock_r` 0.10, `j_shoulder_r` 0.09, `j_elbow_l` 0.06 |
| hind rod loop gap max mm; tail cable gap max ° | 1.3; 3.6 | 1.3; 3.7 | 1.3; 4.3 | 1.5; 4.2 | 1.4; 4.0 |
| non-finite seeds | 0 | 0 | 0 | 0 | 0 |

Left against right, RMS over rated (seed median, L / R; `b1_summary.py`):

| drive | 4.23 | 5.0 | 6.0 |
|---|---|---|---|
| fore abduction | 0.53 / 0.54 | 0.47 / 0.62 | 0.41 / 0.68 |
| scapula | 0.88 / 0.94 | 0.98 / 0.96 | 1.05 / 0.96 |
| shoulder | 0.83 / 1.10 | 0.76 / 1.18 | 0.71 / 1.26 |
| elbow | 1.10 / 1.30 | 1.20 / 1.33 | 1.23 / 1.34 |
| hind abduction | 0.50 / 0.52 | 0.46 / 0.56 | 0.49 / 0.61 |
| hip | 0.78 / 0.77 | 0.83 / 0.97 | 0.82 / 1.18 |
| knee | 0.84 / 0.61 | 0.78 / 0.69 | 0.78 / 0.74 |
| hock | 0.98 / 0.74 | 0.96 / 0.98 | 0.95 / 1.12 |
| `j_spine` / `j_spine_yaw` | 0.77 / 1.44 | 0.81 / 1.50 | 0.83 / 1.46 |

**The hips' peak margin**, beside x1b-warm-150 (hip rated 18 N·m, limit
53 N·m; peak over limit, max over seeds (median); share of frames at the
clamp, median; RMS over rated):

| policy, command | `j_hip_l` | `j_hip_r` |
|---|---|---|
| x1d-reg-150, 4.23 | 0.78 (0.72); 0.000; 0.78 | 1.00 (1.00); 0.002; 0.77 |
| x1d-reg-150, 5.0 | 0.86 (0.82); 0.000; 0.83 | 1.00 (1.00); 0.004; 0.97 |
| x1d-reg-150, 6.0 | 0.83 (0.72); 0.000; 0.82 | 1.00 (1.00); 0.029; 1.18 |
| x1d-reg-50, 6.0 | 1.00 (1.00); 0.003; 1.51 | 1.00 (1.00); 0.004; 1.34 |
| x1b-warm-150, 4.23 | 0.93 (0.82); 0.000; 1.05 | 1.00 (0.96); 0.000; 1.05 |
| x1b-warm-150, 5.0 | 1.00 (0.93); 0.000; 1.37 | 1.00 (1.00); 0.007; 1.41 |
| x1b-warm-150, 6.0 | 1.00 (1.00); **0.073**; **1.74** | 1.00 (1.00); **0.085**; **1.75** |

- **A slower, cheaper gait.** x1d-reg-150 left x1b's 6.25 Hz stride for
  5.56 Hz with shorter steps (611–766 mm against x1b's ~880–930 at
  5–6 m/s), and a footfall near x1b's (RH and LF at 0.33–0.38 of LH's
  stride, RF at 0.78–0.80; x1b 0.37–0.43 and 0.87–0.88), not x1c's
  diagonal trot.
- **Cheaper torque did not buy speed: the hips unloaded.** With torque and
  energy priced at a quarter, the hips run 0.8–1.2× rated at 4.23–6.0
  (x1b-warm-150 1.05–1.75×). The left hip never reaches its limit (peak
  0.72–0.86 of 53 N·m); the right touches it on 0.2–2.9% of frames. The
  worst drive is `j_spine_yaw`, 1.36–1.50×.
- **The trained policy got noisier**: σ rose 0.41 → 0.49 as its reward per
  step fell from 22.9 to 20.5, and the deterministic policy the judge plays
  got slower and tips above 6 m/s. `s2-speed-signal.md` measured that a
  v06 speed policy with its training noise runs ~0.85× its deterministic
  speed, so a policy calibrated for a noisier self plays differently. That
  this is why X1d lost speed is a reading, not measured here.
- **Left against right**: the right fore shoulder now leads the left
  (1.3–1.8×; X1c and x1b leaned left); the right hip leads above 5 m/s
  (1.2–1.4×).
- Peak margin 0.00 at every command (some drive at its limit, as on every
  v06 policy); loops within 1.5 mm; no NaN; the heel pad never touches.

## What it says for X1

**X1d does not raise the top.** Quartering the torque, energy and
action-rate weights on X1b's task, warm from the top with nothing else
changed, ends at 3.95 m/s tracked at 4.23 (Fr 4.02) and 4.09 m/s held at
5.0 (Fr 4.31), and tips on 44 of 130 seeds from 6.0 up, against
x1b-warm-150's 5.72 m/s (Fr 8.42) with 0/100 falls. At its midpoint it was
nearer the top (5.31 m/s tracked, Fr 7.26) and lost speed after.

That is **two failed X1 screens in a row** (X1c, X1d). Under the exhaustion
policy R1 is written in full (`REPORT.md`). The top stays `x1b-warm-150`
(`10f197e1`).

What it shows: the regularisers are not what keeps x1b's hips under their
limit. x1b's hips were already at their 53 N·m limit at 5–6 m/s with the
full penalties, at the clamp on 7–9% of frames at 6.0. Pricing torque less
did not lead to more hip torque or more speed; the policy lost σ control
and slowed down.
