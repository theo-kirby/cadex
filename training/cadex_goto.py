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
SEQUENCE = {"points": 8, "behind": 2, "side": 2, "distance_m": (2.0, 5.0),
            "holds": 2, "hold_share": 0.5, "hold_s": (1.0, 3.0)}

#: The layer's gains and radii. ``arrive_m`` is under G2's 0.3 m reach bar; a
#: point with a hold is arrived on only within ``hold_arrive_m``, so the hold
#: starts inside its 0.15 m bar; ``settle_m`` is the hold's dead band.
LAYER = {"arrive_m": 0.25, "hold_arrive_m": 0.1, "turn_deg": 60.0, "yaw_gain": 2.0, "approach_gain": 1.0,
         "approach_min": 0.25, "hold_gain": 1.5, "hold_max": 0.3, "settle_m": 0.05}

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
    (:data:`BEARINGS`), at a distance in ``distance_m``. At least ``behind``
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
        x, y = x + distance * math.cos(heading), y + distance * math.sin(heading)
        band = bands[rng.randrange(len(bands))]
        speed = rng.uniform(float(band["low"]), float(band["high"]))
        hold = rng.uniform(*options["hold_s"]) if index in held or rng.random() < options["hold_share"] else 0.0
        points.append({"xy_m": [round(x, 4), round(y, 4)], "speed_mps": round(speed, 3),
                       "hold_s": round(hold, 2), "band": str(band["name"]), "bearing": kind})
    return {"schema": GOTO_SCHEMA, "split": split, "seed": int(seed),
            "bands": [dict(band) for band in bands],
            "shape": {key: list(value) if isinstance(value, tuple) else value
                      for key, value in options.items()},
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
            "arrived": xp.zeros(tuple(batch), dtype=bool)}


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
    facing = xp.abs(bearing) < math.radians(g["turn_deg"])
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


class Player:
    """A ``.cxpolicy`` played on its bundle's model as the engine plays one, in numpy.

    The header's channels come from sensordata at the bundle's ``adr`` and
    ``scale``, the goal channels from the layer, and the previous two issued
    commands (and their rate). Then ``(x - mean) / std``, the MLP,
    ``tanh * output_scale + output_bias``, the bundle's clamp and scale into
    ctrl. A channel with no source here (contacts, trackers, scans) is refused.
    """

    def __init__(self, policy_path: Path, task_path: Path, goals: Sequence[str]) -> None:
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
        if hashlib.sha256(xml).hexdigest() != header["model"]["sha256"]:
            raise SystemExit("the policy was not trained on this bundle's model")
        training = header.get("training") or {}
        if float(training.get("action_filter_alpha", 1.0)) != 1.0 or float(training.get("command_slew_deg", 0.0)):
            raise SystemExit("this player plays no action filter or command slew")
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
        for channel in self.channels:
            if not (channel in self.sensor or channel in self.goals or channel in self.command_names
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

    def control(self, data: Any, command: Sequence[float]) -> Any:
        goal = {name: float(value) * scale for name, value, scale in zip(self.goals, command, self.goal_scale)}
        values = []
        for channel in self.channels:
            if channel in self.sensor:
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
        self.before, self.issued = self.issued, surface
        ctrl = data.ctrl.copy()
        ctrl[self.ctrl_index] = surface * self.ctrl_scale
        return ctrl


def episode_seconds(plan: Mapping[str, Any], limits: Mapping[str, Sequence[float]]) -> float:
    """A generous bound on an episode: each leg at its speed, a half turn, its hold, and 10 s."""

    x = y = 0.0
    total = 10.0
    turn = math.pi / max(1e-6, float(limits["wz"][1]))
    for point in plan["points"]:
        px, py = point["xy_m"]
        total += math.hypot(px - x, py - y) / float(point["speed_mps"]) + turn + float(point["hold_s"])
        x, y = px, py
    return total


def judge(samples: Mapping[str, Any], plan: Mapping[str, Any], dt: float,
          fell: bool) -> dict[str, Any]:
    """An episode's readings against G2's bar (:data:`JUDGE`).

    Per point: whether it was reached (the layer moved past it or arrived on
    it), the closest the base came while it was lit, the worst distance
    while held, and on its leg the forward speed over its straight stretch:
    the base faced the point within ``straight_deg``, the command was the
    point's own speed (not the slow-down), and ``straight_settle_s`` had passed
    since that began. A leg with under ``straight_min_s`` of straight is not
    read for speed.
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
               "straight_s": round(float(keep.sum() * dt), 2)}
        if row["straight_s"] >= J["straight_min_s"]:
            row["speed_ratio"] = round(float(forward[keep].mean()) / point["speed_mps"], 4)
        rows.append(row)
    reach = all(r["reached"] and r["closest_m"] is not None and r["closest_m"] <= J["reach_m"] for r in rows)
    hold = all(r["hold_worst_m"] is None or r["hold_worst_m"] <= J["hold_m"] for r in rows if r["hold_s"] > 0)
    speeds = [r["speed_ratio"] for r in rows if "speed_ratio" in r]
    track = all(abs(s - 1.0) <= J["speed_tolerance"] for s in speeds)
    return {"points": rows, "fell": fell, "reached": sum(r["reached"] for r in rows),
            "pass": {"reach": reach, "hold": hold, "speed": track, "no_fall": not fell,
                     "all": reach and hold and track and not fell},
            "speed_ratios": speeds, "thresholds": dict(J)}


def play(options: argparse.Namespace) -> int:
    """Play one held-out (or training) sequence with a policy and write its view and readings."""

    import mujoco
    import numpy as np

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cadex_train

    policy_path = Path(options.policy).expanduser()
    player = Player(policy_path, Path(options.task).expanduser(), options.goals.split(","))
    plan = sequence(options.seed, split=options.split, bands=parse_bands(options.bands),
                    points=options.points)
    arrays = stack(np, [plan])
    model, data = player.model, mujoco.MjData(player.model)
    data.qpos[:] = player.home
    data.ctrl[player.ctrl_index] = player.reset_command * player.ctrl_scale
    mujoco.mj_forward(model, data)
    home_height = float(data.xpos[player.base][2])
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
        step += 1
        data.ctrl[:] = player.control(data, [command["vx"][0], command["vy"][0], command["wz"][0]])
        for _ in range(player.substeps):
            mujoco.mj_step(model, data)
        if not np.all(np.isfinite(data.qpos)):
            fell = True
            break
        R = data.xmat[player.base].reshape(3, 3)
        if R[2, 2] < JUDGE["fall_up_z"] or data.xpos[player.base][2] < JUDGE["fall_height_share"] * home_height:
            fell = True
            poses.append(data.qpos.copy())
            goto_frames.append(dict(goto_frames[-1]))
            break
    readings = judge(record, plan, player.dt, fell)
    out = Path(options.view_dir).expanduser() if options.view_dir else policy_path.parent / "view"
    trace = cadex_train.write_view(out, player.model_xml, poses, player.dt * keep,
                                   source=f"cadex_goto play {policy_path.name} {plan['split']}:{plan['seed']}",
                                   goto={"sequence": plan, "frames": goto_frames})
    result = {"schema": EPISODE_SCHEMA, "policy": str(policy_path), "sequence": plan,
              "limits": player.limits, "layer": dict(LAYER), "seconds": round(len(record["index"]) * player.dt, 2),
              "witness_error": player.witness_error, "view": str(trace), **readings}
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
            verb.add_argument("--view-dir", default=None, help="default: view/ beside the policy")
            verb.add_argument("--seconds", type=float, default=None, help="default: episode_seconds()")
            verb.add_argument("--fps", type=float, default=25.0, help="view frames per second")
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
