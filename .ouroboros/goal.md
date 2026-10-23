# Goal: why leo trains worse than a stock quadruped, settled in three steps

Verified against source: 2026-10-23. Operator charter for orun18, a 24 h
run. It replaces orun17 (`.ouroboros/history/orun17.md`, merged at
`6235e46f`), which the owner stopped at 11.3 h to run this diagnosis.

**Why this run exists (owner, 2026-10-23).**
- **What prompted it:** the owner saw a public clip. A stock Unitree Go2,
  in MuJoCo, chases a target at 2–4 m/s and jumps or ducks bars, trained
  "very fast" on one consumer GPU.
- **The owner's question:** is the gap to leo our framework, our training
  style, or our models?
- **The operator's read** (not yet measured; testing it is this run's job):
  - **Mostly the model and the task.**
    - Leo has 26 actuators, 59 joints, 4 push-rod loops, a sprung paw pin,
      drives at their clamp and about 30 kg. The Go2 has 12 actuators and
      ball feet.
    - We ask for a stylised gait through 18 reward terms and about 10
      pass/fail checks.
  - **Partly the training style:** stacking reward terms where the field
    imitates animal motion.
  - **Least the framework:** speed-only cats reached 4.2–4.64 m/s (orun7,
    orun10) on this trainer, and it is Brax PPO on MJX, the stack MuJoCo
    Playground uses.

**This run tests that read, in the owner's order.** The human owns this
file; unattended roles never edit it.

## Mission

Settle where the gap is, with measurements, in this order:

1. **Clear or blame the framework.** Train a stock quadruped from a
   published, known-good recipe (MuJoCo Playground's Unitree Go1 joystick).
   Then train the same robot on the same plain velocity task through
   Cadex's own trainer, on this machine, and compare.
2. **Find what leo can do with the style taken off.** Train leo v05 on
   speed alone (track speed, stay up, regularise), with no reference clip
   and no heel, paw or lag terms. The result is the body's ceiling, and
   what binds it.
3. **Give leo its style from animal motion, not from reward terms.**
   Retarget real quadruped motion capture to leo, train leo to track it
   alongside a speed command, and judge it on the same tables as orun17's
   best (sgt-4-120).

If the loop achieves only one thing, it is **step 1's verdict**: the same
robot and task trained both ways, with numbers that say whether Cadex's
trainer is the problem.

## The machines

- **The control robot is Unitree Go1, from MuJoCo Playground**
  (`mujoco_playground`, its `Go1JoystickFlatTerrain` environment and its
  published PPO config).
  - Playground ships a tuned recipe and published training times for Go1.
    It has no Go2 recipe the operator knows of. If the actor finds a
    published Go2 recipe of the same standing, Go2 may replace Go1.
  - The model comes from MuJoCo Menagerie, through Playground.
- **Leo is `~/cadex-projects/leo`**, at its current head (`3b0942b`,
  orun17's sgt-5 script). **The model is frozen at leo v05** this run: no
  model changes, because a diagnosis needs a fixed body. New tasks are
  written in its `script.py` as before.
  - The `leo-v02` … `leo-v05` tags are never moved.
  - orun17's best SG policy is `runs/sgt-4/train/` at 120 (judged
    `915a9863`, `docs/probes/orun17/sgt-4-120.md`):
    - 0.88 / 1.70 / 2.66 m/s at 700 / 1550 / 2400 mm/s commanded;
    - heel 0.00 / 0.00 slow, 0.31 / 0.38 fast;
    - U 0.13 / 0.24 fast;
    - rotary on 4 / 10 / 10 seeds;
    - hocks, wrists and `j_tail2` at their clamp on 0.13–0.80 of frames.
- **The trainer** is `training/cadex_train.py`, from `~/cadex-train-venv`
  (brax 0.14.2, jax 0.7.2, mujoco-mjx 3.10.0). It takes the task bundle a
  Cadex build writes (`<task>-task.json` with `model`, `actions`,
  `observations`, `reward`, `reference` and `tracking`).
- **Measured:** leo runs about 70–90 s an iteration at 4096 envs.

## Owner decisions

- **D1. Order.** The GPU work goes A, then B, then C.
  - B's first training waits for A's verdict.
  - C's first training waits for B's first judged run.
  - CPU work for a later step (fetching, reading licences, retargeting,
    writing tasks) may run while an earlier step trains.
  - If A blames the trainer, fixing it is the top of the frontier, and B
    runs on the fixed trainer.
- **D2. Like for like.** A's comparison holds the robot, the physics
  settings, the task and the wall-clock budget as equal as the two
  pipelines allow. Every difference that remains is listed, with its
  likely size:
  - timestep and substeps;
  - solver;
  - action space and PD gains;
  - observations and their noise;
  - reward terms;
  - episode length and termination;
  - envs, batch and PPO hyperparameters;
  - domain randomisation.
- **D3. Judge with one yardstick.** Both A policies are judged by one
  script on the same seeds and commands:
  - tracked forward speed over a 2 s window at three or more commands,
    up to the top of Playground's command range;
  - falls;
  - joint torque against the model's limits.

  The script is written by the actor, outside both pipelines.
  - Leo's B and C runs use the engine's evaluation (`gallop_spec`'s seeds),
    as before, plus orun17's `sg_tables.py`.
  - The trainer's reward is never a pass.
- **D4. Speed only means speed only.**
  - B's task keeps:
    - the speed command and `track_speed`;
    - staying upright and alive;
    - torque, energy and action-rate regularisers;
    - terminations.
  - It drops:
    - the reference clip's tracking terms;
    - `heel_pitch`, `heel_sched`, `paw_flat`, `paw_fold`, `overrun`, the
      lag and sync terms, `hind_scuff`;
    - every other style term.

  The heel, U and footfall order are measured and reported, not rewarded.
- **D5. Real motion, licensed.**
  - C's motion comes from a real-animal capture whose licence permits this
    use: a dog for certain, a cat if one exists.
  - The licence is read and recorded before any download is used.
  - The data stays outside the repository (`~/mocap/`); the repository gets
    only the retargeting code and its outputs' hashes.
  - If no usable licence is found, C stops there and the report says so.
- **D6. Tracking before AMP.** C first carries the motion as the task's
  reference clip, the path the trainer already has: tracking reward plus
  speed plus D4's regularisers, and no style terms.
  - An adversarial motion prior (AMP: a discriminator in `training/`) is
    the next step, only if tracking proves too rigid. It needs an ADR
    (from ADR-786) and its tests.
- **D7. Cold, sized, one trainer at a time (orun17's O8, kept).**
  - Every changed task trains cold.
  - Screens run 100–150 iterations and are judged at 50 and at the end.
  - Time the first ten iterations and set `budget_s` to the iterations
    asked for plus 20%.
  - Keep the GPU busy, with one trainer at a time.
  - Playground's Go1 run is sized by its own published config.
- **D8. Torque, symmetry, a clean simulation (orun17's O5, O6, O9,
  kept).** Every leo number carries:
  - the worst drive's RMS over rated and its peak margin;
  - left against right;
  - O9's checks (no NaN, loops within 2 mm reported, pin rate).
- **D9. Straight lines, flat ground.** No turning, leaping or terrain on
  leo. A's Go1 runs Playground's flat joystick task as published, turning
  commands included, and is judged on forward speed.

## Done criteria

- [ ] **A1. The reference.**
  - Playground's Go1 joystick (flat) trains from its published config in
    its own venv on this 5090.
  - The report gives:
    - wall time and env steps to its final policy;
    - steps per second;
    - D3's judgement: tracked speed at three or more forward commands,
      falls, torque.
  - The source versions are pinned in the report.
- [ ] **A2. The same robot through Cadex.**
  - The same Go1 model, on a plain velocity task, trains cold through
    `training/cadex_train.py` within twice A1's wall time.
  - The task is made as close to Playground's as the Cadex task format
    allows, by the smallest honest route:
    - a Cadex project that builds the Go1 from Menagerie's numbers;
    - or a task bundle written around Menagerie's MJCF;
    - or another route; the report says which was taken and why.
  - The report gives:
    - D3's judgement;
    - wall time;
    - steps per second;
    - D2's table of differences.
- [ ] **A3. The verdict.**
  - **Cleared:** A2's tracked speed is within 10% of A1's at every judged
    command, with no more falls, in at most twice the wall time.
  - **Blamed:** otherwise. The gap is then broken down by D2's list,
    each candidate tested by changing it alone, until one or two explain
    it.
  - If blamed, fixing the trainer comes next (a `training/` change with
    an ADR and the trainer's tests), and A2 is rerun on the fix.
- [ ] **B1. Leo on speed alone.**
  - Leo v05 trains cold on D4's speed-only task, with speed commands up
    to 5 m/s, for 150–200 iterations.
  - It is judged at 50 and at the end at four or more commands (at least
    0.7, 1.5, 2.4 and the fastest it holds). Each judgement gives:
    - tracked speed;
    - falls;
    - the footfall order it chose;
    - flight;
    - heel share and U per hind leg (reported, not required);
    - D8's numbers;
    - which drives sit at their clamp, and on what share of frames.
- [ ] **B2. The ceiling, read.** The report compares B1's top speed:
  - with orun17's best (sgt-4-120);
  - with the cats of orun7 and orun10;
  - with A's Go1, as a Froude number (v² / g·hip height);
  - and says what binds: a drive, the foot or the stride.

  If B1 shows the clip alone moves the gait, a reference-only variant (the
  clip's tracking terms plus D4, no style terms) may be screened to
  separate the clip from the terms.
- [ ] **C1. The motion and its licence.**
  - A real quadruped capture with a gallop or canter is found, its licence
    read and recorded in `docs/probes/orun18/SOURCES.md`, and the data
    fetched to `~/mocap/`.
  - Candidates to check first:
    - the AI4Animation dog capture (Zhang et al. 2018, mode-adaptive
      networks);
    - the retargeted dog clips of Peng et al. 2020 (`motion_imitation`).

    Neither licence is assumed.
- [ ] **C2. Retargeted to leo.**
  - The capture is retargeted to leo's joints and proportions:
    - foot contacts kept;
    - joint limits respected;
    - the spine mapped onto `j_spine` / `j_spine_yaw`.
  - The result is a reference the leo task can carry.
  - The route is the smallest that works:
    - a probe that writes the clip;
    - or an engine generator option (reference from a file), which needs
      an ADR from ADR-786 and the engine and CLI suites.
  - The report shows the retargeted clip against the capture (stills or a
    film), with foot slip and limit violations measured.
- [ ] **C3. Leo on animal motion.**
  - Leo v05 trains cold on the retargeted reference (D6: tracking + speed
    + D4's regularisers, no style terms) and is judged on orun17's SG/RL
    tables at three or more speeds, beside sgt-4-120 and B1.
  - Films show the three side by side, on the run's page.
- [ ] **F1. The films**, on the run's page:
  - A1's and A2's Go1 at the same command;
  - B1 at its fastest;
  - C3 against sgt-4-120 at the slow and fast ends;
  - the retargeted clip.
- [ ] **R1. The closing report.** `docs/probes/orun18/REPORT.md` answers
  the owner's question (framework, training style or model) with:
  - each criterion's numbers;
  - what was ruled out, and what was not tested;
  - the next run's recommendation.

## Horizon ladder

- **short-term:**
  1. Install Playground in its own venv (`~/playground-venv`). Pin its
     version. Launch A1 from its published Go1 joystick config, and time
     it.
  2. While A1 trains: read how Playground's Go1 task is built (timestep,
     substeps, action scale, PD gains, observations, noise, rewards,
     episode, PPO config). Write D2's table before building A2.
  3. Write D3's judging script and check it on A1's policy.
  4. Build A2 by the smallest honest route. Time ten iterations, launch it
     and judge it. Write A3.
  5. While A trains: search for the motion capture, read the licences, and
     write `SOURCES.md` (C1).
- **medium-term:**
  1. If A blames the trainer: test D2's differences one at a time until
     the gap is explained. Fix `training/` with an ADR and rerun A2.
  2. B1: write leo's speed-only task, train it cold and judge it at 50 and
     at the end. Then B2.
  3. C2: retarget the capture to leo, measure slip and limits, and film it.
  4. C3: train it cold and judge it beside sgt-4-120 and B1.
- **long-term:**
  1. If C3 tracks the motion but holds speed badly or too rigidly: AMP
     (D6), with an ADR and tests, screened against C3.
  2. A long run (200–400 iterations, warm on the same task) of whichever of
     B1 and C3 reads best, judged on orun17's criteria (SG, RL, P1, P2).
  3. Fold what this run proves into `training/RECIPE.md` (the control
     comparison, speed-only first, motion over reward terms) and
     `docs/MUJOCO.md` if the trainer changed.
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
  - fetched third-party files: Playground, Menagerie models and meshes,
    motion capture.
- Do not hand-edit `STATE.md`, `PLAN.md` or state claims.

**This run:**
- **Third-party software and data stay outside the repository.**
  - Playground goes into a new venv, `~/playground-venv`, never into
    `~/cadex-train-venv`, the pixi environment or any `requirements.txt`.
  - Menagerie and capture data go under `~/menagerie/` and `~/mocap/`.
  - `SOURCES.md` records each one's URL, version or commit, and licence.
  - Code copied into the repository from any of them needs a compatible
    licence and a `docs/PROVENANCE.md` line. Prefer writing our own.
- **Projects the run writes:**
  - `~/cadex-projects/leo`: tasks only, the model frozen at v05;
  - a new `~/cadex-projects/go1-control` if A2 takes the Cadex-project
    route.

  Every other project is read-only.
- **One training run at a time on the 5090.** This counts Playground's.
  The machine lock is the arbiter for Cadex runs; check `nvidia-smi` before
  a Playground launch. The CLI suite runs with the GPU hidden
  (`CUDA_VISIBLE_DEVICES=`).
- **Long training does not block an iteration.**
  - Cadex runs start detached through `cadex_cli.loop` (`register`,
    `retain_training_view`, `launch`), so the dashboard follows them.
  - Playground runs start in their own scope
    (`systemd-run --user --scope -p MemoryMax=30G ...`) with output to a
    log.
  - Never use a transient service: it kills the trainer.
- **Builds.**
  - A leo build takes 12–15 minutes and goes to the background.
  - The project's `agent.json` timeout stays at most 3600 s.
  - A direct `FreeCADCmd` runs under `ulimit -v 16000000`.
- **The protocol and tool surface stay a contract** (AGENTS.md).
  - An engine change gets an ADR from ADR-786 and the engine and CLI
    suites.
  - A `training/` change gets an ADR and the trainer's tests.
- **The dashboard stays read-only.** The actor may serve it on 127.0.0.1;
  it never runs `tailscale serve` or binds a public address.
- Committed images are PNG, ≤ 300 KB each, under `docs/probes/orun18/`, on
  the dark floor. Films live outside the repo and on the run's page.
- No role starts, stops or restarts the loop or signals its process. Kill
  stray processes by PID, never with a broad `pkill` pattern.

## Owner notes

- **The run's page is the owner's view.** The scribe keeps it, showing:
  - where A, B and C stand;
  - A's comparison table;
  - each judged run's speed table;
  - training curves;
  - the newest films.
- **Gates run in the foreground** and finish within the shell's 10-minute
  limit.
- **Lean suites (ADR-725).** Add a test only for a contract or a regression
  that actually happened.
- **What came before:**
  - **orun12–orun17 on feline v07 and leo v02–v05:** 0 criteria ticked
    across about 60 h of style screens.
    - The fold was cut by the paw spring (orun15).
    - The heel came to follow speed (orun17).
    - The slow fore still strikes twice a stride.
    - Drives sit at their clamp.
  - **Speed:** the best on any cat was 4.64 m/s, on its toes, with few
    style terms (orun10). orun7's gallop reached 4.2 m/s. Every rule
    added cost speed.
- **Probes** from earlier runs: `docs/probes/orun11/judge.py` (engine
  judging), `orun17/sg_tables.py` (SG/RL tables), `orun14/paw_floor.py`
  (U), `orun13/p2_lag.py`, `orun13/spine_foot.py`. Put this run's under
  `docs/probes/orun18/`.
- **Engine caps:** 32 reward terms, 128 observation channels, 64 parameters
  per script (leo is at the cap, so new knobs are literals).

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion. The order is A1, A2, A3, B1,
  B2, C1, C2, C3, F1, R1. C1 may be worked on the CPU at any time.
- Where a published recipe and Cadex's format disagree, write the
  difference down (D2) rather than silently picking one.
- A licence that is unclear counts as unusable.
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
  - for leo, D8's numbers and the SG/RL tables.
- **A comparison is reported with D2's table.** A difference left
  unlisted is a defect.
- **The critic checks numbers at their source.** For every judged run, it
  opens at least one cited evaluation or judging output and checks the
  report against it.
- **The critic checks licences.** No third-party file is committed, and
  `SOURCES.md` names a licence for everything fetched.

## Reconcile

- The scribe folds every five work iterations, or at three unfolded
  records:
  - impacts applied;
  - statuses set with evidence;
  - `STATE.md` rendered;
  - `ouroboros mem check` clean.
- Earlier runs' open claims stay open and untouched.
- Unattended roles never edit this charter.
