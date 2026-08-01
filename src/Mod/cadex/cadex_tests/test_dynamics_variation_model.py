# SPDX-License-Identifier: LGPL-2.1-or-later

"""Reset variation and disturbance, in the pure module (docs/MUJOCO.md M9).

M6 gave a task domain randomisation, which varies the *mechanism*. What it
never gave was a reason for two episodes of one mechanism to differ: every
episode reset to the identical keyframe with every velocity zero, so a
posture found once was never asked a second question. M9's finding is that
this makes **bracing** the winning strategy -- the legs policy held four
motors at 98 % of stall for six seconds and called it balance -- and these
are the two surfaces that ask the second question.

What phase 0 measured, and what this suite pins so it cannot quietly stop
being true:

* ``xfrc_applied`` acts at the body's **centre of mass**, in the **world
  frame**. A one-body probe whose mass sits 100 mm from its frame origin
  took a 1 N push and produced *zero* angular acceleration; the frame-origin
  hypothesis predicted 10 rad/s². Applied at the origin instead, every shove
  would carry a torque nobody declared.
* A free joint's ``qvel[3:6]`` is in the **body's own frame**: set to
  ``(1, 0, 0)`` on a body yawed 90°, the world-frame angular velocity comes
  back ``(0, 1, 0)``.
* Perturbing joint angles is not survivable, which is why no surface here
  does it. The reset pose is the *solved* configuration with the soles
  exactly on the floor, so a few degrees at a knee is a foot through it --
  and the clearance check below is the same arithmetic applied to the rigid
  tilt that replaced it, where the worst case is measurable.
"""

from __future__ import annotations

import math
import random

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
import dynamics_task_episode as runner

mujoco = pytest.importorskip("mujoco")


# ---------------------------------------------------------------------------
# A mechanism that floats, because a reset variation has nothing to move on
# one that does not.
# ---------------------------------------------------------------------------

#: The free body's half-width and how far its underside starts above the
#: floor's top face. Both are read by the clearance tests, which need to
#: know the geometry they are asserting about rather than discover it.
BLOCK_MM = (120.0, 60.0, 40.0)
FLOOR_TOP_MM = 10.0


def hopper(*, clearance_mm: float = 0.0):
    """A grounded floor, a free block resting on it, and a driven flap.

    No joint reaches the block from ground, so the tree gives it a free
    joint and it falls -- which is what a floating base *is*, in this
    engine, and the only configuration ``api.reset_variation`` accepts. The
    flap hangs off the block, which keeps the block the island's root, and
    exists only because a task must declare at least one action: what is
    under test is the reset pose and the applied forces, and neither of them
    goes anywhere near an actuator.

    ``clearance_mm`` lifts the block off the floor. Zero is the interesting
    case and the one a solved standing pose produces: the sole exactly on
    the surface, with no room for a tilt to borrow.
    """

    length, width, height = BLOCK_MM
    return fx.build(
        [
            {
                "name": "floor",
                "grounded": True,
                "size": (600.0, 600.0, 2.0 * FLOOR_TOP_MM),
                "collision": {
                    "shapes": [
                        fx.collision_shape(
                            "box", size_mm=[600.0, 600.0, 2.0 * FLOOR_TOP_MM]
                        )
                    ],
                    "mesh": None,
                },
            },
            {
                "name": "block",
                "size": BLOCK_MM,
                "world": dyn.matrix_from_rotation_translation(
                    (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0),
                    [
                        0.0,
                        0.0,
                        FLOOR_TOP_MM + height / 2.0 + float(clearance_mm),
                    ],
                ),
                "collision": {
                    "shapes": [
                        fx.collision_shape("box", size_mm=[length, width, height])
                    ],
                    "mesh": None,
                },
            },
            # No collision: a flap that could touch the floor would make the
            # clearance measurement about the flap.
            {"name": "flap", "size": (50.0, 20.0, 6.0)},
        ],
        [
            {
                "name": "wrist",
                "kind": "revolute",
                "parent": "block",
                "child": "flap",
                "parent_frame": fx.frame(
                    (0.0, 0.0, height / 2.0 + 20.0), (1.0, 0.0, 0.0), -90.0
                ),
                "child_frame": fx.frame((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), -90.0),
                "values": [0.0],
                "angle_limits_degrees": [-60.0, 60.0],
            }
        ],
    )


MOTOR = {
    "joint": "wrist",
    "motion_type": "angular",
    "kind": "motor",
    "control_nmm": "0",
    "torque_limit_nmm": 50.0,
}

OBSERVATIONS = [
    {"kind": "component_position", "component": "block", "name": "block"},
    {"kind": "component_linear_velocity", "component": "block", "name": "vel"},
    {"kind": "component_angular_velocity", "component": "block", "name": "spin"},
]

TASK = {
    "actions": [
        {"joint": "wrist", "motion_type": "angular", "actuator_kind": "motor"}
    ],
    "reward": [{"label": "height", "expression": "block_z", "weight": 1.0e-3}],
    "termination": [],
    "episode_seconds": 2.0,
    "control_hz": 50,
    "randomisation": [],
    "reset_variation": [],
    "disturbance": [],
    "label": "hop",
}


def _task(**overrides):
    task = dict(TASK)
    task.update(overrides)
    return task


def _bundle(*, clearance_mm: float = 0.0, task=None, actions=True):
    """One compiled model and the bundle built from its exported bytes.

    The flap's motor is the action the task must declare at least one of.
    It is a scaffold: what is under test is the reset pose and the applied
    forces, and neither goes near an actuator.
    """

    components, joints, _placements = hopper(clearance_mm=clearance_mm)
    built = dyn.build_model(components, joints, actuators=[dict(MOTOR)])
    observations = dyn.observation_records(
        list(OBSERVATIONS),
        built["tree"],
        built["joint_records"],
        built["actuators"],
    )
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    bundle = dyn.task_records(
        built,
        reloaded,
        _task(**(task or {})),
        observations=observations,
    )
    return built, reloaded, bundle


VARIATION = {
    "label": "start",
    "component": "block",
    "tilt_degrees_low": 0.0,
    "tilt_degrees_high": 6.0,
    # 6 degrees across a block 120 mm long swings its far corner about
    # 6.9 mm down -- so the lift has to cover that, and the clearance check
    # below is what says so rather than a reader's trigonometry.
    "height_mm_low": 8.0,
    "height_mm_high": 12.0,
    "angular_velocity_dps_low": -20.0,
    "angular_velocity_dps_high": 20.0,
}

SHOVE = {
    "label": "shove",
    "component": "block",
    "direction": "horizontal",
    "newtons_low": 0.5,
    "newtons_high": 1.5,
    "sustained": False,
    "at_seconds_low": 0.5,
    "at_seconds_high": 1.0,
    "duration_s": 0.2,
}

WIND = {
    "label": "wind",
    "component": "block",
    "direction": "horizontal",
    "newtons_low": 0.0,
    "newtons_high": 0.1,
    "sustained": True,
    "at_seconds_low": 0.0,
    "at_seconds_high": 0.0,
    "duration_s": 0.0,
}


# ---------------------------------------------------------------------------
# What the bundle resolves to.
# ---------------------------------------------------------------------------


def test_a_reset_variation_resolves_to_addresses_and_si() -> None:
    """No name lookup and no introspection left for whoever applies a draw.

    The property that lets three evaluators agree: the bundle carries a
    ``qpos`` address, a ``qvel`` address and a body id, and every unit has
    already been converted. A runner that had to find the free joint itself
    would be a third opinion about which joint that is.
    """

    _built, reloaded, bundle = _bundle(task={"reset_variation": [VARIATION]})
    (entry,) = bundle["reset_variation"]

    assert entry["body"] == "block"
    joint = mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_JOINT, "block/free")
    assert entry["qpos_adr"] == int(reloaded.jnt_qposadr[joint])
    assert entry["qvel_adr"] == int(reloaded.jnt_dofadr[joint])
    assert entry["body_id"] == mujoco.mj_name2id(
        reloaded, mujoco.mjtObj.mjOBJ_BODY, "block"
    )

    # Degrees in, radians out; millimetres in, metres out. Converted once,
    # here, because a conversion in three places is three places to get it
    # wrong.
    assert entry["tilt_high_rad"] == pytest.approx(math.radians(6.0))
    assert entry["height_low_m"] == pytest.approx(0.008)
    assert entry["height_high_m"] == pytest.approx(0.012)
    assert entry["angular_velocity_high_rad_s"] == pytest.approx(
        math.radians(20.0)
    )


def test_a_disturbance_records_where_and_in_which_frame_it_acts() -> None:
    """Phase 0's measurement, carried in the file rather than remembered."""

    _built, reloaded, bundle = _bundle(task={"disturbance": [SHOVE, WIND]})
    shove, wind = bundle["disturbance"]

    assert shove["body_id"] == mujoco.mj_name2id(
        reloaded, mujoco.mjtObj.mjOBJ_BODY, "block"
    )
    assert shove["applied_at"] == "centre_of_mass"
    assert shove["frame"] == "world"
    assert (shove["at_low_s"], shove["at_high_s"]) == (0.5, 1.0)
    assert shove["duration_s"] == pytest.approx(0.2)

    # A sustained entry keeps no window at all, rather than a window that
    # happens to span the episode: "the whole episode" is not a number, and
    # storing one would be a number somebody eventually edits.
    assert wind["sustained"] is True
    assert (wind["at_low_s"], wind["at_high_s"], wind["duration_s"]) == (
        0.0,
        0.0,
        0.0,
    )


def test_the_bundle_states_the_episode_draw_algorithm() -> None:
    """Two algorithms, both written down, because they are different.

    The trainer deliberately does not reproduce this one -- MJX draws on
    device through a split key -- and a bundle that stated only the stdlib
    stream would be a bundle claiming a reproducibility nobody has.
    """

    _built, _reloaded, bundle = _bundle(
        task={"reset_variation": [VARIATION], "disturbance": [SHOVE]}
    )
    stated = bundle["variation_algorithm"]
    assert stated == dyn.EPISODE_VARIATION_ALGORITHM
    assert "random.Random(seed)" in stated
    assert "bundle order" in stated
    assert "ignored when sustained" in stated


# ---------------------------------------------------------------------------
# The draw.
# ---------------------------------------------------------------------------


def test_the_draw_order_is_the_order_the_bundle_states() -> None:
    """Written out by hand against the algorithm's own text.

    The one place in this slice where "read the code" is not good enough:
    the algorithm is a *contract* with two other implementations, so this
    asserts the numbers a reader of the sentence would predict rather than
    the numbers the function happens to produce.
    """

    _built, _reloaded, bundle = _bundle(
        task={"reset_variation": [VARIATION], "disturbance": [SHOVE, WIND]}
    )
    drawn = dyn.draw_episode_variation(bundle, random.Random(11))

    expected = random.Random(11)
    variation = bundle["reset_variation"][0]
    tilt = expected.uniform(variation["tilt_low_rad"], variation["tilt_high_rad"])
    azimuth = expected.uniform(0.0, 2.0 * math.pi)
    height = expected.uniform(variation["height_low_m"], variation["height_high_m"])
    angular = [
        expected.uniform(
            variation["angular_velocity_low_rad_s"],
            variation["angular_velocity_high_rad_s"],
        )
        for _ in range(3)
    ]
    # Eight draws, not six: the linear velocity takes a magnitude and an
    # azimuth whether or not the entry declares one, for the same reason the
    # sustained disturbance below still draws a start time.
    speed = expected.uniform(
        variation.get("linear_velocity_low_m_s", 0.0),
        variation.get("linear_velocity_high_m_s", 0.0),
    )
    speed_azimuth = expected.uniform(0.0, 2.0 * math.pi)
    assert drawn["reset_variation"][0]["tilt_rad"] == tilt
    assert drawn["reset_variation"][0]["azimuth_rad"] == azimuth
    assert drawn["reset_variation"][0]["height_m"] == height
    assert drawn["reset_variation"][0]["angular_velocity_rad_s"] == angular
    assert drawn["reset_variation"][0]["linear_speed_m_s"] == speed
    assert drawn["reset_variation"][0]["linear_azimuth_rad"] == speed_azimuth

    for index in range(2):
        entry = bundle["disturbance"][index]
        magnitude = expected.uniform(entry["newtons_low"], entry["newtons_high"])
        # The arc remap takes no draw of its own, and on the full circle --
        # which is what an entry that declares no arc carries -- it is the
        # identity, so the number a reader predicts is the number drawn.
        orientation = expected.uniform(0.0, 2.0 * math.pi)
        assert (entry["azimuth_low_rad"], entry["azimuth_high_rad"]) == (
            0.0, 2.0 * math.pi
        )
        # Drawn even for the sustained entry, whose window is the whole
        # episode and which therefore ignores it. A stream whose *position*
        # depends on a branch is a stream two implementations get wrong
        # differently, and three floats is a cheap price for not having one.
        start = expected.uniform(entry["at_low_s"], entry["at_high_s"])
        push = drawn["disturbance"][index]
        assert push["newtons"] == magnitude
        assert push["azimuth_rad"] == orientation
        assert push["start_s"] == start
        assert push["force_n"] == pytest.approx(
            [magnitude * math.cos(orientation), magnitude * math.sin(orientation), 0.0]
        )


def test_a_declared_arc_reaches_the_bundle_in_radians() -> None:
    """Degrees in, radians out, like every other angle here.

    And an entry that declares no arc carries the full circle rather than
    nothing, so that the draw is one remap and never a branch.
    """

    aimed = dict(SHOVE, azimuth_degrees_low=-60.0, azimuth_degrees_high=60.0)
    _built, _reloaded, bundle = _bundle(task={"disturbance": [aimed, WIND]})
    shove, wind = bundle["disturbance"]

    assert shove["azimuth_low_rad"] == pytest.approx(math.radians(-60.0))
    assert shove["azimuth_high_rad"] == pytest.approx(math.radians(60.0))
    assert (wind["azimuth_low_rad"], wind["azimuth_high_rad"]) == (
        0.0, 2.0 * math.pi
    )


def test_an_arc_narrows_the_drawn_direction_without_touching_the_stream() -> None:
    """The property B1a was designed around, asserted both ways.

    Every draw lands inside the declared arc -- that is the feature -- and
    the *magnitudes and start times* are the identical numbers the same
    seeds produced before the arc was declared, which is what "adds no draw
    to the RNG stream" means. If the remap had cost a draw, the second half
    of this would fail and no amount of reading would have shown it.
    """

    wide = dict(SHOVE)
    narrow = dict(SHOVE, azimuth_degrees_low=-60.0, azimuth_degrees_high=60.0)
    _b1, _r1, open_bundle = _bundle(task={"disturbance": [wide, WIND]})
    _b2, _r2, aimed_bundle = _bundle(task={"disturbance": [narrow, WIND]})

    def signed_degrees(radians: float) -> float:
        return (math.degrees(radians) + 180.0) % 360.0 - 180.0

    outside = 0
    for seed in range(40):
        loose = dyn.draw_episode_variation(open_bundle, random.Random(seed))
        tight = dyn.draw_episode_variation(aimed_bundle, random.Random(seed))
        assert -60.0 <= signed_degrees(
            tight["disturbance"][0]["azimuth_rad"]
        ) <= 60.0
        outside += abs(
            signed_degrees(loose["disturbance"][0]["azimuth_rad"])
        ) > 60.0
        for index in range(2):
            assert (tight["disturbance"][index]["newtons"]
                    == loose["disturbance"][index]["newtons"])
            assert (tight["disturbance"][index]["start_s"]
                    == loose["disturbance"][index]["start_s"])
        # The undeclared entry beside it is untouched, angle and all.
        assert (tight["disturbance"][1]["azimuth_rad"]
                == loose["disturbance"][1]["azimuth_rad"])
    assert outside, "the open bundle must reach outside the arc, or this proves nothing"


def test_the_full_circle_remap_is_the_identity_to_the_last_bit() -> None:
    """Not approximately: exactly, or every task written before B1a moved.

    ``0 + drawn * (2*pi - 0) / (2*pi)`` is the identity in float64 because
    the divisor and the multiplier are the same number. That is the whole
    reason the arc is stored as an arc rather than applied as a scale, and
    it is worth an assertion because it is the kind of thing a later
    simplification would quietly break.
    """

    _built, _reloaded, bundle = _bundle(task={"disturbance": [SHOVE, WIND]})
    for seed in range(20):
        drawn = dyn.draw_episode_variation(bundle, random.Random(seed))
        expected = random.Random(seed)
        for index, entry in enumerate(bundle["disturbance"]):
            expected.uniform(entry["newtons_low"], entry["newtons_high"])
            assert drawn["disturbance"][index]["azimuth_rad"] == (
                expected.uniform(0.0, 2.0 * math.pi)
            )
            expected.uniform(entry["at_low_s"], entry["at_high_s"])


def test_an_arc_on_a_vertical_push_is_refused_by_the_engine_too() -> None:
    """The API refuses it; so does the bundle builder, on its own evidence.

    Not duplication for its own sake: a bundle can be hand-written, and the
    reading it would get here -- an arc of the ground plane applied to a
    draw that means up or down -- is exactly the silent wrongness the
    parameter was refused to prevent.
    """

    vertical = dict(WIND, direction="vertical",
                    azimuth_degrees_low=-60.0, azimuth_degrees_high=60.0)
    with pytest.raises(dyn.DynamicsError) as excinfo:
        _bundle(task={"disturbance": [vertical]})
    assert excinfo.value.reason == "disturbance_azimuth_on_vertical"


def test_a_vertical_disturbance_reads_the_same_draw_as_a_sign() -> None:
    """One draw, two readings, so the stated stream is one sentence."""

    vertical = dict(WIND, direction="vertical", newtons_low=2.0, newtons_high=2.0)
    _built, _reloaded, bundle = _bundle(task={"disturbance": [vertical]})

    ups = downs = 0
    for seed in range(40):
        (push,) = dyn.draw_episode_variation(bundle, random.Random(seed))["disturbance"]
        assert push["force_n"][0] == 0.0 and push["force_n"][1] == 0.0
        assert abs(push["force_n"][2]) == pytest.approx(2.0)
        expected = 1.0 if push["azimuth_rad"] < math.pi else -1.0
        assert push["force_n"][2] == pytest.approx(2.0 * expected)
        ups += push["force_n"][2] > 0
        downs += push["force_n"][2] < 0
    assert ups and downs, "both signs are reachable"


# ---------------------------------------------------------------------------
# What applying a draw does to the model.
# ---------------------------------------------------------------------------


def test_a_tilt_is_rigid_and_touches_no_joint_angle() -> None:
    """The load-bearing property, asserted rather than argued.

    A reset variation may lean a mechanism arbitrarily far without ever
    changing its *shape*, which is what makes it safe where a joint-angle
    jitter is not: the free joint's seven qpos values move and nothing else
    does, so the soles cannot move relative to each other and no limb can
    be driven into another.
    """

    _built, reloaded, bundle = _bundle(task={"reset_variation": [VARIATION]})
    (entry,) = bundle["reset_variation"]
    address = int(entry["qpos_adr"])

    data = mujoco.MjData(reloaded)
    key = mujoco.mj_name2id(
        reloaded, mujoco.mjtObj.mjOBJ_KEY, str(bundle["episode"]["reset_keyframe"])
    )
    mujoco.mj_resetDataKeyframe(reloaded, data, key)
    mujoco.mj_forward(reloaded, data)
    before = [float(value) for value in data.qpos]

    dyn.apply_reset_variation(
        mujoco,
        reloaded,
        data,
        bundle,
        {
            "reset_variation": [
                {
                    "label": "start",
                    "tilt_rad": math.radians(30.0),
                    "azimuth_rad": 0.0,
                    "height_m": 0.005,
                    "angular_velocity_rad_s": [0.1, -0.2, 0.3],
                }
            ],
            "disturbance": [],
        },
    )
    after = [float(value) for value in data.qpos]

    moved = {index for index, (a, b) in enumerate(zip(before, after)) if a != b}
    assert moved <= set(range(address, address + 7)), (
        "only the free joint's own qpos moved"
    )
    # The lift is exact and the orientation really turned.
    assert after[address + 2] - before[address + 2] == pytest.approx(0.005)
    assert after[address + 3 : address + 7] != before[address + 3 : address + 7]

    # A tilt of 30 degrees about the +x azimuth is 30 degrees of roll, and
    # the body's own +z axis now leans by exactly that much from world +z.
    rotation = data.xmat[int(entry["body_id"])].reshape(3, 3)
    lean = math.degrees(math.acos(min(1.0, max(-1.0, float(rotation[2][2])))))
    assert lean == pytest.approx(30.0, abs=1.0e-6)


def test_the_angular_velocity_lands_in_the_bodys_own_frame() -> None:
    """Phase 0's second measurement, pinned where it is relied on.

    Stated in the surface's docstring because it is the difference between
    a 20 deg/s kick about the mechanism's roll axis and one about the
    world's, and on a mechanism that starts yawed those are not the same
    kick.
    """

    _built, reloaded, bundle = _bundle(task={"reset_variation": [VARIATION]})
    (entry,) = bundle["reset_variation"]

    data = mujoco.MjData(reloaded)
    key = mujoco.mj_name2id(
        reloaded, mujoco.mjtObj.mjOBJ_KEY, str(bundle["episode"]["reset_keyframe"])
    )
    mujoco.mj_resetDataKeyframe(reloaded, data, key)
    # Yaw the base 90 degrees about world +z before the draw lands, so the
    # two frames disagree and the answer distinguishes them.
    address = int(entry["qpos_adr"])
    half = math.sqrt(0.5)
    data.qpos[address + 3 : address + 7] = [half, 0.0, 0.0, half]
    mujoco.mj_forward(reloaded, data)

    dyn.apply_reset_variation(
        mujoco,
        reloaded,
        data,
        bundle,
        {
            "reset_variation": [
                {
                    "label": "start",
                    "tilt_rad": 0.0,
                    "azimuth_rad": 0.0,
                    "height_m": 0.0,
                    "angular_velocity_rad_s": [1.0, 0.0, 0.0],
                }
            ],
            "disturbance": [],
        },
    )
    world = [float(value) for value in data.cvel[int(entry["body_id"])][:3]]
    assert world == pytest.approx([0.0, 1.0, 0.0], abs=1.0e-9)


def test_the_linear_velocity_lands_in_the_world_frame_beside_it() -> None:
    """The other half of the same six numbers, and the other frame.

    MuJoCo keeps a free joint's linear velocity in the **world** frame and
    its angular velocity in the **body's**, in one array, and the test above
    plus this one are the pair that says so. Same yawed base, same draw
    shape: a stumble declared along world +X stays along world +X however
    the machine is facing, where the spin above did not.

    That asymmetry is why the docstring states it twice and why two
    implementations copy it. A stumble that rotated with the base would be a
    different experiment on every episode whose tilt azimuth differed.
    """

    _built, reloaded, bundle = _bundle(task={"reset_variation": [VARIATION]})
    (entry,) = bundle["reset_variation"]

    data = mujoco.MjData(reloaded)
    key = mujoco.mj_name2id(
        reloaded, mujoco.mjtObj.mjOBJ_KEY, str(bundle["episode"]["reset_keyframe"])
    )
    mujoco.mj_resetDataKeyframe(reloaded, data, key)
    address = int(entry["qpos_adr"])
    half = math.sqrt(0.5)
    data.qpos[address + 3 : address + 7] = [half, 0.0, 0.0, half]
    mujoco.mj_forward(reloaded, data)

    dyn.apply_reset_variation(
        mujoco,
        reloaded,
        data,
        bundle,
        {
            "reset_variation": [
                {
                    "label": "start",
                    "tilt_rad": 0.0,
                    "azimuth_rad": 0.0,
                    "height_m": 0.0,
                    "angular_velocity_rad_s": [0.0, 0.0, 0.0],
                    "linear_velocity_m_s": [0.25, 0.0, 0.0],
                }
            ],
            "disturbance": [],
        },
    )
    velocity = int(entry["qvel_adr"])
    assert [float(v) for v in data.qvel[velocity : velocity + 3]] == (
        pytest.approx([0.25, 0.0, 0.0])
    )
    # ...and the body really is moving that way in the world, on a base
    # yawed 90 degrees, which is the assertion that distinguishes the frames.
    world = [float(value) for value in data.cvel[int(entry["body_id"])][3:]]
    assert world == pytest.approx([0.25, 0.0, 0.0], abs=1.0e-9)


def test_a_stumble_reaches_the_bundle_in_metres_per_second() -> None:
    """Millimetres per second in, metres per second out, converted once."""

    stumbling = dict(VARIATION, linear_velocity_mm_s_low=0.0,
                     linear_velocity_mm_s_high=250.0)
    _built, _reloaded, bundle = _bundle(task={"reset_variation": [stumbling]})
    (entry,) = bundle["reset_variation"]
    assert entry["linear_velocity_low_m_s"] == 0.0
    assert entry["linear_velocity_high_m_s"] == pytest.approx(0.25)

    # Drawn as a magnitude with an azimuth, exactly as the tilt is -- so the
    # speed is bounded by the declared range and the direction covers the
    # circle. A velocity declared as three independent components would draw
    # a *corner* of a cube at up to sqrt(2) times the declared speed.
    speeds = []
    for seed in range(40):
        (draw,) = dyn.draw_episode_variation(
            bundle, random.Random(seed)
        )["reset_variation"]
        vector = draw["linear_velocity_m_s"]
        assert vector[2] == 0.0
        speeds.append(math.hypot(vector[0], vector[1]))
        assert speeds[-1] == pytest.approx(draw["linear_speed_m_s"])
    assert 0.0 <= min(speeds) and max(speeds) <= 0.25


def test_a_disturbance_pushes_only_inside_its_own_window() -> None:
    """A window that closed stops pushing, which needs the array cleared.

    Written from zero every control step rather than accumulated: a shove
    that added to whatever was there would be a shove that never ends.
    """

    _built, reloaded, bundle = _bundle(task={"disturbance": [SHOVE]})
    (entry,) = bundle["disturbance"]
    body = int(entry["body_id"])
    drawn = {
        "reset_variation": [],
        "disturbance": [
            {"label": "shove", "newtons": 1.0, "azimuth_rad": 0.0,
             "start_s": 0.5, "force_n": [1.0, 0.0, 0.0]}
        ],
    }
    data = mujoco.MjData(reloaded)

    for time_s, expected in (
        (0.0, 0.0),
        (0.49, 0.0),
        (0.5, 1.0),          # inclusive at the start
        (0.6, 1.0),
        (0.699, 1.0),
        (0.7, 0.0),          # exclusive at the end: 0.5 + 0.2
        (1.5, 0.0),
    ):
        dyn.apply_disturbance(data, bundle, drawn, time_s)
        assert float(data.xfrc_applied[body][0]) == pytest.approx(expected), time_s

    # And a sustained entry is the same mechanism with the window opened
    # all the way, which is what makes wind a push rather than a feature.
    _built, reloaded, wind_bundle = _bundle(task={"disturbance": [WIND]})
    (wind_entry,) = wind_bundle["disturbance"]
    data = mujoco.MjData(reloaded)
    for time_s in (0.0, 0.9, 1.99):
        dyn.apply_disturbance(
            data,
            wind_bundle,
            {"reset_variation": [],
             "disturbance": [{"label": "wind", "newtons": 0.05,
                              "azimuth_rad": 0.0, "start_s": 0.0,
                              "force_n": [0.05, 0.0, 0.0]}]},
            time_s,
        )
        assert float(data.xfrc_applied[int(wind_entry["body_id"])][0]) == (
            pytest.approx(0.05)
        )


def test_a_shove_moves_the_episode_it_is_declared_in() -> None:
    """End to end in the engine: the same seed, with and without the push.

    A mechanism sitting on a floor with nothing driving it goes nowhere. A
    horizontal shove is the only thing in the task that could move it
    sideways, so a difference here is the disturbance and cannot be
    anything else.
    """

    _built, reloaded, quiet = _bundle()
    _built, reloaded_pushed, pushed = _bundle(
        # 40 N, because the block is 2.3 kg of steel on a floor whose
        # friction is worth about 22 N: a shove has to beat stiction before
        # it is a shove at all, and one that does not would make this test
        # pass for the wrong reason.
        task={"disturbance": [dict(SHOVE, newtons_low=40.0, newtons_high=40.0)]}
    )

    still = dyn.evaluate_episode(reloaded, quiet, seed=3)
    shoved = dyn.evaluate_episode(reloaded_pushed, pushed, seed=3)

    def travel(episode):
        first = episode["steps"][0]["observation"]
        last = episode["steps"][-1]["observation"]
        return math.hypot(
            last["block_x"] - first["block_x"], last["block_y"] - first["block_y"]
        )

    assert travel(still) < 0.5, "millimetres: nothing pushes it"
    assert travel(shoved) > 5.0, "millimetres: something did"
    # And the episode says what pushed it, so a rollout that fell over can
    # be read against the shove rather than guessed at from the seed.
    (record,) = shoved["disturbance"]
    assert record["newtons"] == pytest.approx(40.0)
    assert 0.5 <= record["start_s"] <= 1.0


# ---------------------------------------------------------------------------
# The clearance measurement, which is the whole reason the surface is shaped
# the way it is.
# ---------------------------------------------------------------------------


def test_a_tilt_with_no_lift_is_refused_with_the_millimetres_in_the_message() -> None:
    """The failure that ruled out perturbing joint angles, met head on.

    The block rests exactly on the floor, so there is nothing for a tilt to
    borrow: leaning it swings one edge straight through the surface, and
    MuJoCo resolves a 3 mm overlap as an impulse. Measured rather than
    bounded -- sixteen azimuths of the widest declared tilt at the smallest
    declared lift -- because the worst direction is drawn and a formula
    would have to be conservative about which one it is.
    """

    with pytest.raises(dyn.DynamicsError) as excinfo:
        _bundle(
            task={
                "reset_variation": [
                    dict(VARIATION, height_mm_low=0.0, height_mm_high=0.0)
                ]
            }
        )
    error = excinfo.value
    assert error.reason == "reset_variation_penetrates"
    assert "height_mm" in error.correction
    # The number is in the message, so the fix is arithmetic rather than
    # trial and error.
    extra = float(error.observed["extra_penetration_mm"])
    assert extra > 1.0
    assert f"{extra:.3g}" in str(error)


def test_enough_lift_clears_the_tilt_and_the_margin_is_recorded() -> None:
    """...and the entry keeps what it measured, so "close" is readable."""

    _built, _reloaded, bundle = _bundle(task={"reset_variation": [VARIATION]})
    (entry,) = bundle["reset_variation"]
    assert entry["clearance_mm"] is not None
    assert entry["clearance_mm"] >= -dyn.RESET_VARIATION_PENETRATION_LIMIT_M * 1000.0


def test_lifting_the_mechanism_off_the_floor_removes_the_question() -> None:
    """A tilt in the air cannot dig in, and the check says so rather than
    refusing on principle."""

    _built, _reloaded, bundle = _bundle(
        clearance_mm=20.0,
        task={
            "reset_variation": [
                dict(VARIATION, height_mm_low=0.0, height_mm_high=0.0,
                     tilt_degrees_high=15.0)
            ]
        },
    )
    (entry,) = bundle["reset_variation"]
    assert entry["clearance_mm"] >= 0.0


# ---------------------------------------------------------------------------
# Refusals.
# ---------------------------------------------------------------------------


def test_a_reset_variation_on_a_bolted_body_is_refused_by_name() -> None:
    """There is no base to vary, and the correction says which bodies are."""

    with pytest.raises(dyn.DynamicsError) as excinfo:
        _bundle(task={"reset_variation": [dict(VARIATION, component="floor")]})
    error = excinfo.value
    assert error.reason == "reset_variation_not_floating"
    assert error.observed["floating"] == ["block"]
    assert "joint angles" in error.correction


def test_two_reset_variations_on_one_base_are_refused() -> None:
    """They compound into a tilt neither declares and a clearance neither
    was checked for."""

    with pytest.raises(dyn.DynamicsError) as excinfo:
        _bundle(task={"reset_variation": [VARIATION, dict(VARIATION, label="again")]})
    assert excinfo.value.reason == "duplicate_reset_variation"


def test_a_shove_shorter_than_a_control_step_is_refused() -> None:
    """It can fall between two steps and never happen at all.

    The check needs the *rounded* schedule, which is why it is here and not
    on the authoring surface: the interval a task really runs at is the one
    the solver step divides into, not the one the script asked for.
    """

    with pytest.raises(dyn.DynamicsError) as excinfo:
        _bundle(task={"disturbance": [dict(SHOVE, duration_s=0.001)]})
    error = excinfo.value
    assert error.reason == "disturbance_shorter_than_control_interval"
    assert error.observed["control_interval_s"] == pytest.approx(0.02)
    assert "control_hz" in error.correction


def test_a_shove_that_runs_past_the_horizon_is_refused_with_the_bound() -> None:
    """Partly a push and partly nothing, and which one depends on the draw."""

    with pytest.raises(dyn.DynamicsError) as excinfo:
        _bundle(
            task={
                "disturbance": [
                    dict(SHOVE, at_seconds_low=1.7, at_seconds_high=1.9,
                         duration_s=0.2)
                ]
            }
        )
    error = excinfo.value
    assert error.reason == "disturbance_past_the_horizon"
    # 2.0 s episode, 0.2 s push: the latest legal start is 1.8.
    assert "1.8" in error.correction


def test_the_two_budgets_do_not_starve_each_other() -> None:
    """Separate caps, because they are separately exhaustible.

    The legs mechanism that motivated M9 was already 31 of 32 randomisation
    entries deep. A shared ceiling would have made "vary one more mass" and
    "add one more shove" compete for one seat.
    """

    assert dyn.MAXIMUM_RESET_VARIATIONS == 4
    assert dyn.MAXIMUM_DISTURBANCES == 8
    assert dyn.MAXIMUM_RANDOMISATION_ENTRIES == 32

    with pytest.raises(dyn.DynamicsError) as excinfo:
        _bundle(
            task={
                "disturbance": [
                    dict(SHOVE, label=f"shove{index}")
                    for index in range(dyn.MAXIMUM_DISTURBANCES + 1)
                ]
            }
        )
    assert excinfo.value.reason == "too_many_disturbances"


# ---------------------------------------------------------------------------
# Two evaluators, one arithmetic. The third is the trainer, and it is pinned
# in test_dynamics_policy_trainer.
# ---------------------------------------------------------------------------


def test_the_reference_runner_draws_the_same_numbers() -> None:
    """Hazard 1, paid the way it has been paid three times before.

    The reference runner reads the bundle and nothing else, so agreement
    here means the *file* says enough to reproduce the draw -- which is the
    whole claim the bundle makes to a trainer that has never seen this
    engine.
    """

    _built, _reloaded, bundle = _bundle(
        task={"reset_variation": [VARIATION], "disturbance": [SHOVE, WIND]}
    )
    mine = dyn.draw_episode_variation(bundle, random.Random(7))
    theirs = runner.draw_variation(bundle, random.Random(7))
    assert mine == theirs


def test_the_reference_runner_lands_on_the_same_episode(tmp_path) -> None:
    """...and applying them agrees too, step for step.

    In process rather than as a subprocess: the subprocess form, with a
    scrubbed ``PYTHONPATH`` proving the runner really cannot see Cadex, is
    ``test_dynamics_task_live``'s. What this adds is the disturbed and
    varied episode, which is where two implementations of one quaternion
    product would drift.
    """

    components, joints, _placements = hopper()
    built = dyn.build_model(components, joints, actuators=[dict(MOTOR)])
    observations = dyn.observation_records(
        list(OBSERVATIONS), built["tree"], built["joint_records"], built["actuators"]
    )
    exported = dyn.export_mjcf(built, observations=observations)
    model_path = tmp_path / "hop.xml"
    model_path.write_bytes(exported["xml"])
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    bundle = dyn.task_records(
        built,
        reloaded,
        _task(reset_variation=[VARIATION],
              disturbance=[dict(SHOVE, newtons_low=3.0, newtons_high=3.0)]),
        observations=observations,
    )
    import hashlib
    import json

    bundle["model"] = {
        "path": "hop.xml",
        "sha256": hashlib.sha256(exported["xml"]).hexdigest(),
        "bytes": len(exported["xml"]),
        "output": "hop",
        "mujoco_version": str(bundle["mujoco_version"]),
    }
    bundle_path = tmp_path / "hop-task.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")

    here = dyn.evaluate_episode(reloaded, bundle, seed=13)
    there = runner.run_episode(str(bundle_path), 13)

    assert there["step_count"] == here["step_count"]
    assert there["total_reward"] == repr(here["total_reward"])
    for mine, yours in zip(here["steps"], there["steps"], strict=True):
        assert yours["observation"] == {
            name: repr(value) for name, value in mine["observation"].items()
        }
    # The draws themselves, so a disagreement is attributable rather than
    # merely visible.
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
    assert [item["label"] for item in there["disturbance"]] == ["shove"]

    # And it really was a varied, disturbed episode rather than two runs of
    # the nominal one.
    nominal = dyn.evaluate_episode(reloaded, bundle)
    assert nominal["total_reward"] != here["total_reward"]
    assert nominal["reset_variation"] == []
