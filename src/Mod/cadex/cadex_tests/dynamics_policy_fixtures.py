# SPDX-License-Identifier: LGPL-2.1-or-later

"""Task bundles and policy containers, built forwards so tests read backwards.

The sibling of :mod:`dynamics_fixtures`, and it keeps that file's discipline:
a fixture is constructed from *known* numbers so a test can assert against
something nothing in the code under test produced.

A policy container here is deliberately built with a **hand-rolled network of
random weights** rather than by running the trainer. Two reasons: a unit test
that needed JAX would not run in the engine environment at all (training is
offboard by design), and a container whose weights came from
``policy_forward`` itself would make the witness a tautology. The witness is
computed by this module's own second forward pass, so a test that the engine
reproduces it is a test that two implementations agree.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from typing import Any, Mapping, Sequence

import CadexDynamics as dyn
import dynamics_fixtures as fx

#: The one-hinge swing-up the CI gate trains, and the smallest mechanism that
#: is a real control problem. The hinge is at the link's *end*: ``fx.build``
#: centres a box on its own origin, so a child frame at the origin would put
#: the axis through the centre of mass and the pendulum would be perfectly
#: balanced -- gravity would produce no torque and there would be nothing to
#: swing up. Measured that way once, and it looked like a converged policy.
SWING_UP_TORQUE_LIMIT_NMM = 2000.0


def swing_up_built(*, torque_limit_nmm: float = SWING_UP_TORQUE_LIMIT_NMM):
    components, joints, _ = fx.build(
        [
            {"name": "post", "grounded": True, "size": (60.0, 60.0, 300.0)},
            {"name": "link", "size": (200.0, 30.0, 15.0)},
        ],
        [
            {"name": "hinge", "kind": "revolute", "parent": "post",
             "child": "link",
             "parent_frame": fx.frame((0.0, 0.0, 150.0), (1.0, 0.0, 0.0), -90.0),
             "child_frame": fx.frame((-100.0, 0.0, 0.0), (1.0, 0.0, 0.0), -90.0),
             "values": [0.0]},
        ],
    )
    return dyn.build_model(
        components, joints,
        actuators=[{
            "joint": "hinge", "motion_type": "angular", "kind": "motor",
            "control_nmm": "0", "torque_limit_nmm": float(torque_limit_nmm),
        }],
    )


#: ``centre_of_mass`` rather than ``component_position``: M6 measured that a
#: link hinged at its own origin has that origin *on* the rotation axis, so
#: its position channel is a constant however far the arm swings.
SWING_UP_OBSERVATIONS = [
    {"kind": "position", "joint": "hinge", "motion_type": "angular",
     "name": "angle"},
    {"kind": "velocity", "joint": "hinge", "motion_type": "angular",
     "name": "rate"},
    {"kind": "centre_of_mass", "component": "link", "name": "tip"},
]

SWING_UP_TASK = {
    "actions": [{"joint": "hinge", "motion_type": "angular",
                 "actuator_kind": "motor"}],
    "reward": [
        {"label": "height", "expression": "tip_z", "weight": 0.01},
        {"label": "spin", "expression": "abs(rate)", "weight": -1.0e-4},
    ],
    "termination": [
        {"label": "spun_out", "expression": "abs(rate)", "above": 3000.0}
    ],
    "episode_seconds": 2.0,
    "control_hz": 50,
    "randomisation": [],
    "label": "swing_up",
}


def swing_up_bundle(
    *, task: Mapping[str, Any] | None = None, model_path: str = "outputs/job-model.xml"
) -> dict[str, Any]:
    """One task bundle, its model's bytes, and the digests of both.

    The bundle carries a ``model`` block exactly as ``_execute_task_bundle``
    writes one, because that block is what a policy is checked against and a
    fixture that omitted it would test a shape nothing produces.
    """

    import mujoco

    built = swing_up_built()
    observations = dyn.observation_records(
        list(SWING_UP_OBSERVATIONS), built["tree"], built["joint_records"],
        built["actuators"],
    )
    exported = dyn.export_mjcf(built, observations=observations)
    reloaded = mujoco.MjModel.from_xml_string(exported["xml"].decode("utf-8"))
    bundle = dyn.task_records(
        built, reloaded, dict(task or SWING_UP_TASK), observations=observations
    )
    bundle["model"] = {
        "path": str(model_path),
        "sha256": hashlib.sha256(exported["xml"]).hexdigest(),
        "bytes": len(exported["xml"]),
        "output": "job_model",
        "mujoco_version": str(bundle["mujoco_version"]),
    }
    payload = json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8")
    return {
        "built": built,
        "model": reloaded,
        "model_xml": exported["xml"],
        "bundle": bundle,
        "task_bytes": payload,
        "task_sha256": hashlib.sha256(payload).hexdigest(),
    }


def _layers(observations: int, actions: int, hidden: Sequence[int]):
    widths = [observations, *[int(width) for width in hidden], actions]
    return [(a, b) for a, b in zip(widths[:-1], widths[1:])]


def _reference_forward(
    shapes, weights, mean, std, scale, bias, sample, *, activation: str = "tanh"
) -> list[float]:
    """A second forward pass, written out rather than shared.

    Deliberately *not* ``dyn.policy_forward``: this is what computes a
    fixture's witness, and a witness computed by the function under test
    would make every test that checks it a tautology.
    """

    values = [(float(v) - mean[i]) / std[i] for i, v in enumerate(sample)]
    cursor = 0
    for index, (inputs, outputs) in enumerate(shapes):
        matrix = weights[cursor:cursor + inputs * outputs]
        cursor += inputs * outputs
        biases = weights[cursor:cursor + outputs]
        cursor += outputs
        result = []
        for column in range(outputs):
            total = biases[column]
            for row in range(inputs):
                total += values[row] * matrix[row * outputs + column]
            result.append(total)
        if index < len(shapes) - 1:
            result = ([math.tanh(v) for v in result] if activation == "tanh"
                      else [v if v > 0.0 else 0.0 for v in result])
        values = result
    return [math.tanh(v) * scale[i] + bias[i] for i, v in enumerate(values)]


def policy_container(
    prepared: Mapping[str, Any],
    *,
    seed: int = 7,
    hidden: Sequence[int] = (8, 8),
    samples: int = 8,
    activation: str = "tanh",
    label: str = "gait",
    normalise: bool = False,
) -> dict[str, Any]:
    """One ``.cxpolicy``'s header, weights and encoded bytes, for a bundle.

    Weights are float32-rounded *before* the witness is computed, because
    float32 is what the container stores and what the engine reads back. A
    witness taken against unrounded weights would be a witness about numbers
    that never land -- which is exactly the class of bug the witness exists
    to catch.
    """

    import struct

    bundle = prepared["bundle"]
    channels = dyn._task_channels(bundle)
    actions = list(bundle["actions"])
    shapes = _layers(len(channels), len(actions), hidden)
    rng = random.Random(seed)

    def as_float32(value: float) -> float:
        return struct.unpack("<f", struct.pack("<f", value))[0]

    weights = [
        as_float32(rng.uniform(-0.6, 0.6))
        for inputs, outputs in shapes
        for _ in range(inputs * outputs + outputs)
    ]
    mean = [as_float32(rng.uniform(-1.0, 1.0)) if normalise else 0.0
            for _ in channels]
    std = [as_float32(rng.uniform(0.5, 2.0)) if normalise else 1.0
           for _ in channels]
    scale, bias = dyn._policy_action_map(bundle)

    observations = [
        [as_float32(rng.uniform(-3.0, 3.0)) for _ in channels]
        for _ in range(samples)
    ]
    recorded = [
        _reference_forward(shapes, weights, mean, std, scale, bias, sample,
                           activation=activation)
        for sample in observations
    ]

    header = {
        "schema": dyn.POLICY_SCHEMA,
        "label": label,
        "task": {"sha256": prepared["task_sha256"],
                 "label": str(bundle["label"])},
        "model": {"sha256": str(bundle["model"]["sha256"]),
                  "path": str(bundle["model"]["path"])},
        "observations": channels,
        "actions": actions,
        "network": {
            "kind": "mlp",
            "layers": [list(shape) for shape in shapes],
            "activation": activation,
            "output": "tanh",
            "output_scale": scale,
            "output_bias": bias,
        },
        "normaliser": {"mean": mean, "std": std},
        "training": {
            "trainer_sha256": "0" * 64,
            "seed": int(seed),
            "hyperparameters": {"iterations": 1},
            "iterations": 1,
            "wall_time_s": 0.0,
            "device": "cpu",
            "versions": {"python": "3", "numpy": "0", "mujoco": "3.10.0",
                         "mjx": "3.10.0", "jax": "0"},
            "reward_curve": [],
        },
        "evaluation": {"observations": observations, "actions": recorded},
    }
    blob = dyn.encode_policy(header, weights)
    return {
        "header": header,
        "weights": weights,
        "blob": blob,
        "sha256": hashlib.sha256(blob).hexdigest(),
        "shapes": shapes,
    }
