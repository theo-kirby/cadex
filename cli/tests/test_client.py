# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The client, against a real ``cadexd``. Skipped when no engine is built.

Everything here is a third client exercising the same contract the shell
and the engine's own harnesses do. The point is not to re-test the engine —
``cadex_tests`` does that — but to prove that *this* client speaks the
protocol correctly: the ready banner, one request at a time, events kept
aside, replies checked against ``OP_RESPONSE_SPECS``, and a project root
that need not exist.
"""

from __future__ import annotations

import pytest

from cadex_cli.client import CadexdClient, CadexdError, open_project
from cadex_cli.session import ProjectBusy, project_lock

PLATE = """
p = params(width=num(30.0, unit="mm", min=10.0, max=90.0, step=1.0))
plate = part.box(p.width, 20.0, 6.0)
result = {"plate": plate}
"""


@pytest.fixture
def client(engine):
    running = CadexdClient(engine)
    running.start()
    try:
        yield running
    finally:
        running.shutdown()


def test_a_project_root_that_does_not_exist_is_created(client, tmp_path) -> None:
    """``cadex -p ... --project ./new`` is one command, not two."""

    root = tmp_path / "not" / "yet" / "here"
    assert not root.exists()

    opened = open_project(client, root)

    assert opened["ok"] is True
    assert opened["script"]["script_present"] is False
    assert root.is_dir()


def test_a_write_is_guarded_and_the_reply_carries_the_next_guard(
    client, tmp_path
) -> None:
    open_project(client, tmp_path / "project")

    written = client.request(
        "write_script", {"source": PLATE, "expected_revision": ""}
    )

    assert written["ok"] is True, written
    revision = written["model_state"]["next_write_expected_revision"]
    assert revision

    stale = client.request(
        "set_params", {"values": {"width": 42.0}, "expected_revision": "bogus"}
    )
    assert stale["ok"] is False
    assert stale["failure_code"] == "STALE_PROGRAM_REVISION"

    patched = client.request(
        "set_params", {"values": {"width": 42.0}, "expected_revision": revision}
    )
    assert patched["ok"] is True, patched
    assert patched["digest"] != written["digest"]


def test_progress_events_are_collected_rather_than_mistaken_for_replies(
    client, tmp_path
) -> None:
    """An event frame carries an ``id`` too; reading one as a reply hangs."""

    seen: list[str] = []
    client.on_event = lambda frame: seen.append(frame["event"]["event"])
    open_project(client, tmp_path / "project")

    written = client.request(
        "write_script", {"source": PLATE, "expected_revision": ""}
    )

    assert written["ok"] is True
    assert seen, "the engine emitted no progress events at all"
    assert client.events


def test_a_reply_that_breaks_the_response_contract_is_an_error(
    client, tmp_path, monkeypatch
) -> None:
    """A third client that tolerates an undeclared key is not a contract.

    The engine is real; the *validator* is made to fail, which is the only
    way to see this path without shipping a broken engine.
    """

    open_project(client, tmp_path / "project")
    monkeypatch.setattr(
        client.engine.protocol,
        "validate_response",
        lambda op, frame: ["describe_api response: unexpected ['surprise']"],
    )

    with pytest.raises(CadexdError) as caught:
        client.request("describe_api")
    assert "OP_RESPONSE_SPECS" in str(caught.value)


def test_describe_api_serves_the_authoring_contract(client, tmp_path) -> None:
    """What the system prompt is built from, asked of the engine itself."""

    open_project(client, tmp_path / "project")

    api = client.request("describe_api")

    assert api["ok"] is True and api["domain"] == "project"
    assert api["instructions"] and api["program_schema"]
    assert "part" in api["source_globals"]


def test_shutdown_is_graceful_and_close_is_idempotent(engine, tmp_path) -> None:
    running = CadexdClient(engine)
    running.start()
    open_project(running, tmp_path / "project")

    running.shutdown()
    running.shutdown()  # a second one must not raise
    running.close()

    with pytest.raises(CadexdError):
        running.request("describe_api")


def test_opening_a_project_that_cannot_be_opened_says_which(engine, tmp_path) -> None:
    running = CadexdClient(engine)
    running.start()
    try:
        blocked = tmp_path / "file-not-a-dir"
        blocked.write_text("", encoding="utf-8")
        with pytest.raises(CadexdError) as caught:
            open_project(running, blocked)
        assert str(blocked) in str(caught.value)
    finally:
        running.shutdown()


# -- the lock, which exists because cadexd is one per project -------------


def test_a_second_run_on_one_project_is_refused_not_raced(tmp_path) -> None:
    root = tmp_path / "project"
    with project_lock(root):
        with pytest.raises(ProjectBusy) as caught:
            with project_lock(root):
                pass
    assert "another Cadex CLI run" in str(caught.value)


def test_the_lock_is_released_when_the_block_ends(tmp_path) -> None:
    root = tmp_path / "project"
    with project_lock(root):
        pass
    with project_lock(root):
        pass  # no stale-lock heuristic to get wrong


def test_two_different_projects_do_not_block_each_other(tmp_path) -> None:
    with project_lock(tmp_path / "a"), project_lock(tmp_path / "b"):
        pass
