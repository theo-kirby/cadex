# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-962: the trainer races its gates over race terrain, with a curriculum on relief.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_race_terrain_training.py`` from the repo.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

import cadex_goto as G
import cadex_train as T

#: A floor, a free base whose box touches the floor as a fall geom does, and a
#: paw sphere on a hinge, as leon VI's cut collides.
WALKER = """
<mujoco><option timestep="0.002"/><worldbody>
  <geom name="environment/floor" type="plane" size="0 0 0.1" contype="1" conaffinity="0"
        solref="0.004 1" friction="0.9 0.005 0.0001"/>
  <body name="base" pos="0 0 0.3"><freejoint/>
    <geom name="trunk" type="box" size="0.1 0.05 0.03" mass="1" contype="0" conaffinity="1"
          priority="1" condim="1"/>
    <body name="arm"><joint name="j" type="hinge" axis="0 1 0" range="-60 60" limited="true"/>
      <geom name="link" type="capsule" fromto="0 0 0 0 0 -0.08" size="0.01" mass="0.1"
            contype="0" conaffinity="0"/>
      <geom name="paw" type="sphere" size="0.015" pos="0 0 -0.1" mass="0.1" contype="0" conaffinity="1"/>
    </body>
  </body></worldbody>
<actuator><position name="j/position" joint="j" kp="5" forcelimited="true" forcerange="-2 2"/></actuator>
<sensor><framelinvel name="v" objtype="body" objname="base"/></sensor>
<keyframe><key name="home" qpos="0 0 0.3 1 0 0 0 0"/></keyframe></mujoco>"""


def walker_task(randomisation=()) -> dict:
    return {
        "episode": {"control_interval_s": 0.02, "solver_steps_per_action": 10, "max_steps": 500,
                    "reset_keyframe": "home"},
        "observations": [{"adr": 0, "dim": 3, "channels": ["vx", "vy", "vz"], "scale": 1000.0,
                          "kind": "body_linear_velocity", "name": "v", "target": "base", "unit": "mm/s"}],
        "actions": [{"actuator": "j/position", "joint": "j", "index": 0, "low": -30.0, "high": 30.0,
                     "scale": math.pi / 180.0, "kind": "position", "motion_type": "angular", "unit": "deg"}],
        "goal": [],
        "reward": [{"label": "bounce", "weight": -0.1, "expression": "(vz/1000)**2"}],
        "termination": [],
        "randomisation": list(randomisation),
    }


def options(*extra: str):
    return T.arguments(["bundle.json", "--out", "x.cxpolicy", "--gates", "--race-terrain", "u1",
                        "--relief-half", "2", *extra])


# -- the fields ---------------------------------------------------------------


def test_a_field_is_train_split_relief_round_the_start_that_no_race_meets() -> None:
    field = G.field_terrain(np, "u1", 3, half_m=2.0)
    assert field["split"] == "train" and field["course_kind"] == "field" and field["seed"] == 3
    again = G.field_terrain(np, "u1", 3, half_m=2.0)
    assert again["sha256"] == field["sha256"]
    assert G.field_terrain(np, "u1", 4, half_m=2.0)["sha256"] != field["sha256"]
    # Its extent is the square and the race's margin; no race's relief is it.
    margin = 1000.0 * G.RACE_TERRAIN["margin_m"]
    assert field["x_range_mm"][0] == pytest.approx(-2000.0 - margin)
    assert field["y_range_mm"][1] >= 2000.0 + margin
    for kind in ("gates", "sprint"):
        for split in ("train", "heldout"):
            course = {"kind": kind, "split": split, "seed": 3,
                      "gates": [{"xy_m": [sx * 2.0, sy * 2.0]} for sx in (-1, 1) for sy in (-1, 1)]}
            assert G.race_terrain(np, course, "u1")["sha256"] != field["sha256"]
    heights = field["heights_mm"]
    assert heights.min() >= 0.0
    # The start's clearing is flat, as a race's is.
    cell, x0, y0 = field["cell_mm"], field["x_range_mm"][0], field["y_range_mm"][0]
    c, r = int(round(-x0 / cell)), int(round(-y0 / cell))
    assert np.all(heights[r - 10:r + 11, c - 10:c + 11] == 0.0)
    with pytest.raises(SystemExit):
        G.field_terrain(np, "u1", 3, half_m=0.0)


def test_field_k_is_its_own_draw_scaled_to_k_of_the_levels() -> None:
    rule = T.relief_rule(options("--relief-levels", "3"))
    fields = T.relief_fields(np, rule, 5)
    assert [f["level"] for f in fields] == [1, 2, 3]
    for f in fields:
        raw = G.field_terrain(np, "u1", 5 * 3 + f["level"] - 1, half_m=2.0)
        assert np.allclose(f["heights_mm"], raw["heights_mm"] * f["level"] / 3)
        assert f["highest_mm"] == pytest.approx(raw["highest_mm"] * f["level"] / 3, abs=1e-3)
        assert f["hill_grade_deg"] == pytest.approx(math.degrees(math.atan(
            f["level"] / 3 * math.tan(math.radians(raw["hill_grade_deg"])))), abs=1e-3)
        assert f["rough_highest_mm"] <= G.RACE_TERRAIN["rough_mm"] * f["level"] / 3 + 1e-6
    assert len({f["sha256"] for f in fields}) == 3


def test_the_rule_needs_a_race_and_is_refused_out_of_its_bounds() -> None:
    rule = T.relief_rule(options())
    assert rule == {"kind": "u1", "levels": T.RELIEF_LEVELS, "half_m": 2.0,
                    "ceiling": {"start": 1, "falls": 0.1, "hold": 10}}
    assert T.relief_rule(T.arguments(["b.json", "--out", "x.cxpolicy", "--gates"])) is None
    assert T.relief_rule(T.arguments(["b.json", "--out", "x.cxpolicy", "--gates",
                                      "--race-terrain", "hills"]))["half_m"] == G.FIELD_HALF_M
    with pytest.raises(SystemExit):
        T.relief_rule(T.arguments(["b.json", "--out", "x.cxpolicy", "--race-terrain", "u1"]))
    for bad in (("--relief-levels", "0"), ("--relief-ceiling", "5,0.1,10"),
                ("--relief-ceiling", "1.5,0.1,10"), ("--relief-ceiling", "1,1.5,10"),
                ("--relief-ceiling", "1,0.1"), ("--relief-half", "-1")):
        with pytest.raises(SystemExit):
            T.relief_rule(options(*bad))


def test_the_top_rises_one_level_on_few_falls_after_its_hold_and_never_falls() -> None:
    rule = T.relief_rule(options("--relief-ceiling", "1,0.1,3"))
    top, since = 1, 0
    top, since = T.relief_top_next(top, since, 0.0, rule)  # held 1 of 3
    top, since = T.relief_top_next(top, since, 0.0, rule)  # held 2 of 3
    assert (top, since) == (1, 2)
    assert T.relief_top_next(top, since, 0.2, rule) == (1, 3)  # too many falls
    assert T.relief_top_next(top, since, None, rule) == (1, 3)  # nothing ended
    assert T.relief_top_next(top, since, float("nan"), rule) == (1, 3)
    assert T.relief_top_next(top, since, 0.1, rule) == (2, 0)
    assert T.relief_top_next(4, 50, 0.0, rule) == (4, 51)  # the last level is the top


# -- the model ----------------------------------------------------------------


def _model():
    import mujoco

    rule = T.relief_rule(options("--relief-levels", "2"))
    fields = T.relief_fields(np, rule, 0)
    model, placed = T.relief_model(mujoco, np, WALKER.encode(), fields)
    return mujoco, rule, fields, model, placed


def test_the_relief_is_the_last_body_and_moves_no_other_index() -> None:
    mujoco, _rule, fields, model, placed = _model()
    base = mujoco.MjModel.from_xml_string(WALKER)
    assert model.nbody == base.nbody + 1 and model.body(model.nbody - 1).name == "environment/relief"
    assert model.ngeom == base.ngeom + 2
    for g in range(base.ngeom):
        assert model.geom(g).name == base.geom(g).name
    for b in range(base.nbody):
        assert model.body(b).name == base.body(b).name
    assert placed["geoms"] == [base.ngeom, base.ngeom + 1]
    floor = model.geom("environment/floor")
    for g, field in zip(placed["geoms"], fields):
        assert int(model.geom_type[g]) == int(mujoco.mjtGeom.mjGEOM_HFIELD)
        for name in ("solref", "friction", "condim"):
            assert np.allclose(getattr(model.geom(g), name), getattr(floor, name)), name
        # Sunk under the plane past the highest field's top until a level raises it.
        assert model.geom_pos[g][2] == pytest.approx(-placed["sink_m"])
        assert placed["sink_m"] == pytest.approx(
            T.RELIEF_SINK_M + 0.001 * max(f["highest_mm"] for f in fields))
        # Its data is the field's heights over its top.
        h = int(model.geom_dataid[g])
        adr, n = int(model.hfield_adr[h]), int(model.hfield_nrow[h] * model.hfield_ncol[h])
        assert np.allclose(model.hfield_data[adr:adr + n] * model.hfield_size[h][2] * 1000.0,
                           field["heights_mm"].ravel(), atol=1e-3 * field["highest_mm"] + 1e-3)


def test_only_the_floors_spheres_and_capsules_touch_the_relief() -> None:
    mujoco, _rule, fields, model, placed = _model()

    def touch(a: int, b: int) -> bool:
        return bool(model.geom_contype[a] & model.geom_conaffinity[b]
                    or model.geom_contype[b] & model.geom_conaffinity[a])

    relief = placed["geoms"][0]
    assert placed["paws"] == ["paw"]
    assert touch(relief, model.geom("paw").id)
    assert not touch(relief, model.geom("trunk").id)  # a box keeps the plane only (ADR-854)
    assert not touch(relief, model.geom("link").id)  # it never touched the floor
    assert not touch(relief, model.geom("environment/floor").id)
    # The paw and the trunk still touch the plane as before.
    assert touch(model.geom("environment/floor").id, model.geom("paw").id)
    assert touch(model.geom("environment/floor").id, model.geom("trunk").id)
    boxy = WALKER.replace('type="sphere" size="0.015"', 'type="box" size="0.015 0.015 0.015"')
    with pytest.raises(SystemExit):
        T.relief_model(mujoco, np, boxy.encode(), fields)


def test_a_paw_meets_only_its_episodes_field_in_mjx() -> None:
    import jax.numpy as jnp
    import mujoco.mjx as mjx

    _mujoco, _rule, fields, model, placed = _model()
    m = mjx.put_model(model)
    high = fields[1]
    heights, cell = high["heights_mm"], high["cell_mm"]
    r, c = np.unravel_index(np.argmax(heights), heights.shape)
    x = (high["x_range_mm"][0] + c * cell) / 1000.0
    y = (high["y_range_mm"][0] + r * cell) / 1000.0
    top = heights[r, c] / 1000.0
    low_there = G.terrain_ground(np, fields[0])(1000.0 * x, 1000.0 * y) / 1000.0
    assert low_there < top - 0.05
    # The paw's centre 10 mm over field 2's peak: 5 mm into it, clear of field 1.
    qpos = jnp.asarray([x, y, top + 0.010 + 0.1, 1, 0, 0, 0, 0], dtype=jnp.float32)
    data = mjx.make_data(m).replace(qpos=qpos)
    relief = set(placed["geoms"])
    for level, expected in ((0, None), (1, None), (2, placed["geoms"][1])):
        # The environment's own layer, as the step lays it.
        z = jnp.where(jnp.arange(1, 3) == level, 0.0, -placed["sink_m"])
        laid = m.replace(geom_pos=m.geom_pos.at[jnp.asarray(placed["geoms"]), 2].set(z))
        contact = mjx.forward(laid, data)._impl.contact
        hits = {int(g) for pair, dist in zip(np.asarray(contact.geom), np.asarray(contact.dist))
                for g in pair if dist < 0 and int(g) in relief}
        assert hits == (set() if expected is None else {expected}), level
        if expected is not None:
            near = [float(dist) for pair, dist in zip(np.asarray(contact.geom), np.asarray(contact.dist))
                    if expected in pair.tolist() and dist < 0]
            assert min(near) == pytest.approx(-0.005, abs=1e-4)


def test_a_drawn_field_extends_to_the_relief_and_its_friction_follows_the_floor() -> None:
    import mujoco

    rule = T.relief_rule(options("--relief-levels", "2"))
    fields = T.relief_fields(np, rule, 0)
    task = walker_task([
        {"label": "floor_friction", "low": 0.4, "high": 1.0, "mode": "scale",
         "fields": [{"field": "geom_friction", "index": 0}]},
        {"label": "mass", "low": 0.9, "high": 1.1, "mode": "scale",
         "fields": [{"field": "body_mass", "index": 1}]}])
    _plain, plain = T.randomised_models(mujoco, np, WALKER.encode(), task, base_seed=7, count=3)
    host, drawn, placed = T.relief_randomised(mujoco, np, WALKER.encode(), task, fields,
                                              base_seed=7, count=3)
    assert drawn["geom_friction"].shape == (3, host.ngeom, 3)
    assert np.array_equal(drawn["geom_friction"][:, :placed["geoms"][0]], plain["geom_friction"])
    for g in placed["geoms"]:
        assert np.array_equal(drawn["geom_friction"][:, g], plain["geom_friction"][:, 0])
    assert drawn["body_mass"].shape == (3, host.nbody)
    assert np.array_equal(drawn["body_mass"][:, :-1], plain["body_mass"])
    # Environment 0's draw is the host's.
    assert np.array_equal(host.geom_friction, drawn["geom_friction"][0])
    assert np.array_equal(host.body_mass, drawn["body_mass"][0])


# -- the environment and the header -------------------------------------------


def _environment(*extra: str):
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    opts = options("--relief-levels", "2", *extra)
    bundle = {"task": T.gate_task(walker_task(), opts), "model_xml": WALKER.encode("utf-8")}
    env = T.build_environment(bundle, opts, count=4, seed=0, jax=jax, jnp=jnp, np=np,
                              mujoco=mujoco, mjx=mjx)
    return env, jax, jnp


def test_each_episode_stands_on_a_level_under_the_top_and_the_step_lays_it() -> None:
    env, jax, jnp = _environment("--relief-ceiling", "1,0.1,0")
    assert env.relief["levels"] == 2 and [f["level"] for f in env.relief["fields"]] == [1, 2]
    assert env.relief["paws"] == ["paw"]
    json.dumps(env.relief)  # the header carries it
    state = env.reset(jax.random.PRNGKey(0))
    assert set(np.asarray(state.info["relief"]).tolist()) <= {0, 1}
    assert np.asarray(state.info["relief_top"]).tolist() == [1] * 4
    # Over field 2's peak with the paw 5 mm into it: on level 2 the field holds
    # it up; on level 0 the paw is in the air.
    high = next(f for f in env.relief["fields"] if f["level"] == 2)
    fields = T.relief_fields(np, T.relief_rule(options("--relief-levels", "2")), 0)
    heights, cell = fields[1]["heights_mm"], high["cell_mm"]
    r, c = np.unravel_index(np.argmax(heights), heights.shape)
    x = (high["x_range_mm"][0] + c * cell) / 1000.0
    y = (high["y_range_mm"][0] + r * cell) / 1000.0
    top = heights[r, c] / 1000.0
    data = state.pipeline_state
    qpos = data.qpos.at[:, :3].set(jnp.asarray([x, y, top + 0.010 + 0.1]))
    qvel = jnp.zeros_like(data.qvel)
    level = jnp.asarray([0, 2, 0, 2], dtype=jnp.int32)
    state = state.replace(pipeline_state=data.replace(qpos=qpos, qvel=qvel),
                          info={**state.info, "relief": level})
    after = env.step(state, jnp.zeros((4, 1)))
    vz = np.asarray(after.pipeline_state.qvel[:, 2])
    assert vz[0] < -0.1 and vz[2] < -0.1  # falling freely
    assert vz[1] > vz[0] + 0.1 and vz[3] > vz[2] + 0.1  # held up by the relief
    assert np.asarray(after.info["relief"]).tolist() == [0, 2, 0, 2]  # nothing ended


def test_a_fresh_episode_draws_its_level_up_to_the_top_the_loop_wrote() -> None:
    env, jax, jnp = _environment("--relief-ceiling", "0,0.1,0")
    state = env.reset(jax.random.PRNGKey(1))
    assert np.asarray(state.info["relief"]).tolist() == [0] * 4  # top 0: the plane only
    seen = set()
    for i in range(20):
        # Every episode ends now, so every environment draws afresh.
        state = state.replace(info={**state.info, "relief_top": jnp.full((4,), 2, jnp.int32),
                                    "steps": jnp.full((4,), 10_000, jnp.int32)})
        state = env.step(state, jnp.zeros((4, 1)))
        seen |= set(np.asarray(state.info["relief"]).tolist())
    assert seen == {0, 1, 2}


def test_without_race_terrain_the_environment_is_unchanged() -> None:
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    opts = T.arguments(["bundle.json", "--out", "x.cxpolicy", "--gates"])
    bundle = {"task": T.gate_task(walker_task(), opts), "model_xml": WALKER.encode("utf-8")}
    env = T.build_environment(bundle, opts, count=2, seed=0, jax=jax, jnp=jnp, np=np,
                              mujoco=mujoco, mjx=mjx)
    assert env.relief is None
    state = env.reset(jax.random.PRNGKey(0))
    assert "relief" not in state.info and "relief_top" not in state.info
    assert state.pipeline_state.qpos.shape == (2, 8)


def test_a_scanning_or_pooled_bundle_is_refused() -> None:
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    opts = options()
    task = {**T.gate_task(walker_task(), opts), "terrain": {"pool": [{}]}}
    with pytest.raises(SystemExit, match="race-terrain"):
        T.build_environment({"task": task, "model_xml": WALKER.encode("utf-8")}, opts, count=2,
                            seed=0, jax=jax, jnp=jnp, np=np, mujoco=mujoco, mjx=mjx)


def test_the_policy_header_names_the_relief_and_its_curriculum() -> None:
    import inspect

    source = inspect.getsource(T.policy_header)
    assert '"race_terrain": {**trained["relief"]' in source
    assert 'if trained.get("relief") else {}' in source


def test_the_loop_reads_falls_per_horizon_of_steps_and_moves_the_top_between_iterations() -> None:
    import inspect

    source = inspect.getsource(T.train)
    # A fall rate that time-outs landing in the batch or not cannot move.
    assert 'report["relief_falls"] = fell * jnp.float32(env.horizon) / jnp.float32(unroll * envs)' in source
    assert 'moved["relief_top"] = jnp.full((envs,), relief_top, jnp.int32)' in source
    assert "relief_top_next(relief_top, relief_since," in source
