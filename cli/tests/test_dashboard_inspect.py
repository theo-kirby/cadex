# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The dashboard's inspection views, orun2 D2 item 5.

The exploded and section views (ADR-510): the explode slider plays the
engine's own ``assembly.exploded_view`` stages from the solved pose through
the viewer's ``setPoses``, and Cut runs ``cadex section`` and clips the
viewer at the plane it cut. Proved against a real engine in headless
Chromium below the collision view's test.

The collision view's t=0 contact readout (ADR-508): which parts' collision
shapes already touch at the pose every simulation starts from. The engine
measured it when it exported the MJCF; the page lists it under the
collision toggle, and the agent reads the same block through ``inspect
scope=contacts``, so a person and the agent see one fact. Proved against a
real engine in headless Chromium: a post sunk 2 mm into the floor is named,
the page's own slider lifts it clear, and the readout empties.
"""

from __future__ import annotations

import json

import pytest

from cadex_cli.__main__ import main
from cadex_cli.client import CadexdClient, open_project
from cadex_cli.report import EXIT_OK
from pathlib import Path

import cadex_cli.review_server as review_server
from cadex_cli.review_server import (_matrix_placement, exploded_views, initial_contacts, serve_projects,
                                     trace_playback)
from cadex_cli.walk import Leg
from test_dashboard_writes import _post, _token, app  # noqa: F401
from test_train import REAL_TRAINER_PYTHON
from test_review_server import _get, _json, _model_state, _open, browser, needs_browser  # noqa: F401

#: A floor, a block that slides on it and a post that slides on the block.
#: The joints exclude block/floor and block/post from contact, so the one
#: pair that can touch is floor/post, and ``sink`` pushes the post into the
#: floor. Measured on a real build: at 2 mm MuJoCo reports four points,
#: each at -2.0 mm; at 0 mm, face on face, it reports none.
REST = """
p = params(sink=num(2.0, unit="mm", min=0.0, max=5.0, step=0.5))
slab = part.box(200, 100, 10, origin=[-100, -50, -10])
brick = part.box(40, 40, 30, origin=[-20, -20, 0])
peg = part.box(20, 20, 50, origin=[-10, -10, 0])
floor = assembly.component(slab, grounded=True)
block = assembly.component(brick, placement=[0, 0, 0])
post = assembly.component(peg, placement=[60, 0, -p.sink])
rail = assembly.joint("slider",
                      assembly.connector(floor, "origin", offset={"position": [0, 0, 0]}),
                      assembly.connector(block, "origin", offset={"position": [0, 0, 0]}))
lift = assembly.joint("slider",
                      assembly.connector(block, "origin", offset={"position": [60, 0, -p.sink]}),
                      assembly.connector(post, "origin", offset={"position": [0, 0, 0]}))
asm = assembly.assembly([floor, block, post], [rail, lift])
diag = assembly.solve(asm)
model = assembly.mjcf(asm, [
    assembly.body(floor, density_kg_m3=1000,
                  collision=[assembly.collision("box", size_mm=[200, 100, 10], offset={"position": [0, 0, -5]})]),
    assembly.body(block, density_kg_m3=1200,
                  collision=[assembly.collision("box", size_mm=[40, 40, 30], offset={"position": [0, 0, 15]})]),
    assembly.body(post, density_kg_m3=1200,
                  collision=[assembly.collision("box", size_mm=[20, 20, 50], offset={"position": [0, 0, 25]})]),
])
result = {"slab": slab, "brick": brick, "peg": peg, "floor": floor, "block": block, "post": post,
          "rail": rail, "lift": lift, "asm": asm, "diag": diag, "model": model}
"""


def _mjcf(dynamics: dict | None) -> dict:
    data = {"assembly_output": "asm"}
    if dynamics is not None:
        data["dynamics"] = dynamics
    return {"name": "model", "type": "mjcf", "assembly_data": data}


def test_initial_contacts_groups_by_pair_and_says_why_when_absent() -> None:
    def contact(a, b, distance, penetrating):
        return {"component_outputs": [a, b], "distance_mm": distance, "penetrating": penetrating}

    block = initial_contacts({"outputs": [_mjcf({
        "initial_contact_count": 3, "initial_contacts_omitted": 0,
        "initial_contacts": [contact("foot", "floor", 0.0, False),
                             contact("post", "floor", -2.0, True), contact("floor", "post", -1.5, True)]})]})
    assert block["available"] is True and block["count"] == 3 and block["omitted"] == 0
    assert "t=0" in block["source"] and "not the exact solids" in block["source"]
    assert block["pairs"] == [
        {"components": ["floor", "post"], "points": 2, "penetrating": True, "deepest_mm": -2.0},
        {"components": ["floor", "foot"], "points": 1, "penetrating": False, "deepest_mm": 0.0},
    ]
    none = initial_contacts({"outputs": [{"name": "plate", "type": "solid"}]})
    assert none["available"] is False and "no assembly.mjcf output" in none["reason"]
    old = initial_contacts({"outputs": [_mjcf(None)]})
    assert old["available"] is False and "rebuild" in old["reason"]


@pytest.fixture
def rest_app(engine, tmp_path, capsys):
    projects = tmp_path / "projects"
    source = tmp_path / "rest.py"
    source.write_text(REST, encoding="utf-8")
    assert main(["script", "--set", str(source), "--project", str(projects / "rest"), "--json"]) == EXIT_OK
    capsys.readouterr()
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield projects / "rest", server
    finally:
        server.shutdown()
        server.server_close()


def _agent_pairs(engine, root) -> list[dict]:
    """What the agent reads: ``inspect scope=contacts`` through cadexd."""

    with CadexdClient(engine) as client:
        open_project(client, root)
        reply = client.request("inspect", {"scope": "contacts", "path": "/models/0/pairs", "limit": 50})
    assert reply["ok"], reply
    return reply["value"]


def test_the_agent_reads_the_parts_touching_at_rest_that_the_server_serves(engine, rest_app, capsys) -> None:
    """ADR-508's agent half: ``inspect scope=contacts`` and ``/api/model``
    name the same pairs, with no page in the loop (the page's collision
    readout was removed by ADR-533)."""

    from cadex_cli.__main__ import main
    from cadex_cli.report import EXIT_OK

    root, server = rest_app
    served = _json(server.url + "p/rest/api/model/accepted")["contacts"]
    agent = _agent_pairs(engine, root)
    assert agent == served["pairs"]
    assert agent[0]["components"] == ["floor", "post"] and agent[0]["points"] == 4
    assert agent[0]["deepest_mm"] == pytest.approx(-2.0, abs=1e-6)
    # Lift the post through the CLI: the rebuilt export reports nothing touching.
    assert main(["params", "--project", str(root), "--set", "sink=0", "--json"]) == EXIT_OK
    capsys.readouterr()
    assert _json(server.url + "p/rest/api/model/accepted")["contacts"]["pairs"] == []
    assert _agent_pairs(engine, root) == []


# -- the exploded and section views (ADR-510) ------------------------------

#: The engine suite's staged explosion (``test_cadexd_lifecycle``): the
#: revolute joint pulls ``swing`` from its declared [0, 0, 40] onto [12, 0, 4],
#: then two moves lift it 30 mm and slide it 20 mm. The declared placement is
#: deliberately not the solved one, so a viewer that starts from it is caught.
BOOM = """
plate = part.box(40, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[12, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
boom = assembly.exploded_view(asm, [
    {"components": [swing], "transform": [0, 0, 30]},
    {"components": [swing], "transform": [20, 0, 0]},
])
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "boom": boom}
"""


def test_a_solved_matrix_becomes_a_placement() -> None:
    # 90 degrees about Z, translated: x -> y.
    placement = _matrix_placement([0, -1, 0, 5, 1, 0, 0, 6, 0, 0, 1, 7, 0, 0, 0, 1])
    assert placement["position_mm"] == [5.0, 6.0, 7.0]
    assert placement["rotation_xyzw"] == pytest.approx([0, 0, 0.5 ** 0.5, 0.5 ** 0.5])
    # 180 degrees about X: the trace is negative, a different branch.
    assert _matrix_placement([1, 0, 0, 0, 0, -1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1])["rotation_xyzw"] \
        == pytest.approx([1, 0, 0, 0])
    assert _matrix_placement([1, 2]) is None and _matrix_placement(None) is None


def test_exploded_frames_are_cumulative_from_the_assembled_pose() -> None:
    def pose(x, z):
        return {"position_mm": [x, 0.0, z], "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0]}

    record = {"assembly_output": "asm", "stages": [
        {"move_index": 0, "kind": "normal", "component_outputs": ["a"], "poses": {"a": pose(0, 30)}},
        {"move_index": 1, "kind": "normal", "component_outputs": ["b"], "poses": {"b": pose(9, 0)}}],
        "final_poses": {}, "lines": [{"component_output": "a", "start_mm": [0, 0, 0], "end_mm": [0, 0, 30]}]}
    rest = {"position_mm": [0.0, 0.0, 0.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}
    [view] = exploded_views({"outputs": [{"name": "plate", "type": "solid"},
                                         {"name": "boom", "type": "exploded_view", "exploded_view": record}]},
                            {"a": rest, "b": rest, "c": None})
    assert view["output"] == "boom" and view["stages"] == 2 and len(view["frames"]) == 3
    assert view["frames"][0] == {"a": rest, "b": rest}
    assert view["frames"][1]["a"]["position_mm"] == [0.0, 0.0, 30.0] and view["frames"][1]["b"] == rest
    # Stage 2 moves b and keeps a where stage 1 left it.
    assert view["frames"][2]["a"]["position_mm"] == [0.0, 0.0, 30.0]
    assert view["frames"][2]["b"]["position_mm"] == [9.0, 0.0, 0.0]
    assert view["lines"] == [{"component": "a", "start_mm": [0.0, 0.0, 0.0], "end_mm": [0.0, 0.0, 30.0]}]
    assert exploded_views({"outputs": [{"name": "plate"}]}, {}) == []


REVISION = "a" * 64


def test_a_section_needs_the_token_and_is_the_cli_section_command(app, monkeypatch) -> None:
    projects, server = app
    root = projects / "biped"
    monkeypatch.setattr(review_server, "read_accepted_identity",
                        lambda _root: {"available": True, "revision": REVISION, "digest": "d" * 64})
    calls = []

    def fake_leg(name, argv, *, capture=True, timeout=0.0):
        calls.append((name, list(argv), timeout))
        offset = next((float(a.split("=", 1)[1]) for a in argv if a.startswith("--offset-mm=")), 2.5)
        plane = argv[argv.index("--plane") + 1]
        cut = Path(argv[argv.index("--project") + 1]) / "review" / "section" / REVISION / f"{plane}-{offset:.17g}"
        cut.mkdir(parents=True, exist_ok=True)
        (cut / "section.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
        (cut / "summary.json").write_text(json.dumps({
            "revision": REVISION, "plane": plane, "offset_mm": offset,
            "offset_source": "derived" if "--offset-mm" not in " ".join(argv) else "explicit",
            "status": "ok", "objects_cut": 1, "objects": {"a": {"status": "ok"}, "b": {"status": "empty"}},
            "approximation": "tessellation cut"}))
        return Leg(name=name, argv=list(argv), code=0, seconds=0.25,
                   envelope={"ok": True, "accepted_revision": REVISION, "digest": "d" * 64})

    monkeypatch.setattr(review_server, "run_leg", fake_leg)
    url = server.url + "p/biped/api/section"
    assert _post(url, {"plane": "XZ"})[0] == 403
    token = _token(server.url + "p/biped/")
    assert _post(url, {"plane": "XZ"}, {"X-Cadex-Token": token, "Origin": "http://evil.example"})[0] == 403
    for bad in ({}, {"plane": "xz"}, {"plane": "XZ", "offset_mm": "1"}, {"plane": "XZ", "offset_mm": True},
                {"plane": "XZ", "offset_mm": 1e9}, {"plane": "--project=/tmp"}):
        assert _post(url, bad, {"X-Cadex-Token": token})[0] == 400, bad
    assert calls == []
    assert _json(server.url + "p/biped/api/project")["sections"]["available"] is False
    status, reply = _post(url, {"plane": "XZ"}, {"X-Cadex-Token": token})
    assert status == 200 and reply["ok"] is True, reply
    assert calls[-1] == ("section", ["section", "--project", str(root.resolve()), "--plane", "XZ", "--json"],
                         review_server.WRITE_TIMEOUT_S)
    assert reply["cut"]["name"] == "XZ-2.5" and reply["cut"]["missed"] == ["b"]
    # A negative offset travels as one --offset-mm= token, never a flag of its own.
    status, reply = _post(url, {"plane": "XY", "offset_mm": -1.5}, {"X-Cadex-Token": token})
    assert status == 200 and calls[-1][1][5] == "--offset-mm=-1.5" and reply["cut"]["name"] == "XY--1.5"
    cuts = _json(server.url + "p/biped/api/project")["sections"]["cuts"]
    assert {cut["name"] for cut in cuts} == {"XZ-2.5", "XY--1.5"}
    status, headers, body = _get(server.url + "p/biped/" + reply["cut"]["svg"])
    assert status == 200 and headers["content-type"] == "image/svg+xml" and body.startswith(b"<svg")
    for missing in ("section/%s/XY--1.5/summary.json" % REVISION, "section/%s/XZ-9/section.svg" % REVISION,
                    "section/%s/XY--1.5/section.svg" % ("b" * 64), "section/%s/..%%2F/section.svg" % REVISION):
        assert _get(server.url + "p/biped/" + missing)[0] == 404, missing


@pytest.fixture
def boom_app(engine, tmp_path, capsys):
    projects = tmp_path / "projects"
    source = tmp_path / "boom.py"
    source.write_text(BOOM, encoding="utf-8")
    assert main(["script", "--set", str(source), "--project", str(projects / "boom"), "--json"]) == EXIT_OK
    capsys.readouterr()
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield projects / "boom", server
    finally:
        server.shutdown()
        server.server_close()


def _engine_final_poses(root: Path) -> dict:
    """The engine's own ``final_poses``, read from the accepted attempt's result."""

    manifest = json.loads((root / "script.json").read_text())
    result = json.loads((root / manifest["accepted_attempt"]["staging"] / "result.json").read_text())
    [record] = [o["exploded_view"] for o in result["outputs"] if "exploded_view" in o]
    return record["final_poses"]


def _poses(page) -> dict:
    return page.evaluate("window.cadexReview.viewer().stats().poses")


# -- rollout playback (ADR-511) --------------------------------------------

def _frame(index, time_s, z, q, command=None):
    frame = {"frame_index": index, "frame_kind": "input" if time_s is None else "solver_output",
             "nominal_time_s": time_s,
             "component_placements": {"arm": {"position_mm": [0.0, 0.0, z], "rotation_xyzw": q}}}
    if command is not None:
        frame["actuator_commands"] = [command]
    return frame


def test_playback_is_timed_frames_with_a_continuous_quaternion_sign() -> None:
    half = 0.5 ** 0.5
    trace = {"schema": review_server.TRACE_SCHEMA, "actuator_channels": [
        {"actuator": "j/motor", "unit": "n", "low": -4.0, "high": 4.0}],
        "frames": [_frame(0, None, 0.0, [0, 0, 0, 1]),
                   _frame(1, 0.0, 0.0, [0, 0, 0, 1]),
                   # The same rotation as -q: the sign flips back so it stays continuous.
                   _frame(3, 0.08, 2.0, [0, 0, -half, -half], 0.5),
                   _frame(2, 0.04, 1.0, [0, 0, 0.1, 0.99], 0.25)]}
    playback = trace_playback(trace)
    assert playback["available"] is True
    # The untimed input frame is dropped; the rest are in time order.
    assert playback["times_s"] == [0.0, 0.04, 0.08] and playback["duration_s"] == 0.08
    assert [f["arm"]["position_mm"][2] for f in playback["frames"]] == [0.0, 1.0, 2.0]
    assert playback["frames"][2]["arm"]["rotation_xyzw"] == pytest.approx([0, 0, half, half])
    # The reset frame was produced by no command.
    assert playback["commands"] == [None, [0.25], [0.5]]
    assert playback["channels"] == [{"actuator": "j/motor", "unit": "n", "low": -4.0, "high": 4.0}]
    assert trace_playback({"schema": "other"})["available"] is False
    untimed = trace_playback({"schema": review_server.TRACE_SCHEMA, "frames": [_frame(0, None, 0.0, [0, 0, 0, 1])]})
    assert untimed == {"available": False, "reason": "the trace has no timed frames with placements"}


@pytest.fixture
def carriage_run(engine, tmp_path, capsys, cpu_training):
    """A real walk of the linear carriage: one training iteration, then a rollout."""

    projects = tmp_path / "projects"
    root = projects / "carriage"
    source = Path(__file__).resolve().parents[2] / "examples/lifecycle/linear-carriage/script.py"
    assert main(["script", "--set", str(source), "--project", str(root), "--json"]) == EXIT_OK
    assert main(["walk", "--project", str(root), "--out", str(root / "runs" / "baseline"),
                 "--iterations", "1", "--envs", "4", "--seed", "0", "--timeout", "600", "--json"]) == EXIT_OK
    capsys.readouterr()
    server, _thread = serve_projects(projects, "127.0.0.1", 0)
    try:
        yield root, server
    finally:
        server.shutdown()
        server.server_close()
