# SPDX-License-Identifier: LGPL-2.1-or-later

"""The control formula (docs/MUJOCO.md M4, phase 3).

M4's first correction to its own plan, in the half that runs. The plan said
"a control callback runs in the worker": a Python callable invoked every
solver step. Phase 0 measured why that is unnecessary -- MuJoCo's
``position`` and ``velocity`` actuators *are* the PD loop, written into
``gainprm``/``biasprm`` and closed in C -- and it would have been actively
harmful, because arbitrary Python inside the stepping loop puts unbounded
code inside the determinism gate and breaks "nothing happens outside the
script" the same way the deleted bpy modes did.

What is left for a script to supply is a **setpoint**, and a setpoint that
may vary is a formula of ``time``. That is a vocabulary this surface
already has: ``api.motion`` has taken one since ADR-048, with an AST
whitelist that M4 extracted rather than copied.

Two properties this file exists to pin.

**Nothing but arithmetic is reachable.** The whitelist is enumerated at the
API and the evaluation globals are a dict with no ``__builtins__``, so a
name that somehow passed the first barrier resolves to nothing at the
second.

**Time is computed, never accumulated.** ``t = start + index · step`` from
an integer index, never ``data.time``. A control that depended on
floating-point accumulation would make the trace depend on it too, and the
determinism gate is what would have to catch it -- after the fact, on a
digest, with nothing to point at.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn


def _compiled(formula: str):
    return dyn.compile_control(formula, context="test actuator")


def _at(formula: str, time_s: float) -> float:
    return dyn.evaluate_control(_compiled(formula), time_s, context="test actuator")


# ---------------------------------------------------------------------------
# What a formula may say.
# ---------------------------------------------------------------------------


def test_a_constant_is_the_common_case_and_ignores_time() -> None:
    code = _compiled("30")
    assert all(
        dyn.evaluate_control(code, t, context="c") == 30.0
        for t in (0.0, 0.5, 100.0)
    )


def test_time_is_seconds_and_arithmetic_works_on_it() -> None:
    assert _at("90*time", 0.5) == pytest.approx(45.0)
    # Python syntax: the API is what turns an author's ``^`` into ``**``,
    # because ``api.motion`` renders the other way for Ondsel and the two
    # surfaces share one validator.
    assert _at("time**2", 3.0) == pytest.approx(9.0)
    assert _at("-time", 2.0) == pytest.approx(-2.0)
    assert _at("(time + 1)/2", 3.0) == pytest.approx(2.0)


def test_the_functions_are_the_ones_api_motion_has() -> None:
    assert _at("sin(pi/2)", 0.0) == pytest.approx(1.0)
    assert _at("cos(0)", 0.0) == pytest.approx(1.0)
    assert _at("abs(0 - time)", 4.0) == pytest.approx(4.0)
    assert _at("asin(1)", 0.0) == pytest.approx(math.pi / 2.0)
    assert _at("arcsin(1)", 0.0) == pytest.approx(math.pi / 2.0)
    assert _at("arctan(1)", 0.0) == pytest.approx(math.pi / 4.0)


def test_a_swept_setpoint_is_what_this_is_for() -> None:
    """30° amplitude at 1 Hz: the second case M4's exit criterion drives."""

    code = _compiled("30*sin(2*pi*time)")
    assert dyn.evaluate_control(code, 0.0, context="c") == pytest.approx(0.0)
    assert dyn.evaluate_control(code, 0.25, context="c") == pytest.approx(30.0)
    assert dyn.evaluate_control(code, 0.75, context="c") == pytest.approx(-30.0)


# ---------------------------------------------------------------------------
# What it may not.
# ---------------------------------------------------------------------------


def test_the_evaluation_globals_carry_no_builtins() -> None:
    """The second barrier, which exists because the first one is a whitelist.

    An AST whitelist is a list of node types and names; this is what is
    actually reachable at run time. Both have to be wrong for anything to
    get through, and they are wrong in different ways.
    """

    assert dyn._CONTROL_GLOBALS["__builtins__"] == {}
    for forbidden in ("__import__", "open", "eval", "exec", "getattr"):
        assert forbidden not in dyn._CONTROL_GLOBALS
    with pytest.raises(dyn.DynamicsError) as excinfo:
        _at("__import__('os')", 0.0)
    assert excinfo.value.reason == "control_formula_failed"


def test_a_formula_that_blows_up_names_the_instant_it_did() -> None:
    """Because "the control failed" without a time is not actionable."""

    with pytest.raises(dyn.DynamicsError) as excinfo:
        _at("1/(time - 2)", 2.0)
    assert excinfo.value.reason == "control_formula_failed"
    assert excinfo.value.observed["time_s"] == 2.0
    with pytest.raises(dyn.DynamicsError) as excinfo:
        _at("asin(1 + time)", 1.0)
    assert "asin" in excinfo.value.correction


def test_an_infinite_control_is_not_a_command() -> None:
    with pytest.raises(dyn.DynamicsError) as excinfo:
        _at("1e308 * 1e10", 0.0)
    assert excinfo.value.reason == "control_formula_failed"


def test_a_formula_that_is_not_an_expression_is_refused() -> None:
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.compile_control("time =", context="test actuator")
    assert excinfo.value.reason == "malformed_control_formula"


# ---------------------------------------------------------------------------
# What the number means once it exists.
# ---------------------------------------------------------------------------


def test_the_same_string_means_six_things_and_the_conversion_knows_which() -> None:
    """"30" is a third of a turn, thirty millimetres, or half a newton-metre.

    Which one it is comes from two other words in the script -- the
    actuator's kind and its joint's coordinate -- and this is the table
    that decides, once, in the module that owns every conversion.
    """

    cases = {
        ("position", "angular"): math.radians(30.0),
        ("position", "linear"): 0.03,
        ("velocity", "angular"): math.radians(30.0),
        ("velocity", "linear"): 0.03,
        ("motor", "angular"): 0.03,
        ("motor", "linear"): 30.0,
    }
    for (kind, motion), expected in cases.items():
        assert dyn.control_si(
            30.0, kind=kind, motion_type=motion, context="c"
        ) == pytest.approx(expected, rel=1.0e-12)


def test_a_motor_on_a_sliding_joint_is_the_one_that_converts_nothing() -> None:
    """Newtons are newtons. Stated because an identity is easy to forget."""

    assert dyn.control_si(
        123.456, kind="motor", motion_type="linear", context="c"
    ) == 123.456


# ---------------------------------------------------------------------------
# Time.
# ---------------------------------------------------------------------------


def test_a_computed_time_is_not_an_accumulated_one() -> None:
    """The rule, demonstrated on the arithmetic that motivates it.

    Adding 0.002 to itself five hundred times does not give 1.0, and the
    error grows with the run. ``start + index * step`` is exact to the last
    bit at every index and does not care how long the run has been going --
    which is what keeps the same script's trace identical across processes
    once a control signal depends on the number.
    """

    step = 0.002
    accumulated = 0.0
    for _index in range(500):
        accumulated += step
    computed = 0.0 + 500 * step
    assert accumulated != computed
    assert computed == 1.0
    assert abs(accumulated - computed) > 0.0


def test_the_pure_module_computes_its_own_time_and_never_reads_the_solvers() -> None:
    """A grep, because this is a rule about code rather than about a number.

    ``simulate`` steps the model itself, so ``data.time`` is right there and
    reaching for it would look entirely reasonable. It is a floating-point
    accumulation MuJoCo maintains, and a control that read it would make the
    trace depend on it.
    """

    from pathlib import Path

    source = (
        Path(__file__).resolve().parent.parent / "CadexDynamics.py"
    ).read_text(encoding="utf-8")
    assert "data.time" not in source, (
        "``simulate`` steps the model itself, so MuJoCo's own accumulated "
        "clock is right there and reaching for it would look reasonable."
    )
    # And the interface makes the alternative awkward on purpose: an
    # evaluation takes the instant as an argument rather than reading one.
    assert "def evaluate_control(code: Any, time_s: float" in source
