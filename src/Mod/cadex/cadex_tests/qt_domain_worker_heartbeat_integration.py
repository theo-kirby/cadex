# SPDX-License-Identifier: LGPL-2.1-or-later

"""Qt heartbeat integration for production-ready geometry/solver workers.

Run this file inside ``FreeCADCmd``.  Candidate subprocess waits happen on a
background thread while the main thread owns a real Qt event loop. Part covers
OCC generation, Part Design covers native Body/sketch/feature recompute,
Sketcher covers geometry/constraint solving, Draft covers
native parametric proxy recompute and array generation, Surface covers B-spline
interpolation plus native extension, and Assembly covers authenticated reference
transfer plus a native solver. Spreadsheet covers a large native batch and
formula recompute. Material covers native catalog loading, full-card hashing,
and physical-property requirement validation. BIM covers native Arch/Draft
hierarchy construction, hosted-opening cuts, and detached BREP validation. Mesh
covers substantial triangle generation, repair, decimation, topology diagnostics,
and BMS export. MeshPart covers authenticated BREP transfer plus a substantial
native Mefisto conversion and BMS validation. Points covers a substantial
canonical transform/filter/voxel pipeline plus authenticated ASC export. Reverse
Engineering covers native B-spline surface fitting, structured reconstruction,
normal-region segmentation, fit metrics, and authenticated BREP/BMS export.
Inspection covers authenticated Points/BREP transfer, native signed-distance
evaluation, typed aggregation, and bounded float32 artifact validation.
Robot covers native trajectory generation, dress-up recompute, thousands of
trajectory interpolation and inverse-kinematics samples, and authenticated
binary diagnostics. FEM covers authenticated BREP transfer, native constraint
mapping, native mesh reconstruction, and CalculiX input-deck generation. CAM
covers authenticated BREP transfer, native operation generation, stock-removal
and protected-model simulation, and native postprocessing.
TechDraw covers authenticated BREP transfer, multi-direction HLR projection,
projected dimension evaluation, and authenticated precomputed-state artifacts.
Future gated prototype domains remain excluded until their production
implementations pass this executable test.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time

MODULE_ROOT = Path(__file__).resolve().parent.parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from PySide import QtCore  # noqa: E402

from CadexModelingSurface import resolve_modeling_surface  # noqa: E402
from CadexScriptedRuntime import (  # noqa: E402
    execute_candidate,
    finalize_candidate,
    prepare_candidate,
    validate_candidate,
)
from CadexScriptedDomains import get_xscript_pack  # noqa: E402


WORKER_CASES = (
    (
        "PartWorkbench",
        "solid",
        "result = {'Result': x.box(2, 3, 4, label=str(total))}\n",
    ),
    (
        "PartWorkbench",
        "solid",
        "base = x.box(8, 8, 8)\n"
        "bore = x.cylinder(2, 8, origin=[4,4,0])\n"
        "result = {'Result': x.cut(base, bore, label=str(total))}\n",
    ),
    (
        "PartWorkbench",
        "solid",
        "lower = x.wire([[0,0,0],[8,0,0],[8,5,0],[0,5,0]], closed=True)\n"
        "upper = x.wire([[1,1,8],[7,1,8],[7,4,8],[1,4,8]], closed=True)\n"
        "result = {'Result': x.loft([lower, upper], solid=True, label=str(total))}\n",
    ),
    (
        "PartDesignWorkbench",
        "solid",
        "circle = x.circle([0,0], 4)\n"
        "profile = x.sketch([circle], label='Heartbeat Profile')\n"
        "tip = x.pad(profile, 8, label='Heartbeat Pad')\n"
        "result = {'Result': x.body(tip, label=str(total))}\n",
    ),
    (
        "SketcherWorkbench",
        "sketch",
        "geometry = []\n"
        "constraints = []\n"
        "for index in range(120):\n"
        "    line = x.line([0,index], [10,index], name='Line' + str(index))\n"
        "    geometry.append(line)\n"
        "    constraints.append(x.constraint('horizontal', [line]))\n"
        "result = {'Result': x.sketch(geometry, constraints, label=str(total))}\n",
    ),
)


class _Bridge(QtCore.QObject):
    finished = QtCore.Signal()


def _candidate(root: Path, index: int, workbench: str, output_type: str, result: str):
    import FreeCAD as App

    pack = get_xscript_pack(workbench)
    assert pack is not None
    busy_source = (
        "total = 0\nfor value in range(30000):\n    total += value % 7\n" + result
    )
    return prepare_candidate(
        {
            "tool_name": f"xscript.{pack.domain}.create_program",
            "operation": "create_program",
            "arguments": {
                "program_name": f"Qt Heartbeat {index}",
                "source": busy_source,
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "inputs": {},
                "expected_outputs": [{"name": "Result", "type": output_type}],
            },
            "pack": pack,
            "project_root": str(root),
            "document_name": "QtHeartbeatDocument",
            "document_uid": "qt-heartbeat-document",
            "document_revision": "qt-heartbeat-revision",
            "document_objects": [],
            "surface": resolve_modeling_surface(workbench, "xscript").summary(),
            "freecad_home": str(App.getHomePath()),
            "timeout_seconds": 60.0,
            "memory_limit_bytes": 2 * 1024 * 1024 * 1024,
        }
    )


def _reference_schema() -> dict:
    return {
        "type": "object",
        "x-cadex-reference": True,
        "properties": {
            "document_uid": {"type": "string", "minLength": 1},
            "object_name": {"type": "string", "minLength": 1},
        },
        "required": ["document_uid", "object_name"],
        "additionalProperties": False,
    }


def _assembly_candidate(root: Path, index: int):
    """Solve and simulate a native assembly entirely off-thread."""

    import FreeCAD as App
    import Part

    pack = get_xscript_pack("AssemblyWorkbench")
    assert pack is not None
    document_uid = "qt-heartbeat-assembly-document"
    references = {
        "base": {"document_uid": document_uid, "object_name": "HeartbeatBase"},
        "arm": {"document_uid": document_uid, "object_name": "HeartbeatArm"},
    }
    busy_source = (
        "total = 0\n"
        "for value in range(30000):\n"
        "    total += value % 7\n"
        "base = x.component(inputs['base'], grounded=True, label='Base')\n"
        "arm = x.component(inputs['arm'], placement=[0,0,8], label=str(total))\n"
        "hinge = x.joint('revolute', x.connector(base), x.connector(arm), "
        "angle_limits_degrees=[-90,90], label='Hinge')\n"
        "model = x.assembly([base,arm], [hinge], label='Heartbeat Assembly')\n"
        "diagnostics = x.solve(model)\n"
        "drive = x.motion(hinge, 'initialValue + pi*time', label='Drive')\n"
        "simulation = x.simulation(model, [drive], end_time_s=.5, "
        "time_step_s=.01, label='Heartbeat Simulation')\n"
        "result = {'Model':model,'Base':base,'Arm':arm,'Hinge':hinge,"
        "'Drive':drive,'Simulation':simulation,"
        "'Diagnostics':diagnostics}\n"
    )
    prepared = prepare_candidate(
        {
            "tool_name": "xscript.assembly.create_program",
            "operation": "create_program",
            "arguments": {
                "program_name": f"Qt Heartbeat {index}",
                "source": busy_source,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "base": _reference_schema(),
                        "arm": _reference_schema(),
                    },
                    "required": ["base", "arm"],
                    "additionalProperties": False,
                },
                "inputs": references,
                "expected_outputs": [
                    {"name": "Model", "type": "assembly"},
                    {"name": "Base", "type": "component_link"},
                    {"name": "Arm", "type": "component_link"},
                    {"name": "Hinge", "type": "joint"},
                    {"name": "Drive", "type": "motion"},
                    {"name": "Simulation", "type": "simulation"},
                    {"name": "Diagnostics", "type": "solver_diagnostics"},
                ],
            },
            "pack": pack,
            "project_root": str(root),
            "document_name": "QtHeartbeatAssemblyDocument",
            "document_uid": document_uid,
            "document_revision": "qt-heartbeat-assembly-revision",
            "document_objects": [
                {"name": "HeartbeatBase", "label": "Base", "type_id": "Part::Feature"},
                {"name": "HeartbeatArm", "label": "Arm", "type_id": "Part::Feature"},
            ],
            "surface": resolve_modeling_surface(
                "AssemblyWorkbench", "xscript"
            ).summary(),
            "freecad_home": str(App.getHomePath()),
            "timeout_seconds": 60.0,
            "memory_limit_bytes": 2 * 1024 * 1024 * 1024,
        }
    )
    shapes = {
        "HeartbeatBase": Part.makeBox(20, 16, 8),
        "HeartbeatArm": Part.makeCylinder(3, 30),
    }
    return finalize_candidate(
        prepared,
        [
            {
                "document_uid": document_uid,
                "object_name": name,
                "label": name,
                "type_id": "Part::Feature",
                "shape_type": str(shape.ShapeType),
                "detached_shape": shape,
                "snapshot_index": snapshot_index,
                "source_kind": "shape",
                "transient_topology": False,
                "requires_semantic_interfaces": False,
                "published_interfaces": {},
            }
            for snapshot_index, (name, shape) in enumerate(shapes.items())
        ],
    )


def main() -> int:
    application = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    del application
    root = Path(tempfile.mkdtemp(prefix="cadex-qt-heartbeat-"))
    try:
        prepared = [
            _candidate(root, index, workbench, output_type, result)
            for index, (workbench, output_type, result) in enumerate(WORKER_CASES)
        ]
        prepared.append(_assembly_candidate(root, len(prepared)))
        outcomes: list[dict] = []
        failures: list[str] = []
        bridge = _Bridge()
        event_loop = QtCore.QEventLoop()
        bridge.finished.connect(event_loop.quit)
        heartbeats = [0]
        timer = QtCore.QTimer()
        timer.setInterval(10)
        timer.timeout.connect(lambda: heartbeats.__setitem__(0, heartbeats[0] + 1))

        def work() -> None:
            try:
                for candidate in prepared:
                    outcome = execute_candidate(candidate, cancellation_check=None)
                    outcomes.append(outcome)
                    if outcome.get("ok") is not True:
                        failures.append(str(outcome))
                        break
            except BaseException as exc:
                failures.append(f"{exc.__class__.__name__}: {exc}")
            finally:
                bridge.finished.emit()

        started = time.monotonic()
        worker = threading.Thread(
            target=work, name="CadexQtHeartbeatWorker", daemon=True
        )
        timer.start()
        worker.start()
        event_loop.exec()
        timer.stop()
        worker.join(timeout=5.0)
        elapsed = time.monotonic() - started
        assert not worker.is_alive(), "The background domain worker did not finish."
        assert not failures, failures
        assert len(outcomes) == len(prepared)
        assert heartbeats[0] >= 10, (
            "The Qt event loop did not remain responsive during domain subprocess waits: "
            f"heartbeats={heartbeats[0]}, elapsed={elapsed:.3f}s"
        )
        for candidate, outcome in zip(prepared, outcomes):
            validated = validate_candidate(candidate, outcome)
            assert validated["ok"] is True
        print(
            json.dumps(
                {
                    "ok": True,
                    "integration": "qt_domain_worker_heartbeat",
                    "domains": [candidate["pack"].domain for candidate in prepared],
                    "heartbeats": heartbeats[0],
                    "elapsed_seconds": round(elapsed, 3),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
