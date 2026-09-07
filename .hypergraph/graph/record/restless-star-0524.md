---
node_id: 3fe96a39-64a4-5358-ace9-bdeb244c184b
slug: restless-star-0524
title: 'Bet: three modes leads as an evidence unit; the review step is wired to the inventory; the clearance check returns in the inventory''s shape'
created_at: '2026-09-07T22:00:51+00:00'
parents:
- fair-rose-5950
summary: ''
---
## What

Both lifecycle criteria that led short are declared met and flipped to
`working` by the reconcile, and the first headless review call landed. Short
is rewritten around what is left on the frontier, in mission order: the one
open mission-2 criterion (three modes, one shape) leads as an evidence unit,
the walk's review step is wired to the inventory that now exists, and the
clearance and intersection check is promoted from medium in the inventory's
shape rather than as a new protocol op. Medium loses the promoted clearance
unit and the remote-handoff unit, drops the design-leg-cause conditional that
never triggered, and gains the wiring unit for the clearance check ahead of
render and section. Long is untouched.

## Why

- **Short ranks 1, 2 and 3 all landed.** The prompt re-run ran clean on a
  second, prompt-designed mechanism and both records declared
  `crisp-reef-5607` and `swift-dusk-2951` met under the tick rule the last
  bet wrote; the reconcile flipped both to `working` [rec: placid-sky-7374]
  [rec: rustic-loom-0992]. The assembly inventory landed as
  `inspect scope="inventory"` plus `cadex inventory`, real-engine qualified,
  with no protocol change and no `shell/` diff [rec: fair-rose-5950]. Short
  is empty, so it is re-ranked from the frontier.
- **Mission 2 still has one open node, and it is cheap.** `witty-spark-2613`
  was held open because the walk did not complete from `--prompt`; that
  reason is gone [rec: placid-sky-7374]. The criterion's own wording asks for
  headless exercised, GUI-attached documented, remote scripted and
  documented, and the same steps and artifacts in all three. The remote
  handoff is scripted and offline-tested [rec: green-delta-7130], the
  scaffold names the mode and the shared paths [rec: wild-marsh-9611], and
  the GUI-attached walk is documented [rec: red-comet-9710]. The last bet
  placed this unit on medium conditional on ranks 1 and 2 running clean
  [rec: rustic-loom-0992]; the condition is met, and the charter's question
  policy says to take the smallest open unit in the highest-ranked mission
  with open work. So it leads: audit against the exact wording, add the one
  missing proof if there is one, declare or name what is missing. No
  dispatch, no GUI.
- **The ladder says wire each review call as it lands.** The operator's
  medium rung reads "one CLI call at a time … then wire each into the walk's
  review step as it lands" [rec: modest-summit-8554], and the inventory's
  record says the review step is wired to nothing, including the call that
  exists [rec: fair-rose-5950]. Wiring is one small walk change that must
  carry `project_docs.py` and its test in the same commit
  [rec: wild-marsh-9611]. It takes rank 2 because it is small, it is a walk
  change (mission 2's shape as much as mission 6's), and it makes the
  criterion's last clause true for the first call before the next one lands.
- **The clearance check returns to short, in the inventory's shape.** The
  promise stood since two bets ago [rec: glad-snow-3838]. The inventory
  proved that a review call can land with no `OP_ARG_SPECS` change and no
  `shell/` diff by publishing at rebuild and joining in `inspect`
  [rec: fair-rose-5950], and the only clearance check today is already a
  rebuild-time one (ADR-130). Measuring pairwise common volume and minimum
  distance in the assembly worker, where every placed solid already is,
  and applying thresholds in the CLI reader keeps the protocol still. The
  cost is rebuild time, so the unit measures it against the standing
  baseline (both example recipes under 16 s) [rec: misty-rain-9048] and
  falls back to the on-demand op the earlier bet specified
  [rec: flat-river-8853] only if the number says so.
- **The design-leg-cause conditional is withdrawn**: it existed only if a
  prompt re-run failed at the design leg, and both re-runs ran clean
  [rec: placid-sky-7374]. Nothing is lost; the envelope that names a cause
  is test-pinned [rec: ancient-wind-0117].
- **Budget.** Five iterations spent 1.3 h and about 22 dollars, but the
  five-hour usage window moved from 13 to 88 percent in this run, so the
  next hour may run slower than the last. Rank 1 is an evidence unit and
  rank 2 is a small walk change; only rank 3 needs a build. Three units is
  the right size for a short rung that may be throttled.
- **No new direction**: the frontier is not empty, and every unit here
  serves an open charter criterion.

## Method

Rewrote `young-crane-9546` (short) and `strong-birch-7412` (medium) in
full, negative knowledge carried forward verbatim; left `late-valley-7350`
(long) as it was. Exported, advanced the plan view's mark, synced,
committed.

## Result

Plan rewritten; PLAN.md regenerated; check green. The next actor's unit is
the three-modes audit against the criterion's exact wording, then the
review-step wiring, then the clearance check.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 3aba6186faf24c1a405e87abb0aef4766837531c

## State Impact

- target: plan/young-crane-9546 — short re-ranked: the three-modes audit leads; wiring the inventory into the walk's review step at rank 2; the clearance check promoted from medium at rank 3 in the inventory's shape
- target: plan/strong-birch-7412 — medium: clearance and remote-handoff units promoted out; the design-leg-cause conditional withdrawn; wiring the clearance check added ahead of render and section
