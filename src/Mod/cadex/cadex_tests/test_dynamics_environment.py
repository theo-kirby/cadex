# SPDX-License-Identifier: LGPL-2.1-or-later

"""Gravity, the solver step, and the integrator (docs/MUJOCO.md M3, phase 3).

Three numbers that were constants and are now decisions.

**Gravity** was a module constant, so every dynamics run in M2 happened on
Earth. A mechanism on the Moon and a mechanism with gravity switched off
are both things an author needs -- the second one especially, because it is
how you find out whether a joint's behaviour is the joint or the falling.
It is metres per second squared, not millimetres, which makes it the second
place after density where this surface is SI. That is deliberate: 9.81 is
how gravity is quoted and −9810 is how a typo hides.

**The solver step** was a constant for the reason M2 gave -- one number to
be wrong about while the translator was being proved. Phase 2 made it
authorable in practice by refusing a bouncing contact at the default step,
so phase 3 makes it authorable in fact. It is rounded so a whole number of
steps lands exactly on each frame, and both numbers are reported, because
"my step was refused for being too coarse" needs to say which step.

**The integrator was never a decision at all until now**, and it is the one
that moves the most numbers. MuJoCo's default is Euler and the measurement
that ruled it out is a freely tumbling asymmetric part -- the shape of
anything that falls over. Over twenty seconds at the default step Euler
*gains* 51% of its kinetic energy: a part that spins faster the longer it
spins, every frame of which looks like physics. ``implicitfast`` conserves
angular momentum and energy to the printed precision and reproduces RK4's
trajectory through three Dzhanibekov flips to three decimals, at one force
evaluation per step rather than four. MuJoCo's full ``implicit`` is worse
than either: it loses 29%.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
from cadex_assembly_api import AssemblyDomainAPI
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS

mujoco = pytest.importorskip("mujoco")

#: A freely tumbling asymmetric plate, in no gravity. The discriminating
#: case: a settled box stack integrates identically under all four of
#: MuJoCo's integrators (measured, to 4e-12), and says nothing.
TUMBLER = """
<mujoco>
  <option timestep="{step}" integrator="{integrator}" gravity="0 0 0"/>
  <worldbody><body name="plate"><freejoint/>
    <geom type="box" size="0.30 0.10 0.02" density="1000"/></body></worldbody>
</mujoco>
"""


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _source(name: str) -> dict[str, str]:
    return {"document_uid": "doc", "object_name": name}


def _tumble(integrator: str, step: float, seconds: float = 20.0):
    """Kinetic energy and angular momentum, before and after a long tumble."""

    model = mujoco.MjModel.from_xml_string(
        TUMBLER.format(step=step, integrator=integrator)
    )
    data = mujoco.MjData(model)
    data.qvel[3:6] = (0.2, 8.0, 0.05)
    mujoco.mj_forward(model, data)
    inertia = model.body_inertia[1]

    def measures():
        rates = data.qvel[3:6]
        energy = 0.5 * sum(inertia[axis] * rates[axis] ** 2 for axis in range(3))
        momentum = math.sqrt(
            sum((inertia[axis] * rates[axis]) ** 2 for axis in range(3))
        )
        return energy, momentum

    before = measures()
    for _step in range(int(seconds / step)):
        mujoco.mj_step(model, data)
    return before, measures()


# ---------------------------------------------------------------------------
# The integrator.
# ---------------------------------------------------------------------------


def test_euler_manufactures_energy_on_a_tumbling_part() -> None:
    """The measurement that made the integrator a decision.

    Half again as much kinetic energy after twenty seconds, out of nothing,
    on a body that is only spinning. This is why the choice is written down
    rather than inherited.
    """

    (energy, _momentum), (after, _) = _tumble("Euler", dyn.DEFAULT_TIME_STEP_S)
    assert (after - energy) / energy > 0.4


def test_implicitfast_conserves_what_a_free_tumble_must_conserve() -> None:
    (energy, momentum), (after_energy, after_momentum) = _tumble(
        "implicitfast", dyn.DEFAULT_TIME_STEP_S
    )
    assert after_energy == pytest.approx(energy, rel=1.0e-6)
    assert after_momentum == pytest.approx(momentum, rel=1.0e-6)


def test_implicitfast_is_not_conserving_by_refusing_to_tumble() -> None:
    """The obvious way to conserve energy is to do nothing, so: check.

    The plate must actually flip -- the Dzhanibekov effect, ``wy`` swinging
    from +8 to −7.3 and back -- and it must flip the way RK4 says it does,
    at four times the cost per step.
    """

    def rates(integrator: str) -> list[float]:
        model = mujoco.MjModel.from_xml_string(
            TUMBLER.format(step=0.0002, integrator=integrator)
        )
        data = mujoco.MjData(model)
        data.qvel[3:6] = (0.2, 8.0, 0.05)
        mujoco.mj_forward(model, data)
        samples = []
        for index in range(int(12.0 / 0.0002)):
            mujoco.mj_step(model, data)
            if index % 5000 == 0:
                samples.append(float(data.qvel[4]))
        return samples

    fast = rates("implicitfast")
    reference = rates("RK4")
    assert min(fast) < -7.0 and max(fast) > 7.0, "the plate must actually flip"
    assert fast == pytest.approx(reference, abs=1.0e-3)


def test_the_translator_compiles_with_implicitfast_and_says_so() -> None:
    built = dyn.build_model(*fx.pendulum()[:2])
    assert int(built["model"].opt.integrator) == int(
        mujoco.mjtIntegrator.mjINT_IMPLICITFAST
    )
    run = dyn.simulate(
        *fx.pendulum()[:2], start_time_s=0.0, end_time_s=0.1, frames_per_second=30
    )
    assert run["evidence"]["solver_integrator"] == "implicitfast"


def test_an_integrator_that_changed_under_us_is_refused() -> None:
    """Asserted on the compiled model, where a MuJoCo default change lands."""

    built = dyn.build_model(*fx.pendulum()[:2])
    model = built["model"]
    model.opt.integrator = int(mujoco.mjtIntegrator.mjINT_EULER)
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn._verify_solver_flags(mujoco, model)
    assert excinfo.value.reason == "solver_flags_changed"
    assert "51%" in excinfo.value.correction


# ---------------------------------------------------------------------------
# Gravity.
# ---------------------------------------------------------------------------


def test_gravity_defaults_to_earth_and_takes_a_vector() -> None:
    assert dyn.DEFAULT_GRAVITY_M_S2 == (0.0, 0.0, -9.81)
    built = dyn.build_model(*fx.pendulum()[:2])
    assert list(built["model"].opt.gravity) == pytest.approx([0.0, 0.0, -9.81])
    moon = dyn.build_model(*fx.pendulum()[:2], gravity_m_s2=(0.0, 0.0, -1.62))
    assert list(moon["model"].opt.gravity) == pytest.approx([0.0, 0.0, -1.62])
    assert moon["gravity_m_s2"] == [0.0, 0.0, -1.62]


def test_a_free_body_falls_by_half_g_t_squared_in_whatever_gravity_it_is_given() -> None:
    """Gravity as a measured drop rather than a number in a dict.

    A part with no joints gets a free joint and falls, so where it is after
    half a second is arithmetic: ½gt². Earth and the Moon differ by a factor
    of six and the trace has to show it.
    """

    def drop(gravity: float) -> float:
        # A grounded component is required -- a model with none has no
        # reference frame -- so the stone falls beside a static anchor.
        components, joints, _placements = fx.build(
            [
                {"name": "anchor", "grounded": True, "size": (40.0, 40.0, 40.0)},
                {"name": "stone", "size": (40.0, 40.0, 40.0)},
            ],
            [],
        )
        run = dyn.simulate(
            components,
            joints,
            start_time_s=0.0,
            end_time_s=0.5,
            frames_per_second=60,
            gravity_m_s2=(0.0, 0.0, gravity),
        )
        first = run["frames"][1]["component_placements"]["stone"]["position_mm"][2]
        last = run["frames"][-1]["component_placements"]["stone"]["position_mm"][2]
        return first - last

    earth = drop(-9.81)
    moon = drop(-1.62)
    assert earth == pytest.approx(0.5 * 9.81 * 0.25 * 1000.0, rel=0.02)
    assert moon == pytest.approx(0.5 * 1.62 * 0.25 * 1000.0, rel=0.02)
    assert earth / moon == pytest.approx(9.81 / 1.62, rel=0.02)


def test_gravity_off_isolates_a_joint_from_the_falling() -> None:
    """The reason this is authorable at all, stated as a test."""

    components, joints, _placements = fx.pendulum()
    run = dyn.simulate(
        components,
        joints,
        start_time_s=0.0,
        end_time_s=1.0,
        frames_per_second=30,
        gravity_m_s2=(0.0, 0.0, 0.0),
    )
    start = run["frames"][1]["component_placements"]["arm"]["position_mm"]
    end = run["frames"][-1]["component_placements"]["arm"]["position_mm"]
    assert end == pytest.approx(start, abs=1.0e-9)
    # And with gravity it does move, so the test above is not vacuous.
    swinging = dyn.simulate(
        components, joints, start_time_s=0.0, end_time_s=1.0, frames_per_second=30
    )
    moved = swinging["frames"][-1]["component_placements"]["arm"]["position_mm"]
    assert max(abs(a - b) for a, b in zip(moved, start)) > 1.0


def test_gravity_in_millimetres_is_refused_by_its_own_magnitude() -> None:
    """−9810 is the typo this parameter's name exists to prevent."""

    with pytest.raises(ValueError, match="metres per second squared"):
        _make_dynamics(gravity_m_s2=[0.0, 0.0, -9810.0])
    assert _make_dynamics(gravity_m_s2=[0.0, 0.0, -1.62]) is not None


# ---------------------------------------------------------------------------
# The solver step.
# ---------------------------------------------------------------------------


def _make_dynamics(**arguments):
    api = _api()
    first = api.component(_source("solid0"), grounded=True)
    second = api.component(_source("solid1"))
    joint = api.joint(
        "revolute", api.connector(first, "origin"), api.connector(second, "origin")
    )
    assembly = api.assembly([first, second], [joint])
    return api.dynamics(
        assembly,
        [
            api.body(first, density_kg_m3=fx.STEEL),
            api.body(second, density_kg_m3=fx.STEEL),
        ],
        **arguments,
    )


def test_the_solver_step_defaults_to_the_module_constant() -> None:
    value = _make_dynamics()
    assert value.properties["solver_step_s"] is None
    assert value.properties["gravity_m_s2"] is None
    assert dyn.DEFAULT_TIME_STEP_S == 0.002


def test_an_authored_step_is_rounded_onto_the_frame_and_both_are_reported() -> None:
    """The rounding is not a detail: it is why two numbers are recorded."""

    run = dyn.simulate(
        *fx.pendulum()[:2],
        start_time_s=0.0,
        end_time_s=0.1,
        frames_per_second=60,
        time_step_s=0.003,
    )
    # 1/60 divided by 0.003 is 5.56, so six steps of 0.002778 s each.
    assert run["steps_per_sample"] == 6
    assert run["solver_step_s"] == pytest.approx(1.0 / 360.0)
    assert run["requested_step_s"] == 0.003
    assert run["steps_per_sample"] * run["solver_step_s"] == pytest.approx(1.0 / 60.0)


def test_a_step_coarser_than_a_frame_is_refused_at_the_api() -> None:
    """The solver steps between frames, never across them."""

    with pytest.raises(ValueError, match="one frame interval"):
        _make_dynamics(frames_per_second=60, solver_step_s=0.05)
    assert _make_dynamics(frames_per_second=60, solver_step_s=0.001) is not None


def test_a_step_fine_enough_to_be_unbounded_is_refused_with_its_cost() -> None:
    """The frame budget bounds how many frames; this bounds what each costs."""

    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.simulate(
            *fx.pendulum()[:2],
            start_time_s=0.0,
            end_time_s=0.1,
            frames_per_second=60,
            time_step_s=1.0e-9,
        )
    assert excinfo.value.reason == "solver_step_too_fine"
    assert excinfo.value.observed["steps_per_sample"] > dyn.MAXIMUM_STEPS_PER_SAMPLE


def test_a_finer_step_is_what_lets_a_bouncing_contact_run() -> None:
    """Phase 2's refusal and phase 3's parameter are the same mechanism.

    Phase 2 refused a restitution the default step could not deliver and
    named the step it would take; this is that step being available to give.
    """

    components, joints, _placements = fx.pendulum()
    for component in components:
        if component["name"] == "arm":
            component["collision"] = {
                "shapes": [
                    fx.collision_shape("sphere", radius_mm=5.0, restitution=0.6)
                ],
                "mesh": None,
            }
    with pytest.raises(dyn.DynamicsError, match="finer"):
        dyn.simulate(
            components,
            joints,
            start_time_s=0.0,
            end_time_s=0.1,
            frames_per_second=60,
        )
    run = dyn.simulate(
        components,
        joints,
        start_time_s=0.0,
        end_time_s=0.1,
        frames_per_second=60,
        time_step_s=0.0005,
    )
    assert run["solver_step_s"] <= 0.001
