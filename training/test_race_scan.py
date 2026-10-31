# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-967: a racer's height scan of the ground ahead, read over the episode's relief field.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_race_scan.py`` from the repo.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

import cadex_goto as G
import cadex_train as T
from test_race_terrain_training import WALKER, walker_task


def options(*extra: str):
    return T.arguments(["bundle.json", "--out", "x.cxpolicy", "--gates", "--race-terrain", "b1",
                        "--relief-half", "2", "--relief-levels", "2", *extra])


def test_the_grid_is_its_default_or_its_rows_and_columns_and_needs_a_race() -> None:
    grid = T.race_scan_grid("default")
    assert len(grid["offsets_mm"]) == 18 and grid["channels"][0] == "rscan0"
    assert grid["offsets_mm"][:3] == [[-200.0, -120.0], [-200.0, 0.0], [-200.0, 120.0]]
    assert grid["offsets_mm"][-1] == [800.0, 120.0]
    assert T.race_scan_grid("0,300:0")["offsets_mm"] == [[0.0, 0.0], [300.0, 0.0]]
    assert T.race_scan_grid(None) is None
    with pytest.raises(SystemExit, match="race-scan"):
        T.race_scan_grid("0,300")
    flat = T.arguments(["bundle.json", "--out", "x.cxpolicy", "--race-scan", "default"])
    with pytest.raises(SystemExit, match="give --gates"):
        T.gate_task(walker_task(), flat)


def test_the_scan_follows_the_gates_and_a_warm_start_gains_only_it() -> None:
    task = T.gate_task(walker_task(), options("--race-scan", "0,300:0"))
    blind = T.gate_task(walker_task(), options())
    assert T.actor_channels(task) == T.actor_channels(blind) + ["rscan0", "rscan1"]
    assert T.channels(task)[-2:] == ["rscan0", "rscan1"]
    assert len(T.sensor_variance_floor(task)) == len(T.channels(task))
    assert T.race_scan_gained(T.actor_channels(blind), task) == 2
    assert T.race_scan_gained(T.actor_channels(task), task) == 0  # nothing to gain
    assert T.race_scan_gained(T.actor_channels(blind)[1:], task) == 0  # another input moved
    assert T.race_scan_gained(T.actor_channels(blind), blind) == 0


def test_the_scan_reads_the_ground_the_judge_reads() -> None:
    field = T.relief_fields(np, T.relief_rule(options()), 0)[1]
    ground = G.terrain_ground(np, field)
    rng = np.random.default_rng(3)
    offsets = np.asarray(T.race_scan_grid("default")["offsets_mm"])
    x, y = rng.uniform(-2.2, 2.2, 6), rng.uniform(-2.2, 2.2, 6)
    z, yaw = rng.uniform(0.1, 0.3, 6), rng.uniform(-math.pi, math.pi, 6)
    grids = np.stack([np.zeros_like(field["heights_mm"]), field["heights_mm"]])
    read = T.race_scan_vector(np, offsets, x, y, z, yaw, grids, np.full(6, 2), field)
    plane = T.race_scan_vector(np, offsets, x, y, z, yaw, grids, np.zeros(6, int), field)
    for e in range(6):
        for p, (ahead, left) in enumerate(offsets):
            px = 1000 * x[e] + math.cos(yaw[e]) * ahead - math.sin(yaw[e]) * left
            py = 1000 * y[e] + math.sin(yaw[e]) * ahead + math.cos(yaw[e]) * left
            assert read[e, p] == pytest.approx(1000 * z[e] - ground(px, py), abs=1e-6)
            assert plane[e, p] == pytest.approx(1000 * z[e])
    assert np.ptp(read) > 0.0 and field["drawn"]["boxes"] + field["drawn"]["steps"] > 0


def test_the_actor_reads_the_scan_over_its_own_episodes_field() -> None:
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    opts = options("--race-scan", "default", "--relief-ceiling", "2,0.1,0")
    task = T.gate_task(walker_task(), opts)
    env = T.build_environment({"task": task, "model_xml": WALKER.encode("utf-8")}, opts, count=4,
                              seed=0, jax=jax, jnp=jnp, np=np, mujoco=mujoco, mjx=mjx)
    assert env.actor_names[-18:] == task["race_scan"]["channels"]
    fields = T.relief_fields(np, T.relief_rule(opts), 0)
    state = env.reset(jax.random.PRNGKey(0))
    for _ in range(3):
        state = state.replace(info={**state.info, "steps": jnp.full((4,), 10_000, jnp.int32)})
        state = env.step(state, jnp.zeros((4, 1)))  # every episode starts afresh
        level = np.asarray(state.info["relief"])
        qpos = np.asarray(state.pipeline_state.qpos)
        w, qx, qy, qz = qpos[:, 3], qpos[:, 4], qpos[:, 5], qpos[:, 6]
        yaw = np.arctan2(2 * (w * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
        for e in range(4):
            ground = (G.terrain_ground(np, fields[level[e] - 1]) if level[e] else (lambda a, b: 0.0))
            for p, (ahead, left) in enumerate(task["race_scan"]["offsets_mm"]):
                px = 1000 * qpos[e, 0] + math.cos(yaw[e]) * ahead - math.sin(yaw[e]) * left
                py = 1000 * qpos[e, 1] + math.sin(yaw[e]) * ahead + math.cos(yaw[e]) * left
                want = 1000 * qpos[e, 2] - ground(px, py)
                assert float(state.obs["state"][e, -18 + p]) == pytest.approx(want, abs=0.05)


def test_the_player_reads_the_headers_scan_over_its_ground() -> None:
    grid = T.race_scan_grid("0,300:0")
    player = G.Player.__new__(G.Player)
    seen = []
    player.__dict__.update(
        np=np, goals=[], goal_scale=[], gate_channels=["gate0_x"], sensor={}, command_names={},
        channels=["gate0_x", *grid["channels"]], base=1, dt=0.02, low=np.array([-1.0]),
        high=np.array([1.0]), filter_alpha=1.0, first=True, issued=np.zeros(1), before=np.zeros(1),
        ctrl_index=np.array([0]), ctrl_scale=np.array([1.0]),
        _act=lambda values: seen.append(values) or np.zeros(1),
        scans=[{"body_id": 1, "scale": 1000.0, "offsets_mm": grid["offsets_mm"],
                "channels": grid["channels"]}],
        ground=lambda x_mm, y_mm: 40.0 if x_mm > 1100.0 else 0.0)
    # The base at (1, 0, 0.2) facing +x: the point 300 mm ahead is over the box.
    data = SimpleNamespace(xpos=np.array([[0, 0, 0], [1.0, 0.0, 0.2]]),
                           xmat=np.array([np.eye(3).ravel()] * 2), ctrl=np.zeros(1), sensordata=[])
    player.control(data, (), [2.5])
    assert seen[0].tolist() == pytest.approx([2.5, 200.0, 160.0])


def test_the_player_and_the_header_carry_the_scan() -> None:
    import inspect

    assert '(header.get("training") or {}).get("race_scan")' in inspect.getsource(G.Player.__init__)
    source = inspect.getsource(T.policy_header)
    assert '{"race_scan": dict(task["race_scan"])} if task.get("race_scan")' in source
