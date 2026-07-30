# SPDX-License-Identifier: LGPL-2.1-or-later

"""Measure OCCT's mass-property convention (docs/MUJOCO.md M2, phase 2).

Runs under FreeCADCmd:

    FreeCADCmd -c "import sys; sys.path.insert(0, '<cadex_tests>'); \\
        sys.path.insert(0, '<cadex>'); \\
        import dynamics_inertia_integration as m; raise SystemExit(m.main())"

Exact inertia is slice M2's differentiator, and every closed-form assertion
in ``test_dynamics_inertia`` is written against *readings* -- dicts the
worker claims OCCT produces. This is the one place that claim is checked
against the kernel, because a suite that stubs FreeCAD cannot notice that
``MatrixOfInertia`` means something other than what the code assumed.

It measured one thing the plan had wrong. docs/MUJOCO.md M2 says
``Solid.MatrixOfInertia`` is taken **about the origin**; under this build it
is taken **about the centre of mass**. Had ``_solid_inertia_readings``
subtracted the parallel-axis term as originally designed, every part
modelled away from the origin would have come out with a *negative*
tensor -- which MuJoCo refuses, so that one would have been loud. The quiet
version is the reverse mistake, and it is why this file exists.

The reading is taken from a copy translated to the origin, which is correct
under either convention, and this asserts both: that the translated reading
matches the closed form, and which convention the untranslated one follows.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

MODULE_ROOT = Path(__file__).resolve().parent.parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

import CadexDynamics as dyn  # noqa: E402
from cadex_assembly_worker import (  # noqa: E402
    AssemblyCandidateError,
    _matrix_of_inertia_rows,
    _solid_inertia_readings,
)

STEEL = 7850.0
RELATIVE = 1.0e-9


def _close(first: float, second: float, tolerance: float = RELATIVE) -> bool:
    scale = max(abs(first), abs(second), 1.0e-30)
    return abs(first - second) <= tolerance * scale


def _box_closed_form(length: float, width: float, height: float) -> list[float]:
    volume = length * width * height
    return [
        volume * (width * width + height * height) / 12.0,
        volume * (length * length + height * height) / 12.0,
        volume * (length * length + width * width) / 12.0,
    ]


def main() -> int:
    import FreeCAD as App
    import Part

    report: dict[str, object] = {}
    length, width, height = 200.0, 100.0, 40.0
    centre = App.Vector(300.0, -150.0, 25.0)

    box = Part.makeBox(length, width, height)
    box.translate(centre - App.Vector(length / 2.0, width / 2.0, height / 2.0))
    readings = _solid_inertia_readings(box, context="component 'plate'")
    assert len(readings) == 1, readings
    reading = readings[0]

    # 1. The reading is what test_dynamics_inertia's fixtures claim it is.
    volume = length * width * height
    assert _close(reading["volume_mm3"], volume), reading
    for axis, expected in enumerate((centre.x, centre.y, centre.z)):
        assert _close(reading["center_of_mass_mm"][axis], expected), reading
    closed = _box_closed_form(length, width, height)
    tensor = reading["inertia_mm5_about_com"]
    for axis in range(3):
        assert _close(tensor[axis * 4], closed[axis]), (tensor, closed)
    for index in (1, 2, 3, 5, 6, 7):
        assert abs(tensor[index]) <= 1.0e-6 * closed[0], tensor

    # 2. Which convention does the untranslated read follow? Measured, not
    #    assumed -- and recorded, because M3 may want to skip the copy.
    raw = _matrix_of_inertia_rows(box.Solids[0].MatrixOfInertia)
    distance_squared = centre.x**2 + centre.y**2 + centre.z**2
    about_origin = [
        closed[0] + volume * (distance_squared - centre.x**2),
        closed[1] + volume * (distance_squared - centre.y**2),
        closed[2] + volume * (distance_squared - centre.z**2),
    ]
    matches_com = all(_close(raw[axis * 4], closed[axis]) for axis in range(3))
    matches_origin = all(_close(raw[axis * 4], about_origin[axis]) for axis in range(3))
    assert matches_com != matches_origin, (raw, closed, about_origin)
    report["matrix_of_inertia_reference_point"] = (
        "center_of_mass" if matches_com else "origin"
    )
    report["origin_term_ratio"] = about_origin[1] / closed[1]

    # 3. Unit density: OCCT's "mass" is the volume, so the tensor is mm⁵ and
    #    ρ·J·1e-15 is the whole conversion. The check is that the tensor
    #    scales with the volume and not with anything else.
    assert _close(tensor[0] / volume, closed[0] / volume), tensor

    # 4. End to end: readings -> body_inertial -> kg·m² against closed form.
    inertial = dyn.body_inertial(readings, STEEL, context="body 'plate'")
    mass = STEEL * volume * 1.0e-9
    assert _close(inertial["mass_kg"], mass), inertial
    for axis in range(3):
        assert _close(
            inertial["inertia_kg_m2"][axis * 4], STEEL * closed[axis] * 1.0e-15
        ), inertial
    report["mass_kg"] = inertial["mass_kg"]
    report["inertia_kg_m2_diagonal"] = [
        inertial["inertia_kg_m2"][index] for index in (0, 4, 8)
    ]

    # 5. A cylinder, whose closed form is the one a box cannot check: the
    #    axial moment is m·r²/2 and the transverse one mixes both lengths.
    radius, cylinder_height = 25.0, 120.0
    cylinder = Part.makeCylinder(radius, cylinder_height)
    cylinder_readings = _solid_inertia_readings(cylinder, context="component 'shaft'")
    cylinder_inertial = dyn.body_inertial(
        cylinder_readings, 2700.0, context="body 'shaft'"
    )
    cylinder_volume = 3.141592653589793 * radius * radius * cylinder_height
    cylinder_mass = 2700.0 * cylinder_volume * 1.0e-9
    assert _close(cylinder_inertial["mass_kg"], cylinder_mass, 1.0e-6), (
        cylinder_inertial
    )
    assert _close(
        cylinder_inertial["inertia_kg_m2"][8],
        cylinder_mass * (radius / 1000.0) ** 2 / 2.0,
        1.0e-6,
    ), cylinder_inertial
    assert _close(
        cylinder_inertial["inertia_kg_m2"][0],
        cylinder_mass
        * (3.0 * (radius / 1000.0) ** 2 + (cylinder_height / 1000.0) ** 2)
        / 12.0,
        1.0e-6,
    ), cylinder_inertial
    assert _close(
        cylinder_inertial["center_of_mass_mm"][2], cylinder_height / 2.0, 1.0e-9
    ), cylinder_inertial

    # 6. A two-solid component is summed about the common centre of mass.
    first = Part.makeBox(20.0, 20.0, 20.0)
    first.translate(App.Vector(-60.0, -10.0, -10.0))
    second = Part.makeBox(20.0, 20.0, 20.0)
    second.translate(App.Vector(40.0, -10.0, -10.0))
    compound = Part.makeCompound([first, second])
    pair = _solid_inertia_readings(compound, context="component 'dumbbell'")
    assert len(pair) == 2, pair
    dumbbell = dyn.body_inertial(pair, STEEL, context="body 'dumbbell'")
    cube_mass = STEEL * 0.02**3
    assert _close(dumbbell["mass_kg"], 2.0 * cube_mass), dumbbell
    for axis in range(3):
        assert abs(dumbbell["center_of_mass_mm"][axis]) <= 1.0e-9, dumbbell
    cube_inertia = cube_mass * (0.02**2 + 0.02**2) / 12.0
    assert _close(dumbbell["inertia_kg_m2"][0], 2.0 * cube_inertia, 1.0e-6), dumbbell
    assert _close(
        dumbbell["inertia_kg_m2"][4],
        2.0 * (cube_inertia + cube_mass * 0.05**2),
        1.0e-6,
    ), dumbbell
    report["dumbbell_center_of_mass_mm"] = dumbbell["center_of_mass_mm"]

    # 7. A sheet-metal plate clears the triangle inequality by its thickness
    #    and is not refused (hazard 8), with the real kernel's rounding.
    sheet = Part.makeBox(200.0, 100.0, 0.5)
    plate = dyn.body_inertial(
        _solid_inertia_readings(sheet, context="component 'sheet'"),
        STEEL,
        context="body 'sheet'",
    )
    principal = plate["principal_inertia_kg_m2"]
    residual = principal[0] + principal[1] - principal[2]
    assert residual > 0.0, principal
    report["sheet_triangle_margin_relative"] = residual / principal[2]

    # 8. A shape with no solid is refused rather than silently massless.
    try:
        _solid_inertia_readings(
            Part.makePolygon(
                [App.Vector(0, 0, 0), App.Vector(10, 0, 0), App.Vector(10, 10, 0)]
            ),
            context="component 'outline'",
        )
    except AssemblyCandidateError as error:
        report["no_solid_refusal"] = str(error)
    else:  # pragma: no cover - the refusal is the assertion
        raise AssertionError("a wire has no mass and must be refused")

    report["ok"] = True
    print(json.dumps(report, indent=2, sort_keys=True))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
