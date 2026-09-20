---
node_id: d4fa2d65-fc9d-5789-82cf-bcd9ca3dd52d
slug: mellow-summit-9733
title: 'F5: the arm create call on ot7-heron-b interrupted at the 30-minute bound — describe_api overflow, three probe scripts, three thinking-only messages at the 32,000-token cap, no design written, no slot spent, retry ot7-heron-c after a recorded effort decision'
created_at: '2026-09-15T22:03:22+00:00'
parents:
- damp-cedar-5823
summary: ''
---
## What

F5's first call that reached a model. The frozen `heron.create.prompt.txt` (9,648 bytes, digest unchanged) was dispatched on the fresh, empty project `ot7-heron-b` through `docs/probes/ot7/runner/run.py heron … --turns 1` at 21:28 UTC, with no actor edit to any design. The runner's ADR-358 probe read **13 %** of the five-hour window and dispatched.

- **The turn did not end on its own**: the runner killed it at **1,800.0 s** and classified it `interrupted` under ADR-356 (`slot_consumed: false`, `slots_spent: 0`, `continuations_used: 0`, retry `ot7-heron-c`). 68 model messages, 52 tool calls, the stream captured frame by frame (1,023,332 bytes, `28ea5aeb…`). No `submit`, no assembly, no design.
- **Where the thirty minutes went.** 21:28:02–21:31:53, reading: `describe_api` returned 163,200 characters, which the harness refused as over its tool-result cap and wrote to a file; the agent tried `Grep`, `Read`, `Bash` and `Agent` on that file, all four disabled in the product-agent session, then paged the contract through 44 `inspect scope=api` reads. 21:29:24–21:31:53, three `write_script` calls: one rejected (`import json`), two accepted as probes of the catalog servo body, a flange cut from it and the horn, three `part` outputs with no `assembly.component` (revision `544ea74e…`, twelve lines). 21:31:53–21:56:46, thinking: three consecutive thinking-only messages of about 31,950 estimated thinking tokens over 479, 494 and 472 s, each ending on the 32,000-token output cap ADR-356 set, each auto-resumed by the harness ("Output token limit hit. Resume directly…"), one read between the second and third; a fourth began at 21:56:46 and the bound fell at 21:58:02.
- **After-read** (the collector, from the published measurements): static fit `unavailable`, 0 pairs; sweep unavailable; inventory empty; `world_geometry` empty, all by construction of a project with zero components. Window 13 % at the first frame, 51 % at the last, 67 % on the probe after the kill; reset 02:20 UTC.
- **Committed** (`docs/probes/ot7/retained/heron-interrupted-b.json`, 8.5 KB, with an `interruption_analysis` block; REPORT.md headline, slot table, a new iteration 55 section, the F5 evidence row and the closing section; the retained index; a runner README section). Tests: `test_ot7_prompts.py`, `test_ot7_runner.py`, `test_retained_fit.py`, `test_lifecycle_report.py`, `test_review_design.py` (215 passed). No product code, protocol, payload, prompt byte or design changed.

## Why

The critic's message: proceed to F5 by running the frozen arm create prompt once on fresh `ot7-heron-b` through the window-gated runner when Claude is available, preserving the per-turn measurements and transcript digest. The reconcile the previous record said was due had already landed (`1a5518e5`), and the runner's probe read 10 % then 13 % against a 45 % bound, so the dispatch was permitted and made. The continuations the critic authorised "as the fit report requires" could not follow: there is no fit report, because the call was interrupted and the runner rightly closes the project (`resume` refuses an interrupted project; the retry is the same frozen prompt in `ot7-heron-c`). The retry was not dispatched in this iteration because the window read 67 % after the kill, above the bound, and because dispatching it under the same settings would most likely reproduce the same outcome, which is a decision to record before spending the window again. Advances F5 (`stormy-aspen-5433`) with its first measured call and F10 (`first-snow-5587`).

## Method

1. Read `.ouroboros/AGENTS.md`, the runner README, the last record (`damp-cedar-5823`) and its receipt builder, and `run.py window` (10 %, room).
2. Dispatched `run.py heron ~/cadex-projects/ot7-heron-b --model claude-fable-5 --turns 1` at 21:28 UTC under `setsid nohup`; the runner probed (13 %), dispatched, captured the stream frame by frame, killed the child at 1,800.0 s, ran the after-read (0.11 s) and exited 0 with `status: interrupted`.
3. Reconstructed the timeline from the stream: per-message timestamps and tool calls, the `describe_api` overflow and the four disabled-tool attempts, the three `write_script` results, the harness's `thinking_tokens` counters per block (the stream redacts thinking text) and the three "Output token limit hit" auto-resume frames; the window from the `rate_limit_event` frames and a probe after the kill.
4. Built the receipt with a create-turn variant of the throwaway builder (`/tmp`, not committed), added the `interruption_analysis` block, verified size and the absence of machine paths, wrote the report sections, ran the five ot7 test files, committed.

## Result

**What is true now.**

- F5 has had one interrupted create call on `ot7-heron-b` and still no attempt: the create prompt and all three continuations are unspent, and the retry is `ot7-heron-c`. Two void or interrupted calls now stand apart from F5's attempts (the pre-restart void call and this one). F6 and F7 are untried.
- The project `ot7-heron-b` holds a twelve-line probe script with three `part` outputs and no assembly; nothing in it is a design and no smoke was run. It stays as the receipt's evidence directory; the retry does not reuse it.
- Under the ADR-356 settings (effort `high`, 32,000-token output cap), this create prompt did not fit the 30-minute bound: the cap that turned iteration 44's single 64,000-token thought into a 16.5-minute kill turned this one into three 8-minute thoughts and a 30-minute kill. The cap bounds a message, not a turn's thinking.
- `describe_api` does not fit the harness's tool-result cap (163,200 characters), and the product agent has no file tool to read the overflow, so its only route to the contract is paging `inspect scope=api`, which cost 3 min 35 s here. This is a product finding about the tool surface; nothing was changed.
- The five-hour window read 67 % after the kill and resets at 02:20 UTC; the seven-day window read 26 %.

**Concerns and assumptions the next iteration must know.**

1. **Do not retry under the same settings without a recorded decision.** The reversible change is the effort level (`CADEX_EFFORT`, the CLI's documented soft control since ADR-356), which changes no prompt byte; lowering it for the create turn, or raising the runner's bound, are each a tooling decision that earns a DECISIONS line and a runner README paragraph before `run.py heron ~/cadex-projects/ot7-heron-c` is dispatched. The retry itself also waits for the 02:20 UTC reset.
2. The `describe_api` overflow is a candidate tooling unit (page or cap its reply so the harness delivers it), but it is not what consumed the bound: reading took four minutes, thinking took twenty-four.
3. The unreconciled tail is one record (this one).
4. The receipt builder is throwaway (`/tmp/ot7/build_create_receipt.py`); its conventions match the four F4 receipts, with `interruption_analysis` added.

Dispatch closed: 1 unit — F5's frozen create prompt dispatched on `ot7-heron-b` at 13 % of the window and interrupted at the runner's 30-minute bound: 4 minutes of reading after a `describe_api` overflow, three probe scripts, then three thinking-only messages that each hit the 32,000-token output cap; no design, no slot spent, retry `ot7-heron-c` after the reset and after a recorded decision on the effort level.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 33bda8623c1882fcdc4eb91ddae90595ab7c8d4f

## State Impact

- target: stormy-aspen-5433 — F5 has had its first call that reached a model, on ot7-heron-b (iteration 55), and it was interrupted: the runner's ADR-358 probe read 13 % and dispatched the frozen create prompt on a fresh empty project; the turn did not end on its own and was killed at 1,800.0 s (ADR-356: interrupted, slot_consumed false, slots_spent 0, continuations_used 0, retry ot7-heron-c). 68 model messages, 52 tool calls, no submit, no assembly: describe_api's 163,200-character reply exceeded the harness's tool-result cap and was written to a file the agent has no tool to read (Grep, Read, Bash, Agent disabled), so it paged the contract through 44 inspect scope=api reads in 3 min 35 s; two probe scripts of the catalog servo body, flange and horn were accepted as part outputs with no component (revision 544ea74e, twelve lines); then three consecutive thinking-only messages of about 31,950 estimated tokens each hit the 32,000-token output cap and were auto-resumed by the harness, 24 minutes in all, before the bound fell. After-read: fit, sweep and inventory unavailable by construction (zero components). Window 13 % to 51 % across the call, 67 % after, reset 02:20 UTC. F5 still has no attempt: the create prompt and all three continuations are unspent; the retry on ot7-heron-c waits for the reset and for a recorded decision on the effort level (CADEX_EFFORT) or the runner bound, since the same settings would most likely reproduce the outcome. Receipt docs/probes/ot7/retained/heron-interrupted-b.json with an interruption_analysis block
- target: first-snow-5587 — REPORT.md carries an iteration 55 section (the arm create call interrupted at the bound, with the timeline: 4 minutes of reading after the describe_api overflow, three probe scripts, three thinking-only messages at the 32,000-token cap), the headline, the F5 slot-table row (one interrupted call apart from the attempts, retry ot7-heron-c), the F5 evidence row and the closing section written forward; the receipt heron-interrupted-b.json (8.5 KB) is indexed in the retained README and the runner README records the two collector facts the call exposed
- target: chilly-union-8972 — Two measured facts about the product-agent turn under ADR-356's settings, recorded and not yet changed: describe_api's reply (163,200 characters) exceeds the harness's tool-result cap and the product agent has no file tool to read the overflow, so its only route to the contract is paging inspect scope=api; and the 32,000-token output cap bounds a message, not a turn's thinking: a create turn produced three consecutive thinking-only messages that each hit the cap and were auto-resumed by the harness, so the cap converts one long thought into several and the 30-minute runner bound still falls. The effort level (CADEX_EFFORT) is the documented soft control and the reversible change to decide on before the F5 retry
- target: mild-ledge-7157 — F5's first call that reached a model was interrupted at the runner's bound with no design written and no slot spent (iteration 55, ot7-heron-b, retry ot7-heron-c); F5–F7 all remain open with every slot unspent, F4 exhausted; the next unit is a recorded decision on the effort level or runner bound for create turns, then the F5 retry after the 02:20 UTC reset when the gate permits; the unreconciled tail is one record
