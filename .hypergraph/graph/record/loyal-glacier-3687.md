---
node_id: 13cc7adb-4d2c-5b50-b533-7487bc95eefd
slug: loyal-glacier-3687
title: 'ADR-577: the checkpoint rule says what a checkpoint does and what it costs'
created_at: '2026-10-06T22:55:54+00:00'
parents:
- cool-mountain-0850
summary: ''
---
## What
ADR-577 (commit `78d6e183`): the base guidance's TRAIN SO A GOOD POLICY CAN BE KEPT paragraph (`cli/cadex_cli/guidance.py`) now states `checkpoint_every` as a trade — what it does (a complete witness-checked policy every N iterations plus the best so far; a stopped run still leaves one; a local run plays each checkpoint in the viewport on the CPU) and what it costs since ADR-576 (one witness-rollout compile at the first checkpoint, tens of seconds on a large task, then about one training iteration each, plus one file; every 10–25 iterations adds a tenth of the run's time or less), so it is left off only for a throwaway run. It no longer says "on every run".

## Why
The critic's named next unit: the last orun3 defect on the long-term rung (the guidance told the agent to set `checkpoint_every` whenever the owner was watching). Finding: that "watching" wording was already gone from `guidance.py` and `CadexAgentGuidance.md` (`git log -S watching` finds nothing; `CadexAgentGuidance.md` never mentioned checkpoints); ADR-565 had reworded it to "Set checkpoint_every on every run", still a ritual with no cost. So the unit restated that sentence as the critic asked. The tool description in `tools.py` already says what it does and was left alone (tool surface contract).

## Method
Costs taken from ADR-576's measurement (42.5 s first compile; 1.9 s per later checkpoint vs a 1.9 s iteration), phrased without the reference task's numbers. New test `test_agent_guidance.py::test_the_checkpoint_rule_says_what_it_does_and_what_it_costs` pins both halves and the absence of "on every run" and "watching"; the ADR-565 test's anchor moved to "Set checkpoint_every on any run". With the old `guidance.py` restored both tests fail (2 failed, 12 passed); with the new one 14 passed.

## Result
Gates, foreground, GPU hidden: CLI thirds 395 passed (2:29), 324 passed 1 skipped (5:40), 490 passed (3:50) — whole CLI suite ~12 min; `pixi run test-engine` 2611 passed, 59 skipped (5:44). No tool, default, protocol op or trainer behaviour changed; `checkpoint_every` still defaults to 0. No new dependency.
Next, per the critic: add ADR-574 to ADR-577 to `docs/probes/orun4/REPORT.md`, then a reconcile pass (one unreconciled record now), then claim done again.

Dispatch closed: 1 unit — ADR-577, the checkpoint rule states what a checkpoint does and costs

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: 78d6e1830176b57e76478609cb8f43e3a065a32a

## State Impact

- target: late-pond-2851 — the base guidance states checkpoint_every as a trade, what it does and its ADR-576 cost (one compile, then ~one iteration each), not 'on every run' (ADR-577, commit 78d6e183)
