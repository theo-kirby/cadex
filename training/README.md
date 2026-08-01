# training/ — the offboard trainer

Verified against source: 2026-08-01. Provenance: `[Cadex-new]`. See
`docs/MUJOCO.md` slice M7 and ADR-084.

This directory is **not part of the engine**. CMake never installs it, it is
in no payload, and nothing in it enters `pixi.toml` — `test_engine_purity_guardrails`
asserts that no `jax` and no `mjx` reach a staged payload, and
`test_dynamics_policy_trainer` asserts no CMake rule references this path.

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
stays a geometry-and-dynamics service, the shell stays a viewer, and M7
builds **no dispatch machinery, no network I/O and no new op**: you copy two
files out, run this, and copy one file back.

**There is no train button and there is nothing to press.** The agent
authors the task, dispatches the run with its own shell, and brings the
weights home through the `put_asset` path that already exists. VISION
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
by *relative* path and sha256 — which is the whole reason copying the
`outputs/` directory works and copying two files out of it into a flat
folder does not. `inspect scope="output"` is the supported way to find the
accepted attempt's directory without guessing at the revision and attempt
ids.

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

The short form: any machine with a CUDA GPU and Python 3.11+, a venv built
from `requirements.txt` with `jax[cuda12]==0.7.2` installed over the pinned
CPU jax, the `outputs/` pair copied across, and one command.

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

Bring the file into the project store with the tool that already exists —
`import_geometry` / `put_asset`. Those two perform no suffix check *of their
own*: they pass the path through and let the engine decide, and the engine's
list (`_STORED_ASSET_SUFFIXES`, `CadexScriptedRuntime.py:361`) is what
accepts `.cxpolicy` alongside the three mesh formats. That is the whole
mechanism by which a policy reaches the store through a tool named for
geometry, and why it cost no protocol change. Then rebuild. The engine verifies the policy against the task it was trained
on and publishes a receipt.

> One rough edge, stated rather than papered over: the tool the shell offers
> is called **`import_geometry`**, and on success it advises
> `mesh.import_file(...)`, which is wrong for a policy. Fixing that wording
> is a `shell/` diff, and every line of one is a future merge conflict
> against upstream Blender (ADR-091), so it wants to be a change somebody
> makes on purpose rather than one that rides along. ADR-086 §4 named it
> available-and-not-taken and ADR-102 §4 left it that way; the engine-side
> refusals carry the correct advice in the meantime.

## Options that matter

| Flag | Default | What it is |
|---|---|---|
| `--seed` | `0` | PPO's seed *and* the base seed for domain randomisation |
| `--iterations` | `200` | outer PPO iterations |
| `--envs` | `256` | parallel MJX environments; also how many distinct randomisation draws exist |
| `--unroll` | `20` | control steps collected per environment per iteration |
| `--hidden` | `64 64` | the MLP the container records |
| `--checkpoint-every` | `0` (off) | write a complete `.cxpolicy` every N iterations, plus `<out>.best.cxpolicy` |
| `--progress` | beside `--out` | where to rewrite `progress.json` |

## Checkpoints, and the file a run publishes while it runs (ADR-098)

`--checkpoint-every 100` writes `walk.000100.cxpolicy`,
`walk.000200.cxpolicy`, ... and keeps `walk.best.cxpolicy` tracking the best
`reward_per_step` seen. **Each one is a complete, witness-checked policy**,
not a weight dump: pull it off the box mid-run, paste its digest into
`assembly.policy`, rebuild, and watch it. Cost is about one iteration each —
a rollout for the witness observations plus 32 forward passes — so every
hundredth of two thousand is 1 %.

The witness is checked on checkpoints too. That error is *relative* and grows
with the activations a policy learns (ADR-094), so a checkpoint that fails it
is a run that is going to fail it, and finding out at iteration 100 beats
finding out after four hours.

`<out>`'s directory also gets **`progress.json`**, rewritten atomically every
iteration:

```json
{"schema": "cadex-training-progress-v1", "state": "training",
 "iteration": 419, "total": 2000, "reward_per_step": 0.391,
 "episode_steps": 137.5,
 "best_reward_per_step": 0.402, "best_iteration": 388,
 "wall_time_s": 913.0, "eta_s": 3440.0, "device": "gpu",
 "checkpoints": [...]}
```

`episode_steps` is the row to actually watch (ADR-101): mean episode length,
steps in the batch over episodes that ended in it. **A reward that climbs
while this falls is a policy failing sooner and being paid more for it** —
which is what two runs did, unnoticed, before there was a number for it. It
is additive under the same schema, so a `progress.json` from before ADR-101
still reads; the panel draws it as a dash.

This is the one artifact everything downstream reads —
`remote_train.sh watch` over rsync, and the shell's Training panel locally.
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
`base_seed` is the episode the engine and the reference runner already agree
on. What this does *not* do is resample the *mechanism* per episode; that
would need the batched model rebuilt inside the training loop, and the
limitation is stated here rather than discovered.

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
written out here rather than shared — this file cannot import the engine —
and a test pins the lines against `CadexDynamics`.

The scan carry grew from `(data, key)` to `(data, key, forces, starts,
elapsed, steps)`, because a disturbance is a property of the *episode*: the
draw has to survive every step between the reset that made it and the reset
that replaces it, and its window is tested against an **episode-local** clock
rather than `data.time`, which this trainer's reset does not rewind.

## The episode is the bundle's, not the trainer's (ADR-101)

`steps` is the last member of that carry and the newest, and it is what makes
this an episode at all. An episode ends when the task terminates **or** when
it reaches the bundle's `episode["max_steps"]` — the same number
`CadexDynamics.evaluate_episode` bounds its own loop by. For two runs the
horizon was read out of the bundle and never used, so an environment whose
policy did not fall over never reset: past the last shove window it was never
pushed again, never re-drawn, and stood still collecting the `alive` bonus.

The two endings are **not** the same event and the code keeps them apart:

* a **failure** ends the future, so the state after it is worth zero;
* a **timeout** ends only our looking, so the state we landed in is worth
  whatever the critic thinks.

So `terminated` cuts the GAE **bootstrap** and `done` cuts the GAE **carry**,
and the value bootstrapped is the critic's on `landed` — the post-step,
*pre-reset* observation. Feeding a timeout into the bootstrap term would
teach the critic that surviving to step 600 is worth exactly as much as
falling over, which at `--discount 0.99` is a large bias traded for the one
this removed. It still trains, still climbs, and is wrong in a way no
run-level number reveals — which is why there is a test that reads the two
lines out of the AST.

## Three evaluators of one whitelist

`CadexDynamics` compiles reward expressions, `cadex_tests/dynamics_task_episode.py`
compiles them again, and this compiles them a third time under `jax.numpy` so
they vectorise. Three is where a whitelist drifts, so the bundle ships its
`functions` array, this file builds its own from scratch, and it **refuses
outright** when the two differ rather than failing partway through a run.
A test asserts all three are equal.

The same discipline covers the container: `encode_policy` here and
`CadexDynamics.encode_policy` are two implementations of one format, and a
test compares their bytes. This file cannot import the engine, so the second
copy is written down and pinned.

## What the CI gate does, and does not, prove

`test_dynamics_policy_live` trains a *tiny* task — one hinge, swing-up, a
fixed seed, a few hundred iterations — **on CPU**, because that is what a
test machine has. It converges: reward per step goes from 1.10 to 2.487
against a theoretical maximum of 2.5, in about four seconds.

The GPU is a speed difference, not a semantic one, and it is the same
trainer file. A remote GPU run is exercised manually and its numbers are
recorded in ADR-084. **The gate does not prove the GPU path.**
