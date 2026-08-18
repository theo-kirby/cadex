---
node_id: c09779df-9bce-588d-bb57-6f02ae95adfa
slug: modest-spark-7806
title: 'S4a: four opt-in keys on the field, and a blend that had to be measured before it was believed'
created_at: '2026-08-11T18:42:21+00:00'
parents:
- honest-basin-6365
summary: ''
---
## What

S4a closed, and spike zero before it (ADR-146, `docs/STRUCTURAL.md` §8.1–8.2,
ROADMAP Phase 16).

`analysis/topology.py` gains four plan keys — `symmetry`, `extrude`,
`interface_pad_mm`, `pin_domain_planes` — **all off by default**, so a plan
written against S2 carves the same field. Three are defects the first real
render of a carved bracket exposed; the fourth is what makes a result read as
designed. No engine code, no protocol change, no payload bytes, no new pinned
dependency, no `shell/` diff.

Spike zero ran first because `docs/ORGANIC.md` §1 said the blended fuse might
sink the whole slice: the robot wolf failed twice trying to weld sixteen
fused lofts, and `part.fuse(blend=)` (ADR-124/125) was built to close that
gap but had never been asked to blend forty-way.

## Why

The carved bracket from S2/S3 was **structurally right and visually wrong**
in four separable ways: thin fins at the loaded end that are not structure,
facets that are the grid, a mounting face Taubin had rounded, and the
blobbiness of SIMP itself. The first three are defects with cheap fixes; the
fourth is the algorithm and is what S4b–d is about.

`interface_pad_mm` is also a **prerequisite** rather than a nicety: without
pads the fins generate garbage skeleton nodes at exactly the places the loads
attach, so the fitter downstream has nothing sound to anchor to.

## Method

Spike zero: hand-written lattices of 14, 24, 44 and 64 spheres-plus-members
driven through a real `cadexd` (`test_cadexd_lifecycle._spawn_cadexd`), timed
at `blend=None`, `refuse`, `reduce` and `skip`, plus a radius sweep at 49
solids.

S4a: each key implemented and then measured against a cantilever with its tip
load pushed off to one side (40 × 16 × 20 mm, 2 mm elements, filter 4 mm, 20
iterations) so that symmetry is not free.

Tests: nine new in `src/Mod/cadex/cadex_tests/test_analysis_topology.py`
(32 total, was 24). Full engine suite 1851 passed / 22 skipped;
`cli/tests` 80 passed; `git status -- shell/` empty.

## Result

**Spike zero passed its gate, and moved twice on the way.**

| solids | `blend=None` | `refuse` | `reduce` | `skip` |
|---|---|---|---|---|
| 14 | 0.95 s | fails, 9 of 37 edges | 6.7 s | 6.8 s |
| 24 | 1.64 s | fails, 7 of 65 | 10.8 s | 10.9 s |
| 44 | 2.06 s | fails, 15 of 114 | 4.9 s | 5.0 s |
| 64 | 3.35 s | fails, 18 of 166 | 5.9 s | 5.9 s |

Radius sweep at 49 solids, `refuse` / `reduce`: 2.0 mm fails (16 of 127) /
4.7 s; 0.8 mm fails (8) / 15.1 s; 0.6 mm fails (4) / 18.4 s; 0.4 mm fails
(**1** of 127) / 9.6 s.

1. **No blend radius survives `refuse`** — not even a quarter of the thinnest
   member. The failure mode is a mode, not a size.
2. **`reduce` clears every size tried, to 64 solids in under 20 s** — inside
   the ~30 s gate. The authorised fallbacks (a pairwise fuse tree, oversized
   node spheres with `blend=None`) were **not taken**.
3. **`part.cone` refuses equal radii.** Every strut of the first lattice was
   refused with `creation of cone failed` before a blend was attempted — that
   surface is a cylinder, and `gp_Cone` needs a non-zero semi-angle. Nothing
   in the plan predicted this.

**S4a, measured:**

- **symmetry** holds to **9.4e-16** — floating point, not convergence —
  because it is imposed on the *filtered sensitivity* and the
  optimality-criteria update is pointwise and monotone in it. Refuses a
  design domain that is not itself symmetric about the named mid-plane;
  warns when `keep` is asymmetric.
- **extrude** needed a second edit nobody predicted: averaging the
  sensitivity alone leaves the design tapered, because the volume gradient
  `filt.backward(inside)` is not constant along the axis near the domain's
  faces. Largest column standard deviation of the density: **0.105 → 0.0009**
  once the volume gradient is averaged too. That is free — averaging
  preserves each column's sum, so `x · gradient_extruded` equals
  `x · gradient` term for term for a design already constant along the axis.
  The residual 0.0009 is left in the *density* deliberately: projecting it
  would break `rho = Hx/d`, which is what makes the analytic sensitivity
  exactly checkable against a finite difference.
- **interface_pad_mm** takes its interfaces on **nodes** and maps to the
  cells that touch them, not through `_cell_regions` — a load declared as a
  zero-thickness plane at `x = 60` selects nodes there and *no cell centre at
  all*. A pad overlapping a declared `void` is clipped with a warning: `void`
  is the region a person declared.
- **pin_domain_planes** is a test on 1e-6 mm rather than a tolerance to tune,
  because a vertex on a face of the blank came out of a cell held at density
  1 and the level set of a step from 1 to a padded 0 lands exactly on the box
  face. Measured: an unpinned smoother moves the cantilever's root face by
  more than 1e-3 mm, a pinned one by less than 1e-9, and the vertices still
  slide within the plane.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: be7ff63d8766f3cede9545152af00a5e01c06fe8

## State Impact

- target: kind-marsh-2645 — S4a closed (ADR-146): analysis/topology.py gains symmetry / extrude / interface_pad_mm / pin_domain_planes, all opt-in and all off by default, so an S2 plan carves the same field. Spike zero measured the blended fuse before any of it and passed its ~30s gate: 64 solids blend in under 20s, but ONLY with blend_on_failure=reduce -- no radius survives 'refuse', not even 0.4mm against a 1.6mm member -- and part.cone refuses equal radii, so a strut of uniform section must be a cylinder. The authorised fallbacks (fuse tree, blend=None plus oversized nodes) were not taken. Symmetry holds to 9.4e-16 because it is imposed on the filtered sensitivity; extrude needed the volume gradient averaged as well, which took the density's largest column standard deviation from 0.105 to 0.0009.
