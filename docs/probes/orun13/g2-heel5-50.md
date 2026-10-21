# orun13 B1 / O5: g2-heel5 at 50 gallops at 2.58 m/s on its toes; the left/right split is the policy's

Verified against source: 2026-10-20. Frozen evidence (orun13, iteration 5).

## g2-heel5 at 50 (`gallop.cxpolicy`, sha256 `a3d6bfb1`)

g2-heel5 (`g2-heel5-25.md`) ran to 50 iterations, cold, 4096 envs, seed 0,
on revision `e46d3273`, from 21:49 to 22:37: **about 58 s per iteration**,
checkpoints included. The trainer read 31.38 reward/step at iteration 49,
up from 17.23 at 24 and still rising about 0.5 an iteration. It was judged
as `g2-heel5-25.md` was, on the bundle's `gallop_spec`, seeds 1001–1010, on
the CPU (`orun11/judge.py`, `orun12/legs.py`, `orun13/p2_lag.py`,
`orun13/spine_foot.py`, `orun12/trace_check.py`; the trace check is in
`~/orun13-logs/trace-g2-heel5-50.txt`).

| evaluation | pass | top 2 s m/s min / med / max | straight (max heading °) | hock_down LH / RH | at toe-off LH / RH | no_tap | every_stride | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel5c-s1-final (orun12, v07) | 0/10 | 2.81 / 2.91 / 3.01 | 10/10 (3.4) | 0.60 / 0.61 | 1.00 / 1.00 | 10/10 | 10/10 | 279 / 286 | 1168 / 1169 | 2.33 / 2.39 | 1.00, 0.260 s | 2.01 (j_spine) | 0.00 | 2.9 |
| g2-heel5-25 | 0/10 | 0.73 / 0.96 / 1.09 | 0/10 (34.6) | 0.24 / 0.57 | 0.18 / 0.55 | 0/10 | 10/10 | −209 / −227 | 170 / 153 | 2.78 / 3.78 | 0.46, 0.000 s | 1.95 (j_spine) | 0.00 | 2.5 |
| **g2-heel5-50** | 0/10 | **2.50 / 2.58 / 2.73** | **10/10 (15.3)** | 0.23 / 0.11 | 0.19 / 0.14 | 0/10 (1.59) | 10/10 | 63 / −204 | 961 / 752 | 2.78 / 3.61 | **1.00, 0.150 s** | 1.89 (j_spine) | 0.00 | 3.9 |
| g2-heel5-50 mirror | 0/10 | 2.33 / 2.53 / 2.59 | 8/10 (18.5) | 0.12 / 0.25 | 0.13 / 0.22 | 2/10 (1.18) | 3/10 | −117 / 74 | 751 / 969 | 3.61 / 2.81 | 0.99, 0.120 s | 1.90 (j_spine) | 0.00 | 4.0 |

### B1 against heel5c-s1

- **Speed: 2.58 m/s at the median**, 89% of heel5c-s1's 2.91 after 50
  cold iterations (heel5c-s1 had about 145 in all). heel5-s1 on v07 was
  at 1.16 at 25.
- **A gallop's shape now.** Every stride has a flight phase, 0.15 s at
  the median (heel5c-s1: 0.26 s). The stride is 961 / 752 mm, against
  heel5c's 1168. `straight` passes 10/10 (15.3°, down from 34.6° at 25).
  `every_stride` passes 10/10. `completes` and `upright` pass 9/10:
  seed 1008 fails at 19.3° median tilt.
- **P1 0/10, and worse than at 25.** The engine has the heels down 0.23 /
  0.11 of stance, and 0.19 / 0.14 at toe-off. heel5c-s1 had 0.60 / 0.61
  and 1.00 / 1.00. In the faster gait the policy went back onto its toes.
  The heel's height in stance is 8 / 12 mm. When the heel is down, the
  foot is flat in 0.45 / 0.36 of frames (`spine_foot.py`) and toes-up in
  0.55 / 0.64. At 25 those were 0.55 / 0.65 flat.
- **`no_tap` 0/10** (1.59 fore touchdowns per hind stride). The fore paws
  step at 1.59 times the hind rate. `overreach` passes 3/10 (median
  −229 mm, LH +63 mm, RH −204 mm).
- **Footfalls (`p2_lag.py`), O3.** At 2.90 strides/s (345 ms a cycle),
  the fore lag is 0.051 of a cycle (18 ms) and the hind lag 0.100 (34 ms).
  Both are under O3's 40 ms. The fore pair lands together 0.44 of the
  time, the hinds 0.24. No seed reads rotary. Of 252 strides, 84 are
  tied and 123 unordered. The fore paws tap, so most strides have no
  clean order.
- **Torque, O6.** The worst drive is `j_spine` at 1.89 × rated RMS, with
  peak margin 0.00. It sits at peak, as it did on v07 (2.01).

B1's four set-up items were met in iterations 1–4: the bundle builds,
the stand is re-measured, the clip's `j_spine2` follows `j_spine` and
seconds per iteration are timed. Its first screen is now judged at 25 and
50 and reported against heel5c-s1 above. **B1 has its evidence.** The
first screen moves and gallops, but it does not hold a heel.

## Spine (`spine_foot.py`), O4

| | j_spine min / max | range per stride (sum of both joints) | at a stop | cable gap max | peak flexion / extension, phase of the LH stride |
|---|---|---|---|---|---|
| g2-heel5-25 | about −26 / +2 | 19.8° | 0.05 | 0.40° | 0.26–0.50 / 0.33–0.75 |
| **g2-heel5-50** | −18.4 to −22.7 / +15.5 to +21.0 | **36.6°** | **0.00** | 0.72° | 0.64–0.84 / 0.33–0.37 |

The spine now flexes and extends through every stride, 36.6° in all at the
median (each joint 16–20°). It reaches neither ±50° stop: 0.00 of frames
are at a stop on every seed. orun7's single spine sat at its ±25° clamp
about 60% of a bound. The cable holds `j_spine2` within 0.72° of
`j_spine`, under O9's 1°, with a closure median of 0.061°.

## Real meshes and loops (`trace_check.py`), O9

- **Front rod loops open to 3.86 / 3.46 mm** (`j_frodbot_l` / `_r`), over
  O9's 2 mm bar. The medians are 0.22 / 0.25 mm. At 25 the worst was
  2.5 mm. The hind rods hold, at 1.74 / 1.64 mm.
- **The hind paws strike the fore elbow drives.** 18 pairs that are apart
  in the build pose go deeper than 5 mm:
  - `c_paw_hl × c_qdd_elbow_l` 27.4 mm (seed 1008, 3 frames);
  - `c_paw_hr × c_qdd_elbow_r` 20.6 mm (31 frames on 8 seeds);
  - hind paw into the humerus or its panel, 7.3–8.1 mm;
  - chest frame against the wrist drives and forearms, 5.2–6.6 mm.

  This is the overreach clash O4 foresaw. A hind paw reaches the fore
  leg as the spine flexes, and nothing in the model collides there.
- Front paw meshes sit 16–19 mm under the floor (the 18 mm mesh offset of
  `g1-s1-25.md`).

## The mirror tests (O5), run before blaming the model or a reward

```
pixi run python docs/probes/orun12/mirror.py RUN/train/cat_model-model.xml
pixi run python docs/probes/orun12/mirror_policy.py RUN/train/cat_model-model.xml \
    RUN/train/gallop.cxpolicy RUN/train/gallop.mirror-50.cxpolicy
PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py ~/cadex-projects/leo RUN/train \
    RUN/train/gallop.mirror-50.cxpolicy g2-heel5-50m
```

Both scripts run on leo unchanged.

- **The model mirrors.** `mirror.py` runs 458 left/right checks and finds
  0 names without a partner. All 13 joint, 13 geom, 9 actuator and 2
  equality pairs agree within 1%, 1 mm and 0.5°. Of the 47 body pairs,
  27 values differ, all on cosmetic panels:
  - the tail, neck-side and muzzle panels, 0.5–1.8 g lighter on the
    right, with their centres of mass 0.6–5 mm off;
  - the camera's centre of mass, 2 mm.

  In all this is under 10 g, on bodies the legs do not carry.
- **The policy mirrors.** `j_spine` and `j_spine2` keep sign +1;
  `j_spine_yaw` and the tail and haa joints flip. The engine's forward
  pass on the mirrored weights equals M_a π(M_o o) to 3.6e-14 on 32
  witness samples.
- **Every handed measure swaps sides under the mirror:**

| measure | g2-heel5-50 LH / RH | mirror LH / RH |
|---|---|---|
| engine heel share | 0.23 / 0.11 | 0.12 / 0.25 |
| heel at toe-off | 0.19 / 0.14 | 0.13 / 0.22 |
| heel height mm | 8 / 12 | 12 / 8 |
| stride mm | 961 / 752 | 751 / 969 |
| touchdown Hz | 2.78 / 3.61 | 3.61 / 2.81 |
| overreach mm | 63 / −204 | −117 / 74 |
| mean lateral speed, mm/s, per seed | −50, −115, −99, −30, −24, −40, +9, −53, −22, −52 | +30, +28, +41, +39, −62, +34, +84, +73, +28, +43 |

The veer swaps too. At 50, nine of ten seeds drift right at 22–115 mm/s.
The mirror drifts left on nine of ten. At 25 the drift was left
(+3 to +36 mm/s on nine seeds). **The left/right difference, in the heel
and in the veer, is a handed gait the policy learned, not the model.**
This matches orun12 (`orun12/mirror-policy.md`). It needs no hardware or
reward explanation.

The mirror is not an exact image (`every_stride` 3/10 against 10/10,
`no_tap` 1.18 against 1.59). The engine's starting state and the clip are
not mirrored: the clip leads with RH and LF (`clip_lag.md`), and the
mirrored policy reads the same clip phase while it moves its legs the
other way round. So it runs a mirror gait against an unmirrored start.
This does not touch the conclusion: the sides swap on every measure that
was handed.

## What this says for P1

At 50 iterations `heel_pitch` alone does not hold leo's heel once the gait
speeds up. On v07 the heel came later: heel5-s1 had 0.13 / 0.16 at 25,
0.37 / 0.36 at 100, and heel5c-s1 0.60 / 0.61 after about 145. Its band pays a toes-up foot too (`g2-heel5-25.md`). At
2.58 m/s the policy kept the band's reward on its toes. g3-flat, queued
behind this run on revision `a280b070`, pays only the flat sole. It is
the screen for that.
