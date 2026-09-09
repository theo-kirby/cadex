# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A task whose model MJX cannot build is refused when it is declared.

ADR-281. A lifecycle walk authored a slider-crank whose frame carried a
**cylinder** collision rail and whose coupler carried a **box**. The
assembly solved, the MJCF exported, the rollout ran, the closure held to
0.0015 mm -- and the training leg died 2.27 seconds in on
``mjx.put_model`` raising ``NotImplementedError: (mjGEOM_CYLINDER,
mjGEOM_BOX) collisions not implemented``, with the design turn that chose
the cylinder twenty minutes and one process boundary away.

MJX builds one contact function per geom **type pair** and has none for
four of them. Nothing about the model is wrong: stock MuJoCo simulates a
cylinder against a box perfectly well, which is why every check the engine
already ran passed. The thing that is wrong is *when* the author finds
out, and a training task is the one export that is only ever consumed by
MJX -- so that is where the refusal goes.

Two halves, and only the first runs under ``pixi run test-engine``:

* the filter and the refusal, on stock MuJoCo, which the engine has;
* the table itself against ``mjx.has_collision_fn``, which needs the
  offboard trainer's venv and skips here (ADR-084). A future MJX that
  implements one of these four fails that test, and that failure is good
  news -- its message says so.
"""

from __future__ import annotations

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")


OBSERVATIONS = [
    {"kind": "position", "joint": "elbow", "motion_type": "angular", "name": "q"},
    {"kind": "velocity", "joint": "elbow", "motion_type": "angular", "name": "qd"},
]

MOTOR = {
    "joint": "elbow",
    "motion_type": "angular",
    "kind": "motor",
    "control_nmm": "400*sin(2*pi*time)",
    "torque_limit_nmm": 800.0,
}

TASK = {
    "actions": [
        {"joint": "elbow", "motion_type": "angular", "actuator_kind": "motor"}
    ],
    "reward": [{"label": "hold", "expression": "-q**2", "weight": 1.0}],
    "termination": [],
    "episode_seconds": 1.0,
    "control_hz": 50,
    "randomisation": [],
    "label": "hold",
}


def _arm(post_kind: str, fore_kind: str):
    """The two-link arm with a collision shape on the post and the forearm.

    ``post`` is grounded and ``fore`` hangs off ``upper``, so the two are
    two joints apart: neither the exclusion the joints write nor MuJoCo's
    parent-child filter separates them, and their shapes are a live
    candidate pair. That is the same topology as the walk's slider-crank,
    where the frame's rail and the coupler were the offending pair.
    """

    shapes = {
        "cylinder": fx.collision_shape(
            "cylinder", radius_mm=20.0, length_mm=200.0
        ),
        "box": fx.collision_shape("box", size_mm=[100.0, 40.0, 20.0]),
        "capsule": fx.collision_shape(
            "capsule", radius_mm=20.0, length_mm=200.0
        ),
    }
    components, joints, _placements = fx.two_link_arm(limits=True)
    by_name = {record["name"]: record for record in components}
    by_name["post"]["collision"] = {"shapes": [shapes[post_kind]], "mesh": None}
    by_name["fore"]["collision"] = {"shapes": [shapes[fore_kind]], "mesh": None}
    return dyn.build_model(components, joints, actuators=[MOTOR])


def _reloaded(built):
    observations = dyn.observation_records(
        list(OBSERVATIONS),
        built["tree"],
        built["joint_records"],
        built["actuators"],
    )
    exported = dyn.export_mjcf(built, observations=observations)
    model = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    return model, observations


# ---------------------------------------------------------------------------
# The filter.
# ---------------------------------------------------------------------------


def test_the_candidate_pairs_are_the_ones_the_joints_did_not_exclude() -> None:
    """Post against forearm, and nothing else, on a three-body arm.

    The exclusions the joints write remove post/upper and upper/fore; what
    is left is the pair two joints apart, which is precisely the pair a
    script never thinks about.
    """

    built = _arm("box", "box")
    model, _ = _reloaded(built)
    named = {
        tuple(
            sorted(
                str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom))
                for geom in pair
            )
        )
        for pair in dyn.candidate_collision_pairs(mujoco, model)
    }
    assert named == {("fore/collision0", "post/collision0")}


def _grouped(post_shape, fore_shape):
    components, joints, _placements = fx.two_link_arm(limits=True)
    by_name = {record["name"]: record for record in components}
    by_name["post"]["collision"] = {"shapes": [post_shape], "mesh": None}
    by_name["fore"]["collision"] = {"shapes": [fore_shape], "mesh": None}
    return dyn.build_model(components, joints, actuators=[MOTOR])


def test_one_sided_collides_with_does_not_separate_the_pair() -> None:
    """``collides_with=[]`` on its own is not the escape, and must not be sold as one.

    MuJoCo's mask test is an ``or`` over both directions, so a shape that
    declares it collides with nothing is still touchable by a shape that
    collides with everything. The module says so; this pins it, and it is
    why the refusal's correction names *both* sides.
    """

    built = _grouped(
        fx.collision_shape(
            "cylinder",
            radius_mm=20.0,
            length_mm=200.0,
            contact_group=1,
            collides_with=[],
        ),
        fx.collision_shape("box", size_mm=[100.0, 40.0, 20.0]),
    )
    model, _ = _reloaded(built)
    assert len(dyn.mjx_unsupported_collision_pairs(mujoco, model)) == 1


def test_groups_that_agree_leave_no_candidate_pair() -> None:
    """The correction, taken on both sides: no candidate pair, no refusal.

    The decorative shape goes in group 1 and the other shape's
    ``collides_with`` omits it, which is what makes the mask test fail in
    both directions.
    """

    built = _grouped(
        fx.collision_shape(
            "cylinder",
            radius_mm=20.0,
            length_mm=200.0,
            contact_group=1,
            collides_with=[],
        ),
        fx.collision_shape(
            "box", size_mm=[100.0, 40.0, 20.0], contact_group=0, collides_with=[0]
        ),
    )
    model, _ = _reloaded(built)
    assert dyn.candidate_collision_pairs(mujoco, model) == []
    assert dyn.mjx_unsupported_collision_pairs(mujoco, model) == []


# ---------------------------------------------------------------------------
# The refusal.
# ---------------------------------------------------------------------------


def test_a_cylinder_against_a_box_is_named_as_the_pair_mjx_cannot_build() -> None:
    """The row carries both geoms, both bodies and both kinds."""

    built = _arm("cylinder", "box")
    model, _ = _reloaded(built)
    rows = dyn.mjx_unsupported_collision_pairs(mujoco, model)
    assert len(rows) == 1
    assert sorted(rows[0]["kinds"]) == ["box", "cylinder"]
    assert sorted(rows[0]["bodies"]) == ["fore", "post"]
    assert sorted(rows[0]["geoms"]) == ["fore/collision0", "post/collision0"]


def test_declaring_a_task_on_that_model_is_refused_where_it_is_written() -> None:
    """The regression. Before ADR-281 this bundle was built and shipped.

    Everything upstream of it still passes -- the model compiles, the MJCF
    exports, the pose holds -- which is exactly why the failure used to
    arrive from a trainer instead.
    """

    built = _arm("cylinder", "box")
    model, observations = _reloaded(built)
    with pytest.raises(dyn.DynamicsError) as caught:
        dyn.task_records(built, model, dict(TASK), observations=observations)
    error = caught.value
    assert error.reason == "mjx_unsupported_collision_pair"
    assert "post/collision0" in str(error)
    assert "fore/collision0" in str(error)
    assert "capsule" in error.correction
    assert "contact_group" in error.correction
    assert error.observed["unsupported_pairs"][0]["bodies"]


def test_the_same_task_is_accepted_once_the_rail_is_a_capsule() -> None:
    """The correction the refusal names, taken, and the task builds.

    A capsule is the stand-in the message offers for a shaft or a rail;
    MJX collides it with everything.
    """

    built = _arm("capsule", "box")
    model, observations = _reloaded(built)
    bundle = dyn.task_records(built, model, dict(TASK), observations=observations)
    assert bundle["label"] == "hold"


# ---------------------------------------------------------------------------
# The table, against MJX itself.
# ---------------------------------------------------------------------------


def test_the_unsupported_table_is_what_mjx_actually_refuses() -> None:
    """Every type pair, both ways, compared with ``mjx.has_collision_fn``.

    Skips in the engine environment by design (ADR-084). Run it from a venv
    built from ``training/requirements.txt``.
    """

    try:
        from mujoco.mjx._src import collision_driver
    except Exception:  # pragma: no cover - the engine environment
        pytest.skip(
            "mujoco.mjx is the offboard trainer's dependency and is "
            "deliberately absent from the engine environment (ADR-084). Run "
            "this test from a venv built from training/requirements.txt."
        )

    kinds = sorted(
        {str(name) for name in dyn._COLLISION_GEOM_TYPES.values()} | {"ellipsoid"}
    )
    measured = set()
    for first in kinds:
        for second in kinds:
            enums = tuple(
                getattr(mujoco.mjtGeom, f"mjGEOM_{kind.upper()}")
                for kind in (first, second)
            )
            if collision_driver.has_collision_fn(
                *enums
            ) or collision_driver.has_collision_fn(*reversed(enums)):
                continue
            measured.add(tuple(sorted((first, second))))
    # plane/plane and plane/hfield have no contact function and never
    # become candidate pairs, so they are not the engine's business.
    measured.discard(("plane", "plane"))
    assert measured == set(dyn._MJX_UNSUPPORTED_PAIRS), (
        "MJX's set of unimplemented collision pairs has changed. If it "
        "shrank, that is good news: drop the row from "
        "CadexDynamics._MJX_UNSUPPORTED_PAIRS and the refusal goes with it."
    )
