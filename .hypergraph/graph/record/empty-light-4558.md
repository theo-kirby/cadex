---
node_id: d8e1b254-edce-51af-bc17-968ddacb346c
slug: empty-light-4558
title: 'S4b-d: the optimiser finds the topology and the deliverable is a script'
created_at: '2026-08-11T18:43:07+00:00'
parents:
- modest-spark-7806
summary: ''
---
## What

S4b–d closed (ADR-147, `docs/STRUCTURAL.md` §8.3–8.5, ROADMAP Phase 16).

`analysis/skeleton.py` — new, ~1500 lines — takes a SIMP density field and
hands back a **parametric xscript**: node and strut tables, mounting pads, a
`part.fuse`, and a `part.stress` check anchored to the blank's own faces. It
installs the script through `./cadex script --set` as a subprocess, sizes it
with a fully-stressed-design loop that runs the real hex FEA on the **rebuilt
CAD** every pass, and reports one number.

Offboard under the identical contract as the rest of `analysis/`: no CMake
rule, no payload, nothing in `pixi.toml`, no GPL import, `requirements.txt`
still three pins. No engine change, no protocol op, no `shell/` diff.

## Why

Every generative-design tool on the market ends in a mesh you cannot edit —
nTop, Fusion, Altair. Move the hole 2 mm and you re-run the optimisation.
Cadex is the one product whose native artifact is a *script*, so it can end
somewhere else: the optimiser finds the **topology**, and the deliverable is
a feature tree a human and an agent can both edit. `docs/VISION.md` principle
3 already demanded this — *the optimiser never authors geometry the script
does not own* — and until now it was honoured only in spirit, by handing over
an STL and hoping the agent redrew it.

## Method

Fit: binary field at rho >= 0.5, a Euclidean distance transform whose value
*is* the local member radius, maximal-ball packing for nodes, Delaunay for
candidate bars, pruned to the bars that stay in the solid.

Sizing: five passes of emit -> `./cadex script --set` -> export STL ->
`analysis/cadex_stress.py` on that STL -> assign elements to members -> FSD
update -> renormalise -> rescale to the measured mass.

Benchmark: a two-footed bracket, 60 × 40 × 40 mm, carved at 2 mm to a volume
fraction of 0.3 with S4a's symmetry, 6 mm pads and plane pinning on. Whole
`--self-check` run: 3m40s to 7m, dominated by the engine rebuilds.

Tests: 20 new in `src/Mod/cadex/cadex_tests/test_analysis_skeleton.py`, one
driving a real cadexd child; `SKELETON` added to the tree-contract loops in
`test_analysis_stress.py`. Full engine suite 1851 passed / 22 skipped;
`cli/tests` 80 passed; `git status -- shell/` empty.

## Result

**The verdict, which is the point of the slice:**

```
SIMP optimum      compliance 10.234 N·mm   mass 40.58 g
rebuilt script    compliance  6.042 N·mm   mass 41.07 g
compliance ratio  0.59        bar 1.15     verdict: ship
coverage 0.926    23 nodes, 51 struts, 3 pads
```

The parametric part is **1.7× stiffer than the SIMP optimum at the same
mass**. That is not the fit beating the optimiser: SIMP minimises compliance
over a *grey* field, and the band a filter of radius R smears over every
member is real material carrying nothing.

End to end verified: `./cadex params --set strut_scale=1.1` moves the
exported volume from 32 975 mm³ to 35 751 mm³, with no model in the loop.

**Four things were wrong first**, and each is negative knowledge:

1. **Local maxima are not the medial axis.** A member is a *ridge* of the
   distance field, and a cell on a ridge is not a strict local maximum. A
   3×3×3 maximum filter proposed 25 cells out of 3500 on the benchmark, the
   packing kept 11, and the fit covered 0.45 of a part whose members run 8 to
   14 mm thick — a fit starved of nodes, reported as a field that did not
   want struts. Maximal-ball packing over the whole solid replaced it.
2. **The distance transform is biased and the bias reverses.** Binary
   transform on a synthetic 8 mm cylinder reads 7.616 where the truth is
   7.293; the textbook half-cell correction gives 7.116, and a strut of 7.1
   covers (7.1/8)² = 79% of the cylinder it was fitted to — so a perfect fit
   to a perfect strut scored 0.69 on the coverage gate and was refused. Fix:
   interpolate the *density* onto a half-cell grid first, then subtract a
   quarter of a fine cell — chosen because it minimises the worst case over a
   convex cylinder (−0.069 cells), a slab (+0.25) and a flat domain face
   (+0.125), leaving everything inside 0.194 cells.
3. **Delaunay plus a radius floor loses connectivity the field has.** On the
   cantilever the field is one component of 2916 cells and the thick bars
   alone split the fit into 73 + 9 + 9 + 3 + … nodes, orphaning the tip load.
   Fixed by adding the thin bars back with Kruskal on min(r0, r1) until
   nothing more joins two components.
4. **`_lift_nodes` said `max(current, incident)`.** A joint radius could only
   ever grow, so every sizing pass ratcheted the part heavier whatever the
   mass correction asked for: a 40.6 g target settled at 45.2 g with the
   controller pulling the other way the whole time. A joint has no size of
   its own; it has the size of the members it joins.

**Coverage: the gate works, its stated reason was half wrong.** The bar is
0.85 as planned, and it discriminates — bracket 0.93, synthetic A-truss 0.97,
SIMP cantilever 0.76, solid block 0.79, hollow box shell 0.56. But decision
2's reason ("a SIMP field often wants a flat web, so refuse rather than fit
plates") is not what the measurement says: **a slab fits fine** (0.90–0.97,
its medial axis is one sheet). What fails is a **shell** — several sheets a
cell or two thick meeting at edges — and a SIMP cantilever, which is one. So
the gate is a *fidelity* gate: it says the emitted strut part does not
contain the material the field had. It refuses the right fields, and its
number is the evidence that would ask for S5 (constraining SIMP itself toward
strut-like solutions, which S4 deliberately does not do).

**`_SUPPRESSION = 2.0` is a diameter and it is also the build budget.**
Bracket at 1.0: 556 solids, coverage 0.99. At 1.4: 200 solids, 0.95. At 2.0:
**74 solids, 0.93.** Below 2.0 the coverage barely moves and the solid count
explodes past what `part.fuse` will blend in a sane time.

**The selector needed four keys, each because the other three were not
enough.** A fitted lattice has no flat face anywhere, so each anchor's
mounting pad is emitted as a `part.box` snapped to the blank's own plane;
`geometry_type` + `normal` then still catch the flat end cap of every strut,
`near_point` narrows to the pad, and `min_area` separates the pad from the
caps that survived the boolean. Measured: a `near_point` of 18.7 mm around
the boss with no area band caught more than one face and the engine refused
the whole script for cardinality.

**What did not survive contact: the fillets are not free.** Spike zero's
`reduce` result does not transfer to a *fitted* lattice — it wants one radius
that blends every seam and near-tangent members leave none, so it refused the
whole part down to 0.0555 mm. `skip` is what the emitted script uses, and
even `skip` refuses when *nothing* blends, which is what the shipped bracket
does at `strut_scale = 1.0` for every radius tried (0.25, 0.5, 1.0, 2.0 mm) —
while at `strut_scale = 0.9` a 1.0 mm blend succeeds and adds 30 000
triangles. `blend_mm` stays a declared parameter and the loop drops the blend
and says so: whether a given lattice blends is a property of the lattice that
only the kernel knows.

**One thing is computed and cannot be read.** `part.stress` publishes no
geometry (ADR-145) and `cadex export --json` describes only BREP outputs — a
stress check comes back as `{"kind": "none", "skipped": "not a BREP
output"}`. Its safety factor is computed and is in the project store, and no
subcommand serves it. Reading the store's attempt files would couple this
tree to a layout ADR-142 keeps it away from, so it does not. The check's more
valuable job still works: it is evaluated on every rebuild, so a parameter
change that moves a mounting face until the load case stops resolving fails
loudly. A `cadex` subcommand serving a non-BREP output's value is separate
work.

**A pass that will not build ends the loop, not the run.** Not hypothetical:
the benchmark's fourth pass is refused reproducibly with "OpenCascade
produced an invalid shape", and the shipped result is the third.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: be7ff63d8766f3cede9545152af00a5e01c06fe8

## State Impact

- target: kind-marsh-2645 — S4 closed (ADR-147), and it is what the whole vertical was for: analysis/skeleton.py fits a strut graph to a SIMP field and emits a PARAMETRIC XSCRIPT rather than a mesh, installs it via ./cadex script --set as a subprocess, and sizes it with a fully-stressed-design loop that runs the real hex FEA on the rebuilt CAD every pass. Verdict on the benchmark bracket: compliance ratio 0.59 against a bar of 1.15 at equal mass, coverage 0.93, 23 nodes and 51 struts -- ship. Negative knowledge worth keeping: local maxima are not the medial axis (25 candidates of 3500, coverage 0.45); the binary distance transform is biased enough that a perfect fit to a perfect strut failed the gate (7.1 read on a true 7.293, covering 79%); Delaunay plus a radius floor loses connectivity the field has; a joint written as max(current, incident) ratchets the sizing loop's mass by 11%; and the fillets are NOT free -- part.fuse(blend=) refuses a fitted lattice at every radius tried at strut_scale 1.0, so blend_mm stays a knob rather than a promise. The coverage gate refuses the right fields (0.56 on a shell, 0.76 on a plate-like cantilever) but for a different reason than planned: a slab fits fine, so it is a fidelity gate, and its number is the evidence that would ask for S5.
