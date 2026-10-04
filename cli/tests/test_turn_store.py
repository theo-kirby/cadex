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
from cadex_cli.review_server import turn_snapshot
from cadex_cli.turn_store import TurnRecorder, latest_turn, turn_file
from test_dashboard_writes import PLATE, fake_claude, plate_app  # noqa: F401
from test_review_server import _get, _open, _model_state, browser, needs_browser  # noqa: F401

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def test_a_turn_keeps_its_transcript_and_looks_and_says_how_it_ended(tmp_path) -> None:
    import sys

    recorder = TurnRecorder(tmp_path, "make it wider", attachments=[{"name": "sketch.png"}], resume=True)
    stored = latest_turn(tmp_path)
    assert stored["state"] == "running" and stored["prompt"] == "make it wider" and stored["resume"] is True
    with recorder.capture():
        sys.stderr.write(" · write_script  accepted\n")
    recorder.look("iso", PNG)
    recorder.look("Top!", PNG)
    report = RunReport(ok=True, accepted_revision="a" * 64, notes=["delivered 1 comment(s) from the owner."])
    recorder.finish(report, EXIT_OK)
    stored = latest_turn(tmp_path)
    assert stored["state"] == "done"
    assert stored["reply"]["ok"] is True and stored["reply"]["exit"] == EXIT_OK
    assert stored["reply"]["accepted_revision"] == "a" * 64
    assert stored["reply"]["notes"] == ["delivered 1 comment(s) from the owner."]
    assert [look["name"] for look in stored["looks"]] == ["look-01-iso.png", "look-02-top.png"]
    snapshot = turn_snapshot(tmp_path, None)
    assert snapshot["source"] == "store" and snapshot["text"] == " · write_script  accepted\n"
    assert [look["url"] for look in snapshot["looks"]] == [f"turn/{recorder.id}/look-01-iso.png",
                                                           f"turn/{recorder.id}/look-02-top.png"]
    assert turn_snapshot(tmp_path, None, since=len(snapshot["text"]))["text"] == ""
    # The directory ignores itself in the project's own repository.
    assert (tmp_path / "turns" / ".gitignore").read_text(encoding="utf-8").splitlines()[-1] == "*"


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


@needs_browser
def test_browser_shows_a_terminal_turns_transcript_and_looks(plate_app, fake_claude, browser, capsys,
                                                             monkeypatch) -> None:
    root, server = plate_app
    # The fake claude imports the bridge client, as a dashboard child's would.
    cli_dir = str(Path(turn_store.__file__).resolve().parents[1])
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [cli_dir, os.environ.get("PYTHONPATH")])))
    script, _seen, _gate = fake_claude
    wider = PLATE.replace("num(30.0,", "num(52.0,")
    script.write_text(json.dumps([
        ["text", "Widening the plate to 52 mm, then looking at it.\n"],
        ["tool", "write_script", {"source": wider}],
        ["tool", "look", {"views": ["iso", "top"]}],
        ["text", "It reads as a flat plate.\n"],
        ["done", "It reads as a flat plate."],
    ]), encoding="utf-8")
    # Typed at a terminal: the dashboard did not start this turn.
    assert main(["--project", str(root), "--prompt=make the plate 52 mm wide", "--json"]) == EXIT_OK
    capsys.readouterr()
    stored = latest_turn(root)
    assert stored["state"] == "done" and [look["view"] for look in stored["looks"]] == ["iso", "top"]
    for look in stored["looks"]:
        assert (root / "turns" / stored["id"] / look["name"]).read_bytes()[:4] == b"\x89PNG"
    # The project's repository did not take the log in.
    tracked = subprocess.run(["git", "-C", str(root), "ls-files", "turns"],
                             capture_output=True, text=True, check=True).stdout
    assert tracked == ""

    page = _open(browser, server.url + "p/plate/")
    assert _model_state(page) == "loaded"
    page.wait_for("window.cadexReview.turn().state === 'done' && window.cadexReview.turn().text.length > 0", timeout=30)
    turn = page.evaluate("window.cadexReview.turn()")
    assert turn["source"] == "store" and turn["reply"]["ok"] is True
    assert "Widening the plate to 52 mm" in page.text("#turn-transcript")
    assert "· write_script" in page.text("#turn-transcript") and "· look  iso, top" in page.text("#turn-transcript")
    assert page.evaluate("document.getElementById('turn-transcript').hidden") is False
    assert turn["reply"]["accepted_revision"][:12] in page.text("#turn-status")
    # Both pictures the model saw are on the page, decoded.
    page.wait_for("Array.prototype.every.call(document.querySelectorAll('#turn-looks img'), "
                  "function (img) { return img.complete && img.naturalWidth > 0; }) && "
                  "document.querySelectorAll('#turn-looks img').length === 2", timeout=30)
    assert page.evaluate("document.getElementById('turn-looks').hidden") is False
    assert page.evaluate("Array.prototype.map.call(document.querySelectorAll('#turn-looks img'), "
                         "function (img) { return img.alt; })") == ["look: iso", "look: top"]
    status, _headers, body = _get(server.url + "p/plate/" + turn["looks"][0]["url"])
    assert status == 200 and body[:4] == b"\x89PNG"
    assert _get(server.url + f"p/plate/turn/{stored['id']}/transcript.txt")[0] == 404
