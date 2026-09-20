---
node_id: 6a20bfeb-a71f-53c7-8310-58b0bdc4d65b
slug: solar-arrow-5671
title: A joint nobody bounded is a coverage hole, not a silence (ADR-375)
created_at: '2026-09-16T21:17:58+00:00'
parents:
- noble-flame-1906
summary: ''
---
## What

ADR-375: the swept report no longer passes over a joint that can move and
declares no limits.

`_measure_joint_sweeps` (`cadex_assembly_worker.py`) opened by dropping every
joint whose `angle_limits_degrees` and `length_limits_mm` were both `None`, so
such a joint reached **no row at all** and the assembly's coverage stayed
`complete`. It is now `incomplete` with a reason naming the limit to declare,
per kind. Exactly two joints keep their silence, because neither holds a range
by construction: a `fixed` joint, whose pair the attachment report measures
(ADR-370), and a suppressed joint the assembly also left unlimited (ADR-371).
An unlimited joint of a kind no sweep supports keeps the existing
unsupported-kind reason — no limit it could declare would have it swept.

`cadex_cli.clearance.SWEEP_NO_JOINTS` stops offering "unlimited" as a reason an
empty sweep found nothing to check: such a joint now has a row of its own, so
the empty sweep is the assembly whose every joint is welded or suppressed. No
other CLI code changed — an `incomplete` row already counts as coverage that is
actually missing, so `sweep_summary` reads it and `_sweep_line` says it.

Reported, never refused: no `fit_failures` entry, no threshold, no acceptance
change, no protocol op or argument change, no `shell/` diff. A revision
accepted before this publishes no such row, so retained receipts read exactly
as they were measured.

Commits `18492813` (the change) and `d18c90c8` (the report's hash).

## Why

F6 and F7 are the ranked frontier and both are blocked. I probed the gate
first, as the charter requires: `run.py window --model claude-fable-5` at
2026-09-16 — **refused in 2.02 s**, `rate_limit_event` rejected on
`seven_day_overage_included`, synthetic `rate_limit` assistant frame, HTTP 429
"You've reached your Fable limit", `disabled_reason: org_level_disabled`,
windows five-hour 7 % / seven-day 55 % / with-overage 100 %, `room: false`.
Void by ADR-355: no slot spent, no design turn dispatched. F6 and F7 keep all
eight create and continuation slots.

The critic's message said to take F6's create turn if the harness was
available, and otherwise to make no change unless a demonstrated tooling defect
remained — explicitly ruling out another documentation guard or waiting record.
So I went looking for a defect of the kind the last two units found, in the
surface F6 will exercise and F5 did not, and found one by reading
`_measure_joint_sweeps` against what a balancer is: **two wheels**. A wheel
rotates continuously and declares no limits, and the report said nothing about
it anywhere.

The shape of the reading is what makes it cost. `sweep_summary` judges over the
rows it is given, so one limited hinge sweeping clean beside two unlimited
wheels reads `sweep pass: 1 joint(s) swept`, and `SWEEP_COVERAGE_NOTE` — the
sentence that says coverage is not fit — prints only when the verdict is not a
pass. The agent is told the motion was checked. This is the third instance of
one defect class in this run's tooling after ADR-371 and ADR-374: a clean
reading taken over a set that silently excludes what matters. It advances
**F3** and reaches **F6** directly.

## Method

1. Probed the window first: refused, receipt above, no slot spent.
2. Reproduced before touching anything, headless: an assembly with one
   suppressed limited hinge and one unsuppressed unlimited revolute published
   `status: complete` with a single `skipped` row and no mention of the wheel.
3. Fixed the loop; re-ran the repro and got the wheel's row and `incomplete`.
4. Engine test (`test_joint_fit_sweep.py`): two wheels, a slider, an unlimited
   ball, a weld, a suppressed unlimited hinge and a suppressed limited one, in
   one call — every row, every status, the per-kind reason, that nothing was
   measured, and that an assembly of welds and suppressed unlimited joints is
   still complete coverage of an empty set. Red on the old code (the two
   wheels, the slider and the ball were absent from `joints`).
5. CLI test (`test_clearance.py`): the balancer-shaped roll-up — `incomplete`,
   3 checked, 1 complete, 0 skipped, `sweep incomplete: 2 of 3 joint(s)
   unswept`, nothing failing, both wheel rows at zero pairs with the
   declaration named — plus the changed wording. Red on the old wording.
6. One pre-existing test failed and had to move with the behaviour:
   `test_cadexd_lifecycle.py`'s ADR-367 coverage test parametrised an
   unlimited hinge expecting `complete`. That case is the wheel. It now expects
   `incomplete` naming the limit, and a third case welds the same pair so
   "complete coverage of an empty set" keeps an end-to-end fixture of its own.
7. `docs/XSCRIPT.md`, `docs/CLI.md`, `docs/INTEGRATION.md` and ADR-375 in the
   same change; `docs/probes/ot7/REPORT.md`'s product-version comparison moved
   from nine changes to ten, with what this one publishes.

## Result

Both suites and the packaged gate are green: `pixi run test-engine` **2151
passed, 53 skipped** (275.2 s); `pixi run python -m pytest cli/tests` **810
passed, 1 skipped** (533.9 s); the packaged gate **21 passed** against a
payload rebuilt and restaged from this change
(`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64`), the staged
worker confirmed to carry the new reason. One full build, as the charter
allows.

What the next iteration must know:

- **F6 and F7 are still blocked and still wholly unspent.** The probe read
  `org_level_disabled` with the five-hour window at 7 %; that is the tenth or
  so consecutive refusal, and no clock dates its end. Re-probe before any
  dispatch — only an unrefused probe is evidence. All eight slots are intact,
  and nothing here dispatched, extended, stopped or restarted anything.
- **This is the tenth product change F6 and F7 will run on**, and the third in
  a row that lands on their own hardware. `docs/probes/ot7/REPORT.md` counts
  it; the `narrow-dune-9454` and `rapid-grove-9687` notes saying the report is
  behind are spent.
- **Assumption recorded, and it is a judgement call.** An unbounded movable
  joint makes the *assembly's* coverage `incomplete`, so a design carrying one
  moves from a swept pass to a swept `incomplete` naming it. I took that over
  a fourth status counted apart like ADR-371's `skipped`, because ADR-371's own
  reasoning is that a suppressed joint *cannot move* — an unlimited one can,
  and an unchecked degree of freedom is missing coverage by the same rule that
  made ADR-367 publish the unswept rows. The consequence is deliberate: it is
  what makes the CLI print the coverage note, which is the sentence the agent
  needs.
- The unreconciled tail is now three records. Reconcile is the critic's call.

Dispatch closed: 1 unit — ADR-375, a joint nobody bounded is named as the
coverage hole it is; engine branch, CLI wording, two known-answer tests red on
the old code, one lifecycle test moved with the behaviour, docs, ADR and the
report's count.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: d18c90c82a0671fc12d2cf4fc8267dd0897ab8fe

## State Impact

- target: forest-wind-0342 — _measure_joint_sweeps publishes a row for every unsuppressed joint that could move and declares no limits: status incomplete with the limit to declare named per kind, so the assembly's coverage is incomplete instead of complete. Only a fixed joint and a suppressed unlimited joint are omitted (ADR-375)
- target: chilly-union-8972 — cadex_cli.clearance.SWEEP_NO_JOINTS no longer offers 'unlimited' as a reason an empty sweep found nothing: an unlimited movable joint now has a row of its own, so the empty sweep is the assembly whose every joint is welded or suppressed. sweep_summary and _sweep_line needed no change; an incomplete row already counts as missing coverage (ADR-375)
- target: narrow-dune-9454 — F6 probed again on 2026-09-16 (run.py window --model claude-fable-5): refused in 2.02 s, org_level_disabled, windows 7 / 55 / 100 %, room false, no slot spent; all four slots remain unspent. ADR-375 lands as the tenth product change F6 will run on and reaches its two wheels directly — a joint with no natural limit was silently unswept
- target: rapid-grove-9687 — same refusal leaves F7's four slots unspent; ADR-375 is the tenth product change it will run on, and a biped's hip and knee joints are the bounded case while any unbounded joint it declares is now named
- target: first-snow-5587 — REPORT.md's F10 product-version section now lists ten product changes since F5 (ADR-362, 366, 367, 368, 370, 371, 372, 373, 374, 375), with ADR-375's paragraph and commit 18492813. No done claim changed
