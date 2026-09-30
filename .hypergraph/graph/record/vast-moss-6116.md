---
node_id: f9219793-b2b0-5c60-a240-1f8cc859496a
slug: vast-moss-6116
title: 'ot11 P3: a task says where to go; goals are drawn per episode by one algorithm the engine, the reference runner and the trainer all run, and a test fails if they drift (ADR-462)'
created_at: '2026-09-30T14:48:31+00:00'
parents:
- rough-cloud-5656
summary: ''
---
## What

P3, goal sampling (ADR-462, commit `f4d55ef7`). A task can now say where to go: `assembly.goal` declares a value, a commanded speed or a reachable point, drawn per episode and optionally again during it. The policy observes it, the reward and the success spec name it, the trace records it, and the trainer draws it by the engine's algorithm with a test that fails if the two drift apart.

Before the unit, the critic's fix (commit `3e380f88`): `docs/probes/ot11/README.md` and ADR-461 now say the floor-marks probe's rule was fixed in working notes and not committed before its first call, and state the rule from here on.

## Why

The critic named this unit: P3 is the top open rung and unblocks W3, the lateral half of W4 and every reach predicate, none of which could be read while a task stated no goal. Target: the charter criterion P3 (`even-nest-5028`).

One deviation from the critic's message. It asked for a reconcile afterwards. This dispatch forbids reconcile in a work iteration, so I did not run it. The tail is now three records (`old-cove-1967`, `rough-cloud-5656`, this one) and a reconcile is due.

## Method

- **Surface.** `assembly.goal(name, kind="value"|"speed"|"point", between=, tip=, tip_offset_mm=, joint_fraction=0.8, min_z_mm=, min_separation_mm=, resample_seconds=)`, passed as `assembly.task(goals=[...])` and optionally restated as `assembly.success(goals=[...])`. A tenth task intermediate, registered in the pack exports, the operation table and the worker.
- **Engine (`CadexDynamics.py`).** `_goal_records` resolves goals to addresses and SI in the bundle (`goal`, with `goal_algorithm`). `draw_episode_goals` continues `random.Random(seed)` after the disturbance draws. A point is the tip's position at a joint configuration drawn in the middle `joint_fraction` of every driven joint's range, redrawn up to 100 times when it is under `min_z_mm`, adds a contact the reset pose does not have, or is within `min_separation_mm` of where the tip starts the segment. `evaluate_episode` shows the goal to the policy and the reward; `rollout_policy` writes `goal_channels`, a `goal` row per frame and `episode.goal`; `evaluate_success` takes the commanded speed and the reach targets from the episode's own draw. `METRICS`' `goal` need became `command` and `target`.
- **Trainer (`training/cadex_train.py`).** `draw_goals` is a host-side copy of the engine's draw. A pool of `--goal-pool` (4096) episodes is drawn from `random.Random(seed)` before training; on device each environment holds one pooled episode, chosen by `jax.random.randint` on every reset, and reads segment `min(step // resample_steps, segments - 1)`. Every `goaled` branch is taken at trace time. `check_training_seed` refuses a `--seed` that is one of the bundle's evaluation seeds, before anything is imported.
- **Reference runner.** `cadex_tests/dynamics_task_episode.py` is the third copy of the draw, in stock MuJoCo with no Cadex.
- **Tests.** Four new files: `test_dynamics_goal_model.py` (34), `test_dynamics_goal_api.py` (19), `test_dynamics_goal_trainer.py` (13 under pixi with 4 skipped, 17 from the training venv), `test_dynamics_goal_live.py` (2, through a live `cadexd`). Three existing tests updated for the split need names.
- **Mutation check.** I broke the trainer twice to see the drift tests fail, then restored it from a backup. `(steps + 1) // period` in `goal_segment` failed the segment test and the device reward-curve test. Dropping the separation rule from `draw_goals` failed seven host tests.
- **Docs.** `docs/XSCRIPT.md` (the goal section, the metrics table, the spec's `goals=`), `docs/INTEGRATION.md` (the trace keys), `docs/CLI.md`, `docs/ARCHITECTURE.md`, `training/README.md`, `docs/probes/ot11/README.md` (two statements that said "until P3"), ADR-462.
- **Gates.** `pixi run build-engine`, `pixi run stage-engine`, both suites, the packaged gate with `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64`, and the trainer-facing suites from the training environment with `JAX_PLATFORMS=cpu`. `~/cadex-train-venv` has no pytest, so I made a scratch venv in `/tmp` layered over it with a `.pth` file and installed pytest there; the user's venv was not modified.

## Result

What is true now:

- **A task declares a goal, and a task with none is unchanged.** `goal` and `goal_algorithm` are new semantic bundle fields, absent when no goal is declared. `EPISODE_VARIATION_ALGORITHM`'s text did not move (its SHA-256 is pinned in a test), so every existing bundle keeps its digest and every existing policy still names its task. The two known negatives' tasks declare no goal; their receipts do not move.
- **A goal moves no other draw.** On the three fixture seeds, an episode with a goal draws the same reset, shove and randomisation as the same task without one.
- **The engine, the reference runner and the trainer draw the same goals.** Trainer against engine: equal with `==` on doubles over five seeds and twenty episodes each, on a bundle with a point, a value and a resampled speed. Reference runner against engine: every goal, observation and reward equal as `repr` text, seeded and unseeded.
- **The device agrees too.** From the training venv, a real run with a pool of one, a reward that is the goal and no termination reported, over five iterations of fifteen steps against a twenty-step episode, the curve the engine's draw from seed 6 fixes, to 2e-6 relative. The policy it wrote was verified by the engine and rolled out with a goal.
- **The success spec reads the goal.** `speed_ratio` equals the measured forward speed over the drawn command on every fixture seed. The reach metrics are measured to the drawn targets: a still policy fails `final_error_arm_lengths_max`, and a positive control (the spec narrows the target to the pose the still policy holds) passes on all three seeds.
- **Suites.** `pixi run test-engine`: 2507 passed, 57 skipped (2439 and 53 before). `pixi run python -m pytest cli/tests`: 1212 passed, 1 skipped. Packaged gate: 25 passed (`test_cadexd_lifecycle.py` and `test_dynamics_goal_live.py`). Training environment, CPU: `test_dynamics_goal_trainer.py` 17 passed; the other trainer-facing suites 123 passed, none skipped.
- **No cadexd op changed, no `shell/` file, no new dependency, no JAX or MJX in the engine.**

Two failures met on the way, both fixed in this commit:

- **The agent's `describe_api` assembly page went over its budget.** `cli/tests/test_client.py` holds it to 21,500 characters against a live engine; it stood at 21,411 and the new export took it past. I cut two rationale sentences from the assembly notes and shortened three, and cut my own goal notes to one sentence. The page is 21,446. The cut text is still in the docstrings. **The page has 54 characters of headroom: the next assembly export will not fit without another cut or a redesign of the page.**
- **A venv-only test was already broken.** `test_dynamics_command_slew.py::test_a_limited_policy_still_verifies_against_the_engine` raised `KeyError: 'task'` from a stale call, independent of this change. It skips under pixi, so no earlier suite run saw it. Fixed; it passes.

Concerns and assumptions for the next iteration:

- **The film does not draw the reach target marker.** The frozen filmstrip text asks for it. The trace now carries the target in every frame, so the film has what it needs. This has to land before any reach film is judged.
- **A point is drawn over the joint's range, not a servo's narrower `command_limits`**, as the contract says. A task that narrows a command can be given a target it cannot reach.
- **"In contact" means a contact pair the reset pose does not have.** The contract says "if the model is in contact at that configuration". The two are the same for a mechanism with no contact at rest, which a bench arm is. I chose the wider reading so a mechanism resting on a floor can have a point goal at all.
- **A changing commanded speed is averaged** over the settled frames for `speed_ratio`. It does not measure how quickly a change is followed. The walk contract holds the speed for the episode, so this does not affect W3.
- **`cadex train` does not expose `--goal-pool`**; the trainer's default of 4096 applies. A warm start across a changed goal is refused.
- **Observed and not changed:** the trainer's randomisation uses `random.Random(base_seed + environment_index)`, so with seed 0 and more than 1101 environments, environment 1101 draws the mass factors evaluation seed 1101 would draw if a spec inherited the task's randomisation. The ot11 specs state `randomisation=[]`, so it does not bite there.
- **The owner edited the charter during this iteration** (`.ouroboros/goal.md`, uncommitted in the working tree, not touched by me). Under P1 it now says the spec is authoritative where it measures a property, the judge's blind spot on slip is to be recorded in the contract as a known limit, and no more judge probes are called for.
- **The tail is three records. A reconcile is due.**

P3's listed parts all exist with measured evidence. The checkbox is the owner's.

Dispatch closed: 1 unit — P3 goal sampling: `assembly.goal` in the task, the rollout, the trace, the success spec and the trainer, with engine–trainer agreement test-pinned (ADR-462)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: f4d55ef7296ba33b3748583aed67ffa31854c410

## State Impact

- target: even-nest-5028 — P3's listed parts all exist with measured evidence; the actor believes the criterion is met and does not tick it (ADR-462, commit f4d55ef7). assembly.goal declares a value, a commanded speed (mm/s) or a reachable point per episode, optionally redrawn every resample_seconds on a whole number of control steps; the policy observes every goal after its sensor channels, reward and termination expressions name goal channels, a rollout trace carries goal_channels, a goal row per frame and policy.goal, and the success spec reads speed_ratio/lateral_ratio against the speed goal and the reach metrics against the point goal from the episode's own draw. The draws continue a seed's stream after the disturbance draws under a separate stated goal_algorithm, so a task with no goal keeps its bundle and digest and a seed keeps its reset and shoves. The trainer draws goals on the host by the same algorithm as a pool of episodes; test_dynamics_goal_trainer holds draw, pool, segment rule and channel order equal to the engine's, and from the training venv holds a real run's reward curve to the engine's draw to 2e-6; both halves were mutated once and failed. No JAX or MJX in the engine. Suites: engine 2507 passed 57 skipped, cli 1212 passed 1 skipped, packaged gate 25 passed, training venv 17 + 123 passed. Open: the film does not yet draw the reach target marker; cadex train does not expose --goal-pool; a warm start across a changed goal is refused.
- target: late-pond-2851 — the trainer reads a task's goals (ADR-462): draw_goals is a host-side copy of CadexDynamics.draw_episode_goals, a pool of --goal-pool (default 4096) episodes is drawn from random.Random(seed) before training and each environment holds one pooled episode chosen on every reset; goal channels join the observation vector after the sensor channels and are always policy inputs; every goal branch is taken at trace time so a task with no goal trains as it did (two runs at one seed, with and without --goal-pool, write the same weights). The trainer now refuses a --seed that is one of the bundle's evaluation seeds, before importing anything. goal is not a key --init-from-task-change may move. A venv-only test, test_a_limited_policy_still_verifies_against_the_engine, was already failing on a stale call and is fixed.
- target: salty-isle-4063 — a task bundle may carry goal and goal_algorithm (ADR-462), both semantic fields and both absent when no goal is declared; evaluate_episode returns the goal schedule it drew, an unseeded episode holds each goal's nominal value, and the stock reference runner reproduces goals, observations and rewards as text. A point goal is the tip's position at a joint configuration drawn in the middle joint_fraction of every driven joint's own range, redrawn up to 100 times against min_z_mm, new contacts and min_separation_mm, and a declaration no draw can meet is refused when the task is built. The agent's describe_api assembly page is at 21,446 of a 21,500 character budget after two rationale sentences were cut and three shortened: the next assembly export will not fit without another cut.
- target: damp-flame-5523 — the evaluation no longer needs a command or targets from outside (ADR-462): CadexEvaluation.METRICS' goal need is split into command (a speed goal) and target (a point goal), evaluate_success reads both from each episode's drawn goal, each seed's report row echoes drawn.goal, and a spec may restate the task's goals by name and kind with assembly.success(goals=[...]). A ratio of a command whose range includes zero is refused when the task is declared. A changing command is averaged over the settled frames.
- target: rough-shore-6557 — no status change. docs/probes/ot11/README.md and ADR-461 now say the floor-marks probe's rule was fixed in working notes and not committed before its first call (commit 3e380f88), and state that a probe's or run's rule is committed before its first call from here on. The README's two 'until P3' statements are updated: the product's evaluation reads the command and targets from the goal, and the film still does not draw the reach target marker although the trace now carries the target. The owner's uncommitted charter edit of 2026-09-30 asks that the judge's blind spot on measured properties be recorded in the contract as a known limit; that is not done yet.
