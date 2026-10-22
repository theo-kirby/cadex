# orun15 O5: LH's fold on hlk8-sole-50 follows the landing order, not the side

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 12).
Follows `hlk8-sole.md`: with `hind_lag` on leo-v04.2 RH lands 40 ms ahead
of LH on every seed, RH's U is 0.02 and LH's 0.29. Is LH's fold the left
side (the model) or the role of the second hind to land (the policy)?

## The tests (CPU, 10 seeds 1001–1010)

```
R=~/cadex-projects/leo/runs/hlk8-sole/train; E=~/cadex-projects/leo/evaluations
pixi run python docs/probes/orun12/mirror.py $R/cat_model-model.xml
pixi run python docs/probes/orun12/mirror_policy.py \
    $R/cat_model-model.xml $R/gallop.cxpolicy $R/gallop.mirror-50.cxpolicy
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R $R/gallop.mirror-50.cxpolicy hlk8-sole-50m
python3 docs/probes/orun12/legs.py $E/hlk8-sole-50 $E/hlk8-sole-50m
pixi run python docs/probes/orun14/paw_floor.py $R/cat_model-model.xml $E/hlk8-sole-50 $E/hlk8-sole-50m
python3 docs/probes/orun13/p2_lag.py $R/gallop-task.json $E/hlk8-sole-50m
```

Policy `4ac25fff` (hlk8-sole's 50), leo-v04.2 bundle `1412f4af`.

- **The model mirrors** (`mirror.py`): 471 left/right checks, 27 differ,
  all on the cosmetic bodies `c_camera`, `c_pnl_neck1_side`,
  `c_pnl_skull_muzzle` and `c_pnl_tail1`–`7`, as on v04 (`rh-mirror.md`).
  No leg body, joint, pin, spring, geom, actuator or rod loop differs.
- **The policy mirrors** (`mirror_policy.py`): 22 actions, 72 channels,
  witness |π'(o) − M_a π(M_o o)| ≤ 3.9e-14.

## Every handed measure swaps

| evaluation | top 2 s m/s med | hock down LH / RH | at toe-off LH / RH | **U LH / RH** | pin ° in stance LH / RH | roll ≥3 frames LH / RH | pin ° at lift LH / RH | overreach mm LH / RH | hind first | pin p95 °/s LH / RH | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hlk8-sole-50 | 2.17 | 0.44 / 0.36 | 0.18 / 0.72 | **0.29 / 0.02** | +17.5 / +9.4 | 0.82 / 0.16 | +43.4 / +18.5 | 348 / 8 | RH, every stride | 760 / 310 | 1.92 (j_spine) | 0.00 | 4.0 |
| hlk8-sole-50m | 2.18 | 0.29 / 0.44 | 0.58 / 0.15 | **0.02 / 0.27** | +9.9 / +17.6 | 0.19 / 0.83 | +18.6 / +43.9 | −13 / 339 | LH, every stride | 323 / 762 | 1.88 (j_spine) | 0.00 | 4.0 |

Both: 10/10 complete, no fall, flight every stride (140 / 105 ms), heels
3 mm up in stance on both legs, no swing over 900 °/s, no flapping.

- **The fold is the second hind's, whichever side it is.** Mirrored, LH
  lands first on every stride and stays flat (U 0.02); RH lands second, with
  the 340 mm overreach, and folds (U 0.27). The swap is within seed noise
  on every column.
- **How it folds:** the second hind lands far forward, stands with the pin
  17–18° toes-up of the metatarsus (the floor pitch stays +2–3°), and rolls
  over the toes for three or more frames on 0.82 of its toe-offs, the pin at
  +43° when it lifts. The first hind lands under the body, pin at +9–10°,
  and rolls on 0.16–0.19.
- `p2_lag.py` scores the mirror 0/10 rotary: its seed rule divides by
  every fore landing, and the mirror's taps move to RF; `legs.py` reads 119
  of 131 ordered strides rotary and every LH-first stride is rotary. The
  order is the original's mirror image, not transverse.

## What it means

- **No left-side model fix.** Nothing in the model is handed; a stiffer
  left coil or a left geom change has no case.
- **The next P1 lever is the second hind's stance**: where it lands
  (its 340 mm overreach, against the first hind's 0) and its roll at
  toe-off. With `hind_lag` on, whichever hind lands second folds, on v04
  (hl-sole-50 LH 0.31) and v04.2 (0.29) alike.
