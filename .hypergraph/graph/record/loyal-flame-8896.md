---
node_id: 6d1dd3f0-cf91-52c8-bfe1-05d48f0747b2
slug: loyal-flame-8896
title: F9's weld-exemption table says only what it models (ADR-370-373)
created_at: '2026-09-16T19:58:58+00:00'
parents:
- pale-jasper-8166
summary: ''
---
## What

Narrowed the counterfactual claim in F9's regression receipt to what it
actually models, and pinned the one measured fact that narrowing rests on.

- `docs/probes/ot7/REGRESSION.md` — the weld-exemption table was introduced as
  "what the same measurements say under **today's checker**" and closed with
  "the gap between the two columns is the four checker changes (ADR-370 –
  ADR-373)". Both overclaimed. The table models **ADR-372's weld exemption
  alone**: the same retained rows through `fit_summary`, with the `attached`
  intent supplied for the pairs each script already welds, nothing else
  varied. The heading now says so, the false sentence is deleted, and a new
  block states what is outside the table — ADR-370's attachment report,
  ADR-371's sweep coverage, ADR-373's clearance rule — and says plainly that
  the third column is not a fresh-build verdict for Finch, Robin or Heron.
- The ADR-370 exclusion is stated with its numbers rather than in the
  abstract, because it is the one exclusion that would *say* something about
  these designs. Of the welded pairs measured in the retained receipts
  (Finch 24, Robin 21, Heron 12), Finch's and Heron's all meet within
  ADR-370's 0.001 mm tolerance, and **ten of Robin's do not**: its chassis
  stands 0.3 mm from each of its two motors and 0.6 mm from each of its eight
  board and clamp screws. The retained revisions publish no `attachments` key
  at all, so nothing in either column counts that; a rebuild would report it.
- `cli/tests/test_retained_fit.py` — `test_welded_pairs_that_do_not_meet`
  pins those three counts and the 0.3 / 0.6 mm distances from the receipts,
  asserting `attachments` is absent, so the doc's numbers cannot drift. The
  weld-exemption test's docstring carries the same narrowing.

No product code changed. The retained measurements, the 44 / 39 / 20
comparison and the 44→28 / 39→28 / 20→12 counterfactual are untouched; only
what the document claims about them is.

## Why

The critic's message ordered this first: "Narrow REGRESSION.md's
counterfactual wording: the table models ADR-372's weld exemption only, not
all ADR-370–373 changes or a complete fresh-build verdict; state the
attachment and sweep exclusions already acknowledged in `pale-jasper-8166`."
That record's own Result section had recorded the exclusion honestly — "a
rebuild would also pick up ADR-370's attachment block and ADR-371's coverage
rule, which the table does not model" — and the document it shipped said the
opposite. F10 links this file as F9's evidence, so the document is what a
reader gets; an assumption that lives only in a record is not stated.

Then the gate, before any other work. F6 was **not** dispatched:
`run.py window --model claude-fable-5` → `room: false`, exit 1 in 1.97 s,
`seven_day_overage_included` 100 % at `org_level_disabled`, `five_hour` 2 %,
result frame "You've reached your Fable limit". `slot_consumed: false`,
`model_messages_before_limit: 0`. All four F6 slots and all four F7 slots
remain unspent. Under the charter's waiting exception this iteration is a
tooling/document unit, which is what the critic's message also prescribes.

## Method

1. `pixi run python docs/probes/ot7/runner/run.py window --model claude-fable-5`
   — refused as above, nothing spent.
2. Read `pale-jasper-8166` for the exclusions it acknowledged, then
   `test_retained_fit.py::test_weld_exemption_would_clear_exactly_these` to
   establish exactly what the second column is computed from: retained rows,
   `attached` intent on welded pairs, `fit_summary`. Nothing else.
3. Verified each exclusion against the receipts rather than asserting it:
   `attachments` is absent from all three `*.measurements.json` files, and
   `attachment_summary` on one of them returns `verdict: unavailable` with
   `pairs_checked: 0`; every `clearance_sweep` reads `unavailable` with the
   reason *No published sweep for this accepted revision*.
4. Computed the welded-pair separations through the test's own `_welded_pairs`
   derivation: Finch 0 of 24 apart, Robin 10 of 21, Heron 0 of 12; Robin's ten
   at 0.29999999999997984 mm (two motors) and 0.5999999999999936–
   0.5999999999999956 mm (eight screws). Wrote them into the document and then
   into the test.
5. `pixi run python -m pytest cli/tests/test_retained_fit.py` — 9 passed.
   Full `pixi run python -m pytest cli/tests` — **805 passed, 1 skipped**
   (530.62 s), the three new parametrisations above the 802 of the previous
   iteration. Engine untouched, no protocol op, argument or response shape
   changed, no payload changed, so neither `test-engine` nor the packaged gate
   is implicated by this diff.

## Result

F9's evidence document now claims only what it computes. Its third column is
labelled as the weld exemption's effect on one retained measurement set, the
three changes it does not model are named, and the sharpest of them carries
its own measurement: ten of Robin's welds hold nothing, at 0.3 and 0.6 mm,
which the retained receipts cannot report and a rebuild would. That number is
test-pinned, so the document and the product cannot drift apart silently.

F6 and F7 remain blocked on provider capacity with all eight slots unspent.
The binding field is still `overage.disabled_reason: org_level_disabled`,
which no clock forecasts; `five_hour` read 2 % while the refusal held, so a
five-hour reset is again not what unblocks them. Do not spend a frozen prompt
from a fallback harness and do not switch the experiment's model.

Concern for the next iteration: the unreconciled tail is now two records
(`pale-jasper-8166` and this one), both touching F9's node; a reconcile pass
should fold the correction that the weld table is ADR-372-only, so no state
projection repeats the wording just removed.

No new dependency.

Dispatch closed: 1 unit — REGRESSION.md's counterfactual narrowed to ADR-372's
weld exemption alone with the ADR-370/371/373 exclusions stated, Robin's ten
non-meeting welds measured (0.3 / 0.6 mm) and pinned in
`test_welded_pairs_that_do_not_meet`; F6 not dispatched, gate refused at
`org_level_disabled`, all eight F6/F7 slots unspent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: c537bb32c1e8f7a3e3a11193839d0fb4f0ec791a

## State Impact

- target: eager-summit-3153 — docs/probes/ot7/REGRESSION.md's weld-exemption counterfactual is now scoped to ADR-372 alone: its heading reads 'under ADR-372's weld exemption', the sentence claiming the two columns differ by 'the four checker changes (ADR-370 – ADR-373)' and that the third column is 'what a new design would be told' is removed, and a new block names the three exclusions. ADR-370's attachment report is not modelled (reported, never failed; the retained receipts carry no attachments key and read unavailable), ADR-371's sweep coverage is not modelled (every retained clearance_sweep is unavailable, 'No published sweep for this accepted revision'), and ADR-373 governs a clearance declaration these three scripts do not make. Measured while narrowing it: of the welded pairs in the retained receipts (Finch 24, Robin 21, Heron 12), Finch's and Heron's all meet within ADR-370's 0.001 mm tolerance and TEN of Robin's do not — chassis to each of two motors at 0.3 mm, chassis to each of eight board and clamp screws at 0.6 mm. cli/tests/test_retained_fit.py::test_welded_pairs_that_do_not_meet pins those counts and distances and asserts the absent attachments key. No product code changed, no retained design was rebuilt, and the 44/39/20 and 44->28 / 39->28 / 20->12 numbers are untouched. cli/tests 805 passed, 1 skipped (530.62 s). Commit c537bb32.
- target: narrow-dune-9454 — F6 was not dispatched this iteration: run.py window --model claude-fable-5 refused in 1.97 s, exit 1, room false, slot_consumed false, model_messages_before_limit 0, seven_day_overage_included 100 % at org_level_disabled, seven_day 55 %, five_hour 2 %, result frame 'You've reached your Fable limit'. All four F6 slots remain unspent and nothing was consumed.
