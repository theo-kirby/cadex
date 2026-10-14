# Goal: A big cat that runs like one

Verified against source: 2026-10-14. Operator charter for orun6, following
orun5 (`.ouroboros/history/orun5.md`) and the owner's panel-cat projects. The
human owns this file; unattended roles never edit it.

## Mission

The panel-cat project designed a robot big cat the owner likes: about 26 kg,
0.5 m legs, white form-fitting panels, CubeMars quasi-direct drives. Teaching
it to run then failed in a way that more training will not fix. Twelve
training runs and ten reward revisions produced a lunge, a three-legged skate,
a dive, a wheelbarrow and a nose-dive, each a loophole in a reward that
*describes* a gait. The best policy passes its spec as a short, twitchy trot
at 1.7 m/s, and every gallop attempt nose-dives with the front drives at
their torque limit.

The diagnosis (the owner's review, 2026-10-14), ranked:

1. **The machine is under-torqued for a gallop.** It has roughly a third of
   the torque, per unit of weight times leg length, of a Mini Cheetah-class
   robot, and its legs are heavy at the far end (a drive at every wrist, legs
   55 % of the mass). A cheetah keeps its mass near the body.
2. **The reward describes a gait instead of showing one.** There is no
   reference motion, so PPO finds the cheapest motion that pays.
3. **There are no smoothness terms, and the task language cannot express
   several.** There is no previous-action channel and no foot contact, and
   there are caps of 64 observation channels and 128 expression nodes.
4. **The spec measures what is easy, not what is cat-like.** An ugly trot
   passed.
5. **The trainer has never been benchmarked** on a quadruped whose good
   result is known, so nobody knows how much of the failure is the trainer.
6. **The loop is slow.** It tests about one hypothesis an hour, and any
   change to mass or drives costs a full CAD rebuild.

This run builds the pipeline that fixes this, then proves it on the cat.

If the run achieves only one thing, it is this: **the cat, redesigned to be
buildable from real drives, trots smoothly by tracking a procedurally
generated gait reference, and passes a spec that judges how the gait looks
as well as what it achieves.**

Priority, in order: H1 (always on), B1, T1, G1, G2, D1, P1, P2, C1.

## Reference project

`~/cadex-projects/panel-cat-3-run` is the reference. Read `DECISIONS.md`
(D14–D27 are the training story), `docs/actuators.md`, `script.py`, and
`runs/*/train/train.log` for the curves. Its run-r5 checkpoint 300 (a trot
that passes D16's spec) is the **baseline** that every smoothness and
gait-quality number is compared against.

The project is read-only. Work on a copy, `~/cadex-projects/orun6-cat`. Copy
it without `runs/` and `evaluations/` if size matters. Nothing in Cadex names
the reference project or reads it at run time.

## Owner decisions

- **O1. Buildable.** The cat must be buildable from real, purchasable parts.
  - New drives, gearboxes, belts or linkages may be added to the library
    where they are within reason: commercially available, priced, at a
    robot hobbyist's or lab's scale, with datasheet-cited specs (peak and
    rated torque, speed, mass, dimensions).
  - A drive's simulated limits are its datasheet's, never stronger.
- **O2. The reference is procedural.** Gait references are generated from
  biomechanics: footfall order, duty factor, phase offsets, stride length
  and frequency scaled by Froude number, spine flexion, and body pitch.
  - They are mapped onto the robot's own legs by inverse kinematics within
    its joint limits.
  - No motion-capture dataset and no video pose extraction.
- **O3. Keep the cat's look and stature.** The owner likes panel-cat-3's
  shape, form and stance. Mass, drives, drive placement and internal
  mechanisms may change. Panels follow the mechanism, as the creature style
  says.
  - A change of overall scale is a last resort.
  - It is allowed only if D1 shows no reasonable drive makes the gait
    feasible at this size, and it is recorded with the numbers.
- **O4. Cadex stays general.** Gait references, motion tracking and
  gait-quality metrics are general locomotion features, not a biomimicry
  fork.
  - Whatever would be wrong for a wheeled base, an arm or a crane goes in a
    style (`CadexAgentStyle.creature.md`) or in `training/`, not in the
    base guidance.
  - The engine never imports JAX or MJX (ADR-084).

## Done criteria

Each criterion needs a causally parented governor record with measured
evidence. The human owns the checkboxes. Roles report results and do not
tick them.

- [ ] **H1. A live progress page the owner watches.**
  - `~/orun6-progress/site/index.html` is a self-contained static page,
    already served on the tailnet at `/orun6/`. The page and its assets live
    only in that directory and are never committed.
  - **Every iteration ends by updating it**, accepted or not. It shows:
    - each criterion's state, with its latest evidence;
    - a timeline of iterations: what was tried, the result, and the next
      step;
    - the latest numbers;
    - visuals: training curves, gait diagrams (footfall plots), joint
      trajectories against the reference, still frames or short videos of
      rollouts, and the reference beside the policy.
  - The page uses the dashboard's dark palette, carries a `refresh` meta of
    60 s, and shows the time it was written.
  - Failures and dead ends go on the page as plainly as successes.
- [ ] **B1. The trainer is benchmarked against a known-good quadruped.**
  - Pick a quadruped with a published, working RL recipe, for example MuJoCo
    Menagerie's Unitree Go1 or Go2 with MuJoCo Playground's joystick task.
    Run that recipe on this box in a separate venv, fetched at run time and
    never committed, for its numbers: sample count, wall time, the gait it
    reaches.
  - Train the same robot through Cadex's trainer. The robot is either
    converted to a task bundle, or rebuilt in xscript with matching masses,
    lengths and drives; the record says which and why.
  - The record states both results side by side: speed, smoothness
    (action-rate and joint-acceleration RMS), samples and wall time. Each
    gap is closed or explained.
  - Trainer changes that close a gap carry an ADR, for example: the sample
    budget, network size, observation history, reward and observation
    normalisation, symmetry, or regulariser terms.
- [ ] **T1. The task language can say "smooth" and "foot down".**
  - A previous-action (or command-rate) channel.
  - Foot contact for the reward and the critic. It is privileged unless a
    real sensor grounds it (a contact switch or a load reading).
  - The standard regularisers expressible as reward terms: action rate,
    joint acceleration, torque or energy, and foot slip.
  - Where the 64-channel or 128-node caps block a standard locomotion
    reward, they are raised with an ADR stating why the new number is safe.
  - Each has tests; `describe_api`, `docs/XSCRIPT.md` and `docs/MUJOCO.md`
    describe it.
- [ ] **G1. A procedural gait reference generator.**
  - Input: a gait name or explicit parameters (walk, trot, pace, canter,
    transverse and rotary gallop, half-bound, bound) and the robot's leg
    chains.
  - Output: a periodic reference clip of joint angles, foot positions,
    contact schedule, and body height and pitch, inside every joint limit.
    Where IK cannot reach, it says so and does not clamp silently.
  - Stride frequency and length scale with Froude number and leg length,
    and the record cites the biomechanics sources used.
  - The clip can be put in a task bundle and played on the dashboard as a
    kinematic rollout, so the owner can see the intended gait before
    anything trains.
  - Tests: the footfall phase offsets and duty factors match the requested
    gait; IK foot positions round-trip within tolerance; an unreachable
    stride is refused with a reason.
- [ ] **G2. Tracking reward and gait-quality metrics.**
  - A reward term (or terms) that pays for tracking the reference,
    phase-aligned to the task's gait clock: joint pose, foot height and
    contact schedule.
  - Evaluation predicates measured from the trace (orun5 A3), each with
    tests:
    - footfall pattern against the reference (phase offsets and duty
      factors);
    - phase-aligned joint RMS error from the reference;
    - smoothness: command-rate RMS and joint-acceleration RMS;
    - cost of transport;
    - each drive's RMS torque against its rated (continuous) torque, and
      its share of time at the peak clamp.
  - Measured on the r5 baseline, recorded as the "before" numbers.
- [ ] **D1. What the cat needs to gallop, measured, and the library to
  build it.**
  - A fast proxy loop: the cat's exported model with masses, link lengths,
    drive limits and drive placement as parameters, trained without a CAD
    rebuild. Screening runs are small enough that several fit in the time
    of one full run.
  - A sweep over drive torque and speed, distal leg mass (for example a
    proximal drive with a belt or pushrod to the wrist or hock, using
    ADR-593's closed linkages), and total mass, with reference-tracking
    screening runs for trot and gallop.
  - The result is a table and a plot: which configurations hold the gait
    within the drives' peak and rated torque.
  - The drives and mechanisms the chosen configuration needs are added to
    the library, real and datasheet-cited (O1). Each has an ADR and tests.
- [ ] **P1. The cat trots well.**
  - On `orun6-cat`, the design is changed to D1's chosen configuration
    (O1, O3), rebuilt and clearance-checked. The panels still fit, and the
    joint sweep passes.
  - A trot policy trained with G1's reference and G2's tracking reward
    passes, on the 10 frozen seeds:
    - the reference project's D16 run spec, every predicate (completes,
      tilt ≤ 30°, heading ≤ 25°, speed ≥ 1000 mm/s, duty factor ≤ 0.5,
      steps ≥ 10, slip ≤ 0.3);
    - a trot footfall pattern: diagonal pairs within ±0.1 of a cycle;
    - command-rate RMS and joint-acceleration RMS **at most half** the r5
      baseline's;
    - every drive's RMS torque within its rated torque.
  - The phase-aligned joint RMS bound is stated in the record before the
    first P1 training run, and it is never loosened to pass a policy.
  - A side-by-side film of the reference and the policy is on the page,
    and the owner judges the look.
- [ ] **P2. The cat gallops.**
  - Starting from P1's policy (curriculum allowed), a gallop or half-bound
    policy passes, on the 10 frozen seeds:
    - completes, tilt ≤ 30°, heading ≤ 25°;
    - mean forward speed ≥ 2500 mm/s;
    - a gallop or half-bound footfall pattern with a flight phase in
      every stride;
    - P1's smoothness bound;
    - every drive within rated RMS torque, and at its peak clamp for no
      more than 10 % of the episode.
  - If D1 shows the gallop is infeasible with any reasonable drive at this
    size, the record says so with the numbers and the best gait reached.
    That is reported as unmet, not redefined.
- [ ] **C1. Closing report.**
  - `docs/probes/orun6/REPORT.md` covers:
    - B1's benchmark table;
    - each new capability, with a plot or still;
    - D1's table and the chosen design;
    - P1's and P2's results against the r5 baseline;
    - the guidance added;
    - every ADR;
    - the remaining defects and what the next run should do.
  - Reconcile, then claim done for critic review without ticking the owner
    boxes.

## Later criteria

Not seeded. Work them only once every criterion above has evidence.

- An adversarial motion prior (AMP) style reward from G1's clips, compared
  with plain tracking on the same gait.
- Jumping, recovery from a push, and gait transitions on command.

## Horizon ladder

- **short-term:**
  1. H1's first page, then keep it current every iteration.
  2. Read the reference project's training story, and measure the r5
     baseline's smoothness and drive efforts (the "before" numbers).
  3. B1: the benchmark robot and recipe, and the first side-by-side numbers.
  4. T1: previous action, contact, and regularisers.
- **medium-term:**
  1. G1: the generator, its tests, and a reference trot played on the
     dashboard.
  2. G2: the tracking reward and gait-quality predicates.
  3. D1: the proxy loop, the sweep, and the library additions.
- **long-term:**
  1. P1 on the redesigned cat.
  2. P2.
  3. Base and creature guidance:
     - how to state a gait;
     - when to track a reference;
     - how to check drive torque against a gait before training.
     Every rule general, with its reason (O4).
  4. C1, and every gate green, every doc true, `STATE.md` reconciled.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries.
  - The repository carries no GPL or AGPL code. A fetched benchmark
    (Menagerie, Playground) lives outside the repo and is never vendored;
    its licence is recorded.
  - Training stays offboard in `training/`, whose `cadex_train.py` imports
    only the standard library at module scope.
  - `CadexDynamics.py` stays unreachable from `cadexd` (ADR-102).
  - `analysis/` imports no GPL package.
- Never commit any of the following:
  - secrets or private hostnames;
  - build outputs;
  - full transcripts;
  - policy binaries, checkpoints or rollout traces;
  - fetched third-party models.
- Do not hand-edit `STATE.md`, `PLAN.md` or state nodes.
- **Keep earlier projects read-only:** every project in `~/cadex-projects`
  except `orun6-*` copies, which are this run's.

**This run:**
- **One training run at a time on the 5090.** The machine lock is the
  arbiter.
  - D1's screening runs are sized to share the GPU in sequence, not in
    parallel.
  - The CLI suite runs with the GPU hidden, so it never collides with a
    training job.
- **Long training does not block an iteration.** `cadex train` detaches
  under its supervisor. An iteration may start a run and end; a later
  iteration reads the result. CPU work (code, tests, CAD) proceeds while the
  GPU trains.
- **The protocol and tool surface stay a contract.**
  - Every `OP_ARG_SPECS` change updates `docs/INTEGRATION.md` in the same
    commit.
  - A tool change goes only through AGENTS.md's rule.
- **The dashboard stays read-only.**
  - A reference clip is played from what `/api/project` serves, with a
    browser test and `docs/DASHBOARD.md` in the same commit.
  - The actor may serve the dashboard on 127.0.0.1 for its own tests. It
    never runs `tailscale serve` and never binds a public address.
- Committed images are PNG, ≤300 KB each, under `docs/probes/orun6/`.
  Renders use the dark floor.
- No role starts, stops or restarts the loop or signals its process.

## Owner notes

- **Gates run in the foreground.** The session ends when the actor's turn
  ends. Every gate is a foreground command that finishes within the shell's
  10-minute limit. Write the record and the handoff before a long gate, then
  amend them with the result.
- **Keep the suites light.** New tests are fast unit tests where a unit test
  makes the claim, with at most one real-engine end-to-end test per
  criterion.
- **A trainer OOM killed the whole loop once (iteration 6).**
  - The B1 Go1 run at `--envs 8192` reached 41 GB of host memory before
    iteration 0, and the run's 40 GB cap killed every process in the loop.
    The cause is in `training/cadex_train.py`: `randomised_models` builds
    one host `MjModel` per environment, so host memory scales with the env
    count times the model's size (meshes included). Fixing or bounding that
    is B1 work, with an ADR.
  - Until it is fixed, size `--envs` from a measured smoke run.
  - Start every training run longer than a smoke in a scope of its own,
    for example `systemd-run --user --scope -p MemoryMax=30G ...`, so an OOM
    kills the trainer and not the loop.
- **A reward exploit is a finding, not a puzzle.** When a policy games a
  term, prefer more reference (tracking) over another hand-written penalty.
  Record the exploit either way.

## Question policy

- Resolve reversible choices autonomously, using the smallest measured step
  towards the highest-ranked open criterion.
- **Is it real hardware?** A drive or sensor no one sells is privileged
  (sensor) or refused (drive). When unsure, record why.
- **Base, style, or `training/`?** Apply O4.
- Where O1–O4 and a measurement disagree, record both and follow O1–O4.
  They are the owner's to change.
- Code and accepted artifacts outrank docs. Update the docs with the
  behaviour they describe.
- A pre-existing test failure is recorded and left alone, unless the unit's
  own change touches it.
- A harness or usage limit is not an attempt: keep the receipt and wait for
  capacity.
- Never invent a measurement, never weaken a test or a spec to pass, and
  never wait for a human.

## Exhaustion policy

`report_done`.
- Once H1, B1, T1, G1, G2, D1, P1, P2 and C1 have evidence, write the
  closing report, reconcile and claim done. Two consecutive critic
  acceptances stop the run.
- Do not claim done while any criterion is unmet unless the run's wall-clock
  stop is near. Until then, work the highest-ranked open criterion, then the
  long-term rung.
- If the stop arrives first, report how far each criterion got and what is
  left. Do not redefine success.

## Quality bar

- At every accepted commit that touches code, run:
  - `pixi run test-engine`;
  - `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`;
  - for `training/` changes, its tests from the training venv as well.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine` before
  the CLI's engine-needing tests count. For protocol or payload changes,
  rebuild and stage, then run the packaged lifecycle gate.
- Every bug fix has a test that fails without it.
- Every new channel, reward term, predicate, library part and trainer change
  has an ADR, starting at ADR-694.
- Every iteration that changes code leaves a record.

## Reconcile

- Every five work iterations or three unreconciled records:
  - fold impacts;
  - advance the high-water mark;
  - regenerate the views;
  - export and check.
- The separate maintainer and planner roles stay off. The critic names the
  next unit.
- Unattended roles never edit this charter.
