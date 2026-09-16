---
node_id: 4b245a66-44e3-58b9-9414-51724e1b37a4
slug: icy-ivy-3606
title: 'ADR-360 correction: an unknown describe_api section is refused after the argument-free engine request is answered, only the section argument never reaching the engine; no design turn at 78 % against the 45 % bound, continue-2 on ot7-heron-c still next, tail at three and reconcile due'
created_at: '2026-09-16T08:02:13+00:00'
parents:
- slender-union-6486
summary: ''
---
## What

A correction under the window gate, and no design turn. The critic's message for iteration 61 named a wrong sentence in three places from iteration 60: `docs/CLI.md`, ADR-360 in `docs/DECISIONS.md` and the record `slender-union-6486` each said that a `describe_api` section the contract lacks is refused "without reaching the engine". The code does not do that. `Bridge.call` (`cli/cadex_cli/bridge.py`) pops the bridge-owned `section` argument, sends the **argument-free** `describe_api` request to the engine, and only then compares the requested section with the section names taken from the reply; an unknown one is answered with `NO_SUCH_SECTION` and the list of sections after the engine has answered. So the true statement is narrower: only the `section` argument itself never reaches the engine, and the refusal cannot be decided before the reply because the section names come from it. All three places now say this (commit `f87b5c1c`); the record carries an italic correction note rather than a silent rewrite, following the precedent of `9a203c24`, which corrected a record body for a portable path. The runner README's iteration 60 section and the two REPORT.md forward notes never carried the wrong sentence and are unchanged. The ADR-360 tests in `cli/tests/test_mcp_protocol.py` already asserted the true behaviour (`client.args_for("describe_api") == [{}]` on the refusal path) and were re-run: 5 passed.

**The window.** `run.py window` read **78 %** at 08:00 UTC (`allowed`, reset 12:20 UTC) against the runner's 45 % bound, so F5 `continue-2` on `ot7-heron-c` was **not dispatched**. `run.py remaining` on `ot7-heron-c` still reads two completed turns, one continuation used, two unspent, `continue-2.prompt.txt` next, not closed. No design, prompt byte, project or accepted state changed.

## Why

The critic's message had two parts: correct the three wrong statements first, then resume `ot7-heron-c` with the frozen `continue-2` if Claude is available and a fresh probe permits, and otherwise make no change and invent no tooling unit. The correction was done exactly as asked. The probe read 78 % at 08:00 UTC with the reset four hours and twenty minutes away, so the charter's rule that design turns wait for the product agent and that a frozen prompt is never spent while the harness is limited kept the second part closed; the actor's own iterations spend the same window, and 78 % cannot fall before 12:20 UTC. Nothing else was changed, per the critic's instruction. Advances the CLI node (`chilly-union-8972`, whose ADR-360 fact was wrong in one clause) and the ot7 charter root (`mild-ledge-7157`); F5 (`stormy-aspen-5433`) is unchanged in slots.

## Method

1. Read the critic's message, ADR-360, the `docs/CLI.md` paragraph, the record body and `Bridge.call` lines 200–233; confirmed the request goes out with `args or None` before `api_sections(reply)` is consulted.
2. Replaced the sentence in all three files with one script, asserting each old sentence occurred exactly once; left an explicit correction note in the record body.
3. Ran `pytest cli/tests/test_mcp_protocol.py -k "section or describe_api or drift"`: 5 passed, 27 deselected.
4. Probed the window (`run.py window`: 78 %, no room) and read the F5 slot state (`run.py remaining`); dispatched nothing.
5. Committed the correction as one change (`f87b5c1c`); this record follows.

## Result

**What is true now.**

- ADR-360's documentation matches its code: an unknown `describe_api` section is refused with `NO_SUCH_SECTION` after the argument-free engine request has been answered, and only the `section` argument never reaches the engine. No code, test, protocol or prompt changed.
- F5 stands where iteration 59 left it: `ot7-heron-c` has two completed turns (create, `continue-1`), static fit 1 of 120 failing (the bench as world geometry), sweep complete with zero overlap, smoke passing, servos and horns uncatalogued; `continue-2` is next through `run.py resume`, two continuations unspent. F6 and F7 untried with every slot unspent; F4 exhausted.
- The window read 78 % at 08:00 UTC, reset 12:20 UTC. No design turn this iteration.

**Concerns and assumptions the next iteration must know.**

1. The unreconciled tail is now **three records** (`easy-otter-0439`, `slender-union-6486`, this one), so by the charter's reconcile rule the next unit is the reconcile pass unless the critic directs otherwise. The critic's own message said to reconcile after the next record brought the tail to three. When the pass folds `slender-union-6486`, it must take the corrected wording for `chilly-union-8972`, not the original clause.
2. After the reconcile, the first action of the next work iteration, when `run.py window` reads at or under 45 %, is `run.py resume "$PROJECTS/ot7-heron-c"` (`continue-2`, frozen, at `medium`). Its transcript is still the first measurement of ADR-360's paging: count the `describe_api` calls, whether each page was accepted, and whether a resumed session calls it at all.
3. Editing a record body is exceptional. It was done here because the critic directed it and a precedent exists; the correction is marked in the body so the record's history stays legible.

Dispatch closed: 1 unit — ADR-360 correction: an unknown `describe_api` section is refused after the argument-free engine request has been answered, only the `section` argument never reaching the engine; fixed in `docs/CLI.md`, ADR-360 and the `slender-union-6486` body (commit `f87b5c1c`), paging tests 5 passed; no design turn, the window read 78 % at 08:00 UTC against the 45 % bound (reset 12:20 UTC), `continue-2` on `ot7-heron-c` still next with two continuations unspent; the tail is three records and a reconcile is due.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: f87b5c1cc51b860b9284cdcf3ac159ed955431ad

## State Impact

- target: chilly-union-8972 — ADR-360's documented refusal path corrected (commit f87b5c1c): an unknown describe_api section is refused with NO_SUCH_SECTION after the argument-free engine request has been answered, because the section names come from that reply; only the bridge-owned section argument never reaches the engine. docs/CLI.md, ADR-360 and the slender-union-6486 body now say this; code and tests were already right (5 paging tests passed)
- target: stormy-aspen-5433 — No design turn in iteration 61: run.py window read 78 % at 08:00 UTC against the 45 % bound (reset 12:20 UTC); ot7-heron-c keeps two completed turns, create and continue-1 spent, two continuations unspent, continue-2 next through run.py resume when the probe reads room
- target: mild-ledge-7157 — Iteration 61 corrected ADR-360's wording at the critic's direction (docs/CLI.md, DECISIONS.md, the slender-union-6486 record body) and dispatched nothing: the window read 78 % against 45 % (reset 12:20 UTC); F5 slots unchanged, F6 and F7 untried, F4 exhausted; the unreconciled tail is three records, so the next unit is the reconcile pass, then continue-2 on ot7-heron-c when the probe reads room
