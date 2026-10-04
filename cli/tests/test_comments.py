# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A person's comments reach the next turn (ADR-505, orun2 D2 item 3).

``cadex comment`` appends to the project's ``comments.jsonl``; the next
``cadex -p`` turn is given every comment not yet delivered, ahead of its
prompt, and marks them delivered once it has run, so the turn after does
not see them again. A failed turn delivers nothing. The browser half —
click a part, comment, start a turn, and the model saw it — is in
``test_dashboard_writes.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from cadex_cli.__main__ import command_prompt, main
from cadex_cli.comments import (
    COMMENT_LIMIT,
    COMMENTS_NAME,
    add_comment,
    mark_delivered,
    pending_comments,
    read_comments,
    with_comments,
)
from cadex_cli.project_docs import PROGRESS_NAME
from cadex_cli.report import EXIT_OK, EXIT_USAGE, RunReport

from mock_backend import turn_factory
from test_turn_loop import BRACKET, _args


def test_a_comment_is_appended_read_back_and_delivered_once(tmp_path) -> None:
    root = tmp_path / "project"
    assert read_comments(root) == [] and pending_comments(root) == []
    whole = add_comment(root, "  the plate looks thin  ")
    post = add_comment(root, "make this taller", part=" post ", revision="r" * 64)
    assert whole["text"] == "the plate looks thin" and whole["part"] == "" and whole["delivered"] == ""
    assert post["part"] == "post" and post["revision"] == "r" * 64
    assert [c["id"] for c in pending_comments(root)] == [whole["id"], post["id"]]
    assert read_comments(root) == [whole, post]
    # A torn or foreign line is skipped, not fatal.
    with (root / COMMENTS_NAME).open("a", encoding="utf-8") as handle:
        handle.write('{"kind": "comment", "id": 3}\n[1, 2]\n{not json\n')
    assert len(read_comments(root)) == 2
    at = mark_delivered(root, [whole], session_id="s-1")
    assert at and pending_comments(root) == [post]
    assert {c["id"]: c["delivered"] for c in read_comments(root)} == {whole["id"]: at, post["id"]: ""}
    assert mark_delivered(root, []) == ""
    lines = [json.loads(line) for line in (root / COMMENTS_NAME).read_text().splitlines()[:2]]
    assert [line["kind"] for line in lines] == ["comment", "comment"]
    for bad in ("", "   ", "x\x00y", "x" * (COMMENT_LIMIT + 1)):
        with pytest.raises(ValueError):
            add_comment(root, bad)
    for part in ("a\nb", "p" * 201):
        with pytest.raises(ValueError):
            add_comment(root, "ok", part=part)


def test_the_prompt_carries_the_comments_ahead_of_it() -> None:
    assert with_comments("make it wider", []) == "make it wider"
    prompt = with_comments("make it wider", [{"text": "too thin", "part": ""},
                                             {"text": "taller", "part": "post"}])
    assert prompt.endswith("\n\nmake it wider")
    assert "- (on the whole design) too thin\n- (on part post) taller" in prompt


def test_cadex_comment_writes_one_line_and_no_row_or_commit(tmp_path, capsys) -> None:
    root = tmp_path / "project"
    root.mkdir()
    code = main(["comment", "--project", str(root), "--json", "--part=post", "--", "--taller, please"])
    envelope = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK and envelope["ok"] is True
    [comment] = envelope["comments"]
    assert comment["text"] == "--taller, please" and comment["part"] == "post"
    assert comment["revision"] == "" and comment["delivered"] == ""
    assert read_comments(root) == [comment]
    # A comment is input to the next run, not a run: no row, no repository.
    assert not (root / PROGRESS_NAME).exists() and not (root / ".git").exists()
    assert main(["comment", "--project", str(root), "--json", "--", "  "]) == EXIT_USAGE
    assert main(["comment", "--project", str(tmp_path / "absent"), "--json", "--", "hi"]) == EXIT_USAGE
    capsys.readouterr()
    assert len(read_comments(root)) == 1


@pytest.mark.usefixtures("engine")
def test_the_next_turn_receives_pending_comments_and_only_once(tmp_path) -> None:
    root = Path(_args(tmp_path).project)
    script = [[("tool", "describe_api", {}), ("tool", "write_script", {"source": BRACKET}), ("done", "Built it.")]]
    first = turn_factory(script)
    assert command_prompt(_args(tmp_path), RunReport(), turn_factory=first) == EXIT_OK
    whole = add_comment(root, "the bracket looks thin")
    picked = add_comment(root, "round this edge", part="bracket")

    # A turn that fails delivers nothing: the comments wait for the next.
    failing = turn_factory([[("fail", "the model went away")]])
    command_prompt(_args(tmp_path, prompt="thicker"), RunReport(), turn_factory=failing)
    assert "the bracket looks thin" in failing.made[0].prompts[0]
    assert [c["id"] for c in pending_comments(root)] == [whole["id"], picked["id"]]

    second = turn_factory(script)
    report = RunReport()
    assert command_prompt(_args(tmp_path, prompt="thicker", resume=True), report, turn_factory=second) == EXIT_OK
    prompt = second.made[0].prompts[0]
    assert prompt == with_comments("thicker", [whole, picked])
    assert "(on part bracket) round this edge" in prompt
    assert pending_comments(root) == []
    assert [c["id"] for c in report.comments] == [whole["id"], picked["id"]]
    assert all(c["delivered"] for c in report.comments)
    assert "delivered 2 comment(s) from the owner." in report.notes

    third = turn_factory(script)
    assert command_prompt(_args(tmp_path, prompt="again"), RunReport(), turn_factory=third) == EXIT_OK
    assert third.made[0].prompts[0] == "again"


def test_the_dashboard_comment_is_the_cli_command(tmp_path, monkeypatch) -> None:
    """``POST api/comment`` spawns ``cadex comment``; a bad body spawns nothing."""

    import cadex_cli.review_server as review_server
    from cadex_cli.walk import Leg

    calls = []

    def fake_leg(name, argv, *, capture=True, timeout=0.0, on_stderr=None):
        calls.append((name, list(argv)))
        return Leg(name=name, argv=list(argv), code=EXIT_OK, seconds=0.2,
                   envelope={"ok": True, "comments": [{"id": "c-1", "text": argv[-1]}]})

    monkeypatch.setattr(review_server, "run_leg", fake_leg)
    root = tmp_path / "project"
    for bad in ({}, {"text": ""}, {"text": 3}, {"text": "x\x00"}, {"text": "ok", "part": 4},
                {"text": "ok", "part": "a\nb"}, {"text": "x" * (COMMENT_LIMIT + 1)}):
        assert review_server.write_comment(root, bad)[0] == 400, bad
    assert calls == []
    status, reply = review_server.write_comment(root, {"text": " --thin ", "part": "post"})
    assert status == 200 and reply["comment"] == {"id": "c-1", "text": "--thin"}
    assert calls == [("comment", ["comment", "--project", str(root), "--json", "--part=post", "--", "--thin"])]
    review_server.write_comment(root, {"text": "whole"})
    assert calls[-1][1] == ["comment", "--project", str(root), "--json", "--", "whole"]


def test_the_comment_command_runs_as_a_child(tmp_path) -> None:
    """The argv the server builds is one the real CLI accepts."""

    from cadex_cli.walk import run_leg

    root = tmp_path / "project"
    root.mkdir()
    leg = run_leg("comment", ["comment", "--project", str(root), "--json", "--part=post", "--", "--taller"])
    assert leg.code == EXIT_OK, leg.envelope
    assert leg.envelope["comments"][0]["text"] == "--taller"
    assert [c["part"] for c in read_comments(root)] == ["post"]
    assert not (root / ".git").exists()
