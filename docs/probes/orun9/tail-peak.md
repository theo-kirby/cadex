# orun9: do the tail servos stay under peak?

Verified against source: 2026-10-17. Frozen evidence (orun9, iteration 4).

C's bar is "drives under peak torque always, within rated RMS except in a
sprint". The cat's tail has one rated QDD (`j_tail1`, 2.5 N·m rated, 7 N·m
peak) and three Feetech STS3215 bus servos (`j_tail2`-`j_tail4`). The
question: does the engine's peak check cover the three unrated servos?

## How the engine bounds peak

- **Peak is a clamp, not a predicate.** Every drive with an effort limit is
  compiled `forcelimited` with `forcerange` at that limit
  (`CadexDynamics.py`, the actuator build), so MuJoCo cannot deliver more.
  The `actuator_efforts` a trace records are the delivered (clamped) force.
  No spec predicate reads peak; `effort_clamp_share_max` and
  `effort_rms_clamp_ratio_max` exist (`CadexEvaluation.py`) but the cat's
  six specs bound neither.
- **The servos' limit is their stall torque.** `lib.servo(...).actuator`
  takes the catalog's stall torque at the chosen voltage. The cat runs them
  at 7.4 V: 19.5 kg·cm = **1912.3 N·mm** (`CadexCatalog.py`, `sts3215`).
- **They carry no rating.** The catalog gives no continuous torque for the
  STS3215, so `effort_rated` is `None` and `within_rated`
  (`effort_rms_rated_ratio_max`) leaves them out. It covers 21 of the cat's
  24 drives.

## Measured (10 frozen seeds, every frame)

Max `|effort|` over limit, RMS over limit, and the share of frames within 1 %
of the limit, pooled over seeds. Script, outside the repo:
`~/orun9-progress/tail/tail_peak.py`.

| eval | j_tail2 rms / at-limit | j_tail3 rms / at-limit | j_tail4 rms / at-limit | j_tail1 max (rated QDD) |
|---|---|---|---|---|
| c1-t6 run | 0.600 / 17.6 % | 0.453 / 1.9 % | 0.615 / 14.5 % | 1.000 |
| c1-t7 run | 0.587 / 15.7 % | 0.466 / 3.6 % | 0.617 / 14.8 % | 0.976 |
| c1-t8 run | 0.606 / 13.9 % | 0.463 / 4.3 % | 0.593 / 11.2 % | 0.631 |
| c1-t7 stand | 0.525 / 7.1 % | 0.331 / 0.1 % | 0.600 / 6.8 % | 0.898 |
| c1-t7 turn2 | 0.681 / 25.9 % | 0.477 / 3.9 % | 0.647 / 18.4 % | 0.974 |
| c1-t8 turn2 | 0.679 / 22.8 % | 0.524 / 11.1 % | 0.649 / 18.0 % | 0.604 |

- **No drive ever exceeds its limit.** Over all six evaluations and all 24
  drives, the largest excess of `|effort|` over the limit is exactly 0. The
  servos reach 1.000 of stall and stop there: they saturate, they do not
  exceed. "Under peak always" holds for the tail, by the clamp.
- **But they live at stall.** `j_tail2` and `j_tail4` sit at stall torque
  for 14-26 % of frames when running or turning (7 % standing), with RMS at
  0.53-0.68 of stall. The datasheet the catalog cites gives no continuous
  torque, so whether a real STS3215 holds that is not known here. No spec
  checks it, and `within_rated` is silent on the tail.

## What follows

The peak clause is met for every drive by construction. The tail is
unchecked on continuous load. Closing it needs a sourced continuous rating
for the STS3215 (a catalog change, not a guess) or a spec bound on
`effort_clamp_share_max`. Neither is done here.
