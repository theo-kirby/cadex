---
node_id: c331b35e-c129-5fc1-91aa-d46d74928d07
slug: kind-marsh-2645
title: Structural analysis, topology optimisation and shape search
created_at: '2026-08-10T11:32:20+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Stress-testing a part, finding where material can be removed safely, and
letting a search pick the shape. Three jobs — lighter printed parts, robot
legs whose mass feeds back into the dynamics a policy has to control, and
shape search — all of which need one thing first, which is a stress number
somebody can believe. `docs/STRUCTURAL.md` is the arc, ROADMAP Phase 16 is
its status line, ADR-141 authorises the tree [rec: fair-beacon-5964].

**All five slices are closed.** S0 and S1 offboard [rec: fair-beacon-5964]
[rec: jolly-shore-2511], S2 offboard [rec: eager-trail-8160], S3
**in-engine, authorised by the owner**, with `docs/VISION.md`'s "FEM … is out
of scope" line amended rather than routed around [rec: honest-basin-6365],
and S4 offboard again [rec: modest-spark-7806] [rec: empty-light-4558]. The
staging worked: what came in-engine was chosen from measurements of S2's own
output rather than from anticipation.

**S4 is what the vertical was for.** Every generative-design tool on the
market ends in a mesh you cannot edit; Cadex is the one product whose native
artifact is a *script*, so the optimiser can find the **topology** and the
deliverable be a feature tree a human and an agent can both edit. That is
`docs/VISION.md` principle 3 made literal rather than honoured in spirit
[rec: empty-light-4558].

### The offboard tree

- **`analysis/` is a second non-engine tree** at the repository root, under
  the identical ADR-084 contract `training/` holds: no CMake rule references
  it, no payload carries it, nothing in it enters `pixi.toml`, and its
  dependencies (`numpy==1.26.4`, `scipy==1.17.0`, `mujoco==3.10.0`) are
  exactly pinned in its own `requirements.txt`. It does not speak the
  protocol — it reads files and writes one JSON report, one line on stdout,
  human stream on stderr. Test-enforced [rec: fair-beacon-5964]. It is
  **still exactly three pins** after S2, because the geometry extraction is
  hand-written rather than a fourth dependency [rec: eager-trail-8160].
- **The solver is a hex-grid linear-elastic core in numpy/scipy**, verified
  three ways: the cantilever against its Timoshenko closed form (1.14184 vs
  1.15218 mm, **0.9%**), the recovered stress against `M y / I` at midspan,
  and **CalculiX 2.23 on the same grid** — 4.4e-7 on displacement, 5.4e-8 on
  von Mises [rec: fair-beacon-5964].
- **The element is C3D8I, not C3D8.** A fully-integrated trilinear hex
  shear-locks in bending and reports a part *stiffer than it is*, which is
  the direction that flatters a safety factor: **5.1% against 0.9%** on the
  same grid. Wilson incompatible modes are nearly free on a structured grid,
  and condensation commutes with a uniform scaling of the element energy —
  which S2 cashed in and a test now asserts to 1e-9 rather than taking on
  trust [rec: fair-beacon-5964] [rec: eager-trail-8160].
- **The report separates what converged from what cannot.** Displacement and
  `p99` settle; **peak von Mises does not and must not**, because a clamped
  face is a genuine stress singularity with no limiting value. Three separate
  fields [rec: fair-beacon-5964].
- **The load case can be measured rather than declared**, which is what makes
  the robot-legs job tractable [rec: fair-beacon-5964].
- **S1 is the loop around S0**: `analysis/search.py` sweeps a project's
  declared parameters with no model in the loop. The design space is read off
  `<project>/script.json`; an evaluation is `./cadex params --json` **as a
  subprocess** rather than an import, which keeps this tree importing nothing
  from the engine and buys crash isolation per evaluation. **0.7 s** a
  rebuild; a 16-point grid with an FEA solve on every point in **12.7 s**
  [rec: jolly-shore-2511].
- **Two caches, and they are not the same cache.** One on the parameter
  vector, which skips the rebuild; one on the **`digest`**, which skips the
  *objective* — two different parameter vectors can produce the same model
  and the digest is the only thing that says so [rec: jolly-shore-2511].
- **The Pareto front is computed from the evaluated set**, not produced by
  the search. A constraint marks a point infeasible rather than dropping it,
  and a refused design point is information about the space rather than a
  failure of the search [rec: jolly-shore-2511]. **Optuna and pymoo are
  deliberately still unpinned** — both arguments for adding a driver turned
  out to be answerable for free [rec: jolly-shore-2511].
- **CalculiX is the second method and the reason to believe the first**
  (ADR-129's lesson). GPL-2, therefore a **subprocess**, and pruned out of
  the payload [rec: fair-beacon-5964].

### S2 — topology optimisation, and it is S0's solver in a loop

- **The density enters in one line of the assembly** and that is the whole of
  what makes S0's solver a SIMP solver. Legitimate with the condensed C3D8I
  element for the reason above. Four edits in total, and **S0's 27 tests pass
  unmodified**, which is the evidence the split is a split
  [rec: eager-trail-8160].
- **Geometry extraction is hand-written marching tetrahedra**, ~60 lines. No
  ambiguous cases where marching cubes has exactly that hole, and vertices
  welded on **the grid edge they lie on** rather than on a tolerance — so the
  surface is watertight by construction. Against a sphere of known volume:
  −4.46% at 10 cells across, −0.16% at 40, and Taubin smoothing moves it
  +0.5% / +0.06% where a plain Laplacian takes off 19.9% / 1.27%
  [rec: eager-trail-8160].
- **It runs on a laptop.** ~0.8 s an iteration at 13.5k elements, ~3.7 s at
  48k; a 100-iteration run is 1.5–6 minutes. **No GPU box**
  [rec: eager-trail-8160].
- **Verified in the order that catches things**: a finite-difference
  sensitivity check to **3e-6** (the classic SIMP bug and the only test that
  catches it); a cantilever beating a uniform field of identical volume by
  **7.3×**; an MBB beam with the textbook chord distribution; mesh
  independence at **95.5%** cell agreement across a 2.5 mm and a 1.5 mm grid
  with the same physical filter radius; and the extracted STL re-voxelised by
  **S0's own voxeliser**, two parts of one tree checking each other
  [rec: eager-trail-8160].
- **`_DIRECT_DOF_LIMIT` was wrong by 6×** and S2 paid to find out: CG beats
  the direct factorisation 3× at 21.8k free dofs and 11× at 47k, so the old
  60,000 sent every interesting problem to the slower solver. Now 10,000,
  with the table in the comment [rec: eager-trail-8160].
- **S2 invents no new asset suffix.** `.stl` is already in `_ASSET_SUFFIXES`
  and in the shell's mirror, so a result comes home through `put_asset` for
  free; a `.cxdensity` would be silently dropped by Save-As. The density
  field and the run receipt stay offboard [rec: eager-trail-8160].
- **Printability is deferred by decision**, and the open question the last
  reconcile carried is answered *neither, for now*: overhang angle and
  minimum wall thickness are not built and not planned, because supports
  handle overhangs. The filter radius stays for a purely numerical reason —
  without it SIMP checkerboards — which is why mesh independence is what it
  is tested on [rec: eager-trail-8160].

### S3 — what earned its way in-engine, and what did not

- **S3a is one op, and it is a diagnostic rather than a repair.** S2's output
  measured through the engine's own `Mesh` kernel is already manifold,
  closed, one component and uniformly wound at every stage — so `smooth`,
  `fillupHoles`, `harmonizeNormals` and `fixSelfIntersections` all earned
  nothing. `mesh.check` earned its place for two measured reasons: a
  *combinatorial* closure check cannot see a self-intersection (the raw
  marching-tets surface had exactly one while reporting every edge in two
  triangles), and **`mesh.decimate` does not report what it did** — a 50% and
  a 90% reduction request both returned 7248 facets, tolerance-bound and
  silent [rec: honest-basin-6365].
- **S3b is `part.stress`**: a declared output carrying a safety factor and no
  geometry, on `part.measurement`'s template. Anchored by **ADR-029
  selector**, so it follows the part — moving `length` 100 → 150 mm moved the
  tip deflection by 3.37× against the cubic beam scaling's 3.375. Every
  material property required, bounded, and refusing by **naming materials**
  rather than ranges [rec: honest-basin-6365].
- **The verdict divides by p99, never the peak**, because ADR-141 measured
  that the peak at a held face does not converge. Both numbers travel and the
  payload's own `note` says which carries the verdict
  [rec: honest-basin-6365].
- **Two implementations, pinned equal by a test.** Neither tree may import
  the other, so the numeric core is written twice and one test solves the
  identical cantilever on the identical grid through both, agreeing to
  **1e-9**. Through a live cadexd: 1.13916 mm tip deflection against a closed
  form of 1.15218, and 5.3790 / 5.3389 MPa peak / p99 — the same digits
  `docs/STRUCTURAL.md` §3.3 records for the offboard solver
  [rec: honest-basin-6365].
- **Cost to the rest of the system: nothing.** No protocol op, no new
  `artifact_kind`, no digest change, and a **`shell/` diff of zero lines**.
  Both new outputs are artifact-less, so they fall through to
  `payload_sha256` — identified by their declaration, which is the reading
  S1's digest cache depends on [rec: honest-basin-6365].
- **Verified against a payload, not only a source tree.** Full engine suite
  1823 passed / 22 skipped, `cli/tests` 80 passed, and the packaged gate
  green against a freshly staged payload carrying `CadexStress.py` — which
  matters because a new CMake install line is precisely the failure mode
  Phase 10b hit [rec: honest-basin-6365].

### S4 — generative design that ends in a script, not a mesh

- **Spike zero ran before the fitter existed**, because `docs/ORGANIC.md` §1
  said the blended fuse might sink the slice. It passed its ~30 s gate: 64
  hand-written solids blend in under 20 s. But **only with
  `blend_on_failure="reduce"`** — no radius survives `refuse`, not even
  0.4 mm against a 1.6 mm member (1 seam of 127 still refuses). The
  authorised fallbacks (a pairwise fuse tree, `blend=None` with oversized
  node spheres) were **not taken** [rec: modest-spark-7806].
- **S4a is four opt-in plan keys on `topology.py`**, all off by default, so an
  S2 plan carves the same field: `symmetry`, `extrude`, `interface_pad_mm`,
  `pin_domain_planes`. Symmetry holds to **9.4e-16** because it is imposed on
  the *filtered sensitivity* and the optimality-criteria update is pointwise
  and monotone in it; the design variable is never projected, so the volume
  constraint is untouched [rec: modest-spark-7806].
- **`extrude` needed the volume gradient averaged as well as the
  sensitivity**, or the filter's edge effect comes straight back through the
  bisection: largest column standard deviation of the density **0.105 →
  0.0009**. Free, because averaging preserves each column's sum. The
  remaining 0.0009 is left in the density on purpose — projecting it would
  break `rho = Hx/d`, which is what makes the analytic sensitivity exactly
  checkable against a finite difference [rec: modest-spark-7806].
- **`interface_pad_mm` is a bug fix wearing an aesthetics hat, and a
  prerequisite.** A load declared over a thin face gets the cheapest membrane
  that can receive it — correct, useless as a mount, and it generates garbage
  skeleton nodes at exactly the places S4b has to anchor to
  [rec: modest-spark-7806].
- **S4b–d is `analysis/skeleton.py`**: distance transform → maximal-ball
  packing → Delaunay bars → an emitted xscript with three `num()` parameters
  and the radii as an editable table → `./cadex script --set` as a subprocess
  → a fully-stressed-design sizing loop that runs the **real hex FEA on the
  rebuilt CAD** every pass. No surrogate and no second physics model, so a
  fit that will not build fails on pass one [rec: empty-light-4558].
- **The verdict is one number, and the benchmark ships.** Two-footed bracket,
  60 × 40 × 40 mm at 2 mm: SIMP compliance 10.234 N·mm at 40.58 g, rebuilt
  script 6.042 N·mm at 41.07 g — **compliance ratio 0.59 against a bar of
  1.15**, coverage 0.926, 23 nodes and 51 struts. The part is 1.7× stiffer at
  the same mass, which is not the fit beating the optimiser: SIMP minimises
  compliance over a *grey* field and the band a filter smears over every
  member is real material carrying nothing [rec: empty-light-4558].
- **The parametric half is real**: `./cadex params --set strut_scale=1.1`
  moves the exported volume 32 975 → 35 751 mm³ with no model in the loop,
  which is the whole claim S4 exists to make [rec: empty-light-4558].
- **The coverage gate refuses the right fields for a different reason than
  planned.** Bar 0.85; bracket 0.93, synthetic truss 0.97, SIMP cantilever
  0.76, solid block 0.79, hollow box shell 0.56. But **a slab fits fine**
  (0.90–0.97) — its medial axis is one sheet — so the gate is not a
  plate-detector, it is a *fidelity* gate: it says the emitted strut part does
  not contain the material the field had [rec: empty-light-4558].
- **`_SUPPRESSION = 2.0` is a diameter and it is also the build budget.**
  Bracket at 1.0: 556 solids, coverage 0.99; at 2.0: **74 solids, 0.93**.
  Below 2.0 the coverage barely moves and the solid count explodes past what
  `part.fuse` will blend in a sane time [rec: empty-light-4558].
- **Cost to the rest of the system: nothing.** No engine change, no protocol
  op, no payload bytes, no `pixi.toml` entry, `requirements.txt` still three
  pins, and a `shell/` diff of zero lines. Full engine suite 1851 passed / 22
  skipped, `cli/tests` 80 passed [rec: empty-light-4558].

**Open**, and S4's own measurements are what set the first two of the
three [rec: empty-light-4558].

- **S5 — constraining SIMP itself toward strut-like solutions.** S4
  deliberately does not change what the optimiser optimises; it fits the
  field. The coverage number is the evidence that would ask for S5, and it is
  now measured: 0.76 on the cantilever and 0.56 on a shell
  [rec: empty-light-4558].
- **A `cadex` subcommand that serves a non-BREP output's value.**
  `part.stress` computes a safety factor, it is in the project store, and
  `cadex export --json` describes only BREP outputs — so a headless caller
  cannot read it. Reading the store's own attempt files would couple
  `analysis/` to a layout ADR-142 keeps it away from, so it does not
  [rec: empty-light-4558].
- Stress-constrained topology optimisation is recorded as a question rather
  than built: SIMP minimises compliance, and the standard MMA implementation
  (`mmapy`) is GPL-3 and barred here, leaving `beso` (LGPL-3) or a p-norm
  aggregation written against this tree's own solver as the two clean options
  [rec: eager-trail-8160].

## Negative knowledge

- [scope: voxelising a part for analysis | confidence: high | evidence: fair-beacon-5964] A voxel grid that is not fitted to the part solves a **differently shaped part at every refinement level**, so the sweep says nothing. Centre-sampled voxelisation of a 10 mm bar at 1.875 mm keeps five cells and throws away 6% of the height, and stiffness goes as the cube of height: the unfitted sweep gave tip deflection 1.14 → 1.45 → 1.21 mm with no convergence to read. Fit each axis to the bounding box.
- [scope: a parity fill over a triangle soup | confidence: high | evidence: fair-beacon-5964] The sample-point nudge that keeps a vertical ray off a shared triangle edge must use a **different** irrational fraction per axis. One fraction shared across axes cannot move a point off the `x = y` diagonal, and a cap tessellated as a triangle fan gives every radial edge to two triangles — so the whole diagonal was double-counted and came out hollow, 4.5% of a cylinder. Visible only after a float32 round trip through an STL. The exact fix is to collapse coincident crossings: a ray through a shared edge crosses the surface once.
- [scope: a single-grid stress number | confidence: high | evidence: fair-beacon-5964] A single grid is not a measurement. A voxel mesh overstates stress at a stair-stepped boundary, and at a genuine singularity refinement makes the peak *worse* rather than better — so a peak from one grid is an estimate, and `p99` is usually the number to read.
- [scope: anything under analysis/ | confidence: high | evidence: fair-beacon-5964] Nothing there may import a GPL package. The obvious tools for structural work are the GPL ones — `gmsh`, `pymeshlab`, `mmapy`, `ccx2paraview`, `pygalmesh`, `pymeshfix`, `tetgen` (AGPL), JAX-FEM, fenitop — and this tree is engine-side, which `docs/PROVENANCE.md` §1 puts at LGPL. It is a test, not a note.
- [scope: an objective evaluated inside a search | confidence: high | evidence: jolly-shore-2511] Use **one fixed grid**, not S0's refinement sweep. A search wants a consistent *ranking*, and a fixed grid gives every candidate the same discretisation bias where a per-candidate adaptive sweep lets the discretisation move between two designs being compared. Say which the report did.
- [scope: reading the CLI's --json envelope | confidence: high | evidence: jolly-shore-2511] It is **pretty-printed across the whole of stdout**, so reading only the last line — the convention `analysis/`'s own tools follow — parses a closing brace. One tree's output discipline is not another's.
- [scope: what analysis/ may be said to do | confidence: high | evidence: jolly-shore-2511] "Nothing in it spawns a process" stopped being true when `search.py` landed: an evaluation is a rebuild. The tree still imports nothing from the engine, which is the property that carries the weight.
- [scope: a winding table derived from a parity argument | confidence: high | evidence: eager-trail-8160] A parity argument only means anything against a **fixed handedness**. Three of the six natural tetrahedron listings for a cube are left-handed; leaving them so produced a surface that was topologically closed — zero boundary edges, zero non-manifold edges — with **half its triangles inside out**, so the closure check passed and the enclosed volume came out as exactly `0.0`. Orient each cell at import and assert the determinant.
- [scope: a filtered SIMP design | confidence: high | evidence: eager-trail-8160] **Read discreteness off the design variable, never off the physical density.** A density filter of radius R smears a binary design over a band of width R, so a member thinner than 2R is grey through its core however well the run converged: measured, a design variable of 3833 cells at 0, 1638 at 1 and 129 anywhere else — non-discreteness 0.017 — has a *density* non-discreteness of 0.32. Reading the second as a quality score says the run failed when it did not.
- [scope: an optimality-criteria volume constraint under a density filter | confidence: high | evidence: eager-trail-8160] Constrain the **physical** density, not the design variable. A normalised filter does not preserve a sum, so bisecting on `sum(x)` landed the reported volume fraction 1.4% off. The filter is linear, so the physical volume is exactly `x · dV/dx` with `dV/dx = Hᵀ(1/d)` — one convolution at construction, and the bisection stays arithmetic.
- [scope: turning a BREP selector into a boundary condition | confidence: high | evidence: honest-basin-6365] **A planar face tessellates to four vertices.** Using tessellation vertices as the anchors for "which grid nodes lie on this face" held a bar at four corner nodes out of twenty-five and loaded it at four — a different structure, reported with a 2e-11 residual, no warnings, and every number internally consistent about the wrong problem. It read 1.78 mm against a closed form of 1.15, and was visible only because the benchmark had an independent answer. Sample the face's triangles, do not take their corners.
- [scope: keeping a heavy dependency out of cadexd | confidence: high | evidence: honest-basin-6365] "Stage it by filename so the closure never reaches it" is **not always available**. `CadexDynamics` stays out because the only module that reaches it is itself outside the closure; `cadex_part_worker` is *inside* it, so `CadexStress` is statically reachable no matter how it is staged. The property worth asserting is the one that costs something: nothing imports it at **module scope**, and it defers its numerics into functions. Reachable and loaded are different questions.
- [scope: a domain API whose domain gains a second output type | confidence: high | evidence: honest-basin-6365] A validator that checks only the *domain* silently stops being enough. `_mesh()` accepted any mesh-domain value, so a `mesh_check` — four integers, no triangles — could be fed into a boolean and would fail in the kernel naming the composed chain instead of the line the script wrote.
- [scope: blending a fused lattice with part.fuse(blend=) | confidence: high | evidence: modest-spark-7806, empty-light-4558] **The fillets are not free**, and this is the one premise of the S4 plan that did not survive contact. On a *hand-written* lattice `reduce` clears every size to 64 solids; on a **fitted** one it refuses, because it looks for a single radius that blends every seam and near-tangent members leave none — it refused the whole part down to 0.0555 mm. `skip` is what an emitted script should use, and even `skip` refuses when *nothing* blends: the shipped benchmark bracket refuses every radius tried (0.25, 0.5, 1.0, 2.0 mm) at `strut_scale = 1.0`, while at `strut_scale = 0.9` a 1.0 mm blend succeeds and adds 30 000 triangles. Whether a given lattice blends is a property of the lattice that only the kernel knows, so a blend radius is a declared knob to try, never a promise.
- [scope: emitting a solid of revolution from a fitted member | confidence: high | evidence: modest-spark-7806] **OCC has no cone of equal radii** — that surface is a cylinder, and `gp_Cone` needs a non-zero semi-angle. Every strut of the first spike lattice was refused with `creation of cone failed` before a blend had been attempted. Branch on `abs(r0 - r1) < 1e-6`.
- [scope: sampling a medial axis from a distance transform | confidence: high | evidence: empty-light-4558] **Local maxima are not the medial axis.** A member is a *ridge*, and a cell on a ridge is not a strict local maximum: a 3×3×3 maximum filter proposed 25 cells out of 3500 on a bracket whose members run 8 to 14 mm thick, the packing kept 11, and the fit covered 0.45 — a fit starved of nodes, reported as a field that did not want struts. Hand the whole solid to a maximal-ball packing instead; it costs one sort.
- [scope: reading a member radius off a binary distance transform | confidence: high | evidence: empty-light-4558] The transform is **biased, and the bias reverses with the boundary**. On a synthetic 8 mm cylinder whose deepest cell centre is a true 7.293 mm from the surface, the binary transform reads 7.616 and the textbook half-cell correction gives 7.116 — and a strut of 7.1 covers `(7.1/8)² = 79%` of the cylinder it was fitted to, so a *perfect* fit to a *perfect* strut failed a 0.85 coverage gate. Interpolate the **density** onto a half-cell grid first; the correction is then a measurement, not a derivation (convex cylinder −0.069 cells, slab +0.25, flat domain face +0.125, so a quarter of a fine cell leaves everything inside 0.194 cells).
- [scope: fitting a graph to a connected field | confidence: high | evidence: empty-light-4558] **Delaunay plus a radius floor loses connectivity the field has.** On the cantilever the field is one component of 2916 cells and the bars thicker than one cell split the fit into 73 + 9 + 9 + 3 + … nodes, orphaning the tip load — which then reads as "this mount is disconnected" about a structure that is not. Add the thin bars back with Kruskal on `min(r0, r1)` until nothing more joins two components, and report which had to be promoted.
- [scope: placing an anchor node in a mounting region | confidence: high | evidence: empty-light-4558] **A pad's centroid is routinely on its own rim**, because the pad is a ball or a slab *intersected with the carved solid*. The cantilever's tip anchor landed one cell from the surface, where the transform reads a single cell, and every bar into it was pruned for being thinner than a member. Take the cells within 20% of the region's deepest and the one nearest the centroid among those.
- [scope: a fully-stressed-design sizing loop | confidence: high | evidence: empty-light-4558] Two things, both of which made it diverge before they were fixed. **A joint written `max(current, incident)` can only grow**, so every pass ratchets the part heavier whatever the mass correction asks: a 40.6 g target settled at 45.2 g with the controller pulling the other way. A joint has the size of the members it joins. And **the redistribution is not volume-neutral on its own** — renormalise it against its own analytic volume *before* the measured-mass correction, or the two corrections fight and neither converges. The renormalisation has to bisect rather than solve, because members go as `r²` and joints as `r³` and both are clipped.
- [scope: naming a face of a fused lattice with an ADR-029 selector | confidence: high | evidence: empty-light-4558] A fitted lattice **has no flat face anywhere**, so a mounting interface must be emitted as its own `part.box` snapped to the blank's plane. Even then the selector needs four keys: `geometry_type` + `normal` still catch the flat end cap of every `part.cone` and `part.cylinder`, `near_point` narrows to the pad, and **`min_area`** separates the pad from the caps that survived the boolean. Measured, a `near_point` of 18.7 mm with no area band caught more than one face and the engine refused the whole script for cardinality.
- [scope: moving analysis work in-engine | confidence: high | evidence: honest-basin-6365] Superseded in part. S3 **is** authorised now, for exactly two ops (ADR-144, ADR-145), and `docs/VISION.md` carries the amendment. What still holds: anything further is a fresh decision, and **tet meshing is not a candidate** — `libSMESH` and `libNETGENPlugin` ship in the payload but `Fem`, the Python binding to volume meshing, is gone, and `MeshPart` exposes Netgen for surface meshing only. A structured grid needs no mesher.

## Provenance

- fair-beacon-5964 — S0: the tree, its contract, the hex core and its three verifications, the rollout-measured load case, and the two voxelisation bugs worth keeping
- jolly-shore-2511 — S1: the search driver, why it drives the CLI rather than importing it, the two caches, and what is deliberately still unpinned
- eager-trail-8160 — S2: SIMP on S0's own grid, marching tetrahedra welded on grid edges, the corrected solver limit, and the two numbers that were being computed about the wrong field
- honest-basin-6365 — S3: the checkpoint that chose a diagnostic over four repairs, `part.stress` pinned equal to the offboard solver, and the staging argument that did not survive contact
- modest-spark-7806 — S4a: spike zero's blended-fuse measurement and the three findings it made, plus the four opt-in field keys and what each of them cost
- empty-light-4558 — S4b-d: the fit, the emitted script, the sizing loop, the compliance-ratio verdict, and the four things that were wrong first
