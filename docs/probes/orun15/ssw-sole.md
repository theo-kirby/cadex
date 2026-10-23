# orun15 P1: ssw-sole, `hind_place` warm from hlk8-sole-50 (dead end at 25)

Verified against source: 2026-10-21.

ss-sole's 22-term task (`ss-sole.md`: hlk8-sole's task plus `hind_place`
w −10, project revision `29298667`, leo-v04.2) warm from hlk8-sole-50
(`4ac25fff`) across the one task change; lr 3e-5, critic warm-up 5, 4,096
envs, seed 0, 50 iterations, `budget_s` 4,600. Launched 23:17:41 (keep
and stop rules in `ss-sole.md`, written before launch). ss-sole's cold run
stood LH on its toe tip; this asks whether the charge moves the second
hind back and takes out its fold when the gait already exists.

## Timed

- Iteration 10 at 23:34:25: **1,004 s from launch**, about 88 s an
  iteration once running (iterations 6–10). 50 would have finished near
  4,520 s, inside 4,600 s with little to spare.
- Reward per step 33.0 at 0, falling to 29.5 at 10 as the critic warmed
  up, back to 33.2 at 25. Episodes 81,920 → 1,107 → 2,926 steps a batch.

## Judged at 25 (`ssw-sole-25`, 10 seeds, CPU)

+25's checkpoint `45dc8fb5`, judged on its own bundle (`29298667`):

```
R=~/cadex-projects/leo/runs/ssw-sole/train; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R $R/gallop.000025.cxpolicy ssw-sole-25
python3 docs/probes/orun12/legs.py $E/hlk8-sole-50 $E/ssw-sole-25
pixi run python docs/probes/orun14/paw_floor.py $R/cat_model-model.xml $E/hlk8-sole-50 $E/ssw-sole-25
python3 docs/probes/orun13/p2_lag.py $R/gallop-task.json $E/hlk8-sole-50 $E/ssw-sole-25
pixi run python docs/probes/orun15/place_term.py $R/cat_model-model.xml $E/ssw-sole-25
pixi run python docs/probes/orun13/spine_foot.py $R/cat_model-model.xml $E/ssw-sole-25
```

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH | at toe-off LH / RH | **U LH / RH** | floor pitch ° in stance LH / RH | on-ground F / R / T / U, LH | on-ground F / R / T / U, RH | touch-down place mm LH / RH | `hind_place` a step | hind lag / together | rotary seeds (ordered) | flight s | overreach (passes, median mm) | pin p95 °/s LH / RH (swing) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hlk8-sole-50 | 0/10 | 2.09 / 2.17 / 2.19 | 0.44 / 0.36 | 0.18 / 0.72 | 0.29 / 0.02 | +2.6 / +2.6 | 0.22 / 0.46 / 0.01 / 0.29 | 0.34 / 0.63 / 0.00 / 0.02 | +208 / +133 | 0.049 | 0.101 / 0.10 | 10/10 | 0.140 | 8/10, +8 | 760 / 310 (363 / 156) | 1.92 (j_spine) | 0.00 | 4.0 |
| **ssw-sole-25** | 0/10 | 2.11 / **2.23** / 2.27 | 0.35 / 0.25 | 0.09 / 0.33 | **0.39** / 0.03 | +3.7 / +2.9 | 0.10 / 0.48 / 0.03 / 0.39 | 0.23 / 0.67 / 0.06 / 0.03 | **+181** / +90 | 0.035 | 0.108 / 0.12 | 10/10 | 0.120 | 0/10, −70 | 782 / 404 (332 / 248) | 1.98 (j_spine) | 0.00 | 4.8 |

- **Speed held** (2.23 m/s median, hlk8-sole-50 2.17): the warm start kept
  the gait, unlike ss-sole's cold 0.96 m/s. Flight 0.120 s on every
  stride.
- **No stilt.** Neither hind stands on its toe tip: floor pitch in stance
  +3.7 / +2.9°, toes-only frames 0.03 / 0.06, no paw-down frame past 30°
  toes-down on LH, 0.02 on RH (`place_term.py`'s new stilt columns).
- **The charge moved the paws, not the fold.** RH leads (LH leads on
  0.00–0.18 of strides), so LH is the second hind. Its touch-down came
  back only 27 mm (+208 → +181) while RH's came back 43 mm (+133 → +90),
  and **LH's U rose, 0.29 → 0.39**; 88% of what `hind_place` still charges
  falls on LH's U frames (its U frames stand at +154 mm, its flat ones at
  +39). The term pays the folded stance, and the policy pays it rather
  than move the leg.
- The heel lost share on both legs (0.44 / 0.36 → 0.35 / 0.25; toe-off
  0.18 / 0.72 → 0.09 / 0.33), and with RH standing further back the
  `overreach` predicate fell 8/10 → 0/10 (median −70 mm).
- Rotary on 10/10 seeds over ordered strides (RH first, all rotary); hind
  lag 0.108 of the stride, together on 0.12; fore lag 0.206, together
  0.21.
- SP: spine 47.5° a stride (both joints), 0.00 of the time at a stop,
  cable gap max 0.43° (O9's 1° holds).
- O6: worst drive `j_spine` 1.98 × rated RMS, peak margin 0.00. O9: loop
  gap max 4.8 mm (the front push-rod loop, as on every fast v04 policy);
  pins p95 782 / 404 °/s, swing 332 / 248, none over 900, no flapping.

## Verdict at 25: stopped (dead end, warm)

The stop rule fires: **the second hind's U is 0.39, not below 0.25**
(its place did move back from +208 mm, so that clause alone would not have
fired). Stopped at 25 (23:54:18, `loop.request_stop`, state `stopped`).

`hind_place` is a dead end cold (ss-sole: LH on its toe tip) and warm
(ssw-sole: LH's fold rises with its touch-down 27 mm further back). The
critic's fallback, a pitch gate on `hind_place`, is not called for, as
there is no stilt to gate. It is scored and kept ready:
`place_term.py`'s stilt charge (`c_down * max(0, -pitch - 30) / 30`) is
1.134 a step on ss-sole-25's LH and 0.000 on hlk8-sole-50 and
ssw-sole-25's LH.

What these runs leave: on v04.2 the fold follows the second hind
(`hlk8-mirror.md`), and neither the clip (no stance shift under 120 mm
builds) nor a place charge moves it. The spring is the lever that has
moved U at speed (`k8-sole.md`: `PAW_K` 4 → 8 cut U 0.29 / 0.29 → 0.11 /
0.20 at 2.58 m/s), so it is the next candidate under O1, kept easy.
