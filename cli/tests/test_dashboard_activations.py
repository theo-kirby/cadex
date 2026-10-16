# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Activations editor (ADR-721, docs/DASHBOARD.md §27).

The server half: a rollout's playback carries what its motors did and the URL
of the policy beside it, and ``api/policy/...`` serves that policy's network,
weights, input kinds and the parts each motor moves. The browser half: on a
trace whose commands are the network's own outputs, the page rebuilds the
inputs and reruns the network to the same commands, and paints the parts.

The policies here are written by hand in the ``CXPOLICY1`` layout
(CadexDynamics ``decode_policy``), small enough to run in pure Python.
"""

from __future__ import annotations

import base64
import json
import math
from pathlib import Path
import random
import struct

import pytest

from cadex_cli.review_server import _mjcf_parts, read_policy, serve
from test_checkpoint_rollouts import BIPED, MODEL
from test_review_checkpoints import RUN, _trace, _training_run
from test_review_record import REVISION_B, _manifest, _project
from test_review_server import _get, _json, _model_state, _open, _rewrite_record, _stage_accepted
from test_review_server import browser, needs_browser  # noqa: F401  (fixture)

#: The biped's four motors and the twelve inputs its task bundle declares for them.
JOINTS = ["hip_l", "knee_l", "hip_r", "knee_r"]
OBSERVATIONS = [f"{kind}_{joint}" for joint in JOINTS for kind in ("q", "dq", "tau")]
LAYERS = [[12, 8], [8, 6], [6, 4]]


def _network(seed: int = 3) -> tuple[list[float], dict]:
    rng = random.Random(seed)
    weights = [rng.uniform(-0.6, 0.6) for a, b in LAYERS for _ in range(a * b + b)]
    network = {"kind": "mlp", "activation": "swish", "layers": LAYERS, "output": "tanh",
               "output_scale": [40.0, 50.0, 40.0, 50.0], "output_bias": [0.0, -5.0, 0.0, -5.0]}
    return weights, network


def write_policy(path: Path, *, label: str = "reed_walk", seed: int = 3) -> dict:
    """A biped policy in the CXPOLICY1 layout; returns its header."""

    weights, network = _network(seed)
    header = {
        "schema": "cadex-policy-v1", "label": f"test policy {seed}", "network": network,
        "normaliser": {"mean": [0.5 * i for i in range(12)], "std": [10.0 + i for i in range(12)]},
        "observations": OBSERVATIONS, "task": {"label": label, "sha256": "0" * 64},
        "model": {"path": f"outputs/{MODEL}", "sha256": "0" * 64},
        "actions": [{"actuator": f"{j}/motor", "joint": j, "low": -60.0, "high": 60.0, "index": i}
                    for i, j in enumerate(JOINTS)]}
    text = json.dumps(header).encode()
    path.write_bytes(b"CXPOLICY1\n" + struct.pack("<Q", len(text)) + text
                     + struct.pack(f"<{len(weights)}f", *weights))
    return header


def _forward(header: dict, values: list[float]) -> list[float]:
    """The policy's command in pure Python, float32 weights as the page reads them."""

    weights, network = _network(int(header["label"].rsplit(" ", 1)[1]))
    weights = list(struct.unpack(f"<{len(weights)}f", struct.pack(f"<{len(weights)}f", *weights)))
    mean, std = header["normaliser"]["mean"], header["normaliser"]["std"]
    a = [(v - m) / s for v, m, s in zip(values, mean, std)]
    cursor = 0
    for index, (n, m) in enumerate(LAYERS):
        matrix, cursor = weights[cursor:cursor + n * m], cursor + n * m
        bias, cursor = weights[cursor:cursor + m], cursor + m
        z = [bias[k] + sum(a[i] * matrix[i * m + k] for i in range(n)) for k in range(m)]
        a = [x / (1 + math.exp(-x)) for x in z] if index < len(LAYERS) - 1 else [math.tanh(x) for x in z]
    return [v * s + b for v, s, b in zip(a, network["output_scale"], network["output_bias"])]


def motor_trace(tag: str, header: dict | None = None, frames: int = 30) -> dict:
    """A checkpoint trace with joint positions, velocities and efforts, and, given a
    policy header, the commands that policy gives one frame on (as a rollout does)."""

    trace = _trace(tag, int(tag) - 1, 1.0, frames=frames)
    trace["actuator_channels"] = [
        {"actuator": f"{j}/motor", "joint": j, "unit": "deg", "low": -60.0, "high": 60.0, "kind": "motor",
         "joint_unit": "deg", "effort_unit": "N·mm", "effort_rated": 1000.0, "effort_low": -3000.0,
         "effort_high": 3000.0} for j in JOINTS]
    rows = []
    for i, frame in enumerate(trace["frames"][1:]):
        q = [30 * math.sin(0.3 * i + k) for k in range(4)]
        dq = [9 * math.cos(0.3 * i + k) for k in range(4)]
        tau = [900 * math.sin(0.2 * i + 2 * k) for k in range(4)]
        frame.update(joint_positions=q, joint_velocities=dq, actuator_efforts=tau)
        rows.append([v for k in range(4) for v in (q[k], dq[k], tau[k])])
    for i, frame in enumerate(trace["frames"][1:]):
        frame["actuator_commands"] = (_forward(header, rows[i - 1]) if header and i else [0.0] * 4)
    return trace


def _policy_project(tmp_path: Path) -> tuple[Path, Path, dict]:
    root = _project(tmp_path)
    _manifest(root, REVISION_B)
    _stage_accepted(root, REVISION_B)
    run = _training_run(root)
    train = run / "train"
    header = write_policy(train / "walk.000020.cxpolicy")
    (train / "walk.000020.rollout-trace.json").write_text(json.dumps(motor_trace("000020", header)))
    return root, run, header


# -- the server ---------------------------------------------------------------------------


def test_a_checkpoint_playback_carries_its_motors_and_its_policy(tmp_path) -> None:
    root, _run, _header = _policy_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        played = _json(server.url + f"api/playback/checkpoint/{RUN}/walk.000020")
        assert played["policy"] == f"api/policy/checkpoint/{RUN}/walk.000020"
        assert len(played["joints"]) == len(played["velocities"]) == len(played["efforts"]) == len(played["times_s"])
        assert played["channels"][0] == {"actuator": "hip_l/motor", "unit": "deg", "low": -60.0, "high": 60.0,
                                         "joint": "hip_l", "kind": "motor", "joint_unit": "deg",
                                         "effort_unit": "N·mm", "effort_rated": 1000.0, "effort_low": -3000.0,
                                         "effort_high": 3000.0}
    finally:
        server.shutdown()
        server.server_close()


def test_the_policy_route_serves_the_network_its_inputs_and_the_parts_each_motor_moves(tmp_path) -> None:
    root, _run, header = _policy_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        policy = _json(server.url + f"api/policy/checkpoint/{RUN}/walk.000020")
        assert policy["available"] and policy["stem"] == "walk.000020"
        assert policy["source"] == f"runs/{RUN}/train/walk.000020.cxpolicy"
        assert policy["network"] == header["network"] and policy["observations"] == OBSERVATIONS
        blob = base64.b64decode(policy["weights"])
        assert len(blob) == 4 * sum(a * b + b for a, b in LAYERS)
        # Every input's kind and target comes from the run's task bundle.
        assert [(i["channel"], i["kind"], i["target"], i["rebuilt"]) for i in policy["inputs"][:3]] == [
            ("q_hip_l", "position", "hip_l", True), ("dq_hip_l", "velocity", "hip_l", True),
            ("tau_hip_l", "actuator_force", "hip_l", True)]
        # This bundle declares no gait reference, so there is no clock.
        assert policy["clock"] is None
        assert policy["parts"]["hip_l"] == {"segment": ["thigh_l_link"], "motor": []}
        assert policy["parts"]["knee_r"] == {"segment": ["shin_r_link", "foot_r_link"], "motor": []}
        # A name that is not a checkpoint policy of the run's is not found.
        assert _get(server.url + f"api/policy/checkpoint/{RUN}/walk.000099")[0] == 404
    finally:
        server.shutdown()
        server.server_close()


def test_the_run_policy_route_and_its_reasons(tmp_path) -> None:
    root, run, _header = _policy_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        none = _json(server.url + f"api/policy/run/{RUN}")
        assert not none["available"] and none["reason"] == "this run retained no policy"
        write_policy(run / "train" / "walk.cxpolicy", seed=5)
        record = json.loads((run / "run.json").read_text())
        _rewrite_record(run, artifacts={**record["artifacts"], "policy": "train/walk.cxpolicy"})
        final = _json(server.url + f"api/policy/run/{RUN}")
        assert final["available"] and final["label"] == "test policy 5"
        (run / "train" / "walk.cxpolicy").write_bytes(b"CXPOLICY1\n" + struct.pack("<Q", 2) + b"{}")
        assert _json(server.url + f"api/policy/run/{RUN}")["reason"] == "the policy is not an MLP the page can run"
    finally:
        server.shutdown()
        server.server_close()


def test_read_policy_refuses_what_it_cannot_run(tmp_path) -> None:
    good = tmp_path / "good.cxpolicy"
    write_policy(good)
    header, blob, reason = read_policy(good)
    assert header and reason == "" and len(blob) == 4 * sum(a * b + b for a, b in LAYERS)
    short = tmp_path / "short.cxpolicy"
    short.write_bytes(good.read_bytes()[:-4])
    assert read_policy(short)[2] == "the policy's weights do not match its layers"
    (tmp_path / "plain.cxpolicy").write_bytes(b"not a policy")
    assert read_policy(tmp_path / "plain.cxpolicy")[2] == "not a CXPOLICY1 file"
    (tmp_path / "link.cxpolicy").symlink_to(good)
    assert read_policy(tmp_path / "link.cxpolicy")[0] is None


def test_a_motor_moves_its_body_and_what_is_welded_to_it_and_drives_from_its_housing(tmp_path) -> None:
    mjcf = tmp_path / "m.xml"
    mjcf.write_text("""<mujoco><worldbody>
      <body name="c_thigh"><joint name="j_hip"/>
        <body name="c_pnl_thigh"/>
        <body name="c_qdd_knee"/>
        <body name="c_shin"><joint name="j_knee"/><body name="c_paw"><joint name="j_ankle"/></body></body>
      </body></worldbody></mujoco>""")
    parts = _mjcf_parts(mjcf, ["j_hip", "j_knee"])
    assert parts["j_hip"] == {"segment": ["c_thigh", "c_pnl_thigh", "c_qdd_knee"], "motor": []}
    # The knee's housing rides on the thigh; the paw has a joint of its own and is not the knee's.
    assert parts["j_knee"] == {"segment": ["c_shin"], "motor": ["c_qdd_knee"]}
    assert _mjcf_parts(tmp_path / "missing.xml", ["j_hip"]) == {}


# -- the browser ---------------------------------------------------------------------------

READY = "(function(){var s=window.cadexReview.activations().state(); return s.ready && s})()"


@needs_browser
def test_browser_reruns_the_policy_to_the_recorded_commands_and_paints_the_parts(tmp_path, browser) -> None:
    root, _run, _header = _policy_project(tmp_path)
    server, _thread = serve(root, "127.0.0.1", 0)
    try:
        page = _open(browser, server.url)
        assert _model_state(page) == "loaded"
        status = [a for a in page.evaluate("window.cadexReview.layout().areas()") if a["editor"] == "status"][0]
        page.evaluate(f"window.cadexReview.layout().setEditor({json.dumps(status['id'])}, 'activations')")
        page.evaluate(f"window.cadexReview.setSource('run:{RUN}')", await_promise=True)
        state = page.wait_for(READY, timeout=20)
        assert state["policy"] == f"api/policy/checkpoint/{RUN}/walk.000020"
        assert state["motors"] == 4 and state["missing"] == []
        # The trace's commands are this network's outputs one frame on: rebuilt, they agree.
        assert all(r is not None and r > 0.999 for r in state["match"]), state["match"]
        assert page.evaluate("document.querySelectorAll('#activations-motors .gauge').length") == 4
        # Show in viewport paints each motor's parts and leaves the rest a quiet grey.
        assert page.evaluate("window.cadexReview.viewer().heat()") is None
        page.click("#activations-viewport")
        heat = page.wait_for("window.cadexReview.viewer().heat()")
        assert set(heat) == {"thigh_l_link", "shin_l_link", "foot_l_link", "thigh_r_link", "shin_r_link", "foot_r_link"}
        assert page.attribute("#activations", "data-viewport") == "on"
        # Silencing a neuron moves some motor; the gauges say by how much.
        delta = page.evaluate("window.cadexReview.activations().hoverNeuron(0, 0)")
        assert len(delta) == 4
        page.evaluate("window.cadexReview.activations().clearHover()")
        page.click("#activations-viewport")
        assert page.evaluate("window.cadexReview.viewer().heat()") is None
    finally:
        server.shutdown()
        server.server_close()
