# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-747: a drawn box course of moguls alone has no box slots, and the pool
keeps its slot axis, so the height scan reads the domes.

orun8's G3 probe found it: a pool drawn with only ``bump_mm`` built ``scan``
as ``(P, 0)`` rather than ``(P, 0, 15)``, and the jitted scan indexed past it.
No jax: the scan is the same function in numpy.
"""

from __future__ import annotations

import numpy as np

from cadex_train import height_scan_vector, terrain_pool

BUMP = {"kind": "bump", "height_mm": 73.9, "radius_mm": 304.9, "x_mm": 2349.3, "y_mm": 3095.2}
TERRAIN = {
    "kind": "boxes", "x_range_mm": [-2000.0, 9000.0], "y_range_mm": [-4000.0, 4000.0],
    "lowest_mm": 0.0, "slots": 0, "dome_slots": 2, "scale": 0.001,
    "pool": [{"features": [BUMP], "lowest_mm": 0.0, "highest_mm": 73.9, "boxes": 0, "domes": 1}],
}


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
    assert np.allclose(scan[0], [500.0 - BUMP["height_mm"], 500.0], atol=1e-6)
