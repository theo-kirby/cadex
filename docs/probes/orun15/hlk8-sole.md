# orun15 P1/P2: hlk8-sole judged at 25 (hind_lag on leo-v04.2, cold)

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 10).
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
