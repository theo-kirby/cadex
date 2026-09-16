---
node_id: 7684a15f-4a0c-5f7f-a8a3-365a6d6e82e5
slug: tidy-nest-3309
title: An unavailable sweep names which of its two causes (ADR-368); REPORT.md's product-version comparison lists three changes since F5
created_at: '2026-09-16T16:35:09+00:00'
parents:
- pale-garden-4669
summary: ''
---
## What

`fit.sweep.verdict: unavailable` now says which of its two causes it is, and
the ot7 report's product-version comparison lists three changes since F5
rather than two (ADR-368, commit `3cd8905e`).

Since ADR-367 the swept block has no joint row to judge in two different
situations and calls both `unavailable`: a revision accepted by an engine
older than ADR-367, which published no sweep at all, and a current revision
whose assembly declares no limited joint. Three surfaces each named only one,
and two of them named different ones — `sweep_summary`'s docstring named the
legacy case, the agent's system prompt named the no-joints case, and
`docs/CLI.md` asserted the legacy case in one paragraph and the no-joints case
in the next. The discriminator already existed in the block: `coverage` is
`unavailable` for the legacy case and `complete` for the no-joints one, and
`reason` says which in words. What was missing was that any surface said so.

- `_sweep_line` (`cli/cadex_cli/bridge.py`) reads `sweep unavailable: no
  published sweep` or `sweep unavailable: no limited joint` instead of a bare
  `sweep unavailable`, so the progress log, the runner's attempt rows and the
  turn report cannot record the two as one fact.
- The agent's system prompt (`cli/cadex_cli/agent.py`) and `sweep_summary`'s
  docstring name both causes, keyed to `coverage`; `docs/CLI.md` no longer
  contradicts itself; `cli/tests/fake_cadexd.py`'s `clearance_value` docstring
  stops calling an absent sweep what a step-less assembly publishes, which
  ADR-367 made false.
- `SWEEP_NO_PUBLISHED` replaces the fallback reason string written twice in
  `clearance.py`. Its text is unchanged, so no receipt's wording moved.
- `docs/probes/ot7/REPORT.md` now opens the product-version paragraph with all
  three ADRs (362, 366, 367) and carries a third-change paragraph for ADR-367
  with ADR-368's wording follow-up; it also records today's refused window
  probe.

No engine, protocol or payload change: this is CLI wording and one phrase.
Acceptance is untouched and the block stays advisory.

## Why

The critic's message asked for exactly two corrections before the unit —
distinguish raw `clearance_sweep.status` `unavailable` from
`fit.sweep.verdict` `unavailable` (which includes the no-limited-joint case),
and update REPORT.md's product-version comparison to three changes — and then
to resume F6 only when the window gate permits, spending no prompts and
manufacturing no work while refused. Both corrections are here. The first one
is not bookkeeping: the wording it fixes is what the agent reads on every
build reply, so it belongs to F1 (`wild-horizon-5461`), and the report edit
belongs to F10 (`first-snow-5587`).

The handoff correction the critic named is made here rather than in
`pale-garden-4669`, whose body is append-only: REPORT.md did already list
ADR-362 and ADR-366 when that record claimed the report needed them, and
ADR-367's own closing sentence ("`unavailable` keeps exactly one meaning")
is true of the raw published status and false of the summary verdict. Both
are corrected forward, in the report and in ADR-368.

F6 was not dispatched, because the gate is still shut — see the probe below.
No frozen prompt was spent and no F6/F7 slot moved.

## Method

- Read the three conflicting surfaces and the code that produces the verdict
  (`cli/cadex_cli/clearance.py:sweep_summary`), confirming from
  `_measure_joint_sweeps` that the engine only ever publishes `complete` or
  `incomplete`, so raw `coverage: unavailable` really is the legacy case
  alone.
- Changed the phrase, the prompt, the two docstrings and `docs/CLI.md`;
  extended the parametrised empty-sweep test to pin `coverage` and the exact
  phrase for all three cases.
- `pixi run python -m pytest cli/tests`: **783 passed, 1 skipped** (530.7 s).
- Failure on the old code proved by stashing only `bridge.py`: the three
  parametrised cases fail (`3 failed, 49 deselected`), and pass with it
  restored.
- `pixi run python -m pytest src/Mod/cadex/cadex_tests/test_project_tool_surface.py`:
  **13 passed** — the only engine test that reads `cadex_cli`.
- Window gate, `pixi run python docs/probes/ot7/runner/run.py window --model
  claude-fable-5` at 16:39 UTC: five-hour **12 %**, seven-day **52 %**, and
  the probe itself **refused in 2.3 s** — rejected `rate_limit_event` naming
  `seven_day_overage_included`, a synthetic `rate_limit` assistant frame, and
  an HTTP 429 reading "You've reached your Fable limit" — reset
  **2026-09-18 14:00 UTC**. By ADR-364 that is `room: false`.

## Result

The two causes of an `unavailable` sweep are distinguishable everywhere the
agent and the receipts read them, and `docs/CLI.md` no longer contradicts
itself. REPORT.md's product-version comparison names three changes since F5,
each with what it publishes that F5's four turns did not, and carries the
dated refused probe so the blocked state has its measurement in the report as
well as in the records. The exhausted F4 and F5 results are untouched.

F6 (`narrow-dune-9454`) and F7 (`rapid-grove-9687`) stay blocked with all
eight slots unspent; the binding limit is the organisation-level Fable one,
not the five-hour window, which read 12 %. The gate reopens no earlier than
2026-09-18 14:00 UTC, which is past this run's likely horizon — the next
iteration should probe once and, if refused, take a tooling, test or reconcile
unit rather than manufacturing design work.

Assumption carried: the fallback reason text was deliberately left byte-identical
so no retained receipt under `docs/probes/ot7/retained/` changes meaning; only
its single definition moved into a constant.

Concern for the next iteration: the tail is now two unreconciled records
(`pale-garden-4669`, this one), so a reconcile pass is due after three or at
the five-iteration mark.

Dispatch closed: 1 unit — ADR-368, an `unavailable` sweep names which of its two causes, and REPORT.md's product-version comparison lists three changes since F5; F6/F7 still gated by a refused Fable probe with all eight slots unspent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 3cd8905ecfb7d3427b12145f1e7658f9332480a0

## State Impact

- target: wild-horizon-5461 — The swept half of the build reply no longer gives one word to two facts: fit.sweep.verdict 'unavailable' is now read against 'coverage', and the agent's instructions, sweep_summary's docstring and docs/CLI.md all name both causes (a revision an older engine accepted, versus an assembly with no limited joint). The one-line phrase reads 'sweep unavailable: no published sweep' or 'sweep unavailable: no limited joint' (ADR-368, commit 3cd8905e). cli/tests 783 passed, 1 skipped; the parametrised empty-sweep test pins coverage and phrase for all three cases and fails on the old code.
- target: first-snow-5587 — REPORT.md's product-version comparison now lists three changes since F5, not two: ADR-362, ADR-366 and ADR-367, each with what it publishes that F5's four turns did not, plus ADR-368's wording follow-up. The report also carries the dated F6 gate reading: on 2026-09-16 at 16:39 UTC the window probe was refused in 2.3 s on the organisation-level Fable limit (five-hour 12 %, seven-day 52 %, reset 2026-09-18 14:00 UTC), so no prompt was spent.
- target: narrow-dune-9454 — Re-measured on 2026-09-16 at 16:39 UTC and still blocked: 'run.py window --model claude-fable-5' returned room=false, the probe refused in 2.3 s with a rejected rate_limit_event naming seven_day_overage_included and an HTTP 429 'You've reached your Fable limit', reset 2026-09-18 14:00 UTC. The five-hour window read 12 %, so the binding limit is the organisation one, not the window. All four F6 slots remain unspent and no frozen prompt was dispatched.
