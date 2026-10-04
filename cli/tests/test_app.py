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
    assert by_name["biped"]["url"] == "/p/biped/"
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
        assert page.attribute("#projects li[data-project='biped'] a", "href") == "/p/biped/"
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


# -- Ouroboros runs beside the projects (orun2 D3, ADR-513) ------------------

RUNS_FIXTURE = CLI_DIR / "tests" / "fixtures" / "ouroboros_runs"


def _runs(tmp_path: Path) -> Path:
    """The committed ``fx1`` run, a newer ``fx2`` with only a status, a
    decoy transcript beside them, and directories that are not runs."""

    import shutil

    runs = tmp_path / "runs"
    shutil.copytree(RUNS_FIXTURE, runs)
    (runs / "fx1" / "transcripts").mkdir()
    (runs / "fx1" / "transcripts" / "actor.jsonl").write_text('{"secret": "transcript"}\n')
    (runs / "fx2").mkdir()
    (runs / "fx2" / "status.json").write_text(json.dumps(
        {"ts": "2026-10-02T08:00:00+00:00", "state": "stopped", "branch": "ouroboros/fx2"}))
    (runs / "notes").mkdir()
    (runs / ".hidden").mkdir()
    (runs / ".hidden" / "status.json").write_text("{}")
    return runs


@pytest.fixture
def app_with_runs(tmp_path):
    projects, runs = _projects(tmp_path), _runs(tmp_path)
    server, _thread = serve_projects(projects, "127.0.0.1", 0, runs_root=runs)
    try:
        yield runs, server
    finally:
        server.shutdown()
        server.server_close()


def test_runs_are_listed_beside_projects_newest_first(app_with_runs) -> None:
    runs, server = app_with_runs
    listing = _json(server.url + "api/runs")
    assert listing["schema"] == "cadex-ouroboros-runs-v1" and listing["available"] is True
    assert [run["name"] for run in listing["runs"]] == ["fx2", "fx1"]
    fx1 = listing["runs"][1]
    assert fx1["url"] == "/r/fx1/" and fx1["state"] == "work" and fx1["branch"] == "ouroboros/fx1"
    assert fx1["started"] == "2026-10-01T09:00:00" and fx1["cost_usd"] == 4.5
    assert fx1["iteration_count"] == 3 and fx1["verdicts"] == {"continue": 1, "reject": 1}
    assert fx1["latest"] == {"iteration": 3, "verdict": None, "did": ""}
    assert fx1["skipped_lines"] == 1 and "iterations" not in fx1
    assert listing["runs"][0]["iteration_count"] == 0 and listing["runs"][0]["state"] == "stopped"
    # The projects listing is unchanged by the runs beside it.
    assert [e["name"] for e in _json(server.url + "api/projects")["projects"]] == ["biped", "empty"]


def test_a_run_shows_each_iteration_with_its_critic_verdict(app_with_runs) -> None:
    runs, server = app_with_runs
    run = _json(server.url + "r/fx1/api/run")
    assert run["schema"] == "cadex-ouroboros-run-v1" and run["name"] == "fx1"
    first, second, third = run["iterations"]
    assert first["housekeeping"] is True and first["verdict"] == "continue"
    assert first["actor"] == {"exit": 0, "timed_out": False, "error": None, "turns": 12}
    assert first["commit"]["sha"] == "aaaaaaaaaa" and first["critic"]["did"] == "Seeded the fixture criteria."
    assert second["verdict"] == "reject" and second["critique"]["must_fix"] == ["Restore the bore assertion."]
    assert second["critique"]["reason"] == "The bracket test was weakened."
    assert second["critic"]["fix_first"] == "Restore the bore assertion."
    assert third["verdict"] is None and third["critic"] is None and third["commit"]["recorded"] is True
    # A live run's next verdict appears on the next read: nothing is cached.
    with (runs / "fx1" / "critic.jsonl").open("a") as handle:
        handle.write(json.dumps({"ts": "2026-10-01T10:21:00+00:00", "iteration": 3, "verdict": "continue",
                                 "reason": "r", "reply": "next", "did": "Fixed the bore.", "doing": "",
                                 "fix_first": "", "source": "critic:claude"}) + "\n")
    assert _json(server.url + "r/fx1/api/run")["iterations"][2]["verdict"] == "continue"
    assert _json(server.url + "api/runs")["runs"][1]["verdicts"] == {"continue": 2, "reject": 1}


def test_a_run_page_serves_only_its_own_files_and_reads_nothing_else(app_with_runs) -> None:
    runs, server = app_with_runs
    status, headers, body = _get(server.url + "r/fx1/")
    assert status == 200 and b'src="run.js"' in body and b'href="review.css"' in body
    assert _get(server.url + "r/fx1/run.js")[0] == 200 and _get(server.url + "r/fx1/review.css")[0] == 200
    for path in ("r/fx1/transcripts/actor.jsonl", "r/fx1/critic.jsonl", "r/fx1/loop.log",
                 "r/notes/", "r/notes/api/run", "r/.hidden/api/run", "r/missing/", "r/fx1/api/project",
                 "r/fx1/index.html", "r/%2E%2E/api/run"):
        assert _get(server.url + path)[0] == 404, path
    assert b"transcript" not in json.dumps(_json(server.url + "r/fx1/api/run")).encode()
    # The bare name redirects into the run's own directory, as /p/<name> does.
    import http.client
    connection = http.client.HTTPConnection(*server.server_address[:2])
    connection.request("GET", "/r/fx1")
    response = connection.getresponse()
    assert response.status == 301 and response.getheader("Location") == "/r/fx1/"
    connection.close()
    # Reading wrote nothing into the run directory.
    assert sorted(p.name for p in (runs / "fx1").iterdir()) == [
        "critic.jsonl", "iterations.jsonl", "run.yml", "status.json", "transcripts"]


def test_no_runs_directory_is_an_empty_list_not_an_error(tmp_path) -> None:
    projects = _projects(tmp_path)
    for runs_root in (None, tmp_path / "absent"):
        server, _thread = serve_projects(projects, "127.0.0.1", 0, runs_root=runs_root)
        try:
            listing = _json(server.url + "api/runs")
            assert listing["available"] is False and listing["runs"] == []
            assert _get(server.url + "r/fx1/")[0] == 404
        finally:
            server.shutdown()
            server.server_close()


def test_the_runs_directory_defaults(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("CADEX_RUNS", raising=False)
    parse = cli.build_parser().parse_args
    assert cli.runs_directory(parse([])) == REPO / ".ouroboros" / "runs"
    monkeypatch.setenv("CADEX_RUNS", str(tmp_path / "env"))
    assert cli.runs_directory(parse([])) == tmp_path / "env"
    assert cli.runs_directory(parse(["app", "--runs", str(tmp_path / "flag")])) == tmp_path / "flag"


FX1_CHARTER = """# Goal: fixture

## Mission

Prose with a checkbox that is not a criterion:
- [ ] not a criterion

## Done criteria

Each criterion needs a record.

- [x] **S1. The shell is gone.**
  - `git ls-files shell` is 0.
- [ ] **D3. Runs are first-class
  in the dashboard.** The charter shows here.
  - Read-only.

A paragraph between criteria belongs to neither.

- [ ] A criterion with no bold title. It still counts.

## Horizon ladder

- [ ] not a criterion either
"""


def _git(checkout: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(checkout), "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


def _checkout_with_runs(tmp_path: Path) -> Path:
    """A git checkout whose ``.ouroboros/runs`` holds the fixture runs:
    ``fx1``'s branch carries :data:`FX1_CHARTER`, ``fx2``'s branch is the one
    checked out with its goal edited in the working tree, and ``main``'s goal
    is a later charter neither run ran to."""

    import shutil

    checkout = tmp_path / "checkout"
    runs = checkout / ".ouroboros" / "runs"
    (tmp_path / "runs-source").mkdir()
    shutil.copytree(_runs(tmp_path / "runs-source"), runs)
    goal = checkout / ".ouroboros" / "goal.md"
    _git(tmp_path, "init", "--quiet", "--initial-branch=main", str(checkout))
    goal.write_text("# Goal: later\n\n## Done criteria\n\n- [ ] **Z9. A later run's criterion.**\n")
    _git(checkout, "add", ".ouroboros/goal.md")
    _git(checkout, "commit", "--quiet", "-m", "later charter")
    _git(checkout, "checkout", "--quiet", "-b", "ouroboros/fx1")
    goal.write_text(FX1_CHARTER)
    _git(checkout, "commit", "--quiet", "-am", "fx1 charter")
    _git(checkout, "checkout", "--quiet", "main")
    _git(checkout, "checkout", "--quiet", "-b", "ouroboros/fx2")
    goal.write_text("# Goal: fx2\n\n## Done criteria\n\n- [ ] **A1. Edited, not committed.**\n")
    return runs


def test_a_run_shows_the_charter_criteria_its_branch_holds(tmp_path) -> None:
    runs = _checkout_with_runs(tmp_path)
    server, _thread = serve_projects(_projects(tmp_path), "127.0.0.1", 0, runs_root=runs)
    try:
        charter = _json(server.url + "r/fx1/api/run")["charter"]
        # From fx1's branch, not the later charter checked out beside it.
        assert charter["available"] is True and charter["source"] == "ouroboros/fx1"
        assert charter["goal"] == ".ouroboros/goal.md" and charter["reason"] is None
        assert (charter["checked"], charter["total"]) == (1, 3)
        s1, d3, bare = charter["criteria"]
        assert s1 == {"id": "S1", "title": "The shell is gone.", "checked": True,
                      "markdown": "**S1. The shell is gone.**\n- `git ls-files shell` is 0."}
        assert d3["id"] == "D3" and d3["title"] == "Runs are first-class in the dashboard." and not d3["checked"]
        assert d3["markdown"].endswith("- Read-only.") and "neither" not in d3["markdown"]
        assert bare["id"] is None and bare["title"] == "A criterion with no bold title"
        # The checked-out run's charter is the working tree's, uncommitted edits and all.
        fx2 = _json(server.url + "r/fx2/api/run")["charter"]
        assert fx2["source"] == "working tree" and [c["title"] for c in fx2["criteria"]] == ["Edited, not committed."]
        # A run whose branch is gone says so instead of showing another run's charter.
        _git(runs.parent.parent, "branch", "-D", "ouroboros/fx1")
        gone = _json(server.url + "r/fx1/api/run")["charter"]
        assert gone["available"] is False and gone["criteria"] == []
        assert gone["reason"] == "neither ouroboros/fx1 nor origin/ouroboros/fx1 holds .ouroboros/goal.md"
        # The listing stays the light one.
        assert "charter" not in _json(server.url + "api/runs")["runs"][0]
        # Reading the charter wrote nothing and moved no branch.
        assert subprocess.run(["git", "-C", str(runs.parent.parent), "status", "--porcelain"], capture_output=True,
                              text=True, check=True).stdout.split() == ["M", ".ouroboros/goal.md", "??", ".ouroboros/runs/"]
    finally:
        server.shutdown()
        server.server_close()


def test_a_charter_outside_a_checkout_or_the_checkout_is_refused(app_with_runs, tmp_path) -> None:
    from cadex_cli.review_server import OuroborosRuns

    _runs_dir, server = app_with_runs
    charter = _json(server.url + "r/fx1/api/run")["charter"]
    assert charter["available"] is False and charter["reason"] == (
        "the runs directory is not a checkout's .ouroboros/runs")
    runs = OuroborosRuns(_checkout_with_runs(tmp_path))
    for goal, branch, reason in (("../secret.md", "ouroboros/fx1", "goal '../secret.md' is not a path inside the checkout"),
                                 ("/etc/passwd", "ouroboros/fx1", "goal '/etc/passwd' is not a path inside the checkout"),
                                 (".ouroboros/goal.md", "--output=x", "branch '--output=x' is not a plain ref name"),
                                 (".ouroboros/goal.md", "a/../b", "branch 'a/../b' is not a plain ref name")):
        assert runs._charter({"goal": goal}, branch)["reason"] == reason


@needs_browser
def test_browser_goes_from_the_index_to_a_runs_iterations_and_verdicts(tmp_path, browser) -> None:
    projects, runs = _projects(tmp_path), _checkout_with_runs(tmp_path)
    server, _thread = serve_projects(projects, "127.0.0.1", 0, runs_root=runs)
    try:
        page = browser.page(server.url)
        page.wait_for("document.querySelectorAll('#runs li').length === 2")
        assert page.evaluate("document.getElementById('runs-card').hidden") is False
        assert page.attribute("#runs li[data-run='fx1'] a", "href") == "/r/fx1/"
        assert "work · 3 iterations" in page.text("#runs li[data-run='fx1']")
        run = browser.page(server.url + "r/fx1/")
        run.wait_for("document.querySelectorAll('#iterations tr').length === 3")
        assert run.text("#run-name") == "fx1"
        assert run.text("#run-line") == "work · 3 iterations"
        # Newest first; the pending iteration says so; a verdict is in its status colour.
        assert run.evaluate("[...document.querySelectorAll('#iterations tr')].map(r => r.dataset.iteration)") == ["3", "2", "1"]
        assert "pending" in run.text("#iterations tr[data-iteration='3']")
        rejected = "#iterations tr[data-iteration='2']"
        assert run.attribute(rejected + " .verdict", "data-tone") == "bad"
        assert "The bracket test was weakened." in run.text(rejected)
        # The charter's criteria, from the run's branch, ticked or not.
        run.wait_for("document.querySelectorAll('#charter li').length === 3")
        assert run.text("#charter-count") == "1 of 3 ticked"
        assert run.evaluate("[...document.querySelectorAll('#charter li')].map(l => l.dataset.criterion + ':' + l.dataset.checked)") == [
            "S1:true", "D3:false", ":false"]
        assert run.text("#charter li[data-criterion='S1']").startswith("✓ S1")
        assert "Runs are first-class in the dashboard." in run.text("#charter li[data-criterion='D3']")
        assert "Read-only." in run.attribute("#charter li[data-criterion='D3']", "title")
        assert run.evaluate("document.getElementById('charter-empty').hidden") is True
    finally:
        server.shutdown()
        server.server_close()


def _checkout_with_probes(tmp_path: Path) -> tuple[Path, Path]:
    """:func:`_checkout_with_runs` with ``docs/probes/fx1/`` beside it:
    a README, an image one directory down, and what must never be served --
    a dot-file, an HTML page, a ``.pyc``, a symlink out of the checkout and a
    symlinked directory."""

    runs = _checkout_with_runs(tmp_path)
    checkout = runs.parent.parent
    probes = checkout / "docs" / "probes" / "fx1"
    (probes / "sweep").mkdir(parents=True)
    (probes / "README.md").write_text("# fx1\n\n![hero](sweep/hero.png)\n\n| a | b |\n|---|---|\n| 1 | **2** |\n")
    (probes / "sweep" / "hero.png").write_bytes(PNG_1PX)
    (probes / "ratings.json").write_text('{"love": 1}\n')
    (probes / ".secret.md").write_text("dot-file\n")
    (probes / "page.html").write_text("<script>alert(1)</script>\n")
    (probes / "__pycache__").mkdir()
    (probes / "__pycache__" / "judge.cpython-312.pyc").write_bytes(b"\0")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("outside the checkout\n")
    (probes / "escape.md").symlink_to(outside / "secret.md")
    (probes / "linked").symlink_to(outside, target_is_directory=True)
    return runs, probes


PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360606060000000050001a5f645400000000049454e44ae426082")


def test_a_runs_probe_material_is_listed_and_served_read_only(tmp_path) -> None:
    runs, probes = _checkout_with_probes(tmp_path)
    server, _thread = serve_projects(_projects(tmp_path), "127.0.0.1", 0, runs_root=runs)
    try:
        listing = _json(server.url + "r/fx1/api/run")["probes"]
        assert listing == {"available": True, "root": "docs/probes/fx1", "reason": None, "readme": "README.md",
                           "truncated": 0, "files": [
                               {"path": "README.md", "kind": "text", "bytes": (probes / "README.md").stat().st_size},
                               {"path": "ratings.json", "kind": "data", "bytes": 12},
                               {"path": "sweep/hero.png", "kind": "image", "bytes": len(PNG_1PX)}]}
        status, headers, body = _get(server.url + "r/fx1/probes/sweep/hero.png")
        assert status == 200 and body == PNG_1PX and headers["content-type"] == "image/png"
        assert headers["content-security-policy"] == "sandbox" and headers["x-content-type-options"] == "nosniff"
        status, headers, body = _get(server.url + "r/fx1/probes/README.md")
        assert status == 200 and body.startswith(b"# fx1") and headers["content-type"].startswith("text/markdown")
        for path in ("r/fx1/probes/.secret.md", "r/fx1/probes/page.html", "r/fx1/probes/escape.md",
                     "r/fx1/probes/linked/secret.md", "r/fx1/probes/__pycache__/judge.cpython-312.pyc",
                     "r/fx1/probes/../../.ouroboros/goal.md", "r/fx1/probes/%2E%2E/%2E%2E/.ouroboros/goal.md",
                     "r/fx1/probes/sweep%2F..%2F..%2Ffx2/x.md", "r/fx1/probes/missing.png", "r/fx1/probes/",
                     "r/fx1/probes/sweep", "r/fx2/probes/README.md", "r/missing/probes/README.md"):
            assert _get(server.url + path)[0] == 404, path
        # A run with no probe directory says so; one whose directory is a symlink is not followed.
        assert _json(server.url + "r/fx2/api/run")["probes"]["reason"] == "docs/probes/fx2 is not a directory of the checkout"
        (probes.parent / "fx2").symlink_to(probes, target_is_directory=True)
        assert _json(server.url + "r/fx2/api/run")["probes"]["available"] is False
        assert _get(server.url + "r/fx2/probes/README.md")[0] == 404
        # Nothing is listed with the light runs listing, and serving wrote nothing.
        assert "probes" not in _json(server.url + "api/runs")["runs"][0]
        assert sorted(p.name for p in probes.iterdir()) == [
            ".secret.md", "README.md", "__pycache__", "escape.md", "linked", "page.html", "ratings.json", "sweep"]
    finally:
        server.shutdown()
        server.server_close()


def test_probes_outside_a_checkout_are_refused(app_with_runs) -> None:
    _runs_dir, server = app_with_runs
    probes = _json(server.url + "r/fx1/api/run")["probes"]
    assert probes["available"] is False and probes["files"] == []
    assert probes["reason"] == "the runs directory is not a checkout's .ouroboros/runs"


# -- A run's records and the artifacts they name (orun2 D3, ADR-518) ---------

def _record(slug: str, branch: str, created: str, body: str, title: str | None = None) -> str:
    title = (title or slug + " — it's a record").replace("'", "''")
    return (f"---\nnode_id: x\nslug: {slug}\ntitle: '{title}'\n"
            f"created_at: '{created}'\nparents: []\n---\n## What\n\n{body}\n\n"
            f"## Repo\n\n- repo: fixture\n- branch: {branch}\n- commit: abc\n")


def _checkout_with_records(tmp_path: Path) -> tuple[Path, Path]:
    """:func:`_checkout_with_probes` with records: two of ``fx1`` (one landing
    in iteration 2, one after the last finished iteration), one of ``fx2``,
    and the files they name, served and not."""

    runs, probes = _checkout_with_probes(tmp_path)
    checkout = runs.parent.parent
    docs = checkout / "docs"
    (docs / "GUIDE.md").write_text("# Guide\n\nText.\n")
    (docs / "SECRET.md").write_text("fx2 only\n")
    (docs / "page.html").write_text("<script>alert(1)</script>\n")
    (docs / "escape.md").symlink_to(tmp_path / "outside" / "secret.md")
    other = docs / "probes" / "other"
    (other / "sub").mkdir(parents=True)
    (other / "shot.png").write_bytes(PNG_1PX)
    (other / "unnamed.png").write_bytes(PNG_1PX)
    (other / "sub" / "a.json").write_text("{}\n")
    (other / "sub" / "b.png").write_bytes(PNG_1PX)
    (other / "sub" / "deeper").mkdir()
    (other / "sub" / "deeper" / "c.md").write_text("deeper\n")
    (docs / "probes" / "third").mkdir()
    (docs / "probes" / "third" / "x.md").write_text("never named\n")
    records = checkout / ".hypergraph" / "graph" / "record"
    records.mkdir(parents=True)
    (records / "early-fox-0001.md").write_text(_record(
        "early-fox-0001", "ouroboros/fx1", "2026-10-01T09:30:00+00:00",
        "Shot `docs/probes/other/shot.png`, the folder docs/probes/other/sub/, the guide docs/GUIDE.md. "
        "Also docs/page.html, docs/escape.md, docs/missing.png and src/docs/GUIDE.md and docs/."))
    (records / "late-owl-0002.md").write_text(_record(
        "late-owl-0002", "ouroboros/fx1", "2026-10-01T10:30:00+00:00", "See docs/probes/fx1/README.md."))
    (records / "other-run-0003.md").write_text(_record(
        "other-run-0003", "ouroboros/fx2", "2026-10-01T09:30:00+00:00", "See docs/SECRET.md and docs/probes/third/x.md."))
    (records / "no-repo-0004.md").write_text("---\nslug: no-repo-0004\n---\n## What\n\ndocs/SECRET.md\n")
    return runs, checkout


def test_a_runs_records_name_their_iteration_and_artifacts(tmp_path) -> None:
    runs, checkout = _checkout_with_records(tmp_path)
    server, _thread = serve_projects(_projects(tmp_path), "127.0.0.1", 0, runs_root=runs)
    try:
        run = _json(server.url + "r/fx1/api/run")
        records = run["records"]
        assert (records["available"], records["root"], records["reason"]) == (True, ".hypergraph/graph/record", None)
        late, early = records["records"]
        assert late == {"slug": "late-owl-0002", "title": "late-owl-0002 — it's a record",
                        "created_at": "2026-10-01T10:30:00+00:00", "iteration": None, "more": 0,
                        "artifacts": [{"path": "docs/probes/fx1/README.md", "kind": "text",
                                       "bytes": (checkout / "docs/probes/fx1/README.md").stat().st_size}]}
        # Landed in iteration 2: the first whose last step is not older than it.
        assert early["iteration"] == 2 and early["more"] == 0
        # A named file, a named directory's own files (not deeper), a trailing period
        # dropped; never HTML, a symlink, a missing file, or a path not rooted at docs/.
        assert [a["path"] for a in early["artifacts"]] == [
            "docs/probes/other/shot.png", "docs/probes/other/sub/a.json", "docs/probes/other/sub/b.png",
            "docs/GUIDE.md"]
        assert [item["records"] for item in run["iterations"]] == [[], ["early-fox-0001"], []]
        assert "records" not in _json(server.url + "api/runs")["runs"][0]
        status, headers, body = _get(server.url + "r/fx1/linked/docs/probes/other/shot.png")
        assert status == 200 and body == PNG_1PX and headers["content-type"] == "image/png"
        assert headers["content-security-policy"] == "sandbox" and headers["x-content-type-options"] == "nosniff"
        assert _get(server.url + "r/fx1/linked/docs/GUIDE.md")[2].startswith(b"# Guide")
        # In a docs/probes/<dir>/ a record names a path in, so a README's own images resolve.
        for path in ("docs/probes/other/unnamed.png", "docs/probes/other/sub/deeper/c.md",
                     "docs/probes/fx1/sweep/hero.png"):
            assert _get(server.url + "r/fx1/linked/" + path)[0] == 200, path
        for path in ("r/fx1/linked/docs/SECRET.md", "r/fx1/linked/docs/probes/third/x.md",
                     "r/fx1/linked/docs/page.html", "r/fx1/linked/docs/escape.md",
                     "r/fx1/linked/docs/probes/fx1/escape.md", "r/fx1/linked/docs/probes/fx1/linked/secret.md",
                     "r/fx1/linked/docs/probes/fx1/.secret.md", "r/fx1/linked/docs/probes/other/../../SECRET.md",
                     "r/fx1/linked/docs/probes/other/%2E%2E/%2E%2E/SECRET.md", "r/fx1/linked/docs/probes/other/sub",
                     "r/fx1/linked/.ouroboros/goal.md", "r/fx1/linked/docs", "r/fx1/linked/",
                     "r/missing/linked/docs/GUIDE.md"):
            assert _get(server.url + path)[0] == 404, path
        # fx2's own record, and only it; a record with no Repo section belongs to no run.
        fx2 = _json(server.url + "r/fx2/api/run")["records"]["records"]
        assert [r["slug"] for r in fx2] == ["other-run-0003"]
        assert [a["path"] for a in fx2[0]["artifacts"]] == ["docs/SECRET.md", "docs/probes/third/x.md"]
        assert _get(server.url + "r/fx2/linked/docs/SECRET.md")[0] == 200
        # A new record appears on the next read; serving wrote nothing.
        (checkout / ".hypergraph/graph/record/new-day-0005.md").write_text(_record(
            "new-day-0005", "ouroboros/fx1", "2026-10-01T09:00:00+00:00", "Nothing named."))
        assert [r["slug"] for r in _json(server.url + "r/fx1/api/run")["records"]["records"]] == [
            "late-owl-0002", "early-fox-0001", "new-day-0005"]
        assert subprocess.run(["git", "-C", str(checkout), "status", "--porcelain"], capture_output=True,
                              text=True, check=True).stdout.split() == [
            "M", ".ouroboros/goal.md", "??", ".hypergraph/", "??", ".ouroboros/runs/", "??", "docs/"]
    finally:
        server.shutdown()
        server.server_close()


def test_records_outside_a_checkout_are_refused(app_with_runs, tmp_path) -> None:
    _runs_dir, server = app_with_runs
    records = _json(server.url + "r/fx1/api/run")["records"]
    assert records["available"] is False and records["records"] == []
    assert records["reason"] == "the runs directory is not a checkout's .ouroboros/runs"
    assert _get(server.url + "r/fx1/linked/docs/GUIDE.md")[0] == 404
    from cadex_cli.review_server import OuroborosRuns

    runs = OuroborosRuns(_checkout_with_runs(tmp_path))
    assert runs.records("fx1", "ouroboros/fx1", [])["reason"] == (
        ".hypergraph/graph/record is not a directory of the checkout")
