# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The trainer's per-step reward floor (ADR-700).

``--reward-floor F`` clamps each step's summed reward from below::

    r[t] = max(sum_i w_i * term_i, F)

which is what MuJoCo Playground's locomotion recipes do at F = 0. The B1 Go1
benchmark ran without it and its mean episode fell to 111 steps by iteration
49 while reward per step was negative: a policy paid less than nothing for
every step it survived learns to stop surviving (ADR-410's collapse).

Two claims, both proved here. **Absent is the old trainer**: the floor is a
Python value branched on at trace time, so no ``maximum`` enters the graph.
**Present, it binds**: a task whose every step pays less than the floor
reports exactly the floor per step.

The source assertions run anywhere; the ones that train are gated on the
trainer's dependencies and skip in the engine environment.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import CadexDynamics as dyn
import dynamics_policy_fixtures as pf

TRAINER = Path(__file__).resolve().parents[4] / "training" / "cadex_train.py"

#: Every step costs 10 less 0.01 * the tip's height in mm, and the swing-up
#: pendulum's tip never reaches 1000 mm, so every step's sum is negative.
COSTLY_TASK = dict(pf.SWING_UP_TASK, reward=[
    *pf.SWING_UP_TASK["reward"],
    {"label": "cost", "expression": "1", "weight": -10.0},
])


def _source() -> str:
    return TRAINER.read_text()


def _venv_python() -> str | None:
    try:
        import jax  # noqa: F401
        import mujoco.mjx  # noqa: F401
    except Exception:
        return None
    return sys.executable


def _behaviour(path: Path) -> str:
    header = dyn.decode_policy(path.read_bytes())["header"]
    return hashlib.sha256(json.dumps({
        "observations": header["observations"],
        "network": header["network"],
        "normaliser": header["normaliser"],
        "evaluation": header["evaluation"],
    }, sort_keys=True).encode()).hexdigest()


def _train(python, root, prepared, out, *extra):
    if not (root / "outputs").exists():
        (root / "outputs").mkdir(parents=True)
        (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])
        (root / "outputs" / "job-task.json").write_bytes(prepared["task_bytes"])
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    return subprocess.run(
        [python, "-P", str(TRAINER), str(root / "outputs" / "job-task.json"),
         "--out", str(out), "--seed", "0", "--iterations", "3",
         "--envs", "8", "--unroll", "10", "--quiet", *extra],
        capture_output=True, text=True, env=environment, check=False,
    )


def _curve(path: Path) -> list[float]:
    header = dyn.decode_policy(path.read_bytes())["header"]
    return [row["reward_per_step"] for row in header["training"]["reward_curve"]]


def test_the_flag_exists_and_defaults_to_no_floor() -> None:
    defaults = {}
    for node in ast.walk(ast.parse(_source())):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") == "add_argument"
                and node.args and isinstance(node.args[0], ast.Constant)):
            for kw in node.keywords:
                if kw.arg == "default" and isinstance(kw.value, ast.Constant):
                    defaults[node.args[0].value] = kw.value.value
    assert "--reward-floor" in defaults
    assert defaults["--reward-floor"] is None


def test_no_floor_adds_nothing_to_the_graph() -> None:
    """The mechanism behind the no-op: the clamp sits behind a trace-time branch."""

    source = _source()
    body = source[source.index("    def reward_of(vector):"):]
    body = body[:body.index("    def done_of(vector):")]
    assert "if reward_floor is not None:" in body
    assert "jnp.maximum(total, jnp.float32(reward_floor))" in body


def test_the_floor_binds_and_reaches_the_header(tmp_path) -> None:
    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle(task=COSTLY_TASK)
    plain = tmp_path / "plain.cxpolicy"
    floored = tmp_path / "floored.cxpolicy"
    first = _train(python, tmp_path, prepared, plain)
    assert first.returncode == 0, first.stderr[-4000:]
    second = _train(python, tmp_path, prepared, floored, "--reward-floor", "0")
    assert second.returncode == 0, second.stderr[-4000:]

    assert all(value < 0.0 for value in _curve(plain))
    assert _curve(floored) == [0.0, 0.0, 0.0]
    assert _behaviour(plain) != _behaviour(floored)
    training = dyn.decode_policy(floored.read_bytes())["header"]["training"]
    assert training["reward_floor"] == 0.0
    plain_training = dyn.decode_policy(plain.read_bytes())["header"]["training"]
    assert plain_training["reward_floor"] is None


def test_a_floor_that_never_binds_is_the_unfloored_policy(tmp_path) -> None:
    """``max(r, -1e9)`` is ``r`` bit for bit, so the policy must be too."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    plain = tmp_path / "plain.cxpolicy"
    low = tmp_path / "low.cxpolicy"
    assert _train(python, tmp_path, prepared, plain).returncode == 0
    assert _train(python, tmp_path, prepared, low,
                  "--reward-floor=-1e9").returncode == 0
    assert _behaviour(plain) == _behaviour(low)


@pytest.mark.parametrize("bad", ["nan", "inf"])
def test_a_non_finite_floor_is_refused(tmp_path, bad) -> None:
    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    result = _train(python, tmp_path, prepared, tmp_path / "x.cxpolicy",
                    "--reward-floor", bad)
    assert result.returncode != 0
    assert "finite" in (result.stderr + result.stdout)
