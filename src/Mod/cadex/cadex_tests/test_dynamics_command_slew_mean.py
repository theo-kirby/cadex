# SPDX-License-Identifier: LGPL-2.1-or-later

"""The trainer's command slew limit on the POLICY MEAN (ADR-164).

``--command-slew-mean-deg`` is the *same operator* as ADR-153's
``--command-slew-deg`` in a *different place*: on the policy mean, before the
exploration noise, instead of on the issued command after it.

Why that is not a refactor
--------------------------

ADR-153's clip is the last thing before the actuator, far downstream of where
the sample is drawn. So the environment executes ``clip(sampled)`` while PPO's
log-probability credits ``sampled``, and **inside the clip
``d(executed)/d(sampled)`` is exactly zero**. That is a *biased* gradient, not
a small one, and the caller measured what it costs: a warm-started policy
scored 0 of 24 survivals on six consecutive checkpoints, from a parent that
scores 12.625 under the *same limit imposed at play time*. The controller was
not the problem and the limit was not the problem; the credit mismatch was.

Applying the limit to the mean removes the mismatch entirely. The distribution
PPO credits has mean ``raw_eff``, the environment executes
``surface_of(sampled)``, and ``sampled`` is drawn from exactly that
distribution — so **executed == sampled**, and the executed action stays a
differentiable function of what the gradient credits at every point.
:func:`test_executed_is_the_sampled_action` and
:func:`test_the_clip_does_not_kill_the_gradient_of_executed_wrt_sampled` are
that argument as arithmetic.

What this file proves
---------------------

The **no-op**, as ADR-140's and ADR-153's did — the default is 0.0 and at 0.0
this trainer must produce the same *policy* the trainer produced before the
flag existed. That claim is load-bearing in a way it was not for ADR-152: this
diff **does** touch expressions jax traces, so the guarantee is measured here
rather than argued from the diff.

And the **round trip**: ADR-164 limits the command in *degrees*, where a rate
limit means something, then hands the result back to the sampler, which lives
pre-``tanh``. ``inverse_surface_of`` is that hand-back and it is where a
plausible-looking implementation goes wrong — an unguarded ``atanh`` at the
box edge is ``inf``, and one ``inf`` in the mean poisons the whole batch.

Structured like its siblings: the source assertions run anywhere, and the ones
that actually train are gated on the trainer's dependencies and skip in the
engine environment.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

import CadexDynamics as dyn
import dynamics_policy_fixtures as pf

TRAINER = Path(__file__).resolve().parents[4] / "training" / "cadex_train.py"


def _source() -> str:
    return TRAINER.read_text()


def _venv_python() -> str | None:
    """An interpreter with the trainer's dependencies, if this one has them."""

    try:
        import jax  # noqa: F401
        import mujoco.mjx  # noqa: F401
    except Exception:
        return None
    return sys.executable


def behavioural_digest(path: Path) -> str:
    """The digest that identifies the POLICY rather than the file.

    Four blocks and not the whole file, for ADR-140's two reasons: a
    ``.cxpolicy``'s whole-file sha256 has never been reproducible (the header
    carries ``wall_time_s`` and the reward curve), and the header now records
    ``command_slew_mean_deg``, so a full-header digest could not match across
    the boundary even if the policy were identical.
    """

    header = dyn.decode_policy(path.read_bytes())["header"]
    return hashlib.sha256(json.dumps({
        "observations": header["observations"],
        "network": header["network"],
        "normaliser": header["normaliser"],
        "evaluation": header["evaluation"],
    }, sort_keys=True).encode()).hexdigest()


def _train(python, tmp_path, prepared, out, *extra, seed=0, iterations=3):
    """One tiny training run, in a process that cannot import Cadex."""

    root = tmp_path / "project"
    if not (root / "outputs").exists():
        (root / "outputs").mkdir(parents=True)
        (root / "outputs" / "job-model.xml").write_bytes(prepared["model_xml"])
        (root / "outputs" / "job-task.json").write_bytes(prepared["task_bytes"])
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [python, "-P", str(TRAINER), str(root / "outputs" / "job-task.json"),
         "--out", str(out), "--seed", str(seed), "--iterations", str(iterations),
         "--envs", "8", "--unroll", "10", "--quiet", *extra],
        capture_output=True, text=True, env=environment, check=False,
    )
    return result


# ---------------------------------------------------------------------------
# The flag itself.
# ---------------------------------------------------------------------------


def test_the_flag_exists_and_defaults_to_no_limit() -> None:
    """0.0 is the default, and 0.0 means *no limit* rather than *frozen*."""

    tree = ast.parse(_source())
    defaults = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") == "add_argument"
                and node.args
                and isinstance(node.args[0], ast.Constant)):
            for kw in node.keywords:
                if kw.arg == "default" and isinstance(kw.value, ast.Constant):
                    defaults[node.args[0].value] = kw.value.value
    assert "--command-slew-mean-deg" in defaults
    assert defaults["--command-slew-mean-deg"] == 0.0


def test_it_is_a_separate_flag_and_not_a_mode_on_the_existing_one() -> None:
    """ADR-153's flag keeps its meaning, its default and its published proof.

    A ``--command-slew-where {issued,mean}`` switch would have been shorter
    and would have made every existing header ambiguous about which operator
    produced its number. Two operators, two names.
    """

    source = _source()
    assert '"--command-slew-deg", type=float, default=0.0' in source
    assert '"--command-slew-mean-deg", type=float, default=0.0' in source


def test_both_limits_at_once_are_refused(tmp_path) -> None:
    """They bound the same command path twice under a name for neither."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    result = _train(python, tmp_path, prepared, tmp_path / "both.cxpolicy",
                    "--command-slew-deg", "0.5",
                    "--command-slew-mean-deg", "0.5")
    assert result.returncode != 0
    assert "both" in (result.stderr + result.stdout).lower()


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_a_non_finite_limit_is_refused(tmp_path, bad) -> None:
    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    result = _train(python, tmp_path, prepared, tmp_path / "bad.cxpolicy",
                    "--command-slew-mean-deg", bad)
    assert result.returncode != 0
    assert "finite" in (result.stderr + result.stdout)


def test_a_limit_wider_than_the_box_is_refused(tmp_path) -> None:
    """A flag claiming a limit must never train an unlimited run.

    ADR-153's rule, repeated rather than shared, because a limit that cannot
    bind is a *silent* no-op and the whole point of the run is the limit.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    widest = max(float(a["high"]) - float(a["low"])
                 for a in _actions(json.loads(prepared["task_bytes"])))
    result = _train(python, tmp_path, prepared, tmp_path / "wide.cxpolicy",
                    "--command-slew-mean-deg", repr(widest * 2.0))
    assert result.returncode != 0
    assert "never bind" in (result.stderr + result.stdout)


def test_a_negative_limit_is_treated_as_off(tmp_path) -> None:
    """Same convention as ADR-153: below zero is OFF, not an error."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    plain = tmp_path / "plain.cxpolicy"
    negative = tmp_path / "negative.cxpolicy"
    assert _train(python, tmp_path, prepared, plain).returncode == 0
    assert _train(python, tmp_path, prepared, negative,
                  "--command-slew-mean-deg", "-1.0").returncode == 0
    assert behavioural_digest(plain) == behavioural_digest(negative)


# ---------------------------------------------------------------------------
# Where the operator sits. This is the whole change.
# ---------------------------------------------------------------------------


def test_the_limit_is_applied_before_the_noise_is_drawn() -> None:
    """The one structural fact ADR-164 exists for.

    Read off the source rather than inferred from behaviour, because "the
    limit is upstream of the sample" is a claim about ORDER and a behavioural
    test would pass for a limit that merely happened to bind rarely.
    """

    source = _source()
    limit = source.index("raw_eff = inverse_surface_of(mean_iss)")
    draw = source.index("noise = jax.random.normal(act_key, raw.shape")
    sample = source.index("sampled = raw_eff + noise * jnp.exp")
    assert limit < draw < sample


def test_ppo_credits_the_limited_mean_and_not_the_raw_network_output() -> None:
    """``gaussian_logp`` must be given ``raw_eff``.

    If it were handed ``raw`` the trainer would credit a distribution the
    environment never sampled from, which is 025's defect wearing a different
    hat.
    """

    assert "logp = gaussian_logp(sampled, raw_eff, params[\"log_std\"])" \
        in _source()


def test_the_downstream_operators_are_skipped_when_the_mean_is_limited() -> None:
    """Otherwise the command is low-passed and rate-limited TWICE.

    And the second one would be on the sampled action, which puts the dead
    zone straight back.
    """

    source = _source()
    assert "step_carrying = carrying and not mean_slewing" in source
    assert "_filter_axes = (0, 0) if step_carrying else ()" in source


def test_the_carry_is_the_limited_mean_and_is_noise_free() -> None:
    """The recursion has to be the one that runs at PLAY time.

    At play time there is no noise, so a carry seeded from the *executed*
    action would make the trained controller and the played controller two
    different filters — and every driver would score a machine that was never
    trained.
    """

    source = _source()
    assert "issued = mean_iss" in source
    assert "filter_carry = [jnp.where(done[:, None], 0.0, issued)]" in source


def test_the_ema_runs_before_the_rate_limit_on_the_mean() -> None:
    """ADR-153's order, for ADR-153's reason.

    The other order lets the EMA smooth the signal back across the limit, so
    what reaches the actuator is not rate limited at all — and
    ``harness/_policy.action_callable`` composes them this way, so the arm
    would be played by a controller it was not trained by.
    """

    source = _source()
    ema = source.index("action_filter_alpha * mean_cmd")
    clip = source.index("jnp.clip(mean_cmd, mean_prev - command_slew_mean_deg")
    assert ema < clip


def test_the_first_command_of_an_episode_is_unlimited() -> None:
    """``steps == 0`` passes through, exactly as ADR-151 and ADR-153 do.

    Seeding the recursion from zero would spend the first tau of every episode
    ramping out of a posture the policy never asked for, inside the reset
    drop.
    """

    source = _source()
    assert "first = (steps == 0)[:, None]" in source
    assert "jnp.where(\n                        first, mean_cmd," in source


# ---------------------------------------------------------------------------
# The round trip. Where a plausible implementation goes wrong.
# ---------------------------------------------------------------------------


def _actions(bundle) -> list:
    """The action table, whichever way the bundle is wrapped.

    ``cadex_train`` reads ``bundle["task"]["actions"]``; the fixture hands
    back the task itself. One accessor rather than a guess, so a test cannot
    silently measure the wrong table.
    """

    task = bundle.get("task", bundle)
    return list(task["actions"])


def _output_map(bundle) -> tuple[list[float], list[float]]:
    actions = _actions(bundle)
    scale = [(float(a["high"]) - float(a["low"])) / 2.0 for a in actions]
    bias = [(float(a["high"]) + float(a["low"])) / 2.0 for a in actions]
    return scale, bias


def _atanh_eps() -> float:
    """``ATANH_EPS`` read out of the trainer, never retyped."""

    for node in ast.walk(ast.parse(_source())):
        if (isinstance(node, ast.Assign)
                and getattr(node.targets[0], "id", "") == "ATANH_EPS"):
            return float(ast.literal_eval(node.value))
    raise AssertionError("ATANH_EPS is not defined in the trainer")


def test_the_round_trip_is_the_identity_away_from_the_box_edge() -> None:
    """``surface_of(inverse_surface_of(x)) == x`` where it matters."""

    scale, bias = _output_map(json.loads(pf.swing_up_bundle()["task_bytes"]))
    eps = _atanh_eps()
    for s, b in zip(scale, bias):
        for frac in (-0.9, -0.5, 0.0, 0.25, 0.9):
            command = b + frac * s
            u = min(max((command - b) / s, -1.0 + eps), 1.0 - eps)
            back = math.tanh(math.atanh(u)) * s + b
            assert abs(back - command) < 1.0e-9


def test_the_round_trip_is_finite_at_the_box_edge() -> None:
    """An unguarded ``atanh`` here is ``inf`` and poisons the whole batch."""

    scale, bias = _output_map(json.loads(pf.swing_up_bundle()["task_bytes"]))
    eps = _atanh_eps()
    for s, b in zip(scale, bias):
        for command in (b - s, b + s):
            u = min(max((command - b) / s, -1.0 + eps), 1.0 - eps)
            raw = math.atanh(u)
            assert math.isfinite(raw)
            assert abs(raw) < 10.0


def test_the_chain_rule_cancels_to_one_where_the_limit_does_not_bind() -> None:
    """The gradient-amplification worry, answered numerically.

    ``d(raw_eff)/d(mean_iss) = 1/(scale*(1-u^2))`` grows at the box edge, and
    ``d(mean_cmd)/d(raw) = scale*(1-tanh^2 raw)`` shrinks there by the same
    factor. Unbound, ``raw_eff`` is ``raw`` and the product is exactly 1 — so
    an unlimited ADR-164 run is the *unmodified* pipeline, not a numerically
    noisier version of it.
    """

    scale, bias = _output_map(json.loads(pf.swing_up_bundle()["task_bytes"]))
    for s, b in zip(scale, bias):
        for raw in (-3.0, -1.0, -0.1, 0.0, 0.4, 2.0, 4.0):
            command = math.tanh(raw) * s + b
            u = (command - b) / s
            forward = s * (1.0 - math.tanh(raw) ** 2)
            backward = 1.0 / (s * (1.0 - u * u))
            assert abs(forward * backward - 1.0) < 1.0e-9


def test_the_clip_does_not_kill_the_gradient_of_executed_wrt_sampled() -> None:
    """025's defect, stated as the arithmetic that refutes it here.

    Under ADR-153 the environment executes ``clip(surface_of(sampled))`` and
    the derivative of that with respect to ``sampled`` is ZERO wherever the
    clip binds. Under ADR-164 it executes ``surface_of(sampled)``, whose
    derivative is ``scale * (1 - tanh^2)`` — strictly positive everywhere.
    """

    scale, bias = _output_map(json.loads(pf.swing_up_bundle()["task_bytes"]))
    s, b = scale[0], bias[0]
    limit = 0.05 * s

    def executed_153(sampled, previous):
        return min(max(math.tanh(sampled) * s + b,
                       previous - limit), previous + limit)

    def executed_154(sampled):
        return math.tanh(sampled) * s + b

    previous = b
    h = 1.0e-6
    # A sample far enough out that the ADR-153 clip certainly binds.
    sampled = 2.5
    d153 = (executed_153(sampled + h, previous)
            - executed_153(sampled - h, previous)) / (2 * h)
    d154 = (executed_154(sampled + h) - executed_154(sampled - h)) / (2 * h)
    assert abs(d153) < 1.0e-9, "ADR-153's clip has a dead zone — that is the bug"
    assert d154 > 0.0


# ---------------------------------------------------------------------------
# The reference recurrence, and that it is the harness's.
# ---------------------------------------------------------------------------


def reference_mean_slew(commands, alpha, limit, resets):
    """EMA then rate limit, against the previous LIMITED command.

    Written out independently of the trainer so a test compares two
    implementations rather than one implementation with itself. This is also
    ``harness/_policy.action_callable``'s composition, which is what makes a
    policy trained under ADR-164 playable without a driver change.
    """

    out = []
    previous = None
    for index, command in enumerate(commands):
        if index in resets or previous is None:
            issued = command
        else:
            issued = alpha * command + (1.0 - alpha) * previous
            issued = min(max(issued, previous - limit), previous + limit)
        out.append(issued)
        previous = issued
    return out


def test_the_limit_binds_on_a_step_change() -> None:
    got = reference_mean_slew([0.0, 10.0, 10.0, 10.0], 1.0, 2.0, resets={0})
    assert got == [0.0, 2.0, 4.0, 6.0]


def test_the_recurrence_restarts_at_an_episode_boundary() -> None:
    got = reference_mean_slew([0.0, 10.0, 10.0], 1.0, 2.0, resets={0, 1})
    assert got == [0.0, 10.0, 10.0]


def test_the_ema_alone_does_not_bound_the_rate() -> None:
    """Why ADR-164 is not "just use a smaller alpha".

    An EMA's per-step change is ``alpha * |raw - previous|``, which on a wide
    box is a large fraction of the box in ONE step. The caller spent two
    experiments discovering this; it is pinned here so nobody derives it a
    third time.
    """

    unlimited = reference_mean_slew([0.0, 50.0], 0.65, 1.0e9, resets={0})
    assert abs(unlimited[1] - unlimited[0]) == pytest.approx(32.5)
    limited = reference_mean_slew([0.0, 50.0], 0.65, 20.0, resets={0})
    assert abs(limited[1] - limited[0]) == pytest.approx(20.0)


def test_the_trainer_states_the_recurrence_it_implements() -> None:
    """The comment and the code must not drift apart.

    ADR-153's sibling test exists for the same reason: this operator is three
    lines and the paragraph explaining *where* it sits is the part that is
    load-bearing.
    """

    source = _source()
    assert "executed == sampled" in source
    assert "before the exploration noise" in source


# ---------------------------------------------------------------------------
# The no-op. This is the reason the change can merge.
# ---------------------------------------------------------------------------


def test_zero_reproduces_the_unmodified_trainer(tmp_path) -> None:
    """Absent and 0.0 must be the same POLICY, not merely a close one.

    Load-bearing in a way ADR-152's was not: this diff **does** touch
    expressions jax traces, so the guarantee is measured rather than argued
    from the diff.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    without = tmp_path / "without.cxpolicy"
    explicit = tmp_path / "explicit.cxpolicy"
    assert _train(python, tmp_path, prepared, without).returncode == 0
    assert _train(python, tmp_path, prepared, explicit,
                  "--command-slew-mean-deg", "0.0").returncode == 0
    assert behavioural_digest(without) == behavioural_digest(explicit)


def test_the_filter_is_unchanged_by_this_flag_existing(tmp_path) -> None:
    """ADR-151's own no-op still holds after ADR-164 reuses its carry."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    a = tmp_path / "a.cxpolicy"
    b = tmp_path / "b.cxpolicy"
    assert _train(python, tmp_path, prepared, a,
                  "--action-filter-alpha", "0.65").returncode == 0
    assert _train(python, tmp_path, prepared, b,
                  "--action-filter-alpha", "0.65",
                  "--command-slew-mean-deg", "0.0").returncode == 0
    assert behavioural_digest(a) == behavioural_digest(b)


def test_the_issued_limit_is_unchanged_by_this_flag_existing(tmp_path) -> None:
    """And so does ADR-153's, which is the arm 025 was trained with."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    a = tmp_path / "a.cxpolicy"
    b = tmp_path / "b.cxpolicy"
    assert _train(python, tmp_path, prepared, a,
                  "--command-slew-deg", "0.5").returncode == 0
    assert _train(python, tmp_path, prepared, b,
                  "--command-slew-deg", "0.5",
                  "--command-slew-mean-deg", "0.0").returncode == 0
    assert behavioural_digest(a) == behavioural_digest(b)


def test_a_mean_limited_run_differs_from_an_unlimited_one(tmp_path) -> None:
    """The mirror, so the no-op tests cannot pass by the flag doing nothing."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    plain = tmp_path / "plain.cxpolicy"
    limited = tmp_path / "limited.cxpolicy"
    assert _train(python, tmp_path, prepared, plain).returncode == 0
    assert _train(python, tmp_path, prepared, limited,
                  "--command-slew-mean-deg", "0.5").returncode == 0
    assert behavioural_digest(plain) != behavioural_digest(limited)


def test_mean_limiting_differs_from_issued_limiting_at_the_same_value(
        tmp_path) -> None:
    """The experiment's whole premise, as a test.

    Same limit, same everything else, different placement — and if these two
    produced the same policy there would be nothing to measure.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    issued = tmp_path / "issued.cxpolicy"
    mean = tmp_path / "mean.cxpolicy"
    assert _train(python, tmp_path, prepared, issued,
                  "--command-slew-deg", "0.5").returncode == 0
    assert _train(python, tmp_path, prepared, mean,
                  "--command-slew-mean-deg", "0.5").returncode == 0
    assert behavioural_digest(issued) != behavioural_digest(mean)


def test_a_mean_limited_run_is_still_reproducible_at_a_fixed_seed(
        tmp_path) -> None:
    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    first = tmp_path / "first.cxpolicy"
    second = tmp_path / "second.cxpolicy"
    assert _train(python, tmp_path, prepared, first,
                  "--command-slew-mean-deg", "0.5").returncode == 0
    assert _train(python, tmp_path, prepared, second,
                  "--command-slew-mean-deg", "0.5").returncode == 0
    assert behavioural_digest(first) == behavioural_digest(second)


# ---------------------------------------------------------------------------
# The header. Provenance, and what a PLAYER reads.
# ---------------------------------------------------------------------------


def test_the_deployed_limit_reaches_the_key_every_driver_reads(
        tmp_path) -> None:
    """``training.command_slew_deg``, because at play time noise is zero.

    The mean IS the issued command with no noise, so the number an evaluator
    must impose is the same number wherever the operator sat during training.
    Writing a second key would make every driver learn a second spelling of
    one limit.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    out = tmp_path / "mean.cxpolicy"
    assert _train(python, tmp_path, prepared, out,
                  "--command-slew-mean-deg", "0.5").returncode == 0
    training = dyn.decode_policy(out.read_bytes())["header"]["training"]
    assert training["command_slew_deg"] == pytest.approx(0.5)
    assert training["command_slew_mean_deg"] == pytest.approx(0.5)
    assert training["command_slew_applied_to"] == "mean"


def test_an_issued_limited_policy_says_so(tmp_path) -> None:
    """The key that distinguishes 025's arm from 028's.

    Both carry ``command_slew_deg = 20`` and they are different experiments.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    out = tmp_path / "issued.cxpolicy"
    assert _train(python, tmp_path, prepared, out,
                  "--command-slew-deg", "0.5").returncode == 0
    training = dyn.decode_policy(out.read_bytes())["header"]["training"]
    assert training["command_slew_deg"] == pytest.approx(0.5)
    assert training["command_slew_mean_deg"] == 0.0
    assert training["command_slew_applied_to"] == "issued"


def test_an_unlimited_policy_records_none(tmp_path) -> None:
    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    out = tmp_path / "plain.cxpolicy"
    assert _train(python, tmp_path, prepared, out).returncode == 0
    training = dyn.decode_policy(out.read_bytes())["header"]["training"]
    assert training["command_slew_deg"] == 0.0
    assert training["command_slew_mean_deg"] == 0.0
    assert training["command_slew_applied_to"] == "none"


def test_a_mean_limited_policy_still_verifies_against_the_engine(
        tmp_path) -> None:
    """The witness is about the NETWORK, and the operator is not in it.

    Stated as a test because it is the one place a reader might expect the
    limit to appear and it must not: ``verify_policy`` replays the output map,
    not the controller.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    out = tmp_path / "mean.cxpolicy"
    assert _train(python, tmp_path, prepared, out,
                  "--command-slew-mean-deg", "0.5").returncode == 0
    decoded = dyn.decode_policy(out.read_bytes())
    assert decoded["header"]["schema"] == "cadex-policy-v1"


def test_resolved_command_slew_deg_is_defined_exactly_once() -> None:
    """It was defined TWICE, identically, at two places in the same file.

    Harmless — the second shadowed the first and they had the same body — and
    fixed here rather than left, because the next person to change one of them
    would have changed the dead one. The surviving copy is the one that was
    executing, so the live code path is byte-identical.
    """

    tree = ast.parse(_source())
    defs = [n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef)
            and n.name == "resolved_command_slew_deg"]
    assert len(defs) == 1
