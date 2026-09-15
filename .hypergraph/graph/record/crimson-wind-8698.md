---
node_id: 0f704a88-8f8f-58a7-be81-73ac3895283a
slug: crimson-wind-8698
title: 'ADR-359: describe_api cut to one tool result (163,200 → 82,194 characters, tested budget), the ot7 collector at recorded medium effort, REPORT rows corrected; no design turn, window 78–95 %, F5 retry on ot7-heron-c after the reset'
created_at: '2026-09-15T22:22:17+00:00'
parents:
- mellow-summit-9733
summary: ''
---
## What

The critic's two fix-first corrections, then one tooling unit toward F5, with no design turn: the window read 78 % at the start of the iteration and 95 % at its end (reset 02:20 UTC), so under ADR-355/ADR-358 no frozen prompt was sent and no slot was touched.

- **REPORT.md corrected** (commit `52ca1e0c`): the F5 row counts two accepted probe scripts of three written; the F4 row counts four completed turns on `ot7-heron-repair-d`.
- **`describe_api` fits one tool result** (ADR-359, commit `b7a76905`). `cadex_cli.bridge.api_view` cuts the model's view of the reply to every domain and library export's name, full signature and the first paragraph of its description, and adds a `descriptions` line naming the `inspect scope=api` path that holds the full text. Measured on the live engine: 163,200 characters to 82,194 (compact would be 69,587; the assembly domain's notes, 10,627 characters, and the catalog rows are kept whole). `API_VIEW_CHAR_BUDGET` is 90,000 characters, a margin under the harness's default 25,000-token MCP tool-result cap, and a live-engine test in `cli/tests/test_client.py` holds the real contract under it and proves every signature is retained; a fixture in `cli/tests/test_mcp_protocol.py` with whole docstrings pins the trim, the note and the untouched engine reply, and fails on the old bridge. The engine op, the protocol and `OP_ARG_SPECS` are unchanged; the tool description in `cli/cadex_cli/tools.py` says what the reply carries.
- **The collector dispatches at `medium` effort** (ADR-359, same commit). `run.py` launches every turn of an attempt at `EFFORT_LEVEL = 'medium'` (`--effort` overrides a new attempt), passes `--child-turn --effort <level>` to the child, which sets `CADEX_EFFORT` before the CLI starts, records `settings` (`effort`, `max_output_tokens`, `turn_bound_seconds`) in the receipt and on every row, and reuses the receipt's level on `resume`; a receipt from before the field resumes at `high`, which is what its turns ran at. The CLI's own default stays `high`; the 32,000-token cap and the 30-minute bound are unchanged. Three fixtures in `cli/tests/test_ot7_runner.py`; the child's flag parsing was also proved by running the child entry with a fake CLI main.
- **Docs**: `docs/CLI.md` (the trim and the budget), the runner README (the describe_api fact closed, a new iteration 56 section with the dispatch command), `docs/DECISIONS.md` ADR-359, and the REPORT F5 row naming the effort the retry runs at.

Verification: `pixi run python -m pytest cli/tests` 760 passed, 1 skipped (pre-existing); the one engine test file that reads these docs, 19 passed. No engine source, protocol, payload, prompt byte or design changed, so no engine build or packaged gate was needed.

## Why

The critic's message: fix the two REPORT rows first; use `CADEX_EFFORT=medium` for the F5 retry, retaining the cap and bound, recorded in DECISIONS.md and the runner README with the effective settings in the receipt; dispatch the unchanged frozen prompt on fresh `ot7-heron-c` only after the reset and when the gate permits; while limited, fix the oversized `describe_api` response with a meaningful fixture. All of that was done except the dispatch, which the gate refused all iteration (78 % rising to 95 %, reset 02:20 UTC); the retry is the next unit's first action when `run.py window` reads room. Advances F5 (`stormy-aspen-5433`) by removing the two measured causes of the iteration 55 interruption before the retry, and the CLI's tool surface (`chilly-union-8972`).

## Method

1. Read the last record, the runner, the bridge, the harness's refusal frame in the `ot7-heron-b` transcript, and the agent's 44 `inspect scope=api` paths, which showed the index-based path form it already knows.
2. Measured the live reply by section (domains 131 KB, of which descriptions 82 KB across 123 exports; first paragraphs 7.6 KB) and the three rendering options, then chose the first-paragraph trim at the bridge over an engine change, an indent change or a shape change, because it is CLI-only, protocol-neutral and keeps the paths the agent used valid.
3. Wrote `api_view` and the two tests; made the runner's effort explicit, recorded and reused, with the flag placed after `--child-turn` so the existing tests' argv tail still names the prompt.
4. Ran the three affected test files, then the whole CLI suite, wrote the docs and the ADR, committed the REPORT corrections apart from the unit, and re-read the window.

## Result

**What is true now.**

- F5 still has no attempt: the create prompt and all three continuations are unspent, and the retry is the same frozen prompt on fresh `ot7-heron-c`, at `medium`, after 02:20 UTC and only when the runner's probe reads room. Both measured causes of the iteration 55 interruption are addressed before it: the contract now fits one tool result, and the turn runs at the documented soft control's lower level.
- The bridge's `describe_api` view is 82,194 characters on the live engine, held under 90,000 by a test; the engine reply is untouched at 163,200.
- Every ot7 receipt written from now on carries `settings`; `resume` cannot change an attempt's level.
- Two commits: `52ca1e0c` (REPORT corrections) and `b7a76905` (ADR-359).

**Concerns and assumptions the next iteration must know.**

1. Whether `medium` fits the 30-minute bound is a measurement the retry makes, not a fact; a further level change is another recorded decision, and a changed prompt would be a new attempt.
2. The first paragraph of a docstring is the summary line; an agent that needs the rest must read `inspect scope=api path=/domains/D/exports/N/description` and count N in listed order. That is the shape the heron-b agent already used, and the note says it, but nothing yet measures whether the trimmed view is enough to author a design without paging; the heron-c transcript will.
3. The 90,000-character budget assumes the harness estimates tokens near four characters each; the harness's refusal message quotes characters, not its ratio. If a future call is still refused, the compact rendering (69,587) is the next cut.
4. The unreconciled tail is two records (this one and `mellow-summit-9733`).

Dispatch closed: 1 unit — the critic's REPORT corrections landed; ADR-359 cut the model's view of `describe_api` from 163,200 to 82,194 characters under a tested 90,000 budget with signatures retained, and the ot7 collector now launches every turn of an attempt at recorded `medium` effort, reused on resume; no design turn, the window read 78–95 % all iteration, and the F5 retry on `ot7-heron-c` is the next unit's first action after the 02:20 UTC reset when the gate reads room.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: b7a76905a9d892714f62366444eb5f2e0bbdb479

## State Impact

- target: stormy-aspen-5433 — Before the F5 retry, both measured causes of the iteration 55 interruption are addressed (ADR-359, iteration 56, commit b7a76905): the bridge's view of describe_api is cut to every export's name, full signature and first-paragraph description with a note naming the inspect scope=api path for the rest (163,200 to 82,194 characters on the live engine, under a 90,000-character budget a live-engine test holds; engine reply and protocol untouched), and the ot7 collector launches every turn of an attempt at medium effort, recorded as settings in the receipt and on every row and reused on resume (CLI default still high; cap and bound unchanged). No design turn this iteration: the window read 78 % at the start and 95 % at the end, reset 02:20 UTC, so no prompt was sent and no slot touched. F5 still has no attempt: create prompt and all three continuations unspent; the retry is the unchanged frozen prompt on fresh ot7-heron-c at medium, dispatched only when run.py window reads room
- target: chilly-union-8972 — describe_api reaches the model cut to one tool result (ADR-359): cadex_cli.bridge.api_view keeps every domain and library export's name and full signature and the first paragraph of its description and adds a descriptions line naming the inspect scope=api path that holds the full text; API_VIEW_CHAR_BUDGET is 90,000 characters, held on the live contract (82,194) by cli/tests/test_client.py, with a whole-docstring fixture in cli/tests/test_mcp_protocol.py pinning the trim, the retained signatures and the untouched engine reply. The engine op, the protocol and the tool surface are unchanged; the describe_api tool description says what the reply carries; docs/CLI.md documents it. The 32,000-token cap and the effort default (high) in the CLI are unchanged
- target: first-snow-5587 — REPORT.md corrected as the critic asked (commit 52ca1e0c): the F5 row counts two accepted probe scripts of three written and the F4 row counts four completed turns; the F5 row names the retry's effort (medium, ADR-359). The runner README closes the describe_api fact and carries an iteration 56 section with the dispatch command and the recorded settings; DECISIONS.md carries ADR-359
- target: mild-ledge-7157 — Iteration 56 was a tooling unit under the window gate (78 % to 95 %, reset 02:20 UTC): ADR-359 landed (describe_api fits one tool result; the collector dispatches at recorded medium effort) and the two REPORT rows were corrected; F5–F7 remain open with every slot unspent, F4 exhausted; the next unit dispatches the unchanged frozen arm create prompt on fresh ot7-heron-c through run.py when the probe reads room, then its continuations as the fit report requires; the unreconciled tail is two records
