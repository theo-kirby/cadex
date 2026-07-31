# training/ — the offboard trainer

Verified against source: 2026-07-31. Branch **`MJC` only** (ADR-063).
Provenance: `[Cadex-new]`. See `docs/MUJOCO.md` slice M7 and ADR-070.

This directory is **not part of the engine**. CMake never installs it, it is
in no payload, and nothing in it enters `pixi.toml` — `test_engine_purity_guardrails`
asserts that no `jax` and no `mjx` reach a staged payload, and
`test_dynamics_policy_trainer` asserts no CMake rule references this path.

It is a thing you **copy to another machine**.

## Why training is offboard

Training does not run on the user's laptop, and that is a design decision
rather than a temporary state (ADR-060, restated by ADR-070):

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

Reads the pair M6 already makes movable:

```
<project>/outputs/<name>-task.json    a cadex-training-task-v1 bundle
<project>/outputs/<name>-model.xml    the MJCF it references, by relative
                                      path and sha256
```

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

## Standing up a box

Any machine with a CUDA GPU and Python 3.11+. Nothing Cadex is installed on
it and nothing Cadex needs to be.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt          # CPU
.venv/bin/pip install "jax[cuda12]==0.7.2"         # ...or replace jax with the GPU wheel
```

`mujoco` must match the release that wrote the model. The bundle records it
as `mujoco_version`; a mismatch is a run whose numbers cannot be compared
with the engine's, because MuJoCo's own `VERSIONING.md` disclaims
cross-version numerical reproducibility. That is why every line of
`requirements.txt` is `==` and not `>=`.

## Dispatching a run

```bash
scp -r <project>/outputs box:~/job/
ssh box '.venv/bin/python cadex_train.py ~/job/outputs/walk-task.json \
    --out ~/job/walk.cxpolicy --seed 0 --iterations 400'
scp box:~/job/walk.cxpolicy .
```

It prints one line of JSON on success — the output path, its size, its
**sha256**, the parameter count, the task digest, the final reward per step,
the wall time, the device, and `cadex_importable` (which must be `false`).

The sha256 is the one you paste into the script:

```python
task   = assembly.task(model, actions=[...], reward=[...],
                       episode_seconds=2.0, control_hz=50)
policy = assembly.policy(task, weights="walk.cxpolicy",
                         sha256="<the sha256 it printed>", label="gait")
result = {"job_model": model, "job_task": task, "job_policy": policy}
```

Bring the file into the project store with the tool that already exists —
`import_geometry` / `put_asset`, which perform no suffix check of their own —
then rebuild. The engine verifies the policy against the task it was trained
on and publishes a receipt.

> One rough edge, stated rather than papered over: the tool the shell offers
> is called **`import_geometry`**, and on success it advises
> `mesh.import_file(...)`, which is wrong for a policy. Fixing that wording
> is a `shell/` diff, and ADR-063 says the whole branch rests on
> `git diff main...MJC -- shell/` printing nothing — so it is deliberately
> not taken. The engine-side refusals carry the correct advice instead.

## Options that matter

| Flag | Default | What it is |
|---|---|---|
| `--seed` | `0` | PPO's seed *and* the base seed for domain randomisation |
| `--iterations` | `200` | outer PPO iterations |
| `--envs` | `256` | parallel MJX environments; also how many distinct randomisation draws exist |
| `--unroll` | `20` | control steps collected per environment per iteration |
| `--hidden` | `64 64` | the MLP the container records |

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
on. What this does *not* do is resample per episode; that would need the
batched model rebuilt inside the training loop, and the limitation is stated
here rather than discovered.

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
recorded in ADR-070. **The gate does not prove the GPU path.**
