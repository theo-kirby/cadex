# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The dashboard's HTTP API is a documented contract (ADR-552, orun3 P1).

``docs/CLI.md``'s "The HTTP API" table lists every ``GET /api/...`` route
and its top-level reply keys. ``ReviewHandler`` dispatches from
``API_ROUTES`` and nothing else, and ``API_RESPONSE_KEYS`` holds the keys.
The three are held together here, and against the live replies of one
fixture biped that reaches every route in each of its shapes, the way
``docs/INTEGRATION.md``'s op table is held to ``OP_ARG_SPECS``.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
import re
import shutil

import pytest

from cadex_cli import review_server
from cadex_cli.review_record import WALK_LOCK_FILENAME
from cadex_cli.review_server import (
    API_RESPONSE_KEYS, API_ROUTES, APP_API_ROUTES, ReviewHandler, serve, serve_projects)
from review_helpers import RUN, _checkpoint_trace, _checkpoint_training_run as _training_run
from review_helpers import _passing
from review_helpers import REVISION_A, REVISION_B, _manifest, _project
from review_helpers import _biped_store
from review_helpers import _escaped_run, _get, _json, _mesh_run, _rewrite_record, _stage_accepted
from review_helpers import _training_run as _untraced_run
from review_helpers import reference_bundle
from review_helpers import motor_trace, write_policy

REPO = Path(__file__).resolve().parents[2]
STATIC = REPO / "cli" / "cadex_cli" / "review_static"
#: The per-viewer conveniences the page may keep in ``localStorage``.
BROWSER_KEYS = {"cadex.theme", "cadex.layout.v6", "cadex.render", "cadex.meshlines", "cadex.meshlines.strength",
                "cadex.reflections", "cadex.look", "cadex.occlusion", "cadex.detail", "cadex.outliner.group",
                "cadex.outliner.folded", "cadex.follow", "cadex.heat", "cadex.activations.views"}


def _documented() -> dict[str, tuple[set[str], set[str]]]:
    """``docs/CLI.md``'s API table: route -> (always, when they apply)."""

    doc = (REPO / "docs" / "CLI.md").read_text(encoding="utf-8")
    section = doc.partition("### The HTTP API (ADR-552)")[2].partition("\n### ")[0]
    table: dict[str, tuple[set[str], set[str]]] = {}
    for line in section.splitlines():
        match = re.match(r"\| `GET api/([^`]+)` \|", line)
        if match is None:
            continue
        cells = line.split("|")
        assert match[1] not in table, f"{match[1]} is listed twice"
        table[match[1]] = (set(re.findall(r"`([a-z0-9_]+)`", cells[3])),
                           set(re.findall(r"`([a-z0-9_]+)`", cells[4])))
    return table


def test_the_doc_table_is_the_route_table_and_its_keys() -> None:
    documented = _documented()
    served = set(API_ROUTES) | set(APP_API_ROUTES)
    assert set(documented) == served, (
        "docs/CLI.md's HTTP API table and API_ROUTES disagree.\n"
        f"  documented but not served: {sorted(set(documented) - served)}\n"
        f"  served but not documented: {sorted(served - set(documented))}")
    assert set(API_RESPONSE_KEYS) == served
    for route, (always, sometimes) in API_RESPONSE_KEYS.items():
        assert documented[route] == (set(always), set(sometimes)), route
        assert not always & sometimes, route


def test_the_router_dispatches_from_the_table_alone() -> None:
    """One ``_api_`` method per route, none without a route; nothing in
    ``_route`` names an API path of its own."""

    methods = {name[len("_api_"):] for name in dir(ReviewHandler) if name.startswith("_api_")}
    assert methods == set(review_server._API_HANDLERS.values())
    assert set(review_server._API_HANDLERS) == set(API_ROUTES)
    for route in API_ROUTES:
        segments = [part if not part.startswith("<") else "x" for part in route.split("/")]
        assert review_server.match_api_route(API_ROUTES, segments) == (
            route, ["x"] * route.count("<"))
    for handler in (ReviewHandler._route, ReviewHandler._route_projects):
        lines = [line for line in inspect.getsource(handler).splitlines() if '"api"' in line]
        assert lines and all("match_api_route" in line or line.strip() == 'if head == "api":'
                             for line in lines), lines


#: The course a trace says its episode stood on (ADR-734): one box.
COURSE = {"kind": "boxes", "x_range_mm": [-500.0, 500.0], "y_range_mm": [-500.0, 500.0],
          "lowest_mm": 0.0, "highest_mm": 40.0, "plane_z_mm": 0.0,
          "boxes": [{"shape": "block", "centre_mm": [0.0, 0.0, -5.0],
                     "rotation_xyzw": [0.0, 0.0, 0.0, 1.0], "half_mm": [500.0, 500.0, 45.0]}]}


@pytest.fixture
def biped(tmp_path):
    """A biped that reaches every route in each of its shapes: accepted with
    a model; a walk training with a ready and a failed checkpoint; runs with
    and without their rollout, one outside the project; a revision trail with
    one unretained revision; an evaluation; a run that borrows the accepted
    model."""

    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    _mesh_run(root, "first", revision=REVISION_A)
    second = _mesh_run(root, "second", revision=REVISION_B)
    # A rollout with timed frames, so its playback has frames to play, on a
    # one-box course (ADR-734).
    (second / "rollout" / "assembly-simulation-trace.json").write_text(json.dumps({
        **motor_trace("000001", write_policy(second / "policy.cxpolicy")), "terrain": COURSE}))
    _rewrite_record(second, artifacts={**json.loads((second / "run.json").read_text())["artifacts"],
                                       "policy": "policy.cxpolicy"})
    broken = _mesh_run(root, "broken", revision=REVISION_A)
    for path in (broken / "rollout").iterdir():
        path.unlink()
    (broken / "rollout").rmdir()
    _escaped_run(root, tmp_path)
    run = _training_run(root)
    train = run / "train"
    # A checkpoint with its policy beside it and a trace that records its motors (ADR-727); a
    # policy file the page cannot run; and the walk's own policy.
    header = write_policy(train / "walk.000040.cxpolicy")
    (train / "walk.000040.rollout-trace.json").write_text(json.dumps(
        {**motor_trace("000040", header), "terrain": COURSE}))
    (train / "walk.000080.cxpolicy").write_bytes(b"not yet rolled out")
    write_policy(train / "walk.cxpolicy", seed=5)
    _rewrite_record(run, artifacts={**json.loads((run / "run.json").read_text())["artifacts"],
                                    "policy": "train/walk.cxpolicy"})
    (train / "walk.000060.rollout-failed.json").write_text(json.dumps({
        "schema": "cadex-checkpoint-rollout-failure-v1", "checkpoint": "walk.000060.cxpolicy",
        "tag": "000060", "iteration": 59, "reason": "child_failed", "error": "the rollout exited 1"}))
    staging = _stage_accepted(root, REVISION_B)
    # A task with a gait reference and one without (ADR-703).
    reference_bundle(staging, "walk")
    reference_bundle(staging, "stand", reference=False)
    # Training at the accepted revision with no rollout yet: its model is the
    # accepted one, borrowed and labelled so.
    _untraced_run(root, "borrowing", revision=REVISION_B)
    _biped_store(root)
    _passing(root)
    return root


#: Each route, the paths that reach it in the fixture, and the 404s it gives.
PROBES = {
    "project": (["api/project"], []),
    "run/<run>": (["api/run/first", "api/run/broken", "api/run/escaped", f"api/run/{RUN}", "api/run/killed"],
                  ["api/run/nope"]),
    "policy-origin/<run>": (["api/policy-origin/first", "api/policy-origin/escaped"],
                            ["api/policy-origin/nope"]),
    "evaluation/<name>": (["api/evaluation/steady"], ["api/evaluation/nope"]),
    "model/accepted": (["api/model/accepted"], []),
    "model/revision/<ordinal>": (["api/model/revision/1", "api/model/revision/2", "api/model/revision/3"],
                                 ["api/model/revision/9", "api/model/revision/x"]),
    "model/run/<run>": (["api/model/run/first", "api/model/run/broken", f"api/model/run/{RUN}",
                         "api/model/run/borrowing"],
                        ["api/model/run/nope"]),
    "playback/run/<run>": (["api/playback/run/second", "api/playback/run/broken"], ["api/playback/run/nope"]),
    "playback/checkpoint/<run>/<stem>": (
        [f"api/playback/checkpoint/{RUN}/walk.000040", f"api/playback/checkpoint/{RUN}/walk.000060"],
        [f"api/playback/checkpoint/{RUN}/walk.000080", "api/playback/checkpoint/nope/walk.000040"]),
    "playback/reference/<task>": (["api/playback/reference/walk", "api/playback/reference/stand"],
                                  ["api/playback/reference/nope"]),
    "policy/run/<run>": ([f"api/policy/run/{RUN}", "api/policy/run/first"], ["api/policy/run/nope"]),
    "policy/checkpoint/<run>/<stem>": (
        [f"api/policy/checkpoint/{RUN}/walk.000040", f"api/policy/checkpoint/{RUN}/walk.000080"],
        [f"api/policy/checkpoint/{RUN}/walk.000060", "api/policy/checkpoint/nope/walk.000040"]),
}


def _check(route: str, reply: dict, seen: dict[str, set[str]]) -> None:
    always, sometimes = API_RESPONSE_KEYS[route]
    keys = set(reply)
    assert always <= keys, (route, sorted(always - keys))
    assert keys <= always | sometimes, (route, sorted(keys - always - sometimes))
    seen.setdefault(route, set()).update(keys)


def test_every_reply_carries_its_documented_keys_and_nothing_else(biped, tmp_path) -> None:
    assert set(PROBES) == set(API_ROUTES)
    seen: dict[str, set[str]] = {}
    # A walk killed before its verdict: `running` under a lock nobody holds (ADR-559).
    shutil.copytree(biped / "runs" / "first", biped / "runs" / "killed")
    _rewrite_record(biped / "runs" / "killed", status="running")
    (biped / "runs" / "killed" / WALK_LOCK_FILENAME).touch()
    server, _thread = serve(biped, "127.0.0.1", 0)
    try:
        for route, (found, missing) in PROBES.items():
            for path in found:
                _check(route, _json(server.url + path), seen)
            for path in missing:
                status, _headers, body = _get(server.url + path)
                assert status == 404 and set(json.loads(body)) == {"error", "what"}, path
        for path in ("api/", "api/projects", "api/nope", "api/model", "api/model/accepted/x",
                     "api/run", "api/run/first/x"):
            status, _headers, body = _get(server.url + path)
            assert status == 404 and set(json.loads(body)) == {"error", "what"}, path
        # A route the table lists and the fixture reached in its available
        # and unavailable shapes alike.
        played = _json(server.url + f"api/playback/checkpoint/{RUN}/walk.000040")
        failed = _json(server.url + f"api/playback/checkpoint/{RUN}/walk.000060")
        assert played["available"] and not failed["available"]
        assert {"meshes"} <= seen["model/accepted"] and {"compare"} <= seen["model/revision/<ordinal>"]
        assert "policy_store" in seen["run/<run>"] and "playback" in seen["model/run/<run>"]
        assert _json(server.url + "api/run/killed")["recorded_status"] == "running"
    finally:
        server.shutdown()
        server.server_close()

    app, _thread = serve_projects(biped.parent, "127.0.0.1", 0)
    try:
        _check("projects", _json(app.url + "api/projects"), seen)
        for route, (found, _missing) in PROBES.items():
            for path in found[:1]:
                _check(route, _json(app.url + f"p/{biped.name}/" + path), seen)
        assert _get(app.url + "api/project")[0] == 404
    finally:
        app.shutdown()
        app.server_close()
    # Every key the table promises is one some reply was seen to carry; a
    # run record's own optional keys are write_run_record's, and the
    # fixture's walks write all but ``video_render``.
    for route, (always, sometimes) in API_RESPONSE_KEYS.items():
        unseen = (always | sometimes) - seen[route]
        assert unseen <= ({"video_render"} if route == "run/<run>" else set()), (route, sorted(unseen))


def test_the_page_keeps_only_per_viewer_conveniences_in_the_browser() -> None:
    """P1's audit: nothing the page shows lives only in the browser."""

    stored: set[str] = set()
    for path in STATIC.glob("*.js"):
        if path.name.startswith("three"):
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"sessionStorage|indexedDB|document\.cookie", text), path.name
        stored |= set(re.findall(r"(?:readPref|writePref|readStored|writeStored)\('([^']+)'", text))
        stored |= set(re.findall(r"storageKey: '([^']+)'", text))
        stored |= set(re.findall(r"var KEY = '([^']+)'", text))
        calls = len(re.findall(r"localStorage\.(?:getItem|setItem|removeItem)\(", text))
        named = {"review.js": 2, "layout.js": 3, "theme.js": 2, "outliner.js": 2, "heat.js": 2, "activations.js": 2}.get(path.name, 0)
        assert calls == named, (path.name, calls)
    assert stored == BROWSER_KEYS
    doc = (REPO / "docs" / "CLI.md").read_text(encoding="utf-8")
    keeps = doc.partition("**What the browser keeps.**")[2].partition("\n\n")[0]
    assert set(re.findall(r"`(cadex\.[a-z0-9.]+)`", keeps)) == BROWSER_KEYS
