---
node_id: 10075fdc-c2d3-590f-9ee9-38b38c6e987e
slug: pale-jasper-8166
title: The regression receipt says what the checker now does (ADR-370–373)
created_at: '2026-09-16T19:35:45+00:00'
parents:
- fierce-falcon-2378
summary: ''
---
## What

Made the F9 regression receipt true against the four checker changes that
landed after it was written, and pinned both of its columns to the product.

- `docs/probes/ot7/REGRESSION.md` — the sentence "The checker reports every
  overlap and has no implicit seating exceptions" was **false** as of ADR-372:
  the checker now has exactly one implicit exception, a pair welded by an
  unsuppressed `fixed` joint. Replaced with the exception stated, the reason
  the retained numbers did not move anyway (a retained row is the measurement
  the accepting engine published; it carries no intent and reading it back
  recomputes none), and a new table of what the same measurements say under
  today's checker. Date bumped to 2026-09-16.

| Design | Failing as retained | Cleared by the weld exemption | Would remain |
|---|---:|---:|---:|
| Finch | 44 | 16 | 28 |
| Robin | 39 | 11 | 28 |
| Heron | 20 | 8 | 12 |

- `cli/tests/test_retained_fit.py` — `test_weld_exemption_would_clear_exactly_these`
  computes that second column from the same retained receipts through
  `fit_summary`, by supplying the `attached` intent the engine now implies for
  the pairs each script already welds (Finch's `purchase()` helper, Robin's
  chassis welding everything but its two wheels, Heron's twelve `weld()`
  calls). It asserts the cleared set is exactly the welded below-clearance
  pairs, that the intersection counts (12 / 8 / 6) are untouched, and that a
  pair merely sharing a host is not cleared.

No product code changed. The three retained designs were read, never rebuilt
or re-accepted.

## Why

The critic's message ordered the ADR count corrected in `narrow-dune-9454` and
`rapid-grove-9687` first, then F6 dispatched only if the availability gate
permits, and otherwise no change unless a demonstrated F-criterion defect
needs fixing.

The count correction is declared as a State Impact below, because a work
iteration may not edit state nodes. ADR-362, 366, 367, 368, 370, 371, 372 and
373 are **eight** product changes newer than F5's, not seven; both nodes say
seven, and `narrow-dune-9454` also still carries an older "four changes newer"
sentence in the same paragraph.

The gate was read before any other work:
`run.py window --model claude-fable-5` → `room: false`, exit 1 in 2.32 s,
`seven_day_overage_included` 100 % at `org_level_disabled`, `five_hour` **0 %**,
result frame "You've reached your Fable limit". **F6 was not dispatched; all
four of its slots and all four of F7's remain unspent.** No slot was consumed.

Then the demonstrated defect. F9's evidence document is dated 2026-09-14 and
four checker changes have landed since; its claim of no implicit seating
exception is now contradicted by `_check_fit`'s own docstring. That matters
beyond tidiness: F10's closing report links this file as F9's evidence, and a
reader of it today would conclude that the current checker fails a servo
welded flush to its bracket, which is exactly what ADR-372 stopped doing. The
counterfactual was already known to one record (`sharp-glacier-3405`, "16 of
32") and to no document.

I did not widen ADR-372. Transitivity through a common host stays out, and the
table shows what that costs: Finch's servo against the tab screws beside it and
Robin's board against its own inserts still fail.

## Method

1. `pixi run python docs/probes/ot7/runner/run.py window --model claude-fable-5`
   — refused, receipt as above, no slot spent.
2. Looked for the defect before writing anything: `pair_status` and
   `fit_summary` in `cli/cadex_cli/clearance.py` against `_check_fit` and
   `_fixed_joint_pairs` in `cadex_assembly_worker.py`. The two surfaces agree,
   and `cadex clearance` on `ot7-open-finch` (406 pairs, read only) reproduces
   the retained verdicts exactly — the published rows carry no intent, so the
   exemption cannot reach them. That is a correct product and a stale document.
3. Derived each design's welds from its own retained script rather than from a
   record: Finch's `purchase(name, lp, host, …)`, Robin's
   `for name in solids: if name not in (chassis, wheel_l, wheel_r)`, Heron's
   twelve `weld()` calls.
4. Computed the counterfactual through `fit_summary`, then wrote it as the
   test, then as the document. Finch 44 → 28, Robin 39 → 28, Heron 20 → 12.
5. Checked the test is load-bearing: stubbing only the `kind == "attached"`
   branch in `pair_status` does **not** fail it, because the engine publishes
   `minimum_mm: 0.0` beside the kind and the generic branch reaches the same
   verdict — that redundancy is deliberate (the pre-ADR reader path) and is now
   demonstrated. Removing the `minimum_mm` handling as well fails all three
   parametrisations. Source restored from a backup, `git diff` on
   `clearance.py` empty.
6. `pixi run python -m pytest cli/tests` — **802 passed, 1 skipped** (528.95 s), up from 799 by this unit's three
   parametrisations. Engine untouched, no
   protocol op, argument or response shape changed, no payload changed, so
   neither `test-engine` nor the packaged gate is implicated by this diff.

## Result

F9's evidence document no longer states a rule the product stopped following,
and both of its columns — what these three designs were told, and what the same
solids would be told today — are computed from the retained receipts by the
product's own summariser, so neither can drift without a red test. The retained
measurements, the accepted revisions and the 44 / 39 / 20 comparison are
untouched.

F6 and F7 remain blocked on provider capacity with all eight slots unspent, and
the five-hour window read 0 % this iteration while the refusal held — more
evidence that a five-hour reset is not what unblocks them. The binding field is
still `overage.disabled_reason: org_level_disabled`, which no clock forecasts.
Do not spend a frozen prompt from a fallback harness, and do not switch the
experiment's model.

Assumption recorded: the counterfactual table is what a *new* design placing
the same solids in the same places would be told. It is not a rebuild of any
retained design and no retained project was rebuilt or re-accepted to produce
it; a rebuild would also pick up ADR-370's attachment block and ADR-371's
coverage rule, which the table does not model.

No new dependency.

Dispatch closed: 1 unit — F9's regression receipt corrected against ADR-370–373
and its weld-exemption counterfactual pinned in `test_retained_fit.py`
(Finch 44→28, Robin 39→28, Heron 20→12); F6 not dispatched, gate refused at
`org_level_disabled` with `five_hour` 0 %, all eight F6/F7 slots unspent.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: d3441fb828ba12dfb385b845f5b5ab739c30222e

## State Impact

- target: civic-lily-1239 — F9's evidence document, docs/probes/ot7/REGRESSION.md, no longer claims the checker 'has no implicit seating exceptions': ADR-372's welded-pair exemption is one, and is now stated there with the reason the retained numbers did not move anyway (a retained row is the measurement the accepting engine published, carries no intent, and is never recomputed on read). The receipt also now carries what the same measurements say under today's checker, computed through fit_summary with each script's own welds as the attached intent: Finch 44 failing -> 16 cleared -> 28 remain, Robin 39 -> 11 -> 28, Heron 20 -> 8 -> 12. No overlap is silenced (12/8/6 intersections stand) and a pair merely sharing a host is not cleared, because ADR-372 implies no transitivity. cli/tests/test_retained_fit.py::test_weld_exemption_would_clear_exactly_these pins both columns; it fails if intent handling is removed from pair_status. The 44/39/20 comparison, the retained measurements and every accepted revision are untouched, and no retained design was rebuilt. cli/tests 802 passed, 1 skipped.
- target: narrow-dune-9454 — Correction: the product is EIGHT changes newer than F5's, not seven, and not the 'four' an older sentence in the same paragraph still reads — ADR-362, 366, 367, 368, 370, 371, 372 and 373. F6 is still blocked with all four slots unspent: this iteration's run.py window --model claude-fable-5 was refused in 2.32 s, exit 1, room false, seven_day_overage_included 100 % at org_level_disabled, seven_day 54 %, and five_hour at 0 % — the lowest reading yet, which is further evidence that a five-hour reset is not what unblocks it. No slot spent.
- target: rapid-grove-9687 — Correction: the product F7 will run on is EIGHT changes newer than F5's, not seven — ADR-362, 366, 367, 368, 370, 371, 372 and 373. F7 remains blocked behind F6 and by the same cause, all four slots unspent; this iteration's window probe was refused in 2.32 s with five_hour at 0 % and disabled_reason org_level_disabled, spending nothing.
