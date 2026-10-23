# Goal: leo v06 on sphere feet: speed, then cheetah motion, then dog motion

Verified against source: 2026-10-23. Operator charter for orun19, a 72 h
run. It replaces orun18 (`.ouroboros/history/orun18.md`, merged at
`44ec3656`), which the owner stopped at 7.2 h to redesign leo first.

**Why this run exists (owner, 2026-10-23).**
- **orun18 cleared the trainer.** The same Go1 model and task, trained
  through `training/cadex_train.py`, tracked within 6% of MuJoCo
  Playground's own recipe, in less wall time (A3, `docs/probes/orun18/a2.md`).
- **The gap is leo's body and task.** On v05:
  - on speed alone, leo held a 2.59 m/s trot with 0/50 falls but did not
    track the command (`b1-s2-180.md`);
  - imitating the dog capture, it galloped rotary but settled at 1.6–1.9 m/s
    whatever it was commanded (`c3-s1-50.md`).
- **Every v05 policy ran on its toes with the hind paw pin shut.** The pad
  touched 15 mm behind the pin, so stance load locked the pin at any spring
  rate (governor `tall-bay-3130`).
- **So the owner redesigned leo before this run (v06, below):** sphere feet
  and heel pads, and no front wrists. The run trains it; it does not change
  it.

The human owns this file; unattended roles never edit it.

## Mission

1. **Make leo v06 track a commanded speed on speed alone.** Use orun18's B1
   task, with no style terms, and compare it with v05's B1.
2. **Give it a gait from cheetah motion.** Retarget AcinoSet's strides to
   v06 and train leo on them.
3. **Then from dog motion.** Do the same with the AI4Animation dog's
   strides, and compare the two.

If the loop achieves only one thing, it is **leo v06 tracking a commanded
speed**: a speed table at four or more commands, beside v05's B1.

## The machines

- **Leo is `~/cadex-projects/leo` at tag `leo-v06`** (project commit
  `356e547`, accepted revision `62e391eb`, script
  `~/orun19-queue/leo_v06.py`). **The model is frozen.** No model changes;
  new tasks are written in `script.py` as before.
  - The `leo-v02` … `leo-v06` tags are never moved.
  - v06's changes from v05 (owner, 2026-10-23):
    - **Hind feet:** the paw, paw pin, spring, toes and claws are gone. The
      metatarsus ends in a white ball, r 30 mm, and a white heel pad, r 16
      mm, sits on a short lever behind the hock.
      - Standing on the balls is the toe stance.
      - Near hock −40° ball and heel pad both touch, which is plantigrade.
      - Past that it rests on the heel.
    - **Fore legs:** the wrist drive (the second motor at the elbow), its
      crank, rod, pastern and the carpus pin are gone. The forearm runs
      straight from the elbow to a white ball, r 22 mm, at v05's standing
      height. Each fore leg has four drives: abduction, scapula, shoulder
      and elbow. The elbow keeps v05's travel.
    - **Hind hock:** unchanged. Both motors are at the knee and the
      parallelogram linkage runs down the inside of the shin.
    - **Totals:** 30.68 kg (v05 31.55) and 24 actuated drives (v05 26).
      Clearance: static pairs 14 → 6, swept pairs 8 → 0, no new pair.
    - **Tasks:** v06 builds only the `speed` task. Without the fore wrist
      the engine's trot (580 mm) and gallop (700 mm) reference gaits cannot
      be generated: the fore foot cannot lift 40 mm with scapula or elbow
      at a stop. So the orun8–9 trot-tracking tasks and the old gallop task
      are not built.
  - orun18's evidence on v05, for comparison:
    - B1 is `runs/b1-s2/` at 180: 1.84 / 2.59 / 1.85 / 1.80 / 1.62 m/s at
      700 / 1500 / 2400 / 3500 / 5000 commanded;
    - C3 (dog) is `runs/c3-s1/` at 50;
    - the C4 cheetah bundle was built on v05 and never trained.
- **The trainer** is `training/cadex_train.py`, from `~/cadex-train-venv`
  (brax 0.14.2, jax 0.7.2, mujoco-mjx 3.10.0), cleared by orun18 A3.
- **The motion:**
  - AcinoSet's cheetah (cited per orun18's D5a) is in `~/mocap/acinoset/`;
  - the AI4Animation dog (CC BY-NC 4.0) is in `~/mocap/`.

  The retargeting code is in `docs/probes/orun18/`: `retarget.py`,
  `acino_retarget.py`, `acino_strides.py`, `c3_bundle.py` and
  `queue_bundle.py`. The licence terms in `docs/probes/orun18/SOURCES.md`
  carry over unchanged.
- **Measured on v05:** about 70–90 s an iteration at 4096 envs.

## Owner decisions

- **O1. The body is v06, frozen.** No model changes this run.
  - A measurement that shows the body is the limit goes in the report as a
    recommendation for the next model.
  - A task that needs a model change is not written.
- **O2. Speed only means speed only (orun18's D4, kept).**
  - The task keeps:
    - the speed command and `track_speed`;
    - staying upright and alive;
    - torque, energy and action-rate regularisers;
    - terminations.
  - It drops every style term: the heel, paw, lag, sync, scuff and
    reference terms.
  - Footfall order, flight, stride and the heel pad's share of stance are
    measured and reported, not rewarded.
- **O3. Tracking means the command.** A speed policy "tracks" when its
  speed over the last 2 s of each judged seed is within 10% of the command
  at every judged command up to its top. Changes to make it track are, in
  this order:
  - the command curriculum and its sampling;
  - `track_speed`'s shape and weight;
  - the regularisers' weights.

  Each change is screened alone against the last, so the cause is known.
- **O4. Motion maps onto v06's joints.**
  - The cheetah's and dog's strides are retargeted onto:
    - v06's hind legs (hip, knee, hock), with the ball as the foot;
    - its fore legs (abduction, scapula, shoulder, elbow), with the ball as
      the foot and no wrist: the capture's carpus and digit angles are
      dropped, and the fore foot is fitted at the ball;
    - its spine and, where the capture has them, its tail and head.
  - The motion tasks follow orun18's D6: tracking plus speed plus O2's
    regularisers, with no style terms.
  - An adversarial motion prior (AMP) comes only if tracking proves too
    rigid, and it needs an ADR (from ADR-791) and its tests.
- **O5. Cold, sized, one trainer at a time (orun18's D7, kept).**
  - Every changed task trains cold.
  - Screens run 100–150 iterations and are judged at 50 and at the end.
  - Time the first ten iterations and set `budget_s` to the iterations
    asked for plus 20%.
  - Keep the GPU busy, with one trainer at a time.
  - A long run (200–400 iterations) is a warm start from a screen, on the
    same task.
- **O6. Torque, symmetry, a clean simulation (orun18's D8, kept).** Every
  judged number carries:
  - the worst drive's RMS over rated and its peak margin;
  - left against right;
  - which drives sit at their clamp, and on what share of frames;
  - no NaN, and the loops' closure (within 2 mm) reported.
- **O7. Straight lines, flat ground.** No turning, leaping or terrain.

## Done criteria

- [ ] **S1. Leo v06 on speed alone.**
  - It trains cold on orun18's B1 task (`b1-s2`'s weights, rebuilt on v06's
    24 drives), with speed commands up to 5 m/s, for 150–200 iterations.
  - It is judged at 50 and at the end at 0.7, 1.5, 2.4, 3.5 and 5.0 m/s
    commanded, beside v05's b1-s2-180. Each judgement gives:
    - tracked speed (the last 2 s);
    - falls;
    - footfall order and flight;
    - the heel pad's share of hind stance;
    - O6's numbers.
- [ ] **S2. It tracks the command.**
  - A v06 speed policy tracks (O3) at four or more commands from 0.7 m/s up
    to its top, with 0 falls on the judged seeds.
  - The report gives the top tracked speed and its Froude number, beside
    v05's B1 (Fr 1.73) and Go1's.
  - If S1 does not track, O3's changes are screened in order until one
    does; the report says what each moved.
- [ ] **M1. Leo v06 on the cheetah.**
  - AcinoSet's steady strides (orun18 C4's three slowest, and faster ones if
    v06 reaches them) are retargeted to v06 per O4, with foot slip and limit
    violations measured.
  - It trains cold and is judged at three or more commands beside S2's best
    and v05's B1, with whether the commanded speed is held.
  - A film shows it beside the retargeted clip.
- [ ] **M2. Leo v06 on the dog.**
  - orun18's C3 strides (gallop27/34/42) are retargeted to v06 the same way
    and trained cold.
  - It is judged beside M1, S2 and v05's c3-s1-50.
  - The report says which motion fits v06 better: foot misses, footfall
    order, held speed, torque.
- [ ] **L1. The long run.**
  - Whichever of S2, M1 and M2 reads best is trained long (O5), and judged
    at the end on the same tables.
  - The report says what the extra iterations bought.
- [ ] **F1. The films**, on the run's page:
  - v06 standing, then at its tracked speeds;
  - S against v05's B1 at the same commands;
  - M1 and M2 beside S at the slow and fast ends, and beside their clips;
  - L1 at its best.
- [ ] **R1. The closing report.** `docs/probes/orun19/REPORT.md` gives:
  - each criterion's numbers;
  - what v06's body allowed against v05, and what binds it now (drive,
    foot or stride);
  - what was not tested;
  - the next run's recommendation, including any model change the evidence
    asks for.

## Horizon ladder

- **short-term:**
  1. Write S1's task on v06 from b1-s2's script. Its paw-pin and wrist
     channels are gone with the model. Build it (12–15 min, in the
     background), time ten iterations and launch it cold.
  2. While S1 trains: adapt the retargeting to v06's legs (O4) and
     retarget the cheetah's strides. Measure slip and limits, film the clip
     and build the M1 bundle.
  3. Judge S1 at 50 with orun18's `speed_judge.py` and `b1_summary.py`,
     beside b1-s2-180.
  4. While M1 trains: retarget the dog's strides the same way and build the
     M2 bundle.
- **medium-term:**
  1. S1 to its end, then S2: screen O3's changes one at a time until v06
     tracks.
  2. M1: train it cold and judge it beside S2 and v05's B1.
  3. M2: train it cold and judge it beside M1.
  4. F1's films on the run's page.
- **long-term:**
  1. L1: the long run of whichever reads best, then judge it.
  2. If tracking motion proves too rigid: AMP (O4), with an ADR and tests,
     screened against M1.
  3. A second long run, or a screen that combines speed tracking with the
     better motion's clip, if L1 leaves a clear next step.
  4. Fold what this run proves into `training/RECIPE.md` (sphere feet,
     speed first, motion over reward terms) and the leo project's docs.
  5. Keep every gate green, every doc true, `STATE.md` folded, and R1
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
  - fetched third-party files: motion capture, or anything derived from the
    capture data (CC BY-NC, and AcinoSet per orun18's D5a).
- Do not hand-edit `STATE.md`, `PLAN.md` or state claims.

**This run:**
- **Projects the run writes:**
  - `~/cadex-projects/leo`: tasks only, on the frozen v06 model.
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
  - where S, M and L stand;
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
- **Probes to reuse:**
  - from `docs/probes/orun18/`: `speed_judge.py`, `b1_summary.py`,
    `froude.py`, `retarget.py`, `acino_retarget.py`, `acino_strides.py`,
    `c3_bundle.py`, `retarget_film.py`, `side_film.py`;
  - `orun13/clearance_diff.py`.

  Put this run's probes under `docs/probes/orun19/`.
- **Engine caps:** 32 reward terms, 128 observation channels, 64 parameters
  per script (leo is at the cap, so new knobs are literals).

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion. The order is S1, S2, M1, M2,
  L1, F1, R1. Retargeting may be done at any time while something trains.
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
