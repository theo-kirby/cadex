# orun9 C1/C2: every checkpoint of c1-t6, c1-t7, c1-t8 on the six specs

Verified against source: 2026-10-17. Frozen evidence (orun9, iteration 1).

`~/cadex-projects/orun8-cat` at accepted revision `9b2517f2` (c1-t8's task), the
10 frozen seeds, the engine's own evaluation child (`judge2.py`, CPU only).
c1-t6 and c1-t7 checkpoints were judged with `--reward-may-differ`: their
bundles differ from today's only in the reward, and each spec's `success`
block is byte-equal to the one their final policies were judged on in orun8.
Iteration 150 is each run's last policy (judged in orun8; c1-t8's evaluations
committed now). Each cell: seeds passed, then every failing predicate with its
pass count and median.

c1-t9 (`hinge_w` 8 -> 3) was never launched and is discarded: it was a
one-guess reward edit, which O8 forbids before the per-drive measurement.

| run | it | run | stand | shove | turn2 | reverse | points |
|---|---|---|---|---|---|---|---|
| c1-t6 | 50 | **0/10**; tracks_speed 0/10 (med 1.15e+03) | **2/10**; still 2/10 (med 225), within_rated 9/10 (med 0.907) | **9/10**; completes 9/10 (med 1), upright 9/10 (med 5.05), recovers 9/10 (med 0.0133) | **0/10**; tracks_yaw 9/10 (med 17.1), tracks_speed 1/10 (med 344), within_rated 7/10 (med 0.97) | **0/10**; reverses 0/10 (med 74.9), within_rated 6/10 (med 0.99) | **0/10**; reaches 0/10 (med 0), close 0/10 (med 1.07e+04) |
| c1-t6 | 100 | **0/10**; tracks_speed 0/10 (med 655) | **0/10**; still 0/10 (med 433), within_rated 1/10 (med 1.2) | **10/10** | **7/10**; tracks_yaw 8/10 (med 18.3), within_rated 9/10 (med 0.97) | **0/10**; reverses 0/10 (med 78.9), within_rated 6/10 (med 0.978) | **0/10**; reaches 0/10 (med 0), close 0/10 (med 1.11e+04) |
| c1-t6 | 150 | **0/10**; tracks_speed 0/10 (med 546) | **0/10**; still 8/10 (med 173), within_rated 0/10 (med 1.2) | **10/10** | **3/10**; within_rated 3/10 (med 1) | **0/10**; reverses 0/10 (med 73.4), within_rated 0/10 (med 1.08), tail_clear 9/10 (med 0) | **0/10**; reaches 0/10 (med 0), close 0/10 (med 1.13e+04) |
| c1-t7 | 50 | **0/10**; tracks_speed 0/10 (med 866) | **3/10**; still 7/10 (med 185), within_rated 5/10 (med 0.998) | **9/10**; completes 9/10 (med 1), upright 9/10 (med 3.93), recovers 9/10 (med 0.0133) | **1/10**; tracks_yaw 4/10 (med 20.1), within_rated 2/10 (med 1.04) | **0/10**; reverses 0/10 (med 101), within_rated 2/10 (med 1.07) | **0/10**; reaches 0/10 (med 0), close 0/10 (med 1.07e+04) |
| c1-t7 | 100 | **0/10**; tracks_speed 0/10 (med 611) | **0/10**; still 7/10 (med 178), within_rated 0/10 (med 1.25) | **9/10**; completes 9/10 (med 1), upright 9/10 (med 4.81), recovers 9/10 (med 0.0104) | **9/10**; within_rated 9/10 (med 0.974) | **0/10**; reverses 0/10 (med 78.9), within_rated 6/10 (med 0.996) | **0/10**; reaches 0/10 (med 0), close 0/10 (med 9.92e+03) |
| c1-t7 | 150 | **0/10**; tracks_speed 0/10 (med 521) | **0/10**; still 8/10 (med 172), within_rated 0/10 (med 1.38) | **9/10**; completes 9/10 (med 1), upright 9/10 (med 4.6), recovers 9/10 (med 0.0133) | **8/10**; within_rated 8/10 (med 0.967) | **0/10**; reverses 0/10 (med 62.9), within_rated 5/10 (med 0.997) | **0/10**; completes 9/10 (med 1), upright 9/10 (med 5.6), reaches 0/10 (med 0), close 0/10 (med 7.78e+03), within_rated 6/10 (med 0.965), tail_clear 8/10 (med 0) |
| c1-t8 | 50 | **0/10**; tracks_speed 0/10 (med 975), tail_clear 6/10 (med 0) | **2/10**; still 2/10 (med 298) | **9/10**; completes 9/10 (med 1), upright 9/10 (med 8.86), recovers 9/10 (med 0.189) | **0/10**; tracks_yaw 9/10 (med 14.5), tracks_speed 0/10 (med 393), tail_clear 0/10 (med 0.00666) | **0/10**; reverses 0/10 (med 47.4), tail_clear 1/10 (med 0.00499) | **0/10**; reaches 0/10 (med 0), close 0/10 (med 1.03e+04) |
| c1-t8 | 100 | **0/10**; tracks_speed 0/10 (med 899), tail_clear 8/10 (med 0) | **1/10**; still 1/10 (med 245) | **10/10** | **4/10**; tail_clear 4/10 (med 0.00166) | **0/10**; reverses 0/10 (med 53.9), tail_clear 1/10 (med 0.00166) | **0/10**; reaches 0/10 (med 0), close 0/10 (med 1.03e+04) |
| c1-t8 | 150 | **0/10**; tracks_speed 0/10 (med 806) | **0/10**; still 0/10 (med 291) | **10/10** | **1/10**; tail_clear 1/10 (med 0.00333) | **0/10**; reverses 0/10 (med 35.9), tail_clear 7/10 (med 0) | **0/10**; reaches 0/10 (med 0), close 0/10 (med 7.97e+03) |

## What the checkpoints show

- **No checkpoint passes run, stand or points.** Intermediate checkpoints hide
  no better C1 policy.
- **turn2:** the best is c1-t7 at 100, **9/10**, failing `within_rated` on one
  seed (median 0.974). c1-t8 at 100 fails only `tail_clear` (4/10).
- **run:** RMS error falls monotonically within each run; the lowest is
  c1-t7 at 150, 521 mm/s (bar 300). c1-t8's price on effort cost speed at
  every checkpoint (975 -> 899 -> 806).
- **stand:** the best is c1-t7 at 50, 3/10 (`still` 7/10 at med 185 mm,
  `within_rated` 5/10 at med 0.998). Over training, the c1-t6/t7 line drifts
  less by iteration 150 (172-173 mm) but goes over rated (1.2-1.38); c1-t8 is within rated but drifts more
  (245-298 mm). The two bars trade against each other.
- **reverse:** heading error falls only under c1-t8 (47 -> 54 -> 36 deg, bar 20).
- **points:** 0/10 everywhere; median closest approach 7.8-11 m.
- **shove:** 9-10/10 throughout.

The trade between `within_rated` and speed/drift is what O8's per-drive
measurement must locate next.
