# SPDX-License-Identifier: LGPL-2.1-or-later

"""The trainer's action filter (ADR-138).

``--action-filter-alpha`` low-passes the command between the clamp and
``data.ctrl``::

    a[t] = alpha * clamped[t] + (1 - alpha) * a[t-1]

per environment, reset with the episode, with the first command of each
episode passed through unfiltered.

**The claim this file exists to prove is the NO-OP.** The default is 1.0 and
at 1.0 the trainer must produce the same POLICY as the trainer it was
before the flag existed — not "close", not "statistically indistinguishable". Every result
this repository's callers have published was trained under the old file, and
a filter that perturbed the default would put every one of them on the far
side of a boundary that would then have to be paid for with a bridge run.

That is why the flag is a **Python float branched on at trace time** rather
than a traced value: at 1.0 there is no extra carry member, no ``where`` and
no multiply in the emitted graph. ``test_alpha_one_emits_no_filter_state``
asserts the mechanism and
``test_alpha_one_reproduces_the_unmodified_trainer`` asserts the
consequence, against the file as it was before this change.

Structured like its sibling ``test_dynamics_policy_trainer.py``: the source
assertions run anywhere, and the ones that actually train are gated on the
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


def _trainer_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("cadex_train", TRAINER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    A ``.cxpolicy``'s whole-file sha256 is **not** reproducible and never was:
    the header carries ``wall_time_s`` and the trainer's reward curve, so two
    identical runs differ in bytes by construction. What is reproducible on
    CPU at a fixed seed is the network and the witness, and that is what
    ``test_a_second_run_at_the_same_seed_writes_the_same_policy`` has always
    compared. This is the same four blocks, named once here because ADR-138's
    whole case rests on them.

    It also has to be these four for a second reason particular to this
    change: the header now records ``action_filter_alpha``, so a full-header
    digest could never match across the boundary even if the policy were
    identical — which is exactly the confusion this function exists to avoid.
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


def test_the_flag_exists_and_defaults_to_no_filter() -> None:
    """1.0, and the default is the whole compatibility story.

    Asserted on the source: the trainer builds its parser inside ``main``
    and exposes no ``build_parser``, so there is nothing to call. The
    end-to-end tests below check the default's *behaviour*; this checks that
    the default is written down as 1.0 and not merely arrived at.
    """

    source = TRAINER.read_text(encoding="utf-8")
    index = source.index('"--action-filter-alpha"')
    assert "default=1.0" in source[index:index + 200]


def test_the_filter_is_applied_between_the_clamp_and_the_ctrl_write() -> None:
    """Order, asserted on the source, because it is not observable later.

    Filtering the CLAMPED command keeps the filter's memory inside the
    action box, so the convex combination is in-box too and no second clamp
    is needed. Filtering the raw surface instead would let the memory hold
    commands the actuator can never be given, and would then need a clamp
    the trainer does not apply.
    """

    source = TRAINER.read_text(encoding="utf-8")
    clamp = source.index("clamped = jnp.clip(surface, low, high)")
    write = source.index("ctrl = data.ctrl.at[ctrl_index].set(clamped * ctrl_scale)")
    filter_line = source.index("action_filter_alpha * clamped")
    assert clamp < filter_line < write, (
        "the filter must sit between the clamp and the ctrl write")


def test_alpha_one_emits_no_filter_state() -> None:
    """The mechanism behind the no-op: a TRACE-time branch, not a runtime one.

    If ``filtering`` were a traced array this would still be *numerically*
    the identity at 1.0 and would still change the graph for every existing
    caller. It is a Python bool, and that is what this pins.
    """

    source = TRAINER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assigns = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "filtering"
                for t in node.targets)
    ]
    assert len(assigns) == 1, "one definition of `filtering`"
    # `action_filter_alpha < 1.0` — a comparison of two Python floats.
    assert isinstance(assigns[0].value, ast.Compare)
    # And it is never smuggled back into the graph as a traced predicate.
    assert "jnp.where(filtering" not in source
    assert "lax.cond(filtering" not in source


@pytest.mark.parametrize("bad", ["0", "0.0", "-0.5", "1.5", "2"])
def test_an_alpha_outside_the_unit_interval_is_refused(tmp_path, bad) -> None:
    """Both directions, and neither is a clamp-and-continue.

    0 freezes the command at each episode's first step, so the policy cannot
    act; above 1 the filter extrapolates past the raw command and amplifies
    exactly the step-to-step change it exists to remove.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    result = _train(python, tmp_path, prepared, tmp_path / "p.cxpolicy",
                    "--action-filter-alpha", bad)
    assert result.returncode != 0
    assert "action-filter-alpha" in result.stderr


# ---------------------------------------------------------------------------
# The no-op, end to end.
# ---------------------------------------------------------------------------


def test_alpha_one_reproduces_the_unmodified_trainer(tmp_path) -> None:
    """The proof PR #2 set the precedent for, and the reason this can merge.

    Trains the same task at the same seed twice — once with the flag absent
    and once with it at its default — and requires the two ``.cxpolicy``
    files to have the same sha256. Absent and 1.0 must not merely agree to a
    tolerance; they must be the same bytes, because everything trained before
    this change is compared against everything trained after it.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    without = tmp_path / "without.cxpolicy"
    explicit = tmp_path / "explicit.cxpolicy"
    first = _train(python, tmp_path, prepared, without)
    assert first.returncode == 0, first.stderr[-4000:]
    second = _train(python, tmp_path, prepared, explicit,
                    "--action-filter-alpha", "1.0")
    assert second.returncode == 0, second.stderr[-4000:]

    assert behavioural_digest(without) == behavioural_digest(explicit), (
        "alpha 1.0 must reproduce the unfiltered trainer exactly")


def test_a_filtered_run_differs_from_an_unfiltered_one(tmp_path) -> None:
    """The mirror, so the test above cannot pass by the flag doing nothing."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()

    plain = tmp_path / "plain.cxpolicy"
    filtered = tmp_path / "filtered.cxpolicy"
    assert _train(python, tmp_path, prepared, plain).returncode == 0
    assert _train(python, tmp_path, prepared, filtered,
                  "--action-filter-alpha", "0.5").returncode == 0
    assert behavioural_digest(plain) != behavioural_digest(filtered)


# ---------------------------------------------------------------------------
# The header, which is how an evaluator finds out.
# ---------------------------------------------------------------------------


def test_the_resolved_alpha_reaches_the_header(tmp_path) -> None:
    """Its own key, not only ``hyperparameters``.

    An evaluator plays a policy with the filter it was trained with by
    reading ``training.action_filter_alpha``. Burying it in the
    hyperparameter dict would work and would also make every driver depend on
    the spelling of a dict that exists for provenance, not for behaviour.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    out = tmp_path / "filtered.cxpolicy"
    assert _train(python, tmp_path, prepared, out,
                  "--action-filter-alpha", "0.5").returncode == 0

    header = dyn.decode_policy(out.read_bytes())["header"]
    assert header["training"]["action_filter_alpha"] == 0.5
    assert header["training"]["hyperparameters"]["action_filter_alpha"] == 0.5


def test_an_unfiltered_policy_records_one_point_zero(tmp_path) -> None:
    """Not absent. A reader must be able to tell "no filter" from "old file"."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    out = tmp_path / "plain.cxpolicy"
    assert _train(python, tmp_path, prepared, out).returncode == 0
    header = dyn.decode_policy(out.read_bytes())["header"]
    assert header["training"]["action_filter_alpha"] == 1.0


def test_a_filtered_policy_still_verifies_against_the_engine(tmp_path) -> None:
    """The filter is on the COMMAND, not on the network.

    ``verify_policy`` replays the recorded witness observations through the
    weights, and a filter that had somehow been folded into the forward pass
    would break that. It must not: what the filter changes is which states
    the machine visits, never what the network computes at a state.
    """

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    out = tmp_path / "filtered.cxpolicy"
    assert _train(python, tmp_path, prepared, out,
                  "--action-filter-alpha", "0.5").returncode == 0
    evidence = dyn.verify_policy(
        dyn.decode_policy(out.read_bytes()),
        prepared["bundle"],
        task_sha256=prepared["task_sha256"],
    )
    assert evidence["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE


def test_a_filtered_run_is_still_reproducible_at_a_fixed_seed(tmp_path) -> None:
    """The filter adds state; it must add no nondeterminism."""

    python = _venv_python()
    if python is None:
        pytest.skip("the trainer's dependencies are absent from this env")
    prepared = pf.swing_up_bundle()
    first = tmp_path / "a.cxpolicy"
    second = tmp_path / "b.cxpolicy"
    assert _train(python, tmp_path, prepared, first,
                  "--action-filter-alpha", "0.5").returncode == 0
    assert _train(python, tmp_path, prepared, second,
                  "--action-filter-alpha", "0.5").returncode == 0
    assert behavioural_digest(first) == behavioural_digest(second)


# ---------------------------------------------------------------------------
# The recurrence, checked against a reference the trainer does not share.
# ---------------------------------------------------------------------------


def reference_filter(commands, alpha, resets):
    """``a[t] = alpha*c[t] + (1-alpha)*a[t-1]``, restarting at every reset.

    Written out here rather than imported, for the reason the whole trainer
    test file exists: two implementations compared is what keeps one honest.
    """

    out, previous = [], None
    for command, reset in zip(commands, resets):
        if reset or previous is None:
            value = list(command)
        else:
            value = [alpha * c + (1.0 - alpha) * p
                     for c, p in zip(command, previous)]
        out.append(value)
        previous = value
    return out


def test_the_reference_recurrence_restarts_at_an_episode_boundary() -> None:
    """The behaviour the trainer's ``steps == 0`` branch implements.

    A filter that carried across a reset would low-pass the first command of
    an episode towards the last command of the one before it, which is a
    different machine and a silent one — the episodes still run, they just
    start somewhere the policy did not ask for.
    """

    commands = [[10.0], [0.0], [0.0], [10.0], [0.0]]
    resets = [True, False, False, True, False]
    got = reference_filter(commands, 0.5, resets)
    assert got == [[10.0], [5.0], [2.5], [10.0], [5.0]]


def test_the_first_command_of_an_episode_is_unfiltered() -> None:
    commands = [[7.0], [0.0]]
    assert reference_filter(commands, 0.25, [True, False])[0] == [7.0]


def test_alpha_one_is_the_identity_in_the_reference_too() -> None:
    commands = [[1.0], [2.0], [3.0]]
    assert reference_filter(commands, 1.0, [True, False, False]) == commands


def test_the_trainer_states_the_recurrence_it_implements() -> None:
    """The formula appears in the help text, so ``--help`` is the spec."""

    source = TRAINER.read_text(encoding="utf-8")
    assert "a[t] = A*clamped[t] + (1-A)*a[t-1]" in source
