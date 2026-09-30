---
node_id: 5a295c7f-6d18-5f80-999d-8c78ba06074f
slug: even-nest-5028
title: P3. A task can say where to go
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **P3. A task can say where to go.** - A task can sample a goal per episode (and optionally change it during the episode), such as a reach target or a commanded velocity. The policy observes the goal, the reward and the spec can name it, and it is recorded in the trace. - The trainer and the engine's rollout agree on it exactly, and a test fails if they drift apart. - Training stays offboard: nothing in the engine imports JAX or MJX. [rec: kind-spire-3578]

Declared target: `gap-p3-task-can-say-where`. The human owns the charter checkbox; roles report results and do not tick it [rec: kind-spire-3578].

**Every listed part now exists with measured evidence; the actor believes the criterion is met and has not ticked it** (ADR-462, commit `f4d55ef7`) [rec: vast-moss-6116]. Reconcile judgement: the status stays `open` because no record declares a flip and acceptance belongs to the owner and the critic, as on P2.

**What exists** [rec: vast-moss-6116]:

- **A task declares a goal.** `assembly.goal(name, kind="value"|"speed"|"point", between=, tip=, tip_offset_mm=, joint_fraction=0.8, min_z_mm=, min_separation_mm=, resample_seconds=)`, passed as `assembly.task(goals=[...])`: a value, a commanded speed (mm/s) or a reachable point, drawn per episode and optionally redrawn every `resample_seconds` on a whole number of control steps. [rec: vast-moss-6116]
- **The policy observes it, the reward and the spec name it, the trace records it.** Every goal follows the sensor channels in the observation; reward and termination expressions name goal channels; a rollout trace carries `goal_channels`, a `goal` row per frame and the episode's goal; the success spec reads `speed_ratio`/`lateral_ratio` against the speed goal and the reach metrics against the point goal, from the episode's own draw (the evaluation half is on `damp-flame-5523`). [rec: vast-moss-6116]
- **A goal moves nothing else.** The draws continue a seed's stream after the disturbance draws under a separately stated `goal_algorithm`, so a seed keeps its reset, shoves and randomisation, and a task with no goal keeps its bundle and digest (the engine half is on `salty-isle-4063`). [rec: vast-moss-6116]
- **The trainer and the engine agree exactly, and tests fail if they drift.** The trainer draws goals on the host by the engine's algorithm as a pool of episodes (detail on `late-pond-2851`). `test_dynamics_goal_trainer.py` holds the draw, the pool, the segment rule and the channel order equal to the engine's (`==` on doubles over five seeds and twenty episodes each), and from the training venv holds a real run's reward curve to the engine's draw to 2e-6 relative. Both halves were mutated once and the tests failed: `(steps + 1) // period` in the segment rule, and the separation rule dropped from the draw (seven host tests). A third copy, the stock-MuJoCo reference runner, reproduces every goal, observation and reward as `repr` text. [rec: vast-moss-6116]
- **Training stays offboard.** No JAX or MJX in the engine; no `cadexd` op, `shell/` file or dependency changed. [rec: vast-moss-6116]

Evidence at `f4d55ef7`: `pixi run test-engine` 2507 passed, 57 skipped; `cli/tests` 1212 passed, 1 skipped; packaged gate 25 passed (lifecycle plus `test_dynamics_goal_live.py`); training venv on CPU, `test_dynamics_goal_trainer.py` 17 passed and the other trainer-facing suites 123 passed, none skipped [rec: vast-moss-6116].

**Open, and assumptions the actor took** [rec: vast-moss-6116]:

- The film does not yet draw the reach target marker, though the trace now carries the target. It has to land before any reach film is judged. [rec: vast-moss-6116]
- `cadex train` does not expose `--goal-pool`; the trainer's default of 4096 applies. A warm start across a changed goal is refused. [rec: vast-moss-6116]
- A point is drawn over each driven joint's own range, not a servo's narrower `command_limits`, as the contract says. A task that narrows a command can be given a target it cannot reach. [rec: vast-moss-6116]
- "In contact" is read as a contact pair the reset pose does not have, wider than the contract's "if the model is in contact at that configuration", so that a mechanism resting on a floor can have a point goal at all. The two agree for a bench arm. [rec: vast-moss-6116]
- A changing commanded speed is averaged over the settled frames for `speed_ratio`; how quickly a change is followed is not measured. The walk contract holds the speed for the episode, so W3 is unaffected. [rec: vast-moss-6116]

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- vast-moss-6116 — assembly.goal in the task, the rollout, the trace, the success spec and the trainer, with engine–trainer agreement test-pinned and mutation-checked (ADR-462); actor believes P3 met
