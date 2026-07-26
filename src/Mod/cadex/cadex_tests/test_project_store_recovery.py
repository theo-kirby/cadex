# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project store must survive a script the engine refused (ADR-044).

``prepare_project_candidate`` writes the candidate source to ``script.py``
before running it, and ``open_project``'s restore pass re-runs a stored
source at every open. Together those two facts turned one refused edit into
a project that could never be opened again — including by the ``write_script``
its own failure report recommended. These tests pin the three properties
that make that impossible: a refused candidate leaves no trace in the working
state, the restore pass reads the accepted revision's source rather than the
working file, and a script's ``print()`` reaches the caller when the run
*succeeds*, so nothing has to fail on purpose to be observed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from CadexScriptedRuntime import (
    accept_project_candidate,
    prepare_project_candidate,
    record_project_candidate_failure,
)
from CadexScriptedDomains import PROJECT_PACK
from CadexScriptStore import CadexProjectScriptStore

GOOD_SOURCE = 'result = {"plate": part.box(1.0, 1.0, 1.0)}\n'
REFUSED_SOURCE = 'raise_me = {}["nope"]\nresult = {"plate": part.box(1.0, 1.0, 1.0)}\n'


def _captured(root: Path, home: Path, source: str, revision: str) -> dict[str, Any]:
    """One ``capture_project_state`` result, without a live FreeCAD service."""

    return {
        "tool_name": "xscript.project.write_script",
        "operation": "write_script",
        "arguments": {"source": source, "expected_revision": revision},
        "pack": PROJECT_PACK,
        "project_root": str(root),
        "project_id": "test",
        "document_name": "CadexdEphemeral",
        "document_uid": "uid",
        "document_revision": "0",
        "document_objects": [],
        "freecad_home": str(home),
        "timeout_seconds": 30.0,
        "memory_limit_bytes": 512 * 1024 * 1024,
    }


@pytest.fixture()
def freecad_home(tmp_path: Path) -> Path:
    """A tree with a FreeCADCmd in it; staging never executes it here."""

    home = tmp_path / "freecad"
    (home / "bin").mkdir(parents=True)
    (home / "bin" / "FreeCADCmd").write_text("#!/bin/sh\n", encoding="utf-8")
    return home


def _prepare(root: Path, home: Path, source: str) -> dict[str, Any]:
    store = CadexProjectScriptStore(root)
    expected = str(store.read_state().get("working_revision") or "")
    return prepare_project_candidate(_captured(root, home, source, expected))


def test_a_refused_candidate_leaves_no_trace_in_the_working_script(
    tmp_path: Path, freecad_home: Path
) -> None:
    """The bug, stated directly: a failed run must not keep the file.

    The restore pass runs whatever ``script.py`` holds. A source that raises
    would therefore fail every future open, and no tool could get in to fix
    it, because every tool opens the project first.
    """

    root = tmp_path / "project.cadex"
    store = CadexProjectScriptStore(root)

    _prepare(root, freecad_home, GOOD_SOURCE)
    assert store.read_source() == GOOD_SOURCE
    good_revision = str(store.read_state()["working_revision"])
    store.write(state_updates={"accepted_revision": good_revision,
                               "accepted_digest": "digest-of-the-good-one"})

    refused = _prepare(root, freecad_home, REFUSED_SOURCE)
    # Mid-flight the candidate *is* the working artifact: a host that dies
    # here still has the source that was running.
    assert store.read_source() == REFUSED_SOURCE

    record_project_candidate_failure(
        refused, {"failure_code": "DOMAIN_CANDIDATE_FAILED", "error": "KeyError"}
    )

    state = store.read_state()
    assert store.read_source() == GOOD_SOURCE
    assert state["working_revision"] == good_revision
    assert state["accepted_revision"] == good_revision
    assert state["latest_candidate"]["status"] == "failed"
    assert state["latest_candidate"]["revision"] == refused["revision"]

    # Rolling back loses nothing: the refused source is still on disk, where
    # `latest_candidate` says it is.
    attempt = Path(str(refused["staging"])) / "request.json"
    assert json.loads(attempt.read_text(encoding="utf-8"))["source"] == REFUSED_SOURCE


def test_a_refused_first_script_leaves_the_project_empty(
    tmp_path: Path, freecad_home: Path
) -> None:
    """The same rule with nothing to roll back to."""

    root = tmp_path / "project.cadex"
    store = CadexProjectScriptStore(root)

    refused = _prepare(root, freecad_home, REFUSED_SOURCE)
    record_project_candidate_failure(refused, {"failure_code": "X", "error": "y"})

    assert store.read_source() == ""
    assert store.read_state()["working_revision"] == ""


def test_a_refused_candidate_does_not_keep_its_parameter_values(
    tmp_path: Path, freecad_home: Path
) -> None:
    """``set_params`` writes values before the run proves them, too."""

    root = tmp_path / "project.cadex"
    store = CadexProjectScriptStore(root)
    _prepare(root, freecad_home, GOOD_SOURCE)
    store.write(state_updates={"param_values": {"w": 1.0}})

    captured = _captured(
        root, freecad_home, GOOD_SOURCE,
        str(store.read_state()["working_revision"]),
    )
    captured["tool_name"] = "xscript.project.set_params"
    captured["operation"] = "set_params"
    captured["arguments"] = {
        "values": {"w": 5.0},
        "expected_revision": str(store.read_state()["working_revision"]),
    }
    store.write(state_updates={"param_specs": [
        {"name": "w", "type": "num", "default": 1.0, "min": 0.0, "max": 10.0}]})
    prepared = prepare_project_candidate(captured)
    assert store.read_state()["param_values"] == {"w": 5.0}

    record_project_candidate_failure(prepared, {"failure_code": "X", "error": "y"})
    assert store.read_state()["param_values"] == {"w": 1.0}


def test_the_restore_pass_reads_the_accepted_revisions_source(
    tmp_path: Path, freecad_home: Path
) -> None:
    """``read_accepted_source`` is what ``open_project`` re-runs.

    Re-running the working file could only ever fail when the two disagree —
    the accepted digest was produced by the accepted source, by definition.
    """

    root = tmp_path / "project.cadex"
    store = CadexProjectScriptStore(root)
    prepared = _prepare(root, freecad_home, GOOD_SOURCE)
    accept_project_candidate(
        prepared,
        {"live_outputs": {}, "removed": []},
        {"digest": "d", "contract": [{"name": "plate", "domain": "part",
                                      "type": "solid"}],
         "stdout": ""},
    )

    # However `script.py` came to hold something else — a pre-ADR-044 engine,
    # a hand edit, a half-written file — the accepted source is unaffected.
    store.write(source="this is not the accepted script\n")
    assert store.read_accepted_source() == GOOD_SOURCE


def test_read_accepted_source_is_empty_when_no_attempt_is_pinned(
    tmp_path: Path,
) -> None:
    """Projects accepted before the attempt was pinned fall back, not crash."""

    store = CadexProjectScriptStore(tmp_path / "project.cadex")
    assert store.read_accepted_source() == ""
    store.write(source=GOOD_SOURCE, state_updates={"accepted_digest": "d"})
    assert store.read_accepted_source() == ""


def test_a_mismatched_restore_does_not_redefine_the_accepted_model(
    tmp_path: Path, freecad_home: Path
) -> None:
    """A restore that fails its digest check must leave the store alone.

    The restore pass runs through ``write_script``, which *accepts* what it
    builds. So the run that proves the model is also the run that could
    silently replace it: open a hand-edited project once and it is reported
    as corrupt, open it a second time and the edit has become the accepted
    revision. This pins the rollback, engine-side, without a live cadexd.
    """

    root = tmp_path / "project.cadex"
    store = CadexProjectScriptStore(root)
    good = _prepare(root, freecad_home, GOOD_SOURCE)
    accept_project_candidate(
        good,
        {"live_outputs": {}, "removed": []},
        {"digest": "accepted-digest", "contract": [], "stdout": ""},
    )
    before = store.read_state()

    # The hand edit runs fine and builds something else, so the lifecycle
    # accepts it; only the digest comparison catches it.
    edited = _prepare(root, freecad_home, 'result = {"plate": part.box(2, 2, 2)}\n')
    accept_project_candidate(
        edited,
        {"live_outputs": {}, "removed": []},
        {"digest": "a-different-digest", "contract": [], "stdout": ""},
    )
    assert store.read_state()["accepted_digest"] == "a-different-digest"

    # What cadexd does on the mismatch branch.
    store.write(state_updates={
        "accepted_revision": before["accepted_revision"],
        "accepted_contract": before["accepted_contract"],
        "accepted_digest": before["accepted_digest"],
        "accepted_attempt": before["accepted_attempt"],
    })

    after = store.read_state()
    assert after["accepted_digest"] == "accepted-digest"
    assert after["accepted_revision"] == before["accepted_revision"]
    assert after["accepted_attempt"] == before["accepted_attempt"]
    # And the accepted source is still the one that made that digest.
    assert store.read_accepted_source() == GOOD_SOURCE


def test_an_accepted_run_reports_the_scripts_stdout(
    tmp_path: Path, freecad_home: Path
) -> None:
    """``print()`` has to work on the path where the script *worked*.

    When it only survived on the failure envelope, the cheapest way to read a
    value out of a working script was to make it fail on purpose — which is
    exactly what bricked a project.
    """

    root = tmp_path / "project.cadex"
    prepared = _prepare(root, freecad_home, GOOD_SOURCE)
    payload = accept_project_candidate(
        prepared,
        {"live_outputs": {}, "removed": []},
        {"digest": "d", "contract": [], "stdout": "peg_y 16.44\n"},
    )
    assert payload["stdout"] == "peg_y 16.44\n"


def test_the_modeling_response_contract_carries_stdout() -> None:
    """A key the shell reads is a key the protocol pins (ADR-025)."""

    from CadexdProtocol import OP_RESPONSE_SPECS, validate_response

    for op in ("write_script", "edit_script", "set_params", "rebuild"):
        required, optional = OP_RESPONSE_SPECS[op]
        assert "stdout" in required | optional, op

    frame = {
        "id": "x", "ok": True, "tool": "t", "revision": "r",
        "accepted_revision": "r", "digest": "d", "outputs": [],
        "live_outputs": {}, "removed": [], "stdout": "printed",
        "model_state": {"status": "accepted", "accepted_is_current": True,
                        "next_write_expected_revision": "r",
                        "verification_goal": "g"},
    }
    assert not validate_response("write_script", frame)
