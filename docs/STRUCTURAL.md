# Structural analysis, topology optimisation and shape search

Verified against source: 2026-08-11. Provenance: `[Cadex-new]`.
Slices **S0–S4, all closed.** ADR-141 authorises the tree, ADR-142 closes S1,
ADR-143 closes S2, ADR-144/ADR-145 close S3 — the two halves that earned their
way in-engine — and ADR-146/ADR-147 close S4, which is where the loop stops
ending in a mesh. `analysis/README.md` is how to run the offboard side.

This is the third vertical to get its own arc doc, after `docs/MUJOCO.md`
(dynamics and control, M0–M9) and `docs/ORGANIC.md` (organic modelling,
O0–O3). It follows their convention: numbered slices, each a resting place,
each recording what was measured rather than what was expected.

## 0. What this is for

Three jobs, all real, in the order they get harder:

1. **Lighter printed parts.** Cut mass and print time and keep a safety
   factor. The binding constraint is usually not stress.
2. **Robot legs.** Parts inside a MuJoCo mechanism, where mass feeds back
   into the dynamics the policy has to control. A leg that is 30% lighter is
   a different control problem, not the same one done better.
3. **Shape search.** Sweep or evolve declared parameters against an
   objective and let the search pick the shape.

And one decision that shapes everything below: **staged, outside the engine
first.** S0–S2 add no engine code, no protocol change and no payload bytes —
that held, and S2 added no new pinned dependency either. S3 is the question
of what earned its way in, answered with S2's output in hand rather than in
anticipation.

## 1. Status

| Slice | What it is | Status |
|---|---|---|
| **S0** | A stress number we can trust | **closed** (ADR-141) |
| **S1** | The search driver | **closed** (ADR-142) |
| **S2** | Topology optimisation | **closed** (ADR-143) |
| **S3** | Bring the useful part in-engine | **closed** (ADR-144, ADR-145) |
| **S4** | Generative design that ends in a **script** | **closed** (ADR-146, ADR-147) |

## 2. What the repository already gave us

More than a fresh look suggests, and this is the part that shaped the plan
most. All of the following was measured, not assumed.

**The sweep loop is a designed feature.** `docs/CLI.md` §1 describes this use
case by name, FEA included: an expensive model turn authors a *parametric*
script once, and a cheap loop then sweeps its parameters with no model in
the loop at all, while an external simulator feeds numbers back.
`docs/VISION.md:151-158` makes the same commitment as the justification for
`cli/` existing. So the outer loop of every optimisation here is
`./cadex params --set k=v --out DIR --json`, and it shipped long ago.

**The search space is already machine-readable.** `params()`/`num()` carry
`min=` / `max=` / `unit=`, and those reach a client as `param_specs` through
`inspect scope="script"` (`CadexInspection.py:305-308`, produced at
`cadex_project_worker.py:822`). An optimiser can read a project's own
bounded search space over the protocol with **zero engine change**.

**numpy and scipy already ship in the payload** — 23 MB and 50 MB, measured
in `build/engine/cadex-engine-0.0.0-macos-arm64`. `trimesh`, `skimage`,
`pyvista`, `meshio`, `gmsh` and `vtk` do not. So a pure numpy/scipy solver
costs **zero new payload bytes** if it ever moves in-engine.

**CalculiX is in the pixi environment and pruned out of the payload.**
`pixi.toml:12` has `calculix = "*"`; `.pixi/envs/default/bin/ccx` is 5.7 MB
and reports 2.23. `package/engine/build_engine_payload.sh:82` keeps exactly
four binaries — `freecadcmd`, `FreeCADCmd`, `CadexGeometryWorker`, `python`
— so `ccx` is dropped. **Leave it dropped.**

**The `Fem` tree is deleted, not disabled.** `docs/FREECAD.md:106-114`:
`Fem` went in Phase 1 batch A (ADR-007), and commit `e85fe5ea` removed 3,589
files including the NETGEN find logic. There is nothing to re-enable.

**Nothing computes stress and there is no material stiffness.** Zero hits for
`stress`, `strain`, `von_mises` or `yield` across the engine. Bodies are
rigid by construction and `assembly.body` carries **density only**.

**An STL already comes home with zero engine change.**
`_ASSET_SUFFIXES = {".stl", ".obj", ".ply"}` (`CadexScriptedRuntime.py:120`),
so an S2 result arrives through `put_asset` and is read by
`mesh.import_file` — the path an imported STL always travelled.

**`part.measurement` is the template for a geometry-free result** (ADR-139,
`cadex_part_api.py:2596`): a declared output that carries no geometry and is
recomputed from the shape rather than remembered. A stress result is the
same species of thing, and S3 should copy it rather than invent.

**Voxelisation is free.** `Shape.isInside` exists
(`src/Mod/Part/App/TopoShapePyImp.cpp:2123`) and `CadexRouting.py` already
runs A* on a 26-connected voxel lattice (`_astar` at :300-363), so the
vocabulary is not new here either.

## 3. Slice S0 — a stress number we can trust

**Closed.** ADR-141. `analysis/`, five files, no engine code, no protocol
change, no payload bytes.

`analysis/README.md` is the usage. This section is what was *measured*.

### 3.1 The element choice is the load-bearing one

A fully-integrated trilinear hex (C3D8) shear-locks in bending: it cannot
bend without parasitic shear, so it reports a part **stiffer than it is** —
the direction that flatters it. Measured on the cantilever benchmark:

| Element | 5.0 mm grid | 2.5 mm grid |
|---|---|---|
| C3D8 (fully integrated) | 5.1% stiff | 5.1% stiff |
| **C3D8I** (Wilson incompatible modes) | **0.9%** | **0.9%** |

So the element carries three incompatible modes, statically condensed at
element level. Two properties make that nearly free here:

* every element of a structured grid is geometrically identical, so the
  condensed 24×24 matrix is computed **once**;
* condensation commutes with a uniform scaling of the element energy, so the
  same matrix is reusable under a SIMP density in S2.

`--element c3d8` selects the locking element. It exists so a test can
*measure* the difference rather than assert it.

### 3.2 The grid is fitted to the part, and that is not a nicety

Centre-sampled voxelisation of a 10 mm bar at 1.875 mm keeps five cells and
throws away 6% of the height. A beam's stiffness goes as the cube of its
height, so a refinement sweep on an unfitted grid was solving a differently
shaped beam at every level: tip deflection went **1.14 → 1.45 → 1.21 mm**
and there was no convergence to read at all.

Fitting each axis to the bounding box — `element_mm` sets how many cells go
across, the cell size is then the extent divided by that count — makes the
volume exact at every level and the sequence monotone. Cells become very
slightly anisotropic, which the element handles because its spacing was
always a 3-vector.

### 3.3 The verification, which is the actual deliverable

**A cantilever against its closed form.** 100 × 10 × 10 mm, PLA, 10 N at the
tip, Timoshenko rather than Euler-Bernoulli because at L/h = 10 the shear
term is about 1% and dropping it would put a real error inside the
tolerance.

```
closed form   1.15218 mm
C3D8I         1.14184 mm   0.9% low, monotone over three levels
```

**Recovered stress against `M y / I`.** At midspan, at the centroid of the
top element row — the fibre the element actually sits at:

```
h = 2.50 mm   fibre z = 8.750   FEA 2.2500   theory 2.2500
h = 1.25 mm   fibre z = 9.375   FEA 2.6250   theory 2.6250
```

**A refinement sweep that says what settled and what did not.** Displacement
converges. `p99` converges. **Peak von Mises does not, and must not** — a
clamped face is a genuine stress singularity with no limiting value, so it
grows with every refinement for ever:

```
h(mm)   elements   displacement   peak vM   p99 vM
2.500        640      1.13916      5.3790   5.3389
1.962       1325      1.14073      5.6440   5.2279
1.422       3479      1.14184      6.1237   5.3163
```

A report that called that peak converged would be lying, so the report
declares `displacement_converged`, `p99_converged` and `peak_converged`
separately.

**CalculiX, at arm's length, as a second implementation.** This is the
answer to ADR-129 — a plausible-looking result survived being written down
and was wrong, and what caught it was a second method.
`analysis/calculix.py` writes the *identical* grid (same nodes, same corner
order, same held degrees of freedom, and the **same assembled force
vector**, so a disagreement cannot be a disagreement about the load) as a
`.inp` deck, runs `ccx` 2.23 as a subprocess and reads the `.dat` back.

```
displacement     4.4e-7   relative
von Mises        5.4e-8   relative
worst component  5.4e-8   relative
```

`.dat` rather than `.frd` deliberately: `*NODE PRINT` and `*EL PRINT` write
whitespace-separated text, and `.frd` is a fixed-column format whose parser
is the kind of code that is wrong for a year.

### 3.4 The load case measured from a rollout

This is what makes the robot-legs job tractable, and it needs **nothing new
from the engine**. `mj_rnePostConstraint` fills two arrays nothing in the
engine reads:

* `data.cfrc_int[body]` — the 6-D joint reaction wrench between a body and
  its parent;
* `data.cfrc_ext[body]` — the 6-D external wrench, contact and applied.

So the load case for "is this thigh strong enough" is the worst wrench that
body saw across a rollout, read out of the same MJCF `assembly.mjcf` already
exports. `contact_force` being a *deferred engine observation*
(`CadexDynamics.py:5532`) does not matter, because this runs offboard in
stock MuJoCo.

`analysis/loads_from_rollout.py` does not run a policy. It replays a
published trace — schema `cadex-assembly-simulation-trace-v1`, the one
`assembly.rollout` writes — by holding each frame's `actuator_commands` over
that frame's interval, and then **checks its own replay** against the poses
the trace recorded. Measured on a two-link leg: a trace sampled at the
control rate replays to **0.0 mm**, and the same motion recorded half as
often drifts **142 mm** and is reported as a different motion.

That check is why the wrench is trustworthy. It is ADR-129's lesson applied
to a second thing: the number is not "what MuJoCo says if you feed it
something plausible", it is "what MuJoCo says on a trajectory that
demonstrably is the one the policy flew". **Author the rollout at
`frames_per_second` equal to the control rate when you intend to read loads
off it.**

Two details that would be silently wrong if left alone, and are not:

* MuJoCo's `cfrc_*` are **com-based** — the torque is about
  `subtree_com[body_rootid[body]]`, not about the body. It is moved onto the
  body's own centre of mass here (`t_p = t_c + (c - p) × F`). Left alone,
  the forces would still check out and the moments would be wrong by
  `r × F`, which on a leg is the whole number. A statics test pins this: at
  rest the reaction at the knee is the shank's weight and carries no moment.
* Frame indexing. The engine writes an untimed `input` frame, then an
  **unstepped** `solver_output` frame at t=0 with no `actuator_commands`,
  then one frame per action. Being one frame out here was the first thing
  the replay-fidelity check caught.

### 3.5 One bug worth writing down

The parity fill lost the whole `x = y` diagonal of a cylinder — 11 columns
of a 20-cell layer, a 4.5% volume error. A cap tessellated as a triangle fan
gives every radial edge to two triangles, so a ray meeting one is counted
twice and the column comes out hollow. The sample-point nudge that was
supposed to prevent it used the **same** irrational fraction on x and y, and
so could not move a point off that diagonal.

It was visible only after a float32 round trip through an STL, which changed
which points landed exactly on an edge — the worst way for a bug to be
visible. Two fixes, and the second is the one that is exact rather than
merely unlikely:

* a different irrational nudge per axis;
* crossings that coincide within a fraction of a nanometre are collapsed to
  one, because a ray through a shared edge crosses the surface **once** and
  both triangles report the same height.

The regression test compares a float64 fill against a float32 one and
requires them to agree.

## 4. Slice S1 — the search driver

**Closed.** ADR-142. `analysis/search.py`, and again no engine code, no
protocol change and no payload bytes.

Sweep or optimise a project's declared parameters against an objective, with
no model in the loop. This is the loop `docs/CLI.md` §1 and
`docs/VISION.md`:151-158 describe as the reason `cli/` exists at all, so the
outer half of it has shipped since Phase 9; S1 is the part that decides
where to look next.

### 4.1 Two things made it small

**The design space is already machine-readable and already on disk.**
`params()`/`num()` carry `min` / `max` / `step` / `unit`, and the collected
specs are cached in the project's own `script.json` — which is what
`inspect scope="script"` serves them out of. So reading the bounds is a file
read, and needs nothing running.

**An evaluation is a subprocess.** `./cadex params --set k=v --out DIR
--json` is documented and test-pinned, and one rebuild of a small parametric
bracket measured **0.7 s**. A 16-point grid with an FEA objective on every
point ran end to end in **12.7 s**.

### 4.2 Why a subprocess rather than importing the client

Importing `cli/cadex_cli/client.py` is allowed — `cli/` is engine-side and
LGPL, so no boundary is crossed, and the plan named it as an option the
`cdx-rl` location did not have. It was still the wrong choice.

Driving the CLI keeps this tree's whole discipline intact: `analysis/`
imports nothing from the engine, reports `cadex_importable` false, and needs
no view on the protocol at all. It also buys **crash isolation per
evaluation**, which is what you want on evaluation 173 when a rebuild
segfaults rather than refuses. The cost is one process spawn per design
point, which the measurement says is noise next to the rebuild.

### 4.3 Two caches, and they are not the same cache

* On the **parameter vector**: a design point already evaluated is not
  rebuilt. That is the free one, and snapping every value onto its declared
  `step` first is what stops it missing on two values that are the same
  control position.
* On the **`digest`**: two *different* parameter vectors can produce the same
  model — a control that rounds away, a feature that clamps, a parameter
  declared for a feature not written yet — and the digest is the only thing
  that says so. The rebuild still happens, because only the engine can say
  the digest is unchanged; what it skips is the **objective**, which is the
  expensive half when the objective is an FEA solve. Test-pinned with an
  unused declared parameter: two design points, two rebuilds, **one**
  objective evaluation.

Compare `digest`, never the files (`docs/CLI.md`:126-131): STEP embeds a
wall-clock timestamp in `FILE_NAME`, so two exports of an identical model
differ byte for byte across a second boundary.

### 4.4 One fixed grid inside a search

S0's refinement sweep exists because a single grid is not a *measurement*.
Inside a search a single grid is the right thing anyway: what a search needs
is a consistent **ranking**, and a fixed grid gives every candidate the same
discretisation bias, where a per-candidate adaptive sweep would let the
discretisation move between two designs being compared. So `refine` defaults
to 1 and the report says so in a `note` it always carries. **Re-run the
design you pick through `cadex_stress.py` properly.**

### 4.5 What it does with what comes back

* **The Pareto front is computed from the evaluated points**, not produced
  by the search — plain numpy over the non-dominated feasible set. That is
  what lets `grid` and `random` answer a genuinely multi-objective question
  with none of the multi-objective machinery.
* **A constraint marks a point infeasible rather than dropping it.** It is
  information about the space.
* **A refused design point is information too.** `docs/CLI.md` gives exit 3
  its own meaning precisely because a refused script is a modelling problem
  rather than an infrastructure one, so the search counts them and carries
  on. A sweep that aborted on the first zero-thickness plate would never map
  anything.
* **Every trial is one JSON line in `<out>/trials.jsonl`**, and `--resume`
  reads it back. No database and no server; `tail` works. A second run into
  a directory that already has a log is refused without `--resume`, because
  appending would silently make the report a mixture of two searches.

### 4.6 The measurement, on a real bracket

Three parameters, a 4×4 grid over two of them, mass against p99 von Mises
with a 12 MPa cap — 16 real rebuilds and 16 FEA solves in **12.7 s**:

```
wall=2.00 rib= 8.50 ->  17.11 g,  6.42 MPa
wall=2.00 rib=14.50 ->  26.04 g,  2.56 MPa
wall=2.00 rib=20.00 ->  34.22 g,  1.40 MPa
wall=5.50 rib=14.50 ->  33.85 g,  2.41 MPa
wall=5.50 rib=20.00 ->  42.04 g,  1.31 MPa
```

A five-point front, and the physics is the physics: a deeper rib is stiffer
and heavier, so mass and peak stress genuinely conflict and the answer is a
front rather than a winner. That is the case S1 was specified for.

### 4.7 What is deliberately not built

**Optuna and pymoo are not dependencies.** `grid` (full factorial), `random`
(a Latin hypercube in four lines of numpy) and `scipy` (differential
evolution) need nothing that is not already installed, and asking for either
of the other two refuses with the reason rather than pretending the plan was
malformed. Which one earns a pin is a question to settle with a measurement
from the three that are free — the survey's argument for Optuna (ask/tell
suits a subprocess evaluator, and its SQLite storage is a free resume) is
answered here by the trial log, and the argument for pymoo (a real Pareto
front) is answered by computing the front from the evaluated set.

**Parallel evaluation.** The project takes a lock, so two rebuilds of one
project cannot overlap; running N workers means N copies of the project.
At 0.7 s a rebuild that is 500 design points in six minutes, so it is not
worth the machinery yet. The report carries per-trial wall time, which is
what will say when it is.

## 5. Slice S2 — topology optimisation

**Closed.** ADR-143. `analysis/topology.py`, and once again no engine code,
no protocol change and no payload bytes — and, this time, **no new pinned
dependency either**: `analysis/requirements.txt` is still three lines.

SIMP on the **same hex grid S0 already built**; that is the payoff of the
stack choice cashed in. S2 is S0's solver in a loop with a density variable,
a filter and an optimality-criteria update.

### 5.1 Four edits to the solver, and S0 did not notice

`solve()` split into `prepare()` — everything a density cannot change: the
element matrix, the pruned occupancy, the node numbering, the held degrees
of freedom, the assembled force vector, the free-DOF index — and
`solve_system()`. The assembly gained a density vector, CG gained a warm
start, and `_DIRECT_DOF_LIMIT` came down. **S0's 27 tests pass unmodified**,
which is the evidence that the split is a split rather than a rewrite.

The density lives in exactly one line. It was
`data = np.tile(flat, len(block))` — every element gets the same 24×24
matrix — and it became `data = (scale[:, None] * flat[None, :]).ravel()`.
That is the whole of what makes S0's solver a SIMP solver, and it is
legitimate with C3D8I because **static condensation commutes with a uniform
scaling of the element energy**. Scaling every block of the element energy by
`s` scales `Kcc`, `Kci` and `Kii` alike, and
`s·Kcc − (s·Kci)(s·Kii)⁻¹(s·Kci)ᵀ` is exactly `s` times the unscaled
condensed matrix. §3.1 claimed that property when it chose the element; a
test now asserts the two assembled matrices agree to 1e-9 relative rather
than taking the algebra on trust.

### 5.2 One measurement that was wrong in the file all along

`_DIRECT_DOF_LIMIT` was 60,000. Measured on the same laptop that set it:

| free dofs | 21,800 | 47,000 | 158,000 |
|---|---|---|---|
| direct (`splu`) | 1.22 s | 7.22 s | — |
| **CG + Jacobi** | **0.24 s** | **0.65 s** | **3.13 s** |

So the old limit sent every problem in the interesting range to the slower
solver — 3× at 21.8k, 11× at 47k. It is 10,000 now, with that table in the
comment beside it. An S0 improvement that S2 paid for.

And what a run costs, so nobody has to wonder whether this needs a GPU box:
one iteration is about **0.8 s at 13.5k elements** and **3.7 s at 48k**, so a
100-iteration run is one and a half to six minutes on a laptop. It needs no
GPU box and gets none.

### 5.3 Marching tetrahedra, and the bug the parity argument nearly hid

Density field → geometry is hand-written, about sixty lines, and that is a
decision rather than an economy. `scikit-image` would have been a fourth pin
for one function. A tetrahedron's four vertices admit **no ambiguous case** —
sixteen sign patterns, none of which two different surfaces could separate —
where marching *cubes* has exactly that hole and produces non-manifold output
through it. And an intersection point is identified by **the grid edge it
lies on**, so two tetrahedra sharing an edge produce the same vertex *index*,
not two vertices a nanometre apart that a welding pass then has to guess
about. Watertight by construction rather than by tolerance.

The winding is a parity argument on the vertex order, and a parity argument
only means anything against a fixed handedness. **Three of the six natural
tetrahedron listings are left-handed.** With them left so, the surface came
out topologically closed — zero boundary edges, zero non-manifold edges — and
with half its triangles inside out, so the closure check passed and the
enclosed volume came out as exactly `0.0`. That is the good version of a
winding bug: an assertion that could not miss it. The six listings are
oriented at import now, and the test asserts each determinant is positive.

What the extraction is worth, against a sphere whose volume is known:

```
cells across   marching tets    Taubin    plain Laplacian
    10            -4.46%        +0.52%        -19.9%
    20            -0.68%        +0.19%        -4.96%
    40            -0.16%        +0.06%        -1.27%
```

It converges, and Taubin smoothing does not shrink the shape while the plain
Laplacian everybody reaches for first eats a fifth of it at the coarsest
grid. `|μ| > λ` is the whole trick and the third column is why it is not
optional.

Decimation is deliberately **not** written here: `mesh.decimate` already
exists in-engine, and a script that wants fewer triangles can call it — at
the price the tree already documents, which is that a decimated tree is
fingerprint-stripped and `part.shape_from_mesh` refuses it.

### 5.4 Two numbers that were being computed about the wrong field

**The volume constraint.** The optimality-criteria bisection first
constrained `sum(x)`, the design variable — and a normalised density filter
does not preserve a sum, so the *reported* volume fraction landed 1.4% off
the declared one. Because the filter is linear the physical volume is exactly
`x · dV/dx` with `dV/dx = Hᵀ(1/d)`, one convolution computed once at
construction, so the bisection can enforce the real constraint and stay
arithmetic instead of running two hundred convolutions an iteration. It holds
to 1e-6 now, asserted at every iteration rather than at the end.

**Discreteness.** A density filter of radius R smears a perfectly binary
design over a band of width R, so a member thinner than 2R is grey right
through its core however well the run converged. Measured on the cantilever:
a design variable of 3833 cells at 0, 1638 at 1 and 129 anywhere else — a
non-discreteness of **0.017**, which is as resolved as SIMP gets — has a
*density* non-discreteness of **0.32**. Reading the second number as a
quality score says the run failed when it did not. Both are in the report and
the warning is spent on the first. What makes that safe rather than a matter
of taste is that the extracted surface is the `ρ = 0.5` level set and the
grey band is symmetric about it: on that same run the cells above the level
set came to 1683 against a density integral of 1680.

### 5.5 The verification

In the order it catches things:

1. **A finite-difference sensitivity check.** `dc/dρ = −(dscale/dρ) uₑᵀk₀uₑ`
   is four terms that can each be wrong while still producing a
   plausible-looking structure — the sign, the exponent, whether `k₀` is the
   condensed matrix, and whose energy it is. A central difference on a
   *random* density (a converged one is nearly binary, where `ρ^(p−1)` is
   flat and a wrong exponent would hide) agrees to **3e-6**. This is S2's
   second method, the way CalculiX was S0's.
2. **A 3-D cantilever and an MBB beam.** The volume constraint holds to
   1e-6; compliance falls once the continuation settles; and the design
   beats a uniform field of *identical* volume solved by the *same* solver at
   the *same* penalty by more than **4×** — measured at 7.3× on the
   self-check. The MBB beam puts more material in its top and bottom thirds
   than in its middle, which is the picture in every textbook and not a
   coincidence of one implementation.
3. **Mesh independence.** A 4 mm filter radius at 2.5 mm and at 1.5 mm cells
   agrees about **95.5%** of the solid/void decision and about the stiffness
   achieved to 2.3%.
4. **Extraction**: watertight, consistently wound, the right volume — and
   re-voxelised with **S0's own voxeliser** it reproduces the fill. Two parts
   of one tree checking each other, and the parity fill of §3.5 asked about a
   shape far harder than the boxes S0 tests it on.
5. **A real project.** STL → `put_asset` → `mesh.import_file` → rebuild,
   against a real cadexd child: 3228 triangles in, a mesh artifact out, and
   the same digest on a second rebuild.

### 5.6 What is deliberately not built

* **No printability constraint.** Overhang angle and minimum wall thickness
  are not built and are not planned: supports handle overhangs, and a
  constraint nobody needs is a constraint that distorts the result. The open
  question §5 used to carry — optimiser or redesign step? — is answered
  *neither, for now*. The **filter radius** stays and is not a manufacturing
  parameter: without it SIMP checkerboards, because the discretised problem
  has no minimiser and the answer changes with the grid. It is what makes the
  problem well-posed, which is why mesh independence is what it is tested on.
* **No stress-constrained TO.** SIMP minimises compliance, and "find where
  material can be removed safely" is a stress question. The ground is thin:
  the maintained permissive option is `beso` (LGPL-3, drives the same `ccx`,
  failure-index criterion), and the standard Python MMA implementation
  `mmapy` is **GPL-3** and barred from this tree by ADR-141's own test.
  Recorded as an open question rather than built. Run the extracted shape
  back through `cadex_stress.py` — that is a real second measurement rather
  than a number the loop produced about itself.
* **No new asset suffix**, so Save-As cannot silently drop anything. A
  `.cxdensity` or a sidecar receipt would be dropped — the exact bug ADR-046
  recorded and ADR-138 fixed for `.cxpart`, still open today for
  `.cxpolicy`. The density field and the receipt stay offboard, in the run
  directory. And since `compute_project_digest` does not walk `assets/`,
  **nothing verifies an STL's bytes** unless the script publishes the
  imported mesh as an output — which carries `geometry_sha256`, the sorted
  exact vertex set, and does reach the digest. So the script publishes it.
* **No mesh → parametric body.** `part.shape_from_mesh` makes a shell of
  triangle faces, not an editable feature tree. The realistic loop is **TO
  informs the redesign**: the agent reads the optimised shape and rewrites
  the script. That is VISION principle 3 holding, not a limitation to route
  around.

## 6. Slice S3 — in-engine

**Closed.** ADR-144 (S3a) and ADR-145 (S3b). Authorised by the owner, and
`docs/VISION.md`'s "FEM … is out of scope" line got an **amendment** rather
than a workaround — on the template the doc already contained two paragraphs
above it, where interactive mesh editing was ruled out and then arrived as
`part.loft_cage` on a declared table (ADR-127).

Three facts make that honest: FreeCAD's `Fem` tree was **deleted, not
disabled** (3,589 files, commit `e85fe5ea`), so nothing is resurrected; there
is **no sixth domain**, because it is one primitive on `part` and by VISION's
own test costs no protocol op; and the expensive half stays offboard.

### 6.1 S3a — one op, and it is a diagnostic

The plan named a likely set — `smooth`, `fillupHoles`, `harmonizeNormals`,
`fixSelfIntersections` — and said the op set was to be decided by **S2's
measured output rather than by anticipation**, with "fewer, or none" an
allowed answer. A real S2 result, through the engine's own `Mesh` kernel:

| | raw marching tets | + Taubin | decimate(0.5) | decimate(0.9) |
|---|---|---|---|---|
| facets | 13320 | 13320 | 7248 | **7248** |
| `hasNonManifolds` | false | false | false | false |
| self-intersections | **1** | **0** | 0 | 0 |
| `isSolid` | true | true | true | true |
| components | 1 | 1 | 1 | 1 |
| non-uniformly oriented facets | 0 | 0 | 0 | 0 |

Every anticipated repair op is answered by a column. Nothing to fill, nothing
to harmonise, and the smoothing is already done offboard by a Taubin pass
that does not shrink the shape. **So none of them earned their place**, and
building them anyway would have been a capability against an imagined input.

What earned its place is `mesh.check`, and the same table says why:

* **A combinatorial closure check cannot see a self-intersection.** The raw
  marching-tetrahedra surface has every undirected edge in exactly two
  triangles and every directed edge exactly once — and one pair of facets
  passing through each other. Those are different properties, and §5.3's
  checker is structurally incapable of noticing the second.
* **`decimate` does not say what it did.** A 50% and a 90% reduction request
  both returned 7248 facets: the tolerance bound is what binds. This section
  used to pose exactly that question, and it had no answer until now.

It never repairs. A repair op mutates geometry and reports nothing, which is
the wrong shape of answer to "is this sound" — the script owns the geometry,
so the script decides what to do about the answer.

### 6.2 S3b — `part.stress`, and the bug that was invisible

A declared output carrying a safety factor and no geometry, modelled line for
line on `part.measurement`. Anchored by **ADR-029 selector**, so it follows
the part; every material property required, unit in its name, refusing by
naming materials; `element_mm` a declared budget the engine caps and refuses
above, naming the size that would fit.

**It divides by p99, never the peak.** §3.3 measured that peak von Mises at a
clamped face does not converge and must not — a genuine singularity, growing
with every refinement for ever. Both numbers travel and the payload's own
`note` says which carries the verdict.

**Two implementations, pinned equal by a test.** `analysis/` may not import
the engine and the engine may not import `analysis/`, so the algorithm is
written twice and one test solves the identical cantilever on the identical
grid through both. Measured through a live cadexd at 2.5 mm:

```
tip deflection   1.13916 mm   (closed form 1.15218, 1.1% low)
peak von Mises   5.3790 MPa
p99  von Mises   5.3389 MPa
```

— the same three digits §3.3 records for the offboard solver at that grid.

**And the bug worth writing down, because nothing about it looked wrong.** A
selector resolves to faces; the faces are tessellated; the solver asks which
grid nodes lie on them. **A planar face tessellates to four vertices.** Taking
those as the anchors held the bar at four corner nodes out of twenty-five and
loaded it at four — a different structure, reported with a residual of 2e-11,
no warnings, and every number internally consistent about the wrong problem.
It surfaced as a tip deflection of 1.78 mm against a closed form of 1.15:
soft by 55%, and visible only because the benchmark had an answer to check
against. That is §3.5's lesson and ADR-129's, arriving a third time. The fix
is to sample each face's triangles barycentrically at a third of a cell.

### 6.3 Where the staging argument did not survive contact

`CadexStress.py` was to be staged by filename with `DECLARED_ENGINE_MODULES`
**not** growing, mirroring how `CadexDynamics` stays out of cadexd's import
closure. That mechanism is not available here: `CadexDynamics` is unreachable
because `cadex_assembly_worker` is itself outside the closure, and
`cadex_part_worker` is **inside** it. So the list grows by one, deliberately,
rather than being routed around with an `importlib` trick that would make the
file harder to read in order to make a list shorter.

What is asserted instead is the property that actually costs something:
nothing imports `CadexStress` at module scope, and `CadexStress` imports numpy
and scipy inside its own functions. A `cadexd` that imports
`cadex_part_worker` does not load the solver, and a worker that loads the
solver does not thereby load 73 MB of numerics. **Reachable and loaded are
different questions**, and the guardrail now asks the second one.

### 6.4 What is still not a candidate

**Tet meshing.** `libSMESH` and `libNETGENPlugin` ship in the payload but
`Fem` — the Python binding to volume meshing — is gone from `src/Mod/`, and
`MeshPart` exposes Netgen for *surface* meshing only
(`src/Mod/MeshPart/App/AppMeshPartPy.cpp:576`). A structured grid needs no
mesher, which is one more reason the stack avoids tets entirely.

**Anything with a solve in `cadexd`.** The linear solve lives in the
sandboxed worker behind a deferred import, and that is where it stays.

## 7. The loop, closed

End to end, with everything above in the tree:

1. Declare a blank and a load case; `analysis/topology.py` carves it.
2. A watertight STL comes home through `put_asset` — no new suffix, so
   Save-As cannot drop it.
3. `mesh.check` says whether what arrived is sound, in the script, where the
   script can act on it.
4. The agent reads the shape and **rewrites the script parametrically**. The
   optimiser never authors geometry the script does not own (VISION principle
   3); `part.shape_from_mesh` makes a shell of triangle faces, not an editable
   feature tree, so TO informs the redesign rather than replacing it.
5. `part.stress` verifies the redesign in-engine, following the parameters.
6. `analysis/search.py` sweeps it, using the digest cache to skip an objective
   when two parameter vectors produce the same model.
7. Re-run the winner through `analysis/cadex_stress.py` for a refinement sweep
   and a CalculiX second opinion, because a single grid inside a search is a
   *ranking* and not a measurement (§4.4).

Every step of that existed or was built here, and none of it needed a button:
the agent authors, dispatches and declares; the human judges.

## 8. Slice S4 — generative design that ends in a script

S0–S3 closed the loop and the first real render showed what it cost. The
carved bracket was **structurally right and visually wrong** in four
separable ways: the thin fins at the loaded end were not structure, the
facets were the grid, Taubin had rounded the flat mounting face, and the
blobbiness was SIMP itself. The first three are defects. The fourth is the
algorithm — and it is where the opportunity was.

**What S4 is.** The optimiser finds the *topology*; the deliverable is a
**feature tree a human and an agent can both edit**. Every generative-design
tool on the market ends in a mesh you cannot edit — nTop, Fusion, Altair.
Move the hole 2 mm and you re-run the optimisation. `docs/VISION.md`
principle 3 already demanded otherwise; S4 makes it literal.

ADR-146 records S4a and spike zero; ADR-147 records S4b–d.

### 8.1 Spike zero, which was authorised to sink the slice

`docs/ORGANIC.md` §1 is why it ran first: the robot wolf failed twice trying
to weld sixteen fused lofts, and `part.fuse(blend=)` was built to close that
gap but had never been asked to blend forty-way. The measured table is in
ADR-146. Three findings, in the order they arrived:

1. **`part.cone` refuses equal radii.** Every strut of the first lattice was
   refused before a blend was attempted. That surface is a cylinder, and the
   emitted `_strut` helper branches on it.
2. **No blend radius survives `blend_on_failure="refuse"`** — not even 0.4 mm
   against a 1.6 mm member. The mode is load-bearing, not a convenience.
3. **`reduce` clears a hand-written lattice at every size to 64 solids in
   under 20 s** — comfortably inside the ~30 s gate. The fallbacks the spike
   was authorised to choose (a pairwise fuse tree, oversized node spheres)
   were not taken.

What did *not* survive is §8.5.

### 8.2 S4a — four opt-in keys on the field

| Plan key | What it does |
|---|---|
| `symmetry: ["y"]` | Mirror-average the filtered sensitivity each iteration. Exact to 9e-16. |
| `extrude: "y"` | Average the sensitivity **and the volume gradient** along one axis. |
| `interface_pad_mm: 3.0` | Dilate every `supports` and `loads` region and hold it. |
| `pin_domain_planes: true` | Keep the vertices that came out on a face of the blank on it. |

All four default off, so an S2 plan carves the same field. `symmetry` is the
largest looks-designed win per line in the file — the eye reads asymmetry as
*error* before it reads anything else — and it halves S4b's job, because a
symmetric field gives a symmetric node set and therefore a symmetric script.
`interface_pad_mm` is a bug fix wearing an aesthetics hat and a prerequisite:
without pads the fins generate garbage skeleton nodes at exactly the places
the loads attach.

The one measurement worth repeating here: **`extrude` needs the volume
gradient averaged too**, or the filter's edge effect comes straight back
through the bisection. Largest column standard deviation of the density on a
40 × 16 × 20 cantilever: **0.105 → 0.0009**.

The documented example grid rises to **1.0–1.25 mm**, which the corrected
`_DIRECT_DOF_LIMIT` already paid for (ADR-143).

### 8.3 S4b — fitting a graph to the field

`analysis/skeleton.py`, offboard under the identical contract as the rest of
this tree. No 3-D thinning: a Euclidean distance transform, whose value *is*
the local member radius, with a maximal-ball packing for nodes and a Delaunay
triangulation for candidate bars. Both are in the pinned scipy 1.17.0, so
`requirements.txt` stays at **three pins**.

Three things were wrong first, and all three are worth knowing:

* **Local maxima are not the medial axis.** A member is a *ridge*, and a cell
  on a ridge is not a strict local maximum. A 3×3×3 maximum filter proposed
  25 cells out of 3500 and the fit covered 0.45 of a part whose members run
  8 to 14 mm thick.
* **The distance transform is biased, and the bias reverses.** A binary
  transform reads 7.616 on a cylinder whose truth is 7.293; the textbook
  half-cell correction takes it to 7.116, and a strut of 7.1 covers 79% of an
  8 mm cylinder — so a perfect fit to a perfect strut failed the coverage
  gate. Interpolating the *density* onto a half-cell grid first, and
  subtracting a quarter of a fine cell, leaves every canonical case inside
  0.194 cells.
* **Delaunay plus a floor loses connectivity the field has.** On the
  cantilever the field is one component of 2916 cells and the thick bars
  alone split the fit into 73 + 9 + 9 + 3 + … nodes, orphaning the tip load.
  The thin bars are added back by Kruskal until nothing more joins two
  components.

**Refusals**, all of them loud and all of them carrying their number: a
support or load region the carve did not reach (naming `interface_pad_mm`); an
anchor not connected to the rest; and coverage below the bar.

### 8.4 Coverage — the gate, and what it actually measures

The bar is **0.85** and the discrimination is real:

| field | solids | coverage |
|---|---|---|
| S4 bracket (SIMP) | 74 | **0.93** |
| A-truss (synthetic) | ~90 | **0.97** |
| cantilever (SIMP) | 134 | 0.76 |
| solid block | 26 | 0.79 |
| hollow box shell | 5 | 0.56 |

But decision 2's stated reason — "a SIMP field often wants a flat web, so
refuse rather than fit plates" — is only half right, and the measurement says
so. **A slab fits fine**: its medial axis is one sheet and coverage comes back
0.90 to 0.97. What fails is a **shell**, several sheets a cell or two thick
meeting at edges — and a SIMP cantilever, which is one. So the gate is a
*fidelity* gate: it says the emitted strut part does not contain the material
the field had. It refuses the right fields, and it is the evidence that would
ask for S5.

### 8.5 S4c/S4d — the script, the loop and the verdict

The emitted script carries three `num()` parameters — `strut_scale`,
`min_radius_mm`, `blend_mm` — and the radii as a plain editable table, because
`num()` is numeric-only and forty parameters is not a search space. **S4 fixes
the topology; S1 tunes the sizes.** Each anchor's mounting pad is emitted as a
`part.box` snapped to the blank's own plane, which is what gives the
`part.stress` selectors a flat face to name — a fitted lattice has none.

The sizing loop is a fully-stressed design on real per-element von Mises, run
on the **rebuilt CAD** every pass: emit → `./cadex script --set` → export STL
→ `analysis/cadex_stress.py` on that. No surrogate and no second physics
model, so a fit that will not build fails on pass one rather than at the end.
A pass that will not build ends the loop rather than the run.

**The verdict on the S4 benchmark:**

```
SIMP optimum      compliance 10.234 N·mm   mass 40.58 g
rebuilt script    compliance  6.042 N·mm   mass 41.07 g
compliance ratio  0.59        bar 1.15     verdict: ship
```

The parametric part is 1.7× stiffer than the SIMP optimum at the same mass —
which is not the fit beating the optimiser, but the grey band a density
filter smears over every member being real material carrying nothing.

**What did not survive contact: the blend.** The plan expected fillets for
free. On a *fitted* lattice `reduce` refuses — it wants one radius that blends
every seam and near-tangent members leave none — and `skip` refuses when
nothing at all blends, which is what the shipped bracket does at
`strut_scale = 1.0` for every radius tried. At `strut_scale = 0.9` a 1.0 mm
blend succeeds. So `blend_mm` stays a declared parameter and the loop drops
it when the kernel refuses: **whether a given lattice blends is a property of
the lattice that only the kernel knows.**

One thing is computed and cannot be read: `part.stress` publishes no geometry,
and `cadex export --json` describes only BREP outputs, so a headless caller
cannot read the safety factor it computed. The check still does its more
valuable job — it is evaluated on every rebuild, so a parameter change that
moves a mounting face until the load case stops resolving fails loudly. A
`cadex` subcommand that serves a non-BREP output's value is separate work.
