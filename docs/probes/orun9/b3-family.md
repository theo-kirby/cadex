# orun9 B3: the randomised quadruped family

Verified against source: 2026-10-17. Frozen evidence (orun9, iterations 12, 15 and 17).

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

  *Fixed since by ADR-760 (`c6c5510b`):* the remap keeps the base's count
  on the inputs it shares and starts only the target's new inputs fresh.
  On the pre-fix trainer a 3-iteration CPU fine-tune of the final base
  onto v0 fell from 1,280-step episodes to 85; on the fixed one it held
  1,280 with the carried statistics moved < 1e-4 of their std.

## Fine-tunes with training iterations (b3-ft150, b3-ftlr)

Both start from `b3-base1` at iteration 150, which scores **0/10** on v0
zero-shot (above). Each trains it on v0 for 75 iterations, half the cold
150, through ADR-760's remap with the base's normaliser carried (24.58 M
samples). The other settings are the recipe's: 8,192 environments, unroll
20, seed 0, critic warm-up 10 and checkpoints every 25. The two runs
differ only in the learning rate. Each checkpoint was judged on v0's walk
spec over the 10 frozen seeds, the same way as the zero-shot table. The
scripts are `launch_ft.py`, `launch_diag.py` and `judge_ft.sh` in
`~/orun9-progress/b3ft/`; the reports are `evaluations/b3-ft150-walk-*` and
`evaluations/b3-ftlr-walk-*`.

| run | it | passed | failing (seeds) | forward mm/s | steps min | clearance | rated |
|---|---|---|---|---|---|---|---|
| b3-ft150 (lr 3e-4) | 25 | **6/10** | W3-speed 3, W6-steps 1, one fall | 195 | 7 | 0.051 | 0.68 |
| b3-ft150 | 50 | **0/10** | W3-speed 10, W6-steps 8, W7-clearance 6 | 90 | 1.5 | 0.029 | 0.59 |
| b3-ft150 | 75 | **0/10** | W3-speed 10, W6-steps 10, W7-clearance 8 | 130 | 2 | 0.015 | 0.56 |
| b3-ftlr (lr 3e-5) | 25 | **4/10** | W6-steps 6, W7-clearance 5, four falls | 264 | 3 | 0.029 | 0.51 |
| b3-ftlr | 50 | **9/10** | W6-steps 1 (seed 9108: 3 steps, min 4) | 295 | 5 | 0.029 | 0.52 |
| b3-ftlr | 75 | **9/10** | W6-steps 1 (seed 9105: 3 steps, min 4) | 295 | 6.5 | 0.038 | 0.58 |
| b3-v1cold (cold) | 50 / 100 / 150 | 4 / 8 / **10**/10 | | 163 / 229 / 236 | | | |
| b3-v7cold (cold) | 50 / 100 / 150 | 0 / 0 / **10**/10 | | 104 / 5 / 273 | | | |

The training curves side by side, as reward a step (sigma):

| it | b3-ft150 | b3-ftlr | b3-v1cold | b3-v7cold |
|---|---|---|---|---|
| 0 | 11.60 (0.141) | 11.60 (0.141) | −5.44 | −5.30 |
| 10 (warm-up ends) | 11.92 (0.141) | 11.92 (0.141) | 2.52 (0.69) | 2.53 (0.71) |
| 11 | **0.51 (0.473)** | 12.22 (0.142) | 2.85 | 2.92 |
| 12 | −2.37 (0.652) | 12.56 (0.143) | 3.21 | 3.29 |
| 25 | 7.16 (0.460) | 12.39 (0.152) | 5.40 (0.52) | 7.13 (0.51) |
| 50 | 10.83 (0.306) | 12.41 (0.155) | 10.26 (0.34) | 10.69 (0.35) |
| 74 | 12.21 (0.243) | 13.16 (0.146) | 12.66 (0.23) | 12.49 (0.25) |

- **At the default learning rate the fine-tune throws the base away.**
  b3-ft150's first actor update, the iteration after the critic warm-up,
  moved sigma from 0.141 to 0.473. Over the base's own iterations 140–160
  sigma moved about 0.001 an iteration. Reward a step fell from 11.9 to
  0.5 and episodes from about 23,000 steps to 121. From there its curve is
  a cold run's: 7.2, 10.8 and 12.2 at 25, 50 and 74, against 5.4–7.1,
  10.3–10.7 and 12.5–12.7 cold. Its 6/10 at 25 is gone by 50.
- **The cause is the step size.** A 15-iteration repeat of b3-ft150 at a
  tenth of the rate (`b3-dlr`, same settings otherwise) kept sigma at
  0.141–0.144 and raised reward from 11.93 to 12.96 in four actor
  iterations. The jump shrank far more than tenfold, so this is an
  instability at 3e-4, not a step in proportion to the rate. Why the cat's
  warm starts at 3e-4 do not show it (c1-c9's sigma went from 0.561 to
  0.578) is not measured. Two differences that could explain it: the base
  sits at a narrow sigma of 0.14, and its Adam moments start from zero on
  a network that has converged.
- **At 3e-5 the fine-tune nearly makes the proof:** 9/10 at 50 and at 75,
  where the cold runs had 0–4/10 at 50 and 0–8/10 at 100. The one failing
  seed, a different one at each checkpoint, has a foot that takes 3 steps
  where the spec asks 4 (`step_count_ratio` 3.67). The gait is lopsided,
  not falling. Forward speed is 295 mm/s against the 250 command.
- **So B3's proof is not met by a fine-tune with iterations at ≤ 75.** The
  standing B3 number is still the zero-shot one: base iterations 250 and
  300 pass v0 10/10 with 0 fine-tune iterations. For the cat, the
  different-shape quadruped, a fine-tune will need iterations, so it
  should use 3e-5, not the default.

## A fine-tune from the base that already passes (b3-ft250)

`b3-ft250` is b3-ftlr's setup (3e-5, 75 iterations, critic warm-up 10,
checkpoints every 25) from `b3-base1` at iteration **250**, which passes v0
**10/10 zero-shot**. It asks whether training iterations on v0 keep or
improve a base that already walks it. Launched with `launch_ft.py b3-ft250
000250 75 3e-5`; judged with `RUN=b3-ft250 judge_ft.sh`; reports
`evaluations/b3-ft250-walk-*`.

| it | passed | failing (seeds) | forward mm/s | lateral mm/s | steps min | clearance | rated |
|---|---|---|---|---|---|---|---|
| 0 (zero-shot) | **10/10** | | 231 | −15 | 10 | 0.039 | 0.49 |
| 25 | **0/10** | W5-lateral 10 (−51 to −56, bound ±50) | 289 | −53 | 10 | 0.054 | 0.59 |
| 50 | **9/10** | seed 9107 falls at frame 37 | 287 | +28 | 10 | 0.064 | 0.46 |
| 75 | **9/10** | seed 9107 falls at frame 39 | 281 | +30 | 11 | 0.047 | 0.56 |

Reward a step (sigma): 12.38 (0.110) at 0, 12.81 (0.110) at 10, 12.89
(0.111) at 11, 12.90 (0.120) at 25, 12.96 (0.126) at 50, 13.65 (0.123)
at 74.

- **3e-5 holds the base**, as in b3-ftlr: sigma went 0.110 → 0.111 on the
  first actor update and stayed under 0.126.
- **But 75 iterations on v0 made the policy worse on the spec**, while the
  reward rose 10%. At 25 every seed drifts sideways just past the ±50 mm/s
  bound; at 50 and 75 the drift flips sign and one seed falls in its first
  0.8 s. The fine-tune pushes forward speed from 231 to 281–289 mm/s
  against the 250 command (bound 175–325), so the reward is buying speed
  the spec does not ask for.
- **So on v0 the base's best number is the zero-shot one** (10/10 at 0
  fine-tune iterations). A fine-tune with iterations does not reach 10/10 at
  any checkpoint ≤ 75 from either base 150 (b3-ftlr, 9/10) or base 250
  (b3-ft250, 9/10). For a target the base already walks, judge the
  zero-shot file first and keep it if it passes (recipe §4.4).

## The cat on the base's body (iteration 19)

B3's proof needs a second quadruped of a different shape, and the cat
counts. `~/cadex-projects/orun9-cat` is a copy of `orun8-cat` (same
`0f036864` geometry, same model `f321f89c`). Its script adds one task,
`b3_walk`, accepted at revision `99a778da`:
- **a body block** (ADR-755). Per leg, `abd` is the girdle's abduction
  (`fhaa`, `hhaa`), `hip` the shoulder or hip, `knee` the elbow or stifle,
  `ankle` the wrist or hock. `scap`, `spine`, `spine_yaw` and the tail are
  not slots.
- **morphology** measured on the exported model at the build pose. The fore
  knee is behind the hip–foot line (−1) and the hind knee ahead of it (+1).
  Thigh is 161 mm fore and 174 mm hind, shank (knee axis to paw centre)
  213 and 232 mm, and hip height 0.386 m (the mean of the shoulder axis at
  372 mm and the hip axis at 400 mm). The family spans hip heights of
  0.292–0.357 m and masses of 7.5–11.0 kg. The cat weighs 31.6 kg.
- **a walk like the family's** (fam_walk, the B1 recipe): one speed,
  270 mm/s (the family's 250 at a 322 mm hip, scaled by dynamic
  similarity), a trot generated at that speed, and the same eight-predicate
  walk spec with shoves sized by the same capture-point rule (18.6–46.5 N in
  the spec, up to 74 N in training). The tail-clearance term is the cat's
  own addition. The over-rated price is split fore and hind, because one
  term over 21 drives is 734 nodes and the cap is 512.

The engine resolved every slot's sign from the axes. The left elbow and
stifle turn about −y, so `knee` is +1 on the left and −1 on the right,
where the family's knee is −1 on both sides. All offsets are 0.

`fit_check.py` (in `~/orun9-progress/b3cat/`, output `fit_check.txt`) runs
`check_base_fits` and `remap_from_base` on `b3-base1` at iteration 250.
**The base is accepted for the cat**:

| inputs copied | inputs folded | inputs zero | outputs copied | outputs zero |
|---|---|---|---|---|
| 33 (24 slot q/dq, 7 IMU, 2 clock) | 13 (morph, at the cat's own values) | 39 (8 ankle q/dq, 16 scap/spine/tail q/dq, 15 scan) | 12 | 12 (4 ankles, 2 scap, spine, spine_yaw, 4 tail) |

The network is 72 → 512 → 256 → 128 → 24. This measures ADR-755's
statement of the cat (32 of 48 joint inputs and 16 of 24 actions on slots),
which was until now only the decision's text.

**Zero-shot** (`zs.sh`: a 0-iteration `--init-from-base`, then the engine's
evaluation on the 10 frozen seeds, CPU) gives **0/10**:
- every seed tips: tilt median 46° (26–50°);
- lateral speed is −520 mm/s (−475 to −566), so the cat goes over to its
  right;
- forward speed is 457 mm/s, inside the speed bound on 1 seed;
- the worst drive is at 2.18× rated (1.88–2.53).

A 9 kg base's actions do not carry a 31.6 kg cat. That is outside the
family's mass and hip-height ranges, and the base's ankle, scapula and
spine outputs all start at their box centres. A CPU smoke (2 iterations,
64 envs, 3e-5) confirms the trainer's path: reward +5.85 a step at
iteration 0 with 1,280-step episodes, then 41-step episodes at iteration 1,
the cat falling in under a second. The witness agrees to 2.2e-7.

**Next.** The cat's half of the proof needs two runs, each a B GPU slot:
- the fine-tune, `launch_cat_ft.py b3-cat-ft 000250 100` (3e-5, checkpoints
  every 25);
- a cold run of `b3_walk` by the recipe, the curve the fine-tune must halve.

## b3-cat-ft: the fine-tune onto the cat, judged (iteration 21)

`b3-cat-ft` fine-tuned `b3-base1` @250 onto the cat's `b3_walk` (revision
`99a778da`) at 3e-5 for 150 iterations, checkpoints every 25, 8,192 envs,
in 2,419 s (scope `orun9-b3-cat-ft2`). It ran every iteration and its
witness agreed to 1.1e-7. `judge_ft.sh` judged every checkpoint on the
cat's walk spec over the 10 frozen seeds, CPU only (evaluations
`b3-cat-ft-000025` … `-000150` in `orun9-cat`; `summ.py` prints the table).

| it | pass | survives | eval episode (median s) | tilt ≤ 25° | speed 189–351 | lateral ±54 | steps ≥ 4 | clearance ≥ 0.02 | within rated | train reward/step | train episode | σ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 (zero-shot) | 0/10 | 0/10 | | 0/10 (46°) | 1/10 (457) | 0/10 (−520) | 0/10 | 0/10 | 0/10 (2.18) | | | 0.205 |
| 25 | 0/10 | 0/10 | 0.91 | 3/10 (31.6°) | 0/10 (459) | 0/10 (−367) | 0/10 (0) | 0/10 | | 9.50 | 48 | 0.205 |
| 50 | 0/10 | 5/10 | 6.47 | 7/10 (15.2°) | 1/10 (120) | 7/10 (23) | 0/10 (0) | 0/10 | 4/10 (1.24) | 10.79 | 187 | 0.224 |
| 75 | 0/10 | **7/10** | 10.0 | 7/10 (10.5°) | 3/10 (130) | **9/10** (25) | 0/10 (1) | 0/10 (0.0063) | 1/10 (1.24) | 12.02 | 467 | 0.255 |
| 100 | 0/10 | 3/10 | 2.15 | 3/10 (26.8°) | 5/10 (201) | 4/10 (68) | 0/10 (0) | 0/10 (0.0117) | 3/10 (1.11) | 13.13 | 491 | 0.264 |
| 125 | 0/10 | 0/10 | 1.78 | 4/10 (25.2°) | 8/10 (315) | 4/10 (58) | 0/10 (0) | 0/10 (0.0060) | **10/10** (0.88) | 13.81 | 498 | 0.275 |
| 150 | 0/10 | 0/10 | 1.60 | 7/10 (24.5°) | 3/10 (420) | 4/10 (66) | 0/10 (0) | 0/10 (0.0068) | **10/10** (0.88) | 14.19 | 501 | 0.286 |

Each cell is the pass count, then the median in brackets. Heading passed
10/10 at every checkpoint.

**The fine-tune does not reach the cat's walk spec in 150 iterations.**
- No checkpoint passes a seed. `steps` is 0/10 throughout: the cat
  shuffles, its feet clearing 2–5 mm against the 7.7 mm the spec asks
  (0.02 of a 386 mm hip height).
- Survival in the engine's evaluation peaks at 75 (7/10, median episode
  10 s) and then falls to 0/10 at 125 and 150. Every seed ends `collapsed`
  (COM below 250 mm) inside 2.5 s, before the first shove at 3 s.
- The trainer's numbers keep climbing all the while: reward 12.0 → 14.2 a
  step and mean episode 467 → 501 steps from 75 to 150. Its own
  deterministic witness rollouts collapse as well (110 steps at 125).
  The sampled policy (σ rising 0.205 → 0.286) survives in training, and its
  mean action does not. **The trainer's curve is not a proxy for the spec
  on the cat.** Judge the checkpoints, as O6 says.
- Drives came within rated (10/10 at 125 and 150, worst 0.88) from 2.18×
  zero-shot.

**The proof is not met yet on the cat.** Its other half, a cold `b3_walk`
run on the cat by the B1 recipe (300 iterations), has not run. If the cold
run passes by 300, the fine-tune has already failed the "half the
iterations" bar (no pass by 150). If it does not pass by 300, the bar is
not decidable on this pair. On v0, the zero-shot base passed and fine-tuning
made it worse (b3-ft250, above). On the cat, the base walks no seed
zero-shot and 150 fine-tune iterations reach none either. The cat is 3×
the family's heaviest member and 8% above its tallest hip, so it lies
outside the base's range.
