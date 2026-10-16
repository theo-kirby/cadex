# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A joint's stop is as stiff as its joint_dynamics says (ADR-724).

MuJoCo's default ``solreflimit`` (0.02 s, ratio 1) makes a light passive
joint's stop a weak spring: on orun7-cat's paw pin 2 N*m pushed it 25 degrees
past the stop. ``limit_time_constant_s`` and ``limit_damping_ratio`` set it.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
from cadex_assembly_api import AssemblyDomainAPI
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS

mujoco = pytest.importorskip("mujoco")


def _api() -> AssemblyDomainAPI:
    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    return AssemblyDomainAPI(pack.api_exports, pack.output_types)


def _hinge(api: AssemblyDomainAPI):
    base = api.component({"document_uid": "doc", "object_name": "base"}, grounded=True)
    part = api.component({"document_uid": "doc", "object_name": "part"})
    return api.joint("revolute", api.connector(base), api.connector(part))


def _elbow(**limit):
    return {"joint": "elbow", "motion_type": "angular", **limit}


def _jnt(model, name: str) -> int:
    return int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name))


def test_the_api_carries_a_limit_stiffness_and_it_alone_is_a_declaration() -> None:
    api = _api()
    value = api.joint_dynamics(_hinge(api), limit_time_constant_s=0.004)
    assert value.properties["limit_time_constant_s"] == 0.004
    assert value.properties["limit_damping_ratio"] is None
    bare = api.joint_dynamics(_hinge(api), damping_nmms_per_deg=0.1)
    assert bare.properties["limit_time_constant_s"] is None


@pytest.mark.parametrize(
    "arguments",
    [
        {"limit_time_constant_s": 0.0},
        {"limit_time_constant_s": -0.01},
        {"limit_time_constant_s": 5.0},
        {"limit_damping_ratio": 0.0},
    ],
)
def test_a_limit_stiffness_out_of_range_is_refused(arguments) -> None:
    api = _api()
    with pytest.raises(Exception, match="limit_"):
        api.joint_dynamics(_hinge(api), **arguments)


def test_the_compiled_model_carries_the_declared_solref_and_others_keep_the_default() -> None:
    components, joints, _ = fx.two_link_arm(limits=True)
    built = dyn.build_model(
        components,
        joints,
        joint_dynamics=[_elbow(limit_time_constant_s=0.004, limit_damping_ratio=1.5)],
    )
    model = built["model"]
    assert list(model.jnt_solref[_jnt(model, "elbow")]) == pytest.approx([0.004, 1.5])
    assert list(model.jnt_solref[_jnt(model, "shoulder")]) == pytest.approx(
        [dyn.DEFAULT_LIMIT_TIME_CONSTANT_S, dyn.DEFAULT_LIMIT_DAMPING_RATIO]
    )
    evidence = dyn.model_evidence(built, components)["joint_dynamics"][0]
    assert evidence["limit_solref"] == pytest.approx([0.004, 1.5])
    assert evidence["declared"]["limit_time_constant_s"] == 0.004
    # One given alone keeps MuJoCo's default for the other.
    ratio_only = dyn.build_model(
        components, joints, joint_dynamics=[_elbow(limit_damping_ratio=2.0)]
    )["model"]
    assert list(ratio_only.jnt_solref[_jnt(ratio_only, "elbow")]) == pytest.approx(
        [0.02, 2.0]
    )


def test_a_time_constant_below_two_solver_steps_is_refused() -> None:
    """MuJoCo would silently raise it to the floor; the refusal names the floor."""

    components, joints, _ = fx.two_link_arm(limits=True)
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(
            components, joints, joint_dynamics=[_elbow(limit_time_constant_s=0.002)]
        )
    assert excinfo.value.reason == "limit_time_constant_below_solver_floor"
    assert excinfo.value.observed["floor_s"] == pytest.approx(0.004)
    # A finer step admits it.
    built = dyn.build_model(
        components,
        joints,
        time_step_s=0.001,
        joint_dynamics=[_elbow(limit_time_constant_s=0.002)],
    )
    assert float(built["model"].jnt_solref[_jnt(built["model"], "elbow")][0]) == 0.002


def test_a_limit_stiffness_on_a_joint_without_limits_is_refused() -> None:
    components, joints, _ = fx.pendulum()
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(
            components,
            joints,
            joint_dynamics=[
                {"joint": "hinge", "motion_type": "angular", "limit_time_constant_s": 0.004}
            ],
        )
    assert excinfo.value.reason == "limit_stiffness_without_limits"


def _past_the_stop_deg(joint_dynamics) -> float:
    """The elbow held against its upper stop by a steady torque, gravity off."""

    components, joints, _ = fx.two_link_arm(limits=True)
    built = dyn.build_model(
        components, joints, gravity_m_s2=(0.0, 0.0, 0.0), joint_dynamics=joint_dynamics
    )
    model = built["model"]
    data = mujoco.MjData(model)
    elbow = _jnt(model, "elbow")
    upper = float(model.jnt_range[elbow][1])
    data.qpos[int(model.jnt_qposadr[elbow])] = upper
    dof = int(model.jnt_dofadr[elbow])
    for _step in range(3000):
        data.qfrc_applied[dof] = 20.0
        mujoco.mj_step(model, data)
    return math.degrees(float(data.qpos[int(model.jnt_qposadr[elbow])]) - upper)


def test_a_stiff_stop_holds_where_the_default_one_yields() -> None:
    """The physics, not the field: the same torque, a fraction of the yield."""

    soft = _past_the_stop_deg([])
    stiff = _past_the_stop_deg([_elbow(limit_time_constant_s=0.004)])
    assert soft > 0.0
    assert stiff < soft / 10.0


def test_the_exported_file_keeps_the_limit_stiffness() -> None:
    components, joints, _ = fx.two_link_arm(limits=True)
    built = dyn.build_model(
        components, joints, joint_dynamics=[_elbow(limit_time_constant_s=0.004)]
    )
    reloaded = dyn.load_model(dyn.export_mjcf(built)["xml"])
    assert float(reloaded.jnt_solref[_jnt(reloaded, "elbow")][0]) == pytest.approx(0.004)
