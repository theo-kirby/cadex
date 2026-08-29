# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Loop closures (docs/MUJOCO.md M2, phase 6).

Our assembly graph may contain loops and MuJoCo may not, so a four-bar
becomes three tree edges plus one equality constraint. The failure this
guards against is not a model that refuses to compile -- it is one that
compiles *pre-stressed*: a closure violated at the starting pose, which the
solver pulls into shape on the first step, so the animation opens with a
snap and every frame after it is a slightly different mechanism than the one
the author drew.

``‖efc_pos‖ ≈ 0`` at the solved pose is the whole gate, and it is asserted
inside :func:`CadexDynamics.build_model` rather than only here, so it holds
for every assembly and not only for the fixtures.

Both anchors of a ``connect`` and the full ``relpose`` of a ``weld`` are
given explicitly. MuJoCo's defaults resolve them through the model's
reference configuration -- and this model's reference configuration is
deliberately *not* the solved pose (phase 4), so the defaults would close
the loop in the wrong place while looking entirely ordinary in the XML.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")


def _equality_residual(model, qpos) -> float:
    data = mujoco.MjData(model)
    data.qpos[:] = list(qpos)
    mujoco.mj_forward(model, data)
    return max(
        (
            abs(float(data.efc_pos[row]))
            for row in range(int(data.nefc))
            if int(data.efc_type[row])
            == int(mujoco.mjtConstraint.mjCNSTR_EQUALITY)
        ),
        default=0.0,
    )


def test_a_four_bar_closes_with_a_connect_and_no_pre_stress() -> None:
    components, joints, placements = fx.four_bar()
    built = dyn.build_model(components, joints)
    model = built["model"]
    assert model.neq == 1
    assert int(model.eq_type[0]) == int(mujoco.mjtEq.mjEQ_CONNECT)
    assert _equality_residual(model, built["qpos_solved"]) < 1.0e-9

    # ...and the tree part still reproduces the solved placements exactly.
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    mujoco.mj_forward(model, data)
    for name, expected in placements.items():
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
        assert dyn.vector_mm(data.xpos[body_id]) == pytest.approx(
            dyn.matrix_translation_mm(expected), abs=1.0e-6
        ), name


def test_a_four_bar_stays_closed_while_it_swings() -> None:
    """The loop is a constraint, not a starting condition."""

    components, joints, _placements = fx.four_bar()
    built = dyn.build_model(components, joints)
    model = built["model"]
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    # The linkage lies in the XY plane and every hinge axis is +Z, so
    # gravity produces no torque on it at all: driving the crank is the only
    # way to make this a test of anything.
    data.qvel[0] = 2.0
    worst = 0.0
    moved = 0.0
    start = float(data.qpos[0])
    for _step in range(500):
        mujoco.mj_step(model, data)
        worst = max(
            worst,
            max(
                (
                    abs(float(data.efc_pos[row]))
                    for row in range(int(data.nefc))
                    if int(data.efc_type[row])
                    == int(mujoco.mjtConstraint.mjCNSTR_EQUALITY)
                ),
                default=0.0,
            ),
        )
        moved = max(moved, abs(float(data.qpos[0]) - start))
    # It really did swing -- a mechanism that never moved would satisfy any
    # closure gate at all.
    assert moved > 0.05
    # 0.05 mm over a second of driven motion, with the stiffened solref.
    # MuJoCo's default equality time constant of 0.02 s gives 3 mm here, on
    # a 200 mm mechanism: a loop that visibly comes apart while it runs.
    assert worst < 1.0e-4, f"the loop drifted open by {dyn.length_mm(worst):.4g} mm"
    assert list(built["model"].eq_solref[0]) == pytest.approx(
        [2.0 * dyn.DEFAULT_TIME_STEP_S, 1.0]
    )


def _welded_pair() -> tuple[list[dict], list[dict], dict]:
    """Two hinged links bridged by a fixed joint that actually closes."""

    components, joints, placements = fx.build(
        [
            {"name": "ground", "grounded": True, "size": (300.0, 40.0, 20.0)},
            {"name": "left", "size": (150.0, 30.0, 20.0)},
            {"name": "right", "size": (150.0, 30.0, 20.0)},
        ],
        [
            {
                "name": "pin_left",
                "kind": "revolute",
                "parent": "ground",
                "child": "left",
                "parent_frame": fx.frame((-100.0, 0.0, 20.0)),
                "child_frame": fx.frame(),
                "values": [0.4],
            },
            {
                "name": "pin_right",
                "kind": "revolute",
                "parent": "ground",
                "child": "right",
                "parent_frame": fx.frame((100.0, 0.0, 20.0)),
                "child_frame": fx.frame(),
                "values": [0.4],
            },
        ],
    )
    joints.append(
        fx.closing_joint(
            "bridge", "fixed", "left", "right", fx.frame((60.0, 0.0, 0.0)), placements
        )
    )
    return components, joints, placements


def test_a_weld_closure_pins_orientation_as_well_as_position() -> None:
    components, joints, placements = _welded_pair()
    built = dyn.build_model(components, joints)
    model = built["model"]
    assert int(model.eq_type[0]) == int(mujoco.mjtEq.mjEQ_WELD)
    assert built["tree"]["closures"][0]["constrained_dof"] == 6
    assert _equality_residual(model, built["qpos_solved"]) < 1.0e-9

    # Two hinges welded to each other is a structure, not a mechanism: the
    # weld's six rows take away both remaining degrees of freedom, so
    # driving one hinge moves nothing.
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    data.qvel[0] = 1.5
    for _step in range(200):
        mujoco.mj_step(model, data)
    assert list(data.qpos) == pytest.approx(built["qpos_solved"], abs=1.0e-3)

    # ...and that is the weld doing it, not the fixture being immovable:
    # without the closure the same push swings both links freely.
    loose = dyn.build_model(components, joints[:2])
    free_data = mujoco.MjData(loose["model"])
    free_data.qpos[:] = loose["qpos_solved"]
    free_data.qvel[0] = 1.5
    for _step in range(200):
        mujoco.mj_step(loose["model"], free_data)
    assert abs(float(free_data.qpos[0]) - loose["qpos_solved"][0]) > 0.1


def test_the_closure_owes_nothing_to_the_reference_configuration() -> None:
    """The bug this design is built around, kept where it can be seen.

    A body-anchored ``connect`` takes one anchor and derives the other by
    resolving it through the model's *reference* configuration. This model's
    reference configuration is the one where every joint's connector frames
    coincide -- deliberately not the solved pose -- so the derived anchor
    lands somewhere else entirely. The four-bar built that way closed 16 mm
    away from where it should, and its XML looked completely ordinary.

    Sites carry both frames explicitly, so nothing is inferred. The test:
    the closure is violated at the reference configuration and satisfied at
    the solved one, which is only possible if the two are different poses
    and the constraint knows about the second.
    """

    components, joints, _placements = _welded_pair()
    built = dyn.build_model(components, joints)
    model = built["model"]
    assert int(model.eq_objtype[0]) == int(mujoco.mjtObj.mjOBJ_SITE)
    assert _equality_residual(model, model.qpos0) > 1.0e-3
    assert _equality_residual(model, built["qpos_solved"]) < 1.0e-9
    # The two poses really are different, so the line above is not two ways
    # of saying the same thing.
    assert list(model.qpos0) != pytest.approx(built["qpos_solved"], abs=1.0e-6)


def test_each_closure_site_sits_on_its_own_connector_frame() -> None:
    components, joints, _placements = fx.four_bar()
    built = dyn.build_model(components, joints)
    closure = built["tree"]["closures"][0]
    model = built["model"]
    for component, local in zip(
        closure["components"], closure["local_matrices"], strict=True
    ):
        site = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_SITE, f"{closure['joint']}/{component}"
        )
        assert site >= 0
        assert list(model.site_pos[site]) == pytest.approx(
            dyn.vector_m(dyn.matrix_translation_mm(local)), abs=1.0e-12
        )
        assert list(model.site_quat[site]) == pytest.approx(
            dyn.quaternion_wxyz_from_matrix(local), abs=1.0e-12
        )
    # Sites are frames, not geometry: the model still carries no collision
    # shape at all.
    assert model.ngeom == 0


def test_a_pre_stressed_closure_is_refused_rather_than_snapped_shut() -> None:
    components, joints, _placements = fx.four_bar()
    # Move the closing joint's connector 3 mm along the coupler: the loop no
    # longer meets, and MuJoCo would happily drag it closed on step one.
    closing = next(joint for joint in joints if joint["name"] == "c")
    closing["connectors"][0]["local_matrix"] = dyn.matrix_multiply(
        closing["connectors"][0]["local_matrix"],
        dyn.matrix_from_rotation_translation(
            [1, 0, 0, 0, 1, 0, 0, 0, 1], (3.0, 0.0, 0.0)
        ),
    )
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "closure_inconsistent"
    assert "3" in str(excinfo.value)


def test_a_joint_at_its_limit_is_not_mistaken_for_an_open_loop() -> None:
    """``efc_pos`` carries limit rows too; only equality rows are a closure."""

    components, joints, _placements = fx.build(
        [{"name": "base", "grounded": True}, {"name": "arm"}],
        [
            {
                "name": "hinge",
                "kind": "revolute",
                "parent": "base",
                "child": "arm",
                "parent_frame": fx.frame((0.0, 0.0, 30.0)),
                "child_frame": fx.frame(),
                "values": [math.radians(45.0)],
                "angle_limits_degrees": [-45.0, 45.0],
            }
        ],
    )
    built = dyn.build_model(components, joints)
    model = built["model"]
    assert model.neq == 0
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"]
    mujoco.mj_forward(model, data)
    assert int(data.nefc) >= 1  # the limit is active, and that is fine
    assert dyn._closure_violation(mujoco, model, built["qpos_solved"]) == 0.0
