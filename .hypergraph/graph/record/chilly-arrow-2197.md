---
node_id: 32c64865-369d-53b4-968d-084c81792297
slug: chilly-arrow-2197
title: 'ot11 P4: the product agent runs the training loop through four bridge tools and a detached, pre-registered supervisor; cadex walk stays as one use (ADR-464)'
created_at: '2026-09-30T16:39:20+00:00'
parents:
- rich-lantern-3026
summary: ''
---
## What

ot11 P4, the architecture and the loop itself (ADR-464). The product agent
can now run the whole training loop through the ordinary product path, and
it is one loop for every behaviour:

- **Four bridge tools**, beside `look`, with no protocol op behind them:
  `train_start`, `train_status`, `train_stop`, `evaluate`
  (`cli/cadex_cli/tools.py`, `bridge.py`). They are in the turn's
  `--allowedTools` (`agent.py`), which until now listed only the op-named
  tools.
- **A run registry and a detached supervisor**, `cli/cadex_cli/loop.py`
  (new, standard library only). `runs/<run>/registration.json` is written
  before anything is launched. The supervisor is `python -m cadex_cli.loop
  RUN_DIR` in its own session and outlives the turn.
- **An agent view of an evaluation**, `evaluate.agent_view`: the summary
  whole, one short row per seed, and the filmstrips returned as pictures.
- **The prompt**: "you cannot train" is replaced by one paragraph giving
  the loop (design, train, evaluate, revise from the evaluation).
- **`cadex walk` stays as one use, not retired.** Its review now carries
  `behaviour`: a task with a success spec is judged by the spec through
  `cadex evaluate`, and the gait reading (ADR-409) is advisory.
- Docs: `docs/CLI.md` (new section, module map, prompt bullet, suite
  table), `docs/DECISIONS.md` ADR-464, one corrected line in
  `docs/MUJOCO.md`.

## Why

P4 is the highest open criterion; the critic accepted P1 to P3 and named
this unit: choose the loop architecture, record it in an ADR, and build it
in the same unit. It targets frontier node `wild-harvest-4848`.

**Deviation from the critic's message, stated plainly.** The critic asked
me to fold `rich-lantern-3026` into state and regenerate the views inside
this iteration. I did not. This iteration's own standing instructions
forbid the reconcile skill, `hypergraph update`, state-node edits and
STATE.md edits in a work iteration "with no exceptions", and say a fat tail
is to be reported, not folded. The two instructions conflict and the
no-exceptions one is the loop's own contract, so I followed it. The tail is
now two records (`rich-lantern-3026` and this one); the frontier still
shows P1, P2 and P3 as open although the critic accepted them as met. A
reconcile pass should fold both.

## Method

Read the existing legs first: `cadex train` (dispatcher), the trainer's
`progress.json` and checkpoints, `cadex evaluate` and its film, the bridge
and how `look` is answered, and `cadex walk`.

Choices, each the smaller reversible one:

- Bridge tools over a protocol op: training is offboard (ADR-084) and
  cadexd dispatches serially; nothing in the engine, `OP_ARG_SPECS`, the
  payload or `shell/` moved, so no packaged gate was due.
- A detached supervisor over a blocking tool: ot10's hexapod-9 died with
  the session that started it.
- The bundle is copied from the accepted attempt the store retained, by
  digest, never rebuilt (the same read `cadex evaluate` makes), so the run
  needs no engine and holds no project lock.
- Liveness by advisory lock, not pid: a status saying `running` under a
  lock nobody holds is read as `interrupted`, not an attempt. A second,
  machine-wide lock is the one training slot. Stop is a file the supervisor
  polls; no process is signalled by pid.
- Registration enforces the charter: a budget on every run (0 < budget <=
  6 h), `--stop-on-collapse` always, one run at a time, a training seed
  that is not an evaluation seed, no ungrounded policy channel, and a
  reason long enough to name a measurement.
- `loop-ledger.jsonl` in the project records each registration (with its
  reason), stop, ending and evaluation, and is handed to a new turn by
  `train_status` with no run.
- `cadex walk` kept: retiring it would break five runs' receipts and tests
  for a command the loop does not depend on.

Tests: `cli/tests/test_loop.py` (new). Fake trainer with a really detached
supervisor for the registry; `Bridge.call` for the tools; `command_prompt`
with a scripted model over the real bridge socket and a live engine for
whole rounds, one with an engine-suite policy fixture as the trainer and
one with the real trainer on CPU from the training venv.

## Result

**True now.**

- A scripted turn against a live engine accepts a task with a success
  spec and calls `train_start`; the turn ends; the run finishes under its
  supervisor. The next turn reads it with `train_status`, stores the policy
  with `put_asset`, declares it, and calls `evaluate`. The reply is the
  spec's verdict (fail, `still` 0 of 2, `completes` and `upright` 2 of 2),
  per-seed rows with metrics and endings, the reward by term, and two PNG
  filmstrips of seed 1101, in under 21,500 characters. The ledger reads
  `train_registered`, `train_ended`, `evaluated`.
- The same round with the real trainer (training venv, CPU, 2 iterations,
  4 envs, `checkpoint_every` 1) ends `finished` with a `best` checkpoint,
  and the live engine verifies the policy by the digest the supervisor
  reported.
- With the fake trainer: registration is whole before launch; ten refusals
  leave nothing behind; a run launched from a process that exits at once
  still finishes; stop, budget (1 s), collapse and crash each end in their
  own state; SIGTERM and SIGKILL of the supervisor both read as
  `interrupted` and free the slot; a second run is refused per project and
  per machine.
- `test_loop.py` refuses behaviour words (walk, gait, foot, leg, reach,
  balance, shove and others) in `loop.py`, in the four tool definitions and
  in the prompt paragraph past its one "nothing in it knows which"
  sentence.

**Suites at this revision.** `pixi run python -m pytest cli/tests`: 1246 passed, 1 skipped
(1219 and 1 before; the 27 new tests are `test_loop.py`, none skipped on
this machine). `pixi run test-engine`: 2507 passed, 57 skipped, unchanged.
No packaged lifecycle gate was run and none was due: no engine, protocol or
payload file changed. The CLI suite takes about 18 minutes here, not the 4
`.ouroboros/AGENTS.md` states.

**Not shown, and not claimed.**

- No real model has run the loop. P4's transcript requirement (three or
  more rounds of design, train, evaluate, revise on one behaviour, each
  revision motivated by a measurement) is **not met** and is the next unit.
  P4 stays open.
- No run longer than two iterations has been supervised, and none on the
  GPU.
- How long the harness lets one MCP tool call block is unmeasured.
  `train_status` caps `wait_s` at 900 s; `evaluate` blocks for the rollouts
  and the film (about a minute for ten seeds of Robin by the P2 receipts,
  film extra).
- The review dashboard lists loop runs through `run.json` (mode `loop`)
  and reads their `train/progress.json`; I did not open the page to look.

**Assumptions and limits for the next iteration.**

- The loop trains on this machine only. Remote dispatch is still
  `cadex train --remote`. The shell's agent has no loop tools.
- The machine lock defaults to `~/.cache/cadex/training.lock`
  (`$CADEX_TRAIN_LOCK` overrides). It guards loop runs only: a hand-run
  `cadex train` or `cadex walk` does not take it.
- The 6 h budget ceiling and the 12-character minimum reason are my
  numbers, not the charter's.
- Evaluation and training seeds live in different random streams; the
  equal-value refusal is the literal reading of the charter's rule.
- The critic said not to start R3 training yet; nothing was trained on any
  ot11 project. The only training was the two-iteration toy in the suite.
- No new dependency.
- The unreconciled tail is two records; see Why.

Dispatch closed: 1 unit — ADR-464: four bridge tools and a detached, pre-registered training supervisor give the product agent one behaviour-agnostic design/train/evaluate/revise loop; `cadex walk` kept as one use; P4's real-model rounds remain open.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 1348a0b31f2ec9a5847fd3560f24d105556ee53e

## State Impact

- target: wild-harvest-4848 — The loop exists and its architecture is recorded (ADR-464, commit 1348a0b3): train_start, train_status, train_stop and evaluate on the CLI bridge, a pre-registered run under a detached supervisor that outlives the turn, a project ledger, and no behaviour named anywhere in it; cadex walk is kept as one use. Proven with a scripted model against a live engine and with the real trainer on CPU. Still open: no real model has run it, so the three-round transcript requirement is unmet.
- target: chilly-union-8972 — The CLI's agent can train and evaluate (ADR-464): four bridge-answered tools beside look, all listed in --allowedTools; cli/cadex_cli/loop.py is the run registry and supervisor (runs/<run>/registration.json, training-status.json, loop-ledger.jsonl); the prompt no longer says the agent cannot train. cli/tests 1246 passed, 1 skipped.
- target: calm-peak-5247 — cadex walk is kept as one scripted single pass and is not the loop (ADR-464); its review.json carries behaviour: a task with a success spec is judged by the spec through cadex evaluate and the gait reading is advisory.
