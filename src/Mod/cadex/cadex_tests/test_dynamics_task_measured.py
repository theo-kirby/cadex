# SPDX-License-Identifier: LGPL-2.1-or-later

"""What MuJoCo does with sensors, control ranges and field writes (M6 phase 0).

The sibling of :mod:`test_dynamics_mjcf_measured`, and it keeps that file's
rule: nothing here imports the M6 translator. Every assertion is about
``mujoco`` 3.10.0 and the spec ``build_model`` already produces, so a failure
names MuJoCo rather than the task surface, and the numbers pinned here are
what phase 1 is later allowed to verify itself against.

A task is data, not geometry -- but the *observation vector* is computed by
MuJoCo, which means the whole surface rests on measurements nobody had taken
yet. Eight findings, each with a test rather than a comment:

1. ``MjSpec.add_sensor`` round-trips through ``to_xml()`` field by field.
   ``nsensor``, ``nsensordata``, ``sensor_adr``, ``sensor_dim``,
   ``sensor_objid`` and ``sensor_type`` all survive, and the first channel's
   value **is** ``qpos`` rather than something derived from it.
2. **Sensors are dynamically inert.** 500 steps with four of them give
   ``qpos`` bit-identical to the same model without them. This is what lets
   M5's claim -- the exported file *is* the simulated model -- survive the
   addition, and it is a measurement rather than a reading of the manual.
3. Each supported sensor kind's dimension and value, against the quantity it
   is supposed to equal. This is the table the M6 scale factors are derived
   from.
4. **The one that would have been silently wrong.** A frame sensor with
   ``objtype="body"`` reads the body's *inertial* frame, not the frame the
   assembly solver placed: ``framequat`` on a link returns the orientation
   of its principal axes of inertia -- a **half turn** off the link's own
   frame on a plain box -- and ``framepos`` on a body with an offset centre
   of mass returns the centre of mass rather than the origin.
   ``objtype="xbody"`` is the component's own frame. M6's ``component_*``
   channels are xbody channels for exactly this reason.
5. ``ctrlrange`` is inert unless ``ctrllimited`` is set, and once set MuJoCo
   clamps the *applied effort* while leaving ``data.ctrl`` alone -- so a
   bound action space is a property of the model rather than of the caller.
6. A **one-sided** joint limit reaches ``jnt_range`` as a synthetic number:
   the missing endpoint is filled from ``_OPEN_ANGLE_MARGIN_RADIANS``, which
   is a hundred turns. Deriving an action range from it would invent a
   mechanical limit, so phase 2 refuses it -- and this is the measurement
   behind that refusal.
7. Each randomisation target's field index, and what writing it moves.
   Scaling ``body_mass`` alone leaves ``body_inertia`` untouched, which is a
   body whose rotational inertia no longer matches its mass; a mass draw has
   to scale both, and that is measured here rather than assumed.
8. Episode determinism across processes, and the XML byte cost per sensor
   that sizes phase 1's channel cap.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")


# ---------------------------------------------------------------------------
# Helpers. Sensors are added to a *copy* of the spec throughout, the way
# ``export_mjcf`` already copies before adding its keyframe: a measurement
# that mutated the built model would make finding 2 unprovable.
# ---------------------------------------------------------------------------


def _built(*, limits=False, actuators=(), joint_dynamics=(), inertials=None):
    components, joints, _placements = fx.two_link_arm(
        shoulder=0.3, elbow=-0.4, limits=limits
    )
    for component in components:
        if inertials and component["name"] in inertials:
            component["inertial"] = inertials[component["name"]]
    return dyn.build_model(
        components,
        joints,
        actuators=list(actuators),
        joint_dynamics=list(joint_dynamics),
    )


def _with_sensors(built, entries, *, keyframe=True):
    """One built model plus sensors, compiled, written and reloaded."""

    spec = built["spec"].copy()
    for index, entry in enumerate(entries):
        sensor = spec.add_sensor()
        sensor.name = entry.get("name", f"obs/{index}")
        sensor.type = entry["type"]
        sensor.objtype = entry["objtype"]
        sensor.objname = entry["objname"]
    if keyframe:
        spec.add_key(name=dyn.MJCF_KEYFRAME_NAME, qpos=list(built["qpos_solved"]))
    spec.compile()
    xml = spec.to_xml()
    return mujoco.MjModel.from_xml_string(xml), xml


def _at_keyframe(model):
    data = mujoco.MjData(model)
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, dyn.MJCF_KEYFRAME_NAME)
    assert key >= 0
    mujoco.mj_resetDataKeyframe(model, data, key)
    mujoco.mj_forward(model, data)
    return data


def _channel(model, data, index):
    adr = int(model.sensor_adr[index])
    dim = int(model.sensor_dim[index])
    return data.sensordata[adr : adr + dim].tolist()


JOINT = mujoco.mjtObj.mjOBJ_JOINT
BODY = mujoco.mjtObj.mjOBJ_BODY
XBODY = mujoco.mjtObj.mjOBJ_XBODY
ACTUATOR = mujoco.mjtObj.mjOBJ_ACTUATOR


# ---------------------------------------------------------------------------
# 1. The round trip, field by field.
# ---------------------------------------------------------------------------


def test_sensors_round_trip_through_to_xml() -> None:
    """Three sensors survive ``to_xml()`` and reload as the same three.

    Every field the M6 bundle later records an index into is asserted here,
    because the bundle's ``adr``/``dim`` pair is what a trainer slices
    ``sensordata`` with: an off-by-one there is a policy trained on the wrong
    number, and it looks like a policy that failed to learn.
    """

    built = _built()
    model, xml = _with_sensors(
        built,
        [
            {"type": mujoco.mjtSensor.mjSENS_JOINTPOS, "objtype": JOINT, "objname": "shoulder"},
            {"type": mujoco.mjtSensor.mjSENS_JOINTVEL, "objtype": JOINT, "objname": "elbow"},
            {"type": mujoco.mjtSensor.mjSENS_FRAMEPOS, "objtype": XBODY, "objname": "fore"},
        ],
    )

    assert "<sensor>" in xml
    assert int(model.nsensor) == 3
    assert int(model.nsensordata) == 5
    assert model.sensor_adr.tolist() == [0, 1, 2]
    assert model.sensor_dim.tolist() == [1, 1, 3]
    assert model.sensor_type.tolist() == [
        int(mujoco.mjtSensor.mjSENS_JOINTPOS),
        int(mujoco.mjtSensor.mjSENS_JOINTVEL),
        int(mujoco.mjtSensor.mjSENS_FRAMEPOS),
    ]
    assert model.sensor_objtype.tolist() == [int(JOINT), int(JOINT), int(XBODY)]
    # Resolved to *ids*, so a name that survived the file but pointed
    # somewhere else would show up here rather than in a trained policy.
    assert model.sensor_objid.tolist() == [
        mujoco.mj_name2id(model, JOINT, "shoulder"),
        mujoco.mj_name2id(model, JOINT, "elbow"),
        mujoco.mj_name2id(model, BODY, "fore"),
    ]
    assert [
        mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_SENSOR, index)
        for index in range(model.nsensor)
    ] == ["obs/0", "obs/1", "obs/2"]

    data = _at_keyframe(model)
    # The observation vector is computed by stock MuJoCo, not by us: the
    # first channel *is* ``qpos[0]``, to the bit, rather than something
    # derived from it.
    assert _channel(model, data, 0) == [data.qpos[0]]
    # And that qpos is the solved shoulder angle to the tolerance M5
    # measured, not to the bit -- the keyframe went through the same
    # six-significant-figure writer as every other number in the file, and
    # 0.3000000000000001 comes back as 0.3. Worth stating rather than
    # papering over: it is the floor on how exactly any observation can
    # agree with the engine that wrote the file.
    assert _channel(model, data, 0)[0] != built["qpos_solved"][0]
    assert _channel(model, data, 0)[0] == pytest.approx(
        built["qpos_solved"][0], rel=dyn.MJCF_FIELD_TOLERANCE
    )
    assert _channel(model, data, 1) == [0.0]
    fore = mujoco.mj_name2id(model, BODY, "fore")
    assert _channel(model, data, 2) == data.xpos[fore].tolist()


# ---------------------------------------------------------------------------
# 2. Inertness -- the finding M5's claim depends on.
# ---------------------------------------------------------------------------


FOUR_SENSORS = [
    {"type": mujoco.mjtSensor.mjSENS_JOINTPOS, "objtype": JOINT, "objname": "shoulder"},
    {"type": mujoco.mjtSensor.mjSENS_JOINTVEL, "objtype": JOINT, "objname": "elbow"},
    {"type": mujoco.mjtSensor.mjSENS_FRAMEPOS, "objtype": XBODY, "objname": "fore"},
    {"type": mujoco.mjtSensor.mjSENS_SUBTREECOM, "objtype": BODY, "objname": "upper"},
]


def _stepped(entries, steps=500):
    built = _built()
    model, xml = _with_sensors(built, entries)
    data = _at_keyframe(model)
    for _ in range(steps):
        mujoco.mj_step(model, data)
    return data.qpos.tolist(), len(xml.encode("utf-8"))


def test_sensors_do_not_move_the_simulation() -> None:
    """500 steps, four sensors, bit-identical ``qpos``.

    Not "within tolerance" -- *identical*. A sensor is a read of state
    MuJoCo already computed, so the difference is exactly zero, and stating
    it as zero is what makes a future MuJoCo that changes this loud. M5 sold
    the exported file as being the simulated model; M6 adds elements to that
    file, and this is the receipt that it stayed true.
    """

    with_sensors, with_bytes = _stepped(FOUR_SENSORS)
    without_sensors, without_bytes = _stepped([])

    assert with_sensors == without_sensors
    assert [a - b for a, b in zip(with_sensors, without_sensors)] == [0.0, 0.0]
    # The mechanism actually moved, so the comparison is between two
    # trajectories rather than between two models that both sat still.
    assert max(abs(value) for value in with_sensors) > 1.0
    assert with_bytes > without_bytes


def test_the_xml_cost_of_a_sensor_is_about_sixty_bytes() -> None:
    """What a channel costs the file, which is what sizes phase 1's cap.

    Measured at 54 bytes a sensor on the arm. The assertion is a band rather
    than the number, because the cost is the length of a name plus an
    element and both are fixture-specific; what matters is the order of
    magnitude, and it is small enough that the channel cap is about
    comprehensibility rather than about bytes.
    """

    _qpos, with_bytes = _stepped(FOUR_SENSORS, steps=1)
    _qpos, without_bytes = _stepped([], steps=1)
    per_sensor = (with_bytes - without_bytes) / len(FOUR_SENSORS)
    assert 30.0 < per_sensor < 120.0


# ---------------------------------------------------------------------------
# 3. Per-kind dimension and value: the table the scale factors come from.
# ---------------------------------------------------------------------------


def test_each_supported_sensor_kind_reads_the_quantity_it_names() -> None:
    """Dimension and value per kind, against what it should equal.

    One test rather than a parametrisation because the *point* is the table:
    a reader deciding what ``OBSERVATION_KINDS`` may contain wants the whole
    set in one place, with the MuJoCo quantity each row is equal to.
    """

    built = _built()
    fore, upper = "fore", "upper"
    entries = [
        ("position", mujoco.mjtSensor.mjSENS_JOINTPOS, JOINT, "elbow", 1),
        ("velocity", mujoco.mjtSensor.mjSENS_JOINTVEL, JOINT, "elbow", 1),
        ("component_position", mujoco.mjtSensor.mjSENS_FRAMEPOS, XBODY, fore, 3),
        ("component_orientation", mujoco.mjtSensor.mjSENS_FRAMEQUAT, XBODY, fore, 4),
        ("component_linear_velocity", mujoco.mjtSensor.mjSENS_FRAMELINVEL, XBODY, fore, 3),
        ("component_angular_velocity", mujoco.mjtSensor.mjSENS_FRAMEANGVEL, XBODY, fore, 3),
        ("centre_of_mass", mujoco.mjtSensor.mjSENS_SUBTREECOM, BODY, upper, 3),
        ("centre_of_mass_velocity", mujoco.mjtSensor.mjSENS_SUBTREELINVEL, BODY, upper, 3),
    ]
    model, _xml = _with_sensors(
        built,
        [
            {"type": kind, "objtype": objtype, "objname": objname}
            for _label, kind, objtype, objname, _dim in entries
        ],
    )
    data = _at_keyframe(model)
    assert model.sensor_dim.tolist() == [dim for *_rest, dim in entries]

    fore_id = mujoco.mj_name2id(model, BODY, fore)
    upper_id = mujoco.mj_name2id(model, BODY, upper)
    # ``subtree_linvel`` is filled by a velocity-stage pass rather than by
    # ``mj_forward``'s position stage. MuJoCo runs it itself for the sensor;
    # calling it here is what lets the *expectation* be read off the field
    # rather than restated as a literal.
    mujoco.mj_subtreeVel(model, data)
    expected = {
        "position": [data.qpos[1]],
        "velocity": [data.qvel[1]],
        "component_position": data.xpos[fore_id].tolist(),
        "component_orientation": data.xquat[fore_id].tolist(),
        "component_linear_velocity": [0.0, 0.0, 0.0],
        "component_angular_velocity": [0.0, 0.0, 0.0],
        "centre_of_mass": data.subtree_com[upper_id].tolist(),
        "centre_of_mass_velocity": data.subtree_linvel[upper_id].tolist(),
    }
    for index, (label, *_rest) in enumerate(entries):
        assert _channel(model, data, index) == pytest.approx(
            expected[label], abs=1.0e-12
        ), label

    # The two that carry a unit the surface has to convert: a joint angle is
    # radians and a position is metres, which is hazard 1's M6 form. The
    # solved elbow was authored as -0.4 rad, and the forearm sits 286.6 mm
    # out in x.
    assert _channel(model, data, 0) == [pytest.approx(-0.4, abs=1.0e-12)]
    assert dyn.length_mm(_channel(model, data, 2)[0]) == pytest.approx(
        286.60094673768177, abs=1.0e-9
    )


def test_the_subtree_velocity_is_not_the_frame_velocity_of_the_same_part() -> None:
    """Why ``centre_of_mass_velocity`` is its own kind (ADR-112).

    The table above reads both velocity channels at the keyframe, where
    everything is zero and any two velocity sensors agree. They agree there
    and nowhere else, which is the trap: a balance reward that reached for
    the frame channel because it was already declared would be given the
    velocity of *one link's origin* where it asked for the velocity of the
    whole machine's centre of mass.

    On the mg-legs machine that difference measured 19% at recovery speeds
    -- 9 mm of capture-point error at 400 mm/s, against a 24.5 mm support
    margin. Here it is on the arm, where the number is bigger because the
    forearm is most of the moving mass: the two channels are not within an
    order of magnitude of each other.
    """

    built = _built()
    model, _xml = _with_sensors(
        built,
        [
            {
                "type": mujoco.mjtSensor.mjSENS_FRAMELINVEL,
                "objtype": XBODY,
                "objname": "upper",
            },
            {
                "type": mujoco.mjtSensor.mjSENS_SUBTREELINVEL,
                "objtype": BODY,
                "objname": "upper",
            },
        ],
    )
    data = _at_keyframe(model)
    # At rest they agree, and that agreement is worth nothing.
    assert _channel(model, data, 0) == _channel(model, data, 1) == [0.0, 0.0, 0.0]

    for _ in range(200):
        mujoco.mj_step(model, data)
    mujoco.mj_forward(model, data)

    frame = _channel(model, data, 0)
    subtree = _channel(model, data, 1)
    assert max(abs(value) for value in subtree) > 0.1, "the arm did not move"
    # Read off the field MuJoCo filled, so the sensor is checked against the
    # quantity rather than against a second copy of the sensor.
    mujoco.mj_subtreeVel(model, data)
    upper_id = mujoco.mj_name2id(model, BODY, "upper")
    assert subtree == pytest.approx(
        data.subtree_linvel[upper_id].tolist(), abs=1.0e-12
    )

    difference = max(abs(a - b) for a, b in zip(frame, subtree))
    scale = max(abs(value) for value in subtree)
    assert difference / scale > 0.5, (frame, subtree)


# ---------------------------------------------------------------------------
# 4. body vs xbody -- the finding that would have been silently wrong.
# ---------------------------------------------------------------------------


def test_a_body_frame_sensor_reads_the_inertial_frame_and_xbody_does_not() -> None:
    """``objtype="body"`` is the *inertial* frame. This is a trap, measured.

    MuJoCo's frame sensors accept two object types that a reader would take
    for the same thing. ``body`` resolves to ``xipos``/``ximat`` -- the
    frame the principal axes of inertia define -- and ``xbody`` to
    ``xpos``/``xquat``, the frame the assembly solver placed and the one
    ``_verify_exported_pose`` already compares against.

    On a link whose inertia tensor is diagonal in a turned frame the two
    orientations differ by that turn: here by 90 degrees, which is not a
    rounding error and not a number anybody would question in a reward.
    """

    offset = fx.box_inertial(300.0, 40.0, 20.0, centre=(60.0, 0.0, 0.0))
    built = _built(inertials={"upper": offset})
    model, _xml = _with_sensors(
        built,
        [
            {"type": mujoco.mjtSensor.mjSENS_FRAMEPOS, "objtype": BODY, "objname": "upper"},
            {"type": mujoco.mjtSensor.mjSENS_FRAMEPOS, "objtype": XBODY, "objname": "upper"},
            {"type": mujoco.mjtSensor.mjSENS_FRAMEQUAT, "objtype": BODY, "objname": "upper"},
            {"type": mujoco.mjtSensor.mjSENS_FRAMEQUAT, "objtype": XBODY, "objname": "upper"},
        ],
    )
    data = _at_keyframe(model)
    upper = mujoco.mj_name2id(model, BODY, "upper")

    # The centre of mass is 60 mm along the link, so the two positions are
    # 60 mm apart -- a discriminating fixture rather than one where the
    # inertial frame happens to sit on the body frame.
    assert model.body_ipos[upper].tolist() == pytest.approx(
        [0.06, 0.0, 0.0], abs=1.0e-12
    )
    assert _channel(model, data, 0) == pytest.approx(
        data.xipos[upper].tolist(), abs=1.0e-12
    )
    assert _channel(model, data, 1) == pytest.approx(
        data.xpos[upper].tolist(), abs=1.0e-12
    )
    # The magnitude rather than the worst component: the link is turned
    # 0.3 rad, so the 60 mm offset lands 57.3 mm along world x and the rest
    # in z -- a max-component comparison would be measuring the pose.
    separation_mm = dyn.length_mm(
        sum(
            (a - b) ** 2
            for a, b in zip(_channel(model, data, 0), _channel(model, data, 1))
        )
        ** 0.5
    )
    assert separation_mm == pytest.approx(60.0, abs=1.0e-6)

    # And the orientations differ by the turn that takes the link's own
    # frame onto its principal axes of inertia -- a half turn on this box,
    # because MuJoCo orders the principal axes by eigenvalue and that order
    # is not the link's local x, y, z. 180 degrees is the whole finding: it
    # is not a rounding error, and a quaternion reward fed the wrong one of
    # these would be exactly reversed.
    assert _channel(model, data, 3) == pytest.approx(
        data.xquat[upper].tolist(), abs=1.0e-12
    )
    turn_degrees = math_degrees_between(
        _channel(model, data, 2), _channel(model, data, 3)
    )
    assert turn_degrees == pytest.approx(180.0, abs=1.0e-6)


def math_degrees_between(first, second) -> float:
    """The angle between two unit quaternions, in degrees."""

    import math

    matrices = [
        dyn.matrix_from_quaternion_wxyz(dyn.quaternion_normalised(value))
        for value in (first, second)
    ]
    return math.degrees(dyn.rotation_angle_between(matrices[0], matrices[1]))


# ---------------------------------------------------------------------------
# 5. ctrlrange: what a bounded action space actually is.
# ---------------------------------------------------------------------------


MOTOR = {
    "joint": "elbow",
    "motion_type": "angular",
    "kind": "motor",
    "control_nmm": "500",
    "torque_limit_nmm": 800.0,
}


def test_the_model_this_engine_builds_today_has_an_unbounded_action_space() -> None:
    """``ctrllimited`` is FALSE on every actuator M4 built, deliberately.

    M6's action bound is therefore new work rather than a read of something
    already there, and this test is what keeps that statement true: if a
    later change starts setting the flag somewhere else, the bound would be
    coming from two places.
    """

    built = _built(actuators=[MOTOR])
    model = built["model"]
    assert model.actuator_ctrllimited.tolist() == [False]
    assert model.actuator_ctrlrange.tolist() == [[0.0, 0.0]]
    # The effort limit is capped and the control is not, which is the
    # distinction M6's action bound rests on: forcerange bounds what the
    # motor may *produce*, ctrlrange bounds what a policy may *ask for*.
    assert model.actuator_forcelimited.tolist() == [True]
    assert model.actuator_forcerange.tolist() == [
        [pytest.approx(-0.8), pytest.approx(0.8)]
    ]


def test_ctrlrange_clamps_the_applied_effort_and_leaves_ctrl_alone() -> None:
    """A control outside the range is clamped by the *model*, not the caller.

    Measured, because both halves matter to M6. The clamp is real, so a
    policy that saturates cannot drive the mechanism past what the bundle
    advertises; and ``data.ctrl`` keeps the value it was handed, so a runner
    that echoes its own action is reporting what it asked for rather than
    what MuJoCo did with it.
    """

    built = _built(actuators=[MOTOR])
    spec = built["spec"].copy()
    for actuator in spec.actuators:
        actuator.ctrllimited = mujoco.mjtLimited.mjLIMITED_TRUE
        actuator.ctrlrange = [-0.2, 0.2]
    spec.add_key(name=dyn.MJCF_KEYFRAME_NAME, qpos=list(built["qpos_solved"]))
    spec.compile()
    model = mujoco.MjModel.from_xml_string(spec.to_xml())

    assert model.actuator_ctrllimited.tolist() == [True]
    assert model.actuator_ctrlrange.tolist() == [
        [pytest.approx(-0.2), pytest.approx(0.2)]
    ]
    data = _at_keyframe(model)
    data.ctrl[0] = 5.0
    mujoco.mj_step(model, data)
    assert data.ctrl.tolist() == [5.0]
    assert data.actuator_force.tolist() == [pytest.approx(0.2)]


# ---------------------------------------------------------------------------
# 6. The synthetic endpoint behind phase 2's refusal.
# ---------------------------------------------------------------------------


def test_a_one_sided_limit_reaches_jnt_range_as_a_hundred_turns() -> None:
    """The filled-in endpoint is a solver convenience, not a bound.

    ``_limit_range`` reports ``one_sided`` in its evidence already; what was
    never measured is *how wrong* the synthetic endpoint would be as an
    action range. It is ``_OPEN_ANGLE_MARGIN_RADIANS`` -- a hundred full
    turns -- so a policy handed that range would spend its whole action
    budget in a region the mechanism cannot reach. Phase 2 refuses it, and
    this is the number that refusal is stated against.
    """

    components, joints, _placements = fx.two_link_arm()
    for joint in joints:
        joint["angle_limits_degrees"] = (
            [None, 90.0] if joint["name"] == "elbow" else [-45.0, 45.0]
        )
    built = dyn.build_model(components, joints)

    assert built["model"].jnt_limited.tolist() == [True, True]
    records = {record["joint"]: record["limits"] for record in built["joint_records"]}
    assert records["shoulder"]["one_sided"] is False
    assert records["elbow"]["one_sided"] is True

    low, high = records["elbow"]["range"]
    assert high == pytest.approx(dyn.angle_radians(90.0))
    assert low == pytest.approx(high - dyn._OPEN_ANGLE_MARGIN_RADIANS)
    assert (high - low) / (2.0 * 3.141592653589793) == pytest.approx(100.0, abs=0.01)

    # And the two-sided fixture the M6 suites use carries no synthetic
    # endpoint at all, so a range derived from it is a range somebody drew.
    limited = dyn.build_model(*fx.two_link_arm(limits=True)[:2])
    for record in limited["joint_records"]:
        assert record["limits"]["one_sided"] is False


# ---------------------------------------------------------------------------
# 7. Randomisation: which field index, and what a write moves.
# ---------------------------------------------------------------------------


def test_a_mass_write_moves_the_subtree_mass_and_not_the_inertia() -> None:
    """Scaling ``body_mass`` alone leaves a body whose inertia is wrong.

    The finding that shapes the surface. MuJoCo derives ``body_subtreemass``
    from ``body_mass`` at ``mj_setConst``, so a mass draw does propagate --
    but ``body_inertia`` is an independent array and nothing rescales it. A
    body twice as heavy with its original inertia tensor is not a heavier
    part; it is a part whose density depends on which equation you ask.

    So an M6 mass randomisation scales **both**, by one draw, which is
    exactly what changing the density of a fixed shape means -- and is how
    ``mass_kg`` and ``inertia_kg_m2`` derived the two numbers in the first
    place, each linear in the density.
    """

    built = _built()
    model = built["model"]
    fore = mujoco.mj_name2id(model, BODY, "fore")
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    mujoco.mj_forward(model, data)

    mass_before = list(model.body_mass.tolist())
    inertia_before = [list(row) for row in model.body_inertia.tolist()]
    subtree_before = list(model.body_subtreemass.tolist())

    model.body_mass[fore] *= 2.0
    mujoco.mj_setConst(model, data)

    # The mass moved, its subtree total moved with it, and the inertia did
    # not -- three separate assertions because each is a separate claim.
    assert model.body_mass[fore] == pytest.approx(2.0 * mass_before[fore])
    assert model.body_subtreemass.tolist()[fore] == pytest.approx(
        2.0 * subtree_before[fore]
    )
    assert model.body_subtreemass.tolist()[0] == pytest.approx(
        subtree_before[0] + mass_before[fore]
    )
    assert [list(row) for row in model.body_inertia.tolist()] == inertia_before

    # Scaling the inertia by the same factor is the write that keeps the
    # body consistent, and it is one array away.
    model.body_inertia[fore] *= 2.0
    mujoco.mj_setConst(model, data)
    assert model.body_inertia[fore].tolist() == pytest.approx(
        [2.0 * value for value in inertia_before[fore]]
    )


def test_each_randomisation_target_resolves_to_one_field_index() -> None:
    """Where a mass and a damping live, and that a write is local.

    The bundle records resolved indices rather than names, so a runner with
    no Cadex on its path can apply a draw with one multiply. This pins the
    resolution: a body's mass is at its body id, a joint's damping at the
    dof address ``jnt_dofadr`` gives, and writing one moves nothing else.
    """

    built = _built(
        joint_dynamics=[
            {"joint": "elbow", "motion_type": "angular", "damping_nmms_per_deg": 12.0}
        ]
    )
    model = built["model"]

    fore = mujoco.mj_name2id(model, BODY, "fore")
    assert fore == 3
    assert model.body_mass.tolist()[fore] == pytest.approx(0.77715)

    elbow = mujoco.mj_name2id(model, JOINT, "elbow")
    dof = int(model.jnt_dofadr[elbow])
    assert dof == 1
    damping_before = list(model.dof_damping.tolist())
    assert damping_before[dof] > 0.0

    model.dof_damping[dof] *= 0.5
    assert model.dof_damping.tolist() == [
        damping_before[0],
        pytest.approx(0.5 * damping_before[1]),
    ]


# ---------------------------------------------------------------------------
# 8. The same episode, in two processes.
# ---------------------------------------------------------------------------


#: A runner that imports **only** ``mujoco``: reset to the solved keyframe,
#: apply a fixed control sequence, report the trajectory. Written to disk by
#: the test and run under ``-P`` with a scrubbed ``PYTHONPATH``, the way
#: ``dynamics_mjcf_digest`` proves its own negative. Phase 5 replaces this
#: with the real episode runner; phase 0's job is only to establish that a
#: control sequence plus a keyframe is reproducible across processes at all.
STOCK_EPISODE = '''
import json, sys
import mujoco
try:
    import CadexDynamics  # noqa: F401
except Exception:
    cadex_importable = False
else:
    cadex_importable = True
model = mujoco.MjModel.from_xml_path(sys.argv[1])
data = mujoco.MjData(model)
key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "solved")
mujoco.mj_resetDataKeyframe(model, data, key)
trajectory = []
for step in range(40):
    data.ctrl[0] = 0.4 * (1.0 if step % 7 < 4 else -1.0)
    for _ in range(10):
        mujoco.mj_step(model, data)
    trajectory.append([repr(float(v)) for v in data.qpos.tolist()])
    trajectory.append([repr(float(v)) for v in data.sensordata.tolist()])
print(json.dumps({"cadex_importable": cadex_importable,
                  "mujoco_version": str(getattr(mujoco, "__version__", "unknown")),
                  "trajectory": trajectory}, sort_keys=True))
'''


def test_an_episode_is_reproducible_across_processes(tmp_path: Path) -> None:
    """Two fresh interpreters, one control sequence, the same trajectory.

    The ``dynamics_trace_digest`` idiom applied to an *episode* rather than
    to a trace: reset to the keyframe, drive a fixed control sequence, and
    compare what came back as text. Floats travel as ``repr``, which
    round-trips exactly, so a difference between two runs is a number and
    never a formatting artefact.

    It also asserts the negative -- neither process could import Cadex --
    because an episode that agreed only because both runs went through the
    same in-process module would prove nothing about M6's exit criterion.
    """

    built = _built(actuators=[MOTOR])
    model, xml = _with_sensors(built, FOUR_SENSORS)
    path = tmp_path / "arm.xml"
    path.write_text(xml, encoding="utf-8")
    script = tmp_path / "episode.py"
    script.write_text(STOCK_EPISODE, encoding="utf-8")

    environment = {
        key: value
        for key, value in __import__("os").environ.items()
        if key != "PYTHONPATH"
    }
    runs = []
    for _ in range(2):
        completed = subprocess.run(
            [sys.executable, "-P", str(script), str(path)],
            capture_output=True,
            text=True,
            env=environment,
            check=True,
        )
        runs.append(json.loads(completed.stdout))

    for run in runs:
        assert run["cadex_importable"] is False
        assert run["mujoco_version"] == str(mujoco.__version__)
    assert runs[0]["trajectory"] == runs[1]["trajectory"]
    # And the mechanism moved under the control sequence, so the agreement
    # is between two episodes rather than between two models that sat still.
    first = [float(value) for value in runs[0]["trajectory"][0]]
    last = [float(value) for value in runs[0]["trajectory"][-2]]
    assert max(abs(a - b) for a, b in zip(first, last)) > 0.01
