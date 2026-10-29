# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The trainer places a pooled course where the engine does (ADR-852), and a
pool of moguls alone keeps its slot axis (ADR-747).

ADR-852 made the engine the one terrain builder: each pooled course carries
its boxes and domes placed, and the trainer only reads them. The parity test
draws two pools through ``CadexDynamics`` itself with every feature kind
(steps, slopes, bumps, platforms, rocks, and since ADR-853 tile patches and
mazes) and holds the trainer's arrays to the
engine's ``terrain_box_geoms`` and ``terrain_dome_geoms``, so the two cannot
drift. No jax: ``terrain_pool`` and the scan are numpy.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Mod" / "cadex"))
import CadexDynamics  # noqa: E402

import cadex_train  # noqa: E402
from cadex_train import height_scan_vector, terrain_pool  # noqa: E402

BUMP = {"x_mm": 2349.3, "y_mm": 3095.2, "top_mm": 73.9, "radius_mm": 667.9}
TERRAIN = {
    "kind": "boxes", "x_range_mm": [-2000.0, 9000.0], "y_range_mm": [-4000.0, 4000.0],
    "lowest_mm": 0.0, "slots": 0, "dome_slots": 2, "scale": 0.001,
    "pool": [{"features": [], "lowest_mm": 0.0, "highest_mm": 73.9, "boxes": [], "domes": [BUMP]}],
}


#: Two pools between them draw every box kind: steps, slopes, bumps,
#: platforms and rocks along x; tile patches and mazes laid out in x and y
#: (ADR-853), which need flat ground the first pool's steps leave no room for.
DECLARED = [
    {"form": "boxes", "x_range_mm": [-2000.0, 9000.0], "y_range_mm": [-2000.0, 2000.0],
     "random": {"seed": 7, "courses": 6, "step_mm": [40.0, 120.0], "grade_deg": [5.0, 15.0],
                "bump_mm": [20.0, 60.0], "bumps": 3, "platform_mm": [80.0, 200.0],
                "rock_mm": [30.0, 60.0]}},
    {"form": "boxes", "x_range_mm": [-2000.0, 9000.0], "y_range_mm": [-2000.0, 2000.0],
     "random": {"seed": 10, "courses": 6, "tile_mm": [40.0, 120.0], "tiles": 2,
                "wall_mm": [300.0, 500.0], "maze_cells": [1, 3]}},
]


def test_the_trainer_places_every_pooled_course_where_the_engine_does():
    for name in ("TERRAIN_BASE_MM", "TERRAIN_PARKED_DEPTH_MM", "TERRAIN_PARKED_HALF_MM"):
        assert getattr(cadex_train, name) == getattr(CadexDynamics, name), name
    terrains = [CadexDynamics.terrain_grid(declared)["descriptor"] for declared in DECLARED]
    pooled = [course for terrain in terrains for course in terrain["pool"]]
    shapes = {box["shape"] for course in pooled for box in course["boxes"]}
    assert shapes == {"block", "ramp", "stone"}, shapes
    assert any(course["domes"] for course in pooled)
    kinds = {feature["kind"] for course in pooled for feature in course["features"]}
    assert kinds == set(CadexDynamics.TERRAIN_FEATURE_KINDS), kinds
    mazes = [feature for course in pooled for feature in course["features"]
             if feature["kind"] == "maze"]
    assert any(maze["cells_x"] > 1 and maze["cells_y"] == 1 for maze in mazes)  # a corridor
    assert any(maze["cells_x"] > 1 and maze["cells_y"] > 1 for maze in mazes)

    for terrain in terrains:
        _hold_pool_to_the_engine(terrain)


def _hold_pool_to_the_engine(terrain):
    pool = terrain_pool(np, terrain)
    for index, course in enumerate(terrain["pool"]):
        lowest = float(course["lowest_mm"])
        boxes = CadexDynamics.terrain_box_geoms(course["boxes"], lowest, terrain["slots"])
        assert np.allclose(pool["plane_z"][index], boxes["plane_z_m"], atol=1e-12)
        assert np.allclose(pool["pos"][index], boxes["pos_m"], atol=1e-12)
        assert np.allclose(pool["quat"][index], boxes["quat"], atol=1e-12)
        assert np.allclose(pool["size"][index], boxes["size_m"], atol=1e-12)
        domes = CadexDynamics.terrain_dome_geoms(course["domes"], lowest, terrain["dome_slots"])
        assert np.allclose(pool["dome_pos"][index], np.reshape(domes["pos_m"], (-1, 3)), atol=1e-12)
        assert np.allclose(pool["dome_size"][index][:, 0], domes["radius_m"], atol=1e-12)

    # The scan reads the ground the engine reads, on each course: across y too,
    # so a maze's walls and a tile patch's rows are crossed.
    task = {"terrain": terrain,
            "scans": [{"body_id": 0, "scale": 1000.0,
                       "offsets_mm": [[x, y] for x in range(-1500, 8500, 250)
                                      for y in range(-1900, 2000, 190)]}]}
    xpos, xmat = np.zeros((1, 1, 3)), np.eye(3).reshape(1, 1, 9)
    for index, course in enumerate(terrain["pool"]):
        placed = (pool["scan"][[index]], pool["lowest"][[index]], pool["dome_scan"][[index]])
        scan = height_scan_vector(np, task, xpos, xmat, course=placed)[0]
        ground = [CadexDynamics.terrain_box_ground_mm(course, x, y)
                  for x, y in task["scans"][0]["offsets_mm"]]
        assert np.allclose(-scan, ground, atol=1e-6), index


def test_a_course_of_moguls_alone_keeps_its_slot_axis_and_scans_its_dome():
    pool = terrain_pool(np, TERRAIN)
    assert pool["pos"].shape == (1, 0, 3)
    assert pool["quat"].shape == (1, 0, 4)
    assert pool["scan"].shape == (1, 0, 15)
    assert pool["dome_scan"].shape == (1, 2, 4)

    task = {"terrain": TERRAIN,
            "scans": [{"body_id": 0, "scale": 1000.0, "offsets_mm": [[0.0, 0.0], [0.0, -1000.0]]}]}
    xpos = np.asarray([[[BUMP["x_mm"] / 1000.0, BUMP["y_mm"] / 1000.0, 0.5]]])
    xmat = np.eye(3).reshape(1, 1, 9)
    course = (pool["scan"][[0]], pool["lowest"][[0]], pool["dome_scan"][[0]])
    scan = height_scan_vector(np, task, xpos, xmat, course=course)
    # Over the dome's peak, then a metre off it on the plane.
    assert np.allclose(scan[0], [500.0 - BUMP["top_mm"], 500.0], atol=1e-6)
