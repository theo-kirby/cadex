# orun15 O5: RH's fold and lift are the policy's lead, not the model

Verified against source: 2026-10-21. Frozen evidence (orun15, iteration 6).
Follows `sfp-sole.md`, whose next-lever list asked for the RH mirror test
before a stiffer coil (PAW_K 4 → 8).

## The question

Through the spring (v04), its preload (v04.1) and the contact-gated fold
term (sf-sole), RH's U held at 0.28–0.29 while LH moved; RH's heel rode
10–15 mm up in stance against LH's 3–4 mm, and it tapped on 0.36–0.38 of
its strides (LH 0.05–0.11). Is that the model (a handed pin, spring or
geom) or the policy?

## The tests (CPU, 10 seeds 1001–1010)

```
R=~/cadex-projects/leo/runs/$RUN; E=~/cadex-projects/leo/evaluations
pixi run python docs/probes/orun12/mirror.py $R/train/cat_model-model.xml
pixi run python docs/probes/orun12/mirror_policy.py \
    $R/train/cat_model-model.xml $R/train/gallop.cxpolicy $R/train/gallop.mirror-50.cxpolicy
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo $R/train $R/train/gallop.mirror-50.cxpolicy $RUN-50m
python3 docs/probes/orun12/legs.py $E/sf-sole-50 $E/sf-sole-50m $E/sfp-sole-50 $E/sfp-sole-50m
pixi run python docs/probes/orun14/paw_floor.py $R/train/cat_model-model.xml $E/$RUN-50 $E/$RUN-50m
```

`RUN` is `sf-sole` (leo v04, `b32a6ace`, policy `51807e31`) and
`sfp-sole` (leo v04.1, `f3482223`, policy `aa89c927`).

## The model mirrors

`mirror.py` makes 471 left/right checks on each exported model (48 body,
14 joint, 13 geom, 9 actuator, 2 equality pairs). 27 differ on each, and
all 27 are cosmetic bodies (tail, neck, muzzle panels and the camera), as
on v03 (`orun14/rh-mirror.md`). No leg body, joint, paw pin, spring
(`stiffness`, `springref`), geom, actuator or rod loop differs. The script
exits 1 on those panels alone.

`mirror_policy.py` maps 22 actions and 72 channels (the pins' encoders
included); its witness matches M_a π(M_o o) to 4.6e-14 (sf-sole) and
5.0e-14 (sfp-sole).

## The policy's mirror swaps sides

`legs.py`, medians:

| evaluation | hock down LH / RH | at toe-off LH / RH | heel stance mm | overreach mm | touchdown Hz | stride mm | top 2 s m/s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| sf-sole-50 | 0.43 / 0.24 | 0.38 / 0.15 | 3 / 10 | 440 / 81 | 2.50 / 2.56 | 981 / 964 | 2.37 | 1.86 (j_spine) | 0.00 | 3.7 |
| sf-sole-50m | 0.23 / 0.43 | 0.18 / 0.38 | 10 / 3 | 78 / 445 | 2.67 / 2.50 | 974 / 981 | 2.36 | 1.86 (j_spine) | 0.00 | 3.7 |
| sfp-sole-50 | 0.37 / 0.21 | 0.13 / 0.04 | 4 / 15 | 400 / 104 | 2.56 / 2.78 | 954 / 953 | 2.35 | 1.81 (j_spine) | 0.00 | 3.8 |
| sfp-sole-50m | 0.21 / 0.40 | 0.00 / 0.16 | 16 / 3 | 80 / 329 | 2.67 / 2.50 | 932 / 936 | 2.35 | 1.80 (j_spine) | 0.00 | 3.8 |

`paw_floor.py`, the paw on its pin:

| evaluation | leg | U | heel share | floor pitch ° | pin ° in stance | taps | pin p95 °/s |
|---|---|---|---|---|---|---|---|
| sf-sole-50 | LH / RH | 0.29 / 0.29 | 0.22 / 0.05 | +1.2 / +4.7 | +16.8 / +25.6 | 0.05 / 0.36 | 823 / 789 |
| sf-sole-50m | LH / RH | 0.26 / 0.29 | 0.05 / 0.22 | +4.7 / +1.4 | +25.2 / +16.7 | 0.36 / 0.05 | 799 / 832 |
| sfp-sole-50 | LH / RH | 0.23 / 0.28 | 0.19 / 0.06 | +1.7 / +4.0 | +17.8 / +28.6 | 0.11 / 0.38 | 819 / 784 |
| sfp-sole-50m | LH / RH | 0.26 / 0.20 | 0.07 / 0.23 | +3.9 / +1.6 | +29.3 / +16.1 | 0.39 / 0.09 | 805 / 801 |

Every handed measure swaps under the mirror, within seed noise: the heel
share, the heel's stance height, the taps, the overreach, the deeper pin
in stance. On sfp-sole the U gap swaps too (0.23 / 0.28 → 0.26 / 0.20).
The simulation is not handed.

## What it means

- **RH's high heel, taps and deeper fold are the policy's.** Both policies
  learned a handed half-bound: one hind leg (LH here) leads with the long
  overreach (400–440 mm) and the heel down; the other (RH) lands short
  under the body, heel up 10–15 mm, and taps. The mirror runs the same
  gait led by RH.
- **U is not a one-leg problem.** On sf-sole both legs fold on 0.26–0.29
  of their on-ground frames, by different routes: the lead leg with the
  paw nearly flat (floor +1.2°, pin +17°), the trailing one deeper (pin
  +26°). A stiffer coil would act on both; nothing in the model argues
  for a side-specific change.
- **The next P1 lever is the policy's lead, not the coil.** The clip asks
  RH −62 ms of LH (`clip-read.md`) and the policies land the hinds within
  0–20 ms, so the trailing hind lands short under the body. The question
  the warm extension (sfw-sole) answers first is whether training alone
  moves U; PAW_K 4 → 8 stays the O1 fallback, now with no left/right case
  for it.

## Why `trained_task_sha256` differs between sf-sole and sfp-sole

sf-sole's evaluation records `69ee341b`, sfp-sole's `31501e73`: each is
the sha256 of the run's own `train/gallop-task.json`. The two bundles
differ in one field, `model.sha256` (`bce1020d` against `51bcac0e`): the
bundle pins the exported model by digest. The two models differ in one
attribute on two joints, `springref` on `j_pawpin_l` / `j_pawpin_r`
(±0.174533 rad = 10° against ±0.523599 = 30°, the v04.1 preload); the
rate (`stiffness` 0.229183), damping and every other line are equal. The
task itself (terms, weights, clip, observations, success spec) is
identical. So the hashes differ because the model did, as they should,
and the trainer's warm-start check (task and model digest) correctly
refuses an sf-sole policy on the v04.1 bundle: the warm extension runs on
leo v04 (`b32a6ace`) restored, not on the working v04.1 script.

## The warm extension: sfw-sole (launched this iteration)

- The project went back to leo v04 with `cadex revision restore b32a6ace`
  (project commit `af8eaaa`, `exact: true`, `same_geometry: true`, 3.5 min
  from the stored attempt): `script.py` carries `PAW_PRELOAD` 10 again.
  No tag moved (`leo-v04` at `939cfb1`, `leo-v04.1` at `ed7d5ca`).
- Registered through `orun13/queue_run.py` with `--expect-revision
  b32a6ace`, in its own `systemd-run --user --scope -p MemoryMax=30G`:
  sf-sole's bundle exactly (task `69ee341b`, model `bce1020d`),
  `--init-from runs/sf-sole/train/gallop.cxpolicy` (`51807e31`),
  `--critic-warmup 5`, `--learning-rate 3e-5`, 50 iterations, 4096 envs,
  seed 0, unroll 20, a checkpoint every 25, `budget_s` 5,400. Launched
  17:15:16.
- The trainer took the warm start (normaliser carries 4,096,000 samples,
  σ 0.679 from the source). Iteration 0 at 228 s, iteration 4 at 501 s:
  **68 s per iteration**; reward per step 32.3, 32.7, 32.5, 32.3, 32.0
  through the critic warm-up (sf-sole ended at 30.7). Trainer ETA ~5,010 s.
- Judged at +25 and +50 with `paw_floor.py` against sf-sole-50. **Keep
  rule:** U falls by at least 0.05 on each leg at no more than 0.15 m/s
  of speed lost (2.37 m/s at sf-sole-50); else training alone does not
  move U at this task.
