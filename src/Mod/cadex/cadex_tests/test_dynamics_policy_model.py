# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The pure module's half of a policy (docs/MUJOCO.md M7, phase 1).

Phase 0 measured what MJX, numpy and Python do. This tests what
:mod:`CadexDynamics` does with a file somebody else wrote: reading the
container without trusting a length in it, evaluating the network, and
cross-checking the whole of it against the task it claims to be for.

Nothing here goes through ``api.`` or through the worker -- the surface is
phase 3's and the receipt is phase 4's. What is under test is the arithmetic
and the refusals.

**The refusals get more room than the successes**, and that is the point of
the slice. A policy is the one artifact in a Cadex project that cannot be
rebuilt from the script, so every claim it makes about the mechanism is a
claim nothing else can check. A refusal nobody tested is a claim nobody
checks.
"""

from __future__ import annotations

import hashlib
import json
import math

import pytest

import CadexDynamics as dyn
import dynamics_policy_fixtures as pf

pytest.importorskip("mujoco")


@pytest.fixture(scope="module")
def prepared():
    return pf.swing_up_bundle()


@pytest.fixture(scope="module")
def container(prepared):
    return pf.policy_container(prepared, normalise=True)


def _decoded(container):
    return dyn.decode_policy(container["blob"])


def _verify(container, prepared, **overrides):
    decoded = _decoded(container)
    if overrides:
        decoded["header"] = {**decoded["header"], **overrides}
    return dyn.verify_policy(
        decoded, prepared["bundle"], task_sha256=prepared["task_sha256"]
    )


def _refusal(container, prepared, **overrides):
    with pytest.raises(dyn.DynamicsError) as excinfo:
        _verify(container, prepared, **overrides)
    return excinfo.value


# ---------------------------------------------------------------------------
# The container.
# ---------------------------------------------------------------------------


def test_the_container_round_trips_through_its_own_bytes(container) -> None:
    decoded = _decoded(container)
    assert decoded["header"] == container["header"]
    assert decoded["weights"] == pytest.approx(container["weights"], rel=0, abs=0)


def test_the_container_is_byte_identical_for_the_same_header_and_weights(
    container,
) -> None:
    """What makes a policy's digest a thing a script can state.

    ``assembly.policy(..., sha256=...)`` is only checkable because two
    encodings of one policy are one file. Sorted keys, no whitespace, ASCII,
    little-endian float32.
    """

    again = dyn.encode_policy(container["header"], container["weights"])
    assert again == container["blob"]
    assert hashlib.sha256(again).hexdigest() == container["sha256"]


def test_the_container_declares_itself_before_anything_reads_it(container) -> None:
    assert container["blob"].startswith(b"CXPOLICY1\n")
    assert container["header"]["schema"] == "cadex-policy-v1"


@pytest.mark.parametrize(
    "corrupt,reason",
    [
        (lambda blob: b"NOTAPOLICY" + blob[10:], "policy_not_a_container"),
        (lambda blob: blob[:12], "policy_truncated"),
        (lambda blob: blob[:10] + (1 << 40).to_bytes(8, "little") + blob[18:],
         "policy_truncated"),
        (lambda blob: blob[:-1], "policy_truncated"),
    ],
)
def test_a_container_that_lies_about_its_own_lengths_is_refused(
    container, corrupt, reason
) -> None:
    """Every length is checked against the bytes that are there.

    This is the one function in the module that reads a file a *user*
    supplied rather than a value the engine computed, so a declared header
    length of a terabyte is a refusal rather than an allocation.
    """

    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.decode_policy(corrupt(container["blob"]))
    assert excinfo.value.reason == reason
    assert excinfo.value.correction


def test_a_header_that_is_not_canonical_json_is_refused(container) -> None:
    blob = container["blob"]
    length = int.from_bytes(blob[10:18], "little")
    broken = blob[:18] + b"{not json" + b" " * (length - 9) + blob[18 + length:]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.decode_policy(broken)
    assert excinfo.value.reason == "policy_header_malformed"


def test_a_file_larger_than_the_cap_is_refused_before_it_is_parsed() -> None:
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.decode_policy(b"\x00" * (dyn.MAXIMUM_POLICY_BYTES + 1))
    assert excinfo.value.reason == "policy_too_large"
    assert "checkpoint" in excinfo.value.correction


def test_the_cap_is_the_one_phase_0_measured() -> None:
    """4 MiB, over a 902 KiB humanoid-scale policy with room and no more.

    docs/MUJOCO.md 3.1 guessed "tens of megabytes"; phase 0 measured three
    orders of magnitude less, and this is the constant that number sized.
    """

    assert dyn.MAXIMUM_POLICY_BYTES == 4 * 1024 * 1024
    assert dyn.MAXIMUM_POLICY_BYTES > 230_925 * 4


# ---------------------------------------------------------------------------
# The forward pass.
# ---------------------------------------------------------------------------


def test_the_engine_reproduces_a_witness_it_did_not_compute(container, prepared) -> None:
    """The claim the whole slice rests on, and it is not a tautology.

    The fixture's witness is produced by a **second** forward pass written
    out in ``dynamics_policy_fixtures``, never by ``policy_forward``. So this
    asserts two implementations of one network agree -- which is exactly what
    the container's witness asserts about the engine and the trainer.
    """

    evidence = _verify(container, prepared)
    assert evidence["witness_samples"] == 8
    assert evidence["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE
    assert evidence["witness_error"] < 1.0e-9


def test_the_forward_pass_takes_a_named_observation_or_an_ordered_one(
    container, prepared
) -> None:
    """An episode holds names; the witness records an order. Both work.

    M8 swaps ``evaluate_episode``'s ``actions=`` callable for this, and that
    callable is handed the named mapping ``observation_values`` produces --
    so the mapping path is the one that matters, and the ordered path is what
    the container itself records.
    """

    header, weights = container["header"], container["weights"]
    ordered = header["evaluation"]["observations"][0]
    named = dict(zip(header["observations"], ordered))
    assert dyn.policy_forward(header, weights, named) == pytest.approx(
        dyn.policy_forward(header, weights, ordered), rel=0, abs=0
    )


def test_an_observation_missing_a_channel_is_refused_by_name(container) -> None:
    header, weights = container["header"], container["weights"]
    named = dict(zip(header["observations"],
                     header["evaluation"]["observations"][0]))
    named.pop("tip_z")
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.policy_forward(header, weights, named)
    assert excinfo.value.reason == "policy_observation_mismatch"
    assert "tip_z" in str(excinfo.value)


def test_an_ordered_observation_of_the_wrong_width_is_refused(container) -> None:
    header, weights = container["header"], container["weights"]
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.policy_forward(header, weights, [0.0, 0.0])
    assert excinfo.value.reason == "policy_observation_mismatch"
    assert excinfo.value.observed == {"given": 2, "expected": 5}


def test_the_output_lands_inside_the_action_range_the_bundle_advertised(
    container, prepared
) -> None:
    """A tanh output through the bundle's own half-range and midpoint.

    This is hazard 1's fifth payment made visible: the number leaving the
    forward pass is already in newton-millimetres, so ``evaluate_episode``
    applies it through exactly the ``clamp then x scale`` it already applies
    to a fallback formula. There is no new conversion for it to be wrong in.
    """

    header, weights = container["header"], container["weights"]
    action = prepared["bundle"]["actions"][0]
    for sample in header["evaluation"]["observations"]:
        produced = dyn.policy_forward(header, weights, sample)
        assert len(produced) == 1
        assert float(action["low"]) <= produced[0] <= float(action["high"])
    assert action["unit"] == "nmm"


def test_a_relu_network_is_evaluated_as_relu(prepared) -> None:
    """Both whitelisted activations, and the difference is a real number."""

    tanh = pf.policy_container(prepared, activation="tanh", normalise=True)
    relu = pf.policy_container(prepared, activation="relu", normalise=True)
    assert tanh["weights"] == relu["weights"]

    sample = tanh["header"]["evaluation"]["observations"][0]
    assert dyn.policy_forward(tanh["header"], tanh["weights"], sample) != (
        pytest.approx(dyn.policy_forward(relu["header"], relu["weights"], sample))
    )
    # ...and each still reproduces its own witness.
    for entry in (tanh, relu):
        assert dyn.verify_policy(
            dyn.decode_policy(entry["blob"]), prepared["bundle"],
            task_sha256=prepared["task_sha256"],
        )["witness_error"] < dyn.POLICY_WITNESS_TOLERANCE


def test_the_normaliser_is_arithmetic_that_has_to_round_trip(prepared) -> None:
    """Explicit arrays in the container, not a convention.

    The normaliser is *not* a unit conversion -- units are the bundle's and
    do not change here -- but it is arithmetic that two implementations must
    agree on, so it gets the same treatment the reward whitelist gets: it is
    written down in the file and checked by a second implementation.
    """

    plain = pf.policy_container(prepared, normalise=False)
    scaled = pf.policy_container(prepared, normalise=True)
    assert plain["header"]["normaliser"]["mean"] == [0.0] * 5
    assert plain["header"]["normaliser"]["std"] == [1.0] * 5
    assert scaled["header"]["normaliser"]["mean"] != [0.0] * 5

    sample = plain["header"]["evaluation"]["observations"][0]
    assert dyn.policy_forward(plain["header"], plain["weights"], sample) != (
        pytest.approx(dyn.policy_forward(scaled["header"], scaled["weights"],
                                          sample))
    )


def test_a_normaliser_with_a_zero_standard_deviation_is_refused(container) -> None:
    """A channel that never moved during training has no scale.

    Refused rather than divided by, because the alternative is an infinity
    that propagates into every action and reads as a broken mechanism.
    """

    header = {**container["header"],
              "normaliser": {"mean": [0.0] * 5, "std": [1.0, 1.0, 0.0, 1.0, 1.0]}}
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.policy_forward(header, container["weights"],
                           header["evaluation"]["observations"][0])
    assert excinfo.value.reason == "policy_normaliser_malformed"
    assert "1.0 for those rather than 0.0" in excinfo.value.correction


# ---------------------------------------------------------------------------
# The six claims verify_policy checks.
# ---------------------------------------------------------------------------


def test_a_policy_trained_on_a_different_task_is_refused(container, prepared) -> None:
    """Claim 1, and the one a user meets most often.

    Change a reward weight and the policy is optimising something else. The
    refusal carries both digests so the mismatch is a fact rather than an
    accusation.
    """

    error = _refusal(container, prepared,
                     task={"sha256": "f" * 64, "label": "swing_up"})
    assert error.reason == "policy_task_mismatch"
    assert error.observed["policy_task_sha256"] == "f" * 64
    assert error.observed["task_sha256"] == prepared["task_sha256"]
    assert "Retrain" in error.correction


def test_a_policy_trained_against_a_different_model_is_refused(
    container, prepared
) -> None:
    """Claim 2: a mechanism whose geometry has since changed.

    The task and the model are two artifacts that only mean anything
    together, and M6 published both digests for exactly this.
    """

    error = _refusal(container, prepared,
                     model={"sha256": "a" * 64, "path": "outputs/job-model.xml"})
    assert error.reason == "policy_model_mismatch"
    assert "different robot" in error.correction


def test_a_policy_observing_the_channels_in_another_order_is_refused(
    container, prepared
) -> None:
    """Claim 3, and the failure it prevents is silent.

    The observation vector is positional: the policy's first input is the
    task's first channel. Reordering the observations in a script changes
    what every weight means, and nothing about the resulting motion would say
    so. The refusal lists both orders.
    """

    reordered = list(container["header"]["observations"])
    reordered[0], reordered[1] = reordered[1], reordered[0]
    error = _refusal(container, prepared, observations=reordered)
    assert error.reason == "policy_channels_mismatch"
    assert error.observed["policy_channels"] == reordered
    assert error.observed["task_channels"] == ["angle", "rate", "tip_x",
                                                "tip_y", "tip_z"]


def test_a_policy_missing_a_channel_the_task_declares_is_refused(
    container, prepared
) -> None:
    error = _refusal(container, prepared,
                     observations=container["header"]["observations"][:-1])
    assert error.reason == "policy_channels_mismatch"


@pytest.mark.parametrize(
    "field,value",
    [
        ("actuator", "hinge/servo"),
        ("index", 3),
        ("unit", "deg"),
        ("low", -1.0),
        ("high", 1.0),
        ("scale", 1.0),
    ],
)
def test_a_policy_whose_action_table_differs_anywhere_is_refused(
    container, prepared, field, value
) -> None:
    """Claim 4, field by field.

    The action table is copied from the bundle verbatim, so *any* difference
    means the policy was trained against a task whose actuators, units or
    derived limits are not these. Each field is checked because each one is a
    different way to drive the wrong thing.
    """

    actions = [{**container["header"]["actions"][0], field: value}]
    error = _refusal(container, prepared, actions=actions)
    assert error.reason == "policy_actions_mismatch"
    assert error.observed["field"] == field


def test_an_action_field_that_arrived_as_the_wrong_type_is_a_refusal(
    container, prepared
) -> None:
    """...rather than an exception. This reads a file somebody else wrote."""

    actions = [{**container["header"]["actions"][0], "low": "-2000"}]
    error = _refusal(container, prepared, actions=actions)
    assert error.reason == "policy_actions_mismatch"


def test_a_policy_driving_a_different_number_of_actuators_is_refused(
    container, prepared
) -> None:
    error = _refusal(container, prepared,
                     actions=list(container["header"]["actions"]) * 2)
    assert error.reason == "policy_actions_mismatch"
    assert error.observed == {"policy_actions": 2, "task_actions": 1}


def test_a_policy_that_scaled_its_outputs_differently_is_refused(
    container, prepared
) -> None:
    """Claim 5, and the numbers come from the mechanism rather than the file.

    ``output_scale`` and ``output_bias`` must be the half-range and midpoint
    of each action's own advertised bound -- which the bundle *derived* from
    a torque limit or a joint limit. A policy that scaled its outputs
    differently is driving the actuator to a limit nobody designed, and
    would look like an aggressive gait rather than a wrong file.
    """

    network = {**container["header"]["network"], "output_scale": [5000.0]}
    error = _refusal(container, prepared, network=network)
    assert error.reason == "policy_output_range_mismatch"
    assert error.observed["task_value"] == [2000.0]
    assert "limit nobody designed" in error.correction


def test_the_output_map_is_the_bundles_own_half_range_and_midpoint(prepared) -> None:
    scale, bias = dyn._policy_action_map(prepared["bundle"])
    action = prepared["bundle"]["actions"][0]
    assert scale == [(float(action["high"]) - float(action["low"])) / 2.0]
    assert bias == [(float(action["high"]) + float(action["low"])) / 2.0]
    assert scale == [2000.0] and bias == [0.0]


def test_a_policy_that_does_not_reproduce_its_own_witness_is_refused(
    container, prepared
) -> None:
    """Claim 6, and the one that makes M8 safe.

    A container whose weights are intact but whose layer order, bias layout
    or activation the engine reads differently passes the first five claims
    and fails this one. Simulated here by moving one recorded action: the
    engine recomputes and disagrees.
    """

    evaluation = json.loads(json.dumps(container["header"]["evaluation"]))
    evaluation["actions"][3][0] += 500.0
    error = _refusal(container, prepared, evaluation=evaluation)
    assert error.reason == "policy_witness_disagrees"
    assert error.observed["witness"] == 3
    assert error.observed["error"] > dyn.POLICY_WITNESS_TOLERANCE
    assert "different network" in error.correction


def test_the_witness_tolerance_is_relative_to_each_actions_own_range(
    container, prepared
) -> None:
    """A tolerance in absolute units would mean something different per joint.

    A 2 N*mm error is nothing on a 2000 N*mm motor and everything on a 2
    N*mm one. Measured just inside the bound and just outside it.
    """

    span = 4000.0  # -2000 .. 2000
    for offset, refused in ((span * 0.5e-4, False), (span * 2.0e-4, True)):
        evaluation = json.loads(json.dumps(container["header"]["evaluation"]))
        evaluation["actions"][0][0] += offset
        if refused:
            assert _refusal(container, prepared,
                            evaluation=evaluation).reason == "policy_witness_disagrees"
        else:
            _verify(container, prepared, evaluation=evaluation)


def test_a_policy_recording_too_few_witness_samples_is_refused(
    prepared,
) -> None:
    """The witness cannot be optional and cannot be one sample.

    One vector agrees by accident far more often than eight do. This is the
    refusal that stops a trainer shipping a policy nothing can check.
    """

    thin = pf.policy_container(prepared, samples=3)
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.verify_policy(dyn.decode_policy(thin["blob"]), prepared["bundle"],
                          task_sha256=prepared["task_sha256"])
    assert excinfo.value.reason == "policy_witness_missing"
    assert excinfo.value.observed["minimum"] == dyn.MINIMUM_POLICY_WITNESS_SAMPLES
    assert "trusted" in excinfo.value.correction


def test_a_witness_with_more_actions_than_observations_is_refused(
    container, prepared
) -> None:
    evaluation = {**container["header"]["evaluation"],
                  "actions": container["header"]["evaluation"]["actions"][:4]}
    error = _refusal(container, prepared, evaluation=evaluation)
    assert error.reason == "policy_witness_missing"


# ---------------------------------------------------------------------------
# The network header, which is read before any length in it is trusted.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "network,fragment",
    [
        ({"kind": "lstm"}, "multilayer perceptron"),
        ({"activation": "gelu"}, "guessed wrong"),
        ({"output": "identity"}, "bounded output"),
        ({"layers": []}, "at least one"),
        ({"layers": [[5, 8], [9, 1]]}, "have to chain"),
        ({"layers": [[5, 2048], [2048, 1]]}, "not free"),
        ({"layers": [[5, 8]] * 9}, "generated by a loop"),
    ],
)
def test_a_malformed_network_header_is_refused_with_the_reason(
    container, network, fragment
) -> None:
    header = {**container["header"],
              "network": {**container["header"]["network"], **network}}
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn._policy_layers(header, context="this policy")
    assert excinfo.value.reason == "policy_network_malformed"
    assert fragment in excinfo.value.correction


def test_a_weight_count_that_disagrees_with_the_header_is_refused(container) -> None:
    """The two halves of the file came from different runs."""

    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.policy_forward(container["header"], container["weights"][:-1],
                           container["header"]["evaluation"]["observations"][0])
    assert excinfo.value.reason == "policy_weights_mismatch"
    assert excinfo.value.observed["carried"] == len(container["weights"]) - 1


def test_a_network_whose_output_width_is_not_the_action_count_is_refused(
    prepared,
) -> None:
    wide = pf.policy_container(prepared)
    header = dict(wide["header"])
    header["network"] = {**header["network"],
                         "layers": [[5, 8], [8, 8], [8, 2]],
                         "output_scale": [2000.0, 2000.0],
                         "output_bias": [0.0, 0.0]}
    with pytest.raises(dyn.DynamicsError) as excinfo:
        dyn.verify_policy({"header": header, "weights": wide["weights"]},
                          prepared["bundle"],
                          task_sha256=prepared["task_sha256"])
    assert excinfo.value.reason == "policy_network_malformed"
    assert excinfo.value.observed == {"outputs": 2, "actions": 1}


def test_a_container_declaring_an_unknown_schema_is_refused(container, prepared) -> None:
    error = _refusal(container, prepared, schema="cadex-policy-v2")
    assert error.reason == "policy_schema_unknown"
    assert "training/cadex_train.py" in error.correction


# ---------------------------------------------------------------------------
# The evidence, which is what the receipt publishes.
# ---------------------------------------------------------------------------


def test_the_evidence_names_everything_the_receipt_needs(container, prepared) -> None:
    evidence = _verify(container, prepared)
    assert evidence["schema"] == dyn.POLICY_SCHEMA
    assert evidence["task_sha256"] == prepared["task_sha256"]
    assert evidence["model_sha256"] == prepared["bundle"]["model"]["sha256"]
    assert evidence["observation_channels"] == ["angle", "rate", "tip_x",
                                                 "tip_y", "tip_z"]
    assert evidence["action_count"] == 1
    assert evidence["layers"] == [[5, 8], [8, 8], [8, 1]]
    assert evidence["parameters"] == 5 * 8 + 8 + 8 * 8 + 8 + 8 * 1 + 1
    assert evidence["activation"] == "tanh"
    assert evidence["witness_tolerance"] == dyn.POLICY_WITNESS_TOLERANCE
    # ...and it is JSON, because it becomes a retained artifact.
    json.dumps(evidence)


# ---------------------------------------------------------------------------
# M8's seam, exercised now so that M8 is a swap rather than a discovery.
# ---------------------------------------------------------------------------


def test_a_policy_drives_an_episode_through_the_callable_m8_will_use(
    container, prepared
) -> None:
    """``evaluate_episode(actions=...)`` already takes a policy.

    M6 wrote that callable as M8's seam. This is the proof it fits: the same
    episode runs with the policy's forward pass in place of the actuators'
    fallback formulas, and nothing else changes. M8 swaps where the action
    comes from and nothing else.
    """

    header, weights = container["header"], container["weights"]
    model = prepared["model"]
    task = prepared["bundle"]

    fallback = dyn.evaluate_episode(model, task)
    driven = dyn.evaluate_episode(
        model, task,
        actions=lambda step, observation: dyn.policy_forward(
            header, weights, observation),
    )

    # The fallback runs the whole horizon: its formula is a constant zero, so
    # the pendulum simply swings.
    assert fallback["step_count"] == 100
    assert fallback["truncated"] is True

    # The random network drives it hard enough to trip the task's own
    # `spun_out` rule, which is the strongest available evidence that the
    # callable was actually consulted -- a fallback episode cannot terminate.
    assert driven["step_count"] < 100
    assert driven["terminated_step"] is not None
    assert driven["termination"] == "spun_out"
    assert driven["total_reward"] != pytest.approx(fallback["total_reward"])

    # ...and every action it produced stayed inside the advertised range,
    # because the forward pass emits through the bundle's own output map.
    for step in driven["steps"]:
        assert -2000.0 <= step["action"][0] <= 2000.0
