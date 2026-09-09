# Training a policy: the four ways

Verified against source: 2026-09-08. Provenance: `[Cadex-new]`. See
ADR-084 (training is offboard) and ADR-089
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
(ADR-084). And **the Mac cannot train**, in the sense that matters: MJX
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

Each stderr line carries three numbers, and the third is the one to watch:

```
iteration  419  reward/step +0.391  loss +0.0021  episode 137.5
```

`episode` is the mean episode length in control steps (ADR-101). **A reward
that climbs while it falls is a policy failing sooner and being paid more
for it** — the failure two runs on this branch had, with no number recording
it. If it reads as `envs × unroll` exactly, no episode is ending at all.

## (b) CPU only

Use CPU for toy tasks and lifecycle verification; it does not establish a
learned gait. Set `JAX_PLATFORMS=cpu` explicitly even when the discovered
venv also supports CUDA. Installing the base requirements does not remove
an existing CUDA plugin. Confirm the trainer receipt reports `device: cpu`.

**Python ≥ 3.12**, and that is a floor, not a preference: the pinned
`numpy==2.5.1` has no wheels below cp312. The pixi environment's 3.11
cannot host this venv — use the OS's own newer interpreter. On macOS the
Homebrew 3.13 is the recommended one, and all four pins have arm64 wheels
for cp312/cp313/cp314:

```bash
/opt/homebrew/bin/python3.13 -m venv .venv           # repo root; gitignored
.venv/bin/pip install -r training/requirements.txt   # pinned trainer dependencies
.venv/bin/pip install pytest                         # to run the venv-gated suites
```

`pytest` is a convenience for running the trainer's own gates from this
venv, not a fifth pin — nothing about a training run needs it.

The CLI discovers `<repo>/.venv`, then `~/cadex-train-venv`, or uses
`--trainer-python` / `$CADEX_TRAIN_PYTHON`; it never creates a venv.
For an existing toy project with a task, run from the repository root:

```bash
JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" \
    --out "$PROJECT/runs/cpu-baseline" --name cpu-baseline.cxpolicy \
    --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

Use fresh output and policy names. This runs export, training, storage,
policy verification, rollout and all four reviews (`docs/CLI.md` §2).
`examples/lifecycle/README.md` supplies the model-free project setup.
`--timeout` bounds the trainer only; under a strict resource budget also
monitor process-tree memory and elapsed time, as that example documents.
The direct trainer invocation uses the same backend selection:

```bash
JAX_PLATFORMS=cpu .venv/bin/python training/cadex_train.py <outputs>/walk-task.json \
    --out walk.cxpolicy --envs 32 --iterations 300 \
    --checkpoint-every 50 --progress <project>/training-progress.json
```

Keep toy environment counts small: the default 256 is sized for a GPU.
Checkpoints are complete, playable policies; `--checkpoint-every 50`
costs about one extra iteration per checkpoint.

**`--progress` is how a local run lights up the shell.** The Training
panel polls `<project>/training-progress.json`; on paths (c) and (d) it is
`remote_train.sh watch` that writes that file, but a local trainer can
just write it there itself — no `watch` leg, no ssh, nothing else running.
Note the redirect is total: with `--progress` the trainer writes *only*
the file you named, not also the default `progress.json` beside `--out`.

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
mandatory. `training/remote_train.sh` (ADR-089) does exactly the three steps
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

**From the CLI, as the walk's training leg (ADR-200):**

```bash
./cadex train --project ./b --out ./b/runs/r1/train --remote --put \
    --iterations 400 --envs 4096
./cadex walk  --project ./b --out ./b/runs/r1 --remote --iterations 400 --envs 4096
```

`cadex train --remote` is `cadex train` with this script in place of the
venv's interpreter: the CLI rebuilds, exports the bundle and the model into
`--out`, runs `remote_train.sh train <bundle> <out.cxpolicy> -- <the same
trainer flags>`, verifies the returned file against the receipt's sha256
and, with `--put`, stores it — so the policy lands at the path the local
trainer would have written and every later step (`cadex script --set`,
the verified rollout, `review.json`) is unchanged. `cadex walk --remote`
is the whole walk with that one leg on the box. `--allow-cpu` passes
through. `cadex train --remote --detach` returns a pending launch receipt in
`--out/training-receipt.json`; `--out` must lie inside the project. No policy
is verified or stored, even with `--put`. Use its run ID with `watch`/`pull`
into a fresh destination, then verify and store the returned policy explicitly.
The same locator is printed as the last JSON line by the dispatcher itself.
`walk` remains blocking; detached collection and continuation are not automated.
A warm start goes too (below). Run `check` first: the CLI reads none of
`.remote.env` and repairs nothing. See ADR-278 and `docs/CLI.md` for pending
semantics and the timeout limit (ending SSH does not stop remote training).
`docs/CLI.md` §2 is the contract.

### A warm start, on the box (ADR-268)

The curriculum pair (ADR-161) names two files on **this** machine, and the
box has seen neither:

```bash
training/remote_train.sh train ./runs/r2/walk-task.json ./runs/r2/walk.cxpolicy \
    -- --iterations 400 --envs 4096 \
       --init-from ./runs/r1/walk.cxpolicy \
       --init-from-parent-task ./runs/r1/walk-task.json \
       --init-from-task-change "a wider shove band"
```

The script lifts those two paths out of the flags after `--`, copies both
files into a `warm/` subdirectory of the run directory — a subdirectory, so
a parent bundle named like the child cannot overwrite it — and re-emits the
two flags pointing at the copies. Everything else after `--` is passed
through untouched, so what the box's trainer is handed is the same argument
list you would have run here. The parent bundle arrives byte-identical
because the trainer ties its digest to the policy's header and refuses
otherwise.

It refuses before it copies anything when a warm file is missing, when the
joined `--init-from=PATH` form is used (that path would reach the box
unrewritten, naming a file that is not there), or when the two warm files
share a basename and would collide in one flat `warm/`. Same rule as the
rest of this script: fail loudly rather than repair.

The same applies through the CLI — `cadex train --remote --init-from …` and
an iterate walk are no longer usage errors — which is what makes an iterate
the same shape locally and on the box.

**Plan it before you dispatch it** (ADR-255). `check` tells you the box is
ready; `--dry-run` tells you what would be sent to it, without sending
anything:

```bash
./cadex train --project ./b --out ./b/runs/r1/train --remote --put --dry-run     --iterations 400 --envs 4096 --json
```

That rebuilds and exports for real, then reports `training_plan` instead of
training: the four files the leg touches — the bundle, the model beside it,
the policy, the stored asset — and the ordered `steps` that touch them,
with `executed: false`. Run it with and without `--remote` and the
`artifacts` are the same object both times; the remote `steps` are the
local ones (`export → train → verify → store`) with `copy-out` and
`copy-back` around the trainer. That is the whole difference between
training here and training on the box, and it is checkable on a machine
that never opens an ssh. It runs no trainer, stores nothing and reads none
of `.remote.env` — it is a plan, not a pre-flight, and it is no substitute
for `check`. Use it in front of `cadex walk --remote`, whose train leg
would otherwise fail only after the design and assembly legs have already
run.

`training/remote_train.sh shell` opens an interactive session with the same
configuration — use it once to accept the host key, since `check` and
`train` run under `BatchMode` where any prompt reads as a connection
failure. `training/remote_train.sh config` prints what it resolved.

### Detached, which is what you want for a real run (ADR-098)

A run is an hour or more, and `train` without `--detach` is one ssh held open
for all of it — so a closed laptop, a sleeping wifi chip or a dropped VPN is
a lost run. Detach instead:

```bash
training/remote_train.sh train <outputs>/stand-task.json ./runs/stand.cxpolicy \
    --detach -- --seed 0 --iterations 2000 --envs 4096 --checkpoint-every 100
#   ==> detached, run stand-task-20260801-162733 (pid 3293214)

training/remote_train.sh watch stand-task-20260801-162733 ~/proj/mg-legs.cadex
training/remote_train.sh pull  stand-task-20260801-162733
training/remote_train.sh stop  stand-task-20260801-162733
```

The trainer is started under `setsid`, owned by nothing, and everything after
that is polling files — `progress.json`, which the trainer rewrites
atomically every iteration. Nothing parses its stderr.

**`watch`** prints one line per change (state, iterations, reward, **mean
episode length**, best-so-far and where it happened, elapsed, ETA,
checkpoints), rsyncs new
`.cxpolicy` files back as they land, and writes **`training-progress.json`**
into the destination. Point that destination at your `.cadex` project
directory and the shell's **Training panel** picks it up — no ssh in the
shell, no protocol change, no engine change. It exits `0` when the run
finishes and `1` when it reports `failed`, with the reason.

**`stop`** sends `TERM` and then *verifies* the process went. Whatever the
run had already written is still on the box; `pull` brings it home.

Do not pipe any of these through `tail`: a pipeline reports the last
command's status, which hides a failed dispatch, and it buffers the output
until the process exits (ADR-093 §4).

### Choosing among the checkpoints

They are all real policies. `compare.py` in the project directory plays each
one locally — stock MuJoCo, no GPU, seconds — and prints survival, episode
length, final tilt, drift and peak/mean torque per motor as one table. That
is the comparison; watching two *animate* at once is not available and should
not be faked (ADR-077: exactly one simulation per script).

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
