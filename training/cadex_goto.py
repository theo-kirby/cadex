# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Go-to-point: one seeded source of point sequences, and the layer that walks them (ADR-839).

A go-to-point episode is a sequence of points on the floor. Each point has a
commanded speed (its band: walk, run) and a hold. The robot goes to the
current point, holds there for the hold's seconds, and then the next point
lights. A point is reached when the base comes within ``arrive_m`` of it, and
the next one appears on arrival or when the hold ends, never on a clock.

Route A of ADR-839 drives a velocity-command policy through a scripted layer.
The layer reads the base's planar pose and turns the current point into the
policy's command: forward, lateral and yaw rate. When the point is behind or
to the side the robot turns in place, then walks; it slows as it closes; it
holds by small position corrections.

This module is the one source both halves use. Training (G2) stacks
:func:`sequence` draws with :func:`stack` and steps :func:`layer_step` in
JAX. The judge plays a policy on stock MuJoCo through the same
:func:`layer_step` in numpy (``play``). Sequences are seeded per split, so a
held-out sequence is never one training drew.

    python training/cadex_goto.py sequence --seed 0 --split heldout --bands walk:0.4-0.7,run:1.0-1.5
    python training/cadex_goto.py play POLICY --task outputs/T-task.json --seed 0 \\
        --split heldout --bands walk:0.4-0.7,run:1.0-1.5 --goals cx,cy,cw

``play --course COURSE.json`` stands a held-out box course in the model's
terrain slots first (ADR-858), and judges a fall by the height over its ground.
``play --sequence SEQ.json`` plays a given sequence in place of a seeded draw,
such as :func:`maze_route`'s way through a maze; a course whose ``walls`` name
its wall slots is judged on whether any body of the robot entered one (ADR-860).

``play`` writes the episode as a ``view/`` beside the policy (ADR-835),
with each frame's goto state, so the dashboard plays it with its points drawn.
It also writes ``goto.json``, the episode's readings against G2's thresholds.

Standard library at module scope (ADR-084); numpy and mujoco only inside ``play``.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Mapping, Sequence

GOTO_SCHEMA = "cadex-goto-sequence-v1"
EPISODE_SCHEMA = "cadex-goto-episode-v1"
SPLITS = ("train", "heldout")
#: Where a point lies against the leg that led to it: bearing ranges in degrees.
BEARINGS = {"ahead": (-30.0, 30.0), "side": (60.0, 120.0), "behind": (150.0, 210.0)}

#: The sequence's shape when the caller names none.
#: ``lead_s`` lengthens each leg by its speed times that many seconds, so a run
#: leg, like a walk leg, has a straight second at full speed to read (ADR-840).
SEQUENCE = {"points": 8, "behind": 2, "side": 2, "distance_m": (2.0, 5.0), "lead_s": 2.5,
            "holds": 2, "hold_share": 0.5, "hold_s": (1.0, 3.0)}

#: The layer's gains and radii. ``arrive_m`` is under G2's 0.3 m reach bar; a
#: point with a hold is arrived on only within ``hold_arrive_m``, so the hold
#: starts inside its 0.15 m bar; ``settle_m`` is the hold's dead band.
#: A point more than ``turn_deg`` off the heading is turned to in place, and a
#: turn in place goes on until the point is within ``face_deg``: with one
#: threshold the orun9 biped chattered at 60 deg, its step-off yawing it back
#: out of the cone each time, and stood turning for 200 s (ADR-865).
LAYER = {"arrive_m": 0.25, "hold_arrive_m": 0.1, "turn_deg": 60.0, "face_deg": 30.0, "yaw_gain": 2.0,
         "approach_gain": 1.0, "approach_min": 0.25, "hold_gain": 1.5, "hold_max": 0.3, "settle_m": 0.05}

#: G2's pass bar (the charter): reach, hold, and speed tracking on straight legs.
JUDGE = {"reach_m": 0.3, "hold_m": 0.15, "speed_tolerance": 0.15,
         "straight_deg": 10.0, "straight_settle_s": 0.5, "straight_min_s": 1.0,
         "fall_up_z": 0.5, "fall_height_share": 0.5}


def parse_bands(text: str) -> list[dict[str, Any]]:
    """``walk:0.4-0.7,run:1.0-1.5`` as speed bands, in m/s."""

    bands = []
    for item in str(text).split(","):
        name, _, span = item.partition(":")
        low, _, high = span.partition("-")
        try:
            band = {"name": name.strip(), "low": float(low), "high": float(high)}
        except ValueError:
            raise SystemExit(f"--bands: {item!r} is not NAME:LOW-HIGH") from None
        if not band["name"] or not 0.0 < band["low"] <= band["high"]:
            raise SystemExit(f"--bands: {item!r} needs a name and 0 < LOW <= HIGH")
        bands.append(band)
    return bands


def sequence(seed: int, *, split: str, bands: Sequence[Mapping[str, Any]],
             **shape: Any) -> dict[str, Any]:
    """One seeded go-to-point sequence, the same on every machine.

    The robot starts at the origin facing +x. Each point is placed against
    the direction of the leg before it: ahead, to a side, or behind
    (:data:`BEARINGS`), at a distance in ``distance_m`` plus ``lead_s``
    seconds at its speed. At least ``behind``
    points are behind and ``side`` to a side; the rest are drawn from all
    three. Each point's band is drawn uniformly, its speed uniformly inside the
    band, and at least ``holds`` points carry a hold in ``hold_s`` (each other
    one with chance ``hold_share``). The draw is seeded by ``(split, seed)``,
    so the ``train`` and ``heldout`` splits never share a sequence.
    """

    if split not in SPLITS:
        raise SystemExit(f"split {split!r} is not one of {SPLITS}")
    if not bands:
        raise SystemExit("a sequence needs at least one speed band")
    options = {**SEQUENCE, **shape}
    count = int(options["points"])
    if options["behind"] + options["side"] > count or options["holds"] > count:
        raise SystemExit(f"{count} points cannot hold {options['behind']} behind, "
                         f"{options['side']} to a side and {options['holds']} holds")
    rng = random.Random(f"cadex-goto:{split}:{int(seed)}")
    kinds = ["behind"] * int(options["behind"]) + ["side"] * int(options["side"])
    kinds += [rng.choice(sorted(BEARINGS)) for _ in range(count - len(kinds))]
    rng.shuffle(kinds)
    held = set(rng.sample(range(count), int(options["holds"])))
    x = y = 0.0
    heading = 0.0
    points = []
    for index, kind in enumerate(kinds):
        low, high = BEARINGS[kind]
        turn = math.radians(rng.uniform(low, high))
        if kind == "side" and rng.random() < 0.5:
            turn = -turn
        heading = math.atan2(math.sin(heading + turn), math.cos(heading + turn))
        distance = rng.uniform(*options["distance_m"])
        band = bands[rng.randrange(len(bands))]
        speed = rng.uniform(float(band["low"]), float(band["high"]))
        distance += speed * float(options["lead_s"])
        x, y = x + distance * math.cos(heading), y + distance * math.sin(heading)
        hold = rng.uniform(*options["hold_s"]) if index in held or rng.random() < options["hold_share"] else 0.0
        points.append({"xy_m": [round(x, 4), round(y, 4)], "speed_mps": round(speed, 3),
                       "hold_s": round(hold, 2), "band": str(band["name"]), "bearing": kind})
    return {"schema": GOTO_SCHEMA, "split": split, "seed": int(seed),
            "bands": [dict(band) for band in bands],
            "shape": {key: list(value) if isinstance(value, tuple) else value
                      for key, value in options.items()},
            "points": points}


#: A maze route's shape (ADR-860): the lead point stands ``lead_cells`` cells
#: out from a door, so the robot lines up before it enters; a cell where the
#: way turns carries ``corner_hold_s``, so the layer arrives within its
#: ``hold_arrive_m`` and the robot turns at the cell's centre; ``clear_m`` is how
#: far an approach leg keeps from every wall.
MAZE = {"lead_cells": 2.0, "corner_hold_s": 0.3, "clear_m": 0.4}


def _covered(walls: Sequence[Any], x: float, y: float) -> bool:
    return any(xs[0] <= x <= xs[1] and ys[0] <= y <= ys[1] for xs, ys, _top in walls)


def _leg_clear(walls: Sequence[Any], a: Sequence[float], b: Sequence[float], clear_mm: float) -> bool:
    steps = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 50.0))
    for k in range(steps + 1):
        x, y = a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps
        if any(xs[0] - clear_mm <= x <= xs[1] + clear_mm and ys[0] - clear_mm <= y <= ys[1] + clear_mm
               for xs, ys, _top in walls):
            return False
    return True


def maze_route(maze: Mapping[str, Any], walls: Sequence[Any], seed: int, *, split: str,
               bands: Sequence[Mapping[str, Any]], **shape: Any) -> dict[str, Any]:
    """A go-to-point sequence through a maze and back (ADR-860), seeded by ``(split, seed)``.

    ``maze`` is the engine's maze feature (``x_mm``, ``y_mm``, ``cells_x``,
    ``cells_y``, ``cell_mm``) and ``walls`` its blocks as
    ``CadexDynamics.terrain_maze_walls`` returns them: ``(x range, y range,
    top)`` in mm. The doors are the outer cells whose -x or +x edge no wall
    covers, the way the shortest path over cell edges no wall covers. From the
    origin the robot goes to a lead point ``lead_cells`` out from the nearer
    door, by a corner if the straight leg passes within ``clear_m`` of a wall;
    then each cell's centre to the far door, a lead point outside it held, and
    the same way back to the first lead point, held. Inside the maze every
    point is at the slowest band's speed; the leads take any band.
    """

    if split not in SPLITS:
        raise SystemExit(f"split {split!r} is not one of {SPLITS}")
    if not bands:
        raise SystemExit("a sequence needs at least one speed band")
    options = {**MAZE, **{k: v for k, v in SEQUENCE.items() if k == "hold_s"}, **shape}
    rng = random.Random(f"cadex-goto-maze:{split}:{int(seed)}")
    cell = float(maze["cell_mm"])
    nx, ny = int(maze["cells_x"]), int(maze["cells_y"])
    x0, y0 = float(maze["x_mm"]) - nx * cell / 2.0, float(maze["y_mm"]) - ny * cell / 2.0

    def centre(i: float, j: float) -> tuple[float, float]:
        return x0 + (i + 0.5) * cell, y0 + (j + 0.5) * cell

    doors = {side: [j for j in range(ny) if not _covered(walls, x0 + edge * cell, centre(0, j)[1])]
             for side, edge in (("-x", 0), ("+x", nx))}
    if len(doors["-x"]) != 1 or len(doors["+x"]) != 1:
        raise SystemExit(f"the maze at {maze['x_mm']:g}, {maze['y_mm']:g} mm has doors {doors}, "
                         "not one each side")
    ends = {"-x": (0, doors["-x"][0]), "+x": (nx - 1, doors["+x"][0])}
    near = min(ends, key=lambda side: math.hypot(*centre(*ends[side])))
    far = "+x" if near == "-x" else "-x"
    start, goal = ends[near], ends[far]
    before = {start: start}
    queue = [start]
    while queue:
        i, j = queue.pop(0)
        for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            k = (i + di, j + dj)
            if not (0 <= k[0] < nx and 0 <= k[1] < ny) or k in before:
                continue
            (cx, cy), (kx, ky) = centre(i, j), centre(*k)
            if not _covered(walls, (cx + kx) / 2.0, (cy + ky) / 2.0):
                before[k] = (i, j)
                queue.append(k)
    if goal not in before:
        raise SystemExit("the maze has no way between its doors")
    way = [goal]
    while way[-1] != start:
        way.append(before[way[-1]])
    way.reverse()
    out = float(options["lead_cells"])
    lead_near = centre(start[0] - out if near == "-x" else start[0] + out, start[1])
    lead_far = centre(goal[0] + out if far == "+x" else goal[0] - out, goal[1])
    clear = 1000.0 * float(options["clear_m"])
    route: list[tuple[tuple[float, float], str]] = []
    if not _leg_clear(walls, (0.0, 0.0), lead_near, clear):
        corners = [c for c in ((lead_near[0], 0.0), (0.0, lead_near[1]))
                   if _leg_clear(walls, (0.0, 0.0), c, clear) and _leg_clear(walls, c, lead_near, clear)]
        if not corners:
            raise SystemExit("no straight or one-corner approach to the maze clears its walls")
        route.append((corners[0], "lead"))
    route.append((lead_near, "lead"))
    # The way's ends run on through the doors to the lead points, so a door
    # cell the way turns in is a corner too.
    ends_out = [(start[0] - 1 if near == "-x" else start[0] + 1, start[1]), *way,
                (goal[0] + 1 if far == "+x" else goal[0] - 1, goal[1])]
    turns = {ends_out[k] for k in range(1, len(ends_out) - 1)
             if (ends_out[k][0] - ends_out[k - 1][0], ends_out[k][1] - ends_out[k - 1][1])
             != (ends_out[k + 1][0] - ends_out[k][0], ends_out[k + 1][1] - ends_out[k][1])}
    inside = [(centre(*c), "corner" if c in turns else "cell") for c in way]
    route += inside + [(lead_far, "held")] + inside[::-1] + [(lead_near, "held")]
    slow = min(bands, key=lambda band: float(band["low"]))
    points, x, y, heading = [], 0.0, 0.0, 0.0
    for (px, py), role in route:
        px, py = px / 1000.0, py / 1000.0
        leg = math.atan2(py - y, px - x)
        turn = abs(math.degrees(math.atan2(math.sin(leg - heading), math.cos(leg - heading))))
        bearing = "ahead" if turn < 45.0 else "side" if turn < 135.0 else "behind"
        band = bands[rng.randrange(len(bands))] if role in ("lead", "held") else slow
        speed = rng.uniform(float(band["low"]), float(band["high"]))
        hold = (rng.uniform(*options["hold_s"]) if role == "held"
                else float(options["corner_hold_s"]) if role == "corner" else 0.0)
        points.append({"xy_m": [round(px, 4), round(py, 4)], "speed_mps": round(speed, 3),
                       "hold_s": round(hold, 2), "band": str(band["name"]), "bearing": bearing,
                       "role": role})
        x, y, heading = px, py, leg
    return {"schema": GOTO_SCHEMA, "split": split, "seed": int(seed), "route": "maze",
            "bands": [dict(band) for band in bands],
            "shape": {key: list(value) if isinstance(value, tuple) else value
                      for key, value in options.items()},
            "maze": {key: maze[key] for key in ("x_mm", "y_mm", "cells_x", "cells_y", "cell_mm", "height_mm")
                     if key in maze},
            "points": points}


def stack(np: Any, sequences: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Sequences of equal length as the layer's plan: ``points (B, N, 2)``, ``speeds``, ``holds (B, N)``."""

    lengths = {len(s["points"]) for s in sequences}
    if len(lengths) != 1:
        raise SystemExit(f"sequences of different lengths {sorted(lengths)} cannot be stacked")
    return {"points": np.asarray([[p["xy_m"] for p in s["points"]] for s in sequences], dtype=np.float32),
            "speeds": np.asarray([[p["speed_mps"] for p in s["points"]] for s in sequences], dtype=np.float32),
            "holds": np.asarray([[p["hold_s"] for p in s["points"]] for s in sequences], dtype=np.float32)}


def layer_start(xp: Any, batch: Sequence[int]) -> dict[str, Any]:
    """The layer's state at an episode's start: the first point lit, nothing held."""

    return {"index": xp.zeros(tuple(batch), dtype=xp.int32),
            "held_s": xp.zeros(tuple(batch), dtype=xp.float32),
            "arrived": xp.zeros(tuple(batch), dtype=bool),
            "turning": xp.zeros(tuple(batch), dtype=bool)}


def _current(xp: Any, plan: Mapping[str, Any], index: Any) -> tuple[Any, Any, Any]:
    last = plan["speeds"].shape[-1] - 1
    at = xp.minimum(index, last)[..., None]
    point = xp.take_along_axis(plan["points"], at[..., None], axis=-2)[..., 0, :]
    speed = xp.take_along_axis(plan["speeds"], at, axis=-1)[..., 0]
    hold = xp.take_along_axis(plan["holds"], at, axis=-1)[..., 0]
    return point, speed, hold


def layer_step(xp: Any, plan: Mapping[str, Any], state: Mapping[str, Any], x: Any, y: Any,
               yaw: Any, dt: float, limits: Mapping[str, Sequence[float]],
               gains: Mapping[str, float] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """One control step: the state moved on, then the command for the point now lit.

    ``x``, ``y`` (m) and ``yaw`` (rad) are the base's planar pose, batched as
    the state is. ``limits`` gives the policy's command ranges, ``vx``, ``vy``
    (m/s) and ``wz`` (rad/s), each ``[low, high]``. Returns the new state and
    ``{"vx", "vy", "wz"}``. Every branch is an ``xp.where``, so the same code
    runs in numpy and in jitted JAX. Once every point is done the command is
    zero.
    """

    g = {**LAYER, **(gains or {})}
    count = plan["speeds"].shape[-1]
    index, held, arrived = state["index"], state["held_s"], state["arrived"]
    point, _speed, hold = _current(xp, plan, index)
    finished = index >= count
    radius = xp.where(hold > 0, g["hold_arrive_m"], g["arrive_m"])
    near = xp.hypot(point[..., 0] - x, point[..., 1] - y) < radius
    arrived = (arrived | near) & ~finished
    held = xp.where(arrived, held + dt, 0.0)
    advance = arrived & (held >= hold)
    index = index + advance.astype(index.dtype)
    arrived = arrived & ~advance
    held = xp.where(advance, 0.0, held)
    new = {"index": index, "held_s": held.astype(state["held_s"].dtype), "arrived": arrived}

    point, speed, _hold = _current(xp, plan, index)
    dx, dy = point[..., 0] - x, point[..., 1] - y
    cos, sin = xp.cos(yaw), xp.sin(yaw)
    ex, ey = cos * dx + sin * dy, -sin * dx + cos * dy
    distance = xp.hypot(ex, ey)
    bearing = xp.arctan2(ey, ex)
    pace = xp.minimum(speed, xp.maximum(g["approach_gain"] * distance, g["approach_min"]))
    off = xp.abs(bearing)
    turning = xp.where(state["turning"], off > math.radians(g["face_deg"]), off >= math.radians(g["turn_deg"]))
    turning = turning & ~arrived & ~(index >= count)
    new["turning"] = turning
    facing = ~turning
    travel_vx = xp.where(facing, pace * xp.cos(bearing), 0.0)
    travel_vy = xp.where(facing, pace * xp.sin(bearing), 0.0)
    travel_wz = g["yaw_gain"] * bearing
    settle = xp.where(distance > g["settle_m"], g["hold_gain"], 0.0)
    hold_vx = xp.clip(settle * ex, -g["hold_max"], g["hold_max"])
    hold_vy = xp.clip(settle * ey, -g["hold_max"], g["hold_max"])
    done = index >= count
    vx = xp.where(done, 0.0, xp.where(arrived, hold_vx, travel_vx))
    vy = xp.where(done, 0.0, xp.where(arrived, hold_vy, travel_vy))
    wz = xp.where(done | arrived, 0.0, travel_wz)
    command = {"vx": xp.clip(vx, *limits["vx"]), "vy": xp.clip(vy, *limits["vy"]),
               "wz": xp.clip(wz, *limits["wz"])}
    return new, command


def played_filter_alpha(header: Mapping[str, Any]) -> float:
    """The action filter a policy was trained with, from its header (ADR-160, ADR-953).

    1.0 is no filter. A command slew (ADR-162) is refused: this player does not
    play one, and a policy trained under one would be judged without it.
    """

    training = header.get("training") or {}
    if float(training.get("command_slew_deg", 0.0) or 0.0):
        raise SystemExit("this player plays no command slew")
    alpha = float(training.get("action_filter_alpha", 1.0))
    if not 0.0 < alpha <= 1.0:
        raise SystemExit(f"action_filter_alpha {alpha!r} is outside (0, 1]")
    return alpha


class Player:
    """A ``.cxpolicy`` played on its bundle's model as the engine plays one, in numpy.

    The header's channels come from sensordata at the bundle's ``adr`` and
    ``scale``, the goal channels from the layer, and the previous two issued
    commands (and their rate). Then ``(x - mean) / std``, the MLP,
    ``tanh * output_scale + output_bias``, the bundle's clamp and scale into
    ctrl. A height scan the actor reads (ADR-748) is the base's height over
    :attr:`ground` at each of its points, turned by its heading, as
    ``CadexDynamics.height_scan_values`` reads it (ADR-859); ``ground`` is the
    bundle's box course, or the plane, until ``play --course`` stands another.
    A channel with no source here (contacts, trackers) is refused.
    """

    def __init__(self, policy_path: Path, task_path: Path, goals: Sequence[str],
                 other_model: bool = False) -> None:
        import hashlib

        import mujoco
        import numpy as np

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import cadex_train

        self.np, self.mujoco = np, mujoco
        container = cadex_train.decode_policy(policy_path.read_bytes(), context=str(policy_path))
        header = container["header"]
        task = json.loads(task_path.read_text(encoding="utf-8"))
        xml = cadex_train._bundle_model_bytes(task_path.resolve(), task)
        if xml is None:
            raise SystemExit(f"the model {task['model']['path']!r} is not beside {task_path}")
        # ``other_model`` plays a policy on a model it did not train on, by
        # channel name: a cut's policy on its export (RECIPE.md §R.9, ADR-865).
        self.trained_on = str(header["model"]["sha256"])
        if hashlib.sha256(xml).hexdigest() != self.trained_on and not other_model:
            raise SystemExit("the policy was not trained on this bundle's model (--other-model plays it by name)")
        self.filter_alpha = played_filter_alpha(header)
        self.filtered_command = cadex_train.filtered_command
        self.task, self.model_xml = task, xml
        self.model = mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
        episode = task["episode"]
        self.substeps = int(episode["solver_steps_per_action"])
        self.dt = float(episode["control_interval_s"])
        self.home = np.array(self.model.keyframe(episode["reset_keyframe"]).qpos)
        free = [j for j in range(self.model.njnt) if int(self.model.jnt_type[j]) == 0]
        if not free:
            raise SystemExit("go-to-point needs a floating base; this model has no free joint")
        self.base = int(self.model.jnt_bodyid[free[0]])
        self.sensor = {}
        for row in task["observations"]:
            if row.get("contact") or row.get("tracker") or row.get("load"):
                continue
            for i, channel in enumerate(row["channels"]):
                self.sensor[channel] = (int(row["adr"]) + i, float(row["scale"]))
        actions = task["actions"]
        self.low = np.array([a["low"] for a in actions])
        self.high = np.array([a["high"] for a in actions])
        self.ctrl_scale = np.array([a["scale"] for a in actions])
        self.ctrl_index = np.array([a["index"] for a in actions])
        key = self.model.keyframe(episode["reset_keyframe"])
        self.reset_command = np.clip(np.array(key.ctrl)[self.ctrl_index] / self.ctrl_scale, self.low, self.high)
        self.command_names = {r["channels"][0]: int(r["action"]) for r in task.get("commands") or ()}
        declared = {str(g["name"]): g for g in task.get("goal") or ()}
        if len(goals) != 3 or any(name not in declared for name in goals):
            raise SystemExit(f"--goals names the forward, lateral and yaw-rate goals; "
                             f"this task declares {sorted(declared)}")
        self.goals = list(goals)
        # The policy's command units: mm/s for speeds, deg/s for the yaw rate.
        unit = {"mm/s": 1000.0, "m/s": 1.0, "deg/s": math.degrees(1.0), "rad/s": 1.0}
        self.goal_scale = []
        for name in goals:
            if declared[name].get("unit") not in unit:
                raise SystemExit(f"goal {name!r}: unit {declared[name].get('unit')!r} is not a speed or a rate")
            self.goal_scale.append(unit[declared[name]["unit"]])
        self.limits = {axis: [float(declared[name]["low"]) / s, float(declared[name]["high"]) / s]
                       for axis, name, s in zip(("vx", "vy", "wz"), goals, self.goal_scale)}
        network = header["network"]
        if network["activation"] != "swish" or network["output"] != "tanh":
            raise SystemExit("this player plays swish networks with a tanh output")
        weights = np.asarray(container["weights"], dtype=np.float64)
        self.layers, cursor = [], 0
        for n_in, n_out in network["layers"]:
            w = weights[cursor:cursor + n_in * n_out].reshape(n_in, n_out)
            cursor += n_in * n_out
            self.layers.append((w, weights[cursor:cursor + n_out]))
            cursor += n_out
        self.out_scale, self.out_bias = np.array(network["output_scale"]), np.array(network["output_bias"])
        self.mean = np.array(header["normaliser"]["mean"])
        self.std = np.array(header["normaliser"]["std"])
        self.channels = list(header["observations"])
        self.scans = [row for row in task.get("scans") or ()
                      if set(row["channels"]) & set(self.channels)]
        scanned = {channel for row in self.scans for channel in row["channels"]}
        terrain = task.get("terrain") or {}
        self.ground = (course_ground(np, terrain) if terrain.get("kind") == "boxes"
                       else (lambda x_mm, y_mm: 0.0))
        for channel in self.channels:
            if not (channel in self.sensor or channel in self.goals or channel in self.command_names
                    or channel in scanned
                    or (channel.endswith("_rate") and channel[:-5] in self.command_names)):
                raise SystemExit(f"channel {channel!r}: no source in this player")
        witness = header["evaluation"]
        error = max(float(np.abs(self._act(np.array(o)) - np.array(a)).max())
                    for o, a in zip(witness["observations"], witness["actions"]))
        if error > 1e-4:
            raise SystemExit(f"the forward pass disagrees with the policy's witness by {error}")
        self.witness_error = error

    def _act(self, values: Any) -> Any:
        np = self.np
        x = (values - self.mean) / self.std
        for k, (w, b) in enumerate(self.layers):
            x = x @ w + b
            if k < len(self.layers) - 1:
                x = x / (1.0 + np.exp(-x))
        return np.tanh(x) * self.out_scale + self.out_bias

    def reset(self) -> None:
        self.issued = self.reset_command.copy()
        self.before = self.reset_command.copy()
        self.first = True

    def control(self, data: Any, command: Sequence[float]) -> Any:
        goal = {name: float(value) * scale for name, value, scale in zip(self.goals, command, self.goal_scale)}
        values = []
        heights = {}
        for row in self.scans:
            body = int(row["body_id"])
            x, y, z = (float(v) * float(row["scale"]) for v in data.xpos[body])
            R = data.xmat[body]
            norm = math.hypot(R[0], R[3])
            cos, sin = (R[0] / norm, R[3] / norm) if norm > 1e-9 else (1.0, 0.0)
            for (ahead, left), channel in zip(row["offsets_mm"], row["channels"]):
                heights[channel] = z - self.ground(x + cos * ahead - sin * left,
                                                   y + sin * ahead + cos * left)
        for channel in self.channels:
            if channel in heights:
                values.append(heights[channel])
            elif channel in self.sensor:
                adr, scale = self.sensor[channel]
                values.append(data.sensordata[adr] * scale)
            elif channel in goal:
                values.append(goal[channel])
            elif channel in self.command_names:
                values.append(self.issued[self.command_names[channel]])
            else:
                i = self.command_names[channel[:-5]]
                values.append((self.issued[i] - self.before[i]) / self.dt)
        surface = self.np.clip(self._act(self.np.array(values)), self.low, self.high)
        if self.filter_alpha < 1.0:
            # ADR-953: the trainer's own filter, after the clamp, the episode's
            # first command through unfiltered.
            surface = self.filtered_command(self.np, surface, self.issued, self.first, self.filter_alpha)
        self.first = False
        self.before, self.issued = self.issued, surface
        ctrl = data.ctrl.copy()
        ctrl[self.ctrl_index] = surface * self.ctrl_scale
        return ctrl


def episode_seconds(plan: Mapping[str, Any], limits: Mapping[str, Sequence[float]]) -> float:
    """A generous bound on an episode: each leg and a half turn at half their speed, its hold, and 10 s.

    Half speed, so a slow robot is not cut off: at its full speed the orun9
    biped's legs take 30-60 s each, and at 0.85 of the command it ran past a
    bound of each leg at its speed plus 10 s on every held-out sequence (orun21
    G3, ADR-865). Play stops a second after the last point, so a sequence that
    finishes is judged the same under either bound. Speed is judged apart.
    """

    x = y = 0.0
    total = 10.0
    turn = 2.0 * math.pi / max(1e-6, float(limits["wz"][1]))
    for point in plan["points"]:
        px, py = point["xy_m"]
        total += 2.0 * math.hypot(px - x, py - y) / float(point["speed_mps"]) + turn + float(point["hold_s"])
        x, y = px, py
    return total


def judge(samples: Mapping[str, Any], plan: Mapping[str, Any], dt: float,
          fell: bool, walls: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """An episode's readings against G2's bar (:data:`JUDGE`).

    Per point: whether it was reached (the layer moved past it or arrived on
    it), the closest the base came while it was lit, the worst distance
    while held, and on its leg the forward speed over its straight stretch:
    the base faced the point within ``straight_deg``, the command was the
    point's own speed (not the slow-down), and ``straight_settle_s`` had passed
    since that began. A leg with under ``straight_min_s`` of straight is not
    read for speed. ``leg_s`` is the time from the point lighting to the base
    reaching it: the layer passing it, or the hold starting. ``walls``, when the
    course has any, is :func:`play`'s count of steps a body of the robot was
    inside a wall; any such step fails ``clear_walls`` (ADR-860).
    """

    import numpy as np

    J = JUDGE
    index = np.asarray(samples["index"])
    distance = np.asarray(samples["distance"])
    arrived = np.asarray(samples["arrived"])
    bearing = np.degrees(np.abs(np.asarray(samples["bearing"])))
    forward = np.asarray(samples["forward"])
    commanded = np.asarray(samples["commanded"])
    settle = int(round(J["straight_settle_s"] / dt))
    rows = []
    for k, point in enumerate(plan["points"]):
        lit = index == k
        held = lit & arrived
        reached = bool((index > k).any() or held.any())
        there = held | (index > k)
        straight = lit & ~arrived & (bearing < J["straight_deg"]) \
            & np.isclose(commanded, point["speed_mps"], atol=1e-3)
        run, keep = 0, np.zeros_like(straight)
        for i, flag in enumerate(straight):
            run = run + 1 if flag else 0
            keep[i] = run > settle
        row = {"point": k, "band": point["band"], "bearing": point["bearing"],
               "speed_mps": point["speed_mps"], "hold_s": point["hold_s"], "reached": reached,
               "closest_m": round(float(distance[lit].min()), 4) if lit.any() else None,
               "hold_worst_m": round(float(distance[held].max()), 4) if held.any() else None,
               "arrived_at_s": round(float(np.argmax(held) * dt), 2) if held.any() else None,
               "leg_s": round(float((np.argmax(there) - np.argmax(lit)) * dt), 2)
               if reached and lit.any() else None,
               "straight_s": round(float(keep.sum() * dt), 2)}
        if row["straight_s"] >= J["straight_min_s"]:
            row["speed_ratio"] = round(float(forward[keep].mean()) / point["speed_mps"], 4)
        rows.append(row)
    reach = all(r["reached"] and r["closest_m"] is not None and r["closest_m"] <= J["reach_m"] for r in rows)
    hold = all(r["hold_worst_m"] is None or r["hold_worst_m"] <= J["hold_m"] for r in rows if r["hold_s"] > 0)
    speeds = [r["speed_ratio"] for r in rows if "speed_ratio" in r]
    track = all(abs(s - 1.0) <= J["speed_tolerance"] for s in speeds)
    clear = not (walls or {}).get("steps")
    return {"points": rows, "fell": fell, "reached": sum(r["reached"] for r in rows),
            "pass": {"reach": reach, "hold": hold, "speed": track, "no_fall": not fell,
                     "clear_walls": clear, "all": reach and hold and track and not fell and clear},
            "speed_ratios": speeds, "thresholds": dict(J),
            **({"walls": dict(walls)} if walls is not None else {})}


def stand_course(mujoco: Any, np: Any, xml: bytes, course: Mapping[str, Any]) -> tuple[Any, Any]:
    """The bundle's model with a box course stood in its terrain slots, and the course's ground.

    ``course`` is a box course in the bundle's form (boxes, domes,
    ``lowest_mm``, ``slots``, ``dome_slots``, ``scale``), as
    ``CadexDynamics.terrain_evaluation_course`` draws it (ADR-718). Each
    ``environment/terrain/<i>`` slot takes its box or a parked cube, each dome
    slot its sphere, and the plane the course's lowest point, as the trainer's
    ``place_course`` writes them; the model is recompiled, so stock MuJoCo's
    static bounding-volume tree is built round the placed boxes. ``ground(x_mm,
    y_mm)`` is the highest box top, dome cap or plane on that vertical, read
    as the trainer's height scan reads boxes (``box_tops``). ADR-858.
    """

    import cadex_train

    if course.get("kind") != "boxes":
        raise SystemExit("--course stands a box course; this one is "
                         f"{course.get('kind')!r}")
    scale = float(course["scale"])
    lowest = float(course["lowest_mm"])
    boxes, domes = list(course["boxes"]), list(course.get("domes") or ())
    slots, dome_slots = int(course["slots"]), int(course.get("dome_slots") or 0)
    if len(boxes) > slots or len(domes) > dome_slots:
        raise SystemExit(f"the course's {len(boxes)} boxes and {len(domes)} domes do not fit "
                         f"the model's {slots} and {dome_slots} slots")
    placed = cadex_train.course_geoms(boxes, lowest, slots, scale)
    spec = mujoco.MjSpec.from_string(xml.decode("utf-8"))
    spec.geom("environment/terrain").pos[2] = placed["plane_z_m"]
    for index, (pos, quat, size) in enumerate(zip(placed["pos_m"], placed["quat"], placed["size_m"])):
        geom = spec.geom(f"environment/terrain/{index}")
        geom.pos, geom.quat, geom.size = pos, quat, size
    parked = lowest - cadex_train.TERRAIN_BASE_MM - cadex_train.TERRAIN_PARKED_DEPTH_MM
    rows = ([[d["x_mm"], d["y_mm"], d["top_mm"] - d["radius_mm"], d["radius_mm"]] for d in domes]
            + [[0.0, 0.0, parked, 0.0]] * (dome_slots - len(domes)))
    for index, (x, y, z, radius) in enumerate(rows):
        geom = spec.geom(f"environment/terrain/dome/{index}")
        geom.pos = [x * scale, y * scale, z * scale]
        geom.size = [(radius or cadex_train.TERRAIN_PARKED_HALF_MM) * scale, 0.0, 0.0]
    return spec.compile(), course_ground(np, course)


def course_ground(np: Any, course: Mapping[str, Any]) -> Any:
    """``ground(x_mm, y_mm)`` on a box course: the highest box top, dome cap or plane there."""

    import cadex_train

    lowest = float(course["lowest_mm"])
    boxes, domes = list(course["boxes"]), list(course.get("domes") or ())
    scan = np.asarray(cadex_train.box_scan_rows(cadex_train.course_geoms(boxes, lowest, len(boxes), 1.0)))
    caps = np.asarray([[d["x_mm"], d["y_mm"], d["top_mm"] - d["radius_mm"], d["radius_mm"]]
                       for d in domes], dtype=np.float64).reshape(-1, 4)

    def ground(x_mm: float, y_mm: float) -> float:
        height = lowest
        if len(scan):
            tops = cadex_train.box_tops(np, scan, np.array([[x_mm]]), np.array([[y_mm]]), lowest)
            height = max(height, float(tops.max()))
        if len(caps):
            reach = caps[:, 3] ** 2 - (caps[:, 0] - x_mm) ** 2 - (caps[:, 1] - y_mm) ** 2
            on = reach > 0
            if on.any():
                height = max(height, float((caps[on, 2] + np.sqrt(reach[on])).max()))
        return height

    return ground


class DriveMeter:
    """Each actuator's RMS and peak force over an episode, read every solver step (ADR-952).

    ``actuator_force`` is MuJoCo's force after the actuator's ``forcerange``
    clamp, in N·m on a hinge, so the RMS is what a motor's continuous rating
    is checked against. Every solver step counts, not only control steps.
    """

    def __init__(self, np: Any, model: Any) -> None:
        self.np = np
        self.names = [model.actuator(i).name or f"actuator{i}" for i in range(model.nu)]
        self.square = np.zeros(model.nu)
        self.peak = np.zeros(model.nu)
        self.samples = 0

    def add(self, data: Any) -> None:
        force = self.np.asarray(data.actuator_force, dtype=self.np.float64)
        self.square += force * force
        self.peak = self.np.maximum(self.peak, self.np.abs(force))
        self.samples += 1

    def reading(self) -> dict[str, Any]:
        rms = self.np.sqrt(self.square / max(self.samples, 1))
        worst = int(self.np.argmax(rms)) if len(rms) else None
        return {"samples": self.samples,
                "rms_nm": {n: round(float(v), 4) for n, v in zip(self.names, rms)},
                "peak_nm": {n: round(float(v), 4) for n, v in zip(self.names, self.peak)},
                "worst": None if worst is None else self.names[worst],
                "worst_rms_nm": None if worst is None else round(float(rms[worst]), 4)}


def play(options: argparse.Namespace) -> int:
    """Play one held-out (or training) sequence with a policy and write its view and readings.

    ``goto.json`` carries ``drives``: each actuator's RMS and peak force over
    the episode (:class:`DriveMeter`, ADR-952).
    """

    import hashlib

    import mujoco
    import numpy as np

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cadex_train

    policy_path = Path(options.policy).expanduser()
    player = Player(policy_path, Path(options.task).expanduser(), options.goals.split(","),
                    other_model=options.other_model)
    if options.sequence:
        plan = json.loads(Path(options.sequence).expanduser().read_text(encoding="utf-8"))
        if plan.get("schema") != GOTO_SCHEMA:
            raise SystemExit(f"--sequence: {options.sequence} is not a {GOTO_SCHEMA}")
    else:
        plan = sequence(options.seed, split=options.split, bands=parse_bands(options.bands),
                        points=options.points)
    arrays = stack(np, [plan])
    course = None
    ground = lambda x_mm, y_mm: 0.0  # noqa: E731
    if options.course:
        course = json.loads(Path(options.course).expanduser().read_text(encoding="utf-8"))
        player.model, ground = stand_course(mujoco, np, player.model_xml, course)
        player.ground = ground
    model, data = player.model, mujoco.MjData(player.model)
    # ADR-860: a course's walls stop only what the model lets touch the ground
    # (often the feet), so a body inside one is read here, by MuJoCo's own
    # geom distance, each control step.
    wall_geoms = [model.geom(f"environment/terrain/{int(i)}").id for i in (course or {}).get("walls") or ()]
    robot_geoms = [g for g in range(model.ngeom) if int(model.geom_bodyid[g]) != 0]
    walls = None if not wall_geoms else {"slots": len(wall_geoms), "steps": 0, "first_s": None, "bodies": []}
    fromto = np.zeros(6)
    data.qpos[:] = player.home
    data.ctrl[player.ctrl_index] = player.reset_command * player.ctrl_scale
    mujoco.mj_forward(model, data)
    # The base's centre of mass, not its frame: a frame may sit at the floor
    # (leon V's concept chest), where any dip would read as a fall (orun21 G3).
    home_height = float(data.xipos[player.base][2])
    player.reset()
    state = layer_start(np, [1])
    seconds = options.seconds or episode_seconds(plan, player.limits)
    steps = int(round(seconds / player.dt))
    keep = max(1, int(round(1.0 / (player.dt * options.fps))))
    poses, goto_frames = [], []
    record = {key: [] for key in ("index", "arrived", "distance", "bearing", "forward", "commanded")}
    fell = False
    count = len(plan["points"])
    step = 0
    drives = DriveMeter(np, model)
    while step < steps:
        R = data.xmat[player.base].reshape(3, 3)
        x, y = float(data.xpos[player.base][0]), float(data.xpos[player.base][1])
        yaw = math.atan2(R[1, 0], R[0, 0])
        state, command = layer_step(np, arrays, state, np.array([x]), np.array([y]), np.array([yaw]),
                                    player.dt, player.limits)
        index = int(state["index"][0])
        lit = min(index, count - 1)
        px, py = plan["points"][lit]["xy_m"]
        ex = math.cos(yaw) * (px - x) + math.sin(yaw) * (py - y)
        ey = -math.sin(yaw) * (px - x) + math.cos(yaw) * (py - y)
        forward = float((R.T @ data.qvel[:3])[0])
        record["index"].append(index)
        record["arrived"].append(bool(state["arrived"][0]))
        record["distance"].append(math.hypot(ex, ey))
        record["bearing"].append(math.atan2(ey, ex))
        record["forward"].append(forward)
        record["commanded"].append(math.hypot(float(command["vx"][0]), float(command["vy"][0])))
        if step % keep == 0:
            poses.append(data.qpos.copy())
            hold = float(plan["points"][lit]["hold_s"])
            goto_frames.append({"index": index, "arrived": bool(state["arrived"][0]),
                                "hold": round(min(1.0, float(state["held_s"][0]) / hold), 3) if hold > 0 else 0.0,
                                "command": [round(float(command[a][0]), 3) for a in ("vx", "vy", "wz")]})
        if index >= count and (step == 0 or record["index"][-2] < count):
            # One second past the last hold, so the end is seen standing.
            steps = min(steps, step + int(round(1.0 / player.dt)))
        if walls is not None:
            mujoco.mj_kinematics(model, data)
            hit = set()
            for g in robot_geoms:
                for w in wall_geoms:
                    gap = np.linalg.norm(data.geom_xpos[g] - data.geom_xpos[w])
                    if gap > model.geom_rbound[g] + model.geom_rbound[w]:
                        continue
                    if mujoco.mj_geomDistance(model, data, g, w, 0.0, fromto) < 0.0:
                        hit.add(model.body(int(model.geom_bodyid[g])).name)
            if hit:
                walls["steps"] += 1
                walls["first_s"] = walls["first_s"] if walls["first_s"] is not None else round(step * player.dt, 2)
                walls["bodies"] = sorted(set(walls["bodies"]) | hit)
        step += 1
        data.ctrl[:] = player.control(data, [command["vx"][0], command["vy"][0], command["wz"][0]])
        for _ in range(player.substeps):
            mujoco.mj_step(model, data)
            drives.add(data)
        if not np.all(np.isfinite(data.qpos)):
            fell = True
            break
        R = data.xmat[player.base].reshape(3, 3)
        # Height over the ground under the base, so a course's pit or step is not a fall.
        bx, by, bz = (float(v) for v in data.xipos[player.base])
        if R[2, 2] < JUDGE["fall_up_z"] or bz - ground(1000.0 * bx, 1000.0 * by) / 1000.0 \
                < JUDGE["fall_height_share"] * (home_height - ground(0.0, 0.0) / 1000.0):
            fell = True
            poses.append(data.qpos.copy())
            goto_frames.append(dict(goto_frames[-1]))
            break
    readings = judge(record, plan, player.dt, fell, walls)
    out = Path(options.view_dir).expanduser() if options.view_dir else policy_path.parent / "view"
    trace = cadex_train.write_view(out, player.model_xml, poses, player.dt * keep,
                                   source=f"cadex_goto play {policy_path.name} {plan['split']}:{plan['seed']}",
                                   goto={"sequence": plan, "frames": goto_frames},
                                   terrain=(course or {}).get("drawing"))
    result = {"schema": EPISODE_SCHEMA, "policy": str(policy_path), "sequence": plan,
              "course": None if course is None else {
                  "course": course.get("course"), "lowest_mm": course["lowest_mm"],
                  "highest_mm": course["highest_mm"], "boxes": len(course["boxes"]),
                  "domes": len(course.get("domes") or ())},
              "limits": player.limits, "layer": dict(LAYER), "seconds": round(len(record["index"]) * player.dt, 2),
              "witness_error": player.witness_error, "action_filter_alpha": player.filter_alpha,
              "view": str(trace),
              "model_sha256": hashlib.sha256(player.model_xml).hexdigest(), "trained_on": player.trained_on,
              "drives": drives.reading(), **readings}
    (out.parent / "goto.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"view": str(trace), "seconds": result["seconds"], "reached": readings["reached"],
                      "of": count, "pass": readings["pass"], "speed_ratios": readings["speed_ratios"]}))
    return 0


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    verbs = parser.add_subparsers(dest="verb", required=True)
    for name in ("sequence", "play"):
        verb = verbs.add_parser(name)
        if name == "play":
            verb.add_argument("policy")
            verb.add_argument("--task", required=True, help="the bundle the policy trained on")
            verb.add_argument("--goals", default="cx,cy,cw",
                              help="the task's forward, lateral and yaw-rate goals, in that order")
            verb.add_argument("--other-model", action="store_true",
                              help="play on a model the policy did not train on, its channels matched by name")
            verb.add_argument("--view-dir", default=None, help="default: view/ beside the policy")
            verb.add_argument("--seconds", type=float, default=None, help="default: episode_seconds()")
            verb.add_argument("--fps", type=float, default=25.0, help="view frames per second")
            verb.add_argument("--course", default=None,
                              help="a box course JSON to stand in the model's terrain slots "
                                   "(CadexDynamics.terrain_evaluation_course; its 'drawing' goes "
                                   "on the view); default: the model as it is")
            verb.add_argument("--sequence", default=None,
                              help="a sequence JSON to play (e.g. maze_route's), in place of "
                                   "--seed/--split/--bands/--points' draw")
        verb.add_argument("--seed", type=int, default=0)
        verb.add_argument("--split", choices=SPLITS, default="heldout")
        verb.add_argument("--bands", required=True, help="NAME:LOW-HIGH,... in m/s")
        verb.add_argument("--points", type=int, default=SEQUENCE["points"])
    options = parser.parse_args(argv[1:])
    if options.verb == "sequence":
        print(json.dumps(sequence(options.seed, split=options.split, bands=parse_bands(options.bands),
                                  points=options.points), indent=1))
        return 0
    return play(options)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
