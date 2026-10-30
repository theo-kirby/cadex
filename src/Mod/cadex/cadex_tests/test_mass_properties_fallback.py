# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-950: non-physical BREP mass properties fall back to a closed mesh.

OCCT can integrate a solid that ``isValid()`` accepts to a negative principal
moment. The contract pinned here: such a reading is recognised, a closed
tessellation of the solid stands in for it with a warning naming the body,
and an open tessellation is refused rather than trusted. The worker's
FreeCAD half only reads ``TopoShape.tessellate``; everything below is the
pure half it calls.

Run: ``pixi run test-engine`` (or ``pixi run python -m pytest
src/Mod/cadex/cadex_tests/test_mass_properties_fallback.py``).
"""

from __future__ import annotations

import pytest

import CadexDynamics as dyn

PA12 = 1010.0


def _box_mesh(length: float, width: float, height: float) -> tuple[list[float], list[int]]:
    """A box centred on the origin, eight shared vertices, outward winding."""

    hx, hy, hz = length / 2.0, width / 2.0, height / 2.0
    vertices: list[float] = []
    for x in (-hx, hx):
        for y in (-hy, hy):
            for z in (-hz, hz):
                vertices.extend((x, y, z))
    # Vertex index = 4·ix + 2·iy + iz.
    quads = [
        (0, 1, 3, 2),  # -x
        (4, 6, 7, 5),  # +x
        (0, 4, 5, 1),  # -y
        (2, 3, 7, 6),  # +y
        (0, 2, 6, 4),  # -z
        (1, 5, 7, 3),  # +z
    ]
    triangles: list[int] = []
    for a, b, c, d in quads:
        triangles.extend((a, b, c, a, c, d))
    return vertices, triangles


def _box_tensor(length: float, width: float, height: float) -> list[float]:
    volume = length * width * height
    return [
        volume * (width**2 + height**2) / 12.0, 0.0, 0.0,
        0.0, volume * (length**2 + height**2) / 12.0, 0.0,
        0.0, 0.0, volume * (length**2 + width**2) / 12.0,
    ]


def _degenerate_reading() -> dict:
    """What OCCT returned for leon VI's ``pnl_neck_side_l``, in shape:
    a positive volume short of the enclosed one, and a negative moment."""

    return {
        "volume_mm3": 2129.6,
        "center_of_mass_mm": [10.0, -20.0, 30.0],
        "inertia_mm5_about_com": [
            4.0e5, 0.0, 0.0,
            0.0, 3.0e5, 0.0,
            0.0, 0.0, -5.9e4,
        ],
    }


def test_a_closed_mesh_measures_a_box_exactly() -> None:
    vertices, triangles = _box_mesh(40.0, 20.0, 10.0)
    assert dyn.mesh_open_edge_count(triangles) == 0
    measured = dyn.mesh_mass_properties(vertices, triangles)
    assert measured["volume_mm3"] == pytest.approx(8000.0, rel=1e-12)
    assert measured["center_of_mass_mm"] == pytest.approx([0.0, 0.0, 0.0], abs=1e-9)
    assert measured["inertia_mm5_about_com"] == pytest.approx(
        _box_tensor(40.0, 20.0, 10.0), rel=1e-12, abs=1e-6
    )


def test_a_non_physical_reading_is_named_and_a_physical_one_is_not() -> None:
    assert "principal moment" in dyn.inertia_reading_defect(_degenerate_reading())
    physical = {
        "volume_mm3": 8000.0,
        "center_of_mass_mm": [0.0, 0.0, 0.0],
        "inertia_mm5_about_com": _box_tensor(40.0, 20.0, 10.0),
    }
    assert dyn.inertia_reading_defect(physical) is None
    with pytest.raises(dyn.DynamicsError) as refused:
        dyn.body_inertial([_degenerate_reading()], PA12, context="body 'panel'")
    assert refused.value.reason == "degenerate_inertia"


def test_the_tessellation_stands_in_for_the_degenerate_solid_with_a_warning() -> None:
    brep = _degenerate_reading()
    vertices, triangles = _box_mesh(40.0, 20.0, 10.0)
    reading = dyn.tessellated_solid_reading(
        brep,
        vertices,
        triangles,
        origin_mm=brep["center_of_mass_mm"],
        deflection_mm=dyn.MASS_TESSELLATION_DEFLECTION_MM,
        defect=dyn.inertia_reading_defect(brep),
        context="body 'c_panel'",
        solid_index=0,
    )
    inertial = dyn.body_inertial([reading], PA12, context="body 'c_panel'")
    assert inertial["mass_kg"] == pytest.approx(PA12 * 8000.0e-9, rel=1e-12)
    assert inertial["center_of_mass_mm"] == pytest.approx([10.0, -20.0, 30.0])
    assert inertial["principal_inertia_kg_m2"] == pytest.approx(
        sorted(PA12 * item * 1e-15 for item in _box_tensor(40.0, 20.0, 10.0)[::4]),
        rel=1e-12,
    )
    assert inertial["mass_properties_source"] == "tessellation"
    (warning,) = inertial["mass_properties_warnings"]
    assert "body 'c_panel'" in warning and "ADR-950" in warning
    assert "2129.6" in warning and "8000" in warning


def test_an_untouched_body_reads_brep_and_carries_no_warning() -> None:
    reading = {
        "volume_mm3": 8000.0,
        "center_of_mass_mm": [0.0, 0.0, 0.0],
        "inertia_mm5_about_com": _box_tensor(40.0, 20.0, 10.0),
    }
    inertial = dyn.body_inertial([reading], PA12, context="body 'c_frame'")
    assert inertial["mass_properties_source"] == "brep"
    assert inertial["mass_properties_warnings"] == []


def test_an_open_tessellation_is_refused_not_trusted() -> None:
    brep = _degenerate_reading()
    vertices, triangles = _box_mesh(40.0, 20.0, 10.0)
    open_triangles = triangles[:-3]
    assert dyn.mesh_open_edge_count(open_triangles) == 3
    with pytest.raises(dyn.DynamicsError) as refused:
        dyn.tessellated_solid_reading(
            brep,
            vertices,
            open_triangles,
            origin_mm=brep["center_of_mass_mm"],
            deflection_mm=dyn.MASS_TESSELLATION_DEFLECTION_MM,
            defect=dyn.inertia_reading_defect(brep),
            context="body 'c_panel'",
            solid_index=0,
        )
    assert refused.value.reason == "degenerate_inertia"
    assert refused.value.observed["mesh_defect"].startswith("3 open")
