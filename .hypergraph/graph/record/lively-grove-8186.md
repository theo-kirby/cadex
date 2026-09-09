---
node_id: ca78cfc2-5c88-5793-8603-447d06e9d5db
slug: lively-grove-8186
title: 'Bet: measure the eyes against the motion the walk trained'
created_at: '2026-09-09T06:04:09+00:00'
parents:
- brisk-eagle-8550
summary: ''
---
## What

Short rank 1 is discharged and the rung re-ranks onto **the eyes measuring the
motion the walk actually trained**:

1. **Clearance over the poses the rollout visits**, promoted from rank 2 and
   re-scoped against what source says this pass. Not carried over unchanged: the
   previous pass's escape hatch ("if the rollout trace does not carry poses the
   kernel can be re-placed from") is **resolved in the affirmative** and re-pointed
   at the real open question, which is frame composition, not data.
2. **The section plane that cuts what moves** — this pass's one new direction, and
   the finding the section eye published about itself on `ot4-cart`.
3. **The scaffold-guide trim**, held at rank 3, unchanged in substance.

Medium re-ranks to say that all four seeded criteria now carry complete evidence
and that what is left on this run's frontier is the *depth* of the eyes, not the
coverage of the walk.

## Why

**Rank 1 of the previous pass landed.** `cadex walk --remote --detach` stops at a
`walk-pending.json` receipt that declares and stores nothing, and
`cadex walk --complete` collects the returned policy through a new `collect` leg
and runs the unchanged `declare`, `rollout` and review legs; six named refusals
guard a walk split in time. ADR-282, `00964ac8`, 719 insertions / 70 deletions,
CLI gate 301 passed [rec: brisk-eagle-8550]. `witty-spark-2613`'s own words
("`--detach` still does not travel through the walk") no longer describe the
tree, so the unit leaves dispatch. A fourth mechanism also completed the
unchanged entry point in the same window — `ot4-cart`, the first rig with a
**passive** joint, exit 0 in 1222.22 s, no code change of any kind
[rec: dry-falcon-5463].

**What both of those runs leave open is the same thing, and it is not coverage.**
Four mechanisms have now walked. Every leg works. The two findings the runs
produced about themselves are both about the *review* step, and both are about
motion:

- `ot4-mix55` reported `1 intersection: frame ∩ slider, 648.0 mm³` **at the
  initial solved pose**, then rolled 151 solved frames with 74.62° of crank
  rotation and 20.32 mm of coupler travel with clearance measured at none of
  them [rec: chilly-basin-7378].
- `ot4-cart`'s derived section chose XZ at −15.0 mm, cut 2 of 3 objects, and the
  object it missed was the pole carrying **all 35.75°** of the mechanism's
  rotation. The eye named it itself, in `section.missed_objects`, as
  `moved: true` [rec: dry-falcon-5463].

A green clearance block and an `ok` section are both, today, statements about one
pose. Mission 6 says the loop is only as good as its review step; these are the
two places where the review step is quietly narrower than a reader will take it
to be. They are also both **token-free**, which matters at a five-hour usage
signal of 92%.

**Source checked this pass, and it changes both units' shapes.**
`CadexInspection.py:1194` already writes `"pose": "initial solved pose (not swept
motion)"`, and `scope=clearance` **reads published measurements** rather than
computing anything — so rank 1 needs a *producer*, and "reuse the two helpers" as
the previous pass phrased it understates it. `_clearance_at_frame` reads
`components[name].Placement` live and composes it with the prepared local
placement, and its own docstring says it is called "inside the frame loop, while
`updateForFrame` has the placements live, because that is the only moment the
trace exists as geometry rather than as numbers." The rollout trace **is**
numbers — `component_placements` with `position_mm` and `rotation_xyzw` per
component per frame (`CadexDynamics.py:8964`) — and those are absolute world
poses [rec: solemn-journey-9731]. So the poses exist; the open question is
whether setting them onto the components composes the same way the solver's do,
which is precisely the class of defect ADR-241 and ADR-242 already fixed once.
That question has a cheap answer, and rank 1 must pay for it: **at the rollout's
first solved frame the new measurement must agree with the static clearance the
review already reports.**

For rank 2, the data is already in hand *before* the choice is made.
`derived_section` ranks candidates by `(available, objects_cut, -index)` — every
object weighted the same — and in the walk's review block
`review_from_outputs` computes `motion` at `cli/cadex_cli/__main__.py:1735`,
about twenty lines before `write_section` is called. The moving components are
known and simply not consulted. That is a small CLI-zone change to a ranking
term, not a new eye.

**Why the scaffold trim stays third and why no walk is ranked.** The trim is a
real 8,399-against-8,000 overrun that elides roughly 400 characters from the
middle of `## Training`; small, and third for that reason. A fresh walk is the
charter's standing unit "every time the short rung is empty" — short is not
empty, and a fifth run of a measured shape would spend a design turn's tokens to
re-measure it. The walk worth running next is the one these two units make
informative.

## Method

One planning pass, no code. Read `PLAN.md`, the two unfolded records
(`dry-falcon-5463`, `brisk-eagle-8550`), the three plan node bodies, and then the
source each ranked unit touches: `cli/cadex_cli/section.py`,
`cli/cadex_cli/walk.py`, `cli/cadex_cli/__main__.py`'s review block,
`src/Mod/cadex/CadexInspection.py` and `src/Mod/cadex/cadex_assembly_worker.py`'s
clearance helpers. Rewrote `## Current` on `short` and `medium`, added negative
knowledge for the discharged unit and for the two live units' boundaries, and
appended this bet to both nodes' provenance. `long` holds: nothing this pass
changes a bet, a parked rung or the standing work.

No charter edit, no state node, no record retirement, no criterion ticked.

## Result

`short`: rank 1 the rollout-pose clearance producer (engine zone, packaged gate,
report-never-refuse, with the first-frame agreement check as its own gate); rank
2 the motion-aware section ranking (CLI zone, this pass's one new direction);
rank 3 the scaffold trim. `medium`: eight items re-ranked so that the eyes'
depth leads and the walk's coverage is recorded as evidenced rather than pending.
`long`: unchanged.

The prediction this bet can be wrong about: that the rollout's world poses
compose onto the assembly's components the way the solver's do. If the
first-frame agreement check fails and the composition cannot be made to match
inside one unit, rank 1 becomes a **measurement record naming the mismatch** and
is dropped — not grown into a swept-volume kernel, a second clearance engine, a
new trace format or a new dependency.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: cf3e1b33ce3669ab2de19126381ba0b5b7f7c5b0

## State Impact

- target: plan/young-crane-9546 — discharge the landed detach unit; promote rollout-pose clearance to rank 1 with its escape hatch re-pointed at frame composition; add the motion-aware section ranking as this pass's one new direction; hold the scaffold trim at rank 3
- target: plan/strong-birch-7412 — re-rank so the eyes' depth leads: record --detach and the fourth mechanism as delivered evidence, and state that what remains on this run's frontier is the review step's depth rather than the walk's coverage
