---
node_id: d603a775-b26f-5fde-9348-70b22c8190c0
slug: western-grotto-7499
title: 'Bet: walk the third mechanism first, and make the walk''s row comparable at all'
created_at: '2026-09-08T18:22:06+00:00'
parents:
- falling-willow-7995
summary: ''
---
## What

Re-rank the short rung. Unit 1 landed (ADR-259, `19549da9`) and an
out-of-plan overseer-directed unit landed on top of it (ADR-260,
`9e888610`), so the rung is re-ordered rather than replaced:

1. **The fresh prompt walk on a third mechanism** is promoted from third to
   **first**. It was ranked behind the two reporting units only because it
   needed them to be more than a fourth pass at the same review shape; unit 1
   supplied the travel eye and the rung's precondition is met.
2. **Carrying travel into the iterate comparison** drops to second, and its
   scope is corrected by a measurement taken in this pass: the walk's
   `PROGRESS.md` row does not go through the comparison machinery **at all**,
   so this is not "add a label to `COMPARED_NUMBERS`".
3. **A model-free `--set` iterate walk on the third mechanism's own project**
   is added third: it costs no tokens, and it is the first row that would
   actually carry a travel delta on a mechanism neither example supplied.

No new direction. No gap node retired, blocked or superseded. No `## Later
criteria` item targeted.

## Why

**The measured correction, and it is the useful half of this pass.**
`_record_progress` in `cli/cadex_cli/__main__.py:1735` branches on the
command. The `command == "walk"` branch builds its numbers cell from
clearance + `_motion_cell` + `_documentation_cell` and **never passes
`previous=previous_numbers(...)`**; only the non-walk branch calls
`progress_numbers(..., previous=...)`. So no walk row has ever shown a delta
against the previous walk of the same project — not clearance, not
documentation, and not the motion figure that just landed. Separately,
`_motion_cell` spells its figures `motion 0 mm (swing), 178.8° (swing)`,
which `_NUMBER_RE` (`project_docs.py:413`, built from
`COMPARED_NUMBERS = ("total_reward", "reward/step")`) cannot parse: the
regex wants `<label> <number>`. The compared numbers live on the **train**
leg's row and the motion figure lives on the **walk** row, written by
different branches. Unit 2 therefore has three parts — a parseable spelling,
the labels in `COMPARED_NUMBERS`, and threading `previous` into the walk
branch — and an actor who reads the plan as written would have found this
after starting. Stating it here is cheaper than discovering it there.

**Why the walk goes first now.** The charter's short rung is explicit: "Run
the documented headless lifecycle entry point end to end, on this machine,
and record exactly which leg still needs a person or a guess... Do this
before anything else, every time the short rung is empty." The rung's own
reason for deferring it — that its review would carry nothing the previous
walks did not — expired when ADR-259 landed. The overseer hard-committed to
a fresh mechanism at #19 and the iteration after it spent itself on
second-mechanism *test* evidence instead [rec: falling-willow-7995], which
was the right call for that iteration and is not a substitute: two offline
regressions prove the dispatch has no mechanism-specific branch, and prove
nothing about whether a third mechanism walks. Seventeen iterations with the
frontier unmoved is not itself actionable — this rung structurally cannot
move it, and that is recorded — but it does say that another reporting-layer
unit is the wrong next thing when the product-level unit is unblocked and
affordable.

**Affordability, read from the loop signals.** 23 iterations, 6.7 h elapsed,
41.3 h left; Claude five-hour 61% and seven-day 65%. One design turn at ≤18
min fits with room, and it is cheaper to schedule while the seven-day figure
is at 65% than after two more units have run. If the provider refuses on
credit, the refusal is the record and unit 2 is the fallback — the order
degrades safely, which is the other reason to spend the model call first.

**What unit 3 adds that unit 2 does not.** Unit 2 makes the walk row
comparable; nothing in this repository then exercises it on a mechanism that
is not one of the two examples. A `--set` walk spends no tokens, reuses the
durable project unit 1 creates, and produces the first comparison row
carrying both channels on unseen geometry. It is the cheapest possible proof
that unit 2 works where it is meant to work.

## Method

Read `square-bay-3436` and `falling-willow-7995` in full; read
`witty-spark-2613` and `crisp-reef-5607`'s `## Current` to confirm nothing on
the charter's own short rung is left unserved — the remote handoff (ADR-200,
ADR-255), the GUI-attached mode doc (ADR-201, corrected by
`early-quill-3654`) and the domain-note convention (ADR-245, ADR-256) are all
delivered, so "run the walk" is the only charter short-rung item outstanding.
Then read `_record_progress`, `_motion_cell`, `COMPARED_NUMBERS`,
`_NUMBER_RE` and `previous_numbers` in the source to size unit 2, which is
where the branch finding came from.

Considered and rejected: promoting "Three modes, one shape" work into short.
Both unexercised limbs are unexercised by this run's standing constraints,
not by missing work, and `witty-spark-2613` says so in the criterion's own
wording. Also rejected: inventing a direction on the strength of the unmoved
frontier — `western-reef-4119` records that promotion is a human edit and an
empty frontier is not licence to open a campaign.

## Result

The short rung is re-ordered 3 → 1, 2 → 2, and gains a third model-free
unit. The medium rung records that its selected direction is half-landed and
that the remaining half is a comparison-plumbing unit rather than a
measurement one. Nothing else moves.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: c90ffc8699b7b2a5e770ae00eb4dec86ba664608

## State Impact

- target: plan/young-crane-9546 — re-rank 3→1, 2→2, add a third model-free --set iterate walk; correct unit 2's scope with the measured _record_progress branch finding
- target: plan/strong-birch-7412 — record the selected direction as half-landed and its remaining half as comparison plumbing, not measurement
