# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A policy is played under the command filter it was trained with (ADR-558).

The trainer writes ``training.action_filter_alpha`` (ADR-160) and
``training.command_slew_deg`` (ADR-162) into every ``.cxpolicy`` header, and
says why in its own comment: *a policy trained with a filter has to be
PLAYED with it*. Until ADR-558 the engine read neither, so every rollout,
checkpoint rollout and evaluation played a filtered policy unfiltered -- a
controller it was never trained against.

:func:`CadexDynamics.rollout_policy` is the one path all three take, so the
filter lives there. The claims:

* **The issued command follows the trainer's recurrence.** Clamp, then the
  EMA, then the slew limit, the first command of an episode passed through
  unfiltered -- written out here as a reference rather than imported.
* **No filter recorded is today's behaviour, exactly.** An old header with
  neither key, and a header recording ``1.0`` and ``0.0``, play the same
  frames, bit for bit, as the policy's raw output.
* **Evaluation applies it**, because it plays :func:`rollout_policy`, and the
  report says which filter it played.
"""

from __future__ import annotations

import copy

import pytest

import CadexDynamics as dyn

mujoco = pytest.importorskip("mujoco")

import dynamics_policy_fixtures as pf  # noqa: E402
from test_evaluate_success_model import BALANCE, evaluate, prepared  # noqa: E402
from test_success_spec_model import spec  # noqa: E402

COMPONENTS = ["post", "link"]


def _made(**training):
    made = pf.swing_up_bundle(task={**pf.SWING_UP_TASK, "termination": []})
    container = pf.policy_container(made, normalise=True)
    header = copy.deepcopy(container["header"])
    header["training"].update(training)
    made["container"] = {"header": header, "weights": container["weights"]}
    return made


def _rollout(made, monkeypatch=None, *, seed=3):
    raw: list[list[float]] = []
    if monkeypatch is not None:
        forward = dyn.policy_forward

        def recording(*args, **kwargs):
            values = forward(*args, **kwargs)
            raw.append([float(v) for v in values])
            return values

        monkeypatch.setattr(dyn, "policy_forward", recording)
    run = dyn.rollout_policy(
        dyn.load_model(made["model_xml"]), made["bundle"], made["container"],
        components=COMPONENTS, frames_per_second=50, seed=seed,
    )
    issued = [frame["actuator_commands"] for frame in run["frames"]
              if "actuator_commands" in frame]
    return run, raw, issued


def flat(rows):
    return [value for row in rows for value in row]


def reference(raw, actions, *, alpha=1.0, slew=0.0):
    """The trainer's recurrence (``cadex_train.py``, ADR-160 then ADR-162)."""

    out, previous = [], None
    for row in raw:
        clamped = [min(max(v, float(a["low"])), float(a["high"]))
                   for v, a in zip(row, actions)]
        if previous is not None:
            if alpha < 1.0:
                clamped = [alpha * c + (1.0 - alpha) * p for c, p in zip(clamped, previous)]
            if slew > 0.0:
                clamped = [min(max(c, p - slew), p + slew) for c, p in zip(clamped, previous)]
        out.append(clamped)
        previous = clamped
    return out


def test_a_filtered_policy_is_played_through_its_filter(monkeypatch) -> None:
    made = _made(action_filter_alpha=0.3)
    run, raw, issued = _rollout(made, monkeypatch)

    assert len(issued) == len(raw) == run["episode"]["step_count"]
    want = reference(raw, made["bundle"]["actions"], alpha=0.3)
    assert flat(issued) == pytest.approx(flat(want), abs=1e-12)
    # The filter did something: the unfiltered clamp is not what was issued.
    assert flat(issued) != pytest.approx(flat(reference(raw, made["bundle"]["actions"])), abs=1e-6)
    assert issued[0] == pytest.approx(want[0])
    assert run["command_filter"] == {"action_filter_alpha": 0.3, "command_slew_deg": 0.0}


def test_a_slew_limited_policy_is_played_through_both_operators_in_order(monkeypatch) -> None:
    made = _made(action_filter_alpha=0.7, command_slew_deg=0.05)
    _run, raw, issued = _rollout(made, monkeypatch)

    want = reference(raw, made["bundle"]["actions"], alpha=0.7, slew=0.05)
    assert flat(issued) == pytest.approx(flat(want), abs=1e-12)
    steps = [abs(b - a) for prev, cur in zip(issued, issued[1:]) for a, b in zip(prev, cur)]
    assert max(steps) <= 0.05 + 1e-12


def test_a_policy_with_no_filter_recorded_plays_exactly_as_before(monkeypatch) -> None:
    old = _made()
    old["container"]["header"]["training"].pop("action_filter_alpha", None)
    old["container"]["header"]["training"].pop("command_slew_deg", None)
    run_old, raw, issued_old = _rollout(old, monkeypatch)
    assert issued_old == reference(raw, old["bundle"]["actions"])
    assert run_old["command_filter"] == {"action_filter_alpha": 1.0, "command_slew_deg": 0.0}

    explicit = _made(action_filter_alpha=1.0, command_slew_deg=0.0)
    run_explicit, _raw, _issued = _rollout(explicit)
    assert run_explicit["frames"] == run_old["frames"]


def test_a_header_without_a_training_block_still_plays() -> None:
    made = _made()
    made["container"]["header"].pop("training")
    run, _raw, _issued = _rollout(made)
    assert run["command_filter"] == {"action_filter_alpha": 1.0, "command_slew_deg": 0.0}


@pytest.mark.parametrize("training, field", [
    ({"action_filter_alpha": 0.0}, "action_filter_alpha"),
    ({"action_filter_alpha": 1.5}, "action_filter_alpha"),
    ({"action_filter_alpha": "half"}, "action_filter_alpha"),
    ({"command_slew_deg": -1.0}, "command_slew_deg"),
])
def test_a_filter_the_trainer_would_refuse_is_refused(training, field) -> None:
    with pytest.raises(dyn.DynamicsError) as caught:
        _rollout(_made(**training))
    assert caught.value.reason == "policy_command_filter_invalid"
    assert field in str(caught.value)


def test_evaluation_plays_the_recorded_filter_and_says_so(monkeypatch) -> None:
    made = prepared(spec(BALANCE, episode_seconds=2.0), still=False)
    made["container"]["header"]["training"]["action_filter_alpha"] = 0.25
    raw: list[list[float]] = []
    forward = dyn.policy_forward

    def recording(*args, **kwargs):
        values = forward(*args, **kwargs)
        raw.append([float(v) for v in values])
        return values

    monkeypatch.setattr(dyn, "policy_forward", recording)
    traces: list[dict] = []
    report = evaluate(made, on_trace=lambda _seed, document: traces.append(document))

    assert report["command_filter"] == {"action_filter_alpha": 0.25, "command_slew_deg": 0.0}
    actions = made["bundle"]["actions"]
    offset = 0
    assert traces
    for document in traces:
        assert document["policy"]["command_filter"] == report["command_filter"]
        issued = [frame["actuator_commands"] for frame in document["frames"]
                  if "actuator_commands" in frame]
        mine = raw[offset:offset + len(issued)]
        offset += len(issued)
        assert len(issued) > 2
        assert flat(issued) == pytest.approx(flat(reference(mine, actions, alpha=0.25)), abs=1e-12)
        assert flat(issued) != pytest.approx(flat(reference(mine, actions)), abs=1e-6)
    assert offset == len(raw)
