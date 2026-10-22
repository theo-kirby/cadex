# orun15 P1: sfw-sole, sf-sole warm +25, judged and stopped (dead end)

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 7).
Follows `rh-mirror.md`, which launched it.

## The question

Is U still falling with training on a fixed task? sf-sole's curve was
still climbing at 49 (30.7 a step), and none of the three levers (spring,
preload, `paw_fold`) moved RH's U off 0.28–0.29.

## The run

- sf-sole's bundle exactly (task `69ee341b`, model `bce1020d`, leo v04
  `b32a6ace`), `--init-from runs/sf-sole/train/gallop.cxpolicy`
  (`51807e31`), `--critic-warmup 5`, `--learning-rate 3e-5`, 4096 envs,
  seed 0. Launched 17:15:16.
- Reward per step 32.3 at 0, down to 31.2 at 10–16 after the critic
  warm-up, back up to 32.9 at 25. +25's checkpoint `be26b327`.
- **Stopped at 26 of 50** (17:51, `loop.request_stop`, state `stopped`,
  2,169 s), per O8 and the critic's rule: +25 did not move U.

## Judged at +25 (`sfw-sole-25`, 10 seeds, CPU)

```
R=~/cadex-projects/leo/runs/sfw-sole; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R/train $R/train/gallop.000025.cxpolicy sfw-sole-25
python3 docs/probes/orun12/legs.py $E/sf-sole-50 $E/sfw-sole-25
pixi run python docs/probes/orun14/paw_floor.py $R/train/cat_model-model.xml $E/sf-sole-50 $E/sfw-sole-25
python3 docs/probes/orun13/p2_lag.py $R/train/gallop-task.json $E/sfw-sole-25
pixi run python docs/probes/orun13/spine_foot.py $R/train/cat_model-model.xml $E/sfw-sole-25
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun15/lag_term.py $R/train/gallop-task.json \
    $R/train/cat_model-model.xml $E/sfw-sole-25
```

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH (spec median) | heel stance mm | **U LH / RH** | no_tap | overreach mm LH / RH (passes) | stride mm | touchdown Hz | flight s | hind together | rotary seeds | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sf-sole-50 | 0/10 | 2.33 / 2.37 / 2.45 | 0.43 / 0.24 (0.241) | 0.38 / 0.15 (0.148) | 3 / 10 | **0.29 / 0.29** | 0/10 (1.91) | +440 / +81 (10/10) | 981 / 964 | 2.50 / 2.56 | 0.180 | 0.83 | 0/10 | 1.86 (j_spine) | 0.00 | 3.7 |
| sfw-sole-25 | 0/10 | 2.32 / 2.42 / 2.47 | 0.30 / 0.21 (0.209) | 0.04 / 0.06 (0.039) | 6 / 14 | **0.25 / 0.29** | 0/10 (1.53) | +386 / −3 (4/10, −2.7) | 988 / 986 | 2.56 / 2.89 | 0.160 | 0.78 | 0/10 | 1.93 (j_spine) | 0.00 | 4.1 |

- **U:** LH 0.29 → 0.25 (−0.04), RH 0.29 → 0.29 (0). The keep rule asked
  for at least 0.05 on each leg. **Fails on both.**
- Speed held (2.42 against 2.37 m/s), but the heel fell: hock down
  0.43 / 0.24 → 0.30 / 0.21, at toe-off 0.38 / 0.15 → 0.04 / 0.06, and
  RH's overreach collapsed (+81 → −3 mm, `overreach` 10/10 → 4/10).
- `paw_floor.py`: the pin sits deeper in stance (LH +16.8 → +21.2°, RH
  +25.6 → +30.0°), RH taps 0.42 of strides (LH 0.10); pin p95 885 / 781
  °/s, under 900, with no swing over 900 and no flapping.
- `p2_lag.py`: hind lag 0.043 of the stride, hinds together on 0.78 of
  strides; fore lag 0.200; flight 0.160 s on every stride. Strides led by
  RH are rotary (6–10 a seed), strides led by LH transverse (2–4), so no
  seed reads rotary. `lag_term.py`: `hind_lag` 0.041 a step (sf-sole-50
  0.059).
- `spine_foot.py`: the spine runs 44.2° a stride (sum of both joints,
  median), 0.00 of the time at a stop, cable gap max 0.38° (O9's 1°
  holds). Heel-down frames flat 0.92 / 0.96.
- O6: worst drive `j_spine` at 1.93 × rated RMS, peak margin 0.00 (at
  peak, as every leo v04 fast policy so far). O9's front rod loop opens to
  4.1 mm, over 2 mm.

## Verdict: a dead end

Warm training at a fixed task, 25 more iterations at 3e-5, does not move
U: the fold is a stable habit of sf-sole's policy, not a curve still
coming down, and the extra training traded the heel at toe-off for it.
sf-sole-50 stays the best fast v04 policy. The next lever, per the critic,
is the hind pair's lag (`lag-term.md`, screen hl-sole), before PAW_K 4 → 8.
