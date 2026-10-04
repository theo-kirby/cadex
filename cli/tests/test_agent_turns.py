# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""CLI agent turns listed as runs beside the Ouroboros runs (orun2 D3, ADR-519).

A turn has no store of its own (A3): it is the ``prompt`` row the CLI writes
to ``PROGRESS.md`` for every accepted turn, joined by its revision to the
trail in ``script_history/`` and to the owner's verdicts and the agent's
notes in ``comments.jsonl``. First the reader, with no engine, on files laid
out by hand; then real turns through a real engine and the real bridge,
with only the model faked, read back from the index page in Chromium.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from cadex_cli.__main__ import main
from cadex_cli.project_docs import append_progress_row, progress_rows
from cadex_cli.report import EXIT_OK
from cadex_cli.review_server import TURNS_SHOWN, agent_turns, serve_projects
from test_dashboard_writes import PLATE, fake_claude  # noqa: F401
from test_review_server import CLI_DIR, _get, _json, browser, needs_browser  # noqa: F401

REV_1 = "1" * 8 + "a" * 56
REV_2 = "2" * 8 + "b" * 56


def _digest(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


def _turned_project(root: Path) -> Path:
    """Two prompt turns, a params run between them, verdicts and notes."""

    root.mkdir(parents=True)
    (root / "script.json").write_text("{}")
    (root / "PROGRESS.md").write_text("# Progress\n\n| When (UTC) | Run | Revision | Digest | What | Numbers |\n"
                                      "|---|---|---|---|---|---|\n"
                                      "| 2026-10-01T10:00:00Z | prompt | 11111111 | d1d1d1d1 | prompt: a plate \\| "
                                      "with a slot → Built the plate. | mesh plate |\n"
                                      "| 2026-10-01T10:05:00Z | params | 11111111 | d1d1d1d1 | params width=40 | — |\n"
                                      "| 2026-10-01T11:00:00Z | prompt | 22222222 | d2d2d2d2 | prompt: thicker | mesh plate |\n"
                                      "| 2026-10-01T12:00:00Z | prompt | — | — | prompt: nothing landed | — |\n")
    (root / "script_history").mkdir()
    (root / "script_history" / "history.json").write_text(json.dumps({"entries": [
        {"ordinal": 1, "revision": REV_1, "saved_at": "x"}, {"ordinal": 2, "revision": REV_2, "saved_at": "y"}]}))
    lines = [
        {"kind": "note", "id": "n-1", "at": "2026-10-01T10:00:01Z", "type": "question",
         "text": "Round the slot?", "revision": REV_1},
        {"kind": "comment", "id": "c-1", "at": "2026-10-01T10:30:00Z", "text": "yes",
         "revision": REV_1, "reply_to": "n-1"},
        {"kind": "comment", "id": "c-2", "at": "2026-10-01T10:31:00Z", "text": "The owner accepted it.",
         "revision": REV_1, "verdict": "accepted"},
        {"kind": "note", "id": "n-2", "at": "2026-10-01T11:00:01Z", "type": "flag",
         "text": "look at the edge", "revision": REV_2},
        {"kind": "comment", "id": "c-3", "at": "2026-10-01T11:30:00Z", "text": "too thick",
         "revision": REV_2, "verdict": "rejected"},
    ]
    (root / "comments.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines) + "not json\n")
    return root


def test_a_turn_is_a_progress_row_joined_to_its_revision(tmp_path) -> None:
    root = _turned_project(tmp_path / "plate")
    before = _digest(root)
    assert [row["run"] for row in progress_rows(root)] == ["prompt", "params", "prompt", "prompt"]
    turns = agent_turns(root)
    assert [turn["prompt"] for turn in turns] == ["a plate | with a slot", "thicker", "nothing landed"]
    first, second, third = turns
    assert first["said"] == "Built the plate." and second["said"] == ""
    assert (first["revision"], first["ordinal"], first["digest"]) == (REV_1, 1, "d1d1d1d1")
    assert (second["revision"], second["ordinal"]) == (REV_2, 2)
    assert first["verdict"] == "accepted" and [v["verdict"] for v in first["verdicts"]] == ["accepted"]
    assert second["verdict"] == "rejected" and second["verdicts"][0]["text"] == "too thick"
    assert first["notes"] == [{"type": "question", "text": "Round the slot?", "answered": True}]
    assert second["notes"] == [{"type": "flag", "text": "look at the edge", "answered": False}]
    # A turn that left no revision joins nothing rather than everything.
    assert (third["revision"], third["ordinal"], third["verdict"], third["verdicts"], third["notes"]) == (
        "", None, None, [], [])
    # A project with no PROGRESS.md has no turns, and reading wrote nothing.
    assert agent_turns(tmp_path / "missing") == []
    assert _digest(root) == before


def test_api_turns_lists_every_projects_turns_newest_first(tmp_path) -> None:
    projects = tmp_path / "projects"
    plate = _turned_project(projects / "plate")
    other = projects / "arm"
    other.mkdir()
    (other / "script.json").write_text("{}")
    append_progress_row(other, run="prompt", what="prompt: an arm", revision=REV_1, digest="e" * 64)
    (projects / "notes").mkdir()  # not a project: no script.json
    before = _digest(projects)
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        listing = _json(server.url + "api/turns")
        assert listing["schema"] == "cadex-agent-turns-v1" and listing["count"] == 4
        turns = listing["turns"]
        assert [(turn["project"], turn["prompt"]) for turn in turns] == [
            ("arm", "an arm"), ("plate", "nothing landed"), ("plate", "thicker"), ("plate", "a plate | with a slot")]
        assert turns[0]["url"] == "/p/arm/" and turns[0]["verdict"] is None
        # arm's revision shares REV_1's prefix but not its trail or comments.
        assert turns[0]["ordinal"] is None and turns[0]["notes"] == []
        # Bounded: past TURNS_SHOWN the newest are kept and the count says so.
        for index in range(TURNS_SHOWN):
            append_progress_row(other, run="prompt", what=f"prompt: arm {index}")
        listing = _json(server.url + "api/turns")
        assert listing["count"] == TURNS_SHOWN + 4 and len(listing["turns"]) == TURNS_SHOWN
        assert listing["turns"][0]["prompt"] == f"arm {TURNS_SHOWN - 1}"
    finally:
        server.shutdown()
        server.server_close()
    assert _digest(plate) == {key.split("/", 1)[1]: value for key, value in before.items()
                              if key.startswith("plate/")}


THICK = PLATE.replace("p.thickness)", "p.thickness * 2.0)")


@needs_browser
def test_browser_lists_real_cli_turns_beside_the_runs_with_their_verdicts(
        engine, tmp_path, capsys, monkeypatch, fake_claude, browser) -> None:
    """Two turns typed at a terminal, through a real engine and the real
    bridge with only the model faked; the owner accepts the first and
    rejects the second; the index lists both, newest first, with the
    revision each left and the verdict on it, and the agent's note."""

    # The fake ``claude`` is a child of this process: it imports the bridge.
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(
        filter(None, [str(CLI_DIR), os.environ.get("PYTHONPATH", "")])))
    projects = tmp_path / "projects"
    root = projects / "plate"
    source = tmp_path / "plate.py"
    source.write_text(PLATE, encoding="utf-8")
    assert main(["script", "--set", str(source), "--project", str(root), "--json"]) == EXIT_OK
    capsys.readouterr()
    script, seen, _gate = fake_claude
    wide = PLATE.replace("num(30.0,", "num(64.0,")
    script.write_text(json.dumps([["tool", "write_script", {"source": wide}],
                                  ["done", "Done: the plate is 64 mm wide."]]), encoding="utf-8")
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        page = browser.page(server.url)
        page.wait_for("document.getElementById('turns-empty').hidden === false", timeout=30)
        assert page.evaluate("document.querySelectorAll('#turns li').length") == 0

        assert main(["-p", "make the plate 64 mm wide", "--project", str(root), "--json"]) == EXIT_OK
        one = json.loads(capsys.readouterr().out)
        assert one["ok"] is True and seen.read_text(encoding="utf-8") == "make the plate 64 mm wide"
        assert main(["revision", "accept", "--project", str(root), "--json"]) == EXIT_OK
        capsys.readouterr()
        script.write_text(json.dumps([
            ["tool", "write_script", {"source": THICK}],
            ["tool", "leave_note", {"type": "question", "text": "Is 12 mm too thick?"}],
            ["done", "Done: doubled the thickness."]]), encoding="utf-8")
        assert main(["-p", "make it thicker", "--project", str(root), "--json"]) == EXIT_OK
        two = json.loads(capsys.readouterr().out)
        assert two["ok"] is True and two["accepted_revision"] != one["accepted_revision"]
        assert main(["revision", "reject", "--project", str(root), "--note", "too thick", "--json"]) == EXIT_OK
        capsys.readouterr()

        # The open index picks them up on its own poll; nothing was clicked.
        page.wait_for("document.querySelectorAll('#turns li').length === 2", timeout=30)
        rows = page.evaluate("Array.from(document.querySelectorAll('#turns li')).map(function (li) {"
                             " return {project: li.dataset.project, revision: li.dataset.revision,"
                             " verdict: li.dataset.verdict, text: li.textContent,"
                             " href: li.querySelector('a').getAttribute('href')}; })")
        newest, oldest = rows
        assert newest["revision"] == two["accepted_revision"] and newest["verdict"] == "rejected"
        assert oldest["revision"] == one["accepted_revision"] and oldest["verdict"] == "accepted"
        assert "make it thicker" in newest["text"] and "Done: doubled the thickness." in newest["text"]
        assert "1 note(s) for the owner, 1 unanswered" in newest["text"]
        assert "make the plate 64 mm wide" in oldest["text"] and "(#2)" in oldest["text"]
        assert newest["project"] == oldest["project"] == "plate" and newest["href"] == "/p/plate/"
        assert page.text("#turns li[data-verdict='rejected'] .turn-verdict") == "rejected"
        # Beside the Ouroboros runs, in the same card, and the link opens the project.
        assert page.evaluate("document.getElementById('turns').closest('section')"
                             " === document.getElementById('runs').closest('section')")
        assert _get(server.url + "p/plate/")[0] == 200
        # The reject and its restore were runs, not turns: only prompt rows list.
        progress = (root / "PROGRESS.md").read_text(encoding="utf-8")
        assert "revision reject" in progress and len(_json(server.url + "api/turns")["turns"]) == 2
    finally:
        server.shutdown()
        server.server_close()
