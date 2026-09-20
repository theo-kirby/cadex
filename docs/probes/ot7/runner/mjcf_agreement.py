# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Does an exported MJCF put each body where the solved assembly put it?

ADR-393 fixed an engine defect that placed a welded body at the **exact
inverse** of its parent-relative transform whenever the script wrote the
weld hardware-first, because FreeCAD's ``ensureUnconnectedIsSecondRef``
swapped ``Placement1``/``Placement2`` under the worker's feet. The defect is
invisible in every static fit number -- those read component placements --
and visible only once the body tree is composed down to world.

This is that composition, as a tool, so a retained model can be held against
the placements its own solve published without rebuilding anything. It reads
an exported ``*-model.xml`` and the ``validations.assembly.component_placements``
of the ``result.json`` beside it, and reports per body the world-position
error in millimetres and the world-orientation error in degrees.

It measures a retained artifact; it never rebuilds or re-accepts a design.

    pixi run python docs/probes/ot7/runner/mjcf_agreement.py MODEL.xml RESULT.json
"""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

#: MJCF lengths are metres; a Cadex placement is millimetres.
MM_PER_M = 1000.0

#: The Ondsel solver's own convergence residual is around 1e-6 mm, so a
#: body that agrees to this is carrying the placement the solve produced.
DEFAULT_TOLERANCE_MM = 1.0e-4

#: Same reasoning on the rotation half, in degrees.
DEFAULT_TOLERANCE_DEGREES = 1.0e-4


def _matrix_from_quaternion(quat):
    """A 3x3 rotation from an MJCF ``quat``, which is ``(w, x, y, z)``."""

    w, x, y, z = quat
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm == 0.0:
        raise ValueError("a zero quaternion is not a rotation")
    w, x, y, z = (value / norm for value in (w, x, y, z))
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]


def _multiply(left, right):
    """Compose two ``(rotation, translation)`` frames, left then right."""

    lr, lt = left
    rr, rt = right
    rotation = [
        [sum(lr[i][k] * rr[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]
    translation = [
        lt[i] + sum(lr[i][k] * rt[k] for k in range(3)) for i in range(3)
    ]
    return rotation, translation


def _frame_of(element):
    """The ``pos``/``quat`` an MJCF ``<body>`` carries, in millimetres."""

    pos = [float(value) * MM_PER_M for value in element.get("pos", "0 0 0").split()]
    quat = [float(value) for value in element.get("quat", "1 0 0 0").split()]
    return _matrix_from_quaternion(quat), pos


def compose_world_frames(model_xml: Path) -> dict:
    """Every named body in ``model_xml``, composed down to a world frame."""

    worldbody = ET.parse(model_xml).getroot().find("worldbody")
    if worldbody is None:
        raise ValueError(f"{model_xml} has no <worldbody>")
    frames: dict[str, tuple] = {}

    def walk(element, parent):
        for body in element.findall("body"):
            world = _multiply(parent, _frame_of(body))
            name = body.get("name")
            if name:
                frames[name] = world
            walk(body, world)

    identity = ([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], [0.0, 0.0, 0.0])
    walk(worldbody, identity)
    return frames


def _placement_frame(placement):
    """A solved component placement as a ``(rotation, translation)`` frame.

    The stored ``matrix`` is row-major 4x4 with a millimetre translation.
    """

    matrix = placement["matrix"]
    rotation = [[matrix[row * 4 + column] for column in range(3)] for row in range(3)]
    translation = [matrix[row * 4 + 3] for row in range(3)]
    return rotation, translation


def _orientation_error_degrees(left, right):
    """The angle of the rotation carrying ``left`` onto ``right``."""

    trace = sum(
        sum(left[k][i] * right[k][j] for k in range(3))
        for i, j in ((0, 0), (1, 1), (2, 2))
    )
    return math.degrees(math.acos(max(-1.0, min(1.0, (trace - 1.0) / 2.0))))


def agreement(model_xml: Path, result_json: Path) -> dict:
    """Per body, how far the model's world pose is from the solved placement."""

    result = json.loads(Path(result_json).read_text())
    placements = result["validations"]["assembly"]["component_placements"]
    frames = compose_world_frames(Path(model_xml))
    rows = []
    for name in sorted(frames):
        placement = placements.get(name)
        if placement is None:
            rows.append({"body": name, "status": "no_placement"})
            continue
        solved = _placement_frame(placement)
        model = frames[name]
        rows.append(
            {
                "body": name,
                "status": "measured",
                "position_error_mm": math.dist(model[1], solved[1]),
                "orientation_error_degrees": _orientation_error_degrees(
                    model[0], solved[0]
                ),
                "solved_rotation_degrees": float(
                    placement.get("rotation_angle_degrees", 0.0)
                ),
            }
        )
    return {
        "model": str(model_xml),
        "result": str(result_json),
        "bodies": len(frames),
        "rows": rows,
        "missing_placements": sorted(
            name for name in frames if name not in placements
        ),
    }


def verdict(report: dict, tolerance_mm=DEFAULT_TOLERANCE_MM,
            tolerance_degrees=DEFAULT_TOLERANCE_DEGREES) -> dict:
    """``report`` reduced to a pass/fail and the worst body behind it."""

    measured = [row for row in report["rows"] if row["status"] == "measured"]
    disagreeing = [
        row
        for row in measured
        if row["position_error_mm"] > tolerance_mm
        or row["orientation_error_degrees"] > tolerance_degrees
    ]
    worst = max(measured, key=lambda row: row["position_error_mm"], default=None)
    return {
        "bodies": report["bodies"],
        "measured": len(measured),
        "disagreeing": len(disagreeing),
        "agrees": not disagreeing and not report["missing_placements"],
        "tolerance_mm": tolerance_mm,
        "tolerance_degrees": tolerance_degrees,
        "worst": worst,
        "disagreeing_bodies": sorted(row["body"] for row in disagreeing),
        "missing_placements": report["missing_placements"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path, help="an exported *-model.xml")
    parser.add_argument("result", type=Path, help="the result.json beside it")
    parser.add_argument("--tolerance-mm", type=float, default=DEFAULT_TOLERANCE_MM)
    parser.add_argument(
        "--tolerance-degrees", type=float, default=DEFAULT_TOLERANCE_DEGREES
    )
    args = parser.parse_args(argv)
    report = agreement(args.model, args.result)
    summary = verdict(report, args.tolerance_mm, args.tolerance_degrees)
    print(json.dumps(summary, indent=2))
    return 0 if summary["agrees"] else 1


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
