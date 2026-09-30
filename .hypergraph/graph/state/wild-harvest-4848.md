---
node_id: 2fd26bda-3024-5527-9ba3-9a6aaa3e2b9f
slug: wild-harvest-4848
title: P4. The product agent runs the loop, and it is the same loop for every behaviour
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot11: **P4. The product agent runs the loop, and it is the same loop for every behaviour.** - Through the ordinary product path, the agent can: - author or revise a task, its reward and its spec; - start bounded training; - read the progress, the evaluation report and the filmstrip; - decide the next revision. - This run chooses the architecture and records it in an ADR. Whatever it is, the loop takes no walking-specific branch. `cadex walk` becomes one use of it, or is retired in its favour, and the ADR says which. - The transcripts must show, for at least one behaviour, three or more rounds of design, train, evaluate and revise. Each revision must be motivated by a measurement from the previous evaluation, and the next evaluation must show whether it helped. [rec: kind-spire-3578]

Declared target: `gap-p4-product-agent-runs-loop`. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

**Every measured part of P4 now has evidence; the owner ticks it.** Status flipped to working on the reconciler's judgement: the architecture is recorded (ADR-464) [rec: chilly-arrow-2197], the loop has run on two behaviours through one path [rec: southern-quartz-3293] [rec: silver-harvest-8970], and reach supplied the three motivated rounds [rec: silver-harvest-8970]. The warm-start defect below is open and does not undo that.

- **Architecture.** Four bridge-answered tools beside `look` — `train_start`, `train_status`, `train_stop`, `evaluate` — with no protocol op behind them, all in `--allowedTools`. `cli/cadex_cli/loop.py` (standard library only) is the run registry and a detached supervisor that outlives the turn. `runs/<run>/registration.json` is written before launch; `loop-ledger.jsonl` records registrations (with reason), stops, endings and evaluations. The bundle is copied from the retained accepted attempt by digest, so a run needs no engine and holds no project lock. One machine-wide training slot guards loop runs. Registration requires a budget (0 < b ≤ 6 h), `--stop-on-collapse`, one run at a time, a training seed that is not an evaluation seed, no ungrounded policy channel, and a reason of at least 12 characters [rec: chilly-arrow-2197].
- **No behaviour is named in it**: `test_loop.py` refuses behaviour words in `loop.py`, the four tool definitions and the prompt paragraph. **`cadex walk` is kept as one scripted single pass, not the loop** (detail on `calm-peak-5247`) [rec: chilly-arrow-2197]. The session driver `docs/probes/ot11/runner/rounds.py` names no behaviour and ran reach unchanged; `runner/goals.py` likewise [rec: silver-harvest-8970].
- **Balance (one round).** On `ot11-robin-1` the agent designed the task, wrote the frozen spec, registered `bal-1`, evaluated its iteration-400 checkpoint: 10 of 10 seeds pass (detail on `staid-tooth-3475`). It closed in one round, so it could not supply the three rounds [rec: southern-quartz-3293] [rec: even-otter-4624].
- **Reach (four motivated rounds).** On `ot11-heron-1`, one pre-registered session: rounds r2–r4 each cite the prior evaluation's failing predicate, value and limit. r2 helped (0 → 1 of 10 seeds), r3 did not (1 → 0), r4 helped (0 → 9 of 10). Detail on `sunny-garden-4245` [rec: silver-harvest-8970].
- **Ledger defect fixed** (commit `4b4b03e8`): `trained_by_run` now names a run for its final policy, any digest its progress named, or any checkpoint file on disk (bal-1's evaluated 000400 checkpoint had been written after the last `progress.json` rewrite); `train_status` lists checkpoints from the files with their own digests. Regression test fails on the old code; `cli/tests` 1252 passed, 1 skipped [rec: soft-otter-1938].
- **A tool call may block at least 900 s** under Claude Code 2.1.285, which `train_status`'s `wait_s` ceiling fits [rec: southern-quartz-3293].

**Open**:

- **Defect: warm start is unreachable.** `train_status` (`loop.run_view`) never names a run's task bundle, so `init_from_parent_task` cannot be used; on reach the agent guessed five paths [rec: silver-harvest-8970].
- Training is local only (remote is still `cadex train --remote`); the shell's agent has no loop tools; the review dashboard's listing of loop runs was not looked at [rec: chilly-arrow-2197].

## Negative knowledge

None yet.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- chilly-arrow-2197 — the loop's architecture (ADR-464): four bridge tools, a pre-registered detached supervisor, a ledger; proven with a scripted model
- southern-quartz-3293 — first real-model round on a copy of Robin: one run, 10 of 10 seeds pass; a tool call may block 900 s; ledger defect
- soft-otter-1938 — ledger defect fixed: checkpoints on disk link to their run
- even-otter-4624 — balance closed in one round, so the three rounds must come from another behaviour
- silver-harvest-8970 — reach: four motivated rounds, 0 → 1 → 0 → 9 of 10; warm start unreachable through train_status
