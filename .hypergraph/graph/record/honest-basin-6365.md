---
node_id: c17fa795-0b6c-51df-bf7c-cfc68e61b796
slug: honest-basin-6365
title: 'S3: a check rather than a repair, and a safety factor that follows its part'
created_at: '2026-08-11T10:49:05+00:00'
parents:
- eager-trail-8160
summary: ''
---
## What

S3 closed, both halves, and it is the first time this vertical put anything
inside the engine. `mesh.check` (ADR-144) and `part.stress` (ADR-145), each a
declared output that publishes a fact and no geometry. `docs/VISION.md`'s
"FEM … is out of scope" line got an **amendment**, on the template ADR-127
set when interactive mesh editing was ruled out and then arrived as
`part.loft_cage`.

One new engine module (`src/Mod/cadex/CadexStress.py`), two new ops, two new
suites (`test_part_stress.py` 14 tests, plus 8 in `test_mesh_domain.py`) and
one new purity guardrail. **No protocol op, no new `artifact_kind`, no digest
change, and a `shell/` diff of exactly zero lines.**

## Why

S0–S2 were staged outside the engine so that the question "what earned its
way in" could be answered with measurements instead of anticipation. This is
that answer. The part that earned it is the part a *rebuild* needs: a verdict
that follows a parameter change. The expensive half — topology optimisation,
refinement sweeps, CalculiX, load cases measured off a MuJoCo rollout — stays
offboard, and is staying there.

## Method

**The S3a checkpoint was a measurement, not a judgement.** A real S2 result —
a 60×20×30 mm cantilever carved at 2 mm, extracted, Taubin-smoothed — was put
through the engine's own `Mesh` kernel before any op was written:

| | raw marching tets | + Taubin | decimate(0.5) | decimate(0.9) |
|---|---|---|---|---|
| facets | 13320 | 13320 | 7248 | **7248** |
| `hasNonManifolds` | false | false | false | false |
| self-intersections | **1** | **0** | 0 | 0 |
| `isSolid` | true | true | true | true |
| components | 1 | 1 | 1 | 1 |
| non-uniformly oriented facets | 0 | 0 | 0 | 0 |

**`part.stress`** takes an ADR-029 selector for what holds the part, a list
of loads, four material properties with units in their names and no defaults,
and an `element_mm` budget. `CadexStress.py` imports no FreeCAD at all —
`cadex_part_worker` resolves selectors to faces, tessellates them and samples
them, and what crosses into the solver is triangles and point clouds.

Commands:

```
pixi run python -m pytest src/Mod/cadex/cadex_tests
pixi run python -m pytest cli/tests
pixi run build-engine && pixi run stage-engine
CADEX_ENGINE_ROOT=$PWD/build/engine/cadex-engine-0.0.0-macos-arm64 \
  pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py
```

## Result

**Full engine suite 1823 passed / 22 skipped** (1776 before this session's
work, 1800 after S2). `cli/tests` 80 passed. Packaged gate 12 passed against
a freshly staged payload, and `CadexStress.py` is in it —
`build/engine/cadex-engine-0.0.0-macos-arm64/Mod/cadex/CadexStress.py` — which
matters because a new CMake install line is exactly the failure mode Phase
10b hit. 84 of the new and adjacent tests re-run green against that payload.
`git status -- shell/` is empty.

**S3a is one op, and it is a diagnostic, not a repair.** Every anticipated
repair op is answered by a column of the table above: nothing to fill (zero
boundary edges at every stage), nothing to harmonise (zero non-uniformly
oriented facets), and the smoothing is already done offboard by a Taubin pass
that does not shrink. **So none of `smooth` / `fillupHoles` /
`harmonizeNormals` / `fixSelfIntersections` earned its place.** What earned
its place is `mesh.check`, for two reasons the same table supplies:

1. **A combinatorial closure check cannot see a self-intersection.** The raw
   marching-tetrahedra surface has every undirected edge in exactly two
   triangles and every directed edge exactly once — and one pair of facets
   passing through each other. Different properties; the offboard checker is
   structurally incapable of noticing the second.
2. **`decimate` does not say what it did.** A 50% and a 90% reduction request
   both returned 7248 facets — tolerance-bound, silently. `docs/STRUCTURAL.md`
   §6 posed exactly that question and it had no answer until now.

It never repairs: a repair op mutates geometry and reports nothing, which is
the wrong shape of answer to "is this sound".

**`part.stress` agrees with the offboard solver and with the closed form.**
Driven through a live cadexd on a 100×10×10 mm PLA cantilever at 2.5 mm,
10 N at the tip:

```
tip deflection   1.13916 mm   (Timoshenko closed form 1.15218, 1.1% low)
peak von Mises   5.3790 MPa
p99  von Mises   5.3389 MPa
```

— the same three digits `docs/STRUCTURAL.md` §3.3 records for
`analysis/cadex_stress.py` at that grid. A separate headless test solves the
identical grid with the identical assembled force vector through both
implementations and requires agreement to **1e-9** on displacement, peak and
p99, plus element-matrix agreement to 1e-9.

**And it follows the part.** `set_params` from length 100 → 150 mm moved the
tip deflection 1.139 → 3.840 mm, a ratio of 3.37 against the cubic beam
scaling's 3.375, and the mass 12.4 → 18.6 g exactly ×1.5.

**The bug worth writing down, because nothing about it looked wrong.** A
selector resolves to faces; the faces are tessellated; the solver asks which
grid nodes lie on them. **A planar face tessellates to four vertices.**
Taking those as anchors held the bar at four corner nodes out of twenty-five
and loaded it at four — a different structure, reported with a relative
residual of 2e-11, no warnings, and every number internally consistent about
the wrong problem. It surfaced as a tip deflection of **1.78 mm against a
closed form of 1.15**: soft by 55%, and visible only because the benchmark
had an independent answer. Fixed by sampling each face's triangles
barycentrically at a third of a cell, capped at 400k points. This is
ADR-129's lesson arriving a third time in this vertical.

**Where the plan's staging argument did not survive contact.** The plan said
`CadexStress.py` would be staged by filename with `DECLARED_ENGINE_MODULES`
**not** growing, mirroring `CadexDynamics`. That mechanism is not available:
`CadexDynamics` is unreachable because `cadex_assembly_worker` is itself
outside the closure, and **`cadex_part_worker` is inside it**. So the list
grows by one, deliberately, rather than being routed around with an
`importlib` trick. What is asserted instead is the property that actually
costs something: nothing imports `CadexStress` at module scope, and it defers
numpy and scipy into its own functions — so a `cadexd` that imports
`cadex_part_worker` does not load the solver, and a worker that loads the
solver does not load 73 MB of numerics. **Reachable and loaded are different
questions.**

**One real gap found and closed.** `inspect scope="output"` did not carry
`measurement` — `_OUTPUT_DETAIL_KEYS` listed only keys describing a thing
with geometry, so an output that *is* a number was readable on the rebuild
response that produced it and nowhere else. Tolerable for a dimension the
viewport draws; not tolerable for a soundness verdict an agent reads an hour
later. Both `measurement` and the two new kinds are there now; the worker had
already computed all three.

**Design commitments that held.** The safety factor divides by **p99 von
Mises, never the peak** — ADR-141 measured that the peak at a held face is a
singularity that grows with every refinement for ever, so a peak safety
factor would be lying; both numbers travel and the payload's own `note` says
which carries the verdict. Every material property is required, bounded, and
refuses by **naming materials** rather than ranges, on `assembly.body`'s
precedent. `element_mm` is a budget the engine caps at 60,000 elements and
refuses above, naming the size that would fit.

**Also found:** `_mesh()` in the mesh API validated the domain but not the
output type, so a `mesh_check` could have been fed into a boolean and failed
in the kernel naming the composed chain rather than the line the script
wrote. Now validated at the API.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: be7ff63d8766f3cede9545152af00a5e01c06fe8

## State Impact

- target: kind-marsh-2645 — S3 closed, both halves (ADR-144, ADR-145), and docs/VISION.md's FEM line amended. S3a is ONE op and it is a diagnostic: S2's output measured through the engine's own Mesh kernel is already manifold, closed, one component and uniformly wound at every stage, so no repair op earned its place; mesh.check earned its place because a combinatorial closure check cannot see a self-intersection (the raw surface had one) and mesh.decimate does not report what it did (50% and 90% requests both returned 7248 facets). S3b is part.stress: a declared output carrying a safety factor and no geometry, anchored by ADR-029 selector, dividing by p99 rather than the peak, pinned equal to the offboard solver to 1e-9 and agreeing with the closed form to 1.1%. A planar face tessellates to four vertices, which held a bar at four corner nodes and reported a 55% error with a 2e-11 residual and no warnings. DECLARED_ENGINE_MODULES grows by one because cadex_part_worker is in the closure where cadex_assembly_worker is not; the guardrail now asserts module-scope non-import instead. Full suite 1823 passed, cli 80 passed, packaged gate 12 passed, shell diff zero.
