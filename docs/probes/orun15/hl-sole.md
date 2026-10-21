# orun15 P2: hl-sole judged at 25 (the hind-lag term, cold)

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 8).
Follows `lag-term.md`, which queued it.

## The question

Does `hind_lag` (w10) split the hind pair the clip's way, where every
fast v04 policy lands the hinds within 0–20 ms? The critic's rule: stop
at 25 if the hinds still land within 20 ms.

## The run

- sf-sole's task plus `hind_lag`, leo v04 `dd9d802f`, model `bce1020d`, 21
  terms; cold, 50 iterations, 4,096 envs, seed 0, `budget_s` 4,500.
  Launched 17:51:36. Iterations 13 → 25 took 75 s each (the first ten
  ~85 s). Reward per step 20.2 at 0, 12.9 at 13, 15.0 at 25.
- +25's checkpoint `076f05d4`. **Not stopped:** the hinds are split (below).

## Judged at 25 (`hl-sole-25`, 10 seeds, CPU)

```
R=~/cadex-projects/leo/runs/hl-sole; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R/train $R/train/gallop.000025.cxpolicy hl-sole-25
python3 docs/probes/orun12/legs.py $E/sf-sole-50 $E/sf-sole-25 $E/hl-sole-25
pixi run python docs/probes/orun14/paw_floor.py $R/train/cat_model-model.xml $E/sf-sole-50 $E/hl-sole-25
python3 docs/probes/orun13/p2_lag.py $R/train/gallop-task.json $E/hl-sole-25   # and $E/sf-sole-25
pixi run python docs/probes/orun13/spine_foot.py $R/train/cat_model-model.xml $E/hl-sole-25
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun15/lag_term.py $R/train/gallop-task.json \
    $R/train/cat_model-model.xml $E/hl-sole-25 $E/sf-sole-25
```

The like-for-like comparison is sf-sole at the same cold checkpoint (25);
sf-sole-50 is the fast reference.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH | **U LH / RH** | stride mm LH / RH | flight s | overreach (passes, median mm) | **hind lag (share) / hinds together** | fore lag / together | **rotary seeds** | `hind_lag` a step (clip 0.282) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sf-sole-50 | 0/10 | 2.33 / 2.37 / 2.45 | 0.43 / 0.24 (0.241) | 0.38 / 0.15 | 0.29 / 0.29 | 981 / 964 | 0.180 | 10/10, +81 | 0.043* / 0.83* | 0.200* | 0/10 | 0.059 | 1.86 (j_spine) | 0.00 | 3.7 |
| sf-sole-25 | 0/10 | 0.83 / 0.85 / 1.09 | 0.00 / 0.04 (0.003) | 0.00 / 0.00 | – | 245 / 192 | 0.000 | 0/10, −309 | 0.150 / 0.27 | 0.381 / 0.00 | 1/10 | 0.098 | 1.56 (j_wrist_l) | 0.00 | 2.2 |
| **hl-sole-25** | 0/10 | 0.51 / 0.76 / 0.85 | 0.02 / 0.23 (0.017) | 0.00 / 0.07 | **0.05 / 0.19** | 122 / 115 | 0.000 | 0/10, −206 | **0.405 / 0.00** | 0.143 / 0.19 | **9/10** | **0.240** | 2.09 (j_spine) | 0.00 | 2.0 |

\* from `sfw-sole.md` / `lag-term.md`.

- **The term moves its measure.** The hinds land together on 0.00 of
  strides (sf-sole-25: 0.27), the hind lag is 0.405 of the stride, RH
  leading on 60–90% of strides, and 9 of 10 seeds read rotary (all of
  them RH-first; seed 1010 has no ordered stride). The policy takes 0.240
  of the clip's 0.282 a step, 2.4× sf-sole-25 at the same checkpoint.
  `legs.py`: 119 of 131 strides rotary, 25 tied.
- **But it is a cold policy at 25, not a gallop:** 0.76 m/s, strides of
  ~120 mm, flight on 0.05 of strides with no measured flight time, every
  hind spec at its floor. Every cold v04 screen is this slow at 25
  (sf-sole-25 0.85, sp-sole-25 0.63 m/s); sf-sole reached 2.37 only by 50.
  So 25 cannot test the keep rule's speed or U, only whether the term
  splits the hinds, and it does.
- **U 0.05 / 0.19** is a slow shuffle's (pin rate p95 300 / 171 °/s), and
  LH stands on its toes (heel share 0.02, heel 16 mm up; RH 0.23, 4 mm).
  It says nothing yet about the fold at speed.
- `spine_foot.py`: the spine runs 27.2° a stride (both joints), 0.13 of
  the time at a stop; cable gap max 0.24° (O9's 1° holds). Heel-down
  frames flat 1.00 / 0.92.
- O6: worst drive `j_spine` 2.09 × rated RMS, peak margin 0.00. O9: loop
  gap max 2.0 mm, at the 2 mm line.

## Verdict at 25

The critic's stop condition (hinds within 20 ms) is not met: the hinds
are as split as the clip asks, and more rotary than any v04 policy so far.
**hl-sole runs on to 50**, where the keep rule (`lag-term.md`) applies:
hind lag ≥ 40 ms on ≥ 5 seeds with rotary order, U ≤ 0.29 each leg,
≥ 2.13 m/s. The risk to watch at 50 is that the split holds only at a
shuffle's speed, as sf-sole-25's 1/10 rotary became sf-sole-50's 0/10.
k8-sole (`leo-v04.2.md`) is queued behind it.
