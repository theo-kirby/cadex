# orun15 P1: k8-sole judged at 25 (sf-sole's task on leo-v04.2, cold)

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 9).
Follows `leo-v04.2.md`, which queued it.

## The question

Does doubling the paw-pin coil (`PAW_K` 4 → 8 N·mm/deg, leo-v04.2) take
RH's fold out, where RH's U sat at 0.28–0.29 through the coil, the 30°
preload, `paw_fold` and warm training? Stop rule (`leo-v04.2.md`): stop at
+25 if RH's U has not moved.

## The run

sf-sole's 20-term task on leo-v04.2 `568d38a9`, cold, 50 iterations,
4,096 envs, seed 0, `budget_s` 5,600; launched 18:56:12 from the queue
when hl-sole finished. Reward per step 15.1 at 25 (sf-sole 15.0 at 25).
+25's checkpoint `a7db9ff8`, judged on `568d38a9`.

```
R=~/cadex-projects/leo/runs/k8-sole; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R/train $R/train/gallop.000025.cxpolicy k8-sole-25
python3 docs/probes/orun12/legs.py $E/sf-sole-25 $E/k8-sole-25
pixi run python docs/probes/orun14/paw_floor.py $R/train/cat_model-model.xml $E/sf-sole-25 $E/k8-sole-25
python3 docs/probes/orun13/p2_lag.py $R/train/gallop-task.json $E/k8-sole-25
```

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH | at toe-off LH / RH | **U LH / RH** | roll ≥ 3 frames LH / RH | stride mm LH / RH | flight s | rotary seeds | pin p95 °/s LH / RH | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sf-sole-25 | 0/10 | 0.83 / 0.85 / 1.09 | 0.00 / 0.04 | 0.00 / 0.00 | 0.00 / 0.10 | 0.02 / 0.15 | 245 / 192 | 0.000 | 1/10 | 418 / 314 | 1.56 (j_wrist_l) | 0.00 | 2.2 |
| **k8-sole-25** | 0/10 | 0.65 / 1.00 / 1.43 | 0.05 / 0.07 | 0.03 / 0.00 | **0.01 / 0.05** | 0.32 / 0.26 | 247 / 174 | 0.000 | 0/10 | 236 / 294 | 1.93 (j_spine) | 0.00 | 3.0 |

- Like hl-sole-25 and sf-sole-25, a cold policy at 25 is a shuffle
  (1.00 m/s, strides under 250 mm, no measured flight), so U here is not
  U at speed. At the same checkpoint RH's U halved (0.10 → 0.05) and LH's
  stayed near zero; both hinds stand on their pads, heels 9–11 mm up.
- The stiffer coil does not flap: pin p95 236 / 294 °/s, no swing over
  900 °/s (max 1,221 / 843 °/s in stance).
- The hinds are not split (hind lag 0.211, 0.17 tied; rotary 0/10), as on
  every v04 policy without `hind_lag`.
- O6: worst drive `j_spine` 1.93 × rated RMS, peak margin 0.00.

## Verdict at 25

RH's U moved at the like-for-like checkpoint, so the stop rule does not
fire: **k8-sole runs on to 50**, where `leo-v04.2.md`'s keep rule applies
(RH's U down ≥ 0.05 against sf-sole-50's 0.29 with LH no worse, speed
within 10% of 2.37 m/s, pin p95 under 900 °/s). hlk8-sole (`hl-sole.md`)
is queued behind it.

## Judged at 50 (`k8-sole-50`, 10 seeds, CPU)

The run finished at 50 at 20:01 (about 80 s an iteration), reward per
step 32.5 (sf-sole 30.7 at 50 on v04). The final policy
`gallop.cxpolicy` is `23765904`; judged on its own bundle (`568d38a9`).
The commands are the ones above with `000025` → `gallop.cxpolicy`, plus
`clip_read.py` for the touchdown lags in ms and `spine_foot.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH | **U LH / RH** | roll ≥ 3 frames LH / RH | heel mm in stance LH / RH | stride mm LH / RH | flight s | overreach (passes, median mm) | RH after LH ms (q1 / q3) | hinds in one frame | LF / RF after LH ms | rotary seeds | pin p95 °/s LH / RH (swing p95) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sf-sole-50 (v04) | 0/10 | 2.33 / 2.37 / 2.45 | 0.43 / 0.24 (0.241) | 0.38 / 0.15 | 0.29 / 0.29 | 0.53 / 0.44 | 3 / 10 | 981 / 964 | 0.180 | 10/10, +81 | +0 (−20 / +0) | 0.42 | +40 / +160 | 0/10 | 823 / 789 (273 / 262) | 1.86 (j_spine) | 0.00 | 3.7 |
| **k8-sole-50 (v04.2)** | 0/10 | **2.51 / 2.58 / 2.61** | 0.38 / 0.24 (0.241) | 0.13 / 0.09 | **0.11 / 0.20** | 0.79 / 0.70 | 4 / 10 | 1040 / 1035 | 0.200 | 10/10, +160 | +0 (+0 / +0) | 0.58 | +40 / +60 | 0/10 | 854 / 865 (296 / 324) | 2.03 (j_spine) | 0.00 | 4.4 (j_frodbot_l) |

- **The stiffer coil cuts the fold on both legs at speed**: U 0.29 / 0.29
  → 0.11 / 0.20, at a faster gait (2.58 m/s, 9% over sf-sole-50; strides
  1,040 mm). The fold that is left is short: rolls of ≥ 3 frames rose
  (0.79 / 0.70), but the paw now rolls about the pad with its floor pitch
  near flat (+0.3 / +4.1° median in stance), the roll the pin is for.
  Heel-down frames are flat on 0.96 of frames each leg.
- **It costs toe-off**: the heel at toe-off fell 0.38 / 0.15 → 0.13 / 0.09;
  the heel's stance share is unchanged (0.38 / 0.24). RH stands with its
  heel 10 mm up, as on v04.
- **The hinds are tied** (in one frame on 0.58 of LH touchdowns, 0/10
  rotary), as on every v04.2 or v04 policy without `hind_lag`; the fore
  pair is 20 ms apart at the median (LF +40 / RF +60 ms after LH).
- The pins: p95 854 / 865 °/s over the whole stride, under O9's 900 with
  little to spare; in swing 296 / 324 °/s, no swing over 900 and no
  flapping.
- `spine_foot.py`: 47.0° a stride (both joints), 0.00 of the time at a
  stop, cable gap max 0.45° (O9's 1° holds).
- O6: worst drive `j_spine` 2.03 × rated RMS, peak margin 0.00. O9: loop
  gap max 4.4 mm on `j_frodbot_l`, the front push-rod loop (`j_frodbot_r`
  3.0 mm; the hind rods 1.5 / 1.8 mm); every fast v04 policy has a front
  rod gap over 2 mm, so it reads as the model's.

## Verdict at 50

Against `leo-v04.2.md`'s keep rule:

| clause | needs | k8-sole-50 | |
|---|---|---|---|
| RH's U | down ≥ 0.05 from 0.29 | 0.20 (−0.09) | passes |
| LH's U | no worse than 0.29 | 0.11 | passes |
| speed | within 10% of 2.37 m/s | 2.58 | passes (faster) |
| pin p95 | under 900 °/s | 854 / 865 | passes |

**leo-v04.2 (`PAW_K` 8) is kept** as the model, by the screen it was built
to move. The policy is not a P1 pass (RH's U sits on the 0.2 line; the
heel at toe-off is 0.13 / 0.09 against P1's spec), and it lands the hinds
together. hlk8-sole (hl-sole's `hind_lag` on v04.2, launched 20:01:30)
asks whether the two changes add up: the split that took RH's fold out on
v04, on the coil that cut both.
