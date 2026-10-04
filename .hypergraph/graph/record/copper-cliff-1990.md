---
node_id: 8ab9160d-39ce-5007-8498-3bcb19d3fee4
slug: copper-cliff-1990
title: 'orun2 A1/W1: a turn reports its tokens and cost and names a tool call written as text (ADR-523)'
created_at: '2026-10-04T04:15:06+00:00'
parents:
- winter-hill-2339
summary: ''
---
## What
The parity ledger's `agent.py` row is fully ported (ADR-523). Each `cadex -p` turn now reports what it cost, and it names a tool call the model wrote as text.
- `cli/cadex_cli/agent.py` gains two re-derived pure functions:
  - `turn_usage(frames)` sums tokens in (including cache writes), cached and out, plus `cost_usd` and `duration_ms`, over every `result` frame the claude CLI sends. A nudged turn has two.
  - `imitated_tool_call(frames)` finds `<invoke name=` or `<function_calls>` in the model's text blocks.
- `cadex -p` puts `usage` in the envelope and writes a ` · turn:` line to stderr. The imitated case writes a ` ✗ ` line and becomes the last note. The turn is not refused for it.
- The dashboard's turn reply passes `usage` through. `#turn-status` adds the token count and price.
- `cost_usd` is null when nothing priced the turn. `usage` is absent when no frame reported any usage.

## Why
The critic's message had two parts.
- **Fix first.** Write iteration 47's missing record. Done as `winter-hill-2339`, with both suites re-run on `63bcead7`.
- **Next unit.** Take the next of W1's remaining "to port" rows. Two were left: `agent.py` (A1) and `cadex_dimension.py`'s viewer overlay (D2.5). I took `agent.py` because it is listed first and serves A1 as well as W1.

## Method
- I read the shell's `agent.py` from `v1-blender-shell` as reference only: its imitated-call note and its result-frame usage reader. I wrote the code fresh against the CLI's own `TurnResult` frames and copied nothing.
- I edited in a detached worktree so the suite runs for the record could finish on the committed tree.
- Test doubles: `mock_backend.MockTurn` now emits assistant text frames. Its `done` step, and `fake_claude.py`'s, accept extra result-frame fields.
- New `cli/tests/test_turn_usage.py`:
  - summing over result frames;
  - an unpriced turn is not a free one;
  - markup detection, where a `tool_use` block and result prose do not count;
  - against a real engine, the envelope and stderr of a priced turn and of a turn that wrote its call as text, which exits 3 with the warning.
- `test_dashboard_writes.py::test_browser_starts_a_turn_and_watches_it_land` uses a real `cadex -p` child, the fake `claude` and headless Chromium. Its fake turn now reports a priced result. The test asserts `reply.usage`, "21,500 tokens, $0.42" on the turn status, and the ` · turn:` transcript line.
- Docs: `docs/CLI.md` (prompt flags, `usage`), `docs/DASHBOARD.md` (turn reply and status), and the `docs/SHELL-PARITY.md` row and counts, with ADR-523.

## Result
True now: the `agent.py` row is ported. One row still says "to port": `cadex_dimension.py`'s in-viewer measurement overlay (D2.5). After it, only the two face-pin rows marked "owner to confirm" remain.

Evidence on `2f40027d`'s tree:
- `pixi run test-engine`: 2607 passed, 56 skipped. No engine code changed.
- `pixi run python -m pytest cli/tests` with the GPU hidden: 1408 passed, 1 skipped, 1 failed (21 min). The failure was `test_dashboard_inspect.py::test_browser_plays_a_real_rollout_with_the_trace_s_placements`: `#play-toggle` was still disabled right after the playback's `times_s` arrived. That run overlapped with an engine suite run. The test passed twice when re-run alone (20 s each), and it passed in the parent tree's full run.
- I read it as a timing flake under load, not a defect from this change, which does not touch playback. The next iteration should make that assertion wait for the toggle, not read it once.
- Before the change was applied in the repo, the worktree run gave 1387 passed and 23 skipped. Those skips were all FFmpeg or private-host tests, because that run was outside `pixi run`.

Not ported: a running session total of cost. Turns are listed from `PROGRESS.md` (ADR-519), which has no cost column. The provider switch went with Codex and pi (ADR-497); `--model` is the model switch.

No new dependency. No protocol or tool-surface change, so no packaged gate is needed. The tail now has three unreconciled records: autumn-rose-7173, winter-hill-2339 and this one. That meets the reconcile trigger.

Next: the `cadex_dimension.py` viewer overlay. Then, with no row left to port, R1's AGENTS.md cut.

Dispatch closed: 1 unit — agent.py ledger row ported: per-turn tokens/cost and the text-tool-call warning in CLI envelope, transcript and dashboard (ADR-523)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 2f40027d3c0a695f726fe220d416f4675a4fead4

## State Impact

- target: shady-clover-5534 — agent.py parity row ported (ADR-523, cli/tests/test_turn_usage.py, test_dashboard_writes.py::test_browser_starts_a_turn_and_watches_it_land); one row still to port: cadex_dimension.py viewer overlay (D2.5); test_browser_plays_a_real_rollout_with_the_trace_s_placements flaked once under load (passes alone)
