# orun19 S2: s2a-hold-150 at 4.23 and 4.63 m/s — it tracks to 4.63

Verified against source: 2026-10-23. Frozen evidence (orun19, iteration 18).
`s2a-hold-150` (`efe7f96b`, judged in `s2a-hold-150.md`) was judged at two
more commands, M2's top stride (4.23 m/s) and M1's slowest (4.63 m/s), so
S has a command in common with each end of M1 and M2 for F1's films. The
same judge, seeds and policy file; nothing was trained.

```
R=~/cadex-projects/leo/runs/s2a-hold/train; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
    ~/cadex-projects/leo $R ~/orun19-queue/s2a-hold-150.cxpolicy s2a-hold-150 --cmd 4230 4630
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py $E/s2a-hold-150-{3500,4230,4630,5000}
python3 docs/probes/orun19/s1_tables.py $E/s2a-hold-150-{3500,4230,4630,5000}
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun19/o3_reread.py $E s2a-hold-150
```

Both evaluations carry `policy_sha256` `efe7f96b`. Each took about 36 s on the
CPU beside l1-dog's trainer.

## Speed, and O3 (revised)

0 falls on the 20 new seeds (C2_SEEDS 1001–1010 per command, upright 20/20).

| command m/s | 0.7 | 1.5 | 2.4 | 3.5 | **4.23** | **4.63** | 5.0 |
|---|---|---|---|---|---|---|---|
| last 2 s m/s, median (min / max) | 0.86 (0.84 / 0.87) | 1.80 (1.77 / 1.83) | 2.95 (2.93 / 2.98) | 4.08 (4.00 / 4.21) | **4.55** (4.51 / 4.58) | **4.57** (4.54 / 4.59) | 4.53 (4.49 / 4.59) |
| slowest seed / command | 1.204 | 1.181 | 1.223 | 1.144 | 1.066 | 0.981 | 0.898 |
| seeds ≥ 0.9 × command | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 9/10 |
| tracks | yes | yes | yes | yes | **yes** | **yes** | no |

- **s2a-hold-150 tracks six commands, 0.7 to 4.63 m/s, with 0 falls.** Its
  top tracked command rises from 3.5 to **4.63 m/s, held at 4.57 m/s median
  (4.54 the slowest seed), Fr 5.38** (hip height 0.396 m). The 3.5 m/s top
  in `o3-reread.md` was set by which commands had been judged, not by the
  policy.
- Above about 4.2 m/s commanded the speed stops following the command: 4.55,
  4.57 and 4.53 m/s at 4.23, 4.63 and 5.0. That is the policy's ceiling,
  ~4.55 m/s.
- Beside it on a tracked command: m2-dog-150 tracks to 3.5 (4.36 m/s held, Fr
  4.89) and m1-cheetah-150 tracks 4.63 only (4.25 m/s held). Faster on one
  command but not tracked: m2-dog-150 holds 4.83 m/s at 4.23 (Fr 6.01), with
  seed 1007 tipped at reset. Beside them: v05's B1 2.59 m/s (Fr 1.73) and
  Go1's 1.53 m/s (Fr 0.80).

## Gait and O6 at the new commands

| command m/s | 3.5 | 4.23 | 4.63 | 5.0 |
|---|---|---|---|---|
| touchdown phase of RH / LF / RF in LH's stride | 0.25 / 0.25 / 0.29 | 0.33 / 0.33 / 0.83 | 0.33 / 0.33 / 0.83 | 0.33 / 0.33 / 0.83 |
| engine footfall stride Hz (seed median) | 6.35 | 8.33 | 8.33 | 8.33 |
| step advance mm LF / RF; LH / RH | 490 / 487; 495 / 492 | 542 / 542; 542 / 539 | 544 / 545; 546 / 544 | 543 / 543; 544 / 542 |
| flight share; flight s | 1.00; 0.060 | 1.00; 0.060 | 1.00; 0.060 | 1.00; 0.060 |
| heel pad share of hind stance LH / RH | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 / 0.00 |
| worst RMS / rated (drive); peak margin | 1.34 (`j_elbow_l`); 0.00 | 1.41 (`j_elbow_l`); 0.00 | 1.42 (`j_elbow_l`); 0.00 | 1.43 (`j_elbow_l`); 0.00 |
| drives at their clamp ≥ 0.05 of frames | `j_tail2` 0.27, `j_elbow_l` 0.14, `j_elbow_r` 0.13, `j_knee_r` 0.08 | `j_tail2` 0.32, `j_elbow_l` 0.17, `j_hock_l` 0.14, `j_knee_r` 0.11, `j_shoulder_l` 0.09 | `j_tail2` 0.33, `j_elbow_l` 0.17, `j_hock_l` 0.15, `j_knee_r` 0.13, `j_shoulder_l` 0.11 | `j_tail2` 0.36, `j_elbow_l` 0.17, `j_hock_l` 0.16, `j_knee_r` 0.14, `j_shoulder_l` 0.13 |
| hind rod loop gap max mm | 1.5 | 1.6 | 1.6 | 1.5 |
| falls; non-finite seeds | 0; 0 | 0; 0 | 0; 0 | 0; 0 |

Left against right, RMS over rated (seed median, L / R):

| drive | 4.23 | 4.63 |
|---|---|---|
| shoulder | 1.30 / 0.74 | 1.32 / 0.73 |
| elbow | 1.41 / 1.15 | 1.42 / 1.11 |
| hip | 0.96 / 1.22 | 0.99 / 1.29 |
| knee | 0.49 / 1.22 | 0.51 / 1.19 |
| hock | 1.14 / 1.07 | 1.20 / 1.22 |

- At 4.23–5.0 it runs one gait: the same 0.33 / 0.33 / 0.83 order, 8.33 Hz
  footfall stride, ~543 mm step and 0.060 s of flight on every stride. It
  sets the gait at 4.23 and does not change it at higher commands.
- It is a toe gait on every command: the heel pad never touches.
- The bound is the left fore elbow, 1.41–1.43× rated, at its clamp on 17% of
  frames. The asymmetry is the one `s2a-hold-150.md` measured: fores lean
  left, hinds lean right at hip and knee.

This changes which policy reads fastest on a tracked command, from
m2-dog-150 (4.36) to s2a-hold-150 (4.57). L1 was picked on the older
reading and is already training on m2-dog-150. X1 counts a top only with 0
falls on the judged seeds. So its previous top is s2a-hold-150's 4.57 m/s.
m2-dog-150's 4.83 m/s at 4.23 does not count, because seed 1007 tipped
there. Its 0-fall best is 4.36 m/s at 3.5.
