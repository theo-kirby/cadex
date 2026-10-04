# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The project's engine budgets (ADR-517).

Stored in ``agent.json`` by ``cadex budgets --set``, sent as
``open_project``'s ``budgets`` by every run, overridden for one call by
``--engine-timeout`` / ``--engine-memory``, and shown read-only on the
dashboard. The engine fills an unset one from its own default, per field.
"""

from __future__ import annotations

import argparse
import json

import pytest

from cadex_cli.__main__ import _walk_common, main
from cadex_cli.client import open_project
from cadex_cli.report import EXIT_OK, EXIT_USAGE, RunReport, emit
from cadex_cli.review_server import ReviewProject, serve_projects
from cadex_cli.session import (
    budget_value,
    effective_budgets,
    read_agent_state,
    write_agent_budgets,
    write_agent_state,
)
from test_review_server import _json, _open, browser, needs_browser  # noqa: F401


# -- the stored values ---------------------------------------------------

def test_budgets_are_stored_beside_the_conversation_and_survive_it(tmp_path) -> None:
    write_agent_state(tmp_path, session_id="s-1", model="sonnet")
    state = write_agent_budgets(tmp_path, {"timeout_seconds": "900", "memory_limit_mb": 8192})
    assert state.budgets == {"timeout_seconds": 900.0, "memory_limit_mb": 8192}
    assert (state.session_id, state.model) == ("s-1", "sonnet")
    on_disk = json.loads((tmp_path / "agent.json").read_text())
    assert on_disk["budgets"] == {"timeout_seconds": 900.0, "memory_limit_mb": 8192}
    # A later turn rewrites the conversation identity and keeps the budgets.
    write_agent_state(tmp_path, session_id="s-2", model="sonnet")
    assert read_agent_state(tmp_path).budgets == {"timeout_seconds": 900.0, "memory_limit_mb": 8192}
    # 0 unsets one; the other stays.
    assert write_agent_budgets(tmp_path, {"timeout_seconds": 0}).budgets == {"memory_limit_mb": 8192}
    assert read_agent_state(tmp_path).session_id == "s-2"


@pytest.mark.parametrize("key,value", [
    ("timeout_seconds", -1), ("timeout_seconds", 3601), ("timeout_seconds", "soon"),
    ("timeout_seconds", float("nan")), ("memory_limit_mb", 1.5), ("memory_limit_mb", 131073),
    ("cpu_seconds", 10),
])
def test_a_budget_out_of_range_is_refused_with_its_bound(key, value) -> None:
    with pytest.raises(ValueError):
        budget_value(key, value)


def test_a_hand_edited_file_with_nonsense_budgets_reads_as_unset(tmp_path) -> None:
    (tmp_path / "agent.json").write_text(json.dumps({
        "schema": "cadex-cli-agent-v1", "session_id": "s",
        "budgets": {"timeout_seconds": -5, "memory_limit_mb": True, "extra": 1}}))
    state = read_agent_state(tmp_path)
    assert state.budgets == {} and state.session_id == "s"
    (tmp_path / "agent.json").write_text(json.dumps({
        "schema": "cadex-cli-agent-v1", "budgets": {"timeout_seconds": 120, "memory_limit_mb": 4096}}))
    assert read_agent_state(tmp_path).budgets == {"timeout_seconds": 120.0, "memory_limit_mb": 4096}


def test_an_override_wins_per_field_and_an_unset_one_does_not() -> None:
    stored = {"timeout_seconds": 900.0, "memory_limit_mb": 8192}
    assert effective_budgets(stored, {"timeout_seconds": 60.0}) == {
        "timeout_seconds": 60.0, "memory_limit_mb": 8192}
    assert effective_budgets(stored, {"memory_limit_mb": 0}) == stored
    assert effective_budgets({}, {"memory_limit_mb": 2048}) == {"memory_limit_mb": 2048}
    with pytest.raises(ValueError):
        effective_budgets(stored, {"timeout_seconds": 99999.0})


class _Recorder:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def request(self, op, args):
        self.sent.append(dict(args))
        return {"ok": True, "budgets": {"timeout_seconds": 300.0, "memory_limit_mb": 6144}}


def test_open_project_sends_only_the_budgets_it_has(tmp_path) -> None:
    client = _Recorder()
    open_project(client, tmp_path)
    open_project(client, tmp_path, budgets={"timeout_seconds": 900.0})
    assert "budgets" not in client.sent[0]
    assert client.sent[1]["budgets"] == {"timeout_seconds": 900.0}


def test_a_walk_hands_its_overrides_to_every_leg() -> None:
    args = argparse.Namespace(project="p", engine="", wait=False, engine_timeout=600.0, engine_memory=4096)
    assert _walk_common(args) == ["--project", "p", "--engine-timeout", "600.0", "--engine-memory", "4096"]
    plain = argparse.Namespace(project="p", engine="", wait=False, engine_timeout=0.0, engine_memory=0)
    assert _walk_common(plain) == ["--project", "p"]


# -- `cadex budgets` -----------------------------------------------------

def test_cadex_budgets_stores_reports_and_unsets_with_no_engine(tmp_path, capsys) -> None:
    root = tmp_path / "p"
    root.mkdir()
    assert main(["budgets", "--project", str(root), "--set", "timeout_seconds=900",
                 "--set", "memory_limit_mb=8192", "--json"]) == EXIT_OK
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is True
    assert envelope["budgets"] == {"stored": {"timeout_seconds": 900.0, "memory_limit_mb": 8192}}
    assert main(["budgets", "--project", str(root), "--json"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["budgets"]["stored"]["timeout_seconds"] == 900.0
    assert main(["budgets", "--project", str(root), "--set", "memory_limit_mb=0"]) == EXIT_OK
    assert "budgets timeout_seconds 900" in capsys.readouterr().out
    assert read_agent_state(root).budgets == {"timeout_seconds": 900.0}
    # A store, not a run: no PROGRESS.md row, no project repository.
    assert not (root / "PROGRESS.md").exists() and not (root / ".git").exists()


@pytest.mark.parametrize("assignment", ["timeout_seconds", "timeout_seconds=-3", "memory_limit_mb=0.5",
                                        "wall=10"])
def test_cadex_budgets_refuses_a_bad_assignment_as_usage(tmp_path, capsys, assignment) -> None:
    assert main(["budgets", "--project", str(tmp_path), "--set", assignment]) == EXIT_USAGE
    assert "error:" in capsys.readouterr().out
    assert read_agent_state(tmp_path).budgets == {}


def test_a_bad_override_is_refused_before_an_engine_starts(tmp_path, capsys) -> None:
    code = main(["params", "--project", str(tmp_path), "--set", "w=1",
                 "--engine", str(tmp_path / "no-engine-here"), "--engine-timeout", "-1"])
    # The engine root is checked first and does not exist; with a real
    # engine the override is the refusal. Either way, nothing is stored.
    assert code != EXIT_OK
    assert read_agent_state(tmp_path).budgets == {}
    capsys.readouterr()


def test_the_human_summary_names_budgets_only_when_they_are_not_the_engines(capsys) -> None:
    report = RunReport(ok=True, budgets={"in_force": {"timeout_seconds": 300.0, "memory_limit_mb": 6144},
                                         "stored": {}, "source": {"timeout_seconds": "engine",
                                                                  "memory_limit_mb": "engine"}})
    emit(report, as_json=False)
    assert "budgets" not in capsys.readouterr().out
    report.budgets["source"]["timeout_seconds"] = "override"
    emit(report, as_json=False)
    assert "budgets memory_limit_mb 6144 (engine)  timeout_seconds 300 (override)" in capsys.readouterr().out


# -- against a real engine -----------------------------------------------

PLATE = """
p = params(width=num(30.0, unit="mm", min=10.0, max=90.0, step=1.0))
plate = part.box(p.width, 20.0, 6.0)
result = {"plate": plate}
"""


def _script(root, tmp_path, *extra: str) -> dict:
    source = tmp_path / "plate.py"
    source.write_text(PLATE, encoding="utf-8")
    assert main(["script", "--set", str(source), "--project", str(root), "--json", *extra]) == EXIT_OK
    return {}


def test_a_run_opens_with_the_stored_budgets_and_a_flag_overrides_one(engine, tmp_path, capsys) -> None:
    root = tmp_path / "orun2-budgets"
    _script(root, tmp_path)
    first = json.loads(capsys.readouterr().out)["budgets"]
    assert first["stored"] == {} and set(first["source"].values()) == {"engine"}
    defaults = first["in_force"]
    assert defaults["timeout_seconds"] > 0 and defaults["memory_limit_mb"] > 0

    assert main(["budgets", "--project", str(root), "--set", "timeout_seconds=901"]) == EXIT_OK
    capsys.readouterr()
    assert main(["params", "--project", str(root), "--set", "width=40", "--json"]) == EXIT_OK
    stored = json.loads(capsys.readouterr().out)["budgets"]
    # The engine took the stored timeout and filled the memory ceiling itself.
    assert stored["in_force"] == {"timeout_seconds": 901.0, "memory_limit_mb": defaults["memory_limit_mb"]}
    assert stored["source"] == {"timeout_seconds": "project", "memory_limit_mb": "engine"}

    assert main(["params", "--project", str(root), "--set", "width=50", "--engine-timeout", "77",
                 "--engine-memory", "5000", "--json"]) == EXIT_OK
    overridden = json.loads(capsys.readouterr().out)["budgets"]
    assert overridden["in_force"] == {"timeout_seconds": 77.0, "memory_limit_mb": 5000}
    assert overridden["source"] == {"timeout_seconds": "override", "memory_limit_mb": "override"}
    # An override is for one call: the store is unchanged.
    assert read_agent_state(root).budgets == {"timeout_seconds": 901.0}

    assert main(["params", "--project", str(root), "--set", "width=60", "--engine-timeout", "-1",
                 "--json"]) == EXIT_USAGE
    assert "timeout_seconds" in json.loads(capsys.readouterr().out)["error"]


@needs_browser
def test_the_dashboard_shows_the_stored_budgets_read_only(engine, tmp_path, capsys, browser) -> None:
    projects = tmp_path / "projects"
    root = projects / "orun2-budgets"
    _script(root, tmp_path)
    capsys.readouterr()
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url + "p/orun2-budgets/")
        page.wait_for("document.getElementById('view-budgets').textContent.length > 0", timeout=30)
        assert page.evaluate("document.getElementById('view-budgets').textContent") == \
            "engine defaults (none stored)"
        assert main(["budgets", "--project", str(root), "--set", "timeout_seconds=900"]) == EXIT_OK
        capsys.readouterr()
        assert _json(server.url + "p/orun2-budgets/api/project")["budgets"] == {
            "stored": {"timeout_seconds": 900.0}}
        page.wait_for("document.getElementById('view-budgets').textContent.indexOf('900 s') === 0",
                      timeout=30)
        assert page.evaluate("document.getElementById('view-budgets').textContent") == \
            "900 s · engine default for the other"
        # Shown, never edited: no control inside the row.
        assert page.evaluate("document.querySelectorAll('#view-budgets input, #view-budgets button').length") == 0
        assert ReviewProject(root).review()["budgets"]["stored"] == {"timeout_seconds": 900.0}
    finally:
        server.shutdown()
        server.server_close()
