# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Exact inertia, asserted against closed forms (docs/MUJOCO.md M2, phase 2).

Standard MJCF authoring guesses inertia from convex hulls or hand-tunes it.
We have the BREP, so ``<inertial>`` can be exact -- and being exact is this
slice's whole differentiator, which makes it the thing most worth proving.

The two hazards this file exists for:

* **The parallel-axis error is silent and passes MuJoCo's validation**
  (hazard 2). For a 200x100x40 mm box centred at (300, 0, 0), taking the
  tensor about the origin instead of about the centre of mass gives a
  result roughly a hundred times too large on two axes -- and it still
  satisfies the triangle inequality, so it compiles, simulates, and looks
  like a heavy part. Only a closed-form assertion catches it.
* **Thin plates sit on the triangle inequality** (hazard 8). In the
  continuum limit Ixx + Iyy = Izz exactly, so a comparison against zero
  margin lands either side of the boundary by one ulp. A real plate clears
  it by its own thickness squared, and that is what is asserted.

The readings this drives are the shape ``cadex_assembly_worker.
_solid_inertia_readings`` produces; ``dynamics_inertia_integration.py``
measures OCCT's actual convention under FreeCADCmd rather than assuming it.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn


STEEL = 7850.0


def _box_reading(
    length: float,
    width: float,
    height: float,
    centre=(0.0, 0.0, 0.0),
) -> dict:
    """A solid box, as OCCT would report it: volume, COM, COM-tensor in mm⁵."""

    volume = length * width * height
    return {
        "volume_mm3": volume,
        "center_of_mass_mm": list(centre),
        "inertia_mm5_about_com": [
            volume * (width * width + height * height) / 12.0, 0.0, 0.0,
            0.0, volume * (length * length + height * height) / 12.0, 0.0,
            0.0, 0.0, volume * (length * length + width * width) / 12.0,
        ],
    }


def test_a_steel_box_matches_the_closed_form() -> None:
    result = dyn.body_inertial([_box_reading(200.0, 100.0, 40.0)], STEEL, context="body")
    mass = STEEL * 0.2 * 0.1 * 0.04
    assert result["mass_kg"] == pytest.approx(mass, rel=1.0e-12)
    assert result["inertia_kg_m2"][0] == pytest.approx(
        mass * (0.1**2 + 0.04**2) / 12.0, rel=1.0e-12
    )
    assert result["inertia_kg_m2"][4] == pytest.approx(
        mass * (0.2**2 + 0.04**2) / 12.0, rel=1.0e-12
    )
    assert result["inertia_kg_m2"][8] == pytest.approx(
        mass * (0.2**2 + 0.1**2) / 12.0, rel=1.0e-12
    )
    assert result["inertia_kg_m2"][1] == 0.0


def test_the_tensor_of_an_offset_body_stays_about_its_own_centre() -> None:
    """Hazard 2, stated as a number: 100x too large on two axes, silently."""

    here = dyn.body_inertial([_box_reading(200.0, 100.0, 40.0)], STEEL, context="body")
    there = dyn.body_inertial(
        [_box_reading(200.0, 100.0, 40.0, centre=(300.0, 0.0, 0.0))],
        STEEL,
        context="body",
    )
    assert there["inertia_kg_m2"] == pytest.approx(here["inertia_kg_m2"], rel=1.0e-12)
    assert there["center_of_mass_mm"] == [300.0, 0.0, 0.0]

    # What the missing shift would have produced, and why it is not caught
    # by any structural check: it is a perfectly valid-looking tensor.
    mass = there["mass_kg"]
    unshifted_yy = there["inertia_kg_m2"][4] + mass * 0.3**2
    # 27x on y and 23x on z, measured -- the plan estimated ~100x, which is
    # the right order and the wrong number. Either way it is the kind of
    # error that shows up as "the arm feels heavy", not as a failure.
    assert unshifted_yy / there["inertia_kg_m2"][4] == pytest.approx(27.0, abs=0.5)
    principal = sorted([there["inertia_kg_m2"][0], unshifted_yy, unshifted_yy])
    assert principal[0] + principal[1] > principal[2]


def test_two_solids_are_summed_about_their_common_centre() -> None:
    """A dumbbell: two 20 mm cubes 100 mm apart on x, plus nothing else."""

    side = 20.0
    readings = [
        _box_reading(side, side, side, centre=(-50.0, 0.0, 0.0)),
        _box_reading(side, side, side, centre=(50.0, 0.0, 0.0)),
    ]
    result = dyn.body_inertial(readings, STEEL, context="body")
    cube_mass = STEEL * (side / 1000.0) ** 3
    assert result["mass_kg"] == pytest.approx(2.0 * cube_mass, rel=1.0e-12)
    assert result["center_of_mass_mm"] == pytest.approx([0.0, 0.0, 0.0], abs=1.0e-12)
    cube_inertia = cube_mass * (0.02**2 + 0.02**2) / 12.0
    # About x the offset contributes nothing; about y and z it contributes
    # m·d² per cube.
    assert result["inertia_kg_m2"][0] == pytest.approx(2.0 * cube_inertia, rel=1.0e-12)
    assert result["inertia_kg_m2"][4] == pytest.approx(
        2.0 * (cube_inertia + cube_mass * 0.05**2), rel=1.0e-12
    )
    assert result["inertia_kg_m2"][8] == pytest.approx(
        2.0 * (cube_inertia + cube_mass * 0.05**2), rel=1.0e-12
    )
    assert result["solid_count"] == 2


def test_a_cylinder_matches_the_closed_form() -> None:
    radius, height = 25.0, 120.0
    volume = math.pi * radius * radius * height
    axial = volume * radius * radius / 2.0
    transverse = volume * (3.0 * radius * radius + height * height) / 12.0
    reading = {
        "volume_mm3": volume,
        "center_of_mass_mm": [0.0, 0.0, 0.0],
        "inertia_mm5_about_com": [
            transverse, 0.0, 0.0,
            0.0, transverse, 0.0,
            0.0, 0.0, axial,
        ],
    }
    result = dyn.body_inertial([reading], 2700.0, context="body")
    mass = 2700.0 * volume * 1.0e-9
    assert result["mass_kg"] == pytest.approx(mass, rel=1.0e-12)
    assert result["inertia_kg_m2"][8] == pytest.approx(
        mass * 0.025**2 / 2.0, rel=1.0e-12
    )
    assert result["inertia_kg_m2"][0] == pytest.approx(
        mass * (3.0 * 0.025**2 + 0.12**2) / 12.0, rel=1.0e-12
    )


def test_an_off_origin_sphere_is_a_sphere_wherever_it_sits() -> None:
    radius = 30.0
    volume = 4.0 / 3.0 * math.pi * radius**3
    moment = 2.0 / 5.0 * volume * radius * radius
    reading = {
        "volume_mm3": volume,
        "center_of_mass_mm": [400.0, -250.0, 90.0],
        "inertia_mm5_about_com": [
            moment, 0.0, 0.0,
            0.0, moment, 0.0,
            0.0, 0.0, moment,
        ],
    }
    result = dyn.body_inertial([reading], STEEL, context="body")
    mass = STEEL * volume * 1.0e-9
    for axis in (0, 4, 8):
        assert result["inertia_kg_m2"][axis] == pytest.approx(
            2.0 / 5.0 * mass * 0.03**2, rel=1.0e-12
        )
    assert result["center_of_mass_mm"] == [400.0, -250.0, 90.0]


def test_a_thin_plate_clears_the_triangle_inequality_by_its_thickness() -> None:
    """Sheet metal is a legitimate shape, so it may not be refused."""

    length, width, thickness = 200.0, 100.0, 0.5
    result = dyn.body_inertial(
        [_box_reading(length, width, thickness)], STEEL, context="body"
    )
    principal = result["principal_inertia_kg_m2"]
    residual = principal[0] + principal[1] - principal[2]
    assert residual > 0.0
    # The margin is the thickness squared, not a rounding artefact -- and it
    # is small enough (2e-5 here) that a check written with a naive absolute
    # tolerance would refuse a perfectly ordinary plate.
    expected = result["mass_kg"] * 2.0 * (thickness / 1000.0) ** 2 / 12.0
    assert residual == pytest.approx(expected, rel=1.0e-9)
    assert residual / principal[2] < 1.0e-4


def test_a_tensor_no_rigid_body_could_have_is_refused_here_not_by_mujoco() -> None:
    reading = {
        "volume_mm3": 1000.0,
        "center_of_mass_mm": [0.0, 0.0, 0.0],
        "inertia_mm5_about_com": [
            1.0e6, 0.0, 0.0,
            0.0, 1.0e6, 0.0,
            0.0, 0.0, 5.0e6,
        ],
    }
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.body_inertial([reading], STEEL, context="body 'plate'")
    assert excinfo.value.reason == "inertia_triangle_violation"
    assert "plate" in str(excinfo.value)


def test_a_component_with_no_solid_is_refused() -> None:
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.body_inertial([], STEEL, context="body 'sketch'")
    assert excinfo.value.reason == "no_solid"


def test_a_zero_volume_solid_is_refused() -> None:
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.body_inertial(
            [_box_reading(0.0, 100.0, 40.0)], STEEL, context="body 'blade'"
        )
    assert excinfo.value.reason == "degenerate_solid"


def test_principal_moments_come_out_of_a_rotated_tensor() -> None:
    """The eigenvalue routine, against a tensor rotated by a known frame."""

    diagonal = [3.0, 7.0, 11.0]
    quaternion = dyn.quaternion_from_axis_angle_wxyz((0.3, -0.7, 0.9), 1.234)
    rotation = dyn.matrix_rotation(dyn.matrix_from_quaternion_wxyz(quaternion))
    rotated = [
        sum(
            rotation[row * 3 + index] * diagonal[index] * rotation[column * 3 + index]
            for index in range(3)
        )
        for row in range(3)
        for column in range(3)
    ]
    assert dyn._symmetric_eigenvalues(rotated) == pytest.approx(diagonal, rel=1.0e-12)


def test_the_products_of_inertia_survive_into_mujoco_order() -> None:
    """MJCF fullinertia is (Ixx, Iyy, Izz, Ixy, Ixz, Iyz)."""

    tensor = [1.0, 0.4, 0.5, 0.4, 2.0, 0.6, 0.5, 0.6, 3.0]
    assert dyn.full_inertia_six(tensor) == [1.0, 2.0, 3.0, 0.4, 0.5, 0.6]


def test_a_rotated_body_keeps_its_products_of_inertia() -> None:
    """A solid whose principal axes are not the component axes.

    Everything else in this file is diagonal, and a transposed or dropped
    product-of-inertia term would survive all of it.
    """

    quaternion = dyn.quaternion_from_axis_angle_wxyz((0.0, 0.0, 1.0), math.radians(30.0))
    rotation = dyn.matrix_rotation(dyn.matrix_from_quaternion_wxyz(quaternion))
    box = _box_reading(200.0, 100.0, 40.0)
    principal = [box["inertia_mm5_about_com"][index] for index in (0, 4, 8)]
    box["inertia_mm5_about_com"] = [
        sum(
            rotation[row * 3 + index] * principal[index] * rotation[column * 3 + index]
            for index in range(3)
        )
        for row in range(3)
        for column in range(3)
    ]
    result = dyn.body_inertial([box], STEEL, context="body")
    assert result["inertia_kg_m2"][1] != 0.0
    assert result["principal_inertia_kg_m2"] == pytest.approx(
        sorted(dyn.inertia_kg_m2(STEEL, principal)), rel=1.0e-9
    )
    six = dyn.full_inertia_six(result["inertia_kg_m2"])
    assert six[3] == pytest.approx(result["inertia_kg_m2"][1], rel=1.0e-15)
