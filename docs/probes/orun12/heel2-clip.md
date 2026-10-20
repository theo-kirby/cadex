# orun12 P1 / Q1: the clip asked for the bar; the model and clip mirror

Verified against source: 2026-10-19. Frozen evidence (orun12, iteration 2).

## The clip's heel share was the spec's bar

v07-g1's clip (`heel_from` 0.5, duty 0.2, 21 samples a stride) holds
each hind heel down on **2 of its 5 stance samples**: a 0.4 share, exactly
`gallop_spec`'s `hock_down` minimum. A policy that tracks the clip perfectly
scores 0.4 at best, and v07-g1 lifted both heels from iteration 75
(`b1-baseline.md`).

`clip_heel.py` regenerates the bundle's clip offline with the engine's own
generator (`CadexGait.generate`) on the bundle's exported MJCF, and checks
that the bundle's own `heel_from` regenerates the bundle's clip exactly
(heel schedule equal, qpos difference 0.0):

```
pixi run python docs/probes/orun12/clip_heel.py \
    RUN/train/gallop-task.json RUN/train/cat_model-model.xml 0.5 0.4 0.3 0.2 0.1 0
```

On v07-g1's bundle:

| heel_from | reachable | heel-down / stance samples, LH and RH | share |
|---|---|---|---|
| 0.5 (v07-g1) | yes | 2/5, 2/5 | 0.4 |
| 0.4 | yes | 3/5, 3/5 | 0.6 |
| 0.3 | yes | 3/5, 3/5 | 0.6 |
| 0.2 | yes | 4/5, 4/5 | 0.8 |
| 0.1 | yes | 4/5, 4/5 | 0.8 |
| 0 | yes | 5/5, 5/5 | 1.0 |

Every setting is reachable. **heel2-s1** takes `heel_from` 0.2: the paw
lands on its toes for one sample, then the heel is held to toe-off, 0.8 of
the stance. It is a literal in the script's clip section, not a parameter,
because the script is at the engine's 64-parameter cap.

## O3: the model mirrors

`mirror.py` pairs every left/right body, joint, geom, actuator and
equality constraint of the exported MJCF by name and compares them mirrored
through the sagittal plane, in the model's keyframe: mass and principal
inertia, world positions and CoM, joint axes (as pseudo-vectors), anchors,
ranges, stiffness, spring reference, damping, armature and friction loss,
geom type, size, friction and solver parameters, drive gear, force range
and gains, and the rod constraints' anchors and solver parameters. The
tolerances are 1% relative, 1 mm and 0.5°.

```
pixi run python docs/probes/orun12/mirror.py RUN/train/cat_model-model.xml
```

On v07-g1's model (`7bc0f4c8…`): 471 checks over 48 body, 14 joint,
13 geom, 9 actuator and 2 equality pairs, no name without a partner.
**Every leg body, joint, drive, collision geom and rod constraint mirrors.**
The 28 differences are all cosmetic covers and a camera: the seven tail
panels (`c_pnl_tail1..7_l` 6–12% heavier than the right, about 1 g each,
CoM 1–2 mm off mirror), the neck side and skull cheek and muzzle panels
(1–2 g, CoM up to 5 mm), and `c_camera_l` (2 mm). The whole model weighs
31.73 kg and its centre of mass sits **0.013 mm** off the midplane.

## O3: the clip mirrors in the hind

In v07-g1's clip the LH and RH contact schedules and heel schedules are
equal, their heel heights equal to 2e-16 m, and their foot paths mirror
exactly (largest |x_L − x_R|, |y_L + y_R|, |z_L − z_R| is 0.0). `hind_lag`
is 0, so neither hind leads. The one asymmetry left in the clip is the fore
pair's `gallop_lag` 0.05 (LF lands after RF).

So the 59% heel-height spread (31 mm LH, 75 mm RH) and the 35% overreach
spread (358 against 234 mm) on v07-g1 come from neither the model nor the
hind clip. What remains of O3 is the mirrored-seed check, which needs a
training run.

## Q2, to fix later

v07-g1's right fore rod's lower end (`j_frodbot_r`) opens to 2.6–3.3 mm
at its worst, over O9's 2 mm. Its median is 0.1–0.3 mm. The hind rods stay
under 1.7 mm. The rods are `equality/connect` at solref 0.004 with solimp
0.99/0.9999. Two fixes are within O1: joint damping on the fore rod ends, or
a stiffer solref. Neither is in heel2-s1, which changes one thing.

## heel2-s1

feline-v07 rebuilt as revision **`26f8972b`** (digest `db341c69`): only the
clip section changed. The exported model is byte-identical to v07-g1's
(`7bc0f4c8…`). The bundle's clip holds each heel from 0.2 of the stance on
4 of 5 samples. heel2-s1 trains cold on it through `cadex_cli.loop` with
`retain_training_view`, in its own scope (`systemd-run --user --scope -p
MemoryMax=30G`). It runs 8192 environments with unroll 20 and seed 0, takes
a checkpoint every 25 iterations, and runs **135 iterations** at
`budget_s` 21,300. The loop caps a budget at 21,600 s, so the 150
iterations the critic asked for, at about 131 s an iteration plus O8's 20%
(23,600 s), do not fit; 135 × 131 × 1.2 = 21,222 s. A later iteration
judges every checkpoint on `gallop_spec`.
