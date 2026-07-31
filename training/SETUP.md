# Training a policy: the four ways

Verified against source: 2026-07-31. Branch **`MJC` only** (ADR-072).
Provenance: `[Cadex-new]`. See ADR-070 (training is offboard) and ADR-076
(remote dispatch).

`training/README.md` is *what the trainer is*. This is *how to run it*, end
to end, four ways. Pick the row that matches the hardware you have:

| | You have | Read |
|---|---|---|
| **(a)** | one machine, with an NVIDIA GPU | [§a](#a-one-machine-with-a-gpu) |
| **(b)** | one machine, no usable GPU | [§b](#b-cpu-only) |
| **(c)** | your laptop, plus a separate GPU box | [§c](#c-a-separate-gpu-box) |
| **(d)** | ...and you want to drive (c) with one command | [§d](#d-driving-the-box-with-remote_trainsh) |

Two facts shape all four. **The engine cannot train** — no `jax` and no
`mjx` reaches `src/Mod/cadex` or a staged payload, and a test asserts it
(ADR-070). And **the Mac cannot train**, in the sense that matters: MJX
needs JAX-on-GPU, `jax-metal` is 0.1.0, and the community MPS backends have
known compatibility problems. So every path below ends with a `.cxpolicy`
file arriving back in the project, and none of them involves the engine
growing a dependency.

---

## Getting the bundle out, which every path needs

Training reads a **pair** that the accepted attempt already wrote:

```
<project>/script_artifacts/<revision>/attempt-<id>/outputs/<name>-task.json
<project>/script_artifacts/<revision>/attempt-<id>/outputs/<name>-model.xml
```

Find that directory with `inspect scope="output"` rather than guessing at
revision and attempt ids.

They must stay **side by side**. The bundle references the model by a
*relative* path and a sha256, which is what makes the pair movable at all —
and why copying the whole `outputs/` directory works and copying two files
into a flat folder of your own devising also works, but copying only the
JSON does not.

---

## (a) One machine, with a GPU

A Linux box with an NVIDIA GPU and a CUDA driver, where you also have the
repository checked out.

```bash
python3 -m venv ~/cadex-train-venv
~/cadex-train-venv/bin/pip install -r training/requirements.txt
~/cadex-train-venv/bin/pip install 'jax[cuda12]==0.7.2'   # replaces the CPU jax
```

The second `pip install` is not optional on this path and is the single
thing most likely to be skipped: `requirements.txt` pins the **CPU** jax,
because that is what a test machine can install. Confirm before spending an
hour:

```bash
~/cadex-train-venv/bin/python -c 'import jax; print(jax.default_backend())'   # -> gpu
```

If that prints `cpu`, you are on path (b) whether you meant to be or not.
Then:

```bash
~/cadex-train-venv/bin/python training/cadex_train.py \
    <outputs>/walk-task.json --out ~/walk.cxpolicy --seed 0 --iterations 400
```

It prints its reward curve on **stderr** as it goes and exactly one line of
**JSON** on stdout at the end. Keep that line — the `sha256` in it is what
goes into the script (see [Bringing it home](#bringing-it-home)), and
`device` in it is how you find out afterwards that it trained on CPU.

## (b) CPU only

Supported, deliberately, and it is what the CI gate does — but understand
what you are buying. `test_dynamics_policy_live` converges a *tiny* task
(one hinge, swing-up) in about four seconds on CPU. The published reference
for a real gait is a Unitree G1 walking policy converging in ~90 minutes at
4096 parallel environments on an RTX 4090. On CPU that is days.

```bash
python3 -m venv .venv
.venv/bin/pip install -r training/requirements.txt        # the CPU jax, as pinned
.venv/bin/python training/cadex_train.py <outputs>/walk-task.json \
    --out walk.cxpolicy --envs 16 --iterations 50
```

Drop `--envs` hard. The default of 256 is sized for a GPU, and on CPU it
mostly buys memory traffic. This path is for proving a task *runs* — that
the reward expression compiles, the observation channels are the ones you
meant, the episode does not immediately terminate — before renting
something. It is not for producing a gait.

## (c) A separate GPU box

The normal case: modelling on a laptop, training somewhere with a GPU.
Nothing Cadex is installed on the box and nothing Cadex needs to be — but
the repository must be checked out there, because that is where
`cadex_train.py` lives.

**On the box, once:**

```bash
git clone <this repo> ~/cadex && cd ~/cadex
python3 -m venv ~/cadex-train-venv
~/cadex-train-venv/bin/pip install -r training/requirements.txt
~/cadex-train-venv/bin/pip install 'jax[cuda12]==0.7.2'
mkdir -p ~/cadex-jobs
~/cadex-train-venv/bin/python -c 'import jax; print(jax.default_backend())'   # -> gpu
```

A full checkout is more than the trainer strictly needs — it is one file and
a requirements list. It is what is documented because the policy records
`trainer_sha256`, so a checkout at a known revision makes *which* trainer
ran recoverable; a file someone scp'd once does not.

**Per run, by hand:**

```bash
outputs=<project>/script_artifacts/<revision>/attempt-<id>/outputs
scp -r "${outputs}" box:~/cadex-jobs/
ssh box '~/cadex-train-venv/bin/python ~/cadex/training/cadex_train.py \
    ~/cadex-jobs/outputs/walk-task.json --out ~/cadex-jobs/walk.cxpolicy \
    --seed 0 --iterations 400'
scp box:~/cadex-jobs/walk.cxpolicy .
shasum -a 256 walk.cxpolicy        # must equal the sha256 the run printed
```

That last line is not ceremony. The digest you paste into the script is the
one the *engine* re-computes on the file it is given, so a truncated
transfer is otherwise discovered as a policy refusal with no obvious cause.

## (d) Driving the box with `remote_train.sh`

Path (c), as one command, with the checks that are easy to skip by hand made
mandatory. `training/remote_train.sh` (ADR-076) does exactly the three steps
above — copy two files out, run the trainer, copy one file back — and adds
nothing to the product: no new op, no protocol change, nothing in
`pixi.toml`, no CMake rule.

**Configure, once:**

```bash
cp training/remote.env.example training/.remote.env
$EDITOR training/.remote.env
```

`.remote.env` is a dotfile and git ignores it two ways over. Every variable
is commented in the example; the ones without defaults are the host, the
repo, the venv and a scratch directory. Authentication is **a path to a key
file** — there is no password variable, because `ssh` has no
non-interactive password path without `sshpass` and a plaintext secret on
disk is a worse thing to own than a path to a key.

Values are read literally, *not* sourced, so a `~` in them means the box's
home directory rather than your laptop's.

**Pre-flight the box:**

```bash
training/remote_train.sh check
```

It reports everything wrong in one round trip rather than one problem per
trip: ssh reachable, the repo present, the venv present **and a venv**, the
four pinned packages at exactly the pinned versions, `jax.default_backend()`
actually `gpu`, and what `nvidia-smi` says. It **never creates the venv** —
it exits naming the path and giving you the three commands. A venv this
script silently built is a venv nobody knows the contents of, and exact pins
exist so that the contents are known.

**Run:**

```bash
training/remote_train.sh train <outputs>/walk-task.json ./walk.cxpolicy \
    -- --seed 0 --iterations 400 --envs 4096
```

Everything after `--` goes to the trainer untouched. The reward curve
streams to your terminal while it trains. Afterwards the policy is copied
back, its sha256 **verified locally against the one the run reported**, and
the run is **rejected if `device` is not `gpu`** — pass `--allow-cpu` if a
CPU run was the intent. That last assertion is the whole reason this file
exists: a silent CPU fallback produces a perfectly valid policy and real
numbers, and costs hours, and is otherwise visible only to someone who
thinks to read `device` out of the artifact afterwards.

`training/remote_train.sh shell` opens an interactive session with the same
configuration — use it once to accept the host key, since `check` and
`train` run under `BatchMode` where any prompt reads as a connection
failure. `training/remote_train.sh config` prints what it resolved.

---

## Bringing it home

Identical on all four paths. Put the file in the project store with the tool
that already exists — `import_geometry` / `put_asset`, which pass the path
through and let the engine's `_STORED_ASSET_SUFFIXES` accept `.cxpolicy`
alongside the three mesh formats — then reference it by digest:

```python
task   = assembly.task(model, actions=[...], reward=[...],
                       episode_seconds=2.0, control_hz=50)
policy = assembly.policy(task, weights="walk.cxpolicy",
                         sha256="<the sha256 the run printed>", label="gait")
result = {"job_model": model, "job_task": task, "job_policy": policy}
```

Rebuild. The engine verifies the policy against the task it was trained on —
re-computing the witness actions with its own pure-Python forward pass and
refusing past `CadexDynamics.POLICY_WITNESS_TOLERANCE` — and publishes a
receipt. A policy whose weights are fine but whose architecture the engine
reads differently is a refusal, not a bad gait.

## When it will not train

- **`jax.default_backend()` is `cpu` on a box with a GPU.** The GPU wheel
  was not installed over the pinned CPU one, or the driver is broken.
  `nvidia-smi` in `check`'s output is there to tell those two apart — and
  when the driver is the problem, installing the wheel looks like it did not
  work, so `check` says which to do first.
- **`nvidia-smi` fails but jax has the GPU anyway.** Real, and measured on
  `sb9x`: NVML and the CUDA driver API are separate libraries, so a
  driver package upgraded without a reboot can leave
  `Failed to initialize NVML: Driver/library version mismatch` while jax
  still runs at 23 TFLOP/s. `check` reports this as a **WARN, not a
  failure** — the box trains fine; what you lose is monitoring, with no
  utilisation or temperature reading during a run. `check` prints the loaded
  kernel-module version beside the userspace library version, because those
  two numbers are the difference between "it is broken" and something
  somebody can act on: when they differ, reboot.
- **A version mismatch `check` refuses.** MuJoCo's own `VERSIONING.md`
  disclaims cross-version numerical reproducibility, so a box one patch
  release off yields numbers that cannot be compared against the engine's.
  That is a wrong answer, not a slow one, which is why it is refused rather
  than warned about.
- **`the model ... is beside neither`.** The pair was separated. Copy the
  whole `outputs/` directory.
- **Reward per step is `nan` from iteration 0.** The trainer stops at the
  first non-finite number and names the iteration, rather than training on
  for another 150 and then dying in the encoder. The task is wrong, not the
  run — check the reward expression and the episode's termination.
