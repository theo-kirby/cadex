# SPDX-License-Identifier: LGPL-2.1-or-later

"""Printable parts: the roster, and the export that is told what to write.

ADR-156 built this as a stored table — a sixth spec/value pair in
``script.json`` and a ``set_printable`` op to write it. ADR-158 took the
store back out: a tick is a decision about a *view* of the model, not a
property of it, so the caller keeps its ticks and names them on the export
call. What is left in the engine is the half that has to be in the engine:

- the **roster**, derived from the accepted worker report rather than cached
  anywhere, which is what makes "what the panel may tick" and "what the
  export will accept" the same list by construction;
- the **refusal** — a requested name the accepted revision does not publish
  is told so, with the roster attached;
- and the **plan** — which files, under which names, and what happens when
  they are already there, because that is where a refusal has to be right.

Turning a solid into triangles is exercised where a kernel exists
(``test_cadexd_lifecycle``, the shell gate); here the mesh maker is replaced
so the plan can be tested without one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import CadexdProtocol as protocol
from CadexPrintables import (
    EXPORTABLE_KINDS,
    MAX_PRINTABLE,
    PrintableError,
    allocate_file_name,
    canonical_printable_rows,
    printable_roster,
    stl_file_name,
)
from CadexScriptStore import CadexProjectScriptStore
from cadexd import CadexdServer


def _outputs():
    return [
        {"name": "bracket", "domain": "part", "artifact_kind": "brep",
         "artifact_path": "outputs/output-000.brep"},
        {"name": "arm", "domain": "part", "artifact_kind": "brep",
         "artifact_path": "outputs/output-001.brep"},
        {"name": "shell", "domain": "mesh", "artifact_kind": "mesh",
         "artifact_path": "outputs/output-002.ply"},
        # No surface: a solver diagnostic is not a candidate at all.
        {"name": "solve", "domain": "assembly", "artifact_kind": ""},
    ]


# --------------------------------------------------------------------------
# the roster
# --------------------------------------------------------------------------


def test_only_outputs_with_a_surface_are_candidates() -> None:
    roster = printable_roster(_outputs())
    assert roster == {"bracket": "brep", "arm": "brep", "shell": "mesh"}
    assert "solve" not in roster
    assert set(EXPORTABLE_KINDS) == {"brep", "mesh"}
    # Report order, not sorted: the panel draws the parts in the order the
    # script published them, which is the order somebody wrote them in.
    assert list(roster) == ["bracket", "arm", "shell"]


def test_a_row_may_not_smuggle_a_non_string() -> None:
    """A name is a name. There is exactly one thing to say about an output
    here, and an object with one key in it would be a table pretending to a
    shape it does not have."""

    for bad in ([{"name": "bracket"}], [None], [3], ["bracket", b"arm"]):
        with pytest.raises(PrintableError):
            canonical_printable_rows(bad, what="printable")
    for bad in ("bracket", {"bracket": True}, 3):
        with pytest.raises(PrintableError):
            canonical_printable_rows(bad, what="printable")


def test_names_are_stripped_deduped_and_kept_in_order() -> None:
    rows = canonical_printable_rows(
        [" arm ", "bracket", "arm", "shell"], what="printable"
    )
    assert rows == ["arm", "bracket", "shell"]


def test_a_name_that_could_become_a_path_is_refused() -> None:
    for bad in ("../escape", "a/b", "a\\b", "bad\nname"):
        with pytest.raises(PrintableError):
            canonical_printable_rows([bad], what="printable")
    with pytest.raises(PrintableError):
        canonical_printable_rows([""], what="printable")
    with pytest.raises(PrintableError):
        canonical_printable_rows(["x" * 129], what="printable")
    with pytest.raises(PrintableError):
        canonical_printable_rows(["x"] * (MAX_PRINTABLE + 1), what="printable")


# --------------------------------------------------------------------------
# names on disk
# --------------------------------------------------------------------------


def test_an_output_name_becomes_a_slicer_friendly_file_name() -> None:
    assert stl_file_name("bracket") == "bracket.stl"
    assert stl_file_name("Left Arm") == "Left_Arm.stl"
    assert stl_file_name("../escape") == "escape.stl"
    assert stl_file_name("...") == "part.stl"


def test_keep_both_takes_the_next_free_ordinal() -> None:
    assert allocate_file_name("arm.stl", ()) == "arm.stl"
    assert allocate_file_name("arm.stl", {"arm.stl"}) == "arm-002.stl"
    assert allocate_file_name(
        "arm.stl", {"arm.stl", "arm-002.stl"}) == "arm-003.stl"


# --------------------------------------------------------------------------
# what the store does NOT carry (ADR-158)
# --------------------------------------------------------------------------


def test_the_store_carries_no_print_state_at_all() -> None:
    """The claim ADR-158 is: a tick is not project state.

    ``write`` refuses a field the default state does not declare, so this is
    also what stops anything writing a mark back into ``script.json`` by
    accident.
    """

    default = CadexProjectScriptStore.default_state()
    assert not [key for key in default if key.startswith("print")]


def test_a_store_written_under_adr_156_needs_no_migration(tmp_path) -> None:
    """The two dead keys are simply dropped; nothing reads them, nothing
    trips over them, and the next write leaves them out."""

    store = CadexProjectScriptStore(tmp_path)
    store.state_path.parent.mkdir(parents=True, exist_ok=True)
    legacy = dict(CadexProjectScriptStore.default_state())
    legacy["print_specs"] = {"outputs": [
        {"name": "bracket", "artifact_kind": "brep"}]}
    legacy["print_values"] = ["bracket"]
    store.state_path.write_text(json.dumps(legacy), encoding="utf-8")

    state = store.read_state()
    assert "print_specs" not in state and "print_values" not in state
    written = store.write(state_updates={"working_revision": "abcdef01"})
    assert not [key for key in written if key.startswith("print")]
    with pytest.raises(ValueError):
        store.write(state_updates={"print_values": ["bracket"]})


def test_a_print_mark_does_not_move_the_content_revision() -> None:
    """Unchanged from ADR-156, and now true for free: there is no mark in
    the store to keep out of ``project_script_revision``."""

    import inspect as _inspect

    from CadexScriptedDomains import project_script_revision

    parameters = set(_inspect.signature(project_script_revision).parameters)
    assert not any(name.startswith("print") for name in parameters)


# --------------------------------------------------------------------------
# the harness
# --------------------------------------------------------------------------


class _FakeMesh:
    """Stands in for the kernel: the plan is what is under test here."""

    CountFacets = 12

    def __init__(self, name: str) -> None:
        self._name = name

    def write(self, Filename: str, Format: str = "") -> None:  # noqa: N803
        assert Format == "STL"
        Path(Filename).write_bytes(b"solid " + self._name.encode("ascii"))


class _Server:
    """A cadexd server with a project root and no document."""

    def __init__(self, root: Path) -> None:
        self.frames: list[dict] = []
        self.server = CadexdServer(self.frames.append)
        self.server._service = object()
        self.server._project_root = Path(root)
        self.store = CadexProjectScriptStore(root)

    def export(self, names=(), **args):
        return self.server._op_export_printable(
            "r1", {"printable": list(names), **args})


def _accepted(tmp_path, *, outputs=None):
    """A project with an accepted revision whose artifacts are on disk."""

    items = _outputs() if outputs is None else outputs
    harness = _Server(tmp_path)
    staging = tmp_path / "script_artifacts/abcdef01/attempt-000"
    (staging / "outputs").mkdir(parents=True, exist_ok=True)
    for item in items:
        artifact = str(item.get("artifact_path") or "")
        if artifact:
            (staging / artifact).write_bytes(b"artifact")
    (staging / "result.json").write_text(
        json.dumps({"ok": True, "outputs": items}), encoding="utf-8")
    harness.store.write(state_updates={
        "accepted_revision": "abcdef01",
        "accepted_attempt": {
            "attempt_id": "attempt-000",
            "staging": "script_artifacts/abcdef01/attempt-000",
            "revision": "abcdef01",
        },
    })
    harness.server._printable_mesh = (
        lambda _staging, item, _kind, _deflection: _FakeMesh(str(item["name"]))
    )
    return harness


# --------------------------------------------------------------------------
# the inspect block
# --------------------------------------------------------------------------


def test_the_inspect_block_is_the_roster_and_only_the_roster(tmp_path) -> None:
    """No ``printable`` flag on an entry, because the engine does not know
    of one. What the panel draws a tick from is its own state (ADR-158)."""

    _accepted(tmp_path)
    from CadexInspection import _complete_script

    block = _complete_script({"project_root": str(tmp_path)})["printable"]
    assert block == {
        "outputs": [
            {"name": "bracket", "artifact_kind": "brep"},
            {"name": "arm", "artifact_kind": "brep"},
            {"name": "shell", "artifact_kind": "mesh"},
        ]
    }
    assert "printable" in protocol.NESTED_RESPONSE_SPECS["script"][0]


def test_a_project_with_nothing_accepted_reads_as_an_empty_roster(
    tmp_path,
) -> None:
    """A read path may not take ``inspect`` down with it — and this is the
    ordinary state of a project somebody has only just opened."""

    from CadexInspection import _complete_script

    CadexProjectScriptStore(tmp_path).write(state_updates={})
    block = _complete_script({"project_root": str(tmp_path)})["printable"]
    assert block == {"outputs": []}


def test_a_report_that_cannot_be_read_reads_as_an_empty_roster(
    tmp_path,
) -> None:
    harness = _accepted(tmp_path)
    (tmp_path / "script_artifacts/abcdef01/attempt-000/result.json").write_text(
        "{not json", encoding="utf-8")
    from CadexInspection import _complete_script

    block = _complete_script({"project_root": str(tmp_path)})["printable"]
    assert block == {"outputs": []}
    # ...and the export refuses rather than writing a partial job.
    assert harness.export(["bracket"])["failure_code"] == (
        "PRINT_ARTIFACT_MISSING")


# --------------------------------------------------------------------------
# export_printable
# --------------------------------------------------------------------------


def test_export_refuses_before_the_first_accepted_revision(tmp_path) -> None:
    harness = _Server(tmp_path)
    payload = harness.export(["bracket"])
    assert payload["failure_code"] == "NO_ACCEPTED_REVISION"
    assert not (tmp_path / "print").exists()


def test_export_refuses_with_nothing_named(tmp_path) -> None:
    harness = _accepted(tmp_path)
    payload = harness.export([])
    assert payload["failure_code"] == "NOTHING_MARKED_PRINTABLE"
    # The roster rides on the refusal, so a caller that asked too early is
    # told what it could have ticked.
    assert payload["observed"]["outputs"] == ["arm", "bracket", "shell"]
    assert not (tmp_path / "print").exists()


def test_a_requested_unknown_name_is_refused(tmp_path) -> None:
    """The loud half of ADR-039's asymmetry, and now the only half the
    engine has: a caller naming a part that is not there has a stale roster,
    and is told so with the current one attached."""

    harness = _accepted(tmp_path)
    payload = harness.export(["bracket", "flange"])
    assert payload["ok"] is False
    assert payload["failure_code"] == "UNKNOWN_PRINTABLE_OUTPUT"
    assert "flange" in payload["error"]
    assert payload["observed"]["outputs"] == ["arm", "bracket", "shell"]
    # An output with no surface is not in the roster either, so it is
    # refused by the same check rather than by one of its own.
    assert harness.export(["solve"])["failure_code"] == (
        "UNKNOWN_PRINTABLE_OUTPUT")
    assert not (tmp_path / "print").exists()


def test_a_malformed_name_list_is_refused(tmp_path) -> None:
    harness = _accepted(tmp_path)
    payload = harness.export([{"name": "arm"}])
    assert payload["failure_code"] == "PRINTABLE_REJECTED"
    assert payload["observed"]["outputs"] == ["arm", "bracket", "shell"]
    assert not (tmp_path / "print").exists()


def test_export_writes_one_stl_per_named_part(tmp_path) -> None:
    harness = _accepted(tmp_path)
    payload = harness.export(["bracket", "shell"])
    assert payload["ok"] is True
    assert payload["directory"] == "print"
    assert payload["revision"] == "abcdef01"
    assert [item["file"] for item in payload["files"]] == [
        "bracket.stl", "shell.stl"]
    assert [item["name"] for item in payload["files"]] == ["bracket", "shell"]
    assert all(item["bytes"] > 0 and item["triangles"] == 12
               for item in payload["files"])
    assert sorted(path.name for path in (tmp_path / "print").iterdir()) == [
        "bracket.stl", "shell.stl"]
    assert not protocol.validate_response(
        "export_printable", {"id": "r1", **payload})
    # Nothing was remembered: the job was the argument, and a project that
    # holds no marks holds none after a print either.
    state = harness.store.read_state()
    assert not [key for key in state if key.startswith("print")]


def test_a_second_export_refuses_and_names_the_files(tmp_path) -> None:
    """``link_part``'s arrangement: call it with nothing chosen and the
    *refusal* is what carries the list the dialog is built from."""

    harness = _accepted(tmp_path)
    assert harness.export(["bracket", "shell"])["ok"] is True
    payload = harness.export(["bracket", "shell"])
    assert payload["failure_code"] == "PRINT_FILES_EXIST"
    assert payload["observed"]["existing"] == ["bracket.stl", "shell.stl"]
    assert "bracket.stl" in payload["error"]
    # And it refused before writing anything, so the folder is untouched.
    assert sorted(path.name for path in (tmp_path / "print").iterdir()) == [
        "bracket.stl", "shell.stl"]


def test_overwrite_replaces_and_keep_both_takes_002(tmp_path) -> None:
    harness = _accepted(tmp_path)
    assert harness.export(["bracket"])["ok"] is True
    (tmp_path / "print/bracket.stl").write_bytes(b"stale")

    overwritten = harness.export(["bracket"], conflict="overwrite")
    assert overwritten["ok"] is True
    assert (tmp_path / "print/bracket.stl").read_bytes() != b"stale"
    assert [path.name for path in (tmp_path / "print").iterdir()] == [
        "bracket.stl"]

    kept = harness.export(["bracket"], conflict="keep_both")
    assert [item["file"] for item in kept["files"]] == ["bracket-002.stl"]
    assert sorted(path.name for path in (tmp_path / "print").iterdir()) == [
        "bracket-002.stl", "bracket.stl"]
    # ...and again, so "next free" is really next free rather than "-002".
    assert [item["file"] for item in
            harness.export(["bracket"], conflict="keep_both")["files"]] == [
        "bracket-003.stl"]


def test_an_unknown_conflict_is_refused(tmp_path) -> None:
    harness = _accepted(tmp_path)
    payload = harness.export(["bracket"], conflict="rename")
    assert payload["failure_code"] == "PRINT_CONFLICT_INVALID"
    assert payload["allowed_values"] == ["overwrite", "keep_both"]


def test_a_part_whose_artifact_is_gone_refuses_before_writing(tmp_path) -> None:
    harness = _accepted(tmp_path)
    (tmp_path / "script_artifacts/abcdef01/attempt-000/outputs/output-000.brep"
     ).unlink()
    payload = harness.export(["bracket", "shell"])
    assert payload["failure_code"] == "PRINT_ARTIFACT_MISSING"
    # Nothing was written: the whole job is resolved before any of it lands.
    assert not (tmp_path / "print").exists()


def test_two_names_that_sanitise_alike_do_not_collide(tmp_path) -> None:
    """An output name is nearly always already a filename, but it is not
    guaranteed to be one — and a run that quietly wrote one part over
    another would be the worst way to find that out."""

    outputs = [
        {"name": "left arm", "domain": "part", "artifact_kind": "brep",
         "artifact_path": "outputs/output-000.brep"},
        {"name": "left_arm", "domain": "part", "artifact_kind": "brep",
         "artifact_path": "outputs/output-001.brep"},
    ]
    harness = _accepted(tmp_path, outputs=outputs)
    payload = harness.export(["left arm", "left_arm"])
    assert [item["file"] for item in payload["files"]] == [
        "left_arm.stl", "left_arm-002.stl"]
    assert [item["name"] for item in payload["files"]] == [
        "left arm", "left_arm"]


def test_export_needs_an_open_project() -> None:
    server = CadexdServer(lambda _frame: None)
    payload = server._op_export_printable("r1", {"printable": ["bracket"]})
    assert payload["failure_code"] == "CADEXD_NOT_OPEN"


def test_the_op_takes_the_job_as_an_argument() -> None:
    """The protocol half of ADR-158: ``printable`` is required, and there is
    no op that stores one."""

    required, optional = protocol.OP_ARG_SPECS["export_printable"]
    assert required == {"printable": list}
    assert set(optional) == {"conflict", "deflection"}
    assert "set_printable" not in protocol.OP_ARG_SPECS
