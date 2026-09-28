---
node_id: 10252de1-abf4-59d7-99ee-7819f50902e1
slug: sharp-tide-2612
title: 'ot10: build replies bounded for the model — outputs summarised, fit lists worst first (ADR-435)'
created_at: '2026-09-28T22:57:54+00:00'
parents:
- tidy-banner-2442
summary: ''
---
## What

The model's view of a successful build reply (`write_script`, `edit_script`, `set_params`, `rebuild`) is now bounded (ADR-435, amends ADR-346). The change is in `cli/cadex_cli/bridge.py` only. The engine reply, the protocol, `OP_ARG_SPECS` and the shell client are unchanged.
- `outputs` + `live_outputs` become one `outputs_view`: count, counts by `domain type`, names when 40 or fewer, `not_live`, and rows carrying facts or diagnostics. The pointer is `inspect scope=output target=<name>`.
- `fit_view` keeps every verdict, count and threshold. It lists each pair list worst first, cut at 12, with `<list>_omitted` and a `<list>_rest` scope path. `sweep.joints` lists only joints not swept to completion.
- `inventory_view` turns `appearance` into role counts, and `printed_edges` into totals plus the 12 sharpest parts.
- The turn report, `state.last_fit`/`last_inventory` and `look` keep the whole blocks.

## Why

This is the critic's named unit. `tidy-banner-2442` recorded that the agent's build replies overflowed the tool limit at about 200 outputs, which forced it to page `inspect scope=clearance`. It serves A5/A4 (`loyal-fountain-8709`): refusals and wasted turns in product turns.

**Deviation:** the critic asked me to reconcile `tidy-banner-2442` first. I did not. This dispatch's rules forbid the hypergraph-reconcile skill, `hypergraph update` and state-node edits in a work iteration, "no exceptions". The tail is now 2 unreconciled records (`tidy-banner-2442` and this one), so the next reconcile pass should fold both. I did run `hypergraph export` and `check` on the record graph.

## Method

- **Measured before changing anything.** I copied `ot10-biped-3` and `ot10-hexapod-11` to /tmp, which leaves the originals read-only. I replayed a `rebuild` of each accepted revision through the real `Bridge` on the dev-tree engine.
  - Biped (215 outputs): 85,954 characters.
  - Hexapod (186 outputs): 82,981 characters.
  - The budget is `API_VIEW_CHAR_BUDGET` = 21,500, from ADR-359, where the harness refused 82,523 and accepted up to 21,742.
  - On the biped, `outputs` + `live_outputs` were 60,669 characters. The fit block was 9,578 (sweep joints 6,694) and the inventory 8,611. The fit's `failing` list was 201 characters, so the overflow was the echoed output list, not the pairs.
- **Implemented** `outputs_view`, `fit_view` and `inventory_view`. Replayed through the new view: biped **12,163** characters, hexapod **13,758**.
- **Regression:** `cli/tests/test_build_view.py` builds a reply at biped-3 scale: 215 outputs, 2,485 pairs with 30 failing, 19 swept joints and 71 inventory components.
  - It asserts that the old view (the reply minus `display`) is over the budget, so it fails on today's shape.
  - It asserts that the new one is under the budget, with worst-first order, counts, pointers, and whole blocks kept by the parent.
  - Two smaller tests: a single-output build keeps its name and facts, and an output with no live object is named.
- **Updated tests that pinned the old shape:**
  - `test_a_build_reply_names_every_failing_pair_past_forty` is replaced by `test_sixty_failing_pairs_reach_the_model_worst_first_and_counted`. It pins the ADR-346 amendment.
  - Six engine-backed `test_clearance.py` tests now assert `fit_view(whole) == view`.
- **Overlay:** the two sentences in `cli/cadex_cli/agent.py` that promised "every failing pair" and "one row per joint" now describe the view and name the paging paths.
- **Docs:** `docs/CLI.md` has a new "A build reply fits one tool result" section and amends the two never-cut-short paragraphs. ADR-435 is in `docs/DECISIONS.md`.

## Result

- A build reply at robot scale now fits one tool result: 85,954 → 12,163 characters on `ot10-biped-3` and 82,981 → 13,758 on `ot10-hexapod-11`, against the measured 21,500 budget. Each view carries every verdict and count, the worst 12 rows of each pair list, and the `inspect` path for the rest.
- `pixi run test-engine`: 2247 passed, 53 skipped.
- `pixi run python -m pytest cli/tests` at the final revision: 1068 passed, 1 skipped. The first full run had found 6 `test_clearance.py` tests pinning the old shape; they were updated to the new invariant.
- The packaged gate was not run. No engine, protocol or payload file changed; the diff touches only `cli/`, `docs/` and tests.

Concerns and assumptions for the next iteration:
- ADR-346's "every failing pair in the reply" is now "counted whole, listed worst first, at most 12". This is a recorded direction change, not an accident. It rests on the measurement that an over-budget reply delivered zero pairs.
- The limit of 12 is a choice: the measured views sit at 12–14K, which leaves headroom for 12-row lists. It is not tuned against a transcript.
- The effect on the agent is not yet measured in a product turn. The next A5 transcript should show no paging of `inspect scope=clearance` to learn the fit.
- The A5 rubric, bar, judge and prompts are untouched. Nothing is re-scored. A5 by its letter stays not met.
- Reconcile is due: 2 unreconciled records.
- No new dependency.

Dispatch closed: 1 unit — build replies bounded for the model (ADR-435): outputs summarised, fit/inventory lists worst first at 12 with counts and paging pointers; biped-3 reply 85,954 → 12,163 chars under the 21,500 budget; regression fails on the old shape

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: f12da48fb4ab04893b1665c4ff5edcb83539c68b

## State Impact

- target: chilly-union-8972 — The model's view of a successful build reply is bounded (ADR-435, commit f12da48f, amends ADR-346): outputs+live_outputs become an outputs summary (count, by_kind, names ≤40, not_live, detail rows with facts), fit and inventory lists are worst first at 12 rows with <list>_omitted and an inspect path, sweep.joints lists only unswept joints; ot10-biped-3's rebuild reply fell 85,954 → 12,163 chars and ot10-hexapod-11's 82,981 → 13,758 under the measured 21,500 budget; the turn report keeps whole blocks; engine reply and protocol unchanged; test_build_view.py fails on the old shape
