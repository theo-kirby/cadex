# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-839: one go-to-point source for training and the judge.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_cadex_goto.py`` from the repo.
"""

from __future__ import annotations

import math

import numpy as np

from cadex_goto import DriveMeter, layer_start, layer_step, maze_route, sequence, stack

BANDS = [{"name": "walk", "low": 0.4, "high": 0.7}, {"name": "run", "low": 1.0, "high": 1.5}]
LIMITS = {"vx": [-1.5, 1.5], "vy": [-0.8, 0.8], "wz": [-1.2, 1.2]}


def test_a_sequence_is_its_seed_and_split_and_honours_its_shape() -> None:
    a = sequence(3, split="heldout", bands=BANDS)
    assert a == sequence(3, split="heldout", bands=BANDS)
    assert a["points"] != sequence(3, split="train", bands=BANDS)["points"]
    kinds = [p["bearing"] for p in a["points"]]
    assert len(kinds) == 8 and kinds.count("behind") >= 2 and kinds.count("side") >= 2
    assert sum(p["hold_s"] > 0 for p in a["points"]) >= 2
    for p in a["points"]:
        band = next(b for b in BANDS if b["name"] == p["band"])
        assert band["low"] <= p["speed_mps"] <= band["high"]


def test_the_next_point_lights_on_arrival_and_after_the_hold_not_on_a_clock() -> None:
    plan = stack(np, [{"points": [{"xy_m": [1.0, 0.0], "speed_mps": 1.0, "hold_s": 0.5},
                                  {"xy_m": [1.0, 3.0], "speed_mps": 1.0, "hold_s": 0.0}]}])
    state = layer_start(np, [1])
    one = lambda x, y, yaw=0.0: layer_step(np, plan, state, np.array([x]), np.array([y]),  # noqa: E731
                                           np.array([yaw]), 0.02, LIMITS)
    # Far from the first point, any number of steps: it stays lit, and the command heads there.
    for _ in range(500):
        state, command = one(-2.0, 0.0)
    assert int(state["index"][0]) == 0 and command["vx"][0] > 0.9 and abs(command["wz"][0]) < 1e-6
    # Behind the robot: it turns in place, toward the point.
    state, command = one(2.0, 0.0)
    assert command["vx"][0] == 0.0 and abs(command["wz"][0]) == 1.2
    # On the point: held for 0.5 s (25 steps of 0.02 s), then the next point lights.
    for _ in range(24):
        state, command = one(1.0, 0.0)
        assert int(state["index"][0]) == 0 and bool(state["arrived"][0])
    for _ in range(2):
        state, command = one(1.0, 0.0)
    assert int(state["index"][0]) == 1 and command["wz"][0] == 1.2
    # A point with no hold is passed on arrival; past the last one the command is zero.
    state, command = one(1.0, 2.9, math.pi / 2)
    assert int(state["index"][0]) == 2 and all(float(v[0]) == 0.0 for v in command.values())


def test_a_maze_route_turns_at_a_door_cell_and_comes_back_the_same_way() -> None:
    # ADR-860's regression: a way that turns in its door cell left the robot
    # turning 0.25 m short of the centre, and its hind legs swept a wall.
    # 2 x 2 cells of 1 m centred at (5, 0) m: in by the -x door in row 0, up,
    # then out by the +x door in row 1.
    maze = {"x_mm": 5000.0, "y_mm": 0.0, "cells_x": 2, "cells_y": 2, "cell_mm": 1000.0, "height_mm": 400.0}
    walls = [((3970.0, 4030.0), (-30.0, 1030.0), 400.0), ((5970.0, 6030.0), (-1030.0, 30.0), 400.0),
             ((4970.0, 5030.0), (-1030.0, 30.0), 400.0),
             ((3970.0, 6030.0), (-1030.0, -970.0), 400.0), ((3970.0, 6030.0), (970.0, 1030.0), 400.0)]
    route = maze_route(maze, walls, 0, split="heldout", bands=BANDS)
    assert route == maze_route(maze, walls, 0, split="heldout", bands=BANDS)
    got = [(tuple(p["xy_m"]), p["role"]) for p in route["points"]]
    there = [((2.5, -0.5), "lead"), ((4.5, -0.5), "corner"), ((4.5, 0.5), "corner"),
             ((5.5, 0.5), "cell"), ((7.5, 0.5), "held")]
    assert got == there + there[-2::-1][:-1] + [((2.5, -0.5), "held")]
    assert [p["bearing"] for p in route["points"]][5] == "behind"
    assert all(p["band"] == "walk" for p in route["points"] if p["role"] in ("cell", "corner"))


def test_a_turn_in_place_goes_on_until_the_point_is_well_inside_the_cone() -> None:
    # ADR-865's regression: with one 60 deg threshold the orun9 biped chattered
    # at the cone's edge, each step-off yawing it back out, and turned for 200 s.
    plan = stack(np, [{"points": [{"xy_m": [0.0, -4.0], "speed_mps": 1.0, "hold_s": 0.0}]}])
    state = layer_start(np, [1])
    one = lambda yaw: layer_step(np, plan, state, np.array([0.0]), np.array([0.0]),  # noqa: E731
                                 np.array([math.radians(yaw)]), 0.02, LIMITS)
    state, command = one(0.0)  # the point 90 deg to the right: turn in place
    assert bool(state["turning"][0]) and command["vx"][0] == 0.0 and command["wz"][0] < 0.0
    state, command = one(-40.0)  # 50 deg off, inside 60 but not 30: still turning
    assert bool(state["turning"][0]) and command["vx"][0] == 0.0
    state, command = one(-65.0)  # 25 deg off: walk, still turning toward it
    assert not bool(state["turning"][0]) and command["vx"][0] > 0.0
    state, command = one(-40.0)  # back out to 50 deg while walking: keeps walking
    assert not bool(state["turning"][0]) and command["vx"][0] > 0.0


def test_the_drive_meter_reads_a_held_arm_at_its_static_torque() -> None:
    # ADR-952: a 0.5 kg point 0.2 m out on a hinge, held level by a stiff
    # position drive, needs m g l = 0.981 N m; a second drive clamped at
    # 0.3 N m reads its clamp, as a motor at its limit would.
    import mujoco

    model = mujoco.MjModel.from_xml_string("""
    <mujoco><option timestep="0.001"/><worldbody>
      <body><joint name="a" type="hinge" axis="0 1 0" damping="2"/>
        <geom type="sphere" size="0.01" pos="0.2 0 0" mass="0.5"/></body>
      <body pos="0 1 0"><joint name="b" type="hinge" axis="0 1 0" damping="2"/>
        <geom type="sphere" size="0.01" pos="0.2 0 0" mass="0.5"/></body>
    </worldbody><actuator>
      <position name="held" joint="a" kp="2000"/>
      <position name="weak" joint="b" kp="2000" forcelimited="true" forcerange="-0.3 0.3"/>
    </actuator></mujoco>""")
    data = mujoco.MjData(model)
    for _ in range(3000):
        mujoco.mj_step(model, data)
    meter = DriveMeter(np, model)
    for _ in range(500):
        mujoco.mj_step(model, data)
        meter.add(data)
    reading = meter.reading()
    assert reading["samples"] == 500
    assert abs(reading["rms_nm"]["held"] - 0.5 * 9.81 * 0.2) < 1e-3
    assert abs(reading["rms_nm"]["weak"] - 0.3) < 1e-6 and reading["peak_nm"]["weak"] <= 0.3 + 1e-9
    assert reading["worst"] == "held" and reading["worst_rms_nm"] == reading["rms_nm"]["held"]


def _stub_player(alpha: float, raw: list) -> "object":
    # A Player with no policy file: its network replays ``raw`` in order and it
    # reads only its issued commands, so ``control`` exercises the clamp and the
    # filter and nothing else.
    import cadex_train
    from cadex_goto import Player

    player = Player.__new__(Player)
    player.np, player.dt = np, 0.02
    player.goals, player.goal_scale, player.scans, player.sensor = ["vx", "vy", "wz"], [1.0] * 3, [], {}
    player.channels, player.command_names = ["q0", "q1"], {"q0": 0, "q1": 1}
    player.low, player.high = np.array([-25.0, -10.0]), np.array([25.0, 40.0])
    player.ctrl_scale, player.ctrl_index = np.full(2, math.pi / 180.0), np.array([0, 1])
    player.reset_command = np.array([3.0, -2.0])
    player.filter_alpha, player.filtered_command = alpha, cadex_train.filtered_command
    stream = iter(raw)
    player._act = lambda values: np.array(next(stream), dtype=np.float64)
    return player


class _Data:
    def __init__(self) -> None:
        self.ctrl = np.zeros(2)


def test_the_player_filters_the_command_as_the_trainer_does() -> None:
    # ADR-953: a policy trained with ADR-160's filter is played under it, by the
    # trainer's own function, from its header. The trainer's step (jax) and the
    # player (numpy) issue the same commands from the same raw stream, the first
    # of each episode unfiltered and every one clamped before it is filtered.
    import inspect

    import cadex_train
    import jax
    import jax.numpy as jnp

    source = inspect.getsource(cadex_train.build_environment)
    assert "filtered_command(jnp, clamped, previous, first," in source
    alpha = 1.0 - math.exp(-2.0 * math.pi * 4.0 * 0.02)  # 4 Hz at 50 Hz: 0.395
    rng = np.random.default_rng(7)
    raw = rng.uniform(-60.0, 60.0, size=(40, 2)).tolist()
    low, high = np.array([-25.0, -10.0]), np.array([25.0, 40.0])
    player = _stub_player(alpha, raw + raw)
    step = jax.jit(lambda c, p, f: cadex_train.filtered_command(jnp, c, p, f, alpha))
    for _ in range(2):  # two episodes: reset restarts the filter
        player.reset()
        previous = jnp.zeros(2, dtype=jnp.float32)
        expected = None
        for t, command in enumerate(raw):
            clamped = np.clip(command, low, high)
            ctrl = player.control(_Data(), [0.0, 0.0, 0.0])
            previous = step(jnp.asarray(clamped, jnp.float32), previous, jnp.asarray(t == 0))
            expected = clamped if t == 0 else alpha * clamped + (1.0 - alpha) * expected
            assert np.allclose(player.issued, np.asarray(previous), atol=1e-4)
            assert np.allclose(player.issued, expected, atol=1e-9)
            assert np.allclose(ctrl, expected * math.pi / 180.0, atol=1e-9)
            assert np.all(player.issued >= low) and np.all(player.issued <= high)


def test_an_unfiltered_policy_plays_its_clamped_command_and_a_slew_is_refused() -> None:
    import pytest

    from cadex_goto import played_filter_alpha

    raw = [[40.0, 5.0], [-40.0, 50.0], [1.0, 2.0]]
    player = _stub_player(1.0, raw)
    player.reset()
    for command in raw:
        player.control(_Data(), [0.0, 0.0, 0.0])
        assert np.array_equal(player.issued, np.clip(command, [-25.0, -10.0], [25.0, 40.0]))
    assert played_filter_alpha({}) == 1.0
    assert played_filter_alpha({"training": {"action_filter_alpha": 0.395}}) == 0.395
    for training in ({"command_slew_deg": 3.0}, {"action_filter_alpha": 0.0}, {"action_filter_alpha": 1.2}):
        with pytest.raises(SystemExit):
            played_filter_alpha({"training": training})
