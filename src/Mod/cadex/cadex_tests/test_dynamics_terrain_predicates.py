# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Terrain predicates, and a held-out course per evaluation seed (ADR-718).

A success spec can bound what a robot did on its ground: how far it made
good along the heading it started on, whether it fell, and the steps and
slopes it crossed. A drawn box course (ADR-717) is re-drawn for each
evaluation seed from a stream the trainer's pool never uses, so a policy is
judged on courses it did not train on, and the seed's rollout stands on that
course: its geoms placed in the compiled model, its scan reading it, its
predicates counting its features.
"""

from __future__ import annotations

import hashlib
import json
import math

import pytest

import CadexDynamics as dyn
import CadexEvaluation as evaluation
from test_dynamics_terrain_random import RANDOM_COURSE, _descriptor

# -- the held-out course, pure ------------------------------------------------


def test_each_seed_draws_its_own_held_out_course_that_fits_the_models_slots() -> None:
    descriptor = _descriptor()
    pooled = [repr(course["features"]) for course in descriptor["pool"]]
    drawn = {}
    for seed in range(1001, 1011):
        course = dyn.terrain_evaluation_course(descriptor, seed)
        assert course == dyn.terrain_evaluation_course(descriptor, seed)
        assert course["course"]["seed"] == seed
        assert course["course"]["key"] == f"eval:{seed}:{course['course']['draw']}"
        assert course["course"]["algorithm"] == dyn.TERRAIN_EVALUATION_ALGORITHM
        assert repr(course["features"]) not in pooled
        assert len(course["boxes"]) <= descriptor["slots"] == course["slots"]
        assert "pool" not in course
        built = dyn.terrain_boxes(course["features"], descriptor["x_range_mm"],
                                  descriptor["y_range_mm"])
        assert built["boxes"] == course["boxes"]
        assert dyn.terrain_box_ground_mm(course, 0.0, 0.0) == 0.0
        drawn[seed] = repr(course["features"])
    assert len(set(drawn.values())) == 10


def test_a_listed_course_is_every_seeds_course() -> None:
    listed = {key: RANDOM_COURSE[key] for key in ("form", "x_range_mm", "y_range_mm")}
    descriptor = dyn.terrain_grid(
        {**listed, "features": [{"kind": "step", "x_mm": 800.0, "height_mm": 60.0}]})["descriptor"]
    assert dyn.terrain_evaluation_course(descriptor, 1001) == descriptor
    assert "course" not in dyn.terrain_evaluation_course(descriptor, 1001)


def test_a_seed_with_no_draw_that_fits_is_refused_with_its_reason() -> None:
    descriptor = {**_descriptor(), "slots": 0}
    with pytest.raises(dyn.DynamicsError) as caught:
        dyn.terrain_evaluation_course(descriptor, 1001)
    assert caught.value.reason == "terrain_evaluation_course_unfit"
    assert caught.value.correction


# -- the predicates, pure -----------------------------------------------------

RIG = {"base": "body", "reference_xyzw": [0.0, 0.0, 0.0, 1.0], "base_com_local_mm": [0.0, 0.0, 0.0]}
STEP_SLOPE = {"features": [
    {"kind": "step", "x_mm": 600.0, "height_mm": -80.0},
    {"kind": "slope", "from_x_mm": 1000.0, "to_x_mm": 1500.0, "grade_deg": 12.0},
    {"kind": "step", "x_mm": 2000.0, "height_mm": 40.0},
    {"kind": "bump", "x_mm": 700.0, "y_mm": 0.0, "radius_mm": 100.0, "height_mm": 30.0},
]}


def _ground(x_mm: float, y_mm: float) -> float:
    return dyn.terrain_height_mm([f for f in STEP_SLOPE["features"] if f["kind"] != "bump"],
                                 x_mm, y_mm)


def _samples(xs, *, height_mm=300.0, pitch_deg=0.0, yaw_deg=0.0, ground=_ground):
    out = []
    for index, x in enumerate(xs):
        pitch = math.radians(pitch_deg if index == len(xs) - 1 else 0.0) / 2.0
        yaw = math.radians(yaw_deg) / 2.0
        # yaw about z, then pitch about y; [x, y, z, w]
        quat = [-math.sin(yaw) * math.sin(pitch), math.cos(yaw) * math.sin(pitch),
                math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch)]
        position = [x * math.cos(2 * yaw), x * math.sin(2 * yaw), ground(x, 0.0) + height_mm]
        out.append((0.02 * index, {"body": {"position_mm": position, "rotation_xyzw": quat}}))
    return out


def test_steps_and_slopes_crossed_are_counted_with_the_largest_of_each() -> None:
    read = evaluation.terrain_metrics(_samples([0.0, 400.0, 900.0, 1700.0]), RIG,
                                      terrain=STEP_SLOPE, ground=_ground)
    assert read["falls"] == 0.0
    assert read["steps_crossed"] == 1.0 and read["largest_step_crossed_mm"] == 80.0
    assert read["slopes_crossed"] == 1.0
    assert read["steepest_slope_crossed_deg"] == pytest.approx(12.0)
    assert [f["kind"] for f in read["terrain"]["crossed"]] == ["step", "slope"]
    assert read["terrain"]["features"] == 3
    short = evaluation.terrain_metrics(_samples([0.0, 500.0]), RIG,
                                       terrain=STEP_SLOPE, ground=_ground)
    assert short["steps_crossed"] == 0.0 and short["largest_step_crossed_mm"] == 0.0
    # Crossed and come back is not crossed.
    back = evaluation.terrain_metrics(_samples([0.0, 900.0, 300.0]), RIG,
                                      terrain=STEP_SLOPE, ground=_ground)
    assert back["steps_crossed"] == 0.0


def test_a_fall_is_read_from_tilt_or_height_above_the_ground_under_the_base() -> None:
    # Down an 80 mm step at standing height above the ground is not a fall.
    assert evaluation.terrain_metrics(_samples([0.0, 900.0]), RIG, ground=_ground)["falls"] == 0.0
    tipped = _samples([0.0, 100.0], pitch_deg=evaluation.FALL_TILT_DEG + 1.0)
    assert evaluation.terrain_metrics(tipped, RIG)["falls"] == 1.0
    leaning = _samples([0.0, 100.0], pitch_deg=evaluation.FALL_TILT_DEG - 5.0)
    assert evaluation.terrain_metrics(leaning, RIG)["falls"] == 0.0
    slumped = _samples([0.0, 100.0]) + [(0.1, {"body": {
        "position_mm": [200.0, 0.0, 140.0], "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}})]
    assert evaluation.terrain_metrics(slumped, RIG)["falls"] == 1.0
    # 140 mm over flat ground is a fall; 140 mm over a 200 mm ledge read as
    # flat would hide one, so the ground is the course's.
    raised = _samples([0.0, 100.0], ground=lambda x, y: 0.0)
    raised.append((0.1, {"body": {"position_mm": [200.0, 0.0, 400.0],
                                  "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}}))
    assert evaluation.terrain_metrics(raised, RIG, ground=lambda x, y: 0.0)["falls"] == 0.0
    assert evaluation.terrain_metrics(raised, RIG, ground=lambda x, y: 260.0 if x > 150 else 0.0)[
        "falls"] == 1.0


def test_distance_made_good_is_along_the_heading_the_episode_started_on() -> None:
    base = evaluation.base_series(_samples([0.0, 250.0, 1000.0], yaw_deg=30.0,
                                           ground=lambda x, y: 0.0), RIG)
    assert evaluation.posture(base, None)["distance_made_good_mm"] == pytest.approx(1000.0)
    sideways = [(t, {"body": {"position_mm": [0.0, 30.0 * i, 300.0],
                              "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]}}) for i, t in enumerate((0, .1, .2))]
    assert evaluation.posture(evaluation.base_series(sideways, RIG), None)[
        "distance_made_good_mm"] == pytest.approx(0.0)


def test_the_terrain_family_is_in_the_vocabulary_with_its_needs() -> None:
    assert evaluation.METRICS["distance_made_good_mm"] == ("posture", ("base",))
    assert evaluation.METRICS["falls"] == ("terrain", ("base",))
    for name in ("steps_crossed", "slopes_crossed", "largest_step_crossed_mm",
                 "steepest_slope_crossed_deg"):
        assert evaluation.METRICS[name] == ("terrain", ("base", "terrain"))


# -- the model, stock MuJoCo ----------------------------------------------------

mujoco = pytest.importorskip("mujoco")


def test_a_placed_course_is_the_ground_a_block_comes_to_rest_on() -> None:
    """``place_terrain_course`` re-places the compiled model's slots; a block
    dropped on a raised flat place of each seed's course rests 10 mm (its
    half-height) above that course's ground, not course 0's."""

    from test_dynamics_terrain import _free_block

    components, joints, _ = _free_block()
    built = dyn.build_model(components, joints, terrain=RANDOM_COURSE)
    descriptor = built["environment"]["terrain"]
    grounds = []
    for seed in (1001, 1002, 1003, 1004):
        course = dyn.terrain_evaluation_course(descriptor, seed)
        for x_mm in range(800, 5600, 25):
            around = {round(dyn.terrain_box_ground_mm(course, x_mm + dx, dy), 6)
                      for dx in range(-200, 225, 25) for dy in (-60.0, 0.0, 60.0)}
            if len(around) == 1 and abs(next(iter(around))) > 5.0 and next(iter(around)) != round(
                    dyn.terrain_box_ground_mm(descriptor, x_mm, 0.0), 6):
                break
        else:
            continue
        ground = next(iter(around))
        model = dyn.load_model(dyn.export_mjcf(built)["xml"])
        dyn.place_terrain_course(model, course)
        data = mujoco.MjData(model)
        data.qpos[:] = built["qpos_solved"]
        data.qpos[0] += x_mm / 1000.0
        data.qpos[2] += (ground + 30.0) / 1000.0
        for _ in range(400):
            mujoco.mj_step(model, data)
        assert data.qpos[2] * 1000.0 == pytest.approx(ground + 10.0, abs=2.0), (seed, x_mm)
        grounds.append(ground)
    assert len(grounds) >= 2


def test_every_seed_is_evaluated_on_its_own_course_and_read_for_terrain(tmp_path) -> None:
    """End to end on the block: each seed's row names its held-out course,
    the terrain predicates are measured on it, and a predicate on a step
    count holds against what was crossed."""

    import dynamics_policy_fixtures as pf
    from test_dynamics_height_scan import TASK, scanned

    success = {
        "label": "", "seeds": [1001, 1002, 1003], "feet": [], "tip": None,
        "episode_seconds": None, "randomisation": None, "reset_variation": None,
        "disturbance": None, "scale": None,
        "predicates": [{"id": "stands", "metric": "falls", "max": 0.0},
                       {"id": "none_crossed", "metric": "steps_crossed", "max": 0.0},
                       {"id": "made_good", "metric": "distance_made_good_mm", "min": -50.0}],
    }
    prepared = scanned(terrain=RANDOM_COURSE, task={**TASK, "success": success})
    payload = json.dumps(prepared["bundle"], indent=2, sort_keys=True).encode("utf-8")
    prepared["task_sha256"] = hashlib.sha256(payload).hexdigest()
    made = pf.policy_container(prepared)
    # Zero weights: every action mid-range, no torque; the block stands.
    container = {"header": made["header"], "weights": [0.0] * len(made["weights"])}
    report = dyn.evaluate_success(prepared["xml"], prepared["bundle"], container,
                                  components=["block", "arm"])
    keys = []
    for row in report["seeds"]:
        course = dyn.terrain_evaluation_course(prepared["bundle"]["terrain"], row["seed"])
        assert row["detail"]["terrain"]["course"] == course["course"]
        assert row["metrics"]["falls"] == 0.0
        assert row["metrics"]["steps_crossed"] == 0.0
        assert row["pass"], row["failing"]
        keys.append(course["course"]["key"])
    assert len(set(keys)) == 3


def test_a_step_count_on_flat_ground_is_refused_where_it_is_declared() -> None:
    from test_success_spec_model import refusal, spec

    error = refusal(spec([{"id": "crosses", "metric": "steps_crossed", "min": 1.0}]))
    assert error.reason == "success_metric_needs_terrain"
    assert "terrain=" in error.correction
    # falls and distance made good need only a base.
    from test_success_spec_model import bundle

    bundle(spec([{"id": "stands", "metric": "falls", "max": 0.0},
                 {"id": "far", "metric": "distance_made_good_mm", "min": 0.0}]))
