# ot9 — the balance experiment contract

Verified against source: 2026-09-22. [Cadex-new]

**This is B1**: the frozen baseline, evaluation seeds, bar and run accounting
every ot9 training and evaluation run is measured against, written before any
of them. The machine-readable copy is [`contract.json`](contract.json), and
`cli/tests/test_ot9_contract.py` holds this page and that file equal. A
changed seed, bar value or baseline pin is a new experiment, not a revision of
this one. The closing report will be `REPORT.md`, written last.

ot8 ended with Robin **control-blocked** (`docs/probes/ot8/REPORT.md`, G4):
fit, swept fit and exact-BREP smoke geometry all pass, and the zero-command
hold falls — `fallen` at 0.660 s, 102.2° of chassis tilt — because a
two-wheeled inverted pendulum with an 11.59 /s unstable eigenvalue needs
feedback. ot9 supplies that feedback as a trained policy, and nothing else
may stand in for it.

## The baseline

Every value below was read from the project's own artifacts, read-only, on
2026-09-22: `script.py` hashed, `script.json` read, and the accepted attempt's
`result.json` and `outputs/` hashed from a copy outside the project.

| field | value |
|---|---|
| project | `ot8-robin` — an independent mechanical copy of `ot7-robin-c` (`docs/probes/ot8/baselines.json`); ot8 dispatched no product turn on it and accepted nothing |
| script | `script.py`, sha256 `f805fdc2bd886b5da8b01f3051bd2668497a2e53c8d7f9fba392ed2c3c9d30e8` |
| accepted revision | `0b4385616eb1610b5e8aeaec2dff56f2c073e6c1451b8975b4d9e08236975b3b` (= working revision) |
| accepted attempt | `1789860047622-6f21a6af7553` |
| accepted digest | `b933d905ae51ef908af6bcb6fe677b1713b4b8e75e532410f138fd7f58d5638c` — recomputed from the attempt's outputs with `CadexGeometryDigest.project_digest`, and it reproduces |
| geometry digest | `34898ebcf359f1403070b9bf13a4c0b702bc0b7cf4bf82a5ba2e657664d918bb` — `staged_geometry_digest` of the accepted attempt under `FreeCADCmd`, identical in two processes |
| MJCF | `robin_model` → `outputs/robin_model-model.xml`, sha256 `933b1ac6288d61904d8b7245076b96a5e02f13f7e0538ba0b5f49a322b869614`, MuJoCo 3.10.0 |
| task | `balance_task` → `outputs/balance_task-task.json`, sha256 `1f8c1040d6668a4f86a0cabb5d41d40a2c03bb5b1830d50d10c731d590269246` |
| project git head | `b75dd2d5d66e417b3544be67f31603f9fe420545` |

`script.json`'s learned `accepted_geometry` block names geometry digest
`4c75ff53…` keyed on accepted digest `0a6fe0f5…`, which is not this project's
accepted digest. It is stale — the same non-blocking observation ot8 made of
Plover — and it is **not** the pin; the pin is the recomputed value above.

The task the policy must satisfy, as the accepted bundle declares it: two
wheel motors, ±92.18251 N·mm each; a 0.002 s solver step, ten per action, so
**50 Hz** control; **400 steps = 8.0 s**; reset from the solved keyframe with
chassis tilt drawn in [0°, 3°] and height in [3, 5] mm; one termination,
`fallen` when `chassis_pos_z` < 75.25 mm; reward `alive` (+1), `pitch_penalty`
(−3 × |asin(qy)|) and `control_cost` (−2e-6 × Σ torque²).

## The bar

A candidate policy passes **only if every one of the ten evaluation seeds**
does all of the following, on the accepted policy, model and task:

- runs the full **8.0 s** — **400 steps at 50 Hz** — and ends by truncation;
- never fires **`fallen`**;
- keeps `comp_chassis` within **30°** of its attitude in the accepted solved
  pose (before reset variation) at every sampled step, the same reference
  `cadex smoke`'s support check uses (ADR-377).

One failed seed fails the candidate; results are never averaged, and a
candidate's result is reported on all ten seeds, not only the ones it passed.
Reward is never a pass. Neither is the zero-torque `cadex smoke` hold, which
cannot pass on this mechanism by construction.

What may not be used to pass it: an actor edit to the design, a grounded
base, an added stabiliser or support, a hidden or suppressed joint, a shorter
episode, a lower control rate, or a looser tilt or `fallen` threshold.
Mechanics, task and reward change only through a product-agent turn
(`claude-opus-5-5`, no fallback) on an `ot9-*` project, with a before/after
measurement. A task change that moves the bar's own quantities is refused by
this contract, whatever its reason.

## The evaluation seeds

**0, 1, 2, 3, 4, 5, 6, 7, 8, 9.** These are exactly the ten values the
baseline script's own `rollout_seed` parameter admits (`num(0.0, min=0.0,
max=9.0, step=1.0)`), so every evaluation episode is the design's declared
`assembly.rollout(pol, seed=int(p.rollout_seed))`, run by the engine's
`CadexDynamics.rollout_policy` from the accepted model, task and stored
policy, with reset draws from `random.Random(seed)` as the bundle's
`variation_algorithm` states.

They were fixed before any training and before any seed's reset draw was
computed. They are never re-chosen, extended or subset, and they stay the
same across every design, task and policy revision — including one that
changes that parameter's range.

Training cannot see them: the trainer draws its per-episode resets from
`jax.random` keys split on device (`training/cadex_train.py`,
`RESET_VARIATION_ALGORITHM`), not from the host `random.Random(seed)` stream,
and this task declares no `randomisation`. Trainer `--seed` values and any
tuning evaluation are recorded separately from these ten.

## Commands

`$PROJECTS` is the operator's external project directory. Every ot9 project
is a new `ot9-*` copy prepared mechanically, the way ot8 prepared its seeds:
every file of the baseline except `evidence/`, `agent.json` and
`.cadex-cli.lock`, then checked against the pin above before anything runs.

```bash
mkdir "$PROJECTS/ot9-robin" && (cd "$PROJECTS/ot8-robin" && tar cf - \
  --exclude=./evidence --exclude=./agent.json --exclude=./.cadex-cli.lock .) \
  | tar xf - -C "$PROJECTS/ot9-robin"
```

**Training** — one offboard PPO run, on the accepted task, with its settings
and stop rule recorded in the record *before* it starts. `--put` stores the
policy and reports its sha256; the run directory keeps the receipt, the
training curve and the checkpoint.

```bash
./cadex train --project "$PROJECTS/ot9-robin" \
  --out "$PROJECTS/ot9-robin/runs/<run>" --put --name <run>.cxpolicy \
  --iterations <N> --envs <E> --seed <S> --label <run> --timeout <T> --json
```

**Installation** — the script already carries the iterate convention
(`policy_on` switch, one `assembly.policy(task, weights="robin.cxpolicy",
sha256="0…0")` with inline literals), so the policy is installed by the
walk's digest edit and nothing else: `cadex script` read, the two literals
rewritten to the stored name and sha256, `cadex script --set`, then
`cadex params --set policy_on=1`. The engine witness-verifies the policy
against the task digest at that rebuild, and the policy is accepted through
the ordinary script path.

**Evaluation** — one ordinary rebuild per seed, on the accepted policy
revision, each landing its own `PROGRESS.md` row and exported trace:

```bash
for S in 0 1 2 3 4 5 6 7 8 9; do
  ./cadex params --project "$PROJECTS/ot9-robin" --set rollout_seed=$S \
    --out "$PROJECTS/ot9-robin/eval/<candidate>/seed-$S" --json
done
```

Each seed's report carries: seed, steps, duration, termination, peak tilt and
the time it occurred, minimum chassis height, total reward, and the policy,
MJCF and task sha256 of the artifacts that ran. Peak tilt and minimum height
are read from the exported trace's `comp_chassis` poses at every control
step (one frame per control step, `assembly.rollout`'s default) and from the episode block's
`termination`. The reader is
[`runner/balance_eval.py`](runner/balance_eval.py), pinned by
`cli/tests/test_ot9_balance_eval.py` against traces whose answers are stated
before it runs. It takes the tilt reference from the model's `solved`
keyframe — never from the trace, whose first frame is the *reset* pose — and
it calls a trace **void** when the model it ran is not the model read or not
the pin. It reports every seed and a candidate verdict that is `pass` only
for all ten contract seeds, each passing:

```bash
pixi run python docs/probes/ot9/runner/balance_eval.py \
  --model "$PROJECTS/ot9-robin/bundle/robin_model-model.xml" \
  --expect-mjcf <pin> --expect-task <pin> \
  "$PROJECTS"/ot9-robin/eval/<candidate>/seed-*/assembly-simulation-trace.json
```

It also reads a `cadex smoke` trace (beside its `smoke.json`), which is how
the no-policy fall was re-measured on `ot9-robin`; a smoke trace never
passes, because it has no policy in it.

## Reproduced on `ot9-robin`

[`retained/r2-robin-no-policy.json`](retained/r2-robin-no-policy.json).
`ot9-robin` was prepared by the command above and every pin reproduced on the
copy: script, revisions, attempt, accepted digest (`project_digest`),
geometry digest (`staged_geometry_digest` under `FreeCADCmd`), MJCF and task.
An 8 s zero-torque `cadex smoke` read by the reader fires `fallen` at
**0.66 s** with the chassis at 66.7328 mm and reads **102.234°** at 1.0 s —
G4's values to 1e-9 — then peaks at 108.1° on the floor impact at 0.74 s and
lies at 102.2° to the end. `cadex export` rebuilt the accepted digest and
wrote the training bundle (`bundle/`) with the pinned MJCF and task.

## Run accounting

Every run is listed in the report with its receipt, whatever its class.
Nothing is deleted, and nothing in one class is reported as another.

| class | training run | evaluation run | counts toward the bar |
|---|---|---|---|
| **completed** | the trainer exited 0 and wrote a `.cxpolicy` with its receipt, whatever the reward | all ten seeds ran on pinned artifacts, whatever they measured | yes — a completed evaluation is a pass or a fail |
| **failed** | the trainer exited non-zero on its own, or produced a non-finite curve | — | a failed training run produces no candidate; it is still reported |
| **interrupted** | stopped at `--timeout`, killed, or its host lost before it wrote a policy | a seed that did not finish: engine crash, lock, wall-time bound | no; an interrupted evaluation reruns **all ten** seeds on the same artifacts |
| **void** | invalidated by a defect in this repository, or run against artifacts whose MJCF or task digest does not match the accepted pin | the same, or any seed run on a policy, model or task other than the accepted one | no; void evidence is kept and is never a design verdict |

A provider usage, session or credit limit on a product-agent turn is void,
as in ot8 (ADR-355); if `claude-opus-5-5` is unavailable, the receipt is kept
and the turn waits for capacity rather than falling back to another model.
