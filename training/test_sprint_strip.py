# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-972: ``--race-terrain`` without ``--gates`` lays relief as a strip along +x under a sprint.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_sprint_strip.py`` from the repo.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

import cadex_goto as G
import cadex_train as T
from test_race_terrain_training import WALKER, walker_task


def sprint_options(*extra: str):
    return T.arguments(["bundle.json", "--out", "x.cxpolicy", "--race-terrain", "u1",
                        "--relief-strip", "6", *extra])


def test_a_strip_is_train_split_relief_along_x_that_no_race_or_judge_meets() -> None:
    strip = G.strip_terrain(np, "u1", 3, length_m=20.0)
    assert strip["split"] == "train" and strip["course_kind"] == "strip" and strip["seed"] == 3
    assert G.strip_terrain(np, "u1", 3, length_m=20.0)["sha256"] == strip["sha256"]
    assert G.strip_terrain(np, "u1", 4, length_m=20.0)["sha256"] != strip["sha256"]
    margin = 1000.0 * G.RACE_TERRAIN["margin_m"]
    assert strip["x_range_mm"][0] == pytest.approx(-margin)
    assert strip["x_range_mm"][1] >= 20000.0 + margin - G.RACE_TERRAIN["cell_mm"]
    assert strip["y_range_mm"][0] == pytest.approx(-margin)
    assert strip["y_range_mm"][1] == pytest.approx(margin, abs=G.RACE_TERRAIN["cell_mm"])
    # Not the held-out straight strip a sprint is judged on (Symon's
    # tools/sprint_terrain.py), nor a race's or a field's relief, on any seed tried.
    heldout = [G.race_terrain(np, {"kind": kind, "split": split, "seed": s,
                                   "gates": [{"xy_m": [20.0, 0.0]}]}, "u1")["sha256"]
               for kind in ("straight", "sprint", "gates", "field") for split in ("train", "heldout")
               for s in (2, 3, 4) if (kind, split) != ("strip", "train")]
    assert strip["sha256"] not in heldout
    heights = strip["heights_mm"]
    assert heights.min() >= 0.0 and strip["highest_mm"] > 20.0
    assert strip["hill_grade_deg"] <= G.RACE_TERRAIN["grade_deg"][1] + 0.5
    # The start's clearing is flat; the relief runs the strip's length.
    cell, x0, y0 = strip["cell_mm"], strip["x_range_mm"][0], strip["y_range_mm"][0]
    c, r = int(round(-x0 / cell)), int(round(-y0 / cell))
    assert np.all(heights[r - 10:r + 11, c - 10:c + 11] == 0.0)
    gx = x0 + cell * np.arange(strip["ncol"])
    assert heights[:, gx > 15000.0].max() > 10.0
    with pytest.raises(SystemExit):
        G.strip_terrain(np, "u1", 3, length_m=0.0)


def test_a_b1_strip_stands_an_obstacle_across_the_path_about_every_3_m() -> None:
    length = 60.0
    strip = G.strip_terrain(np, "b1", 7, length_m=length)
    obstacles = strip["drawn"]["obstacles"]
    low, high = (float(v) for v in G.RACE_TERRAIN["field_leg_m"])
    assert length / high - 1 <= len(obstacles) <= length / low + 1
    assert {o["kind"] for o in obstacles} == {"box", "step"}
    for o in obstacles:
        x, y = o["centre_mm"]
        assert 0.0 < x < 1000.0 * length
        assert abs(y) <= G.RACE_TERRAIN["obstacle_offset_mm"] + 1e-6
        assert abs(o["yaw_deg"]) <= G.RACE_TERRAIN["obstacle_yaw_deg"] + 1e-6
        assert G.RACE_TERRAIN["box_mm"][0] <= o["height_mm"] <= G.RACE_TERRAIN["box_mm"][1]
    # Its relief outside the obstacles is the u1 strip's, as a race's b1 is.
    u1 = G.strip_terrain(np, "u1", 7, length_m=length)
    assert strip["drawn"]["grade_deg"] == pytest.approx(u1["drawn"]["grade_deg"])
    assert strip["sha256"] != u1["sha256"]


def test_earlier_draws_are_unchanged_by_the_strip() -> None:
    """The strip's branch is its own: a field's and a race's draws are the
    ones ADR-962 to ADR-966 made, to the digest."""

    course = G.gate_course(0, split="heldout")
    assert G.race_terrain(np, course, "b1")["sha256"].startswith("d828152bfdcd2e74")
    assert G.race_terrain(np, G.sprint_course(5, split="heldout"), "b1")["sha256"].startswith("71cc8c22c0639134")
    assert G.field_terrain(np, "b1", 3, half_m=4.0)["sha256"].startswith(FIELD_B1_DIGEST)
    assert G.field_terrain(np, "u1", 3, half_m=4.0)["sha256"].startswith(FIELD_U1_DIGEST)


#: ``field_terrain(np, kind, 3, half_m=4.0)``'s digests before ADR-972.
FIELD_B1_DIGEST = "3027154dffccedc5"
FIELD_U1_DIGEST = "3140f5da9700535e"


def test_the_rule_without_gates_is_a_strip_and_refuses_a_fields_size() -> None:
    rule = T.relief_rule(sprint_options())
    assert rule == {"kind": "u1", "levels": T.RELIEF_LEVELS, "half_m": None, "fields": "scaled",
                    "ceiling": {"start": 1, "falls": 0.1, "hold": 10}, "strip_m": 6.0}
    assert T.relief_rule(T.arguments(["b.json", "--out", "x.cxpolicy"])) is None
    for bad in (["--relief-strip", "0"], ["--relief-half", "2"], ["--relief-levels", "0"]):
        with pytest.raises(SystemExit):
            T.relief_rule(sprint_options(*bad))
    with pytest.raises(SystemExit, match="relief-strip"):
        T.relief_rule(T.arguments(["b.json", "--out", "x.cxpolicy", "--gates", "--race-terrain", "u1",
                                   "--relief-strip", "50"]))
    # A gate race's rule is ADR-962's, with no strip in it.
    assert "strip_m" not in T.relief_rule(T.arguments(["b.json", "--out", "x.cxpolicy", "--gates",
                                                       "--race-terrain", "u1"]))


@pytest.mark.parametrize("mode", ["scaled", "graded", "graded-rough"])
def test_strip_fields_are_the_strips_draws_on_the_fields_seeds(mode: str) -> None:
    rule = T.relief_rule(sprint_options("--relief-levels", "3", "--relief-fields", mode))
    fields = T.relief_fields(np, rule, 5)
    assert [f["level"] for f in fields] == [1, 2, 3]
    assert all(f["course_kind"] == "strip" and f["split"] == "train" for f in fields)
    low, high = G.RACE_TERRAIN["grade_deg"]
    for f in fields:
        k = f["level"]
        if mode == "scaled":
            raw = G.strip_terrain(np, "u1", 5 * 3 + k - 1, length_m=6.0)
            assert np.allclose(f["heights_mm"], raw["heights_mm"] * k / 3)
        elif mode == "graded-rough" and k == 1:
            raw = G.strip_terrain(np, "rough", 5 * 3, length_m=6.0)
            assert f["kind"] == "rough" and f["sha256"] == raw["sha256"]
        else:
            grade = low + (high - low) * (k / 3 if mode == "graded" else (k - 1) / 2)
            raw = G.strip_terrain(np, "u1", 5 * 3 + k - 1, length_m=6.0, grade_deg=(grade, grade))
            assert f["sha256"] == raw["sha256"]
    assert len({f["sha256"] for f in fields}) == 3
    json.dumps([T.relief_drawn_record(f["drawn"]) for f in fields])


def _sprint_environment(*extra: str):
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    opts = sprint_options("--relief-levels", "2", *extra)
    bundle = {"task": walker_task(), "model_xml": WALKER.encode("utf-8")}
    env = T.build_environment(bundle, opts, count=4, seed=0, jax=jax, jnp=jnp, np=np,
                              mujoco=mujoco, mjx=mjx)
    return env, jax, jnp


def test_a_sprint_stands_on_its_strip_and_a_paw_meets_only_its_episodes_level() -> None:
    env, jax, jnp = _sprint_environment("--relief-ceiling", "1,0.1,0")
    assert env.relief["strip_m"] == 6.0 and env.relief["half_m"] is None
    margin = 1000.0 * G.RACE_TERRAIN["margin_m"]
    for f in env.relief["fields"]:  # each a strip from behind the start to past 6 m along +x
        assert f["x_range_mm"][0] == pytest.approx(-margin) and f["x_range_mm"][1] >= 6000.0 + margin - 25.0
        assert f["y_range_mm"][1] == pytest.approx(margin, abs=25.0)
    json.dumps(env.relief)  # the header carries it
    state = env.reset(jax.random.PRNGKey(0))
    assert set(np.asarray(state.info["relief"]).tolist()) <= {0, 1}
    assert "gates" not in state.info
    fields = T.relief_fields(np, T.relief_rule(sprint_options("--relief-levels", "2")), 0)
    high = fields[1]
    heights, cell = high["heights_mm"], high["cell_mm"]
    r, c = np.unravel_index(np.argmax(heights), heights.shape)
    x = (high["x_range_mm"][0] + c * cell) / 1000.0
    y = (high["y_range_mm"][0] + r * cell) / 1000.0
    assert x > 0.5  # on the strip, ahead of the start's clearing
    top = heights[r, c] / 1000.0
    data = state.pipeline_state
    qpos = data.qpos.at[:, :3].set(jnp.asarray([x, y, top + 0.010 + 0.1]))
    state = state.replace(pipeline_state=data.replace(qpos=qpos, qvel=jnp.zeros_like(data.qvel)),
                          info={**state.info, "relief": jnp.asarray([0, 2, 0, 2], dtype=jnp.int32)})
    after = env.step(state, jnp.zeros((4, 1)))
    vz = np.asarray(after.pipeline_state.qvel[:, 2])
    assert vz[0] < -0.1 and vz[2] < -0.1  # level 0: the plane, the paw in the air
    assert vz[1] > vz[0] + 0.1 and vz[3] > vz[2] + 0.1  # level 2: held up by the strip


def test_a_sprint_without_race_terrain_is_unchanged() -> None:
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    opts = T.arguments(["bundle.json", "--out", "x.cxpolicy"])
    env = T.build_environment({"task": walker_task(), "model_xml": WALKER.encode("utf-8")}, opts,
                              count=2, seed=0, jax=jax, jnp=jnp, np=np, mujoco=mujoco, mjx=mjx)
    assert env.relief is None
    assert "relief" not in env.reset(jax.random.PRNGKey(0)).info
