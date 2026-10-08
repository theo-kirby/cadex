---
node_id: 5a0a7b27-5fc2-5fee-8c52-365abf11ad4a
slug: honest-bay-2056
title: 'Ouroboros run: orun5 [3db04ab1] — operator directive'
created_at: '2026-10-07T17:56:35+00:00'
parents:
- odd-banner-6071
summary: ''
---
## What

Operator directive: an Ouroboros loop starts on this repo. Every work node of the run descends from this node.

## Why

The charter (the operator's goal document), verbatim:

# Goal: Sense the world, close the loop, judge the motion

Verified against source: 2026-10-07. Operator charter for orun5, following
orun4 (`.ouroboros/history/orun4.md`) and the owner's first two design
projects that were neither legged nor walking: a ball-balancing plate that
passed both of its tasks, and a tracked desktop excavator that stopped at a
~20 mm reach floor. The human owns this file; unattended roles never edit it.

## Mission

Both projects reached a good MVP, and both had to work around Cadex to get
there. The ball-plate agent faked a touch panel with two sliders and a
hidden bead, because Cadex has no sensor that reads where a free object is.
It built a serial gimbal because a pushrod linkage cannot be driven in the
exported simulation. It caught a policy that passed its spec by rocking,
because no predicate can say "it went round". The excavator agent's best
explanation for its precision floor is servo sag, which it could not test,
because the bus servo's load reading is not a channel.

This run removes those workarounds, so the next unusual machine is designed
as it would be built.

In priority order:

1. **Sense the world.** A grounded sensor for the position of a free body
   (a touch panel, a camera tracking a marker), and one for an actuator's
   load (the bus servo's load or current reading).
2. **Judge the motion.** Success predicates that measure what happened over
   an episode: laps or angular progress about a point, and a body's
   distance from a point. These replace the point-goal hack.
3. **Close the loop.** Closed kinematic chains (four-bars, pushrod cranks)
   export to MuJoCo and can be driven by an actuator on one of their joints.
4. **Goals relative to the machine.** A reach goal can be held in a body's
   frame, so a policy on a moving base sees its goal as the base sees it.

If the run achieves only one thing, it is this: **the ball-plate rebuilt
with a real ball rolling on a real plate, its position read by a grounded
sensor, trains its centring task to a pass.**

Priority, in order: S1, M1, S2, L1, R1 (capabilities), P1, P2 (proofs),
C1 (report).

## The reference projects

`~/cadex-projects/ball-plate` and `~/cadex-projects/excavator-mini` are the
references. Read both end to end: `script.py`, `DECISIONS.md`,
`docs/rejected.md`, `docs/actuators.md`, `docs/sensors.md`, `PROGRESS.md`,
`runs/*/` and `evaluations/*/`. Their workarounds are the requirements:

- ball-plate ADR-004: the ball on two sliders, because only `imu` and
  `joint_encoder` sensors exist (`_SENSOR_KINDS`,
  `src/Mod/cadex/cadex_assembly_api.py`);
- ball-plate ADR-002 and `docs/rejected.md`: pushrod tilt rejected, because
  closed loops cannot be actuated in the MJCF export;
- ball-plate ADR-005 and ADR-008: a `point` goal with `joint_fraction=0.01`
  to get a "distance from centre" metric, and circulation judged by hand
  from traces because no predicate measures it;
- excavator-mini ADR-015: a precision floor with two open hypotheses, servo
  sag (needs a load channel) and a goal fixed in the world while the base
  drifts (needs a body-frame goal).

They are read-only. They are evidence, never a dependency. Nothing in Cadex
names them or reads them at run time.

## Owner-revisable assumptions

- **A1. A grounded channel is real hardware.** A new sensor kind names what
  measures it on the machine: a catalog part where one exists, or a kind
  with a datasheet-like declaration (range, resolution, rate, noise) where
  not. The trainer adds that noise and quantisation. A sensor that no real
  part could be is privileged, not grounded.
- **A2. The simulator is MuJoCo, and the export is the contract.** Closed
  loops use MuJoCo equality constraints (`connect`, `weld`) in the exported
  MJCF. The exact-solid fit sweep must move a closed chain consistently, or
  refuse it with a reason; it never sweeps the joints of a loop
  independently.
- **A3. Predicates are measurements of the trace.** A new metric is computed
  by `CadexEvaluation` from the rollout's samples. It is not a reward-term
  total and not a judgement.
- **A4. The base guidance stays domain-neutral (ADR-560).** New rules about
  sensing, linkages and motion predicates go in the base, phrased for any
  machine. Nothing names a reference project.
- **A5. The tool surface does not grow for this.** Sensors, loops,
  predicates and goal frames are xscript API, reached through
  `describe_api` and the existing tools. A tool change goes only through
  AGENTS.md's rule.

## Owner notes

- **Gates run in the foreground (carried from orun4).** In this loop the
  session ends when the actor's turn ends. Never end a turn waiting on a
  background task. Every gate is a foreground command that finishes within
  the shell's 10-minute limit; `pixi run test-engine` and the CLI suite
  (GPU hidden) each fit. Write the record and handoff before a long gate,
  then amend them with the result.
- **Keep the suites light.** orun4 slimmed the CLI suite. New tests are
  fast unit tests where a unit test makes the claim; at most one
  real-engine end-to-end test per criterion.

## Done criteria

Each criterion needs a causally parented record with measured evidence.
The human owns the checkboxes. Roles report results and do not tick them.

- [ ] **S1. A grounded sensor reads a free body's position.**
  - A new sensor kind measures a body's position, and optionally its
    velocity, in the frame of a named component: for example a touch panel
    on a plate reading a ball's x and y, or a camera on a mast reading a
    marker. It declares range, resolution, rate and noise (A1), and the
    trainer applies them.
  - A body outside the sensor's range reads as out of range, which the
    task can terminate on. It never reads as a stale or a clamped value.
  - `describe_api`, `docs/XSCRIPT.md` and `docs/MUJOCO.md` describe it.
  - Tests: the channel matches the body's true position in the
    component's frame through a tilt and a turn; out of range is reported;
    noise and quantisation follow the declaration; a task naming the
    channel trains without the "ungrounded" refusal.
- [ ] **M1. Predicates measure the motion, not only where it ended.**
  - New evaluation metrics, from the trace (A3):
    - **angular progress about a point**: net signed turns of a body about
      a point and axis in a frame, and laps completed, so a body that
      rocks on an arc measures about zero;
    - **distance from a point**: a body's final and mean distance from a
      point in a frame, with no goal declared.
  - A spec can bound them like any metric. A metric that could not be
    measured fails (the `judge` rule, ADR-586).
  - Tests: a circling trace passes a laps predicate; a rocking trace on
    the same arc fails it; a trace that ends early fails rather than
    crashes.
- [ ] **S2. A grounded sensor reads an actuator's load.**
  - A new sensor kind reads an actuator's load: the force or torque it
    applies, as the bus servo or a current sensor reports it, with the
    declared resolution and noise (A1).
  - The catalog's bus servos say they report load; a hobby PWM servo
    does not, and declaring a load sensor on one is refused with a reason.
  - Tests: the channel tracks the actuator's applied force under a held
    load and saturates at the stall line; a PWM servo's load sensor is
    refused.
- [ ] **L1. A closed linkage exports and is driven.**
  - The assembly can declare a loop closure: two bodies joined by a
    constraint that closes a chain (A2). The MJCF export writes it as an
    equality constraint, and an actuator on one joint of the loop drives
    the whole chain.
  - The fit sweep moves the closed chain consistently, by solving the
    loop, or refuses with a reason that names the loop.
  - The smoke check holds a linkage steady, and the export's closure
    error stays within the MJCF pose tolerance (ADR-584).
  - Tests: a four-bar driven by its crank, and a slider-crank, each
    reaching the analytic output angle across the crank's range within
    tolerance; an over-constrained loop is refused.
- [ ] **R1. A goal can be held in a body's frame.**
  - A reach goal (point or pool) can be declared relative to a component,
    so it moves with that component. The policy's goal channel is then
    what the base itself would see.
  - The reach metrics measure against the goal where it actually was at
    each frame.
  - Tests: a goal on a drifting base stays put in that base's frame, and
    the final error is measured against it.
- [ ] **P1. The ball-plate, rebuilt as built.**
  - On a scratch copy (`orun5-ball-plate`), the ball is a free sphere
    rolling on the plate by contact, read by an S1 touch panel. No sliders,
    and no hidden bead.
  - The centring task trains and passes its spec, with distance from the
    centre measured by M1 (no point goal).
  - The circle task's spec bounds M1's laps, so a rocking policy fails it.
    It is trained to a pass if the run's time allows; otherwise the record
    shows the predicate failing a rocking trace and passing a circling one.
  - If L1 has landed, the plate may be tilted by pushrods instead. That is
    optional, not required.
- [ ] **P2. The excavator's precision floor, measured.**
  - On a scratch copy (`orun5-excavator`), the policy reads each servo's
    S2 load channel, and its goal is held in the track frame (R1). One
    reach run starts cold with the reference project's reward.
  - The record reports whether the ~20 mm floor moved, on the same frozen
    seeds. **Either outcome is a result.** A floor that does not move rules
    out both hypotheses, and the record says so.
  - Optional, if L1 has landed: the bucket driven through a four-bar
    linkage, as a real excavator's is.
- [ ] **C1. Closing report.**
  - `docs/probes/orun5/REPORT.md` covers:
    - each capability, with a still or a plot showing it work;
    - P1's and P2's results, with their numbers, and P1's hero if it
      passed;
    - the base-guidance rules added, and the ledger
      (`docs/probes/orun5/LESSONS.md`) of every workaround in the
      reference projects and what replaced it;
    - every ADR the run added;
    - the remaining defects.
  - Reconcile, then claim done for critic review without ticking the owner
    boxes.

## Horizon ladder

- **short-term:**
  1. Read both reference projects end to end, and write the ledger's
     skeleton: every workaround, with its evidence.
  2. M1: the angular-progress and distance metrics. They are small, pure
     functions over the trace, and they unblock P1's spec.
  3. S1: the position sensor kind, its noise model and its trainer path.
- **medium-term:**
  1. P1's centring task on a free ball.
  2. S2, then R1.
  3. L1: the loop closure in the assembly, the MJCF export, then the fit
     sweep.
  4. P2's measured run.
- **long-term:**
  1. The base guidance: how to choose a sensor, when to use a linkage, and
     how to state a motion as a predicate. Every rule general, with its
     reason.
  2. The closing report (C1).
  3. Defects left from earlier runs:
     - a project reads "not found" until its first script;
     - the trainer stalls 37–39 s before each checkpoint (measure first);
     - a warm start is refused across tasks whose success specs differ,
       even when the observations and actions match (decide whether that
       rule is right, with an ADR either way).
  4. Keep every gate green and every doc true, and `STATE.md` reconciled.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries. The
  repository carries no GPL or AGPL code. The tag `v1-blender-shell` may be
  read but never copied from.
- Training stays offboard in `training/`. JAX and MJX never enter the
  engine or a payload, and `training/cadex_train.py` imports only the
  standard library at module scope. `analysis/` imports no GPL package.
- `CadexDynamics.py` stays unreachable from `cadexd` (ADR-102).
- Never commit any of the following:
  - secrets, machine paths, private hostnames;
  - build outputs;
  - full transcripts or activity logs;
  - policy binaries, checkpoints or rollout traces.
- Do not hand-edit `STATE.md`, `PLAN.md`, `ROADMAP.md` or state nodes.
- **Keep earlier projects read-only:** ball-plate, excavator-mini,
  biped-sts, biped-mg90, biped-new, quad-qdd, hex*, ot5–ot11, orun1-*
  through orun4-*, every `sweep-*` and `digestbug-*`. Work on copies named
  `orun5-*`.

**This run:**
- **No guidance, doc, test or default in Cadex names a reference project**,
  or reads files from one at run time. Records and the ledger may cite them
  as evidence. The guidance tests' project-name patterns already cover
  them (ADR-586's commit).
- **The protocol stays a contract.** Every `OP_ARG_SPECS` change updates
  `docs/INTEGRATION.md` in the same commit. The tool surface does not
  change (A5) except under AGENTS.md's rule.
- **The page stays read-only.** If a new sensor or loop is drawn on the
  page, it is drawn from what `/api/project` already serves, with a browser
  test and `docs/DASHBOARD.md` in the same commit.
- The run branch builds and both suites pass at every accepted commit.
- One training run at a time on the 5090. The machine lock is the arbiter.
- The actor may serve the dashboard on 127.0.0.1 for its own browser tests.
  It never runs `tailscale serve` and never binds a public address.
- Committed images are PNG, ≤300 KB each, under `docs/probes/orun5/`.
- No role starts, stops or restarts the loop or signals its process.

## Question policy

- Resolve reversible choices autonomously, using the smallest measured step
  towards the highest-ranked open criterion.
- **Is it real hardware?** If no part on the market measures a channel the
  way it is declared, it is privileged. When unsure, make it privileged and
  record why.
- **Base or style?** A guidance rule that would be wrong for a crane, a
  wheeled base or a fixed arm goes in a style.
- Where A1–A5 and a measurement disagree, record both and follow A1–A5.
  They are the owner's to change.
- Code and accepted artifacts outrank docs. Update the docs with the
  behaviour they describe.
- A pre-existing test failure is recorded and left alone, unless the unit's
  own change touches it.
- A harness or usage limit is not an attempt: keep the receipt and wait for
  capacity.
- Never invent a measurement, never weaken a test to pass, and never wait
  for a human.

## Exhaustion policy

`report_done`.
- Once S1, M1, S2, L1, R1, P1, P2 and C1 have evidence, write the closing
  report, reconcile and claim done. Two consecutive critic acceptances stop
  the run.
- Do not claim done while any criterion is unmet unless the 24-hour ceiling
  has arrived. Until then, work the highest-ranked open criterion, then the
  long-term rung.
- If the ceiling arrives first, report how far each criterion got and what
  is left. Do not redefine success.

## Quality bar

- Run `pixi run test-engine` and `pixi run python -m pytest cli/tests` (GPU
  hidden) at every accepted commit that touches code.
- Python changes under `src/Mod/cadex/` need `pixi run build-engine` before
  the CLI's engine-needing tests count. For protocol or payload changes,
  rebuild and stage, then run the packaged lifecycle gate. Engine-needing
  tests that skip on a bare build do not count as passes.
- Every bug fix has a test that fails without it.
- Every new sensor kind, predicate, constraint and goal frame has an ADR,
  starting at ADR-587.
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

**Done criteria as gaps** (one open state node each; work closes them through declared impacts):

- [gap] gap-s1-grounded-sensor-reads-free: **S1. A grounded sensor reads a free body's position.** - A new sensor kind measures a body's position, and optionally its velocity, in the frame of a named component: for example a touch panel on a plate reading a ball's x and y, or a camera on a mast reading a marker. It declares range, resolution, rate and noise (A1), and the trainer applies them. - A body outside the sensor's range reads as out of range, which the task can terminate on. It never reads as a stale or a clamped value. - `describe_api`, `docs/XSCRIPT.md` and `docs/MUJOCO.md` describe it. - Tests: the channel matches the body's true position in the component's frame through a tilt and a turn; out of range is reported; noise and quantisation follow the declaration; a task naming the channel trains without the "ungrounded" refusal.
- [gap] gap-m1-predicates-measure-motion-not: **M1. Predicates measure the motion, not only where it ended.** - New evaluation metrics, from the trace (A3): - **angular progress about a point**: net signed turns of a body about a point and axis in a frame, and laps completed, so a body that rocks on an arc measures about zero; - **distance from a point**: a body's final and mean distance from a point in a frame, with no goal declared. - A spec can bound them like any metric. A metric that could not be measured fails (the `judge` rule, ADR-586). - Tests: a circling trace passes a laps predicate; a rocking trace on the same arc fails it; a trace that ends early fails rather than crashes.
- [gap] gap-s2-grounded-sensor-reads-actuator: **S2. A grounded sensor reads an actuator's load.** - A new sensor kind reads an actuator's load: the force or torque it applies, as the bus servo or a current sensor reports it, with the declared resolution and noise (A1). - The catalog's bus servos say they report load; a hobby PWM servo does not, and declaring a load sensor on one is refused with a reason. - Tests: the channel tracks the actuator's applied force under a held load and saturates at the stall line; a PWM servo's load sensor is refused.
- [gap] gap-l1-closed-linkage-exports-driven: **L1. A closed linkage exports and is driven.** - The assembly can declare a loop closure: two bodies joined by a constraint that closes a chain (A2). The MJCF export writes it as an equality constraint, and an actuator on one joint of the loop drives the whole chain. - The fit sweep moves the closed chain consistently, by solving the loop, or refuses with a reason that names the loop. - The smoke check holds a linkage steady, and the export's closure error stays within the MJCF pose tolerance (ADR-584). - Tests: a four-bar driven by its crank, and a slider-crank, each reaching the analytic output angle across the crank's range within tolerance; an over-constrained loop is refused.
- [gap] gap-r1-goal-can-be-held: **R1. A goal can be held in a body's frame.** - A reach goal (point or pool) can be declared relative to a component, so it moves with that component. The policy's goal channel is then what the base itself would see. - The reach metrics measure against the goal where it actually was at each frame. - Tests: a goal on a drifting base stays put in that base's frame, and the final error is measured against it.
- [gap] gap-p1-ball-plate-rebuilt-as: **P1. The ball-plate, rebuilt as built.** - On a scratch copy (`orun5-ball-plate`), the ball is a free sphere rolling on the plate by contact, read by an S1 touch panel. No sliders, and no hidden bead. - The centring task trains and passes its spec, with distance from the centre measured by M1 (no point goal). - The circle task's spec bounds M1's laps, so a rocking policy fails it. It is trained to a pass if the run's time allows; otherwise the record shows the predicate failing a rocking trace and passing a circling one. - If L1 has landed, the plate may be tilted by pushrods instead. That is optional, not required.
- [gap] gap-p2-excavator-s-precision-floor: **P2. The excavator's precision floor, measured.** - On a scratch copy (`orun5-excavator`), the policy reads each servo's S2 load channel, and its goal is held in the track frame (R1). One reach run starts cold with the reference project's reward. - The record reports whether the ~20 mm floor moved, on the same frozen seeds. **Either outcome is a result.** A floor that does not move rules out both hypotheses, and the record says so. - Optional, if L1 has landed: the bucket driven through a four-bar linkage, as a real excavator's is.
- [gap] gap-c1-closing-report-docs-probes: **C1. Closing report.** - `docs/probes/orun5/REPORT.md` covers: - each capability, with a still or a plot showing it work; - P1's and P2's results, with their numbers, and P1's hero if it passed; - the base-guidance rules added, and the ledger (`docs/probes/orun5/LESSONS.md`) of every workaround in the reference projects and what replaced it; - every ADR the run added; - the remaining defects. - Reconcile, then claim done for critic review without ticking the owner boxes.

## Method

Ouroboros iterations on branch `ouroboros/orun5`: orient, one dispatched unit, record, commit; a reconcile pass folds the tail on pressure; with the planner on, a bet follows each reconcile.

## Result

Directive recorded. Work follows as child nodes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: f3489df96683509072d7f44495fe2cc55e9d2dc0

## State Impact

- target: NEW gap-s1-grounded-sensor-reads-free — Charter gap, status open: **S1. A grounded sensor reads a free body's position.** - A new sensor kind measures a body's position, and optionally its velocity, in the frame of a named component: for example a touch panel on a plate reading a ball's x and y, or a camera on a mast reading a marker. It declares range, resolution. Flip to working only when the criterion is verifiably met.
- target: NEW gap-m1-predicates-measure-motion-not — Charter gap, status open: **M1. Predicates measure the motion, not only where it ended.** - New evaluation metrics, from the trace (A3): - **angular progress about a point**: net signed turns of a body about a point and axis in a frame, and laps completed, so a body that rocks on an arc measures about zero; - **distance from. Flip to working only when the criterion is verifiably met.
- target: NEW gap-s2-grounded-sensor-reads-actuator — Charter gap, status open: **S2. A grounded sensor reads an actuator's load.** - A new sensor kind reads an actuator's load: the force or torque it applies, as the bus servo or a current sensor reports it, with the declared resolution and noise (A1). - The catalog's bus servos say they report load; a hobby PWM servo does not,. Flip to working only when the criterion is verifiably met.
- target: NEW gap-l1-closed-linkage-exports-driven — Charter gap, status open: **L1. A closed linkage exports and is driven.** - The assembly can declare a loop closure: two bodies joined by a constraint that closes a chain (A2). The MJCF export writes it as an equality constraint, and an actuator on one joint of the loop drives the whole chain. - The fit sweep moves the close. Flip to working only when the criterion is verifiably met.
- target: NEW gap-r1-goal-can-be-held — Charter gap, status open: **R1. A goal can be held in a body's frame.** - A reach goal (point or pool) can be declared relative to a component, so it moves with that component. The policy's goal channel is then what the base itself would see. - The reach metrics measure against the goal where it actually was at each frame. -. Flip to working only when the criterion is verifiably met.
- target: NEW gap-p1-ball-plate-rebuilt-as — Charter gap, status open: **P1. The ball-plate, rebuilt as built.** - On a scratch copy (`orun5-ball-plate`), the ball is a free sphere rolling on the plate by contact, read by an S1 touch panel. No sliders, and no hidden bead. - The centring task trains and passes its spec, with distance from the centre measured by M1 (no p. Flip to working only when the criterion is verifiably met.
- target: NEW gap-p2-excavator-s-precision-floor — Charter gap, status open: **P2. The excavator's precision floor, measured.** - On a scratch copy (`orun5-excavator`), the policy reads each servo's S2 load channel, and its goal is held in the track frame (R1). One reach run starts cold with the reference project's reward. - The record reports whether the ~20 mm floor moved,. Flip to working only when the criterion is verifiably met.
- target: NEW gap-c1-closing-report-docs-probes — Charter gap, status open: **C1. Closing report.** - `docs/probes/orun5/REPORT.md` covers: - each capability, with a still or a plot showing it work; - P1's and P2's results, with their numbers, and P1's hero if it passed; - the base-guidance rules added, and the ledger (`docs/probes/orun5/LESSONS.md`) of every workaround in . Flip to working only when the criterion is verifiably met.
