# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The design's history in the 3D viewport (ADR-547, orun3 V3).

``/api/model/revision/<ordinal>`` serves one stored revision's retained
model (ADR-546 keeps it), the revision before it as a ghost and the parts
whose digest changed; ``/mesh/revision/<sha256>.stl`` serves one kept part.
The server half is pinned here with a hand-written store and no engine. The
browser half writes a real biped through the real engine three times and
scrubs the timeline across all three, then drops one revision's row the way
a store from before ADR-546 lacks it, and watches the page say so.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK
from cadex_cli.review_server import serve
from cadex_cli.revision_meshes import INDEX_NAME, NOT_RETAINED, PARTS_DIR, SCHEMA, revision_model, store_root
from test_review_server import _get, _json, _model_state, _open, browser, needs_browser  # noqa: F401  (fixture)
from test_revision_meshes import BIPED

PLACED = {"position_mm": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}


def _tess(scale: float) -> tuple[str, bytes, bytes]:
    """One triangle as a ``cadex-tessellation-v1`` buffer and its sidecar."""

    import struct
    vertices = struct.pack("<9f", 0, 0, 0, scale, 0, 0, 0, scale, 0)
    triangles = struct.pack("<3I", 0, 1, 2)
    data = vertices + triangles
    sha = hashlib.sha256(data).hexdigest()
    sidecar = {"schema": "cadex-tessellation-v1", "byte_order": "little", "artifact_path": f"{sha}.tess.bin",
               "counts": {"vertices": 3, "triangles": 1},
               "layout": {"vertices": {"dtype": "f32", "offset": 0, "bytes": len(vertices)},
                          "triangles": {"dtype": "u32", "offset": len(vertices), "bytes": len(triangles)}}}
    return sha, data, json.dumps(sidecar).encode()


def _biped_store(root: Path) -> dict[str, str]:
    """A four-revision biped trail: 1 not retained, 2 to 4 retained, the
    foot changing at 3 and the torso moving (not changing) at 4."""

    revisions = [c * 64 for c in "abcd"]
    trail = root / "script_history"
    trail.mkdir(parents=True)
    (trail / "history.json").write_text(json.dumps({"entries": [
        {"ordinal": n, "revision": rev, "file": f"{n:04d}.py", "saved_at": f"2026-10-05T10:0{n}:00Z"}
        for n, rev in enumerate(revisions, start=1)]}))
    parts = store_root(root) / PARTS_DIR
    parts.mkdir(parents=True)
    shas = {}
    for name, scale in (("torso", 60.0), ("foot_a", 40.0), ("foot_b", 70.0)):
        sha, data, sidecar = _tess(scale)
        (parts / f"{sha}.tess.bin").write_bytes(data)
        (parts / f"{sha}.tess.json").write_bytes(sidecar)
        shas[name] = sha

    def row(n: int, foot: str, torso_z: float) -> dict:
        moved = {"position_mm": [0.0, 0.0, torso_z], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}
        return {"ordinal": n, "revision": revisions[n - 1], "digest": f"d{n}",
                "parts": {"torso": {"sha256": shas["torso"]}, "foot_l": {"sha256": shas[foot]}},
                "components": [{"name": "torso", "output": "torso", "placement": moved},
                               {"name": "foot_l", "output": "foot_l", "placement": PLACED}]}

    (store_root(root) / INDEX_NAME).write_text(json.dumps({"schema": SCHEMA, "revisions": {
        "2": row(2, "foot_a", 0.0), "3": row(3, "foot_b", 0.0), "4": row(4, "foot_b", 5.0)}}))
    return shas


def test_a_revision_model_carries_its_ghost_and_the_parts_that_changed(tmp_path) -> None:
    root = tmp_path / "orun3-biped-history"
    shas = _biped_store(root)
    three = revision_model(root, 3)
    assert three["available"] and three["previous"]["ordinal"] == 2 and three["previous"]["available"]
    assert three["changed"] == ["foot_l"] and three["compare"] == "against revision 2"
    by_name = {c["name"]: c for c in three["components"]}
    assert by_name["foot_l"]["changed"] and not by_name["torso"]["changed"]
    assert by_name["foot_l"]["mesh"] == f"/mesh/revision/{shas['foot_b']}.stl"
    assert {c["name"]: c["sha256"] for c in three["previous"]["components"]}["foot_l"] == shas["foot_a"]
    # A part moved but not rebuilt is not a changed part.
    assert revision_model(root, 4)["changed"] == []

    # The revision before 2 was never kept: no ghost, no comparison, and no borrowing.
    two = revision_model(root, 2)
    assert two["available"] and two["changed"] is None and two["previous"]["available"] is False
    assert two["previous"]["components"] == [] and "was not retained" in two["compare"]
    one = revision_model(root, 1)
    assert one["available"] is False and one["reason"] == NOT_RETAINED and one["components"] == []
    assert revision_model(root, 9) is None


def test_the_routes_serve_a_kept_part_and_refuse_anything_else(tmp_path) -> None:
    root = tmp_path / "orun3-biped-history"
    shas = _biped_store(root)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        trail = _json(server.url + "api/project")["revisions"]
        assert [(e["ordinal"], e["retained"]) for e in trail] == [(4, True), (3, True), (2, True), (1, False)]
        assert trail[3]["retained_reason"] == NOT_RETAINED and "retained_reason" not in trail[0]
        assert _json(server.url + "api/model/revision/3")["changed"] == ["foot_l"]
        for missing in ("api/model/revision/9", "api/model/revision/x", "mesh/revision/" + "0" * 64 + ".stl",
                        "mesh/revision/..%2Findex.json.stl", "mesh/revision/" + shas["torso"].upper() + ".stl"):
            assert _get(server.url + missing)[0] == 404, missing
        status, headers, body = _get(server.url + f"mesh/revision/{shas['foot_b']}.stl")
        assert status == 200 and headers["content-type"].startswith("model/stl")
        assert len(body) == 84 + 50  # one triangle
        assert _get(server.url + f"mesh/revision/{shas['foot_b']}.stl", {"If-None-Match": headers["etag"]})[0] == 304
        # A blob whose bytes no longer hash to its name is not served as that part.
        (store_root(root) / PARTS_DIR / f"{shas['torso']}.tess.bin").write_bytes(b"\0" * 48)
        assert _get(server.url + f"mesh/revision/{shas['torso']}.stl")[0] == 404
    finally:
        server.shutdown()
        server.server_close()


def _run(capsys, *argv: str) -> dict:
    code = main([*argv, "--json"])
    out = json.loads(capsys.readouterr().out)
    assert code == EXIT_OK, out
    return out


SHOWN = "window.cadexReview.revisions().model && window.cadexReview.revisions().model.ordinal"
LOADED = "document.getElementById('model-status').dataset.state === 'loaded'"


def _menu(page) -> list[tuple[int, bool]]:
    return [tuple(row) for row in page.evaluate(
        "Array.from(document.querySelectorAll('#revision-list li')).map("
        "li => [Number(li.dataset.ordinal), li.dataset.current === 'true'])")]


@needs_browser
def test_the_timeline_scrubs_three_real_revisions_with_a_ghost_and_a_tint(engine, tmp_path, browser, capsys) -> None:
    root = tmp_path / "orun3-biped-timeline"
    (tmp_path / "biped.py").write_text(BIPED, encoding="utf-8")
    project = ["--project", str(root)]
    _run(capsys, "script", "--set", str(tmp_path / "biped.py"), *project)
    _run(capsys, "params", "--set", "foot=55", *project)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        assert _model_state(page) == "loaded"
        # Not the source yet: the accepted model stands and the timeline is hidden.
        assert page.evaluate("document.getElementById('revision-timeline').hidden")
        assert page.evaluate("Array.from(document.getElementById('view3d-source').options).some(o => o.value === 'revisions')")
        # A third revision lands while the page is open.
        _run(capsys, "params", "--set", "foot=70", *project)
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        page.evaluate("window.cadexReview.setSource('revisions')", await_promise=True)
        page.wait_for(SHOWN + " === 3 && " + LOADED, timeout=30)
        assert not page.evaluate("document.getElementById('revision-timeline').hidden")
        assert page.evaluate("document.getElementById('revision-timeline').dataset.follow") == "true"

        # The menu and the timeline agree on the ordinals and on which is current.
        revisions = page.evaluate("window.cadexReview.revisions()")
        assert [(s["ordinal"], s["current"]) for s in revisions["stops"]] == list(reversed(_menu(page))) == \
            [(1, False), (2, False), (3, True)]
        assert all(s["retained"] for s in revisions["stops"])

        info, ink = page.evaluate("[getComputedStyle(document.documentElement).getPropertyValue('--info').trim(),"
                                  " getComputedStyle(document.documentElement).getPropertyValue('--paper-ink').trim()]")
        # Newest: the foot changed against revision 2, so it is tinted and its old self is the ghost.
        stats = page.evaluate("window.cadexReview.viewer().stats()")
        assert stats["components"] == 4 and stats["ghost"] == ["foot_l"]
        assert stats["colours"]["foot_l"] == info and stats["colours"]["torso"] == ink
        assert revisions["model"]["changed"] == ["foot_l"] and revisions["model"]["previous"] == 2
        label = page.evaluate("document.getElementById('revision-label').textContent")
        assert label.startswith("revision 3 · current") and "3/3" in label
        assert "changed: foot_l · against revision 2" in page.evaluate(
            "document.getElementById('revision-status').textContent")

        # Scrub back: each stop is that revision's own model.
        assert page.evaluate("window.cadexReview.pickRevision(1)") == 2
        page.wait_for(SHOWN + " === 2 && " + LOADED, timeout=30)
        assert page.evaluate("document.getElementById('revision-timeline').dataset.follow") == "false"
        assert page.evaluate("window.cadexReview.viewer().stats().ghost") == ["foot_l"]
        foot_2 = page.evaluate("window.cadexReview.revisions().model.parts.foot_l")
        assert page.evaluate("window.cadexReview.pickRevision(0)") == 1
        page.wait_for(SHOWN + " === 1 && " + LOADED, timeout=30)
        first = page.evaluate("window.cadexReview.viewer().stats()")
        # The first revision has nothing before it: no ghost, nothing tinted.
        assert first["ghost"] == [] and set(first["colours"].values()) == {ink}
        assert "the first stored revision" in page.evaluate("document.getElementById('revision-status').textContent")
        # Its own 40 mm foot, not the 55 mm one; the torso is the same part throughout.
        parts_1 = page.evaluate("window.cadexReview.revisions().model.parts")
        assert parts_1["foot_l"] != foot_2 and parts_1["torso"] == revisions["model"]["parts"]["torso"]

        # The Revisions menu opens a row on the timeline; back at the newest end it follows again.
        page.evaluate("document.querySelector('#revision-list li[data-ordinal=\"2\"]').click()")
        page.wait_for(SHOWN + " === 2 && " + LOADED, timeout=30)
        assert page.evaluate("window.cadexReview.pickRevision(2)") is None
        page.wait_for(SHOWN + " === 3 && " + LOADED, timeout=30)
        assert page.evaluate("document.getElementById('revision-timeline').dataset.follow") == "true"

        # A store from before ADR-546 has no row for revision 1: the page says so and draws nothing.
        index_path = store_root(root) / INDEX_NAME
        index = json.loads(index_path.read_text())
        del index["revisions"]["1"]
        index_path.write_text(json.dumps(index))
        page.evaluate("window.cadexReview.refresh()", await_promise=True)
        page.evaluate("window.cadexReview.pickRevision(0)")
        page.wait_for("document.getElementById('model-status').dataset.state === 'missing'", timeout=30)
        assert page.evaluate("document.getElementById('revision-timeline').dataset.state") == "missing"
        assert page.evaluate("window.cadexReview.viewer().stats().components") == 0
        assert page.evaluate("document.getElementById('revision-status').textContent") == "not shown: " + NOT_RETAINED
        # Its successor still draws, with nothing to compare against and no ghost.
        page.evaluate("window.cadexReview.pickRevision(1)")
        page.wait_for(SHOWN + " === 2 && " + LOADED, timeout=30)
        assert page.evaluate("window.cadexReview.viewer().stats().ghost") == []
        assert "revision 1 was not retained" in page.evaluate("document.getElementById('revision-status').textContent")
        assert page.evaluate("window.cadexReview.state().stale") is False
    finally:
        server.shutdown()
        server.server_close()
