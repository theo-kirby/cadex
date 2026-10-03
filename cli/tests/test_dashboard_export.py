# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The dashboard's exports, orun2 D2 item 6 (ADR-509).

The Export button is ``cadex export`` run by the server into the project's
ignored ``review/export/<revision>/``, behind the same per-launch token as
every other write; what it wrote is offered for download by name, for the
accepted revision only. Proved with no engine for the guard and the
allowlist, then against a real engine in headless Chromium: the page
exports the plate and the browser downloads a STEP and an STL whose bytes
are what they claim, and the concept sheet ``cadex render`` drew downloads
as a PNG.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import struct

import pytest

import cadex_cli.review_server as review_server
from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK
from cadex_cli.walk import Leg
from test_dashboard_writes import _post, _token, app, plate_app  # noqa: F401
from test_review_server import _get, _json, _open, _model_state, browser, needs_browser  # noqa: F401

REVISION = "a" * 64


@pytest.fixture
def exported(app, monkeypatch):
    """An app whose biped project has ``REVISION`` accepted, and a fake ``cadex export``."""

    projects, server = app
    identity = {"available": True, "revision": REVISION, "digest": "d" * 64}
    monkeypatch.setattr(review_server, "read_accepted_identity", lambda root: dict(identity))
    calls = []

    def fake_leg(name, argv, *, capture=True, timeout=0.0):
        calls.append((name, list(argv), timeout))
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "plate.step").write_bytes(b"ISO-10303-21;\nEND-ISO-10303-21;\n")
        (out / "plate.stl").write_bytes(b"solid \nendsolid \n")
        (out / "notes.txt").write_bytes(b"not offered")
        return Leg(name=name, argv=list(argv), code=EXIT_OK, seconds=0.5,
                   envelope={"ok": True, "accepted_revision": identity["revision"], "digest": "d" * 64})

    monkeypatch.setattr(review_server, "run_leg", fake_leg)
    return projects / "biped", server, calls, identity


def test_an_export_needs_the_token_and_is_the_cli_export_command(exported) -> None:
    root, server, calls, _identity = exported
    url = server.url + "p/biped/api/export"
    assert _post(url, {})[0] == 403
    assert _post(url, {}, {"X-Cadex-Token": "x" * 43})[0] == 403
    token = _token(server.url + "p/biped/")
    assert _post(url, {}, {"X-Cadex-Token": token, "Origin": "http://evil.example"})[0] == 403
    for bad in ({"formats": "step"}, {"formats": []}, {"formats": ["obj"]}, {"formats": ["step", "step"]},
                {"formats": ["--out=/tmp"]}):
        assert _post(url, bad, {"X-Cadex-Token": token})[0] == 400, bad
    assert calls == []
    # Nothing exported yet: the block says so and offers no file.
    listing = _json(server.url + "p/biped/api/project")["exports"]
    assert listing == {"available": False, "revision": REVISION,
                       "reason": "not exported yet: Export runs cadex export for this revision"}
    status, reply = _post(url, {}, {"X-Cadex-Token": token})
    assert status == 200 and reply["ok"] is True and reply["revision"] == REVISION, reply
    out = root.resolve() / "review" / "export" / REVISION
    assert calls == [("export", ["export", "--project", str(root.resolve()), "--out", str(out),
                                 "--format", "step,stl", "--json"], review_server.WRITE_TIMEOUT_S)]
    # Offered by name, for this revision, and only the export suffixes.
    names = [entry["name"] for entry in reply["exports"]["files"]]
    assert names == ["plate.step", "plate.stl"]
    assert _json(server.url + "p/biped/api/project")["exports"] == reply["exports"]
    status, headers, body = _get(server.url + "p/biped/export/%s/plate.step?download=1" % REVISION)
    assert status == 200 and body.startswith(b"ISO-10303-21;")
    assert 'attachment; filename="plate.step"' in headers["content-disposition"]
    for missing in ("export/%s/notes.txt" % REVISION, "export/%s/plate.brep" % REVISION,
                    "export/%s/plate.step" % ("b" * 64), "export/%s/..%%2Fplate.step" % REVISION,
                    "export/%s" % REVISION):
        assert _get(server.url + "p/biped/" + missing)[0] == 404, missing
    assert _post(url, {"formats": ["brep"]}, {"X-Cadex-Token": token})[0] == 200
    assert calls[-1][1][5:7] == ["--format", "brep"]


def test_a_moved_revision_leaves_no_export_under_the_old_name(exported) -> None:
    """A write landing between the button and the child's lock: the files are removed."""

    root, server, calls, identity = exported
    original = review_server.run_leg

    def moving_leg(name, argv, **kwargs):
        leg = original(name, argv, **kwargs)
        leg.envelope["accepted_revision"] = "c" * 64
        return leg

    review_server.run_leg = moving_leg
    try:
        status, reply = _post(server.url + "p/biped/api/export", {},
                              {"X-Cadex-Token": _token(server.url + "p/biped/")})
    finally:
        review_server.run_leg = original
    assert status == 409 and reply["ok"] is False and "export again" in reply["error"]
    assert not (root / "review" / "export" / REVISION).exists()
    assert _json(server.url + "p/biped/api/project")["exports"]["available"] is False


def test_no_accepted_revision_is_nothing_to_export(app, monkeypatch) -> None:
    _projects, server = app
    monkeypatch.setattr(review_server, "read_accepted_identity",
                        lambda root: {"available": False, "reason": "no manifest"})
    monkeypatch.setattr(review_server, "run_leg", lambda *a, **k: pytest.fail("spawned"))
    status, reply = _post(server.url + "p/biped/api/export", {},
                          {"X-Cadex-Token": _token(server.url + "p/biped/")})
    assert status == 409 and "no accepted revision" in reply["error"]
    assert _json(server.url + "p/biped/api/project")["exports"]["available"] is False


# -- against a real engine -----------------------------------------------


def _stl_extents(text: str) -> list[float]:
    vertices = [[float(v) for v in match.groups()] for match in
                re.finditer(r"vertex\s+(\S+)\s+(\S+)\s+(\S+)", text)]
    return [round(max(v[i] for v in vertices) - min(v[i] for v in vertices), 3) for i in range(3)]


@needs_browser
def test_browser_exports_step_and_stl_and_downloads_the_concept_sheet(plate_app, browser, capsys) -> None:
    root, server = plate_app
    assert main(["render", "--project", str(root), "--json"]) == EXIT_OK
    capsys.readouterr()
    page = _open(browser, server.url + "p/plate/")
    assert _model_state(page) == "loaded"
    revision = page.evaluate("window.cadexReview.state().revision")
    assert "not exported yet" in page.text("#export-list")

    page.wait_for("!document.getElementById('export-run').disabled", timeout=30)
    page.click("#export-run")
    page.wait_for("document.getElementById('export-status').dataset.state === 'done'"
                  " || document.getElementById('export-status').dataset.state === 'error'", timeout=180)
    assert page.evaluate("document.getElementById('export-status').dataset.state") == "done", \
        page.text("#export-status")
    reply = page.evaluate("window.cadexReview.lastExport()")
    assert reply["accepted_revision"] == revision and reply["command"][:2] == ["cadex", "export"]
    page.wait_for("document.querySelectorAll('#export-list li[data-name]').length === 2", timeout=30)
    # The CLI's own export: its PROGRESS.md row names the command.
    assert "export" in (root / "PROGRESS.md").read_text()

    step = page.download('#export-list li[data-name="plate.step"] a', timeout=30)
    data = step.path.read_bytes()
    assert step.path.name == "plate.step" and step.received_bytes == len(data) > 0
    assert data.startswith(b"ISO-10303-21;") and b"HEADER;" in data
    assert data.rstrip().endswith(b"END-ISO-10303-21;")
    assert b"MANIFOLD_SOLID_BREP" in data or b"ADVANCED_BREP_SHAPE_REPRESENTATION" in data

    stl = page.download('#export-list li[data-name="plate.stl"] a', timeout=30)
    text = stl.path.read_text(encoding="ascii")
    assert stl.path.name == "plate.stl" and text.startswith("solid") and text.rstrip().endswith(
        text.splitlines()[0].replace("solid", "endsolid", 1).rstrip())
    assert text.count("facet normal") == 12  # a box: six faces, two triangles each
    assert _stl_extents(text) == [30.0, 20.0, 6.0]

    sheet = page.download("#concept-download", timeout=30)
    png = sheet.path.read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR"
    width, height = struct.unpack(">2I", png[16:24])
    assert width > 0 and height > 0
    summary = json.loads((root / "review" / "render" / "summary.json").read_text())
    assert summary["revision"] == revision
    assert png == (root / "review" / "render" / "sheet.png").read_bytes()
