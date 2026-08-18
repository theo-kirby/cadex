---
node_id: eaa7e154-9094-53e6-a042-f3da4ec93d25
slug: eager-trail-8160
title: 'S2: SIMP on S0''s own grid, and a surface welded on grid edges rather than on a tolerance'
created_at: '2026-08-11T10:48:15+00:00'
parents:
- jolly-shore-2511
summary: ''
---
## What

S2 closed. `analysis/topology.py` carves a declared blank against a declared
load case and hands back a watertight STL — SIMP on the same hex grid S0
already built, plus a hand-written marching-tetrahedra extraction (ADR-143,
`docs/STRUCTURAL.md` §5, ROADMAP Phase 16).

One new file, four precise edits to `analysis/cadex_stress.py` that S0's 27
tests did not notice, and one new suite
(`src/Mod/cadex/cadex_tests/test_analysis_topology.py`, 24 tests). No engine
code, no protocol change, no payload bytes — **and no new pinned dependency**:
`analysis/requirements.txt` is still three lines.

## Why

S0 gave a stress number and S1 a search over declared parameters, but both
answer "is this shape good"; neither invents a shape. S2 is the third job the
vertical was sized from. It was cheap because the stack choice paid off: SIMP
runs on a structured hex grid, which is exactly what S0 already builds and
solves, so the whole slice is S0's solver in a loop with a density variable.

## Method

**The four solver edits.** `solve()` split into `prepare()` — everything a
density cannot change: the element matrix, the pruned occupancy, the node
numbering, the held degrees of freedom, the assembled force vector, the
free-DOF index — and `solve_system()`. The assembly gained a density vector,
CG gained `x0`, and `_DIRECT_DOF_LIMIT` came down from 60,000 to 10,000.
`solve()` is now the two-line wrapper it always was in effect.

The density enters in **one line**. It was `data = np.tile(flat, len(block))`
— every element gets the same 24×24 matrix — and became
`data = (scale[:, None] * flat[None, :]).ravel()`. That is legitimate with the
condensed C3D8I element because static condensation commutes with a uniform
scaling of the element energy: scaling every block by `s` scales `Kcc`, `Kci`
and `Kii` alike, and `s·Kcc − (s·Kci)(s·Kii)⁻¹(s·Kci)ᵀ` is exactly `s` times
the unscaled condensed matrix. ADR-141 claimed that property when it chose
the element; a test now asserts the assembled matrices agree to 1e-9 relative
rather than taking the algebra on trust.

**Extraction is hand-written marching tetrahedra**, ~60 lines, six tetrahedra
per cube sharing the main diagonal. Chosen over `scikit-image` for three
reasons and the third decided it: no fourth dependency; a tetrahedron admits
**no ambiguous case** where marching cubes has exactly that hole; and
intersection points are identified by **the grid edge they lie on**, so two
tetrahedra sharing an edge produce the same vertex *index* rather than two
vertices a nanometre apart. Watertight by construction, not by tolerance.

Then Taubin smoothing (alternating λ/μ Laplacian passes) and a binary STL
through the `write_binary_stl` that already existed.

Commands:

```
pixi run python analysis/topology.py --self-check
pixi run python -m pytest src/Mod/cadex/cadex_tests/test_analysis_topology.py
pixi run python -m pytest src/Mod/cadex/cadex_tests/test_analysis_stress.py
```

## Result

**S0's 27 tests pass unmodified**, which is the evidence that the split is a
split and not a rewrite. The full engine suite is 1800 passed / 22 skipped
with S2 in (was 1776).

**`_DIRECT_DOF_LIMIT` was wrong by a wide margin**, measured on the same
M-series laptop that set it:

```
free dofs            21,800      47,000     158,000
direct (splu)        1.22 s      7.22 s          --
CG + Jacobi          0.24 s      0.65 s      3.13 s
```

The old 60,000 sent every problem in the interesting range to the slower
solver — 3× at 21.8k, 11× at 47k. An S0 improvement that S2 paid for.

**Cost of a run:** ~0.8 s an iteration at 13.5k elements, ~3.7 s at 48k. A
100-iteration run is 1.5–6 minutes on a laptop. **No GPU box.**

**The winding bug, and it is the one worth keeping.** The case table is
derived from a parity argument on vertex order, and a parity argument only
means anything against a fixed handedness. **Three of the six natural
tetrahedron listings are left-handed.** With them left so, the extracted
surface was topologically closed — zero boundary edges, zero non-manifold
edges — and had **half its triangles inside out**, so the closure check
passed and the enclosed volume came out as exactly `0.0`. Fixed by orienting
the listings at import; a test asserts each determinant is positive.

**Extraction accuracy, against a sphere whose volume is known:**

```
cells across   marching tets    Taubin    plain Laplacian
    10            -4.46%        +0.52%        -19.9%
    20            -0.68%        +0.19%        -4.96%
    40            -0.16%        +0.06%        -1.27%
```

It converges, and Taubin does not shrink the shape while the plain Laplacian
everybody reaches for first eats a fifth of it at the coarsest grid.
`|μ| > λ` is the whole trick.

**Two numbers were being computed about the wrong field, and both were
fixed:**

- *The volume constraint.* The OC bisection first constrained `sum(x)`, the
  design variable — and a normalised density filter does not preserve a sum,
  so the reported volume fraction landed **1.4% off**. Because the filter is
  linear the physical volume is exactly `x · dV/dx` with `dV/dx = Hᵀ(1/d)`,
  one convolution computed once at construction. It holds to **1e-6** now,
  asserted at every iteration.
- *Discreteness.* A density filter of radius R smears a binary design over a
  band of width R, so a member thinner than 2R is grey through its core
  however well the run converged. Measured: a design variable of 3833 cells
  at 0, 1638 at 1 and 129 anywhere else — non-discreteness **0.017**, as
  resolved as SIMP gets — has a *density* non-discreteness of **0.32**.
  Reading the second as a quality score says the run failed when it did not.
  Both are in the report and the warning is spent on the first. Safe because
  the surface is the ρ=0.5 level set and the grey band is symmetric about it:
  cells above the level set came to 1683 against a density integral of 1680.

**Verification, in the order it catches things:**

1. **Finite-difference sensitivity check** — the classic SIMP bug and the
   only test that catches it. Central difference on a *random* density (a
   converged one is nearly binary, where `ρ^(p−1)` is flat and a wrong
   exponent would hide) agrees to **3e-6**.
2. **3-D cantilever and MBB beam.** Volume constraint to 1e-6; compliance
   falls once continuation settles; the design beats a uniform field of
   identical volume solved by the same solver at the same penalty by
   **7.3×**. The MBB beam puts more material in its top and bottom thirds
   than its middle.
3. **Mesh independence.** A 4 mm filter radius at 2.5 mm and 1.5 mm cells
   agrees about **95.5%** of the solid/void decision and about the stiffness
   achieved to 2.3%. That is what the filter is for, so it is what the filter
   is tested on.
4. **Extraction** — watertight, consistently wound, right volume, and
   re-voxelised with **S0's own voxeliser** it reproduces the fill.
5. **A real project.** STL → `put_asset` → `mesh.import_file` → rebuild
   against a real cadexd child: 3228 triangles in, a mesh artifact out, the
   same digest on a second rebuild.

**S2c cost nothing**, as predicted: `.stl` is already in the engine's
`_ASSET_SUFFIXES` and the shell's `CARRIED_ASSET_SUFFIXES`. The rule that
imposes: **S2 invents no new asset suffix** — a `.cxdensity` would be
silently dropped by Save-As, the bug ADR-046 recorded. The density field and
the receipt stay offboard.

**Deliberately not built.** No printability constraint — overhang angle and
minimum wall thickness are not built and not planned; supports handle
overhangs, and a constraint nobody needs distorts the result. The filter
radius stays for a purely numerical reason. No stress-constrained TO: `mmapy`
is GPL-3 and barred from this tree. No mesh → parametric body.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: be7ff63d8766f3cede9545152af00a5e01c06fe8

## State Impact

- target: kind-marsh-2645 — S2 closed (ADR-143). analysis/topology.py: SIMP on S0's hex grid, four edits to cadex_stress.py that S0's 27 tests did not notice, hand-written marching tetrahedra so requirements.txt stays at three pins. Verified by a finite-difference sensitivity check (3e-6), a cantilever beating a uniform design of the same volume by 7.3x, an MBB beam, mesh independence at 95.5%, extraction converging on a sphere (-4.5% -> -0.16%), and a round trip through a real cadexd. One iteration is 0.8 s at 13.5k elements, so a 100-iteration run is a laptop-minute and needs no GPU box. _DIRECT_DOF_LIMIT corrected from 60,000 to 10,000 (CG beats direct by 3x at 21.8k dofs and 11x at 47k). Three of six tetrahedron listings were left-handed, producing a closed surface with half its triangles inside out and a volume of exactly zero. The volume constraint moved onto the physical density (was 1.4% off) and discreteness is now read off the design variable (0.017) rather than the filtered density (0.32). 24 tests.
