---
node_id: b35e3bd1-3d13-5a43-bc3d-a706cdfdf518
slug: sleepy-hollow-9498
title: 'Bet: retire the motion screen on measurement and report the rollout''s travel'
created_at: '2026-09-08T17:24:37+00:00'
parents:
- chilly-glacier-9294
summary: ''
---
## What

Retire the rollout **motion-clearance screen** unbuilt, on a measurement taken
this pass, and put the rung's iteration into the thing that measurement found
instead: **report the rollout's actual travel in the walk's review**.

The screen's own stop condition — written into the previous bet — was "if the
trace's placements cannot be joined to the render's components, or if every
pair overlaps at every frame on the toy mechanisms, record that and stop". The
join holds. The overlap condition is met. So the direction stops here rather
than after two iterations of code.

Short becomes, ranked: (1) a `motion` block in `review.json` and a travel
figure in the `PROGRESS.md` row, computed from the trace the walk already
locates; (2) that figure carried into the iterate comparison beside
`total_reward`; (3) one fresh prompt walk on a third mechanism, taken **after**
both new eyes exist, so it is the first walk whose review has a shape no prior
walk had. The inventory-retention tail is dropped, not deferred.

## Why

**The join premise holds, and I checked it rather than assuming it.** On
`~/cadex-projects/ot4-swing2`, the baseline rollout trace's per-frame
`component_placements` keys are exactly the keys of the render summary's
`objects` map (`cmp_base_plate`, `cmp_servo`, `cmp_swing_arm`, …), and the
render carries each object's 4×4 `placement` and world `bounds_mm`. Frame 0 is
the identity for every component, so the frame placements are deltas against
the accepted pose — the composition the screen wanted. Nothing about the data
shape was wrong.

**The screen would say nothing worth reading.** Two facts, both measured:

- *Assemblies are made of parts that touch.* On the swing rig's ten
  components, **22 of 45 pairs already overlap in world AABB at the accepted
  pose** — every bolt in its plate, both nuts on their bolts, the servo in the
  retainer, the arm on its pinch bolt, and all nine pairs against the base
  plate, whose AABB is the whole 100×77×90 mm envelope. A bounding-box screen
  can only ever return `separated` or `not proven clear`; for those 22 pairs it
  returns `not proven clear` at every frame no matter what the policy does.
  Those are precisely the pairs a person would ask about.
- *The remaining 23 pairs are the ones nobody worries about*, and the motion is
  too small to change their verdict: over 152 frames the swing rollout moves
  three components by **1.094 mm** and rotates none of them measurably. The
  carriage moves further — **103.298 mm** on the slide — and its single pair
  still overlaps throughout, because the carriage rides a column that lives
  inside the base's AABB by construction.

So the screen's positive verdict is available only where it is uninteresting,
and unavailable everywhere it would matter. That is a property of axis-aligned
boxes over jointed assemblies, not of toy scale or of these two mechanisms, and
no threshold fixes it. The kernel-accurate successor (`_clearance_at_frame`
over the dynamics rollout) stays on the long rung, where the previous bet put
it; what changes is that the box screen is no longer its cheap stand-in,
because a stand-in that cannot speak is not cheap, it is free and worthless.

**What the measurement found instead is a real hole in the review step.** The
carriage's baseline rollout travels 103.298 mm and its iterate travels
103.719 mm, while `total_reward` fell 3.296298 → 2.760187. The walk reported
the reward drop and said nothing about the travel. The swing rig's rollout
moves 1.094 mm — effectively a static mechanism — and its review reads exactly
like the carriage's: four renders at the initial pose, a section at the initial
pose, an inventory, an initial-pose clearance count, a verified rollout and a
reward. **Nothing in the review step distinguishes a mechanism that moved from
one that did not.** Mission 6 says the loop is only as good as its review step,
and this is the cheapest gap in it: the number is already in the file the walk
already opens, it needs no engine, protocol, payload or `shell/` change, and it
is one iteration in the LGPL CLI zone.

It also gives the iterate comparison a second axis. "Reward fell and travel was
unchanged" and "reward fell and the thing stopped moving" are different
findings, and today the walk cannot tell them apart.

**On the overseer's steer.** The overseer's #19 verdict hard-commits the next
unit to a fresh mechanism walk, on the ground that the frontier has been
unmoved for thirteen iterations. The frontier metric cannot move on this rung:
all four seeded criteria are `working` in the state projection, the three open
frontier nodes are standing work or parked under `## Later criteria`, and the
charter reserves promotion to a human edit. A bare third mechanism walk is
re-evidence — `swift-dusk-2951` already carries two mechanisms on this machine
with comparable rows. So the steer is honoured with its point intact rather
than declined: the walk stays on the rung, ranked third, **after** the travel
report and the iterate carry, so that it is the first walk whose review reads
back both the ADR-256 documentation eye and a travel figure. That walk earns
its model turn; a fourth pass at the same review shape would not.

**On the inventory tail.** It is dropped. Five iterations went to inventory
report prose and fixtures, the overseer called that `looping` at #16, the
measured boundary is already documented in `docs/CLI.md`, in the project
scaffold and as negative knowledge on `damp-moon-9297`, and the original
reports survive in each project's own Git. Keeping a sixth pass on the rung
because it is small is how a rung stops being true. Removing it is the
charter's philosophy applied to the plan.

**One correction to a record's own claim.** `eager-lake-5745` states that "no
walk has yet produced a domain note from a real design turn's closing text on
this machine (every note in evidence was placed by hand or by a unit test)".
That is false: `~/cadex-projects/ot4-carriage/docs/actuators.md` and
`docs/sensors.md`, and the same two files in `ot4-swing2` and `ot4-swing`, were
each committed by a `cadex prompt:` commit — the design turn's own closing
text, on this machine, three times. The write half of ADR-245's convention is
exercised; only the ADR-256 read-back eye has never run on a real prompt walk.
Recording this so no iteration is spent re-proving the write half.

## Method

Planner-side measurement only; no product code was written and no state node
touched. Read `runs/baseline/rollout/assembly-simulation-trace.json` and
`review/render/<revision>/summary.json` in `~/cadex-projects/ot4-swing2` and
`~/cadex-projects/ot4-carriage` with throwaway `python3 -c` reads: key
agreement between the trace's `component_placements` and the render's
`objects`; per-component position range and quaternion range across every
frame; and pairwise world-AABB overlap at the accepted pose over all 45 swing
pairs. Scratch deleted; nothing written into either project.

One decision record, two plan impacts: `young-crane-9546` re-ranked onto the
travel report, the iterate carry and the deferred walk, with the screen units
and the inventory tail removed; `strong-birch-7412` re-scoped from the screen
to the travel report, with the screen recorded as a direction retired on
measurement rather than a direction still open.

## Result

The plan is one direction shorter and one direction truer. No charter gap is
retired, blocked or superseded by this pass; no `## Later criteria` item is
targeted; the charter, the record graph, the state graph and `STATE.md` are
untouched.

Budget read from the loop signals rather than a clock: 19 iterations, 5.7 h
elapsed, 42.3 h left, Claude seven-day 63%, Codex seven-day 76%. Two model-free
units and one model-gated walk fit with room; the two iterations the screen
would have taken are returned to the run.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 1db6c9c918effa6647607c1787dd02c98c6cc58d

## State Impact

- target: plan/young-crane-9546 — re-rank onto the rollout travel report, the iterate carry and a deferred third-mechanism walk; drop the motion-screen units and the inventory tail
- target: plan/strong-birch-7412 — replace the motion-screen direction with the travel report; record the screen as retired on measurement
