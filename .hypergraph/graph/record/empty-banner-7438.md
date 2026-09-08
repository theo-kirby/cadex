---
node_id: 83703f32-34d3-5fdf-ad71-206acee3533b
slug: empty-banner-7438
title: A pan-tilt walk runs clean and catches the clearance surface lying about catalog parts
created_at: '2026-09-08T01:51:27+00:00'
parents:
- salty-nest-8235
summary: ''
---
## What

Ran the documented headless lifecycle entry point once, from a design prompt, on a
mechanism topology the walk had never carried: a **two-axis pan-tilt head — two
revolute joints in series on orthogonal axes, driven by two catalog TowerPro MG90S
servos.** Fresh scratch project outside the checkout, ordinary installed engine by
explicit `--engine`, local toy CPU training. **No repository source changed; the tree
is unchanged and clean.**

**All four legs exit 0. No leg needed a person and no leg needed a guess.**

| leg | exit | seconds |
|---|---|---|
| design (1 prompt turn) | 0 | 347.25 |
| train (1 it x 4 envs, CPU) | 0 | 17.49 |
| declare (the digest edit) | 0 | 1.54 |
| rollout | 0 | 1.74 |

Whole walk **371.70 s wall, 1.419 GB peak process-tree RSS**, inside the charter's
850 s and 2.9 GB guards, no cutoff. `walk_seconds` 371.45.

**But the review leg is wrong on catalog parts, and this walk is the first to show
it.** `clearance` reports three intersecting pairs; four independent surfaces built
from the same accepted revision say two of the three cannot be true, and the third
is out by 10x. That is a defect in the review surface (`damp-moon-9297`), found by
using it — not a walk failure. It is named below and is the next unit.

## Why

The plan's short rung, rank 1 (`young-crane-9546`): run the documented walk on an
unwalked topology, record per leg whether it was clean, needed a guess or needed a
person. It serves missions 1, 2 and 6 and three frontier criteria at once —
`crisp-reef-5607` (the walk exists and is tested headlessly), `swift-dusk-2951` (the
walk holds on another mechanism, same entry point, no mechanism-specific code) and
`damp-moon-9297` (the agent can see its work without a screen).

**Assumption written down, nobody to ask.** The overseer's message for this dispatch
asked for "Three modes, one shape" and named its "two remaining legs": the remote
handoff scripted-not-executed, and the GUI-attached mode doc. **Both legs are already
closed and recorded** — the remote handoff is ADR-200 (`green-delta-7130`, commit
5143099c) with whole-walk local/remote artifact parity re-verified in
`gilded-basin-9946`, and the GUI-attached doc is ADR-201 (`red-comet-9710`), corrected
by ADR-204 (`still-badger-2386`). `witty-spark-2613` records the criterion as met
under its stated limits. The same message said four records were unreconciled where
STATE.md shows one, so it appears to be written from a stale read. Writing a third
document for a shipped leg would add without removing and would close no criterion,
so I took the planner's rank 1 instead, which the same message also endorses in its
closing sentence (finish and evidence the second-mechanism walk rather than restart
it). If the overseer wants the doc pass regardless, it is one cheap unit and the
evidence above says what it would be duplicating.

## Method

Prerequisites already present; nothing built and no GUI launched. Installed bundle
identity re-checked against `strong-raven-3067` before use and unchanged: manifest
`c23a9d1826ca8816...`, binary `ef31342ea2803e4c...`, library API
`bf469234aa874519...`. `CADEX_ENGINE_ROOT`, `MESH_CADEX_ENGINE`, `MESH_FREECADCMD`,
`MESH_CADEXD_MODULE` and `PYTHONPATH` unset for the command; the engine chosen by
explicit `--engine` at the installed manifest directory. Scratch project created
outside the parent checkout so the CLI owns its own git repository.

One command: `cadex walk --engine <bundle> --project <scratch> --out
<scratch>/runs/baseline --prompt "<pan-tilt head, two MG90S, position servos with
MG90S torque and speed limits, a joint-angle sensor per axis, a task driving both
joints to pan 0.4 rad / tilt -0.3 rad with a small effort cost>" --trainer-python
<repo>/.venv/bin/python --iterations 1 --envs 4 --seed 0 --timeout 600 --json`, with
`JAX_PLATFORMS=cpu`, wrapped in the existing process-tree monitor (0.2 s RSS
sampling, SIGTERM at 2.9 GB or 850 s, five-second SIGKILL fallback). Model
`claude-fable-5` (the walk's default); the design turn is the only leg that spends
tokens.

Inspected the review outputs rather than trusting the exit code: extracted and
**looked at all four embedded view PNGs**, read the section summary contours, the
inventory and clearance markdown, the MJCF body inertials and the exported STL
vertex bounds.

## Result

**The mechanism is new to the walk and the design turn built it unaided.** The script
declares two `fixed` servo mounts and two `revolute` joints (`joint_pan` about Z at
28 mm, `joint_tilt` about Y at 64 mm), two `position` actuators carrying the MG90S
stall torque (176.5 N.mm) with damping set from the 600 deg/s free speed,
`joint_dynamics` on both, joint-angle/velocity and actuator-force observations, a
task with an `exp` closeness bonus, a quadratic tracking cost and an effort cost,
+-10% head-mass randomisation and termination within 2 deg of either joint limit.
Prior walked topologies were one revolute (hinged arm) and one prismatic (linear
carriage); this is the first serial two-DOF chain and the first walk whose mechanism
uses catalog parts. The agent wrote three of its own `DECISION:` lines into the
project's `DECISIONS.md`.

Training: CPU, 1 iteration, 4 envs, seed 0, 4,738 parameters, wall 2.158 s,
reward/step -31.594, **witness error 4.028e-09** against a 1e-4 tolerance, policy
sha256 `923c0386dd...`, task sha256 `a968b67c90...`. Rollout `total_reward`
-2380.357 (closeness +2.826, tracking cost -2383.181, effort cost -0.0014). These are
toy execution measurements, not learned-control quality — one iteration cannot track.

Project: **five commits, clean status**, `ARCHITECTURE.md`, `DECISIONS.md`,
`PROGRESS.md`, `docs/inventory.md`, `docs/clearance.md`, `runs/baseline/review.json`,
four view SVGs, the XZ section at Y = 3.125 mm and its summary, `assets/task.cxpolicy`.

**Views inspected, all four correct.** Iso, front, right and top all read as a
pan-tilt head: blue base plate, green MG90S standing on it as the pan servo, blue
U-shaped yoke on the pan shaft, purple MG90S lying across the yoke arms as the tilt
servo, orange head plate with a camera cube. Section: five objects, all `status: ok`,
closed contours, base X -25..25 / Z -4..0, servo_pan Z -0.4..28, yoke Z 31..34,
servo_tilt Z 57.9..70.1, head Z 49..79. Inventory: **5 components, 2 catalogued,
`servo/mg90s` x2**, three uncatalogued hand-modelled outputs named — the first walk
whose inventory carries catalog ids at all (the hinged arm's was zero).

**The defect. `clearance` measures `lib.*`-placed bodies in the wrong frame.** It
reports 10 pairs checked, 0 unknown, 3 offending:

| pair | clearance says | four other surfaces say |
|---|---|---|
| servo_pan / servo_tilt | intersection, common volume **8240.943 mm3** | disjoint: Z -0.4..32 vs 57.9..70.1 |
| base / servo_tilt | intersection, 1112.640 mm3 | disjoint: Z -4..0 vs 57.9..70.1 |
| base / servo_pan | intersection, 1112.640 mm3 | real, but a 0.4 mm sink = ~111.3 mm3 |

8240.943 mm3 is **exactly** the inventory volume of one servo, i.e. total
containment; 1112.640 = 22.8 x 12.2 x **4.0**, the servo body footprint over the base
plate's whole thickness rather than over the 0.4 mm they actually share — ten times
the true figure. Both are what you get if the two `lib.servo` bodies are measured
**at the canonical origin frame, before `_place`**. The four surfaces that disagree
are independent of each other and of the clearance path: the render summary bounds,
the section contours, the MJCF `inertial pos` (servo_pan COM z = 0.0141 m, servo_tilt
z = 0.064 m, y = 0.0061 m — the physics is placed correctly), and the **exported STL
vertex bounds**, the printable artifact: servo_pan Z -0.4..32.0, servo_tilt Z
57.9..70.1. The hand-modelled parts (base, yoke, head) measure correctly — base/yoke
31.0 mm, base/head 49.0 mm — because they are authored directly in world coordinates
and their component placements are identity. Only bodies moved by
`lib.*` -> `_place` -> `part.transform` (`cadex_library_api.py:448`) are wrong, which
is why no earlier walk saw it.

Why no test caught it: `_measure_clearance` (`cadex_assembly_worker.py:5314`) reads
`components[name].Shape`, and `cadex_tests/test_clearance_scope.py` drives it with
`SimpleNamespace` stubs. **No real-kernel clearance test uses a transformed or
`lib.*`-placed component.** Nothing here is a walk failure: an offending pair is a
finding by design, so the walk correctly exits 0 — it is the *number* that is false,
which is worse than an error because it reads as a verdict.

Not claimed: the clearance frame diagnosis is a hypothesis fitted to two exact
arithmetic coincidences and four agreeing surfaces, not a read of the failing line.
Sections are tessellated cuts, clearance is initial-pose and not swept, and the
render is opaque standard tessellation. No engine, CLI or shell suite was rerun,
because no repository source changed. No remote dispatch, no GUI launch, no build.

Next: **fix the clearance frame for `lib.*`-placed components, with a real-kernel
regression that fails on today's source** — one `part.transform`ed component and one
authored-in-place component in one assembly, asserting the transformed pair's
distance and common volume against the placed geometry. It is the only leg this run
named, it sits on `damp-moon-9297` (the review criterion the lifecycle walk depends
on), and it is the plan's rank 2 conditional. Until it lands, no clearance number for
an assembly containing catalog parts should be believed, and `damp-moon-9297` cannot
be ticked. `crisp-reef-5607` and `swift-dusk-2951` gain a third clean mechanism each
and need nothing more from this unit. The unreconciled tail becomes two nodes; the
maintainer owns that, not this iteration.
Dispatch closed: 1 unit — a clean four-leg pan-tilt walk on an unwalked two-revolute topology, with the review leg's clearance numbers proved wrong for catalog-placed parts.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: a31cb8283eb19e043db578ddc32927fc10f0734c

## State Impact

- target: crisp-reef-5607 — A third clean prompt walk on the installed bundle, first serial two-revolute topology: four legs exit 0, 371.70 s, 1.419 GB peak, no leg needed a person or a guess.
- target: swift-dusk-2951 — The same entry point took a third mechanism (pan-tilt head, two catalog MG90S) through design/train/declare/rollout/review with no mechanism-specific code change; PROGRESS numbers comparable.
- target: damp-moon-9297 — Render, section and inventory verified correct against exported STL bounds and MJCF inertials, and inventory carries catalog ids for the first time; but clearance measures lib.*-placed bodies in the canonical origin frame, giving two false intersections and one 10x-inflated volume, uncovered by real-kernel tests.
