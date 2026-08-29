# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Collision geometry, and what it refuses (docs/MUJOCO.md M3, phase 1).

Hazard 2, in one sentence: **MuJoCo takes the convex hull of every
collision mesh and does not say so.** A bracket with a slot becomes a solid
block, the mechanism still runs, the contacts still look like contacts, and
nothing anywhere reports a problem. It is the loudest failure in this arc
that arrives completely silent.

We have the BREP, so the answer is to measure rather than hope. That turned
out to be *two* measurements, not one, and the second is a correction to
the plan found by working out what a tessellated cylinder does:

**Concavity** is the hull's volume against the mesh's own volume. Both come
from the same vertices, so for a genuinely convex part they agree to
floating-point noise and any gap is real concavity. Comparing the hull
against the *exact* BREP volume -- which is what the plan said -- would
have charged every cylinder in the tree for its faceting: at the default
deflection a 5 mm pin is short of its exact volume by 1.6% before any
concavity exists at all.

**Fidelity** is that faceting, measured on purpose and separately: the
mesh's volume against the exact ``GProp_GProps`` volume. It answers a
different question -- is this still the part -- and it is *not* waived by
the hull opt-in, because an author who accepted the hull of their bracket
has not thereby accepted an eight-sided cylinder.

A concave part is refused, naming the component and the volume error, the
way M2 refused ``rack_pinion`` rather than shipping a guessed sign
convention. ``hull`` is the opt-in that turns the refusal into a recorded
acceptance, and it is a *kind* rather than a boolean so it appears in the
script's own text.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import tempfile

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
from cadex_assembly_api import AssemblyDomainAPI
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

mujoco = pytest.importorskip("mujoco")


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _pendulum_with(collision: dict | None, *, on: str = "arm"):
    """The M2 pendulum, with one body given something to touch with."""

    components, joints, placements = fx.pendulum()
    for component in components:
        if component["name"] == on and collision is not None:
            component["collision"] = collision
    return components, joints, placements


# ---------------------------------------------------------------------------
# The script surface.
# ---------------------------------------------------------------------------


def test_collision_is_exported_and_is_not_publishable() -> None:
    """An argument to a body, like ``connector`` is to ``joint``."""

    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "collision" in pack.api_exports
    assert "collision" not in pack.output_types
    value = _api().collision("sphere", radius_mm=5.0)
    assert value.output_type == "collision"
    assert value.operation == "collision"


@pytest.mark.parametrize(
    "kind, parameters",
    [
        ("box", {"size_mm": [10.0, 20.0, 30.0]}),
        ("plane", {"size_mm": [1200.0, 1200.0, 50.0]}),
        ("sphere", {"radius_mm": 4.0}),
        ("cylinder", {"radius_mm": 4.0, "length_mm": 25.0}),
        ("capsule", {"radius_mm": 4.0, "length_mm": 25.0}),
        ("mesh", {}),
        ("hull", {"deflection_mm": 0.05}),
    ],
)
def test_every_kind_accepts_exactly_its_own_parameters(kind, parameters) -> None:
    value = _api().collision(kind, **parameters)
    assert value.properties["kind"] == kind


@pytest.mark.parametrize(
    "kind, parameters, unwanted",
    [
        ("box", {"size_mm": [1.0, 1.0, 1.0]}, {"radius_mm": 2.0}),
        ("sphere", {"radius_mm": 2.0}, {"length_mm": 5.0}),
        ("mesh", {}, {"size_mm": [1.0, 1.0, 1.0]}),
        ("capsule", {"radius_mm": 2.0, "length_mm": 5.0}, {"deflection_mm": 0.1}),
    ],
)
def test_a_parameter_that_belongs_to_another_kind_is_refused(
    kind, parameters, unwanted
) -> None:
    """A silently ignored parameter is a script that does not do what it says."""

    with pytest.raises(ValueError, match="not a .* parameter"):
        _api().collision(kind, **parameters, **unwanted)


def test_a_missing_required_parameter_is_refused() -> None:
    with pytest.raises(ValueError, match="size_mm"):
        _api().collision("box")
    with pytest.raises(ValueError, match="radius_mm"):
        _api().collision("cylinder", length_mm=10.0)
    with pytest.raises(ValueError, match="length_mm"):
        _api().collision("cylinder", radius_mm=10.0)


def test_an_unknown_kind_names_the_ones_that_exist() -> None:
    with pytest.raises(ValueError, match="box"):
        _api().collision("convex_decomposition")


def test_a_mesh_cannot_be_offset_from_the_part_it_came_from() -> None:
    """It is already in the component's frame; moving it moves the physics."""

    with pytest.raises(ValueError, match="does not apply"):
        _api().collision("mesh", offset=[10.0, 0.0, 0.0])
    # A primitive is a different matter: placing it is the whole point.
    placed = _api().collision("box", size_mm=[10.0, 10.0, 10.0], offset=[5.0, 0.0, 0.0])
    assert list(placed.properties["offset"]["position"]) == [5.0, 0.0, 0.0]


def test_a_body_collides_with_nothing_unless_it_says_otherwise() -> None:
    """The default is the M2 behaviour, and it is deliberate.

    The alternative default would be to infer a collision shape from the
    part, which is the one thing this whole surface exists to prevent.
    """

    api = _api()
    component = api.component(_source("solid0"), grounded=True)
    assert list(api.body(component, density_kg_m3=fx.STEEL).properties["collision"]) == []


def test_a_body_takes_one_shape_or_a_list_of_them() -> None:
    api = _api()
    component = api.component(_source("solid0"))
    single = api.body(
        component,
        density_kg_m3=fx.STEEL,
        collision=api.collision("sphere", radius_mm=3.0),
    )
    assert len(single.properties["collision"]) == 1
    several = api.body(
        component,
        density_kg_m3=fx.STEEL,
        collision=[
            api.collision("box", size_mm=[10.0, 10.0, 10.0]),
            api.collision("box", size_mm=[10.0, 10.0, 10.0], offset=[20.0, 0.0, 0.0]),
        ],
    )
    assert len(several.properties["collision"]) == 2


def test_one_body_cannot_have_two_meshes() -> None:
    """They are both the whole component, so the second is the first twice."""

    api = _api()
    component = api.component(_source("solid0"))
    with pytest.raises(ValueError, match="at most one mesh or hull"):
        api.body(
            component,
            density_kg_m3=fx.STEEL,
            collision=[api.collision("mesh"), api.collision("hull")],
        )


# ---------------------------------------------------------------------------
# The two measurements.
# ---------------------------------------------------------------------------


def test_mesh_volume_reads_a_closed_outward_wound_mesh() -> None:
    mesh = fx.box_mesh(100.0, 40.0, 20.0)
    assert dyn.mesh_volume_mm3(mesh["vertices_mm"], mesh["triangles"]) == pytest.approx(
        80_000.0, rel=1e-12
    )
    bracket = fx.l_bracket_mesh()
    assert dyn.mesh_volume_mm3(
        bracket["vertices_mm"], bracket["triangles"]
    ) == pytest.approx(fx.l_bracket_volume_mm3(), rel=1e-12)


def test_an_inverted_winding_reads_negative_rather_than_plausible() -> None:
    """The failure mode that would otherwise pass every other check."""

    mesh = fx.box_mesh(100.0, 40.0, 20.0)
    flipped = list(mesh["triangles"])
    for index in range(0, len(flipped), 3):
        flipped[index + 1], flipped[index + 2] = flipped[index + 2], flipped[index + 1]
    assert dyn.mesh_volume_mm3(mesh["vertices_mm"], flipped) == pytest.approx(-80_000.0)


def test_a_convex_part_has_a_hull_the_size_of_itself() -> None:
    mesh = fx.box_mesh(100.0, 40.0, 20.0)
    hull = dyn.convex_hull_volume_mm3(mesh["vertices_mm"], context="box")
    volume = dyn.mesh_volume_mm3(mesh["vertices_mm"], mesh["triangles"])
    assert (hull - volume) / hull < dyn.COLLISION_CONVEXITY_TOLERANCE


def test_the_l_brackets_hull_is_forty_percent_bigger_than_the_bracket() -> None:
    """The hazard, as a number. 2000 mm² of outline, 2800 mm² of hull."""

    bracket = fx.l_bracket_mesh()
    hull = dyn.convex_hull_volume_mm3(bracket["vertices_mm"], context="bracket")
    volume = dyn.mesh_volume_mm3(bracket["vertices_mm"], bracket["triangles"])
    assert hull == pytest.approx(28_000.0, rel=1e-9)
    assert volume == pytest.approx(20_000.0, rel=1e-9)
    assert (hull - volume) / hull == pytest.approx(2.0 / 7.0, rel=1e-9)


def test_a_concave_body_is_refused_and_the_refusal_carries_the_volume_error() -> None:
    bracket = fx.l_bracket_mesh()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.collision_geoms(
            [fx.collision_shape("mesh", deflection_mm=0.25)],
            bracket,
            exact_volume_mm3=fx.l_bracket_volume_mm3(),
            context="component 'bracket'",
        )
    error = excinfo.value
    assert error.reason == "collision_mesh_concave"
    assert "bracket" in str(error)
    assert error.observed["concavity"] == pytest.approx(2.0 / 7.0, rel=1e-9)
    assert error.observed["hull_volume_mm3"] == pytest.approx(28_000.0, rel=1e-9)
    # The refusal names both ways out, and neither is inferred.
    assert "assembly.collision('box'" in error.correction
    assert "assembly.collision('hull')" in error.correction


def test_the_hull_opt_in_accepts_the_same_part_and_records_that_it_did() -> None:
    bracket = fx.l_bracket_mesh()
    records = dyn.collision_geoms(
        [fx.collision_shape("hull", deflection_mm=0.25)],
        bracket,
        exact_volume_mm3=fx.l_bracket_volume_mm3(),
        context="component 'bracket'",
    )
    assert len(records) == 1
    assert records[0]["accepted_hull"] is True
    assert records[0]["concavity"] == pytest.approx(2.0 / 7.0, rel=1e-9)
    assert records[0]["hull_volume_mm3"] == pytest.approx(28_000.0, rel=1e-9)


def test_a_cylinder_faceted_by_tessellation_is_not_called_concave() -> None:
    """The correction to the plan, stated as the test that found it.

    An inscribed 44-gon prism is convex. Measured against its own hull it is
    convex to 1e-15; measured against the exact circle it is 0.34% short.
    Comparing hull-to-exact -- which is what the plan said -- would have
    reported concavity for every round part in every assembly.
    """

    mesh = fx.faceted_cylinder_mesh(10.0, 30.0, 44)
    exact = math.pi * 100.0 * 30.0
    volume = dyn.mesh_volume_mm3(mesh["vertices_mm"], mesh["triangles"])
    hull = dyn.convex_hull_volume_mm3(mesh["vertices_mm"], context="pin")
    assert (hull - volume) / hull < 1.0e-12
    assert (exact - volume) / exact == pytest.approx(0.0034, abs=5.0e-4)
    records = dyn.collision_geoms(
        [fx.collision_shape("mesh", deflection_mm=0.25)],
        mesh,
        exact_volume_mm3=exact,
        context="component 'pin'",
    )
    assert records[0]["concavity"] < dyn.COLLISION_CONVEXITY_TOLERANCE


def test_a_mesh_too_coarse_to_be_the_part_is_refused_by_volume() -> None:
    """Eight sides is 10% of the pin missing, and its contacts would be flat."""

    mesh = fx.faceted_cylinder_mesh(10.0, 30.0, 8, deflection_mm=3.0)
    exact = math.pi * 100.0 * 30.0
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.collision_geoms(
            [fx.collision_shape("mesh", deflection_mm=3.0)],
            mesh,
            exact_volume_mm3=exact,
            context="component 'pin'",
        )
    assert excinfo.value.reason == "collision_mesh_too_coarse"
    assert excinfo.value.observed["volume_error"] == pytest.approx(0.0997, abs=1e-3)
    assert "deflection_mm" in excinfo.value.correction


def test_accepting_the_hull_does_not_also_accept_an_eight_sided_cylinder() -> None:
    """Two measurements, two questions; the opt-in only answers one of them."""

    mesh = fx.faceted_cylinder_mesh(10.0, 30.0, 8, deflection_mm=3.0)
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.collision_geoms(
            [fx.collision_shape("hull", deflection_mm=3.0)],
            mesh,
            exact_volume_mm3=math.pi * 100.0 * 30.0,
            context="component 'pin'",
        )
    assert excinfo.value.reason == "collision_mesh_too_coarse"


# ---------------------------------------------------------------------------
# The units boundary, which M2 built and M3 must not leak a second copy of.
# ---------------------------------------------------------------------------


def test_a_box_becomes_half_extents_in_metres() -> None:
    """The factor of two and the factor of a thousand, in one place."""

    records = dyn.collision_geoms(
        [fx.collision_shape("box", size_mm=[100.0, 40.0, 20.0])],
        None,
        exact_volume_mm3=80_000.0,
        context="component 'block'",
    )
    assert records[0]["size_m"] == pytest.approx([0.05, 0.02, 0.01])
    assert records[0]["size_mm"] == [100.0, 40.0, 20.0]


def test_a_planes_three_numbers_are_not_three_extents() -> None:
    """Two half-widths and a grid spacing, which is why it has its own branch.

    A plane is the one primitive whose ``size_mm`` is not a size in all
    three places: MuJoCo reads it as ``(x_half, y_half, grid)``, and the
    grid is what the viewer rules the surface with rather than a thickness,
    because a plane has none. The widths are halved exactly as a box's
    extents are so that ``1200`` means 1200 mm of floor either way; the grid
    is converted and never halved.
    """

    records = dyn.collision_geoms(
        [fx.collision_shape("plane", size_mm=[1200.0, 800.0, 50.0])],
        None,
        exact_volume_mm3=1.0,
        context="component 'ground'",
    )
    assert records[0]["size_m"] == pytest.approx([0.6, 0.4, 0.05])
    assert records[0]["size_mm"] == [1200.0, 800.0, 50.0]


def test_a_plane_with_no_edge_is_the_usual_floor() -> None:
    """Zero is a legal width meaning infinite, and only here.

    Every other primitive refuses a zero size, because a box 0 mm thick is
    a mistake. A plane 0 mm wide is a plane with no edge at all, which is
    what a ground plane usually wants -- so the two checks cannot be shared,
    and this is the case that says so.
    """

    records = dyn.collision_geoms(
        [fx.collision_shape("plane", size_mm=[0.0, 0.0, 50.0])],
        None,
        exact_volume_mm3=1.0,
        context="component 'ground'",
    )
    assert records[0]["size_m"] == pytest.approx([0.0, 0.0, 0.05])
    # ...and the API agrees, rather than refusing what the engine accepts.
    assert list(
        _api().collision("plane", size_mm=[0.0, 0.0, 50.0]).properties["size_mm"]
    ) == [0.0, 0.0, 50.0]


@pytest.mark.parametrize(
    "size, message",
    [
        ([-1.0, 0.0, 50.0], "cannot be negative"),
        ([1200.0, 1200.0, 0.0], "grid SPACING"),
    ],
)
def test_a_malformed_plane_is_refused_on_the_number_that_is_wrong(
    size, message: str
) -> None:
    """A negative width, and a third number read as a thickness.

    The second is the one this message exists for: ``[1200, 1200, 40]``
    looks exactly like the box floor it replaces, and a reader who has not
    been told will write the thickness there and get a 40 mm grid instead of
    a 40 mm slab. Refusing zero is what forces the question to be asked.
    """

    with pytest.raises(ValueError, match=message):
        _api().collision("plane", size_mm=size)


def test_a_plane_compiles_and_only_a_static_body_may_carry_one() -> None:
    """MuJoCo's own refusal, pinned rather than duplicated.

    A plane on a moving body is meaningless -- an infinite half-space with
    momentum -- and MuJoCo says so by name, naming the geom. A second check
    here would be a second opinion about a question that already has a good
    answer; what this pins is that the answer keeps arriving.
    """

    components, joints, _placements = _pendulum_with(
        {
            "shapes": [fx.collision_shape("plane", size_mm=[1200.0, 1200.0, 50.0])],
            "mesh": None,
        },
        on="base",
    )
    model = dyn.build_model(components, joints)["model"]
    assert int(model.geom_type[0]) == int(mujoco.mjtGeom.mjGEOM_PLANE)
    # The surface is the component's own origin facing local +Z, where a
    # box's colliding surface is its top face -- which is the whole reason a
    # plane floor drops the offset a box floor needs (ADR-074).
    assert model.geom_pos[0] == pytest.approx([0.0, 0.0, 0.0])

    moving, joints, _placements = _pendulum_with(
        {
            "shapes": [fx.collision_shape("plane", size_mm=[100.0, 100.0, 10.0])],
            "mesh": None,
        }
    )
    with pytest.raises(dyn.DynamicsError, match="static bodies"):
        dyn.build_model(moving, joints)


def test_a_sphere_keeps_its_radius_and_a_cylinder_halves_its_length() -> None:
    records = dyn.collision_geoms(
        [
            fx.collision_shape("sphere", radius_mm=8.0),
            fx.collision_shape("cylinder", radius_mm=5.0, length_mm=30.0),
            fx.collision_shape("capsule", radius_mm=5.0, length_mm=30.0),
        ],
        None,
        exact_volume_mm3=1.0,
        context="component 'parts'",
    )
    assert records[0]["size_m"] == pytest.approx([0.008])
    assert records[1]["size_m"] == pytest.approx([0.005, 0.015])
    # A capsule's half-length is of the cylindrical section only: the caps
    # sit outside it, so this one is 40 mm long overall, not 30.
    assert records[2]["size_m"] == pytest.approx([0.005, 0.015])


def test_an_offset_converts_position_to_metres_and_rotation_to_wxyz() -> None:
    """The script surface speaks xyzw because FreeCAD does; MuJoCo does not."""

    half = math.sqrt(0.5)
    records = dyn.collision_geoms(
        [
            fx.collision_shape(
                "sphere",
                radius_mm=2.0,
                offset={"position": (30.0, -10.0, 5.0), "rotation": (half, 0.0, 0.0, half)},
            )
        ],
        None,
        exact_volume_mm3=1.0,
        context="component 'ball'",
    )
    assert records[0]["pos_m"] == pytest.approx([0.03, -0.01, 0.005])
    assert records[0]["quat_wxyz"] == pytest.approx([half, half, 0.0, 0.0])


def test_the_mesh_crosses_the_seam_in_millimetres_and_is_stored_in_metres() -> None:
    mesh = fx.box_mesh(100.0, 40.0, 20.0)
    records = dyn.collision_geoms(
        [fx.collision_shape("mesh", deflection_mm=0.25)],
        mesh,
        exact_volume_mm3=80_000.0,
        context="component 'block'",
    )
    assert max(records[0]["vertices_m"]) == pytest.approx(0.05)
    assert records[0]["mesh_volume_mm3"] == pytest.approx(80_000.0)


# ---------------------------------------------------------------------------
# The declared deflection.
# ---------------------------------------------------------------------------


def test_the_deflection_is_declared_and_never_inherited_from_the_display() -> None:
    """A fixed length, not a fraction of the bounding box.

    ``cadex_tessellation`` scales its deflection by the diagonal because it
    is choosing how a part looks. A collision mesh built that way would
    collide differently at draft quality than at fine, which is a physics
    result depending on a view setting.
    """

    import cadex_tessellation

    assert dyn.DEFAULT_COLLISION_DEFLECTION_MM == 0.25
    small = cadex_tessellation.resolve_deflection({}, 10.0)
    large = cadex_tessellation.resolve_deflection({}, 1000.0)
    assert small != large, "the display deflection scales; ours must not"

    shapes = [fx.collision_shape("mesh", deflection_mm=None)]
    assert dyn.collision_deflection_mm(shapes, context="c") == 0.25
    declared = [fx.collision_shape("hull", deflection_mm=0.05)]
    assert dyn.collision_deflection_mm(declared, context="c") == 0.05


def test_a_body_of_primitives_never_asks_for_a_tessellation() -> None:
    """Which is what keeps an explicit-primitive body free of BREP cost."""

    shapes = [
        fx.collision_shape("box", size_mm=[10.0, 10.0, 10.0]),
        fx.collision_shape("sphere", radius_mm=5.0),
    ]
    assert dyn.collision_deflection_mm(shapes, context="c") is None


# ---------------------------------------------------------------------------
# The compiled model.
# ---------------------------------------------------------------------------


def _geom_count(model, name: str) -> int:
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
    return int(model.body_geomnum[body_id])


def test_geoms_are_counted_per_body_rather_than_globally() -> None:
    """M2 asserted ``ngeom == 0``; M3's version has to be finer than that.

    One body opts into contact, the other does not, and the model has to
    show exactly that -- a global count cannot tell "collision works" from
    "collision landed on the wrong part".
    """

    components, joints, _placements = _pendulum_with(
        {
            "shapes": [
                fx.collision_shape("box", size_mm=[300.0, 40.0, 20.0]),
                fx.collision_shape(
                    "sphere", radius_mm=10.0, offset={"position": (150.0, 0.0, 0.0)}
                ),
            ],
            "mesh": None,
        }
    )
    model = dyn.build_model(components, joints)["model"]
    assert _geom_count(model, "arm") == 2
    assert _geom_count(model, "base") == 0
    assert model.ngeom == 2


def test_a_model_with_no_collision_at_all_still_has_no_geoms() -> None:
    """M2's assertion, kept: the default did not change underneath anyone."""

    model = dyn.build_model(*fx.four_bar()[:2])["model"]
    assert model.ngeom == 0


def test_each_kind_compiles_to_the_mujoco_type_it_names() -> None:
    components, joints, _placements = _pendulum_with(
        {
            "shapes": [
                fx.collision_shape("box", size_mm=[10.0, 10.0, 10.0]),
                fx.collision_shape("sphere", radius_mm=5.0),
                fx.collision_shape("cylinder", radius_mm=5.0, length_mm=20.0),
                fx.collision_shape("capsule", radius_mm=5.0, length_mm=20.0),
            ],
            "mesh": None,
        }
    )
    model = dyn.build_model(components, joints)["model"]
    assert [int(value) for value in model.geom_type] == [
        int(mujoco.mjtGeom.mjGEOM_BOX),
        int(mujoco.mjtGeom.mjGEOM_SPHERE),
        int(mujoco.mjtGeom.mjGEOM_CYLINDER),
        int(mujoco.mjtGeom.mjGEOM_CAPSULE),
    ]
    assert model.geom_size[0] == pytest.approx([0.005, 0.005, 0.005])
    assert model.geom_size[2][1] == pytest.approx(0.01)


def test_a_mesh_geom_reaches_the_compiler_as_a_mesh() -> None:
    components, joints, _placements = _pendulum_with(
        {"shapes": [fx.collision_shape("mesh")], "mesh": fx.box_mesh(300.0, 40.0, 20.0)}
    )
    built = dyn.build_model(components, joints)
    model = built["model"]
    assert model.nmesh == 1
    assert int(model.geom_type[0]) == int(mujoco.mjtGeom.mjGEOM_MESH)
    # MuJoCo hulls it, which for a box is the box: eight vertices.
    assert int(model.mesh_vertnum[0]) == 8


def test_a_geom_does_not_change_the_exact_inertia_it_hangs_on() -> None:
    """The differentiator, re-checked with geometry present.

    ``inertiafromgeom`` is off and the inertia is explicit, so a geom must
    decide what touches what and nothing else. This is the assertion that
    survives a MuJoCo release deciding a geom implies mass.
    """

    without = dyn.build_model(*fx.pendulum()[:2])["model"]
    components, joints, _placements = _pendulum_with(
        {"shapes": [fx.collision_shape("box", size_mm=[300.0, 40.0, 20.0])], "mesh": None}
    )
    with_geom = dyn.build_model(components, joints)["model"]
    assert list(with_geom.body_mass) == list(without.body_mass)
    for row, reference in zip(with_geom.body_inertia, without.body_inertia, strict=True):
        assert list(row) == list(reference)


def test_a_concave_component_is_refused_by_build_model_naming_the_component() -> None:
    """The refusal reaches the author through the model build, not just the
    helper -- which is where a script would actually meet it."""

    components, joints, _placements = fx.pendulum()
    for component in components:
        if component["name"] == "arm":
            component["collision"] = {
                "shapes": [fx.collision_shape("mesh")],
                "mesh": fx.l_bracket_mesh(),
            }
            component["inertial"] = fx.box_inertial(60.0, 60.0, 10.0)
            # The exact volume the check compares against is the solid's,
            # and the L encloses less than its bounding box.
            component["inertial"]["volume_mm3"] = fx.l_bracket_volume_mm3()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "collision_mesh_concave"
    assert "'arm'" in str(excinfo.value)


def test_the_evidence_records_what_each_body_collides_with() -> None:
    components, joints, _placements = _pendulum_with(
        {
            "shapes": [fx.collision_shape("box", size_mm=[300.0, 40.0, 20.0])],
            "mesh": None,
        }
    )
    built = dyn.build_model(components, joints)
    evidence = dyn.model_evidence(built, components)
    assert [entry["component_output"] for entry in evidence["collisions"]] == ["arm"]
    shape = evidence["collisions"][0]["shapes"][0]
    assert shape["kind"] == "box"
    assert list(shape["size_mm"]) == [300.0, 40.0, 20.0]
    # The geometry itself is in the model; the evidence carries decisions.
    assert "vertices_m" not in shape


def test_the_evidence_keeps_the_three_volumes_that_allowed_a_mesh() -> None:
    components, joints, _placements = _pendulum_with(
        {"shapes": [fx.collision_shape("hull")], "mesh": fx.box_mesh(300.0, 40.0, 20.0)}
    )
    built = dyn.build_model(components, joints)
    shape = dyn.model_evidence(built, components)["collisions"][0]["shapes"][0]
    assert shape["mesh_volume_mm3"] == pytest.approx(240_000.0)
    assert shape["hull_volume_mm3"] == pytest.approx(240_000.0)
    assert shape["solid_volume_mm3"] == pytest.approx(240_000.0)
    assert shape["accepted_hull"] is True
    assert shape["deflection_mm"] == dyn.DEFAULT_COLLISION_DEFLECTION_MM


# ---------------------------------------------------------------------------
# The seam itself, through a running engine.
# ---------------------------------------------------------------------------
#
# Everything above this line runs on fixtures, which means it proves the
# arithmetic and proves nothing about the read that feeds it. The worker
# half -- tessellating the component's own solids at a declared deflection
# and handing millimetres across -- only exists in a process with a kernel
# in it, and ADR-023's rule generalises: a passing pure module proves
# nothing about the code that fills its arguments.

_LIVE = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)

#: A cylinder dropped on a plate. Convex, curved, and therefore the case
#: that would have been refused had concavity been measured against the
#: exact volume the way the plan first said.
CONVEX_SCRIPT = """
plate = part.box(200, 200, 10)
pin = part.cylinder(20, 60)
ground = assembly.component(plate, grounded=True)
drop = assembly.component(pin, placement=[100, 100, 150])
asm = assembly.assembly([ground, drop], [])
diag = assembly.solve(asm)
sim = assembly.dynamics(asm, [
    assembly.body(ground, density_kg_m3=7850,
                  collision=assembly.collision("box", size_mm=[200, 200, 10],
                                               offset=[100, 100, 5])),
    assembly.body(drop, density_kg_m3=2700,
                  collision=assembly.collision("KIND")),
], end_time_s=0.5, frames_per_second=30)
result = {"plate": plate, "pin": pin, "ground": ground, "drop": drop,
          "asm": asm, "diag": diag, "sim": sim}
"""

#: The hazard as real BREP: a 60x60x10 plate with a 40x40 corner cut out.
#: Exactly the L the fixtures model, built by ``part.cut`` instead of by
#: hand, so the numbers the refusal reports can be checked against a
#: closed form that no code under test produced.
CONCAVE_SCRIPT = """
plate = part.box(200, 200, 10)
big = part.box(60, 60, 10)
notch = part.box(40, 40, 30, origin=[20, 20, -10])
bracket = part.cut(big, notch)
ground = assembly.component(plate, grounded=True)
drop = assembly.component(bracket, placement=[80, 80, 150])
asm = assembly.assembly([ground, drop], [])
diag = assembly.solve(asm)
sim = assembly.dynamics(asm, [
    assembly.body(ground, density_kg_m3=7850,
                  collision=assembly.collision("box", size_mm=[200, 200, 10],
                                               offset=[100, 100, 5])),
    assembly.body(drop, density_kg_m3=2700,
                  collision=assembly.collision("KIND")),
], end_time_s=0.5, frames_per_second=30)
result = {"plate": plate, "big": big, "notch": notch, "bracket": bracket,
          "ground": ground, "drop": drop, "asm": asm, "diag": diag, "sim": sim}
"""


def _live_dynamics(source: str) -> dict:
    """One dynamics script through a cadexd of its own; the raw response."""

    root = Path(tempfile.mkdtemp(prefix="m3-collision-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        written = client.request(
            "write_script", {"source": source, "expected_revision": ""}
        )
        if written["ok"] is True:
            entry = written["display"]["sim"]
            written = dict(written)
            written["trace"] = json.loads(
                Path(entry["artifact_path"]).read_text(encoding="utf-8")
            )
        return written
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


@_LIVE
def test_a_real_curved_part_tessellates_to_a_convex_mesh_geom() -> None:
    """A cylinder, off a real kernel, measured on both axes.

    Its hull matches its own mesh to 1e-15 -- it is convex -- while its mesh
    is 0.04% short of the exact ``GProp_GProps`` volume, which is faceting
    and nothing else. Two numbers, two questions, and only the second one
    moves when the deflection does.
    """

    response = _live_dynamics(CONVEX_SCRIPT.replace("KIND", "mesh"))
    assert response["ok"] is True, response
    shapes = {
        entry["component_output"]: entry["shapes"]
        for entry in response["trace"]["dynamics"]["collisions"]
    }
    mesh = shapes["drop"][0]
    assert mesh["kind"] == "mesh"
    assert mesh["deflection_mm"] == dyn.DEFAULT_COLLISION_DEFLECTION_MM
    assert abs(mesh["concavity"]) < 1.0e-12
    assert 0.0 < mesh["volume_error"] < dyn.COLLISION_TESSELLATION_TOLERANCE
    assert mesh["solid_volume_mm3"] == pytest.approx(
        math.pi * 400.0 * 60.0, rel=1.0e-6
    )
    # And it lands on the plate rather than through it: the plate's top is
    # at z = 10 and the pin's own frame is at its base.
    heights = [
        frame["component_placements"]["drop"]["position_mm"][2]
        for frame in response["trace"]["frames"]
    ]
    assert heights[1] == pytest.approx(150.0)
    assert 9.0 < heights[-1] < 10.1


@_LIVE
def test_a_real_concave_part_is_refused_with_the_numbers_in_it() -> None:
    """The bracket, cut by OCCT, refused with a closed-form volume error.

    20 000 mm³ of bracket inside a 28 000 mm³ hull: the missing 8 000 is
    the 40x40x10 notch minus the corner the hull cuts back off. Nothing in
    the code under test produced either number.
    """

    response = _live_dynamics(CONCAVE_SCRIPT.replace("KIND", "mesh"))
    assert response["ok"] is False
    text = json.dumps(response)
    assert "collision_mesh_concave" in text
    assert "28000" in text and "20000" in text
    assert "assembly.collision('hull')" in text


@_LIVE
def test_the_same_bracket_is_accepted_when_the_script_says_hull() -> None:
    """The opt-in is a word in the script, and the model records it."""

    response = _live_dynamics(CONCAVE_SCRIPT.replace("KIND", "hull"))
    assert response["ok"] is True, response
    shapes = {
        entry["component_output"]: entry["shapes"]
        for entry in response["trace"]["dynamics"]["collisions"]
    }
    mesh = shapes["drop"][0]
    assert mesh["kind"] == "hull"
    assert mesh["accepted_hull"] is True
    assert mesh["mesh_volume_mm3"] == pytest.approx(20_000.0, rel=1.0e-9)
    assert mesh["hull_volume_mm3"] == pytest.approx(28_000.0, rel=1.0e-9)
    assert mesh["concavity"] == pytest.approx(2.0 / 7.0, rel=1.0e-9)
