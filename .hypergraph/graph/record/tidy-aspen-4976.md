---
node_id: 9d9aafe1-b08f-5536-8c2c-62e491bb560f
slug: tidy-aspen-4976
title: 'Holistic architecture review: panel system diagnosis and breadth gaps'
created_at: '2026-10-10T10:55:04+00:00'
parents:
- small-brook-2395
summary: ''
---
## What

A holistic architectural review of Cadex, written to `docs/ARCHITECTURE-REVIEW.md`. It covers four things:

- the whole architecture, measured;
- a deep dive on the panel/shell system (`lib.panel`, `lib.housing`, `fit.shells`, the creature panel rules);
- what non-creature machines need: 3D printers, CNC, mowers, tractors, excavators, tracked vehicles, sheet metal and extrusion, enclosures;
- 14 recommendations, ranked by impact over effort, with a removal list.

No code was changed.

## Why

The owner asked for a step back after many fast changes. They named two concerns: the panel system is "really just not there", and Cadex must handle far more varied machines.

## Method

- **Line counts and AST import graph** over `src/Mod/cadex/*.py` (55 files, 80,255 lines) and `cli/cadex_cli/*.py` (37 files, 21,186 lines) at `587ffd43`.
- **Duplication**: AST spans across the declared-table modules and the vector helpers.
- **Dead code**: name-token search, with string-dispatched `_op_*` names set aside.
- **Panel code**: `CadexPanels.py`, `cadex_assembly_worker._measure_shell_gaps` and `CadexFitReport.shell_summary`, read end to end.
- **Projects**: the nine 2026-10-09 creature projects (`~/cadex-projects/cfix-*`, `castra-*`), read only: `script.py`, every `script_history/` revision, `DECISIONS.md` and `PROGRESS.md`.
- **Library usage**: all 320 project scripts grepped.

## Result

**Panels.**

- None of the 9 creature projects ships a `lib.panel`. Only castra-heron ever called it (3 of 9 history revisions), and that project removed it. Its project ADR-006 says the sleeve "obscured the mechanism, collided with moving links", and the compact panel "measured 10.2 mm away from its frame and its screws missed the frame".
- **Diagnosis.** `lib.panel` runs at script time with no kernel, so it carries a second CSG evaluator, `CadexPanels.sample` (~330 lines). It can only make a closed convex superellipse sleeve along one axis that wraps the frame too. That is the egg/sausage.
  - It ignores motion.
  - It has no openings.
  - Its bosses rest on sampled frame points.
  - `fit.shells` infers what a shell covers from bounding boxes, and judges on the median gap.
  - `appearance="shell"` conflates colour with role: agents painted links "shell" and got them judged as panels.
- **Proposed design.**
  - `part.envelope(over, clearance, radius, motion)` in the worker: offset(closing(C, r), c), where r is a rolling-ball radius from hug (small) to hull (infinite).
  - `part.panel(env, region, seams, thickness, openings, edge)`.
  - `part.panel_mounts`, publishing a `mounts` table for the screws.
  - `role="panel", covers=[...]`.
  - `fit.panels`: gap p90, coverage, exposes, egg_ratio, motion, wall, held, printable, seams. It counts as a fit failure.

**Architecture.**

- 9 separate fit and clearance paths.
- 6 or more render, film and video entry points.
- 4 copies of the declared-table pattern: about 1,280 lines of shared structure, 700-900 removable.
- `_unit` defined in 8 files and `_cross` in 7.
- The CLI loads 5 engine modules by path, while `ARCHITECTURE.md` says it loads only `CadexdProtocol`.
- `CadexDynamics` is 12,066 lines; the docs say 10,824.
- `CadexProject.py` (914 lines) looks dead.
- The base guidance is 6,012 words, with creature and gait content in it.
- Legged assumptions sit in `CadexEvaluation.METRICS` (12 of 31 metrics are gait), `evaluation_rig(feet=)`, the `DRIVE_FAMILIES` constants and `CadexAnatomy`.

**Breadth blockers.**

- **Dynamics:**
  - a slider closing a loop is refused (`CadexDynamics.py:1836`), which blocks every hydraulic linkage;
  - `rack_pinion` is refused (`:2381`), which blocks a belt-driven carriage;
  - couplings are two-joint only, which blocks CoreXY and the differential;
  - there is no track model;
  - the world is a 1 m floor.
- **Tasks**: there are no path, coverage, odometry or tool-frame metrics.
- **Catalog**: there are no rails, belts, leadscrews, steppers, extrusion, cylinders or spindles, and it is 1,559 lines of code rather than data.
- **Unused generators**: `lib.spur_gear`, `rack`, `rack_and_pinion`, `linear_actuator` and `bldc` are used by none of the 320 projects.

**Ranking.** The review is in `docs/ARCHITECTURE-REVIEW.md` §4. It estimates about 6,000-8,000 lines removed against about 2,500 added.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: worktree-agent-a84f506f6c208cda2
- commit: 587ffd43a981c19f42cd93af3619fffec4612433

## State Impact

- target: idle-lantern-9094 — negative knowledge: lib.panel (ADR-610) produces a closed convex superellipse sleeve along one axis, recipe-sampled with no kernel; none of 9 creature projects of 2026-10-09 kept it, and castra-heron removed it (10.2 mm off the frame, screws missed the frame, collided with moving links). Proposed replacement: worker-side part.envelope (closing+offset) + part.panel + published mounts, role=panel/covers=, fit.panels as a counted failure (docs/ARCHITECTURE-REVIEW.md §2)
- target: brave-stone-9609 — breadth gaps measured: the catalog has no rails, belts, leadscrews, steppers, extrusion, cylinders or spindles; lib.spur_gear/rack/rack_and_pinion/linear_actuator/bldc are unused in all 320 projects; recommendation: catalog as data with interface generators (docs/ARCHITECTURE-REVIEW.md §3, §4 rec 4)
- target: salty-isle-4063 — open gaps for non-legged machines: slider loop closure refused (CadexDynamics.py:1836), rack_pinion refused (:2381), couplings two-joint only, no track model, world is a floor, 12 of 31 evaluation metrics are feet-based gait; recommended: fixed-tendon n-joint couplings, a cylinder actuator, tool frame, path/coverage tasks (docs/ARCHITECTURE-REVIEW.md §3.3)
