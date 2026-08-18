---
node_id: 252419fb-ad3a-5981-b247-00b4f33b62cf
slug: fair-beacon-5964
title: 'S0: analysis/ as a second offboard tree — a hex-grid FEA core, rollout-measured loads, and a CalculiX second opinion'
created_at: '2026-08-10T11:30:02+00:00'
parents:
- odd-banner-6071
- humble-path-4466
summary: ''
---
## What

A new vertical, and its first slice closed. `analysis/` joins `training/` at
the repository root as a **second non-engine tree** under the identical
ADR-084 contract, and S0 delivers a stress number with the evidence for
believing it (ADR-141, `docs/STRUCTURAL.md`, ROADMAP Phase 16).

Five new files, none of them engine code:

- `analysis/cadex_stress.py` — a hex-grid linear-elastic solver in
  numpy/scipy: voxelise a solid, assemble, solve, recover stress, sweep the
  grid, report.
- `analysis/loads_from_rollout.py` — the load case **measured from a policy
  rollout**, by replaying a published trace in stock MuJoCo.
- `analysis/calculix.py` — the arm's-length second opinion: the identical
  grid written as a CalculiX deck, `ccx` run as a subprocess, results
  compared.
- `analysis/requirements.txt`, `analysis/README.md`.
- `src/Mod/cadex/cadex_tests/test_analysis_stress.py` — 27 tests.

No engine code, no protocol change, no payload bytes, no new op.

## Why

Three jobs asked for it: lighter printed parts, robot legs whose mass feeds
back into the dynamics a policy has to control, and shape search. All three
need one thing first — a stress number somebody can believe — and the
repository had nothing that computes stress and no material stiffness at all
(zero hits for `stress`/`strain`/`von_mises`/`yield` across the engine;
`assembly.body` carries density only).

Outside the engine for ADR-084's reason, reached again. Assembly is not the
cost — a structured hex grid at 54,000 elements and 176k degrees of freedom
assembles in 0.61 s here — but the **solve** is, and a SIMP system is
ill-conditioned by construction as densities go to zero. That is a thing to
find out about on a machine with time, not inside a service that owes a
viewport an answer.

Much of the plan was shaped by what the repository already had, all of it
verified rather than assumed: `docs/CLI.md` §1 already describes this use
case by name (FEA included), `param_specs` from `inspect scope="script"` is
already a machine-readable design space, numpy and scipy are already in the
payload (23 MB and 50 MB), `ccx` is already in `pixi.toml` and already
pruned out of the payload, and `_ASSET_SUFFIXES` already accepts `.stl` so
an S2 result needs no new suffix.

## Method

**A hand-written hex core rather than a library**, for four measured
reasons: S2 needs a voxel grid anyway so a tet pipeline would be a second
codebase for one job; numpy and scipy are already in the payload so an S3
move costs no bytes; a structured grid needs no mesher so it needs no
`gmsh` so it raises no GPL question; and an August 2026 survey found nothing
better under those constraints — `scikit-fem` (BSD) assembles only,
`torch-fem` (MIT) drags PyTorch into a 3.3 GB app, `SfePy` has no osx-arm64
build, and JAX-FEM and fenitop are GPL-3.

**The element is C3D8I, not C3D8.** A fully-integrated trilinear hex
shear-locks in bending and reports a part *stiffer than it is* — the
direction that flatters a safety factor. Wilson incompatible modes,
statically condensed, cost almost nothing on a structured grid: every
element is geometrically identical so the condensed 24x24 matrix is computed
once, and condensation commutes with a uniform scaling of the element energy
so the same matrix is reusable under a SIMP density in S2.

**The grid is fitted to the part's bounding box per axis.** Not a nicety —
see the first result below.

**The load case can be measured rather than declared.**
`mj_rnePostConstraint` already fills `cfrc_int` (the joint reaction wrench
between a body and its parent) and `cfrc_ext` (contact and applied), so the
load case for "is this thigh strong enough" is the worst wrench a body saw
across a rollout, read out of the same MJCF `assembly.mjcf` already exports.
`contact_force` being a *deferred engine observation*
(`CadexDynamics.py:5532`) does not matter, because this is stock MuJoCo
offboard. `loads_from_rollout.py` does not run a policy: it replays a
published `cadex-assembly-simulation-trace-v1` by holding each frame's
`actuator_commands` over that frame's interval, and then checks its own
replay frame by frame against the poses the trace recorded.

**CalculiX is the second method**, and the reason to believe the first —
ADR-129's standing lesson. `calculix.py` writes the identical grid (same
nodes, same corner order, same held degrees of freedom, and the **same
assembled force vector**, so a disagreement cannot be a disagreement about
the load) and reads `.dat` rather than `.frd`, because `*NODE PRINT` and
`*EL PRINT` write whitespace-separated text while `.frd` is a fixed-column
format whose parser is the kind of code that is wrong for a year.

Commands:

```
pixi run python analysis/cadex_stress.py --self-check
pixi run python analysis/calculix.py --self-check
pixi run python -m pytest src/Mod/cadex/cadex_tests/test_analysis_stress.py
pixi run python -m pytest src/Mod/cadex/cadex_tests
```

## Result

`test_analysis_stress.py` — **27 passed**. Full engine suite — **1757
passed, 22 skipped**, unchanged beside it. The numeric half really runs in
the pixi environment, because numpy 1.26.4, scipy 1.17.0, mujoco 3.10.0 and
`ccx` 2.23 are all there.

| Check | Result |
|---|---|
| Cantilever tip deflection vs Timoshenko | 1.14184 vs 1.15218 mm — **0.9%** |
| Recovered bending stress vs `M y / I`, midspan | 2.2500 vs 2.2500; 2.6250 vs 2.6250 |
| C3D8 (locking) vs C3D8I, same grid | **5.1%** stiff vs **0.9%** |
| CalculiX 2.23 vs the hex core, same grid | **4.4e-7** displacement, **5.4e-8** von Mises, **5.4e-8** worst component |
| Constant-strain patch test | incompatible modes vanish to 1e-12 |
| Rollout replay vs its own trace | **0.0 mm** |
| The same motion recorded half as often | **142 mm** — reported as a different motion |
| Reaction at rest vs weight | shank mass x g, to 2% |

**Convergence behaves as the physics says it must**, and the report says so
rather than averaging it away. Over three levels on the cantilever:

```
h(mm)   elements   displacement   peak vM   p99 vM
2.500        640      1.13916      5.3790   5.3389
1.962       1325      1.14073      5.6440   5.2279
1.422       3479      1.14184      6.1237   5.3163
```

Displacement converges, `p99` converges, **peak von Mises does not and must
not** — a clamped face is a genuine stress singularity with no limiting
value, so it grows with every refinement for ever. The report declares
`displacement_converged`, `p99_converged` and `peak_converged` separately; a
report that called that peak converged would be lying.

**Two things that were silently wrong before the checks caught them**, both
now pinned by tests:

1. **The grid had to be fitted to the part.** Centre-sampled voxelisation of
   a 10 mm bar at 1.875 mm keeps five cells and throws away 6% of the
   height, and stiffness goes as the cube of height. The unfitted sweep gave
   tip deflection **1.14 -> 1.45 -> 1.21 mm** — every level solving a
   differently shaped beam, and no convergence to read at all. Fitting each
   axis to the bounding box makes the volume exact at every level and the
   sequence monotone.

2. **The parity fill lost a diagonal.** A cylinder came out 4.5% light — 11
   columns of a 20-cell layer, exactly the `x = y` line. A cap tessellated
   as a triangle fan gives every radial edge to two triangles, so a ray
   meeting one is counted twice and the column comes out hollow. The
   sample-point nudge that exists to prevent that used the **same**
   irrational fraction on x and y, and so could not move a point off that
   diagonal. It was visible only after a float32 round trip through an STL,
   which changed which points landed exactly on an edge. Fixed twice over: a
   different irrational per axis, and collapsing coincident crossings — the
   second exact rather than merely unlikely, because a ray through a shared
   edge crosses the surface once and both triangles report the same height.
   The regression test compares a float64 fill against a float32 one and
   requires them to agree.

Two smaller ones caught the same way. MuJoCo's `cfrc_*` are **com-based** —
the torque is about `subtree_com[body_rootid[body]]`, not the body — so it
is moved onto the body's own centre of mass (`t_p = t_c + (c - p) x F`).
Left alone the forces would still check out and the moments would be wrong
by `r x F`, which on a leg is the whole number; a statics test pins it. And
the trace's frame indexing (untimed `input`, then an **unstepped**
`solver_output` at t=0 with no commands, then one frame per action) was off
by one in the first replay, which is precisely what the fidelity check
exists to catch.

**Standing guidance that falls out:** author a rollout at
`frames_per_second` equal to the control rate when you intend to read loads
off it. A trace sampled more coarsely holds only some of the actions.

**Licence rule, test-enforced.** Nothing under `analysis/` may import a GPL
package — the obvious tools for structural work are the GPL ones (`gmsh`,
whose linking exception runs the other way; `pymeshlab`, `mmapy`,
`ccx2paraview`, `pygalmesh`, `pymeshfix`, `tetgen`, JAX-FEM). CalculiX is
the one GPL tool used, as a subprocess, and stays pruned out of the payload
where `build_engine_payload.sh` keeps exactly four binaries.

**What is not done and is not authorised.** S1 (search driver), S2
(topology optimisation) and S3 (anything in-engine) are open. S3 in
particular needs its own ADR and owner sign-off, because
`docs/VISION.md:125` puts FEM out of scope — a new Cadex surface is a
different decision from resurrecting FreeCAD's deleted `Fem`, but it is
still a decision. Two open questions are written down rather than guessed:
whether S1's driver should be Optuna or pymoo (the survey argues Optuna,
because a CAD rebuild plus an FEA solve is a 50-500 evaluation budget, not
50,000), and whether a printability constraint belongs in the optimiser or
in the redesign step that reads its output.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: be7ff63d8766f3cede9545152af00a5e01c06fe8

## State Impact

- target: NEW structural-analysis-and-shape-search — NEW node for Phase 16's vertical (docs/STRUCTURAL.md, ADR-141). Status working for S0, open for S1-S3. Claims: analysis/ is a second non-engine tree at the repo root under the ADR-084 contract (no CMake rule, no payload, nothing in pixi.toml, three exact pins in its own requirements.txt), test-enforced by test_analysis_stress.py (27 tests); a hex-grid C3D8I linear-elastic solver in numpy/scipy verified against the cantilever closed form (0.9%), against M y / I for recovered stress (exact at the sampled fibre), and against CalculiX 2.23 on the same grid (4.4e-7 displacement, 5.4e-8 von Mises); the report separates displacement/p99 convergence from peak von Mises, which at a clamped face is a genuine singularity and must not converge. Negative knowledge: an unfitted voxel grid solves a differently shaped part at every refinement level (tip deflection swung 1.14/1.45/1.21 mm), and a parity fill whose sample nudge shares one irrational across axes loses whole diagonals of a fan-tessellated cap (4.5% of a cylinder, visible only after a float32 round trip). Constraint: nothing under analysis/ may import a GPL package; CalculiX is a subprocess and stays pruned out of the payload. S3 (anything in-engine) is NOT authorised by ADR-141 and needs its own ADR and owner sign-off against docs/VISION.md:125.
- target: salty-isle-4063 — New claim: a published rollout trace is now also a load-case source. loads_from_rollout.py replays a cadex-assembly-simulation-trace-v1 in stock MuJoCo and reads mj_rnePostConstraint's cfrc_int/cfrc_ext, so the deferred contact_force observation does not block structural work on mechanism parts. It needs nothing new from the engine. Two facts to carry: MuJoCo's cfrc_* are com-based about subtree_com, not about the body, so a torque read without moving it is wrong by r x F; and a replay is only the rollout if it tracked it, checked frame by frame against the trace's own poses. Standing guidance: author a rollout at frames_per_second equal to the control rate when you intend to read loads off it — the same motion recorded half as often replayed 142 mm away from itself.
