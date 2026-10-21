# orun13 P1: g4-peak at 50 lays both soles flat, at a cost in speed

Verified against source: 2026-10-21. Frozen evidence (orun13, iteration 8).

## g4-peak at 50 (`gallop.cxpolicy`, sha256 `02f16f15`)

g4-peak (`g4-peak-25.md`) is g3-flat's task with `heel_pitch` peaked on
the flat sole. It ran on to 50 iterations, cold, 4096 envs, seed 0, on
revision `b4680361`, from 23:52 to 00:38. The trainer read 30.76
reward/step at iteration 49, still rising about 0.4 an iteration. It was
judged as `g3-flat-50.md` was, on the bundle's `gallop_spec`, seeds
1001–1010, on the CPU (`orun11/judge.py`, evaluation `g4-peak-50`;
`orun12/legs.py`, `orun13/spine_foot.py`, `orun13/p2_lag.py`, and the new
`orun13/foot_frames.py`). The comparison is g3-flat at 50: the same model
XML and the same task except for the band.

| evaluation | pass | top 2 s m/s min / med / max | straight (°) | hock_down LH / RH | at toe-off LH / RH | heel-down frames flat LH / RH | toes-up LH / RH | heel mm in stance LH / RH | no_tap | every_stride | overreach | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g3-flat-50 | 0/10 | 2.75 / 2.80 / 2.88 | 10/10 (15.8) | 0.39 / 0.11 | 0.50 / 0.24 | 0.68 / 0.13 | 0.32 / 0.87 | 2 / 12 | 0/10 (1.21) | 10/10 | 10/10 (516) | 572 / 516 | 2.89 / 2.67 | 1.00, 0.220 | 1.82 (j_spine) | 0.00 | 4.5 |
| **g4-peak-50** | 0/10 | 2.40 / **2.43** / 2.49 | 10/10 (19.8) | **0.44 / 0.22** | 0.43 / 0.21 | **0.91 / 0.94** | **0.09 / 0.06** | 2 / 14 | 0/10 (1.68) | 10/10 | 10/10 (141) | 416 / 141 | 2.33 / **4.00** | 1.00, 0.160 | 1.80 (j_spine) | 0.00 | 3.8 |

- **The toes-up foot is gone on both legs.** When a heel is down, the sole
  is flat in 0.91 (LH) and 0.94 (RH) of frames, against 0.68 and 0.13.
  Toes-up falls from 0.87 to 0.06 on the right and from 0.32 to 0.09 on
  the left. The peaked band is the lever that did it: the ≤10° band paid
  the toes-up sole in full (`heel_expr.py`), and this one does not.
- **Both heels rose.** The engine's heel share of stance is 0.44 / 0.22
  (from 0.39 / 0.11). P1 is still 0/10: `hock_down` worst-leg median
  0.218, `hock_at_toeoff` 0.214.
- **The right hind is now a toe stance, and it taps.** Its heel sits
  14 mm up at the median in stance, and the RH paw touches down
  4.00 times a second against LH's 2.33 (a 42% spread). `foot_frames.py`
  on seed 1001 shows why. The RH lands flat for one frame, rolls onto its
  toes, and makes a separate one- or two-frame toe touch between
  stances. The LH lands flat for 4–5 frames and then rolls onto its toes
  to push off.
- **Slower.** 2.43 m/s at the median, against 2.80. The strides are 978 /
  868 mm, against 1130 / 1121, and the RH overreach is 141 mm, against
  516. `no_tap` worsened to 1.68 (bar 1.10).
- **Footfalls (`p2_lag.py`, O3).** At 2.50 strides/s (400 ms a cycle):
  - the fore lag is 0.128 of a cycle (about 51 ms), which passes O3's
    40 ms;
  - the hind lag is 0.045 (about 18 ms), and the hind pair lands
    together 0.64 of the time. g3-flat had it the other way round (fore
    21 ms, hind 72 ms).
  - 73 of 80 ordered strides are rotary, all of them RH first, but the
    tied strides (94) keep every seed from reading rotary.
- **Spine (`spine_foot.py`, O4).**
  - 34.2° a stride (sum of both joints), against 37.7°.
  - j_spine runs −16.5..−24.5° to +7.2..+16.0°, with 0.00 of frames at a
    stop.
  - The cable gap is at most 0.45° (O9: 1°).
- **Torque (O6).** The worst drive is `j_spine` at 1.80 × rated RMS,
  with peak margin 0.00.

### Per-leg trace frames (`foot_frames.py`, seed 1001, 1.0–2.0 s)

`F` is flat (heel and toes down), `U` toes-up, `T` toe stance (heel up),
and `.` is off the floor. There is one letter per 20 ms frame.

```
g3-flat-50  LH  TT..............UFFFFTT..............UTUFFTT.......
            RH  TT...............U...UTTT..............UUUUTTT.....
g4-peak-50  LH  T...........FFFFFTTTT............FFFFTTT...........
            RH  ..TTT.......FTTT......TT...........FTT.....T.......
```

Over the whole seed (on-ground frames, from 1 s on):

| | flat | toes-up | toe stance |
|---|---|---|---|
| g3-flat-50 LH | 0.30 | 0.18 | 0.52 |
| g3-flat-50 RH | 0.06 | 0.42 | 0.52 |
| g4-peak-50 LH | 0.50 | 0.05 | 0.45 |
| g4-peak-50 RH | 0.21 | 0.02 | 0.77 |

The stills `g4-peak-50-hl-flat.png` (from the left) and
`g4-peak-50-hr-flat.png` (from the right) render the frame at 1.24 s on
seed 1001 with `orun12/render_frame.py`. Both feet are in their first
flat frame, with heel and toes at −1.8 / −2.2 mm (LH) and −0.2 / −0.1 mm
(RH). The metatarsus, heel, paw and claws are in the accent colour.

## Decision

The keep rule, from `g4-peak-25.md`, had three parts:

| part | needed | result | met? |
|---|---|---|---|
| RH toes-up | well below 0.87 | 0.06 | yes |
| heel shares | at least 0.39 / 0.11 | 0.44 / 0.22 | yes |
| speed | near 2.80 m/s | 2.43 | no: 13% slower |

**g4-peak is kept for P1, the higher-ranked criterion**, and the speed
cost is written down here. The peaked band is the only lever this run
has found that removes O2's toes-up foot, and the question policy ranks
P1 above S1. The ≤10° band is not restored.

**The mirror augmentation the critic proposed is not built.** It was
conditional on the toes-up habit surviving, and that habit is gone on
both legs. There is also a reason it would not reach what is left. The
clip is chiral: RH lands 0.15 of a cycle before LH (`clip_lag.md`).
Under the clip, RH stands while the spine is flexed (q_spine −5.5..+2.1°)
and LH while it extends (0..+6.5°) (`heel_expr.py`'s sample table). The
mirrored state of a visited one is the left-lead gallop, which the clip
never asks for. A symmetric-minibatch loss would therefore constrain the
policy only on states it never visits, and would not tie the leading
hind's stance to the trailing one's. What is left is the leading hind's
toe stance and tap.

**Next screen (launched at 00:40): `g4-peakc`.** It is g4-peak warm,
with 50 more iterations (5 critic-only), on the same task and revision
`b4680361`, at 4096 envs and the default learning rate, as `g2-heel5c`
was. The trainer's curve was still climbing at 49. Judged at 25, it is
kept only if:
- toes-up stays at or below 0.10 on each leg;
- both heel shares hold at or above 0.44 / 0.22;
- the RH touchdown rate falls towards LH's, or the speed recovers
  towards 2.80.

`g2-heel5c` lost its heels on the same continuation (0.23 / 0.11 to
0.10 / 0.05 at 25), so a fall at 25 stops it as a dead end.
