# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A point goal on a coupled mechanism is drawn at a pose it can take (ADR-474).

A ``point`` goal is the tip's position at a drawn joint configuration, and
the draw checks that configuration for contacts before it accepts it. A gear,
belt or screw follower is not free: the dynamics hold it to its driver with
an ``equality/joint`` row. Before ADR-474 the draw left every follower at the
reset keyframe, so it judged a pose the mechanism never reaches.

The ot11 grip probe measured it on the smallest gripper the vocabulary
allows -- two hinged jaws, a 1:1 ``gears`` coupling, one position servo --
and the fixture below is that gripper, headless. On the probe's ten seeds,
segment 1 of 1102, 1105 and 1110 is a target where the coupled jaws overlap
by 0.5 to 4.3 mm while the pose the draw read had them 14-16 mm apart.

This pins the three implementations -- the engine, the reference runner and
the trainer's host side -- to reading the coupled pose. Whether an overlap
of two coupled jaws should then *refuse* the target is a separate question:
the builder excludes contact between the two components of every joint,
couplings included, so today it does not. That is ADR-474's open item, and
this file does not decide it.
"""

from __future__ import annotations

import random

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
import dynamics_task_episode as runner
from test_dynamics_goal_model import ARM_TASK, made, model
from test_dynamics_policy_trainer import _trainer_module

mujoco = pytest.importorskip("mujoco")
np = pytest.importorskip("numpy")

#: The grip probe's seeds: ot11's frozen reach seeds.
SEEDS = list(range(1101, 1111))
#: Each jaw hinges +/- this; the probe's script, read back.
LIMIT_DEG = 20.0
_HINGE = ((1.0, 0.0, 0.0), -90.0)


def _jaw(name: str) -> dict:
    return {
        "name": name, "size": (8.0, 10.0, 80.0),
        "collision": {"shapes": [fx.collision_shape(
            "box", size_mm=[8.0, 10.0, 80.0],
            offset={"position": (0.0, 0.0, -40.0)})], "mesh": None},
    }


def gripper():
    """A grounded palm and two 80 mm jaws on parallel hinges, geared 1:1."""

    components, joints, placements = fx.build(
        [
            {"name": "palm", "grounded": True, "size": (80.0, 20.0, 20.0),
             "world": dyn.matrix_from_rotation_translation(
                 (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0), [0.0, 0.0, 180.0])},
            _jaw("fa"),
            _jaw("fb"),
        ],
        [
            {"name": name, "kind": "revolute", "parent": "palm", "child": child,
             "parent_frame": fx.frame((x, 0.0, 0.0), *_HINGE),
             "child_frame": fx.frame((0.0, 0.0, 0.0), *_HINGE),
             "values": [0.0], "angle_limits_degrees": [-LIMIT_DEG, LIMIT_DEG]}
            for name, child, x in (("ha", "fa", -20.0), ("hb", "fb", 20.0))
        ],
    )
    joints.append({
        "name": "mesh", "kind": "gears", "suppressed": False,
        "parameters": {"radius1_mm": 10.0, "radius2_mm": 10.0},
        "length_limits_mm": None, "angle_limits_degrees": None,
        "connectors": [
            {"component": "fa", "local_matrix": fx.frame((0.0, 0.0, 0.0), *_HINGE)},
            {"component": "fb", "local_matrix": fx.frame((0.0, 0.0, 0.0), *_HINGE)},
        ],
    })
    return components, joints, placements


MOTORS = [{"joint": "ha", "motion_type": "angular", "kind": "position",
           "control_deg": "0", "stiffness_nmm_per_deg": 400.0,
           "damping_nmms_per_deg": 12.0}]
OBSERVATIONS = [{"kind": "position", "joint": "ha", "motion_type": "angular",
                 "name": "jaw"}]
GRIP_TASK = {
    "label": "grip",
    "actions": [{"joint": "ha", "motion_type": "angular", "actuator_kind": "position"}],
    "reward": [{"label": "jaw", "expression": "jaw", "weight": 0.0}],
    "termination": [],
    "episode_seconds": 4.0,
    "control_hz": 50,
    "randomisation": [],
    "goal": [{"name": "target", "kind": "point", "tip": "fa",
              "tip_offset_mm": [0.0, 0.0, -80.0], "min_separation_mm": 5.0,
              "resample_seconds": 2.0}],
}


def grip():
    return made(GRIP_TASK, mechanism=gripper, motors=MOTORS, observations=OBSERVATIONS)


class _Spy:
    """Stock ``mujoco``, recording every pose a draw forwards and its tip."""

    def __init__(self, entry):
        self.entry = entry
        self.poses: list[tuple[list[float], np.ndarray]] = []

    def __getattr__(self, name):
        return getattr(mujoco, name)

    def mj_forward(self, model, data):
        mujoco.mj_forward(model, data)
        tip = dyn._goal_tip_m(data, int(self.entry["body_id"]), self.entry["local_m"])
        self.poses.append((tip, data.qpos.copy()))


def _jaw_gap_mm(compiled, qpos) -> float:
    data = mujoco.MjData(compiled)
    data.qpos[:] = qpos
    mujoco.mj_forward(compiled, data)
    bodies = [mujoco.mj_name2id(compiled, mujoco.mjtObj.mjOBJ_BODY, name)
              for name in ("fa", "fb")]
    first, second = (
        [g for g in range(compiled.ngeom) if int(compiled.geom_bodyid[g]) == body][0]
        for body in bodies
    )
    return 1000.0 * float(
        mujoco.mj_geomDistance(compiled, data, first, second, 0.2, np.zeros(6))
    )


IMPLEMENTATIONS = {
    "engine": lambda: dyn.draw_episode_goals,
    "runner": lambda: runner.draw_goals,
    "trainer": lambda: _trainer_module().draw_goals,
}


# -- the bundle -------------------------------------------------------------

def test_a_coupled_point_goal_carries_its_followers_and_says_so() -> None:
    bundle = grip()["bundle"]
    (target,) = bundle["goal"]
    compiled = model(grip())
    driver = mujoco.mj_name2id(compiled, mujoco.mjtObj.mjOBJ_JOINT, "ha")
    follower = mujoco.mj_name2id(compiled, mujoco.mjtObj.mjOBJ_JOINT, "hb")

    assert [joint["joint"] for joint in target["joints"]] == ["ha"]
    assert target["followers"] == [{
        "joint": "hb",
        "qpos_adr": int(compiled.jnt_qposadr[follower]),
        "reference": 0.0,
        "driver_qpos_adr": int(compiled.jnt_qposadr[driver]),
        "driver_reference": 0.0,
        "polycoef": [0.0, -1.0, 0.0, 0.0, 0.0],
    }]
    assert bundle["goal_algorithm"] == dyn.GOAL_ALGORITHM + dyn.GOAL_FOLLOWER_ALGORITHM


def test_an_uncoupled_point_goal_is_the_record_it_always_was() -> None:
    bundle = made(ARM_TASK)["bundle"]
    assert all("followers" not in entry for entry in bundle["goal"])
    assert bundle["goal_algorithm"] == dyn.GOAL_ALGORITHM


def test_the_follower_law_is_the_one_the_dynamics_enforce() -> None:
    """Placed by the law, the equality row's residual is zero -- checked on a
    2:1 gear train as well, so a slope of -1 cannot hide a sign or a ratio."""

    from test_dynamics_coupled import _gear_train

    built = dyn.build_model(*_gear_train("gears")[:2])
    exported = dyn.export_mjcf(built, observations=[])
    for compiled in (model(grip()), dyn.load_model(exported["xml"])):
        followers = dyn._goal_followers(mujoco, compiled)
        assert len(followers) == 1
        data = mujoco.MjData(compiled)
        for angle in (-0.3, 0.05, 0.27):
            data.qpos[:] = compiled.qpos0
            data.qpos[int(followers[0]["driver_qpos_adr"])] += angle
            dyn._place_goal_followers(data, followers)
            mujoco.mj_forward(compiled, data)
            equality = [
                abs(float(data.efc_pos[row])) for row in range(int(data.nefc))
                if int(data.efc_type[row]) == int(mujoco.mjtConstraint.mjCNSTR_EQUALITY)
            ]
            assert equality and max(equality) < 1e-12


# -- the draw ---------------------------------------------------------------

@pytest.mark.parametrize("which", sorted(IMPLEMENTATIONS))
def test_every_accepted_target_was_judged_at_the_coupled_pose(which) -> None:
    """Fails on the old draw at 1102, 1105 and 1110, segment 1: the jaws
    overlap at the pose the target really is, and the draw read them apart."""

    draw = IMPLEMENTATIONS[which]()
    prepared = grip()
    bundle = prepared["bundle"]
    (target,) = bundle["goal"]
    compiled = model(prepared)
    # Read off the model, not the bundle, so the old draw fails on the
    # overlaps rather than on a missing key: hb = -ha at 1:1.
    driver, follower = (
        int(compiled.jnt_qposadr[mujoco.mj_name2id(compiled, mujoco.mjtObj.mjOBJ_JOINT, name)])
        for name in ("ha", "hb")
    )

    seen, real = set(), set()
    for seed in SEEDS:
        spy = _Spy(target)
        drawn = draw(spy, compiled, bundle, random.Random(seed))
        for index, segment in enumerate(drawn[0]["segments"]):
            (pose,) = {
                tuple(qpos) for tip, qpos in spy.poses
                if [value * float(target["scale"]) for value in tip] == segment
            }
            judged = np.array(pose)
            coupled = judged.copy()
            coupled[follower] = -coupled[driver]
            if _jaw_gap_mm(compiled, judged) < 0.0:
                seen.add((seed, index))
            if _jaw_gap_mm(compiled, coupled) < 0.0:
                real.add((seed, index))
    assert real == {(1102, 1), (1105, 1), (1110, 1)}
    assert seen == real


def test_the_three_draws_agree_on_a_coupled_mechanism() -> None:
    prepared = grip()
    bundle = prepared["bundle"]
    for seed in [0, 7, *SEEDS]:
        streams = {name: random.Random(seed) for name in IMPLEMENTATIONS}
        drawn = {
            name: [IMPLEMENTATIONS[name]()(mujoco, model(prepared), bundle, streams[name])
                   for _ in range(5)]
            for name in IMPLEMENTATIONS
        }
        assert drawn["runner"] == drawn["engine"] == drawn["trainer"]
        assert len({stream.random() for stream in streams.values()}) == 1
