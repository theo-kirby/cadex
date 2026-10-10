# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The machine vocabulary on the script surface (ADR-642, ADR-643, ADR-645).

``assembly.coupling`` ties joint coordinates together, ``assembly.tool``
declares a tool point and the work area it must reach -- both arguments to
``assembly.assembly`` and never outputs -- and ``kind='cylinder'`` is a
position actuator whose force range is bore x pressure. The worker's
reading of each is pinned here against the stubbed API.
"""

from __future__ import annotations

import math

import pytest

from cadex_assembly_api import AssemblyDomainAPI
from cadex_assembly_worker import coupling_entries
from cadex_domain_api import _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _gantry(api):
    frame, carriage, motor = (api.component(_source(n)) for n in ("frame", "carriage", "motor"))
    x = api.joint("slider", api.connector(frame), api.connector(carriage),
                  length_limits_mm=[-100, 100])
    a = api.joint("revolute", api.connector(frame), api.connector(motor))
    return frame, carriage, motor, x, a


@pytest.mark.parametrize("name", ["coupling", "tool"])
def test_coupling_and_tool_are_intermediates(name) -> None:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert name in pack.api_exports and name not in pack.output_types
    assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"][name] == name


def test_a_coupling_carries_its_joints_ratios_and_units_into_the_assembly() -> None:
    api = _api()
    frame, carriage, motor, x, a = _gantry(api)
    belt = api.coupling([(x, 1.0), (a, -40.0 / 360.0)], label="belt")
    assert belt.arguments == (x, a)
    assert list(belt.properties["ratios"]) == [1.0, -40.0 / 360.0]
    assert list(belt.properties["motion_types"]) == ["linear", "angular"]
    built = api.assembly([frame, carriage, motor], [x, a], couplings=[belt])
    assert list(built.properties["couplings"]) == [belt]
    assert "couplings" not in api.assembly([frame, carriage, motor], [x, a]).properties
    entries = coupling_entries(built.properties, {id(x): "x", id(a): "a"})
    assert entries == [{"name": "coupling/belt", "terms": [
        {"joint": "x", "motion_type": "linear", "ratio": 1.0},
        {"joint": "a", "motion_type": "angular", "ratio": -40.0 / 360.0}]}]


def test_a_coupling_refuses_what_has_no_coordinate() -> None:
    api = _api()
    frame, carriage, motor, x, a = _gantry(api)
    weld = api.joint("fixed", api.connector(carriage), api.connector(motor))
    with pytest.raises(ValueError, match="fixed joint has no coordinate"):
        api.coupling([(x, 1.0), (weld, 1.0)])
    with pytest.raises(ValueError, match="two or more"):
        api.coupling([(x, 1.0)])
    with pytest.raises(ValueError, match="non-zero"):
        api.coupling([(x, 1.0), (a, 0.0)])
    other = api.joint("revolute", api.connector(frame), api.connector(motor))
    belt = api.coupling([(x, 1.0), (other, 1.0)])
    with pytest.raises(ValueError, match="not listed in joints"):
        api.assembly([frame, carriage, motor], [x, a], couplings=[belt])


def test_a_tool_names_its_point_area_and_frame() -> None:
    api = _api()
    frame, carriage, motor, x, a = _gantry(api)
    nozzle = api.tool(carriage, origin_mm=[0, -35, 20],
                      work_area_mm=[[110, 110, 0], [-110, -110, 0]], work_frame=frame)
    assert nozzle.arguments == (carriage, frame)
    assert [list(c) for c in nozzle.properties["work_area_mm"]] == [[-110, -110, 0], [110, 110, 0]]
    built = api.assembly([frame, carriage, motor], [x, a], tools=[nozzle])
    assert list(built.properties["tools"]) == [nozzle]
    with pytest.raises(ValueError, match="only with work_area_mm"):
        api.tool(carriage, work_frame=frame)


def test_a_cylinder_is_a_position_servo_with_bore_times_pressure() -> None:
    api = _api()
    _frame, _carriage, _motor, x, a = _gantry(api)
    ram = api.actuator(x, kind="cylinder", bore_mm=40, rod_mm=18, pressure_bar=120,
                       control_mm="10*time", stiffness_n_per_mm=2000)
    props = ram.properties
    assert props["kind"] == "position" and props["force_limit_n"] is None
    assert props["cylinder"]["rod_mm"] == 18
    import CadexDynamics as dyn

    extend = 120e5 * math.pi * 0.04 ** 2 / 4
    retract = 120e5 * math.pi * (0.04 ** 2 - 0.018 ** 2) / 4
    assert dyn.cylinder_forces_n(props["cylinder"]) == pytest.approx((-retract, extend))
    plain = api.actuator(x, kind="position", control_mm="0", stiffness_n_per_mm=10)
    assert "cylinder" not in plain.properties
    with pytest.raises(ValueError, match="cylinder drives a slider"):
        api.actuator(a, kind="cylinder", bore_mm=40, pressure_bar=100, control_deg="0",
                     stiffness_nmm_per_deg=1)
    with pytest.raises(ValueError, match="derived"):
        api.actuator(x, kind="cylinder", bore_mm=40, pressure_bar=100, control_mm="0",
                     stiffness_n_per_mm=1, force_limit_n=10)
    with pytest.raises(ValueError, match="only to kind='cylinder'"):
        api.actuator(x, kind="position", bore_mm=40, control_mm="0", stiffness_n_per_mm=1)


# -- path and coverage readings (ADR-645) -------------------------------------------


def test_a_tool_on_its_path_reads_its_error_and_progress() -> None:
    import CadexEvaluation as ev

    path = [[0, 0, 0], [100, 0, 0], [100, 100, 0]]
    points = [[x, 0.5, 0] for x in range(0, 101, 10)] + [[100.4, y, 0] for y in range(0, 51, 10)]
    read = ev.path_metrics(points, path)
    assert read["max_path_error_mm"] == pytest.approx(0.5)
    assert read["path_progress"] == pytest.approx(150.0 / 200.0)


def test_a_mower_that_mows_stripes_covers_what_its_blade_swept() -> None:
    import CadexEvaluation as ev

    square = [[0, 0], [100, 0], [100, 100], [0, 100]]
    stripes = []
    for row, y in enumerate((12.5, 37.5, 62.5, 87.5)):
        xs = (0, 100) if row % 2 == 0 else (100, 0)
        stripes += [[xs[0], y, 0], [xs[1], y, 0]]
    full = ev.coverage_metrics(stripes, square, footprint_mm=26.0, cell_mm=2.0)
    assert full["coverage"] == pytest.approx(1.0)
    half = ev.coverage_metrics(stripes[:4], square, footprint_mm=25.0, cell_mm=2.0)
    assert half["coverage"] == pytest.approx(0.5, abs=0.03)
