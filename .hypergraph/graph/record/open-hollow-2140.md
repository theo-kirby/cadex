---
node_id: b8248ce3-6f95-542a-89c7-f00bd56333a5
slug: open-hollow-2140
title: The first prompt walk on this machine fails at the train leg; the model default is fixed
created_at: '2026-09-08T12:59:44+00:00'
parents:
- humble-forest-6896
summary: ''
---
## What

Ran the documented headless lifecycle entry point — `cadex walk --prompt` —
end to end on this run's machine (the Linux GPU box) for the first time. It
failed, in two different places, and this unit fixes the first and bounds the
second.

**Leg 1, the model.** The design leg refused in 2.4 s: the walk's default
model, the constant `claude-fable-5`, is out of usage credits on this login.
Probing the four ids the harness names, `claude-sonnet-5`, `claude-opus-5`
and `claude-haiku-4-5-20251001` all answered `ok` on the *same* login; only
the default did not. The walk reported the refusal faithfully and could do
nothing about it, because nothing on the machine can name a different model.
Fixed as ADR-249: `--model` now defaults to `$CADEX_MODEL`, then
`DEFAULT_MODEL`, the way `--project` reads `$CADEX_PROJECT` and `--engine`
reads `$CADEX_ENGINE_ROOT`. Explicit `--model` still wins; the shell default
is unchanged.

**Leg 2, the dynamics layer.** Rerun on `--model claude-opus-5`, the design
leg exited 0 after 3,983.3 s and the walk failed at `train` (exit 3, 2.1 s):
*the accepted revision exports no training task*. Whole walk 1:06:25, 318,556
KiB peak RSS, exit 3. The design agent had built the rig — MG90S from the
catalog, printed base plate, retainer and swing arm, six M3 bolts and nuts,
10 components, 3 joints, one project commit, `docs/actuators.md`,
`docs/sensors.md` and `docs/rejected.md` written — and then gated the entire
training layer behind `policy_on=0`, because `assembly.mjcf` and
`assembly.dynamics` never return: four separate 300 s worker kills
(returncode -24, SIGXCPU), surfaced as `The isolated domain worker exited
without a result` and `XScript domain execution exceeded 300 seconds`. Not
fixed here; recorded in ROADMAP as the lifecycle frontier's next unit.

## Why

The charter's short rung says this run's first unit is to run the documented
headless lifecycle entry point end to end on this machine and record exactly
which leg still needs a person or a guess; a clean run closes the walk gap, a
failed run names the next unit. It advances **The walk exists and is tested
headlessly** (`crisp-reef-5607`) and serves mission item 2.

The criterion cannot be ticked. The walk has never completed on this machine:
this attempt exited 3 at the train leg, and the one leg the criterion names —
toy-scale local CPU training from a prompt-designed mechanism — was never
reached. What is still missing is a `assembly.mjcf` that returns for a rig of
this size.

Two decisions taken without a person, per the question policy. First, naming a
model that has credit rather than parking on the constant that does not: the
previous run spent three iterations waiting for credit to return, and
`--model` is a documented flag of the documented entry point, so choosing one
is the reversible option. Second, an environment variable rather than changing
`DEFAULT_MODEL`: the constant is deliberately the shell's answer to "what does
Cadex run", and an override a machine sets leaves that answer intact.

## Method

Prerequisites first: `build/release/bin/{FreeCADCmd,CadexGeometryWorker}`
present, `~/cadex-train-venv` carrying jax 0.7.2 and mujoco 3.10.0, `claude`
2.1.263 on PATH. `PYTHONPATH`, `CADEX_ENGINE_ROOT` and `CADEX_MODULE_DIR`
unset; `JAX_PLATFORMS=cpu`; `/usr/bin/time -v` around the whole tree.

Walk, into a durable project outside this repository so no generated artifact
enters the run branch:

```sh
JAX_PLATFORMS=cpu ./cadex walk --project <durable> --out <durable>/runs/baseline \
  --prompt <one-servo swing-arm rig> [--model claude-opus-5] \
  --trainer-python <training-venv>/bin/python \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

Model probe: `claude -p "reply with the single word ok" --model <id>` for each
of the four ids, one call each.

Then four controls against the design agent's own diagnosis, each a fresh
project on the dev-tree engine, timed:

1. grounded one-body `assembly.mjcf` with `assembly.collision("box")`, no
   joints — **0 s, accepted**;
2. the reference `linear-carriage` script (two bodies, one slider) with a box
   collision added — **0.55 s**; with `mesh` — **1 s**; with `hull` — **0 s**;
   with `plane` — refused correctly by MuJoCo (*plane only allowed in static
   bodies*);
3. the walk's own accepted `script.py` rebuilt geometry-only — **1 s**;
4. the same script at `params --set policy_on=1` — **exactly 300 s, exit 3,
   `The isolated domain worker exited without a result`.**

Read `cadex_domain_worker.py:_resource_limits` and
`CadexEngineSettings.py`: `RLIMIT_CPU` is set to `timeout_seconds`, default
`DEFAULT_SCRIPTED_TIMEOUT_SECONDS = 300.0`, and `RLIMIT_AS` to
`DEFAULT_SCRIPTED_MEMORY_LIMIT_MB = 6144` on non-darwin only.

Implementation: `MODEL_ENV`/`default_model()` in `cli/cadex_cli/agent.py`, the
two argparse defaults in `__main__.py`, `docs/CLI.md` §2, ADR-249 and two
ROADMAP entries.

## Result

**The walk does not complete on this machine.** Exit 3, 1:06:25, 318,556 KiB
peak RSS. Two legs needed a person: choosing a model, now fixed; and a
training layer the design agent could not publish, not fixed.

ADR-249 landed at `bc203d28`. `pixi run python -m pytest cli/tests` — **217
passed, no skips**. `test_analysis_search.py` (the engine-side `docs/CLI.md`
pin) — 19 passed. The new `test_the_machine_can_name_the_turn_model_once`
cannot import on the old source. No engine change, no protocol op, no
`shell/` diff; the diff is 113 lines over `cli/**` and `docs/**`.

**The design agent's narrower claim is false and this matters for the next
unit.** `docs/rejected.md` in the walked project asserts that a single
grounded box with one box collision exhausts the cap. It does not: that model
builds in under a second in a fresh project, as do the reference carriage's
box, mesh and hull variants. The swing rig's own script rebuilds geometry-only
in 1 s and then burns exactly 300 s of CPU at `policy_on=1`. So the fault is
in that rig's dynamics declarations, not in `assembly.mjcf` as such, and the
next unit is a bisect over them — the rig declares bodies with per-component
collisions, a servo actuator with real limits, observations, sensors, two
`assembly.disturbance` values with ranged newtons, azimuth and `at_seconds`,
and a reward list. Two secondary facts for whoever takes it: the cap is a
`RLIMIT_CPU` in CPU-seconds while the parent's timeout is the same number in
wall-clock seconds, so a threaded pass on a 32-core box reaches the former
first and dies by SIGXCPU as an opaque "exited without a result" rather than a
budget refusal; and script-level `print(..., flush=True)` is lost on that
kill, so instrumenting from inside the script does not locate the stall.

The unreconciled tail was 2 nodes at dispatch and is 3 now.

Dispatch closed: 1 unit — the first prompt walk on this machine fails at the train leg; the model leg is fixed as ADR-249 with the CLI suite green, and the `assembly.mjcf` stall is reproduced, bounded and left as the named next unit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: bc203d2814ec48bfdaf8893c308c44a6b8d4567e

## State Impact

- target: crisp-reef-5607 — First prompt walk on the Linux GPU box exits 3 at the train leg after 1:06:25: the design leg's default model was out of credit (fixed, ADR-249, $CADEX_MODEL) and the accepted design gates its whole training layer off because assembly.mjcf burns the 300 s worker CPU cap; the criterion stays open on this machine
- target: salty-isle-4063 — assembly.mjcf never returns for a ten-component catalog rig on the dev-tree engine (SIGXCPU at the 300 s cap), while a grounded one-body model with a box collision and the reference carriage's box/mesh/hull variants build in under 1 s; the fault is in that rig's dynamics declarations, not in the export
- target: chilly-union-8972 — ADR-249: --model defaults to $CADEX_MODEL then DEFAULT_MODEL, so a machine whose default model has no credit can run the walk without a person on every command; CLI suite 217 passed, no skips
