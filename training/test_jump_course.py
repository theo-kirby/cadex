# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-973: a jump course stands one engine box across a straight run, held out by its seed string,
and the whole body -- a trunk's box too -- collides with it.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_jump_course.py`` from the repo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mujoco
import numpy as np
import pytest

import cadex_goto as G
import cadex_train as T

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Mod" / "cadex"))
import CadexDynamics  # noqa: E402

#: A floor and one free body whose box collides only by the floor's bits, as Symon's trunk does
#: (contype 4, conaffinity 121: the floor's contype 1 meets its conaffinity), and a free sphere.
WORLD = b"""<mujoco><option timestep="0.002"/><worldbody>
<geom name="environment/floor" type="plane" size="0 0 0.1" solref="0.004"/>
<body name="trunk" pos="0 0 1"><freejoint/>
<geom name="trunk/box" type="box" size="0.06 0.05 0.03" mass="2" contype="4" conaffinity="121"/></body>
<body name="paw" pos="0 2 1"><freejoint/>
<geom name="paw/sphere" type="sphere" size="0.015" mass="0.05" contype="2" conaffinity="3"/></body>
</worldbody></mujoco>"""


def test_a_course_is_its_seed_strings_and_a_held_out_course_is_never_a_train_one() -> None:
    for kind in G.JUMP_KINDS:
        course = G.jump_course(kind, "heldout", 3)
        assert course["schema"] == G.JUMP_SCHEMA and course["kind"] == kind
        assert G.jump_course(kind, "heldout", 3) == course
        assert G.jump_course(kind, "heldout", 4)["sha256"] != course["sha256"]
        train = {G.jump_course(kind, "train", s)["sha256"] for s in range(200)}
        held = {G.jump_course(kind, "heldout", s)["sha256"] for s in range(10)}
        assert not train & held
    with pytest.raises(SystemExit):
        G.jump_course("under", "train", 0)
    with pytest.raises(SystemExit):
        G.jump_course("over", "test", 0)
    with pytest.raises(SystemExit):
        G.jump_course("over", "train", 0, depth_mm=(1.0, 2.0))
    with pytest.raises(SystemExit):
        G.jump_course("over", "train", 0, near_m=(0.2, 1.0))
    with pytest.raises(SystemExit):
        G.jump_course("over", "train", 0, height_mm=(120.0, 100.0))


def test_an_over_box_is_j1s_thin_box_across_the_path_and_an_onto_box_carries_its_goal_on_top() -> None:
    for seed in range(10):
        over = G.jump_course("over", "heldout", seed)
        box = over["box"]
        assert box["height_mm"] == 80.0 and 60.0 <= box["along_mm"] <= 150.0
        assert 2000.0 <= box["near_mm"] <= 4000.0 and box["far_mm"] == pytest.approx(
            box["near_mm"] + box["along_mm"], abs=1e-3)
        assert abs(box["y_mm"]) <= 50.0 and box["across_mm"] >= 1000.0
        assert over["highest_mm"] == pytest.approx(80.0)
        (gx, gy), = over["goals_xy_m"]
        assert gx * 1000.0 == pytest.approx(box["far_mm"] + 2000.0, abs=0.01) and gy == 0.0

        onto = G.jump_course("onto", "heldout", seed, height_mm=(120.0, 120.0))
        box = onto["box"]
        assert box["height_mm"] == 120.0 and box["along_mm"] >= 600.0
        top, past = onto["goals_xy_m"]
        assert top == pytest.approx([box["x_mm"] / 1000.0, box["y_mm"] / 1000.0], abs=1e-6)
        assert past[0] * 1000.0 > box["far_mm"]
    # A rung: the same draw but its height, which is the first draw, so the box moves with it.
    assert G.jump_course("over", "heldout", 0, height_mm=(100.0, 100.0))["box"]["height_mm"] == 100.0


def test_the_box_is_the_engines_record_and_a_trainer_pools_it_where_the_engine_stands_it() -> None:
    course = G.jump_course("onto", "train", 7)
    assert course["boxes"] == CadexDynamics.terrain_boxes(
        course["features"], [-1000.0, course["goals_xy_m"][-1][0] * 1000.0 + 1000.0],
        [-course["box"]["across_mm"], course["box"]["across_mm"]])["boxes"]
    record, = course["boxes"]
    assert record["shape"] == "block" and record["top_mm"][0] == pytest.approx(course["box"]["height_mm"])
    pool = T.terrain_pool(np, {"slots": 2, "dome_slots": 0, "scale": 0.001, "pool": [course]})
    placed = CadexDynamics.terrain_box_geoms(course["boxes"], course["lowest_mm"], 2)
    assert np.allclose(pool["pos"][0], placed["pos_m"]) and np.allclose(pool["size"][0], placed["size_m"])
    assert pool["pos"][0][1][2] < -1.0  # the spare slot parked under the plane


def _settle(model, data, seconds=1.5):
    for _ in range(int(seconds / model.opt.timestep)):
        mujoco.mj_step(model, data)


def test_a_trunk_box_lands_on_the_box_top_and_a_paw_meets_its_face() -> None:
    course = G.jump_course("onto", "heldout", 0, height_mm=(120.0, 120.0), offset_mm=0.0)
    box = course["box"]
    model = G.jump_model(mujoco, WORLD, course)
    jump = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "environment/jump/0")
    floor = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "environment/floor")
    assert jump >= 0 and model.geom_contype[jump] == model.geom_contype[floor]
    assert model.geom_conaffinity[jump] == model.geom_conaffinity[floor]

    # The trunk dropped over the box rests on its top, not through it to the plane.
    data = mujoco.MjData(model)
    data.qpos[0:3] = [box["x_mm"] / 1000.0, 0.0, 0.3]
    data.qpos[7:10] = [0.0, 2.0, 0.1]
    _settle(model, data)
    assert data.qpos[2] == pytest.approx(0.12 + 0.03, abs=0.003)
    seen = G.jump_contacts(mujoco, model, data, course)
    assert seen and {c["geom"] for c in seen} == {"trunk/box"} and {c["where"] for c in seen} == {"top"}

    # Beside the box it rests on the plane.
    data = mujoco.MjData(model)
    data.qpos[0:3] = [box["near_mm"] / 1000.0 - 0.5, 0.0, 0.3]
    data.qpos[7:10] = [0.0, 2.0, 0.1]
    _settle(model, data)
    assert data.qpos[2] == pytest.approx(0.03, abs=0.003)
    assert G.jump_contacts(mujoco, model, data, course) == []

    # A paw pressed into the near face at half its height is a face contact.
    data = mujoco.MjData(model)
    data.qpos[0:3] = [box["near_mm"] / 1000.0 - 0.5, 0.0, 0.03]
    data.qpos[7:10] = [box["near_mm"] / 1000.0 - 0.010, 0.0, 0.06]
    mujoco.mj_forward(model, data)
    seen = G.jump_contacts(mujoco, model, data, course)
    assert [c["geom"] for c in seen] == ["paw/sphere"] and seen[0]["where"] == "face"


def test_the_held_out_draws_are_pinned_and_the_race_relief_draws_are_unchanged() -> None:
    assert G.jump_course("over", "heldout", 0)["sha256"] == \
        "a7ea9a5bc038ca748f0197e96d2932c764498a752962f92712a666af1a94ba33"
    assert G.jump_course("onto", "heldout", 0)["sha256"] == \
        "f4385a84aeb2170d735c466df1fe1f7e18cae3980b72510d36738bea5a3ec4e7"
    course = {"kind": "straight", "split": "heldout", "seed": 0, "gates": [{"xy_m": [10.0, 0.0]}]}
    assert G.race_terrain(np, course, "b1")["sha256"] == \
        "c74b6168f7849e7fc910877efc0cb0102fa18b67ec39f92add7b0f48c81cc765"
