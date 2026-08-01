# SPDX-License-Identifier: LGPL-2.1-or-later

"""The exit criterion (docs/MUJOCO.md M6, phase 5).

A script fully specifies a trainable task; the bundle it writes is read by a
process with no Cadex on its path, which resets the model to the solved
keyframe, acts, observes, accumulates reward and terminates -- producing the
same numbers the engine produced.

**What this proves, stated precisely, because a gate that overclaims is
worse than none.**

It proves the *task spec* is complete and unambiguous. Both evaluators read
the same JSON and the same XML and may consult nothing else, so agreement
means every number a trainer needs is in the files: which slice of
``sensordata`` each channel is, what to multiply it by, what the reward
arithmetic is, where an action goes and what it is bounded by.

It does **not** re-prove M5's physics, and it is arranged so that it cannot
be mistaken for doing so: the engine evaluates its episode on the *reloaded
exported bytes*, exactly as the subprocess does. The model is therefore not
a variable in the comparison. M5's own suites are what say the exported file
is the model the engine simulated; this says the bundle beside it describes
a task.

It says nothing about a different MuJoCo or a different machine. MuJoCo
disclaims cross-version reproducibility outright (hazard 3), the pin is what
holds it, and ``mujoco_version`` in the bundle is what makes a bump legible.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx
import dynamics_task_episode as runner

mujoco = pytest.importorskip("mujoco")

RUNNER = Path(runner.__file__).resolve()

MOTOR = {
    "joint": "elbow",
    "motion_type": "angular",
    "kind": "motor",
    "control_nmm": "400*sin(2*pi*time)",
    "torque_limit_nmm": 800.0,
}

OBSERVATIONS = [
    {"kind": "position", "joint": "elbow", "motion_type": "angular",
     "name": "elbow_angle"},
    {"kind": "velocity", "joint": "elbow", "motion_type": "angular",
     "name": "elbow_rate"},
    {"kind": "component_position", "component": "fore", "name": "hand"},
    {"kind": "component_orientation", "component": "fore", "name": "grip"},
    {"kind": "centre_of_mass", "component": "upper", "name": "arm_com"},
    {"kind": "actuator_force", "joint": "elbow", "motion_type": "angular",
     "actuator_kind": "motor", "name": "effort"},
]

DECLARATION = {
    "actions": [
        {"joint": "elbow", "motion_type": "angular", "actuator_kind": "motor"}
    ],
    # Every function the whitelist offers gets used somewhere, so a runner
    # that was missing one fails here rather than on somebody's task.
    "reward": [
        {"label": "reach", "expression": "-(hand_x - 300)**2", "weight": 1.0e-4},
        {"label": "upright", "expression": "tanh(grip_qw)", "weight": 0.5},
        {"label": "spread", "expression": "exp(-sqrt(abs(arm_com_z)))",
         "weight": 0.25},
        {"label": "control_cost", "expression": "abs(effort)", "weight": -1.0e-6},
    ],
    "termination": [
        {"label": "spun_out", "expression": "abs(elbow_rate)", "above": 4000.0}
    ],
    "episode_seconds": 3.0,
    "control_hz": 50,
    "randomisation": [
        {"target": "mass", "component": "fore", "low": 0.8, "high": 1.2,
         "label": "forearm_mass"},
        {"target": "damping", "joint": "elbow", "motion_type": "angular",
         "low": 0.5, "high": 2.0, "label": "elbow_damping"},
    ],
    "label": "reach",
}


def _write_bundle(root: Path, declaration=None, *, joint_dynamics=()):
    """One model and one bundle on disk, in the layout the worker writes.

    Deliberately the worker's layout -- ``outputs/<name>-model.xml`` beside
    ``outputs/<name>-task.json`` -- rather than a flat directory, because
    resolving the model from the bundle's own location is part of what the
    subprocess has to get right.
    """

    components, joints, _placements = fx.two_link_arm(limits=True)
    built = dyn.build_model(
        components, joints, actuators=[MOTOR], joint_dynamics=list(joint_dynamics)
    )
    observations = dyn.observation_records(
        OBSERVATIONS, built["tree"], built["joint_records"], built["actuators"]
    )
    exported = dyn.export_mjcf(built, observations=observations)

    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    model_relative = Path("outputs") / "model-model.xml"
    (root / model_relative).write_bytes(exported["xml"])

    reloaded = dyn.load_model(exported["xml"])
    bundle = dyn.task_records(
        built,
        reloaded,
        dict(DECLARATION if declaration is None else declaration),
        observations=observations,
    )
    import hashlib

    bundle["model"] = {
        "path": model_relative.as_posix(),
        "sha256": hashlib.sha256(exported["xml"]).hexdigest(),
        "bytes": len(exported["xml"]),
        "output": "model",
        "mujoco_version": str(bundle["mujoco_version"]),
    }
    bundle_path = outputs / "job-task.json"
    bundle_path.write_bytes(
        json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8")
    )
    return bundle_path, bundle, reloaded


def _stock(bundle_path: Path, seed=None) -> dict:
    """The runner, in an interpreter that cannot reach Cadex.

    ``-P`` keeps the script's own directory off ``sys.path`` and a scrubbed
    ``PYTHONPATH`` keeps the suite's off it, which together are what make
    ``cadex_importable`` false rather than merely unlikely.
    """

    environment = {
        key: value for key, value in os.environ.items() if key != "PYTHONPATH"
    }
    command = [sys.executable, "-P", str(RUNNER), str(bundle_path)]
    if seed is not None:
        command.append(str(seed))
    completed = subprocess.run(
        command, capture_output=True, text=True, env=environment, check=False
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _engine(bundle, model, seed=None) -> dict:
    return dyn.evaluate_episode(model, bundle, seed=seed)


# ---------------------------------------------------------------------------
# The exit criterion.
# ---------------------------------------------------------------------------


def test_a_stock_mujoco_runs_the_episode_the_engine_ran(tmp_path: Path) -> None:
    """The claim, in full, and every number compared as text.

    ``repr`` round-trips exactly in Python 3, so this is a comparison of
    numbers rather than of formatting -- and it is taken step by step rather
    than on the total, because a total can agree while two trajectories
    diverge and cancel.
    """

    bundle_path, bundle, model = _write_bundle(tmp_path)
    there = _stock(bundle_path)
    here = _engine(bundle, model)

    # The negative first: a run that could import Cadex proves nothing.
    assert there["cadex_importable"] is False
    assert there["mujoco_version"] == str(mujoco.__version__)

    assert there["step_count"] == here["step_count"]
    assert there["truncated"] is here["truncated"]
    assert there["terminated_step"] == here["terminated_step"]
    assert there["termination"] == here["termination"]
    assert there["label"] == here["label"]
    assert there["total_reward"] == repr(here["total_reward"])

    for mine, yours in zip(here["steps"], there["steps"], strict=True):
        assert yours["step"] == mine["step"]
        assert yours["action"] == [repr(value) for value in mine["action"]]
        assert yours["reward"] == repr(mine["reward"])
        assert yours["observation"] == {
            name: repr(value) for name, value in mine["observation"].items()
        }
        assert yours["reward_terms"] == [
            {"label": term["label"], "value": repr(term["value"]),
             "weighted": repr(term["weighted"])}
            for term in mine["reward_terms"]
        ]

    # And the episode did something: a comparison of two runs that sat still
    # would pass on a bundle describing nothing.
    assert here["step_count"] == 150
    positions = [step["observation"]["hand_x"] for step in here["steps"]]
    assert max(positions) - min(positions) > 50.0
    assert here["total_reward"] != 0.0


def test_the_runner_checks_the_model_against_the_digest_the_bundle_recorded(
    tmp_path: Path,
) -> None:
    """A bundle whose model moved is detectable, which is why both are hashed.

    One output and one artifact was the design decision; the digest is what
    makes it a decision rather than a convenience. Retrain against a model
    somebody re-exported and the observation addresses may still be valid
    while meaning something else.
    """

    bundle_path, _bundle, _model = _write_bundle(tmp_path)
    assert _stock(bundle_path)["model_sha256"]

    model = tmp_path / "outputs" / "model-model.xml"
    model.write_bytes(model.read_bytes().replace(b"<mujoco", b"<mujoco "))
    environment = {
        key: value for key, value in os.environ.items() if key != "PYTHONPATH"
    }
    completed = subprocess.run(
        [sys.executable, "-P", str(RUNNER), str(bundle_path)],
        capture_output=True, text=True, env=environment, check=False,
    )
    assert completed.returncode != 0
    assert "does not match the digest" in completed.stderr


def test_the_three_evaluators_share_one_function_whitelist(tmp_path: Path) -> None:
    """Two evaluators is where a whitelist drifts; M7 made it three.

    Four things asserted equal rather than two: the runner's own globals, the
    array in the bundle, the engine's ``REWARD_FUNCTIONS``, and -- since
    ADR-084 -- the offboard trainer's, which compiles the same expressions a
    third time under ``jax.numpy`` so they vectorise. This codebase keeps
    catching drift by writing the second copy down; here it costs one array
    and one more assertion.
    """

    bundle_path, bundle, _model = _write_bundle(tmp_path)
    there = _stock(bundle_path)

    assert there["functions"] == list(dyn.REWARD_FUNCTIONS)
    assert bundle["functions"] == list(dyn.REWARD_FUNCTIONS)
    assert there["functions"] == bundle["functions"]

    # The third evaluator. Loaded from source rather than imported as a
    # package -- it lives at the repository root and is in no payload -- and
    # asked for its whitelist with a stand-in for jax.numpy, so this runs in
    # an engine environment that has no jax at all.
    import importlib.util

    trainer_path = RUNNER.parents[4] / "training" / "cadex_train.py"
    assert trainer_path.is_file(), "the offboard trainer is gone"
    spec = importlib.util.spec_from_file_location("cadex_train", trainer_path)
    trainer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trainer)

    class _Spellings:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    assert trainer.function_names(trainer.globals_for(_Spellings())) == (
        bundle["functions"]
    )
    # The runner refuses outright rather than failing mid-episode when the
    # two differ, which is what makes this a seam and not a coincidence.
    tampered = dict(bundle)
    tampered["functions"] = [name for name in bundle["functions"] if name != "tanh"]
    bundle_path.write_bytes(json.dumps(tampered, sort_keys=True).encode("utf-8"))
    environment = {
        key: value for key, value in os.environ.items() if key != "PYTHONPATH"
    }
    completed = subprocess.run(
        [sys.executable, "-P", str(RUNNER), str(bundle_path)],
        capture_output=True, text=True, env=environment, check=False,
    )
    assert completed.returncode != 0
    assert "function whitelist differs" in completed.stderr


def test_a_seeded_episode_agrees_across_the_boundary_too(tmp_path: Path) -> None:
    """Domain randomisation is part of the spec, so it is part of the gate.

    The draw is a *stated* algorithm -- ``random.Random(seed)`` drawing
    ``uniform(low, high)`` in bundle order -- and it has to be, because two
    implementations cannot agree on "whatever the RNG did". This is what
    says the statement is enough to reproduce it.
    """

    bundle_path, bundle, model = _write_bundle(
        tmp_path,
        joint_dynamics=[
            {"joint": "elbow", "motion_type": "angular",
             "damping_nmms_per_deg": 12.0}
        ],
    )
    there = _stock(bundle_path, seed=17)
    here = _engine(bundle, dyn.load_model(
        (tmp_path / "outputs" / "model-model.xml").read_bytes()
    ), seed=17)

    assert there["seed"] == 17
    assert [entry["label"] for entry in there["randomisation"]] == [
        "forearm_mass", "elbow_damping"
    ]
    assert there["randomisation"] == [
        {"label": entry["label"], "factor": repr(entry["factor"])}
        for entry in here["randomisation"]
    ]
    assert there["total_reward"] == repr(here["total_reward"])
    for mine, yours in zip(here["steps"], there["steps"], strict=True):
        assert yours["observation"] == {
            name: repr(value) for name, value in mine["observation"].items()
        }

    # A different seed really is a different episode, so the seed is doing
    # something rather than being recorded and ignored.
    other = _stock(bundle_path, seed=18)
    assert other["randomisation"] != there["randomisation"]
    assert other["total_reward"] != there["total_reward"]


def test_the_runner_imports_nothing_but_the_standard_library_and_mujoco() -> None:
    """The claim the whole file rests on, checked by reading it.

    ``dynamics_mjcf_digest`` proves its negative at run time and so does
    this one, but a run-time check only covers the path that ran. An import
    added inside a branch nobody exercised would still make the file
    non-stock, and this is what catches that.
    """

    import ast as _ast

    allowed = {
        "ast", "hashlib", "json", "math", "mujoco", "pathlib", "random",
        "sys", "typing", "__future__",
    }
    tree = _ast.parse(RUNNER.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, _ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    # The one deliberate exception: the import of CadexDynamics that exists
    # solely to report that it failed.
    assert roots - allowed == {"CadexDynamics"}


def test_a_termination_rule_fires_identically_on_both_sides(tmp_path: Path) -> None:
    """An episode that ends is the interesting case, so it is tested as one."""

    declaration = {
        **DECLARATION,
        "termination": [
            {"label": "swung", "expression": "abs(elbow_angle)", "above": 30.0}
        ],
        "randomisation": [],
    }
    bundle_path, bundle, model = _write_bundle(tmp_path, declaration)
    there = _stock(bundle_path)
    here = _engine(bundle, model)

    assert here["terminated_step"] is not None
    assert here["truncated"] is False
    assert there["terminated_step"] == here["terminated_step"]
    assert there["termination"] == here["termination"] == "swung"
    assert there["step_count"] == here["step_count"] < 150
    assert there["steps"][-1]["terminated"] is True
