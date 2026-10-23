# orun19 S2a: s2a-hold judged at 150; speed now follows the command tightly, but ~20% over it

Verified against source: 2026-10-23. Frozen evidence (orun19, iteration 9).
Charter S2's first O3 screen, `s2a-hold` (s1-v06's task with the speed command
held per episode, resample 3 s → 12 s, cold, 150 iterations;
`s1-v06-180.md` § S2a's launch), judged at its end beside its own midpoint
(`s2a-hold-50.md`), `s1-v06-180` and v05's `b1-s2-180`
(`../orun18/b1-s2-180.md`).

```
R=~/cadex-projects/leo/runs/s2a-hold/train; E=~/cadex-projects/leo/evaluations
cp $R/speed.000150.cxpolicy ~/orun19-queue/s2a-hold-150.cxpolicy                    # efe7f96b = speed.cxpolicy
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
    ~/cadex-projects/leo $R ~/orun19-queue/s2a-hold-150.cxpolicy s2a-hold-150 --cmd 700 1500 2400 3500 5000
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py $E/s2a-hold-150-{700,1500,2400,3500,5000}
python3 docs/probes/orun19/s1_tables.py $E/s2a-hold-150-{700,1500,2400,3500,5000}
```

Per-seed speeds are `b1_summary.last_window_speed` on each evaluation's seeds.

## The checkpoint

`speed.000150.cxpolicy` = the final `speed.cxpolicy`, **`efe7f96b`** (the
evaluations' `policy_sha256`; the status file's receipt, witness error
1.5e-7), trained task `d5b25b15`, judged task `4ae65191`, model `f9b8ab82`
(leo v06, unchanged). 150/150 iterations, 3,118 s of trainer wall. Reward
per step 10.20 at 50, 15.09 at 100, 17.24 at 125, **18.92 at 150** (best
148, still climbing ~0.07 an iteration), σ 0.52, episode 463 of 500 steps.

## Speed, and O3

**0 falls on 50 seeds** (C2_SEEDS 1001–1010 per command, upright 50/50).

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| **s2a-hold-150, last 2 s m/s, median (min / max)** | **0.86** (0.84 / 0.87) | **1.80** (1.77 / 1.83) | **2.95** (2.93 / 2.98) | **4.08** (4.00 / 4.21) | **4.53** (4.49 / 4.59) |
| over the command, median | +23% | +20% | +23% | +17% | −9% |
| seeds within 10% of the command (O3) | 0/10 | 0/10 | 0/10 | 0/10 | **9/10** |
| mean forward m/s over the episode, median | 0.86 | 1.80 | 2.93 | 3.97 | 4.38 |
| max tilt °, median | 6.9 | 8.2 | 10.8 | 10.5 | 9.5 |
| s2a-hold-50, last 2 s m/s, median | 1.80 | 1.95 | 1.63 | 2.23 | 1.05 |
| s1-v06-180, last 2 s m/s, median (within 10%) | 0.75 (6/10) | 2.17 (0/10) | 3.07 (0/10) | 3.77 (10/10) | 4.24 (0/10) |
| **v05 b1-s2-180, last 2 s m/s, median** | 1.84 | 2.59 | 1.85 | 1.80 | 1.62 |

Per seed, last 2 s m/s:

| command | seeds 1001–1010 |
|---|---|
| 700 | 0.84 0.86 0.86 0.86 0.87 0.86 0.84 0.86 0.86 0.85 |
| 1500 | 1.78 1.82 1.82 1.78 1.79 1.77 1.80 1.78 1.83 1.80 |
| 2400 | 2.95 2.96 2.96 2.93 2.94 2.95 2.98 2.95 2.95 2.95 |
| 3500 | 4.21 4.17 4.00 4.07 4.07 4.14 4.10 4.12 4.00 4.01 |
| 5000 | 4.57 4.53 4.49 4.58 4.53 4.51 4.53 4.53 4.56 4.59 |

- **Speed now follows the command, monotone and tight**: seed to seed
  within ±2% at 700–2400 and ±3% at 3500, against s1-v06-180's 1.07–1.45×
  scatter between commands. No seed veers (max tilt ≤ 11°).
- **But it runs ~1.2× the command** at every command it can reach
  (+17–23% at 700–3500), and so **tracks (O3) at one command only, 5000**
  (9/10; seed 1003 at 4.49 is 10.2% short), where the body tops out at
  4.53 m/s. s1-v06-180 tracked two (700, 3500). **S2 is not met.**
- **The top tracked speed is 4.53 m/s, Fr 5.28** (hip height 0.396 m, as
  in `s1-v06-180.md`), against v05's B1 2.59 m/s (Fr 1.73), Go1's tracked
  1.53 m/s (Fr 0.80), and s1-v06-180's tracked 3.77 m/s (Fr 3.66).
- **Why over, uniformly.** `track_speed` is the tent
  `UP * (v − 0.75 (v − cmd + |v − cmd|)) / cmd`: slope +1/cmd below the
  command but only −0.5/cmd above it. With the speed varying through each
  stride, the expected reward of such a tent peaks above the command (the
  mean sits where twice the share of time under it equals the share over
  it). A uniform proportional overshoot with a tiny spread is what that
  predicts once sampling no longer confounds it. This is the reading, not a
  measurement: S2b tests it.

## Footfall, flight, the heel pad

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| touchdown phase of RH / LF / RF in LH's stride (pooled median, t ≥ 4 s) | – / – / – | 0.18 / – / – | 0.30 / – / 0.25 | 0.25 / 0.25 / 0.29 | 0.33 / 0.33 / 0.83 |
| engine footfall stride Hz (seed median) | – | 4.55 | 1.85 | 6.35 | 8.33 |
| touchdown Hz LF / RF; LH / RH | 10.0 / 10.0; 10.1 / 9.6 | 9.3 / 9.2; 9.2 / 8.9 | 8.9 / 8.9; 8.1 / 8.8 | 8.4 / 8.2; 7.2 / 8.0 | 8.3 / 7.9; 7.7 / 8.3 |
| step advance mm LF / RF; LH / RH | – / –; 187 / 168 | – / –; 282 / 215 | 158 / 342; 492 / 344 | 490 / 487; 495 / 492 | 543 / 543; 544 / 542 |
| flight share; flight s | –; – | –; – | –; – | 1.00; 0.060 | 1.00; 0.060 |
| **heel pad share of hind stance LH / RH** | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| heel pad stance height mm LH / RH | 140 / 124 | 139 / 133 | 138 / 137 | 137 / 139 | 136 / 135 |

- **Two gaits now, not one.** At 700–2400 no flight and short, fast steps
  (8–10 touchdowns a second per foot, hind steps 170–490 mm; where `–`,
  `s1_tables.py` found too few fore touchdowns inside a left-hind stride to
  phase). At 3500–5000 a flight on every stride (60 ms) with all four feet
  stepping ~490–545 mm, the hinds 0.25–0.33 apart: bound-like. s2a-hold-50
  bounded at every command.
- **The heel pad never touches** (rides 124–140 mm up): toe stance on the
  balls at every speed, as on every v06 policy so far.

## O6: torque, left against right, a clean simulation

| command mm/s | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| worst RMS / rated (drive); peak margin | 1.03 (`j_shoulder_r`); 0.00 | 1.14 (`j_shoulder_l`); 0.00 | 1.17 (`j_knee_r`); 0.00 | 1.34 (`j_elbow_l`); 0.00 | 1.43 (`j_elbow_l`); 0.00 |
| drives at their clamp ≥ 0.05 of frames (seed median) | none | `j_knee_r` 0.08 | `j_knee_r` 0.10, `j_tail2` 0.08 | `j_tail2` 0.27, `j_elbow_l` 0.14, `j_elbow_r` 0.13, `j_knee_r` 0.08 | `j_tail2` 0.36, `j_elbow_l` 0.17, `j_hock_l` 0.16, `j_knee_r` 0.14, `j_shoulder_l` 0.13 |
| hind rod loop gap max mm; cable gap max ° (`coupling/cable_tail4`) | 1.0; 1.8 | 1.3; 2.9 | 1.3; 3.8 | 1.5; 4.5 | 1.5; 4.7 |
| falls; non-finite seeds | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |

RMS over rated, seed median, left / right (`b1_summary.py`; v06 has no
wrist, and `j_tail2` has no rating):

| drive | 700 | 1500 | 2400 | 3500 | 5000 |
|---|---|---|---|---|---|
| fore abduction | 0.42 / 0.49 | 0.46 / 0.33 | 0.46 / 0.29 | 0.56 / 0.35 | 0.67 / 0.41 |
| scapula | 0.62 / 0.46 | 0.72 / 0.31 | 0.79 / 0.42 | 0.99 / 0.69 | 1.12 / 0.91 |
| shoulder | 0.97 / 1.03 | 1.14 / 0.82 | 1.16 / 0.66 | 1.06 / 0.53 | 1.34 / 0.65 |
| elbow | 0.42 / 0.48 | 0.55 / 0.66 | 0.70 / 1.10 | 1.34 / 1.27 | 1.43 / 0.96 |
| hind abduction | 0.39 / 0.36 | 0.52 / 0.38 | 0.60 / 0.45 | 0.65 / 0.50 | 0.70 / 0.51 |
| hip | 0.30 / 0.31 | 0.34 / 0.44 | 0.55 / 0.73 | 0.87 / 1.09 | 1.00 / 1.31 |
| knee | 0.67 / 0.82 | 0.58 / 1.05 | 0.53 / 1.17 | 0.57 / 1.11 | 0.51 / 1.22 |
| hock | 0.25 / 0.28 | 0.31 / 0.32 | 0.55 / 0.49 | 0.95 / 0.86 | 1.24 / 1.27 |
| `j_spine`, `j_spine_yaw`, `j_tail1` | 0.26, 0.56, 0.68 | 0.49, 0.83, 0.68 | 0.66, 1.06, 0.67 | 0.55, 1.31, 0.73 | 0.70, 1.37, 0.74 |

- **Torque.** Near rated at 700 (worst 1.03), over it from 1500 and most at
  speed: the left elbow 1.34–1.43×, the spine yaw 1.31–1.37×, the hocks and
  the right hip 1.24–1.31× at 5000. Peak margin 0.00 everywhere; at 5000 the
  left elbow, left hock, right knee and left shoulder each sit at the clamp
  on 0.13–0.17 of frames. The spine pitch drive, 1.12–1.73× at 50, is
  within rated now (0.26–0.70).
- **Left against right.** The fores lean left (shoulder 1.4–2.1× the
  right's at 1500–5000, scapula 1.2–2.3×); the hinds lean right at the knee
  (1.2–2.4× the left's) and the hip, as on s1-v06 and at 50.
- **Clean.** No NaN; **hind rod loops within 2 mm** (1.0–1.5 mm max); tail
  cable couplings open 1.8–4.7° at most (`cable_tail4`).

## Read at 150, and S2b's launch

Holding the command per episode (O3's first lever) did what s1-v06 did not:
speed is a tight, monotone function of the command, and the slow end walks
without flight. It did not make it track: a uniform ~1.2× overshoot, the
asymmetric tent's signature, leaves one tracked command (5000). Next is
O3's second lever, `track_speed`'s shape, alone.

`~/orun19-queue/leo_s2b.py` is `leo_s2a.py` with one expression changed,
`track_speed`'s tent made symmetric:

```
UP * (comv_x - 0.75 * (comv_x - cmd + abs(comv_x - cmd))) / cmd    # s2a: slope -0.5/cmd over
UP * (cmd - abs(comv_x - cmd)) / cmd                               # s2b: slope -1/cmd over
```

The peak (1 at the command), the undershoot side, the weight (20) and every
other term, goal and channel are s2a-hold's.

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun13/queue_run.py ~/cadex-projects/leo s2b-tent 3600 150 \
    "orun19 S2b: s2a-hold's task with track_speed's tent made symmetric (overshoot slope -0.5 -> -1), cold" \
    --seed 0 --task speed --envs 4096 --after s2a-hold --build ~/orun19-queue/leo_s2b.py
```

Cold, seed 0, 4096 envs, 150 iterations, queued 2026-10-23 16:07:33; the
budget is s2a-hold's 3,600 s, its measured 3,118 s + 15%: under O5's + 20%
(3,740 s), so it binds only if S2b runs more than 15% slower than S2a.

Built by `queue_run.py` as leo revision **`4ff224d2`** in ~3 min, launched
16:10:45. Its bundle `runs/s2b-tent/train/speed-task.json` (`c5e8223c`)
differs from s2a-hold's `d5b25b15` in exactly one field,
`reward/1/expression` (`track_speed`); the model XML is byte-identical
(`f9b8ab82`). Iteration 10 came at 336 s of trainer wall (s2a-hold: 372 s),
reward 3.28 (s2a-hold: 3.43), GPU 99% busy.
