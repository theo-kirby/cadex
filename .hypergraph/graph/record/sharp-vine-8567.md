---
node_id: cd43a588-43f3-59a2-907c-7aa2a70208d7
slug: sharp-vine-8567
title: 'Bet: shrink the guide that evicts its own training contract, then re-run the fresh walk'
created_at: '2026-09-09T03:39:28+00:00'
parents:
- golden-dune-8756
summary: ''
---
## What

Rank the short horizon onto two units, in this order.

**Unit 1 — shrink the scaffold guide back under the prompt budget, and spend
part of what is freed on the trainer's collision-geometry limit (mission 2,
offline).** `_ARCHITECTURE_TEMPLATE` in `cli/cadex_cli/project_docs.py`
measures **8,397 characters against `PROMPT_DOC_LIMIT = 8_000`**. ADR-279
bounded the file from both ends, half the budget each, so a project's own
paragraphs reach the prompt again — but the price is that the guide's own
middle, from roughly character 4,000 onward, is the omitted span on any
project that has written anything. `## Training` starts at 1,397 and ends at
6,871: more than half of the walk's training contract is already invisible to
every design turn. Cut the guide under 8,000 by removing redundancy, not
contract, and in the same unit add the one constraint the last walk paid
1,136 seconds to discover: MJX builds only some collision geom pairs, so
prefer box, capsule or sphere collision geometry, treat a cylinder as a valid
MuJoCo geom that may be an untrainable MJX one, and mark a decorative geom
contact-free. State it generally, not as a slider-crank special case. Pin
both facts with tests — the rendered scaffold under the budget, and the
constraint surviving into prompt context — then the CLI gate, an ADR and the
ROADMAP line. No engine change and no `mjx` import anywhere.

**Unit 2 — then re-run the fresh mixed-joint walk, same prompt, new empty
project.** Not a prompt rewritten to dodge the cylinder: the question unit 1
poses is whether the guide alone changes what an unaided design turn authors,
and a hand-steered prompt cannot answer it.

The one new direction this pass, on the medium rung: **a mechanical,
`mjx`-free check for unsupported collision geom pairs at MJCF export**, so a
design turn sees the problem inside its own leg instead of nineteen minutes
later. Promoted only if unit 2 shows prose was not enough.

## Why

Charter criterion **The walk exists and is tested headlessly**, and mission
item 2 behind it. `golden-dune-8756` moved the evidence for the first time in
this run's fresh-walk attempts: the design leg **passed** — a four-body
closed-loop slider-crank, mobility 1, 0.0015 mm worst closure residual, servo
unsaturated, project ADRs and three domain notes landed — and `train` died in
2.27 s on `mjx.put_model` raising `NotImplementedError` for the
`(mjGEOM_CYLINDER, mjGEOM_BOX)` pair. The geometry half of the criterion is
evidenced; the training half is not, and the named cause is one design
decision made without the constraint in view.

That record wrote the constraint into `docs/CLI.md` §2. No design turn reads
`docs/CLI.md`. The document a design turn does read on every visit is the
project's `ARCHITECTURE.md`, and its `## Training` section is where every
other trainer constraint already lives — so that is where this one belongs,
and unit 1 is the shortest path from the measured failure to a different
outcome.

Measuring where to put it turned up the larger defect. ADR-279 fixed a real
regression — the guide had grown past the budget and evicted every project's
own architecture from every prompt — by keeping both ends. It did not shrink
the guide, so the eviction moved rather than ended: it is now the guide's own
middle that never arrives. Adding a sentence without cutting would land it in
the dropped span and change nothing, which is why the trim is the unit and
the constraint rides along. This is also the charter's philosophy at its most
literal: remove more than we add, in the one file where every added sentence
costs a sentence someone else needed.

Unit 2 stays a walk because the charter's short rung says to run the entry
point end to end whenever the rung empties, and because the criterion is a
claim about a run, not about a diff. It goes second, not first, because the
last run already told us what it would hit. Budget supports one: the run has
32 hours left, the last walk cost 1,138 s and 730 MB peak tree RSS with no
watchdog intervention, and claude's seven-day usage is at 77% while codex is
at 99% — which argues for spending the offline unit first and the walk
deliberately, not for skipping either.

The mechanical check is deliberately medium and deliberately conditional.
Prose in the guide is reversible and costs one iteration; a geom-pair table
in the export path is a standing claim about a trainer the engine may not
import (ADR-084 bars `jax` and `mjx` under `src/Mod/cadex` and in any
payload), so it is worth building only if the cheap fix demonstrably fails.

## Method

One decision record, folded into `short` (`young-crane-9546`) and `medium`
(`strong-birch-7412`). The long rung is unchanged and untouched. No charter
gap is retired, no checkbox moves, no state node is written: the walk
criterion stays open on the evidence in `golden-dune-8756`, and the four
criteria the projection already carries as working keep their evidence.

Measurements taken this pass, from the checkout at `44049c6e`:
`len(_ARCHITECTURE_TEMPLATE) == 8397`, `PROMPT_DOC_LIMIT == 8000`,
`## Training` spanning characters 1,397 to 6,871 of the unformatted template.
The actor should confirm these against the rendered scaffold, since the
template's `{name}`/`{docs}`/`{progress}` placeholders substitute.

## Result

The short rung leads with an offline guide unit whose defect is measured
rather than guessed, followed by the walk that tests it. The medium rung
carries one new direction, fenced and conditional, and keeps the detached
handoff continuation behind its already-landed receipt.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 44049c6eab1097fb20b2a5d5e3cdece1d8e92190

## State Impact

- target: plan/young-crane-9546 — re-rank short onto the scaffold-guide trim carrying the MJX collision constraint, then the fresh mixed-joint walk re-run
- target: plan/strong-birch-7412 — refresh medium: fresh-walk coverage now blocked at train not design, and add one new conditional direction, an mjx-free unsupported-geom-pair check at MJCF export
