# orun15 P1: sf-sole judged at 25 and 50: the fold term makes the fold shallower, not rarer

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 4).
Follows `fd-sole.md` (the term, the bundle, the launch) and `sp-sole.md`
(the baseline: the same task without `paw_fold`, on the same model).

- **The run:** sf-sole, sp-sole's 19 terms plus the contact-gated
  `paw_fold` (w −10), on leo v04 (revision `b32a6ace`, task `69ee341b`,
  model `bce1020d`, byte-identical to sp-sole's). Cold, 50 iterations,
  4096 envs, seed 0, launched 14:55:31, done 16:00 (exit 0, 50
  iterations, about 70 s/it).
- **The checkpoints:** `gallop.000025.cxpolicy` (sha256 `71cb21bf`,
  15:30, reward per step 14.6 at 25); the final `gallop.cxpolicy`
  (`51807e31`, iteration 49, which is also the trainer's `best`, 30.7
  reward per step, still climbing). Both evaluations record
  `trained_task_sha256` `69ee341b`.
- **The judging:** as `sp-sole.md`: `orun11/judge.py` on `gallop_spec`,
  seeds 1001–1010, on the CPU (evaluations `sf-sole-25`, `sf-sole-50`),
  then `orun12/legs.py`, `orun13/p2_lag.py`, `orun13/spine_foot.py`,
  `orun14/paw_floor.py` and `orun14/fold_term.py`.

```
R=~/cadex-projects/leo/runs/sf-sole; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R/train $R/train/gallop.cxpolicy sf-sole-50
python3 docs/probes/orun12/legs.py $E/sp-sole-50 $E/sf-sole-50
python3 docs/probes/orun13/p2_lag.py $R/train/gallop-task.json $E/sf-sole-50
pixi run python docs/probes/orun13/spine_foot.py $R/train/cat_model-model.xml $E/sf-sole-50
pixi run python docs/probes/orun14/paw_floor.py $R/train/cat_model-model.xml $E/sf-sole-50
pixi run python docs/probes/orun14/fold_term.py $R/train/cat_model-model.xml $E/sp-sole-50 $E/sf-sole-50
```

## The judged runs

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH (spec median) | heel stance height mm | U LH / RH | no_tap | every_stride | overreach mm LH / RH (passes) | stride mm LH / RH | touchdown Hz LH / RH | flight share / s | rotary seeds | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sp-sole-25 | 0/10 | 0.46 / 0.63 / 0.92 | 0.13 / 0.12 (0.114) | 0.02 / 0.00 | 10 / 6 | 0.13 / 0.11 | 0/10 (2.43) | 10/10 | −200 / −190 | 189 / 125 | 3.28 / 2.78 | 0.08 / 0.000 | 3/10 | 2.05 (j_spine) | 0.00 | 2.6 |
| **sf-sole-25** | 0/10 | 0.83 / **0.85** / 1.09 | **0.00 / 0.04** (0.003) | 0.00 / 0.00 | 49 / 13 | **0.00 / 0.10** | 0/10 (1.98) | 9/10 | −284 / −298 | 245 / 192 | 2.87 / 2.94 | 0.07 / 0.000 | 1/10 | 1.56 (j_wrist_l) | 0.00 | 2.2 |
| sp-sole-50 | 0/10 | 2.08 / 2.18 / 2.29 | 0.41 / 0.26 (0.257) | 0.31 / 0.07 (0.071) | 2 / 11 | 0.32 / 0.29 | 0/10 (1.80) | 10/10 | +247 / −46 (0/10) | 823 / 528 | 2.78 / 4.00 | 1.00 / 0.115 | 0/10 | 1.93 (j_spine) | 0.00 | 4.8 |
| **sf-sole-50** | 0/10 | 2.33 / **2.37** / 2.45 | **0.43 / 0.24** (0.241) | 0.38 / 0.15 (0.148) | 3 / 10 | **0.29 / 0.29** | 0/10 (1.91) | 10/10 | +440 / +81 (**10/10**, 81.5) | **981 / 964** | **2.50 / 2.56** | 1.00 / **0.180** | **0/10** | 1.86 (j_spine) | 0.00 | 3.7 |

At 50, passing: `completes`, `no_fall`, `upright` (20.4°), `straight`
(15.1°), `every_stride` and, for the first time on leo v04, `overreach`
(10/10). Failing: `top_speed`, `hock_down`, `hock_at_toeoff`, `no_tap`.

### The hind paws (`paw_floor.py`, medians over 10 seeds)

| evaluation | leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | pin ° / floor ° at lift | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|---|
| sf-sole-25 | LH | 0.00 / 0.49 / 0.47 / **0.00** | 0.00 (0.00) | −6.6 | +15.3 | +26.2 / −4.3 | 418 / 1018 | 162 | 0.00 |
| sf-sole-25 | RH | 0.04 / 0.81 / 0.00 / **0.10** | 0.04 (0.04) | +1.3 | +23.0 | +31.5 / −1.6 | 314 / 916 | 132 | 0.00 |
| sf-sole-50 | LH | 0.21 / 0.48 / 0.03 / **0.29** | 0.22 (0.43) | +1.2 | +16.8 | +43.1 / −4.2 | 823 / 1163 | 273 | 0.00 |
| sf-sole-50 | RH | 0.05 / 0.62 / 0.05 / **0.29** | 0.05 (0.24) | +4.7 | +25.6 | +47.3 / −0.9 | 789 / 1150 | 262 | 0.00 |

`fold_term.py`, sf-sole-50 against sp-sole-50:

| leg | U frames: paw down / heel only | U floor pitch ° q1 / med / q3 | U past `paw_flat`'s 15° | `fold` per U frame | `fold` on F / R / T |
|---|---|---|---|---|---|
| LH | 311 / 22 (383 / 62) | +13 / **+16** / +21 (+18 / +25 / +32) | 0.60 (0.86) | 0.393 (0.676) | 0.034 / 0.002 / 0.000 |
| RH | 269 / 0 (381 / 5) | +15 / **+19** / +25 (+16 / +23 / +29) | 0.71 (0.79) | 0.493 (0.602) | 0.055 / 0.010 / 0.000 |

`spine_foot.py`'s flat-foot check on the heel-down frames at 50: LH 0.96
flat / 0.04 toes-up, RH 1.00 / 0.00 (sole tilt −4.5 / −11.2 mm, heel 2.7
/ 10.5 mm up in stance).

- **At 25 LH's U moved** (0.13 → 0.00), at a faster 0.85 m/s, so by
  `fd-sole.md`'s stop rule the run went on to 50. But it moved by leaving
  the heel up: LH stands on its toes (T 0.47, heel 49 mm up, heel share
  0.00). The slow policy dodged the term by going digitigrade.
- **At 50 the term made the fold shallower and less frequent, not a
  smaller share.** The median fold fell from +25° to +16° toes-up of the
  floor on LH and +23° to +19° on RH; the U frames fell by a fifth (LH)
  and a third (RH), and the term's charge per U frame fell from 0.68 to
  0.39 on LH. The on-ground frames fell with them (the stride is longer
  and the touchdowns fewer), so **U as a share is 0.29 / 0.29**, against
  sp-sole-50's 0.32 / 0.29.
- The pin's p95 rate is 823 / 789 °/s, under O9's 900, no flapping.

### Gait, spine and drives at 50

- **Speed:** 2.37 m/s median, +9% on sp-sole-50, inside tr-sole-50's
  spread (2.14–2.59).
- **Left and right (O5):** the stride is 981 / 964 mm and the touchdowns
  2.50 / 2.56 Hz, within 2% (sp-sole-50: 36% and 31%). The right hind's
  short double step (`orun14/rh-mirror.md`) is gone on this policy. The
  heel share is still uneven: 0.43 / 0.24 (44%).
- **Pair lag (`p2_lag.py`):** fore 0.275 of the stride (together 0.17),
  hind **0.000** (together 0.83). The fore pair is rotary-lagged, more
  than the clip's 0.15, but **the hinds land together**: a half-bound,
  so **rotary 0/10** (66 rotary of 73 ordered strides, 106 tied). Flight
  0.180 s every stride (sp-sole-50: 0.115). The fore paws still tap
  (1.91 fore touchdowns per hind stride, `no_tap` 0/10).
- **Spine (`spine_foot.py`):** 38.3° a stride for the two joints together
  (the clip asks 28°), 0.00 at a stop, cable gap at most 0.42°.
- **Drives (O6):** worst RMS over rated 1.86 on `j_spine`; peak margin 0
  (a drive reaches peak, as on every v03 and v04 screen).
- **Loops (O9):** largest push-rod gap 3.7 mm, over the 2 mm bound
  (sp-sole-50: 4.8).

## The decision: `paw_fold` not kept as the fold's fix

**Keep rule** (`fd-sole.md`): U under 0.2 on both legs at 50, at ≥ 1.96
m/s median, with heel share ≥ sp-sole-50's less 0.05 (0.36 / 0.21).

- Speed 2.37 m/s: passes.
- Heel 0.43 / 0.24: passes.
- **U 0.29 / 0.29: fails on both legs.**

The term earns some of what it was for (a shallower fold, fewer fold
frames) and buys, unasked, a faster, longer, symmetric stride and
`overreach` 10/10. It does not bring U under 0.2. At −10 a fold of +16°
costs about 3.7 a frame on one leg, against `track_speed`'s 20 at full
speed: the policy pays it.

**For sfp-sole** (sf-sole's task on leo-v04.1, launched 16:01:08 on
`f3482223` from the queue): its baseline is now this row. The preload
is kept if LH's U falls at least 0.1 below 0.29 with RH no worse (or U
under 0.2 on both), the speed is within 10% of 2.37 m/s (≥ 2.13), and
the pin's p95 stays under 900 °/s (sf-sole-50's is 823 / 789, so the
margin is 77 °/s).
