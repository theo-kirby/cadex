# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A chain that hangs from the base and is not a leg (ADR-722).

A success spec may name an appendage -- a tail, a trunk -- root first, and
bound three things about it read from the rollout's poses: the share of
frames any of its collision shapes is on the ground, how closely its root's
pitch follows the pitch of the body it hangs from, and how strongly its yaw
relative to the base follows a commanded yaw rate.
"""

from __future__ import annotations

import math

import pytest

import CadexDynamics as dyn
import CadexEvaluation as evaluation

HZ = 50
SPHERE = {"kind": "sphere", "size_mm": [20.0, 0.0, 0.0], "pos_mm": [-100.0, 0.0, 0.0],
          "quat_xyzw": [0.0, 0.0, 0.0, 1.0]}
RIG = {
    "base": "body", "reference_xyzw": [0.0, 0.0, 0.0, 1.0],
    "base_com_local_mm": [0.0, 0.0, 0.0], "floor_mm": 0.0,
    "appendage": {"bodies": ["t1", "t2"], "geoms": {"t1": [SPHERE], "t2": [SPHERE]},
                  "parent": "body"},
}


def _quat(yaw_deg=0.0, pitch_deg=0.0):
    """Yaw about world +Z after pitch about +Y, as xyzw."""

    cy, sy = math.cos(math.radians(yaw_deg) / 2), math.sin(math.radians(yaw_deg) / 2)
    cp, sp = math.cos(math.radians(pitch_deg) / 2), math.sin(math.radians(pitch_deg) / 2)
    # q_yaw * q_pitch
    return [-sy * sp, cy * sp, sy * cp, cy * cp]


def _rotate(q, v):
    x, y, z, w = q
    tx, ty, tz = 2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])
    return [v[0] + w * tx + y * tz - z * ty, v[1] + w * ty + z * tx - x * tz,
            v[2] + w * tz + x * ty - y * tx]


def _samples(seconds=8.0, *, base_pitch=lambda t: 0.0, tail_pitch=lambda t: 0.0,
             tail_yaw=lambda t: 0.0, height=300.0, base_yaw=lambda t: 0.0):
    """A base at ``height`` with a two-link tail behind it.

    ``tail_pitch`` and ``tail_yaw`` are the tail root's angles relative to
    the base; the second link carries on straight from the first.
    """

    out = []
    for i in range(int(seconds * HZ)):
        t = i / HZ
        base_q = _quat(base_yaw(t), base_pitch(t))
        root_q = _quat(base_yaw(t) + tail_yaw(t), base_pitch(t) + tail_pitch(t))
        root = [p + q for p, q in zip(_rotate(base_q, [-150.0, 0.0, 0.0]), [0.0, 0.0, height])]
        second = [p + q for p, q in zip(_rotate(root_q, [-200.0, 0.0, 0.0]), root)]
        out.append((t, {
            "body": {"position_mm": [0.0, 0.0, height], "rotation_xyzw": base_q},
            "t1": {"position_mm": root, "rotation_xyzw": root_q},
            "t2": {"position_mm": second, "rotation_xyzw": root_q},
        }))
    return out


def _hold(segments):
    return [value for seconds, value in segments for _ in range(int(round(seconds * HZ)))]


def test_a_tail_carried_rigidly_by_the_hips_correlates_fully_and_one_that_works_against_them_does_not() -> None:
    nod = lambda t: 12.0 * math.sin(2 * math.pi * 2.4 * t)
    rigid = evaluation.appendage_metrics(_samples(base_pitch=nod), RIG)
    assert rigid["appendage_pitch_parent_correlation"] == pytest.approx(1.0, abs=1e-9)
    # The root joint cancels the hips' pitch: the root holds its attitude.
    held = evaluation.appendage_metrics(
        _samples(base_pitch=nod, tail_pitch=lambda t: -nod(t)
                 + 5.0 * math.sin(2 * math.pi * 0.7 * t)), RIG)
    assert abs(held["appendage_pitch_parent_correlation"]) < 0.1
    assert held["appendage"]["parent_pitch_sd_deg"] == pytest.approx(12.0 / math.sqrt(2), rel=0.02)


def test_ground_contact_is_the_share_of_frames_a_shape_is_on_the_ground() -> None:
    # The tail tip hangs 100 mm below the root's line at a 30 deg droop...
    clear = evaluation.appendage_metrics(_samples(tail_pitch=lambda t: -30.0), RIG)
    assert clear["appendage_ground_contact_share"] == 0.0
    assert clear["appendage"]["min_clearance_mm"] > 1.0
    # ...and the first quarter of each second it droops until the far sphere is on the floor.
    # Far sphere centre: 200 + 100 mm along the link at pitch p, below z = 300.
    strike = -math.degrees(math.asin((300.0 - 20.0) / 300.0)) - 0.5
    read = evaluation.appendage_metrics(
        _samples(tail_pitch=lambda t: strike if (t % 1.0) < 0.25 else -30.0), RIG)
    # Frames 0-12 of every 50: thirteen of fifty.
    assert read["appendage_ground_contact_share"] == pytest.approx(13 / 50, abs=1e-9)
    assert read["appendage"]["min_clearance_mm"] < 0.0


def test_ground_contact_is_read_against_the_ground_under_the_shape() -> None:
    # A raised ground under the tail (x < -300 mm) at 140 mm.
    ground = lambda x, y: 140.0 if x < -300.0 else 0.0
    read = evaluation.appendage_metrics(_samples(tail_pitch=lambda t: -30.0), RIG, ground=ground)
    assert read["appendage_ground_contact_share"] == 1.0


def test_a_tail_that_sweeps_with_the_turn_command_reads_its_correlation_and_slope() -> None:
    rates = _hold([(2.0, 0.0), (2.0, 60.0), (2.0, -40.0), (2.0, 20.0)])
    turning = lambda t: rates[min(int(round(t * HZ)), len(rates) - 1)]
    def base_yaw(t):
        return sum(rates[:int(round(t * HZ))]) / HZ

    # Out of the turn: 0.4 deg of tail yaw per deg/s, against the rate's sign.
    read = evaluation.appendage_metrics(
        _samples(base_yaw=base_yaw, tail_yaw=lambda t: -0.4 * turning(t)), RIG,
        yaw_rates=rates)
    assert read["appendage_yaw_turn_correlation"] == pytest.approx(1.0, abs=1e-6)
    assert read["appendage"]["yaw_turn_r"] == pytest.approx(-1.0, abs=1e-6)
    assert read["appendage"]["yaw_deg_per_deg_s"] == pytest.approx(-0.4, abs=1e-3)
    # A tail that ignores the command reads none of it.
    still = evaluation.appendage_metrics(
        _samples(base_yaw=base_yaw, tail_yaw=lambda t: 8.0 * math.sin(2 * math.pi * 1.3 * t)),
        RIG, yaw_rates=rates)
    assert still["appendage_yaw_turn_correlation"] < 0.15


def test_a_command_that_never_changes_measures_no_turn_correlation() -> None:
    read = evaluation.appendage_metrics(_samples(), RIG, yaw_rates=[0.0] * 400)
    assert read["appendage_yaw_turn_correlation"] is None
    assert evaluation.check([{"id": "t", "metric": "appendage_yaw_turn_correlation",
                              "min": 0.3, "max": None}],
                            {"appendage_yaw_turn_correlation": None})[0]["pass"] is False
    with pytest.raises(ValueError):
        evaluation.appendage_metrics(_samples(), RIG, yaw_rates=[0.0] * 3)


def test_measure_reads_the_family_only_for_a_rig_with_an_appendage() -> None:
    episode = {"truncated": True, "termination": "", "duration_s": 8.0}
    samples = _samples(tail_pitch=lambda t: -30.0)
    plain = {key: value for key, value in RIG.items() if key != "appendage"}
    assert not any(name.startswith("appendage_")
                   for name in evaluation.measure(samples, episode, plain)["metrics"])
    read = evaluation.measure(samples, episode, RIG)
    assert read["metrics"]["appendage_ground_contact_share"] == 0.0
    assert "appendage_yaw_turn_correlation" not in read["metrics"]
    assert read["detail"]["appendage"]["bodies"] == ["t1", "t2"]
    turned = evaluation.measure(samples, episode, RIG,
                                commands={"yaw_rate": _hold([(4.0, 0.0), (4.0, 30.0)])})
    assert "appendage_yaw_turn_correlation" in turned["metrics"]


def test_every_appendage_metric_needs_an_appendage_and_the_turn_one_a_turn() -> None:
    family = {name: needs for name, (kind, needs) in evaluation.METRICS.items()
              if kind == "appendage"}
    assert family == {
        "appendage_ground_contact_share": ("base", "appendage"),
        "appendage_pitch_parent_correlation": ("base", "appendage"),
        "appendage_yaw_turn_correlation": ("base", "appendage", "turn"),
    }
    assert "appendage" in dyn._SUCCESS_NEED_CORRECTIONS


# -- the spec and the model ------------------------------------------------------

def test_a_spec_names_its_appendage_root_first_and_omits_it_when_none() -> None:
    from test_success_spec_api import BALANCE, SEEDS, _api, _scene, _source, _task

    api = _api()
    scene = _scene(api)
    base, limb = scene["components"]
    spec = api.success(BALANCE, seeds=SEEDS, appendage=[limb])
    assert list(spec.properties["appendage"]) == [limb]
    _task(api, scene, success=spec)
    assert "appendage" not in api.success(BALANCE, seeds=SEEDS).properties
    with pytest.raises(ValueError) as twice:
        api.success(BALANCE, seeds=SEEDS, appendage=[limb, limb])
    assert "more than once" in str(twice.value)
    stranger = api.component(_source("solid9"))
    with pytest.raises(ValueError) as refusal:
        _task(api, scene, success=api.success(BALANCE, seeds=SEEDS, appendage=[stranger]))
    assert "success.appendage[0]" in str(refusal.value)


def test_the_bundle_carries_the_appendage_and_the_model_refuses_what_is_not_a_chain() -> None:
    pytest.importorskip("mujoco")
    from test_success_spec_model import bundle, refusal, spec

    contact = [{"id": "clear", "metric": "appendage_ground_contact_share", "max": 0.0}]
    _model, task = bundle(spec(contact, appendage=["rear"]))
    assert task["success"]["appendage"] == ["rear"]
    assert "appendage" not in bundle(spec())[1]["success"]
    rig = dyn.evaluation_rig(_model, appendage=["rear"])
    assert rig["appendage"]["parent"] == "body"
    assert rig["appendage"]["geoms"]["rear"][0]["kind"] == "sphere"

    assert refusal(spec(contact)).reason == "success_metric_needs_appendage"
    assert refusal(spec(contact, appendage=["ghost"])).reason == "evaluation_body_missing"
    error = refusal(spec(contact, appendage=["front", "rear"]))
    assert error.reason == "evaluation_appendage_not_a_chain"
    assert error.observed["link"] == "rear"
