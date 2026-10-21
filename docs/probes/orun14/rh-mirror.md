# orun14 O5: RH's double contact is the policy's, not the model's

Verified against source: 2026-10-21. Frozen evidence (orun14, iteration 5).
Follows `g1-free-50.md`, where RH touched down at 5.50 Hz to LH's 2.44.

## The tests

O5 asks for orun12's two mirror tests before blaming hardware or a reward
for a left/right difference.

```
pixi run python docs/probes/orun12/mirror.py RUN/train/cat_model-model.xml
pixi run python docs/probes/orun12/mirror_policy.py \
    RUN/train/cat_model-model.xml RUN/train/gallop.cxpolicy RUN/train/gallop.mirror-50.cxpolicy
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/leo RUN/train RUN/train/gallop.mirror-50.cxpolicy g1-free-50m
python3 docs/probes/orun12/legs.py EVAL/g1-free-50 EVAL/g1-free-50m
pixi run python docs/probes/orun14/paw_floor.py RUN/train/cat_model-model.xml EVAL/g1-free-50 EVAL/g1-free-50m
```

`RUN` is `~/cadex-projects/leo/runs/g1-free`, `EVAL` the project's
`evaluations/`. The policy is g1-free's final (`gallop.cxpolicy`, sha256
`8ded5f68`). The judging runs on the CPU, 37 s for 10 seeds.

## The model mirrors

`mirror.py` makes 467 left/right checks on leo v03's exported model
(`bc287c9c`): 47 body, 14 joint, 13 geom, 9 actuator and 2 equality pairs.
27 differ, and every one is a cosmetic body:

- the tail panels `c_pnl_tail2..7`;
- `c_pnl_neck1_side`, `c_pnl_skull_muzzle`;
- `c_camera` (CoM 2 mm).

The differences are 0.5–1.8 g and a few mm of CoM per panel. No leg body,
joint, paw pin, geom, actuator or rod loop differs. The script exits 1 on
these panels alone.

## The policy's mirror swaps sides

`mirror_policy.py` maps 22 actions and 68 channels. `j_pawpin_l/_r` take
sign −1, like the other pitch joints. On 32 witness samples the engine's
forward pass equals M_a pi(M_o o) to 4.0e-14.

Seeds 1001–1010, medians:

| evaluation | hock down LH / RH | at toe-off LH / RH | heel stance mm | overreach mm LH / RH | touchdown Hz LH / RH | stride mm LH / RH | top 2 s m/s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|
| g1-free-50 | 0.30 / 0.16 | 0.15 / 0.29 | 4 / 7 | 451 / 47 | 2.44 / 5.50 | 895 / 475 | 2.24 | 1.67 (j_spine) | 0.00 | 3.9 |
| g1-free-50m | 0.17 / 0.30 | 0.31 / 0.18 | 7 / 4 | 37 / 449 | 5.56 / 2.50 | 481 / 891 | 2.23 | 1.65 (j_spine) | 0.00 | 4.2 |

`paw_floor.py`, the paw on its pin:

| evaluation | leg | F / R / T / U | heel share (engine) | floor pitch ° | pin ° | toe-offs | taps | roll ≥3 |
|---|---|---|---|---|---|---|---|---|
| g1-free-50 | LH | 0.02 / 0.22 / 0.00 / 0.76 | 0.02 (0.30) | +32.8 | +43.8 | 22 | 0.09 | 0.74 |
| g1-free-50 | RH | 0.03 / 0.19 / 0.01 / 0.77 | 0.03 (0.16) | +25.7 | +38.1 | 49 | 0.38 | 0.06 |
| g1-free-50m | LH | 0.02 / 0.17 / 0.02 / 0.79 | 0.02 (0.17) | +27.0 | +38.0 | 50 | 0.38 | 0.04 |
| g1-free-50m | RH | 0.01 / 0.17 / 0.00 / 0.82 | 0.01 (0.30) | +34.8 | +45.0 | 22 | 0.05 | 0.75 |

**Every left/right difference swaps sides.** The double contact, the short
stride, the short overreach, the low heel share and the taps all move from
RH to LH. So g1-free learned a handed gait. The model, the simulation and
the evaluation's seed draws are not handed. No hardware change and no
one-sided reward is warranted for Q1.

The toes-up paw (`U` 0.76–0.82) is on both legs in both runs. O2's fault is
not a side's.

## The evaluation reads some predicates on the left hind

`no_tap` and `every_stride` do not swap. They read 2.31 and 1.02 on
g1-free-50, and 1.16 and 0.50 on the mirror. `overreach` passes 10/10
(47.1 mm), against 7/10 (36.7 mm).

- **The stride clock:** `CadexEvaluation.footfall_metrics` clocks the
  stride on the left hind's landings (`REFERENCE_ANCHOR = "LH"`, ADR-774).
  - With the double contact on RH, the clock is LH's 2.44 Hz. RH reads
    2.25× it, which fails `no_tap`.
  - Mirrored, the clock is LH's doubled 5.56 Hz. RH reads 0.45× it, which
    fails `every_stride`.
  - Either way, a double-contacting hind fails the spec. The design holds,
    but which predicate fails depends on the side.
- **Overreach:** `overreach` takes the worse hind's median, measured
  against the same side's fore paw. Its 10 mm shift comes from the fore
  landings, which are not mirrored seed for seed.

So a judged report reads `no_tap` and `every_stride` from the per-foot
touchdown rates (`legs.py`'s touchdown Hz), not from the predicate alone.

## What it means for the next screens

- Q1's asymmetry is a policy habit. It may change with any cold screen
  (h1-meta, p1-flat), so read it per leg on each one. Do not change the
  model for it.
- If a passing policy keeps a handed gait, the likely lever is on the
  trainer: mirrored rollouts, or a symmetry term in the loss. This was not
  screened here.
