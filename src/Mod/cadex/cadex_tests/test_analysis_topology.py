# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Topology optimisation, and the four things that make it S2 (ADR-143).

``analysis/topology.py`` is S0's solver in a loop with a density variable.
Its placement contract -- where it lives, what CMake may never do with it,
what it may import and the standing prohibition on GPL packages -- is
asserted beside the rest of the tree in ``test_analysis_stress.py``; this
file is about whether the answer is right.

Four checks, in the order they catch things:

1. **The finite-difference sensitivity check.** Perturb one element's
   density and confirm the analytic sensitivity matches the compliance
   change. A wrong sensitivity is *the* SIMP bug and it is invisible from
   the outside -- the run still converges, to the wrong shape. This is S2's
   second method, the way CalculiX was S0's.
2. **The benchmarks.** A 3-D cantilever and an MBB beam: the volume
   constraint holds, compliance falls once the continuation settles, and the
   design beats a uniform one of identical volume by a large factor.
3. **Mesh independence.** The same ``filter_radius_mm`` in *physical* units
   at two grid resolutions gives the same topology. That is what the filter
   is for, so it is what the filter is tested on.
4. **Extraction.** Watertight, correctly wound, the right volume -- and
   **re-voxelised with S0's own voxeliser it reproduces the fill**. Two
   parts of one tree checking each other.

The numeric half runs in the pixi environment and skips cleanly where scipy
is not, so this file works from either interpreter. The round trip through a
real project needs a built engine and skips without one, the bar
``cli/tests`` sets.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[4]
ANALYSIS = ROOT / "analysis"
TOPOLOGY = ANALYSIS / "topology.py"
STRESS = ANALYSIS / "cadex_stress.py"


def _module(path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(path.stem, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def topology():
    pytest.importorskip("scipy", reason="the SIMP loop solves with scipy.sparse")
    return _module(TOPOLOGY)


@pytest.fixture(scope="module")
def stress():
    pytest.importorskip("scipy", reason="the hex core solves with scipy.sparse")
    return _module(STRESS)


def _prepared(topology, stress, *, size=(24.0, 8.0, 12.0), element_mm=2.0):
    plan = topology.Plan.from_mapping(
        topology.cantilever_plan(size_mm=size, element_mm=element_mm))
    grid = topology.domain_grid(plan.domain, plan.element_mm)
    material = stress.Material.from_mapping(plan.load_case["material"])
    return plan, grid, stress.prepare(grid, material, plan.load_case)


# ---------------------------------------------------------------------------
# 1. The sensitivity, checked against a finite difference.
# ---------------------------------------------------------------------------


def test_the_analytic_sensitivity_matches_a_finite_difference(
        topology, stress) -> None:
    """The one test that catches the classic SIMP bug.

    ``dc/drho_e = -(d scale/d rho) u_e^T k0 u_e`` is four terms that can each
    be wrong in a way that still produces a plausible-looking structure: the
    sign, the exponent, whether ``k0`` is the condensed matrix or the
    unscaled one, and whether the energy is the element's or the system's.
    A central difference on a random density catches all four, and nothing
    else does.

    Random densities rather than a converged field on purpose -- a converged
    field is nearly binary, where ``rho**(p-1)`` is nearly flat and a wrong
    exponent would hide.
    """

    _, _, prepared = _prepared(topology, stress)
    rng = np.random.default_rng(7)
    density = rng.uniform(0.25, 0.95, prepared.element_count)
    penalty = 3.0

    _, sensitivity, _, _ = topology.compliance_and_sensitivity(
        prepared, density, penalty, solver="direct")

    step = 1.0e-6
    for index in rng.choice(prepared.element_count, 6, replace=False):
        up = density.copy()
        up[index] += step
        down = density.copy()
        down[index] -= step
        high, _, _, _ = topology.compliance_and_sensitivity(
            prepared, up, penalty, solver="direct")
        low, _, _, _ = topology.compliance_and_sensitivity(
            prepared, down, penalty, solver="direct")
        finite = (high - low) / (2.0 * step)
        assert abs(finite - sensitivity[index]) <= 1e-4 * abs(finite), (
            f"element {index}: analytic {sensitivity[index]:.8e} against "
            f"finite difference {finite:.8e}"
        )
        assert sensitivity[index] < 0.0, "more material is never less stiff"


def test_simp_scale_and_its_gradient_are_one_derivative_apart(topology,
                                                              stress) -> None:
    """The interpolation and its gradient are written once each, on purpose.

    They are two functions in ``cadex_stress`` rather than two expressions
    because a sensitivity that disagrees with the objective it differentiates
    is invisible at every level above this one.
    """

    density = np.linspace(0.02, 1.0, 25)
    for penalty in (1.0, 2.0, 3.0, 4.5):
        step = 1e-7
        finite = ((stress.simp_scale(density + step, penalty)
                   - stress.simp_scale(density - step, penalty)) / (2.0 * step))
        analytic = stress.simp_scale_gradient(density, penalty)
        assert np.allclose(finite, analytic, rtol=1e-5, atol=1e-9)
    # And at the ends: void carries the floor, solid carries all of it.
    assert stress.simp_scale(np.array([0.0]), 3.0)[0] == pytest.approx(1e-9)
    assert stress.simp_scale(np.array([1.0]), 3.0)[0] == pytest.approx(1.0)


def test_a_density_scales_the_assembly_exactly(topology, stress) -> None:
    """The one line that makes S0's solver a SIMP solver, checked directly.

    Static condensation commutes with a uniform scaling of the element
    energy, so a grid at a **uniform** density ``s`` must assemble to exactly
    ``simp_scale(s, p)`` times the solid matrix -- and therefore deflect by
    exactly the reciprocal. If that were only nearly true, the C3D8I element
    would not be usable under SIMP at all and ADR-141's claim would be
    wrong.
    """

    _, _, prepared = _prepared(topology, stress)
    solid = stress.assemble_stiffness(prepared)
    for value, penalty in ((0.5, 3.0), (0.8, 1.0), (0.25, 2.0)):
        density = np.full(prepared.element_count, value)
        scaled = stress.assemble_stiffness(prepared, density, penalty)
        factor = float(stress.simp_scale(np.array([value]), penalty)[0])
        difference = abs(scaled - solid * factor)
        assert difference.max() <= 1e-9 * abs(solid).max()

    uniform = stress.solve_system(prepared, density=np.full(
        prepared.element_count, 0.5), penalty=3.0, solver="direct")
    full = stress.solve_system(prepared, solver="direct")
    factor = float(stress.simp_scale(np.array([0.5]), 3.0)[0])
    assert uniform.max_displacement_mm == pytest.approx(
        full.max_displacement_mm / factor, rel=1e-6)


def test_a_warm_start_reaches_the_same_answer(topology, stress) -> None:
    """Warm-starting CG is an accelerator, not a different solver.

    Densities move slowly under an optimality-criteria update, so the
    previous displacement is a good guess -- but a guess that changed the
    answer would be a bug hiding behind a speed-up.
    """

    _, _, prepared = _prepared(topology, stress)
    density = np.full(prepared.element_count, 0.6)
    cold = stress.solve_system(prepared, density=density, penalty=3.0,
                               solver="cg")
    warm = stress.solve_system(
        prepared, density=density, penalty=3.0, solver="cg",
        guess=cold.displacement.reshape(-1)[prepared.free])
    assert warm.max_displacement_mm == pytest.approx(
        cold.max_displacement_mm, rel=1e-8)
    assert warm.solver["iterations"] < cold.solver["iterations"]

    with pytest.raises(stress.StressError, match="starting guess"):
        stress.solve_system(prepared, density=density, solver="cg",
                            guess=np.zeros(3))


def test_the_direct_solver_limit_is_where_the_measurement_put_it(stress) -> None:
    """S0 sent every interesting problem to the slower solver until S2 measured it.

    Pinned as a number because the comment beside it is a table of timings,
    and a limit that drifts away from its own evidence is worse than no
    limit at all.
    """

    assert stress._DIRECT_DOF_LIMIT == 10_000
    source = STRESS.read_text(encoding="utf-8")
    assert "CG + Jacobi" in source, (
        "the measurement that set _DIRECT_DOF_LIMIT is no longer beside it"
    )


# ---------------------------------------------------------------------------
# 2. The benchmarks.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cantilever(topology):
    """One 3-D cantilever run, shared: it is the expensive fixture here."""

    raw = topology.cantilever_plan(size_mm=(48.0, 12.0, 24.0), element_mm=2.0,
                                   volume_fraction=0.3)
    raw["filter_radius_mm"] = 4.0
    raw["iterations"] = 60
    plan = topology.Plan.from_mapping(raw)
    return plan, topology.optimise(plan)


def test_the_volume_constraint_holds_exactly(topology, cantilever) -> None:
    """Not approximately, and the difference is a bug this had.

    The optimality-criteria bisection constrains the **physical** density,
    which is the filtered one. A normalised filter does not preserve a sum,
    so bisecting on the design variable instead lands 1.4% off -- measured,
    not feared. The filter is linear, so the physical volume is exactly
    ``x . dV/dx`` and the bisection can enforce the real constraint without
    a convolution inside its loop.
    """

    plan, run = cantilever
    for record in run.history:
        assert record["volume_fraction"] == pytest.approx(
            plan.volume_fraction, abs=1e-3)
    assert run.history[-1]["volume_fraction"] == pytest.approx(
        plan.volume_fraction, abs=1e-6)


def test_the_design_beats_a_uniform_one_of_the_same_volume(topology,
                                                           cantilever) -> None:
    """SIMP's whole claim, as a ratio.

    Where the material goes matters more than how much of it there is. The
    comparison is against a uniform field of *identical* volume solved by the
    *same* solver at the *same* penalty, so the only difference between the
    two numbers is the arrangement.
    """

    plan, run = cantilever
    cell = tuple(run.prepared.element_indices.T)
    uniform = np.where(run.inside, plan.volume_fraction, 0.0)[cell]
    baseline, _, _, _ = topology.compliance_and_sensitivity(
        run.prepared, uniform, plan.penalty)
    optimised = run.history[-1]["compliance_n_mm"]
    assert optimised > 0.0
    assert baseline / optimised > 4.0, (
        f"uniform {baseline:.3f} against optimised {optimised:.3f}"
    )


def test_compliance_falls_once_the_continuation_settles(topology,
                                                        cantilever) -> None:
    """Rising compliance during continuation is the continuation working.

    The penalty ramps from 1 to 3 over the first half of the run, and a
    higher penalty makes the *same* grey design stiffer on paper and so
    costs compliance as it is applied. What has to fall is the second half,
    where the penalty is fixed and the only thing changing is the shape.
    """

    _, run = cantilever
    tail = [record["compliance_n_mm"]
            for record in run.history if record["iteration"] >= run.continuation_ends]
    assert len(tail) >= 10
    assert all(record["penalty"] == run.history[-1]["penalty"]
               for record in run.history
               if record["iteration"] >= run.continuation_ends)
    assert tail[-1] < tail[0], f"{tail[0]:.4f} -> {tail[-1]:.4f}"
    # Not required to be monotone step by step -- an optimality-criteria step
    # with a move limit may overshoot -- but the trend must be one direction.
    rises = sum(1 for a, b in zip(tail, tail[1:]) if b > a + 1e-9)
    assert rises <= len(tail) // 4, f"{rises} rises in {len(tail)} settled steps"


def test_the_design_variable_resolves_even_though_the_density_does_not(
        topology, cantilever) -> None:
    """The two fields are different things and only one of them is the answer.

    A density filter of radius R smears a binary design over a band of width
    R, so a member thinner than 2R is grey right through its core however
    well the run converged. Measured here: the design variable resolves to
    a non-discreteness well under 0.1 while the density's is several times
    that. Reading the second number as a quality score says the run failed
    when it did not, and that is why the warning is spent on the first.
    """

    _, run = cantilever
    last = run.history[-1]
    assert last["measure_of_non_discreteness"] < 0.1
    assert last["density_non_discreteness"] > last["measure_of_non_discreteness"]
    # The grey band is symmetric about the level set, so it cancels: the
    # cells above 0.5 carry the volume the density integral says they should.
    above = float((run.density > 0.5).sum())
    integral = float(run.density.sum())
    assert above == pytest.approx(integral, rel=0.05)


def test_an_mbb_beam_puts_its_material_where_the_textbook_does(topology) -> None:
    """The other benchmark every SIMP implementation is checked against.

    Half an MBB beam by symmetry: rolled at the symmetry plane, pinned at the
    far bottom corner, loaded down at the top of the symmetry plane. The
    answer is the one everybody's picture shows -- a solid top chord under
    the load, a bottom tie, and a web between them -- so the assertion is
    that the top and bottom thirds carry more material than the middle
    third, which is the shape of that picture and not a coincidence of one
    implementation.
    """

    plan = topology.Plan.from_mapping({
        "schema": topology.PLAN_SCHEMA,
        "name": "mbb",
        "domain": {"box": {"size_mm": [60.0, 10.0, 20.0]}},
        "element_mm": 2.0,
        "volume_fraction": 0.4,
        "filter_radius_mm": 4.0,
        "penalty": 3.0,
        "iterations": 50,
        "material": {"name": "PLA", "youngs_modulus_mpa": 3500.0,
                     "poissons_ratio": 0.36, "yield_strength_mpa": 50.0,
                     "density_kg_m3": 1240.0},
        "supports": [
            {"name": "symmetry",
             "region": {"face": {"axis": "x", "at": "min", "depth_mm": 1e-6}},
             "axes": ["x"]},
            {"name": "roller",
             "region": {"box": {"min_mm": [58.0, None, -1e-6],
                                "max_mm": [None, None, 1e-6]}},
             "axes": ["z"]},
        ],
        "loads": [
            {"name": "midspan",
             "region": {"box": {"min_mm": [None, None, 20.0 - 1e-6],
                                "max_mm": [2.0, None, None]}},
             "force_n": [0.0, 0.0, -100.0]},
        ],
    })
    run = topology.optimise(plan)
    density = run.density
    _, _, nz = density.shape
    third = max(1, nz // 3)
    bottom = float(density[:, :, :third].mean())
    middle = float(density[:, :, third:2 * third].mean())
    top = float(density[:, :, 2 * third:].mean())
    assert top > middle and bottom > middle, (
        f"bottom {bottom:.3f} middle {middle:.3f} top {top:.3f}"
    )
    assert run.history[-1]["volume_fraction"] == pytest.approx(0.4, abs=1e-6)


# ---------------------------------------------------------------------------
# 3. Mesh independence, which is what the filter is for.
# ---------------------------------------------------------------------------


def test_the_same_physical_filter_radius_gives_the_same_topology(
        topology) -> None:
    """The filter's whole justification, tested as its whole justification.

    ``filter_radius_mm`` is not a manufacturing constraint -- printability is
    deferred by decision and overhang angle is not built. It is here because
    without it SIMP checkerboards: the discretised problem has no minimiser
    and the answer changes with the grid. So the claim to test is that the
    answer does *not* change with the grid, and a 4 mm radius at 2.5 mm and
    at 1.5 mm cells must agree about where the material goes.
    """

    designs = {}
    for element_mm in (2.5, 1.5):
        raw = topology.cantilever_plan(size_mm=(60.0, 10.0, 30.0),
                                       element_mm=element_mm,
                                       volume_fraction=0.3)
        raw["filter_radius_mm"] = 4.0
        raw["iterations"] = 60
        run = topology.optimise(topology.Plan.from_mapping(raw))
        designs[element_mm] = run

    def _resample(run, shape=(24, 4, 12)):
        density = run.density
        picks = [((np.arange(n) + 0.5) * density.shape[axis] / n).astype(int)
                 for axis, n in enumerate(shape)]
        return density[np.ix_(*picks)]

    coarse = _resample(designs[2.5]) > 0.5
    fine = _resample(designs[1.5]) > 0.5
    agreement = float(np.mean(coarse == fine))
    assert agreement > 0.85, f"the two grids agree about only {agreement:.1%}"

    # ...and they agree about the stiffness they achieved, too.
    a = designs[2.5].history[-1]["compliance_n_mm"]
    b = designs[1.5].history[-1]["compliance_n_mm"]
    assert abs(a - b) / b < 0.15, f"{a:.3f} against {b:.3f}"


# ---------------------------------------------------------------------------
# 4. Extraction.
# ---------------------------------------------------------------------------


def test_every_tetrahedron_is_listed_right_handed(topology) -> None:
    """Because leaving three of them left-handed is not a subtle failure.

    The winding table is derived from a parity argument, and a parity
    argument only means anything against a fixed handedness. Three of the
    six natural listings are left-handed; with them left so, the extracted
    surface came out topologically closed with **half its triangles inside
    out**, so the closure check passed and the enclosed volume was exactly
    zero.
    """

    assert len(topology._TETRAHEDRA) == 6
    assert len({frozenset(tet) for tet in topology._TETRAHEDRA}) == 6
    for tet in topology._TETRAHEDRA:
        corners = topology._CUBE_CORNERS[list(tet)]
        volume = np.linalg.det(np.stack([corners[1] - corners[0],
                                         corners[2] - corners[0],
                                         corners[3] - corners[0]]))
        assert volume > 0.0, f"{tet} is listed left-handed"
    # Every tetrahedron carries the main diagonal, which is what makes two
    # neighbouring cubes split their shared face on the same diagonal.
    for tet in topology._TETRAHEDRA:
        assert 0 in tet and 7 in tet
    # Six tetrahedra of a sixth of the cube each: the split is a partition.
    assert sum(
        abs(np.linalg.det(np.stack([
            topology._CUBE_CORNERS[list(tet)][k]
            - topology._CUBE_CORNERS[list(tet)][0] for k in (1, 2, 3)]))) / 6.0
        for tet in topology._TETRAHEDRA) == pytest.approx(1.0)


def test_the_case_table_covers_the_sixteen_cases_and_no_more(topology) -> None:
    """Sixteen, not two hundred and fifty-six, and none of them ambiguous.

    A tetrahedron's four vertices admit no configuration where two different
    surfaces would separate them -- which is exactly the hole in marching
    cubes that produces non-manifold output, and exactly why this is
    hand-written rather than a dependency.
    """

    cases = topology._CASES
    assert len(cases) == 16
    assert cases[0] == () and cases[15] == ()
    for index, entry in enumerate(cases[1:15], start=1):
        above = bin(index).count("1")
        assert len(entry) == (1 if above in (1, 3) else 2)
        for triangle in entry:
            assert len(triangle) == 3
            for low, high in triangle:
                # Every cut edge joins a solid vertex to a void one.
                assert ((index >> low) & 1) != ((index >> high) & 1)


def test_a_solid_block_extracts_to_its_own_box(topology, stress) -> None:
    """The simplest surface there is, at the size it is supposed to be.

    Sampling at cell centres with a one-cell void pad is what makes this
    exact: the level set of a step from 1 to 0 sits halfway between two
    centres, which is the cell face, which is the boundary of the block.
    """

    grid = stress.voxelise(stress.box_triangles([10.0, 6.0, 4.0]), 1.0)
    density = np.asarray(grid.occupancy, dtype=float)
    vertices, faces = topology.extract_surface(density, grid)
    closure = topology.surface_is_watertight(faces)
    assert closure["watertight"], closure
    assert closure["boundary_edges"] == 0 and closure["non_manifold_edges"] == 0
    assert np.allclose(vertices.min(axis=0), [0.0, 0.0, 0.0])
    assert np.allclose(vertices.max(axis=0), [10.0, 6.0, 4.0])
    # A stair-stepped block loses a chamfer off each convex edge at this
    # resolution; 5% of 240 mm^3 is that chamfer and it shrinks with the cell.
    assert stress.mesh_volume_mm3(vertices[faces]) == pytest.approx(240.0, rel=0.05)


def test_the_extracted_volume_converges_and_smoothing_does_not_shrink_it(
        topology, stress) -> None:
    """A sphere, whose volume is known, at three resolutions.

    Two claims in one measurement. The extraction converges on the true
    volume -- 4.5% low at ten cells across and 0.2% low at forty -- and
    Taubin smoothing does not shrink the shape, which is the whole reason
    the smoother alternates a positive pass with a larger negative one
    instead of just running a Laplacian. The last loop below is what makes
    that second claim mean something: the same passes with ``mu = 0`` are a
    plain Laplacian, and they eat the sphere.
    """

    radius = 7.0
    exact = 4.0 / 3.0 * np.pi * radius ** 3
    errors = []
    for count in (10, 20, 40):
        spacing = 20.0 / count
        grid = stress.voxelise(stress.box_triangles([20.0, 20.0, 20.0]), spacing)
        centres = grid.cell_centres().reshape(grid.shape + (3,))
        distance = np.linalg.norm(centres - 10.0, axis=-1)
        density = np.clip(0.5 + (radius - distance) / spacing, 0.0, 1.0)

        vertices, faces = topology.extract_surface(density, grid)
        assert topology.surface_is_watertight(faces)["watertight"]
        raw = stress.mesh_volume_mm3(vertices[faces])
        smoothed = stress.mesh_volume_mm3(
            topology.taubin_smooth(vertices, faces, passes=10)[faces])
        errors.append(abs(raw - exact) / exact)
        assert smoothed > raw * 0.999, (
            f"Taubin smoothing shrank the shape: {raw:.2f} -> {smoothed:.2f}"
        )
        assert abs(smoothed - raw) < 0.015 * raw, (
            f"smoothing moved the volume by {abs(smoothed - raw) / raw:.2%}"
        )

        # The same ten passes with `mu = 0` are a plain Laplacian. Measured
        # here: it takes 20% off the sphere at ten cells across, 5.0% at
        # twenty and 1.3% at forty, while Taubin adds 0.5%, 0.2% and 0.06%.
        laplacian = stress.mesh_volume_mm3(
            topology.taubin_smooth(vertices, faces, passes=10, mu=0.0)[faces])
        assert laplacian < 0.995 * raw < smoothed, (
            f"raw {raw:.2f}, Taubin {smoothed:.2f}, Laplacian {laplacian:.2f} "
            "-- a plain Laplacian did not shrink the sphere, so this "
            "measurement is not testing what makes the alternation necessary"
        )
    assert errors[0] > errors[1] > errors[2], errors
    assert errors[-1] < 0.01


def test_the_extracted_stl_revoxelises_back_to_the_field_it_came_from(
        topology, stress, cantilever) -> None:
    """S0 verifies S2: two parts of one tree checking each other.

    The strong form of the round trip. The density field becomes a surface,
    the surface becomes an STL on disk, S0's *own* voxeliser reads that STL
    back, and the fill it produces has to be the fill the optimiser
    declared. Every step of the chain that could be inside out, mis-scaled or
    half a cell adrift is exercised at once, and the parity fill is asked
    about a shape far harder than the boxes S0 tests it on.
    """

    _, run = cantilever
    vertices, faces = topology.extract_surface(run.density, run.grid)
    vertices = topology.taubin_smooth(vertices, faces, passes=10)
    triangles = vertices[faces]

    volume = stress.mesh_volume_mm3(triangles)
    assert volume > 0.0, "the surface came out inside out"

    with tempfile.TemporaryDirectory() as directory:
        path = stress.write_binary_stl(triangles, Path(directory) / "design.stl")
        read_back, _ = stress.read_solid(path)
        assert len(read_back) == len(triangles)
        assert stress.mesh_volume_mm3(read_back) == pytest.approx(volume, rel=1e-4)

        # Re-voxelised at half the optimiser's own cell, so the fill is a
        # measurement of the surface rather than of the grid it came from.
        fine = float(run.grid.spacing.min()) / 2.0
        refilled = stress.voxelise(read_back, fine)
        filled = refilled.solid_count * refilled.element_volume_mm3
        assert filled == pytest.approx(volume, rel=0.10), (
            f"the surface encloses {volume:.1f} mm^3 and refills to "
            f"{filled:.1f} mm^3"
        )

    # A converged SIMP design with a stiffness floor is one connected
    # structure, which is what makes `part.shape_from_mesh` able to sew it.
    counts = np.bincount(faces.ravel(), minlength=len(vertices))
    assert counts.min() > 0, "the surface carries an unreferenced vertex"


def test_the_report_declares_the_surface_it_wrote(topology, cantilever,
                                                  tmp_path) -> None:
    plan, run = cantilever
    stl = tmp_path / "design.stl"
    finished = topology.report(run, plan, stl=stl)
    assert finished["schema"] == topology.REPORT_SCHEMA
    assert finished["surface"]["watertight"] is True
    assert finished["surface"]["stl"]["sha256"] == __import__("hashlib").sha256(
        stl.read_bytes()).hexdigest()
    assert finished["result"]["final_volume_fraction"] == pytest.approx(
        plan.volume_fraction, abs=1e-6)
    # `cadex_importable` is not asserted here: this suite runs with the
    # engine on `sys.path` and FreeCAD stubbed, so it is legitimately true.
    # The negative is asserted where it means something, which is the
    # subprocess run below.
    assert "cadex_importable" in finished


# ---------------------------------------------------------------------------
# S4a: the four field keys (ADR-146).
# ---------------------------------------------------------------------------


def _asymmetric_plan(topology, **overrides):
    """The cantilever with its tip load pushed off to one side.

    Off-centre on purpose: the stock cantilever is already symmetric about
    ``y`` because its load spans the whole width, so it would pass a
    symmetry test without the key doing anything at all.
    """

    raw = topology.cantilever_plan(size_mm=(40.0, 16.0, 20.0), element_mm=2.0,
                                   volume_fraction=0.35)
    raw["iterations"] = 20
    raw["filter_radius_mm"] = 4.0
    raw["loads"] = [{
        "name": "tip",
        "region": {"box": {"min_mm": [40.0 - 1e-6, 0.0, -1e-6],
                           "max_mm": [None, 6.0, 1e-6]}},
        "force_n": [0.0, 0.0, -100.0],
    }]
    raw.update(overrides)
    return topology.Plan.from_mapping(raw)


def test_the_four_s4a_keys_are_off_by_default(topology) -> None:
    """A plan written against S2 carves the same field under S4's file.

    All four keys are opt-in, so this is the assertion that S4a cost the
    existing behaviour nothing -- and it is cheap, because the defaults are
    on the dataclass rather than scattered through the loop.
    """

    plan = topology.Plan.from_mapping(topology.cantilever_plan())
    assert plan.symmetry == () and plan.extrude is None
    assert plan.interface_pad_mm == 0.0 and plan.pin_domain_planes is False

    run = topology.optimise(_asymmetric_plan(topology))
    assert run.pads.sum() == 0
    assert not np.allclose(run.density, np.flip(run.density, axis=1)), (
        "the fixture is meant to be asymmetric, or the symmetry test below "
        "proves nothing"
    )


def test_symmetry_mirrors_the_design_about_the_domain_mid_plane(topology) -> None:
    """The largest looks-designed win per line in the file.

    Imposed on the **filtered sensitivity**, so it holds exactly rather than
    approximately: the optimality-criteria update is pointwise and monotone
    in the sensitivity, so a symmetric sensitivity and a symmetric starting
    design give a symmetric step for ever after.
    """

    run = topology.optimise(_asymmetric_plan(topology, symmetry=["y"]))
    assert np.abs(run.density - np.flip(run.density, axis=1)).max() < 1e-12


def test_symmetry_refuses_a_domain_that_is_not_symmetric(topology) -> None:
    """Mirroring into cells that are not in the domain is not symmetry."""

    with pytest.raises(topology.TopologyError, match="not symmetric"):
        topology.optimise(_asymmetric_plan(
            topology, symmetry=["y"],
            void=[{"name": "half",
                   "region": {"box": {"min_mm": [None, 0.0, None],
                                      "max_mm": [None, 4.0, None]}}}]))


def test_extrude_holds_the_density_constant_through_the_thickness(
        topology) -> None:
    """A 2.5-D part you can route or laser-cut, not only print.

    The residual is the number the file's own comment quotes: averaging the
    sensitivity alone leaves a column standard deviation of 0.105 -- a taper
    you can see -- and averaging the volume gradient with it brings that to
    0.0009, which you cannot. The rest is the cone filter's edge effect and
    is left alone so the sensitivity stays exactly checkable.
    """

    run = topology.optimise(_asymmetric_plan(topology, extrude="y"))
    assert float(run.density.std(axis=1).max()) < 0.01


def test_a_pad_grows_the_interface_and_removes_the_membrane(topology) -> None:
    """The bug fix wearing an aesthetics hat, measured as a thickness.

    A load declared over a 2 mm-deep face gets the cheapest membrane that
    can receive the force -- structurally correct, useless as a mounting
    interface, and it is also what generates garbage skeleton nodes at
    exactly the places S4b has to anchor to.

    The statistic is the **fill fraction of the interface neighbourhood**,
    measured on the *same* set of cells in both runs: solid everywhere with
    the pad, by construction, and full of holes without it. A depth
    statistic was tried first and says nothing here -- the tip load sits in
    a corner of the blank, where the distance to the surface is one cell
    whatever the optimiser does with the material behind it.
    """

    bare = topology.optimise(_asymmetric_plan(topology))
    padded = topology.optimise(_asymmetric_plan(topology, interface_pad_mm=5.0))

    assert padded.pads.sum() > 0
    assert bare.pads.sum() == 0
    assert np.all(padded.density[padded.pads] == 1.0)

    # The pad is exactly the declared interfaces, dilated -- not a region of
    # its own invention.
    plan = _asymmetric_plan(topology, interface_pad_mm=5.0)
    interfaces = topology._interface_cells(
        list(plan.load_case["supports"]) + list(plan.load_case["loads"]),
        padded.grid, "interface")
    expected = (topology._dilate(interfaces, 5.0, padded.grid.spacing)
                & np.asarray(padded.grid.occupancy, dtype=bool))
    assert np.array_equal(padded.pads, expected)

    holes = float((bare.density[padded.pads] < 0.5).mean())
    assert holes > 0.05, (
        f"only {holes:.2%} of the mounting pad was missing before the pad "
        "key was declared, so this fixture does not exercise it"
    )


def test_a_pad_never_overrides_a_declared_void(topology) -> None:
    """``void`` is the region a person declared; the pad is one this file
    grew. The clash is clipped and said out loud rather than refused."""

    run = topology.optimise(_asymmetric_plan(
        topology, interface_pad_mm=6.0,
        void=[{"name": "slot",
               "region": {"box": {"min_mm": [34.0, None, None],
                                  "max_mm": [None, None, 4.0]}}}]))
    assert not np.any(run.pads & run.void)
    assert any("interface pad" in warning for warning in run.warnings)


def test_pinning_keeps_a_mounting_face_flat_through_the_smoother(
        topology) -> None:
    """Taubin does not know a face is a face.

    The root of the cantilever is a flat plane of the blank that the run
    held solid; the smoother reads the rim where it meets the carved body as
    curvature and pulls the whole face in. Pinning the vertices that started
    on a domain plane keeps them there while they still slide *within* it,
    so the staircase along the rim still goes.
    """

    plan = _asymmetric_plan(topology, interface_pad_mm=5.0)
    run = topology.optimise(plan)
    vertices, faces = topology.extract_surface(run.density, run.grid)
    planes = topology.domain_planes(run.grid)
    on_root = np.abs(vertices[:, 0] - float(run.grid.origin[0])) <= 1e-6
    assert on_root.sum() > 10, "the fixture has no flat root to keep flat"

    loose = topology.taubin_smooth(vertices, faces, passes=10)
    pinned = topology.taubin_smooth(vertices, faces, passes=10, planes=planes)

    assert np.abs(loose[on_root, 0] - run.grid.origin[0]).max() > 1e-3
    assert np.abs(pinned[on_root, 0] - run.grid.origin[0]).max() <= 1e-9
    # It is a pin, not a freeze: the vertices still move within the plane.
    assert np.abs(pinned[on_root, 1:] - vertices[on_root, 1:]).max() > 1e-6


def test_the_report_declares_which_s4a_keys_were_used(topology) -> None:
    """A receipt that does not say what it did is not a receipt."""

    plan = _asymmetric_plan(topology, symmetry=["y"], interface_pad_mm=4.0,
                            pin_domain_planes=True)
    finished = topology.report(topology.optimise(plan), plan)
    assert finished["plan"]["symmetry"] == ["y"]
    assert finished["plan"]["interface_pad_mm"] == 4.0
    assert finished["plan"]["pin_domain_planes"] is True
    assert finished["grid"]["interface_pad_cells"] > 0


# ---------------------------------------------------------------------------
# Keep, void, and the refusals.
# ---------------------------------------------------------------------------


def test_a_keep_region_survives_the_run_and_a_void_region_stays_empty(
        topology) -> None:
    """Both enter as **bounds**, which is why they cost nothing in the loop.

    They also reuse S0's region vocabulary unchanged -- ``face``, ``box``,
    ``sphere``, ``all`` -- so S2 invents no geometry language of its own and
    a load case written for a stress check is already most of a plan.
    """

    raw = topology.cantilever_plan(size_mm=(48.0, 12.0, 24.0), element_mm=3.0,
                                   volume_fraction=0.4)
    raw["iterations"] = 25
    raw["filter_radius_mm"] = 6.0
    raw["keep"] = [{"name": "boss",
                    "region": {"sphere": {"centre_mm": [24.0, 6.0, 20.0],
                                          "radius_mm": 5.0}}}]
    raw["void"] = [{"name": "bore",
                    "region": {"box": {"min_mm": [8.0, None, 8.0],
                                       "max_mm": [16.0, None, 16.0]}}}]
    run = topology.optimise(topology.Plan.from_mapping(raw))

    assert run.keep.sum() > 0 and run.void.sum() > 0
    assert np.all(run.density[run.keep] == 1.0)
    assert np.all(run.density[run.void] == 0.0)
    assert not np.any(run.keep & run.void)


def test_a_plan_that_cannot_be_carried_out_is_refused_with_a_sentence(
        topology) -> None:
    """Every refusal names the number it refused and what to do instead."""

    good = topology.cantilever_plan()

    with pytest.raises(topology.TopologyError, match="schema"):
        topology.Plan.from_mapping({**good, "schema": "something-else"})
    with pytest.raises(topology.TopologyError, match="volume_fraction"):
        topology.Plan.from_mapping({**good, "volume_fraction": 1.5})
    with pytest.raises(topology.TopologyError, match="checkerboards"):
        topology.Plan.from_mapping({**good, "filter_radius_mm": 0.1})
    with pytest.raises(topology.TopologyError, match=r"penalty"):
        topology.Plan.from_mapping({**good, "penalty": 12.0})
    with pytest.raises(topology.TopologyError, match="exactly one `domain`"):
        topology.Plan.from_mapping({**good, "domain": {}})

    # keep larger than the whole budget
    overfull = {**good, "volume_fraction": 0.05, "element_mm": 4.0,
                "keep": [{"region": {"all": {}}}]}
    with pytest.raises(topology.TopologyError, match="keep"):
        topology.optimise(topology.Plan.from_mapping(overfull))

    # everything pinned: nothing left to decide
    frozen = {**good, "element_mm": 4.0, "void": [{"region": {"all": {}}}]}
    with pytest.raises(topology.TopologyError, match="void"):
        topology.optimise(topology.Plan.from_mapping(frozen))


def test_a_solid_domain_is_the_same_code_path_as_a_box(topology, stress,
                                                       tmp_path) -> None:
    """Lightening an existing part is a run whose domain happens to be the part.

    It falls out of the box case rather than being a second feature, and the
    benchmarks are written around the blank because that is the primary case
    -- but the path is real and is tested, not asserted.
    """

    path = stress.write_binary_stl(
        stress.box_triangles([40.0, 10.0, 20.0]), tmp_path / "blank.stl")
    raw = topology.cantilever_plan(element_mm=2.5, volume_fraction=0.4)
    raw["domain"] = {"solid": path.name}
    raw["iterations"] = 20
    raw["filter_radius_mm"] = 5.0
    raw["loads"] = [{"name": "tip",
                     "region": {"face": {"axis": "x", "at": "max",
                                         "depth_mm": 1e-6}},
                     "force_n": [0.0, 0.0, -100.0]}]
    plan = topology.Plan.from_mapping(raw, base=tmp_path)
    run = topology.optimise(plan)
    assert run.grid.shape == (16, 4, 8)
    assert run.history[-1]["volume_fraction"] == pytest.approx(0.4, abs=1e-6)

    with pytest.raises(topology.TopologyError, match="not a file"):
        topology.optimise(topology.Plan.from_mapping(
            {**raw, "domain": {"solid": "nowhere.stl"}}, base=tmp_path))


# ---------------------------------------------------------------------------
# The CLI, and the rule S2c imposes.
# ---------------------------------------------------------------------------


def test_the_report_is_one_json_line_on_stdout(topology) -> None:
    """``training/``'s discipline, and for the reason ADR-093 measured.

    Exactly one JSON line on stdout; the human stream is stderr and nothing
    parses stderr.
    """

    result = subprocess.run(
        [sys.executable, str(TOPOLOGY), "--self-check"],
        capture_output=True, text=True, check=False, timeout=1800,
        env={**os.environ, "PYTHONPATH": ""},
    )
    if result.returncode != 0 and "No module named" in result.stderr:
        pytest.skip("this interpreter has no scipy")
    assert result.returncode == 0, result.stderr[-2000:]
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, result.stdout[:2000]
    report = json.loads(lines[0])
    assert report["schema"] == "cadex-analysis-topology-self-check-v1"
    assert report["cadex_importable"] is False
    assert report["improvement_factor"] > 4.0
    assert report["surface"]["watertight"] is True


def test_a_refusal_is_an_exit_code_and_a_sentence(tmp_path) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(TOPOLOGY), str(plan)],
        capture_output=True, text=True, check=False, timeout=300)
    assert result.returncode == 2
    assert result.stderr.startswith("refused: ")
    assert not result.stdout.strip()


def test_s2_invents_no_new_asset_suffix() -> None:
    """The rule S2c imposes, and it is a rule rather than a preference.

    A ``.cxdensity`` or a sidecar receipt would be **silently dropped by
    Save-As** -- the exact bug ADR-046 recorded and ADR-138 fixed for
    ``.cxpart``, still open today for ``.cxpolicy``. ``.stl`` is already in
    ``_ASSET_SUFFIXES`` and already in the shell's mirror of it, so an S2
    result comes home for free; the density field and the run's receipt stay
    offboard, in the run directory, where nothing can drop them.
    """

    from CadexScriptedRuntime import _ASSET_SUFFIXES, _STORED_ASSET_SUFFIXES

    assert ".stl" in _ASSET_SUFFIXES
    source = TOPOLOGY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    # `isalpha` rather than `isalnum`, so that a format specifier -- `.3f`,
    # `.6g` -- is not read as a file suffix.
    invented = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
            if (text.startswith(".") and 4 <= len(text) <= 12
                    and text[1:].isalpha()):
                invented.add(text.lower())
    assert ".stl" in invented, (
        "topology.py no longer names the suffix it writes; this check would "
        "now pass vacuously"
    )
    unknown = {suffix for suffix in invented
               if suffix not in _STORED_ASSET_SUFFIXES
               and suffix not in {".npy", ".json"}}
    assert not unknown, (
        f"topology.py names asset suffixes the store would drop: {unknown}"
    )


# ---------------------------------------------------------------------------
# The round trip home, through a real engine.
# ---------------------------------------------------------------------------


SHIM = ROOT / "cadex"


def _engine_available() -> bool:
    if os.environ.get("CADEX_ENGINE_ROOT"):
        return True
    return (ROOT / "build/release/bin/FreeCADCmd").is_file()


_IMPORT_SCRIPT = """
scan = mesh.import_file("design.stl")

result = {"design": scan}
"""


@pytest.mark.skipif(not _engine_available(),
                    reason="no built engine; run `pixi run build-engine`")
def test_a_carved_shape_comes_home_through_put_asset(topology, stress,
                                                     tmp_path) -> None:
    """The whole of S2c, and it costs no engine change at all.

    ``.stl`` is already in ``_ASSET_SUFFIXES`` *and* in the shell's
    ``CARRIED_ASSET_SUFFIXES``, so a SIMP result arrives through ``put_asset``
    and Save-As carries it. What this pins is the consequence that matters:
    the script **publishes** the imported mesh as an output, so it carries a
    ``geometry_sha256`` and therefore reaches the project digest -- which is
    the only thing that verifies an STL's bytes, since
    ``compute_project_digest`` does not walk ``assets/``.
    """

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    raw = topology.cantilever_plan(size_mm=(40.0, 10.0, 20.0), element_mm=2.5,
                                   volume_fraction=0.4)
    raw["iterations"] = 25
    raw["filter_radius_mm"] = 5.0
    plan = topology.Plan.from_mapping(raw)
    run = topology.optimise(plan)
    vertices, faces = topology.extract_surface(run.density, run.grid)
    vertices = topology.taubin_smooth(vertices, faces, passes=10)
    carved = stress.write_binary_stl(vertices[faces], tmp_path / "design.stl")

    project = tmp_path / "project"
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(project)})
        assert opened["ok"] is True, opened

        stored = client.request(
            "put_asset", {"source_path": str(carved), "name": "design.stl"})
        assert stored["ok"] is True, stored
        assert stored["bytes"] == carved.stat().st_size
        assert (project / "assets" / "design.stl").is_file()

        written = client.request(
            "write_script",
            {"source": _IMPORT_SCRIPT, "expected_revision": "",
             "display": {"quality": "standard"}})
        assert written["ok"] is True, written
        first_digest = written["digest"]
        assert written["display"]["design"]["artifact_kind"] == "mesh"

        outputs = client.request("inspect", {"scope": "output"})
        assert outputs["ok"] is True, outputs

        # A rebuild of the same script reaches the same digest, which is the
        # claim that the imported geometry is part of the model's identity
        # rather than a file that happens to be nearby.
        again = client.request(
            "write_script",
            {"source": _IMPORT_SCRIPT, "expected_revision": written["revision"],
             "display": {"quality": "standard"}})
        assert again["ok"] is True, again
        assert again["digest"] == first_digest
    finally:
        _stop(client)
