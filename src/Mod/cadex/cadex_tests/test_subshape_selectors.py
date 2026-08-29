# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Geometric selectors replace index arguments (Phase 10b, ADR-029).

Five part ops — ``subshape``, ``defeature``, ``fillet``, ``chamfer`` and
``thicken`` — used to take 1-based ordinals into ``TopExp::MapShapes``.
ADR-028 established that the ordering is *reproducible*; it is not *stable
across edits*. Any parameter change that alters topology renumbers every
subshape after the change, so a saved ``edges=[3, 7]`` keeps validating and
starts filleting different edges.

These tests pin the replacement: the selector vocabulary itself, the
validation that rejects the ways a selector can be wrong, and the real
resolution against a live kernel.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

from CadexSubshapeQuery import (
    SELECTOR_KEYS,
    SubshapeSelectionError,
    fingerprint_key,
    query_subelements,
    resolve_selected_subshapes,
)


# -- fake shapes -------------------------------------------------------------


class _Point:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x, self.y, self.z = x, y, z


def _surface(name: str, radius: float | None = None):
    """Stands in for Part.Plane / Part.Cylinder — the type name is the fact.

    ``subshape_geometry`` reads ``type(face.Surface).__name__``, so the
    class name is the whole fixture.
    """

    namespace = {} if radius is None else {"Radius": radius}
    return type(name, (), namespace)()


class _Face:
    def __init__(self, *, area, center, normal, surface="Plane", radius=None) -> None:
        self.Area = area
        self.CenterOfMass = _Point(*center)
        self.Surface = _surface(surface, radius)
        self.ParameterRange = (0.0, 1.0, 0.0, 1.0)
        self._normal = normal

    def normalAt(self, _u, _v):
        return _Point(*self._normal)


class _Shape:
    def __init__(self, faces=(), edges=()) -> None:
        self.Faces = list(faces)
        self.Edges = list(edges)
        self.Wires = []
        self.Shells = []
        self.Solids = []


def _drilled_plate() -> _Shape:
    """Six planar faces plus four 3 mm cylindrical holes."""

    planes = [
        _Face(area=300.0, center=(0, 15, 5), normal=(-1, 0, 0)),
        _Face(area=400.0, center=(20, 0, 5), normal=(0, -1, 0)),
        _Face(area=1086.9, center=(20, 15, 10), normal=(0, 0, 1)),
        _Face(area=400.0, center=(20, 30, 5), normal=(0, 1, 0)),
        _Face(area=1086.9, center=(20, 15, 0), normal=(0, 0, -1)),
        _Face(area=300.0, center=(40, 15, 5), normal=(1, 0, 0)),
    ]
    holes = [
        _Face(
            area=188.5,
            center=(x, y, 5),
            normal=(1, 0, 0),
            surface="Cylinder",
            radius=3.0,
        )
        for x, y in ((8, 7.5), (32, 7.5), (8, 22.5), (32, 22.5))
    ]
    return _Shape(faces=planes + holes)


# -- the vocabulary ----------------------------------------------------------


def test_cylindrical_faces_are_selectable_by_radius() -> None:
    """The whole point: "the four 3 mm holes", not "faces 7 through 10".

    Faces carried no ``radius_mm`` before Phase 10b, so this selection
    matched nothing at all while looking perfectly reasonable.
    """

    shape = _drilled_plate()
    selected, details = resolve_selected_subshapes(
        shape,
        "face",
        {"geometry_type": "Cylinder", "radius": 3.0, "expected_count": 4},
    )
    assert len(selected) == 4
    assert [item["name"] for item in details] == ["Face7", "Face8", "Face9", "Face10"]
    assert {item["radius_mm"] for item in details} == {3.0}


def test_a_selector_resolves_to_the_face_not_its_position() -> None:
    """The same selector survives a renumbering that would break an ordinal."""

    shape = _drilled_plate()
    selection = {"normal": [0, 0, 1], "min_area": 1000.0, "expected_count": 1}
    before, _ = resolve_selected_subshapes(shape, "face", selection)

    # A fifth hole drilled first pushes every later face along by one; the
    # old `faces=[3]` would now name a different face, silently.
    shape.Faces.insert(
        0,
        _Face(area=188.5, center=(20, 15, 5), normal=(1, 0, 0), surface="Cylinder", radius=3.0),
    )
    after, details = resolve_selected_subshapes(shape, "face", selection)
    assert after[0] is before[0]
    assert details[0]["name"] == "Face4"  # renumbered, same face


def test_cardinality_mismatch_raises_with_the_available_candidates() -> None:
    shape = _drilled_plate()
    with pytest.raises(SubshapeSelectionError) as excinfo:
        resolve_selected_subshapes(
            shape, "face", {"geometry_type": "Cylinder", "expected_count": 9}
        )
    details = excinfo.value.details
    assert details["expected_count"] == 9
    assert details["actual_count"] == 4
    # The envelope has to carry enough for the agent to re-query rather
    # than guess again.
    assert len(details["available"]) == 10
    assert details["stage"] == "topology_selection"


def test_all_selects_every_subshape_of_the_kind() -> None:
    shape = _drilled_plate()
    selected, details = resolve_selected_subshapes(shape, "face", "all")
    assert len(selected) == 10 and len(details) == 10


def test_all_on_an_empty_collection_is_a_failure_not_a_silent_noop() -> None:
    with pytest.raises(SubshapeSelectionError):
        resolve_selected_subshapes(_Shape(), "edge", "all")


def test_query_subelements_keeps_the_partdesign_contract() -> None:
    """Pin resolution and partdesign call this directly; names come back."""

    names, details = query_subelements(
        _drilled_plate(),
        {"element_type": "face", "geometry_type": "Plane", "expected_count": 6},
    )
    assert names == [f"Face{index}" for index in range(1, 7)]
    assert all(item["element_type"] == "face" for item in details)


def test_fingerprint_key_describes_geometry_not_position() -> None:
    shape = _drilled_plate()
    _selected, details = resolve_selected_subshapes(shape, "face", "all")
    keys = [fingerprint_key(item) for item in details]
    assert len(set(keys)) == len(keys), "the plate's faces are all distinguishable"
    assert keys[0].startswith("face|Plane|")
    assert "radius_mm=3.000" in keys[6]
    # The key must not encode the ordinal, or it would move when faces do.
    assert not any("Face" in key for key in keys)


# -- API-side validation -----------------------------------------------------


def _part_api():
    import CadexScriptedDomains as domains
    from cadex_domain_api import create_domain_api

    pack = domains.get_xscript_pack("PartWorkbench")
    assert pack is not None
    return create_domain_api(pack.domain, pack.api_exports, pack.output_types)


def test_index_lists_are_rejected_with_the_reason() -> None:
    api = _part_api()
    box = api.box(10, 10, 10)
    with pytest.raises(ValueError, match=r"index lists were removed"):
        api.fillet(box, 1.0, edges=[1, 2])
    with pytest.raises(ValueError, match=r"index lists were removed"):
        api.thicken(box, [1], 1.0)


def test_a_selector_must_declare_its_cardinality() -> None:
    api = _part_api()
    with pytest.raises(ValueError, match=r"expected_count"):
        api.defeature(api.box(10, 10, 10), {"geometry_type": "Cylinder"})


def test_unrecognised_selector_keys_are_rejected() -> None:
    """A typo must not widen the match — it would build wrong geometry."""

    api = _part_api()
    with pytest.raises(ValueError, match=r"unrecognised selector keys"):
        api.fillet(
            api.box(10, 10, 10),
            1.0,
            edges={"radius_tolerence": 0.1, "radius": 3.0, "expected_count": 1},
        )


def test_subshape_pins_expected_count_to_one() -> None:
    api = _part_api()
    box = api.box(10, 10, 10)
    value = api.subshape(box, "face", {"normal": [0, 0, 1]})
    assert value.arguments[-1]["expected_count"] == 1
    with pytest.raises(ValueError, match=r"must be 1"):
        api.subshape(box, "face", {"normal": [0, 0, 1], "expected_count": 2})


def test_all_is_only_accepted_where_it_means_something() -> None:
    api = _part_api()
    box = api.box(10, 10, 10)
    assert api.fillet(box, 1.0, edges="all").properties["edges"] == "all"
    with pytest.raises(ValueError, match=r"does not accept 'all'"):
        api.defeature(box, "all")


def test_selector_keys_are_the_documented_vocabulary() -> None:
    """The API validator and the resolver must agree on one key set."""

    assert "expected_count" in SELECTOR_KEYS
    assert {"geometry_type", "normal", "radius", "near_point"} <= SELECTOR_KEYS
    assert "element_type" not in SELECTOR_KEYS, (
        "the operation fixes the element type; letting a script restate it "
        "would allow part.fillet(edges={'element_type': 'face'})"
    )


# -- against a real kernel ---------------------------------------------------


CANONICAL = """
drilled = part.box(40, 30, 10)
for x in (8.0, 32.0):
    for y in (7.5, 22.5):
        drilled = part.cut(drilled, part.cylinder(3.0, 20.0, origin=[x, y, -5.0]))
result = {
    "drilled": drilled,
    "rounded": part.fillet(
        drilled, 0.5,
        edges={"geometry_type": "Circle", "radius": 3.0, "expected_count": 8},
    ),
    "healed": part.defeature(
        drilled, {"geometry_type": "Cylinder", "radius": 3.0, "expected_count": 4}
    ),
    "cup": part.thicken(
        part.box(20, 20, 10), {"normal": [0, 0, 1], "expected_count": 1}, -1.5
    ),
}
"""


def _face_kinds(client, output: str) -> dict[str, int]:
    """Harvest a shape's faces through the expected_count=0 failure envelope."""

    probe = client.request(
        "resolve_pin",
        {"output": output, "selection": {"element_type": "face", "expected_count": 0}},
    )
    counts: dict[str, int] = {}
    for face in (probe.get("observed") or {}).get("available") or []:
        counts[face["geometry_type"]] = counts.get(face["geometry_type"], 0) + 1
    return counts


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle", fromlist=["FREECADCMD"]).FREECADCMD is None,
    reason="No FreeCADCmd binary available for selector resolution.",
)
def test_selectors_resolve_against_a_real_kernel() -> None:
    """End to end: selectors pick the geometry they name, not an ordinal."""

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()
        client.request(
            "open_project",
            {"project_root": tempfile.mkdtemp(prefix="cadexd-selectors-")},
        )
        written = client.request(
            "write_script", {"source": CANONICAL, "expected_revision": ""}
        )
        assert written["ok"] is True, written

        # The plate: six planes, four cylindrical holes.
        assert _face_kinds(client, "drilled") == {"Plane": 6, "Cylinder": 4}
        # Filleting the eight radius-3 rims adds exactly eight toroids.
        assert _face_kinds(client, "rounded") == {
            "Plane": 6,
            "Cylinder": 4,
            "Toroid": 8,
        }
        # Defeaturing the four holes by radius heals back to a bare box.
        assert _face_kinds(client, "healed") == {"Plane": 6}
        # Thickening with the top face removed leaves a 6+5 hollow box.
        assert _face_kinds(client, "cup") == {"Plane": 11}
    finally:
        _stop(client)
