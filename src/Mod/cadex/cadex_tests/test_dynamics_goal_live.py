# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A goal, through a live ``cadexd`` (ADR-462).

``test_dynamics_goal_api`` and ``test_dynamics_goal_model`` prove the two
halves against fixtures. This proves the seam: a script that declares
``assembly.goal`` goes into a real engine, the bundle the project store
retains carries the goal resolved against a real Ondsel solve and a real
export, a policy built against that bundle is verified with the goal among
its inputs, and the rollout's trace -- the artifact the shell bakes and
``cadex evaluate`` films -- records what each frame was asked.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import pytest

import CadexDynamics as dyn
from test_cadexd_lifecycle import FREECADCMD
from test_dynamics_policy_live import _Session, _container_for

mujoco = pytest.importorskip("mujoco")

pytestmark = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)

#: One limited hinge under a position servo: the smallest arm. The target
#: is a point the link's far end can reach, drawn again every second; the
#: value beside it is a number the reward gives its own meaning. The spec
#: judges the reach over four seconds, on the task's own goals.
TASK_SCRIPT = """
post = part.box(60, 60, 300)
link = part.box(200, 30, 15)
base = assembly.component(post, grounded=True)
swing = assembly.component(link, placement=[0, 0, 150])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [0, 0, 150],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": -90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [-100, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": -90}),
                   angle_limits_degrees=[-60, 60])
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
servo = assembly.actuator(j, kind="position", control_deg="0",
                          stiffness_nmm_per_deg=4000,
                          damping_nmms_per_deg=120)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=7850),
    assembly.body(swing, density_kg_m3=2700),
], actuators=[servo], observations=[
    assembly.observation(j, "position", name="angle"),
    assembly.observation(swing, "centre_of_mass", name="tip"),
])
target = assembly.goal("target", kind="point", tip=swing,
                       tip_offset_mm=[100, 0, 0], min_separation_mm=20,
                       resample_seconds=1.0)
ask = assembly.goal("ask", between=[1, 2], label="how much")
spec = assembly.success(
    [{"id": "arrives", "metric": "final_error_arm_lengths_max", "max": 0.05}],
    seeds=[1101, 1102], tip=swing, tip_offset_mm=[100, 0, 0],
    episode_seconds=4.0)
job = assembly.task(model, actions=[servo], goals=[target, ask],
                    reward=[
                        assembly.reward("-abs(tip_z - target_z)", weight=0.01,
                                        label="near"),
                        assembly.reward("ask", weight=1.0e-3, label="asked"),
                    ],
                    episode_seconds=2.0, control_hz=50, success=spec,
                    label="reach")
result = {"post": post, "link": link, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "model": model, "job": job}
"""

ROLLOUT_SCRIPT = TASK_SCRIPT.replace(
    'result = {"post"',
    """gait = assembly.policy(job, weights="reach.cxpolicy",
                       sha256="__SHA256__", label="reach")
play = assembly.rollout(gait, frames_per_second=50, seed=9, label="reach")
result = {"play": play, "gait": gait, "post\"""",
)


def test_a_declared_goal_reaches_the_bundle_the_policy_and_the_trace() -> None:
    root = Path(tempfile.mkdtemp(prefix="goal-live-"))
    try:
        with _Session(root) as session:
            written = session.write(TASK_SCRIPT)
            assert written["ok"] is True, json.dumps(written)[:4000]
            revision = str(written["revision"])
            bundle_path = Path(written["display"]["job"]["artifact_path"])
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

            target, ask = bundle["goal"]
            assert bundle["goal_algorithm"] == dyn.GOAL_ALGORITHM
            # A component value in the script; the model's body name, its id
            # and SI in the file.
            assert (target["kind"], target["body"]) == ("point", "swing")
            assert target["channels"] == ["target_x", "target_y", "target_z"]
            assert target["local_m"] == pytest.approx([0.1, 0.0, 0.0])
            assert target["min_separation_m"] == pytest.approx(0.02)
            assert (target["resample_steps"], target["segments"]) == (50, 2)
            assert [joint["joint"] for joint in target["joints"]] == ["j"]
            assert target["joints"][0]["low"] == pytest.approx(-0.8 * 1.0471975512, abs=1.0e-5)
            assert (ask["label"], ask["kind"], ask["low"], ask["high"]) == (
                "how much", "value", 1.0, 2.0)
            # The spec judges over its own horizon, on the task's own goals.
            assert bundle["success"]["goal"][0]["segments"] == 4
            assert dyn.policy_channels(bundle) == [
                "angle", "tip_x", "tip_y", "tip_z",
                "target_x", "target_y", "target_z", "ask",
            ]

            container = _container_for(bundle_path, label="reach")
            assert container["header"]["observations"][-4:] == [
                "target_x", "target_y", "target_z", "ask"
            ]
            weights = root.parent / "reach.cxpolicy"
            weights.write_bytes(container["blob"])
            assert session.put_asset(weights, "reach.cxpolicy")["ok"] is True
            played = session.write(
                ROLLOUT_SCRIPT.replace("__SHA256__", container["sha256"]), revision
            )
            assert played["ok"] is True, json.dumps(played)[:4000]

            trace = json.loads(
                Path(played["display"]["play"]["artifact_path"]).read_text(encoding="utf-8")
            )
            assert trace["schema"] == "cadex-assembly-simulation-trace-v1"
            assert [row["channel"] for row in trace["goal_channels"]] == [
                "target_x", "target_y", "target_z", "ask"
            ]
            drawn_target, drawn_ask = trace["policy"]["goal"]
            first, second = (segment["values"] for segment in drawn_target["segments"])
            value = drawn_ask["segments"][0]["values"]
            assert first != second and 1.0 <= value[0] <= 2.0
            timed = trace["frames"][1:]
            assert len(timed) == 101
            for frame in timed:
                held = first if frame["nominal_time_s"] < 1.0 - 1.0e-9 else second
                assert frame["goal"] == held + value
            # The same seed, played from the retained files, asks the same.
            model_bytes = Path(
                played["display"]["model"]["artifact_path"]
            ).read_bytes()
            assert hashlib.sha256(model_bytes).hexdigest() == bundle["model"]["sha256"]
            again = dyn.evaluate_episode(dyn.load_model(model_bytes), bundle, seed=9,
                                         actions=lambda _step, _seen: [0.0])
            assert [segment["values"] for segment in again["goal"][0]["segments"]] == [
                first, second
            ]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_goal_the_model_cannot_keep_fails_the_script_live() -> None:
    """The engine's half of the refusals, where both halves are real: a goal
    named after an observation channel, and a period between control steps."""

    for change, reason in (
        (('assembly.goal("ask", between=[1, 2], label="how much")',
          'assembly.goal("tip_z", between=[1, 2])'), "duplicate_goal_channel"),
        (("resample_seconds=1.0", "resample_seconds=0.03"),
         "goal_resample_between_control_steps"),
    ):
        root = Path(tempfile.mkdtemp(prefix="goal-live-refusal-"))
        try:
            source = TASK_SCRIPT.replace(*change).replace(
                'assembly.reward("ask", weight=1.0e-3, label="asked"),', "")
            assert change[1] in source
            with _Session(root) as session:
                written = session.write(source)
            assert written["ok"] is False, json.dumps(written)[:2000]
            assert reason in json.dumps(written)
        finally:
            shutil.rmtree(root, ignore_errors=True)
