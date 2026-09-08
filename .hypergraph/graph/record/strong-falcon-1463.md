---
node_id: a18fedca-4fee-509b-ae0c-a83c8131c6da
slug: strong-falcon-1463
title: 'Bet: give the walk''s review motion coverage over the rollout trace'
created_at: '2026-09-08T16:55:20+00:00'
parents:
- candid-otter-2615
summary: ''
---
## What

One new direction for the short rung, and the first that attacks the review
step's own largest stated hole: **give the walk's review motion coverage** by
screening the exported rollout trace for pairs that come together while the
mechanism moves, computed in the LGPL CLI zone from data both halves already
produce. Two ranked units — the screen and the command that writes it, then the
walk's review wiring plus one model-free rehearsal on the repo-owned toy. The
measured named-inventory retention survives unchanged as the third and last
unit. Nothing is retired; no charter box is claimed.

## Why

**The frontier is dry of anything the planner may target.** All four seeded
criteria stand `working` with evidence on this machine — the walk headless
twice [rec: wandering-jasper-6102] [rec: rare-cliff-9595], iterate with numbers
[rec: mellow-quartz-8093], three modes audited and now offline-checkable
[rec: early-quill-3654] [rec: candid-otter-2615], four review eyes inspected
[rec: soft-crane-2369]. The three open frontier nodes are the charter's
standing reduction work and two `## Later criteria` the charter reserves to a
human edit. So this pass takes its one permitted direction, from three
candidates.

**And the loop is circling.** Eleven iterations with the frontier unmoved, five
of them on inventory-report prose and test fixtures, is what the overseer's
`looping` verdict at #16 names. Leading the rung with a fourth inventory unit
would continue it. The rung needs a unit that adds a capability the review step
does not have.

**The hole is stated in the product's own output.** Every clearance report the
walk writes carries the line "Initial solved pose only; this is not a
swept-motion check" (`cli/cadex_cli/clearance.py:46`), and `review.json` records
`"scope": "initial solved pose"` (`cli/cadex_cli/__main__.py:1477`). Nearly every
record of this run repeats it in its "not claimed" paragraph — swept-motion
safety is the single most-cited limit on the mission-6 eyes, and no unit has
ever gone at it. Mission 6's own words: the loop is only as good as its review
step.

**Why the engine's existing swept check cannot simply be turned on.**
`assembly.simulation(clearance=[(a, b)], clearance_mm=…)` is the swept-volume
check (ADR-130, ADR-242, `cadex_assembly_api.py:1403`), capped at 32 pairs, and
it runs over the **kinematic OndselSolver trace**. The walk's motion is
`assembly.rollout` — a MuJoCo dynamics trace (`examples/lifecycle/hinged-arm/script.py:42`)
with no clearance surface on it at all. That is why ADR-242's path is exercised
only by its regression [rec: morning-summit-7848]. Reaching it from the walk
means either an engine change in `CadexDynamics.py` (engine zone, payload gate,
its own unit) or auto-declaring pairs the author did not declare — and a breach
there **raises** (`cadex_assembly_worker.py:3248`), which would turn a design
finding into a walk-killing refusal after training has already been spent. This
rung's own negative knowledge already ruled that trade the other way: report,
do not refuse.

**What is available offline, in the CLI zone, today.** The rollout trace carries
`component_placements` for every frame (`CadexDynamics.py:8790`), and the render
carries each component's accepted `placement` and world `bounds_mm`
(`cli/cadex_cli/render.py:132`). A rigid transform of an axis-aligned box's eight
corners, re-bounded, contains the body at that frame; two disjoint boxes at a
frame **prove** those parts are apart there. That is a broad-phase screen, and
it is the same second-path discipline `bounds_agreement` already uses — kernel
numbers on one side, placed tessellation on the other. It costs no engine diff,
no protocol op, no `shell/` line, and no model turn.

**Honesty conditions, written into the deliverable rather than left to the
reader.** The screen proves separation and never proves contact: an overlap is
"not proven clear", to be inspected, and must never be reported as a collision.
It is sampled at the trace's frames, so motion between frames is uncovered. Its
inputs are f32 tessellation bounds, so it inherits `BOUNDS_TOLERANCE_MM`-scale
slack. And it must not refuse — the walk keeps reporting.

**The two rejected candidates.** (a) Extend `_clearance_at_frame` into the
dynamics rollout: the right long-run answer and a real kernel measurement, but
engine zone plus the packaged gate, and it lands the refusal semantics this rung
has already declined; it belongs on the long rung as the successor this screen
would justify. (b) A third mechanism or a catalog-part walk: two mechanisms have
completed here and five on nt3 [rec: rare-cliff-9595] [rec: proud-beacon-8002],
so it spends six to eighteen minutes and a model turn to re-evidence a `working`
criterion. Remote dispatch and GUI attachment are not candidates at all — the
run's standing constraints bar both.

## Method

Short becomes three ranked units: (1) the motion screen as a function plus the
command that writes it, with a real-engine regression; (2) the walk's review and
`PROGRESS.md` row carrying it, rehearsed model-free on the repo-owned toy with
the added wall-clock measured; (3) the already-measured named-inventory
retention [rec: soft-crane-2369], unchanged and last. Medium records the
selection, the two rejections and the budget. Long gains the engine-side kernel
successor as a direction that this screen would have to justify first, and keeps
every parked rung parked.

## Result

The bet is right if the walk's review, on an ordinary toy walk, either names a
pair and the frame and time at which its boxes met, or reports the whole trace
separated — with no engine diff and inside the rehearsal's existing time and
memory ceilings. It is wrong, and retires to negative knowledge rather than
expanding, if the exported trace's placements cannot be joined to the render's
components, or if the screen is vacuous on these mechanisms because every pair's
boxes overlap at every frame. Unit 1 measures that before unit 2 wires anything.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: a354f46f236fca4253b1d340b1689b240929241f

## State Impact

- target: plan/young-crane-9546 — the short rung leads with the motion clearance screen and its walk wiring; the measured named-inventory retention drops to third and last
- target: plan/strong-birch-7412 — the selected direction becomes review motion coverage; inventory fidelity demotes to its tail, with the two rejected candidates and the budget recorded
- target: plan/late-valley-7350 — the engine-side kernel swept check over the dynamics rollout is recorded as the successor direction this screen must justify first
