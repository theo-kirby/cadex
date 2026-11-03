# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-977: ``--relief-span`` lays a training strip's obstacles across its full width, walled.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_sprint_span.py`` from the repo.
"""

from __future__ import annotations

from collections import deque

import numpy as np
import pytest

import cadex_goto as G
import cadex_train as T

WALL = 400.0


def reachable(heights: np.ndarray, start: tuple[int, int], below: float) -> np.ndarray:
    """Every grid cell an 8-connected walk from ``start`` reaches over cells under ``below`` mm."""

    seen = np.zeros(heights.shape, dtype=bool)
    seen[start] = True
    queue = deque([start])
    nrow, ncol = heights.shape
    while queue:
        r, c = queue.popleft()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if 0 <= rr < nrow and 0 <= cc < ncol and not seen[rr, cc] and heights[rr, cc] < below:
                    seen[rr, cc] = True
                    queue.append((rr, cc))
    return seen


def start_cell(strip: dict) -> tuple[int, int]:
    cell = strip["cell_mm"]
    return int(round(-strip["y_range_mm"][0] / cell)), int(round(-strip["x_range_mm"][0] / cell))


@pytest.mark.parametrize("seed", [0, 3, 11])
def test_a_spanned_strip_has_no_way_round_its_first_obstacle(seed: int) -> None:
    """On a ``boxes`` strip (obstacles on the plane, b1's draws) a walk from the
    start over anything lower than the lowest box never passes the first
    obstacle's near side, never reaches the grid's edge (the rim walls), and so
    never reaches the plane beyond the grid; without the span it goes round."""

    low = float(G.RACE_TERRAIN["box_mm"][0])
    spanned = G.strip_terrain(np, "boxes", seed, length_m=30.0, span_wall_mm=WALL)
    first = min(o["centre_mm"][0] for o in spanned["drawn"]["obstacles"])
    seen = reachable(spanned["heights_mm"], start_cell(spanned), low)
    gx = spanned["x_range_mm"][0] + spanned["cell_mm"] * np.arange(spanned["ncol"])
    assert not seen[:, gx >= first].any()
    assert not (seen[0, :].any() or seen[-1, :].any() or seen[:, 0].any() or seen[:, -1].any())
    assert spanned["drawn"]["span_wall_mm"] == WALL and spanned["highest_mm"] == WALL
    # The same draw unspanned leaves a way past every obstacle to the far end.
    open_ = G.strip_terrain(np, "boxes", seed, length_m=30.0)
    seen = reachable(open_["heights_mm"], start_cell(open_), low)
    assert seen[:, -1].any()


def test_every_spanned_obstacle_crosses_every_row_of_the_grid() -> None:
    """Each obstacle's own top stands in every row of the grid (b1 and boxes
    share the obstacles' draws, so b1's are as wide), turned or not."""

    boxes = G.strip_terrain(np, "boxes", 5, length_m=60.0, span_wall_mm=WALL)
    b1 = G.strip_terrain(np, "b1", 5, length_m=60.0, span_wall_mm=WALL)
    assert boxes["drawn"]["obstacles"] == b1["drawn"]["obstacles"]
    assert np.all(b1["heights_mm"] >= boxes["heights_mm"] - 1e-6)
    heights, cell = boxes["heights_mm"], boxes["cell_mm"]
    rim = int(round(boxes["drawn"]["span_rim_mm"] / cell))
    gx = boxes["x_range_mm"][0] + cell * np.arange(boxes["ncol"])
    turned = 0
    for o in boxes["drawn"]["obstacles"]:
        assert o["centre_mm"][1] == 0.0
        turned += abs(o["yaw_deg"]) > 5.0
        reach = 0.5 * o["along_mm"] + o["across_mm"] * abs(np.sin(np.radians(o["yaw_deg"])))
        near = np.abs(gx - o["centre_mm"][0]) <= reach
        band = heights[rim:-rim][:, near]
        assert np.all((band >= o["height_mm"] - 1e-6).any(axis=1)), o
    assert turned > 0


def test_a_spanned_strip_keeps_the_strips_draws() -> None:
    """Spanning changes the across, the offset and the clearing's test, not
    the draws: the obstacles past the clearing are the strip's own, leg for
    leg, in kind, place along, along-side, turn and height."""

    for kind, seed in (("b1", 7), ("boxes", 2)):
        plain = {o["leg"]: o for o in G.strip_terrain(np, kind, seed, length_m=60.0)["drawn"]["obstacles"]}
        spanned = G.strip_terrain(np, kind, seed, length_m=60.0, span_wall_mm=WALL)["drawn"]["obstacles"]
        assert len(spanned) >= len(plain) - 1
        width = 2000.0 * G.RACE_TERRAIN["margin_m"]
        for o in spanned:
            p = plain[o["leg"]]
            for key in ("kind", "along_mm", "yaw_deg", "height_mm"):
                assert o[key] == p[key]
            assert abs(o["centre_mm"][0] - p["centre_mm"][0]) <= G.RACE_TERRAIN["obstacle_offset_mm"] * 0.35
            assert o["across_mm"] >= width


def test_held_out_and_earlier_draws_are_unchanged_to_the_digest() -> None:
    """The judge's held-out strips and straight strips, and a training strip
    without the span, are what they were before ADR-977."""

    def heldout(course: str, seed: int) -> str:
        return G.race_terrain(np, {"kind": course, "split": "heldout", "seed": seed,
                                   "gates": [{"xy_m": [125.0, 0.0]}]}, "b1")["sha256"]

    assert heldout("strip", 0).startswith("500f7208bff601b4")
    assert heldout("strip", 9).startswith("ed70de6f4f5bbcb6")
    assert heldout("straight", 0).startswith("09d30ea9c831f66d")
    assert G.strip_terrain(np, "b1", 7, length_m=60.0)["sha256"].startswith("47d6c41d5d186c9b")
    assert G.strip_terrain(np, "boxes", 2, length_m=30.0)["sha256"].startswith("a70c9c3364f37113")
    assert G.race_terrain(np, G.gate_course(0, split="heldout"), "b1")["sha256"].startswith("d828152bfdcd2e74")


def test_the_span_is_a_strips_alone() -> None:
    with pytest.raises(SystemExit):
        G.field_terrain(np, "b1", 1, half_m=5.0, span_wall_mm=WALL)
    with pytest.raises(SystemExit):
        G.race_terrain(np, G.gate_course(0, split="train"), "b1", span_wall_mm=WALL)
    with pytest.raises(SystemExit):
        G.strip_terrain(np, "b1", 1, length_m=10.0, span_wall_mm=0.0)


def options(*extra: str):
    return T.arguments(["bundle.json", "--out", "x.cxpolicy", "--relief-strip", "12", *extra])


def test_the_trainer_spans_its_strips_only_when_asked() -> None:
    rule = T.relief_rule(options("--race-terrain", "b1", "--relief-span", "400"))
    assert rule["span_wall_mm"] == 400.0 and rule["strip_m"] == 12.0
    assert "span_wall_mm" not in T.relief_rule(options("--race-terrain", "b1"))
    with pytest.raises(SystemExit):
        T.relief_rule(options("--race-terrain", "u1", "--relief-span", "400"))
    with pytest.raises(SystemExit):
        T.relief_rule(options("--race-terrain", "b1", "--relief-span", "-1"))
    with pytest.raises(SystemExit):
        T.relief_rule(T.arguments(["bundle.json", "--out", "x.cxpolicy", "--gates", "--race-terrain", "b1",
                                   "--relief-span", "400"]))
    fields = T.relief_fields(np, {**rule, "levels": 4, "fields": "graded-rough"}, 3)
    # Level 1 is rough relief alone (no obstacles, nothing to span); levels 2-4 are spanned and walled.
    assert "span_wall_mm" not in fields[0]["drawn"]
    for field in fields[1:]:
        assert field["drawn"]["span_wall_mm"] == 400.0 and field["highest_mm"] >= 400.0
        heights = field["heights_mm"]
        assert min(heights[0].min(), heights[-1].min(), heights[:, 0].min()) >= 400.0
        assert all(o["across_mm"] >= 6000.0 for o in field["drawn"]["obstacles"])
    plain = T.relief_fields(np, {**T.relief_rule(options("--race-terrain", "b1")),
                                 "levels": 4, "fields": "graded-rough"}, 3)
    assert [f["drawn"]["obstacles"][0]["height_mm"] for f in plain[1:]] == \
        [f["drawn"]["obstacles"][0]["height_mm"] for f in fields[1:]]
