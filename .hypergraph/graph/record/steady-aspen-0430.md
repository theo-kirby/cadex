---
node_id: 972c1659-912e-5570-b7c8-0f70ac16394c
slug: steady-aspen-0430
title: 'ot10: ADR-427 a part resting on world geometry at the solved pose is advisory; hexapod-6 replay 7 -> 1 failing static rows'
created_at: '2026-09-28T09:48:36+00:00'
parents:
- smooth-sky-9692
summary: ''
---
## What

ADR-427 (commit `cafd3960`, iteration 40, which landed without a record):
in the CLI's `fit_summary` (`cli/cadex_cli/clearance.py`), a solved-pose
pair one side of which the static block names as world geometry, and whose
status is `below clearance`, is published under `world_geometry_contacts`
(with `world_geometry_contact_count`, `counts["world geometry contact"]`
and `FIT_WORLD_NOTE`) and never in `failing`. The progress line appends
`; N resting on world geometry (advisory)`. An **intersection** with world
geometry at the solved pose still fails, an **unmeasured** pair still fails,
and the world geometry's own row stays in `failing`. Engine, protocol,
published measurements, the 0.1 mm default and the overlay are unchanged.
Docs moved with it: `docs/DECISIONS.md` ADR-427, `docs/CLI.md`,
`docs/XSCRIPT.md`, `docs/probes/ot10/README.md`.

## Why

The critic's fix-first item: nothing in `.hypergraph` mentioned ADR-427.
The decision itself came from attempt 6's diagnosis [rec: true-rose-1584]:
`ot10-hexapod-6` is the first design that stands on its floor at the solved
pose, and each ball foot at 0.0 mm and 0.0 mm³ against `c_floor` failed as
`below clearance`. ADR-420 already made swept findings against world
geometry advisory and ADR-424 took world geometry out of P2; the static
pair rows were the last place the floor was held to a gap between two
parts. Standing on the floor is the stance, not a closed gap.

## Method

Rebuilt the accepted revision `3cb2b1d0` of `ot10-hexapod-6` on a fresh
`/tmp` copy (`cadex params --set fasteners=1`, 3 min 58 s, same revision),
read the fit block on the previous and the new source. Two regressions in
`cli/tests/test_clearance.py`: a foot resting on the floor fails on the
previous source and passes now; a sunk foot (intersection), an unmeasured
floor pair and a printed pair below its gap beside the floor all still fail.
Suites re-run at `cafd3960` in iteration 41.

## Result

- **Before (previous source):** 7 failing static rows — the floor's own
  advisory row plus six `c_floor ∩ c_foot_*` at 0.0 mm, 0.0 mm³.
- **After (ADR-426 + ADR-427 source):** 1 failing static row (the floor's
  own), 6 world-geometry contacts, 3,735 clear, 0 intersections; sweep
  12/12 joints pass at 5° (ADR-426).
- `pixi run test-engine`: **2239 passed, 53 skipped** (6 min 29 s).
- `pixi run python -m pytest cli/tests`: **1012 passed, 1 skipped**
  (12 min 15 s).
- Attempt 6's published verdict stays a miss: the bar counts the turn as it
  ran. The accepted `ot10-hexapod-6` project is unchanged.
- Engine not touched, so no packaged gate is owed for this change.

Dispatch closed: 1 unit — ADR-427 recorded (fix-first item): world-geometry resting contacts advisory at the solved pose; 7 → 1 failing static rows on hexapod-6's replay; both suites green.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: cafd3960474d528c0d7a4bf0b94f58de09616980

## State Impact

- target: loyal-fountain-8709 — ADR-427: a below-clearance static pair against world geometry (a foot resting on the floor, 0.0 mm, 0.0 mm³) is reported under world_geometry_contacts, never failing; an intersection or unmeasured pair still fails. hexapod-6 accepted revision replay: 7 failing static rows -> 1 (the floor's own advisory row), 6 contacts, sweep 12/12. Attempt 6 stays a miss. Suites 2239 passed/53 skipped and 1012 passed/1 skipped at cafd3960.
