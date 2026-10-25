# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-825: `--teacher`, a student distilled by command band.

No jax and no device. The band routing, the teacher's forward pass and the
loss are pure functions of numpy arrays, and every refusal is a function of a
header and a bundle dict, so a distillation that is going to be refused is
refused before anything reserves a card.
"""

from __future__ import annotations

import argparse
import hashlib
import json

import numpy as np
import pytest

from cadex_train import (
    arguments,
    check_teachers,
    distillation_loss,
    encode_policy,
    flat_parameters,
    forward,
    layer_shapes,
    load_teacher,
    parse_teacher,
    policy_header,
    teacher_actions,
    teacher_provenance,
)

ACTIONS = [
    {"actuator": "j/position", "high": 25.0, "index": 0, "joint": "j",
     "kind": "position", "low": -25.0, "scale": 0.01745, "unit": "deg"},
    {"actuator": "k/position", "high": 25.0, "index": 1, "joint": "k",
     "kind": "position", "low": -25.0, "scale": 0.01745, "unit": "deg"},
]
TASK = {
    "actions": ACTIONS,
    "goal": [{"channels": ["cmd"], "kind": "speed", "label": "cmd", "low": 0.0, "high": 4500.0}],
    "observations": [{"channels": ["a", "b"], "dim": 2}],
}
CHANNELS = ["a", "b", "cmd"]
MODEL = "m" * 64


def bundle() -> dict:
    return {"task": json.loads(json.dumps(TASK)), "task_sha256": "t" * 64,
            "model_sha256": MODEL, "model_path": "model.xml"}


def write_teacher(tmp_path, name: str, seed: int, *, observations=CHANNELS,
                  model=MODEL, actions=ACTIONS) -> str:
    """A two-layer teacher container, as the trainer would have written it."""

    rng = np.random.default_rng(seed)
    shapes = layer_shapes(len(observations), len(actions), [4])
    layers = [(rng.normal(size=shape).astype(np.float32),
               rng.normal(size=shape[1]).astype(np.float32)) for shape in shapes]
    header = {
        "label": name,
        "model": {"sha256": model},
        "task": {"sha256": hashlib.sha256(name.encode()).hexdigest()},
        "observations": list(observations),
        "actions": [dict(action) for action in actions],
        "network": {"kind": "mlp", "layers": [list(s) for s in shapes],
                    "activation": "swish"},
        "normaliser": {"mean": [0.5, -0.5, 2000.0], "std": [2.0, 1.0, 1000.0]},
        "training": {"iterations": 50},
    }
    path = tmp_path / f"{name}.cxpolicy"
    path.write_bytes(encode_policy(header, flat_parameters(np, layers)))
    return str(path)


def teachers(tmp_path, *specs):
    return [load_teacher(np, *parse_teacher(spec)) for spec in specs]


def test_parse_teacher_reads_band_and_path_and_refuses_the_rest():
    assert parse_teacher("0:250:/x/a:b.cxpolicy") == (0.0, 250.0, "/x/a:b.cxpolicy")
    for bad in ("0:250", "a:250:p", "250:250:p", "300:250:p", "0:250:"):
        with pytest.raises(SystemExit):
            parse_teacher(bad)


def test_two_teachers_fit_and_the_goal_index_is_cmds(tmp_path):
    a = write_teacher(tmp_path, "stand", 1)
    b = write_teacher(tmp_path, "gallop", 2)
    loaded = teachers(tmp_path, f"0:250:{a}", f"2000:4500:{b}")
    assert check_teachers(loaded, bundle(), "cmd") == 2
    assert check_teachers([], bundle(), "cmd") == -1


@pytest.mark.parametrize("change, message", [
    ({"model": "x" * 64}, "model"),
    ({"observations": ["b", "a", "cmd"]}, "observation channels"),
    ({"actions": ACTIONS[:1]}, "action table"),
    ({"actions": [ACTIONS[0], {**ACTIONS[1], "high": 30.0}]}, "action table"),
])
def test_a_teacher_for_another_body_or_interface_is_refused(tmp_path, change, message):
    path = write_teacher(tmp_path, "other", 3, **change)
    with pytest.raises(SystemExit, match=message):
        check_teachers(teachers(tmp_path, f"0:250:{path}"), bundle(), "cmd")


def test_overlapping_bands_a_band_outside_the_goal_and_an_unknown_goal_are_refused(tmp_path):
    a = write_teacher(tmp_path, "a", 1)
    b = write_teacher(tmp_path, "b", 2)
    with pytest.raises(SystemExit, match="overlap"):
        check_teachers(teachers(tmp_path, f"0:300:{a}", f"250:1000:{b}"), bundle(), "cmd")
    with pytest.raises(SystemExit, match="range"):
        check_teachers(teachers(tmp_path, f"4000:5000:{a}"), bundle(), "cmd")
    with pytest.raises(SystemExit, match="goal"):
        check_teachers(teachers(tmp_path, f"0:250:{a}"), bundle(), "yaw")
    family = {**bundle(), "family": [bundle(), bundle()]}
    with pytest.raises(SystemExit, match="family"):
        check_teachers(teachers(tmp_path, f"0:250:{a}"), family, "cmd")


def test_each_step_is_taught_by_the_teacher_whose_band_holds_its_goal(tmp_path):
    a = write_teacher(tmp_path, "stand", 1)
    b = write_teacher(tmp_path, "gallop", 2)
    loaded = teachers(tmp_path, f"0:250:{a}", f"2000:4500:{b}")
    goals = np.array([0.0, 249.0, 250.0, 1000.0, 2000.0, 4500.0], dtype=np.float32)
    rng = np.random.default_rng(0)
    observation = np.concatenate(
        [rng.normal(size=(6, 2)).astype(np.float32), goals[:, None]], axis=1)
    target, mask = teacher_actions(np, loaded, observation, 2)
    assert mask.tolist() == [1, 1, 0, 0, 1, 1]
    for row, owner in ((0, 0), (1, 0), (4, 1), (5, 1)):
        teacher = loaded[owner]
        own = np.tanh(forward(np, teacher["layers"],
                              (observation[row] - teacher["mean"]) / teacher["std"],
                              activation="swish"))
        assert np.allclose(target[row], own, atol=1e-6)
    assert not target[2].any() and not target[3].any()
    assert target.shape == (6, 2) and target.dtype == np.float32


def test_the_loss_is_zero_on_the_teachers_own_action_and_ignores_untaught_steps(tmp_path):
    a = write_teacher(tmp_path, "stand", 1)
    loaded = teachers(tmp_path, f"0:250:{a}")
    observation = np.array([[0.1, 0.2, 100.0], [0.3, 0.4, 3000.0]], dtype=np.float32)
    target, mask = teacher_actions(np, loaded, observation, 2)
    teacher = loaded[0]
    location = forward(np, teacher["layers"],
                       (observation - teacher["mean"]) / teacher["std"], activation="swish")
    assert distillation_loss(np, location, target, mask) == pytest.approx(0.0, abs=1e-12)
    # Off by 0.5 in tanh space on the taught step only: half the steps taught.
    shifted = np.arctanh(np.clip(np.tanh(location) + np.array([[0.5, 0.5], [0.9, 0.9]]),
                                 -0.999, 0.999))
    expected = np.mean(np.square(np.tanh(shifted[0]) - target[0])) / 2.0
    assert distillation_loss(np, shifted, target, mask) == pytest.approx(expected, rel=1e-5)


def test_the_header_records_teachers_by_digest_and_a_plain_run_is_unchanged(tmp_path):
    a = write_teacher(tmp_path, "stand", 1)
    loaded = teachers(tmp_path, f"0:250:{a}")
    record = teacher_provenance(loaded, "cmd", 1.0)
    assert record["teachers"][0]["sha256"] == hashlib.sha256(
        open(a, "rb").read()).hexdigest()
    assert record["teachers"][0]["label"] == "stand"
    assert str(tmp_path) not in json.dumps(record)
    assert teacher_provenance([], "cmd", 1.0) is None

    options = arguments(["b.json", "--out", "o.cxpolicy"])
    taught = arguments(["b.json", "--out", "o.cxpolicy", "--teacher", f"0:250:{a}"])
    assert taught.teacher == [f"0:250:{a}"] and taught.distill_weight == 1.0
    plain = header_of(options, None)
    distilled = header_of(taught, record)
    assert "distill" not in plain["training"]
    assert distilled["training"]["distill"] == record
    for header in (plain, distilled):
        assert not {"teacher", "teacher_goal", "distill_weight"} & set(
            header["training"]["hyperparameters"])
    assert plain["training"]["hyperparameters"] == distilled["training"]["hyperparameters"]


def header_of(options: argparse.Namespace, distill) -> dict:
    trained = {
        "layers": [[3, 2]], "activation": "swish", "log_std": [0.0, 0.0],
        "normaliser": {"mean": [0.0] * 3, "std": [1.0] * 3, "count": 1},
        "output_scale": [1.0, 1.0], "output_bias": [0.0, 0.0],
        "observations": CHANNELS, "witness_observations": [], "witness_actions": [],
        "reward_curve": [], "iterations": 0, "wall_time_s": 0.0, "init_from": None,
        "distill": distill, "backend": "cpu", "devices": [], "versions": {},
    }
    task = {**bundle()["task"], "label": "u", "episode": {"control_hz": 50},
            "schema": "cadex-training-task-v1"}
    return policy_header({**bundle(), "task": task}, options, trained,
                         cadex_importable=False)
