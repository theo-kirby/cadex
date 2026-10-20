# orun12 P1 (O2a): heel5-s1 at 75 and 100

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 12).

## heel5-s1 at 75 and 100

heel5-s1 (`44411418`, digest `e4327e17`; `heel5-pitch.md`, `heel5-judge.md`)
is heel3-s1's task with `heel_pitch` (weight 10) in place of `track_ankle`:
cold, 4096 envs, seed 0. It finished all 100 iterations (exit 0, 7,033 s
wall, best reward/step 39.5 at iteration 99, still rising). Its
iteration-75 checkpoint and its final policy (`gallop.cxpolicy`, iteration
100, sha256 `42494591`) were judged on the bundle's `gallop_spec`, seeds
1001–1010, on the CPU:

```
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.000075.cxpolicy heel5-s1-75
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.cxpolicy heel5-s1-100
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/heel5-s1-{25,50,75,100}
python3 docs/probes/orun12/stance_pose.py RUN/train/cat_model-model.xml \
    ~/cadex-projects/feline-v07/evaluations/heel5-s1-{75,100}
```

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | metatarsus pitch LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | stride mm LH / RH | overreach mm LH / RH | flight s | no_tap | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 0/10 | 0.13 / 0.16 | 0.06 / 0.06 | 14 / 12 | 23 / 22 | 1.10 / 1.16 / 1.86 | 2.56 / 2.44 | 405 / 424 | −81 / −142 | 0.22 | 4/10 (1.11) | 1.43 (j_spine) | 0.00 | 3.8 |
| 50 | 0/10 | 0.19 / 0.18 | 0.32 / 0.09 | 11 / 8 | 18 / 18 | 2.90 / 2.99 / 3.11 | 2.44 / 2.44 | 1189 / 1203 | 339 / 314 | 0.18 | 0/10 (1.62) | 2.11 (j_spine) | 0.00 | 2.8 |
| 75 | 0/10 | 0.15 / 0.20 | 0.37 / 0.24 | 13 / 7 | 19 / 17 | 3.02 / 3.08 / 3.17 | 2.33 / 2.33 | 1247 / 1255 | 409 / 390 | 0.22 | 0/10 (1.45) | 2.16 (j_spine) | 0.00 | 3.0 |
| **100** | 0/10 | **0.37 / 0.36** | **0.84 / 0.57** | **3 / 2** | **11 / 10** | 3.17 / 3.21 / 3.25 | 2.33 / 2.44 | 1306 / 1305 | 391 / 366 | 0.24 | 7/10 (1.03) | 2.12 (j_spine) | 0.00 | 3.3 |

Heel shares, toe-off shares, heights, stride and touchdown rate are
`legs.py`'s medians over seeds of the engine's `detail.heels` and contact
metrics. The metatarsus pitch is `stance_pose.py`'s median over the
engine's own stance frames (its frame counts equal the engine's: 617 / 814
at 75, 718 / 857 at 100).

Per seed at 100 (heel down share LH / RH, at toe-off LH / RH):

| seed | 1001 | 1002 | 1003 | 1004 | 1005 | 1006 | 1007 | 1008 | 1009 | 1010 |
|---|---|---|---|---|---|---|---|---|---|---|
| share | 0.40 / 0.32 | 0.37 / 0.33 | 0.40 / 0.38 | 0.37 / 0.34 | 0.38 / 0.36 | 0.36 / 0.30 | 0.36 / 0.43 | 0.37 / 0.42 | 0.38 / 0.36 | 0.37 / 0.38 |
| toe-off | 0.90 / 0.43 | 0.81 / 0.52 | 0.90 / 0.67 | 0.90 / 0.48 | 0.86 / 0.64 | 0.77 / 0.45 | 0.82 / 0.82 | 0.82 / 0.68 | 0.95 / 0.55 | 0.82 / 0.59 |

At 100: completes, no_fall, upright, straight, every_stride and overreach
pass on 10/10 (overreach median 366 mm), and no_tap passes on 7/10 (median
1.03, its best on any v07 policy). There are no falls, and every stride has
a flight phase (0.24 s). Footfall is rotary on 145 of 181 ordered strides.

**The heel nearly reaches the bar at 100, on both legs alike.**

- `hock_down` still fails on every seed. It asks for 0.40 on the worse leg
  of each seed, and the median of the worse leg is 0.36. Every seed's
  worse leg sits between 0.30 and 0.38, and no single leg is under 0.30.
- `hock_at_toeoff` asks for every toe-off with the heel down (1.0). The
  left is at 0.84 and the right at 0.57. This is now the further of the
  two bars.
- The share was flat from 50 to 75 (0.19/0.18 → 0.15/0.20) and then
  doubled from 75 to 100. The reward was still rising at 99. The curve
  climbs, so by O7 the run is worth extending.
- The legs are alike. The share spread is 3% (Q1's bar is 20%), the stride
  spread 0%, and the touchdown spread 5%. Only the toe-off share differs:
  0.84 against 0.57.

**What changed between 75 and 100 is the metatarsus pitch.** The stance
metatarsus fell from 19 / 17° to 11 / 10°. Across both legs' stance frames,
the heel is down on 0.76 of frames at 5–10° and on 0.02 at 10–15°. At 100
there are 754 frames at 5–10°, against 384 at 75. The binding limit is the
same as at 50: the heel lands only when the metatarsus is under about 10°.
The policy is learning to get there, through what `heel_pitch` pays, which
is 0.72 / 0.73 of full in stance (0.60 / 0.64 at 75).

**Speed did not cost the heel.** The top 2 s speed rose from 2.99 to
3.21 m/s while the heel share doubled. The speed command is still capped at
2 m/s (heel3-s1's task), so O2a's rule holds: speed stays second until P1
passes.

Torque (O4): the worst drive is `j_spine` at 2.12× rated RMS. One drive
reaches its clamp on every seed (peak margin 0.00), as on every v07 policy.
The loop gap is 3.3 mm, still over O9's 2 mm. It stays a Q2 item and is not
chased before P1.

## What follows

heel5-s1-100 is the closest policy to P1 so far. Two steps follow:

- extend it while it climbs;
- then carry `heel_pitch` onto the flat clip.

heel6-s1 (the flat clip without `heel_pitch`, `heel6-flat.md`) launched
when heel5-s1 ended, at 01:54:57. It is a 2-hour screen. It answers whether
the clip alone moves the heel, which the combined screen needs to know.

### heel6-s1's first ten iterations (O8)

heel6-s1 started at 01:54:57 and logged iteration 10 at about 02:10:50,
953 s in. heel5-s1, on the same model and envs, took 886 s. At heel5-s1's
67 s an iteration after the first compile, 100 iterations come to about
7,100–7,400 s, inside `budget_s` 9,700 with more than O8's 20% to spare.
Its reward per step falls from 19.8 to 13.0 over the first ten iterations
while its episodes lengthen (23 → 134 steps), as on heel5-s1's start.
