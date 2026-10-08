# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The dashboard is read-only (ADR-537).

The page writes nothing. Every method but GET and HEAD is refused, under
``cadex review``'s ``/`` and ``cadex app``'s ``/p/<name>/``, and the
project is byte-identical afterwards -- proved with no engine. Then,
against a real engine in headless Chromium, the change comes from where
it now always comes from, the CLI the agent drives, and the open page
follows it to the rebuilt model.
"""

from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

import pytest

from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK
from cadex_cli.review_server import serve, serve_projects
from test_app import _projects
from test_review_server import _get, _json, _open, _model_state, browser, needs_browser  # noqa: F401

PLATE = """
p = params(width=num(30.0, unit="mm", min=10.0, max=90.0, step=1.0),
           thickness=num(6.0, unit="mm", min=2.0, max=20.0, step=0.5))
plate = part.box(p.width, 20.0, p.thickness)
result = {"plate": plate}
"""


def _send(url: str, method: str, body: bytes = b"{}") -> int:
    parts = urlsplit(url)
    connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=30)
    try:
        connection.request(method, parts.path, body=body, headers={"Content-Type": "application/json"})
        return connection.getresponse().status
    finally:
        connection.close()


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes()
            for path in sorted(root.rglob("*")) if path.is_file()}


@pytest.fixture
def app(tmp_path):
    projects = _projects(tmp_path)
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield projects, server
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def plate_app(engine, tmp_path, capsys):
    projects = tmp_path / "projects"
    source = tmp_path / "plate.py"
    source.write_text(PLATE, encoding="utf-8")
    assert main(["script", "--set", str(source), "--project", str(projects / "plate"), "--json"]) == EXIT_OK
    capsys.readouterr()
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield projects / "plate", server
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    """A ``claude`` on PATH that replays a script through the real bridge."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "claude"
    wrapper.write_text('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (
        sys.executable, Path(__file__).with_name("fake_claude.py")), encoding="utf-8")
    wrapper.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
    script, seen, gate = tmp_path / "turn.json", tmp_path / "seen.txt", tmp_path / "gate"
    monkeypatch.setenv("CADEX_FAKE_CLAUDE_SCRIPT", str(script))
    monkeypatch.setenv("CADEX_FAKE_CLAUDE_SEEN", str(seen))
    return script, seen, gate


#: Every route the page once wrote through (ADR-503 to ADR-509), and the page itself.
FORMER_WRITES = ("api/params", "api/turn", "api/comment", "api/revision", "api/export",
                 "api/section", "api/project", "")


def test_no_method_but_get_reaches_a_project(app, tmp_path) -> None:
    projects, server = app
    before = _snapshot(projects)
    for route in FORMER_WRITES:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            status = _send(server.url + "p/biped/" + route, method)
            assert status == 501, (method, route, status)
    single, _thread = serve(projects / "biped", "127.0.0.1", 0)
    try:
        for route in FORMER_WRITES:
            assert _send(single.url + route, "POST") == 501, route
    finally:
        single.shutdown()
        single.server_close()
    assert _snapshot(projects) == before
    page = _get(server.url + "p/biped/")[2].decode("utf-8")
    assert "write-token" not in page and "chat" not in page and 'id="params' not in page


@needs_browser
def test_browser_follows_a_change_the_cli_makes(plate_app, browser, capsys) -> None:
    """The agent's change, made where an agent makes it, reaches an open page."""

    root, server = plate_app
    page = _open(browser, server.url + "p/plate/")
    assert _model_state(page) == "loaded"
    width = ("window.cadexReview.viewer().stats().bounds.max[0]"
             " - window.cadexReview.viewer().stats().bounds.min[0]")
    assert page.evaluate(width) == pytest.approx(30.0, abs=0.01)
    before = page.evaluate("window.cadexReview.state().revision")
    assert main(["params", "--project", str(root), "--set", "width=55", "--json"]) == EXIT_OK
    capsys.readouterr()
    accepted = _json(server.url + "p/plate/api/project")["accepted"]["revision"]
    assert accepted != before
    page.wait_for("window.cadexReview.state().revision === %s" % json.dumps(accepted), timeout=30)
    page.wait_for("(window.cadexReview.state().model || {}).revision === %s" % json.dumps(accepted), timeout=60)
    # The manifest is the page's as soon as it arrives; the meshes are drawn
    # once every one is in and installed, which takes its own time.
    page.wait_for("Math.abs(%s - 55) < 0.01" % width, timeout=60)
    assert page.evaluate(width) == pytest.approx(55.0, abs=0.01)
    assert page.evaluate("document.querySelectorAll('#revision-list li').length") >= 2


def test_remote_viewing_is_tailscale_serve_in_front_of_loopback() -> None:
    """DASHBOARD.md §22 says how another device reaches the page, and the defaults it relies on hold."""

    import inspect

    from cadex_cli.__main__ import build_parser

    spec = (Path(__file__).resolve().parents[2] / "docs" / "DASHBOARD.md").read_text(encoding="utf-8")
    section = spec.split("## 22. Remote viewing", 1)[1].split("\n## ", 1)[0]
    for needed in ("`127.0.0.1`", "tailscale serve --bg 8765", "tailscale funnel", "0.0.0.0"):
        assert needed in section, needed
    # The loopback default it relies on, in each way of starting the server.
    for function in (serve, serve_projects):
        assert inspect.signature(function).parameters["host"].default == "127.0.0.1"
    parser = build_parser()
    for command in ("app", "review"):
        argv = [command] + (["--project", "p"] if command == "review" else [])
        assert parser.parse_args(argv).host == "127.0.0.1", command
