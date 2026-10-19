# orun11: the hind leg's range for a plantigrade stance, and rod1-s1 judged

Verified against source: 2026-10-18. Frozen evidence (orun11, iteration 5).

## rod1-s1, checkpoint by checkpoint

rod1-s1 is the first screen on the built rod foot: orun11-cat 4cd04aaf,
trained cold for 150 iterations (4,697 s on the GPU) on eq1-s1's 17-term
task and tiptoe gallop clip (0.7 m, 2.4 Hz). Every checkpoint was judged on
the bundle's own ADR-774 `gallop_spec`, seeds 1001–1010, with the engine's
evaluation on the CPU:

```
PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
  ~/cadex-projects/orun11-cat RUN/train RUN/train/gallop.<checkpoint>.cxpolicy rod1-s1-<checkpoint>
```

The reports are `orun11-cat/evaluations/rod1-s1-<checkpoint>/evaluation.json`.
The evaluation reads the model and task from the run's bundle (4cd04aaf).
The `accepted_revision` field names the project's head when it was judged,
which is the range change below.

| checkpoint | pass | failing (median, seeds passing) | top 2 s m/s min / med / max | hock down LH / RH | hock at toe-off LH / RH | hock stance height LH / RH mm | sole LH / RH deg | touchdown Hz LF RF LH RH | stride Hz | worst RMS/rated | peak ratio | stride | rod closure LH, RH: median / max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 0/10 | straight 25.4 (4), top_speed 693, hock_down 0.08, hock_at_toeoff 0, no_tap 1.81, overreach −461 | 0.51 / 0.69 / 0.85 | 0.14 / 0.08 | 0 / 0 | 66 / 71 | 27 / 63 | 4.22 3.17 2.44 3.00 | 2.27 | 1.86 (j_hock_l) | 1.00 | 0.18 m | 0.07 / 2.4, 0.06 / 2.6 |
| 50 | 0/10 | top_speed 1590, hock_down 0.15, hock_at_toeoff 0, no_tap 1.46, overreach −194 | 1.54 / 1.59 / 1.75 | 0.15 / 0.16 | 0 / 0 | 70 / 68 | 53 / 59 | 2.44 2.56 3.56 3.11 | 2.38 | 1.79 (j_hock_r) | 1.00 | 0.61 m | 0.11 / 4.1, 0.09 / 4.7 |
| 75 | 0/10 | top_speed 2370, hock_down 0.13, hock_at_toeoff 0, no_tap 1.53, every_stride (8), overreach 7 (5) | 2.34 / 2.37 / 2.39 | 0.20 / 0.14 | 0.03 / 0.03 | 46 / 77 | 28 / 60 | 2.44 3.22 3.89 3.33 | 2.41 | 1.89 (j_spine) | 1.00 | 0.95 m | 0.13 / 3.3, 0.13 / 5.2 |
| 100 | 0/10 | top_speed 2590, hock_down 0.04, hock_at_toeoff 0, no_tap 1.36 | 2.55 / 2.59 / 2.62 | 0.21 / 0.04 | 0 / 0.04 | 9 / 85 | 16 / 63 | 2.44 2.72 3.28 2.83 | 2.50 | 1.91 (j_spine) | 1.00 | 1.05 m | 0.14 / 3.2, 0.15 / 3.7 |
| 125 | 0/10 | top_speed 2930, hock_down 0.17, hock_at_toeoff 0, no_tap 1.59 | 2.92 / 2.93 / 2.96 | 0.17 / 0.24 | 0 / 0.27 | 64 / 75 | 35 / 44 | 2.44 3.78 2.78 2.44 | 2.38 | 1.93 (j_spine) | 1.00 | 1.20 m | 0.13 / 3.4, 0.14 / 3.9 |
| best (149) | 0/10 | top_speed 3190, hock_down 0.06, hock_at_toeoff 0, no_tap 1.26 | 3.14 / **3.19** / **3.20** | 0.06 / **0.45** | 0 / **0.57** | 77 / **3** | 55 / 18 | 2.44 3.00 2.50 2.44 | 2.38 | 1.94 (j_spine) | 1.00 | 1.31 m | 0.13 / 2.9, 0.17 / 3.5 |
| final (150) | 0/10 | the same as best, seed for seed | 3.14 / 3.19 / 3.20 | 0.06 / 0.45 | 0 / 0.57 | 77 / 3 | 55 / 18 | 2.44 3.00 2.50 2.44 | 2.38 | 1.94 (j_spine) | 1.00 | 1.31 m | 0.13 / 2.9, 0.17 / 3.5 |

Medians over 10 seeds, columns as in `eq1-s1-judged.md`. The predicates
take the worse leg. No seed fell. The run started cold.

**What it shows.**

- **One hind leg lays down, now the right.** At the end the right hock
  case is down 45% of stance (8 of 10 seeds at 0.40 or more: 1004 has
  0.38, 1007 has 0.37). It is down at 57% of toe-offs, at a median stance
  height of 3 mm. The left stays up: 6% of stance, 77 mm, sole 55°
  toes-down. eq1-s1 had it the other way round (left 19%, right never).
  On the same tiptoe clip, the built rod gives one leg the pose, and which
  leg it is changes from run to run.
- **The right fore taps** at 3.0 Hz against a 2.38 Hz stride (no_tap
  1.26). That is less than eq1-s1's 4.56 Hz.
- **Speed** 3.19 m/s, as eq1-s1's 3.17, on the clip's clock, with a 1.31 m
  stride and 0.14 s of flight. The worst drive is the spine at 1.94×
  rated RMS, with a peak margin of 0.
- **The built rod's loop holds in the physics**: the connect's error is
  0.13–0.17 mm median, 2.9–3.5 mm at worst.

## The range a plantigrade clip needs (O3)

`hind_range.py` runs `plantigrade_reach.py`'s 108-clip grid on rod1-s1's
exported model with the hind stops widened:

```
pixi run python docs/probes/orun11/hind_range.py <cat_model-model.xml>
```

Hip flexion (knee forward) and knee flexion (shin folded back) are the
directions the crouched, heel-down stance uses. ADR-776's note called them
"extension" and "range".

| added to 4cd04aaf's stops | reachable of 108 | at 0.7 m |
|---|---|---|
| none (hip −30..+40, knee −40..+50) | 0 | 0 |
| hip flexion +15, knee flexion +20 | 4 | 1 |
| the same, and knee extension +15 | 5 | 1 |
| hip flexion +20, knee flexion +25, knee extension +15 | 8 | 2 |

The second row is the smallest change that gives a clip at the training
stride: 0.7 m, duty 0.2, the hock case down from half the stance to
toe-off, the trunk 60 mm down, 6° nose-up, the hind stance 120 mm forward.
It runs the left hip to −45..+3°, knee −60..+30° and hock −39..+12°. The
right mirrors it. **That clip reaches the new stops**, so it has no margin.
With those stops, 47 of the other rows still bind at the left knee with
the heel down.

## The change on orun11-cat

The left stops go from hip −30..+40 to **−45..+40** and knee −40..+50 to
**−60..+50**, mirrored on the right. They were cleared on the exact
geometry. Each collision was found by rotating the exported BREPs about
the joint axis in `FreeCADCmd` and reading the common solid's tessellated
bounds. Each fix was tested the same way before its rebuild:

- **Hip flexion past 38°.** The thigh and knee drive meet the pelvis's
  front former, which is clipped from z 395 so the knees pass under it.
  It is now clipped from **z 405**.
- **Hip flexion past 40°.** The thigh nicks the loin panel's rear foot,
  at x −140..−131 and z 412..428. Each loin panel gets a **notch** at
  x −141..−125, z 411..433.
- **Hip flexion past 40°, at the abduction drive.** The thigh former's
  inboard edge, at y 78–87, meets the AK70-10 abduction (HAA) drive.
  The former is **notched** there: x −182..−160, y 70..91, z 316..346.
- **Knee flexion past 41°.** The shin's former and outer panel fold into
  the thigh former's rear arc, at x −263..−240 and z 267..298. That arc
  is **notched** inboard of the thigh panel: x −270..−232, y 70..121,
  z 260..304. The project's `former_` fuses the whole hoop back over a
  `keep_out`, which only trims the web, so the notches are cut from the
  finished thigh frame.

The thigh panel and the formers' outboard arcs that carry it are
unchanged. No drive, link or mounting changes.

**Revisions.**

- **64da27fd:** the stops alone. The sweep failed on 12 pairs: thigh into
  shin and the shin panel, the pelvis frame and loin panel into the
  thigh, and the HAA drive into the thigh. Panels failed 4 of 45.
- **1cb71c3e:** adds the former clip and the loin notch, and a thigh
  `keep_out` that did not take, for the reason above. The knee pairs and
  the HAA pair were left.
- **A refused attempt:** the notches cut through the clip split the hoop
  into two solids.
- **d6fe5680 (accepted):** the notches cut from the frame.

**Verdicts on d6fe5680:**

- fit **pass**: 7,626 pairs, none failing;
- mounting **pass**: 30 of 30 purchased parts held;
- panels: 0 failing of 45, the same 12 advisory `egg` rows;
- sweep **incomplete**: 24 of 36 limited joints swept, **no failing
  pair**. That includes the hips at −45..+40 and the knees at −60..+50.
  The 12 tail joints (`j_tail1`–`j_tail5p` and four more) hit the
  engine's 90 s per-joint sweep bound. The pelvis is their parent and its
  geometry changed, so their pairs could not come from the fit cache, as
  they did on 4cd04aaf (36 of 36). Every change since 4cd04aaf takes
  material away (the former clip, a notch in each loin panel and two in each
  thigh former), and none of it is near the tail, at x ≤ −306. So the tail
  sweep that passed on 4cd04aaf still bounds the tail. No engine verdict
  says so yet.

**On d6fe5680's own export** (`cat_model-model.xml` from the accepted
attempt), the stops read hip −45..+40 and knee −60..+50 (left), mirrored on
the right. `plantigrade_reach.py`'s grid finds the same 4 of 108 reachable
clips, the 0.7 m one among them.

**What it leaves.** A plantigrade clip at the training stride now exists
inside the joint limits, crouched by 60 mm. ADR-776's `heels` still reach
the generator only from a probe, not through `assembly.gait`. M1's static
check has not been rerun in that clip's stance pose. The clip sits on the
new hip and knee stops. If a policy needs margin, the next step is a
longer femur or shin. The 47 rows still bound at the knee with the heel
down point the same way.
