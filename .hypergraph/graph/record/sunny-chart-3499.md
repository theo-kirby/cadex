---
node_id: 8a16add9-a1cc-57f4-a5c6-5056b7ee3a63
slug: sunny-chart-3499
title: 'Record for d516011c (ADR-356): interrupted calls return their slot, streams captured as they arrive, every turn effort-pinned and output-capped; full CLI suite green'
created_at: '2026-09-15T10:31:40+00:00'
parents:
- rare-birch-0755
summary: ''
---
## What

The causal record for commit `d516011c` (iteration 46, ADR-356), which landed without one. That commit carried decision #44 into the F4–F7 evidence collector and bounded every product-agent turn per message, in three parts:

1. `docs/probes/ot7/runner/run.py`: a turn whose child exited `timeout` or `launch_failed`, and that is not void, is **interrupted**. Its slot is returned, `continuations_used` stays at the count before the call, the receipt counts it in `interrupted_calls` apart from `void_calls` and `slots_spent`, the measurement is still read and hashed, no smoke runs, and `retry` names the next letter-suffixed project. A provider error the call returned on its own is `failed` and keeps its slot. `--classify` reports interruptions from the sibling `attempt.json`.
2. `CapturedTurn` appends each provider frame to `transcript.jsonl` as it arrives, so a kill at the runner's bound loses nothing received; a stale-session retry appends after the first attempt.
3. `cli/cadex_cli/agent.py`: `ClaudeTurn` launches every turn with `--effort` (`$CADEX_EFFORT`, default `high`, the harness's own default) and passes `CLAUDE_CODE_MAX_OUTPUT_TOKENS` (`$CADEX_MAX_OUTPUT_TOKENS`, default 32,000) in the child's environment, the harness's documented per-message cap on thinking and text together. A bad value in either variable refuses the turn with a `ValueError` naming it.

Docs written forward in the same commit: `docs/CLI.md` §2, the runner README, `docs/probes/ot7/REPORT.md` (table row and an iteration 46 section), `docs/probes/ot7/retained/README.md`, and a `ruling` field added to `retained/repair-timeout-b.json` carrying decision #44 while its historical `slot_consumed: true`, `slots_spent: 1` and `continuations_used: 1` stay as the collector of that day wrote them. No frozen prompt changed and no design was edited.

## Why

The critic's fix-first for iterations 46 and 47: iteration 46 committed this work with the message "no record" and left its full CLI suite unverified, and iteration 47 changed nothing. Under the Hypergraph protocol unrecorded work is invisible, and the charter's quality bar says CLI changes run the CLI suite. This record supplies the missing evidence and the missing causal node; it is bookkeeping for a landed commit, not this iteration's unit, which follows in its own record. Advances F4 (`polished-forest-0215`): the two collector defects that iteration 44 named as blocking any further design turn are fixed, so the F4 retry can be dispatched.

## Method

1. Read the commit's diff (ten files, +511/−81) against ADR-356 and the critic's verdicts for iterations 46 and 47.
2. Ran the full CLI suite in this iteration: `pixi run python -m pytest cli/tests -q -p no:cacheprovider`. Result: **738 passed, 1 skipped in 526.81 s** (the skip is the engine-needing case that skips without a built engine); exit 0. Log kept at the operator's `/tmp/cli-tests-48.log`, not committed.
3. The engine suite did not run: the commit touches nothing under `src/Mod/cadex/`, no protocol op, and no payload, so no engine build or packaged gate applies.
4. Field confirmation of part 2, from this iteration's own dispatch on `ot7-heron-repair-c` (recorded separately): a call cut off by the provider after 79.9 s left a 216,946-byte `transcript.jsonl` with every frame it had received, where the iteration 44 kill had left none.

## Result

**What is true now.**

- Runner-bound kills and never-launched children are `interrupted` and spend no slot; provider errors the call returned on its own are `failed` and do; usage limits are `void` (ADR-355). `run.py --classify` reports all three.
- The provider stream is captured frame by frame; a kill keeps what arrived.
- Every CLI product-agent turn runs at an explicit effort level with a 32,000-token per-message output cap. The 30-minute turn bound is unchanged.
- Fixtures in `cli/tests/test_ot7_runner.py` pin a kill on a create, on a continuation after two completed turns and on the repair, the mid-stream capture, and that a limit seen before a kill is void rather than interrupted; `cli/tests/test_commands.py` pins the effort pin, the cap, their overrides and their refusals.
- The iteration 44 receipt keeps its historical values with a `ruling` field; F4's repair prompt and all three continuations are unspent.

**Concerns and assumptions.**

1. The output cap bounds one message, not a turn: a model can still spend the 30 minutes across many 32,000-token thinking messages. Whether that happens is a design-turn measurement, not a tooling fact.
2. The runner still cannot see the provider window before dispatching; the operator's probe answers "available" even at 95 % utilization (see this iteration's `ot7-heron-repair-c` receipt). The first `rate_limit_event` frame of a turn carries the utilization and is now in the captured stream.

Dispatch closed: 1 unit — the missing record for d516011c (ADR-356): interrupted calls return their slot, streams are captured as they arrive, every turn is effort-pinned and output-capped; full CLI suite evidence attached.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: d516011ca2f246eb6bec18e3ccd0eeb9751d1825

## State Impact

- target: polished-forest-0215 — the two collector defects iteration 44 named are fixed (ADR-356): a runner-bound kill or never-launched child is interrupted and returns its slot, the provider stream is written frame by frame, and the CLI bounds every turn per message (effort high, 32,000-token output cap); the iteration 44 receipt keeps its historical slot values with a ruling field; F4's repair prompt and all three continuations are unspent and the retry may be dispatched
- target: chilly-union-8972 — ClaudeTurn launches every product-agent turn with --effort ($CADEX_EFFORT, default high) and passes CLAUDE_CODE_MAX_OUTPUT_TOKENS ($CADEX_MAX_OUTPUT_TOKENS, default 32,000) in the child's environment; bad values refuse the turn with a ValueError; docs/CLI.md §2 documents both; full CLI suite 738 passed, 1 skipped
- target: mild-ledge-7157 — decision #44 is applied by the collector itself: void (usage limit), interrupted (runner kill or no launch) and failed (provider error returned on its own) are three distinct outcomes, only the last spends a slot; the pre-dispatch blocker on any further design turn is cleared
- target: first-snow-5587 — REPORT.md carries an iteration 46 section and the F4 row now reads zero attempts, one interrupted call apart from three void ones, retry ot7-heron-repair-c
