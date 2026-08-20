# SPDX-License-Identifier: LGPL-2.1-or-later

"""Printable parts: the marks, and the export that reads them (ADR-156).

Cadex could build an assembly and could not hand it to a slicer. The missing
step is small and it is not geometry — *which* outputs are parts you mean to
print, and where the STLs go — so this is the sixth stored spec/value pair
in ``script.json`` and it behaves like the five before it in every way that
was already load-bearing: the spec cache is flat JSON, the marks replace
wholesale, and drift is **pruned rather than refused** (ADR-039).

Two things are deliberately unlike them, and both are asserted here rather
than described:

- the specs are **not a declaration**. There is no ``printable(...)``
  script global; the roster is whatever ``brep``/``mesh`` outputs the last
  accepted run published. So a rebuild is what moves it.
- neither key touches ``project_script_revision``. A print mark changes no
  geometry, and a checkbox that costs a full rebuild is not a checkbox.

The export's own half is the *plan* — which files, under which names, and
what happens when they are already there — because that is where a refusal
has to be right. Turning a solid into triangles is exercised where a kernel
exists (``test_cadexd_lifecycle``, the shell gate); here the mesh maker is
replaced so the plan can be tested without one.
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
    declared_printables,
    effective_printables,
    prune_printable_rows,
    roster_from_outputs,
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
# the table's six invariants
# --------------------------------------------------------------------------


def test_the_spec_cache_is_json_and_flat() -> None:
    specs = roster_from_outputs(_outputs())
    encoded = json.loads(json.dumps(specs))
    assert encoded == {
        "outputs": [
            {"name": "bracket", "artifact_kind": "brep"},
            {"name": "arm", "artifact_kind": "brep"},
            {"name": "shell", "artifact_kind": "mesh"},
        ]
    }
    # Only the two things the export needs; an output record's other fields
    # are the run's business rather than the store's.
    assert all(set(entry) == {"name", "artifact_kind"}
               for entry in encoded["outputs"])
    assert set(EXPORTABLE_KINDS) == {"brep", "mesh"}


def test_only_outputs_with_a_surface_are_candidates() -> None:
    roster = declared_printables(roster_from_outputs(_outputs()))
    assert roster == {"bracket": "brep", "arm": "brep", "shell": "mesh"}
    assert "solve" not in roster


def test_a_row_may_not_smuggle_a_non_string() -> None:
    """A mark is a name. There is exactly one thing to say about an output
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


def test_marks_replace_wholesale() -> None:
    specs = roster_from_outputs(_outputs())
    assert effective_printables(specs, ["arm", "bracket"]) == ["arm", "bracket"]
    # ...and the empty list is a statement, not an absence: nothing ticked.
    assert effective_printables(specs, []) == []


def test_a_name_the_script_no_longer_publishes_is_pruned_not_raised_on() -> None:
    """ADR-039, on the silent half of the asymmetry. A script that stops
    publishing a part has changed its mind, not made an error, and a store
    that wedged on that is what ADR-039 was written about."""

    before = roster_from_outputs(_outputs())
    marks = effective_printables(before, ["bracket", "arm"])
    after = roster_from_outputs([_outputs()[0]])
    assert prune_printable_rows(marks, after) == ["bracket"]
    assert effective_printables(after, marks) == ["bracket"]


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
# the store, and what it costs
# --------------------------------------------------------------------------


def test_the_store_carries_the_pair_and_needs_no_migration(tmp_path) -> None:
    default = CadexProjectScriptStore.default_state()
    assert default["print_specs"] == {}
    assert default["print_values"] == []

    # A script.json written before ADR-156 loads unchanged, exactly as one
    # written before every other table's pair does.
    store = CadexProjectScriptStore(tmp_path)
    store.state_path.parent.mkdir(parents=True, exist_ok=True)
    legacy = {key: value for key, value in default.items()
              if not key.startswith("print_")}
    store.state_path.write_text(json.dumps(legacy), encoding="utf-8")
    state = store.read_state()
    assert state["print_specs"] == {}
    assert state["print_values"] == []


def test_a_print_mark_does_not_move_the_content_revision() -> None:
    """The whole reason this is not a sixth ``set_params`` table.

    ``project_script_revision`` takes the five declared tables and nothing
    else; if a mark ever reached it, ticking a checkbox would rebuild the
    project.
    """

    import inspect as _inspect

    from CadexScriptedDomains import project_script_revision

    parameters = set(_inspect.signature(project_script_revision).parameters)
    assert not any(name.startswith("print") for name in parameters)


# --------------------------------------------------------------------------
# set_printable
# --------------------------------------------------------------------------


class _Server:
    """A cadexd server with a project root and no document."""

    def __init__(self, root: Path) -> None:
        self.frames: list[dict] = []
        self.server = CadexdServer(self.frames.append)
        self.server._service = object()
        self.server._project_root = Path(root)
        self.store = CadexProjectScriptStore(root)

    def set_printable(self, names):
        return self.server._op_set_printable("r1", {"printable": list(names)})

    def export(self, **args):
        return self.server._op_export_printable("r1", dict(args))


def _project(tmp_path, *, marks=None, outputs=None):
    harness = _Server(tmp_path)
    harness.store.write(state_updates={
        "print_specs": roster_from_outputs(
            _outputs() if outputs is None else outputs),
        "print_values": list(marks or []),
    })
    return harness


def test_set_printable_replaces_the_whole_list(tmp_path) -> None:
    harness = _project(tmp_path, marks=["bracket"])
    payload = harness.set_printable(["arm", "shell"])
    assert payload["ok"] is True
    assert payload["printable"] == ["arm", "shell"]
    assert harness.store.read_state()["print_values"] == ["arm", "shell"]
    # The roster rides back with the flags on it: one round trip answers
    # "did it take" and "what else is there to tick".
    assert payload["outputs"] == [
        {"name": "bracket", "artifact_kind": "brep", "printable": False},
        {"name": "arm", "artifact_kind": "brep", "printable": True},
        {"name": "shell", "artifact_kind": "mesh", "printable": True},
    ]
    assert not protocol.validate_response(
        "set_printable", {"id": "r1", **payload})


def test_a_requested_unknown_name_is_refused(tmp_path) -> None:
    """The loud half of the asymmetry. Pruning is for drift the script
    caused; a caller naming a part that is not there is a caller with a
    stale roster, and it is told so with the roster attached."""

    harness = _project(tmp_path)
    payload = harness.set_printable(["bracket", "flange"])
    assert payload["ok"] is False
    assert payload["failure_code"] == "UNKNOWN_PRINTABLE_OUTPUT"
    assert "flange" in payload["error"]
    assert payload["observed"]["outputs"] == ["arm", "bracket", "shell"]
    # Nothing was written: a refused mark list leaves the old one alone.
    assert harness.store.read_state()["print_values"] == []


def test_a_malformed_mark_list_is_refused(tmp_path) -> None:
    harness = _project(tmp_path, marks=["bracket"])
    payload = harness.set_printable([{"name": "arm"}])
    assert payload["failure_code"] == "PRINTABLE_REJECTED"
    assert harness.store.read_state()["print_values"] == ["bracket"]


def test_set_printable_needs_an_open_project() -> None:
    server = CadexdServer(lambda _frame: None)
    payload = server._op_set_printable("r1", {"printable": []})
    assert payload["failure_code"] == "CADEXD_NOT_OPEN"


# --------------------------------------------------------------------------
# the inspect block
# --------------------------------------------------------------------------


def test_the_inspect_block_is_the_roster_plus_the_flags(tmp_path) -> None:
    _project(tmp_path, marks=["arm"])
    from CadexInspection import _complete_script

    block = _complete_script({"project_root": str(tmp_path)})["printable"]
    assert block == {
        "outputs": [
            {"name": "bracket", "artifact_kind": "brep", "printable": False},
            {"name": "arm", "artifact_kind": "brep", "printable": True},
            {"name": "shell", "artifact_kind": "mesh", "printable": False},
        ]
    }
    assert "printable" in protocol.NESTED_RESPONSE_SPECS["script"][0]


def test_a_stored_list_gone_bad_reads_as_nothing_ticked(tmp_path) -> None:
    """A read path may not take ``inspect`` down with it; the write path is
    where a malformed list is refused."""

    harness = _project(tmp_path)
    harness.store.write(state_updates={"print_values": [{"name": "arm"}, 7]})
    from CadexInspection import _complete_script

    block = _complete_script({"project_root": str(tmp_path)})["printable"]
    assert [entry["printable"] for entry in block["outputs"]] == [
        False, False, False]


# --------------------------------------------------------------------------
# export_printable
# --------------------------------------------------------------------------


class _FakeMesh:
    """Stands in for the kernel: the plan is what is under test here."""

    CountFacets = 12

    def __init__(self, name: str) -> None:
        self._name = name

    def write(self, Filename: str, Format: str = "") -> None:  # noqa: N803
        assert Format == "STL"
        Path(Filename).write_bytes(b"solid " + self._name.encode("ascii"))


def _accepted(tmp_path, *, marks, outputs=None):
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
        "print_specs": roster_from_outputs(items),
        "print_values": list(marks),
    })
    harness.server._printable_mesh = (
        lambda _staging, item, _kind, _deflection: _FakeMesh(str(item["name"]))
    )
    return harness


def test_export_refuses_before_the_first_accepted_revision(tmp_path) -> None:
    harness = _project(tmp_path, marks=["bracket"])
    payload = harness.export()
    assert payload["failure_code"] == "NO_ACCEPTED_REVISION"
    assert not (tmp_path / "print").exists()


def test_export_refuses_with_nothing_marked(tmp_path) -> None:
    harness = _accepted(tmp_path, marks=[])
    payload = harness.export()
    assert payload["failure_code"] == "NOTHING_MARKED_PRINTABLE"
    # The roster rides on the refusal, so a caller that asked too early is
    # told what it could have ticked.
    assert payload["observed"]["outputs"] == ["arm", "bracket", "shell"]
    assert not (tmp_path / "print").exists()


def test_export_writes_one_stl_per_marked_part(tmp_path) -> None:
    harness = _accepted(tmp_path, marks=["bracket", "shell"])
    payload = harness.export()
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


def test_a_second_export_refuses_and_names_the_files(tmp_path) -> None:
    """``link_part``'s arrangement: call it with nothing chosen and the
    *refusal* is what carries the list the dialog is built from."""

    harness = _accepted(tmp_path, marks=["bracket", "shell"])
    assert harness.export()["ok"] is True
    payload = harness.export()
    assert payload["failure_code"] == "PRINT_FILES_EXIST"
    assert payload["observed"]["existing"] == ["bracket.stl", "shell.stl"]
    assert "bracket.stl" in payload["error"]
    # And it refused before writing anything, so the folder is untouched.
    assert sorted(path.name for path in (tmp_path / "print").iterdir()) == [
        "bracket.stl", "shell.stl"]


def test_overwrite_replaces_and_keep_both_takes_002(tmp_path) -> None:
    harness = _accepted(tmp_path, marks=["bracket"])
    assert harness.export()["ok"] is True
    (tmp_path / "print/bracket.stl").write_bytes(b"stale")

    overwritten = harness.export(conflict="overwrite")
    assert overwritten["ok"] is True
    assert (tmp_path / "print/bracket.stl").read_bytes() != b"stale"
    assert [path.name for path in (tmp_path / "print").iterdir()] == [
        "bracket.stl"]

    kept = harness.export(conflict="keep_both")
    assert [item["file"] for item in kept["files"]] == ["bracket-002.stl"]
    assert sorted(path.name for path in (tmp_path / "print").iterdir()) == [
        "bracket-002.stl", "bracket.stl"]
    # ...and again, so "next free" is really next free rather than "-002".
    assert [item["file"] for item in
            harness.export(conflict="keep_both")["files"]] == [
        "bracket-003.stl"]


def test_an_unknown_conflict_is_refused(tmp_path) -> None:
    harness = _accepted(tmp_path, marks=["bracket"])
    payload = harness.export(conflict="rename")
    assert payload["failure_code"] == "PRINT_CONFLICT_INVALID"
    assert payload["allowed_values"] == ["overwrite", "keep_both"]


def test_a_mark_whose_artifact_is_gone_refuses_before_writing(tmp_path) -> None:
    harness = _accepted(tmp_path, marks=["bracket", "shell"])
    (tmp_path / "script_artifacts/abcdef01/attempt-000/outputs/output-000.brep"
     ).unlink()
    payload = harness.export()
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
    harness = _accepted(tmp_path, marks=["left arm", "left_arm"],
                        outputs=outputs)
    payload = harness.export()
    assert [item["file"] for item in payload["files"]] == [
        "left_arm.stl", "left_arm-002.stl"]
    assert [item["name"] for item in payload["files"]] == [
        "left arm", "left_arm"]


def test_export_needs_an_open_project() -> None:
    server = CadexdServer(lambda _frame: None)
    assert server._op_export_printable("r1", {})["failure_code"] == (
        "CADEXD_NOT_OPEN")
