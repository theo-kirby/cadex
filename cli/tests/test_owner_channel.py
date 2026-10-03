# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The agent reaches the owner without waiting (ADR-512, orun2 A1).

The agent's ``leave_note`` tool appends a note -- a flag on the accepted
revision or one project file, or a question -- to the project's
``comments.jsonl`` and returns at once. The dashboard lists the notes; the
owner answers with ``cadex comment --reply NOTE_ID``, and the answer reaches
the next turn the way every comment does, quoting the note it answers. The
browser half -- a turn leaves a question, the page shows it, the owner
answers there, and the next turn receives it -- is in
``test_dashboard_writes.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
import time

import pytest

from cadex_cli.__main__ import command_prompt, main
from cadex_cli.bridge import Bridge
from cadex_cli.comments import (
    add_comment,
    add_note,
    pending_comments,
    read_comments,
    read_notes,
    with_comments,
)
from cadex_cli.report import EXIT_OK, EXIT_USAGE, RunReport
from cadex_cli.tools import BRIDGE_TOOLS

from fake_cadexd import FakeCadexd
from mock_backend import turn_factory
from test_turn_loop import BRACKET, _args


def _payload(reply: dict) -> dict:
    return json.loads(reply["content"][0]["text"])


def test_a_note_is_appended_and_an_answer_is_a_comment_that_quotes_it(tmp_path) -> None:
    root = tmp_path / "project"
    (root / "out").mkdir(parents=True)
    (root / "out" / "hero.png").write_bytes(b"\x89PNG")
    flag = add_note(root, "flag", "  the horn sits proud of the shell  ", revision="r" * 64,
                    artifact="out/../out/hero.png")
    question = add_note(root, "question", "M2 or M3 screws? I went with M3.")
    assert flag["artifact"] == "out/hero.png" and flag["text"] == "the horn sits proud of the shell"
    assert flag["revision"] == "r" * 64 and flag["answers"] == [] and flag["id"].startswith("n-")
    assert read_notes(root) == [flag, question]
    # A note is not a comment: nothing reaches the next turn until the owner answers.
    assert read_comments(root) == [] and pending_comments(root) == []

    answer = add_comment(root, "M2, they are what I have", reply_to=question["id"])
    assert answer["reply_to"] == question["id"]
    [pending] = pending_comments(root)
    assert pending["answers"] == question["text"]
    assert "- (answering your note \"M2 or M3 screws? I went with M3.\") M2, they are what I have" \
        in with_comments("go on", [pending])
    notes = {note["id"]: note for note in read_notes(root)}
    assert notes[question["id"]]["answers"] == [{"id": answer["id"], "at": answer["at"], "text": answer["text"]}]
    assert notes[flag["id"]]["answers"] == []
    # A long note is quoted short.
    long = add_note(root, "question", "why " * 100)
    quoted = with_comments("p", [dict(add_comment(root, "because", reply_to=long["id"]), answers=long["text"])])
    assert "…\") because" in quoted and len(quoted) < 300

    with pytest.raises(ValueError, match="no agent note"):
        add_comment(root, "hi", reply_to="n-000000000000")
    for kind, text, artifact in (("flag", "", ""), ("note", "x", ""), ("question", "x\x00", ""),
                                 ("flag", "x", "/etc/passwd"), ("flag", "x", "../outside.png"),
                                 ("flag", "x", "out/absent.png"), ("flag", "x", "out")):
        with pytest.raises(ValueError):
            add_note(root, kind, text, artifact=artifact)
    assert len(read_notes(root)) == 3


def test_leave_note_returns_at_once_and_leaves_the_note(tmp_path) -> None:
    project = tmp_path / "project"
    (project / "out").mkdir(parents=True)
    (project / "out" / "hero.png").write_bytes(b"\x89PNG")
    with Bridge(FakeCadexd(), project_root=project) as bridge:
        started = time.monotonic()
        reply = bridge.call("leave_note", {"type": "question", "text": "Wheel or track? I chose wheels."})
        assert time.monotonic() - started < 1.0
        assert reply["is_error"] is False, reply
        said = _payload(reply)
        assert said["ok"] is True and said["type"] == "question" and "do not wait" in said["delivery"]
        flagged = _payload(bridge.call("leave_note", {"type": "flag", "text": "look at the hero",
                                                        "artifact": "out/hero.png"}))
        assert flagged["artifact"] == "out/hero.png"
        assert [(n["id"], n["type"]) for n in read_notes(project)] == [
            (said["id"], "question"), (flagged["id"], "flag")]
        assert bridge.state.calls[-1].summary == f"flag {flagged['id']} on out/hero.png"
        for arguments, error in (({"type": "flag"}, "non-empty text"),
                                 ({"type": "ping", "text": "x"}, "type is one of"),
                                 ({"type": "flag", "text": "x", "wait_s": 60}, "leave_note takes"),
                                 ({"type": "flag", "text": "x", "artifact": "../x.png"}, "no file")):
            refused = bridge.call("leave_note", arguments)
            assert refused["is_error"] is True and error in _payload(refused)["error"], arguments
        assert len(read_notes(project)) == 2
    with Bridge(FakeCadexd()) as bridge:
        refused = bridge.call("leave_note", {"type": "flag", "text": "x"})
        assert refused["is_error"] is True and "needs a project directory" in _payload(refused)["error"]


def test_the_tool_asks_for_nothing_that_could_wait() -> None:
    schema = BRIDGE_TOOLS["leave_note"]["input_schema"]
    assert set(schema["properties"]) == {"type", "text", "artifact"}
    assert schema["required"] == ["type", "text"] and schema["additionalProperties"] is False
    assert schema["properties"]["type"]["enum"] == ["flag", "question"]
    assert "WITHOUT WAITING" in BRIDGE_TOOLS["leave_note"]["description"]


def test_cadex_comment_reply_answers_a_note(tmp_path, capsys) -> None:
    root = tmp_path / "project"
    root.mkdir()
    note = add_note(root, "question", "Is 40 mm tall enough?")
    code = main(["comment", "--project", str(root), "--json", "--reply=" + note["id"], "--", "make it 50"])
    envelope = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK and envelope["comments"][0]["reply_to"] == note["id"]
    assert read_notes(root)[0]["answers"][0]["text"] == "make it 50"
    assert main(["comment", "--project", str(root), "--json", "--reply=n-ffffffffffff", "--", "x"]) == EXIT_USAGE
    capsys.readouterr()


def test_the_dashboard_answer_is_the_cli_command(tmp_path, monkeypatch) -> None:
    import cadex_cli.review_server as review_server
    from cadex_cli.walk import Leg

    calls = []
    monkeypatch.setattr(review_server, "run_leg", lambda name, argv, **_: calls.append(list(argv)) or Leg(
        name=name, argv=list(argv), code=EXIT_OK, seconds=0.1, envelope={"ok": True, "comments": [{"id": "c-1"}]}))
    root = tmp_path / "project"
    for bad in ({"text": "x", "reply_to": 3}, {"text": "x", "reply_to": "--part=x"},
                {"text": "x", "reply_to": "n-../../etc"}):
        assert review_server.write_comment(root, bad)[0] == 400, bad
    assert calls == []
    status, _reply = review_server.write_comment(root, {"text": "yes", "reply_to": "n-0123456789ab"})
    assert status == 200
    assert calls == [["comment", "--project", str(root), "--json", "--reply=n-0123456789ab", "--", "yes"]]


def test_the_project_review_lists_notes_and_serves_what_they_flag(tmp_path) -> None:
    from cadex_cli.review_server import ReviewProject

    root = tmp_path / "project"
    (root / "out").mkdir(parents=True)
    (root / "out" / "hero.png").write_bytes(b"\x89PNG")
    (root / "secret.key").write_text("k")
    shown = add_note(root, "flag", "look", artifact="out/hero.png")
    unshown = add_note(root, "flag", "not a served type", artifact="secret.key")
    plain = add_note(root, "question", "which?")
    project = ReviewProject(root)
    notes = {note["id"]: note for note in project.review()["notes"]}
    assert notes[shown["id"]]["url"] == f"note/{shown['id']}"
    assert notes[unshown["id"]]["url"] == "" and notes[plain["id"]]["url"] == ""
    assert project.note_artifact(shown["id"]) == (root / "out" / "hero.png").resolve()
    assert project.note_artifact(unshown["id"]) is None and project.note_artifact("n-000000000000") is None
    (root / "out" / "hero.png").unlink()
    assert project.note_artifact(shown["id"]) is None


@pytest.mark.usefixtures("engine")
def test_a_question_from_one_turn_is_answered_into_the_next(tmp_path) -> None:
    root = Path(_args(tmp_path).project)
    first = turn_factory([[("tool", "describe_api", {}), ("tool", "write_script", {"source": BRACKET}),
                           ("tool", "leave_note", {"type": "question",
                                                     "text": "Countersunk or plain holes? I went plain."}),
                           ("done", "Built it, plain holes.")]])
    report = RunReport()
    assert command_prompt(_args(tmp_path), report, turn_factory=first) == EXIT_OK
    [note] = read_notes(root)
    assert note["type"] == "question" and note["revision"] == report.accepted_revision
    assert pending_comments(root) == []

    add_comment(root, "countersunk, please", reply_to=note["id"])
    second = turn_factory([[("tool", "describe_api", {}), ("tool", "write_script", {"source": BRACKET}),
                            ("done", "Noted.")]])
    assert command_prompt(_args(tmp_path, prompt="go on", resume=True), RunReport(),
                          turn_factory=second) == EXIT_OK
    prompt = second.made[0].prompts[0]
    assert "(answering your note \"Countersunk or plain holes? I went plain.\") countersunk, please" in prompt
    assert prompt.endswith("\n\ngo on") and pending_comments(root) == []
