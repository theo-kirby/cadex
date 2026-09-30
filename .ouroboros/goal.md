# Goal: a training and evaluation loop that works for any behaviour

Verified against source: 2026-09-29. Operator charter for ot11, following
ot10 (`docs/probes/ot10/REPORT.md`) and ot9 (`docs/probes/ot9/REPORT.md`).
The human owns this file; unattended roles never edit it.

## Mission

Cadex can design a robot, see it, present it and train a policy on it. What
it cannot do yet is tell a good behaviour from a bad one, or improve a
policy on purpose.

ot10's quadruped passed the gait check (`walked = true`) and shuffled.
ot9's Robin balanced and wandered. In both cases the reward and the check
said yes, and the owner's eye said no.

Build a **task-agnostic training and evaluation pipeline**, and a loop in
which the product agent:
- designs a task: its reward, its observations, its terminations, and a
  success spec that is separate from the reward;
- trains a policy under a bounded budget;
- evaluates the policy against that spec on frozen seeds;
- watches the result, diagnoses it from measurements, then redesigns and
  retrains.

Prove the pipeline on three different behaviours, on three different
mechanisms:
- **walking with real steps**, on a quadruped;
- **reaching**, on an arm, to targets placed at random;
- **balancing in place**, on a balancer, including recovery from a shove.

Nothing in the pipeline may be walking-specific. Closing a hand or moving
an arm must go through the same path.

Priority, in order:
1. The evaluation is trustworthy (P1, P2).
2. The loop exists (P3, P4).
3. The three behaviours pass (R1–R3).

Keep the 72-hour ceiling and two-accepted-done stop. Every Ouroboros role and
headless product-agent call uses `claude-opus-5-5`, with no model fallback.

## Done criteria

Each criterion needs a causally parented record with measured evidence.
The human owns the checkboxes; roles report results and do not tick them.

- [ ] **P1. Each behaviour has a frozen evaluation contract, and it catches
  the known failures.**
  - `docs/probes/ot11/README.md` freezes the following for walk, reach and
    balance, before any ot11 training run:
    - **a success spec:** measurable predicates on a rollout trace,
      independent of the reward;
    - **ten or more evaluation seeds**, with the reset variation and
      disturbances;
    - **a pass rule:** every seed must pass, unless the spec states a
      per-seed rate with its reason;
    - **a blind video judge:** a fresh model call that sees the frozen
      rubric, the task's one-paragraph intent and filmstrip frames of the
      rollout on the dark prototype floor, and nothing else;
    - **the judge's pass bar.**
  - **Known negatives are measured before anything new is trained:**
    - ot10's `w2-2` shuffle must fail the walk spec, and must fail it for
      the right reason (stepping, foot clearance or slip), not by accident.
    - ot9's Robin policy is measured against the balance spec. If it
      wanders, the spec must say so.
  - Changing a frozen item later is a recorded decision that re-evaluates
    every earlier policy.
  - **The spec and the judge each have a job (owner, 2026-09-30).**
    - Where the success spec measures a property (slip, stepping, foot
      clearance, drift, heading, reach error), the spec is authoritative
      for it.
    - A judge blind spot on a measured property, such as the still-frame
      judge not seeing w2-2's slip (ADR-460, ADR-461), is recorded in the
      contract as a known limit. It does not block P1, and it does not call
      for more judge probes.
    - The judge's job is what the spec cannot measure: whether the
      behaviour reads as the intended one at all, and gross failures such
      as falling, flailing or the wrong motion.
    - The judge's bar still applies to R1–R3. Where the judge contradicts a
      measured predicate, the predicate wins, and the disagreement is
      recorded.
- [ ] **P2. The product evaluates any policy against its task's spec.**
  - The success spec is declared in xscript alongside the task, and is
    documented in `docs/XSCRIPT.md`.
  - One command evaluates an accepted policy on its frozen seeds. It writes
    a report into the project with:
    - pass or fail per seed and per predicate;
    - the reward decomposed term by term;
    - termination causes;
    - behaviour metrics;
    - the video and a filmstrip, on the dark floor.
  - The behaviour metrics include at least:
    - **gait:** step count, foot clearance, foot slip, duty factor and
      commanded-velocity tracking;
    - **reach:** final error, time to target and overshoot;
    - **balance:** tilt, drift from the start position, heading and the
      time to recover from a shove.
  - The review dashboard shows the report. Tests pin every metric on
    fixtures that pass and fail, and the w2-2 shuffle is one of the failing
    fixtures.
- [ ] **P3. A task can say where to go.**
  - A task can sample a goal per episode (and optionally change it during
    the episode), such as a reach target or a commanded velocity. The
    policy observes the goal, the reward and the spec can name it, and it
    is recorded in the trace.
  - The trainer and the engine's rollout agree on it exactly, and a test
    fails if they drift apart.
  - Training stays offboard: nothing in the engine imports JAX or MJX.
- [ ] **P4. The product agent runs the loop, and it is the same loop for
  every behaviour.**
  - Through the ordinary product path, the agent can:
    - author or revise a task, its reward and its spec;
    - start bounded training;
    - read the progress, the evaluation report and the filmstrip;
    - decide the next revision.
  - This run chooses the architecture and records it in an ADR. Whatever
    it is, the loop takes no walking-specific branch. `cadex walk` becomes
    one use of it, or is retired in its favour, and the ADR says which.
  - The transcripts must show, for at least one behaviour, three or more
    rounds of design, train, evaluate and revise. Each revision must be
    motivated by a measurement from the previous evaluation, and the next
    evaluation must show whether it helped.
- [ ] **R1. A quadruped walks with real steps.**
  - The final pre-registered confirmation evaluation passes the frozen walk
    spec on every evaluation seed, and meets the video judge's bar.
  - The policy is installed, verified and reopened through the supported
    path, on an accepted design. That design may be one of ot10's, copied
    into a new `ot11-*` project.
  - Every earlier training run and evaluation is published, including the
    failures.
- [ ] **R2. An arm reaches targets placed at random.**
  - Under a goal-sampling task (P3), the final pre-registered confirmation
    evaluation meets the frozen reach spec on every seed, and meets the
    judge's bar.
  - The spec covers tolerance, time and overshoot, over targets the policy
    never trained on.
  - The mechanism may be an earlier arm (Heron, ot6–ot8) or a new one
    designed by the product agent.
- [ ] **R3. A balancer balances in place and recovers from a shove.**
  - The final pre-registered confirmation evaluation passes the frozen
    balance spec on every seed: upright, within position and heading
    bounds, and recovering from the declared shoves.
  - The judge's bar is met.
  - Robin (ot8/ot9) or a new balancer is copied into an `ot11-*` project.
    Robin's baseline policy is the ot9 one, and it stays read-only.
- [ ] **C1. Regressions and a closing report are complete.**
  - Both full suites pass at the final revision, plus the packaged
    lifecycle gate for any engine or payload change.
  - `docs/probes/ot11/REPORT.md` lists every training run with its settings,
    its budget and the GPU time spent, and every evaluation and judge score.
    It also covers every revision the agent made and why, every failure,
    and the remaining defects.
  - Reconcile, then claim done for critic review without ticking the owner
    boxes.

## Horizon ladder

- **short-term:**
  1. Write P1's contract and measure w2-2 and Robin against it before
     building anything.
  2. Declare the success spec in xscript, and add the evaluation command
     and report with the three metric families (P2).
  3. Goal sampling in the task, the trainer and the rollout (P3).
  4. The filmstrip and the frozen video judge, run on the known negatives.
- **medium-term:**
  1. Build the loop (P4), with bounded training runs the agent can start,
     watch and stop.
  2. Balance first. It is the closest to passing, and it proves the loop
     end to end.
  3. Then reach, which proves goal sampling. Then walking, which is the
     hardest.
  4. Diagnose every failed evaluation before the next revision. Let the
     agent revise the mechanism where the measurement points to it.
- **long-term:**
  1. A fourth behaviour through the same loop with no new code path, such
     as a gripper closing on a target pose. This is a direction, not a bar.
  2. Sim-to-real readiness: actuator limits, sensor noise and latency in
     the task, with results reported against them.
  3. Keep every gate green and every doc true. Keep `STATE.md` reconciled.

## Constraints

**Standing:**
- Obey AGENTS.md, the licensing rules and the process boundaries. `cli/` is
  LGPL: copy nothing from `shell/`.
- Training stays offboard in `training/`, on its own pinned requirements.
  JAX and MJX never enter the engine or a payload.
- Never commit secrets, machine paths, private hostnames, build outputs,
  full transcripts, policy binaries or rollout traces.
- Do not hand-edit `STATE.md`, `PLAN.md`, `ROADMAP.md` or state nodes.
- Keep earlier projects read-only (hex, ot5–ot10). Work on copies, each
  under a new `ot11-*` name.

**This run:**
- **Only the product agent authors what R1–R3 count:** the tasks, the
  rewards, the success specs it trains against, and any change to a
  mechanism.
  - The actor builds the pipeline, the tools, the metrics, the judge and
    the prompts.
  - The actor never hand-tunes a reward, a spec or a policy that a
    criterion counts.
  - The frozen P1 contract is the evaluation authority. It is the actor's,
    written before any training.
- **The reward never judges itself.** A success spec may not be a threshold
  on the task's own reward. Evaluation seeds are never training seeds.
- **Pre-register every training run before it starts:** its settings, its
  seed, its wall-clock budget and its stop rule.
  - Keep `--stop-on-collapse` on.
  - One GPU training job at a time on this machine, unless an ADR shows
    that two fit.
  - A run with no budget stated is not started.
- **Keep product turns and training jobs supervised.**
  - Keep them inside one iteration, or under a supervisor that outlives
    the actor's session (ot10's hexapod-9 died with its actor).
  - A killed job is recorded as an interruption, not an attempt.
- **Use confirmation evaluations, not "one failure fails forever".**
  - Each R criterion is judged on its final pre-registered confirmation
    evaluation at the final revision.
  - Every earlier attempt is published, but it does not count against the
    final one.
  - Never re-run a confirmation to fish for a pass. A second confirmation
    needs a recorded product change between the two.
- **Videos and filmstrips use the dark prototype floor** (ADR-444).
  - Committed images are PNG, 300 KB or less each, under
    `docs/probes/ot11/`.
  - Videos live in the projects and are never committed.
- ot10's A7 (design aesthetics beyond the bar) stays parked. Do not spend
  this run on robot looks.
- No role starts, stops or restarts the loop or signals its process.

## Question policy

- Resolve reversible choices autonomously, using the smallest measured step
  towards the highest-ranked open criterion.
- The evaluation outranks the loop, and the loop outranks the behaviours.
  A policy that passes an evaluation you do not trust has not passed.
- When an evaluation and the video judge disagree, record both and diagnose
  the disagreement before training again.
- Code and accepted artifacts outrank docs. Update the docs with the
  behaviour they describe.
- A harness or usage limit is not an attempt: keep the receipt and wait for
  capacity.
- Never invent a measurement, never weaken a frozen threshold to pass, and
  never treat a provider refusal as a verdict.

## Exhaustion policy

`report_done`.
- Once P1–P4, R1–R3 and C1 have evidence, write the closing report,
  reconcile and claim done. Two consecutive critic acceptances stop the run.
- Do not claim done while any criterion is unmet unless the 72-hour ceiling
  has arrived. Until then, work the highest-ranked open criterion, then the
  long-term rung.
- If the ceiling arrives first, report the highest bar reached and every
  failed run and seed. Do not redefine success.

## Quality bar

- Run `pixi run test-engine` and `pixi run python -m pytest cli/tests` at
  the final revision.
- For protocol or payload changes, rebuild and stage, then run the packaged
  lifecycle gate. Report skips and failures as such.
- Trainer changes are tested from the training venv as well as under pixi,
  as `training/README.md` describes.
- A product fix needs a regression test that fails before it.
- Every behaviour claim cites an evaluation report and its seeds, never a
  reward curve alone.
- Record each unit with its State Impact. Direction changes, new APIs and
  removals also earn ADR entries.

## Reconcile

- Every five work iterations or three unreconciled records:
  - fold impacts;
  - advance the high-water mark;
  - regenerate the views;
  - export and check.
- The separate maintainer and planner roles stay off; the critic names the
  next unit.
- Unattended roles never edit this charter.
