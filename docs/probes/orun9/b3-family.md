# orun9 B3: the randomised quadruped family

Verified against source: 2026-10-17. Frozen evidence (orun9, iterations 12 and 15).

B3's base model trains on a randomised quadruped family. ADR-758 sets out
how the family is made: as built variants of one parametric robot,
`~/cadex-projects/orun9-qfam`, with masses drawn per environment. This is
the family as built, the check that MJX can batch it, and two cold runs on
members of it. The last section is the base trained on it (ADR-759,
`b3-base1`) and its checkpoints played zero-shot on the held-out v0.

The files are outside the repo, in `~/orun9-progress/b3/`:
- `qfam-script.py`: the family script;
- `variants.json`: the draws;
- `build_variants.sh` and `rebuild_all.sh`: one build per variant;
- `family/vN/`: each variant's `fam_walk-task.json` and `model-model.xml`;
- `tools/family_check.py` and its output `family-check.json`;
- `judge_fam.py` and `judge_v1cold.sh`.

## The variants

Each variant is a `cadex params` build of the family script. Fit, mounting
(14 held of 14) and the 12-joint sweep pass on every build, and each build
resolves its `body` onto the canonical quadruped (ADR-755). Knee direction
is +1 when the knee is ahead of the hip–foot line, and quad-qdd's own build
is −1.

| id | thigh mm | shank mm | front knee | hind knee | hip height mm | build mass kg | clip samples | hip box ° | model |
|---|---|---|---|---|---|---|---|---|---|
| v0 (held out) | 200 | 200 | −1 | −1 | 322 | 9.270 | 44 | −35…15 | `c1e43e3f` |
| v1 | 185 | 225 | +1 | +1 | 330 | 9.281 | 45 | −15…35 | `ddc2f051` |
| v2 | 200 | 215 | +1 | −1 | — | — | — | — | does not build |
| v3 | 200 | 235 | −1 | +1 | 349 | 9.314 | 47 | −35…15 | `54b0680f` |
| v4 | 215 | 195 | −1 | −1 | 330 | 9.284 | 45 | −35…15 | `55f45e5e` |
| v5 | 225 | 220 | +1 | +1 | 357 | 9.329 | 48 | −15…35 | `fe770635` |
| v6 | 195 | 200 | +1 | −1 | 319 | 9.263 | 44 | −15…35 | `42453062` |
| v7 | 180 | 180 | −1 | +1 | 292 | 9.218 | 41 | −35…15 | `5f5b7569` |

- **Lengths** were drawn uniformly in 160–240 mm by `random.Random(758)`
  and rounded to 5 mm. The eight draws came out at 180–235 mm.
- **Masses** are drawn per environment by 22 randomisation entries:
  - the chassis ×0.8–1.2;
  - the battery ×0.7–1.3;
  - each thigh, shin and drive case ×0.8–1.2.

  On v0 that moves 8.45 of the 9.27 kg, a swing of ±1.76 kg (7.5–11.0 kg).
- **The first build took about 12 min.** The other variants took 1.5–2 min
  each, in parallel on three scratch copies (`/tmp/qfam-a`, `-b`, `-c`).
  The variant bundles were then rebuilt once to add the drive-case entries,
  which kept the same models.
- **v2 fails in OCCT.** `part.cut` on `shin_rl`, the bolt holes through the
  shin, refines to an invalid shape. It failed at the 1200 s budget and
  again at 3000 s. The point is left out and v6 has its knee combination.
  The family script cannot build that point, which is a defect in the
  script, not in the family.

## Can MJX batch it?

`family_check.py` compiles every variant's exported MJCF in stock MuJoCo
3.x and compares each against v0.

- **Sizes and shapes:** every `n*` size and every array shape is the same
  on all seven. There is no mismatch.
- **Fields that differ** (largest difference from v0):
  - `geom_pos` and `jnt_pos`: 0.273 m;
  - `body_ipos`: 0.273 m;
  - `body_iquat`: 0.48;
  - `jnt_range`: 0.349 rad, the mirrored hip limits;
  - `site_pos`: 0.026 m;
  - `body_mass`: 0.011 kg;
  - `body_inertia`: 3e-4;
  - what is derived from these (`body_subtreemass`, `dof_M0`,
    `*_invweight0`, `actuator_acc0`, `dof_length`).

  `body_pos` and the reset keyframe are equal on every variant: Cadex
  exports each body at the origin with its frames in world coordinates, and
  the reset pose is the build pose.
- **Per-variant task data:**
  - the tracking clip (41–48 samples);
  - the height reward's constant (for example `abs(com_z - 270.718)` on v0
    and `278.378` on v1) and the crouch floor;
  - the shove's newtons and the reset lift;
  - the hip action box;
  - `body.morph`.

  The 77 channels, the 12 actions, the 9 reward terms and their weights are
  the same on every variant.

## Two cold runs on members, by the recipe

Each run is b1-q1's setup unchanged: 8192 environments, seed 0, unroll 20,
checkpoints every 50, on `orun9-qfam`'s accepted revision at that variant.
Each was judged on the family's walk spec (250 mm/s; 10 frozen seeds
9101–9110; W1–W8, with W8 `within_rated`) through the engine's evaluation
(`judge_fam.py`). In the tables, "speed" and "rated" are medians: forward
speed in mm/s, and the worst drive's share of rated torque.

**`b3-v1cold`**: v1, all four knees ahead. It trained for 200 iterations in
965 s, on the first family task (10 mass entries, ±0.78 kg). The walk spec
that judged it is the same spec.

| it | passed | failing (pass count, median) | speed | rated |
|---|---|---|---|---|
| 50 | **4/10** | W3-speed 4/10 (163), W6-steps 6/10 (6.5), W7-clearance 6/10 | 163 | 0.60 |
| 100 | **8/10** | W1-survives 8/10, W2-tilt 8/10, W3-speed 9/10, W5-lateral 8/10, W6-steps 8/10 | 229 | 0.60 |
| 150 | **10/10** | — | 236 | 0.57 |
| 200 | **10/10** | — | 259 | 0.54 |

The reward per step went −5.4 at iteration 0, 10.3 at 50, 13.8 at 100,
13.5 at 150 and 14.6 at 199.

**b1-q1** (quad-qdd, knees behind; `b1-quad.md`): 0/10 at 50, 0/10 at 100,
10/10 at 150 and at 200.

**`b3-v7cold`**: v7, front knee behind and hind knee ahead, 180/180 mm. It
trained for 200 iterations in 915 s, on the widened family task (22
entries, ±1.76 kg).

| it | passed | failing (pass count, median) | speed | rated |
|---|---|---|---|---|
| 50 | **0/10** | W3-speed 0/10 (104), W6-steps 0/10 (1.5), W7-clearance 7/10 | 104 | 0.35 |
| 100 | **0/10** | W3-speed 0/10 (4.5), W6-steps 0/10 (0), W7-clearance 0/10: it stands | 5 | 0.48 |
| 150 | **10/10** | — | 273 | 0.45 |
| 200 | **10/10** | — | 269 | 0.44 |

The reward per step went −5.3 at iteration 0, 10.7 at 50, 10.7 at 100,
13.9 at 150 and 14.6 at 199. At 100 it was standing: it earned the alive,
pose and posture pay without the speed term, the same plateau b1-q1 went
through. It walked by 150.

**So the cold curve, by the recipe, is 150 iterations to the walk spec on
all three quadrupeds tried** (knees behind, all ahead, and mixed). For B3's
proof, "half" is a fine-tune that passes by iteration 75 or earlier. The
checkpoints are every 50, so the fine-tune needs a pass at 50 or a
checkpoint at 75.

## What this settles and what it does not

- The family is one MJX topology. What differs between members are model
  fields of the kind the trainer already batches, plus per-variant task
  constants and clips. That is what ADR-758's trainer half has to carry.
- Knee-forward and mixed-knee members train by the recipe as fast as
  quad-qdd: each first passes at 150, as b1-q1 did. So inverting a knee
  does not make a member untrainable.
- **Not shown here** (see the next section for the base): any fine-tune
  from it with training iterations, and the cat mapped onto it.

## The base, b3-base1, played zero-shot on the held-out v0 (iteration 15)

`b3-base1` trained cold by the recipe (8,192 environments, unroll 20,
seed 0) on v7 plus v1, v3, v4, v5 and v6 (ADR-759), 300 iterations,
checkpoints every 50, from 15:34 to 16:29 (about 55 min with the compile;
the reward per step went 5.4 at 25, 9.2 at 49 and 14.4 at 299, σ 0.08).
v0, quad-qdd's own point (200/200 mm, both knees behind), was never in
its training set.

A family policy cannot be played by the engine (ADR-759), so each
checkpoint was mapped onto v0 by a **0-iteration fine-tune**:
`cadex_train.py` on v0's `fam_walk` bundle with `--init-from <checkpoint>
--init-from-base … --iterations 0 --critic-warmup 1` (CPU, 32
environments). The actor is not trained: the remap copies 33 inputs, folds
the 13 `morph.*` inputs into the first layer's bias at v0's own values,
copies the 12 outputs, and writes an ordinary v0 policy, witness-checked
(2e-7). Each was judged on v0's walk spec, the 10 frozen seeds 9101–9110,
by the engine's evaluation (`judge_fam.py`, accepted revision `ffa9f8ee`,
v0 set by `cadex params`). Scripts: `~/orun9-progress/b3ft/` (`zs.sh`,
`summ.py`); reports: `~/cadex-projects/orun9-qfam/evaluations/b3-base1-zs-v0-*`.

| base it | passed | failing (seeds failing it) | forward mm/s | steps min | clearance | rated |
|---|---|---|---|---|---|---|
| 50 | **0/10** | W3-speed 10, W6-steps 10, W7-clearance 9 | 13 | 0 | 0.016 | 0.45 |
| 100 | **0/10** | W3-speed 10, W6-steps 9, W7-clearance 10 | 97 | 1.5 | 0.015 | 0.55 |
| 150 | **0/10** | W7-clearance 10, W6-steps 9, W3-speed 8, one fall | 174 | 2 | 0.018 | 0.52 |
| 200 | **0/10** | W6-steps 10, W7-clearance 2 | 236 | 2.5 | 0.034 | 0.49 |
| 250 | **10/10** | — | 231 | 10 | 0.039 | 0.49 |
| 300 (final = best) | **10/10** | — | 228 | 10.5 | 0.054 | 0.53 |

Medians over the 10 seeds; "clearance" is the step clearance in hip
heights (spec ≥ 0.02), "rated" the worst drive's RMS over rated.

**So a robot the base never saw walks the spec with zero fine-tune
iterations,** against 150 cold (b1-q1 on `orun9-quad`, b3-v1cold, b3-v7cold).
The base's own 250 iterations are not counted against it: B3 compares the
fine-tune with a cold run on the target.

Limits of this result:
- v0 lies **inside** the family's ranges (an interpolation test). The cat,
  with a spine, a tail and other legs, is the extrapolation test, and
  needs its canonical mapping (ADR-755) and real fine-tune iterations.
- The cold reference on v0's geometry is b1-q1, which trained
  `orun9-quad`'s `b1_walk`, not v0's `fam_walk` (whose masses are drawn
  over 22 entries rather than 10). The two other cold points (v1, v7) are
  on the family's own task, and all three took 150.
- The remap sets the normaliser's sample count to one, so a fine-tune
  *with* training iterations would replace the base's statistics on its
  first batch (the issue ADR-753 fixed for same-robot warm starts). A zero
  -iteration fine-tune does not update them, so it does not touch this
  result.
