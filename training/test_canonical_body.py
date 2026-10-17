# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-755: a warm start across robots matches them on the canonical body.

No jax. The contract: a remap onto the policy's own robot is the identity,
and a remap onto the same robot with its channels, actions and legs listed
in another order, one joint mounted the other way round and a joint the
source never had, plays the same actions on the matching inputs and holds
the new joint at its box centre.
"""

from __future__ import annotations

import argparse
import math

import numpy as np
import pytest

from cadex_train import (
    body_layout,
    check_base_fits,
    check_family,
    family_body,
    flat_parameters,
    forward,
    morph_inputs,
    remap_from_base,
    unflatten_parameters,
)

DEG = 180.0 / math.pi
HIDDEN = [16, 8]


def joint_rows(joint: str) -> list[dict]:
    return [{"channels": [f"q_{joint}"], "dim": 1, "kind": "position",
             "scale": DEG, "target": joint},
            {"channels": [f"dq_{joint}"], "dim": 1, "kind": "velocity",
             "scale": DEG, "target": joint}]


def task_of(joints: list[str], slots: dict, extra_rows: list[dict] = ()) -> dict:
    """A biped bundle: ``slots`` maps joint -> (leg, slot, sign, offset)."""

    rows = [row for joint in joints for row in joint_rows(joint)] + [
        {"channels": ["imu_qw", "imu_qx", "imu_qy", "imu_qz"], "dim": 4,
         "kind": "component_orientation", "scale": 1.0, "target": "c_imu"},
        {"channels": ["gyro_x", "gyro_y", "gyro_z"], "dim": 3,
         "kind": "component_angular_velocity", "scale": DEG, "target": "c_imu"},
        {"channels": ["com_z"], "dim": 1, "kind": "centre_of_mass", "role": "privileged",
         "scale": 1000.0, "target": "c_base"},
    ] + list(extra_rows)
    legs: dict = {}
    for index, joint in enumerate(joints):
        if joint in slots:
            leg, slot, sign, offset = slots[joint]
            legs.setdefault(leg, {})[slot] = {
                "joint": joint, "action": index, "q": f"q_{joint}", "dq": f"dq_{joint}",
                "sign": sign, "offset": offset}
    return {
        "observations": rows,
        "actions": [{"joint": joint, "low": -30.0, "high": 30.0} for joint in joints],
        "goal": [{"channels": ["cmd"]}],
        "body": {"family": "biped", "version": 1, "legs": legs,
                 "body": {"quat": ["imu_qw", "imu_qx", "imu_qy", "imu_qz"],
                          "gyro": ["gyro_x", "gyro_y", "gyro_z"]}},
    }


SOURCE_SLOTS = {"lh": ("l", "hip", 1, 5.0), "lk": ("l", "knee", -1, -40.0),
                "rh": ("r", "hip", 1, 5.0), "rk": ("r", "knee", -1, -40.0)}
SOURCE = task_of(["lh", "lk", "rh", "rk"], SOURCE_SLOTS)


def policy_on(task: dict, seed: int = 0, layout: dict | None = None) -> tuple[dict, list[float]]:
    layout = layout or body_layout(task)
    inputs, actions = len(layout["inputs"]), len(layout["outputs"])
    rng = np.random.default_rng(seed)
    widths = [inputs] + HIDDEN + [actions]
    layers = [(rng.normal(size=(a, b)) * 0.4, rng.normal(size=b) * 0.2)
              for a, b in zip(widths[:-1], widths[1:])]
    header = {
        "body": layout,
        "model": {"sha256": "m"}, "task": {"sha256": "t"},
        "network": {"layers": [[a, b] for a, b in zip(widths[:-1], widths[1:])],
                    "activation": "tanh"},
        "normaliser": {"mean": list(rng.normal(size=inputs) * 3.0),
                       "std": list(rng.uniform(0.5, 4.0, size=inputs))},
        "exploration": {"log_std": list(rng.normal(size=actions) * 0.1 - 1.5)},
    }
    return header, flat_parameters(np, layers)


def play(layers, mean, std, x) -> np.ndarray:
    z = (np.asarray(x) - np.asarray(mean)) / np.asarray(std)
    return np.tanh(forward(np, [(np.asarray(w, np.float64), np.asarray(b, np.float64))
                                for w, b in layers], z))


def options(**overrides) -> argparse.Namespace:
    return argparse.Namespace(**{"hidden": HIDDEN, "critic_warmup": 10,
                                 "init_from_task_change": "", **overrides})


def test_a_remap_onto_its_own_robot_is_the_identity_and_a_permuted_one_plays_the_same():
    header, weights = policy_on(SOURCE)
    source_layers = unflatten_parameters(
        np, weights, [tuple(shape) for shape in header["network"]["layers"]])

    same = remap_from_base(np, header, weights, body_layout(SOURCE))
    for (w, b), (w0, b0) in zip(same["layers"], source_layers):
        np.testing.assert_allclose(w, w0, rtol=1e-6, atol=1e-6)
        np.testing.assert_allclose(b, b0, rtol=1e-6, atol=1e-6)
    np.testing.assert_allclose(same["mean"], header["normaliser"]["mean"], atol=1e-9)
    np.testing.assert_allclose(same["std"], header["normaliser"]["std"], atol=1e-9)
    assert same["log_std"] == pytest.approx(header["exploration"]["log_std"])

    # The same robot listed right leg first, knee before hip, its right
    # knee's encoder mounted the other way round (sign +1, offset +40), and
    # a tail the source never had.
    target_slots = {"rk": ("r", "knee", 1, 40.0), "rh": ("r", "hip", 1, 5.0),
                    "lk": ("l", "knee", -1, -40.0), "lh": ("l", "hip", 1, 5.0)}
    target = task_of(["rk", "rh", "tail", "lk", "lh"], target_slots)
    layout = body_layout(target)
    assert check_base_fits(header, {"task": target}, options()) == layout
    with pytest.raises(SystemExit, match="critic-warmup"):
        check_base_fits(header, {"task": target}, options(critic_warmup=0))
    mapped = remap_from_base(np, header, weights, layout)
    assert mapped["counts"]["inputs_zero"] == 2 and mapped["counts"]["outputs_zero"] == 1

    rng = np.random.default_rng(7)
    for _ in range(20):
        # One physical state, read by each robot's encoders.
        angle = {joint: rng.uniform(-30, 30) for joint in SOURCE_SLOTS}
        rate = {joint: rng.uniform(-200, 200) for joint in SOURCE_SLOTS}
        imu = list(rng.normal(size=7))
        cmd = rng.uniform(-500, 500)

        def reading(slots, joints, extra=0.0):
            values = []
            for joint in joints:
                if joint not in slots:
                    values += [extra, extra]
                    continue
                _leg, _slot, sign, offset = slots[joint]
                values += [offset + sign * angle[joint], sign * rate[joint]]
            return values + imu + [cmd]

        x_s = reading(SOURCE_SLOTS, ["lh", "lk", "rh", "rk"])
        x_t = reading(target_slots, ["rk", "rh", "tail", "lk", "lh"], extra=rng.uniform(-9, 9))
        u_s = play(source_layers, header["normaliser"]["mean"], header["normaliser"]["std"], x_s)
        u_t = play(mapped["layers"], mapped["mean"], mapped["std"], x_t)
        order = {"lh": 0, "lk": 1, "rh": 2, "rk": 3}
        for j, joint in enumerate(["rk", "rh", "tail", "lk", "lh"]):
            if joint == "tail":
                assert u_t[j] == pytest.approx(0.0, abs=1e-6)
                continue
            flip = SOURCE_SLOTS[joint][2] * target_slots[joint][2]
            assert u_t[j] == pytest.approx(flip * u_s[order[joint]], abs=2e-5)


def test_a_family_base_folds_its_morph_inputs_at_the_targets_values():
    """ADR-759: a --family policy reads each variant's morph constants after
    its channels; remapped onto one robot of the family it plays what the
    base plays reading that robot's constants."""

    morph = {"l": {"knee_dir": -1, "thigh_m": 0.2}, "r": {"knee_dir": -1, "thigh_m": 0.2},
             "hip_h_m": 0.32}
    variant = {"l": {"knee_dir": 1, "thigh_m": 0.185}, "r": {"knee_dir": 1, "thigh_m": 0.185},
               "hip_h_m": 0.33}

    def bundle(values, sha):
        task = {**SOURCE, "body": {**SOURCE["body"], "morph": values}, "reward": [{}],
                "episode": {"max_steps": 500, "solver_steps_per_action": 4}}
        return {"task": task, "task_sha256": sha}

    family = [bundle(morph, "a"), bundle(variant, "b")]
    check_family(family)
    with pytest.raises(SystemExit, match="morph names"):
        check_family([family[0], bundle({"hip_h_m": 0.3}, "c")])
    layout = family_body({**family[0], "family": family})
    names = [name for name, _ in morph_inputs(morph)]
    assert [row[0] for row in layout["inputs"][-len(names):]] == names
    header, weights = policy_on(SOURCE, layout=layout)
    source_layers = unflatten_parameters(
        np, weights, [tuple(shape) for shape in header["network"]["layers"]])

    target = family[1]["task"]
    mapped = remap_from_base(np, header, weights, body_layout(target))
    assert mapped["counts"]["inputs_folded"] == len(names)
    rng = np.random.default_rng(11)
    for _ in range(10):
        x = list(rng.normal(size=len(layout["inputs"]) - len(names)) * 5.0)
        u_s = play(source_layers, header["normaliser"]["mean"], header["normaliser"]["std"],
                   x + [value for _, value in morph_inputs(variant)])
        u_t = play(mapped["layers"], mapped["mean"], mapped["std"], x)
        np.testing.assert_allclose(u_t, u_s, atol=2e-5)
