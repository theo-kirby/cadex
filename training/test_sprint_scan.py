# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-976: a sprint over a relief strip (ADR-972) reads the race scan (ADR-967) without ``--gates``.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_sprint_scan.py`` from the repo.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

import cadex_goto as G
import cadex_train as T
from test_race_terrain_training import WALKER, walker_task


def sprint_options(*extra: str):
    return T.arguments(["bundle.json", "--out", "x.cxpolicy", "--race-terrain", "b1",
                        "--relief-strip", "6", "--relief-levels", "2", *extra])


def test_a_sprint_strip_takes_the_scan_last_and_a_warm_start_gains_only_it() -> None:
    blind = walker_task()
    task = T.gate_task(blind, sprint_options("--race-scan", "default"))
    assert "gates" not in task and task["goal"] == blind["goal"] and task["reward"] == blind["reward"]
    assert task["race_scan"] == T.race_scan_grid("default")
    assert T.actor_channels(task) == T.actor_channels(blind) + task["race_scan"]["channels"]
    assert T.channels(task)[-18:] == task["race_scan"]["channels"]
    assert len(T.sensor_variance_floor(task)) == len(T.channels(task))
    assert T.race_scan_gained(T.actor_channels(blind), task) == 18
    assert T.gate_task(blind, sprint_options()) is blind  # no scan: the task as it was
    scanned = {**blind, "scans": [{"channels": ["s0"]}]}
    with pytest.raises(SystemExit, match="ADR-715"):
        T.gate_task(scanned, sprint_options("--race-scan", "default"))


def test_the_sprints_actor_reads_the_scan_over_its_own_episodes_strip() -> None:
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    opts = sprint_options("--race-scan", "default", "--relief-ceiling", "2,0.1,0")
    task = T.gate_task(walker_task(), opts)
    env = T.build_environment({"task": task, "model_xml": WALKER.encode("utf-8")}, opts, count=4,
                              seed=0, jax=jax, jnp=jnp, np=np, mujoco=mujoco, mjx=mjx)
    assert env.actor_names[-18:] == task["race_scan"]["channels"]
    assert env.relief["strip_m"] == 6.0
    fields = T.relief_fields(np, T.relief_rule(opts), 0)
    state = env.reset(jax.random.PRNGKey(0))
    assert "gates" not in state.info
    seen = set()
    for _ in range(3):
        state = state.replace(info={**state.info, "steps": jnp.full((4,), 10_000, jnp.int32)})
        state = env.step(state, jnp.zeros((4, 1)))  # every episode starts afresh
        level = np.asarray(state.info["relief"])
        seen |= set(level.tolist())
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
    assert seen & {1, 2}  # some episode read a strip, not only the plane


def test_the_scan_reads_a_strips_obstacle_ahead() -> None:
    strip = G.strip_terrain(np, "b1", 7, length_m=20.0)
    ground = G.terrain_ground(np, strip)
    box = max(strip["drawn"]["obstacles"], key=lambda o: o["height_mm"])
    cx, cy = (float(v) for v in box["centre_mm"][:2])
    offsets = np.asarray(T.race_scan_grid("default")["offsets_mm"])
    # The base 600 mm short of the obstacle's centre, facing +x, 200 mm up.
    read = T.race_scan_vector(np, offsets, np.array([(cx - 600.0) / 1000.0]), np.array([cy / 1000.0]),
                              np.array([0.2]), np.array([0.0]), strip["heights_mm"][None], np.array([1]),
                              strip)
    centre = [p for p, (a, l) in enumerate(offsets) if a == 600.0 and l == 0.0][0]
    assert read[0, centre] == pytest.approx(200.0 - ground(cx, cy), abs=1e-6)
    assert ground(cx, cy) >= box["height_mm"] - 1.0
