# training/ — the offboard trainer

Verified against source: 2026-10-27. Provenance: `[Cadex-new]`. See
`docs/MUJOCO.md` slice M7 and ADR-084.

This directory is **not part of the engine**. CMake never installs it, it is
in no payload, and nothing in it enters `pixi.toml`.
`test_offboard_boundaries` asserts that no CMake rule references this path,
that `requirements.txt` is exactly pinned and stays out of `pixi.toml`, and
that `cadex_train.py` imports only the standard library at module scope.
`test_engine_purity_guardrails` asserts that no `jax` or `mjx` appears under
`src/Mod/cadex`, and the packaged gate (`test_cadexd_lifecycle`) that none
reaches a staged payload.

It is a thing you **copy to another machine**.

## Why training is offboard

Training does not run on the user's laptop, and that is a design decision
rather than a temporary state (ADR-075, restated by ADR-084):

- MJX needs JAX-on-GPU. `jax-metal` is 0.1.0, and the two community MPS
  backends have known compatibility problems.
- MuJoCo Warp needs CUDA.
- The published reference — a Unitree G1 walking policy converging in
  ~90 minutes — is 4096 parallel environments on an RTX 4090. On CPU that is
  days.

This turns out to be a clean boundary rather than a compromise. The engine
stays a geometry-and-dynamics service, the dashboard stays a viewer, and M7
builds **no dispatch machinery, no network I/O and no new op**: you copy two
files out, run this, and copy one file back.

**There is no train button and there is nothing to press.** The agent
authors the task, dispatches the run with its own shell (`cadex train`,
or the `train_start` tool `cadex mcp` serves), and brings the weights home
through the `put_asset` path that already exists. VISION
principle 5 is untouched — the human still only judges.

## What it reads and what it writes

Reads the pair M6 already makes movable. They are **retained artifacts of
the accepted attempt**, so they live under the project's staging tree rather
than at the project root:

```
<project>/script_artifacts/<revision>/attempt-<id>/outputs/<name>-task.json
                                      a cadex-training-task-v1 bundle
<project>/script_artifacts/<revision>/attempt-<id>/outputs/<name>-model.xml
                                      the MJCF it references, by relative
                                      path and sha256
```

The two must stay **side by side**, because the bundle references the model
by *relative* path and sha256. `load_bundle` looks for the model at that
path relative to the project root first, and then by its basename beside
the task, so both the staged `outputs/` directory and a flat folder holding
the two files under their staged names are bundles. The flat folder is what
`./cadex export --out DIR` writes (`docs/CLI.md` §3): the task JSON, the
model XML, the policy receipt and the rollout trace land beside the STEP
and STL under their staged names, so a pipeline never reads a staging
path. `inspect scope="output"` remains the supported way to find the
accepted attempt's directory from the agent's side.

Writes one self-contained file:

```
<name>.cxpolicy                       schema cadex-policy-v1
```

`CXPOLICY1\n | <u64 LE header length> | <canonical JSON header> | <raw f32 LE blob>`

The header carries what it was trained on (the task and model digests), what
it observes (the bundle's expanded scalar channel names, in order), what it
drives (the bundle's action table, verbatim), the network, the observation
normaliser, the training provenance — and the **witness**: N observation
vectors and the actions this trainer's own JAX network produced for them.

The witness is the point. The engine re-computes those actions with its own
pure-Python forward pass and refuses past a measured tolerance
(`CadexDynamics.POLICY_WITNESS_TOLERANCE`, 1e-4 relative to each action's
range; two implementations were measured at 1.5e-5 apart at worst). A policy
whose weights are fine but whose architecture the engine reads differently
is a refusal, not a bad gait.

## Standing up a box, and running it

**`training/SETUP.md` is the end-to-end version**, and there are four of
them: (a) one machine with a GPU, (b) CPU only, (c) a separate GPU box, and
(d) driving (c) with `training/remote_train.sh` (ADR-089). This file stays
*what the trainer is*; that one is *how to run it*. Duplicating the commands
here is how the two drift.

**`training/RECIPE.md` is how to write a legged task that trains cold**:
the reference gait, the start inside it, the speed and stand terms, the
warm-start rules and the budgets, each with the run that showed it.

The short form: any machine with a CUDA GPU and Python 3.12+ (the pinned
`numpy==2.5.1` has no wheels below cp312), a venv built from
`requirements.txt` with `jax[cuda12]==0.7.2` installed over the pinned CPU
jax, the `outputs/` pair copied across, and one command.

`mujoco` must match the release that wrote the model. The bundle records it
as `mujoco_version`; a mismatch is a run whose numbers cannot be compared
with the engine's, because MuJoCo's own `VERSIONING.md` disclaims
cross-version numerical reproducibility. That is why every line of
`requirements.txt` is `==` and not `>=`.

The trainer prints its reward curve on **stderr** and, on success, exactly
one line of JSON on **stdout** — the output path, its size, its **sha256**,
the parameter count, the task digest, the final reward per step, the wall
time, the device, and `cadex_importable` (which must be `false`).

The sha256 is the one you paste into the script:

```python
task   = assembly.task(model, actions=[...], reward=[...],
                       episode_seconds=2.0, control_hz=50)
policy = assembly.policy(task, weights="walk.cxpolicy",
                         sha256="<the sha256 it printed>", label="gait")
result = {"job_model": model, "job_task": task, "job_policy": policy}
```

Bring the file into the project store with the path that already exists —
the `put_asset` tool, `cadex asset --put`, or `cadex train --put`. None
performs a suffix check *of its own*: each passes the path through and lets
the engine decide, and the engine's list (`_STORED_ASSET_SUFFIXES`,
`CadexScriptedRuntime.py:194`) is what accepts `.cxpolicy` alongside the
three mesh formats. That is the whole
mechanism by which a policy reaches the store through a tool named for
geometry, and why it cost no protocol change. Then rebuild. The engine verifies the policy against the task it was trained
on and publishes a receipt.

> The rough edge this paragraph once carried went with the Blender shell
> (ADR-498): its tool was called **`import_geometry`** and advised
> `mesh.import_file(...)` on success, which is wrong for a policy (ADR-086
> §4, ADR-102 §4). The agent's tool is now the op itself, `put_asset`, and
> its description names `.cxpolicy` and `assembly.policy`.

## The actor reads what the robot can; the critic reads everything (ADR-408)

A task row marked `role: privileged` is a simulation-only quantity -- a
centre of mass, a world velocity -- that the reward and the terminations
may use. The trainer is an asymmetric actor-critic: the **actor** reads
only the policy channels (every row not marked privileged, in task order),
and the **critic** and the running normaliser read every channel. The
container's header lists the actor's channels and carries the actor's
slice of the normaliser, so the engine, the witness and every rollout see
exactly what the policy reads. A task with no privileged rows -- every
task before ADR-408 -- trains exactly as it always did. `actor_channels`
here and `CadexDynamics.policy_channels` in the engine are the same rule,
written twice because this file imports nothing from the engine.

## The learner (ADR-712)

The PPO is **Brax's** (`brax.training.agents.ppo`): its swish policy and value
networks, its tanh-squashed Gaussian, its running observation normaliser, its
loss and GAE, and its minibatched SGD under optax's Adam. The defaults below
are MuJoCo Playground's locomotion recipe. The environment is this file's
(`build_environment`): everything the bundle declares stays here. The
iteration loop is Brax's `training_step` with one unroll per iteration, so
`progress.json`, checkpoints, the best-so-far and collapse detection work as
they always did. The hand-written PPO it replaced learned to stand still on a
Go1 benchmark that Brax learns to trot in under six minutes (docs/MUJOCO.md
§7, "The learner").

## Options that matter

| Flag | Default | What it is |
|---|---|---|
| `--seed` | `0` | PPO's seed *and* the base seed for domain randomisation |
| `--iterations` | `200` | outer PPO iterations: one unroll of every environment, then `--epochs` passes of `--minibatches` minibatches |
| `--envs` | `256` | parallel MJX environments; also how many distinct randomisation draws exist. Host memory holds one compiled model plus the drawn fields, whatever the count (ADR-695). Playground's locomotion recipe uses 8192 |
| `--unroll` | `20` | control steps collected per environment per iteration |
| `--epochs` | `4` | passes over each iteration's batch (Brax's `num_updates_per_batch`) |
| `--minibatches` | `32`, or the largest count `--envs` divides by under it | minibatches per pass; each is `--envs/--minibatches` environments' whole unrolls |
| `--hidden` | `512 256 128` | the policy MLP; the container records it |
| `--value-hidden` | the policy's | the critic MLP |
| `--activation` | `swish` | the hidden activation, recorded in the policy; `tanh` continues a policy trained before ADR-712 |
| `--entropy`, `--clip`, `--max-grad-norm` | `0.01`, `0.3`, `1.0` | Brax PPO's entropy cost, clip epsilon and gradient-norm clip (`0` does not clip) |
| `--learning-rate`, `--discount`, `--gae-lambda` | `3e-4`, `0.97`, `0.95` | optax Adam's rate; GAE's discount and lambda |
| `--value-weight`, `--reward-scaling` | `0.5`, `1.0` | the value loss's coefficient; a factor on every reward before the loss |
| `--initial-std` | unset | the exploration width a run starts at; see `action_std` below |
| `--goal-pool` | `4096` | episodes of goals drawn before training (ADR-462, below) |
| `--checkpoint-every` | `0` (off) | write a complete `.cxpolicy` every N iterations, plus `<out>.best.cxpolicy` |
| `--stop-on-collapse` | off | stop once the mean episode has collapsed (ADR-410, below) |
| `--progress` | beside `--out` | where to rewrite `progress.json` |
| `--label`, `--quiet` | | a label recorded in the policy; no stderr curve |

## Shaping the command

Three flags shape what the policy issues or is paid. All three default to
**off**, and off means the emitted jax graph is the one this file emitted
before the flag existed: each is a Python value branched on at trace time,
never a `jnp.where`.

| Flag | Default | What it is |
|---|---|---|
| `--action-filter-alpha` | `1.0` (no filter) | ADR-160. Low-passes the command between the clamp and `data.ctrl`: `a[t] = α·clamped[t] + (1−α)·a[t−1]`, per environment, reset with the episode. Bounds **smoothness**. |
| `--command-slew-deg` | `0.0` (no limit) | ADR-162. Clips the issued command to `previous ± S` degrees, *after* the filter. Bounds **rate**, which the filter does not. `0` is off here, unlike alpha, where `0` freezes the command and is refused. |
| `--reward-floor F` | absent (no floor) | ADR-700. Clamps each step's summed reward from below: `r = max(Σ wᵢ·termᵢ, F)`, as MuJoCo Playground's locomotion recipes clip theirs at 0. At or above the cost of dying it removes the pay for ending an episode early while costs outweigh rewards. A task that only pays costs learns nothing under a floor of 0. Training-only: recorded at `training.reward_floor`, never applied by an evaluator. |

**Filter, smooth and rate-limit are three different operators.** An EMA's
per-step change is `α·|raw − previous|`, so on a ±25° command box at α 0.65 it
can still move 32.5° in one control step — more than the box's own half-width.
Turning alpha further down does not turn it into a rate limit; that is what
`--command-slew-deg` is for, and the two compose in that order because the
playback harness composes them in that order.

**The engine plays a policy under the filter it recorded** (ADR-558). Both
values go into the `.cxpolicy` header at `training.action_filter_alpha` and
`training.command_slew_deg`, and every rollout, checkpoint rollout and
evaluation (`CadexDynamics.rollout_policy`) applies them in the same order,
first command of the episode unfiltered. A header that records neither plays
unfiltered, as it was trained. There is no flag to set at evaluation.

A slew limit at or below the joint's own physical reach in one control step is
worse than none: it forbids commands the servo *can* execute. Measure it
against the actuator rather than deriving it — ADR-162 carries the numbers.

## Warm starts, and crossing a task change (ADR-161)

| Flag | What it is |
|---|---|
| `--init-from POLICY` | start the actor from an existing `.cxpolicy`. It must match this bundle's task and model digests, its observation channels in order, its action table, the `--hidden` shape and the `--activation` it was trained with. The actor's location half, its exploration width (unless `--initial-std` is given, ADR-471) and the observation normaliser are carried, the normaliser with the weight of the samples it rests on (ADR-753). The critic and the optimiser start fresh: the container holds neither. |
| `--init-from-task-change REASON` | let `--init-from` cross a task change, as a **curriculum**, with a one-line reason written into the policy header. It skips the whole-file task digest and nothing else. Requires `--init-from-parent-task`. |
| `--init-from-parent-task BUNDLE` | the bundle the source policy was trained on. Its digest must equal the one in that policy's header, so the change can be named key by key. |
| `--family BUNDLE…` | train **one policy on a family** of built variants of one robot (ADR-759): the bundle is variant 0 and names the run, these are the others. Each must map a body with a `morph` block and share the channels, joints, reward-term count, episode and model sizes. The environments are split into contiguous blocks, one per variant, each its own environment (model, randomisation, reward, terminations, clip, reset, pushes, action box); environment *e* draws `random.Random(seed + e)` whatever its variant. The actor and critic read the variant's `morph.*` constants after the channels, and the header lists the variants under `training.family`. Such a policy is a base, not something the engine plays: `--init-from-base` folds its morph inputs into the bias at the target's own values. |
| `--init-from-base REASON` | let `--init-from` cross onto **another robot of the family** (ADR-755). Both bundles map a canonical body (`api.task(body=...)`); the digests are not compared, but the family and version, the hidden layers and at least one shared joint slot per leg are, and `--critic-warmup` is required. The actor is remapped by canonical name: matched inputs and actions copy, sign-corrected, with the statistics mapped through each channel's sign, offset and scale; a source input the target lacks folds into the first layer's bias at its rest value; a target input or action the source lacks starts at zero (its box centre) with the default exploration width. The actor's statistics keep the base's sample count on the inputs it shares with the target, and a target input the base lacks starts fresh, set by the target's own first batch (ADR-760). |

The keys that may differ are `CURRICULUM_TASK_KEYS`: `disturbance`,
`episode` (`episode_seconds` and `max_steps` only, never the control rate),
`label`, `randomisation`, `reset_variation`, `reward`, `success` (ADR-597)
and `termination`. None changes what the network reads or emits. Every
other key is refused: `observations`, `actions`, `goal`, `reference` and
the rest. A goal's draw range is the one part of `goal` that may move
(ADR-791): when its entries differ only in `CURRICULUM_GOAL_KEYS` (`low`,
`high`, `nominal`, `sequence`) the step is named `goal.range` and admitted,
because the actor reads the drawn value as it is; its channels, kind, unit,
period and ramp may not move. One exception is a step onto a course, or between courses
(ADR-736). There, `model`, `terrain`, `scans` and `observations` may move
together, provided the robot is the same less everything named
`environment/` (`robot_xml`), and only privileged rows (a height scan) come
or go. Because the critic starts fresh, `--critic-warmup N` trains only the
critic for the first N iterations (ADR-740). Without it, PPO followed the
fresh critic's noise and knocked the carried actor over.

Every policy before ADR-712 is `tanh`; continue one with `--activation tanh`.
`training/test_curriculum_warm_start.py` (training venv) holds these rules.
`training/test_canonical_body.py` holds the base remap: onto its own robot
it is the identity, and onto the same robot listed in another order with a
joint mounted the other way round it plays the same actions.

## Distilling teachers by command band (ADR-825)

`--teacher LOW:HIGH:POLICY`, repeated, trains a cold student on the bundle
while each teacher's action is a target on the steps whose goal (`--teacher-goal`,
default `cmd`) lies in `[LOW, HIGH)`; the last band also takes its `HIGH`.
The term is `--distill-weight` (default 1) times the mean, over every step
of the minibatch, of the taught mask times the squared distance between
`tanh` of the student's location and `tanh` of the teacher's: the action
the engine plays, before the action box. It sits beside PPO's loss, which
still trains every step, so a band with no teacher learns from the reward
alone. Each teacher's network reads its own normaliser, as it was played.

A teacher must be on the same model, read the bundle's actor channels in
order and emit its action table (`check_policy_fits` without the task
digest: a teacher was trained on another bundle). Bands may not overlap and
stay inside the goal's range; a `--family` run is refused. The header
records the teachers by digest, label, task digest and iterations under
`training.distill`, never their paths; a run without `--teacher` writes the
header it always wrote. The iteration line and the curve gain
`distill_loss` and `taught` (the share of steps with a teacher).
`training/test_distill.py` holds these rules; `docs/probes/l3r1/distill.py`
replays real teachers through them.

A band whose command is 0 is a stand. The engine evaluates it as measured
speeds with `speed_ratio` and `lateral_ratio` read as `None` (ADR-823), so
a stand is judged on the speeds and the feet, never on a ratio.

## Checkpoints, and the file a run publishes while it runs (ADR-098)

`--checkpoint-every 100` writes `walk.000100.cxpolicy`,
`walk.000200.cxpolicy`, ... and keeps `walk.best.cxpolicy` tracking the best
`reward_per_step` seen. **Each one is a complete, witness-checked policy**,
not a weight dump: pull it off the box mid-run, paste its digest into
`assembly.policy`, rebuild, and watch it. Cost is about one iteration each —
a rollout for the witness observations plus 32 forward passes — so every
hundredth of two thousand is 1 %. The first checkpoint also pays one compile
of that rollout; later ones reuse it (ADR-576).

The witness is checked on checkpoints too. That error is *relative* and grows
with the activations a policy learns (ADR-094), so a checkpoint that fails it
is a run that is going to fail it, and finding out at iteration 100 beats
finding out after four hours.

`<out>`'s directory also gets **`progress.json`**, rewritten atomically every
iteration:

```json
{"schema": "cadex-training-progress-v1", "state": "training",
 "iteration": 419, "total": 2000, "reward_per_step": 0.391,
 "episode_steps": 137.5, "action_std": 0.318,
 "best_reward_per_step": 0.402, "best_iteration": 388,
 "curve": [[0, -0.021], [1, 0.004], ..., [419, 0.391]],
 "wall_time_s": 913.0, "eta_s": 3440.0, "device": "gpu",
 "checkpoints": [...]}
```

`curve` is the whole run's reward so far, as compact
`[iteration, reward_per_step]` pairs decimated to at most
`CURVE_POINTS_CAP` (512) points with the first and last always kept —
about 12 KB at the cap, which is what makes rewriting it every iteration
free. Additive under the same schema, on the same terms as the two rows
below; it is what the dashboard's 2D viewport plots and its Training editor charts (ADR-732), for a run
under the project's `runs/<run>/train/`.

`episode_steps` is the row to actually watch (ADR-101): mean episode length,
steps in the batch over episodes that ended in it. **A reward that climbs
while this falls is a policy failing sooner and being paid more for it** —
which is what two runs did, unnoticed, before there was a number for it. It
is additive under the same schema, so a `progress.json` from before ADR-101
still reads; the dashboard just has no episode-length curve to plot.

**The trainer now watches it too (ADR-410).** When every one of the last 50
iterations averaged under both 5% of the horizon and half of the run's own
early episode length (iterations 1–10), the policy has learned that ending
its episodes pays. It says so on stderr and as `progress.json`'s `warning`
(additive, same schema), naming the fix: a positive per-step reward.
`--stop-on-collapse` stops the run there instead of training on; `cadex
walk` always passes it. hex3 (2026-09-26) fell from 28 to 2 of 200 steps by
iteration ~80 and then trained for seven hours.

`action_std` is the second row to watch (ADR-103): the mean width of the
Gaussian the rollout samples its actions from. Brax's network outputs that
width beside the action, so it depends on the observation. A cold run
starts where Brax's network does, about 0.69; `--initial-std` sets the
start instead, and `--init-from` carries the source policy's own per-action
width unless `--initial-std` is given (ADR-471). Nothing but the loss
bounds it. A σ that has walked well off its start is a policy whose
rollouts and whose mean action are no longer the same policy, which is the
first thing to rule out when a training curve and a local replay disagree.
Additive on the same terms as `episode_steps`. Every `.cxpolicy` header
carries it as `exploration.log_std`, per action, the mean over the witness
observations, with `exploration.state_dependent: true` (ADR-712).

This is the one artifact everything downstream reads —
`remote_train.sh watch` over rsync, `train_status`, `cadex walk`, and the
dashboard's training plots locally.
Nothing parses this program's stderr, deliberately: ADR-093 measured what
happens when a receipt is taken from a stream something else can write into.

Why it matters in minutes: `mg-legs` trained for 76 minutes and its reward
**peaked at iteration 1200 of 2000**. Thirty of those minutes made the policy
worse, and the run produced exactly one artifact.

## Domain randomisation, and the extension this trainer states

The bundle states exactly one algorithm: `random.Random(seed)` drawing
`uniform(low, high)` in bundle order. That is **one** parameter set, and a
training run needs thousands.

The extension is written into the container rather than left to be inferred
from whichever loop happened to run:

> **Environment *e* of the batch uses `seed = base_seed + e`**, the bundle's
> own algorithm unchanged, held fixed for the run.

Measured: 1000 seeds give 1000 distinct draw tuples, and seed 0 reproduces
the bundle's own numbers exactly — so a single-environment run at
`base_seed` is the episode the engine already plays. What this does *not*
do is resample the *mechanism* per episode; that would need the batched
model rebuilt inside the training loop, and the limitation is stated here
rather than discovered. The XML is compiled once, and only the drawn fields
are batched, so host memory does not grow with `--envs` (ADR-695). Fields
`mj_setConst` derives (for example `body_subtreemass`) are not batched:
every environment uses environment 0's.

## Courses, re-drawn per episode (ADR-717)

A task on a drawn box course carries its pool of courses in the bundle's
`terrain.pool`. The trainer rebuilds each pooled course's boxes with its
own copy of the engine's builder (`course_boxes`, `course_geoms`), and at
every reset gives each environment a course by `jax.random.randint` folded
from the reset key. `place_course` writes that course's geoms into the MJX
model inside the vmapped step, and the height scan (ADR-715) reads the
same course. The policy header records `training.terrain`. Train on a box
course, not a heightfield: MJX's heightfield collider is unstable under
driven motion (ADR-715, ADR-716), and a heightfield is never re-drawn.

## Goals, and the one draw this trainer takes from the bundle (ADR-462)

A task may declare goals (`assembly.goal`): a number, a commanded speed or a
reachable point, drawn per episode and optionally again during it. The
policy observes every goal after its sensor channels, the reward and the
terminations name goal channels, and the bundle states how they are drawn
in `goal_algorithm`.

Unlike the reset variation below, **the trainer draws goals by the bundle's
own algorithm, number for number**:

> **`random.Random(base_seed)` drawing `--goal-pool` consecutive episodes by
> the bundle's `goal_algorithm` on the host; on device each environment is
> given one pooled episode, chosen by `jax.random.randint` on every reset.**

The reason is what a `point` is: where a tip is at a drawn joint
configuration that touches nothing it does not already touch and clears a
stated height. That takes forward kinematics and a contact check, and a
second rule that only resembled the bundle's would train a policy on
targets the evaluation never asks for. So `draw_goals` here is a copy of
`CadexDynamics.draw_episode_goals`, run with stock `mujoco` before training
starts, with the same segment rule (`goal_segment`: `steps //
resample_steps`, clamped) and the same scripted openings
(`GOAL_SEQUENCE_ALGORITHM`, ADR-721: a goal's `sequence` holds its first
segments, and each draw is still taken). On a coupled mechanism the goal
also carries `followers`, which the draw places by their coupling law
before it forwards the pose (`place_goal_followers`, ADR-474). The copies
are written out because this file cannot import the engine; since ADR-725
no test holds them equal.

- `--goal-pool N` (default 4096) is how many episodes are drawn. It is
  ignored, and left out of the policy header, for a task with no goal.
- The header records the stream under `training.goal`.
- **`--seed` may not be one of the bundle's evaluation seeds**, and the
  trainer refuses one before importing anything. The pool's first episode
  is the first draws of `random.Random(seed)`; for a task with no
  randomisation, reset variation or disturbance those are exactly the goals
  that evaluation seed is judged on.
- A task with no goal takes no extra key split and carries no extra member
  in the scan, so it trains as it did.
- A warm start across a changed goal is refused: `goal` is not among the
  keys `--init-from-task-change` may move.

## Reset variation and disturbance, and a second algorithm (ADR-097)

M9 added two things the bundle can declare that change **every episode**
rather than every environment: where the episode starts
(`assembly.reset_variation` — a rigid tilt of the floating base, a lift, a
spin) and what happens to it while it runs (`assembly.disturbance` — a force
at a body's centre of mass, in a window or sustained).

This trainer implements both, and its algorithm is **deliberately not the
bundle's**:

> **`jax.random.split` of the rollout key, drawing `uniform(low, high)` in
> bundle order per environment on every reset.**

The bundle states a host-side `random.Random(seed)` stream. That cannot run
here: a reset happens **on device, inside a jitted scan**, thousands of times
an iteration. The two do not produce the same numbers and do not need to —
nobody replays a training episode, and what has to be reproducible from the
script is the *rollout*, which runs in the engine on the stdlib path. Both
algorithms are recorded in the policy header under `training.randomisation`
and `training.episode_variation`.

What **must** be identical is the arithmetic: the same quaternion product,
the same window test, the same centre-of-mass application point. Those are
written out here rather than shared, because this file cannot import the
engine.

A disturbance is a property of the *episode*: the draw has to survive every
step between the reset that made it and the reset that replaces it, and its
window is tested against an **episode-local** clock rather than `data.time`,
which this trainer's reset does not rewind. So each environment's state
carries, beside the MJX data, its pushes (`forces`, `starts`), the
episode's `elapsed` time and `steps`, and, when the task has them, its
goal pick, its reference start sample (ADR-709), its course (ADR-717) and,
on a speed cadence or a speed schedule, the gait clock's turned cycles
(`turned`, ADR-752, ADR-773). On a schedule the reference is the strides
blended at the goal's commanded speed each step (`tracking_vector(...,
told)`), a goal may ramp between segments (`goals_at`), and a random start
row is a sample of the stride nearest the opening command, whose goal pick
is drawn first (`fold_in(key, 773)`). A task without a goal, a reference
start, a course, a cadence or a schedule carries no member for it and draws
no key for it, so it trains as it did.

## The episode is the bundle's, not the trainer's (ADR-101)

An episode ends when the task terminates **or** when it reaches the bundle's
`episode["max_steps"]`, the same number `CadexDynamics.evaluate_episode`
bounds its own loop by. For two runs the horizon was read out of the bundle
and never used, so an environment whose policy did not fall over never
reset: past the last shove window it was never pushed again, never re-drawn,
and stood still collecting the `alive` bonus.

The two endings are **not** the same event and the code keeps them apart:

* a **failure** ends the future, so the state after it is worth zero;
* a **timeout** ends only our looking, so the state we landed in is worth
  whatever the critic thinks.

So the step's `truncation` flag marks a timeout and only a timeout (a step
that terminates on its last step is a failure). Brax's GAE masks a
truncated step and bootstraps from the critic, and cuts the bootstrap on a
failure (ADR-712). A reset environment's readings are of its new pose:
`mjx.forward` runs where an episode ended.

## Two evaluators of one whitelist

`CadexDynamics` compiles reward expressions, and this file compiles them
again under `jax.numpy` so they vectorise. That is where a whitelist
drifts, so the bundle ships its `functions` array, this file builds its own
from scratch, and it **refuses outright** when the two differ rather than
failing partway through a run. (A third evaluator, the stock-MuJoCo
reference runner `cadex_tests/dynamics_task_episode.py`, went with ADR-725.)

The same discipline covers the container: `encode_policy` here and
`CadexDynamics.encode_policy` are two implementations of one format. The
engine decodes and verifies every policy this file writes, witness
included, so a drift is a refusal on rebuild.

## Stateful foot terms (ADR-870)

Two of MuJoCo Playground's locomotion terms read a per-foot memory, which a
reward expression cannot: `feet_air_time` (time since lift-off less a
threshold) and `feet_height` (the swing peak's squared shortfall from a
target), each paid at first contact while the command is not zero. A task's
optional `feet` block names the channels they read:

```json
"feet": {"contacts": ["kfl_down", ...], "heights": ["pfl_z", ...],
         "height_scale": 0.001, "active": "sqrt((cx/1000)**2+...)",
         "active_above": 0.01,
         "air_time": {"weight": 0.002, "threshold_s": 0.1},
         "swing_height": {"weight": -0.004, "target_m": 0.12}}
```

`feet_step` keeps the memory in Playground's order, and `--reward-floor`
then clips the whole sum. Training-only: no evaluator scores it.

## A saturated servo is the engine's machine (ADR-465)

MJX and stock MuJoCo are the same physics only where they agree, and a
Cadex servo is where they did not. Under `implicitfast` MJX 3.10 folds an
affine actuator's `-kv` into the implicit step always; the engine drops it
for an actuator clamped at its `forcerange`. Every exported servo is exactly
that actuator, and a small one saturates most of the time, so ot11's walk
policies trained forwards here and walked backwards in the engine.
`match_engine_actuator_derivative` applies the engine's rule inside MJX, and
`train()` installs it before it builds a model. It replaces a function in a
private MJX module, which is tolerable only because `mujoco-mjx` is pinned.
It goes the day raw MJX agrees; since ADR-725 no test watches for that day,
so re-measure it on any `mujoco-mjx` bump.

## Screening drives and masses without a rebuild (ADR-710)

`cadex_proxy.py` answers "would these drives hold this gait?" in seconds,
on the exported model, before any CAD rebuild or training run. It edits a
bundle's model in memory, then replays the bundle's gait reference
(ADR-706) as position targets with the base held by a virtual PD support,
and rates every drive against its datasheet:

```bash
~/cadex-train-venv/bin/python training/cadex_proxy.py <bundle>-task.json \
    --drives docs/probes/orun6/d1/drives.json \
    --configs docs/probes/orun6/d1/configs.json \
    --support full attitude height posture swing inverse --joints j_scap_l j_hip_l --out sweep
```

- **A configuration** names drive swaps (`drives`: joint -> library key),
  mass moves (`move_mass`: from, to, `kg` or `fraction`) and a
  `mass_scale`. A swap sets the clamp to the peak torque, the joint's
  damping to peak over no-load speed (the line `lib.qdd` exports), the
  armature to rotor inertia times the gear ratio squared, the friction loss
  to the back-drive torque when the datasheet gives one, and puts the mass
  difference on the joint's parent body. The as-built drive is identified
  by its clamp and the bundle's `rated_effort`; one that matches no library
  drive cannot be swapped.
- **Support modes.** `full` holds the base on the reference's path and
  carries weight; `attitude` holds only attitude and horizontal position,
  so the legs carry the weight; `swing` is `full` with gravity and contact
  off: what moving the legs along the clip costs.
- **Free-path supports (ADR-711).** `height` holds attitude and height,
  `posture` attitude only; both leave the forward path to the legs. Every
  replay reports the support's forward push (% of weight), the speed the
  body reached, and each joint's RMS miss from the pose it was sent. On
  the cat the exported servo misses the trot clip by 10–16° RMS, so a held
  replay measures a lagging servo, not the gait.
- **`--support inverse` (ADR-711)** follows the clip exactly: inverse
  dynamics on its `qpos` with central differences, and the base wrench
  carried by the stance feet as least-norm forces at their COMs (flight
  samples' wrench spread over stance). It reports what the feet cannot
  supply, because a kinematic clip need not be dynamically possible.
  `--reference CLIP.json` swaps in any `CadexGait.generate` clip.
- **Output.** `OUT.json` and `OUT.md`: per configuration and mode, seeds
  completed, each drive's RMS over rated, share of steps at its peak clamp,
  peak needed and speed over no-load, and `holds` (every drive at or under
  rated RMS, at most 10 % of steps at peak, under its no-load speed, every
  seed completed).

A screen is a necessary condition. A held replay does not balance and a
position servo fighting the support inflates some torques, so a
configuration that holds goes on to a tracking run, and one that does not
is out. Like `cadex_train.py` it imports only the standard library at
module scope.

## What the suites do, and do not, prove

No suite trains (ADR-725). The engine and CLI suites hold the boundary
above and nothing of the learner. The training venv's own tests,
`training/test_cadex_proxy.py`, `training/test_curriculum_warm_start.py`,
`training/test_canonical_body.py`, `training/test_terrain_pool.py` and
`training/test_distill.py`, cover the proxy, the warm-start rules, the base
remap, the course pool's height scan (ADR-747) and distillation's routing
and refusals. A change to the trainer is
verified by running it: a few iterations on CPU (`SETUP.md` §b), then the
engine's own verification of the policy it wrote. The GPU is a speed
difference, not a semantic one, and it is the same trainer file.

## Retained review telemetry (ADR-287)

The atomic `progress.json` snapshot now includes `updated_at` (Unix seconds),
`task_sha256`, `model_sha256`, `loss_curve` and `episode_steps_curve` (and,
since ADR-606, `action_std_curve`), additively under `cadex-training-progress-v1`. Like `curve`, each history is capped at 512
uniformly selected samples including the first and last. These are retained
sampled histories, not full-resolution logs. Checkpoint names and digests stay
in `checkpoints`; files are written before their progress snapshot is committed.
A caught training or final policy packaging/saving failure preserves the last
reported histories, iteration and checkpoint references and publishes `failed`
with the error (ADR-288). `done` is published only after the final policy is
validated and saved. Hard kills or an unwritable progress file may instead leave
a stale training snapshot; the dashboard does not call it success. Keep `progress.json`
and its policy files together when retaining or copying a run. No new dependency.
