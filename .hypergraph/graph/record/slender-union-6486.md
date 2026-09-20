---
node_id: d17ae530-959b-5f22-9a5f-bebe65b29803
slug: slender-union-6486
title: 'ADR-360: describe_api paged into an index and per-section pages under a measured 21,500-character budget, section consumed by the bridge and never the engine; no design turn at 52 % against the 45 % bound, F5 continue-2 next on ot7-heron-c when the probe reads room'
created_at: '2026-09-16T07:58:49+00:00'
parents:
- easy-otter-0439
summary: ''
---
## What

ADR-360, a tooling unit under the window gate: `describe_api` now reaches the product agent as an **index** and **per-section pages**, each under a budget taken from measurement, and no design turn was sent (commit `147d553a`). The probe read 52 % at 07:40 UTC against the runner's 45 % bound (reset 12:20 UTC), so `continue-2` on `ot7-heron-c` was not dispatched; the two continuations stay unspent and no design, prompt byte or accepted state changed.

**The cut.** Without an argument, `describe_api` is the index: everything above the domains whole, each domain and the library with their globals and output types and their exports **by name only**, the catalog as its family names, and a `sections` line saying where the signatures are. With the bridge's own `section=<domain>` or `section=library`, it is one section: the block's notes, every export's name, full signature and first-paragraph description, the whole catalog for the library, and a `descriptions` line naming the `inspect scope=api` path holding the rest of any docstring. A section the contract lacks is refused with `NO_SUCH_SECTION` and the list of sections, after the engine has answered the argument-free request (the section names come from that reply); only the `section` argument itself never reaches the engine. *(Corrected in iteration 61 at the critic's direction; the original sentence said the refusal happened without reaching the engine.)* **`section` is the bridge's argument, not the protocol's**: `VIEW_ARGS` in `cadex_cli.tools` is the one allowed schema drift, the bridge pops it before the request, `OP_ARG_SPECS["describe_api"]` still takes nothing (pinned in `test_project_tool_surface.py`), and the engine op, reply, goldens and shell client are untouched. `API_VIEW_CHAR_BUDGET` is **21,500 characters**, under the largest result the harness accepted on `ot7-heron-c` (21,742, turn-1's largest `inspect scope=document` reply; 82,523 and 163,200 were refused). Measured on the live engine on 2026-09-16: index 13,239; sections assembly 20,502, part 20,457, library 16,358, partdesign 6,226, sketcher 4,616, mesh 3,337. The system prompt and tool description now say to read the index, then the section of every domain used; the frozen ot7 prompts are not touched.

**Evidence.** `cli/tests/test_mcp_protocol.py`: the drift test reads the allowlist; four new tests pin the index (no signature, engine args `{}`), a domain and the library section (signatures, first paragraphs, notes, the path note, `section` never reaching the engine, the engine reply untouched), and the refusal by name. `cli/tests/test_client.py`: the live-engine test holds the index and every section under the budget and checks that the sections between them carry every signature of the raw reply. `docs/CLI.md` (dated 2026-09-16), ADR-360 in `docs/DECISIONS.md`, the runner README's iteration 60 section and two forward notes in REPORT.md.

## Why

The critic's message: run F5 `continue-2` on `ot7-heron-c` through `resume` when Claude is available and a fresh window probe permits; if limited, take the bounded `describe_api` tooling unit with its fixture and required gates. The probe read 52 %, above the 45 % bound (ADR-358), and the charter forbids dispatching a design turn without room and forbids spending a frozen prompt while limited; the percentage rose from 38 % because the actor's own iterations spend the same window and it cannot fall before the reset. So the fallback was taken: the cut that flat-cove-2253 and the README's iteration 57 section named as a separate recorded decision. The kind of cut was decided by the measurement rather than a ratio guess: the compact rendering ADR-359 measured (69,587) lies inside the unknown band, and a per-domain page is exactly the shape the heron-c agent already paged by hand (`/domains/assembly`, one export at a time, `/library/catalog/servos`). Advances the CLI (`chilly-union-8972`) and the ot7 charter root (`mild-ledge-7157`); F5 (`stormy-aspen-5433`) is unchanged in slots and gains the fact that the next turn measures the paging.

## Method

1. Read the last record and the runner README; probed the window (52 %, no room); confirmed `remaining` reads two completed turns with `continue-2` next and a clean tree.
2. Measured where the ADR-359 view's 82,523 characters go on the live engine (domains 55,009 of which assembly notes 10,627; library 16,057 of which catalog 8,387), scanned both `ot7-heron-c` transcripts for the largest accepted tool result (21,742) and for the `scope=api` paths the agent read, and rendered candidate layouts to find one whose every page is under that size.
3. Rewrote `api_view` as `api_index` and `api_section` with `api_sections` and `no_such_section`; added `VIEW_ARGS` to `tools.py` and threaded it through `tool_definitions` and `Bridge.call`; rewrote the prompt line in `agent.py`.
4. Replaced the two ADR-359 tests, added the engine-side pin, ran `test_mcp_protocol.py` and `test_client.py` (44 passed), `test_project_tool_surface.py` (13 passed) and the full CLI suite (763 passed, 1 skipped, 527.6 s).
5. Wrote the docs and the ADR; committed.

## Result

**What is true now.**

- `describe_api` reaches the model as an index of names plus sections read with the bridge-owned `section` argument; every page is under 21,500 characters on the live engine, held by a test that also checks the sections carry every signature. The protocol, the engine op, the goldens, the shell client and the frozen prompts are unchanged; no build or packaged gate was needed (no engine source, protocol or payload changed).
- F5 is where it was: two completed turns on `ot7-heron-c`, create and `continue-1` spent, two continuations unspent, `continue-2` next through `resume`. F6 and F7 untried with every slot unspent; F4 exhausted.
- The window read 52 % at 07:40 UTC (reset 12:20 UTC); no design turn was dispatched this iteration.

**Concerns and assumptions the next iteration must know.**

1. The next unit's first action, when `run.py window` reads room, is `run.py resume "$PROJECTS/ot7-heron-c"` (`continue-2`, frozen, at `medium`). Its transcript is the first measurement of the paging: under this budget no page exceeds a size the harness has accepted, so a refused page would mean the cap is lower than any result yet seen and must be recorded; count the `describe_api` calls and whether each was accepted, and note that a resumed session's earlier contract reads are in its context already, so the agent may not call it at all.
2. The budget is a measured floor, not the cap. The assembly section has about a thousand characters of headroom; growth there fails `test_every_page_of_the_live_contract_fits_one_tool_result` rather than a design turn, and the fix is either a larger measured accepted result (raise the budget) or a further page split, both recorded decisions.
3. The full engine suite (`pixi run test-engine`) was not re-run; the only engine-side change is one assertion in `test_project_tool_surface.py`, which passed in its file. Reported as such.
4. The unreconciled tail is two records (`easy-otter-0439` and this one).

Dispatch closed: 1 unit — ADR-360: `describe_api` paged into an index and per-section pages under a measured 21,500-character budget (index 13,239, largest section 20,502 on the live engine), `section` consumed by the bridge and never sent to the engine, protocol and prompts untouched, drift test allowlisted and engine op pinned argument-free, CLI suite 763 passed; no design turn, the window read 52 % against the 45 % bound, `continue-2` on `ot7-heron-c` next through `resume` when the probe reads room.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 147d553a860ee04a25935a9d6815cc13d342b602

## State Impact

- target: chilly-union-8972 — describe_api reaches the model as an index and per-section pages (ADR-360, commit 147d553a): without an argument the index (everything above the domains, exports by name, catalog families, a sections line); with the bridge-owned section=<domain>|library argument one section (notes, every signature, first-paragraph descriptions, the whole catalog for the library, the inspect scope=api path for the rest); an unknown section refused as NO_SUCH_SECTION after the argument-free engine request has been answered, only the section argument never reaching the engine. VIEW_ARGS in cadex_cli.tools is the one allowed schema drift; OP_ARG_SPECS describe_api still takes nothing, pinned in test_project_tool_surface.py; engine op, protocol, goldens and shell client untouched. API_VIEW_CHAR_BUDGET is 21,500 characters, under the largest result the harness accepted on ot7-heron-c (21,742; 82,523 and 163,200 refused); live: index 13,239, assembly 20,502, part 20,457, library 16,358; the live test holds every page under the budget and that the sections carry every signature. The system prompt and tool description say to read the index then each used section. CLI suite 763 passed, 1 skipped
- target: stormy-aspen-5433 — No design turn in iteration 60: the probe read 52 % at 07:40 UTC against the 45 % bound (reset 12:20 UTC), so continue-2 was not dispatched; ot7-heron-c keeps two completed turns, create and continue-1 spent, two continuations unspent, continue-2 next through run.py resume when the probe reads room. Its transcript is the first measurement of ADR-360's paging: whether each describe_api page is accepted, or whether the agent, resumed into a session that already read the contract, calls it at all
- target: first-snow-5587 — REPORT.md carries two forward notes for ADR-360 (the iteration 57 describe_api fact now says the cut was made in iteration 60; the open section says continue-2 runs with describe_api paged and that iteration 60 sent no design turn at 52 %); the runner README gains an iteration 60 section with the window reading and the page sizes; DECISIONS.md carries ADR-360; docs/CLI.md documents the page shapes and the measured budget
- target: mild-ledge-7157 — Iteration 60 was a tooling unit under the window gate (52 % against 45 %, reset 12:20 UTC): ADR-360 landed, describe_api paged under a measured budget with the protocol and the frozen prompts untouched; F5 slots unchanged (two continuations unspent on ot7-heron-c), F6 and F7 untried with every slot unspent, F4 exhausted; the next unit is continue-2 on ot7-heron-c through resume when the probe reads room; the unreconciled tail is two records
