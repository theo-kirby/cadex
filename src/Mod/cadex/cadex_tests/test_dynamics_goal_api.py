# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""``assembly.goal`` on the script surface (ADR-462).

A goal is what an episode asks the policy to do: one more intermediate on
``api.task``, and on ``api.success`` when an evaluation draws it
differently. It is split the way ``api.disturbance`` is.

**The API refuses what a reader of the script could see**: a name a reward
could not write, a kind that is not one, a range out of order, a point with
no tip, a tip that is not in the assembly. **The engine refuses what needs
the model or the rounded schedule**: a name an observation already has, a
period that falls between control steps, a point nothing can reach. That
half is ``test_dynamics_goal_model``.

None of this touches ``CadexdProtocol.OP_ARG_SPECS``: ``assembly.*`` is the
xscript authoring surface, not the cadexd op table.
"""

from __future__ import annotations

import pytest

import CadexDynamics as dyn
import cadex_assembly_api
from cadex_domain_api import _DOMAIN_OPERATION_OUTPUT_TYPES
from CadexScriptedDomains import XSCRIPT_WORKBENCH_PACKS
from CadexScriptedRuntime import describe_project_api
from test_success_spec_api import BALANCE, SEEDS, _api, _scene, _source, _task


# -- registration -----------------------------------------------------------

def test_goal_is_an_intermediate_and_never_an_output() -> None:
    """An argument to a task, on the terms a disturbance is one."""

    pack = XSCRIPT_WORKBENCH_PACKS["AssemblyWorkbench"]
    assert "goal" in pack.api_exports
    assert "goal" not in pack.output_types
    assert _DOMAIN_OPERATION_OUTPUT_TYPES["assembly"]["goal"] == "goal"
    assert "goal" in _api().exported_names


def test_the_api_and_the_engine_name_the_same_kinds() -> None:
    assert cadex_assembly_api._GOAL_KINDS == dyn.GOAL_KINDS


def test_the_agent_is_told_the_surface_exists() -> None:
    """``describe_api`` is how the product agent learns a function, so a
    surface it does not list is one the agent cannot author with."""

    api = describe_project_api()
    assembly = api["domains"]["assembly"]
    (listed,) = [entry for entry in assembly["exports"] if entry["name"] == "goal"]
    for parameter in ("kind", "between", "tip", "min_separation_mm", "resample_seconds"):
        assert parameter in listed["signature"], parameter
    assert listed["description"].startswith("Tell the policy where to go")
    (task,) = [entry for entry in assembly["exports"] if entry["name"] == "task"]
    assert "goals" in task["signature"]
    # ...and the notes, which are the page the agent is shown whole, say
    # what it is for in a sentence. The page has a size budget (ADR-360)
    # that ``cli/tests/test_client.py`` holds against a live engine.
    assert "assembly.goal(name, kind='value'|'speed'|'point'|'phase', ...)" in assembly["notes"]
    assert "api.task(goals=[...])" in assembly["notes"]


# -- what a goal carries ----------------------------------------------------

def test_a_value_and_a_speed_carry_a_name_and_a_range() -> None:
    api = _api()
    pace = api.goal("pace", between=[0.5, 2])
    assert pace.output_type == "goal"
    assert dict(pace.properties) == {
        "name": "pace", "kind": "value", "low": 0.5, "high": 2.0,
    }
    command = api.goal("command", kind="speed", between=[60, 96],
                       resample_seconds=2.5, label="walk speed")
    assert command.properties["kind"] == "speed"
    assert (command.properties["low"], command.properties["high"]) == (60.0, 96.0)
    assert command.properties["resample_seconds"] == 2.5
    assert command.properties["label"] == "walk speed"
    # A point draw that is held is a range with one number in it.
    assert api.goal("fixed", between=[3, 3]).properties["low"] == 3.0


def test_a_point_carries_its_tip_and_how_it_is_drawn() -> None:
    api = _api()
    scene = _scene(api)
    hand = scene["components"][1]
    target = api.goal("target", kind="point", tip=hand, tip_offset_mm=[0, 0, 40],
                      joint_fraction=0.6, min_z_mm=25, min_separation_mm=80,
                      resample_seconds=4)
    assert target.properties["tip"] is hand
    assert list(target.properties["tip_offset_mm"]) == [0.0, 0.0, 40.0]
    assert target.properties["joint_fraction"] == 0.6
    assert target.properties["min_z_mm"] == 25.0
    assert target.properties["min_separation_mm"] == 80.0
    assert target.properties["resample_seconds"] == 4.0

    plain = api.goal("target", kind="point", tip=hand)
    assert list(plain.properties["tip_offset_mm"]) == [0.0, 0.0, 0.0]
    assert plain.properties["joint_fraction"] == 0.8
    assert plain.properties["min_separation_mm"] == 0.0
    # No floor unless one is stated, and no period unless one is asked for.
    assert "min_z_mm" not in plain.properties
    assert "resample_seconds" not in plain.properties


def test_a_phase_carries_its_period_and_nothing_else() -> None:
    """A clock (ADR-598): its period is all it declares. A range, a tip or
    a missing period is refused, and no other kind takes a period."""

    api = _api()
    lead = api.goal("lead", kind="phase", period_seconds=4, resample_seconds=8)
    assert dict(lead.properties) == {
        "name": "lead", "kind": "phase", "period_seconds": 4.0,
        "resample_seconds": 8.0,
    }
    hand = _scene(api)["components"][1]
    with pytest.raises(ValueError, match="invalid period_seconds"):
        api.goal("lead", kind="phase")
    for wrong in (0, -2, float("inf"), "soon"):
        with pytest.raises(ValueError, match="invalid period_seconds"):
            api.goal("lead", kind="phase", period_seconds=wrong)
    with pytest.raises(ValueError, match="invalid between"):
        api.goal("lead", kind="phase", period_seconds=4, between=[0, 1])
    with pytest.raises(ValueError, match="describes how a point goal is drawn"):
        api.goal("lead", kind="phase", period_seconds=4, tip=hand)
    with pytest.raises(ValueError, match="invalid period_seconds"):
        api.goal("pace", between=[0, 1], period_seconds=4)


def test_a_task_takes_its_goals_and_a_task_without_any_is_the_value_it_was() -> None:
    api = _api()
    scene = _scene(api)
    hand = scene["components"][1]
    target = api.goal("target", kind="point", tip=hand)
    pace = api.goal("pace", between=[1, 2])
    task = _task(api, scene, goals=[target, pace],
                 reward=[api.reward("angle - pace", label="paced")])
    assert list(task.properties["goals"]) == [target, pace]

    bare = _task(api, scene)
    assert "goals" not in bare.properties
    assert "goals" not in bare.to_payload()["properties"]
    assert "goals" not in _task(api, scene, goals=[]).properties


def test_a_spec_may_restate_the_goals_it_is_judged_on() -> None:
    """Absent is "the task's own"; a list is what the evaluation draws."""

    api = _api()
    scene = _scene(api)
    command = api.goal("command", kind="speed", between=[40, 80])
    faster = api.goal("command", kind="speed", between=[100, 120])
    assert "goals" not in api.success(BALANCE, seeds=SEEDS).properties
    spec = api.success(BALANCE, seeds=SEEDS, goals=[faster])
    assert list(spec.properties["goals"]) == [faster]
    task = _task(api, scene, goals=[command], success=spec)
    assert task.properties["success"] is spec


# -- refusals a reader could see --------------------------------------------

@pytest.mark.parametrize("name", ["", "2fast", "has space", "x" * 49, "a-b", None])
def test_a_name_a_reward_could_not_write_is_refused(name) -> None:
    with pytest.raises(ValueError, match="invalid name"):
        _api().goal(name, between=[0, 1])


def test_a_kind_that_is_not_one_is_refused_with_the_kinds() -> None:
    with pytest.raises(ValueError) as refusal:
        _api().goal("target", kind="pose", between=[0, 1])
    assert "['value', 'speed', 'point', 'phase']" in str(refusal.value)


def test_a_range_is_two_numbers_in_order() -> None:
    api = _api()
    for wrong in (None, [1], [2, 1], [0, float("inf")], "0..1", [0, 1, 2]):
        with pytest.raises(ValueError, match="invalid between"):
            api.goal("pace", between=wrong)
        with pytest.raises(ValueError, match="invalid between"):
            api.goal("command", kind="speed", between=wrong)


def test_each_kind_refuses_the_other_kinds_arguments() -> None:
    """A parameter that means nothing for a kind is refused, not ignored."""

    api = _api()
    hand = _scene(api)["components"][1]
    with pytest.raises(ValueError, match="invalid between"):
        api.goal("target", kind="point", tip=hand, between=[0, 1])
    with pytest.raises(ValueError, match="invalid tip"):
        api.goal("target", kind="point")
    for arguments in ({"tip": hand}, {"tip_offset_mm": [0, 0, 1]}, {"min_z_mm": 5},
                      {"joint_fraction": 0.5}, {"min_separation_mm": 10}):
        with pytest.raises(ValueError, match="describes how a point goal is drawn"):
            api.goal("pace", between=[0, 1], **arguments)


def test_a_points_draw_is_checked_where_it_is_written() -> None:
    api = _api()
    scene = _scene(api)
    hand = scene["components"][1]
    for arguments in (
        {"tip": "c_hand"},
        {"tip": scene["motor"]},
        {"tip": hand, "tip_offset_mm": [0, 0]},
        {"tip": hand, "joint_fraction": 0.0},
        {"tip": hand, "joint_fraction": 1.5},
        {"tip": hand, "min_separation_mm": -1},
        {"tip": hand, "min_z_mm": "low"},
        {"tip": hand, "resample_seconds": 0},
    ):
        with pytest.raises(ValueError):
            api.goal("target", kind="point", **arguments)


def test_a_task_refuses_a_goal_whose_tip_is_in_another_assembly() -> None:
    api = _api()
    scene = _scene(api)
    stranger = api.goal("target", kind="point", tip=api.component(_source("solid9")))
    with pytest.raises(ValueError) as refusal:
        _task(api, scene, goals=[stranger])
    assert "goals[0]" in str(refusal.value)
    assert "not listed in this assembly" in str(refusal.value)

    with pytest.raises(ValueError) as refusal:
        _task(api, scene, success=api.success(BALANCE, seeds=SEEDS, goals=[stranger]))
    assert "success.goals[0]" in str(refusal.value)


def test_goals_are_goal_values_and_each_is_given_once() -> None:
    api = _api()
    scene = _scene(api)
    pace = api.goal("pace", between=[1, 2])
    for wrong in ("pace", [api.reward("angle")], [scene["components"][0]], [pace, pace]):
        with pytest.raises(ValueError, match="invalid goals"):
            _task(api, scene, goals=wrong)
        with pytest.raises(ValueError, match="invalid goals"):
            api.success(BALANCE, seeds=SEEDS, goals=wrong)
