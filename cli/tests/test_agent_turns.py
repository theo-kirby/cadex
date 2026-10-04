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
