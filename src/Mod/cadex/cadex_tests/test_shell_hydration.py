# SPDX-License-Identifier: LGPL-2.1-or-later

"""Shell hydration unit coverage on conftest stubs (Phase 5.4)."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

import CadexScriptedDomains as contracts
import CadexShellHydration as hydration


class _FakeShape:
    def __init__(self) -> None:
        self.imported_path: str | None = None

    def importBrep(self, path: str) -> None:
        self.imported_path = path

    def isNull(self) -> bool:
        return False

    def isValid(self) -> bool:
        return "invalid" not in str(self.imported_path or "")


class _FakeMesh:
    def __init__(self) -> None:
        self.read_path: str | None = None

    def read(self, Filename: str) -> None:
        self.read_path = Filename


class _FakeObject:
    _counter = 0

    def __init__(self, type_id: str, name: str) -> None:
        _FakeObject._counter += 1
        self.TypeId = type_id
        self.Name = f"{name}_{_FakeObject._counter}"
        self.Label = ""
        self.PropertiesList: list[str] = []
        self.OutList: list[Any] = []
        self.Group: list[Any] = []
        self.OutListRecursive: list[Any] = []

    def addProperty(self, _kind: str, name: str, _group: str, _doc: str):
        if name not in self.PropertiesList:
            self.PropertiesList.append(name)
            setattr(self, name, "")
        return self


class _FakeDocument:
    def __init__(self) -> None:
        self.Objects: list[_FakeObject] = []
        self.transactions: list[str] = []
        self.commits = 0
        self.aborts = 0
        self.recomputes = 0
        self.removed: list[str] = []

    def addObject(self, type_id: str, name: str) -> _FakeObject:
        obj = _FakeObject(type_id, name)
        self.Objects.append(obj)
        return obj

    def removeObject(self, name: str) -> None:
        self.removed.append(name)
        self.Objects = [obj for obj in self.Objects if obj.Name != name]

    def getObject(self, name: str) -> _FakeObject | None:
        return next((obj for obj in self.Objects if obj.Name == name), None)

    def openTransaction(self, label: str) -> None:
        self.transactions.append(label)

    def commitTransaction(self) -> None:
        self.commits += 1

    def abortTransaction(self) -> None:
        self.aborts += 1

    def recompute(self) -> None:
        self.recomputes += 1


@pytest.fixture(autouse=True)
def _fake_geometry_modules(monkeypatch):
    part = types.ModuleType("Part")
    part.Shape = _FakeShape
    mesh = types.ModuleType("Mesh")
    mesh.Mesh = _FakeMesh
    monkeypatch.setitem(sys.modules, "Part", part)
    monkeypatch.setitem(sys.modules, "Mesh", mesh)
    freecad = sys.modules["FreeCAD"]
    monkeypatch.setattr(
        freecad, "Matrix", lambda *values: ("matrix", values), raising=False
    )
    monkeypatch.setattr(
        freecad, "Placement", lambda matrix: ("placement", matrix), raising=False
    )


def _payload(
    names: list[str],
    *,
    revision: str = "rev-1",
    kinds: dict[str, str] | None = None,
    placements: dict[str, list[float]] | None = None,
) -> dict:
    kinds = kinds or {}
    placements = placements or {}
    return {
        "ok": True,
        "revision": revision,
        "outputs": [
            {"name": name, "type": "solid", "domain": "part"} for name in names
        ],
        "display": {
            name: {
                "artifact_kind": kinds.get(name, "brep"),
                "artifact_path": f"/staging/outputs/{name}.artifact",
                "placement": placements.get(name),
                "tessellation": None,
            }
            for name in names
        },
    }


def test_creates_tagged_objects_in_one_transaction() -> None:
    doc = _FakeDocument()
    report = hydration.hydrate_accepted_state(doc, _payload(["plate", "lid"]))
    assert len(report["created"]) == 2
    assert report["updated"] == [] and report["removed"] == []
    assert doc.transactions == ["Cadex model update"]
    assert doc.commits == 1 and doc.aborts == 0
    assert doc.recomputes == 1
    plate = next(obj for obj in doc.Objects if obj.Label == "plate")
    assert plate.TypeId == "Part::Feature"
    assert getattr(plate, contracts.PROP_PROGRAM_ID) == "project"
    assert getattr(plate, contracts.PROP_PROGRAM_OUTPUT) == "plate"
    assert getattr(plate, contracts.PROP_PROGRAM_REVISION) == "rev-1"
    assert plate.Shape.imported_path == "/staging/outputs/plate.artifact"


def test_updates_existing_objects_and_moves_revision_tag() -> None:
    doc = _FakeDocument()
    hydration.hydrate_accepted_state(doc, _payload(["plate"]))
    first = doc.Objects[0]
    report = hydration.hydrate_accepted_state(
        doc, _payload(["plate"], revision="rev-2")
    )
    assert report["created"] == []
    assert report["updated"] == [first.Name]
    assert doc.Objects[0] is first
    assert getattr(first, contracts.PROP_PROGRAM_REVISION) == "rev-2"
    # Still exactly one undo step per pass.
    assert doc.commits == 2


def test_contract_driven_gc_removes_leavers() -> None:
    doc = _FakeDocument()
    hydration.hydrate_accepted_state(doc, _payload(["plate", "lid"]))
    lid = next(obj for obj in doc.Objects if obj.Label == "lid")
    report = hydration.hydrate_accepted_state(
        doc, _payload(["plate"], revision="rev-2")
    )
    assert report["removed"] == [lid.Name]
    assert all(obj.Label != "lid" for obj in doc.Objects)


def test_type_mismatch_is_replaced_not_updated() -> None:
    doc = _FakeDocument()
    # A stale publication-era native object still tagged for this output.
    body = doc.addObject("PartDesign::Body", "OldBody")
    for prop, value in (
        (contracts.PROP_PROGRAM_ID, "project"),
        (contracts.PROP_PROGRAM_DOMAIN, "partdesign"),
        (contracts.PROP_PROGRAM_OUTPUT, "plate"),
    ):
        body.addProperty("App::PropertyString", prop, "Cadex", "")
        setattr(body, prop, value)
    report = hydration.hydrate_accepted_state(doc, _payload(["plate"]))
    assert report["created"], report
    assert body.Name in report["removed"]
    plate = next(obj for obj in doc.Objects if obj.Label == "plate")
    assert plate.TypeId == "Part::Feature"


def test_mesh_outputs_hydrate_mesh_features() -> None:
    doc = _FakeDocument()
    hydration.hydrate_accepted_state(
        doc, _payload(["skin"], kinds={"skin": "mesh"})
    )
    skin = doc.Objects[0]
    assert skin.TypeId == "Mesh::Feature"
    assert skin.Mesh.read_path == "/staging/outputs/skin.artifact"


def test_placement_is_applied_to_components() -> None:
    doc = _FakeDocument()
    matrix = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 4.0,
              0.0, 0.0, 0.0, 1.0]
    hydration.hydrate_accepted_state(
        doc, _payload(["top"], placements={"top": matrix})
    )
    top = doc.Objects[0]
    assert top.Placement == ("placement", ("matrix", tuple(matrix)))


def test_non_displayable_outputs_create_nothing() -> None:
    doc = _FakeDocument()
    payload = _payload(["diag"])
    payload["display"]["diag"]["artifact_kind"] = None
    report = hydration.hydrate_accepted_state(doc, payload)
    assert doc.Objects == []
    assert report["created"] == []


def test_failure_aborts_the_transaction() -> None:
    doc = _FakeDocument()
    payload = _payload(["plate"])
    payload["display"]["plate"]["artifact_path"] = "/staging/invalid.brep"
    with pytest.raises(RuntimeError):
        hydration.hydrate_accepted_state(doc, payload)
    assert doc.aborts == 1
    assert doc.commits == 0
