# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A free base stands on the environment's floor (ADR-335).

An assembly that grounds nothing is a mechanism whose fixed frame is not a
part of the design -- a biped, a balancer, anything that is meant to fall.
The tree gives its first component a free joint; ``build_model`` writes one
plane on the world body for it to stand on, and nothing for a grounded model,
whose ground is whatever it grounded. Headless: stock MuJoCo, no engine.
"""

from __future__ import annotations

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")

BLOCK = (100.0, 40.0, 20.0)


def _free_pendulum() -> tuple[list[dict], list[dict], dict]:
    """A block resting on z = 0 with an arm hinged to it, nothing grounded.

    The block is a 20 mm tall box centred on its own origin, placed 10 mm
    up, so its underside is exactly on the world's z = 0 -- the pose a
    solved biped's soles have -- and a floor at z = 0 is what keeps it
    there.
    """

    return fx.build(
        [
            {
                "name": "block",
                "world": fx.frame((0.0, 0.0, 10.0)),
                "size": BLOCK,
                "collision": {
                    "shapes": [fx.collision_shape("box", size_mm=list(BLOCK))],
                    "mesh": None,
                },
            },
            {"name": "arm", "size": (300.0, 40.0, 20.0)},
        ],
        [
            {
                "name": "hinge",
                "kind": "revolute",
                "parent": "block",
                "child": "arm",
                # The hinge is over the block's centre and through the arm's
                # own centre, so the arm balances and the stack stands
                # rather than tipping: what is measured is the floor, not
                # a cantilever falling over.
                "parent_frame": fx.frame((0.0, 0.0, 30.0), (1.0, 0.0, 0.0), 90.0),
                "child_frame": fx.frame((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 90.0),
                "values": [0.0],
            }
        ],
    )


def _geom(model, name: str) -> int:
    return int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name))


def test_a_free_base_gets_the_environment_floor_and_a_grounded_model_does_not() -> None:
    components, joints, _placements = _free_pendulum()
    built = dyn.build_model(components, joints)
    floor = built["environment"]["floor"]
    assert floor["geom"] == dyn.ENVIRONMENT_FLOOR_GEOM
    assert floor["body"] == "world"
    assert floor["z_mm"] == 0.0
    model = built["model"]
    index = _geom(model, dyn.ENVIRONMENT_FLOOR_GEOM)
    assert index >= 0
    assert int(model.geom_type[index]) == int(mujoco.mjtGeom.mjGEOM_PLANE)
    assert int(model.geom_bodyid[index]) == 0, "the floor is the world's, not a part's"
    assert list(model.geom_friction[index]) == pytest.approx(
        list(dyn.ENVIRONMENT_FLOOR_FRICTION)
    )
    # Seven free coordinates and one hinge.
    assert int(model.nq) == 8

    grounded_components, grounded_joints, _ = fx.pendulum()
    grounded = dyn.build_model(grounded_components, grounded_joints)
    assert grounded["environment"] is None
    assert _geom(grounded["model"], dyn.ENVIRONMENT_FLOOR_GEOM) == -1


def test_a_free_base_rests_on_the_floor_rather_than_falling_through_it() -> None:
    """Half a second of passive physics: the block stays where it was placed.

    Without the floor the block and its arm would be 1.2 m down by now.
    With it, the block's underside meets z = 0 and the pair's default
    contact holds it there to the tolerance the solver works at.
    """

    components, joints, placements = _free_pendulum()
    built = dyn.build_model(components, joints)
    model, data = built["model"], mujoco.MjData(built["model"])
    data.qpos[:] = list(built["qpos_solved"])
    mujoco.mj_forward(model, data)
    body = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "block"))
    start_z_mm = dyn.length_mm(float(data.xpos[body][2]))
    assert start_z_mm == pytest.approx(10.0, abs=1e-6)
    steps = int(round(0.5 / float(model.opt.timestep)))
    for _ in range(steps):
        mujoco.mj_step(model, data)
    end_z_mm = dyn.length_mm(float(data.xpos[body][2]))
    assert end_z_mm == pytest.approx(start_z_mm, abs=1.0), end_z_mm
    touching = {
        str(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(g)))
        for index in range(int(data.ncon))
        for g in (data.contact[index].geom1, data.contact[index].geom2)
    }
    assert dyn.ENVIRONMENT_FLOOR_GEOM in touching, touching


def test_the_manifest_names_the_floor_a_free_base_stood_on() -> None:
    components, joints, _placements = _free_pendulum()
    built = dyn.build_model(components, joints)
    evidence = dyn.model_evidence(built, components)
    assert evidence["grounded_components"] == []
    assert evidence["environment"]["floor"]["geom"] == dyn.ENVIRONMENT_FLOOR_GEOM
    assert (evidence["joints"][0]["mujoco_joint"], evidence["joints"][0]["mujoco_type"]) == (
        "block/free",
        "free",
    )
    # Resting, at t = 0, on the environment's floor -- reported as world.
    pairs = [
        sorted(contact["component_outputs"]) for contact in evidence["initial_contacts"]
    ]
    assert ["block", "world"] in pairs, pairs

    grounded_components, grounded_joints, _ = fx.pendulum()
    grounded = dyn.model_evidence(
        dyn.build_model(grounded_components, grounded_joints), grounded_components
    )
    assert grounded["environment"] is None


#: A foot like ot11-quad-1's: a 7.5 mm sphere, on a 10 g body.
FOOT_RADIUS_MM = 7.5
FOOT_MASS_KG = 0.010

#: The stepping load, as a multiple of the foot's weight. A servo pressing a
#: light foot into the floor drives it far harder than gravity does, and a
#: soft contact sinks in proportion to that acceleration rather than to the
#: weight: round 11's policy on the old spring sank 6.5-9.4 mm, which is
#: about 30 g by MuJoCo's own impedance arithmetic (ADR-469).
STEPPING_LOAD_WEIGHTS = 30.0

#: The walk contract's stance threshold (``CadexEvaluation.STANCE_MM``): a
#: foot pressed into the floor must still read as a foot on it, not in it.
STANCE_MM = 1.0


def test_a_foot_under_a_stepping_load_stays_on_the_floor_rather_than_in_it() -> None:
    """The exported contact, pressed the way a stepping servo presses it.

    One free 7.5 mm sphere on the environment floor, pushed down at thirty
    times its own weight for a second. Measured: 2.6 mm into the floor on
    MuJoCo's default 0.02 s spring, which is what ``export_mjcf`` wrote for
    both the foot and the floor until ADR-469, and 0.46 mm at 0.004 s. The
    floor's own spring is asserted too, because a pair averages the two and
    a default floor would undo half of the foot's.
    """

    built = dyn.build_model(
        *fx.build(
            [
                {
                    "name": "foot",
                    "world": fx.frame((0.0, 0.0, FOOT_RADIUS_MM)),
                    "size": (15.0, 15.0, 15.0),
                    "collision": {
                        "shapes": [
                            fx.collision_shape("sphere", radius_mm=FOOT_RADIUS_MM)
                        ],
                        "mesh": None,
                    },
                }
            ],
            [],
        )[:2]
    )
    model = built["model"]
    floor = _geom(model, dyn.ENVIRONMENT_FLOOR_GEOM)
    sphere = _geom(model, "foot/collision0")
    assert list(model.geom_solref[floor]) == pytest.approx([dyn.CONTACT_TIMECONST_S, 1.0])
    assert list(model.geom_solref[sphere]) == pytest.approx([dyn.CONTACT_TIMECONST_S, 1.0])

    body = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "foot"))
    model.body_mass[body] = FOOT_MASS_KG
    data = mujoco.MjData(model)
    data.qpos[:] = list(built["qpos_solved"])
    weight_n = FOOT_MASS_KG * 9.81
    data.xfrc_applied[body][2] = -STEPPING_LOAD_WEIGHTS * weight_n
    deepest_mm = 0.0
    for _ in range(int(round(1.0 / float(model.opt.timestep)))):
        mujoco.mj_step(model, data)
        bottom_mm = dyn.length_mm(float(data.xpos[body][2])) - FOOT_RADIUS_MM
        deepest_mm = min(deepest_mm, bottom_mm)
    assert -deepest_mm <= STANCE_MM, deepest_mm
