# orun9 O8: the over-rated price, screened by weight

Verified against source: 2026-10-17. Frozen evidence (orun9, iteration 4 on).

O8 measured that `stand` fails `within_rated` on `j_hock_r` alone and `run`
fails on speed, not torque (`o8-torque.md`). The screen re-prices the
reward-only change c1-t8 made at weight 8: two terms, `over_rated_fore` and
`over_rated_hind`, price each drive's squared excess over its rating at
`hinge_w`, gated off with the speed asked (`exp(-(v/2 m/s)^2)`). Each screen
is a 100-iteration warm start from c1-t7 at iteration 150 (ADR-753; critic
warm-up 10, 8192 envs, seed 0), judged at iterations 50 and 100 on the six
specs and the 10 frozen seeds with the engine's evaluation
(`~/orun8-progress/c1/judge2.py`, `--reward-may-differ`), as in
`c1-checkpoints.md`.

| screen | hinge_w | cat revision | task |
|---|---|---|---|
| c1-t7 (base) | — | `ffa07dad` | `62790eb7` |
| c1-h2 | 2 | `07b0d74b` | `1673469d` |
| c1-h4 | 4 | `eafcc0f6` | `983ab777` (training) |
| c1-t8 (orun8) | 8 | — | `b5940042` |

## Pass counts (cell: passed/10; then each failing predicate, its pass count and median)

| run | it | run | stand | shove | turn2 | reverse | points |
|---|---|---|---|---|---|---|---|
| c1-t7 | 150 | **0/10**; tracks_speed 0/10 (med 521) | **0/10**; still 8/10 (med 172), within_rated 0/10 (med 1.38) | **9/10** | **8/10**; within_rated 8/10 (med 0.967) | **0/10**; reverses 0/10 (med 62.9), within_rated 5/10 (med 0.997) | **0/10**; reaches 0/10, close 0/10 (med 7.78e+03) |
| c1-h2 | 50 | **0/10**; tracks_speed 0/10 (med 691) | **1/10**; still 1/10 (med 267) | **10/10** | **7/10**; completes 9/10, upright 9/10, tail_clear 8/10 | **0/10**; reverses 0/10 (med 36.4), completes 8/10, upright 8/10, tail_clear 8/10 | **0/10**; reaches 0/10, close 0/10 (med 8.3e+03) |
| c1-h2 | 100 | **0/10**; tracks_speed 0/10 (med 626) | **0/10**; still 0/10 (med 497) | **10/10** | **10/10** | **0/10**; reverses 0/10 (med 66.5) | **0/10**; reaches 0/10, close 0/10 (med 6.94e+03) |

## c1-h2 (weight 2)

- **turn2 passes 10/10 at iteration 100**, the first full turn2 pass on the
  cat: yaw error median 15.1 deg/s, speed error 267 mm/s, worst drive
  0.845 of rated, tail clear and used in turns (`tail_turns` 10/10).
- **`within_rated` passes on every spec and seed at iteration 100**: worst
  drive median 0.83 on `run`, 0.68 on `stand` (c1-t7 had 1.38 on stand).
- **It traded the same way c1-t8 did (weight 8), less far on run.** `stand` drift
  rose from 172 to 497 mm (bar 200). `run` error rose from 521 to 626 mm/s.
  Median chest speed in the 3 m/s segments fell from 2.56/2.42 to
  2.33/2.28 m/s (c1-t8: 806 mm/s, 1.90/1.85 m/s). The run's worst drive
  is `j_wrist_r` (0.83 whole). `j_spine_yaw` is 1.06/1.02 of rated in the
  sprint segments, which the sprint exception allows. The gate still prices
  the excess at exp(-(3/2)^2) = 0.105 of the weight at 3 m/s.
- **reverse** stays 0/10 (heading error 36 deg at it 50, 66 at it 100,
  bar 20). **points** stays 0/10 (closest approach 6.9 m).

Between iterations 50 and 100, run, turn2 and points improve while stand
drift doubles. Reward per step was still climbing at 100 (best 6.20 at
it 96).
