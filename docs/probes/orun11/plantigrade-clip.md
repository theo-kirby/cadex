# orun11 rung 8: the plantigrade clip on the script surface, and heel1-s1

Verified against source: 2026-10-18. Frozen evidence (orun11, iteration 6).

## The clip

ADR-777 puts ADR-776's plantigrade stance on `assembly.gait` (`heels`,
`heel_from`, `body_drop_mm`, `body_pitch_deg`, `stance_shift_mm`).
orun11-cat's gallop clip now declares it when `gallop_heel` is 1 (the new
default). The clip:

- rotary, 0.7 m at 2.4 Hz, lags 0.05, spine `j_spine`;
- duty 0.2, set by `heel_duty`. The project stores `gallop_duty` at 0.25,
  and no plantigrade clip is reachable at duty 0.25, so the toe clip keeps
  that parameter and the plantigrade clip has its own;
- swing 40 mm, pitch amplitude 2°;
- the hock cases (`c_qdd_hock_l`, `c_qdd_hock_r`) held on the floor from
  half the hind stance to toe-off;
- the trunk 60 mm down and 6° nose-up, the hind stance 120 mm forward.

**Why duty has its own parameter.** The engine refused the first two
builds: "leg RH cannot reach its swing target at 0.952 of the stride: it
misses by 2.5 mm [then 3.6 mm, at 40 mm of swing] with j_knee_r, j_hock_r at
a stop". The project stores `gallop_duty` at 0.25, which overrides the
script's default, so both builds ran at duty 0.25, where no plantigrade clip
is reachable. `heel_duty` has no stored value. The swing went from
`hind_range.py`'s 50 mm to 40 mm between those builds, on a wrong guess
that the first refusal was the swing. Both are reachable at duty 0.2.

**The reachable region**, on the training bundle's model (07a92830), at 0.7
m and duty 0.2 (`/tmp` scan, not committed): 106 of 432 settings are
reachable, over swing 30/40/50 mm, pitch amplitude 0/2°, drop 50–80 mm,
pitch 4–8°, shift 100–140 mm and heel from 0.5/0.6. At drop 60 mm, pitch 6°
and shift 120 mm, every swing from 30 to 50 mm passes. All but four
reachable settings have a hind joint at a stop at some sample. The best
margin is 0.3°, at 30 mm of swing.

Accepted on **07a92830** (the same geometry as d6fe5680; only the clip
changed):

- fit **pass**: 0 failing of 7,626 pairs;
- mounting **pass**: 30 of 30;
- panels: 0 failing of 45, 12 advisory;
- sweep **incomplete**: 29 of 36 limited joints swept with no failing pair.
  `j_tail1`–`j_tail7` hit the 90 s per-joint bound. The fit cache now
  covers the other five tail joints that d6fe5680 left unswept.

The bundle's clip: 21 samples a stride. The hind heels are held down on 2
samples each (LH 3–4, RH 4–5). The rod's closures are held to 0.0004 mm (LH)
and 0.0007 mm (RH).

## M1's static check, in the clip's stance pose

`clip_static.py` poses the training bundle's exported model in each stance
sample of the bundle's own clip, with the floor where the generator put it.
It replaces `foot_static.py`'s level-trunk pose, which crouched the hip 70–84
mm below standing:

```
pixi run python docs/probes/orun11/clip_static.py \
  runs/heel1-s1/train/cat_model-model.xml runs/heel1-s1/train/gallop-task.json
```

| foot | sample | sole pitch (deg, + toes-down) | hock case over floor (mm) | heel held |
|---|---|---|---|---|
| LH | 0 (touchdown) | −13.4 | 30.0 | no |
| LH | 1 | −6.6 | 37.8 | no |
| LH | 2 | +0.4 | 47.3 | no |
| LH | 3 | −12.7 | 0.0 | yes |
| LH | **4 (push-off)** | **−9.1** | **0.0** | yes |
| RH | 2 (touchdown) | −9.7 | 37.4 | no |
| RH | 3 | −2.3 | 45.6 | no |
| RH | 4 | −15.5 | 0.0 | yes |
| RH | **5 (push-off)** | **−10.3** | **0.0** | yes |

**M1's static check fails, narrowly.** At push-off the hock case is on the
floor on both legs (0.0 mm, within 10 mm). But the sole is 9.1° (LH) and
10.3° (RH) toes-up, outside the 8° limit by 1.1° and 2.3°. With the case
down, the rod holds the paw rolled back on its pad, toes off the floor. The
rod's offset (its turnbuckle length) sets the paw's angle at a given hock
angle. About 10° more toes-down at the push-off hock would flatten the sole
there. The cost is about 10° more toes-down everywhere else on the curve.

## heel1-s1

The first screen on this clip:

- orun11-cat 07a92830, cold, 150 iterations;
- 8,192 envs, unroll 20, seed 0, checkpoints every 25;
- a 7,200 s budget;
- rod1-s1's 17 terms, unchanged, so the clip is the one variable.

**O8 timing.** Iteration 10 came at 549 s: about 245 s of compile, then
about 30 s an iteration. The trainer's ETA at iteration 10 was 5,837 s more,
so the run should end about 6,400 s after its start, inside the budget.
Iteration 10's reward/step is 10.65 and its episode 128 steps, against
rod1-s1's 10.71 and 101. Unjudged.
