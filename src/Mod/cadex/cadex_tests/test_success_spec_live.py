# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A success spec, through a live ``cadexd`` (ADR-456).

``test_success_spec_api`` and ``test_success_spec_model`` prove the two
halves against fixtures. This proves the seam between them, which neither
can: a script that declares ``assembly.success`` goes into a real engine,
the sandboxed worker finds ``CadexEvaluation`` staged beside
``CadexDynamics``, and the bundle the project store retains carries the
spec resolved -- component values as the body names the model knows, the
conditions as addresses and SI.

And the refusal the surface exists for, where both halves are real: a
predicate on the task's own reward fails the script.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile

import pytest

import CadexDynamics as dyn
from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

mujoco = pytest.importorskip("mujoco")

pytestmark = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)

#: A free block with a paddle it can swing, and nothing grounded: the block
#: is the floating base and the floor is the environment's plane, which is
#: the shape a walker or a balancer has. The paddle stands in for a foot --
#: a body with a primitive collision shape on a joint below the base.
#:
#: The task trains under a 1 s episode and a light shove. The spec judges
#: over 3 s, on three seeds, under a harder shove and no reset variation.
SCRIPT = """
brick = part.box(120, 60, 40)
tab = part.box(50, 20, 6)
block = assembly.component(brick)
paddle = assembly.component(tab, placement=[0, 0, 60])
wrist = assembly.joint("revolute",
                       assembly.connector(block, "origin",
                                          offset={"position": [0, 0, 40],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": 90}),
                       assembly.connector(paddle, "origin",
                                          offset={"position": [0, 0, 0],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": 90}))
asm = assembly.assembly([block, paddle], [wrist])
diag = assembly.solve(asm)
motor = assembly.actuator(wrist, kind="motor", control_nmm="0",
                          torque_limit_nmm=200)
model = assembly.mjcf(asm, [
    assembly.body(block, density_kg_m3=2700,
                  collision=[assembly.collision(
                      "box", size_mm=[120, 60, 40],
                      offset={"position": [60, 30, 20]})]),
    assembly.body(paddle, density_kg_m3=2700,
                  collision=[assembly.collision("sphere", radius_mm=5)]),
], actuators=[motor], observations=[
    assembly.observation(block, "component_position", name="base"),
    assembly.observation(wrist, "position", name="angle"),
])
start = assembly.reset_variation(block, tilt_degrees=[0.0, 4.0],
                                 height_mm=[10.0, 13.0], label="start")
shove = assembly.disturbance(block, newtons=[2.0, 4.0],
                             at_seconds=[0.2, 0.5], duration_s=0.1,
                             label="shove")
harder = assembly.disturbance(block, newtons=[6.0, 8.0],
                              at_seconds=[1.0, 1.5], duration_s=0.1,
                              label="harder")
spec = assembly.success(
    [
        {"id": "completes", "metric": "completed", "min": 1},
        {"id": "upright", "metric": "max_tilt_deg", "max": 30},
        {"id": "in_place", "metric": "max_drift_com_heights", "max": 2.0},
        {"id": "recovers", "metric": "recovery_s_max", "max": 1.0},
        {"id": "on_the_floor", "metric": "foot_lowest_hip_heights_min",
         "min": -0.05},
    ],
    seeds=[1101, 1102, 1103],
    feet=[paddle],
    episode_seconds=3.0,
    reset_variation=[],
    disturbance=[harder],
    label="stays put",
)
job = assembly.task(model, actions=[motor],
                    reward=[assembly.reward("base_z", weight=1.0e-3,
                                            label="height")],
                    episode_seconds=1.0, control_hz=50,
                    reset_variation=[start], disturbance=[shove],
                    success=spec, label="stand")
result = {"brick": brick, "tab": tab, "block": block, "paddle": paddle,
          "wrist": wrist, "asm": asm, "diag": diag, "model": model,
          "job": job}
"""


def _write(source: str, root: Path) -> dict:
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        written = client.request(
            "write_script", {"source": source, "expected_revision": ""}
        )
        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
        return written
    finally:
        _stop(client)


def test_a_declared_spec_reaches_the_retained_bundle_resolved() -> None:
    root = Path(tempfile.mkdtemp(prefix="success-live-"))
    try:
        written = _write(SCRIPT, root)
        assert written["ok"] is True, json.dumps(written)[:4000]
        bundle = json.loads(
            Path(written["display"]["job"]["artifact_path"]).read_text(encoding="utf-8")
        )
        success = bundle["success"]
        assert success["schema"] == dyn.SUCCESS_SCHEMA
        assert success["label"] == "stays put"
        assert [row["id"] for row in success["predicates"]] == [
            "completes", "upright", "in_place", "recovers", "on_the_floor"
        ]
        assert success["predicates"][3] == {
            "id": "recovers", "metric": "recovery_s_max", "min": None, "max": 1.0
        }
        assert success["seeds"] == [1101, 1102, 1103]
        # A component value in the script; the model's body name in the file.
        assert success["feet"] == ["paddle"]
        assert success["scale"]["hip_height_mm"] == pytest.approx(40.0, abs=0.5)
        assert success["scale"]["com_height_mm"] > 0.0

        # Judged over its own horizon and its own shove; trained under the
        # task's. Neither list leaked into the other.
        assert bundle["episode"]["episode_seconds"] == pytest.approx(1.0)
        assert success["episode"]["episode_seconds"] == pytest.approx(3.0)
        assert [entry["label"] for entry in bundle["disturbance"]] == ["shove"]
        assert [entry["label"] for entry in success["disturbance"]] == ["harder"]
        assert success["disturbance"][0]["body"] == "block"
        assert [entry["label"] for entry in bundle["reset_variation"]] == ["start"]
        assert success["reset_variation"] == []

        # And the file says enough to play an evaluation episode from.
        model = dyn.load_model(
            Path(written["display"]["model"]["artifact_path"]).read_bytes()
        )
        episode = dyn.evaluate_episode(
            model, dyn.evaluation_task(bundle), seed=1101, record_steps=False
        )
        assert episode["step_count"] == 150
        (push,) = episode["disturbance"]
        assert push["label"] == "harder" and 6.0 <= push["newtons"] <= 8.0
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.parametrize(
    "predicate, reason",
    [
        # ``height`` is this task's one reward term.
        ('{"id": "paid", "metric": "height", "min": 0.05}', "success_reads_the_reward"),
        ('{"id": "paid", "metric": "total_reward", "min": 1}', "success_reads_the_reward"),
        # ``base_z`` is one of its observation channels.
        ('{"id": "tall", "metric": "base_z", "min": 20}', "unknown_success_metric"),
    ],
)
def test_a_predicate_on_the_reward_or_a_channel_fails_the_script_live(
    predicate, reason
) -> None:
    root = Path(tempfile.mkdtemp(prefix="success-live-refusal-"))
    try:
        source = SCRIPT.replace(
            '{"id": "completes", "metric": "completed", "min": 1},', predicate + ","
        )
        assert source != SCRIPT
        written = _write(source, root)
        assert written["ok"] is False, json.dumps(written)[:2000]
        text = json.dumps(written)
        assert reason in text
        # The correction names what a spec may bound instead.
        assert "max_tilt_deg" in text
    finally:
        shutil.rmtree(root, ignore_errors=True)
