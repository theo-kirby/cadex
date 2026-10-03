# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The dashboard's first write: a parameter slider (orun2 D2, ADR-503).

Two halves. Every POST, under ``cadex review``'s ``/`` and ``cadex app``'s
``/p/<name>/``, is refused without the per-launch token the server writes
into the page it serves, or from another origin — proved with no engine,
because a guard that only an engine run exercises is a guard most runs
never see. Then, against a real engine in headless Chromium, a slider
moves, the CLI's own ``cadex params`` runs (its ``PROGRESS.md`` row and
its project commit are the evidence that it was that path and no other),
and the page draws the rebuilt model.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import statistics
import subprocess
import urllib.error
import urllib.request

import pytest

import cadex_cli.review_server as review_server
from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK
from cadex_cli.review_server import serve, serve_projects
from cadex_cli.walk import Leg
from test_app import _projects
from test_review_server import _get, _json, _open, _model_state, browser, needs_browser  # noqa: F401

PLATE = """
p = params(width=num(30.0, unit="mm", min=10.0, max=90.0, step=1.0),
           thickness=num(6.0, unit="mm", min=2.0, max=20.0, step=0.5))
plate = part.box(p.width, 20.0, p.thickness)
result = {"plate": plate}
"""


def _token(page_url: str) -> str:
    body = _get(page_url)[2].decode("utf-8")
    found = re.search(r'<meta name="cadex-write-token" content="([^"]*)">', body)
    assert found and found.group(1), "the served page carries no write token"
    return found.group(1)


def _post(url: str, body: object, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


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
def spawned(monkeypatch):
    """Record the child the server would spawn, and answer as ``params`` would."""

    calls = []

    def fake_leg(name, argv, *, capture=True, timeout=0.0):
        calls.append((name, list(argv), timeout))
        return Leg(name=name, argv=list(argv), code=EXIT_OK, seconds=0.25,
                   envelope={"ok": True, "accepted_revision": "f" * 64, "digest": "e" * 64,
                             "params": {"width": 40.0}})

    monkeypatch.setattr(review_server, "run_leg", fake_leg)
    return calls


def test_every_post_needs_the_launch_token_and_this_origin(app, spawned) -> None:
    projects, server = app
    progress = (projects / "biped" / "PROGRESS.md").read_text()
    url = server.url + "p/biped/api/params"
    token = _token(server.url + "p/biped/")
    body = {"values": {"width": 40}}
    for headers in ({}, {"X-Cadex-Token": "x" * 43}, {"X-Cadex-Token": token[:-1]},
                    {"X-Cadex-Token": token, "Origin": "http://evil.example"},
                    {"X-Cadex-Token": token, "Origin": server.url.replace("127.0.0.1", "localhost").rstrip("/")}):
        status, reply = _post(url, body, headers)
        assert status == 403 and reply["ok"] is False, (headers, reply)
    # Refused before routing: an unknown path is a 403 too, not a 404.
    assert _post(server.url + "p/biped/api/nope", body)[0] == 403
    assert _post(server.url + "api/params", body)[0] == 403
    assert spawned == []
    assert (projects / "biped" / "PROGRESS.md").read_text() == progress
    # The token is the launch's: a second server has its own.
    other, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        assert _token(other.url + "p/biped/") != token
        assert _post(other.url + "p/biped/api/params", body, {"X-Cadex-Token": token})[0] == 403
    finally:
        other.shutdown()
        other.server_close()
    # The index carries no token; the review page alone writes.
    assert b"cadex-write-token" not in _get(server.url)[2]


def test_a_tokened_write_is_the_cli_params_command(app, spawned) -> None:
    projects, server = app
    token = {"X-Cadex-Token": _token(server.url + "p/biped/")}
    status, reply = _post(server.url + "p/biped/api/params",
                          {"values": {"width": 40, "thickness": 6.5}},
                          {**token, "Origin": server.url.rstrip("/")})
    assert status == 200 and reply["ok"] is True and reply["accepted_revision"] == "f" * 64
    root = str((projects / "biped").resolve())
    assert spawned == [("params", ["params", "--project", root, "--set", "thickness=6.5",
                                   "--set", "width=40", "--json"], review_server.WRITE_TIMEOUT_S)]
    assert reply["command"] == ["cadex", "params", "--project", root, "--set", "thickness=6.5",
                                "--set", "width=40"]
    for bad in ({}, {"values": {}}, {"values": {"--wait": 1}}, {"values": {"width": "1; rm"}},
                {"values": {"width": True}}, {"values": {"width": float("inf")}}, {"values": [1]}):
        payload = json.dumps(bad).replace("Infinity", "1e999").encode("utf-8")
        assert _post(server.url + "p/biped/api/params", payload, token)[0] == 400, bad
    assert _post(server.url + "p/biped/api/params", b"not json", token)[0] == 400
    assert _post(server.url + "p/nope/api/params", {"values": {"width": 1}}, token)[0] == 404
    assert _post(server.url + "p/biped/api/project", {"values": {"width": 1}}, token)[0] == 404
    assert _post(server.url + "api/params", {"values": {"width": 1}}, token)[0] == 404
    assert len(spawned) == 1


def test_cadex_review_guards_its_root_the_same_way(tmp_path, spawned) -> None:
    root = _projects(tmp_path) / "biped"
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        assert _post(server.url + "api/params", {"values": {"width": 40}})[0] == 403
        token = {"X-Cadex-Token": _token(server.url)}
        status, reply = _post(server.url + "api/params", {"values": {"width": 40}}, token)
        assert status == 200 and reply["ok"] is True
        assert spawned[0][1][:3] == ["params", "--project", str(root.resolve())]
    finally:
        server.shutdown()
        server.server_close()


def test_a_refused_write_says_why_and_is_not_a_200(app, monkeypatch) -> None:
    _projects_root, server = app
    monkeypatch.setattr(review_server, "run_leg", lambda name, argv, **_k: Leg(
        name=name, argv=list(argv), code=1, envelope={"ok": False, "error": "project busy"}))
    status, reply = _post(server.url + "p/biped/api/params", {"values": {"width": 40}},
                          {"X-Cadex-Token": _token(server.url + "p/biped/")})
    assert status == 409 and reply == {**reply, "ok": False, "exit": 1, "error": "project busy"}


# -- against a real engine -----------------------------------------------


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


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(fraction * (len(ordered) - 1)))]


@needs_browser
def test_browser_moves_a_slider_and_sees_the_rebuilt_model(plate_app, browser) -> None:
    root, server = plate_app
    page = _open(browser, server.url + "p/plate/")
    assert _model_state(page) == "loaded"
    assert page.evaluate("window.cadexReview.viewer().stats().bounds.max[0]"
                         " - window.cadexReview.viewer().stats().bounds.min[0]") == pytest.approx(30.0, abs=0.01)
    slider = "#params input[type=range][data-param=width]"
    assert page.attribute(slider, "min") == "10" and page.attribute(slider, "max") == "90"
    commits = int(subprocess.run(["git", "-C", str(root), "rev-list", "--count", "HEAD"],
                                 capture_output=True, text=True, check=True).stdout)
    total_ms, server_s, revisions = [], [], set()
    for width in (55, 41, 72, 63, 48):
        before = page.evaluate("window.cadexReview.state().revision")
        page.evaluate(
            "(() => { const s = document.querySelector(%s); s.value = '%d';"
            " s.dispatchEvent(new Event('input')); s.dispatchEvent(new Event('change')); })()"
            % (json.dumps(slider), width))
        page.wait_for("(window.cadexReview.lastWrite() || {}).value === %d" % width, timeout=60)
        write = page.evaluate("window.cadexReview.lastWrite()")
        assert write["ok"] is True, write
        assert page.attribute("#params-write", "data-state") == "done"
        # The page shows the accepted revision the CLI reported, drawn.
        assert page.evaluate("window.cadexReview.state().revision") == write["revision"] != before
        assert _model_state(page) == "loaded"
        assert write["revision"][:12] in page.text("#model-status")
        size = page.evaluate("window.cadexReview.viewer().stats().bounds.max[0]"
                             " - window.cadexReview.viewer().stats().bounds.min[0]")
        assert size == pytest.approx(float(width), abs=0.01)
        assert page.evaluate("[document.querySelector(%s).value, document.querySelector(%s).disabled]"
                             % (json.dumps(slider), json.dumps(slider))) == [str(width), False]
        total_ms.append(write["total_ms"])
        server_s.append(write["server_s"])
        revisions.add(write["revision"])
    assert len(revisions) == 5
    # It was the CLI's path: a PROGRESS.md row and a project commit per move.
    progress = (root / "PROGRESS.md").read_text()
    for width in (55, 41, 72, 63, 48):
        assert f"params width={float(width)!r}" in progress or f"params width={width}" in progress
    after = int(subprocess.run(["git", "-C", str(root), "rev-list", "--count", "HEAD"],
                               capture_output=True, text=True, check=True).stdout)
    assert after == commits + 5
    assert _json(server.url + "p/plate/api/project")["accepted"]["param_values"]["width"] == 48.0
    print("slider latency, slider release to model drawn: p50 %.0f ms, p95 %.0f ms;"
          " cadex params child: p50 %.2f s, p95 %.2f s (n=%d)" % (
              statistics.median(total_ms), _percentile(total_ms, 0.95),
              statistics.median(server_s), _percentile(server_s, 0.95), len(total_ms)))
