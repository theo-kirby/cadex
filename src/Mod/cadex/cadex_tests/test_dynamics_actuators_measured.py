# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""What MuJoCo's actuators actually do (docs/MUJOCO.md M4, phase 0).

Nothing here imports the translator. Every test builds an ``MjSpec`` by
hand, compiles it, and records what mujoco 3.10.0 does -- before there is a
feature to blame it on. That ordering is the one M2 and M3 each found paid
best: ``balanceinertia`` invents inertia, ``compiler.degree`` defaults to
degrees, ``mjDSBL_ISLAND`` is a *disable* bit, and every one of those was a
name promising something other than what it did.

Five questions, and four of the answers moved a decision:

* **What is a ``position`` actuator, exactly?** It is a PD controller
  written into ``gainprm``/``biasprm``, evaluated in C every step. That is
  what makes M4's correction -- a whitelisted formula of ``time`` instead of
  a Python control callback -- cost nothing: the loop that has to close
  every step already closes in the solver.
* **Does ``ctrlrange`` imply ``ctrllimited``?** Only because
  ``compiler.autolimits`` defaults *on*. With it off, a ``forcerange``
  without a ``forcelimited`` is a compile error rather than an inference.
* **Is ``ctrl`` in joint units?** Only at ``gear = 1``. At gear 2 a
  setpoint of 0.5 rad holds the joint at 0.25. So M4 pins the gear and
  refuses anything else, and the surface has exactly one way to say a ratio.
* **How stiff may a position gain be at a given solver step?** The boundary
  is ``ω·h = 2`` for an undamped actuator -- the textbook explicit limit,
  measured to three digits and invariant across a 400x range of inertia.
  Damping buys headroom because ``implicitfast`` integrates it implicitly,
  which is half of why M3 chose that integrator; a *velocity* actuator,
  which is all damping, never blows up at all.
* **Does an actuator that is doing nothing change the answer?** A ``motor``
  at zero control is bitwise identical to no actuator. A ``position``
  actuator at zero control is not, and must never be described as one: it is
  a servo commanded to zero.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn

mujoco = pytest.importorskip("mujoco")

#: The arm every measurement below is made on: a 300 x 40 x 20 mm aluminium
#: bar hinged at one end and horizontal, so gravity has maximum leverage on
#: it. Its inertia about the hinge is 0.0194616 kg·m², which is the number
#: the stability boundary is expressed against.
_ARM_MASS_KG = 2700.0 * 0.3 * 0.04 * 0.02
_ARM_INERTIA_KG_M2 = (
    _ARM_MASS_KG * (0.3**2 + 0.02**2) / 12.0 + _ARM_MASS_KG * 0.15**2
)


def _arm_spec(
    *, timestep: float = dyn.DEFAULT_TIME_STEP_S, damping: float = 0.0,
    armature: float = 0.0, mass_scale: float = 1.0,
):
    """One hinged bar, built with the same options the translator sets."""

    spec = mujoco.MjSpec()
    spec.compiler.degree = False
    spec.compiler.balanceinertia = False
    spec.compiler.boundinertia = 0.0
    spec.compiler.boundmass = 0.0
    spec.compiler.inertiafromgeom = mujoco.mjtInertiaFromGeom.mjINERTIAFROMGEOM_FALSE
    spec.option.gravity = list(dyn.DEFAULT_GRAVITY_M_S2)
    spec.option.timestep = float(timestep)
    spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    spec.option.disableflags = int(mujoco.mjtDisableBit.mjDSBL_ISLAND)
    body = spec.worldbody.add_body(name="arm", pos=[0.0, 0.0, 0.0])
    mass = _ARM_MASS_KG * mass_scale
    body.explicitinertial = True
    body.mass = mass
    body.ipos = [0.15, 0.0, 0.0]
    body.fullinertia = [
        mass * (0.04**2 + 0.02**2) / 12.0,
        mass * (0.3**2 + 0.02**2) / 12.0,
        mass * (0.3**2 + 0.04**2) / 12.0,
        0.0, 0.0, 0.0,
    ]
    joint = body.add_joint(
        name="hinge", type=mujoco.mjtJoint.mjJNT_HINGE, pos=[0, 0, 0], axis=[0, 1, 0]
    )
    # Measured, and a surprise worth writing down: ``damping`` and
    # ``stiffness`` are three-vectors on an MjsJoint (one per dof, for a
    # ball joint's three), while ``armature`` and ``frictionloss`` are
    # scalars. Assigning a float to ``damping`` is a TypeError, which is at
    # least the loud kind of wrong.
    joint.damping = [float(damping), 0.0, 0.0]
    joint.armature = float(armature)
    return spec


def _drive(spec, kind: str, *, kp: float = 0.0, kv: float = 0.0):
    actuator = spec.add_actuator()
    actuator.name = "drive"
    actuator.target = "hinge"
    actuator.trntype = mujoco.mjtTrn.mjTRN_JOINT
    if kind == "motor":
        actuator.set_to_motor()
    elif kind == "position":
        actuator.set_to_position(kp, kv=kv)
    else:
        actuator.set_to_velocity(kv)
    return actuator


def _effective_inertia(model) -> float:
    """The joint's own diagonal of the mass matrix, armature included."""

    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    import numpy

    dense = numpy.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, dense)
    return float(dense[0, 0])


# ---------------------------------------------------------------------------
# 1. The three kinds, as gain and bias parameters.
# ---------------------------------------------------------------------------


def test_a_motor_is_a_pass_through_and_nothing_else() -> None:
    """``force = gain · ctrl`` with gain 1 and no bias: ctrl *is* the torque."""

    spec = _arm_spec()
    _drive(spec, "motor")
    model = spec.compile()
    assert int(model.actuator_gaintype[0]) == int(mujoco.mjtGain.mjGAIN_FIXED)
    assert int(model.actuator_biastype[0]) == int(mujoco.mjtBias.mjBIAS_NONE)
    assert float(model.actuator_gainprm[0][0]) == 1.0
    assert list(model.actuator_biasprm[0][:3]) == [0.0, 0.0, 0.0]


def test_a_position_actuator_is_the_pd_loop_and_it_lives_in_c() -> None:
    """``gainprm = [kp]``, ``biasprm = [0, −kp, −kv]``: force = kp(c − q) − kv·v.

    This is the measurement that made M4's first correction a decision
    rather than a preference. The plan it came from said "a control
    callback runs in the worker" -- a Python callable evaluated every solver
    step, which would put unbounded arbitrary code inside the determinism
    gate. It is unnecessary: the closed loop is three numbers in a compiled
    model, and what the script actually has to supply is a *setpoint*.
    """

    spec = _arm_spec()
    _drive(spec, "position", kp=4000.0, kv=120.0)
    model = spec.compile()
    assert int(model.actuator_gaintype[0]) == int(mujoco.mjtGain.mjGAIN_FIXED)
    assert int(model.actuator_biastype[0]) == int(mujoco.mjtBias.mjBIAS_AFFINE)
    assert float(model.actuator_gainprm[0][0]) == pytest.approx(4000.0)
    assert list(model.actuator_biasprm[0][:3]) == pytest.approx([0.0, -4000.0, -120.0])


def test_a_velocity_actuator_biases_on_rate_alone() -> None:
    """``gainprm = [kv]``, ``biasprm = [0, 0, −kv]``: force = kv(c − v)."""

    spec = _arm_spec()
    _drive(spec, "velocity", kv=120.0)
    model = spec.compile()
    assert float(model.actuator_gainprm[0][0]) == pytest.approx(120.0)
    assert list(model.actuator_biasprm[0][:3]) == pytest.approx([0.0, 0.0, -120.0])


# ---------------------------------------------------------------------------
# 2. autolimits, which is a default doing load-bearing work.
# ---------------------------------------------------------------------------


def test_autolimits_defaults_on_so_a_range_silently_becomes_a_limit() -> None:
    spec = _arm_spec()
    assert bool(mujoco.MjSpec().compiler.autolimits) is True
    actuator = _drive(spec, "position", kp=4000.0, kv=120.0)
    actuator.ctrlrange = [-1.0, 1.0]
    actuator.forcerange = [-8.0, 8.0]
    model = spec.compile()
    assert bool(model.actuator_ctrllimited[0]) is True
    assert bool(model.actuator_forcelimited[0]) is True


def test_with_autolimits_off_a_range_without_a_flag_is_a_compile_error() -> None:
    """Which is the behaviour worth having: loud, and at build time.

    The translator sets ``autolimits = False`` and states both flags on
    every actuator, so a limit that exists is a limit somebody wrote down.
    An inferred one is the same class of thing as an inferred density.
    """

    spec = _arm_spec()
    spec.compiler.autolimits = False
    actuator = _drive(spec, "position", kp=4000.0, kv=120.0)
    actuator.forcerange = [-8.0, 8.0]
    with pytest.raises(Exception) as excinfo:
        spec.compile()
    assert "forcelimited" in str(excinfo.value)


def test_stating_both_flags_explicitly_compiles_with_autolimits_off() -> None:
    spec = _arm_spec()
    spec.compiler.autolimits = False
    actuator = _drive(spec, "position", kp=4000.0, kv=120.0)
    actuator.forcerange = [-8.0, 8.0]
    actuator.ctrllimited = mujoco.mjtLimited.mjLIMITED_FALSE
    actuator.forcelimited = mujoco.mjtLimited.mjLIMITED_TRUE
    model = spec.compile()
    assert bool(model.actuator_ctrllimited[0]) is False
    assert bool(model.actuator_forcelimited[0]) is True


def test_a_force_limit_really_clamps_and_the_arm_sags() -> None:
    """The reason the evidence reports a peak actuator force.

    Half a newton-metre cannot hold this arm at 30°, so it holds it at
    15.9° instead -- a mechanism that looks like it is working and is
    simply not strong enough. "The arm sagged" is not actionable; "it
    saturated at 0.5 N·m" is.
    """

    spec = _arm_spec()
    spec.compiler.autolimits = False
    actuator = _drive(spec, "position", kp=4000.0, kv=17.6)
    actuator.forcerange = [-0.5, 0.5]
    actuator.ctrllimited = mujoco.mjtLimited.mjLIMITED_FALSE
    actuator.forcelimited = mujoco.mjtLimited.mjLIMITED_TRUE
    model = spec.compile()
    data = mujoco.MjData(model)
    data.ctrl[0] = math.radians(30.0)
    peak = 0.0
    for _step in range(2000):
        mujoco.mj_step(model, data)
        peak = max(peak, abs(float(data.actuator_force[0])))
    assert peak == pytest.approx(0.5, abs=1.0e-9)
    assert 14.0 < math.degrees(float(data.qpos[0])) < 18.0


# ---------------------------------------------------------------------------
# 3. gear, which is why the surface has no ratio argument.
# ---------------------------------------------------------------------------


def test_gear_defaults_to_one_and_ctrl_is_then_in_joint_units() -> None:
    spec = _arm_spec(damping=5.0)
    _drive(spec, "position", kp=4000.0, kv=120.0)
    model = spec.compile()
    assert list(model.actuator_gear[0]) == [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    data = mujoco.MjData(model)
    data.ctrl[0] = 0.5
    for _step in range(6000):
        mujoco.mj_step(model, data)
    assert float(data.qpos[0]) == pytest.approx(0.5, abs=1.0e-3)


def test_a_gear_other_than_one_silently_rescales_the_setpoint() -> None:
    """Measured, and the reason M4 pins the gear at 1 and refuses the rest.

    At gear 2 a commanded 0.5 holds the joint at 0.25: ``ctrl`` addresses
    the *actuator's* coordinate, which is ``gear · q``. A surface with both
    a setpoint and a ratio would have two ways to say the same thing and
    one of them would be wrong in a script that runs.
    """

    spec = _arm_spec(damping=5.0)
    actuator = _drive(spec, "position", kp=4000.0, kv=120.0)
    actuator.gear = [2.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    model = spec.compile()
    data = mujoco.MjData(model)
    data.ctrl[0] = 0.5
    for _step in range(6000):
        mujoco.mj_step(model, data)
    assert float(data.qpos[0]) == pytest.approx(0.25, abs=1.0e-3)


# ---------------------------------------------------------------------------
# 4. The stability ceiling, which becomes a refusal.
# ---------------------------------------------------------------------------


def _diverges(kp: float, kv: float, step: float, *, mass_scale: float = 1.0) -> bool:
    spec = _arm_spec(timestep=step, mass_scale=mass_scale)
    _drive(spec, "position", kp=kp, kv=kv)
    model = spec.compile()
    data = mujoco.MjData(model)
    data.ctrl[0] = math.radians(30.0)
    for _index in range(int(2.0 / step)):
        mujoco.mj_step(model, data)
        angle = float(data.qpos[0])
        if not math.isfinite(angle) or abs(angle) > 10.0:
            return True
    return False


def _boundary(step: float, damping_ratio: float, *, mass_scale: float = 1.0) -> float:
    """The ``ω·h`` at the first gain that blows up, by decade-tenth search."""

    inertia = _ARM_INERTIA_KG_M2 * mass_scale
    exponent = 1.0
    while exponent < 10.0:
        gain = 10.0**exponent
        if _diverges(
            gain,
            damping_ratio * 2.0 * math.sqrt(gain * inertia),
            step,
            mass_scale=mass_scale,
        ):
            spec = _arm_spec(timestep=step, mass_scale=mass_scale)
            _drive(spec, "position", kp=gain, kv=0.0)
            measured = _effective_inertia(spec.compile())
            return step * math.sqrt(gain / measured)
        exponent += 0.05
    raise AssertionError("no divergence found below a gain of 1e10")


def test_an_undamped_position_gain_diverges_at_exactly_omega_h_of_two() -> None:
    """The textbook explicit-integration limit, measured rather than cited.

    ``implicitfast`` integrates *damping* implicitly, not stiffness, so a
    position actuator's spring term is stepped explicitly and inherits the
    classical ``ω·h < 2``. At the default step that is a gain of 19 950 on
    this arm -- and the number is the same at four different steps, which is
    what makes it a property of the integrator rather than a coincidence.
    """

    for step in (0.004, 0.002, 0.001, 0.0005):
        assert _boundary(step, 0.0) == pytest.approx(2.02, abs=0.02)


def test_the_boundary_is_omega_h_and_not_a_gain(
) -> None:
    """A 400x range of inertia, one number: so the refusal can be dimensionless.

    A refusal stated as a maximum *gain* would be wrong for every mechanism
    but the one it was measured on. Stated as ``ω·h`` it is right for all of
    them, and the translator already knows the inertia -- it is the joint's
    own diagonal of the compiled mass matrix.
    """

    for scale in (0.05, 1.0, 20.0):
        assert _boundary(0.002, 1.0, mass_scale=scale) == pytest.approx(5.09, abs=0.05)


def test_damping_buys_headroom_which_is_why_the_limit_ignores_it() -> None:
    """ζ = 0 → 2.0, ζ = 0.5 → 3.4, ζ = 1 → 5.1: the ceiling depends on feel.

    Which is exactly why ``MAXIMUM_ACTUATOR_OMEGA_STEP`` is the *undamped*
    boundary. A model whose stability rests on a damping number the author
    picked for how the arm looks is a model that breaks when somebody
    smooths the motion, and nothing would say why.
    """

    assert _boundary(0.002, 0.0) == pytest.approx(2.02, abs=0.05)
    assert _boundary(0.002, 0.5) == pytest.approx(3.40, abs=0.05)
    assert _boundary(0.002, 1.0) == pytest.approx(5.09, abs=0.05)


def test_a_velocity_actuator_never_diverges_because_it_is_all_damping() -> None:
    """The other half of M3's integrator choice, paying out here.

    ``implicitfast`` was chosen because it conserves a tumbling part's
    energy; this is the second dividend. A pure damper is integrated
    implicitly and is unconditionally stable under it, so a velocity gain
    a thousand times past where a position gain would explode tracks its
    setpoint to eight digits instead.
    """

    for step in (0.002, 0.0005):
        spec = _arm_spec(timestep=step)
        _drive(spec, "velocity", kv=1.0e8)
        model = spec.compile()
        data = mujoco.MjData(model)
        data.ctrl[0] = 1.0
        for _index in range(int(0.5 / step)):
            mujoco.mj_step(model, data)
        assert math.isfinite(float(data.qpos[0]))
        assert abs(float(data.qvel[0]) - 1.0) < 1.0e-6


def test_a_damping_gain_does_not_explode_it_freezes_and_says_nothing() -> None:
    """The failure mode a velocity actuator does have, measured (M4 phase 0).

    Past ``kv / M ≈ 1.2e10`` per second the solver's own regularisation
    wins and the joint simply stops: commanded 1 rad/s, delivered 1e-9,
    finite the whole way and warned about by nothing. That is silence
    rather than divergence, which is the worse of the two, so it gets its
    own ceiling -- and the ceiling is a *rate*, invariant across four
    decades of inertia and both solver steps, not a gain.
    """

    measured = []
    for scale in (0.01, 1.0, 100.0):
        for step in (0.002, 0.0005):
            exponent = 6.0
            frozen = None
            while exponent < 14.0 and frozen is None:
                gain = 10.0**exponent
                spec = _arm_spec(timestep=step, mass_scale=scale)
                _drive(spec, "velocity", kv=gain)
                model = spec.compile()
                data = mujoco.MjData(model)
                mujoco.mj_forward(model, data)
                import numpy

                dense = numpy.zeros((model.nv, model.nv))
                mujoco.mj_fullM(model, data, dense)
                data.ctrl[0] = 1.0
                for _index in range(200):
                    mujoco.mj_step(model, data)
                if float(data.qvel[0]) < 0.9:
                    frozen = gain / float(dense[0, 0])
                exponent += 0.125
            assert frozen is not None
            measured.append(frozen)
    for rate in measured:
        assert rate == pytest.approx(1.218e10, rel=0.02)


def test_joint_damping_freezes_at_the_same_order_and_so_shares_the_ceiling() -> None:
    """It is the dof's total damping that does it, not the actuator's share.

    A joint damping of 5.6e8 N·m·s/rad on this arm -- ``c / M`` of 2.9e10 --
    swallows a torque that should have driven it at half a radian per
    second and leaves it at 1.7e-9. Same mechanism, same order, so one
    ceiling covers both rather than two that could drift apart.
    """

    exponent = 4.0
    while exponent < 14.0:
        damping = 10.0**exponent
        spec = _arm_spec(damping=damping)
        _drive(spec, "motor")
        model = spec.compile()
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        import numpy

        dense = numpy.zeros((model.nv, model.nv))
        mujoco.mj_fullM(model, data, dense)
        data.ctrl[0] = damping * 0.5
        for _index in range(400):
            mujoco.mj_step(model, data)
        if abs(float(data.qvel[0]) - 0.5) > 0.05:
            assert damping / float(dense[0, 0]) == pytest.approx(2.9e10, rel=0.05)
            return
        exponent += 0.25
    raise AssertionError("joint damping never froze the joint")


def test_the_translators_two_ceilings_are_the_measured_ones() -> None:
    """The constants, checked against the measurements they came from.

    Both carry margin in the direction that refuses rather than delivers:
    the stiffness limit is the *undamped* boundary and the damping limit is
    a decade below the frozen one.
    """

    assert dyn.MAXIMUM_ACTUATOR_OMEGA_STEP == 2.0
    assert dyn.MAXIMUM_DAMPING_RATE_PER_S == 1.0e9
    assert dyn.MAXIMUM_DAMPING_RATE_PER_S < 1.218e10


# ---------------------------------------------------------------------------
# 5. Two interactions, both of which could have made the digest story worse.
# ---------------------------------------------------------------------------


def _swing(actuator: str | None, control: float = 0.0) -> list[float]:
    spec = _arm_spec()
    if actuator == "motor":
        _drive(spec, "motor")
    elif actuator == "position":
        _drive(spec, "position", kp=4000.0, kv=120.0)
    model = spec.compile()
    data = mujoco.MjData(model)
    if actuator is not None:
        data.ctrl[0] = control
    trail = []
    for _step in range(500):
        mujoco.mj_step(model, data)
        trail.append(float(data.qpos[0]))
    return trail


def test_a_motor_at_zero_control_is_bitwise_the_unactuated_run() -> None:
    """Adding an actuator that does nothing must change nothing at all.

    Not "to within a tolerance" -- identically, because these traces are
    compared as bytes across processes. If a zero motor moved the answer,
    the digest gate would have a prior problem worth finding here rather
    than after an arm is holding position on top of it.
    """

    assert _swing(None) == _swing("motor", 0.0)


def test_a_position_actuator_at_zero_control_is_not_the_unactuated_run() -> None:
    """The converse, stated so the first test cannot be misread.

    A ``position`` actuator commanded to zero is a servo holding the joint
    at zero, which for an arm released horizontally is most of a radian of
    difference. "No actuator" and "an actuator asking for nothing" are the
    same sentence in English and opposite models.
    """

    bare = _swing(None)
    servoed = _swing("position", 0.0)
    assert max(abs(a - b) for a, b in zip(bare, servoed, strict=True)) > 1.0


def test_an_actuator_does_not_break_an_equality_joint_coupling() -> None:
    """Driving one side of a screw pair: the coupling still holds to 0.06 mm.

    M2 stiffened every equality this module writes because a heavy nut
    overwhelmed a screw coupling entirely at MuJoCo's defaults. An actuator
    is a new way to push on exactly that constraint, so it is measured
    against the same tolerance rather than assumed to inherit it.
    """

    for torque, tolerance_mm in ((0.01, 0.02), (0.1, 0.08)):
        spec = mujoco.MjSpec()
        spec.compiler.degree = False
        spec.compiler.inertiafromgeom = (
            mujoco.mjtInertiaFromGeom.mjINERTIAFROMGEOM_FALSE
        )
        spec.option.gravity = [0.0, 0.0, 0.0]
        spec.option.timestep = 0.001
        spec.option.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST
        shaft = spec.worldbody.add_body(name="shaft")
        shaft.explicitinertial = True
        shaft.mass = 0.5
        shaft.ipos = [0.0, 0.0, 0.0]
        shaft.fullinertia = [1.0e-4, 1.0e-4, 2.0e-4, 0.0, 0.0, 0.0]
        shaft.add_joint(name="spin", type=mujoco.mjtJoint.mjJNT_HINGE, axis=[0, 0, 1])
        nut = spec.worldbody.add_body(name="nut")
        nut.explicitinertial = True
        nut.mass = 2.0
        nut.ipos = [0.0, 0.0, 0.0]
        nut.fullinertia = [1.0e-3, 1.0e-3, 1.0e-3, 0.0, 0.0, 0.0]
        nut.add_joint(name="travel", type=mujoco.mjtJoint.mjJNT_SLIDE, axis=[0, 0, 1])
        pitch_m = dyn.length_m(4.0)
        equality = spec.add_equality()
        equality.name = "screw"
        equality.type = mujoco.mjtEq.mjEQ_JOINT
        equality.objtype = mujoco.mjtObj.mjOBJ_JOINT
        equality.name1, equality.name2 = "travel", "spin"
        row = [0.0] * 11
        row[1] = pitch_m / (2.0 * math.pi)
        equality.data = row
        equality.solref = [2.0 * 0.001, 1.0]
        equality.solimp = [0.99, 0.9999, 0.0001, 0.5, 2.0]
        actuator = spec.add_actuator()
        actuator.name = "drive"
        actuator.target = "spin"
        actuator.trntype = mujoco.mjtTrn.mjTRN_JOINT
        actuator.set_to_motor()
        model = spec.compile()
        data = mujoco.MjData(model)
        data.ctrl[0] = torque
        for _step in range(2000):
            mujoco.mj_step(model, data)
        expected = pitch_m * float(data.qpos[0]) / (2.0 * math.pi)
        residual_mm = dyn.length_mm(abs(float(data.qpos[1]) - expected))
        assert residual_mm < tolerance_mm
        assert abs(float(data.qpos[0])) > 1.0, "the drive must have actually turned it"
