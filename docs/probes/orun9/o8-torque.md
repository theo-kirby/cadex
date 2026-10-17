# orun9 O8: where each drive's RMS goes, per spec segment

Verified against source: 2026-10-17. Frozen evidence (orun9, iteration 2).

The engine evaluations of c1-t6, c1-t7 (and its iteration 100) and c1-t8 on
`run`, `stand` and `turn2` (`~/cadex-projects/orun8-cat/evaluations/`, the 10
frozen seeds, task `9b2517f2`; judged as in `c1-checkpoints.md`) were cut
into the five 2.4 s segments of each episode. For each of the 21 rated drives:
RMS torque over its continuous rating per segment and over the whole episode,
the share of frames at peak, and the chest's plan speed per segment. The
whole-episode figure reproduces the engine's `effort_rms_rated_ratio_max` on
every seed (asserted). Scripts, outside the repo: `~/orun9-progress/o8/`
(`o8_rms.py`, `summ.py`, `o8_sat.py`) and `~/orun8-progress/c1/segspeed.py`.

`run` commands 0.5, 3.0, 1.5, 0.5, 3.0 m/s (segments s0-s4). Cells are the
median over seeds; the bar is 1.0 over rated, whole episode, worst drive.

## run: torque does not bind the spec; speed does

| run | max drive, whole | s0 0.5 | s1 3.0 | s2 1.5 | s3 0.5 | s4 3.0 | speed s1 / s4 (m/s) | RMS error |
|---|---|---|---|---|---|---|---|---|
| c1-t6 | spine_yaw **0.916** | 0.42 | **1.21** | 0.95 | 0.47 | **1.21** | 2.45 / 2.41 | 546 |
| c1-t7 | spine_yaw **0.897** | 0.47 | **1.15** | 1.00 | 0.52 | **1.08** | 2.56 / 2.42 | 521 |
| c1-t8 | spine_yaw **0.632** | 0.41 | 0.75 | 0.71 | 0.44 | 0.74 | 1.90 / 1.85 | 806 |

- **The binding drive at speed is `j_spine_yaw`** (lateral spine, rated
  9 N·m) on 9-10 of 10 seeds in c1-t6 and c1-t8; c1-t7 shares it with
  `j_wrist_r`. Next are `j_scap_l`/`j_scap_r` (1.0-1.12 in the 3 m/s
  segments) and `j_wrist_r` (~1.0 in s2).
- **No seed's whole-episode ratio exceeds 1.0 on `run`** in any of the three
  runs: the 3 m/s segments go 8-21% over rated, the walk segments pay it
  back. c1-t6/t7 fail `run` only on `tracks_speed` (2.4-2.6 m/s at a 3 m/s
  command), never on `within_rated`.
- **No leg drive runs at peak.** The only drives that saturate at peak are
  the unrated tail servos (`j_tail2`/`j_tail4`, 18-31% of frames in the
  3 m/s segments; they carry no rating, so `within_rated` does not see
  them); the worst leg drive, `j_wrist_r`, sits at peak in 6-8% of s2's
  frames. The cat is not peak-limited at 2.5 m/s.
- **c1-t8's price cost speed it did not need to pay.** Its hinge term is
  gated to 0.1 at 3 m/s, yet the policy fell to 1.9 m/s with its worst drive
  at 0.75 in the sprint, a quarter below rated. Headroom on `run` is
  therefore not the question; the trade is the stand (below).

## stand: one drive, `j_hock_r`, on every seed

| run | max drive, whole | s0 | s1 | s2 | s3 | s4 | the other hock | drift (mm) |
|---|---|---|---|---|---|---|---|---|
| c1-t6 | hock_r **1.20** | 1.27 | 1.31 | 1.16 | 1.09 | 0.90 | hock_l 0.68 | 173 |
| c1-t7 | hock_r **1.38** | 1.46 | 1.41 | 1.32 | 1.33 | 1.35 | hock_l 0.74 | 172 |
| c1-t7 it 100 | hock_r **1.22** | 1.15 | 1.21 | 1.27 | 1.20 | 1.21 | hock_l 0.93 | 178 |
| c1-t8 | tail1 0.57 | 0.63 | 0.56 | 0.55 | 0.55 | 0.57 | — | 291 |

- **The stand fails `within_rated` on `j_hock_r` alone, 10/10 seeds** in
  c1-t6 and c1-t7. The hock is the smallest leg drive (rated 3 N·m, peak
  9 N·m), and the stance is lopsided: the left hock carries about half
  the right's torque. No other drive exceeds 0.8 at a stand.
- c1-t8's per-drive hinge (weight 8) fixed it outright (every drive ≤ 0.63)
  but drift rose to 291 mm against the 200 mm bar.

## turn2

- c1-t6: `j_spine_yaw` is the worst drive on 9/10 seeds, whole 1.005 (over
  on 7 seeds). c1-t7: whole 0.963, worst split `j_spine_yaw`/`j_hock_r`;
  over on 2 seeds (one each). c1-t8: 0.65, none over (it fails on the tail).

## The finding

1. **What binds is the right hock at a stand and the lateral spine at a
   sprint.** Each is one drive, not the whole body.
2. **3 m/s within rated is not shown impossible.** At 2.4-2.6 m/s the worst
   drive's whole-episode RMS is 0.90-0.92 and no leg drive is peak-limited.
   The sprint segments go up to 21% over rated, which the charter allows.
3. **c1-t8 overpaid.** Its hinge is near zero at 3 m/s, yet it left a
   quarter of the sprint rating unused and lost 0.6 m/s. Weight 8 is far
   past what the stand needs: c1-t7's overage is one drive at 1.2-1.4.

**Next (O8's screen):** price the hinge at a few lighter weights,
consecutive 100-iteration screens warm from c1-t7 (iteration 150: lowest
`run` error, 521 mm/s, and within rated on `run`), judged on `run`, `stand`
and `turn2`. c1-t8 (from c1-t7, `hinge_w` 8) is the heavy end point already
measured.
