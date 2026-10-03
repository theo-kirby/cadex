# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``inspect scope="contacts"``: which parts touch at rest (ADR-508).

The assembly worker already measures it. Every ``assembly.mjcf`` export runs
MuJoCo's collision pass at the solved pose and keeps the result in the
accepted attempt's ``result.json`` (``CadexDynamics._initial_contacts``,
ADR-087). Until this scope the agent could not read it: ``scope=output``
serves an output's facts and not its ``assembly_data``. The dashboard's
collision view shows the same block (``review_server.accepted_model``).

The store here is fabricated, the idiom ``test_inventory_scope`` uses; the
block's shape is the one the real worker wrote for a floor and a post sunk
2 mm into it, measured on a real build.
"""

from __future__ import annotations

import pytest

from CadexInspection import (
    CONTACTS_MEASURE,
    CONTACTS_POSE,
    _complete_contacts,
    capture_inspection,
    complete_inspection,
    contact_pairs,
)

from test_inventory_scope import _service, _store


def _contact(a: str, b: str, x: float, y: float, distance: float) -> dict:
    return {
        "geoms": [f"{a}/collision0", f"{b}/collision0"],
        "component_outputs": [a, b],
        "position_mm": [x, y, distance / 2],
        "distance_mm": distance,
        "penetrating": distance < -1.0e-6,
        "margin_mm": 0.0,
    }


SUNK = [_contact("floor", "post", x, y, -2.0) for x in (50.0, 70.0) for y in (-10.0, 10.0)]
RESTING = [_contact("foot", "floor", 0.0, 0.0, 0.0)]


def _mjcf(name: str, contacts: list, *, omitted: int = 0, dynamics: bool = True) -> dict:
    data = {"assembly_output": "asm", "mjcf_output": name}
    if dynamics:
        data["dynamics"] = {
            "initial_contact_count": len(contacts) + omitted,
            "initial_contacts": contacts,
            "initial_contacts_omitted": omitted,
            "contact_exclusions": [["block", "floor"], ["block", "post"]],
        }
    return {"name": name, "type": "mjcf", "domain": "assembly",
            "artifact_kind": "assembly_mjcf_xml", "assembly_data": data}


def _captured(root, **arguments):
    captured = capture_inspection(_service(root), {"scope": "contacts", **arguments})
    assert captured["kind"] == "contacts"
    return captured


def _contacts(root, **arguments):
    """The scope's whole value, before the inspection page cuts it."""

    return {"value": _complete_contacts(_captured(root, **arguments))}


def test_contacts_are_grouped_by_pair_penetrating_first(tmp_path) -> None:
    root = _store(tmp_path, {"ok": True, "outputs": [
        {"name": "asm", "type": "assembly", "domain": "assembly"},
        _mjcf("model", RESTING + SUNK),
    ]})
    value = _contacts(root)["value"]

    assert value["available"] is True
    assert value["revision"] == "c" * 64
    # What it is and is not, on the value itself.
    assert value["pose"] == CONTACTS_POSE and "t=0" in value["pose"]
    assert value["measures"] == CONTACTS_MEASURE and "scope=clearance" in value["measures"]
    [model] = value["models"]
    assert model["mjcf_output"] == "model" and model["assembly_output"] == "asm"
    assert model["count"] == 5 and model["omitted"] == 0 and model["pairs_complete"] is True
    # Four points of one sunk post are one pair, ahead of the foot that rests.
    assert model["pairs"] == [
        {"components": ["floor", "post"], "points": 4, "penetrating": True, "deepest_mm": -2.0},
        {"components": ["floor", "foot"], "points": 1, "penetrating": False, "deepest_mm": 0.0},
    ]
    assert model["contacts"] == RESTING + SUNK
    assert model["contact_exclusions"] == [["block", "floor"], ["block", "post"]]
    # Through the paged inspection, a pointer reaches one pair.
    paged = complete_inspection(_captured(root, path="/models/0/pairs/0", limit=10))
    assert paged["ok"] is True and paged["value"]["components"] == ["floor", "post"]


def test_nothing_touching_is_available_and_empty(tmp_path) -> None:
    root = _store(tmp_path, {"ok": True, "outputs": [_mjcf("model", [])]})
    [model] = _contacts(root)["value"]["models"]
    assert model["available"] is True and model["count"] == 0 and model["pairs"] == []


def test_a_listing_cut_at_the_cap_says_its_pairs_may_be_incomplete(tmp_path) -> None:
    root = _store(tmp_path, {"ok": True, "outputs": [_mjcf("model", SUNK, omitted=70)]})
    [model] = _contacts(root)["value"]["models"]
    assert model["count"] == 74 and model["omitted"] == 70
    assert model["pairs_complete"] is False


def test_no_export_and_an_export_without_evidence_say_why(tmp_path) -> None:
    none = _contacts(_store(tmp_path / "a", {"ok": True, "outputs": [
        {"name": "asm", "type": "assembly", "domain": "assembly"}]}))["value"]
    assert none["available"] is False and none["models"] == []
    assert "no assembly.mjcf output" in none["reason"]

    old = _contacts(_store(tmp_path / "b", {"ok": True, "outputs": [
        _mjcf("model", [], dynamics=False)]}))["value"]
    assert old["available"] is False
    assert old["models"][0]["available"] is False
    assert "rebuild" in old["models"][0]["reason"]


def test_a_target_names_one_export_and_an_unknown_one_is_refused(tmp_path) -> None:
    root = _store(tmp_path, {"ok": True, "outputs": [_mjcf("a", SUNK), _mjcf("b", RESTING)]})
    [model] = _contacts(root, target="b")["value"]["models"]
    assert model["mjcf_output"] == "b"
    refused = complete_inspection(_captured(root, target="nope"))
    assert refused["ok"] is False
    assert "no MJCF export named 'nope'" in str(refused)


@pytest.mark.parametrize("junk", [None, [], [{"component_outputs": ["one"]}], ["x"]])
def test_malformed_rows_are_skipped_not_fatal(junk) -> None:
    assert contact_pairs(junk) == []
