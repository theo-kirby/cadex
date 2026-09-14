---
node_id: 9d118d7b-9cf1-5aa3-9de3-e411ac5944b9
slug: happy-dawn-1960
title: 'F1: every build reply carries the measured fit, clearance joins the agent''s inspect scopes, and the prompt says a printout is a claim (ADR-346)'
created_at: '2026-09-14T17:59:53+00:00'
parents:
- silent-union-5108
summary: ''
---
## What

F1, the first product change of ot7 (ADR-346): the agent now sees measured fit. Every successful `write_script`, `edit_script`, `set_params` and `rebuild` reply the CLI bridge hands the model carries a `fit` block computed from the engine's published clearance measurements (`inspect scope=clearance`, read after the build under the bridge lock), never from stdout: verdict (`pass` / `fail` / `unavailable`), thresholds, check counts by status, and every failing pair by name with its minimum distance and common volume — intersections, pairs below the `cadex clearance` minimum, and pairs the engine could not measure, which fail too. `clearance` is now an inspect scope on the agent's tool surface. The system prompt's "verify through stdout" bullet is replaced by "FIT IS MEASURED, NOT PRINTED": a printout is a claim the script makes about itself, the `fit` block is the evidence, and a failing pair overrules any printout. The turn's `--json` envelope carries the last accepted build's block as `fit`; the prose report prints one line per failing pair.

## Why

F1 is the highest-ranked open criterion and the critic's named next unit after the freeze recovery. The cause ot6 measured is in the product: the engine already measures every pair at the solved pose but the agent could not reach it, so Heron's 248.2 mm³ buried tab and 0.2 mm horn gap were found by hand while the agent's printout said "fits". This unit is the smallest reversible change that puts those numbers in front of the agent on every build: CLI-side only, no protocol op or response shape change (the existing `clearance` scope is the producer), so no INTEGRATION.md or shell-client change. The critic's fix-first items were done first: the a024283a CLI suite result was recovered (624 passed, 1 skipped) and the freeze was recorded as `silent-union-5108`.

## Method

- `cli/cadex_cli/clearance.py`: `fit_summary(value, minimum, maximum_volume)` and `read_fit(client)`, reusing `pair_status` and the pager; bounded to 40 failing pairs with a `failing_truncated` count.
- `cli/cadex_cli/bridge.py`: `MODELLING_OPS`; `_read_fit()` never raises — an unreadable measurement is `verdict: unavailable` with the error and the build stays accepted (report, never refuse). `ToolCall.fit`, `BridgeState.last_fit`, progress line `fit fail: N failing of M pair(s)`.
- `cli/cadex_cli/tools.py`: `clearance` in `INSPECT_SCOPES`, scope and tool descriptions. `cli/cadex_cli/agent.py`: the overlay paragraph. `cli/cadex_cli/report.py` + `__main__.py`: `RunReport.fit`, envelope and prose.
- Tests: real-engine transaction test `test_a_script_that_prints_no_overlap_gets_the_overlap_in_its_reply` (script prints "fit check: no overlap" over two 10 mm blocks offset 9 mm; the model's reply carries the printout and `a ∩ b` intersection 100 mm³, equal to `cadex clearance`'s row); fake-engine bridge tests for fail, pass, unavailable, every modelling op and no read, refused build, unreadable measurement; `fit_summary` unit tests (unknown counts as failing, truncation, no assembly); prompt pins (old stdout line gone); scripted-turn report carries `fit`; prose lines. Engine side: `test_project_tool_surface.py::test_clearance_is_a_served_inspect_scope_the_cli_offers` loads the CLI's scope list by path and pins that the engine knows every offered scope and refuses an unknown one.
- Docs: `docs/CLI.md` (new §4 subsection on the fit block, the agent-instructions bullets, the envelope, the `clearance` row, file map), ADR-346.
- Verification: full CLI suite and full engine suite on this tree — results in Result. No protocol or payload change, so the packaged gate was not run.

## Result

F1's evidence now exists: the tool-surface test is updated under ADR-346; the misleading-stdout transaction test passes on a real engine; `clearance` is an inspect scope; the prompt no longer says to verify by printing; `docs/CLI.md` is updated. Ticks F1 pending the owner's checkbox.

Suites on this tree: `pixi run python -m pytest cli/tests` → 634 passed, 1 skipped in 538.8 s, exit 0 (up from 624 on the freeze tree: the ten new tests). `pixi run test-engine` → 2114 passed, 53 skipped, 1 failed in 308.4 s; the failure was the freeze test file missing its SPDX header (iteration 2, recorded on `silent-union-5108`), fixed in this iteration, after which `test_licensing_compliance.py` is 10 passed, 1 skipped. No other engine test changed. Packaged gate not run: no protocol or payload change.

What remains for the ladder: F2 (fit-intent declarations and the four-way check, with fixtures for Heron's three defects) is next; F3 (swept ranges) after it. The block's `pose` still reads "initial solved pose (not swept motion)" until F3. A design that places no assembly components gets `fit: unavailable`, which the prompt says means nothing was checked — a future F2 unit may want that to be a reported failure for a multi-part design.

Concern for the next iteration: the fit read adds one store-backed `inspect` per build reply; on the three-block fixture it is milliseconds, but nobody has timed it on a 20-component assembly (190 pairs, paged at 50). If a design turn feels slow, measure that read first.

No new dependency. No actor edit to any design. The unreconciled tail is now two records (this and `silent-union-5108`).

Dispatch closed: 1 unit — F1: every build reply carries the measured fit, `clearance` is on the agent's tool surface, and the prompt says a printout is a claim (ADR-346).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: a83c33661673b9ee40c20e18e753072dfba49581

## State Impact

- target: wild-horizon-5461 — F1's evidence exists (ADR-346): the bridge attaches a fit block computed from inspect scope=clearance to every successful write_script/edit_script/set_params/rebuild reply (verdict, counts, every failing pair with distance and common volume; unknown pairs fail; unreadable measurement is unavailable and never refuses); clearance is in the CLI's INSPECT_SCOPES; the system prompt's stdout-verification bullet is replaced by FIT IS MEASURED, NOT PRINTED; test_project_tool_surface.py pins the scope; the real-engine transaction test (script prints 'no overlap', reply carries the 100 mm³ a∩b intersection) passes; docs/CLI.md updated. Ticks F1 pending the owner's checkbox; pose is still the initial solved pose until F3
- target: chilly-union-8972 — cadex prompt's --json envelope carries fit (the last accepted build's block) and the prose report prints one line per failing pair; ToolCall.fit and BridgeState.last_fit expose it to the parent; each build reply costs one extra store-backed inspect read, untimed on large assemblies
- target: eager-summit-3153 — regression floor on this tree: CLI suite 634 passed/1 skipped; engine suite 2114 passed/53 skipped with one failure (the freeze test's missing SPDX header) fixed in the same iteration; packaged gate not run because no protocol or payload changed
