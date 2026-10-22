# orun15 P1: sfp-sole, sf-sole's task on leo v04.1 (paw spring preload 30°)

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 5).
Follows `leo-v04.1.md` (the model change, its build and its keep rule)
and `sf-sole.md` (the baseline: the same 20-term task on leo v04).

- **The run:** sfp-sole, sf-sole's task (task `69ee341b`'s 20 terms,
  `paw_fold` w −10) on leo v04.1 (revision `f3482223`, `PAW_PRELOAD`
  10 → 30°, `PAW_K` 4 N·mm/deg). Cold, 50 iterations, 4096 envs, seed 0,
  `budget_s` 5,100; launched from the queue at 16:01:08.
- **Timing:** iteration 0 (the compile) logged at 16:06:23, 315 s after
  launch; iterations 1–10 took 691 s, **69.1 s/it** (sf-sole: about
  70). 50 iterations are about 3,770 s with the compile, and 5,100 s is
  over that plus 20% (4,520 s), so `budget_s` stands.
- **The judging:** as `sf-sole.md`: `orun11/judge.py` on `gallop_spec`,
  seeds 1001–1010, on the CPU, then `orun12/legs.py`,
  `orun13/p2_lag.py`, `orun14/paw_floor.py`.

```
R=~/cadex-projects/leo/runs/sfp-sole; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R/train $R/train/gallop.000025.cxpolicy sfp-sole-25
python3 docs/probes/orun12/legs.py $E/sf-sole-25 $E/sfp-sole-25
pixi run python docs/probes/orun14/paw_floor.py $R/train/cat_model-model.xml $E/sfp-sole-25
python3 docs/probes/orun13/p2_lag.py $R/train/gallop-task.json $E/sfp-sole-25
```

## At 25 (`gallop.000025.cxpolicy`, `de4bf4db`)

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH | heel stance height mm | U LH / RH | floor pitch ° LH / RH | on-ground T LH / RH | stride mm LH / RH | touchdown Hz LH / RH | rotary seeds | hind lag (together) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sf-sole-25 | 0/10 | 0.83 / 0.85 / 1.09 | 0.00 / 0.04 | 49 / 13 | 0.00 / 0.10 | −6.6 / +1.3 | 0.47 / 0.00 | 245 / 192 | 2.87 / 2.94 | 1/10 | – | 1.56 (j_wrist_l) | 0.00 | 2.2 |
| **sfp-sole-25** | 0/10 | 0.65 / **1.03** / 1.32 | 0.01 / 0.01 | 72 / 26 | **0.02 / 0.21** | −74.6 / +1.2 | 0.82 / 0.09 | 237 / 241 | 3.00 / 3.44 | 1/10 | 0.150 (0.32) | 1.57 (j_wrist_l) | 0.00 | 2.2 |

- As sf-sole at 25, the slow policy is up on its toes: LH stands on its
  toe bulbs (T 0.82, the paw pitched −75° of the floor), so its U is
  low by being digitigrade, not by a flat paw. RH stands on its pad with
  the pin at +34° (U 0.21, R 0.72), no better than sf-sole-25's 0.10.
- The pin's p95 rate is 569 / 438 °/s, swing p95 182 / 190 °/s, no
  flapping.
- **The hind pair lag at 25 is the clip's 0.150** (together on 0.32 of
  strides); sf-sole loses it only at speed (`clip-read.md`).
- Not the stop: the screen asks its question at speed, and sf-sole's 25
  was as slow; the run goes to 50.

## At 50 (`gallop.cxpolicy`, `aa89c927`, iteration 49, also the trainer's best)

Done 17:05, exit 0, 50 iterations, reward per step 30.6 (sf-sole: 30.7),
still climbing. The evaluation records `trained_task_sha256` `31501e73`
and revision `f3482223`.

```
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R/train $R/train/gallop.cxpolicy sfp-sole-50
python3 docs/probes/orun12/legs.py $E/sf-sole-50 $E/sfp-sole-50
pixi run python docs/probes/orun14/paw_floor.py $R/train/cat_model-model.xml $E/sfp-sole-50
python3 docs/probes/orun13/p2_lag.py $R/train/gallop-task.json $E/sfp-sole-50
pixi run python docs/probes/orun13/spine_foot.py $R/train/cat_model-model.xml $E/sfp-sole-50
python3 docs/probes/orun15/clip_read.py $R/train/gallop-task.json $E/sfp-sole-50
```

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH (spec median) | heel stance height mm | U LH / RH | no_tap | overreach mm LH / RH (passes) | stride mm LH / RH | touchdown Hz LH / RH | flight s | rotary seeds | hind / fore lag (together) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sf-sole-50 (v04) | 0/10 | 2.33 / 2.37 / 2.45 | 0.43 / 0.24 (0.241) | 0.38 / 0.15 (0.148) | 3 / 10 | 0.29 / 0.29 | 0/10 (1.91) | +440 / +81 (10/10) | 981 / 964 | 2.50 / 2.56 | 0.180 | 0/10 | 0.000 (0.83) / 0.275 | 1.86 (j_spine) | 0.00 | 3.7 |
| **sfp-sole-50 (v04.1)** | 0/10 | 2.32 / **2.35** / 2.45 | 0.37 / 0.21 (0.214) | **0.13 / 0.04** (0.039) | 4 / 15 | **0.23 / 0.28** | 0/10 (1.66) | +400 / +104 (10/10, 104) | 954 / 953 | 2.56 / 2.78 | 0.180 | 0/10 | 0.022 (0.68) / 0.098 (0.41) | 1.81 (j_spine) | 0.00 | 3.8 |

Passing: `completes`, `no_fall`, `upright` (18.4°), `straight` (16.5°),
`every_stride`, `overreach`. Failing: `top_speed`, `hock_down`,
`hock_at_toeoff`, `no_tap`.

| leg | on-ground F / R / T / U | heel share (engine) | floor pitch ° in stance | pin ° in stance | pin ° / floor ° at lift | pin rate p95 / max °/s | swing p95 °/s | flapping |
|---|---|---|---|---|---|---|---|---|
| LH | 0.19 / 0.54 / 0.04 / **0.23** | 0.19 (0.37) | +1.7 | +17.8 | +45.6 / −2.9 | 819 / 1141 | 293 | 0.00 |
| RH | 0.06 / 0.58 / 0.06 / **0.28** | 0.06 (0.21) | +4.0 | +28.6 | +55.8 / −2.6 | 784 / 1216 | 295 | 0.00 |

- `spine_foot.py`: the heel-down frames are flat on LH 0.95 / toes-up
  0.05, RH 1.00 / 0.00 (sole tilt −6.1 / −15.8 mm, heel 4.1 / 14.7 mm up
  in stance). The spine runs 40.3° a stride (sum of both joints, median),
  0.00 of the time at a stop, cable gap max 0.50° (O9's 1° holds).
- O9: no NaN or fall; the pin p95 819 / 784 °/s under 900, no flapping;
  the front rod loop `j_frodbot_l` opens to 3.81 mm, over 2 mm (sf-sole:
  3.7), the hind rods 1.5 / 1.6 mm.
- `clip_read.py`: RH lands −20 ms of LH (median, clip −62), in LH's frame
  on 0.31 of LH touchdowns; LF +40, RF +60 ms (clip +146 / +208).

## Verdict: not kept

Against `leo-v04.1.md`'s rule:

- U on LH fell **0.06** (0.29 → 0.23), not the 0.1 asked, and RH moved
  0.29 → 0.28; neither leg is under 0.2. **Fails.**
- The speed is 2.35 m/s against 2.37, within 10%. Passes.
- The pin's p95 is 819 / 784 °/s, under 900. Passes.

So **leo v04.1 is not kept**: the preload helps LH a little and RH not
at all, and the heel at toe-off fell with it (0.38 / 0.15 → 0.13 / 0.04;
one seed of training each, so the cause is not settled). sf-sole-50 on leo v04 stays the
best fast v04 policy. The `leo-v04.1` tag stays (tags are never moved);
the project's working model goes back to v04's preload only when the
next model change is written up.

Across the three levers on the fold, at about 2.2–2.4 m/s:

| run | model | task | U LH / RH |
|---|---|---|---|
| sp-sole-50 | v04 (preload 10°) | 19 terms | 0.32 / 0.29 |
| sf-sole-50 | v04 | + `paw_fold` | 0.29 / 0.29 |
| sfp-sole-50 | v04.1 (preload 30°) | + `paw_fold` | 0.23 / 0.28 |

RH sits at 0.28–0.29 whatever the lever; LH moves with each.

## The next P1 lever (U is still at or over 0.2)

The ladder's levers are spent once each: the spring (v04), its preload
(v04.1) and the contact-gated fold term (sf-sole). Each moved LH by
0.03–0.06; none moved RH. In order:

1. **On the GPU first, no build:** sf-sole extended warm from
   `sf-sole/train/gallop.cxpolicy` (`51807e31`) on leo v04, 50 more
   iterations at `--critic-warmup` and about 3e-5 (O8's fine-tune). The
   question: is U still falling with training at a fixed task (sf-sole's
   curve was still climbing at 49, 30.7 a step)? Judged at +25 and +50
   with `paw_floor.py` against sf-sole-50.
2. **On the CPU while it trains: the mirror test on RH** (O5;
   `orun12/mirror.py`, `mirror_policy.py`) on sfp-sole-50 and
   sf-sole-50. RH's U sits at 0.28–0.29 through three levers, its heel
   rides 10–15 mm up in stance against LH's 3–4 mm, and it taps 0.38 of
   its strides (LH 0.11). orun14 found RH's short step was the policy's
   (`orun14/rh-mirror.md`); this settles whether RH's fold is too, before
   another spring step.
3. **Only if the mirror test clears the policy:** leo v04.2, the spring's
   rate `PAW_K` 4 → 8 N·mm/deg at v04's 10° preload (80 N·mm at flat,
   320 N·mm at 30° toes-up: still under a stance push at the pad),
   written up, built and screened on sf-sole's task as v04.1 was.
