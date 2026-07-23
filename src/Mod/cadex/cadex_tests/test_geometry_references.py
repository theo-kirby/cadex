# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pinned geometry references: capture, fingerprinting, and payload delivery.

``CadexService.capture_selection_reference`` turns the live 3D selection into
durable, message-scoped picks. Each pick gets a stable per-kind handle and a
geometric fingerprint whose fields are produced by the very same helpers as
``partdesign.find_subelements`` (``_canonical_geometry_type``, ``_vector_dict``,
``_bounding_box_dict``), so the agent can feed them straight back into that tool
after a recompute drifts topology names. These tests pin that contract with
lightweight geometry fakes (no running FreeCAD) plus the provider-payload gating.
"""

from __future__ import annotations

import math
import sys
from types import SimpleNamespace

import pytest

import CadexCore
from CadexCore import CadexService
from CadexSession import _provider_state_payload


# --- Geometry fakes (duck-typed to the Part.TopoShape surface we consume) ----


class Vec:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x, self.y, self.z = float(x), float(y), float(z)

    @property
    def Length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalize(self) -> "Vec":
        length = self.Length or 1.0
        self.x, self.y, self.z = self.x / length, self.y / length, self.z / length
        return self


class BBox:
    def __init__(self, xmin, xmax, ymin, ymax, zmin, zmax) -> None:
        self.XMin, self.XMax = xmin, xmax
        self.YMin, self.YMax = ymin, ymax
        self.ZMin, self.ZMax = zmin, zmax


class Line:
    """Curve whose class name canonicalizes to 'line'."""


class Circle:
    """Curve whose class name canonicalizes to 'circle'."""

    def __init__(self, radius: float) -> None:
        self.Radius = radius


class FakeEdge:
    def __init__(self, curve, length, center, direction=None, bbox=None) -> None:
        self.Curve = curve
        self.Length = length
        self.CenterOfMass = center
        self.FirstParameter = 0.0
        self._direction = direction
        self.BoundBox = bbox or BBox(0, length, 0, 0, 0, 0)

    def tangentAt(self, _param):
        if self._direction is None:
            raise RuntimeError("no tangent")
        return Vec(self._direction.x, self._direction.y, self._direction.z)


class FakeShape:
    def __init__(self, edges=(), faces=(), vertexes=()) -> None:
        self.Edges = list(edges)
        self.Faces = list(faces)
        self.Vertexes = list(vertexes)


class FakeObject:
    def __init__(self, name, shape, type_id="PartDesign::Pad", label=None) -> None:
        self.Name = name
        self.Label = label or name
        self.TypeId = type_id
        self.Shape = shape


class FakeSelectionItem:
    def __init__(self, obj, sub_names=(), sub_objects=()) -> None:
        self.Object = obj
        self.SubElementNames = list(sub_names)
        self.SubObjects = list(sub_objects)


class FakeSelectionApi:
    def __init__(self, items) -> None:
        self._items = list(items)

    def getSelectionEx(self):
        return list(self._items)


def _service_with_selection(items) -> CadexService:
    """A bare service whose only live state is the pinned-references list."""
    service = CadexService.__new__(CadexService)
    service._geometry_references = []
    service.structural_document_revision = lambda: "rev-1"  # type: ignore[method-assign]
    gui = sys.modules["FreeCADGui"]
    gui.Selection = FakeSelectionApi(items)
    return service


@pytest.fixture(autouse=True)
def _restore_gui_selection():
    gui = sys.modules["FreeCADGui"]
    had = hasattr(gui, "Selection")
    previous = getattr(gui, "Selection", None)
    yield
    if had:
        gui.Selection = previous
    elif hasattr(gui, "Selection"):
        del gui.Selection


# --- Capture + fingerprint ---------------------------------------------------


def test_capture_edge_pin_fingerprint_matches_find_subelements_fields() -> None:
    edge = FakeEdge(
        curve=Line(),
        length=20.0,
        center=Vec(10.0, 0.0, 0.0),
        direction=Vec(1.0, 0.0, 0.0),
        bbox=BBox(0.0, 20.0, 0.0, 0.0, 0.0, 0.0),
    )
    obj = FakeObject("Pad", FakeShape(edges=[FakeEdge(Line(), 0, Vec(0, 0, 0)), edge]))
    service = _service_with_selection([FakeSelectionItem(obj, ["Edge2"])])

    result = service.capture_selection_reference()

    assert result["ok"] is True
    assert result["count"] == 1
    (reference,) = result["references"]
    assert reference["kind"] == "edge"
    assert reference["handle"] == "@edge-1"
    assert reference["object_name"] == "Pad"
    assert reference["object_type"] == "PartDesign::Pad"
    assert reference["subelement"] == "Edge2"
    assert reference["captured_at_revision"] == "rev-1"

    fingerprint = reference["fingerprint"]
    # Fields produced by the shared find_subelements helpers.
    assert fingerprint["geometry_type"] == "line"
    assert fingerprint["length"] == 20.0
    assert fingerprint["center_of_mass"] == {"x": 10.0, "y": 0.0, "z": 0.0}
    assert fingerprint["direction"] == {"x": 1.0, "y": 0.0, "z": 0.0}
    assert fingerprint["bounding_box"]["x_max"] == 20.0
    assert "radius" not in fingerprint


def test_capture_circular_edge_records_radius() -> None:
    edge = FakeEdge(curve=Circle(4.0), length=25.13, center=Vec(0, 0, 5))
    obj = FakeObject("Pad", FakeShape(edges=[edge]))
    service = _service_with_selection([FakeSelectionItem(obj, ["Edge1"])])

    (reference,) = service.capture_selection_reference()["references"]
    assert reference["fingerprint"]["geometry_type"] == "circle"
    assert reference["fingerprint"]["radius"] == 4.0
    assert "direction" not in reference["fingerprint"]


def test_empty_selection_returns_error() -> None:
    service = _service_with_selection([])
    result = service.capture_selection_reference()
    assert result["ok"] is False
    assert "Select an edge" in result["error"]
    assert service._geometry_references == []


def test_whole_object_pick_yields_object_reference() -> None:
    obj = FakeObject("Body", FakeShape(edges=[FakeEdge(Line(), 1.0, Vec(0, 0, 0))]))
    obj.Shape.Volume = 1000.0
    obj.Shape.ShapeType = "Solid"
    obj.Shape.BoundBox = BBox(0, 10, 0, 10, 0, 10)
    service = _service_with_selection([FakeSelectionItem(obj, [])])

    (reference,) = service.capture_selection_reference()["references"]
    assert reference["kind"] == "object"
    assert reference["handle"] == "@object-1"
    assert reference["object_name"] == "Body"
    assert reference["fingerprint"]["volume"] == 1000.0
    assert reference["fingerprint"]["shape_type"] == "Solid"


def test_sketch_subelement_skips_find_subelements_fingerprint() -> None:
    obj = FakeObject("Sketch", FakeShape(), type_id="Sketcher::SketchObject")
    service = _service_with_selection([FakeSelectionItem(obj, ["Edge3"])])

    (reference,) = service.capture_selection_reference()["references"]
    assert reference["kind"] == "sketch_element"
    assert reference["fingerprint"] == {}
    assert "sketch tools" in reference["fingerprint_note"]


def test_handles_never_renumber_across_captures() -> None:
    obj = FakeObject("Pad", FakeShape(edges=[FakeEdge(Line(), 5.0, Vec(0, 0, 0))]))
    service = _service_with_selection([FakeSelectionItem(obj, ["Edge1"])])

    service.capture_selection_reference()
    # Remove the first pin, then capture again; the handle must advance, not reuse.
    first_id = service._geometry_references[0]["id"]
    service.remove_geometry_reference(first_id)
    service.capture_selection_reference()

    assert service._geometry_references[0]["handle"] == "@edge-2"


def test_capture_enforces_cap_and_flags_truncation() -> None:
    edges = [FakeEdge(Line(), float(i), Vec(i, 0, 0)) for i in range(20)]
    obj = FakeObject("Pad", FakeShape(edges=edges))
    sub_names = [f"Edge{i + 1}" for i in range(20)]
    service = _service_with_selection([FakeSelectionItem(obj, sub_names)])

    result = service.capture_selection_reference()
    assert result["truncated"] is True
    assert result["count"] == CadexCore.MAX_GEOMETRY_REFERENCES


def test_missing_shape_records_partial_fingerprint_note() -> None:
    obj = SimpleNamespace(
        Name="Anno", Label="Anno", TypeId="Draft::Text", Shape=None
    )
    service = _service_with_selection([FakeSelectionItem(obj, ["Edge1"])])

    (reference,) = service.capture_selection_reference()["references"]
    assert reference["fingerprint"] == {}
    assert reference["fingerprint_note"] == "no shape geometry"


def test_summary_empty_when_nothing_pinned() -> None:
    service = _service_with_selection([])
    assert service.geometry_references_summary() == {}


def test_summary_carries_reresolution_note_when_pinned() -> None:
    obj = FakeObject("Pad", FakeShape(edges=[FakeEdge(Line(), 5.0, Vec(0, 0, 0))]))
    service = _service_with_selection([FakeSelectionItem(obj, ["Edge1"])])
    service.capture_selection_reference()

    summary = service.geometry_references_summary()
    assert summary["count"] == 1
    assert "find_subelements" in summary["note"]
    assert summary["references"][0]["handle"] == "@edge-1"


# --- Provider payload gating -------------------------------------------------


def test_payload_includes_pinned_geometry() -> None:
    context = {
        "selection": {"selection": []},
        "message_geometry_references": {
            "count": 1,
            "note": "n",
            "references": [{"id": "a", "handle": "@edge-1"}],
        },
    }
    payload = _provider_state_payload(context)
    assert "message_geometry_references" in payload


def test_payload_omits_empty_geometry_summary() -> None:
    context = {
        "selection": {"selection": []},
        "message_geometry_references": {},
    }
    payload = _provider_state_payload(context)
    assert "message_geometry_references" not in payload
