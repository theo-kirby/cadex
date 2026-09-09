---
node_id: 62541e3f-d180-5c49-8e31-5fd442fe9baf
slug: solemn-journey-9731
title: 'Bet: the arm rotates and never moves — correct the travel report''s premises'
created_at: '2026-09-08T17:53:11+00:00'
parents:
- blue-quill-9477
summary: ''
---
## What

The direction stands and the premises under it do not. Before an actor builds
the `motion` travel block that leads the short rung, three of the four facts
that unit rests on are corrected against measurement taken this pass, and the
unit's reporting rule is changed as a result:

1. **A displacement-only travel figure reports `0.0 mm` for the repository's
   own first documented example.** The hinged arm's `swing` component holds
   position `[12, 0, 6]` for all 27 frames and rotates **178.83°**. Its travel,
   as the rung specified it, is exactly zero — indistinguishable from a dead
   rollout, which is the failure the whole direction exists to prevent.
2. **Frame 0 is not the identity.** The plan said it was, and read a "no
   composition needed" licence off that. Placements are absolute world poses:
   `swing` starts at `[12, 0, 6]`, `base` at the origin. Travel is a delta from
   frame 0, and the unit must say so rather than assume a normalised trace.
3. **Frame 0 is not a rollout frame.** It is `frame_kind: "input"` with
   `nominal_time_s: None`; the other 26 are `solver_output` over 0.0–1.0 s. A
   duration read off the trace's first frame is `None`, and a "frame count" of
   27 mixes one pre-solve pose into 26 solved ones.

So the unit's `PROGRESS.md` row carries **two** figures, millimetres and
degrees, and either names the largest mover under a rule that can rank a pure
rotation against a pure translation or declines to rank and names both. And
the two example projects `western-gate-9567` left behind are the regression
material: they are the moving-and-rotating pair the unit needs, reproducible in
13–15 s with no model call.

## Why

Two iterations passed since the last bet and neither touched the short rung's
unit 1; both were prose repairs. The rung is therefore unchanged in direction,
and restating it would be the fourth pass at the same sentence. What *is* new
is that `western-gate-9567` left two real rollout traces on this machine from
the documented example path, and they were never read for motion. Reading them
took one pass and falsified the unit's stated premises:

```
hinged-arm      swing   max_disp    0.0000 mm   max_rot  178.8334 deg
linear-carriage slide   max_disp 4739.3783 mm   max_rot    0.0000 deg
```

A revolute mechanism that works has zero position travel. A prismatic
mechanism that fails — the carriage free-falling 4.74 m in 1.0 s on an ideal
unlimited guide, which matches `crisp-reef-5607`'s recorded `z = -4699 mm at
1 s` — has the largest travel in the run. Ship the rung as written and the
review would have said `0.0 mm` about the arm and `4739 mm` about the fall:
both readings exactly inverted from what a person wants to know, from a report
whose entire purpose was to distinguish motion from stillness. That is worth a
planning pass to catch and would have been expensive to catch in review.

This also sharpens `sleepy-hollow-9498`'s own numbers rather than contradicting
them. It measured the ot4 prompt-walk swing rig at 1.094 mm with "no measurable
rotation" and the ot4 carriage at 103.298 mm. Those are different projects from
these examples, and the pairing is instructive: across four real traces on this
machine the two revolute rigs are the two with near-zero displacement. The
rotation channel is not an edge case to add for completeness — on half the
evidence it is the only channel carrying anything.

The claim boundary is unchanged and restated because it now has a sharper
counterexample: **travel is a fact about one rollout, never a score.** 4739 mm
of falling outranks 178.8° of working swing on any single-number ordering, so
no ordering is offered.

No new direction is proposed and none is retired; the selected direction is the
same one, with its premises corrected and its output rule fixed. Unit 3 is
unaffected and its justification is if anything stronger: `western-gate-9567`
ran *recipe* walks, which run no design turn, so no walk on this machine has
yet had the ADR-256 documentation eye read a real design turn's own `NOTE`
lines back. Budget supports the rung as it stands: 21 iterations, 6.2 h
elapsed, 41.8 h left, Claude seven-day 64%; two model-free code units and one
model-gated walk fit with room.

## Method

Read `build/lifecycle/{hinged-arm,linear-carriage}/runs/baseline/rollout/
assembly-simulation-trace.json` — the artifacts commit `f152798a` produced and
gitignored — and for each component computed, against frame 0, the maximum
Euclidean displacement, the per-axis range, and the maximum quaternion angle
`2·acos(|q0·q|)`. Also counted `frame_kind` values and read `nominal_time_s`
across the trace, and read both `review.json` files to confirm the review
carries no motion field today (`clearance`, `documentation`, `inventory`,
`legs`, `params`, `render`, `reward_totals`, `section`, `total_reward`,
`trace`, `training`, `walk_seconds`, `weights` — and nothing else).

Read-only; no file in the repository was modified by the measurement, and no
model call, engine build or test run was spent on it.

## Result

The short rung keeps its three units and its order. Unit 1 is rewritten: the
false identity premise is out, the two-figure rule is in, the `input`-frame and
`None`-duration handling is now a stated requirement rather than a discovery
left for the actor, and the two example projects are named as the regression
material with the all-identity case kept as the second regression. Unit 2
inherits the two-figure requirement so the iterate comparison cannot report a
rotating mechanism as motionless either. Unit 3 is unchanged.

The medium rung's item 1 loses the same false premise and gains the
measurement. One entry is added to negative knowledge on both rungs: a travel
report that reads only displacement is not a partial answer but a wrong one, on
half the traces this run has produced.

Nothing is retired, blocked or superseded, and no `## Later criteria` item is
targeted.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: c822e9b330c82280c87767e66d0cba83b62447fa

## State Impact

- target: plan/young-crane-9546 — rewrite unit 1: drop the false frame-0-identity premise, require both a millimetre and a degree figure in the PROGRESS row, state the input-frame and None-duration handling, and name the two example traces as regression material; unit 2 inherits the two-figure rule
- target: plan/strong-birch-7412 — correct item 1's frame-0-identity premise and record the hinged-arm 0.0 mm / 178.83 deg and carriage 4739.38 mm / 0.0 deg measurement as the reason the report needs two channels
