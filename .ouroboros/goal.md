# Goal: a fast, general, watchable design-to-policy loop for Cadex

Verified against source: 2026-10-28. Operator charter for orun21, a Cadex-wide
run on `main` (merged at `9ebef99a` plus ADR-900). It follows orun20 in this
repo and the project runs l4r1/l5r1 (leon IV, leon V), which ran in their own
repositories.

## Mission

Cadex can design a robot and train it, but each robot has needed its own pile
of tools, its own training recipe and a person checking whether the dashboard is
telling the truth. Before the robots get stranger, the loop itself has to get
fast, general and visible. This run works on the **engine, the trainer and the
dashboard**, not on any one robot. Robots are proving grounds only.

1. **Iteration speed.** Measure where the time goes in one design-to-policy
   iteration, then cut the biggest sinks. Candidates, none assumed: build time,
   the training models' speed, training budgets, how a run is judged and how the
   next step is chosen, docs agents read every turn, and suites or gates that
   cost more than they protect.
2. **One route from spec to policy, in Cadex.** Today's three tiers are:
   - **concept:** `training/cadex_concept.py` (ADR-834), boxes and capsules
     from a spec;
   - **training model:** a fast MJCF derived from the CAD export (floor
     contacts only, merged static bodies, a cheap solver), which lives only in
     leon V's `tools/training_model.py` with its fidelity check and benchmark;
   - **engine MJCF:** the full CAD export, the judge.

   About 12,000 lines of judges and tools were copied from leon IV to leon V
   rather than shared. Make this one documented route in Cadex, and decide,
   with evidence, whether the tiers stay separate, merge or change. The owner's
   view to test: production CAD need not mix with training until late, provided
   the stand-in models are faithful and train fast.
3. **A dashboard that tells the truth, whoever drove the work.** A run started
   by Ouroboros, an MCP agent, a `cadex` command or a bare `cadex_train.py`
   call must show the same thing: designing while designing, training with
   live telemetry while training, its checkpoints and rollouts, and the CAD on
   the bodies when the model came from CAD.
4. **Go-to-point as the general locomotion task.** One policy, many skills. A
   point lights up on the floor and the robot walks or runs to it, turning
   round when it is behind or to the side, holds there, and goes on to the
   next point, which may be another colour for another speed. This replaces
   training a right turn, a sprint and a stand as separate skills.
5. **A general terrain and obstacle system.** Bumps and hills, slopes, steps,
   boxes to climb or jump onto, walls and a small maze, and courses from a
   mesh or heightfield, with a curriculum. One source of truth for the engine
   and the trainer, usable for training and for held-out evaluation.
6. **A recipe that generalises, from research.** Read how MuJoCo Playground,
   legged_gym / Isaac Lab and published work set up commands, terrain,
   curricula, observations and budgets. Find where Cadex does slow or unusual
   things, fix them, and write the result as the recipe a new robot follows.

If the loop achieves only one thing, it is **the dashboard's run contract (D1)
and go-to-point training on the Go1 reference (G2)**: everything else is judged
by watching runs, and go-to-point is the task every later robot uses.

## The proving machines

Read-only originals; the run works on copies in `~/cadex-projects/orun21-lab/`.
- **Go1, the fixed reference.** Playground's Go1 joystick, as orun18 brought it
  through Cadex (`docs/probes/orun18/a2_bundle.py`, `go1_judge.py`; our
  trainer is within 6% of Playground on it). Every recipe change is first
  measured here, against a number that does not move.
- **leon V**, `~/cadex-projects/leon-v` (main, `4d67e21`): its D1/E1 concept
  specs (`concept/`), its frozen CAD (`docs/frozen-body.json`), and its
  derived training model. The QDD creature (B2), and the only robot with all
  three tiers.
- **The biped**, `~/cadex-projects/orun9-biped`: RECIPE.md's `b1-b1`, 10/10 at
  iteration 100. The odd body: anything claimed as general must also work here,
  with no bespoke tools.

## Done criteria

Rung 1: measure and see.

- [ ] **M0. Where an iteration's time goes.** `docs/probes/orun21/ITERATION.md`
  breaks a design-to-policy iteration into its parts with measured wall times:
  - from the logs of l4r1, l5r1 and orun20 (`runs/*/` in each repo): actor
    turn, critic and scribe, builds, exports, compiles, training, judging, and
    waiting on usage;
  - timed fresh: a warm and a cold build of leon V and of the biped; steps/s of
    each tier for leon V and of the Go1; a full suite run of each suite;
  - what an actor reads per turn, in tokens: the docs, the memory, the tools'
    output.

  It ends with the sinks ranked by time saved per unit of work, and states which
  ones S1 takes on.
- [ ] **R1. The research.** `docs/probes/orun21/RESEARCH.md`, with sources
  (paper, repository and commit, or doc page), covers:
  - command and goal sampling, including position or waypoint goals: velocity
    commands plus a go-to-point layer, against end-to-end position targets
    (Rudin et al. 2022);
  - terrain generation and curricula (legged_gym's game-inspired curriculum,
    Isaac Lab's terrain generator, Playground's rough-terrain tasks), and how
    Playground runs heightfields in MJX;
  - observation, action, reward and budget defaults, and domain randomisation;
  - a table of where Cadex differs from that practice, each row marked keep
    (with the reason), change (and which criterion changes it) or test.
- [ ] **D1. One run contract, whoever starts the run.** The trainer itself
  writes what the dashboard needs, so no driver has to: a run record at launch
  and at the end, a heartbeat that stays live through a long compile, the
  model's digest, checkpoints where the dashboard finds them, a closing view,
  and a map from each MJCF body to its CAD parts. The dashboard reads it
  wherever the run sits under `runs/` (including `runs/<name>/seed*/` and
  nested stages), and the run picked shows its own state. When the run's model
  digest matches an accepted CAD revision, or the run was cut from one (the
  training model), the CAD is drawn on the bodies with the primitives as
  outlines. A concept run shows its primitives and says it is a concept.
  - Proven by three bare `cadex_train.py` runs started from a shell, each
    watched in the dashboard from launch to end: a leon V concept, leon V's
    CAD-derived training model, and the biped. Screenshots of each at
    launch, mid-run and end go on the run's page.
  - The HTTP API pin (`cli/tests`) gains the contract, with an ADR.
  - The `leon-iv-run-records` style of backfill is no longer needed: say so in
    the ADR.
- [ ] **D2. The rest of the dashboard, listed.** `docs/probes/orun21/DASHBOARD.md`
  ranks every remaining case where the dashboard shows an empty, stale or wrong
  state (the activity chip that ignores agent work, the projects page picking
  the wrong run, symlinked or outside runs, checkpoints with no rollout,
  anything found in use), each with its cause at file:line and a one-line fix.
  Fix the cheap ones; list the rest.

Rung 2: the route and the tasks.

- [ ] **P1. One route from spec to policy, in Cadex.** In `training/`, under
  ADR-084's rules (offboard, standard library at module scope, contract tests
  only):
  - the CAD export to fast training MJCF (leon V's `training_model.py`), its
    fidelity and standing check (`training_fidelity.py`), the throughput bench
    (`train_bench.py`) and the concept-against-CAD comparison
    (`cad_vs_concept.py`), each one command, generic over robots;
  - `training/RECIPE.md` states the route: spec, concept training, frozen
    numbers, CAD, the derived training model passing fidelity, the confirming
    retrain, judged on the engine MJCF;
  - leon V and the biped each go through it with only Cadex's tools. The biped
    has no concept spec: writing one from its CAD is part of the proof;
  - an ADR decides the tiers' shape (separate, merged or changed), from P1's
    measurements and M0's, not from taste.
- [ ] **S1. Faster iterations.** At least the three largest sinks M0 ranked
  are cut, or shown not cuttable with the reason. Each cut has a before and
  after on the same input, and an ADR for any removal. M0's table is re-run at
  the end and the total for a representative iteration (spec change to judged
  policy, on leon V's concept and on the CAD route) is reported against the
  start.
- [ ] **G1. A target the owner can see.** A go-to-point episode draws its
  targets: in the dashboard's viewport during playback and in a film, the
  current point lit, the next ones dim, each coloured by its commanded speed,
  and a hold shown as a ring that fills. The waypoint goal (ADR-751) is drawn
  today by nothing.
- [ ] **G2. Go-to-point on the Go1.** The easier route that gives the better
  result, chosen by R1 and stated in an ADR (expected: a velocity-command
  policy, omnidirectional with yaw rate, under a go-to-point layer; the other
  route is for later). The task family:
  - points ahead, to the side and behind, at walk and run speeds, with holds of
    a few seconds;
  - a new point appears when the robot arrives or the hold ends, not on a fixed
    clock;
  - the episode generator is one source used by both training and evaluation,
    seeded, with held-out sequences.

  Passes when, on 10 seeds of a held-out sequence of at least 8 points
  including at least two behind the robot: every point is reached within
  0.3 m, every hold stays within 0.15 m, the Go1 never falls, and speeds track
  within 15% of the command on the straight legs. The trainer's budget is
  stated in env steps and wall minutes against Playground's.
- [ ] **G3. Go-to-point on the other two.** G2's task, recipe and judge,
  unchanged except for the robot's speed bands, on leon V (concept, then the
  CAD-derived model) and on the biped. Report what had to change; anything
  robot-specific beyond speed bands and drive data is a defect in the recipe.
- [ ] **T1. One terrain system.**
  - One terrain spec compiles to geoms in the engine and in the trainer from a
    single source, or with a parity test that fails when they drift (STATE's
    open claim `shy-sky-8568`).
  - Kinds: random rough and bumps, slopes and hills, steps up and down, boxes
    to climb or jump onto, walls with a corridor or a small maze, and a course
    from a heightfield or mesh file. Not laid out only along x.
  - Levels and a curriculum, the way R1 found practice does it.
  - Heightfields either train in MJX (the open `winter-bay-5176`, fixed the
    way Playground's MJX tasks run them) or are replaced, with the reason.
  - The dashboard draws every kind.
- [ ] **T2. Go-to-point across terrain.** The Go1 trains on G2's task over
  T1's mixed pool and, on held-out courses at stated levels, reaches the
  points with G2's thresholds widened by no more than the ADR states. One
  sequence must pass a wall or maze section, so the points steer it round.
- [ ] **K1. The recipe, locked.** `training/RECIPE.md` is rewritten as the
  route a new robot follows: P1's tiers, G2's task, T1's terrain and the
  defaults from R1, each step with the run that proved it. The test: the biped
  is taken from its CAD through the recipe to G3 by following RECIPE.md alone,
  and every place the recipe was wrong or silent is fixed in it.
- [ ] **C1. Closing report.** `docs/probes/orun21/REPORT.md`: M0's before and
  after, the tier ADR, the go-to-point and terrain results per robot, what is
  still slow, and the recommended next run. The human owns this checkbox.

Beyond, in order, once the above are met or blocked:
- **E1.** The other go-to-point route (end-to-end position targets) against
  G2's, on the Go1, judged the same way.
- **J1.** Boxes to jump onto and gaps, on the Go1 and leon V's concept.
- **X1.** leon V's go-to-point policy trained on its CAD-derived model and
  confirmed on the engine MJCF, as P1's route says.

## Horizon ladder

- **short-term:**
  1. Copy the proving machines into `~/cadex-projects/orun21-lab/`; rebuild
     the Go1 bundle and confirm orun18's number on this checkout.
  2. M0 from the logs first (cheap), then the timed measures.
  3. D1, early: every later criterion is watched through it.
  4. R1, before G2's or T1's design is fixed.
- **medium-term:**
  1. G1 then G2 on the Go1.
  2. P1, porting leon V's tools and running leon V and the biped through it.
  3. S1 on the sinks M0 ranked; D2's cheap fixes.
  4. T1, then T2.
- **long-term:**
  1. G3 on leon V and the biped.
  2. K1 by following the recipe on the biped.
  3. C1, kept current; then the beyond list.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries.
  - The repository carries no GPL or AGPL code. Playground, legged_gym and
    Isaac Lab are read and cited, never copied into the tree; fetched files
    stay outside it.
  - `CadexDynamics.py` stays unreachable from `cadexd` (ADR-102); no `jax` or
    `mjx` under `src/Mod/cadex` (ADR-084).
  - The protocol and the agent's tool surface are contracts: change them only
    with their tests and an ADR.
- Never commit any of the following: secrets or private hostnames; build
  outputs; full transcripts; policy binaries, checkpoints or rollout traces;
  fetched third-party files.
- Do not hand-edit `STATE.md`, `PLAN.md` or state claims.

**This run:**
- **Where it writes:** this repository (branch `ouroboros/orun21`) and
  `~/cadex-projects/orun21-lab/`. Every other project, leon V and
  `orun9-biped` included, is read-only.
- **Remove more than we add.** A tool ported from leon V replaces its copies;
  a gate or test that costs more than it protects goes, with an ADR saying what
  it protected. Every removal is verified by build and both suites.
- **ADRs from ADR-837.** Every change of behaviour gets one in
  `docs/DECISIONS.md`, and the doc it touches is updated in the same commit.
- **Training.**
  - One GPU (the 5090). One training at a time unless the two fit; check
    `nvidia-smi` first.
  - Budgets: screens of minutes, Playground-sized runs (hundreds of millions of
    steps in tens of minutes) on fast models; never an hour-long run on the
    engine MJCF to answer a question a fast model can answer. Extend by warm
    start only while the curve still climbs.
  - Every run starts under `systemd-run --user --scope -p MemoryMax=30G` and
    is killed by PID when the unit's work is done; none is left running at the
    end of an iteration unless the report says it is meant to run on, and how
    the next iteration finds it.
- **Builds:** at most two at once, each FreeCADCmd under
  `ulimit -v 16000000`; a project's `agent.json` timeout stays ≤ 3600 s.
- **Images:** on the dark floor; committed PNGs ≤ 300 KB under
  `docs/probes/orun21/`.
- **The dashboard stays read-only.** The actor may serve it on 127.0.0.1;
  it never runs `tailscale serve` or binds a public address.
- No role starts, stops or restarts the loop or signals its process. Kill stray
  processes by PID, never with a broad `pkill` pattern.

## Owner notes

- The owner wants to train faster and better, and to lock in a recipe that
  generalises before the robots get weird. Speed is iteration speed overall,
  not only the trainer's: the trainer already matches Playground on the Go1.
- Go-to-point: whichever route is easier and gives the better result first;
  the other later, for completeness (E1).
- The dashboard does not need a dashboard-focused run: fix the run contract
  outright, list the rest, fix what is cheap.
- Lean suites (ADR-725): add a test only for a contract or a regression that
  actually happened.
- Useful from before:
  - l4r1's gap study (`~/cadex-projects/leon-iv/seed/MUJOCO-GAP.md`): our
    MJCFs were 70–200× slower per step than Playground's, policies lacked
    velocity and last-action observations, terminations were strict;
  - leon V's `docs/training-model.md`, `CONCEPT.md`, `CONCEPT-VS-CAD.md`;
  - the waypoint goal already in the engine (ADR-751: drawn on a clock, no
    arrival trigger, no marker, never trained to a result);
  - the box course and random pool (ADR-716/717/744/745) and the MJX
    heightfield failure (ADR-714, `winter-bay-5176`).

## Question policy

- Resolve reversible choices autonomously, with the smallest measured step
  towards the highest-ranked open criterion. The order is M0, D1, R1, G1, G2,
  P1, S1, D2, T1, T2, G3 on leon V, then K1's rewrite and C1, then the biped.
- **Owner, live edit (2026-10-29, after T2 closed):** the 7-day usage window
  will run out before the 24 h does, so protect the recipe and the report.
  After G3 on leon V, the next units are:
  1. **K1's rewrite:** `training/RECIPE.md` rewritten as the route a new robot
     follows, from what this run proved (P1, G2, T1, T2, R1's defaults), each
     step with its run. K1 stays unticked until the biped proof below.
  2. **C1:** `docs/probes/orun21/REPORT.md` written from what is measured so
     far, then kept current.
  3. **Then the biped:** G3 on the biped by following RECIPE.md alone, which is
     also K1's test; fix the recipe wherever it was wrong or silent.

  If usage stops the run before step 3, the recipe and the report are what
  it leaves.
- **Diagnose before repeating.** After three failed attempts at the same
  criterion, the next unit is a step back: re-read the evidence, write down
  what is binding and why, and change the approach, not the parameters.
- Do not copy a recipe "as it is" and then tune one knob at a time without a
  hypothesis; every change says what it expects to move.
- Code and accepted artifacts outrank docs.
- A pre-existing test failure is recorded and left alone, unless the unit's
  own change touches it.
- A harness or usage limit is not an attempt: wait for capacity.
- Never invent a measurement, never weaken a criterion to pass, and never wait
  for a human.

## Exhaustion policy

`report_done`.
- When every criterion has evidence or a recorded blocker, work the beyond list.
- Write C1 and claim done when the beyond list is done or blocked.
- Two consecutive critic acceptances stop the run.
- If the stop arrives first, report how far each criterion got. Do not
  redefine success.

## Quality bar

- At every accepted commit that touches code, run:
  - `pixi run test-engine`;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`;
  - the trainer's tests a change touches, from `~/cadex-train-venv` with
    `CUDA_VISIBLE_DEVICES=`.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine` before
  the CLI's engine-needing tests count.
- **The critic looks.** For D1, G1 and T1 it opens the screenshots and films
  and checks they show what the claim says (the run live, the CAD on the
  bodies, the lit point, the terrain kind).
- **The critic checks numbers at their source:** judge outputs, progress
  files and timing logs, not the report's prose.
- A pass is on held-out seeds and sequences the policy never trained on.

## Reconcile

- The scribe folds every five work iterations, or at three unfolded records:
  impacts applied, statuses set with evidence, `STATE.md` rendered,
  `ouroboros mem check` clean.
- Earlier runs' open claims stay open unless this run's work closes them with
  evidence.
- Unattended roles never edit this charter.
