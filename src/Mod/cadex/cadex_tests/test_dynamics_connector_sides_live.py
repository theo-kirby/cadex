# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The exported body tree stands where the solver put the parts (ADR-393).

An MJCF body's frame is written *relative to its parent*, derived from the
joint's two connector frames rather than from the solved placements, so that
the model's reference configuration is a canonical one and the solved pose
has to be recovered as a joint coordinate. That derivation is only as good
as the pairing between a connector frame and the component it belongs to,
and FreeCAD breaks that pairing on its own: ``setJointConnectors`` calls
``ensureUnconnectedIsSecondRef``, which swaps ``Reference1``/``Reference2``
together with ``Placement1``/``Placement2`` whenever the first reference's
part is the unconnected one.

That is exactly the shape a weld takes when a script fixes a bought part to
the printed part carrying it -- ``connector(part, "origin")`` first, the host
second -- and before ADR-393 every such body was exported at the **exact
inverse** of its parent-relative transform. Nothing refused: the model
compiled, it had mass and collision geoms, and it simulated. The check that
catches it is the one this file runs: compose the exported tree down to world
and compare it with the placements the assembly solver actually produced.

The fixture carries both orders in one assembly, because the fix has to move
one without moving the other:

* ``tab`` is welded to ``base`` with the **tab's** connector written first --
  the unconnected part first, so FreeCAD swaps. Its parent-relative frame
  must be the host-side connector frame, 20 mm along the rotated base's own
  +X and 6 mm up, turned 90 degrees about X.
* ``swing`` hinges on ``base`` with the **base's** connector written first --
  the connected part first, so FreeCAD does not swap. It was already right
  and must stay right.

The base is placed at 37 degrees about +Z so that an inverted frame cannot
pass by symmetry.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ElementTree

import pytest

import CadexDynamics as dyn
from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

pytestmark = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)

#: One grounded plate at a non-symmetric angle, one welded tab written
#: hardware-first, one hinged arm written host-first.
SOURCE = """
plate = part.box(60, 60, 6)
block = part.box(10, 10, 10)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True,
                          placement={"position": [0, 0, 0],
                                     "axis": [0, 0, 1],
                                     "angle_degrees": 37})
tab = assembly.component(block)
swing = assembly.component(arm, placement=[0, 0, 40])
weld = assembly.joint("fixed",
                      assembly.connector(tab, "origin"),
                      assembly.connector(base, "origin",
                                         offset={"position": [20, 0, 6],
                                                 "axis": [1, 0, 0],
                                                 "angle_degrees": 90}))
hinge = assembly.joint("revolute",
                       assembly.connector(base, "origin",
                                          offset={"position": [12, 0, 6],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": 90}),
                       assembly.connector(swing, "origin",
                                          offset={"position": [0, 0, 0],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": 90}))
asm = assembly.assembly([base, tab, swing], [weld, hinge])
diag = assembly.solve(asm)
model = assembly.mjcf(asm, [assembly.body(base, density_kg_m3=2700),
                            assembly.body(tab, density_kg_m3=2700),
                            assembly.body(swing, density_kg_m3=7850)])
result = {"plate": plate, "block": block, "arm": arm, "base": base,
          "tab": tab, "swing": swing, "weld": weld, "hinge": hinge,
          "asm": asm, "diag": diag, "model": model}
"""


def _exported() -> tuple[bytes, dict[str, list[float]]]:
    """The retained MJCF, and the pose the solver settled each part at."""

    root = Path(tempfile.mkdtemp(prefix="connector-sides-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        written = client.request(
            "write_script", {"source": SOURCE, "expected_revision": ""}
        )
        assert written["ok"] is True, json.dumps(written)[:4000]
        xml = next(
            Path(entry["artifact_path"]).read_bytes()
            for entry in written["display"].values()
            if str(entry.get("artifact_kind") or "") == "assembly_mjcf_xml"
        )
        inventory = client.request(
            "inspect", {"scope": "inventory", "path": "/components"}
        )
        assert inventory["ok"] is True, json.dumps(inventory)[:2000]
        placements = {
            str(row["component"]): list(row["placement"]["matrix"])
            for row in inventory["value"]
        }
        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
        return xml, placements
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


def _body_frames(xml: bytes) -> dict[str, list[float]]:
    """Every MJCF body, composed down the tree to world, in millimetres."""

    world: dict[str, list[float]] = {}

    def walk(element, parent: list[float]) -> None:
        for body in element.findall("body"):
            position = [
                float(value) * 1000.0
                for value in (body.get("pos") or "0 0 0").split()
            ]
            quaternion = [
                float(value) for value in (body.get("quat") or "1 0 0 0").split()
            ]
            local = dyn.matrix_from_quaternion_wxyz(quaternion, position)
            frame = dyn.matrix_multiply(parent, local)
            world[str(body.get("name"))] = frame
            walk(body, frame)

    root = ElementTree.fromstring(xml.decode("utf-8"))
    walk(root.find("worldbody"), list(dyn.IDENTITY_MATRIX))
    return world


def test_exported_bodies_stand_where_the_solver_put_them() -> None:
    xml, placements = _exported()
    world = _body_frames(xml)
    assert set(world) == set(placements), sorted(world)
    for name, solved in sorted(placements.items()):
        # A tenth of a micrometre: the hinged arm disagrees by 4.1e-6 mm,
        # which is the Ondsel solver's own convergence residual and not a
        # frame error. What this rules out is measured in tens of
        # millimetres -- the welded tab was 41.2 mm away before ADR-393.
        assert world[name] == pytest.approx(solved, abs=1.0e-4), (
            f"{name} is exported at a different pose than the solver produced"
        )


def test_the_welded_tab_carries_the_host_side_connector_frame() -> None:
    """The number this fixture is worth, stated before it is measured.

    ``tab``'s frame relative to ``base`` is the base-side connector: 20 mm
    along the base's own +X, 6 mm up, rotated 90 degrees about +X. Its
    inverse -- what the swap produced -- is -20 mm, -6 mm and -90 degrees,
    which the first assertion below also rules out on its own.
    """

    xml, placements = _exported()
    world = _body_frames(xml)
    relative = dyn.matrix_multiply(
        dyn.matrix_inverse(world["base"]), world["tab"]
    )
    expected = dyn.matrix_from_quaternion_wxyz(
        dyn.quaternion_from_axis_angle_wxyz((1.0, 0.0, 0.0), math.radians(90.0)),
        (20.0, 0.0, 6.0),
    )
    assert relative == pytest.approx(expected, abs=1.0e-9)
    # ...and the hinge, written host-first, was never swapped and is unmoved.
    hinged = dyn.matrix_multiply(
        dyn.matrix_inverse(world["base"]), world["swing"]
    )
    assert dyn.matrix_translation_mm(hinged) == pytest.approx(
        [12.0, 0.0, 6.0], abs=1.0e-9
    )
    assert placements["base"][:3] == pytest.approx(
        [math.cos(math.radians(37.0)), -math.sin(math.radians(37.0)), 0.0],
        abs=1.0e-9,
    )
