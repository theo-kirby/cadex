# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""M6's exit criterion, end to end (docs/MUJOCO.md M6, phase 6).

A script goes into a live ``cadexd``, a training task and the model it
references come out on disk, and a subprocess that has **never heard of
Cadex** reads the bundle, opens the model beside it, resets to the solved
pose and runs a full episode -- landing on the numbers the engine landed on.

Nothing here recomputes an artifact a helper produced: the bundle compared
is the one the project store retained, and the model is the one the bundle's
own recorded digest points at.

Three things are proved that no unit test could:

* the task survives a **real Ondsel solve** rather than a fixture composed
  forwards from known joint coordinates -- the inertias come off real OCCT
  solids, the connector frames off objects FreeCAD placed, and the
  observation addresses off a model compiled from those;
* the bundle and its model are **two artifacts the store retained
  together**, resolvable from each other by the relative path the bundle
  records;
* a script may declare **more than one** task against one model, and each
  names its own bundle.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest

import CadexDynamics as dyn
import dynamics_task_episode
from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

mujoco = pytest.importorskip("mujoco")

pytestmark = pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)

RUNNER = Path(dynamics_task_episode.__file__).resolve()

#: The M5 mechanism, driven and observed. A motor rather than a servo
#: because a motor's action range comes from its own torque limit, while a
#: servo's comes from joint limits -- and this tree's native solver is what
#: decides whether those reach the model, which is a different slice's
#: problem. The refusals around the servo case are proved in
#: ``test_dynamics_task_model`` where a fixture can state them exactly.
TASK_SCRIPT = """
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
motor = assembly.actuator(j, kind="motor", control_nmm="120*sin(2*pi*time)",
                          torque_limit_nmm=400)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=2700),
    assembly.body(swing, density_kg_m3=7850),
], actuators=[motor], observations=[
    assembly.observation(j, "position", name="angle"),
    assembly.observation(j, "velocity", name="rate"),
    assembly.observation(swing, "component_position", name="tip"),
    assembly.observation(swing, "centre_of_mass", name="com"),
    assembly.observation(motor, "actuator_force", name="effort"),
])
job = assembly.task(model, actions=[motor],
                    reward=[
                        assembly.reward("-(com_z - 60)^2", weight=1.0e-4,
                                        label="lift"),
                        assembly.reward("abs(effort)", weight=-1.0e-6,
                                        label="control_cost"),
                    ],
                    termination=[
                        assembly.termination("abs(rate)", above=100000.0,
                                             label="spun_out"),
                    ],
                    episode_seconds=1.0, control_hz=50,
                    randomisation=[
                        assembly.randomise(swing, "mass", scale=[0.9, 1.1]),
                    ],
                    label="lift")
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "model": model, "job": job}
"""

#: Two tasks against one model. Legal because nothing bakes a task, and the
#: rule that makes it legal is the one worth a live test: two
#: ``api.simulation`` outputs are refused.
TWO_TASKS_SCRIPT = TASK_SCRIPT.replace(
    'result = {"plate"',
    """hold = assembly.task(model, actions=[motor],
                     reward=[assembly.reward("-abs(angle)", label="still")],
                     episode_seconds=0.5, control_hz=20, label="hold")
result = {"hold": hold, "plate\"""",
).replace('"model": model, "job": job}', '"model": model, "job": job}')


#: M9's mechanism: a floating block on a grounded floor, with a flap it can
#: drive. The block is ungrounded and no joint reaches it from the floor, so
#: the engine gives it a free joint -- which is what a floating base is, and
#: the only thing ``assembly.reset_variation`` accepts.
#:
#: The lift is 10-13 mm, and *why* is the thing worth reading. A tilt pivots
#: about the base's own frame origin, and ``part.box``'s origin is a corner
#: -- so the far corner of this brick is 134 mm from the pivot rather than
#: the 67 mm a centred solid would give, and 4 degrees swings it 9.4 mm down
#: instead of 4.7. Half the trigonometry a reader would do by hand is wrong
#: for a reason that is invisible in the script, which is exactly why the
#: engine measures it and refuses rather than documenting a formula.
SHOVED_SCRIPT = """
slab = part.box(400, 400, 20)
brick = part.box(120, 60, 40)
tab = part.box(50, 20, 6)
ground = assembly.component(slab, grounded=True)
block = assembly.component(brick, placement=[0, 0, 20])
flap = assembly.component(tab, placement=[0, 0, 60])
wrist = assembly.joint("revolute",
                       assembly.connector(block, "origin",
                                          offset={"position": [0, 0, 40],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": 90}),
                       assembly.connector(flap, "origin",
                                          offset={"position": [0, 0, 0],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": 90}))
asm = assembly.assembly([ground, block, flap], [wrist])
diag = assembly.solve(asm)
motor = assembly.actuator(wrist, kind="motor", control_nmm="0",
                          torque_limit_nmm=200)
model = assembly.mjcf(asm, [
    # The offsets put each collision box on its solid rather than on the
    # component frame origin, which for a part.box is a corner. A box
    # centred on the corner would be a mechanism nobody drew, and the
    # clearance measurement would be about it.
    assembly.body(ground, density_kg_m3=2700,
                  collision=[assembly.collision(
                      "box", size_mm=[400, 400, 20],
                      offset={"position": [200, 200, 10]})]),
    assembly.body(block, density_kg_m3=2700,
                  collision=[assembly.collision(
                      "box", size_mm=[120, 60, 40],
                      offset={"position": [60, 30, 20]})]),
    assembly.body(flap, density_kg_m3=2700),
], actuators=[motor], observations=[
    assembly.observation(block, "component_position", name="base"),
    assembly.observation(block, "component_linear_velocity", name="drift"),
    assembly.observation(wrist, "position", name="angle"),
])
start = assembly.reset_variation(block,
                                 tilt_degrees=[0.0, 4.0],
                                 height_mm=[10.0, 13.0],
                                 angular_velocity_dps=[-20.0, 20.0],
                                 label="start")
shove = assembly.disturbance(block, newtons=[20.0, 40.0],
                             direction="horizontal",
                             at_seconds=[0.2, 0.5], duration_s=0.1,
                             label="shove")
wind = assembly.disturbance(block, newtons=[0.0, 2.0],
                            direction="horizontal", sustained=True,
                            label="wind")
job = assembly.task(model, actions=[motor],
                    reward=[assembly.reward("base_z", weight=1.0e-3,
                                            label="height")],
                    episode_seconds=1.0, control_hz=50,
                    reset_variation=[start], disturbance=[shove, wind],
                    label="shoved")
result = {"slab": slab, "brick": brick, "tab": tab, "ground": ground,
          "block": block, "flap": flap, "wrist": wrist, "asm": asm,
          "diag": diag, "model": model, "job": job}
"""


def _written(source: str, root: Path) -> dict:
    """One script through one live cadexd, into a project root that stays.

    Unlike M5's helper this does **not** remove the root: the subprocess has
    to open the bundle *and* the model it references from their real
    relative positions, so the store's own directory is the fixture.
    """

    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        written = client.request(
            "write_script", {"source": source, "expected_revision": ""}
        )
        assert written["ok"] is True, json.dumps(written)[:4000]
        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
        return written
    finally:
        _stop(client)


def _stock(bundle_path: Path, seed=None) -> dict:
    """The runner, in an interpreter that cannot reach Cadex."""

    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHASHSEED", None)
    command = [sys.executable, "-P", str(RUNNER), str(bundle_path)]
    if seed is not None:
        command.append(str(seed))
    finished = subprocess.run(
        command, capture_output=True, text=True, timeout=600, env=environment
    )
    assert finished.returncode == 0, finished.stderr
    result = json.loads(finished.stdout)
    assert result["cadex_importable"] is False, (
        "the subprocess reached Cadex, so it proves nothing about a stock MuJoCo"
    )
    return result


# ---------------------------------------------------------------------------
# The exit criterion.
# ---------------------------------------------------------------------------


def test_cadexd_writes_a_task_a_stock_mujoco_can_train_against() -> None:
    """Design a mechanism in Cadex; get a trainable environment out.

    The whole slice in one assertion chain: the script declares observation
    channels, an action, a reward and a termination rule; the engine writes
    one bundle beside one model; and a process with no Cadex on its path
    runs a full episode from those two files and produces the engine's
    numbers.
    """

    root = Path(tempfile.mkdtemp(prefix="m6-live-"))
    try:
        written = _written(TASK_SCRIPT, root)
        entry = written["display"]["job"]
        assert entry["artifact_kind"] == "assembly_training_task_json", entry
        # A task is not display geometry and must not pretend to be: this is
        # what keeps it invisible to a shell that was never changed.
        assert entry["tessellation"] is None
        assert entry["placement"] is None

        bundle_path = Path(entry["artifact_path"])
        assert bundle_path.name == "job-task.json"
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        assert bundle["schema"] == dyn.TASK_SCHEMA

        # The model reference: a relative path and a digest, both pointing
        # at the artifact the store retained for the *other* output. The
        # path is relative to the run's artifact root -- the directory the
        # bundle's own ``outputs/`` sits in -- which is what makes the pair
        # movable together and resolvable by a reader with no store.
        model_entry = written["display"]["model"]
        model_path = Path(model_entry["artifact_path"])
        artifact_root = bundle_path.parent.parent
        assert bundle["model"]["path"] == "outputs/model-model.xml"
        assert (
            artifact_root / bundle["model"]["path"]
        ).resolve() == model_path.resolve()
        import hashlib

        assert bundle["model"]["sha256"] == hashlib.sha256(
            model_path.read_bytes()
        ).hexdigest()

        # The channels reached the file, and the observation vector is
        # MuJoCo's: six scalars from four declarations.
        text = model_path.read_text(encoding="utf-8")
        assert "<sensor>" in text
        assert 'objtype="xbody"' in text, (
            "a component channel must read the frame the solver placed, not "
            "the inertial one"
        )
        channels = [
            channel
            for record in bundle["observations"]
            for channel in record["channels"]
        ]
        assert channels == [
            "angle", "rate", "tip_x", "tip_y", "tip_z",
            "com_x", "com_y", "com_z", "effort",
        ]

        # The action range came off the mechanism rather than a default.
        action = bundle["actions"][0]
        assert action["source"] == "torque_limit_nmm"
        assert (action["low"], action["high"]) == (-400.0, 400.0)
        assert action["unit"] == "nmm"
        assert action["fallback"] == "120*sin(2*pi*time)"

        # It published, with the two digests that make a task and its model
        # one thing.
        live = written["live_outputs"]["job"]
        assert live["domain"] == "assembly"
        assert live["output_type"] == "task"
        assert live["type_id"] == "App::FeaturePython"

        # And now the criterion itself.
        there = _stock(bundle_path)
        here = dyn.evaluate_episode(dyn.load_model(model_path.read_bytes()), bundle)

        assert there["step_count"] == here["step_count"] == 50
        assert there["truncated"] is here["truncated"] is True
        assert there["total_reward"] == repr(here["total_reward"])
        for mine, yours in zip(here["steps"], there["steps"], strict=True):
            assert yours["action"] == [repr(value) for value in mine["action"]]
            assert yours["observation"] == {
                name: repr(value) for name, value in mine["observation"].items()
            }
            assert yours["reward"] == repr(mine["reward"])

        # The arm actually moved under the motor, so the agreement is
        # between two episodes rather than two still models. The angle
        # swings and the centre of mass rises and falls with it, both in the
        # surface's own units.
        angles = [step["observation"]["angle"] for step in here["steps"]]
        heights = [step["observation"]["com_z"] for step in here["steps"]]
        assert max(angles) - min(angles) > 5.0, "degrees"
        assert max(heights) - min(heights) > 1.0, "millimetres"

        # And a finding worth recording where it is visible: ``tip_z`` never
        # moves. A component_position reads the body *frame origin*, and
        # this link's frame origin is its hinge anchor -- a point on the
        # rotation axis. The channel is correct and useless here, which is
        # exactly why centre_of_mass exists as a separate kind.
        assert len({step["observation"]["tip_z"] for step in here["steps"]}) == 1

        # The whitelist is the same on both sides and in the file.
        assert there["functions"] == bundle["functions"] == list(dyn.REWARD_FUNCTIONS)

        # And the seeded form agrees too, which is what puts domain
        # randomisation inside the gate rather than beside it.
        seeded_there = _stock(bundle_path, seed=5)
        seeded_here = dyn.evaluate_episode(
            dyn.load_model(model_path.read_bytes()), bundle, seed=5
        )
        assert seeded_there["randomisation"] == [
            {"label": item["label"], "factor": repr(item["factor"])}
            for item in seeded_here["randomisation"]
        ]
        assert seeded_there["total_reward"] == repr(seeded_here["total_reward"])
        assert seeded_there["total_reward"] != there["total_reward"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_varied_disturbed_episode_survives_the_round_trip_live() -> None:
    """M9's exit criterion on the same terms M6's was proved on.

    A script declares a floating base, a reset variation and two
    disturbances; the engine writes one bundle; and a process with no Cadex
    on its path reproduces the *draws* and the episode they produced. That
    is the claim the two new surfaces make to a trainer -- that the file
    says enough -- and the only way to test it is with a second
    implementation that cannot cheat.

    The unit-level agreement is ``test_dynamics_variation_model``'s. What
    this adds is the whole path: a real solve, a real export, a real store,
    and a subprocess whose ``PYTHONPATH`` is scrubbed.
    """

    root = Path(tempfile.mkdtemp(prefix="m9-live-"))
    try:
        written = _written(SHOVED_SCRIPT, root)
        bundle_path = Path(written["display"]["job"]["artifact_path"])
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

        # The two lists reached the file, resolved to addresses rather than
        # names -- which is what lets a reader index arrays instead of
        # introspecting a model.
        (variation,) = bundle["reset_variation"]
        assert variation["body"] == "block"
        assert variation["qpos_adr"] >= 0 and variation["qvel_adr"] >= 0
        assert variation["tilt_high_rad"] > 0.0
        # Degrees in the script, radians in the bundle: converted once.
        assert variation["tilt_high_rad"] == pytest.approx(math.radians(4.0))
        assert variation["clearance_mm"] is not None

        shove, wind = bundle["disturbance"]
        assert [entry["label"] for entry in bundle["disturbance"]] == [
            "shove", "wind"
        ]
        assert shove["sustained"] is False and wind["sustained"] is True
        assert shove["applied_at"] == "centre_of_mass"
        assert shove["frame"] == "world"
        assert bundle["variation_algorithm"] == dyn.EPISODE_VARIATION_ALGORITHM

        model_path = Path(written["display"]["model"]["artifact_path"])
        model = dyn.load_model(model_path.read_bytes())

        # The criterion: same seed, same draws, same episode, on two
        # implementations that share only the file.
        there = _stock(bundle_path, seed=9)
        here = dyn.evaluate_episode(model, bundle, seed=9)

        assert there["step_count"] == here["step_count"]
        assert there["total_reward"] == repr(here["total_reward"])
        assert there["reset_variation"] == [
            {
                "label": draw["label"],
                "tilt_rad": repr(draw["tilt_rad"]),
                "azimuth_rad": repr(draw["azimuth_rad"]),
                "height_m": repr(draw["height_m"]),
                "angular_velocity_rad_s": [
                    repr(value) for value in draw["angular_velocity_rad_s"]
                ],
            }
            for draw in here["reset_variation"]
        ]
        assert there["disturbance"] == [
            {
                "label": draw["label"],
                "newtons": repr(draw["newtons"]),
                "azimuth_rad": repr(draw["azimuth_rad"]),
                "start_s": repr(draw["start_s"]),
                "force_n": [repr(value) for value in draw["force_n"]],
            }
            for draw in here["disturbance"]
        ]
        for mine, yours in zip(here["steps"], there["steps"], strict=True):
            assert yours["observation"] == {
                name: repr(value) for name, value in mine["observation"].items()
            }

        # And it really was varied: the unseeded episode is a different one,
        # so the agreement above is about the mechanism rather than about
        # two runs of the nominal pose.
        nominal = dyn.evaluate_episode(model, bundle)
        assert nominal["total_reward"] != here["total_reward"]
        assert nominal["reset_variation"] == []

        # Two seeds are two episodes, which is the entire point: a posture
        # found once is now asked a second question.
        other = dyn.evaluate_episode(model, bundle, seed=10)
        assert other["total_reward"] != here["total_reward"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_tilt_that_would_dig_into_the_floor_is_refused_live() -> None:
    """The refusal that shaped the surface, in the engine that measures it.

    The block rests on the floor, so a tilt with no lift swings a corner
    through it -- and a script that reached a trainer with that in it would
    spend its whole run learning that the floor hits back.
    """

    root = Path(tempfile.mkdtemp(prefix="m9-dig-"))
    try:
        source = SHOVED_SCRIPT.replace("height_mm=[10.0, 13.0]", "height_mm=[0.0, 0.0]")
        client = None
        try:
            client = _spawn_cadexd()
            opened = client.request("open_project", {"project_root": str(root)})
            assert opened["ok"] is True, opened
            written = client.request(
                "write_script", {"source": source, "expected_revision": ""}
            )
        finally:
            _stop(client)
        assert written["ok"] is False, json.dumps(written)[:2000]
        text = json.dumps(written)
        assert "reset_variation_penetrates" in text
        assert "height_mm" in text
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_task_naming_a_channel_it_never_declared_is_refused_live() -> None:
    """The refusal happens in the engine, not in somebody's trainer.

    The division M6 turns on, proved where both halves are real: the API
    accepts ``badger`` because ``api.reward`` is written before there is a
    task to belong to and cannot know the channel list, and the engine
    refuses it because only there is that list known -- and *expanded*, so
    the correction can name what was available instead.

    A script that reaches this point has already had its model built and
    exported, so the refusal costs the export. That is the right trade: the
    alternative is a bundle that describes a reward nothing can evaluate.
    """

    root = Path(tempfile.mkdtemp(prefix="m6-live-refusal-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        written = client.request(
            "write_script",
            {
                "source": TASK_SCRIPT.replace(
                    '"-(com_z - 60)^2"', '"-(badger - 60)^2"'
                ),
                "expected_revision": "",
            },
        )
        assert written["ok"] is False
        message = json.dumps(written)
        assert "badger" in message
        # The correction lists the channels that do exist, expanded.
        assert "com_z" in message
        assert "vector observation expands" in message
        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


def test_two_tasks_may_share_one_model_through_a_live_engine() -> None:
    """Not under the "exactly one simulation" rule, proved where it counts."""

    root = Path(tempfile.mkdtemp(prefix="m6-live-two-"))
    try:
        written = _written(TWO_TASKS_SCRIPT, root)
        job = Path(written["display"]["job"]["artifact_path"])
        hold = Path(written["display"]["hold"]["artifact_path"])
        assert job != hold
        assert job.name == "job-task.json" and hold.name == "hold-task.json"

        first = json.loads(job.read_text(encoding="utf-8"))
        second = json.loads(hold.read_text(encoding="utf-8"))
        # One model, two tasks: the same file, the same digest, different
        # episodes and different rewards.
        assert first["model"] == second["model"]
        assert first["label"] == "lift" and second["label"] == "hold"
        assert first["episode"]["max_steps"] == 50
        assert second["episode"]["max_steps"] == 10
        assert [term["label"] for term in second["reward"]] == ["still"]

        # Both run, from the one model they share.
        for bundle_path in (job, hold):
            result = _stock(bundle_path)
            assert result["step_count"] > 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_the_protocol_did_not_change() -> None:
    """A task arrives as an ordinary output with a kind the shell ignores.

    M6 promised no protocol change and no ``shell/`` diff. This is the half
    that can be asserted from here: the bundle reaches the shell through the
    same ``display`` entry every other artifact uses, with no tessellation,
    so ``cadex_hydrate`` skips it for want of geometry and ``cadex_animate``
    for want of the simulation kind.
    """

    from CadexdProtocol import OP_ARG_SPECS

    root = Path(tempfile.mkdtemp(prefix="m6-live-protocol-"))
    try:
        written = _written(TASK_SCRIPT, root)
        entry = written["display"]["job"]
        # The same display keys every other artifact-bearing output uses --
        # no field was added for a task.
        assert set(entry) == set(written["display"]["model"])
        assert entry["tessellation"] is None
        assert entry["placement"] is None
        # No op was added, and none should have been.
        assert "task" not in OP_ARG_SPECS
        assert "train" not in OP_ARG_SPECS
    finally:
        shutil.rmtree(root, ignore_errors=True)
