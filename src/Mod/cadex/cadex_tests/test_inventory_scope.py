# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``inspect scope="inventory"``: what the assembly is made of (ADR-236).

Two halves, and each fails without the other.

The **stamp**: ``lib.bolt("M3", 12).body`` is an ordinary part solid by the
time a script returns it, so a bill of catalogued hardware reached the report
as a list of anonymous solids. ``_stamp_catalog_identity`` writes the family
and part number beside the definition — never inside it, which is what keeps
the content digest still: a definition change forces every project using it
to be re-accepted (ADR-064).

The **join**: a ``component_link`` output already names the output it places
(``source_output``, ADR-049) and carries the pose the solver settled on. The
scope walks one to the other, so an agent reviewing an assembly headlessly
reads one call instead of one ``scope="output"`` per output plus the join by
hand.

``inspect`` already takes ``{"scope": str}``, so none of this is a protocol
change; the store here is fabricated, the idiom ``test_wiring_scope`` uses.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import cadex_project_worker
from CadexInspection import capture_inspection, complete_inspection
from CadexScriptStore import CadexProjectScriptStore
from cadex_domain_api import DomainValue
from cadex_library_api import LibraryPart, library_catalog_identity


REVISION = "c" * 64
DIGEST = "d" * 64


def _solid(operation: str, arguments: list) -> DomainValue:
    return DomainValue(
        domain="part",
        operation=operation,
        output_type="solid",
        arguments=tuple(arguments),
        properties={},
    )


def _part_output(name: str, value: DomainValue, **extra) -> dict:
    item = {
        "name": name,
        "type": "solid",
        "domain": "part",
        "artifact_kind": "brep",
        "definition": value.to_payload(),
        "facts": {
            "shape_type": "Solid",
            "solids": 1,
            "volume_mm3": 84.823,
            "area_mm2": 210.5,
            "bounds_mm": [0.0, 0.0, -12.0, 5.5, 5.5, 2.0],
            "center_of_mass_mm": [0.0, 0.0, -5.0],
            "faces": 6,
        },
    }
    item.update(extra)
    return item


def _component_output(name: str, source: str, *, position, grounded=False) -> dict:
    return {
        "name": name,
        "type": "component_link",
        "domain": "assembly",
        "definition": {
            "domain": "assembly",
            "operation": "component",
            "output_type": "component_link",
            "arguments": [{"document_uid": "inline", "object_name": "tok"}],
            "properties": {"label": f"{name} label", "grounded": grounded},
        },
        "source_output": source,
        "solved_placement_matrix": [
            1.0, 0.0, 0.0, position[0],
            0.0, 1.0, 0.0, position[1],
            0.0, 0.0, 1.0, position[2],
            0.0, 0.0, 0.0, 1.0,
        ],
    }


def _service(root):
    class _Service:
        def active_workbench_name(self) -> str:
            return "PartWorkbench"

        def modeling_engine(self) -> str:
            return "xscript"

        def _active_document(self):
            return SimpleNamespace(Name="Ephemeral", Uid="doc", Objects=[])

        def project_scope_snapshot(self):
            return {"root": str(root)}

    return _Service()


def _store(tmp_path, report: dict):
    root = tmp_path / "project.cadex"
    staging = root / "script_artifacts" / REVISION[:16] / "attempt-1"
    staging.mkdir(parents=True)
    (staging / "result.json").write_text(json.dumps(report), encoding="utf-8")
    CadexProjectScriptStore(root).write(
        source="result = {}",
        state_updates={
            "accepted_revision": REVISION,
            "accepted_digest": DIGEST,
            "accepted_attempt": {
                "attempt_id": "1",
                "staging": staging.relative_to(root).as_posix(),
                "revision": REVISION,
            },
        },
    )
    return root


def _inventory(root, **arguments):
    captured = capture_inspection(_service(root), {"scope": "inventory", **arguments})
    assert captured["kind"] == "inventory"
    return complete_inspection(captured)


# --------------------------------------------------------------------------
# the stamp
# --------------------------------------------------------------------------


def test_a_library_body_is_stamped_with_its_catalog_row() -> None:
    body = _solid("fuse", [1.0, 2.0])
    LibraryPart("bolt", "m3x12-socket", body, {"nominal_dia_mm": 3.0})
    plain = _solid("box", [40.0, 20.0, 4.0])

    outputs = [_part_output("m3", body), _part_output("plate", plain)]
    cadex_project_worker._stamp_catalog_identity(outputs)

    assert outputs[0]["catalog"] == {
        "family": "bolt",
        "part_number": "m3x12-socket",
    }
    # Absent rather than null, so the key is a positive signal.
    assert "catalog" not in outputs[1]


def test_the_stamp_stays_out_of_the_definition_the_digest_hashes() -> None:
    """The whole reason the identity is a side table (ADR-064)."""

    body = _solid("cut", [3.0])
    LibraryPart("nut", "m3-hex", body, {})
    item = _part_output("nut", body)
    before = cadex_project_worker._canonical_json(item["definition"])

    cadex_project_worker._stamp_catalog_identity([item])

    assert cadex_project_worker._canonical_json(item["definition"]) == before
    assert "catalog" not in item["definition"]


def test_the_side_table_records_family_and_part_number() -> None:
    body = _solid("cylinder", [2.5, 8.0])
    LibraryPart("washer", "m3", body, {})

    recorded = library_catalog_identity()
    key = cadex_project_worker._canonical_json(body.to_payload())
    assert recorded[key] == {"family": "washer", "part_number": "m3"}


# --------------------------------------------------------------------------
# the join
# --------------------------------------------------------------------------


def _project(tmp_path):
    bolt_body = _solid("fuse", [3.0, 12.0])
    LibraryPart("bolt", "m3x12-socket", bolt_body, {})
    second_body = _solid("fuse", [3.0, 16.0])
    LibraryPart("bolt", "m3x16-socket", second_body, {})
    plate = _solid("box", [40.0, 20.0, 4.0])

    outputs = [
        _part_output("plate", plate),
        _part_output("m3a", bolt_body),
        _part_output("m3b", second_body),
        _component_output("base", "plate", position=(0.0, 0.0, 0.0), grounded=True),
        _component_output("boltA", "m3a", position=(6.0, 0.0, 4.0)),
        _component_output("boltB", "m3b", position=(-6.0, 0.0, 4.0)),
        {
            "name": "asm",
            "type": "assembly",
            "domain": "assembly",
            "definition": {
                "domain": "assembly",
                "operation": "assembly",
                "output_type": "assembly",
                "arguments": [],
                "properties": {},
            },
        },
    ]
    cadex_project_worker._stamp_catalog_identity(outputs)
    return _store(tmp_path, {"ok": True, "digest": DIGEST, "outputs": outputs})


def test_the_inventory_summarises_the_accepted_assembly(tmp_path) -> None:
    result = _inventory(_project(tmp_path))

    assert result["ok"] is True
    value = result["value"]
    assert value["revision"] == REVISION
    assert value["assembly"] == "asm"
    assert value["component_count"] == 3
    # The component list outgrows the per-key preview budget, so the summary
    # hands back the pointer to page it — the ordinary `inspect` contract,
    # and what `cadex inventory` follows.
    assert value["components"]["inspect_path"] == "/components"
    assert value["components"]["item_count"] == 3


def test_the_inventory_lists_every_component_with_its_catalog_id(tmp_path) -> None:
    result = _inventory(_project(tmp_path), path="/components", limit=50)

    assert result["ok"] is True
    rows = result["value"]
    assert result["page"]["total"] == 3
    assert result["page"]["next_offset"] is None
    assert [row["component"] for row in rows] == ["base", "boltA", "boltB"]

    bolt = rows[1]
    assert bolt["source_output"] == "m3a"
    assert bolt["catalog"] == {"family": "bolt", "part_number": "m3x12-socket"}
    assert bolt["label"] == "boltA label"
    assert bolt["grounded"] is False
    assert bolt["placement"]["position_mm"] == [6.0, 0.0, 4.0]
    assert bolt["source_facts"]["volume_mm3"] == pytest.approx(84.823)
    # Short on purpose: the full measurement is one scope="output" away.
    assert "faces" not in bolt["source_facts"]

    assert rows[0]["grounded"] is True
    assert "catalog" not in rows[0]


def test_the_roll_up_counts_catalogued_parts_and_names_the_rest(tmp_path) -> None:
    value = _inventory(_project(tmp_path))["value"]

    assert value["catalog_counts"] == {
        "bolt/m3x12-socket": 1,
        "bolt/m3x16-socket": 1,
    }
    assert value["uncatalogued_sources"] == ["plate"]


def test_a_target_names_the_assembly_and_refuses_any_other(tmp_path) -> None:
    root = _project(tmp_path)

    assert _inventory(root, target="asm")["value"]["assembly"] == "asm"

    refusal = _inventory(root, target="nope")
    assert refusal["ok"] is False
    assert refusal["failure_code"] == "INSPECTION_FAILED"
    assert "no assembly output named 'nope'" in refusal["error"]
    assert "'asm'" in refusal["error"]


def test_a_project_with_no_accepted_revision_is_refused(tmp_path) -> None:
    root = tmp_path / "empty.cadex"
    CadexProjectScriptStore(root).write(source="result = {}", state_updates={})

    value = _inventory(root)["value"]
    assert value["ok"] is False
    assert "no accepted revision" in value["error"]


@pytest.mark.skipif(
    __import__("test_cadexd_lifecycle").FREECADCMD is None,
    reason="No FreeCADCmd binary available for the real-kernel inventory.",
)
def test_one_catalog_body_placed_twice_counts_two_instances(tmp_path) -> None:
    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    source = """
bolt = lib.bolt("M3", 12.0).body
first = assembly.component(bolt, grounded=True)
second = assembly.component(bolt)
asm = assembly.assembly([first, second])
diag = assembly.solve(asm)
result = {"bolt": bolt, "first": first, "second": second,
          "asm": asm, "diag": diag}
"""
    client = None
    try:
        client = _spawn_cadexd()
        assert client.request("open_project", {"project_root": str(tmp_path)})["ok"]
        written = client.request("write_script", {"source": source, "expected_revision": ""})
        assert written["ok"], written
        reply = client.request("inspect", {"scope": "inventory"})
        assert reply["ok"], reply
        value = reply["value"]
        assert value["component_count"] == 2
        assert value["catalog_counts"] == {"bolt/m3x12-socket": 2}
        # Component facts can exceed the preview budget; read leaf paths.
        names = set()
        for index in range(2):
            for field in ("component", "source_output", "catalog"):
                leaf = client.request("inspect", {
                    "scope": "inventory", "path": f"/components/{index}/{field}",
                })
                assert leaf["ok"], leaf
                if field == "component":
                    names.add(leaf["value"])
                elif field == "source_output":
                    assert leaf["value"] == "bolt"
                else:
                    assert leaf["value"] == {"family": "bolt", "part_number": "m3x12-socket"}
        assert names == {"first", "second"}
        assert value["uncatalogued_sources"] == []
        assert not {"catalog_generated", "catalog_calls_known", "unplaced_catalog"} & value.keys()
    finally:
        _stop(client)
