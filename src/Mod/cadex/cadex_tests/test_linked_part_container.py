# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ``.cxpart`` container: what it carries, and what it refuses (ADR-138).

Everything here runs with no FreeCAD, no worker and no built engine, because
that is the claim the feature rests on: building a linked part is reading
files out of the source project's pinned accepted attempt. A fixture project
here is therefore the real thing — a real ``CadexProjectScriptStore``, a real
``accepted_attempt`` locator, a real staging directory — assembled by hand
rather than by running a script.

What this file does **not** prove is that a container imports: that needs
OCCT and a live project, and lives in ``test_linked_part_live.py`` (the
ADR-135 lesson — unit tests that never touch the real store pass while the
feature is unusable).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from CadexLinkedPart import (
    LINKED_PART_MAGIC,
    LINKED_PART_SCHEMA,
    MAXIMUM_CXPART_BYTES,
    LinkedPartError,
    build_linked_part,
    decode_linked_part,
    encode_linked_part,
    read_linked_part,
    source_outputs,
)
from CadexScriptStore import CadexProjectScriptStore

BREP = b"DBRep_DrawableShape\n\nCASCADE Topology V1, (c) Matra-Datavision\n"
SOURCE = 'p = params(bore=num(5, unit="mm"))\nresult = {"sensor": part.box(10, 10, p.bore)}\n'


def _project(
    root: Path,
    *,
    contract=(("sensor", "solid", "part"),),
    artifact_kind: str = "brep",
    shape_type: str = "Solid",
    accepted: bool = True,
    brep: bytes = BREP,
    staging_present: bool = True,
) -> Path:
    """A source project with one accepted revision, built by hand.

    The shape of the store is the contract this feature reads, so it is
    written out here in full rather than mocked: ``accepted_attempt.staging``
    is a project-relative path, the worker report is ``result.json`` beside
    the ``outputs/`` it names, and ``request.json`` is what carries the
    accepted source.
    """

    staging = root / "script_artifacts" / "abc123" / "attempt-1"
    if staging_present:
        (staging / "outputs").mkdir(parents=True)
        (staging / "outputs" / "output-000.brep").write_bytes(brep)
        (staging / "request.json").write_text(
            json.dumps({"source": SOURCE}), encoding="utf-8"
        )
        (staging / "result.json").write_text(
            json.dumps(
                {
                    "ok": True,
                    "outputs": [
                        {
                            "name": name,
                            "artifact_kind": artifact_kind,
                            "artifact_path": "outputs/output-000.brep",
                            "domain": domain,
                            "facts": {"shape_type": shape_type},
                        }
                        for name, _type, domain in contract
                    ],
                }
            ),
            encoding="utf-8",
        )
    store = CadexProjectScriptStore(root)
    store.write(
        source=SOURCE,
        state_updates={
            "accepted_revision": "abc123" if accepted else "",
            "accepted_digest": "d1g357",
            "accepted_contract": [
                {"name": name, "type": kind, "domain": domain}
                for name, kind, domain in contract
            ],
            "accepted_attempt": {
                "attempt_id": "attempt-1",
                "staging": "script_artifacts/abc123/attempt-1",
                "revision": "abc123",
            },
            "param_specs": [{"name": "bore", "type": "num", "default": 5.0}],
            "param_values": {"bore": 5.0},
        },
    )
    return root


def test_a_built_container_carries_the_solid_and_its_provenance(tmp_path) -> None:
    root = _project(tmp_path / "sensorA.cadex")
    blob = build_linked_part(root, "sensor")

    assert blob.startswith(LINKED_PART_MAGIC)
    header, brep = decode_linked_part(blob)
    assert brep == BREP, "the container must carry the exact accepted BREP bytes"
    assert header["schema"] == LINKED_PART_SCHEMA
    assert header["source"]["output"] == "sensor"
    assert header["source"]["revision"] == "abc123"
    assert header["source"]["digest"] == "d1g357"
    assert header["source"]["output_type"] == "solid"
    assert header["source"]["project_title"] == "sensorA"
    assert header["shape_sha256"] == hashlib.sha256(BREP).hexdigest()
    assert header["brep_bytes"] == len(BREP)


def test_the_script_and_params_travel_with_the_solid(tmp_path) -> None:
    """Carried and not yet read, on purpose (ADR-138).

    Nothing in slice 1 consumes these three fields. They are what a parameter
    override needs — ``part.import_part("s.cxpart", bore=6)`` — and what
    makes a linked part rebuildable rather than baked, and recording them now
    costs bytes where adding them later would cost a container version. The
    test exists so the absence of a reader never reads as an oversight.
    """

    header, _brep = decode_linked_part(build_linked_part(_project(tmp_path / "a.cadex"), "sensor"))

    assert header["script"] == SOURCE
    assert header["params"] == {"bore": 5.0}
    assert header["param_specs"] == [{"name": "bore", "type": "num", "default": 5.0}]


def test_the_container_is_byte_deterministic(tmp_path) -> None:
    """Two pulls of one accepted revision are the same file.

    Load-bearing rather than tidy: a linked part's bytes are what the
    consuming project's BREP digest is computed from, so a container that
    varied by when it was written would move B's digest on every refresh that
    changed nothing.
    """

    root = _project(tmp_path / "a.cadex")
    assert build_linked_part(root, "sensor") == build_linked_part(root, "sensor")


def test_a_container_round_trips_through_a_file(tmp_path) -> None:
    root = _project(tmp_path / "a.cadex")
    path = tmp_path / "sensor.cxpart"
    path.write_bytes(build_linked_part(root, "sensor"))

    header, brep = read_linked_part(path)
    assert brep == BREP
    assert header["source"]["output"] == "sensor"


def test_a_container_still_reads_with_the_source_project_gone(tmp_path) -> None:
    """``project_root`` is a hint for refresh, never a load-bearing path.

    Same standing as ``mesh_cadex_source_root`` (ADR-046): a linked part is
    fully usable with A deleted, off another machine, out of a directory that
    never existed here. Only refresh needs the path.
    """

    import shutil

    root = _project(tmp_path / "a.cadex")
    path = tmp_path / "sensor.cxpart"
    path.write_bytes(build_linked_part(root, "sensor"))
    shutil.rmtree(root)

    header, brep = read_linked_part(path)
    assert brep == BREP
    assert header["source"]["project_root"].endswith("a.cadex")


def test_a_project_with_no_accepted_revision_is_refused_by_name(tmp_path) -> None:
    root = _project(tmp_path / "a.cadex", accepted=False)
    with pytest.raises(LinkedPartError) as caught:
        build_linked_part(root, "sensor")
    assert "no accepted revision" in str(caught.value)
    assert str(root) in str(caught.value)


def test_an_unknown_output_lists_what_the_project_declares(tmp_path) -> None:
    root = _project(
        tmp_path / "a.cadex",
        contract=(("sensor", "solid", "part"), ("mount", "solid", "part")),
    )
    with pytest.raises(LinkedPartError) as caught:
        build_linked_part(root, "housing")
    assert "is not an output of" in str(caught.value)
    assert "sensor, mount" in str(caught.value)
    # The candidate list is what lets the shell offer a choice rather than
    # making the user guess the name.
    assert caught.value.candidates == ["sensor", "mount"]


def test_a_non_brep_output_is_refused_as_not_a_solid(tmp_path) -> None:
    root = _project(
        tmp_path / "a.cadex",
        contract=(("hull", "mesh", "mesh"),),
        artifact_kind="mesh",
        shape_type="",
    )
    with pytest.raises(LinkedPartError) as caught:
        build_linked_part(root, "hull")
    assert "is a mesh output, not a solid" in str(caught.value)


def test_a_brep_output_that_is_not_a_solid_is_refused(tmp_path) -> None:
    root = _project(
        tmp_path / "a.cadex",
        contract=(("skin", "shell", "part"),),
        shape_type="Shell",
    )
    with pytest.raises(LinkedPartError) as caught:
        build_linked_part(root, "skin")
    assert "is a Shell output, not a solid" in str(caught.value)


def test_a_missing_accepted_attempt_says_to_re_accept(tmp_path) -> None:
    root = _project(tmp_path / "a.cadex", staging_present=False)
    with pytest.raises(LinkedPartError) as caught:
        build_linked_part(root, "sensor")
    assert "no locatable accepted attempt" in str(caught.value)
    assert "re-accepted once" in str(caught.value)


def test_an_oversized_solid_names_the_limit(tmp_path) -> None:
    root = _project(tmp_path / "a.cadex", brep=b"x" * (MAXIMUM_CXPART_BYTES + 1))
    with pytest.raises(LinkedPartError) as caught:
        build_linked_part(root, "sensor")
    assert "the limit for one linked part is 64 MB" in str(caught.value)


def test_a_file_that_is_not_a_container_is_refused_before_it_is_parsed(tmp_path) -> None:
    path = tmp_path / "sensor.cxpart"
    path.write_bytes(b"solid tetra\nfacet normal 0 0 -1\n")
    with pytest.raises(LinkedPartError) as caught:
        read_linked_part(path)
    assert "magic line" in str(caught.value)


def test_a_modified_container_fails_its_own_digest(tmp_path) -> None:
    """The authentication ``configure_part_references`` performs, one step further.

    A host-staged reference crossed a process boundary; a linked part crossed
    a project, a filesystem and possibly a machine, so the header's
    ``shape_sha256`` is checked before anything is built from the bytes.
    """

    root = _project(tmp_path / "a.cadex")
    blob = build_linked_part(root, "sensor")
    tampered = blob[:-4] + b"XXXX"
    with pytest.raises(LinkedPartError) as caught:
        decode_linked_part(tampered)
    assert "does not match its own header" in str(caught.value)


@pytest.mark.parametrize(
    "blob",
    [
        LINKED_PART_MAGIC,
        LINKED_PART_MAGIC + (1024).to_bytes(8, "little") + b"{}",
        LINKED_PART_MAGIC + (2).to_bytes(8, "little") + b"[]" + BREP,
        LINKED_PART_MAGIC + (2).to_bytes(8, "little") + b"{}" + BREP,
    ],
    ids=["no-length", "header-not-there", "header-not-an-object", "wrong-schema"],
)
def test_every_declared_length_is_checked_against_the_bytes_present(blob) -> None:
    with pytest.raises(LinkedPartError):
        decode_linked_part(blob)


def test_a_container_with_no_brep_is_refused(tmp_path) -> None:
    header = {"schema": LINKED_PART_SCHEMA, "shape_sha256": ""}
    with pytest.raises(LinkedPartError) as caught:
        decode_linked_part(encode_linked_part(header, b""))
    assert "no BREP bytes" in str(caught.value)


def test_source_outputs_answers_what_a_project_declares(tmp_path) -> None:
    root = _project(
        tmp_path / "a.cadex",
        contract=(("sensor", "solid", "part"), ("hull", "mesh", "mesh")),
    )
    assert source_outputs(root) == [
        {"name": "sensor", "type": "solid", "domain": "part"},
        {"name": "hull", "type": "mesh", "domain": "mesh"},
    ]


def test_the_store_accepts_a_cxpart_and_lists_it(tmp_path) -> None:
    """Widening the union is the whole of what reaching the store takes.

    ``_ASSET_SUFFIXES`` stays exactly three members — the shell mirrors that
    set by name — and ``.cxpart`` joins the union beside ``.cxpolicy`` and
    the provenance pair, which is what ADR-084 and ADR-135 each cost.
    """

    from CadexScriptedRuntime import (
        _ASSET_SUFFIXES,
        _STORED_ASSET_SUFFIXES,
        list_project_assets,
        store_project_asset,
    )

    assert _ASSET_SUFFIXES == frozenset({".stl", ".obj", ".ply"})
    assert ".cxpart" in _STORED_ASSET_SUFFIXES

    root = _project(tmp_path / "a.cadex")
    blob = build_linked_part(root, "sensor")
    incoming = tmp_path / "pulled.cxpart"
    incoming.write_bytes(blob)

    consumer = tmp_path / "b.cadex"
    consumer.mkdir()
    stored = store_project_asset(consumer, str(incoming), "sensor.cxpart")
    assert stored["name"] == "sensor.cxpart"
    assert stored["bytes"] == len(blob)
    assert stored["sha256"] == hashlib.sha256(blob).hexdigest()
    assert [item["name"] for item in list_project_assets(consumer)] == ["sensor.cxpart"]

    # Overwriting an existing name is allowed: that is re-import, and it is
    # exactly what refresh does.
    again = store_project_asset(consumer, str(incoming), "sensor.cxpart")
    assert again == stored


def test_the_store_refusal_enumerates_the_cxpart(tmp_path) -> None:
    from CadexScriptedRuntime import store_project_asset

    rejected = tmp_path / "notes.txt"
    rejected.write_text("x", encoding="utf-8")
    consumer = tmp_path / "b.cadex"
    consumer.mkdir()
    with pytest.raises(ValueError) as caught:
        store_project_asset(consumer, str(rejected))
    assert ".cxpart" in str(caught.value)
    assert "part.import_part" in str(caught.value)
