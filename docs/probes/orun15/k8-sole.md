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
