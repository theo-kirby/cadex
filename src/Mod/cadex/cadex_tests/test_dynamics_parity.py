# SPDX-License-Identifier: LGPL-2.1-or-later

"""The exit criterion (docs/MUJOCO.md M2, phase 5).

Everything after M2 depends on the model being *right*, and a model that is
wrong in the ways that matter still compiles, still simulates, and still
produces an animation somebody will believe. So the gate is not "does it
run": it is two claims that a wrong model fails.

**Pose parity at t=0.** Each tree joint's coordinate is derived *from the
solved placements by inversion*, then ``mj_forward`` runs and every body's
world pose is compared against ``component_placements``. The derivation is
what makes this a test rather than a tautology: the model's reference
configuration is the one where each joint's two connector frames coincide,
not the solved one, so recovering the solved pose means the anchor, the
axis and the frame composition are all right. Building the model *at* the
solved pose and checking its own reference configuration would assert only
that the same numbers were written twice -- it passes on a model whose
joint axes are entirely wrong.

**Perturbation parity.** Pose at t=0 cannot distinguish a hinge from a
slide sharing a frame: at their common reference configuration both are the
identity. So each joint is displaced by δ in turn, and the child's motion
relative to its parent must be exactly the motion that joint kind allows,
about that connector's +Z, of magnitude δ -- with everything outside the
joint's subtree unmoved. That is the difference between "the tree is right"
and "the mechanism is right".

Plus the residual gate, which needs no MuJoCo at all and is the cheapest
detector there is for a frame-composition, unit or handedness error.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
import dynamics_trace_digest as digest_module

mujoco = pytest.importorskip("mujoco")

#: The plan's tolerances: 1e-6 mm on position, 1e-9 per quaternion
#: component. Both are far tighter than any error a wrong model produces --
#: those are millimetres and whole degrees -- and comfortably looser than
#: double-precision composition noise.
POSITION_TOLERANCE_MM = 1.0e-6
ROTATION_TOLERANCE = 1.0e-9


def _world_matrices(model, data) -> dict[str, list[float]]:
    """Every body's pose as a placement matrix in millimetres."""

    poses = {}
    for body_id in range(1, model.nbody):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        poses[name] = dyn.matrix_from_quaternion_wxyz(
            list(data.xquat[body_id]), dyn.vector_mm(data.xpos[body_id])
        )
    return poses


def _forward(built, qpos=None):
    model = built["model"]
    data = mujoco.MjData(model)
    data.qpos[:] = built["qpos_solved"] if qpos is None else qpos
    mujoco.mj_forward(model, data)
    return data


def _assert_pose_parity(built, placements) -> None:
    model = built["model"]
    data = _forward(built)
    poses = _world_matrices(model, data)
    assert set(poses) == set(placements), (
        "every component must appear in the model exactly once"
    )
    for name, expected in placements.items():
        assert dyn.matrix_translation_mm(poses[name]) == pytest.approx(
            dyn.matrix_translation_mm(expected), abs=POSITION_TOLERANCE_MM
        ), name
        first = dyn.quaternion_wxyz_from_matrix(poses[name])
        second = dyn.quaternion_wxyz_from_matrix(expected)
        if sum(a * b for a, b in zip(first, second)) < 0.0:
            second = [-value for value in second]
        assert first == pytest.approx(second, abs=ROTATION_TOLERANCE), name


def test_pose_parity_on_a_pendulum() -> None:
    components, joints, placements = fx.pendulum()
    _assert_pose_parity(dyn.build_model(components, joints), placements)


def test_pose_parity_on_a_chain_of_mixed_joints() -> None:
    """Depth, and every direct joint type in one tree."""

    components, joints, placements = fx.build(
        [
            {"name": "base", "grounded": True, "size": (200.0, 200.0, 20.0)},
            {"name": "turret", "size": (120.0, 120.0, 60.0)},
            {"name": "boom", "size": (400.0, 50.0, 30.0)},
            {"name": "stick", "size": (250.0, 40.0, 25.0)},
            {"name": "bucket", "size": (90.0, 80.0, 70.0)},
            {"name": "bracket", "size": (60.0, 60.0, 15.0)},
        ],
        [
            {
                "name": "swing",
                "kind": "revolute",
                "parent": "base",
                "child": "turret",
                "parent_frame": fx.frame((0.0, 0.0, 10.0)),
                "child_frame": fx.frame((0.0, 0.0, -30.0)),
                "values": [0.83],
            },
            {
                "name": "lift",
                "kind": "revolute",
                "parent": "turret",
                "child": "boom",
                "parent_frame": fx.frame((30.0, 0.0, 20.0), (1.0, 0.0, 0.0), 90.0),
                "child_frame": fx.frame((-180.0, 0.0, 0.0), (1.0, 0.0, 0.0), 90.0),
                "values": [-0.42],
            },
            {
                "name": "extend",
                "kind": "cylindrical",
                "parent": "boom",
                "child": "stick",
                "parent_frame": fx.frame((180.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0),
                "child_frame": fx.frame((-100.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0),
                "values": [0.037, 0.29],
            },
            {
                "name": "wrist",
                "kind": "ball",
                "parent": "stick",
                "child": "bucket",
                "parent_frame": fx.frame((110.0, 0.0, 0.0)),
                "child_frame": fx.frame((-20.0, 0.0, 0.0)),
                "values": dyn.quaternion_from_axis_angle_wxyz((0.3, 0.5, -0.8), 0.66),
            },
            {
                "name": "tag",
                "kind": "fixed",
                "parent": "turret",
                "child": "bracket",
                "parent_frame": fx.frame((-40.0, 25.0, 15.0), (0.0, 1.0, 0.0), 22.0),
                "child_frame": fx.frame((0.0, 0.0, -7.5)),
                "values": [],
            },
        ],
    )
    built = dyn.build_model(components, joints)
    assert built["tree"]["maximum_depth"] == 4
    _assert_pose_parity(built, placements)


def test_pose_parity_survives_a_far_from_origin_assembly() -> None:
    """Composition error grows with distance; 4 m out is a real machine."""

    components, joints, placements = fx.pendulum()
    far = dyn.matrix_from_quaternion_wxyz(
        dyn.quaternion_from_axis_angle_wxyz((0.2, 0.9, 0.3), 1.9),
        (4000.0, -2500.0, 900.0),
    )
    for component in components:
        component["solved_matrix"] = dyn.matrix_multiply(
            far, component["solved_matrix"]
        )
    moved = {
        name: dyn.matrix_multiply(far, matrix) for name, matrix in placements.items()
    }
    _assert_pose_parity(dyn.build_model(components, joints), moved)


def _descendants(model, body_id: int) -> set[int]:
    found = {body_id}
    for candidate in range(1, model.nbody):
        parent = candidate
        while parent > 0:
            if parent in found:
                found.add(candidate)
                break
            parent = int(model.body_parentid[parent])
    return found


@pytest.mark.parametrize("delta", [0.17, -0.23])
def test_perturbation_parity_moves_exactly_one_subtree(delta: float) -> None:
    """A hinge and a slide sharing a frame are identical at t=0; not here."""

    components, joints, placements = fx.build(
        [
            {"name": "base", "grounded": True},
            {"name": "arm"},
            {"name": "hand"},
            {"name": "post"},
        ],
        [
            {
                "name": "shoulder",
                "kind": "revolute",
                "parent": "base",
                "child": "arm",
                "parent_frame": fx.frame((20.0, 5.0, 40.0), (1.0, 0.0, 0.0), 90.0),
                "child_frame": fx.frame((-90.0, 0.0, 10.0), (0.0, 1.0, 0.0), 25.0),
                "values": [0.31],
            },
            {
                "name": "reach",
                "kind": "slider",
                "parent": "arm",
                "child": "hand",
                "parent_frame": fx.frame((90.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0),
                "child_frame": fx.frame((-30.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0),
                "values": [0.045],
            },
            {
                "name": "mast",
                "kind": "revolute",
                "parent": "base",
                "child": "post",
                "parent_frame": fx.frame((-60.0, 0.0, 40.0)),
                "child_frame": fx.frame(),
                "values": [0.9],
            },
        ],
    )
    built = dyn.build_model(components, joints)
    model = built["model"]
    reference = _world_matrices(model, _forward(built))

    for record in built["joint_records"]:
        joint_id = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_JOINT, record["mujoco_joint"]
        )
        address = int(model.jnt_qposadr[joint_id])
        qpos = list(built["qpos_solved"])
        qpos[address] += delta
        poses = _world_matrices(model, _forward(built, qpos))

        body_id = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_BODY, record["body"]
        )
        moved = _descendants(model, body_id)
        for other_id in range(1, model.nbody):
            name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, other_id)
            displacement = math.dist(
                dyn.matrix_translation_mm(poses[name]),
                dyn.matrix_translation_mm(reference[name]),
            )
            turn = dyn.rotation_angle_between(
                dyn.quaternion_wxyz_from_matrix(poses[name]),
                dyn.quaternion_wxyz_from_matrix(reference[name]),
            )
            if other_id in moved:
                assert displacement + turn > 1.0e-3, (
                    f"{name} is in {record['mujoco_joint']}'s subtree and did "
                    "not move"
                )
            else:
                assert displacement < POSITION_TOLERANCE_MM, name
                assert turn < ROTATION_TOLERANCE, name

        # ...and the motion is exactly this joint's own: recovered from the
        # perturbed world poses, in the connector frame, it is δ about +Z
        # (or along it) with nothing left over.
        body = next(
            item for item in built["tree"]["bodies"] if item["name"] == record["body"]
        )
        transform = dyn.joint_transform(
            poses[str(body["parent"])],
            body["parent_local_matrix"],
            poses[record["body"]],
            body["child_local_matrix"],
        )
        coordinates = dyn.joint_coordinates(
            str(body["joint_kind"]), transform, context="perturbation"
        )
        solved = dyn.joint_coordinates(
            str(body["joint_kind"]),
            dyn.joint_transform(
                placements[str(body["parent"])],
                body["parent_local_matrix"],
                placements[record["body"]],
                body["child_local_matrix"],
            ),
            context="solved",
        )
        assert coordinates["values"][0] == pytest.approx(
            solved["values"][0] + delta, abs=1.0e-9
        )
        assert coordinates["residual_mm"] < 1.0e-6
        assert coordinates["residual_radians"] < 1.0e-9


def test_a_slide_and_a_hinge_on_one_frame_are_told_apart() -> None:
    """The case pose parity alone cannot see, made explicit."""

    def _built(kind: str, value: float):
        components, joints, _placements = fx.build(
            [{"name": "base", "grounded": True}, {"name": "arm"}],
            [
                {
                    "name": "j",
                    "kind": kind,
                    "parent": "base",
                    "child": "arm",
                    "parent_frame": fx.frame((10.0, 20.0, 30.0), (1.0, 1.0, 0.0), 55.0),
                    "child_frame": fx.frame((10.0, 20.0, 30.0), (1.0, 1.0, 0.0), 55.0),
                    "values": [value],
                }
            ],
        )
        return dyn.build_model(components, joints)

    hinge = _built("revolute", 0.0)
    slide = _built("slider", 0.0)
    # Same frames, same reference pose -- indistinguishable at t=0.
    hinge_pose = _world_matrices(hinge["model"], _forward(hinge))
    slide_pose = _world_matrices(slide["model"], _forward(slide))
    for name, matrix in hinge_pose.items():
        assert matrix == pytest.approx(slide_pose[name], abs=1.0e-12), name
    # Displace both by the same coordinate and they part company.
    turned = _world_matrices(hinge["model"], _forward(hinge, [0.3]))["arm"]
    slid = _world_matrices(slide["model"], _forward(slide, [0.3]))["arm"]
    assert dyn.rotation_angle_between(
        dyn.quaternion_wxyz_from_matrix(turned), [1.0, 0.0, 0.0, 0.0]
    ) == pytest.approx(0.3, abs=1.0e-9)
    assert dyn.rotation_angle_between(
        dyn.quaternion_wxyz_from_matrix(slid), [1.0, 0.0, 0.0, 0.0]
    ) == pytest.approx(0.0, abs=1.0e-12)
    assert math.dist(dyn.matrix_translation_mm(slid), [0.0, 0.0, 0.0]) == pytest.approx(
        300.0, abs=1.0e-6
    )


def test_the_residual_gate_needs_no_mujoco_and_passes_on_a_solved_assembly() -> None:
    for fixture in (fx.pendulum(), fx.four_bar()):
        components, joints, _placements = fixture
        for residual in dyn.closure_residuals(components, joints):
            assert residual["residual_mm"] < dyn.CLOSURE_RESIDUAL_MM, residual
            assert residual["residual_radians"] < dyn.CLOSURE_RESIDUAL_RADIANS, residual


def test_the_residual_gate_catches_a_connector_frame_that_moved() -> None:
    """The cheapest possible detector for a composition or unit error."""

    components, joints, _placements = fx.pendulum()
    joints[0]["connectors"][1]["local_matrix"] = dyn.matrix_multiply(
        joints[0]["connectors"][1]["local_matrix"],
        dyn.matrix_from_rotation_translation(
            [1, 0, 0, 0, 1, 0, 0, 0, 1], (0.0, 2.0, 0.0)
        ),
    )
    residual = dyn.closure_residuals(components, joints)[0]
    assert residual["residual_mm"] == pytest.approx(2.0, abs=1.0e-9)
    # ...and the model refuses to build on it rather than drifting quietly.
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "joint_residual"


def test_the_residual_gate_catches_a_millimetre_metre_confusion() -> None:
    """A frame composed in the wrong unit is out by a factor of a thousand."""

    components, joints, _placements = fx.pendulum()
    frame = list(joints[0]["connectors"][0]["local_matrix"])
    for index in (3, 7, 11):
        frame[index] = frame[index] / 1000.0
    joints[0]["connectors"][0]["local_matrix"] = frame
    residual = dyn.closure_residuals(components, joints)[0]
    assert residual["residual_mm"] > 1.0


def test_a_hinge_whose_axis_was_taken_from_the_wrong_connector_is_refused() -> None:
    """The exact mistake pose parity is built to catch, made by hand."""

    components, joints, _placements = fx.pendulum()
    joints[0]["connectors"][1]["local_matrix"] = dyn.matrix_multiply(
        joints[0]["connectors"][1]["local_matrix"],
        dyn.matrix_from_quaternion_wxyz(
            dyn.quaternion_from_axis_angle_wxyz((1.0, 0.0, 0.0), 0.35)
        ),
    )
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.build_model(components, joints)
    assert excinfo.value.reason == "joint_residual"
    assert excinfo.value.observed["residual_radians"] == pytest.approx(0.35, abs=1e-9)


def _digest_in_a_fresh_interpreter(fixture: str) -> dict:
    """Run one fixture in a process that has never seen this one."""

    here = Path(__file__).resolve().parent
    completed = subprocess.run(
        [sys.executable, str(here / "dynamics_trace_digest.py"), fixture],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(here),
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_the_same_assembly_gives_byte_identical_frames_across_processes() -> None:
    """M3 phase 0, and it is deliberately measured before contact exists.

    If a trace is not already reproducible across interpreters with no
    geoms in the model at all, then contact is not what broke it and the
    determinism gate has a prior problem -- one far cheaper to find now
    than after mesh collision has muddied it. Measured: three separate
    interpreters, identical digests, so the gate starts from a clean base
    and phase 5 inherits a claim rather than a hope.

    Two processes would prove the claim; three is barely more expensive and
    catches the case where a hash happens to be seeded per-pair.
    """

    digests = [_digest_in_a_fresh_interpreter("four_bar") for _repeat in range(3)]
    assert len({record["digest"] for record in digests}) == 1, digests
    assert digests[0]["frame_count"] > 2
    # The same numbers computed in *this* interpreter, so the subprocess
    # path is not quietly comparing two copies of the same mistake.
    components, joints, _placements = fx.four_bar()
    run = dyn.simulate(
        components, joints, start_time_s=0.0, end_time_s=0.5, frames_per_second=60
    )
    assert digest_module.trace_digest(run["frames"]) == digests[0]["digest"]


def test_the_same_assembly_gives_byte_identical_qpos_within_one_process() -> None:
    """Determinism, at the level M2 owns: same inputs, same numbers.

    Cross-restart determinism is M3's gate and needs MuJoCo pinned and
    single-threaded; this is the part that must hold before that is even
    worth measuring.
    """

    components, joints, placements = fx.four_bar()
    reference = None
    for _repeat in range(4):
        built = dyn.build_model(components, joints)
        data = _forward(built)
        snapshot = (
            list(built["qpos_solved"]),
            [float(value) for value in data.xpos.flatten()],
            [float(value) for value in data.xquat.flatten()],
        )
        if reference is None:
            reference = snapshot
        assert snapshot == reference
    _assert_pose_parity(dyn.build_model(components, joints), placements)
