---
node_id: 146c20fc-98b9-5e4e-8d67-47fe8068f6f8
slug: swift-orchard-8539
title: 'Bet: the walk runs from nothing again, and the section names the moving part it missed'
created_at: '2026-09-09T00:20:14+00:00'
parents:
- sage-glacier-2165
summary: ''
---
## What

The short rung is empty — both dispatchable units of the last plan landed
(ADR-274 and the uninterrupted walk `runs/uninterrupted-46`, exit 0 in 103.2 s
[rec: sage-glacier-2165]; ADR-273, the derived section ranked by what it cuts
[rec: rising-rain-0117]). Re-rank it onto three, in this order:

1. **Run the walk again — from nothing, on a mechanism this machine has not
   built, in one uninterrupted invocation.** Not a re-roll of
   `runs/uninterrupted-46`: that run resumed `ot4-quill`'s conversation and its
   accepted script, and design-from-nothing in one invocation on this machine
   is evidenced only by `ot4-swing2` and `ot4-carriage`, both walked *before*
   ADR-271, ADR-273 and ADR-274 existed.
2. **Let the walk resolve its model from the project's own record, and stop a
   failed turn regressing it.** Carried unspent from the last pass, re-checked
   against the source this pass.
3. **The one new direction: the section block names what it missed, and says
   when what it missed was moving.** `review.json` already carries per-object
   section statuses and a motion block read from the rollout trace; nothing
   crosses them, so the eye can still report `ok` while the part the rig exists
   to move was never cut.

## Why

**Unit 1.** The rung is explicit: "Run the documented headless lifecycle entry
point end to end, on this machine, and record exactly which leg still needs a
person or a guess… Do this before anything else, every time the short rung is
empty." It is empty. What it must *not* become is the same run again — the
standing negative knowledge bars re-rolling a completed walk, and
`uninterrupted-46` is completed. The non-redundant reading is the one gap that
record names itself: "this run resumed an existing project, so
design-from-nothing through the same entry point is unevidenced here" — and the
two from-nothing walks that do evidence it (17:43 and 5:59.8) predate every fix
this evening landed. A fresh mechanism is also the only honest test of ADR-273
and ADR-274: both were tuned or diagnosed on rigs that already existed, and
ADR-274's follow-up has never fired live at all [rec: sage-glacier-2165]
[rec: rising-rain-0117] [rec: swift-dusk-2951 via crisp-reef-5607].

Choose a mechanism with **two joint kinds in one rig** — a crank-slider: a
revolute crank driven by a position servo, a coupler link, a prismatic slider.
Every walk on this machine has been single-joint-kind (revolute swing arm,
prismatic carriage, revolute quill lift), so this is new coverage for
`swift-dusk-2951`'s "no mechanism-specific code" half rather than a fourth
sample of the same shape; and its parts lie near one plane, which is the
geometry ADR-273's ranking was never given.

**Unit 2.** The defect is unchanged and was re-read against the tree this pass:
`--model` takes `default=default_model()` at parse time
(`cli/cadex_cli/__main__.py:160,411`), `default_model()` is `$CADEX_MODEL` or
`DEFAULT_MODEL` (`cli/cadex_cli/agent.py:45,59`), and `agent.json`'s recorded
model is read by nothing in the resolution path — so a project that last worked
under one model runs the next turn under whatever the machine's default is. Then
`write_agent_state` compares `(session_id, model)` as one identity
(`cli/cadex_cli/session.py:87`) and rewrites the record with the model that just
failed, session id unchanged. Token-free, `cli/` only, offline-testable
[rec: sleepy-mesa-0821] [rec: dry-rain-0489].

**Unit 3, the new direction (mission 6).** `damp-moon-9297` now says twice, in
its own negative knowledge, what the review does not do: "a bounds-coverage
count says nothing about **which** objects get cut, and in particular nothing
about the moving part," and "Read the per-object statuses." Both are
instructions to a *reader*. ADR-273 made the count legible and honestly
concluded that on `ot4-swing2` no single XZ plane cuts the arm and its mounts
together — which is the right answer and still leaves a reviewing agent to
notice, unaided, that `cmp_swing_arm` was the object missed. The cross is
already paid for: `write_review` assembles `section` (with per-object statuses)
and `motion` (component travel from the rollout trace) into one file, so naming
the missed objects and marking the ones the rollout shows moving is one helper
and no new measurement. It removes a reading rule from the negative knowledge
rather than adding a search [rec: rising-rain-0117] [rec: copper-canyon-0231]
[rec: square-bay-3436].

**Why not something else.** The four seeded criteria all sit at `working` and
their remaining gaps are either a human's tick, or forbidden by this run's
constraints (a real GUI-attached run, a real remote dispatch), or parked in
`## Later criteria` (the parts library, mg-legs, the fleet, control quality).
Inherited-tree reduction is standing work on the long rung by the charter's own
words. Usage argues the same ranking: five-hour is at 80% and codex seven-day at
94%, so one live walk plus two token-free units is what the rung can spend.

## Method

Fold into `young-crane-9546` (all three units, re-ranked) and
`strong-birch-7412` (its unit 1 landed; restate what each criterion still needs
for a human to tick it). `late-valley-7350` holds. Rails carried forward
unchanged in the short node's negative knowledge, plus three new ones: unit 1 is
from-nothing or it is not unit 1; unit 3 is a cross of two blocks the review
already writes, not multi-plane sectioning and not a claim about clearance or
fit; and no unit may be reported as provider-blocked without first probing a
named model.

## Result

Predicted: unit 1 either produces a third mechanism's clean walk on this machine
— from a sentence, one invocation, with the evening's three fixes exercised on
geometry none of them saw — or it fails and names the next unit, which is the
same value at lower cost. Units 2 and 3 are token-free and land whether or not
the provider answers, so an iteration that attempts unit 1 and is refused still
ships code. The frontier will not move: all four seeded criteria are `working`
and the tick is the human's.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 178e5091b2eb9ec6fa98c2f6feb16fedd67db8cd

## State Impact

- target: plan/young-crane-9546 — re-rank onto the from-nothing uninterrupted walk, the project-recorded model, and the section's missed-object naming
- target: plan/strong-birch-7412 — unit 1 landed; restate what each seeded criterion still needs for a human tick
