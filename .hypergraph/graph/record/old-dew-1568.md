---
node_id: f494f4f2-e359-51ce-861a-9ee742eacdbc
slug: old-dew-1568
title: 'ot7''s closing report: one row per design, and the done claim (ADR-397)'
created_at: '2026-09-20T02:56:30+00:00'
parents:
- frosty-sea-6051
summary: ''
---
## What

F10: ot7's closing report, rewritten forward into the document the charter
asks for, and a test that holds it there (ADR-397, commit `f7205560`).

`docs/probes/ot7/REPORT.md` now opens with **one row per design** — frozen
prompts and their digests, turns that reached the model, continuations used,
static fit per turn, final static and swept checks, smoke result, inventory,
actor edits and the ot6 comparison — followed by a complete fourteen-row list
of **every call that was not an attempt**, each with its receipt and its rule
(void / interrupted / unreached). The F1–F9 evidence table's F7, F8 and F9
rows are brought up to date, the restart amendment's stale F6 and F7 rows are
corrected, and the closing section claims done and names what remains open.
The chronology below those sections is unchanged: it is the record of what
happened.

`cli/tests/test_ot7_report.py` (6 tests) pins the four sections, the
per-design table's eleven columns and their values, the fourteen-row
non-attempt list with every receipt resolving, the F1–F9 rows, the open-items
list, the done claim, and every relative link, anchor, record slug and ADR the
report cites.

## Why

The critic named F10 as the next unit after the reconcile, and the charter
calls it the run's last unit. I did **not** run the reconcile the critic asked
for first: this dispatch forbids it in a work iteration, in those words and
with no exceptions, and says to say so in `## Result` and keep working. The
tail is now three records past the high-water mark — `fresh-dawn-0892`,
`frosty-sea-6051` and this one — and the next reconcile pass should fold F7's
smoke pass, the ADR-396 reopening and this report together.

I also did not spend F7's `continue-2` or `continue-3`, as the critic
directed. F7's bar is *at most* three continuations and it was met in one.

## Method

Every number in the new tables was read from a committed receipt rather than
restated from the prose, and two prose figures turned out to be wrong when
checked: F5's component count (11 in my first draft, **15** in
`heron-continue-3-c.json`) and the split of its seven uncatalogued sources
(three printed parts and four modified purchased solids, not five and two).
Both were corrected before the commit.

The per-design rows:

| Criterion | Turns | Cont. | Static per turn | Final | Swept | Smoke | Inventory |
|---|---:|---:|---|---|---|---|---|
| F4 | 4 | 3/3 | seed 15/120 → 0/120 → 0/105 ×3 | 0 of 105 | complete 5° | not required | 15 comps, all purchased catalogued |
| F5 | 4 | 3/3 | 7/120 → 1/120 → 0/105 → 0/105 | 0 of 105 | complete 5° | **pass** | 15 comps, 4 purchased solids uncatalogued |
| F6 | 4 | 3/3 | 0/276 → 0/378 ×3 | 0 of 378 | complete 100° | **fail** (support 102.2°) | 28 comps, all purchased catalogued |
| F7 | 2 | **1/3** | 12/406 → 0/406 | 0 of 406 | complete 15° | **pass** (re-exported model) | 29 comps, 24 catalogued / 5 printed |

Fourteen calls reached the model and ended on their own; fourteen others —
eight void, five interrupted, one unreached — spent no slot. Zero actor edits
to any design, in any project, across the whole run.

Verification: the test fails **5 of 6** against the report as it stood at
`7ae8760a`, and passes on the new one. `pixi run python -m pytest cli/tests`:
**861 passed, 1 skipped in 561.76 s**. No engine, protocol or payload code
changed, so no engine suite or packaged gate was run for this unit; the last
recorded ones are `pixi run test-engine` 2196 passed / 53 skipped and the
packaged gate 23 passed, from iteration 172.

## Result

**F10 has its report, and the report claims done.** Every F1–F9 criterion has
its evidence linked from one table; every design has one row; every call that
was not an attempt is listed with its receipt; and the open items are named
rather than argued away — F7's two unspent continuations and its smoke pin,
F5's uncatalogued servos and horns, F6's balancer needing a controller rather
than a fix, the swept check's discreteness, and the suites' skips as
unexecuted evidence. The critic owns the acceptance; the owner owns the
checkboxes.

What the report deliberately does **not** claim: that ot7's designs are better
mechanisms than ot6's (the two runs' checkers use different rules, so their
failure counts are not comparable numbers), that F7 has a smoke verdict on its
*accepted pin* (the pin holds the pre-ADR-393 MJCF; moving it costs a design
turn, and the control is printed beside the measurement), and that F5's
catalog failure or F6's topple are anything but measured results.

Concerns for the next iteration:

- **The tail is three records deep** and a reconcile is overdue by the
  charter's own threshold. It is the first thing after this.
- **F7 holds `continue-2` and `continue-3` unspent, and should keep holding
  them.** The exhaustion policy forbids repeating an attempt to fill the run,
  and its fit report names nothing to fix.
- No new dependency. No red tree. Nothing left stubbed.

Dispatch closed: 1 unit — ot7's closing report rewritten to one row per
design with its evidence, non-attempt list and open items, pinned by a new
six-test suite, done claimed (ADR-397).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: f720556059e8af614756267febe3aa4cfbc9dcf7

## State Impact

- target: first-snow-5587 — F10's report now exists in the shape the criterion asks for: one row per design with prompts, turns, continuations, per-turn fit failures, final static and swept checks, smoke and the ot6 comparison; a fourteen-row list of every call that was not an attempt; the F1-F9 evidence table current; the open items named; and done claimed. Pinned by cli/tests/test_ot7_report.py, which fails 5 of 6 on the prior report. Critic acceptance of done is the one thing still outstanding.
- target: mild-ledge-7157 — the ot7 charter reaches its last unit: F10's report is written and claims done. F7 keeps continue-2 and continue-3 unspent by design, its bar met in one continuation.
