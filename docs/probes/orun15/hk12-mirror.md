# orun15 O5: hk12-sole-50's short first hind and its yaw are the policy's

Verified against source: 2026-10-22. Frozen evidence (orun15, iteration 18).
Follows `hk12-sole.md`: on leo-v04.3 (PAW_K 12) hk12-sole-50 took the fold
out of both hinds (U 0.07 / 0.02) but RH stepped short and often (505 mm,
3.89 Hz against LH's 789 mm, 2.67 Hz), its heel share fell to 0.20, and
the cat yawed (`straight` 0/10, 28°). The critic asked for the mirror tests
before a lever was chosen.

## The tests (CPU, 10 seeds 1001–1010)

```
R=~/cadex-projects/leo/runs/hk12-sole/train; E=~/cadex-projects/leo/evaluations
pixi run python docs/probes/orun12/mirror.py $R/cat_model-model.xml
pixi run python docs/probes/orun12/mirror_policy.py \
    $R/cat_model-model.xml $R/gallop.cxpolicy $R/gallop.mirror-50.cxpolicy
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R $R/gallop.mirror-50.cxpolicy hk12-sole-50m
python3 docs/probes/orun12/legs.py $E/hk12-sole-50 $E/hk12-sole-50m
pixi run python docs/probes/orun14/paw_floor.py $R/cat_model-model.xml $E/hk12-sole-50 $E/hk12-sole-50m
python3 docs/probes/orun14/lead_order.py $R/gallop-task.json $E/hk12-sole-50 $E/hk12-sole-50m
pixi run python docs/probes/orun15/fore_tap.py $R/cat_model-model.xml $E/hk12-sole-50 $E/hk12-sole-50m
pixi run python docs/probes/orun15/hind_step.py $R/gallop-task.json $R/cat_model-model.xml \
    $E/hk12-sole-50 $E/hk12-sole-50m
```

## The model mirrors

`mirror.py` on leo-v04.3's exported model (`7a69ad4a`): 471 left/right
checks (48 body, 14 joint, 13 geom, 9 actuator, 2 equality pairs), 27
differ, 0 without a partner. All 27 are cosmetic bodies (the tail
panels 1–7, `c_pnl_neck1_side`, `c_pnl_skull_muzzle`, `c_camera`), as on
v04 (`rh-mirror.md`) and v03. No leg body, joint, pin, spring, geom,
actuator or rod loop differs.

`mirror_policy.py`: 72 channels, 22 actions; the witness matches
M_a π(M_o o) to 3.6e-14. Mirrored policy `c121f92a`.

## The mirrored policy swaps every asymmetry

| evaluation | hock down LH / RH | at toe-off LH / RH | heel stance mm | overreach mm | touchdown Hz | stride mm | top 2 s m/s | final heading ° (median) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| hk12-sole-50 | 0.51 / 0.20 | 0.28 / 0.36 | 1 / 6 | 255 / −127 | 2.67 / 3.89 | 789 / 505 | 1.91 | −21.4 | 1.69 (j_spine) | 0.00 | 4.0 |
| hk12-sole-50m | 0.20 / 0.51 | 0.29 / 0.35 | 6 / 1 | −128 / 252 | 3.67 / 2.50 | 517 / 794 | 1.94 | **+20.8** | 1.71 (j_spine) | 0.00 | 3.9 |

| evaluation | leg | U | on-ground F / R / T / U | heel share | floor pitch ° | taps | pin p95 °/s (swing) |
|---|---|---|---|---|---|---|---|
| hk12-sole-50 | LH / RH | 0.07 / 0.02 | 0.47/0.45/0.02/0.07 · 0.20/0.60/0.18/0.02 | 0.49 / 0.20 | +0.9 / +2.2 | 0.00 / 0.56 | 781 / 468 (424 / 373) |
| hk12-sole-50m | LH / RH | 0.02 / 0.08 | 0.19/0.63/0.15/0.02 · 0.46/0.46/0.01/0.08 | 0.19 / 0.48 | +2.3 / +1.0 | 0.59 / 0.00 | 458 / 786 (341 / 424) |

- **Lead:** hk12-sole-50 lands RH first on every ordered stride (the
  clip's order); the mirror lands LH first on every one (`lead_order.py`:
  73 rotary, 37 transverse, 82 tied, RH-first on 0.00).
- **The short stepper is the first hind to land, whichever side it is.**
  The yaw's sign follows it: −21.4° → +20.8°, `straight` 0/10 on both.
- So, as in `rh-mirror.md` on v04, the asymmetry is the policy's: no
  model change is argued for.

## Two candidate terms, scored per step (O7)

`hind_step.py` (new) reads every settled control step with the clip's
clock recovered as `lag_term.py` does, and scores, per hind leg, contact
in the clip's swing (`off`) and no contact in its stance (`miss`), the
candidate `hind_tap` (`fore_tap`'s form on the hinds) and `straight`'s
heading part, 4·|imu_qz|:

| evaluation | off LH / RH | miss LH / RH | track_contact pay LH / RH (w10) | hind_tap a step | 4·abs(qz) a step |
|---|---|---|---|---|---|
| hlk8-sole-50 (v04.2, straight 10/10) | 0.07 / 0.02 | 0.03 / 0.07 | 2.25 / 2.27 | 0.045 | 0.16 |
| hk12-sole-50 | 0.05 / 0.04 | 0.01 / 0.05 | 2.35 / 2.26 | 0.048 | **0.61** |

(The mirror's own row is not comparable: it runs the unmirrored clip.)

- **`hind_tap` is cut before training.** RH's extra landings sit inside
  the clip's stance window (`off` 0.04; `fore_tap.py` counts 0.00 taps a
  step: each is a full step, 145 mm and more). The term scores the
  short-stepping policy no worse than the balanced one (0.048 vs 0.045).
- **`straight` separates them** 4 : 1 on heading. At its weight of 1 the
  yaw costs about 0.6 a step against `track_speed`'s ~19.

## The next screen: st4-sole

- hk12-sole's task with `straight` 1 → 4 (`~/orun15-queue/orun15-st4.py`,
  the one change), warm from hk12-sole-50 (`d0d260e3`) across the task
  change (`--parent-task`, `--task-change`), `--critic-warmup 5`,
  `--learning-rate 3e-5`, 4,096 envs, seed 0, 50 iterations,
  `budget_s` 5,500. Queued 01:18:23 with `orun13/queue_run.py --after
  hk12-s1 --build` (`~/orun15-queue/st4-sole.log`); it builds now and
  launches when hk12-s1 frees the slot.
- **The question:** does pricing the heading straighten the cat, and does
  the first hind's stride lengthen with it (RH 505 mm, heel 0.20)?
- **Stop at 25** if `straight` is under 5/10 and the first hind's stride
  has not lengthened past 600 mm, or either hind's U is ≥ 0.2.
- **Keep at 50** if `straight` passes on ≥ 8/10, both hinds' U < 0.2,
  each hind's heel share ≥ 0.3, and ≥ 1.9 m/s (hk12-sole-50's 1.91).
- If hk12-s1 shows the fold is seed 0's (second hind U ≥ 0.2, so
  leo-v04.3 not kept), st4-sole is stopped before it is judged.

## hk12-s1 (seed 1) judged at 25

`hk12-s1-25` (policy `9121aeec`, revision `7a69ad4a`), the same commands
as `hk12-sole.md`:

| evaluation | top 2 s m/s min / med / max | hock_down LH / RH | **U LH / RH** | on-ground F / R / T / U, LH | on-ground F / R / T / U, RH | stride mm LH / RH | touch-down Hz LH / RH | hind lag / together | rotary seeds (ordered) | final heading ° (median) | pin p95 °/s LH / RH (swing) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hk12-sole-25 (seed 0) | 0.45 / 0.77 / 0.89 | 0.10 / 0.13 | 0.12 / 0.07 | 0.08/0.79/0.00/0.12 | 0.10/0.79/0.00/0.07 | 143 / 106 | 2.67 / 2.78 | 0.293 / 0.00 | 2/10 | – | 261 / 204 (170 / 179) | 2.07 (j_tail1) | 0.00 | 2.3 |
| **hk12-s1-25 (seed 1)** | 0.62 / **0.85** / 1.05 | 0.12 / 0.08 | **0.07 / 0.00** | 0.10/0.80/0.02/0.07 | 0.08/0.88/0.01/0.00 | 146 / 146 | 2.33 / 2.44 | 0.434 / **0.00** | 3/10 (7 seeds < 5 ordered) | −17.7 | 285 / 217 (180 / 201) | 1.99 (j_tail1) | 0.00 | 2.5 |

- Still a shuffle at 25 (0.85 m/s, no flight), as seed 0 was. Both hinds'
  U are under the stop rule's 0.25, and the hinds never tie, so **it runs
  on**.
- It already yaws the way seed 0 did (final heading −17.7°, max 42.5°,
  `straight` 0/10): a second seed turning to the same side, with RH the
  clip's first hind, points at the policy's role for the leading hind,
  not at seed 0.
- `evaluation.json` checked at source: `max_forward_speed_2s_mm_s` median
  855, `max_heading_deg` median 42.5, revision `7a69ad4a`.

## hk12-s1 judged at 50: leo-v04.3 is kept

The run finished at 50 at 02:17 (reward per step 33.6 at 49, still
climbing: 30.7 at 44; hk12-sole 29.4). Final policy `27954048`, judged on
its own bundle (`7a69ad4a`), with the commands above plus
`orun13/spine_foot.py`.

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec median) | at toe-off LH / RH (spec median) | **U LH / RH** | on-ground F / R / T / U, LH | on-ground F / R / T / U, RH | heel mm in stance LH / RH | stride mm LH / RH | touch-down Hz LH / RH | flight s | overreach (passes, median mm) | straight (passes, median °) | hind lag / together | rotary seeds (ordered) | pin p95 °/s LH / RH (swing) | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hk12-sole-50 (seed 0) | 0/10 | 1.87 / 1.91 / 1.98 | 0.51 / 0.20 (0.204) | 0.28 / 0.36 (0.271) | 0.07 / 0.02 | 0.47/0.45/0.02/0.07 | 0.20/0.60/0.18/0.02 | 1 / 6 | 789 / 505 | 2.67 / 3.89 | 0.140 | 0/10, −127 | 0/10, 28.0 | 0.381 / 0.05 | 9/10 | 781 / 468 (424 / 373) | 1.69 (j_spine) | 0.00 | 4.0 |
| **hk12-s1-50 (seed 1)** | 0/10 | 2.35 / **2.40** / 2.45 | 0.32 / 0.35 (0.319) | **0.00** / 0.50 (0.000) | **0.16 / 0.01** | 0.24/0.57/0.02/0.16 | 0.34/0.61/0.02/0.01 | 9 / 4 | **991 / 991** | 2.33 / 2.44 | 0.160 | 1/10, −14 | **10/10, 12.0** | 0.117 / 0.00 | 10/10 (10/10 of all strides) | 852 / 577 (385 / 277) | 1.92 (j_spine) | 0.00 | 3.2 |

- **Seed 1 keeps both hinds under U 0.2** (0.16 / 0.01), so the spring's
  effect replicates: by the rule written before launch, **leo-v04.3 is
  kept**. LH, the second hind, carries what fold is left: on-ground U
  0.16, and `spine_foot.py` counts 0.32 of its heel-down frames toes-up
  of flat (RH 0.03), sole tilt −9.8 mm.
- **The asymmetry was seed 0's.** Seed 1 lands RH first on every ordered
  stride (`lead_order.py`: 175 rotary, LF before RF, RH before LH, as the
  clip) and still steps both hinds alike: stride 991 / 991 mm,
  touch-down 2.33 / 2.44 Hz, heel share 0.32 / 0.35. It runs straight
  (`straight` 10/10, max heading median 12.0°, final −2.3°). So the
  first hind's role does not force a short step, and no yaw term is
  needed: st4-sole was stopped (below).
- **Fastest split-gait policy of the run:** 2.40 m/s (hlk8-sole-50 2.17,
  hk12-sole-50 1.91), flight 0.160 s on every stride, rotary on every seed's strides,
  ordered and all (hind lag 0.117 of the stride, about 47 ms at 2.50 Hz,
  over O3's 40; fore lag 0.333; together 0.00 / 0.07).
- **What fails P1:** `hock_down` 0/10 (0.30–0.34 per seed against 0.4)
  and `hock_at_toeoff` 0/10 (LH 0.00 on every seed, RH 0.50): the heel
  lifts before toe-off, mostly on LH. P2: `no_tap` 0/10 (1.98, the fore,
  as on every fast v04 policy: `no-tap.md`), `overreach` 1/10 (RH −14 mm,
  from −127).
- SP: spine 41.4° a stride (both joints; hk12-sole-50 30.8°), 0.00 of
  the time at a stop, cable gap max 0.52° (O9's 1° holds).
- O6: worst drive `j_spine` 1.92 × rated RMS, peak margin 0.00. O9: loop
  gap max 3.2 mm (the front push-rod loop, over O9's 2 mm as on every
  fast v04 policy); pins p95 852 / 577 °/s, swing 385 / 277, none over
  900 in swing, no flapping.
- `evaluation.json` checked at source: `max_forward_speed_2s_mm_s`
  median 2,399, `max_heading_deg` median 12.0, per-seed
  `heel_down_stance_share_min` 0.305–0.343, `heel_down_at_toeoff_share_min`
  0.00–0.095, policy `27954048`, revision `7a69ad4a`.

## The next screen: hk12-s1x (st4-sole stopped)

- **st4-sole** (`straight` 1 → 4, warm from hk12-sole-50, revision
  `4e3defdf`) launched at 02:18:07 and was **stopped before its first
  iteration** (`loop.request_stop`, 02:18:51): it was to straighten seed
  0's yaw, and seed 1 runs straight on the unchanged task. Its scoring
  (`straight`'s heading part 0.61 vs 0.16 a step) stays as evidence.
- **hk12-s1x:** hk12-s1 continued on its own task (hk12-sole's bundle,
  rebuilt from `~/orun15-queue/orun15-v043.py`), warm from hk12-s1-50
  (`27954048`), `--critic-warmup 5`, `--learning-rate 3e-5`, 4,096 envs,
  seed 1, 50 iterations, `budget_s` 4,500 (~75 s/it measured on hk12-s1
  after its first iterations, +20%). Queued 02:18:55
  (`~/orun15-queue/hk12-s1x.log`); rebuilt as `7a69ad4a` and **launched
  02:22:38**, the trainer logging `init-from` `27954048`. Warranted because the curve still
  climbs (+2.9 a step over its last 5 iterations) with both hinds' U
  under 0.2; it asks whether `hock_down` and LH's heel at toe-off climb
  with it.
  - **Stop at +25** if either hind's U is ≥ 0.2, or speed falls under
    2.2 m/s, or `straight` falls under 8/10.
  - **Keep at +50** if both hinds' U < 0.2, `hock_down` median ≥ 0.35,
    LH's heel at toe-off above 0.1, and ≥ 2.3 m/s. Otherwise the next
    lever is the toe-off: the clip's `hock_down` at the end of stance or
    `heel_pitch`'s window, on this policy.
