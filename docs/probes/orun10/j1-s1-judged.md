# orun10 J1: j1-s1 judged at every checkpoint

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 11).

j1-s1 is the first J1 leap screen. It warm-starts on orun10-jump (`b59eb2b1`,
the 6 m wide J1 course: a 300 mm ledge at x = 3 m, 1.5 m long, then a drop)
from orun9's c1-c11b final policy. It ran at lr 3e-5 with a 10-iteration
critic warm-up, for 100 iterations at about 27 s each, with a checkpoint every
25 (`j-course.md`). Each checkpoint is judged on the leap bundle's own
`j1_spec`, seeds 1001–1010, through the engine's evaluation
(`orun10-jump/evaluations/j1-s1-*`; `judge_j1.py` and `summ_j1.py` in the
run's progress folder, `s8/`). The trainer's best is iteration 99, the same
policy as the final (identical judged numbers).

| checkpoint | pass | completes | up_across_down (platforms crossed, median) | lands_running (6 m made good; median) | highest platform reached | best 2 s speed, median | runs round the ledge (\|y\| > 3 m) | chest stalls at x (median, the rest) | worst RMS / rated (median; range) | peak margin |
|---|---|---|---|---|---|---|---|---|---|---|
| c1-c11b, zero-shot (for scale) | 0/10 | 9/10 | 0/10 (0) | 0/10 (2.60 m) | 0 | 1.17–1.24 m/s | none | 2.43–2.80 m | 1.24 (0.84–1.55) | 0 |
| 25 | 0/10 | 9/10 | 0/10 (0) | 0/10 (2.68 m) | 0 on all 10 | 1.23 m/s | 1004 | 2.68 m | 1.13 (1.06–1.42; j_hock_r 5, j_hock_l 4) | 0 |
| 50 | 0/10 | 9/10 | 0/10 (0) | 3/10 (2.73 m) | 0 on all 10 | 1.25 m/s | 1003, 1004, 1005, 1008 | 2.71 m | 1.17 (0.83–1.30; j_wrist_l 5, j_hock_l 4) | 0 |
| 75 | 0/10 | 7/10 | 0/10 (0) | 2/10 (2.70 m) | 0 on all 10 | 1.23 m/s | 1003, 1004, 1005 | 2.70 m | 1.09 (0.75–1.77; j_hock_l 7, j_shoulder_r 3) | 0 |
| final = best 99 | 0/10 | 6/10 | 0/10 (0) | 0/10 (2.70 m) | 0 on all 10 | 1.23 m/s | 1003, 1004, 1009 | 2.70 m | 1.06 (0.77–1.38; j_hock_l 5) | 0 |

`no_fall` passes 10/10 at every checkpoint. `completes` fails on tips (4 at
the final, worst tilt 22°). No take-off or leap peak is measured on any seed,
since none leaves the ground at the face. Every drive stays at or under peak:
the model clamps at peak, margin 0. The trainer's reward per step rose
0.80 → 6.57, which pays no pass (it is not a pass).

What it shows:

- **No seed leaps at any checkpoint.** The chest stops at x ≈ 2.7 m against
  the 3 m face on every seed that stays on the course. The highest platform
  reached is 0 on all 50 judged episodes. 100 iterations from C1 bought
  neither a take-off nor the run-up speed: the best 2 s mean stays at
  1.23–1.25 m/s, against the task's 2.5 m/s command, the same as zero-shot.
- **Seeds still run round the 6 m wide ledge.** Three or four seeds per
  checkpoint from 50 on leave the course sideways (y 4.8–19 m). The 3/10
  `lands_running` at 50 are three of these detours, not leaps. Widening the
  course from 1.2 m to 6 m moved the detour out; it did not stop it.
- **Why, in the task.** The leap task carries orun9's C1 reward. Its `speed`
  term tracks the command in the body frame, and it has no heading term
  (the gallop task has `heading`, −4 × |q_z|). `track_yaw` pays a yaw rate
  near zero, not a heading. So turning away to run round the ledge costs
  almost nothing, and nothing pays progress along +x or height gained. The
  reward has no reason to leap.

## Next for J1

O8's lesson for the reward applies before another screen: a per-step check
on the accepted leap bundle. A world-frame +x progress term (or the gallop
task's heading term) should pay the cat more for a leap onto the ledge than
for stalling at the face or detouring round it. Only then train on it. A
reward change is a curriculum key (ADR-161), so the next screen can
warm-start from j1-s1's final.
