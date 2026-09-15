---
node_id: 6f7a4829-367f-5d45-9e1e-f7739ad2a9b7
slug: plain-dusk-2906
title: 'F4: continue-2 completed on ot7-heron-repair-d — no failing check named, no edit, unchanged script re-accepted at f03054d6; ADR-358 window gate committed and used for the dispatch; one continuation left'
created_at: '2026-09-15T20:32:53+00:00'
parents:
- light-river-7871
summary: ''
---
## What

F4's second frozen continuation, `continue-2.prompt.txt` (611 bytes, digest `9a78ff9d…`, unchanged), reached the model on `ot7-heron-repair-d` through `docs/probes/ot7/runner/run.py resume`, into the agent's own session after the completed repair turn and `continue-1` (ADR-357), with no actor edit to any design. Before it, this iteration verified and committed the ADR-358 runner change its own first attempt had written and left uncommitted when the actor's session limit cut it off at 15:49 UTC.

- **ADR-358 landed** (`0a7b3d21`): `run.py` probes the five-hour window with a one-word `claude -p` turn before every frozen prompt, keeps the reading in the receipt (`window_readings`, `window` on each dispatched row), and without room writes `status: paused` with a `deferred` block before any slot is persisted. `cli/tests/test_ot7_runner.py`: 68 passed. The gate's first live use was this dispatch.
- **Dispatch.** The window reset at 20:20 UTC. `run.py window` read 4 % at 20:22; the runner's own probe before the prompt read 6 % (`allowed`, reset 01:20 UTC) and dispatched at 20:23; the turn's first `rate_limit_event` frame read 7 %.
- **The turn ended on its own** after **128.7 s**: 17 model messages, 8 tool calls (7 `inspect` reads of the clearance scope: summary, all 105 pairs over three pages, the sweep and both joints' swept tables; 1 `rebuild`, reproducing digest `bf167b32…`), **no `edit_script` or `write_script` call**. The prompt asserts that the report still names failing checks; the agent wrote down the measured value at every tight pair, found `failing_count 0` at the rest pose and `maximum_common_volume 0.0` on all 210 swept rows, re-ran the unchanged script through acceptance (same revision `f03054d6…`, same digest) and recorded the project's ADR-014: "the claim of remaining failures is overruled by the engine's published measurements". Usage 3,486 output tokens (1,563 thinking), 2.40 M cache-read input tokens; the window went from 7 % to 28 % with the actor's session sharing it. Transcript 217,234 bytes (`ad4c2dae…`), frame by frame.
- **Committed** (`76b88953`): the receipt `docs/probes/ot7/retained/repair-continue-2-d.json` (7.9 KB), REPORT.md's headline, slot table, an iteration 52 section rewritten to carry both attempts, the F4 evidence row and the closing paragraph written forward, the retained index and one paragraph in the runner README. Tests: `test_ot7_prompts.py`, `test_ot7_runner.py`, `test_retained_fit.py`, `test_lifecycle_report.py`, `test_review_design.py` (215 passed). Full CLI suite: 755 passed, 1 skipped in 529.6 s (run concurrently with the design turn; the turn's 128.7 s is its own measurement).

## Why

The critic's message: resume `continue-2` on `ot7-heron-repair-d` after the recorded 20:20 UTC reset with current evidence that Claude has capacity, keep the frozen prompt unchanged, supply no design feedback. The reset had happened two minutes before this attempt started and the runner's own probe read 6 %, under the 45 % bound, so the continuation was sent. The one deviation from "only the continuation": the tree held the previous attempt's complete, uncommitted ADR-358 unit, and the runner that dispatches is that code, so it was verified and committed first as its own commit rather than left dirty under a design turn or stashed around it. No tooling beyond that, no prompt byte, no design edit. Advances F4 (`polished-forest-0215`).

## Method

1. Read `.ouroboros/AGENTS.md`, the loop log (attempt 0 of iteration 52 cut off at 15:49 UTC by the actor's session limit, 17 turns, nothing committed), the last record (`light-river-7871`), the uncommitted diff, and `run.py remaining` on d (2 completed, 2 unspent, next `continue-2`).
2. Ran `cli/tests/test_ot7_runner.py` (68 passed) and `run.py window` (4 %, room); committed ADR-358.
3. Dispatched `run.py resume ~/cadex-projects/ot7-heron-repair-d` in the background at 20:23 UTC with the default 45 % bound; the runner probed, dispatched, captured the stream frame by frame, ran the after-read and exited 0 at 20:25 UTC with `status: paused`.
4. Read the collector's after-read (`fit.json`, `clearance.json`, `inventory.json`, `repair-assessment.json`), the turn row, the result frame and the project's git log and `DECISIONS.md` (one new entry, script bytes unchanged at `59ff7c95…`).
5. Built the compact receipt with a throwaway script validated against `repair-continue-1-d.json` (turn, swept-fit, zero-distance and edit blocks reproduce it exactly); wrote the report sections; ran the five ot7 test files and the full CLI suite; scanned for machine paths (none); committed.

## Result

**What is true now (measured by the collector from the published measurements, not by the agent's text).**

- F4 stands at **three completed turns** on `ot7-heron-repair-d`: the repair prompt (iteration 48), `continue-1` (iteration 51) and `continue-2` (this iteration). `slots_spent: 3`, `continuations_used: 2`, one continuation unspent, next `continue-3.prompt.txt`, runner status `paused`.
- The accepted design is unchanged from iteration 51: revision `f03054d6…`, script `59ff7c95…` (557 lines). Static fit **pass, 105 pairs, 0 failing**, 16 pairs at 0 mm all declared contacts, `world_geometry` empty. Swept fit **complete** at 5°, shoulder [−90°, +65°] in 32 samples and elbow [−100°, +25°] in 26 (31.0 s in all), solved-pose agreement true, maximum common volume 0, no first contact beyond the 18 declared contacts per joint present from each lower limit. Inventory: all five catalog families at full count, `uncatalogued_sources` exactly base, upper_arm, forearm.
- **Attachment assessment: fail, unchanged.** `comp_horn_shoulder`/`comp_upper_arm` 0.19999999999999732 mm and `comp_horn_elbow`/`comp_forearm` 0.19999999999993 mm, declared as 0.05 mm clearances. Against F4's bar: "accepts with zero failing fit checks" met a third time on the product's checks; "resolves all three defects" still two of three.
- **The run's clearest measurement of the charter's premise so far.** A continuation that asserts failures without naming one, on a design whose every product check passes, does not move the agent: it trusts the measurements over the prompt, exactly as `cli/cadex_cli/agent.py` tells it to, and says so in a recorded decision. The horn gap stays a declared clearance because no report the agent reads calls it anything else. `continue-3` says "resolve every failing check it names" and asks for `NOTE design_specs:` lines with pass and fail counts; on this design it will most likely also change nothing, and that is F4's final measured result unless the agent reads the 0.2 mm horn rows differently on its own.
- ADR-358 is live: the receipt row for this turn carries the probe reading it was dispatched at, and `window_readings` holds the time and the bound.

**Concerns and assumptions the next iteration must know.**

1. **Window budget.** This turn cost about 21 points of a five-hour window (7 % → 28 %) with the actor sharing it, far less than the two editing turns (about 50–55 points each). `continue-3` fits in this window by the 45 % bound only if the actor's own usage leaves it there; the runner's probe decides, and a deferral costs nothing. The seven-day window read 47–48 % on the unified frame.
2. **Bash background timeout.** The dispatch ran under a Bash background task whose harness timeout is 10 minutes; this turn took 2 minutes, but a 12- or 25-minute turn dispatched the same way risks the harness killing the runner while the child turn (its own session) continues. Dispatch long turns with `setsid nohup` or through a process the harness does not own.
3. **The receipt builder is throwaway** (`/tmp`, not committed), validated against continue-1's receipt; its conventions (zero distance means exactly 0.0, first contacts exclude those present from the lower limit) match the previous receipt and are stated in the report.
4. No product code, protocol or payload changed in the design-turn commit; ADR-358 changed only `docs/probes/ot7/runner/run.py` and its test. The packaged gate was not needed.
5. The unreconciled tail is now two records (`light-river-7871` and this one).

Dispatch closed: 1 unit — F4's second frozen continuation completed on `ot7-heron-repair-d`: 128.7 s, 8 reads, no edit, the unchanged script re-accepted at `f03054d6…` with zero failing product checks static and swept and the horn gap still declared as clearance; the ADR-358 window gate committed and used for the dispatch; one continuation remains, next `continue-3`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 76b88953ea1282b80c295e74be77fe030acfc248

## State Impact

- target: polished-forest-0215 — F4 stands at three completed turns on ot7-heron-repair-d: the repair prompt, continue-1 and continue-2 (128.7 s, 17 messages, 7 clearance reads and 1 rebuild, no edit_script or write_script call); told by the frozen prompt that failing checks remain, the agent re-read every measurement, found failing_count 0 static and maximum common volume 0 on all 210 swept rows, re-accepted the unchanged script at the same revision f03054d6 and digest, and recorded the project's ADR-014 overruling the prompt; the after-read is unchanged from continue-1 (static pass 105 pairs 0 failing, swept complete at 5° on both joints, inventory all five catalog families, world_geometry empty, attachment assessment still failing on both horn-to-link pairs at 0.2 mm declared as 0.05 mm clearance), so two of three ot6 defects are resolved; slots_spent 3, continuations_used 2, one unspent, next continue-3 on d; this turn cost 7 % → 28 % of a five-hour window
- target: first-snow-5587 — REPORT.md carries an iteration 52 section for both attempts (the ADR-358 gate written by the cut-off first attempt, then continue-2 completed), the headline, slot table (F4: 3 attempts reached the model, 1 of 3 continuations unspent), F4 evidence row and closing paragraph written forward; the receipt docs/probes/ot7/retained/repair-continue-2-d.json (7.9 KB) is indexed in the retained README
- target: mild-ledge-7157 — ADR-358 is landed (commit 0a7b3d21) and exercised live: run.py probes the five-hour window before every frozen prompt, records the reading in the receipt and pauses with a deferred block when there is no room; its first live dispatch read 6 % and sent continue-2; a design turn that only reads costs about 21 points of a window, an editing turn about 50–55; test_ot7_runner 68 passed, full CLI suite 755 passed 1 skipped
