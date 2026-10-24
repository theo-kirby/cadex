# orun19 S2b: s2b-tent judged at 150; the symmetric tent ran further over the command, not closer; lever 2 rejected

Verified against source: 2026-10-23. Frozen evidence (orun19, iteration 12).
Charter S2's second O3 screen, `s2b-tent` (`s2a-hold-150.md` § S2b's launch:
s2a-hold's task with `track_speed`'s tent made symmetric, overshoot slope
−0.5 → −1 /cmd, nothing else changed, cold, 150 iterations), judged at its
end beside its own midpoint (`s2b-tent-50.md`), its parent's end
`s2a-hold-150` (`s2a-hold-150.md`) and v05's `b1-s2-180`
(`../orun18/b1-s2-180.md`).

```
R=~/cadex-projects/leo/runs/s2b-tent/train; E=~/cadex-projects/leo/evaluations
cp $R/speed.000150.cxpolicy ~/orun19-queue/s2b-tent-150.cxpolicy                    # f971c970 = speed.cxpolicy
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
    ~/cadex-projects/leo $R ~/orun19-queue/s2b-tent-150.cxpolicy s2b-tent-150 --cmd 700 1500 2400 3500 5000
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py $E/s2b-tent-150-{700,1500,2400,3500,5000}
python3 docs/probes/orun19/s1_tables.py $E/s2b-tent-150-{700,1500,2400,3500,5000}
```

Per-seed speeds are `b1_summary.last_window_speed` on each evaluation's
seeds; headings are the engine's `max_heading_deg` / `final_heading_deg`.

## The checkpoint

`speed.000150.cxpolicy` = the final `speed.cxpolicy`, **`f971c970`** (the
evaluations' `policy_sha256`; the status file's receipt, witness error
1.8e-7), trained task `c5e8223c`, judged task `04042bc3`, model `f9b8ab82`
(leo v06, unchanged). 150/150 iterations, 3,141 s of trainer wall (3,211 s
supervised, inside the 3,600 s budget). Reward per step 8.75 at 50, 12.90
at 100, 15.04 at 125, **17.41 at 150** (best 149, still climbing ~0.1 an
iteration), σ 0.54, episode 491 of 500 steps. The judge ran on the CPU
beside M1's trainer, 3 min 10 s for 50 seeds.

## Speed, and O3

**0 falls on 50 seeds** (C2_SEEDS 1001–1010 per command, upright 50/50).

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| **s2b-tent-150, last 2 s m/s, median (min / max)** | **0.97** (0.92 / 1.00) | **1.89** (1.88 / 1.93) | **3.09** (3.07 / 3.12) | **3.82** (3.77 / 3.92) | **4.01** (1.57 / 4.07) |
| over the command, median | +39% | +26% | +29% | +9% | −20% |
| seeds within 10% of the command (O3) | 0/10 | 0/10 | 0/10 | 6/10 | 0/10 |
| mean forward m/s over the episode, median | 0.97 | 1.89 | 3.05 | 3.73 | 3.89 |
| max tilt °, median | 8.6 | 9.3 | 10.8 | 12.1 | 11.4 |
| s2b-tent-50, last 2 s m/s, median | 1.27 | 1.43 | 1.49 | 1.23 | 1.16 |
| s2a-hold-150, last 2 s m/s, median (within 10%) | 0.86 (0/10) | 1.80 (0/10) | 2.95 (0/10) | 4.08 (0/10) | 4.53 (9/10) |
| **v05 b1-s2-180, last 2 s m/s, median** | 1.84 | 2.59 | 1.85 | 1.80 | 1.62 |

Per seed, last 2 s m/s:

| command | seeds 1001–1010 |
|---|---|
| 700 | 0.98 0.97 0.97 1.00 0.95 0.96 0.96 0.97 0.96 0.92 |
| 1500 | 1.89 1.93 1.89 1.88 1.90 1.90 1.89 1.89 1.92 1.90 |
| 2400 | 3.10 3.08 3.09 3.09 3.10 3.08 3.12 3.08 3.07 3.08 |
| 3500 | 3.82 3.88 3.86 3.77 3.80 3.86 3.92 3.81 3.80 3.82 |
| 5000 | 4.04 4.07 1.57 3.97 4.01 4.02 4.05 4.01 4.06 3.99 |

- **It does not track (O3)** at any command on every seed. At 3500 six
  seeds sit inside 10% (3.77–3.82 m/s against the 3.85 bound); the other
  four run 3.86–3.92. Its nearest is 3500 at +9% median.
- **Speed follows the command as tightly as s2a-hold-150's** (±2% seed to
  seed at 700–3500), monotone, but **further over it at the slow end**:
  +26–39% at 700–2400 against s2a-hold-150's +20–23%. Halving the reward
  for overshoot's slope did not pull the speeds down; it pushed them up.
- **The top end fell**: 4.01 m/s at 5000 (s2a-hold-150: 4.53), and seed
  1003 at 5000 slows to 1.57 m/s in its last 2 s, upright (max heading
  7.5°, the only seed past 5°).
- **Straight**: max heading 1.7–4.3° on 49/50 seeds, final heading within
  ±1.9°; the veer s2b-tent-50 showed above ~3 m/s is gone, as on
  s2a-hold-150.
- **Top speed and Froude.** Nothing is tracked on every seed. The fastest
  command with a majority inside 10% is 3500 at 3.82 m/s, **Fr 3.76** (hip
  height 0.396 m, as in `s1-v06-180.md`); against s2a-hold-150's 4.53 m/s
  (Fr 5.28, 9/10 at 5000), s1-v06-180's 3.77 m/s (Fr 3.66, 10/10 at 3500),
  v05's B1 2.59 m/s (Fr 1.73) and Go1's 1.53 m/s (Fr 0.80).

## Footfall, flight, the heel pad

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| touchdown phase of RH / LF / RF in LH's stride (pooled median, t ≥ 4 s) | 0.50 / 0.20 / 0.44 | 0.65 / – / 0.40 | – / – / 0.95 | 0.32 / 0.47 / 0.67 | 0.33 / 0.41 / 0.59 |
| engine footfall stride Hz (seed median) | 4.76 | 3.33 | 5.00 | 4.55 | 3.13 |
| touchdown Hz LF / RF; LH / RH | 9.9 / 10.2; 6.4 / 9.9 | 10.0 / 9.6; 5.5 / 10.0 | 10.0 / 10.0; 4.5 / 10.0 | 9.2 / 8.4; 5.0 / 6.2 | 8.9 / 7.9; 4.1 / 6.2 |
| step advance mm LF / RF; LH / RH | 212 / 158; 179 / 178 | – / 249; 391 / 371 | 131 / 372; 623 / 329 | 462 / 448; 835 / 790 | 477 / 473; 958 / 776 |
| flight share; flight s | 1.00; 0.160 | –; – | –; – | 1.00; 0.130 | 1.00; 0.100 |
| **heel pad share of hind stance LH / RH** | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| heel pad stance height mm LH / RH | 137 / 131 | 136 / 135 | 138 / 138 | 127 / 136 | 124 / 136 |

- **The feet tap at ~10 Hz** (fore both, right hind) at 700–2400, where the
  pooled phase is undefined (–) for feet whose touchdowns do not fall once
  a stride; the left hind steps at 4.5–6.4 Hz. At 3500–5000 it settles to
  a bounding stride with flight every stride (100–130 ms) and long hind
  steps (776–958 mm).
- **Left against right in the hinds**: the right hind touches down 1.2–2.2×
  as often as the left at every command.
- **The heel pad never touches** (rides 124–138 mm up): toe stance on the
  balls, as on every v06 policy so far.

## O6: torque, left against right, a clean simulation

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| worst RMS / rated (drive); peak margin | 1.37 (`j_knee_r`); 0.00 | 1.45 (`j_knee_r`); 0.00 | 1.42 (`j_elbow_l`); 0.00 | 1.58 (`j_hip_r`); 0.00 | 1.78 (`j_hip_r`); 0.00 |
| drives at their clamp ≥ 0.05 of frames (seed median) | `j_tail2` 0.20, `j_knee_r` 0.10 | `j_tail2` 0.30, `j_knee_r` 0.16 | `j_knee_r` 0.18, `j_tail2` 0.15, `j_elbow_l` 0.11 | `j_tail2` 0.22, `j_elbow_l` 0.15, `j_knee_r` 0.12, `j_elbow_r` 0.08, `j_shoulder_r` 0.06, `j_shoulder_l` 0.05 | `j_tail2` 0.22, `j_elbow_l` 0.14, `j_hip_r` 0.13, `j_knee_r` 0.12, `j_elbow_r` 0.07, `j_shoulder_l` 0.06, `j_shoulder_r` 0.05 |
| hind rod loop gap max mm; tail cable gap max ° (`coupling/cable_tail4`) | 1.5; 3.7 | 1.7; 5.3 | 1.8; 5.5 | **2.2**; 5.4 | **2.3**; 5.8 |
| falls; non-finite seeds | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |

RMS over rated, seed median, left / right (`b1_summary.py`; v06 has no
wrist, and `j_tail2` has no rating):

| drive | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| fore abduction | 0.39 / 0.29 | 0.30 / 0.30 | 0.31 / 0.36 | 0.36 / 0.35 | 0.33 / 0.38 |
| scapula | 0.56 / 0.37 | 0.68 / 0.43 | 0.73 / 0.47 | 0.92 / 0.66 | 0.99 / 0.71 |
| shoulder | 0.87 / 0.84 | 0.91 / 0.80 | 0.87 / 0.63 | 0.95 / 0.97 | 0.98 / 0.94 |
| elbow | 0.66 / 0.50 | 0.94 / 0.65 | 1.42 / 0.80 | 1.44 / 1.18 | 1.44 / 1.15 |
| hind abduction | 0.40 / 0.28 | 0.44 / 0.36 | 0.52 / 0.43 | 0.63 / 0.64 | 0.64 / 0.66 |
| hip | 0.20 / 0.59 | 0.30 / 0.90 | 0.55 / 1.18 | 0.98 / 1.58 | 1.12 / 1.78 |
| knee | 0.29 / 1.37 | 0.40 / 1.45 | 0.34 / 1.40 | 0.50 / 1.17 | 0.47 / 1.16 |
| hock | 0.20 / 0.57 | 0.29 / 0.58 | 0.59 / 0.72 | 0.72 / 0.93 | 0.83 / 1.02 |
| `j_spine`, `j_spine_yaw`, `j_tail1` | 0.97, 0.41, 0.72 | 1.17, 0.71, 0.78 | 1.07, 0.85, 0.75 | 0.65, 0.97, 0.95 | 0.63, 0.99, 1.01 |

- **Torque.** The fore shoulders came under rated (0.63–0.98, s2b-tent-50:
  1.11–1.58) and the spine pitch drive with them at 3500–5000 (0.63–0.65);
  what binds now is **the right hind**: knee 1.16–1.45× at every command,
  hip 1.18–1.78× from 2400, and the left elbow 1.42–1.44× from 2400.
  Peak margin 0.00 everywhere (`j_tail2`, unrated, at its clamp on
  0.15–0.30 of frames).
- **Left against right: lopsided in the hinds.** Right knee 2.3–4.7× the
  left's, right hip 1.6–3.0× (at 700, 0.59 against 0.20), matching the
  right hind's extra touchdowns; the left elbow carries 1.2–1.8× the
  right's.
- **Clean, but the rod loops are open past 2 mm at the top**: no NaN; hind
  rod loops 1.5–1.8 mm at 700–2400 and **2.2 / 2.3 mm at 3500 / 5000**,
  over O6's 2 mm (s2a-hold-150 and s2b-tent-50 stayed within it); tail
  cable couplings open 3.7–5.8°.

## Lever 2's verdict

**Rejected.** At its end, against its parent at the same iteration count
(`s2a-hold-150`), the symmetric tent:

- tracked on fewer seeds (6/50 within 10% against 9/50), at no command on
  every seed (s2a-hold-150: 5000 on 9/10);
- ran **further** over the command at 700–2400 (+26–39% against +20–23%),
  though it now pays twice as much for each m/s of overshoot;
- lost the top end (4.01 against 4.53 m/s at 5000) and drove the right
  hind's knee and hip over rated and the rod loops past 2 mm.

The overshoot growing under a steeper overshoot penalty says the tent's
shape is not what holds the slow end above its command. What does is not
measured yet; the next screen on O3's list is the third lever, one
regulariser weight alone, on `s2a-hold`'s task (the better of the two
parents, so s2b's tent is not carried forward). The trainer is busy with
M1 (`m1-cheetah`, launched 17:04 when s2b-tent finished, so the GPU did not
sit idle); the lever-3 screen queues behind it.

## M1's launch

Launched by the command in `s2b-tent-50.md` § M1, ready for the GPU, at
17:04:34, 2 min after s2b-tent's supervisor ended: run `m1-cheetah` on leo
revision `4ff224d2`, task `mocap_gallop` **`c3c099af`** in place of `speed`
`c5e8223c`, model `f9b8ab82` (the bundle's own, checked by
`queue_bundle.py`), cold, seed 0, 4096 envs, 150 iterations, budget
3,600 s. Iteration 10 came at **370 s** of trainer wall (s2b-tent 336 s,
s2a-hold 372 s), ~18.5 s an iteration over 4–10, reward 20.9 per step,
episodes 36 steps (a cold tracking task terminating early). At s2b-tent's
pace (~19.7 s an iteration after 10) 150 iterations take ~3,130 s, so the
3,600 s budget is +15% over that, under O5's +20% (3,760 s); the supervisor
reads its budget at start, so it is not re-set mid-run. It binds only if M1
runs more than 15% slower than s2b-tent did, and then it ends
`budget_exhausted` on its last 25-iteration checkpoint.
