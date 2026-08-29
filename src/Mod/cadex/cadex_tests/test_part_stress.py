# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``part.stress``: a safety factor that follows the shape (ADR-145).

Three halves, and the third one is what makes the number worth having.

The **first** is the API surface, headless: what a stress check refuses, and
that it refuses by naming materials rather than ranges. ``assembly.body``'s
density refusal set that bar and is required by test to name steel and
aluminium; a bound that only says "must be under 1e6" tells an author the
number is wrong and nothing about what a right one looks like.

The **second** drives a real cadexd child. It builds a parametric cantilever,
declares a stress check on it, and asserts the tip deflection against the
closed form engineering already knows. Then it **moves a parameter and
asserts the check moved with it**, which is the entire justification for
putting a stress check in the script rather than running one beside it: a
verdict that did not follow its part would be a decoration.

The **third** is the comparison against ``analysis/cadex_stress.py``.
``analysis/`` may not import the engine and the engine may not import
``analysis/`` -- both test-enforced, ADR-141 and ADR-084 -- so the algorithm
is written twice, and this file solves the same cantilever on the same grid
through both and requires them to agree. That is the ``encode_policy`` /
``cadex_train.py`` arrangement, and it is what makes an in-engine number
worth the same as the verified offboard one.

The client, the spawn and the response validation are
``test_cadexd_lifecycle``'s, so every frame here is checked against the engine
under test's own ``OP_RESPONSE_SPECS`` -- and this file therefore also gates
the ``display.<output>.stress`` record against a packaged payload when
``CADEX_ENGINE_ROOT`` is set.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile

import pytest

from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from cadex_domain_api import create_domain_api

from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

PART_PACK = XSCRIPT_WORKBENCH_PACKS["PartWorkbench"]
ROOT = Path(__file__).resolve().parents[4]
OFFBOARD = ROOT / "analysis" / "cadex_stress.py"

#: The benchmark, and it is the same one ADR-141 verified against a closed
#: form and against CalculiX: 100 x 10 x 10 mm PLA, held at ``x = 0``, 10 N
#: down at the tip. ``length`` is the parameter that moves; the section is
#: fixed, so a rebuild that moved *that* would be a bug this test would see.
CANTILEVER = """
p = params(length=num(100.0, unit="mm", min=40.0, max=200.0, step=5.0))

bar = part.box(p.length, 10.0, 10.0)

check = part.stress(
    bar,
    hold={"geometry_type": "Plane", "normal": [-1, 0, 0], "expected_count": 1},
    load=[{"at": {"geometry_type": "Plane", "normal": [1, 0, 0],
                  "expected_count": 1},
           "force_n": [0.0, 0.0, -10.0]}],
    youngs_modulus_mpa=3500.0, poissons_ratio=0.36,
    yield_strength_mpa=50.0, density_kg_m3=1240.0,
    element_mm=2.5,
)

result = {"bar": bar, "check": check}
"""


def _part():
    return create_domain_api(
        PART_PACK.domain, PART_PACK.api_exports, PART_PACK.output_types
    )


def _box():
    return _part().box(100.0, 10.0, 10.0, label="bar")


def _hold(**extra):
    return {"geometry_type": "Plane", "normal": [-1, 0, 0], "expected_count": 1,
            **extra}


def _load(**extra):
    return {
        "at": {"geometry_type": "Plane", "normal": [1, 0, 0], "expected_count": 1},
        "force_n": [0.0, 0.0, -10.0],
        **extra,
    }


def _material(**extra):
    return {
        "youngs_modulus_mpa": 3500.0,
        "poissons_ratio": 0.36,
        "yield_strength_mpa": 50.0,
        "density_kg_m3": 1240.0,
        "element_mm": 2.5,
        **extra,
    }


# ---------------------------------------------------------------------------
# The API surface, headless.
# ---------------------------------------------------------------------------


def test_a_stress_check_is_a_declared_output_with_no_geometry() -> None:
    """The same species of thing as ``part.measurement`` (ADR-139).

    A declared output that publishes a fact about a shape and no shape of
    its own. Nothing can be built from it, and that is the point.
    """

    value = _part().stress(_box(), hold=_hold(), load=[_load()], **_material())

    assert value.domain == "part"
    assert value.output_type == "stress"
    assert "stress" not in {"solid", "shell", "face", "wire", "compound"}
    # Through `to_payload`, because the properties themselves are frozen
    # into mappingproxies and tuples the moment the value is built.
    properties = value.to_payload()["properties"]
    assert properties["hold"] == [{"at": _hold(), "axes": ["x", "y", "z"]}]
    assert properties["load"][0]["force_n"] == [0.0, 0.0, -10.0]
    assert properties["load"][0]["torque_n_mm"] == [0.0, 0.0, 0.0]
    assert properties["element_mm"] == 2.5

    from cadex_part_api import _PACK_OUTPUT_TYPES, _PUBLISHABLE_TYPES

    assert "stress" in _PACK_OUTPUT_TYPES
    # ...and NOT in the set that validates a caller's `output_type=`:
    # `sew(..., output_type="stress")` is a typo, not a request.
    assert "stress" not in _PUBLISHABLE_TYPES
    assert "stress" in PART_PACK.output_types
    assert "stress" in PART_PACK.api_exports


def test_a_material_property_has_no_default_and_its_refusal_names_materials(
) -> None:
    """``assembly.body``'s ``density_kg_m3`` is the precedent, exactly.

    A guessed stiffness produces a plausible-looking number that is wrong,
    and a safety factor against a strength nobody declared is a number
    pretending to be a verdict. So all five are required -- which is
    asserted here by calling without each of them in turn -- and every bound
    refuses by naming materials, because "must be under 1e6" says the number
    is wrong and nothing about what a right one looks like.
    """

    part = _part()
    for missing in ("youngs_modulus_mpa", "poissons_ratio", "yield_strength_mpa",
                    "density_kg_m3", "element_mm"):
        arguments = _material()
        arguments.pop(missing)
        with pytest.raises(TypeError, match=missing):
            part.stress(_box(), hold=_hold(), load=[_load()], **arguments)

    with pytest.raises(ValueError) as stiff:
        part.stress(_box(), hold=_hold(), load=[_load()],
                    **_material(youngs_modulus_mpa=3.5e9))
    assert "diamond" in str(stiff.value) and "steel 200000" in str(stiff.value)
    assert "MPa, not Pa" in str(stiff.value)

    with pytest.raises(ValueError) as strong:
        part.stress(_box(), hold=_hold(), load=[_load()],
                    **_material(yield_strength_mpa=5.0e7))
    assert "aluminium 6061 275" in str(strong.value)

    with pytest.raises(ValueError) as heavy:
        part.stress(_box(), hold=_hold(), load=[_load()],
                    **_material(density_kg_m3=90000.0))
    assert "steel is 7850" in str(heavy.value)

    with pytest.raises(ValueError) as poisson:
        part.stress(_box(), hold=_hold(), load=[_load()],
                    **_material(poissons_ratio=0.5))
    assert "positive definite" in str(poisson.value)
    assert "rubber" in str(poisson.value)

    with pytest.raises(ValueError) as element:
        part.stress(_box(), hold=_hold(), load=[_load()],
                    **_material(element_mm=5000.0))
    assert "metre across" in str(element.value)


def test_a_load_case_that_cannot_be_applied_is_refused_by_name() -> None:
    part = _part()

    with pytest.raises(ValueError, match="rigid-body modes"):
        part.stress(_box(), hold=[], load=[_load()], **_material())
    with pytest.raises(ValueError, match="load"):
        part.stress(_box(), hold=_hold(), load=[], **_material())
    with pytest.raises(ValueError, match="'at' selector"):
        part.stress(_box(), hold=_hold(), load=[{"force_n": [0, 0, -1]}],
                    **_material())
    # A load that pushes with nothing is a load case that says nothing.
    with pytest.raises(ValueError, match="loads the part with nothing"):
        part.stress(_box(), hold=_hold(),
                    load=[{"at": _hold(), "force_n": [0.0, 0.0, 0.0]}],
                    **_material())
    with pytest.raises(ValueError, match="axes"):
        part.stress(_box(), hold=[{"at": _hold(), "axes": ["w"]}], load=[_load()],
                    **_material())
    with pytest.raises(ValueError, match="returned by this Part api"):
        part.stress("bar", hold=_hold(), load=[_load()], **_material())


def test_the_selector_is_the_shared_one_and_carries_its_cardinality() -> None:
    """ADR-029, unchanged, and the ``expected_count`` is not ceremony here.

    A held face that silently becomes two after an edit changes what the
    part is bolted to, and a load spread over a face that split in half is a
    different load case reported as the same one. The cardinality is what
    makes that fail instead of quietly answering a different question.
    """

    part = _part()
    with pytest.raises(ValueError, match="expected_count"):
        part.stress(_box(), hold={"geometry_type": "Plane", "normal": [-1, 0, 0]},
                    load=[_load()], **_material())
    with pytest.raises(ValueError, match="unrecognised selector keys"):
        part.stress(
            _box(),
            hold=_hold(radius_tolerence=0.1),
            load=[_load()],
            **_material(),
        )
    # Indices are gone everywhere, and here too.
    with pytest.raises(ValueError, match="index lists were removed"):
        part.stress(_box(), hold=_hold(), load=[_load(at=[3, 7])], **_material())
    # A hold entry that is not a selector at all fails the same way.
    with pytest.raises(ValueError, match="non-empty selector mapping"):
        part.stress(_box(), hold=[1, 2], load=[_load()], **_material())


def test_a_check_is_published_as_a_row_with_no_geometry_and_no_artifact(
        tmp_path: Path) -> None:
    """No artifact, so no artifact hash: the declaration is the identity.

    Right for the same reason it is right for a measurement (ADR-139). What
    identifies a stress check is which faces it names and what material it
    declares, not what today's parameters make it read -- and S1's digest
    cache depends on exactly that reading: the same digest means the same
    geometry means the same number.
    """

    import cadex_project_worker as project_worker
    from CadexScriptedDomainPublication import _NATIVE_TYPE_BY_OUTPUT, _native_type

    assert _NATIVE_TYPE_BY_OUTPUT["stress"] == "App::FeaturePython"
    assert _native_type("stress") == "App::FeaturePython"

    value = _part().stress(_box(), hold=_hold(), load=[_load()], **_material())
    item = {
        "name": "check",
        "domain": "part",
        "type": "stress",
        "definition": value.to_payload(),
        "stress": {"safety_factor": 9.4, "p99_von_mises_mpa": 5.3},
    }
    digest = project_worker.compute_project_digest(tmp_path, [item])
    assert isinstance(digest, str) and len(digest) == 64
    moved = dict(item, stress={"safety_factor": 0.2, "p99_von_mises_mpa": 250.0})
    assert project_worker.compute_project_digest(tmp_path, [moved]) == digest
    # ...but a different load *is* a different check.
    other = _part().stress(
        _box(), hold=_hold(),
        load=[_load(force_n=[0.0, 0.0, -20.0])], **_material()
    )
    changed = dict(item, definition=other.to_payload())
    assert project_worker.compute_project_digest(tmp_path, [changed]) != digest


def test_the_display_block_carries_a_stress_check_as_an_optional_key() -> None:
    from CadexdProtocol import NESTED_RESPONSE_SPECS

    required, optional = NESTED_RESPONSE_SPECS["display.*"]
    assert required == frozenset(
        {"artifact_kind", "artifact_path", "placement", "tessellation"}
    )
    assert optional == frozenset(
        {"source_output", "measurement", "mesh_check", "stress", "exploded_view"}
    )


def test_a_stress_check_reaches_inspect_scope_output() -> None:
    """Not optional for a verdict, unlike a dimension the viewport draws.

    ``inspect scope="output"`` reported only keys describing a thing with
    geometry, so an output that *is* a number was readable on the rebuild
    response that produced it and nowhere else (ADR-144, ADR-145).
    """

    from CadexInspection import _OUTPUT_DETAIL_KEYS

    assert "stress" in _OUTPUT_DETAIL_KEYS
    assert "measurement" in _OUTPUT_DETAIL_KEYS


# ---------------------------------------------------------------------------
# The solver, headless: the same benchmark, no kernel.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def offboard():
    pytest.importorskip("scipy", reason="both solvers solve with scipy.sparse")
    spec = importlib.util.spec_from_file_location(OFFBOARD.stem, OFFBOARD)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(OFFBOARD.stem, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def engine():
    pytest.importorskip("scipy", reason="both solvers solve with scipy.sparse")
    import CadexStress

    return CadexStress


def test_the_element_matrix_is_the_same_one_the_offboard_solver_builds(
        engine, offboard) -> None:
    """The condensed C3D8I stiffness, element by element.

    The narrowest comparison there is, and the one that localises a
    disagreement: if the two implementations differ *here*, nothing above it
    is worth comparing.
    """

    import numpy as np

    spacing = np.array([2.5, 2.5, 2.5])
    material = offboard.Material(
        youngs_modulus_mpa=3500.0, poissons_ratio=0.36,
        yield_strength_mpa=50.0, density_kg_m3=1240.0,
    )
    theirs = offboard.build_element(spacing, material)
    d = engine.elasticity_matrix(3500.0, 0.36)
    assert np.allclose(d, material.elasticity_matrix(), rtol=0.0, atol=1e-12)

    mine, recover, corner, internal = engine.build_element(spacing, d)
    assert np.allclose(mine, theirs.stiffness, rtol=1e-12, atol=1e-9)
    assert np.allclose(recover, theirs.recover, rtol=1e-10, atol=1e-10)
    assert np.allclose(corner, theirs.corner_strain, rtol=1e-12, atol=1e-12)
    assert np.allclose(internal, theirs.internal_strain, rtol=1e-12, atol=1e-12)

    # And the element is right in its own terms: symmetric, positive
    # semi-definite, with exactly six rigid-body modes.
    assert np.allclose(mine, mine.T, atol=1e-9)
    eigenvalues = np.linalg.eigvalsh(mine)
    assert int(np.sum(np.abs(eigenvalues) < 1e-6 * np.abs(eigenvalues).max())) == 6


def test_the_two_solvers_agree_on_the_cantilever(engine, offboard) -> None:
    """The claim that makes an in-engine number worth having.

    Identical grid, identical held degrees of freedom, identical assembled
    force vector -- so a disagreement could only be a disagreement about the
    *solve*, not about the load case. ``analysis/`` is the implementation
    ADR-141 verified against a closed form (0.9%), against ``M y / I``, and
    against CalculiX (4.4e-7 relative).
    """

    import numpy as np

    case = offboard.cantilever_case()
    triangles = offboard.box_triangles(case["size_mm"])
    length, width, height = case["size_mm"]

    grid = offboard.voxelise(triangles, 2.5)
    material = offboard.Material.from_mapping(case["load_case"]["material"])
    theirs = offboard.solve(grid, material, case["load_case"])

    # The same two faces, expressed the way the engine gets them: point
    # clouds covering the held and loaded faces of the same box.
    def _face_points(axis, at, count=41):
        u, v = [k for k in range(3) if k != axis]
        extent = [length, width, height]
        a, b = np.meshgrid(
            np.linspace(0.0, extent[u], count),
            np.linspace(0.0, extent[v], count),
            indexing="ij",
        )
        points = np.zeros((a.size, 3), dtype=float)
        points[:, axis] = 0.0 if at == "min" else extent[axis]
        points[:, u] = a.ravel()
        points[:, v] = b.ravel()
        return points

    mine = engine.analyse(
        triangles,
        element_mm=2.5,
        material={
            "youngs_modulus_mpa": material.youngs_modulus_mpa,
            "poissons_ratio": material.poissons_ratio,
            "yield_strength_mpa": material.yield_strength_mpa,
            "density_kg_m3": material.density_kg_m3,
        },
        holds=[{"anchors": _face_points(0, "min"), "axes": (0, 1, 2)}],
        loads=[{"anchors": _face_points(0, "max"),
                "force_n": [0.0, 0.0, -case["force_n"]]}],
    )

    assert mine["grid"]["shape"] == list(theirs.grid.shape)
    assert mine["grid"]["elements"] == len(theirs.element_indices)
    assert mine["solver"]["free_dofs"] == theirs.solver["free_dofs"]
    assert mine["solver"]["held_dofs"] == int(theirs.fixed_dofs.sum())

    assert mine["max_displacement_mm"] == pytest.approx(
        theirs.max_displacement_mm, rel=1e-9
    )
    assert mine["peak_von_mises_mpa"] == pytest.approx(
        theirs.peak_von_mises_mpa, rel=1e-9
    )
    assert mine["p99_von_mises_mpa"] == pytest.approx(
        float(np.percentile(theirs.von_mises_mpa, 99.0)), rel=1e-9
    )

    # ...and both of them are the closed form, which is what the agreement
    # is worth anything for.
    assert mine["max_displacement_mm"] == pytest.approx(
        case["tip_deflection_mm"], rel=0.02
    )


def test_the_verdict_divides_by_p99_and_the_peak_travels_beside_it(
        engine, offboard) -> None:
    """ADR-141 measured that the peak does not converge and must not.

    A clamped face is a genuine stress singularity with no limiting value,
    so it grows with every refinement for ever. An output that published a
    peak safety factor would be lying. Both numbers travel; only one carries
    the verdict, and this is the assertion that says which.
    """

    import numpy as np

    case = offboard.cantilever_case()
    triangles = offboard.box_triangles(case["size_mm"])
    length, width, height = case["size_mm"]
    a, b = np.meshgrid(np.linspace(0, width, 21), np.linspace(0, height, 21),
                       indexing="ij")

    def _end(x):
        points = np.zeros((a.size, 3), dtype=float)
        points[:, 0] = x
        points[:, 1] = a.ravel()
        points[:, 2] = b.ravel()
        return points

    report = engine.analyse(
        triangles,
        element_mm=2.5,
        material={"youngs_modulus_mpa": 3500.0, "poissons_ratio": 0.36,
                  "yield_strength_mpa": 50.0, "density_kg_m3": 1240.0},
        holds=[{"anchors": _end(0.0), "axes": (0, 1, 2)}],
        loads=[{"anchors": _end(length), "force_n": [0.0, 0.0, -10.0]}],
    )
    assert report["peak_von_mises_mpa"] > report["p99_von_mises_mpa"]
    assert report["safety_factor"] == pytest.approx(
        50.0 / report["p99_von_mises_mpa"]
    )
    assert report["safety_factor"] > 50.0 / report["peak_von_mises_mpa"]
    assert "does not converge" in report["note"]
    assert report["mass_g"] == pytest.approx(
        length * width * height * 1240.0 * 1e-6, rel=1e-6
    )


def test_an_element_budget_it_cannot_afford_is_refused_with_the_size_to_use(
        engine, offboard) -> None:
    """Expensive-on-rebuild is not novel; stating the ceiling is.

    ``assembly.simulation`` is already expensive on every rebuild. The
    difference is that this one caps itself and, when it refuses, names the
    ``element_mm`` that would fit rather than leaving an author to bisect.
    """

    triangles = offboard.box_triangles([100.0, 10.0, 10.0])
    with pytest.raises(engine.StressError) as refused:
        engine.analyse(
            triangles,
            element_mm=0.4,
            material={"youngs_modulus_mpa": 3500.0, "poissons_ratio": 0.36,
                      "yield_strength_mpa": 50.0, "density_kg_m3": 1240.0},
            holds=[], loads=[],
            max_elements=1000,
        )
    message = str(refused.value)
    assert "1000" in message and "element_mm of about" in message
    assert refused.value.details["correction"]


def test_a_part_nothing_holds_and_a_part_nothing_loads_are_both_refused(
        engine, offboard) -> None:
    import numpy as np

    triangles = offboard.box_triangles([20.0, 10.0, 10.0])
    material = {"youngs_modulus_mpa": 3500.0, "poissons_ratio": 0.36,
                "yield_strength_mpa": 50.0, "density_kg_m3": 1240.0}
    face = np.array([[0.0, y, z] for y in (0.0, 5.0, 10.0)
                     for z in (0.0, 5.0, 10.0)])
    end = face + np.array([20.0, 0.0, 0.0])

    with pytest.raises(engine.StressError, match="rigid-body modes"):
        engine.analyse(triangles, element_mm=2.5, material=material,
                       holds=[], loads=[{"anchors": end,
                                         "force_n": [0.0, 0.0, -10.0]}])
    with pytest.raises(engine.StressError, match="came to zero"):
        engine.analyse(triangles, element_mm=2.5, material=material,
                       holds=[{"anchors": face, "axes": (0, 1, 2)}], loads=[])


# ---------------------------------------------------------------------------
# The whole thing, against a real engine.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(FREECADCMD is None, reason="no FreeCADCmd binary for cadexd")
def test_a_stress_check_follows_its_part_through_a_parameter_change() -> None:
    """The justification for the whole slice, as one assertion.

    A check that did not move when the part moved would be a decoration. A
    cantilever's tip deflection goes as the cube of its length, so a 100 mm
    bar taken to 150 mm must deflect 3.375 times as far -- which is a number
    nobody can fake by rounding, and which the closed form supplies
    independently of both implementations.
    """

    root = Path(tempfile.mkdtemp(prefix="cadex-stress-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script",
            {"source": CANTILEVER, "expected_revision": "",
             "display": {"quality": "standard"}},
        )
        assert written["ok"] is True, written
        entry = written["display"]["check"]
        # A stress check has no geometry, so every artifact key is empty and
        # the `stress` key is the whole of what it publishes.
        assert entry["artifact_kind"] is None
        assert entry["artifact_path"] is None
        assert entry["tessellation"] is None
        check = entry["stress"]

        # 100 x 10 x 10 mm, PLA, 10 N at the tip. Timoshenko closed form:
        # 1.15218 mm (docs/STRUCTURAL.md 3.3).
        assert check["max_displacement_mm"] == pytest.approx(1.15218, rel=0.03)
        assert check["grid"]["elements"] == 640
        # The whole held face, not four corners of it: 5 x 5 nodes x 3 axes.
        assert check["solver"]["held_dofs"] == 75
        assert check["solver"]["loaded_nodes"] == [25]
        assert check["held_faces"] == [1] and check["loaded_faces"] == [1]
        assert check["safety_factor"] == pytest.approx(
            50.0 / check["p99_von_mises_mpa"]
        )
        assert check["mass_g"] == pytest.approx(12.4, rel=1e-3)
        assert check["warnings"] == []
        assert check["solver"]["relative_residual"] < 1e-6

        # ...and the numbers are the offboard implementation's own, at this
        # grid, to the digits docs/STRUCTURAL.md 3.3 records.
        assert check["max_displacement_mm"] == pytest.approx(1.13916, rel=1e-4)
        assert check["peak_von_mises_mpa"] == pytest.approx(5.3790, rel=1e-3)
        assert check["p99_von_mises_mpa"] == pytest.approx(5.3389, rel=1e-3)

        # Move the parameter. The check has to move with it.
        patched = client.request(
            "set_params",
            {"values": {"length": 150.0}, "expected_revision": written["revision"]},
        )
        assert patched["ok"] is True, patched
        longer = patched["display"]["check"]["stress"]
        assert longer["max_displacement_mm"] == pytest.approx(
            check["max_displacement_mm"] * 1.5 ** 3, rel=0.05
        )
        assert longer["mass_g"] == pytest.approx(check["mass_g"] * 1.5, rel=1e-6)
        assert longer["safety_factor"] < check["safety_factor"], (
            "a longer cantilever carries more bending stress, so it is less "
            "safe; the safety factor did not follow the part"
        )

        # And it is readable an hour later, not only on the response that
        # produced it (ADR-144's gap, closed for both artifact-less kinds).
        detail = client.request(
            "inspect", {"scope": "output", "target": "check"}
        )
        assert detail["ok"] is True, detail
        assert detail["value"]["type"] == "stress"
        assert detail["value"]["stress"]["safety_factor"] == pytest.approx(
            longer["safety_factor"]
        )
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(FREECADCMD is None, reason="no FreeCADCmd binary for cadexd")
def test_a_selector_that_stops_matching_fails_loudly_and_names_itself() -> None:
    """ORGANIC's hazard applies: a contract that cannot be satisfied is worse
    than a missing op.

    A stress check is anchored by selector so that it follows the shape. The
    other half of that bargain is that when a change removes the face it
    held, it says so -- by name -- rather than quietly holding something
    else.
    """

    root = Path(tempfile.mkdtemp(prefix="cadex-stress-refusal-"))
    client = None
    try:
        client = _spawn_cadexd()
        assert client.request(
            "open_project", {"project_root": str(root)}
        )["ok"] is True

        source = CANTILEVER.replace(
            '"geometry_type": "Cylinder"', '"geometry_type": "Cylinder"'
        ).replace(
            'hold={"geometry_type": "Plane", "normal": [-1, 0, 0], '
            '"expected_count": 1}',
            'hold={"geometry_type": "Cylinder", "radius": 4.0, '
            '"expected_count": 1}',
        )
        refused = client.request(
            "write_script",
            {"source": source, "expected_revision": "",
             "display": {"quality": "standard"}},
        )
        assert refused["ok"] is False, refused
        message = str(refused.get("error") or "")
        assert "hold[0].at" in message, message
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)
