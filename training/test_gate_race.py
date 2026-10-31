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


def test_a_sprint_course_is_its_seed_and_split_and_meets_no_other_course() -> None:
    # ADR-960.
    a = G.sprint_course(3, split="heldout")
    assert a == G.sprint_course(3, split="heldout")
    train = {json.dumps(G.sprint_course(s, split="train")["gates"]) for s in range(200)}
    heldout = {json.dumps(G.sprint_course(s, split="heldout")["gates"]) for s in range(200)}
    assert len(train) == len(heldout) == 200 and not train & heldout
    gates = {json.dumps(G.gate_course(s, split=sp, gates=8)["gates"]) for s in range(200)
             for sp in G.SPLITS}
    assert not (train | heldout) & gates


def test_a_sprint_course_turns_within_its_bound_and_spaces_its_gates() -> None:
    turns = []
    for seed in range(100):
        course = G.sprint_course(seed, split="train")
        assert course["kind"] == "sprint" and course["schema"] == G.GATE_SCHEMA
        assert course["radius_m"] == 0.25 and len(course["gates"]) == 8
        x = y = heading = 0.0
        for gate in course["gates"]:
            assert set(gate) == {"xy_m", "bearing"} and gate["bearing"] == "ahead"
            dx, dy = gate["xy_m"][0] - x, gate["xy_m"][1] - y
            assert 2.0 - 1e-3 <= math.hypot(dx, dy) <= 4.0 + 1e-3
            leg = math.atan2(dy, dx)
            turn = math.degrees(math.atan2(math.sin(leg - heading), math.cos(leg - heading)))
            assert abs(turn) <= 30.0 + 0.01
            turns.append(turn)
            x, y, heading = gate["xy_m"][0], gate["xy_m"][1], leg
    # Both ways, and out to the bound.
    assert min(turns) < -25.0 and max(turns) > 25.0
    course = G.sprint_course(0, split="heldout", gates=5, turn_deg=10.0, radius_m=0.3)
    assert len(course["gates"]) == 5 and course["radius_m"] == 0.3
    with pytest.raises(SystemExit):
        G.sprint_course(0, split="heldout", radius_m=1.0)  # gates would overlap
    with pytest.raises(SystemExit):
        G.sprint_course(0, split="test")
    with pytest.raises(SystemExit):
        G.sprint_course(0, split="train", turn_deg=120.0)


def test_the_gates_verb_draws_either_kind_at_its_own_default_length(capsys) -> None:
    assert G.main(["cadex_goto.py", "gates", "--sprint", "--seed", "4", "--split", "train"]) == 0
    assert json.loads(capsys.readouterr().out) == G.sprint_course(4, split="train")
    assert G.main(["cadex_goto.py", "gates", "--seed", "4", "--split", "train"]) == 0
    assert json.loads(capsys.readouterr().out) == G.gate_course(4, split="train")
    assert G.main(["cadex_goto.py", "gates", "--sprint", "--gates", "3", "--radius", "0.3"]) == 0
    assert json.loads(capsys.readouterr().out) == G.sprint_course(0, split="heldout", gates=3,
                                                                  radius_m=0.3)


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
    assert rule["weights"] == {"progress": 1.0, "entry": 0.5, "time": 0.1, "backward": 0.0}
    assert T.gate_rule(gate_options("--gate-backward", "1"))["weights"]["backward"] == 1.0
    with pytest.raises(SystemExit):
        T.gate_rule(gate_options("--gate-backward", "-0.5"))
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


def test_lead_is_the_speed_along_the_bases_own_heading() -> None:
    lead = lambda yaw, vx, vy: float(G.gate_lead(np, np.array([yaw]), np.array([vx]),  # noqa: E731
                                                 np.array([vy]))[0])
    assert lead(0.0, 2.0, 0.0) == pytest.approx(2.0)  # fore end first
    assert lead(0.0, -2.0, 0.0) == pytest.approx(-2.0)  # hind end first
    assert lead(math.pi / 2, 0.0, 1.5) == pytest.approx(1.5)
    assert lead(math.pi, 1.0, 0.0) == pytest.approx(-1.0)
    assert lead(0.0, 0.0, 3.0) == pytest.approx(0.0)  # sideways


def test_the_backward_cost_charges_only_hind_first_speed() -> None:
    env, jax, jnp = _environment("--gate-backward", "0.8")
    state = env.reset(jax.random.PRNGKey(0))
    gates = {**state.info["gates"], "pick": jnp.zeros(2, jnp.int32), "turn": jnp.zeros(2),
             "start": jnp.zeros((2, 2))}
    data = state.pipeline_state
    far = jnp.asarray([[-50.0, -50.0], [-50.0, -50.0]])  # far from every gate: no entry
    # Both environments head +x in the world, unturned: 0 runs fore end first
    # at 1 m/s, 1 hind end first at 1 m/s.
    qvel = data.qvel.at[:, :2].set(jnp.asarray([[1.0, 0.0], [-1.0, 0.0]]))
    state = state.replace(pipeline_state=data.replace(qpos=data.qpos.at[:, :2].set(far), qvel=qvel),
                          info={**state.info, "gates": gates})
    off_env, _, _ = _environment()
    after = env.step(state, jnp.zeros((2, 1)))
    plain = off_env.step(state, jnp.zeros((2, 1)))
    lead = np.asarray(after.info["gate_lead"])
    assert lead[0] > 0.0 > lead[1]
    paid, base = np.asarray(after.reward), np.asarray(plain.reward)
    assert paid[0] == pytest.approx(base[0], abs=1e-6)  # fore first: no cost
    assert paid[1] == pytest.approx(base[1] - 0.8 * 0.02 * -lead[1], abs=1e-5)


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


# -- race terrain (ADR-961) ---------------------------------------------------


def test_a_race_terrain_is_its_kind_course_split_and_seed() -> None:
    course = G.gate_course(3, split="heldout")
    first = G.race_terrain(np, course, "u1")
    assert G.race_terrain(np, course, "u1")["sha256"] == first["sha256"]
    others = {G.race_terrain(np, G.gate_course(3, split="train"), "u1")["sha256"],
              G.race_terrain(np, G.gate_course(4, split="heldout"), "u1")["sha256"],
              G.race_terrain(np, G.sprint_course(3, split="heldout"), "u1")["sha256"],
              G.race_terrain(np, course, "hills")["sha256"],
              G.race_terrain(np, course, "rough")["sha256"]}
    assert first["sha256"] not in others and len(others) == 5
    with pytest.raises(SystemExit):
        G.race_terrain(np, course, "stairs")


def test_a_race_terrain_keeps_its_bounds_and_a_flat_start_under_every_gate() -> None:
    shape = G.RACE_TERRAIN
    for seed in range(10):
        course = G.gate_course(seed, split="heldout")
        rough, hills, both = (G.race_terrain(np, course, kind) for kind in ("rough", "hills", "u1"))
        for terrain in (rough, hills, both):
            heights = terrain["heights_mm"]
            assert heights.shape == (terrain["nrow"], terrain["ncol"])
            assert heights.min() >= 0.0 and terrain["highest_mm"] == pytest.approx(heights.max())
            ground = G.terrain_ground(np, terrain)
            for x, y in [(0.0, 0.0), (300.0, -200.0), (-450.0, 100.0)]:
                assert ground(x, y) == 0.0  # the start's clearing
            (x0, x1), (y0, y1) = terrain["x_range_mm"], terrain["y_range_mm"]
            for gate in course["gates"]:
                gx, gy = (1000.0 * v for v in gate["xy_m"])
                assert x0 + 1000.0 * shape["margin_m"] - 1e-6 <= gx <= x1 - 1000.0 * shape["margin_m"] + 1e-6
                assert y0 + 1000.0 * shape["margin_m"] - 1e-6 <= gy <= y1 - 1000.0 * shape["margin_m"] + 1e-6
        assert 0.0 < rough["highest_mm"] <= shape["rough_mm"] and rough["hill_grade_deg"] == 0.0
        low, high = shape["grade_deg"]
        for terrain in (hills, both):
            assert terrain["drawn"]["hills"] >= 1
            assert terrain["hill_grade_deg"] == pytest.approx(terrain["drawn"]["grade_deg"], abs=1e-3)
            assert low - 1e-3 <= terrain["hill_grade_deg"] <= high + 1e-3
        assert both["drawn"]["rough_highest_mm"] <= shape["rough_mm"]


def test_box_terrain_stands_a_box_or_step_across_each_leg_on_u1s_relief() -> None:
    """ADR-965: b1 is u1's relief outside its boxes, each box's top flat over the
    hills inside it, and boxes stands the same boxes on the plane."""

    shape = G.RACE_TERRAIN
    low, high = shape["box_mm"]
    kinds_seen = set()
    for seed in range(10):
        course = G.gate_course(seed, split="heldout")
        b1, u1, boxes = (G.race_terrain(np, course, kind) for kind in ("b1", "u1", "boxes"))
        hills = G.race_terrain(np, course, "u1", rough_mm=0.0)  # u1's hills, its rough relief clipped away
        obstacles = b1["drawn"]["obstacles"]
        assert obstacles == boxes["drawn"]["obstacles"] and 0 < len(obstacles) <= len(course["gates"])
        assert b1["sha256"] != u1["sha256"] and boxes["hill_grade_deg"] == 0.0
        ground = G.terrain_ground(np, b1)
        assert ground(0.0, 0.0) == 0.0 and ground(300.0, -200.0) == 0.0
        gx = b1["x_range_mm"][0] + b1["cell_mm"] * np.arange(b1["ncol"])
        gy = b1["y_range_mm"][0] + b1["cell_mm"] * np.arange(b1["nrow"])
        covered = np.zeros(b1["heights_mm"].shape, dtype=bool)
        ends = [(0.0, 0.0)] + [tuple(1000.0 * v for v in g["xy_m"]) for g in course["gates"]]
        for box in obstacles:
            kinds_seen.add(box["kind"])
            assert low <= box["height_mm"] <= high
            (ax, ay), (bx, by) = ends[box["leg"]], ends[box["leg"] + 1]
            length = math.hypot(bx - ax, by - ay)
            assert box["along_mm"] <= shape["obstacle_leg_share"] * length + 1e-3
            # On its leg, between obstacle_at's fractions, at most the offset aside.
            cx, cy = box["centre_mm"]
            t = ((cx - ax) * (bx - ax) + (cy - ay) * (by - ay)) / length ** 2
            aside = abs((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / length
            assert shape["obstacle_at"][0] - 1e-5 <= t <= shape["obstacle_at"][1] + 1e-5
            assert aside <= shape["obstacle_offset_mm"] + 1e-3
            yaw = math.radians(box["yaw_deg"])
            px, py = gx[None, :] - cx, gy[:, None] - cy
            inside = ((np.abs(px * math.cos(yaw) + py * math.sin(yaw)) <= 0.5 * box["along_mm"])
                      & (np.abs(-px * math.sin(yaw) + py * math.cos(yaw)) <= 0.5 * box["across_mm"]))
            assert inside.any()
            # The box covers the rough relief: inside it, b1 stands at least its height over the hills.
            lift = b1["heights_mm"][inside] - hills["heights_mm"][inside]
            assert lift.min() >= box["height_mm"] - 2e-3 and lift.max() <= high + 2e-3
            assert np.all(boxes["heights_mm"][inside] >= box["height_mm"] - 1e-3)
            covered |= inside
        # Off every box by a cell (the recorded centre and yaw are rounded), b1 is u1.
        near = covered.copy()
        for axis in (0, 1):
            for shift in (-1, 1):
                near |= np.roll(covered, shift, axis=axis)
        assert np.array_equal(b1["heights_mm"][~near], u1["heights_mm"][~near])
        assert np.all(boxes["heights_mm"][~near] == 0.0)
        assert boxes["highest_mm"] == pytest.approx(b1["drawn"]["box_highest_mm"])
        assert b1["drawn"]["boxes"] + b1["drawn"]["steps"] == len(obstacles)
    assert kinds_seen == {"box", "step"}
    course = G.gate_course(3, split="heldout")
    assert G.race_terrain(np, course, "b1")["sha256"] == G.race_terrain(np, course, "b1")["sha256"]
    assert len({G.race_terrain(np, other, "b1")["sha256"]
                for other in (course, G.gate_course(3, split="train"), G.sprint_course(3, split="heldout"),
                              G.gate_course(4, split="heldout"))}) == 4


#: A floor and a ball that collides with it as a paw does.
FLOOR = """
<mujoco><worldbody>
  <geom name="environment/floor" type="plane" size="0 0 0.1" solref="0.004" contype="1" conaffinity="1"/>
  <body name="ball" pos="0 0 1"><freejoint/>
    <geom type="sphere" size="0.015" mass="0.1" contype="2" conaffinity="3"/></body>
</worldbody></mujoco>"""


def test_the_terrain_stands_on_the_floor_where_its_ground_says_and_collides_as_the_floor() -> None:
    import mujoco

    course = G.gate_course(1, split="heldout")
    terrain = G.race_terrain(np, course, "u1")
    model = G.terrain_model(mujoco, FLOOR.encode(), terrain)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    field = model.geom("environment/race_terrain")
    floor = model.geom("environment/floor")
    assert int(field.type[0]) == int(mujoco.mjtGeom.mjGEOM_HFIELD)
    for name in ("contype", "conaffinity", "solref", "friction"):
        assert np.allclose(getattr(field, name), getattr(floor, name)), name
    ground = G.terrain_ground(np, terrain)
    heights, cell = terrain["heights_mm"], terrain["cell_mm"]
    x0, y0 = terrain["x_range_mm"][0], terrain["y_range_mm"][0]
    rng = np.random.default_rng(0)
    geomid = np.zeros(1, dtype=np.int32)
    for _ in range(50):
        r, c = int(rng.integers(1, terrain["nrow"] - 1)), int(rng.integers(1, terrain["ncol"] - 1))
        x, y = x0 + c * cell, y0 + r * cell
        assert ground(x, y) == pytest.approx(heights[r, c])
        hit = mujoco.mj_ray(model, data, np.array([x / 1000.0, y / 1000.0, 2.0]), np.array([0.0, 0.0, -1.0]),
                            None, 1, -1, geomid)
        assert 2.0 - hit == pytest.approx(heights[r, c] / 1000.0, abs=1e-6)
    with pytest.raises(SystemExit):
        G.terrain_model(mujoco, b"<mujoco><worldbody/></mujoco>", terrain)


def test_a_terrain_drawing_is_a_heightfield_the_dashboard_reads() -> None:
    terrain = G.race_terrain(np, G.gate_course(0, split="heldout"), "hills")
    drawing = G.terrain_drawing(np, terrain)
    grid = drawing["grid"]
    assert drawing["kind"] == "heightfield" and grid["rows"] <= 129 and grid["columns"] <= 129
    assert len(grid["heights_mm"]) == grid["rows"] * grid["columns"]
    assert max(grid["heights_mm"]) <= terrain["highest_mm"]
    assert drawing["course"]["sha256"] == terrain["sha256"]
