# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A CLI turn's transcript and ``look`` images on the project page (ADR-526, orun2 C1 defect 3).

``cadex -p`` keeps each turn under the project's ``turns/<id>/``; the
dashboard reads that store and writes nothing (A3). First the store alone:
its bounds, its self-ignoring directory and its refusals. Then, against a
real engine in headless Chromium, a turn typed at a terminal -- not started
from the page -- whose transcript and ``look`` images the project page shows.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time

import cadex_cli.turn_store as turn_store
from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK, RunReport
from cadex_cli.turn_store import TurnRecorder, latest_turn, turn_file
from test_dashboard_read_only import PLATE, fake_claude, plate_app  # noqa: F401
from test_review_server import _get, _json, _open, _model_state, browser, needs_browser  # noqa: F401

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def test_the_store_is_bounded(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(turn_store, "TRANSCRIPT_LIMIT", 10)
    monkeypatch.setattr(turn_store, "LOOKS_PER_TURN", 1)
    monkeypatch.setattr(turn_store, "TURNS_KEPT", 2)
    recorder = TurnRecorder(tmp_path, "one")
    recorder.write("12345678")
    recorder.write("abcdef")
    recorder.write("never")
    assert (recorder.dir / "transcript.txt").read_text(encoding="utf-8") == \
        "12345678\n[transcript truncated at 10 characters]\n"
    recorder.look("iso", PNG)
    recorder.look("top", PNG)
    assert [look["name"] for look in recorder.record["looks"]] == ["look-01-iso.png"]
    assert recorder.record["looks_dropped"] == 1
    ids = [recorder.id]
    for prompt in ("two", "three"):
        time.sleep(1.01)  # ids sort by their UTC second
        ids.append(TurnRecorder(tmp_path, prompt).id)
    kept = sorted(child.name for child in (tmp_path / "turns").iterdir() if child.is_dir())
    assert kept == ids[1:]


def test_a_turn_whose_process_died_reads_interrupted(tmp_path) -> None:
    recorder = TurnRecorder(tmp_path, "killed")
    record = json.loads((recorder.dir / "turn.json").read_text(encoding="utf-8"))
    record["pid"] = 2 ** 22 + 12345  # above pid_max's default: no such process
    (recorder.dir / "turn.json").write_text(json.dumps(record), encoding="utf-8")
    assert latest_turn(tmp_path)["state"] == "interrupted"


def test_only_the_stores_own_images_are_served(tmp_path) -> None:
    recorder = TurnRecorder(tmp_path, "look")
    recorder.look("iso", PNG)
    assert turn_file(tmp_path, recorder.id, "look-01-iso.png") == (recorder.dir / "look-01-iso.png").resolve()
    (tmp_path / "secret.png").write_bytes(PNG)
    for turn_id, name in ((recorder.id, "transcript.txt"), (recorder.id, "turn.json"),
                          ("..", "secret.png"), (recorder.id, "../../secret.png"),
                          (recorder.id, "look-02-iso.png")):
        assert turn_file(tmp_path, turn_id, name) is None
    # ...and a link out of the project is refused even with the store's name.
    project = tmp_path / "project"
    project.mkdir()
    linked = TurnRecorder(project, "link")
    os.symlink(tmp_path / "secret.png", linked.dir / "look-01-iso.png")
    assert turn_file(project, linked.id, "look-01-iso.png") is None
