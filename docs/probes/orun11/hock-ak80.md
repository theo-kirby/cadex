# The AK80-9 hock (orun11 iteration 9)

Verified against source: 2026-10-19.

`hind-asymmetry.md` found the AK60-6 hock (9 N·m peak) buckling at peak on
the leg that lays down and the other leg reversing its foot. This build
replaces both hind hock drives with the CubeMars AK80-9 V3.0 KV100 (sold,
already in the catalog and on this cat's hips and spine: 22 N·m peak,
9 N·m rated, 490 g against 380 g). O3 allows a leg drive change when a
measurement names it.

## The change

On `orun11-cat`, a new parameter `hock_ak80` (default 1; 0 restores the
AK60-6 build) selects the hock drive. The geometry it moves:

- The AK80-9 is 38.5 mm deep against the AK60-6's 31 mm. The hock's
  output face, the metatarsus plate and the paw's clevis therefore move
  7.5 mm outboard, from y 90.5 to y 98. The pad (y 80–132) is unchanged,
  and so is the slot it carries for the plate.
- The AK80-9 case is 98 mm across against 79 mm. The hock case's floor
  contact sphere grows from 40 to 49 mm radius and moves to the case's
  middle, at y 78.75. The metatarsus sphere follows the plate to y 101.5.
- The rod lug's foot sat on the shin plate 40 mm from the hock axis. That
  point now falls inside the AK80's seat, so the first build was refused
  (`shin_l` fused to two solids). The foot moves to 60 mm along the shin.
  The AK80 has no rear boss through the shin plate, so the strap behind
  it is clear.
- The rod, horn, paw seat and turnbuckle trim (10°) are unchanged.

The MJCF hock row is now `forcerange -22 22`, `gainprm 60.16` (it was
±9 N·m, 30.08), the same on both legs. The model's mass goes from 31.40
to 31.57 kg.

## Verdicts

The build was accepted as **2c5a51e6** (project commit `dc91896`):

- fit **pass**: 0 failing of 7,626 pairs;
- mounting **pass**: 30 of 30;
- panels: 0 failing of 45, 12 advisory;
- sweep **pass**: 36 of 36 limited joints swept, no failing pair. The
  tail joints that hit the 90 s bound on 07a92830 and ca32a9b4 finished
  this time, so the build's own sweep verdict now passes.

## M1's static check, in the clip's stance pose

`clip_static.py` on 2c5a51e6's exported model and gallop task (the engine
regenerated the clip: rotary, 0.7 m at 2.4 Hz, duty 0.2, plantigrade):

| foot | push-off sample | sole pitch (deg, + toes-down) | hock case over floor (mm) |
|---|---|---|---|
| LH | 4 | +6.2 | 0.0 |
| RH | 5 | +5.1 | 0.0 |

**It passes on both legs**, against limits of 8° and 10 mm. The soles are
4.6° (LH) and 4.9° (RH) further from flat than on ca32a9b4 (+1.6°,
+0.2°). The larger case reaches the floor sooner and holds the hock about
9.5 mm higher. If a later build needs the margin back, a turnbuckle trim
of about −5° would recover it.

`foot_static.py` on the same model: the coupling is the rod's and has not
changed. The level-trunk check passes for shin pitch −18 to −28° (it was
−16 to −28°). At a 3× body-weight push up the toes the worst rod load is
**1,261 N** at hock −60°: an M5 pin at 32.1 MPa in double shear, and an
Euler margin of 2.2× (it was 1,254 N).

## The load the hock must hold (corrected)

The earlier estimate in `hind-asymmetry.md` put the hind pair's half of
the body weight on one paw. With each hind paw carrying a quarter, the
mean stance load is about 0.25 × 308 × 0.42 / 0.11 ≈ **295 N**. That is
an estimate from the duty factor; the traces carry no contact forces. At
the ~78 mm toe lever the AK80-9's 22 N·m holds about 280 N, about 95 % of
the estimate. The AK60-6 held about 115 N.

## trim1-s1, judged: the reason for the change

trim1-s1 trained on ca32a9b4 (AK60-6 hocks, rod trim 10°, the plantigrade
clip, rod1-s1's 17 terms), cold, 150 iterations, 4,755 s. Every checkpoint
was judged on the bundle's ADR-774 `gallop_spec`, seeds 1001–1010
(`judge.py`, then `summarize.py`; reports in
`orun11-cat/evaluations/trim1-s1-*`):

| checkpoint | pass | failing (median, passes) | top 2 s m/s min / med / max | hock down LH / RH | hock at toe-off LH / RH | hock stance height LH / RH mm | sole LH / RH deg | touchdown Hz LF RF LH RH | stride Hz | worst RMS/rated | peak ratio | falls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 0/10 | straight 27.8 (2/10); top_speed 802 (0/10); hock_down 0.103 (0/10); hock_at_toeoff 0 (0/10); no_tap 1.37 (0/10); every_stride 0.978 (7/10); overreach −417 (0/10) | 0.64 / 0.80 / 1.29 | 0.24 / 0.10 | 0.00 / 0.00 | 37 / 74 | 29 / 75 | 3.06 3.11 2.22 2.78 | 2.27 | 1.96 (j_hock_l) | 1.00 | 0 |
| 50 | 0/10 | top_speed 2.10e3 (0/10); hock_down 0.0523 (0/10); hock_at_toeoff 0 (0/10); no_tap 1.56 (0/10); overreach −117 (0/10) | 2.03 / 2.10 / 2.18 | 0.32 / 0.05 | 0.05 / 0.00 | 17 / 74 | 24 / 80 | 2.44 3.17 3.61 2.67 | 2.38 | 1.92 (j_spine) | 1.00 | 0 |
| 75 | 0/10 | top_speed 2.78e3 (0/10); hock_down 0 (0/10); hock_at_toeoff 0 (0/10); no_tap 1.14 (4/10) | 2.76 / 2.78 / 2.82 | 0.49 / 0.00 | 0.65 / 0.00 | 1 / 83 | 9 / 82 | 2.44 2.72 2.44 2.44 | 2.38 | 2.20 (j_spine) | 1.00 | 0 |
| 100 | 0/10 | top_speed 3.05e3 (0/10); hock_down 0 (0/10); hock_at_toeoff 0 (0/10); no_tap 1.61 (0/10) | 3.02 / 3.05 / 3.09 | 0.53 / 0.00 | 0.86 / 0.00 | 1 / 84 | 12 / 80 | 2.44 3.83 2.44 2.33 | 2.38 | 2.15 (j_spine) | 1.00 | 0 |
| 125 | 0/10 | top_speed 3.37e3 (0/10); hock_down 0 (0/10); hock_at_toeoff 0 (0/10); no_tap 1.31 (2/10) | 3.21 / 3.37 / 3.39 | 0.53 / 0.00 | 0.48 / 0.00 | 1 / 84 | 14 / 77 | 2.44 3.11 2.39 2.33 | 2.38 | 2.17 (j_spine) | 1.00 | 0 |
| best (149) | 0/10 | top_speed 3.47e3 (0/10); hock_down 0 (0/10); hock_at_toeoff 0 (0/10); no_tap 1.96 (0/10) | 3.45 / 3.47 / 3.56 | 0.51 / 0.00 | 0.28 / 0.00 | 1 / 87 | 15 / 75 | 2.44 4.67 2.33 2.44 | 2.38 | 2.05 (j_spine) | 1.00 | 0 |

The trim made the clip's push-off flat, but the policy did not follow it.
As on heel1-s1 and rod1-s1, one hind (here the LH) lays its hock down for
about half its stance, and the other (RH) never does. The RH case stands
74–87 mm up at every checkpoint. P1 fails on the RH alone, so the hock
drive is the next variable, as `hind-asymmetry.md` proposed.

## hock80-s1

The screen on 2c5a51e6 matches trim1-s1 in everything but the hock drive:
the same clip, the same 17 terms, cold, 150 iterations, seed 0, 8,192
envs, and a 7,200 s budget.
The first ten iterations took 440 s of trainer wall time (514 s from
launch). The trainer's ETA at iteration 10 was 5,570 s more, so the
budget leaves about 1,100 s of margin (O8).
