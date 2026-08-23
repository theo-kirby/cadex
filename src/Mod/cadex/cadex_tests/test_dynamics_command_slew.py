# SPDX-License-Identifier: LGPL-2.1-or-later

"""The trainer's command slew limit (ADR-153).

``--command-slew-deg`` caps the per-step change of the ISSUED command::

    a[t] = clip(a[t], a[t-1] - S, a[t-1] + S)

per environment, applied **after** the action filter, reset with the episode,
with the first command of each episode passed through unlimited.

**A SLEW LIMIT IS A DIFFERENT OPERATOR FROM THE EMA.** That sentence is the
reason this file exists as well as ``test_dynamics_action_filter.py``. An
EMA's per-step change is ``alpha * |raw - previous|`` — on a +/-25 deg box at
alpha 0.65 that is up to 32.5 deg in ONE control step — so it bounds the
command's *smoothness* and does not bound its *rate* at all. The caller's
measurements say the same thing from the other end: two experiments cut the
resting duty hard with an EMA and both still commanded ~25 deg steps into a
joint that physically reaches 12.53 deg per control step.
``test_the_ema_does_not_bound_the_rate`` pins the distinction numerically so
that nobody re-derives it a third time.

**The claim this file exists to prove is the NO-OP**, exactly as ADR-140's
did. The default is 0.0, and at 0.0 the trainer must produce the same POLICY
as the trainer it was before the flag existed — not "close". Everything the
caller has published was trained under the old file.

That is why the limit is a **Python float branched on at trace time** rather
than a traced value: at 0.0 there is no extra carry member, no ``where`` and
no ``clip`` in the emitted graph, and the carry that ADR-151 added is
*shared* rather than duplicated — ``carrying = filtering or slewing``.

Structured like its siblings: the source assertions run anywhere, and the
ones that actually train are gated on the trainer's dependencies and skip in
the engine environment.
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
    ``command_slew_deg``, so a full-header digest could not match across the
    boundary even if the policy were identical.
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
    """0.0 is the default, and 0.0 has to mean *no limit* rather than *frozen*."""

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
    assert "--command-slew-deg" in defaults
    assert defaults["--command-slew-deg"] == 0.0


def test_zero_is_no_limit_and_not_a_frozen_command() -> None:
    """The one place a slew limit's edge case differs from the EMA's.

    Alpha 0 *freezes* the command and is refused. Slew 0 is the opposite
    convention — it is the OFF switch — because a rate of zero is the natural
    spelling of "no rate limit imposed" and the flag's absence has to mean
    something. Pinned here so the two conventions are never harmonised by
    somebody tidying up.
    """

    source = _source()
    # Read off the resolver rather than off a spelling: the trainer resolves
    # this in one module-level function so `train` and `policy_header` cannot
    # disagree, and an assertion looking for a literal `command_slew_deg =
    # 0.0` assignment pinned a draft that no longer exists. The rule is
    # "absent, None, zero and negative all mean no limit", so that is what is
    # asserted — with the OFF switch itself, `slewing`, still pinned as text
    # because it is the branch that keeps 0.0 a true no-op.
    resolver = source[source.index("def resolved_command_slew_deg(options)"):]
    resolver = resolver[:resolver.index("\ndef ", 1)]
    assert 'getattr(options, "command_slew_deg", 0.0)' in resolver
    assert "return value if value > 0.0 else 0.0" in resolver
    assert "slewing = command_slew_deg > 0.0" in source


def test_the_limit_is_applied_after_the_filter_and_before_the_ctrl_write() -> None:
    """Order is behaviour, not style.

    Rate-limiting *before* the EMA would let the EMA smooth the signal back
    across the limit, so what reached the actuator would not be rate limited
    at all. The harness composes them EMA-then-slew; the trainer must match,
    or a policy is trained by one controller and played by another.
    """

    source = _source()
    clamp = source.index("clamped = jnp.clip(surface, low, high)")
    ema = source.index("action_filter_alpha * clamped", clamp)
    slew = source.index("previous - command_slew_deg", clamp)
    write = source.index("ctrl = data.ctrl.at[ctrl_index].set", clamp)
    assert clamp < ema < slew < write, (
        "the order must be clamp, filter, slew, ctrl")


def test_the_carry_is_shared_with_the_action_filter() -> None:
    """One carry member, not two.

    Both operators need exactly the same thing — the previous issued command,
    per environment, episode-local — so ADR-153 reuses ADR-151's rather than
    adding a seventh state member that would have to be kept in step with it.
    """

    source = _source()
    assert "carrying = filtering or slewing" in source
    # Every plumbing site tests the shared flag. The ONE surviving bare
    # `if filtering:` is the EMA arithmetic itself, nested inside the shared
    # branch -- if a second one appears, a carry site has been missed.
    assert source.count("if filtering:") == 1


def test_zero_emits_no_carry_state() -> None:
    """The mechanism behind the no-op, asserted separately from its effect.

    At slew 0 and alpha 1.0 the vmap axes are empty, so the traced signature
    is the pre-ADR-151 one and the graph cannot differ.
    """

    assert "_filter_axes = (0, 0) if carrying else ()" in _source()


@pytest.mark.parametrize("bad", ["nan", "inf"])
def test_a_non_finite_limit_is_refused(tmp_path, bad) -> None:
    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    result = _train(python, tmp_path, prepared, tmp_path / "x.cxpolicy",
                    "--command-slew-deg", bad)
    assert result.returncode != 0
    assert "finite" in (result.stderr + result.stdout).lower()


def test_a_limit_wider_than_the_box_is_refused(tmp_path) -> None:
    """A flag that claims a limit must not silently train an unlimited run.

    016 lost two clips to a literal default that could not bind; the repair
    there was to refuse rather than to substitute, and this is the same rule
    applied before the GPU is taken instead of after.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    result = _train(python, tmp_path, prepared, tmp_path / "x.cxpolicy",
                    "--command-slew-deg", "100000")
    assert result.returncode != 0
    assert "never bind" in (result.stderr + result.stdout)


def test_a_negative_limit_is_treated_as_off(tmp_path) -> None:
    """Below zero is off, not an error, and matches the default exactly."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    plain = tmp_path / "plain.cxpolicy"
    negative = tmp_path / "negative.cxpolicy"
    assert _train(python, tmp_path, prepared, plain).returncode == 0
    assert _train(python, tmp_path, prepared, negative,
                  "--command-slew-deg", "-5").returncode == 0
    assert behavioural_digest(plain) == behavioural_digest(negative)


# ---------------------------------------------------------------------------
# The no-op. This is the reason the change can merge.
# ---------------------------------------------------------------------------


def test_zero_reproduces_the_unmodified_trainer(tmp_path) -> None:
    """Absent and 0.0 must be the same POLICY, not merely a close one."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    without = tmp_path / "without.cxpolicy"
    explicit = tmp_path / "explicit.cxpolicy"
    first = _train(python, tmp_path, prepared, without)
    assert first.returncode == 0, first.stderr[-4000:]
    second = _train(python, tmp_path, prepared, explicit,
                    "--command-slew-deg", "0.0")
    assert second.returncode == 0, second.stderr[-4000:]

    assert behavioural_digest(without) == behavioural_digest(explicit), (
        "slew 0.0 must reproduce the unlimited trainer exactly")


def test_the_filter_is_unchanged_by_this_flag_existing(tmp_path) -> None:
    """ADR-151's own no-op still holds after ADR-153 shares its carry.

    The carry became conditional on ``filtering or slewing``; this asserts
    that a filtered, unlimited run is still exactly what it was, which is what
    protects every result the caller trained under alpha 0.5 and 0.65.
    """

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
                  "--command-slew-deg", "0.0").returncode == 0
    assert behavioural_digest(a) == behavioural_digest(b)


def test_a_limited_run_differs_from_an_unlimited_one(tmp_path) -> None:
    """The mirror, so the no-op tests cannot pass by the flag doing nothing."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    plain = tmp_path / "plain.cxpolicy"
    limited = tmp_path / "limited.cxpolicy"
    assert _train(python, tmp_path, prepared, plain).returncode == 0
    assert _train(python, tmp_path, prepared, limited,
                  "--command-slew-deg", "0.5").returncode == 0
    assert behavioural_digest(plain) != behavioural_digest(limited)


def test_the_two_operators_compose_rather_than_replace(tmp_path) -> None:
    """Filter-and-limit is a third machine, not either one of them."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    ema = tmp_path / "ema.cxpolicy"
    slew = tmp_path / "slew.cxpolicy"
    both = tmp_path / "both.cxpolicy"
    assert _train(python, tmp_path, prepared, ema,
                  "--action-filter-alpha", "0.65").returncode == 0
    assert _train(python, tmp_path, prepared, slew,
                  "--command-slew-deg", "0.5").returncode == 0
    assert _train(python, tmp_path, prepared, both,
                  "--action-filter-alpha", "0.65",
                  "--command-slew-deg", "0.5").returncode == 0
    digests = {behavioural_digest(p) for p in (ema, slew, both)}
    assert len(digests) == 3


# ---------------------------------------------------------------------------
# The header, which is how an evaluator finds out.
# ---------------------------------------------------------------------------


def test_the_resolved_limit_reaches_the_header(tmp_path) -> None:
    """Its own key, for ADR-151's reason: a driver told separately is forgotten."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    out = tmp_path / "limited.cxpolicy"
    assert _train(python, tmp_path, prepared, out,
                  "--command-slew-deg", "0.5").returncode == 0
    header = dyn.decode_policy(out.read_bytes())["header"]
    assert header["training"]["command_slew_deg"] == pytest.approx(0.5)


def test_an_unlimited_policy_records_zero(tmp_path) -> None:
    """The key is always present, so a reader never has to guess."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    out = tmp_path / "plain.cxpolicy"
    assert _train(python, tmp_path, prepared, out).returncode == 0
    header = dyn.decode_policy(out.read_bytes())["header"]
    assert header["training"]["command_slew_deg"] == 0.0


def test_a_limited_policy_still_verifies_against_the_engine(tmp_path) -> None:
    """The witness is the engine's, and a rate limit must not disturb it."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    out = tmp_path / "limited.cxpolicy"
    assert _train(python, tmp_path, prepared, out,
                  "--command-slew-deg", "0.5").returncode == 0
    dyn.verify_policy(out.read_bytes(), prepared["task"])


def test_a_limited_run_is_still_reproducible_at_a_fixed_seed(tmp_path) -> None:
    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    a = tmp_path / "a.cxpolicy"
    b = tmp_path / "b.cxpolicy"
    assert _train(python, tmp_path, prepared, a,
                  "--command-slew-deg", "0.5").returncode == 0
    assert _train(python, tmp_path, prepared, b,
                  "--command-slew-deg", "0.5").returncode == 0
    assert behavioural_digest(a) == behavioural_digest(b)


# ---------------------------------------------------------------------------
# The recurrence, as arithmetic, away from jax.
# ---------------------------------------------------------------------------


def reference_slew(commands, limit, resets):
    """What the trainer is supposed to compute, written once, in plain Python."""

    out, previous = [], None
    for command, reset in zip(commands, resets):
        if reset or previous is None:
            issued = float(command)
        else:
            issued = max(previous - limit, min(previous + limit,
                                               float(command)))
        out.append(issued)
        previous = issued
    return out


def test_the_first_command_of_an_episode_is_unlimited() -> None:
    """Seeding from zero would ramp out of a posture nobody asked for."""

    got = reference_slew([20.0, 20.0], 1.0, [True, False])
    assert got[0] == 20.0
    assert got[1] == 20.0


def test_the_limit_binds_on_a_step_change() -> None:
    got = reference_slew([0.0, 25.0, 25.0, 25.0], 10.0, [True, False, False,
                                                         False])
    assert got == [0.0, 10.0, 20.0, 25.0]


def test_the_recurrence_restarts_at_an_episode_boundary() -> None:
    got = reference_slew([0.0, 25.0, 25.0], 10.0, [True, False, True])
    assert got == [0.0, 10.0, 25.0]


def test_the_ema_does_not_bound_the_rate() -> None:
    """The whole reason ADR-153 exists, as a number rather than as a sentence.

    An EMA at alpha 0.65 on a +/-25 deg box can move the command 32.5 deg in
    one control step — more than the box's own half-width, and 2.6x what the
    joint physically reaches in that time. Whatever alpha is chosen, the EMA
    is not the operator that bounds this.
    """

    alpha, box = 0.65, 25.0
    previous, raw = -box, box
    step = abs(alpha * raw + (1.0 - alpha) * previous - previous)
    assert step == pytest.approx(alpha * 2.0 * box)
    assert step > box
    # And the limit does what the EMA does not.
    assert abs(reference_slew([previous, raw], 5.0,
                              [True, False])[1] - previous) == 5.0


def test_the_trainer_states_the_recurrence_it_implements() -> None:
    """The docstring is the specification; keep them in the same file."""

    source = _source()
    assert "a[t] = clip(a[t], a[t-1] - S, a[t-1] + S)" in source or (
        "previous - command_slew_deg" in source
        and "previous + command_slew_deg" in source)
