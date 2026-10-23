# Goal: leo on sphere feet, speed first, then animal motion

Verified against source: 2026-10-23. Operator charter for orun19, a 24 h
run. It replaces orun18 (`.ouroboros/history/orun18.md`, merged at
`44ec3656`), which the owner stopped at 7.2 h to start this one.

**Why this run exists (owner, 2026-10-23).**
- **orun18 cleared the trainer.** The same Go1 model and task, trained
  through `training/cadex_train.py`, tracked within 6% of MuJoCo
  Playground's own recipe, in less wall time (A3, `docs/probes/orun18/a2.md`).
- **The gap is leo's body and task.** Two of orun18's leo results:
  - On speed alone, leo v05 holds a 2.59 m/s trot with 0/50 falls but does
    not track the command (`b1-s2-180.md`).
  - Imitating the dog capture, it gallops rotary but settles at 1.6–1.9 m/s
    whatever it is commanded (`c3-s1-50.md`).
- **Every leo policy ran on its toes with the hind paw pin shut**
  (`pin_stop.py`: at its stop on 0.72–0.86 of frames).
  - The cause is geometry, not the spring. The hind pad touches 15 mm
    behind the pin, so stance load locks the pin on its stop at any spring
    rate from 0 to 12 N·mm/deg (governor `tall-bay-3130`).
  - The Go1 that trained well has sphere feet.
- **The owner's decision: sphere feet.** No paw redesign. Leo gets the
  simplest foot, and the run asks what leo can do on it.

The human owns this file; unattended roles never edit it.

## Mission

1. **Build leo v06 on sphere feet.** Each of the four feet ends in one
   sphere and nothing else of the foot touches the ground. The hind paw pin
   and its spring are gone.
2. **Train leo v06 on speed alone and make it track the command.** Use
   orun18's B1 task, with no style terms, and compare it with v05's B1.
3. **Give it its gait from animal motion.** Use the dog (orun18 C3) and
   then the cheetah (orun18 C4) captures, retargeted to v06's legs and
   spine.

If the loop achieves only one thing, it is **leo v06 tracking a commanded
speed on sphere feet**: a speed table at four or more commands, beside
v05's B1.

## The machines

- **Leo is `~/cadex-projects/leo`**, at its current head (orun18's
  scripts). This run makes **one model change, v06 (O1)**, and then freezes
  it.
  - The `leo-v02` … `leo-v05` tags are never moved.
  - orun18's evidence on v05:
    - B1 is `runs/b1-s2/` at 180: 1.84 / 2.59 / 1.85 / 1.80 / 1.62 m/s at
      700 / 1500 / 2400 / 3500 / 5000 commanded;
    - C3 is `runs/c3-s1/` at 50;
    - the C4 bundle `c4-bundle` (e6a04ce8, cmd 4629–5328) was built but
      not trained.
- **The trainer** is `training/cadex_train.py`, from `~/cadex-train-venv`
  (brax 0.14.2, jax 0.7.2, mujoco-mjx 3.10.0), cleared by orun18 A3.
- **The motion:**
  - the AI4Animation dog (CC BY-NC 4.0) is in `~/mocap/`;
  - AcinoSet's cheetah (cited per orun18's D5a) is in `~/mocap/acinoset/`.

  The retargeting code is `docs/probes/orun18/retarget.py`,
  `acino_retarget.py` and `c3_bundle.py`. The licence terms in
  `docs/probes/orun18/SOURCES.md` carry over unchanged.
- **Measured on v05:** about 70–90 s an iteration at 4096 envs.

## Owner decisions

- **O1. Sphere feet (owner, 2026-10-23).** Leo v06 is v05 with all four
  feet replaced by spheres.
  - **Hind feet:**
    - the paw pin, its spring and damping, and the paw body are removed;
    - a sphere sits at the foot's end, the ball of the foot, where the pad
      was;
    - the heel's collision geometry comes off, or is shown clear of the
      floor through the whole judged gait.
  - **Fore feet:** the paw's capsules are replaced by one sphere at the
    same contact point.
  - **Everything else stays v05:** the drives, the push-rod loops, the
    spine, the tail and the head.
  - **Each sphere's radius and material** are the actor's choice:
    - stated with their reason, e.g. Go1's foot scaled to leo's mass;
    - the friction and contact settings follow the engine's defaults
      unless measured otherwise.
  - **The new parts are designed,** not stand-ins: a foot sphere is a
    real part (a rubber-capped hemisphere on the leg's end, as robot dogs
    use), so the renders read as a robot.
  - **The checks:**
    - the build passes `cadex clearance` and `--sweep` with no new pairs
      against v05's reports;
    - the stand holds for 3 s on every drive with no NaN;
    - the mass and the hip heights are reported against v05.

    Then the result is tagged `leo-v06`, and the model is frozen.
- **O2. Speed only means speed only (orun18's D4, kept).**
  - The task keeps:
    - the speed command and `track_speed`;
    - staying upright and alive;
    - torque, energy and action-rate regularisers;
    - terminations.
  - It drops every style term: the heel, paw, lag, sync, scuff and
    reference terms.
  - Footfall order, flight and stride are measured and reported, not
    rewarded.
  - Paw-pin and heel measures no longer apply and are not reported.
- **O3. Tracking means the command.** A speed policy "tracks" when its
  speed over the last 2 s of each judged seed is within 10% of the command
  at every judged command up to its top. Changes to make it track are, in
  this order:
  - the command curriculum and its sampling;
  - `track_speed`'s shape and weight;
  - the regularisers' weights.

  Each change is screened alone against the last, so the cause is known.
- **O4. Motion uses the legs and spine only.** The retargeted clips map
  onto v06's legs, spine and (where the capture has them) tail and head.
  - The capture's paw and digit angles are dropped; nothing maps to them.
  - The motion tasks follow orun18's D6: tracking plus speed plus O2's
    regularisers, with no style terms.
  - An adversarial motion prior (AMP) comes only if tracking proves too
    rigid, and it needs an ADR (from ADR-791) and its tests.
- **O5. Cold, sized, one trainer at a time (orun18's D7, kept).**
  - Every changed task or model trains cold.
  - Screens run 100–150 iterations and are judged at 50 and at the end.
  - Time the first ten iterations and set `budget_s` to the iterations
    asked for plus 20%.
  - Keep the GPU busy, with one trainer at a time.
- **O6. Torque, symmetry, a clean simulation (orun18's D8, kept).** Every
  judged number carries:
  - the worst drive's RMS over rated and its peak margin;
  - left against right;
  - which drives sit at their clamp, and on what share of frames;
  - no NaN, and the loops' closure (within 2 mm) reported.
- **O7. Straight lines, flat ground.** No turning, leaping or terrain.

## Done criteria

- [ ] **V1. Leo v06 on sphere feet** is built, checked and tagged `leo-v06`
  as O1 asks.
  - `docs/probes/orun19/leo-v06.md` gives:
    - each sphere's radius and reason;
    - what was removed;
    - the clearance diff;
    - the stand;
    - mass and hip heights against v05.
  - A render on the dark floor shows the new feet.
- [ ] **S1. Leo v06 on speed alone.**
  - It trains cold on orun18's B1 task (`b1-s2`'s weights, the paw-pin
    observations dropped), with speed commands up to 5 m/s, for 150–200
    iterations.
  - It is judged at 50 and at the end at 0.7, 1.5, 2.4, 3.5 and 5.0 m/s
    commanded, beside v05's b1-s2-180. Each judgement gives:
    - tracked speed (the last 2 s);
    - falls;
    - footfall order;
    - flight;
    - O6's numbers.
- [ ] **S2. It tracks the command.**
  - A v06 speed policy tracks (O3) at four or more commands from 0.7 m/s up
    to its top, with 0 falls on the judged seeds.
  - The report gives the top tracked speed and its Froude number, beside
    v05's B1 (Fr 1.73) and Go1's.
  - If S1 does not track, O3's changes are screened in order until one
    does, or until the remaining runs are spent; the report says what
    each moved.
- [ ] **M1. Leo v06 on the dog.**
  - orun18's C3 strides (gallop27/34/42) are retargeted to v06 per O4,
    with foot slip and limit violations measured.
  - It trains cold and is judged at three or more commands beside S1's
    best and v05's c3-s1-50, with whether the commanded speed is held.
- [ ] **M2. Leo v06 on the cheetah.**
  - orun18's AcinoSet strides are retargeted to v06 the same way and
    trained cold.
  - It is judged beside M1, S1 and v05's B1.
  - The report says which motion fits v06 better: foot misses, footfall
    order, held speed.
- [ ] **F1. The films**, on the run's page:
  - v06's new feet, standing;
  - S1 against v05's B1 at the same commands;
  - S2's tracked speeds;
  - M1 and M2 beside S1 at the slow and fast ends.
- [ ] **R1. The closing report.** `docs/probes/orun19/REPORT.md` gives:
  - each criterion's numbers;
  - whether sphere feet changed what leo can do, against v05, with what
    was not tested;
  - the next run's recommendation.

## Horizon ladder

- **short-term:**
  1. Write `docs/probes/orun19/leo-v06.md` before the build: what is
     removed, each sphere's radius and why, and the expected change in
     mass. Then build v06 (12–15 min, in the background), check it as O1
     asks, and tag it.
  2. Write S1's task on v06 from b1-s2's script, with the paw-pin
     observations and anything that reads the pin removed. Time ten
     iterations and launch it cold.
  3. While S1 trains: retarget the dog's C3 strides to v06 (O4) and build
     the bundle, then do the same for the cheetah's.
  4. Judge S1 at 50 with orun18's `speed_judge.py` and `b1_summary.py`,
     beside b1-s2-180.
- **medium-term:**
  1. S1 to its end, then S2: screen O3's changes one at a time until v06
     tracks.
  2. M1: train it cold and judge it beside S1 and c3-s1-50.
  3. M2: train it cold and judge it beside M1.
  4. F1's films on the run's page.
- **long-term:**
  1. A long run (200–400 iterations, warm on the same task) of whichever
     of S2 and M1/M2 reads best.
  2. Fold what this run proves into `training/RECIPE.md` (sphere feet,
     speed first, motion over reward terms) and the leo project's docs.
  3. If motion tracking proves too rigid: AMP (O4), with an ADR and tests,
     screened against M1.
  4. Keep every gate green, every doc true, `STATE.md` folded, and R1
     current.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries.
  - The repository carries no GPL or AGPL code.
  - Training stays offboard in `training/`, whose `cadex_train.py` imports
    only the standard library at module scope.
  - `CadexDynamics.py` stays unreachable from `cadexd` (ADR-102).
- Never commit any of the following:
  - secrets or private hostnames;
  - build outputs;
  - full transcripts;
  - policy binaries, checkpoints or rollout traces;
  - fetched third-party files: Menagerie models and meshes, motion
    capture, or anything derived from the capture data (CC BY-NC, and
    AcinoSet per orun18's D5a).
- Do not hand-edit `STATE.md`, `PLAN.md` or state claims.

**This run:**
- **Projects the run writes:**
  - `~/cadex-projects/leo`: the v06 model change (O1), then tasks only.
  - Every other project is read-only.
- **Motion data stays in `~/mocap/`.** The repository gets only
  retargeting code and hashes.
- **One training run at a time on the 5090.** The machine lock is the
  arbiter. The CLI suite runs with the GPU hidden
  (`CUDA_VISIBLE_DEVICES=`).
- **Long training does not block an iteration.**
  - Cadex runs start detached through `cadex_cli.loop` (`register`,
    `retain_training_view`, `launch`), so the dashboard follows them.
  - Never use a transient service: it kills the trainer.
- **Builds.**
  - A leo build takes 12–15 minutes and goes to the background.
  - The project's `agent.json` timeout stays at most 3600 s.
  - A direct `FreeCADCmd` runs under `ulimit -v 16000000`.
- **The protocol and tool surface stay a contract** (AGENTS.md).
  - An engine change gets an ADR from ADR-791 and the engine and CLI
    suites.
  - A `training/` change gets an ADR and the trainer's tests.
- **The dashboard stays read-only.** The actor may serve it on 127.0.0.1;
  it never runs `tailscale serve` or binds a public address.
- Committed images are PNG, ≤ 300 KB each, under `docs/probes/orun19/`, on
  the dark floor. Films live outside the repo and on the run's page.
- No role starts, stops or restarts the loop or signals its process. Kill
  stray processes by PID, never with a broad `pkill` pattern.

## Owner notes

- **The run's page is the owner's view.** The scribe keeps it, showing:
  - where V1, S and M stand;
  - each judged run's speed table beside v05's;
  - training curves;
  - the newest films.
- **Gates run in the foreground** and finish within the shell's 10-minute
  limit.
- **Lean suites (ADR-725).** Add a test only for a contract or a regression
  that actually happened.
- **What came before:**
  - **orun12–orun17:** about 60 h of style screens on feline v07 and leo
    v02–v05, with 0 criteria ticked.
  - **orun18:** the trainer was cleared. Leo's speed-only and dog-motion
    policies ran on their toes and did not track the command.
  - **Speed:** the best on any cat was 4.64 m/s, with few style terms
    (orun10).
- **Probes** to reuse:
  - `docs/probes/orun18/`: `speed_judge.py`, `b1_summary.py`, `froude.py`,
    `retarget.py`, `acino_retarget.py`, `c3_bundle.py`, `side_film.py`;
  - `orun14/stand_pin.py` (the stand);
  - `orun13/clearance_diff.py`.

  Put this run's probes under `docs/probes/orun19/`.
- **Engine caps:** 32 reward terms, 128 observation channels, 64 parameters
  per script (leo is at the cap, so new knobs are literals).

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion. The order is V1, S1, S2, M1,
  M2, F1, R1. Retargeting may be done at any time while something trains.
- Code and accepted artifacts outrank docs.
- A pre-existing test failure is recorded and left alone, unless the unit's
  own change touches it.
- A harness or usage limit is not an attempt: wait for capacity.
- Never invent a measurement, never weaken a criterion to pass, and never
  wait for a human.

## Exhaustion policy

`report_done`.
- Once every criterion has evidence, write R1 and claim done. Two
  consecutive critic acceptances stop the run.
- Until then, work the highest-ranked open criterion, then the long-term
  rung.
- If the stop arrives first, report how far each criterion got. Do not
  redefine success.

## Quality bar

- At every accepted commit that touches code, run:
  - `pixi run test-engine`;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`;
  - for `training/` changes, its tests from `~/cadex-train-venv`.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine` before
  the CLI's engine-needing tests count.
- **A judged run is reported with:**
  - its source checkpoint;
  - tracked speed per command;
  - falls;
  - O6's numbers;
  - the v05 run it is compared with.
- **The critic checks numbers at their source.** For every judged run, it
  opens at least one cited evaluation or judging output and checks the
  report against it.
- **The critic checks licences.** No capture data or derivative is
  committed.

## Reconcile

- The scribe folds every five work iterations, or at three unfolded
  records:
  - impacts applied;
  - statuses set with evidence;
  - `STATE.md` rendered;
  - `ouroboros mem check` clean.
- Earlier runs' open claims stay open and untouched.
- Unattended roles never edit this charter.
