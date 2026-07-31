# SPDX-License-Identifier: LGPL-2.1-or-later

"""The pure module's half of a task (docs/MUJOCO.md M6, phase 1).

Phase 0 measured what MuJoCo does. This tests what :mod:`CadexDynamics`
does with it: resolving declared channels against a model that really
carries them, writing them into the exported file, deriving an action range
from the mechanism or refusing to, compiling reward and termination against
the channel namespace, and running an episode from the bundle.

Nothing here goes through ``api.`` or through the worker -- the surface is
phase 2's and the artifact is phase 3's. What is under test is the
arithmetic and the refusals, which is where a task is either honest or
silently wrong.

The refusals get as much room as the successes, and that is deliberate:
M6's fork on action bounds was decided as "underivable is a refusal, not a
default", and a refusal nobody tested is a default waiting to happen.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")


MOTOR = {
    "joint": "elbow",
    "motion_type": "angular",
    "kind": "motor",
    "control_nmm": "400*sin(2*pi*time)",
    "torque_limit_nmm": 800.0,
}
SERVO = {
    "joint": "shoulder",
    "motion_type": "angular",
    "kind": "position",
    "control_deg": "10",
    "stiffness_nmm_per_deg": 4000.0,
    "damping_nmms_per_deg": 120.0,
}

OBSERVATIONS = [
    {"kind": "position", "joint": "elbow", "motion_type": "angular",
     "name": "elbow_angle"},
    {"kind": "velocity", "joint": "elbow", "motion_type": "angular",
     "name": "elbow_rate"},
    {"kind": "component_position", "component": "fore", "name": "hand"},
    {"kind": "actuator_force", "joint": "elbow", "motion_type": "angular",
     "actuator_kind": "motor", "name": "effort"},
]

TASK = {
    "actions": [
        {"joint": "elbow", "motion_type": "angular", "actuator_kind": "motor"}
    ],
    "reward": [
        {"label": "reach", "expression": "-(hand_x - 300)**2", "weight": 1.0e-4},
        {"label": "control_cost", "expression": "abs(effort)", "weight": -1.0e-6},
    ],
    "termination": [
        {"label": "spun_out", "expression": "abs(elbow_rate)", "above": 2000.0}
    ],
    "episode_seconds": 4.0,
    "control_hz": 50,
    "randomisation": [],
    "label": "reach",
}


def _built(*, limits=True, actuators=(MOTOR,), joint_dynamics=()):
    components, joints, _placements = fx.two_link_arm(limits=limits)
    return dyn.build_model(
        components,
        joints,
        actuators=list(actuators),
        joint_dynamics=list(joint_dynamics),
    )


def _observations(built, entries=None):
    return dyn.observation_records(
        list(OBSERVATIONS if entries is None else entries),
        built["tree"],
        built["joint_records"],
        built["actuators"],
    )


def _bundle(built=None, task=None, entries=None):
    built = built or _built()
    observations = _observations(built, entries)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    bundle = dyn.task_records(
        built,
        reloaded,
        dict(TASK if task is None else task),
        observations=observations,
    )
    return built, reloaded, bundle, exported


# ---------------------------------------------------------------------------
# Observation channels.
# ---------------------------------------------------------------------------


def test_every_supported_kind_resolves_to_the_sensor_that_reads_it() -> None:
    """The table, exercised rather than restated.

    Each row's sensor, object type and object name, plus the unit and the
    scale a trainer multiplies by -- so a row edited in the table without a
    reason shows up as a changed number here.
    """

    built = _built(actuators=(MOTOR,))
    records = dyn.observation_records(
        [
            {"kind": "position", "joint": "elbow", "motion_type": "angular", "name": "a"},
            {"kind": "velocity", "joint": "elbow", "motion_type": "angular", "name": "b"},
            {"kind": "actuator_force", "joint": "elbow", "motion_type": "angular",
             "actuator_kind": "motor", "name": "c"},
            {"kind": "component_position", "component": "fore", "name": "d"},
            {"kind": "component_orientation", "component": "fore", "name": "e"},
            {"kind": "component_linear_velocity", "component": "fore", "name": "f"},
            {"kind": "component_angular_velocity", "component": "fore", "name": "g"},
            {"kind": "centre_of_mass", "component": "upper", "name": "h"},
        ],
        built["tree"],
        built["joint_records"],
        built["actuators"],
    )
    by_name = {record["name"]: record for record in records}

    assert by_name["a"]["sensor"] == "mjSENS_JOINTPOS"
    assert by_name["a"]["objtype"] == "mjOBJ_JOINT"
    assert by_name["a"]["object_name"] == "elbow"
    assert (by_name["a"]["unit"], by_name["a"]["scale"]) == (
        "deg",
        pytest.approx(57.29577951308232),
    )
    assert by_name["b"]["unit"] == "deg/s"
    assert by_name["c"]["objtype"] == "mjOBJ_ACTUATOR"
    assert by_name["c"]["object_name"] == "elbow/motor"
    assert (by_name["c"]["unit"], by_name["c"]["scale"]) == ("nmm", 1000.0)

    # The four component channels are xbody channels, which is the phase 0
    # finding turned into a property of the table: objtype="body" would
    # report the inertial frame and a reward naming a position would be
    # given the centre of mass instead.
    for name in ("d", "e", "f", "g"):
        assert by_name[name]["objtype"] == "mjOBJ_XBODY", name
    assert (by_name["d"]["unit"], by_name["d"]["scale"]) == ("mm", 1000.0)
    assert (by_name["e"]["unit"], by_name["e"]["scale"]) == ("quat", 1.0)
    assert (by_name["f"]["unit"], by_name["f"]["scale"]) == ("mm/s", 1000.0)
    assert by_name["g"]["unit"] == "deg/s"
    # ...and the centre of mass is not, because subtreecom is a mass-weighted
    # quantity over a subtree rather than a frame.
    assert by_name["h"]["objtype"] == "mjOBJ_BODY"

    # Positional MJCF names, in declaration order.
    assert [record["mujoco_sensor"] for record in records] == [
        f"obs/{index}" for index in range(8)
    ]


def test_a_vector_channel_expands_to_suffixed_scalar_names() -> None:
    """Reward formulas do arithmetic on scalars, so the names are scalars."""

    built = _built()
    records = dyn.observation_records(
        [
            {"kind": "component_position", "component": "fore", "name": "hand"},
            {"kind": "component_orientation", "component": "fore", "name": "grip"},
            {"kind": "position", "joint": "elbow", "motion_type": "angular",
             "name": "elbow_angle"},
        ],
        built["tree"],
        built["joint_records"],
        built["actuators"],
    )
    assert records[0]["channels"] == ["hand_x", "hand_y", "hand_z"]
    assert records[1]["channels"] == ["grip_qw", "grip_qx", "grip_qy", "grip_qz"]
    # A scalar channel keeps its own name with no suffix, so the common case
    # reads the way the script wrote it.
    assert records[2]["channels"] == ["elbow_angle"]


def test_two_channels_with_one_name_are_refused_including_by_expansion() -> None:
    """The collision an author would not see coming is the expanded one."""

    built = _built()
    with pytest.raises(dyn.DynamicsError) as plain:
        dyn.observation_records(
            [
                {"kind": "position", "joint": "elbow", "motion_type": "angular",
                 "name": "x"},
                {"kind": "velocity", "joint": "elbow", "motion_type": "angular",
                 "name": "x"},
            ],
            built["tree"],
            built["joint_records"],
            built["actuators"],
        )
    assert plain.value.reason == "duplicate_observation_channel"

    with pytest.raises(dyn.DynamicsError) as expanded:
        dyn.observation_records(
            [
                {"kind": "component_position", "component": "fore", "name": "hand"},
                {"kind": "position", "joint": "elbow", "motion_type": "angular",
                 "name": "hand_x"},
            ],
            built["tree"],
            built["joint_records"],
            built["actuators"],
        )
    assert expanded.value.reason == "duplicate_observation_channel"
    assert expanded.value.observed["channel"] == "hand_x"


def test_an_unsupported_kind_is_refused_and_a_deferred_one_says_why() -> None:
    built = _built()
    with pytest.raises(dyn.DynamicsError) as unknown:
        dyn.observation_records(
            [{"kind": "vibes", "component": "fore", "name": "x"}],
            built["tree"], built["joint_records"], built["actuators"],
        )
    assert unknown.value.reason == "unknown_observation_kind"
    assert "component_position" in unknown.value.correction

    # A kind MuJoCo plainly supports gets the reason it is absent rather
    # than being treated as a typo.
    with pytest.raises(dyn.DynamicsError) as deferred:
        dyn.observation_records(
            [{"kind": "touch", "component": "fore", "name": "x"}],
            built["tree"], built["joint_records"], built["actuators"],
        )
    assert "site" in str(deferred.value)


def test_a_channel_on_something_the_model_does_not_carry_is_refused() -> None:
    built = _built()
    with pytest.raises(dyn.DynamicsError) as component:
        dyn.observation_records(
            [{"kind": "component_position", "component": "gripper", "name": "x"}],
            built["tree"], built["joint_records"], built["actuators"],
        )
    assert component.value.reason == "observation_component_missing"
    assert component.value.observed["available"] == ["post", "upper", "fore"]

    with pytest.raises(dyn.DynamicsError) as actuator:
        dyn.observation_records(
            [{"kind": "actuator_force", "joint": "shoulder",
              "motion_type": "angular", "actuator_kind": "position", "name": "x"}],
            built["tree"], built["joint_records"], built["actuators"],
        )
    assert actuator.value.reason == "observation_actuator_missing"

    # And a joint that owns no coordinate is refused with the reason the
    # coordinate table already knows, not with "no such joint".
    components, joints, placements = fx.four_bar()
    loop = dyn.build_model(components, joints)
    closing = str(loop["tree"]["closures"][0]["joint"])
    with pytest.raises(dyn.DynamicsError) as closed:
        dyn.observation_records(
            [{"kind": "position", "joint": closing, "motion_type": "angular",
              "name": "x"}],
            loop["tree"], loop["joint_records"], loop["actuators"],
        )
    assert closed.value.reason == "joint_has_no_coordinate"
    assert "closes a loop" in str(closed.value)


def test_the_channel_count_is_capped_on_scalars_not_declarations() -> None:
    """A component_position is three channels, and the cap counts three."""

    built = _built()
    entries = [
        {"kind": "component_position", "component": "fore", "name": f"p{index}"}
        for index in range(dyn.MAXIMUM_OBSERVATION_CHANNELS // 3 + 1)
    ]
    with pytest.raises(dyn.DynamicsError) as excess:
        dyn.observation_records(
            entries, built["tree"], built["joint_records"], built["actuators"]
        )
    assert excess.value.reason == "too_many_observation_channels"
    assert excess.value.observed["channels"] > dyn.MAXIMUM_OBSERVATION_CHANNELS


# ---------------------------------------------------------------------------
# The export, with channels and without.
# ---------------------------------------------------------------------------


def test_an_export_with_no_observations_is_the_m5_export_byte_for_byte() -> None:
    """The M5 regression, stated as bytes rather than as intent.

    ``observations`` is defaulted and additive, and this is what keeps that
    true: an ``api.mjcf`` that declares no channels has to produce exactly
    the file it produced before M6 existed, or every M5 digest moved.
    """

    built = _built()
    before = dyn.export_mjcf(built)
    after = dyn.export_mjcf(built, observations=[])
    assert before["xml"] == after["xml"]
    assert b"<sensor" not in before["xml"]
    assert before["evidence"]["sensor_count"] == 0
    assert before["evidence"]["observation_channels"] == []
    assert before["evidence"]["worst_sensor_rel_error"] == 0.0


def test_channels_reach_the_exported_file_and_are_verified_there() -> None:
    built = _built()
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)

    assert b"<sensor>" in exported["xml"]
    assert exported["evidence"]["sensor_count"] == 4
    assert exported["evidence"]["sensor_value_count"] == 6
    assert exported["evidence"]["observation_channels"] == [
        "elbow_angle", "elbow_rate", "hand_x", "hand_y", "hand_z", "effort"
    ]
    # A sensor reads state MuJoCo already computed, so the reload agrees
    # exactly rather than within the field tolerance.
    assert exported["evidence"]["worst_sensor_rel_error"] == 0.0

    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    assert int(reloaded.nsensor) == 4
    assert reloaded.sensor_adr.tolist() == [0, 1, 2, 5]
    assert reloaded.sensor_dim.tolist() == [1, 1, 3, 1]


def test_adding_channels_does_not_move_the_model_that_was_simulated() -> None:
    """Phase 0 measured this once; the export re-takes it every time.

    The M5 claim is that the exported file is the model the engine
    simulated, and it is verified field by field against ``built["model"]``
    -- which has no sensors. So an export *with* channels passing that same
    verification is the receipt that the channels changed nothing.
    """

    built = _built()
    exported = dyn.export_mjcf(built, observations=_observations(built))
    assert exported["evidence"]["worst_field_rel_error"] < dyn.MJCF_FIELD_TOLERANCE
    assert exported["evidence"]["worst_pose_error_mm"] < dyn.MJCF_POSE_TOLERANCE_MM

    # And the trajectories agree to the bit over a real integration, which
    # is the strong form of the same claim.
    def _run(xml):
        model = mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
        data = mujoco.MjData(model)
        key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, dyn.MJCF_KEYFRAME_NAME)
        mujoco.mj_resetDataKeyframe(model, data, key)
        for _ in range(400):
            mujoco.mj_step(model, data)
        return data.qpos.tolist()

    assert _run(exported["xml"]) == _run(dyn.export_mjcf(built)["xml"])


# ---------------------------------------------------------------------------
# The action space: derivation, and the refusals that are the point.
# ---------------------------------------------------------------------------


def test_a_motor_action_range_is_its_effort_limit_in_the_unit_it_was_written() -> None:
    _built_model, _reloaded, bundle, _exported = _bundle()
    action = bundle["actions"][0]
    assert action["actuator"] == "elbow/motor"
    assert action["index"] == 0
    assert action["unit"] == "nmm"
    assert (action["low"], action["high"]) == (-800.0, 800.0)
    assert action["source"] == "torque_limit_nmm"
    # The scale carries one N·mm into what ``data.ctrl`` reads, so the
    # runner multiplies rather than converts -- and it is the *forward*
    # conversion, unlike an observation's.
    assert action["scale"] == pytest.approx(0.001)
    assert action["fallback"] == "400*sin(2*pi*time)"


def test_a_position_action_range_is_the_joints_own_declared_limits() -> None:
    built = _built(actuators=(SERVO,))
    observations = dyn.observation_records(
        [{"kind": "position", "joint": "shoulder", "motion_type": "angular",
          "name": "angle"}],
        built["tree"], built["joint_records"], built["actuators"],
    )
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    bundle = dyn.task_records(
        built,
        reloaded,
        {
            **TASK,
            "actions": [{"joint": "shoulder", "motion_type": "angular",
                         "actuator_kind": "position"}],
            "reward": [{"label": "hold", "expression": "-abs(angle)",
                        "weight": 1.0}],
            "termination": [],
        },
        observations=observations,
    )
    action = bundle["actions"][0]
    assert action["unit"] == "deg"
    assert (action["low"], action["high"]) == tuple(
        fx.ARM_LIMITS_DEGREES["shoulder"]
    )
    assert action["source"] == "angle_limits_degrees"
    assert action["scale"] == pytest.approx(dyn.angle_radians(1.0))


def test_a_velocity_actuator_has_no_derivable_action_range() -> None:
    """Nothing in a FreeCAD assembly states a speed limit, so this refuses.

    The alternative would be picking a number, and a made-up speed bound is
    a mechanism nobody designed presented to a policy as if it were one.
    """

    velocity = {
        "joint": "elbow",
        "motion_type": "angular",
        "kind": "velocity",
        "control_deg_per_s": "90",
        "damping_nmms_per_deg": 40.0,
    }
    built = _built(actuators=(velocity,))
    observations = dyn.observation_records(
        [{"kind": "position", "joint": "elbow", "motion_type": "angular",
          "name": "angle"}],
        built["tree"], built["joint_records"], built["actuators"],
    )
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    with pytest.raises(dyn.DynamicsError) as refusal:
        dyn.task_records(
            built,
            reloaded,
            {
                **TASK,
                "actions": [{"joint": "elbow", "motion_type": "angular",
                             "actuator_kind": "velocity"}],
                "reward": [{"label": "hold", "expression": "-abs(angle)",
                            "weight": 1.0}],
                "termination": [],
            },
            observations=observations,
        )
    assert refusal.value.reason == "action_range_underivable"
    assert "speed" in str(refusal.value)
    # The correction names both ways out rather than merely saying no.
    assert "motor actuator" in refusal.value.correction
    assert "position actuator" in refusal.value.correction


def test_a_motor_with_no_effort_limit_has_no_derivable_action_range() -> None:
    motor = {key: value for key, value in MOTOR.items() if key != "torque_limit_nmm"}
    built = _built(actuators=(motor,))
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    with pytest.raises(dyn.DynamicsError) as refusal:
        dyn.task_records(built, reloaded, dict(TASK), observations=observations)
    assert refusal.value.reason == "action_range_underivable"
    assert "torque_limit_nmm" in refusal.value.correction


def test_a_position_actuator_on_an_unlimited_joint_is_refused() -> None:
    built = _built(limits=False, actuators=(SERVO,))
    observations = dyn.observation_records(
        [{"kind": "position", "joint": "shoulder", "motion_type": "angular",
          "name": "angle"}],
        built["tree"], built["joint_records"], built["actuators"],
    )
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    with pytest.raises(dyn.DynamicsError) as refusal:
        dyn.task_records(
            built,
            reloaded,
            {
                **TASK,
                "actions": [{"joint": "shoulder", "motion_type": "angular",
                             "actuator_kind": "position"}],
                "reward": [{"label": "hold", "expression": "-abs(angle)",
                            "weight": 1.0}],
                "termination": [],
            },
            observations=observations,
        )
    assert refusal.value.reason == "action_range_underivable"
    assert "angle_limits_degrees" in refusal.value.correction


def test_a_one_sided_limit_is_a_refusal_rather_than_a_hundred_turns() -> None:
    """The refusal phase 0's margin measurement exists to justify."""

    components, joints, _placements = fx.two_link_arm(limits=True)
    for joint in joints:
        if joint["name"] == "shoulder":
            joint["angle_limits_degrees"] = [None, 95.0]
    built = dyn.build_model(components, joints, actuators=[SERVO])
    observations = dyn.observation_records(
        [{"kind": "position", "joint": "shoulder", "motion_type": "angular",
          "name": "angle"}],
        built["tree"], built["joint_records"], built["actuators"],
    )
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    with pytest.raises(dyn.DynamicsError) as refusal:
        dyn.task_records(
            built,
            reloaded,
            {
                **TASK,
                "actions": [{"joint": "shoulder", "motion_type": "angular",
                             "actuator_kind": "position"}],
                "reward": [{"label": "hold", "expression": "-abs(angle)",
                            "weight": 1.0}],
                "termination": [],
            },
            observations=observations,
        )
    assert refusal.value.reason == "action_range_underivable"
    assert "hundred turns" in refusal.value.correction
    # The pair is reported as declared, missing endpoint and all, so the
    # refusal says *which* end is absent rather than merely that one is.
    assert refusal.value.observed["declared"] == [None, 95.0]


def test_an_action_naming_an_actuator_the_model_lacks_is_refused() -> None:
    built = _built()
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    with pytest.raises(dyn.DynamicsError) as missing:
        dyn.task_records(
            built,
            reloaded,
            {**TASK, "actions": [{"joint": "shoulder", "motion_type": "angular",
                                  "actuator_kind": "motor"}]},
            observations=observations,
        )
    assert missing.value.reason == "action_actuator_missing"
    assert missing.value.observed["available"] == ["elbow/motor"]

    with pytest.raises(dyn.DynamicsError) as twice:
        dyn.task_records(
            built,
            reloaded,
            {**TASK, "actions": list(TASK["actions"]) * 2},
            observations=observations,
        )
    assert twice.value.reason == "duplicate_action"


def test_a_task_with_no_action_or_no_reward_is_refused() -> None:
    built = _built()
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    with pytest.raises(dyn.DynamicsError) as no_actions:
        dyn.task_records(
            built, reloaded, {**TASK, "actions": []}, observations=observations
        )
    assert no_actions.value.reason == "task_has_no_actions"
    with pytest.raises(dyn.DynamicsError) as no_reward:
        dyn.task_records(
            built, reloaded, {**TASK, "reward": []}, observations=observations
        )
    assert no_reward.value.reason == "task_has_no_reward"


# ---------------------------------------------------------------------------
# Reward and termination.
# ---------------------------------------------------------------------------


def test_a_reward_may_name_only_the_channels_this_task_declares() -> None:
    built = _built()
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    with pytest.raises(dyn.DynamicsError) as unknown:
        dyn.task_records(
            built,
            reloaded,
            {**TASK, "reward": [{"label": "r", "expression": "shoulder_angle",
                                 "weight": 1.0}]},
            observations=observations,
        )
    assert unknown.value.reason == "reward_names_unknown_channel"
    assert unknown.value.observed["unknown"] == ["shoulder_angle"]
    # The correction lists what *is* available, which is the whole point of
    # refusing at the engine rather than at the API: only here is the
    # expanded channel list known.
    assert "hand_x" in unknown.value.correction

    # Naming the unexpanded vector is the mistake worth catching by name.
    with pytest.raises(dyn.DynamicsError) as unexpanded:
        dyn.task_records(
            built,
            reloaded,
            {**TASK, "reward": [{"label": "r", "expression": "hand", "weight": 1.0}]},
            observations=observations,
        )
    assert unexpanded.value.observed["unknown"] == ["hand"]


def test_the_reward_whitelist_is_the_control_one_plus_three() -> None:
    """``exp``, ``sqrt`` and ``tanh``, and ``api.motion``'s set untouched."""

    control = {
        name for name, value in dyn._CONTROL_GLOBALS.items() if callable(value)
    }
    assert set(dyn.REWARD_FUNCTIONS) == control | {"exp", "sqrt", "tanh"}
    assert dyn.REWARD_FUNCTIONS == tuple(sorted(dyn.REWARD_FUNCTIONS))
    # The array the bundle ships is this tuple, so the reference runner can
    # be asserted equal to it rather than kept equal by attention.
    _b, _r, bundle, _e = _bundle()
    assert bundle["functions"] == list(dyn.REWARD_FUNCTIONS)


def test_a_reward_that_is_not_a_finite_number_is_refused_at_evaluation() -> None:
    code = dyn.compile_reward("1.0/x", names=["x"], context="reward 'r'")
    assert dyn.evaluate_reward(code, {"x": 2.0}, context="reward 'r'") == 0.5
    with pytest.raises(dyn.DynamicsError) as blown:
        dyn.evaluate_reward(code, {"x": 0.0}, context="reward 'r'")
    assert blown.value.reason == "reward_formula_failed"


def test_a_termination_rule_needs_a_threshold() -> None:
    built = _built()
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    with pytest.raises(dyn.DynamicsError) as bare:
        dyn.task_records(
            built,
            reloaded,
            {**TASK, "termination": [{"label": "t", "expression": "elbow_rate"}]},
            observations=observations,
        )
    assert bare.value.reason == "malformed_termination"


# ---------------------------------------------------------------------------
# The episode schedule.
# ---------------------------------------------------------------------------


def test_a_control_step_is_a_whole_number_of_solver_steps() -> None:
    _b, _r, bundle, _e = _bundle()
    episode = bundle["episode"]
    assert episode["control_hz"] == 50
    # The default solver step is 0.002 s, so 50 Hz is exactly ten of them.
    assert episode["solver_step_s"] == pytest.approx(dyn.DEFAULT_TIME_STEP_S)
    assert episode["solver_steps_per_action"] == 10
    assert episode["control_interval_s"] == pytest.approx(0.02)
    assert episode["max_steps"] == 200
    assert episode["episode_seconds"] == pytest.approx(4.0)
    assert episode["reset_keyframe"] == dyn.MJCF_KEYFRAME_NAME
    assert episode["reward_stage"] == "after_step"


def test_a_control_rate_the_solver_cannot_carry_is_refused_with_its_ceiling() -> None:
    built = _built()
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    with pytest.raises(dyn.DynamicsError) as fast:
        dyn.task_records(
            built, reloaded, {**TASK, "control_hz": 5000},
            observations=observations,
        )
    assert fast.value.reason == "control_rate_too_high"
    # The ceiling is named, so the refusal is one a model can act on.
    assert "500 Hz" in fast.value.correction


def test_a_rate_that_does_not_divide_the_solver_step_is_rounded_and_reported() -> None:
    """The rounding ``api.dynamics`` already does for frames.

    30 Hz is 16.67 steps of 0.002 s, so it rounds to 17 and the episode
    really runs at 29.4 Hz. Reporting the rounded interval rather than the
    requested rate is what keeps two runs comparable.
    """

    built = _built()
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    bundle = dyn.task_records(
        built, reloaded, {**TASK, "control_hz": 30}, observations=observations
    )
    episode = bundle["episode"]
    assert episode["solver_steps_per_action"] == 17
    assert episode["control_interval_s"] == pytest.approx(0.034)
    assert episode["control_hz"] == 30
    assert episode["episode_seconds"] == pytest.approx(120 * 0.034)


# ---------------------------------------------------------------------------
# Randomisation.
# ---------------------------------------------------------------------------


def test_a_mass_draw_resolves_to_the_mass_and_its_three_inertia_entries() -> None:
    """Phase 0's finding, as the shape of a bundle entry."""

    built = _built(
        joint_dynamics=[{"joint": "elbow", "motion_type": "angular",
                         "damping_nmms_per_deg": 12.0}]
    )
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    bundle = dyn.task_records(
        built,
        reloaded,
        {
            **TASK,
            "randomisation": [
                {"target": "mass", "component": "fore", "low": 0.9, "high": 1.1,
                 "label": "forearm_mass"},
                {"target": "damping", "joint": "elbow", "motion_type": "angular",
                 "low": 0.5, "high": 2.0, "label": "elbow_damping"},
            ],
        },
        observations=observations,
    )
    mass, damping = bundle["randomisation"]
    fore = mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_BODY, "fore")
    assert mass["mode"] == "scale"
    assert mass["fields"] == [
        {"field": "body_mass", "index": fore},
        {"field": "body_inertia", "index": 3 * fore},
        {"field": "body_inertia", "index": 3 * fore + 1},
        {"field": "body_inertia", "index": 3 * fore + 2},
    ]
    elbow = mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_JOINT, "elbow")
    assert damping["fields"] == [
        {"field": "dof_damping", "index": int(reloaded.jnt_dofadr[elbow])}
    ]


def test_a_mass_range_that_would_zero_a_mass_is_refused() -> None:
    built = _built()
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    with pytest.raises(dyn.DynamicsError) as zeroed:
        dyn.task_records(
            built,
            reloaded,
            {**TASK, "randomisation": [
                {"target": "mass", "component": "fore", "low": 0.0, "high": 1.1}
            ]},
            observations=observations,
        )
    assert zeroed.value.reason == "malformed_randomisation"
    assert "undefined acceleration" in zeroed.value.correction

    with pytest.raises(dyn.DynamicsError) as unknown:
        dyn.task_records(
            built,
            reloaded,
            {**TASK, "randomisation": [
                {"target": "stiffness", "component": "fore", "low": 0.9, "high": 1.1}
            ]},
            observations=observations,
        )
    assert unknown.value.reason == "unknown_randomisation_target"


def test_a_draw_scales_the_named_fields_and_the_subtree_mass_with_them() -> None:
    built = _built()
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    bundle = dyn.task_records(
        built,
        reloaded,
        {**TASK, "randomisation": [
            {"target": "mass", "component": "fore", "low": 1.5, "high": 1.5,
             "label": "heavy"}
        ]},
        observations=observations,
    )
    fore = mujoco.mj_name2id(reloaded, mujoco.mjtObj.mjOBJ_BODY, "fore")
    mass_before = float(reloaded.body_mass[fore])
    inertia_before = list(reloaded.body_inertia[fore].tolist())
    subtree_before = float(reloaded.body_subtreemass[0])

    data = mujoco.MjData(reloaded)
    drawn = dyn.apply_randomisation(mujoco, reloaded, data, bundle, seed=7)

    assert drawn == [{"label": "heavy", "factor": 1.5}]
    assert float(reloaded.body_mass[fore]) == pytest.approx(1.5 * mass_before)
    assert reloaded.body_inertia[fore].tolist() == pytest.approx(
        [1.5 * value for value in inertia_before]
    )
    # ``mj_setConst`` propagated it, which is the half a draw that skipped
    # the call would silently lose.
    assert float(reloaded.body_subtreemass[0]) == pytest.approx(
        subtree_before + 0.5 * mass_before
    )


# ---------------------------------------------------------------------------
# The episode.
# ---------------------------------------------------------------------------


def test_an_episode_runs_from_the_bundle_alone() -> None:
    """The bundle is the only input besides the model, which is the point.

    Both evaluators consume the same file, so a disagreement between them is
    a disagreement about the task spec rather than about which side had more
    information.
    """

    _b, reloaded, bundle, _e = _bundle()
    episode = dyn.evaluate_episode(reloaded, bundle)

    assert episode["step_count"] == bundle["episode"]["max_steps"]
    assert episode["truncated"] is True
    assert episode["terminated_step"] is None
    assert episode["seed"] is None
    assert len(episode["steps"]) == 200

    first = episode["steps"][0]
    assert sorted(first["observation"]) == [
        "effort", "elbow_angle", "elbow_rate", "hand_x", "hand_y", "hand_z"
    ]
    # Units are the surface's, which is what the scale factors are for: the
    # forearm starts 300 mm out in x rather than 0.3.
    assert first["observation"]["hand_x"] == pytest.approx(300.0, abs=1.0)
    assert [term["label"] for term in first["reward_terms"]] == [
        "reach", "control_cost"
    ]
    assert episode["total_reward"] == pytest.approx(
        sum(step["reward"] for step in episode["steps"])
    )
    # The elbow is held near its declared limit rather than spinning. Near
    # rather than at: MuJoCo's joint limits are *soft* constraints, so a
    # driven joint pushed into one overshoots it and is pushed back --
    # measured here at about 10 degrees past a limit the motor is driving
    # hard into. This is worth stating because an action range derived from
    # jnt_range is not a hard promise about where the joint can go, and a
    # reward that assumed it were would be scored outside its own domain.
    angles = [step["observation"]["elbow_angle"] for step in episode["steps"]]
    low, high = fx.ARM_LIMITS_DEGREES["elbow"]
    assert min(angles) < low, "the motor really does drive into the limit"
    assert min(angles) >= low - 15.0
    assert max(angles) <= high + 15.0


def test_an_episode_is_reproducible_and_its_reward_is_the_weighted_sum() -> None:
    _b, reloaded, bundle, _e = _bundle()
    first = dyn.evaluate_episode(reloaded, bundle)
    second = dyn.evaluate_episode(reloaded, bundle)
    assert first["total_reward"] == second["total_reward"]
    assert [step["observation"] for step in first["steps"]] == [
        step["observation"] for step in second["steps"]
    ]
    step = first["steps"][5]
    assert step["reward"] == pytest.approx(
        sum(term["weighted"] for term in step["reward_terms"])
    )
    for term, declared in zip(step["reward_terms"], bundle["reward"], strict=True):
        assert term["weighted"] == pytest.approx(
            float(declared["weight"]) * term["value"]
        )


def test_the_fallback_action_is_the_control_formula_the_script_already_wrote() -> None:
    """No policy, and the episode still runs -- which is what M8 replaces."""

    _b, reloaded, bundle, _e = _bundle()
    episode = dyn.evaluate_episode(reloaded, bundle)
    interval = bundle["episode"]["control_interval_s"]
    for index in (0, 3, 17):
        expected = 400.0 * math.sin(2.0 * math.pi * index * interval)
        assert episode["steps"][index]["action"][0] == pytest.approx(expected)


def test_an_action_is_clamped_to_the_range_the_bundle_advertises() -> None:
    """A policy that ignores the bound cannot drive a different mechanism."""

    _b, reloaded, bundle, _e = _bundle()
    low, high = bundle["actions"][0]["low"], bundle["actions"][0]["high"]
    episode = dyn.evaluate_episode(
        reloaded, bundle, actions=lambda step, observation: [1.0e6]
    )
    assert all(step["action"] == [high] for step in episode["steps"])

    episode = dyn.evaluate_episode(
        reloaded, bundle, actions=lambda step, observation: [-1.0e6]
    )
    assert all(step["action"] == [low] for step in episode["steps"])

    # A policy is handed the observation it is acting on, in surface units.
    seen: list[dict[str, float]] = []

    def _policy(step, observation):
        seen.append(dict(observation))
        return [0.0]

    dyn.evaluate_episode(reloaded, bundle, actions=_policy)
    assert len(seen) == bundle["episode"]["max_steps"]
    assert seen[0]["hand_x"] == pytest.approx(300.0, abs=1.0)


def test_a_wrong_shaped_action_is_refused_rather_than_broadcast() -> None:
    _b, reloaded, bundle, _e = _bundle()
    with pytest.raises(dyn.DynamicsError) as shape:
        dyn.evaluate_episode(
            reloaded, bundle, actions=lambda step, observation: [0.0, 0.0]
        )
    assert shape.value.reason == "action_shape_mismatch"


def test_termination_ends_the_episode_at_the_step_that_crossed() -> None:
    _b, reloaded, bundle, _e = _bundle()
    # A threshold the arm crosses almost immediately under gravity, so the
    # rule fires on a real trajectory rather than on a contrived one.
    bundle = {
        **bundle,
        "termination": [
            {"label": "spun_out", "expression": "abs(elbow_rate)", "above": 30.0,
             "below": None}
        ],
    }
    episode = dyn.evaluate_episode(reloaded, bundle)
    assert episode["terminated_step"] is not None
    assert episode["termination"] == "spun_out"
    assert episode["truncated"] is False
    assert episode["step_count"] == episode["terminated_step"] + 1
    assert episode["steps"][-1]["terminated"] is True
    assert abs(episode["steps"][-1]["observation"]["elbow_rate"]) > 30.0
    # Every earlier step was under the threshold, so the episode stopped at
    # the first crossing rather than at some later one.
    assert all(
        abs(step["observation"]["elbow_rate"]) <= 30.0
        for step in episode["steps"][:-1]
    )


def test_a_below_threshold_terminates_too() -> None:
    _b, reloaded, bundle, _e = _bundle()
    bundle = {
        **bundle,
        "termination": [
            {"label": "dropped", "expression": "hand_z", "above": None,
             "below": 150.0}
        ],
    }
    episode = dyn.evaluate_episode(reloaded, bundle)
    assert episode["termination"] == "dropped"
    assert episode["steps"][-1]["observation"]["hand_z"] < 150.0


def test_the_same_seed_draws_the_same_factors_and_a_different_one_does_not() -> None:
    built = _built()
    observations = _observations(built)
    exported = dyn.export_mjcf(built, observations=observations)
    declaration = {
        **TASK,
        "randomisation": [
            {"target": "mass", "component": "fore", "low": 0.5, "high": 1.5,
             "label": "forearm_mass"}
        ],
    }

    def _episode(seed):
        model = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
        bundle = dyn.task_records(
            built, model, declaration, observations=observations
        )
        return dyn.evaluate_episode(model, bundle, seed=seed)

    first = _episode(11)
    again = _episode(11)
    other = _episode(12)

    assert first["randomisation"] == again["randomisation"]
    assert first["total_reward"] == again["total_reward"]
    assert first["randomisation"] != other["randomisation"]
    # A draw that changed the mass changed the trajectory, so the seed is
    # doing something rather than being recorded and ignored.
    assert first["total_reward"] != other["total_reward"]
    assert 0.5 <= first["randomisation"][0]["factor"] <= 1.5
