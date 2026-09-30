---
node_id: 2fd26bda-3024-5527-9ba3-9a6aaa3e2b9f
slug: wild-harvest-4848
title: P4. The product agent runs the loop, and it is the same loop for every behaviour
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **P4. The product agent runs the loop, and it is the same loop for every behaviour.** - Through the ordinary product path, the agent can: - author or revise a task, its reward and its spec; - start bounded training; - read the progress, the evaluation report and the filmstrip; - decide the next revision. - This run chooses the architecture and records it in an ADR. Whatever it is, the loop takes no walking-specific branch. `cadex walk` becomes one use of it, or is retired in its favour, and the ADR says which. - The transcripts must show, for at least one behaviour, three or more rounds of design, train, evaluate and revise. Each revision must be motivated by a measurement from the previous evaluation, and the next evaluation must show whether it helped. [rec: kind-spire-3578]

Declared target: `gap-p4-product-agent-runs-loop`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

**The loop exists and its architecture is recorded (ADR-464, commit `1348a0b3`) [rec: chilly-arrow-2197].** Still open: the three-round transcript requirement is unmet.

- **Architecture.** Four bridge-answered tools beside `look` — `train_start`, `train_status`, `train_stop`, `evaluate` — with no protocol op behind them, all in `--allowedTools`. `cli/cadex_cli/loop.py` (standard library only) is the run registry and a detached supervisor (`python -m cadex_cli.loop RUN_DIR`, own session) that outlives the turn. `runs/<run>/registration.json` is written before launch; `loop-ledger.jsonl` records registrations (with reason), stops, endings and evaluations, and `train_status` with no run hands it to a new turn. The bundle is copied from the retained accepted attempt by digest, so a run needs no engine and holds no project lock. Liveness is an advisory lock, not a pid; one machine-wide training slot (`~/.cache/cadex/training.lock`, `$CADEX_TRAIN_LOCK`) guards loop runs only. Registration requires a budget (0 < b ≤ 6 h), `--stop-on-collapse`, one run at a time, a training seed that is not an evaluation seed, no ungrounded policy channel, and a reason of at least 12 characters (the 6 h and 12 are the actor's numbers) [rec: chilly-arrow-2197].
- **No behaviour is named in it**: `test_loop.py` refuses behaviour words in `loop.py`, the four tool definitions and the prompt paragraph. **`cadex walk` is kept as one scripted single pass, not the loop**; a task with a success spec is judged by the spec (detail on `calm-peak-5247`) [rec: chilly-arrow-2197].
- **Proven with a scripted model** against a live engine (train, turn ends, next turn reads status, declares the policy, evaluates; reply under 21,500 characters with two filmstrips) and with the real trainer on CPU for two iterations. Stop, budget, collapse, crash, SIGTERM/SIGKILL of the supervisor and per-project and per-machine refusals are each tested. `cli/tests` 1246 passed, 1 skipped [rec: chilly-arrow-2197].
- **First real-model use (commit `0ffc6569`) [rec: southern-quartz-3293].** `claude-opus-5-5` on `ot11-robin-1` (a copy of `ot9-robin`, which is untouched) designed the task, wrote the frozen balance spec byte for byte, registered one run `bal-1` (650 it × 1024 envs, seed 7, 900 s budget, reason citing the baseline's B3/B4/B5), which ended `budget_exhausted` at iteration 400, then declared that checkpoint and evaluated it: pass on 10 of 10 seeds (detail on `staid-tooth-3475`). One 24.5-min turn, 28 tool calls, none failing, $2.80. Driven by `docs/probes/ot11/runner/rounds.py` (names no behaviour; frozen first and continuation prompts, digests in `retained/p4-robin-1-registration.json`; stops on a pass or four evaluated runs); receipt `retained/p4-robin-1-rounds.json`; `cli/tests` 1251 passed, 1 skipped [rec: southern-quartz-3293].
- **A tool call may block at least 900 s** under Claude Code 2.1.285 (`runner/block_probe.py`, 900.1 s, no error; receipts `retained/p4-block-probe-{900s,5s}.json`) — `train_status`'s `wait_s` ceiling fits [rec: southern-quartz-3293].

**Open**:

- **The three motivated rounds are unmet.** The first evaluation passed, so nothing was revised; the actor judged forcing rounds after a pass to be fishing. Reach (R2) is the proposed place for them [rec: southern-quartz-3293].
- **Defect:** the ledger's `evaluated.trained_by_run` matches only a run's final policy, so an evaluated checkpoint of a budget-exhausted run (`bal-1`) is left unlinked (`trained_by_run: []`). Proposed fix: also match checkpoint digests from `progress.json` in `bridge.py`'s `trained_by` [rec: southern-quartz-3293].
- Training is local only (remote is still `cadex train --remote`); the shell's agent has no loop tools; no loop run longer than two iterations was supervised under test, and the review dashboard's listing of loop runs (`run.json` mode `loop`) was not looked at [rec: chilly-arrow-2197].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- chilly-arrow-2197 — the loop's architecture (ADR-464): four bridge tools, a pre-registered detached supervisor, a ledger; proven with a scripted model
- southern-quartz-3293 — first real-model round on a copy of Robin: one run, 10 of 10 seeds pass; a tool call may block 900 s; ledger defect
