---
node_id: bc1b541b-dfe6-5377-81da-1c1037ee99d3
slug: northern-comet-5917
title: The walk's PROGRESS.md row carries a delta, and travel is spelled so it can
created_at: '2026-09-08T18:36:12+00:00'
parents:
- western-grotto-7499
summary: ''
---
## What

The walk's `PROGRESS.md` row now carries a delta, and the travel figures are
spelled so it can. Three changes in one commit (`2b0c1678`, ADR-260):

1. `_record_progress` (`cli/cadex_cli/__main__.py`) reads
   `previous_numbers()` once, before the row is appended, for **both**
   branches. It previously passed `previous=` only on the non-walk branch.
2. `_motion_cell` spells the two channels `travel_mm N on <component>,
   travel_deg N on <component>` and runs each through `compared_number`, so
   a later walk of the same project writes the change against the last walk
   that carried it.
3. `COMPARED_NUMBERS` gains `travel_mm` and `travel_deg`; `_compared` became
   the public `compared_number` and its per-label spelling the new
   `spelled_number` — one decimal for `total_reward`, four significant
   figures for everything else.

The run note is the same cell with its prefix stripped, so there is one
spelling to learn and the note carries the same delta. `review.json` is
untouched: it keeps `millimetres` and `degrees` under their own keys.

## Why

Charter criterion advanced: **the walk exists and is tested headlessly**
(`crisp-reef-5607`) and mission item 2's *iterate* leg — a walk that cannot
compare itself against its own previous run has no review step worth the
name. This is the planner's short-rung unit 2 (`western-grotto-7499`) and
the overseer's explicit instruction this dispatch: travel figures, both
channels, in the iterate comparison row.

The measurement behind it: **no walk row had ever carried a delta for any
figure.** `_record_progress` branches on the command and only the non-walk
branch called `progress_numbers(..., previous=...)`. Compounding it, ADR-259
spelled the travel `motion 0 mm (swing), 178.8° (swing)`, which `_NUMBER_RE`
— built from `COMPARED_NUMBERS` as `<label> <number>` — cannot parse, so
even registering the labels would have read nothing back. The reward deltas
live on the walk's **train** leg row and the travel figure on its **walk**
row, written by different branches, and nothing joined them.

The worked example is the linear carriage: baseline 103.298 mm travel at
`total_reward` 3.296298, iterate 103.719 mm at 2.760187. The travel held
while the reward fell — the exact thing an iterate run exists to notice —
and the walk could not say it.

Assumption written down rather than asked: **a delta is not a verdict.**
ADR-259 declined to rank the two channels against each other, and this unit
does not walk that back. A row that reports more travel and less reward
makes no claim about which mattered; that is the next design turn's call.

Also decided without asking: one spelling for the note and the row, rather
than keeping units in the note. Two wordings of one figure is the kind of
thing a reader has to reconcile, and the note is prose nothing parses, so
there was no cost to making it match.

## Method

- Read `_record_progress`, `_motion_cell`, `progress_numbers`,
  `previous_numbers`, `_NUMBER_RE` and `_compared` and confirmed the two
  defects by reading, not by guessing at them.
- Made the change, threading `previous` through both call sites of
  `_motion_cell` (the row and the note).
- Regressions, offline: the toy walk pins the new spelling and asserts a
  project's **first** walk carries no delta; a new
  `test_project_docs.py` round-trip writes a walk-shaped row, reads both
  travel labels back off it, and asserts the delta text is not mistaken for
  the next row's own value.
- Regression, real engine: extended the existing iterate lifecycle test
  (`test_the_walk_takes_the_toy_to_a_verified_rollout_and_iterates`) rather
  than adding a matrix, per the plan. It now asserts the first walk row
  carries no delta, the second carries `(Δ ±N vs <digest> at N)` on **both**
  channels, the row is not truncated, and it still ends in its documentation
  finding — the thing `PROGRESS_NUMBERS_LIMIT` protects.
- Docs in the same commit: `docs/CLI.md` §motion, `docs/DECISIONS.md`
  ADR-260, `docs/ROADMAP.md` checkbox.

## Result

`pixi run python -m pytest cli/tests` — **233 passed, 0 failed** in 213 s,
including the real-engine CPU-training lifecycle test with the new
assertions. `cli/tests/test_project_docs.py` — 24 passed, including the new
round-trip test (added after the full run was collected, so run separately).
Zone gate for `cli/**` is that suite; no other zone was touched, so no
build, no `pixi run gate`.

The row a second walk of a project now writes:

    clearance offending 1; unknown 0; pairs checked 1 (...); motion
    travel_mm 103.7 (Δ +0.419 vs 4b0a1c2d at 103.3) on carriage,
    travel_deg 0 (Δ ±0 vs 4b0a1c2d at 0) on carriage over 61 solved
    frame(s); docs notes 1, no actuators

One precision note worth having in the record: the change is measured
against the row **as written** (four significant figures), not against the
raw float, because the row is what a later run can read. So the carriage
delta is `+0.419`, not `+0.421`. The raw figure stays in `review.json`.

Still missing before `crisp-reef-5607` can be ticked: the charter's leading
short-rung instruction — one fresh `cadex walk --prompt` end to end on this
machine, on a third mechanism, into a project outside this repository. That
is plan unit 1 and was not attempted here; the overseer directed this
dispatch at the comparison row instead. Nothing in this unit needed a model
provider, so it was safe to do offline.

The tail is now 2 unreconciled record nodes (`western-grotto-7499` and this
one); no reconcile was run, per the work-iteration rules.

Dispatch closed: 1 unit — the walk's PROGRESS.md row carries travel deltas on both channels, pinned by an offline round-trip and the real-engine iterate lifecycle regression (ADR-260, commit 2b0c1678).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 2b0c1678ce7434923069e880b479de52504004da

## State Impact

- target: crisp-reef-5607 — The walk's PROGRESS.md row now carries a delta on both travel channels (ADR-260): _record_progress threads previous_numbers() through the walk branch, which it never did, so no walk row had ever carried a delta for any figure; and travel is spelled travel_mm/travel_deg so _NUMBER_RE can read it back. The review step can now say an iterate held its travel while its reward fell. Pinned by an offline round-trip test and the real-engine iterate lifecycle regression; cli/tests 233 passed.
- target: calm-peak-5247 — The lifecycle walk's iterate comparison is real for the first time: the row joins the travel figure (walk row) to what changed since the previous walk, and the run note carries the same delta off the same read. One spelling for note and row; review.json unchanged. A delta is not a verdict — ADR-259's refusal to rank the two channels stands.
