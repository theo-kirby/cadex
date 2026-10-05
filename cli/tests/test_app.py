# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""`cadex app`: the dashboard over a directory of projects (orun2 D1).

A bare `./cadex` and `pixi run app` serve, on 127.0.0.1, an index of every
project under one directory, and each project's review page under
`/p/<name>/` — the same page `cadex review` serves at `/`, its requests
carrying the prefix. Read-only, like `cadex review`: nothing in a project
changes for having been listed or opened.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tomllib

import pytest

import cadex_cli.__main__ as cli
from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK, EXIT_USAGE
from cadex_cli.review_server import serve_projects
from test_review_record import REVISION_B
from test_review_server import (
    _get, _json, _model_state, _open, _review_project, _stage_accepted, browser, needs_browser,  # noqa: F401
)

CLI_DIR = Path(__file__).resolve().parents[1]
REPO = CLI_DIR.parent


def _projects(tmp_path: Path) -> Path:
    """``biped`` (accepted at B, three runs), ``empty`` (a manifest, nothing
    accepted), and two directories that are not projects."""

    projects = tmp_path / "projects"
    projects.mkdir()
    _review_project(projects)
    empty = projects / "empty"
    empty.mkdir()
    (empty / "script.json").write_text("{}")
    (projects / "notes").mkdir()
    (projects / ".cache").mkdir()
    (projects / ".cache" / "script.json").write_text("{}")
    return projects


@pytest.fixture
def app(tmp_path):
    projects = _projects(tmp_path)
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield projects, server
    finally:
        server.shutdown()
        server.server_close()


def test_the_index_lists_only_projects_and_finds_new_ones_live(app) -> None:
    projects, server = app
    listing = _json(server.url + "api/projects")
    assert listing["schema"] == "cadex-projects-v1" and listing["root"] == "projects"
    by_name = {entry["name"]: entry for entry in listing["projects"]}
    assert list(by_name) == ["biped", "empty"]
    assert by_name["biped"]["url"] == "p/biped/"
    assert by_name["biped"]["accepted"]["revision"] == REVISION_B and by_name["biped"]["runs"] == 3
    assert by_name["empty"]["accepted"]["available"] is False and by_name["empty"]["runs"] == 0
    (projects / "notes" / "script.json").write_text("{}")
    assert [e["name"] for e in _json(server.url + "api/projects")["projects"]] == ["biped", "empty", "notes"]
    status, headers, body = _get(server.url)
    assert status == 200 and headers["content-type"].startswith("text/html")
    assert b'id="projects"' in body and b'src="projects.js"' in body
    assert _get(server.url + "review.css")[0] == 200


def test_each_project_is_its_review_page_under_its_own_prefix(app) -> None:
    _projects_root, server = app
    status, headers, _body = _get(server.url + "p/biped")
    # urllib follows the redirect; the page it lands on is the project's.
    assert status == 200 and headers["content-type"].startswith("text/html")
    page = _get(server.url + "p/biped/")[2]
    assert b'id="project-name"' in page and b'src="viewer.js"' in page
    assert _get(server.url + "p/biped/viewer.js")[0] == 200
    review = _json(server.url + "p/biped/api/project")
    assert review["project"] == "biped" and review["accepted"]["revision"] == REVISION_B
    assert _json(server.url + "p/biped/api/run/second")["run"] == "second"
    for missing in ("p/nope/", "p/nope/api/project", "p/notes/api/project", "p/.cache/api/project",
                    "p/biped/api/nope", "api/project"):
        assert _get(server.url + missing)[0] == 404, missing


def test_a_bare_cadex_is_the_app(monkeypatch) -> None:
    seen = []
    monkeypatch.setattr(cli, "command_app", lambda args, report: seen.append(args) or EXIT_OK)
    assert main([]) == EXIT_OK
    assert len(seen) == 1 and seen[0].command is None
    assert main(["app", "--port", "0"]) == EXIT_OK and seen[1].port == 0


def test_the_projects_directory_defaults(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CADEX_PROJECTS", raising=False)
    parse = cli.build_parser().parse_args
    assert cli.projects_directory(parse([])) == tmp_path / "cadex-projects"
    monkeypatch.setenv("CADEX_PROJECTS", str(tmp_path / "env"))
    assert cli.projects_directory(parse([])) == tmp_path / "env"
    assert cli.projects_directory(parse(["app", "--projects", str(tmp_path / "flag")])) == tmp_path / "flag"


def test_the_app_refuses_a_file_and_a_bad_port(tmp_path, capsys) -> None:
    (tmp_path / "file").write_text("")
    assert main(["app", "--projects", str(tmp_path / "file")]) == EXIT_USAGE
    assert "not a directory" in capsys.readouterr().out
    assert main(["app", "--projects", str(tmp_path), "--port", "70000"]) == EXIT_USAGE
    assert "--port must be" in capsys.readouterr().out


def test_the_shim_serves_the_index_on_loopback_and_writes_nothing(tmp_path) -> None:
    projects = _projects(tmp_path)
    progress = (projects / "biped" / "PROGRESS.md").read_text()
    fresh = tmp_path / "fresh"  # absent: the app creates it rather than refusing
    env = {**os.environ, "CADEX_PROJECTS": str(fresh)}
    for directory, names in ((projects, ["biped", "empty"]), (fresh, [])):
        process = subprocess.Popen(
            [str(REPO / "cadex"), "app", "--port", "0", "--json"] + (
                ["--projects", str(directory)] if directory == projects else []),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, cwd=tmp_path)
        try:
            line = process.stderr.readline()
            assert f"app: serving {directory} at http://127.0.0.1:" in line, line
            url = line.split(" at ")[1].split(" ")[0]
            assert b'id="projects"' in _get(url)[2]
            assert [e["name"] for e in _json(url + "api/projects")["projects"]] == names
            process.send_signal(signal.SIGTERM)
            stdout, stderr = process.communicate(timeout=20)
        finally:
            if process.poll() is None:
                process.kill()
        assert process.returncode == EXIT_OK, stderr
        assert json.loads(stdout)["notes"] == [f"app: served {url}; stopped"]
    assert (projects / "biped" / "PROGRESS.md").read_text() == progress
    assert not (projects / "biped" / ".git").exists() and not (tmp_path / ".cadex").exists()


def test_pixi_run_app_is_the_app() -> None:
    tasks = tomllib.loads((REPO / "pixi.toml").read_text())["tasks"]
    assert tasks["app"] == {"cmd": ["./cadex", "app"]}


@needs_browser
def test_browser_goes_from_the_index_to_a_drawn_project(tmp_path, browser) -> None:
    projects = _projects(tmp_path)
    _stage_accepted(projects / "biped", REVISION_B)
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        page = browser.page(server.url)
        page.wait_for("document.querySelectorAll('#projects li').length === 2")
        # Newest accepted first, each a link and a date; one page, so no pager.
        assert page.evaluate("[...document.querySelectorAll('#projects li')].map(l => l.dataset.project)")[0] == "biped"
        assert page.attribute("#projects li[data-project='biped'] a", "href") == "p/biped/"
        assert page.text("#projects-count") == "2"
        assert page.evaluate("document.getElementById('pager').hidden") is True
        project = _open(browser, server.url + "p/biped/")
        assert project.text("#project-name") == "biped"
        assert project.attribute("#home", "href") == "../../"
        assert _model_state(project) == "loaded"
        assert project.evaluate("window.cadexReview.viewer().stats()")["components"] >= 1
    finally:
        server.shutdown()
        server.server_close()


@needs_browser
def test_browser_pages_through_the_projects_newest_first(tmp_path, browser) -> None:
    """ADR-533: 20 projects to a page, newest accepted first, the page in the URL."""

    projects = tmp_path / "many"
    for index in range(45):
        (projects / f"p{index:02d}").mkdir(parents=True)
        (projects / f"p{index:02d}" / "script.json").write_text("{}")
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        page = browser.page(server.url)
        page.wait_for("document.querySelectorAll('#projects li').length === 20")
        assert page.text("#page-at") == "1 of 3"
        assert page.evaluate("document.getElementById('page-prev').disabled") is True
        first = page.evaluate("[...document.querySelectorAll('#projects li')].map(l => l.dataset.project)")
        assert first[0] == "p00" and first[-1] == "p19"
        page.click("#page-next")
        page.click("#page-next")
        page.wait_for("document.getElementById('page-at').textContent === '3 of 3'")
        assert page.evaluate("document.querySelectorAll('#projects li').length") == 5
        assert page.evaluate("location.search") == "?page=3"
        assert page.evaluate("document.getElementById('page-next').disabled") is True
        again = browser.page(server.url + "?page=2")
        again.wait_for("document.getElementById('page-at').textContent === '2 of 3'")
        assert again.evaluate("document.querySelector('#projects li').dataset.project") == "p20"
    finally:
        server.shutdown()
        server.server_close()
