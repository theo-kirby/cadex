# orun15 P1/P2: hlk8-sole judged at 25 and 50 (hind_lag on leo-v04.2, cold)

Verified against source: 2026-10-21. Frozen evidence (orun15, iterations 10 and 11).
Follows `hl-sole.md` (hind_lag split the hinds and took RH's fold out on
v04, not LH's) and `k8-sole.md` (the k8 coil cut U on both legs, hinds
tied; leo-v04.2 kept).

## The run

- hl-sole's 21-term task (`hind_lag` w10) on leo-v04.2, revision
  `1412f4af` (project `e11bd4f`), model `b2bb0efe`; cold, 50 iterations,
  4,096 envs, seed 0, `budget_s` 4,600. Launched from the queue at
  20:01:30 when k8-sole finished.
- **Timed:** iteration 10 at 20:18:20, 16.8 min after launch (about 90 s an
  iteration with start-up); the trainer's ETA at 14 was 2,831 s more, so
  about 4,200 s in all, inside the budget. Reward per step 20.3 / 13.8 at
  0 / 10 (hl-sole 20.2 / 13.6).
- +25's checkpoint `bcf9dbef`, judged on its own bundle.

```
R=~/cadex-projects/leo/runs/hlk8-sole/train; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R $R/gallop.000025.cxpolicy hlk8-sole-25
python3 docs/probes/orun12/legs.py $E/hl-sole-25 $E/k8-sole-25 $E/hlk8-sole-25
pixi run python docs/probes/orun14/paw_floor.py $R/cat_model-model.xml $E/hlk8-sole-25
python3 docs/probes/orun13/p2_lag.py $R/gallop-task.json $E/hlk8-sole-25
```

## Judged at 25 (10 seeds, CPU)

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH | at toe-off LH / RH | **U LH / RH** | stride mm LH / RH | flight s | hind lag / hinds together | fore lag / fores together | **rotary seeds** | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hl-sole-25 (v04) | 0/10 | 0.51 / 0.76 / 0.85 | 0.02 / 0.23 | 0.00 / 0.07 | 0.05 / 0.19 | 122 / 115 | 0.000 | 0.405 / 0.00 | 0.143 / 0.19 | 9/10 | 2.09 (j_spine) | 0.00 | 2.0 |
| k8-sole-25 (v04.2) | 0/10 | 0.65 / 1.00 / 1.43 | 0.05 / 0.07 | 0.03 / 0.00 | 0.01 / 0.05 | 247 / 174 | 0.000 | 0.211* / 0.17* | – | 0/10 | 1.93 (j_spine) | 0.00 | 3.0 |
| **hlk8-sole-25 (v04.2)** | 0/10 | 0.48 / 0.69 / 0.85 | 0.13 / 0.35 | 0.00 / 0.05 | **0.01 / 0.19** | 93 / 131 | 0.000 | **0.333 / 0.00** | 0.204 / 0.00 | **9/10** | 2.13 (j_spine) | 0.00 | 2.0 |

\* from `k8-sole.md` (`p2_lag.py`); `legs.py` reads 14 tied of 61 strides.

- **The hinds split on v04.2 as on v04**: together on 0.00 of strides,
  hind lag 0.333 of the stride, 9 of 10 seeds rotary (`legs.py`: 110 of
  114 ordered strides rotary, 3 tied); the fore pair is split too (0.204,
  0.00 together).
- **It is a cold shuffle at 25**, as every cold v04 screen is: 0.69 m/s,
  strides of 93 / 131 mm, no flight. U 0.01 / 0.19 is a slow gait's, not
  P1 evidence; pins p95 208 / 129 °/s, no swing over 900, no flapping.
- O6: worst drive `j_spine` 2.13 × rated RMS, peak margin 0.00. O9: loop
  gap max 2.0 mm.

## Verdict at 25

The stop rule (hinds within 20 ms) does not fire: **hlk8-sole runs on to
50** (about 21:10), where its keep rule applies against hl-sole-50 and
k8-sole-50: LH's U down ≥ 0.05 from 0.31 with RH's ≤ 0.1, the hinds ≥ 40
ms apart on ≥ 5 seeds, ≥ 2.0 m/s. fl-sole (`fore-lag.md`) is built and
queued behind it.

## Judged at 50 (`hlk8-sole-50`, 10 seeds, CPU)

The run finished at 50 at 21:07 (about 80 s an iteration after start-up),
reward per step 30.5 (k8-sole 32.5, hl-sole 29.2 at 50). The final policy
`gallop.cxpolicy` is `4ac25fff`, judged on its own bundle (`1412f4af`).
The commands are the ones above with `000025` → `gallop.cxpolicy`, plus
`clip_read.py`, `fore_tap.py` (`no-tap.md`) and `spine_foot.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH (spec median) | **U LH / RH** | heel mm in stance LH / RH | stride mm LH / RH | flight s | overreach (passes, median mm) | RH after LH ms (q1 / q3) | hinds in one frame | seeds hinds ≥ 40 ms | LF / RF after LH ms | rotary seeds | no_tap ratio (LF taps a step) | pin p95 °/s LH / RH (swing p95) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hl-sole-50 (v04) | 0/10 | 2.08 / 2.12 / 2.19 | 0.49 / 0.18 (0.183) | 0.43 / 0.33 (0.283) | 0.31 / 0.01 | 1 / 6 | 867 / 770 | 0.140 | 7/10, +7 | −40 | 0.00 | 10 | – | 9/10* | 1.35 (0.19) | 734 / 272 (273 / 183) | 1.76 (j_spine) | 0.00 | 3.5 |
| k8-sole-50 (v04.2) | 0/10 | 2.51 / 2.58 / 2.61 | 0.38 / 0.24 (0.241) | 0.13 / 0.09 (0.087) | 0.11 / 0.20 | 4 / 10 | 1040 / 1035 | 0.200 | 10/10, +160 | +0 | 0.58 | 0 | +40 / +60 | 0/10 | 1.96 (0.77) | 854 / 865 (296 / 324) | 2.03 (j_spine) | 0.00 | 4.4 |
| **hlk8-sole-50 (v04.2)** | 0/10 | 2.09 / **2.17** / 2.19 | **0.44 / 0.36** (0.357) | 0.18 / 0.72 (0.178) | **0.29 / 0.02** | 3 / 3 | 868 / 878 | 0.140 | 8/10, +8 | **−40 (−60 / −40)** | **0.01** | **10** | +60 / +100 | **9/10** | 1.54 (0.50) | 760 / 310 (363 / 156) | 1.92 (j_spine) | 0.00 | 4.0 |

\* from `hl-sole.md`.

- **The two changes do not add up on LH.** With the hinds split, RH lands
  40 ms ahead of LH on every seed (10/10, in one frame on 0.01 of LH
  touchdowns) and RH's fold is gone (U 0.02, as on hl-sole-50's 0.01),
  but LH folds as on v04 (0.29 against hl-sole-50's 0.31). The k8 coil
  that took LH's U to 0.11 on the tied gait does not take it out of the
  second hind to land. On v04 and v04.2 alike, with `hind_lag` the leg
  that lands second folds; the mirror tests (O5) would say whether the
  fold follows the order or the side.
- **The heel is the closest yet to P1's 0.4 on both legs**: heel share
  0.44 / 0.36 (k8-sole-50 0.38 / 0.24), both legs standing with the heel
  3 mm up in stance, sole flat on 0.92 / 0.97 of heel-down frames
  (`spine_foot.py`). The heel at toe-off splits: LH 0.18, RH 0.72.
- **It costs speed**, as `hind_lag` did on v04: 2.17 m/s, 16% under
  k8-sole-50, with strides of 870 mm against 1,040.
- **Rotary 9/10** (148 of 148 ordered strides rotary, RH first on every
  seed), fore pair 40 ms apart at the median (LF +60 / RF +100 ms after
  LH) and in one frame on 0.20 of strides; a flight of 140 ms every
  stride.
- `no_tap` 1.54: LF taps on 0.50 of its steps, the skip `no-tap.md`
  reads (3 frames, 14 mm, 91 mm forward, at 0.26 of its cycle); RF 0.04,
  the hinds none.
- Spine: 43.2° a stride, 0.00 of the time at a stop, cable gap max 0.38°.
- Pins: p95 760 / 310 °/s, in swing 363 / 156, no swing over 900, no
  flapping. O6: worst drive `j_spine` 1.92 × rated RMS, peak margin 0.00.
  O9: loop gap max 4.0 mm (the front push-rod's, as on k8-sole-50).

## Verdict at 50

Against the keep rule set at 25:

| clause | needs | hlk8-sole-50 | |
|---|---|---|---|
| LH's U | down ≥ 0.05 from hl-sole-50's 0.31 | 0.29 (−0.02) | **fails** |
| RH's U | ≤ 0.1 | 0.02 | passes |
| hinds | ≥ 40 ms apart on ≥ 5 seeds | 10 seeds | passes |
| speed | ≥ 2.0 m/s | 2.17 | passes |

**hlk8-sole is not kept**: the coil does not take LH's fold out with the
hinds split. What it shows is the nearest any v04 policy has come to P1's
heel (0.44 / 0.36) with RH flat and rotary 9/10, so the open question is
LH's fold on the second hind to land. fl-sole (`fore-lag.md`), launched
from the queue at 21:07:12, runs hlk8-sole's task with the fore pair's
terms changed; its LH U is read against this one.
