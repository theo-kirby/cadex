# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-955..957: gate racing, its trainer task, its judge's traces and the gallop guide.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_gate_race.py`` from the repo.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

import cadex_goto as G
import cadex_train as T

#: A free box that floats (no gravity, no contact), so its velocity over a
#: step is exactly what the test gives it, with one hinge for an action.
FLOATER = """
<mujoco><option timestep="0.01" gravity="0 0 0"/><worldbody>
  <body name="base" pos="0 0 0.2"><freejoint/>
    <geom type="box" size="0.1 0.05 0.03" mass="1" contype="0" conaffinity="0"/>
    <body name="arm"><joint name="j" type="hinge" axis="0 0 1" range="-60 60" limited="true"/>
      <geom type="sphere" size="0.02" pos="0.1 0 0" mass="0.1" contype="0" conaffinity="0"/></body>
  </body></worldbody>
<actuator><position name="j/position" joint="j" kp="5" forcelimited="true" forcerange="-2 2"/></actuator>
<sensor><framelinvel name="v" objtype="body" objname="base"/></sensor>
<keyframe><key name="home" qpos="0 0 0.2 1 0 0 0 0"/></keyframe></mujoco>"""


def floater_task() -> dict:
    return {
        "episode": {"control_interval_s": 0.02, "solver_steps_per_action": 2, "max_steps": 500,
                    "reset_keyframe": "home"},
        "observations": [{"adr": 0, "dim": 3, "channels": ["vx", "vy", "vz"], "scale": 1000.0,
                          "kind": "body_linear_velocity", "name": "v", "target": "base", "unit": "mm/s"}],
        "actions": [{"actuator": "j/position", "joint": "j", "index": 0, "low": -30.0, "high": 30.0,
                     "scale": math.pi / 180.0, "kind": "position", "motion_type": "angular", "unit": "deg"}],
        "goal": [{"name": "cx", "channels": ["cx"], "kind": "value", "unit": "mm/s", "low": -500.0,
                  "high": 500.0, "nominal": [0.0], "resample_steps": 100, "segments": 1}],
        "reward": [{"label": "tracking", "weight": 0.02, "expression": "exp(-((cx-vx)/1000)**2)"},
                   {"label": "bounce", "weight": -0.1, "expression": "(vz/1000)**2"}],
        "termination": [],
    }


def gate_options(*extra: str):
    return T.arguments(["bundle.json", "--out", "x.cxpolicy", "--gates", *extra])


# -- the course source --------------------------------------------------------


def test_a_gate_course_is_its_seed_and_split_and_the_splits_never_meet() -> None:
    a = G.gate_course(3, split="heldout")
    assert a == G.gate_course(3, split="heldout")
    train = {json.dumps(G.gate_course(s, split="train")["gates"]) for s in range(200)}
    heldout = {json.dumps(G.gate_course(s, split="heldout")["gates"]) for s in range(200)}
    assert len(train) == len(heldout) == 200 and not train & heldout
    # Its own stream: no course is a go-to-point sequence's points.
    bands = [{"name": "walk", "low": 0.4, "high": 0.7}]
    assert [g["xy_m"] for g in a["gates"]] != [p["xy_m"] for p in
                                                G.sequence(3, split="heldout", bands=bands)["points"]]


def test_a_gate_course_honours_its_shape_and_carries_no_speed_or_hold() -> None:
    course = G.gate_course(0, split="heldout", gates=16, radius_m=0.3)
    kinds = [g["bearing"] for g in course["gates"]]
    assert len(kinds) == 16 and kinds.count("behind") >= 2 and kinds.count("side") >= 3
    assert course["radius_m"] == 0.3
    x = y = 0.0
    for gate in course["gates"]:
        assert set(gate) == {"xy_m", "bearing"}
        leg = math.hypot(gate["xy_m"][0] - x, gate["xy_m"][1] - y)
        assert 1.0 - 1e-3 <= leg <= 4.0 + 1e-3
        x, y = gate["xy_m"]
    assert G.course_length_m(course) == pytest.approx(
        sum(math.hypot(b["xy_m"][0] - a["xy_m"][0], b["xy_m"][1] - a["xy_m"][1])
            for a, b in zip([{"xy_m": [0, 0]}] + course["gates"], course["gates"])))
    with pytest.raises(SystemExit):
        G.gate_course(0, split="heldout", radius_m=0.6)  # gates would overlap
    with pytest.raises(SystemExit):
        G.gate_course(0, split="test")


# -- the race's logic ---------------------------------------------------------


def _plan():
    return G.gate_stack(np, [{"gates": [{"xy_m": [2.0, 0.0]}, {"xy_m": [2.0, 3.0]}, {"xy_m": [-1.0, 3.0]}],
                              "radius_m": 0.25}])


def test_entering_a_gate_lights_the_next_at_once_and_nothing_past_the_last() -> None:
    plan = _plan()
    state = G.gate_start(np, [1])
    one = lambda x, y: G.gate_step(np, plan, state, np.array([x]), np.array([y]))  # noqa: E731
    for x in (0.0, 1.0, 1.74):  # outside the 0.25 m circle: not entered
        state, entered = one(x, 0.0)
        assert int(state["index"][0]) == 0 and not entered[0]
    state, entered = one(1.80, 0.1)  # inside it
    assert int(state["index"][0]) == 1 and entered[0]
    state, entered = one(1.80, 0.1)  # the next is lit; standing here enters nothing more
    assert int(state["index"][0]) == 1 and not entered[0]
    # The third gate cannot be entered before the second.
    state, entered = one(-1.0, 3.0)
    assert int(state["index"][0]) == 1 and not entered[0]
    for x, y in ((2.0, 3.0), (-1.0, 3.0)):
        state, entered = one(x, y)
        assert entered[0]
    assert int(state["index"][0]) == 3
    state, entered = one(-1.0, 3.0)
    assert int(state["index"][0]) == 3 and not entered[0]


def test_the_policy_sees_the_next_gates_in_its_heading_frame() -> None:
    plan = _plan()
    index = np.array([0])
    # At the origin facing +y: gate 0 (2, 0) is 2 m to the right, gate 1 (2, 3) 3 ahead, 2 right.
    view = G.gate_view(np, plan, index, np.array([0.0]), np.array([0.0]), np.array([math.pi / 2]), 2)
    assert np.allclose(view[0], [0.0, -2.0, 3.0, -2.0], atol=1e-6)
    assert G.gate_channel_names(2) == ["gate0_x", "gate0_y", "gate1_x", "gate1_y"]
    # Far away the reading is clipped; past the last gate it reads the last.
    far = G.gate_view(np, plan, index, np.array([-20.0]), np.array([0.0]), np.array([0.0]), 1)
    assert np.allclose(far[0], [G.GATE_VIEW_M, 0.0])
    done = G.gate_view(np, plan, np.array([3]), np.array([0.0]), np.array([3.0]), np.array([0.0]), 2)
    assert np.allclose(done[0], [-1.0, 0.0, -1.0, 0.0])


def test_progress_is_the_speed_made_good_toward_the_lit_gate() -> None:
    plan = _plan()
    at = lambda i, vx, vy: float(G.gate_speed(np, plan, np.array([i]), np.array([0.0]),  # noqa: E731
                                              np.array([0.0]), np.array([vx]), np.array([vy]))[0])
    assert at(0, 3.0, 0.0) == pytest.approx(3.0)  # straight at it
    assert at(0, 0.0, 2.0) == pytest.approx(0.0)  # across the line to it
    assert at(0, -1.0, 0.0) == pytest.approx(-1.0)  # away
    assert at(1, 0.0, 1.0) == pytest.approx(3.0 / math.hypot(2.0, 3.0))
    assert at(3, 3.0, 0.0) == 0.0  # the course is done


# -- the trainer's task -------------------------------------------------------


def test_a_race_is_told_gates_not_speeds_and_keeps_the_regularisers() -> None:
    task = floater_task()
    raced = T.gate_task(task, gate_options())
    assert raced["goal"] == [] and [t["label"] for t in raced["reward"]] == ["bounce"]
    assert raced["gates"]["dropped_reward"] == ["tracking"]
    assert T.channels(raced) == ["vx", "vy", "vz", "gate0_x", "gate0_y", "gate1_x", "gate1_y"]
    assert T.actor_channels(raced)[-4:] == ["gate0_x", "gate0_y", "gate1_x", "gate1_y"]
    assert len(T.sensor_variance_floor(raced)) == len(T.channels(raced))
    assert T.gate_task(task, T.arguments(["b", "--out", "x"])) is task  # off: unchanged
    for flag in (["--goto", "walk:0.4-0.7"], ["--gate-ahead", "0"]):
        with pytest.raises(SystemExit):
            T.gate_task(task, gate_options(*flag))
    stopping = {**task, "termination": [{"expression": "cx", "above": 1.0, "below": None, "label": "x"}]}
    with pytest.raises(SystemExit):
        T.gate_task(stopping, gate_options())


def test_the_ceiling_rises_only_when_the_population_reaches_it_and_the_guide_fades() -> None:
    rule = T.gate_rule(gate_options())
    assert rule["weights"] == {"progress": 1.0, "entry": 0.5, "time": 0.1}
    ceiling = rule["ceiling"]
    assert ceiling == {"start": 0.5, "step": 0.25, "max": 6.0, "promote": 0.7}
    assert T.gate_ceiling_next(0.5, 0.34, ceiling) == 0.5
    assert T.gate_ceiling_next(0.5, 0.35, ceiling) == 0.75
    assert T.gate_ceiling_next(5.9, 5.0, ceiling) == 6.0
    assert T.gate_ceiling_next(1.0, float("nan"), ceiling) == 1.0
    with pytest.raises(SystemExit):
        T.gate_rule(gate_options("--gate-ceiling", "1,0.1,0.5,0.7"))  # start above max
    assert [T.reference_weight_at(i, 0.5, 100) for i in (0, 50, 100, 150)] == [0.5, 0.25, 0.0, 0.0]
    assert T.reference_weight_at(10_000, 0.5, 0) == 0.5


def _environment(*extra: str):
    import jax
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx

    options = gate_options("--gate-weights", "1,0.5,0.25", "--gate-ceiling", "0.5,0.25,6,0.7", *extra)
    bundle = {"task": T.gate_task(floater_task(), options), "model_xml": FLOATER.encode("utf-8")}
    env = T.build_environment(bundle, options, count=2, seed=0, jax=jax, jnp=jnp, np=np,
                              mujoco=mujoco, mjx=mjx)
    return env, jax, jnp


def test_the_trainer_pays_capped_progress_an_entry_and_time_and_shows_the_next_gates() -> None:
    env, jax, jnp = _environment()
    state = env.reset(jax.random.PRNGKey(0))
    # A known course: environment 0's first pooled course, unturned, from the origin.
    gates = state.info["gates"]
    gates = {**gates, "pick": jnp.zeros(2, jnp.int32), "turn": jnp.zeros(2), "start": jnp.zeros((2, 2))}
    course = G.gate_course(0, split="train", gates=T.GATE_TRAIN_GATES, radius_m=0.25)
    g0, g1 = (np.asarray(course["gates"][k]["xy_m"]) for k in (0, 1))
    toward = (g0 - g0 / np.linalg.norm(g0) * 1.0)  # 1 m short of gate 0, on the line to it
    unit = g0 / np.linalg.norm(g0)
    data = state.pipeline_state
    qpos = data.qpos.at[:, :2].set(jnp.asarray([toward, g0 - unit * 0.1]))
    # Environment 0 heads for the gate at 2 m/s, past the 0.5 m/s ceiling;
    # environment 1 stands inside it.
    qvel = data.qvel.at[0, :2].set(jnp.asarray(unit * 2.0))
    state = state.replace(pipeline_state=data.replace(qpos=qpos, qvel=qvel),
                          info={**state.info, "gates": gates})
    after = env.step(state, jnp.zeros((2, 1)))
    dt = 0.02
    paid = np.asarray(after.reward)
    assert paid[0] == pytest.approx(1.0 * dt * 0.5 - 0.25 * dt, abs=1e-5)  # capped at the ceiling
    assert paid[1] == pytest.approx(0.5 - 0.25 * dt, abs=1e-5)  # entered: the bonus, no progress
    assert np.asarray(after.info["gates"]["index"]).tolist() == [0, 1]
    assert np.asarray(after.info["gate_entered"]).tolist() == [0.0, 1.0]
    # The policy now reads gate 1 first in environment 1, gate 0 in environment 0.
    seen = np.asarray(after.obs["state"])
    position = np.asarray(after.pipeline_state.qpos[:, :2])
    assert np.allclose(seen[1, 3:5], g1 - position[1], atol=1e-4)
    assert np.allclose(seen[0, 3:5], g0 - position[0], atol=1e-4)
    # The ceiling is the train loop's: raised, the same speed pays more.
    raised = state.replace(info={**state.info, "gate_ceiling": jnp.full((2,), 3.0)})
    assert float(env.step(raised, jnp.zeros((2, 1))).reward[0]) == pytest.approx(
        1.0 * dt * 2.0 - 0.25 * dt, abs=1e-4)


def test_a_policy_header_names_the_race_and_no_other_header_changes() -> None:
    import inspect

    source = inspect.getsource(T.policy_header)
    assert 'not key.startswith("gate") or getattr(options, "gates", False)' in source
    assert '"gates": {**gate_rule(options), "channels": gate_channels(task)' in source
    assert T.gate_channels(floater_task()) == []


# -- the judge and its traces -------------------------------------------------


def test_a_race_is_judged_gate_by_gate() -> None:
    course = {"gates": [{"xy_m": [2.0, 0.0], "bearing": "ahead"}, {"xy_m": [2.0, 3.0], "bearing": "side"},
                        {"xy_m": [-1.0, 3.0], "bearing": "side"}]}
    judged = G.judge_race(course, [1.0, 4.0], 9.0, True, 8.5)
    assert judged["passed"] == 2 and judged["of"] == 3 and not judged["finished"]
    assert [r["leg_s"] for r in judged["gates"][:2]] == [1.0, 3.0]
    assert judged["gates"][1]["leg_speed_mps"] == 1.0 and "at_s" not in judged["gates"][2]
    assert judged["mean_speed_mps"] == pytest.approx(5.0 / 4.0) and judged["fell"] and not judged["stalled"]


def test_drive_load_reads_rms_against_rated_and_the_peak_against_the_clamp() -> None:
    import mujoco

    model = mujoco.MjModel.from_xml_string(FLOATER)
    reading = {"rms_nm": {"j/position": 0.8}, "peak_nm": {"j/position": 1.5}}
    load = G.drive_load(reading, model, 1.6)
    assert load["rms_over_rated"] == {"j/position": 0.5} and load["peak_over_peak"] == {"j/position": 0.75}
    assert load["worst_rms_over_rated"] == 0.5 and load["peak_nm_clamp"] == {"j/position": 2.0}
    assert G.drive_load(reading, model, None)["rms_over_rated"] is None


def test_a_view_carries_what_the_motors_did_in_the_engine_rollouts_units(tmp_path) -> None:
    # ADR-956: the Activations editor reads joint_positions, joint_velocities
    # and actuator_efforts per frame, in actuator_channels order (ADR-694's units).
    import mujoco

    model = mujoco.MjModel.from_xml_string(FLOATER)
    poses = [model.key_qpos[0].copy() for _ in range(3)]
    poses[1][7] = 0.5
    rates = [np.zeros(model.nv) for _ in range(3)]
    rates[2][6] = -1.0
    efforts = [np.array([0.25]), np.array([-1.5]), np.array([2.0])]
    goto = {"sequence": {"points": [{"xy_m": [1.0, 0.0], "speed_mps": 0.0, "radius_m": 0.25}]},
            "frames": [{"index": 0}] * 3}
    trace = json.loads(T.write_view(tmp_path, FLOATER.encode(), poses, 0.04, source="test", goto=goto,
                                    velocities=rates, efforts=efforts, rated_nm=1.6).read_text())
    channel = trace["actuator_channels"][0]
    assert channel["joint"] == "j" and channel["joint_unit"] == "deg" and channel["effort_unit"] == "N·mm"
    assert (channel["low"], channel["high"]) == pytest.approx((-60.0, 60.0))
    assert (channel["effort_low"], channel["effort_high"], channel["effort_rated"]) == (-2000.0, 2000.0, 1600.0)
    frames = trace["frames"]
    assert [f["joint_positions"][0] for f in frames] == pytest.approx([0.0, math.degrees(0.5), 0.0], abs=1e-3)
    assert [f["joint_velocities"][0] for f in frames] == pytest.approx([0.0, 0.0, -math.degrees(1.0)], abs=1e-3)
    assert [f["actuator_efforts"][0] for f in frames] == [250.0, -1500.0, 2000.0]
    assert frames[0]["goto"] == {"index": 0} and trace["goto"]["points"][0]["radius_m"] == 0.25
    # Without the rollout's rates and forces only the positions are written.
    bare = json.loads(T.write_view(tmp_path / "b", FLOATER.encode(), poses, 0.04, source="t").read_text())
    assert "joint_positions" in bare["frames"][0] and "actuator_efforts" not in bare["frames"][0]


def test_the_dashboard_reads_a_race_trace_as_a_goto_episode_with_motors(tmp_path) -> None:
    # The served shape (cli/cadex_cli/review_server.trace_playback) without importing the
    # server: its goto points need xy_m and speed_mps, its frames an index.
    import mujoco

    model = mujoco.MjModel.from_xml_string(FLOATER)
    course = G.gate_course(1, split="heldout", gates=5)
    judged = G.judge_race(course, [2.0], 6.0, False, None)
    poses = [model.key_qpos[0]] * 2
    drawn = {"points": [{"xy_m": g["xy_m"], "radius_m": 0.25, "band": "gate",
                         "speed_mps": float(r.get("leg_speed_mps") or 0.0)}
                        for g, r in zip(course["gates"], judged["gates"])]}
    trace = json.loads(T.write_view(tmp_path, FLOATER.encode(), poses, 0.04, source="t",
                                    goto={"sequence": drawn, "frames": [{"index": 0}, {"index": 1}]},
                                    velocities=[np.zeros(model.nv)] * 2, efforts=[np.zeros(1)] * 2
                                    ).read_text())
    assert all(isinstance(p["speed_mps"], float) and len(p["xy_m"]) == 2 for p in trace["goto"]["points"])
    assert trace["goto"]["points"][0]["speed_mps"] > 0.0 and trace["goto"]["points"][1]["speed_mps"] == 0.0
    assert all({"joint_positions", "joint_velocities", "actuator_efforts"} <= set(f) for f in trace["frames"])


def test_the_gallop_guide_pays_the_nearest_stride_sample_in_pose_and_rate(tmp_path) -> None:
    # ADR-957: a clip JSON (four samples) on the floater; at a sample's pose
    # and rate the guide pays its full weight, and the rate's sign matters.
    clip = {"schema": "cadex-gait-clip-v1", "gait": "test", "joints": ["j"], "sample_dt_s": 0.02,
            "joint_angles_rad": [[0.0], [0.1], [0.2], [0.1]], "parameters": {"speed_m_s": 1.0}}
    path = tmp_path / "clip.json"
    path.write_text(json.dumps(clip))
    env, jax, jnp = _environment("--gait-reference", str(path), "--reference-weight", "2.0")
    assert env.guide["samples"] == 4
    state = env.reset(jax.random.PRNGKey(0))
    data = state.pipeline_state
    # Environment 0 stands at sample 0 (0 rad, still); environment 1 is at the
    # same pose but turning at 5 rad/s, a rate no sample near that pose has.
    qpos = data.qpos.at[:, 7].set(0.0)
    qvel = data.qvel.at[:, 6].set(jnp.asarray([0.0, -5.0]))
    held = state.replace(pipeline_state=data.replace(qpos=qpos, qvel=qvel))
    paid = np.asarray(env.step(held, jnp.zeros((2, 1))).reward)
    assert paid[0] == pytest.approx(2.0 * 0.02 * 1.0 - 0.25 * 0.02, abs=1e-3)
    assert paid[1] < paid[0] - 0.003
    guide = T.reference_guide(FLOATER.encode(), floater_task(),
                              T.arguments(["b", "--out", "x", "--gait-reference", str(path)]),
                              __import__("mujoco"), np)
    assert np.allclose(guide["dq"][:, 0], [0.0, 5.0, 0.0, -5.0]) and guide["joints"] == ["j"]
