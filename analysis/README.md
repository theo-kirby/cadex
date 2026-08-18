# analysis/ — offboard structural analysis

Verified against source: 2026-08-11. Provenance: `[Cadex-new]`. See
`docs/STRUCTURAL.md` slices S0–S4, ADR-141, ADR-142, ADR-143, ADR-146 and
ADR-147.

This directory is **not part of the engine**. CMake never installs it, it is
in no payload, and nothing in it enters `pixi.toml` —
`test_analysis_stress.py` asserts all three, the same way
`test_dynamics_policy_trainer` asserts them for `training/`.

It is the second tree to live at the repository root under the ADR-084
contract, and it is here for the same reason the trainer is: it is a thing
you **copy to another machine**, or run in a venv beside the repo, and its
answers come home as files.

## What it is for

Three jobs, in the order they get easier:

1. **Lighter printed parts** — cut mass and print time, keep a safety factor.
2. **Robot legs** — parts inside a MuJoCo mechanism, where mass feeds back
   into the dynamics the policy has to control.
3. **Shape search** — sweep or evolve parameters against an objective and
   let the search pick the shape.

**S0** produces **one number you can trust**: a peak von Mises stress and a
safety factor for a declared load, with the evidence for believing it
attached. Everything above it needs that first.

**S1** is the loop around it: sweep or optimise a project's declared
parameters against those numbers, with no model in the loop. Together they
do jobs 1 and 2.

**S2** is job 3: `topology.py` carves a declared blank against a declared
load case and hands back a watertight STL. It is S0's solver in a loop with
a density variable — the same grid, the same element, the same load-case
schema — and it added **no new pinned dependency**, because the geometry
extraction is hand-written marching tetrahedra rather than a mesh library.

## What it reads and what it writes

Like the trainer, **nothing here speaks the cadexd protocol**. Nothing
imports the engine, and every entry point reports `cadex_importable` false.

`cadex_stress.py`, `loads_from_rollout.py` and `calculix.py` go further and
never spawn anything either: they read files off disk and write one JSON
report.

`search.py` is the one that has to reach the engine, because a design point
is a rebuild. It does so by running **`./cadex params --json` as a
subprocess** rather than by importing `cli/cadex_cli/client.py` — which is
allowed, `cli/` being engine-side and LGPL, and was still the wrong choice.
Driving the CLI keeps this tree with no view on the protocol at all, and
buys crash isolation per evaluation, which is what you want on evaluation
173 when a rebuild segfaults rather than refuses.

```
a solid          bracket.stl | .ply | .obj        what ./cadex --out writes
                 bracket.step                     with pythonocc-core installed
a load case      loads.json                       schema cadex-analysis-load-case-v1
      ->
one report       schema cadex-analysis-stress-v1  exactly one JSON line on stdout
```

**Exactly one JSON line on stdout; the human-readable stream is stderr, and
nothing parses stderr.** ADR-093 measured what happens when a receipt is
taken from a stream something else can write into.

Every entry point reports `cadex_importable`, so a test can assert the
negative. A run where that comes back `true` was not a stock process and
proves nothing about what these files can do with their pinned dependencies
alone.

## The files

| File | What it is |
|---|---|
| `cadex_stress.py` | The hex-grid linear-elastic core and its CLI. Voxelise, assemble, solve, recover stress, sweep the grid, report. |
| `loads_from_rollout.py` | The load case **measured from a rollout**: replays a published trace in stock MuJoCo and reads `cfrc_int` / `cfrc_ext` back out. |
| `calculix.py` | The arm's-length cross-check. Writes the identical grid as a CalculiX deck, runs `ccx` as a subprocess, compares. |
| `search.py` | The parameter search: reads the design space off the project, drives `./cadex params` per design point, scores it, and reports a Pareto front. |
| `topology.py` | SIMP topology optimisation on the same grid, and the marching-tetrahedra extraction that turns a density field into a watertight STL. |
| `skeleton.py` | S4: fits a strut graph to a carved density field and emits a **parametric xscript** for it, installs it through `./cadex script --set`, sizes it against the real FEA on the rebuilt CAD, and reports one number — the compliance ratio against the SIMP optimum. |
| `requirements.txt` | Three exact pins, installed into a venv. Read its comments before adding anything. |

## Running it

```bash
python3 -m venv .venv
.venv/bin/pip install -r analysis/requirements.txt

# Does the install work, and does the solver still know what a beam is?
.venv/bin/python analysis/cadex_stress.py --self-check

# A part and a declared load.
.venv/bin/python analysis/cadex_stress.py bracket.stl \
    --load-case bracket-loads.json --element-mm 1.5 --out report.json

# The same grid, solved by somebody else. Needs ccx, which the repository's
# pixi environment already has -- so run this one under pixi.
pixi run python analysis/calculix.py bracket.stl --load-case bracket-loads.json

# A load case measured from a policy rollout.
pixi run python analysis/loads_from_rollout.py legs-model.xml \
    --trace outputs/legs-simulation-trace.json \
    --body thigh_left --emit-load-case thigh-loads.json

# Sweep a project's declared parameters against those numbers. Needs a built
# engine, because every design point is a real rebuild.
pixi run python analysis/search.py plan.json --out ./sweep
pixi run python analysis/search.py plan.json --out ./sweep --resume

# Carve a declared blank against a declared load case. Needs no engine.
.venv/bin/python analysis/topology.py --self-check
.venv/bin/python analysis/topology.py carve.json --out ./run

# Fit a parametric SCRIPT to that carve, install it, and size it. The fit
# alone needs no engine; the sizing loop rebuilds for real, so it does.
.venv/bin/python analysis/skeleton.py carve.json --run ./run --out ./fit
pixi run python analysis/skeleton.py carve.json --run ./run \
    --project ./bracket --out ./fit --passes 4
pixi run python analysis/skeleton.py --self-check --out ./fit \
    --project ./bracket
```

The suites are `src/Mod/cadex/cadex_tests/test_analysis_stress.py` (S0),
`test_analysis_search.py` (S1), `test_analysis_topology.py` (S2 and S4a) and
`test_analysis_skeleton.py` (S4b–d), and all four run with
`pixi run test-engine`. numpy, scipy, mujoco and `ccx` are all
in the pixi environment, so the numeric half really runs there; S1 drives a
real project through the real CLI and S2's round trip drives a real cadexd
child. They skip cleanly where a dependency or a built engine is absent, and
are written to run from either interpreter.

## Carving a blank (S2)

A topology plan is a `cadex-analysis-topology-v1` JSON file. It reuses
`material`, `supports` and `loads` **verbatim** from the load case above, and
`keep` / `void` reuse the same four region kinds — so a load case you already
wrote is most of a plan:

```json
{
  "schema": "cadex-analysis-topology-v1",
  "name": "bracket",
  "domain": {"box": {"size_mm": [60, 20, 30], "origin_mm": [0, 0, 0]}},
  "element_mm": 1.25,
  "volume_fraction": 0.3,
  "filter_radius_mm": 3.0,
  "penalty": 3.0,
  "iterations": 120,
  "symmetry": ["y"],
  "interface_pad_mm": 4.0,
  "pin_domain_planes": true,
  "material": {"name": "PLA", "youngs_modulus_mpa": 3500,
               "poissons_ratio": 0.36, "yield_strength_mpa": 50,
               "density_kg_m3": 1240},
  "supports": [{"name": "root",
                "region": {"face": {"axis": "x", "at": "min",
                                    "depth_mm": 0.001}}}],
  "loads": [{"name": "tip",
             "region": {"face": {"axis": "x", "at": "max", "depth_mm": 2.0}},
             "force_n": [0, 0, -250]}],
  "keep": [{"name": "boss",
            "region": {"sphere": {"centre_mm": [30, 10, 25],
                                  "radius_mm": 6}}}],
  "void": [{"name": "clearance",
            "region": {"box": {"min_mm": [10, null, 5],
                               "max_mm": [20, null, 15]}}}]
}
```

`domain` is either a `box` — declare a blank and let the loop carve it, which
is the case S2 was specified around — or `{"solid": "part.stl"}`, which is
the same code path with a different starting occupancy and is how you lighten
a part you already have.

Four things worth knowing before you read the answer:

- **`filter_radius_mm` is not a printing parameter.** It is here because
  without it SIMP checkerboards: the discretised problem has no minimiser and
  the answer changes with the grid. Declare at least 1.5 elements; 2 to 3 is
  usual. Overhang angle and wall thickness are **not** built and are not
  planned — supports handle overhangs.
- **Read `measure_of_non_discreteness`, not `density_non_discreteness`.**
  The first is on the design variable and is the one that says whether the
  run resolved. The second is on the filtered density, which is grey in a
  band of width R around every surface no matter how well the run went.
- **`converged` is a real field.** A run that used all its iterations while
  still moving is reported as such, with a warning naming the number. Give it
  more `iterations` rather than believing it.
- **`keep` regions sit above the volume constraint.** They are a promise
  about the shape, so they are held at 1.0 after the filter rather than
  allowed to blur — and the material that adds is on top of the fraction the
  optimiser bisected to. A run with `keep` reports the fraction it actually
  reached and warns that it did; without `keep` the constraint holds to
  1e-6.
- **The answer is a shape to read, not a body to edit** — or hand it to
  `skeleton.py` below, which turns it into a script that *is* editable. Run
  the STL back through `cadex_stress.py` for a stress number either way. The
  optimiser never authors geometry the script does not own.

The four **S4a** keys above are all opt-in and all default off, so a plan
written before them carves the same field (ADR-146):

| Key | What it does |
|---|---|
| `symmetry: ["y"]` | Mirror-average the sensitivity each iteration, so the design comes out symmetric. Holds to 9e-16, and it is the biggest looks-designed win in the file. |
| `extrude: "y"` | Hold the density constant through one axis: a 2.5-D part you can route or laser-cut, not only print. |
| `interface_pad_mm: 4.0` | Grow every `supports` and `loads` region and hold it solid. Without this a load on a thin face gets a **membrane** — correct, and useless as a mounting interface. |
| `pin_domain_planes: true` | Keep the vertices that came out on a face of the blank on it through the smoother, so a mounting face stays flat. |

What comes out of `--out DIR`: `<name>.stl` (the surface),
`<name>-density.npy` (the field) and `report.json` (the receipt). Only the
STL comes home — `put_asset` accepts it and Save-As carries it. The other two
stay here, because a suffix the store does not know is a file Save-As drops.

## Fitting a script to the carve (S4)

`skeleton.py` reads exactly the same plan plus the `--run` directory
`topology.py` wrote, and hands back a **parametric xscript** rather than a
mesh: node and strut tables, mounting pads, a `part.fuse`, and a
`part.stress` check anchored to the blank's own faces so it follows the
parameters. Three `num()` parameters — `strut_scale`, `min_radius_mm`,
`blend_mm` — which is what `search.py` sweeps afterwards. **S4 fixes the
topology; S1 tunes the sizes.**

With `--project`, it also installs the script through `./cadex script --set`
and runs a fully-stressed-design sizing loop: every pass rebuilds through the
real engine, exports the STL and solves it with `cadex_stress.py`, so a fit
that will not build fails on pass one rather than at the end.

Three things worth knowing before you trust the answer:

- **The verdict is one number.** `verdict.compliance_ratio` is the rebuilt
  part's compliance against the SIMP optimum's, at equal or lower mass, and
  `ship` means it cleared 1.15. Below 1 is normal and is not the fit beating
  the optimiser: SIMP minimises compliance over a *grey* field, and the band
  a filter of radius R smears over every member is real material carrying
  nothing.
- **`fit.coverage.fraction` is a refusal, not a score.** Below 0.85 the run
  stops and names the number and the largest place it missed. A strut graph
  cannot hold a shell — measured, 0.93 on a two-footed bracket, 0.76 on a
  cantilever, 0.56 on a hollow box — and a tidy part that is much weaker than
  the one you carved is worse than no part.
- **The blend is a knob to try, not a promise.** `part.fuse(blend=)` will
  often refuse a fitted lattice at *every* radius, and when it does the loop
  ships the part unblended and says so. Sweep `blend_mm` with
  `./cadex params` afterwards; whether a given lattice blends is a property
  of the lattice that only the kernel knows.

## Declaring a load case

```json
{
  "schema": "cadex-analysis-load-case-v1",
  "material": {
    "name": "PLA",
    "youngs_modulus_mpa": 3500.0,
    "poissons_ratio": 0.36,
    "yield_strength_mpa": 50.0,
    "density_kg_m3": 1240.0
  },
  "supports": [
    {"name": "base",
     "region": {"face": {"axis": "z", "at": "min", "depth_mm": 1.0}}}
  ],
  "loads": [
    {"name": "bolt",
     "region": {"sphere": {"centre_mm": [20.0, 0.0, 30.0], "radius_mm": 3.0}},
     "force_n": [0.0, 0.0, -250.0],
     "torque_n_mm": [0.0, 1200.0, 0.0]}
  ],
  "gravity_m_s2": [0.0, 0.0, -9.80665]
}
```

Regions are named **geometrically** — `face`, `box`, `sphere`, `all` —
rather than by a face id, because a face id is a thing the script owns and
this tree has no script. A support may name `axes` to hold only some of
them; a load takes a total `force_n` shared over the region and a
`torque_n_mm` applied as a couple, which is what lets a 6-D wrench out of a
MuJoCo rollout be one load entry.

**`yield_strength_mpa` has no default and never will.** A safety factor
against a strength nobody declared is a number pretending to be a verdict.

## Searching a design space

`search.py` is the loop `docs/CLI.md` §1 was written for: an expensive model
turn authors a parametric script once, and a cheap loop sweeps it. A plan
says what to search, what to measure, and how to look:

```json
{
  "schema": "cadex-analysis-search-v1",
  "project": "./bracket",
  "parameters": ["wall", "rib"],
  "objectives": [
    {"name": "mass_g", "kind": "mass", "density_kg_m3": 1240.0,
     "direction": "min"},
    {"name": "stress_mpa", "kind": "stress", "load_case": "loads.json",
     "element_mm": 3.0, "refine": 1, "field": "p99_von_mises_mpa",
     "direction": "min", "max": 12.0}
  ],
  "search": {"kind": "grid", "levels": 4}
}
```

**The design space is not in the plan.** It is read off the project's own
`script.json`, where `params()`/`num()`'s collected specs are cached with
their `min`, `max`, `step` and `unit` — so a search cannot ask for a value
the script does not offer, and every design point it reports is one a
slider could reach. Name `parameters` to search a subset; omit it for all
of them.

**Objective kinds**: `mass`, `volume`, `extent` (an axis of the bounding
box), `stress` (runs S0 on the design point), and `command` — an external
program run in the output directory whose last stdout line is a JSON object.
That last one is `docs/CLI.md` §1's "an external simulator feeds its numbers
back", and it is how airflow or print-time gets in without this file
learning about either.

**A `max` or `min` on an objective is a constraint.** A point that violates
it is recorded and marked infeasible rather than dropped — it is information
about the space.

**Search kinds**: `grid` (full factorial), `random` (a Latin hypercube), and
`scipy` (differential evolution). All three need nothing that is not already
installed. `optuna` and `pymoo` refuse with the reason they are not pinned:
which of them earns a dependency is a question to settle with a measurement
from the three that are free.

**The Pareto front is computed from the evaluated points**, not produced by
the search — so `grid` and `random` answer a genuinely multi-objective
question with none of the multi-objective machinery. Mass against peak
stress is the case this was built for, and they really do conflict.

### Two caches, and they are not the same cache

- On the **parameter vector**: a design point already evaluated is not
  rebuilt.
- On the **`digest`**: two different parameter vectors can produce the same
  model — a control that rounds away, a feature that clamps, a parameter
  declared for a feature not written yet — and the digest is the only thing
  that says so. Hitting it skips the *objective*, which is the expensive
  half when the objective is an FEA solve. Compare `digest`, never the
  files: STEP embeds a wall-clock timestamp, so two exports of an identical
  model differ byte for byte across a second boundary.

### One fixed grid inside a search

S0's refinement sweep exists because a single grid is not a *measurement*.
Inside a search a single grid is the right thing anyway: what a search needs
is a consistent **ranking**, and a fixed grid gives every candidate the same
discretisation bias. So `refine` defaults to 1 and the report says so.
**Re-run the design you pick through `cadex_stress.py` properly.**

### Resuming

Every trial is appended to `<out>/trials.jsonl` as one JSON line, and
`--resume` reads it back. No database and no server; `tail` works. A second
run into a directory that already has a log is refused without `--resume`,
because appending would silently make the report a mixture of two searches.

Evaluations run **serially**: the project takes a lock, so two rebuilds of
one project cannot overlap. At the measured 0.7 s a rebuild that is 500
design points in six minutes, which is why parallelism is not built. If a
project's rebuild is much slower than that, the report's per-trial wall time
is what tells you it is worth building.

## How to read the report

Four things, in the order they matter.

**1. `convergence`, before anything else.** The default is a three-level
refinement sweep, because a single grid is not a measurement. It reports
`displacement_converged`, `p99_converged` and `peak_converged` separately,
and on almost every real part the last of those is **false** — that is the
report being honest, not the sweep being too short. A clamped face or a
re-entrant corner is a genuine stress singularity: it has no limiting value,
so it grows with every refinement for ever. `p99_von_mises_mpa` is the
volume statistic that does settle, and is usually the number to read.

**2. `mass.fill_error_fraction`.** How far the voxelisation is from the
solid's own volume. The grid is fitted to the part's bounding box, so this
is exact for a box and a percent or two for a curved part. Above 5% it warns:
the grid is too coarse to be standing in for that shape.

**3. `solver.relative_residual`.** Below `1e-8` the linear system was solved.
Above `1e-6` it warns, and the numbers are not a converged solution.

**4. `warnings`.** Dropped unsupported islands, an under-constrained model, a
single-grid run. They are in the report rather than in a log for the same
reason the receipt is on stdout.

## Three things worth knowing before you trust a number

**The element is C3D8I, not C3D8.** A fully-integrated trilinear hex
shear-locks in bending and reports a part stiffer than it is — which is the
direction that flatters it. So the element carries Wilson incompatible
modes, statically condensed. `--element c3d8` selects the locking element,
and exists so a test can measure the difference rather than assert it: on
the cantilever at 5 mm it is 5% stiff where the incompatible one is under 1%.

**A voxel mesh stair-steps a curved boundary,** and overstates the stress
there. That is why the sweep exists, why `p99` is reported beside the peak,
and why `calculix.py` exists.

**`calculix.py` is the second method, and it is the reason to believe the
first.** ADR-129 is the standing lesson in this repository: a
plausible-looking result survived being written down and was wrong, and what
caught it was comparing against a second method. On the cantilever the two
agree to 4e-7 on displacement and 5e-8 on von Mises.

## Licences — the one real constraint this tree has

`analysis/` is **engine-side**, and `docs/PROVENANCE.md` §1 puts the engine
side at LGPL. `AGENTS.md` calls the GPL boundary "one-way and hard" about
`shell/`; the reasoning transfers exactly, and a test enforces it here.

- **Nothing under `analysis/` may import a GPL package.** Not `gmsh` (GPL-2,
  and its linking exception runs the other way), not `pymeshlab`, `mmapy`,
  `ccx2paraview`, `pygalmesh`, `pymeshfix`, `tetgen` (AGPL) or `jax-fem`.
  This is not a judgement call, and `test_nothing_under_analysis_imports_a_gpl_package`
  is not advisory.
- **CalculiX is GPL-2 and is a subprocess.** A text deck in, a text result
  out; never linked, never imported. The same arm's length FreeCAD's own
  LGPL Fem module used. `ccx` is in `pixi.toml` and is pruned out of the
  payload by `package/engine/build_engine_payload.sh`, which keeps exactly
  four binaries. **Leave it pruned** — shipping it is distributing a GPL-2
  binary, which is a decision and not a build fix.
- Clean and usable if a later slice needs them: scikit-fem, SfePy,
  scikit-image, trimesh, meshio, pymoo, Optuna, `cma`, manifold3d, Netgen.
  S2 considered `scikit-image` for marching cubes and did not take it: sixty
  lines of marching *tetrahedra* have no ambiguous cases, so the surface is
  manifold by construction, and the pin count stayed at three.

## Why a hand-written hex core

It looks like reinventing a wheel. The reasons it is not, measured:

- **S2 needs a voxel grid anyway.** SIMP topology optimisation runs on a
  structured hex mesh, so a tetrahedral pipeline for S0 and a voxel pipeline
  for S2 would be two codebases for one job.
- **numpy and scipy are already in the payload** (23 MB and 50 MB, measured).
  If S3 ever moves a linear solve in-engine it costs no payload bytes.
- **Filling a structured grid needs no mesher**, so it needs no `gmsh`, so
  it raises no licence question.
- **The August 2026 survey found nothing better under the constraints.** The
  maintained permissive options are `scikit-fem` (BSD, assembles only —
  you still bring a solver, and it is a dependency for the part that was
  never the hard part), `torch-fem` (MIT, excellent, and drags PyTorch into
  a 3.3 GB app), and `SfePy` (BSD, and has no osx-arm64 build). The two
  best-known topology-optimisation stacks, JAX-FEM and fenitop, are GPL-3.

## What this does *not* do

- It does not resurrect FreeCAD's `Fem`. That tree was deleted in Phase 1,
  not disabled. **Two pieces have since moved in-engine** with their own ADRs
  and the owner's sign-off — `mesh.check` (ADR-144) and `part.stress`
  (ADR-145), and `docs/VISION.md` carries the amendment. Everything else here
  stays outside the engine: topology optimisation, refinement sweeps,
  CalculiX and rollout-measured load cases are all offboard and staying that
  way. `part.stress` is a *second implementation* of this tree's numeric
  core, not an import of it — neither side may import the other, and a test
  solves the same cantilever through both and requires them to agree.
- It builds **no button**. ADR-084 already answered the general form of this
  question for training: the agent authors, dispatches and declares; the
  human reads a viewport and judges. A search reports a front; **it never
  writes the script**, and picking a point off that front is a person's job
  or an agent's turn.
- It does not let an optimiser author geometry. That is S2's constraint and
  it is VISION principle 3 — the script is the truth. `topology.py` hands
  back a **shape to read**, not a feature tree; `part.shape_from_mesh` makes
  a shell of triangle faces, not something you can edit. TO informs the
  redesign, and the redesign is authored.
- It invents **no new asset suffix**. `.stl` already comes home through
  `put_asset` and is already carried by Save-As; a `.cxdensity` would be
  silently dropped, which is the bug ADR-046 recorded. The density field and
  the run receipt stay here, in the run directory.
