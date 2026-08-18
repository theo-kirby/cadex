# SPDX-License-Identifier: LGPL-2.1-or-later

"""The offboard structural analysis, and the two things that make it S0.

``analysis/`` is not part of the engine (ADR-141, the contract ADR-084 wrote
for ``training/``). So, like ``test_dynamics_policy_trainer``, most of this
file tests it the way you test a contract with something that is not here:
by reading its source and asserting what it may and may not contain -- where
it lives, what CMake must never do with it, what it may import, and the one
prohibition this tree has that ``training/`` did not need, which is that
nothing in it may import a GPL package.

The rest actually runs it, and that half is the point of the slice. **A
stress number nobody can check is not a result**, so the numeric tests are
the two independent checks S0 was specified around:

* the cantilever against its closed form, and a refinement sweep that
  settles;
* the same grid solved by CalculiX, at arm's length, as a second
  implementation. ADR-129's lesson, applied.

The numeric half runs in the pixi environment -- numpy, scipy, mujoco and
``ccx`` are all there -- and skips cleanly where they are not, so this file
works from either interpreter.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[4]
ANALYSIS = ROOT / "analysis"
STRESS = ANALYSIS / "cadex_stress.py"
LOADS = ANALYSIS / "loads_from_rollout.py"
CALCULIX = ANALYSIS / "calculix.py"
SEARCH = ANALYSIS / "search.py"
TOPOLOGY = ANALYSIS / "topology.py"
SKELETON = ANALYSIS / "skeleton.py"
REQUIREMENTS = ANALYSIS / "requirements.txt"


def _module(path: Path):
    """One analysis file imported by path, the way the trainer test does it.

    By path rather than by package because ``analysis/`` is not on any
    interpreter's path and must never need to be: it is a directory you copy
    to another machine, not a module the engine can reach.
    """

    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(path.stem, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def stress():
    pytest.importorskip("scipy", reason="the hex core solves with scipy.sparse")
    return _module(STRESS)


# ---------------------------------------------------------------------------
# Where it lives, and what that placement is for.
# ---------------------------------------------------------------------------


def test_the_analysis_tree_lives_at_the_root_and_not_under_the_engine() -> None:
    """The same three reasons ``training/`` is where it is (ADR-141).

    CMake never installs it, so it cannot reach the payload by accident; it
    is a thing you copy to a machine with time to spend; and its
    dependencies are pinned in a requirements.txt installed into a venv
    there.
    """

    for path in (STRESS, LOADS, CALCULIX, SEARCH, TOPOLOGY, SKELETON,
                 REQUIREMENTS,
                 ANALYSIS / "README.md"):
        assert path.is_file(), f"{path} is missing"
        assert "src/Mod/cadex" not in path.as_posix()


def test_no_cmake_rule_installs_the_analysis_tree() -> None:
    """The payload check that does not need a payload built.

    ``test_engine_purity_guardrails`` asserts what reaches a *staged*
    payload; this asserts nothing would ever put this there.
    """

    hits = []
    for path in ROOT.rglob("CMakeLists.txt"):
        if any(part in {"build", "build_darwin", ".pixi", "shell", ".git"}
               for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ("cadex_stress" in text or "topology.py" in text
                or "skeleton.py" in text or "analysis/" in text):
            hits.append(str(path))
    assert not hits, f"CMake references the offboard analysis tree: {hits}"


def test_the_requirements_are_exactly_pinned_and_stay_out_of_pixi() -> None:
    """ADR-076's constant stays one entry long, which is what it is named for.

    The three pins are the versions the engine payload itself carries. That
    is the point rather than a coincidence: if S3 ever moves a linear solve
    in-engine it costs no payload bytes, and the number it computes there is
    the number computed here.
    """

    lines = [
        line.strip()
        for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert lines, "the requirements file declares nothing"
    for line in lines:
        assert "==" in line, f"{line!r} is not exactly pinned"
    assert {line.split("==")[0] for line in lines} == {"numpy", "scipy", "mujoco"}

    manifest = ROOT / "package/rattler-build/scripts/relocate_conda_environment.py"
    text = manifest.read_text(encoding="utf-8")
    start = text.index("CARRIED_PYPI_PACKAGES")
    carried = text[start:text.index(")", start)]
    assert carried.count('"') + carried.count("'") == 2, (
        "CARRIED_PYPI_PACKAGES grew past one entry. The analysis tree is "
        "offboard by design (ADR-141) and the engine must ship without it."
    )


def test_the_analysis_files_import_only_numpy_and_the_standard_library() -> None:
    """What may be reached at module scope, and what must be deferred.

    ``numpy`` is at module scope on purpose -- it is in the payload, so its
    presence proves nothing about whether this could be in-engine. ``scipy``
    and ``mujoco`` are deferred, so every contract assertion in this file
    runs on an interpreter that has neither.
    """

    allowed_top = {
        "__future__", "argparse", "collections", "dataclasses", "hashlib",
        "itertools", "json", "math", "os", "pathlib", "platform", "shutil",
        "struct", "subprocess", "sys", "tempfile", "time", "typing", "numpy",
        "cadex_stress", "topology",
    }
    allowed_deferred = allowed_top | {
        "scipy", "mujoco", "OCC", "CadexDynamics", "importlib",
    }
    for path in (STRESS, LOADS, CALCULIX, SEARCH, TOPOLOGY, SKELETON):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
            else:
                roots = {(node.module or "").split(".")[0]}
            top_level = node.col_offset == 0
            permitted = allowed_top if top_level else allowed_deferred
            assert roots <= permitted, (
                f"{path.name} line {node.lineno} imports {roots - permitted}"
            )


def test_nothing_under_analysis_imports_a_gpl_package() -> None:
    """The one prohibition this tree has that ``training/`` did not need.

    ``analysis/`` is engine-side, and ``docs/PROVENANCE.md`` 1 puts the
    engine side at LGPL. ``AGENTS.md`` calls the GPL boundary "one-way and
    hard" about ``shell/``, and the reasoning transfers exactly: a GPL
    import in a repository-resident file is not a judgement call.

    The named packages are the ones a reasonable person reaches for while
    doing this work and that a survey found are GPL: the meshers, the mesh
    repairers, the MMA implementation everyone uses, and the ``.frd``
    converter that computes von Mises for you.
    """

    forbidden = {
        "gmsh": "GPL-2; its linking exception runs the other way",
        "pygmsh": "GPL-3",
        "pymeshlab": "GPL-3, and meshlabserver is gone so there is no CLI escape",
        "pymeshfix": "GPL-3",
        "pygalmesh": "GPL-3",
        "tetgen": "AGPL-3",
        "mmapy": "GPL-3",
        "ccx2paraview": "GPL-3",
        "jax_fem": "GPL-3",
        "fenitop": "GPL-3",
        "platypus": "GPL-3",
    }
    offenders = []
    for path in sorted(ANALYSIS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            roots: set[str] = set()
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                roots = {(node.module or "").split(".")[0]}
            for name in roots & set(forbidden):
                offenders.append(f"{path.name} -> {name} ({forbidden[name]})")
    assert not offenders, (
        f"A GPL package entered the engine-side tree: {offenders}"
    )


def test_calculix_is_driven_as_a_subprocess_and_never_imported() -> None:
    """``ccx`` is GPL-2, so the boundary is a process boundary.

    The same arm's length FreeCAD's own LGPL Fem module used: a text deck in,
    a text result out, nothing linked. Asserted rather than assumed, because
    "just import it" is exactly the shape of the mistake.
    """

    text = CALCULIX.read_text(encoding="utf-8")
    assert "subprocess.run" in text
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = {alias.name for alias in getattr(node, "names", [])}
            names |= {getattr(node, "module", None) or ""}
            assert not any("ccx" in name or "calculix" == name for name in names), (
                f"line {node.lineno} imports CalculiX rather than running it"
            )


def test_the_analysis_tree_is_not_an_engine_module() -> None:
    """Stated as its own assertion because the placement *is* the mechanism."""

    from test_engine_purity_guardrails import DECLARED_ENGINE_MODULES

    assert "cadex_stress" not in DECLARED_ENGINE_MODULES
    assert not (ROOT / "src/Mod/cadex/cadex_stress.py").exists()
    assert "scipy.sparse" in STRESS.read_text(encoding="utf-8"), (
        "cadex_stress.py is gone or is some other file that took the name; "
        "this guardrail would now pass vacuously"
    )


def test_nothing_from_the_analysis_tree_reaches_a_staged_payload() -> None:
    """The shape of the jax/mjx assertion, for the tree ADR-141 adds.

    Skips when no payload is staged, exactly as the packaged checks do: a
    source tree that passes proves nothing about a payload (ADR-023), and a
    payload that is not there proves nothing at all.

    Matched on **content**, not on filename. The payload carries a whole
    CPython, and a stdlib that has an ``idlelib/search.py`` and a
    ``pip/_internal/commands/search.py`` in it — so a filename match reports
    three offenders that have nothing to do with this tree, which is how
    this test failed the first time it was widened. A digest also catches a
    copy that arrived under another name.
    """

    staged = sorted((ROOT / "build/engine").glob("cadex-engine-*"))
    if not staged:
        pytest.skip("no staged payload; run `pixi run stage-engine` first")
    ours = {
        hashlib.sha256(path.read_bytes()).hexdigest(): path.name
        for path in sorted(ANALYSIS.glob("*.py"))
    }
    assert ours, "the analysis tree has no files; this would pass vacuously"
    offenders = [
        f"{path.relative_to(staged[-1])} is {ours[digest]}"
        for path in staged[-1].rglob("*.py")
        if path.is_file()
        and (digest := hashlib.sha256(path.read_bytes()).hexdigest()) in ours
    ]
    assert not offenders, (
        f"the offboard analysis tree entered the payload: {offenders}"
    )
    assert not (staged[-1] / "bin" / "ccx").exists(), (
        "ccx entered the payload. build_engine_payload.sh keeps exactly four "
        "binaries and this is not one of them; shipping it would be "
        "distributing a GPL-2 binary, which is a decision and not a build fix."
    )


# ---------------------------------------------------------------------------
# The element, checked before anything is asked of it.
# ---------------------------------------------------------------------------


def test_the_element_passes_the_constant_strain_patch_test(stress) -> None:
    """A uniform stretch must come out as exactly uniaxial stress.

    The first thing that goes wrong when incompatible modes are added: the
    internal degrees of freedom must vanish under a constant strain, or the
    element cannot represent a rigid body plus a uniform stretch, and every
    number after that is decorated nonsense. It passes here because each
    mode's derivative integrates to zero over the element.
    """

    material = stress.Material(youngs_modulus_mpa=1000.0, poissons_ratio=0.3,
                               yield_strength_mpa=1.0, density_kg_m3=1000.0)
    spacing = np.array([2.0, 3.0, 5.0])
    element = stress.build_element(spacing, material, incompatible=True)

    # A 0.1% stretch along x, with the Poisson contraction that goes with it.
    strain = 1.0e-3
    nu = material.poissons_ratio
    corners = (stress._NODE_SIGNS + 1.0) / 2.0 * spacing[None, :]
    displacement = np.stack([
        corners[:, 0] * strain,
        corners[:, 1] * -nu * strain,
        corners[:, 2] * -nu * strain,
    ], axis=1).reshape(-1)

    internal = element.recover @ displacement
    assert np.abs(internal).max() < 1e-12 * strain * float(spacing.max()), (
        "the incompatible modes did not vanish under a constant strain"
    )
    d = material.elasticity_matrix()
    for point in range(8):
        stress_vector = d @ (element.corner_strain[point] @ displacement)
        assert stress_vector[0] == pytest.approx(
            material.youngs_modulus_mpa * strain, rel=1e-10)
        assert np.abs(stress_vector[1:]).max() < 1e-9


def test_the_element_matrix_is_symmetric_and_has_six_rigid_body_modes(stress) -> None:
    """Six zero eigenvalues, and no negative ones. The cheapest sanity there is."""

    material = stress.Material(1000.0, 0.3, 1.0, 1000.0)
    element = stress.build_element(np.array([1.0, 1.0, 1.0]), material)
    eigenvalues = np.linalg.eigvalsh(element.stiffness)
    assert np.allclose(element.stiffness, element.stiffness.T)
    assert (np.abs(eigenvalues[:6]) < 1e-9 * eigenvalues.max()).all()
    assert eigenvalues[6] > 1e-6 * eigenvalues.max()


# ---------------------------------------------------------------------------
# The cantilever: the closed form, the sweep, and the locking element.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cantilever(stress, tmp_path_factory):
    case = stress.cantilever_case()
    path = stress.write_binary_stl(
        stress.box_triangles(case["size_mm"]),
        tmp_path_factory.mktemp("analysis") / "cantilever.stl")
    return case, path


def test_the_cantilever_matches_its_closed_form(stress, cantilever) -> None:
    """S0's headline claim, against the answer engineering already knows.

    Timoshenko rather than Euler-Bernoulli: at a length-to-height ratio of
    10 the shear term is about 1% and dropping it would put a real error
    inside the tolerance.
    """

    case, path = cantilever
    report = stress.analyse(path, case["load_case"], element_mm=2.5, levels=3)
    tip = report["result"]["max_displacement_mm"]
    assert tip == pytest.approx(case["tip_deflection_mm"], rel=0.03)
    assert report["convergence"]["displacement_converged"]
    assert report["solver"]["relative_residual"] < 1e-8
    assert report["result"]["safety_factor_p99"] > 0.0


def test_the_grid_fits_the_solid_at_every_level(stress, cantilever) -> None:
    """Every level must solve the *same beam*, or the sweep says nothing.

    Measured before the grid was fitted to the bounding box: a 10 mm bar
    voxelised at 1.875 mm kept five cells and lost 6% of its height, and
    stiffness goes as the cube of height -- the sweep moved 1.14 -> 1.45 ->
    1.21 mm and there was no convergence to read.
    """

    case, path = cantilever
    report = stress.analyse(path, case["load_case"], element_mm=2.5, levels=3)
    exact = float(np.prod(case["size_mm"]))
    for level in report["convergence"]["levels"]:
        assert level["volume_mm3"] == pytest.approx(exact, rel=1e-9)
    assert report["mass"]["fill_error_fraction"] < 1e-9
    assert report["mass"]["mass_g"] == pytest.approx(exact * 1240.0 * 1e-6)


def test_displacement_converges_and_the_clamp_singularity_does_not(
        stress, cantilever) -> None:
    """The honest half of the report, asserted so it stays honest.

    Displacement is an integral of the solution and settles. Peak stress at
    a clamped face is a genuine singularity: it has no limit, so it grows
    with every refinement, and a report that called it converged would be
    lying. ``p99`` is the volume statistic that does settle, and is what a
    reader should take.
    """

    case, path = cantilever
    report = stress.analyse(path, case["load_case"], element_mm=2.5, levels=3)
    levels = report["convergence"]["levels"]
    peaks = [level["peak_von_mises_mpa"] for level in levels]
    assert peaks == sorted(peaks), "the clamp singularity stopped growing"
    assert not report["convergence"]["peak_converged"]
    assert report["convergence"]["p99_converged"]
    assert report["convergence"]["displacement_converged"]
    assert report["result"]["p99_von_mises_mpa"] < report["result"][
        "peak_von_mises_mpa"]


def test_the_fully_integrated_element_shear_locks(stress, cantilever) -> None:
    """Why the default element is not the obvious one.

    A trilinear hex with full integration cannot bend without parasitic
    shear, so it reports the beam stiffer than it is. The gap is the
    measurement that makes the choice in ``build_element`` a decision rather
    than a preference -- and it must shrink under refinement, because
    locking is a discretisation error and not a modelling one.
    """

    case, path = cantilever
    closed = case["tip_deflection_mm"]
    errors = []
    for size in (5.0, 2.5):
        locked = stress.analyse(path, case["load_case"], element_mm=size,
                                levels=1, incompatible=False)
        rich = stress.analyse(path, case["load_case"], element_mm=size,
                              levels=1, incompatible=True)
        locked_tip = locked["result"]["max_displacement_mm"]
        rich_tip = rich["result"]["max_displacement_mm"]
        assert locked_tip < rich_tip, "the locking element was not stiffer"
        assert abs(rich_tip - closed) < abs(locked_tip - closed)
        errors.append(abs(locked_tip - closed) / closed)
    assert errors[1] < errors[0], "locking did not ease under refinement"


def test_the_recovered_stress_matches_beam_theory_away_from_the_clamp(
        stress, cantilever) -> None:
    """The number S0 actually delivers, against ``M y / I``.

    Sampled at midspan, where the theory is valid, and at the centroid of
    the top row of elements -- which is half a cell below the surface, so
    the fibre the comparison uses is the fibre the element actually sits at.
    """

    case, path = cantilever
    material = stress.Material.from_mapping(case["load_case"]["material"])
    triangles, _ = stress.read_solid(path)
    grid = stress.voxelise(triangles, 1.25)
    result = stress.solve(grid, material, case["load_case"])

    centres = result.element_centres()
    length, _, height = case["size_mm"]
    slab = np.abs(centres[:, 0] - length / 2.0) < grid.spacing[0]
    top = centres[:, 2] > height - grid.spacing[2]
    chosen = slab & top
    assert chosen.sum() >= 4

    fibre = float(centres[chosen, 2].mean())
    expected = (case["midspan_bending_stress_mpa"]
                * (fibre - height / 2.0) / (height / 2.0))
    assert float(result.centroid_stress_mpa[chosen, 0].mean()) == pytest.approx(
        expected, rel=0.02)


# ---------------------------------------------------------------------------
# Loads: what a declaration means, and what it refuses.
# ---------------------------------------------------------------------------


def test_a_declared_torque_lands_as_a_couple(stress, cantilever) -> None:
    """A 6-D wrench has to be expressible as one load entry.

    That is what makes ``loads_from_rollout.py``'s measured wrench usable
    without a second vocabulary: the couple lands exactly on the region's
    own centroid and adds no net force.
    """

    case, path = cantilever
    triangles, _ = stress.read_solid(path)
    grid = stress.voxelise(triangles, 2.5)
    material = stress.Material.from_mapping(case["load_case"]["material"])
    result = stress.solve(grid, material, case["load_case"])

    torque = [12.0, -30.0, 7.0]
    declared = {
        "loads": [{
            "name": "twist",
            "region": {"face": {"axis": "x", "at": "max", "depth_mm": 3.0}},
            "force_n": [1.0, 2.0, 3.0],
            "torque_n_mm": torque,
        }]
    }
    forces = stress.assemble_forces(grid, material, declared, result.element_dofs)
    nodes = grid.node_positions()
    vectors = forces.reshape(-1, 3)
    loaded = np.nonzero(np.abs(vectors).sum(axis=1) > 0)[0]
    assert np.allclose(vectors.sum(axis=0), [1.0, 2.0, 3.0])

    arms = nodes[loaded] - nodes[loaded].mean(axis=0)[None, :]
    moment = np.cross(arms, vectors[loaded]).sum(axis=0)
    assert np.allclose(moment, torque, atol=1e-8)


def test_an_island_with_no_support_is_dropped_and_declared(stress, tmp_path) -> None:
    """Unheld material is a rigid-body mode, and a singular matrix.

    Dropping it is the only honest option, and the count belongs in the
    report rather than in a log -- ADR-093's rule about receipts, applied to
    a warning.
    """

    triangles = np.concatenate([
        stress.box_triangles([20.0, 10.0, 10.0]),
        stress.box_triangles([20.0, 10.0, 10.0], origin_mm=[40.0, 0.0, 0.0]),
    ])
    path = stress.write_binary_stl(triangles, tmp_path / "two.stl")
    load_case = {
        "schema": stress.LOAD_CASE_SCHEMA,
        "material": {"youngs_modulus_mpa": 3500.0, "poissons_ratio": 0.36,
                     "yield_strength_mpa": 50.0, "density_kg_m3": 1240.0},
        "supports": [{"name": "left",
                      "region": {"face": {"axis": "x", "at": "min",
                                          "depth_mm": 1e-6}}}],
        "loads": [{"name": "down",
                   "region": {"box": {"min_mm": [15.0, None, None],
                                      "max_mm": [20.0, None, None]}},
                   "force_n": [0.0, 0.0, -5.0]}],
    }
    report = stress.analyse(path, load_case, element_mm=2.5, levels=1)
    assert any("not connected to any support" in text
               for text in report["warnings"])
    assert report["result"]["peak_von_mises_mpa"] > 0.0


def test_a_load_case_of_another_schema_is_refused(stress, tmp_path) -> None:
    path = tmp_path / "wrong.json"
    path.write_text(json.dumps({"schema": "something-else"}), encoding="utf-8")
    with pytest.raises(stress.StressError):
        stress._load_case(path)


def test_a_material_without_a_yield_strength_is_refused(stress) -> None:
    """There is no default strength here and there should not be.

    A safety factor against a yield nobody declared is a number pretending
    to be a verdict.
    """

    with pytest.raises(stress.StressError):
        stress.Material.from_mapping({"youngs_modulus_mpa": 1.0,
                                      "poissons_ratio": 0.3,
                                      "density_kg_m3": 1000.0})


def test_an_inside_out_tessellation_is_refused(stress, tmp_path) -> None:
    """A surface with reversed normals fills to the complement of the part."""

    triangles = stress.box_triangles([10.0, 10.0, 10.0])[:, ::-1, :]
    path = stress.write_binary_stl(triangles, tmp_path / "inverted.stl")
    with pytest.raises(stress.StressError, match="inside out"):
        stress.analyse(path, stress.cantilever_case()["load_case"],
                       element_mm=2.5, levels=1)


def test_the_voxel_volume_matches_a_shape_the_grid_cannot_fit(stress, tmp_path) -> None:
    """A cylinder is where a voxel grid is honest about being a voxel grid.

    And where the parity fill is most easily wrong. A cap tessellated as a
    triangle fan gives every radial edge to two triangles, so a ray meeting
    one is counted twice and the column comes out hollow. The first version
    of this filled 300 columns a layer instead of 311 -- the whole ``x = y``
    diagonal -- because the sample nudge used the same fraction on x and y
    and so could not move a point off that diagonal.

    The round trip is in this test on purpose: it is what made the bug
    visible. Writing an STL rounds to float32, which shifted which points
    landed exactly on an edge, so the float64 and float32 fills disagreed
    by 4.5% of the volume. Two fills of the same solid must agree.
    """

    angles = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    radius, height = 10.0, 20.0
    rim = np.stack([radius * np.cos(angles), radius * np.sin(angles)], axis=1)
    triangles = []
    for index in range(len(angles)):
        a = rim[index]
        b = rim[(index + 1) % len(angles)]
        low_a, low_b = [*a, 0.0], [*b, 0.0]
        high_a, high_b = [*a, height], [*b, height]
        triangles += [[low_a, low_b, high_b], [low_a, high_b, high_a],
                      [[0.0, 0.0, 0.0], low_b, low_a],
                      [[0.0, 0.0, height], high_a, high_b]]
    exact = np.pi * radius ** 2 * height
    double = np.asarray(triangles, dtype=float)
    path = stress.write_binary_stl(double, tmp_path / "cylinder.stl")
    read, _ = stress.read_solid(path)

    assert stress.mesh_volume_mm3(read) == pytest.approx(exact, rel=0.01)
    exact_grid = stress.voxelise(double, 1.0)
    rounded_grid = stress.voxelise(read, 1.0)
    assert exact_grid.solid_count == rounded_grid.solid_count, (
        "the fill depends on which floats the triangles arrived in"
    )
    filled = rounded_grid.solid_count * rounded_grid.element_volume_mm3
    assert filled == pytest.approx(exact, rel=0.02)

    # Every layer of a prism is the same layer; a fan edge losing a diagonal
    # shows up here as a layer count that is not constant across the height.
    per_layer = rounded_grid.occupancy.sum(axis=(0, 1))
    assert len(set(per_layer.tolist())) == 1


# ---------------------------------------------------------------------------
# The CLI, and the negative it has to report about itself.
# ---------------------------------------------------------------------------


def test_the_report_is_one_json_line_on_stdout_and_cadex_is_not_importable(
        tmp_path) -> None:
    """ADR-093's rule, and the trainer's ``cadex_importable`` discipline.

    Run with ``-P`` and a scrubbed ``PYTHONPATH`` so the subprocess cannot
    reach the engine. A run where ``cadex_importable`` comes back ``true``
    was not a stock process and proves nothing about what this file can do
    with its own pinned dependencies alone.
    """

    pytest.importorskip("scipy")
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-P", str(STRESS), "--self-check"],
        capture_output=True, text=True, env=environment, check=False,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr[-4000:]
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, "stdout carried more than the one JSON line"
    report = json.loads(lines[0])
    assert report["cadex_importable"] is False
    assert report["schema"] == "cadex-analysis-self-check-v1"
    assert report["c3d8i"]["error_fraction"] < 0.03
    assert report["c3d8"]["error_fraction"] > report["c3d8i"]["error_fraction"]


def test_a_refusal_is_an_exit_code_and_a_sentence(tmp_path) -> None:
    """Nothing parses stderr, so a refusal must not arrive on stdout either."""

    pytest.importorskip("scipy")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"schema": "nope"}), encoding="utf-8")
    solid = tmp_path / "missing.stl"
    solid.write_bytes(b"")
    result = subprocess.run(
        [sys.executable, str(STRESS), str(solid), "--load-case", str(bad)],
        capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert result.stdout.strip() == ""
    assert "refused:" in result.stderr


# ---------------------------------------------------------------------------
# The second method. This is the test that makes the first one worth having.
# ---------------------------------------------------------------------------


def _ccx() -> str | None:
    found = shutil.which("ccx")
    if found:
        return found
    local = ROOT / ".pixi/envs/default/bin/ccx"
    return str(local) if local.is_file() else None


def test_calculix_agrees_with_the_hex_core() -> None:
    """Two implementations of the same element, on the same grid.

    ADR-129's lesson made into a test. ``ccx`` is GPL-2 and is a subprocess:
    a text deck goes in and a text result comes out, which is arm's length
    in the sense the licence means.

    The tolerances are three orders of magnitude looser than what this
    actually measures (4e-7 on displacement, 5e-8 on von Mises when it was
    written), because the point of the test is to catch a sign or a
    permutation, not to pin a linear solver's last digit.
    """

    pytest.importorskip("scipy")
    binary = _ccx()
    if binary is None:
        pytest.skip("no ccx; it is in this repository's pixi environment")

    module = _module(CALCULIX)
    report = module.run_self_check(element_mm=2.5, ccx=binary)
    assert report["agrees"], report["difference"]
    assert report["difference"]["displacement_fraction"] < 1e-3
    assert report["difference"]["von_mises_fraction"] < 5e-3
    assert report["difference"]["worst_component_fraction"] < 5e-3
    assert report["deck"]["element_type"] == "C3D8I"
    assert report["cadex_stress"]["max_displacement_mm"] == pytest.approx(
        report["closed_form"]["tip_deflection_mm"], rel=0.03)


# ---------------------------------------------------------------------------
# The load case measured from a rollout.
# ---------------------------------------------------------------------------


def _chain_model() -> str:
    """A two-link torque-driven leg: the smallest thing with a knee."""

    return """
<mujoco model="chain">
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <worldbody>
    <body name="thigh" pos="0 0 0.5">
      <joint name="hip" type="hinge" axis="0 1 0" pos="0 0 0"/>
      <geom name="g1" type="capsule" fromto="0 0 0 0 0 -0.25" size="0.03"
            density="1200"/>
      <body name="shank" pos="0 0 -0.25">
        <joint name="knee" type="hinge" axis="0 1 0" pos="0 0 0"/>
        <geom name="g2" type="capsule" fromto="0 0 0 0 0 -0.25" size="0.025"
              density="1200"/>
      </body>
    </body>
  </worldbody>
  <actuator>
    <motor name="hip_m" joint="hip" gear="1" ctrlrange="-20 20"/>
    <motor name="knee_m" joint="knee" gear="1" ctrlrange="-20 20"/>
  </actuator>
</mujoco>
"""


def _write_trace(tmp_path, *, steps_per_frame: int, frames: int, torque: float):
    """A trace in the engine's own convention, written by stock MuJoCo.

    The convention is copied from ``CadexDynamics.rollout_policy``: an
    untimed ``input`` frame, then an **unstepped** ``solver_output`` frame at
    t=0 carrying no ``actuator_commands``, then one frame per recorded
    control step whose ``actuator_commands`` is the action that produced it.
    Getting this wrong by one frame is what a replay-fidelity check is for,
    and it is what it caught the first time this ran.
    """

    mujoco = pytest.importorskip("mujoco")
    model_path = tmp_path / "chain.xml"
    model_path.write_text(_chain_model(), encoding="utf-8")
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    names = ["thigh", "shank"]
    ids = {name: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
           for name in names}

    def placements():
        return {name: {
            "position_mm": [float(value) * 1000.0 for value in data.xpos[ids[name]]],
            "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
        } for name in names}

    records = [
        {"frame_index": 0, "frame_kind": "input", "nominal_time_s": None,
         "component_placements": placements()},
        {"frame_index": 1, "frame_kind": "solver_output", "nominal_time_s": 0.0,
         "component_placements": placements()},
    ]
    rng = np.random.default_rng(0)
    for index in range(1, frames):
        command = [float(value) for value in rng.uniform(-torque, torque, 2)]
        data.ctrl[:] = command
        for _ in range(steps_per_frame):
            mujoco.mj_step(model, data)
        records.append({
            "frame_index": len(records), "frame_kind": "solver_output",
            "nominal_time_s": index * steps_per_frame * 0.002,
            "component_placements": placements(),
            "actuator_commands": command,
        })

    trace = {
        "schema": "cadex-assembly-simulation-trace-v1",
        "assembly_output": "legs", "simulation_output": "walk",
        "component_outputs": names,
        "parameters": {"start_time_s": 0.0,
                       "end_time_s": records[-1]["nominal_time_s"],
                       "time_step_s": steps_per_frame * 0.002,
                       "error_tolerance": 1e-8,
                       "frames_per_second": int(1.0 / (steps_per_frame * 0.002))},
        "frames": records,
        "actuator_channels": [
            {"actuator": "hip_m", "joint": "hip", "motion_type": "revolute",
             "kind": "torque", "unit": "N*mm", "low": -20.0, "high": 20.0},
            {"actuator": "knee_m", "joint": "knee", "motion_type": "revolute",
             "kind": "torque", "unit": "N*mm", "low": -20.0, "high": 20.0},
        ],
        "policy": {"policy_output": "walk-policy"},
    }
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(trace), encoding="utf-8")
    return model_path, trace_path


def test_a_replayed_rollout_reproduces_its_trace_and_reads_the_wrench(
        tmp_path) -> None:
    """The whole reason the robot-legs job is tractable.

    ``mj_rnePostConstraint`` fills ``cfrc_int`` -- the joint reaction wrench
    between a body and its parent -- and the load case for "is this thigh
    strong enough" is the worst one of those across a rollout. Nothing new
    is needed from the engine: this is stock MuJoCo on the MJCF
    ``assembly.mjcf`` already exports.
    """

    pytest.importorskip("mujoco")
    module = _module(LOADS)
    model_path, trace_path = _write_trace(tmp_path, steps_per_frame=5,
                                          frames=60, torque=8.0)
    report = module.measure(model_path, trace_path)

    assert report["replay"]["reproduced"], report["replay"]
    assert report["replay"]["worst_position_error_mm"] < module.REPLAY_TOLERANCE_MM
    assert report["warnings"] == []
    assert report["cadex_importable"] in (True, False)

    thigh = report["bodies"]["thigh"]
    assert thigh["internal"]["peak_force_n"] > 0.0
    assert thigh["internal"]["at_peak_force"]["force_n"]
    # The thigh is held at the hip and the shank hangs off it at the knee.
    assert [row["joint"] for row in thigh["held_at"]] == ["hip"]
    assert [row["body"] for row in thigh["children_at"]] == ["shank"]

    fragment = report["load_cases"]["thigh"]
    assert fragment["schema"] == "cadex-analysis-load-case-v1"
    assert fragment["material"] is None, "a strength must be declared, not defaulted"
    assert fragment["supports"][0]["region"]["sphere"]["centre_mm"] == pytest.approx(
        [0.0, 0.0, 500.0])
    assert fragment["loads"][0]["name"].startswith("shank")


def test_the_wrench_at_rest_is_the_weight_it_carries(tmp_path) -> None:
    """The physical check: statics, where the answer is arithmetic.

    Hanging still under gravity with no torque, the reaction at the knee is
    the shank's own weight and the reaction at the hip is both links'. If
    the com-based torque had not been moved onto the body -- MuJoCo reports
    ``cfrc_*`` about the subtree centre of mass, not about the body -- the
    forces would still pass and the moments would be wrong by ``r x F``,
    which on a leg is the whole number.
    """

    mujoco = pytest.importorskip("mujoco")
    module = _module(LOADS)
    model_path, trace_path = _write_trace(tmp_path, steps_per_frame=5,
                                          frames=40, torque=0.0)
    report = module.measure(model_path, trace_path)
    assert report["replay"]["reproduced"]

    model = mujoco.MjModel.from_xml_path(str(model_path))
    shank = float(model.body_mass[
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "shank")])
    thigh = float(model.body_mass[
        mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "thigh")])

    assert report["bodies"]["shank"]["internal"]["peak_force_n"] == pytest.approx(
        shank * 9.81, rel=0.02)
    assert report["bodies"]["thigh"]["internal"]["peak_force_n"] == pytest.approx(
        (shank + thigh) * 9.81, rel=0.02)
    # At rest and hanging vertically the reaction is pure force: the weight
    # acts through the joint axis, so there is no moment about it.
    assert report["bodies"]["shank"]["internal"]["peak_torque_n_mm"] < 1.0


def test_a_subsampled_trace_is_reported_as_a_different_motion(tmp_path) -> None:
    """The check that makes the wrench trustworthy, doing its job.

    A trace sampled at fewer frames a second than the policy acted at holds
    only some of the actions, so a replay of it flies a different
    trajectory. That is not a failure to hide -- it is the reason the
    fidelity number is in the report at all, and the reason the guidance is
    to author the rollout at the control rate when you intend to read loads
    off it.
    """

    pytest.importorskip("mujoco")
    module = _module(LOADS)
    model_path, trace_path = _write_trace(tmp_path, steps_per_frame=1,
                                          frames=80, torque=8.0)
    # Drop every second frame: the same motion, recorded half as often.
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    kept = [trace["frames"][0], trace["frames"][1]]
    kept += [frame for index, frame in enumerate(trace["frames"][2:])
             if index % 2 == 1]
    for position, frame in enumerate(kept):
        frame["frame_index"] = position
    trace["frames"] = kept
    trace["parameters"]["time_step_s"] *= 2
    coarse = tmp_path / "coarse.json"
    coarse.write_text(json.dumps(trace), encoding="utf-8")

    report = module.measure(model_path, coarse)
    assert not report["replay"]["reproduced"]
    assert any("drifted" in text for text in report["warnings"])
