# orun9 O8: the over-rated price, screened by weight

Verified against source: 2026-10-17. Frozen evidence (orun9, iterations 4–6).

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
| c1-h4 | 4 | `eafcc0f6` | `983ab777` |
| c1-h2x | 2 | `07b0d74b` | `1673469d` (c1-h2 at 100, extended 100; its it 50/100 are 150/200 overall) |
| c1-t8 (orun8) | 8 | — | `b5940042` |

## Pass counts (cell: passed/10; then each failing predicate, its pass count and median)

| run | it | run | stand | shove | turn2 | reverse | points |
|---|---|---|---|---|---|---|---|
| c1-t7 | 150 | **0/10**; tracks_speed 0/10 (med 521) | **0/10**; still 8/10 (med 172), within_rated 0/10 (med 1.38) | **9/10** | **8/10**; within_rated 8/10 (med 0.967) | **0/10**; reverses 0/10 (med 62.9), within_rated 5/10 (med 0.997) | **0/10**; reaches 0/10, close 0/10 (med 7.78e+03) |
| c1-h2 | 50 | **0/10**; tracks_speed 0/10 (med 691) | **1/10**; still 1/10 (med 267) | **10/10** | **7/10**; completes 9/10, upright 9/10, tail_clear 8/10 | **0/10**; reverses 0/10 (med 36.4), completes 8/10, upright 8/10, tail_clear 8/10 | **0/10**; reaches 0/10, close 0/10 (med 8.3e+03) |
| c1-h2 | 100 | **0/10**; tracks_speed 0/10 (med 626) | **0/10**; still 0/10 (med 497) | **10/10** | **10/10** | **0/10**; reverses 0/10 (med 66.5) | **0/10**; reaches 0/10, close 0/10 (med 6.94e+03) |
| c1-h4 | 50 | **0/10**; tracks_speed 0/10 (med 739) | **0/10**; still 0/10 (med 541) | **10/10** | **0/10**; tail_clear 0/10 (med 0.00166) | **0/10**; reverses 0/10 (med 41.8), tail_clear 1/10 (med 0.0025) | **0/10**; reaches 0/10, close 0/10 (med 9.04e+03) |
| c1-h4 | 100 | **0/10**; tracks_speed 0/10 (med 713) | **0/10**; still 0/10 (med 391) | **10/10** | **6/10**; tail_clear 6/10 (med 0) | **0/10**; reverses 0/10 (med 63.2), tail_clear 5/10 (med 0.000832) | **0/10**; reaches 0/10, close 0/10 (med 6.31e+03) |
| c1-h2x | 50 | **0/10**; tracks_speed 0/10 (med 675) | **0/10**; still 0/10 (med 249) | **10/10** | **7/10**; tracks_yaw 7/10 (med 17.9) | **0/10**; reverses 0/10 (med 38.1), completes 9/10, upright 9/10, tail_clear 7/10 | **0/10**; reaches 0/10, close 0/10 (med 8.4e+03) |
| c1-h2x | 100 | **0/10**; tracks_speed 0/10 (med 611) | **0/10**; still 0/10 (med 455) | **10/10** | **7/10**; tail_clear 7/10 (med 0) | **0/10**; reverses 0/10 (med 71.3) | **0/10**; reaches 0/10, close 0/10 (med 6.1e+03) |

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

## c1-h4 (weight 4)

- **No clause passes that c1-h2 did not.** `within_rated` passes on every
  spec and seed at both checkpoints (worst drive median 0.72 on `run`, 0.63
  on `stand`, 0.78 on `turn2` at iteration 100), as at weight 2.
- **turn2 is 0/10 at 50 and 6/10 at 100, on `tail_clear` alone**: the tail
  touches the ground in 0.08–1.0% of frames (bar 0). Yaw error (median
  15.9 deg/s), speed error (129 mm/s) and `tail_turns` (0.79) all pass on
  every seed. Weight 2 passed it 10/10.
- **Stand and run are worse than weight 2.** Stand drift median 541 mm at
  50 and 391 mm at 100 (h2: 267, 497; bar 200). Run error 739 and
  713 mm/s (h2: 691, 626). Median chest speed in the two 3 m/s segments
  is 2.05/2.00 m/s at 50 and 2.15/2.08 m/s at 100 (h2 at 100: 2.33/2.28).
- **reverse** 0/10 (heading error 41.8 deg at 50, 63.2 at 100);
  **points** 0/10 (closest approach 6.3 m).

Across weights 2, 4 and 8 a heavier price buys no rated margin the
spec needs (every weight passes `within_rated`) and costs sprint speed:
2.33, 2.15 and 1.90 m/s in the first 3 m/s segment at weights 2, 4 and 8.
Stand drift fails at every weight (497, 391, 291 mm; bar 200), so the
price does not settle standing; c1-t7, with no price, drifted 172 mm but
stood over rated on `j_hock_r` (1.38).

c1-h2x was then run: c1-h2 extended by 100 warm-started iterations on
the identical bundle (`1673469d`, revision `07b0d74b`, scope
`orun9-c1-h2x`), because weight 2 was the better screen and its reward was
still climbing at 100 (O6).

## c1-h2x (weight 2, extended: 200 iterations from c1-t7@150)

- **No clause passes that c1-h2 did not.** It is the second judged cat run
  in a row with no new clause (c1-h4, c1-h2x), so O1's B slot comes next.
- **turn2 falls from c1-h2's 10/10 to 7/10** at both checkpoints: at 50 on
  `tracks_yaw` (median 17.9 deg/s, bar 20), at 100 on `tail_clear` alone
  (the tail touches in 0–0.17% of frames on three seeds; bar 0).
- **Sprint speed recovers a little and stays short.** Median chest speed
  in the two 3 m/s segments is 2.22/2.19 m/s at 50 and 2.40/2.35 m/s at
  100 (c1-h2 at 100: 2.33/2.28; c1-t7 at 150: 2.56/2.42). Run error 675
  and 611 mm/s (bar 300), the lowest of the weight-2 line.
- **Stand drift does not settle:** 249 mm at 50, 455 at 100 (bar 200).
- **within_rated passes on every spec and seed**, worst drive median 0.87
  on `run`, 0.69 on `stand`, 0.88 on `turn2` at 100: the price holds
  rated without the speed back.
- **reverse** 0/10 (heading error 38.1 deg at 50, 71.3 at 100);
  **points** 0/10 (closest approach 6.1 m at 100).

**Next GPU run: B1's cold quadruped** (`b1-q1` on `orun9-quad`,
`b1-quad.md`), O1's B slot. Then the cat again.
