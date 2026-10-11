---
node_id: 3df8b4e4-14f0-5826-80af-d90df8e3942d
slug: violet-gate-4339
title: Machine parts publish mounting holes; the 2020 slot and T-nut fit (ADR-660, ADR-661)
created_at: '2026-10-11T09:30:26+00:00'
parents:
- little-ash-2582
- staid-harvest-9652
summary: ''
---
## What

Fixed two catalog bugs that the first breadth wave of agent-designed machines surfaced (ADR-660, ADR-661).

1. Parts made with `lib.part(sku)` published `mount_axes: []`. As a result, `fit.mounting` reported rails, carriages, steppers, nuts and brackets as "contact only", and a screw in a carriage's or stepper's tap-drill hole read as an intersection.
2. The catalog M5 T-nut (10 x 10 x 4.5) did not fit the catalog 2020/2040 slot, which was modelled 8 mm wide and 5 mm deep. The wave-1 liquid handler's `docs/rejected.md` reports each nut intersecting the 2040 by about 176 mm^3.

## Why

Without holes, the mounting check cannot tell a screwed-down machine part from one that merely rests in place. Without a T-nut that fits, every extrusion joint had to be modelled as a screw ending in an empty slot. Both made gantry machines read as unheld.

## Method

**Holes.**
- Each `CadexMachineParts` interface now returns `.spec['mount_points']`: origin, axis, and `thread_dia_mm` or `hole_dia_mm`. `lib.part` carries them through the placement into `_MOUNT_AXES`.
- `LibraryPart` keeps the per-row size facts.
- Tapped holes are open bores at the nominal diameter, the convention every other catalog part already uses.
- The rail's hole pattern is now centred.
- The SFU1204 flange holes now keep off the flats.

**Fit report.**
- `takes_thread` covers nuts, inserts and T-nuts, so they get the ADR-492 thread allowance and the nut path. A bolt that touches no printed part is credited to whatever printed part its nut touches.
- `_on_output` puts a pulley on a drive's output only when the pulley sits on the drive axis.
- `_clamped_by` holds a spindle by a clamp.

**Slot and T-nut.**
- The slot is now the B-type section, built as an extruded polygon: 6.2 opening, 1.8 lip, 11 mm undercut, 1.2 mm straight wall, then 45-degree flanks down to 6.1.
- Added `2020-tnut-m3`. Both T-nuts are now slide-in sections: 9.8 x 4 body, 6 x 1 neck, 2.4 chamfer.
- The profile spec gains `slot_datums`, and `MachinePart.slot(face, along, index)` gives a nut's world placement.
- Provenance is in PROVENANCE §8k.

## Result

- `test_parts_data.py` (16 tests) and `test_mounting_check.py` (36 tests, including the new real-kernel `test_a_rail_on_t_nuts_a_carriage_and_a_stepper_are_held_on_the_real_kernel`) pass.
- In that real-kernel test, a live cadexd builds a rail on four T-nuts in a 2020, an MGN12H under a plate, and a NEMA17 on a printed mount with a GT2 pulley.
  - The rail, carriage and motor each read `held` by screws, 4 of 4.
  - The pulley reads `held` on the output, and every T-nut reads `held` against the beam.
  - There are no intersections. `threaded_count` is 4, and every T-nut/beam pair has 0 common volume.
- describe_api page sizes: assembly 21,479 (unchanged), part 21,055, library 21,147, library_parts 9,509, index 15,290. All are under 21,500.
- Both full suites pass: `pixi run test-engine` reports 2845 passed and 62 skipped, under `ulimit -v 25000000`. `pytest cli/tests` reports 1261 passed and 1 skipped, with the engine built in this worktree.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: worktree-agent-abb14212d898b5d9f
- commit: 0af99997e6da71d4a108ab4d8dfcfb92b9b5700c

## State Impact

- target: brave-stone-9609 — lib.part machine parts publish their mounting holes (mount_points: rail, carriage, NEMA face, nut flanges, T-nuts, bracket, caster, pulley bore) and the mounting check credits screws into them, through T-nuts to extrusion, with nuts/inserts/T-nuts given the thread allowance; the 2020/2040 slot is the B-type section and the M3/M5 T-nuts fit it, placed by MachinePart.slot (ADR-660, ADR-661)
