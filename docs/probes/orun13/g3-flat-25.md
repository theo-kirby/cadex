# orun13 P1: g3-flat at 25, the two-sided flat-sole term flattens the left foot but lifts the right heel

Verified against source: 2026-10-20. Frozen evidence (orun13, iteration 5).

g3-flat is g2-heel5's task with `hind_flat` retargeted two-sided to leo's
flat sole (`g2-heel5-25.md`): full at `heel_pitch` +4.5°, nothing at
±15°, weight 6. It runs on revision `a280b070`, with the model XML
byte-identical to g2-heel5's. It is cold, 50 iterations, 4096 envs,
seed 0, launched 22:37:47. Checkpoint 25 (`gallop.000025.cxpolicy`,
sha256 `0b62ec3e`) was judged as `g2-heel5-50.md` was, on the bundle's
`gallop_spec`, seeds 1001–1010, on the CPU. The comparison is g2-heel5 at
the same checkpoint.

| evaluation | pass | top 2 s m/s min / med / max | straight (°) | hock_down LH / RH | at toe-off LH / RH | heel-down frames flat LH / RH | toes-up LH / RH | heel mm in stance LH / RH | no_tap | every_stride | overreach mm LH / RH | stride mm LH / RH | flight share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g2-heel5-25 | 0/10 | 0.73 / 0.96 / 1.09 | 0/10 (34.6) | 0.24 / 0.57 | 0.18 / 0.55 | 0.55 / 0.65 | 0.45 / 0.35 | 5.0 / 0.4 | 0/10 (1.83) | 10/10 | −209 / −227 | 170 / 153 | 0.46, 0.000 | 1.95 (j_spine) | 0.00 | 2.5 |
| **g3-flat-25** | 0/10 | 0.58 / **0.62** / 0.86 | 10/10 (21.3) | **0.23 / 0.11** | 0.16 / 0.04 | **0.85 / 0.62** | 0.15 / 0.38 | 4.0 / 7.4 | 0/10 (1.73) | 9/10 | −152 / −148 | 217 / 228 | 0.66, 0.020 | 2.24 (j_tail1) | 0.00 | 2.2 |

- **The flat share moved on the left, not the right.** When the left
  heel is down, the sole is flat in 0.85 of frames, against 0.55. On the
  right it is 0.62, against 0.65. The term pays what it was written for
  on one leg.
- **The heel share fell on the right**, 0.57 → 0.11, and stayed on the
  left, 0.24 → 0.23. Toe-off is 0.16 / 0.04, against 0.18 / 0.55. P1 is
  0/10 (`hock_down` worst-leg median 0.109).
- **Speed fell**, 0.96 → 0.62 m/s at the median, just over O8's 0.6 m/s
  line for a move-or-stop call. `straight` passes 10/10 (21.3°), where
  g2-heel5 at 25 failed 10/10.
- **Footfalls (`p2_lag.py`).** At 2.38 strides/s, the fore lag is 0.220
  of a cycle (about 92 ms) and the hind lag 0.158 (about 66 ms). The
  pairs land together only 0.03 and 0.10 of the time. No seed reads
  rotary: the fore paws step at 1.63 times the hind rate, and 114 of 183
  strides are unordered. Flight: 0.66 of strides, 0.020 s at the median.
- **Spine (`spine_foot.py`).** 24.4° in all per stride. It is at a stop
  0.22 of the time, against 0.05 for g2-heel5 at 25. The cable gap max is
  0.29°.
- **Torque.** The worst drive is `j_tail1` at 2.24 × rated, with peak
  margin 0.00.

## Decision

The screen's measure, the flat share of heel-down frames, moved on one
leg by its first checkpoint (+0.30) and held on the other (−0.03). Under
O8 that is not "clearly not moving", so g3-flat runs on to 50.
g2-heel5 gained 0.96 → 2.58 m/s between 25 and 50, so 25 does not settle
speed either. At 50, g3-flat is judged against g2-heel5-50:

- heels 0.23 / 0.11;
- flat 0.45 / 0.36;
- 2.58 m/s.

g3-flat is kept only if it beats g2-heel5-50 on the flat share and the
heel share at a speed within reach of it.

The left/right split is the policy's on g2-heel5 (`g2-heel5-50.md`,
mirror tests). The right heel's fall here is read the same way until a
mirror says otherwise.

Queued behind it: **g2-heel5c**. It warm-starts g2-heel5's final policy
(`a3d6bfb1`) for 50 iterations, 5 of them critic-only, at the default
learning rate, on heel5's own bundle (rebuilt from `leo-lag15.py` with
the stored parameters; `--expect-revision e46d3273`). The question:
does leo's heel return as the gait settles, as v07's did between 25
iterations and about 145?
