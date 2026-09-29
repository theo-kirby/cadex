# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A build reply the model sees fits one tool result (ADR-435).

ot10-biped-3's agent (2026-09-28) read its fit by paging `inspect
scope=clearance` because a rebuild reply for 215 outputs came to 85,954
characters, and the harness refuses an MCP result past about 21,700
(ADR-359). Two thirds of it was the output list said twice. These tests
drive the bridge with a fake engine at that scale and hold the reply under
the budget the harness was measured to accept, with every verdict and count
intact and each cut list worst first, counted, and pointed at.
"""

from __future__ import annotations

import json
from typing import Any

from cadex_cli.bridge import (
    API_VIEW_CHAR_BUDGET, BUILD_VIEW_LIST_LIMIT, BUILD_VIEW_NAME_LIMIT, Bridge,
)

from fake_cadexd import (
    FakeCadexd, accepted_reply, clearance_value, inspect_reply, inventory_value,
)


def _biped_scale_reply() -> dict[str, Any]:
    """A rebuild reply shaped like ot10-biped-3's: 215 outputs, each twice."""

    kinds = ([("part", "solid", f"part_{i:02d}") for i in range(71)]
             + [("assembly", "component_link", f"c_part_{i:02d}") for i in range(71)]
             + [("assembly", "joint", f"j_{i:02d}") for i in range(69)]
             + [("assembly", "assembly", "assembly"),
                ("assembly", "solver_diagnostics", "diagnostics"),
                ("assembly", "mjcf", "model"), ("assembly", "task", "task")])
    reply = accepted_reply("rebuild", "rev-1", outputs=[name for _, _, name in kinds])
    reply["outputs"] = [{"domain": d, "name": n, "type": t} for d, t, n in kinds]
    reply["live_outputs"] = {
        n: {"domain": d, "label": n, "object_name": f"VibeAssembly_project_{n}",
            "output_type": t, "type_id": "Part::Feature"}
        for d, t, n in kinds
    }
    return reply


def _clearance() -> dict[str, Any]:
    """2,485 measured pairs, 30 of them failing, and 18 swept joints."""

    pairs = [{"first": f"c_part_{i % 71:02d}", "second": f"c_part_{(i * 7 + 1) % 71:02d}",
              "distance_mm": 5.0, "common_volume_mm3": 0.0} for i in range(2455)]
    # Failing rows in rising severity, so worst-first has to reorder them.
    pairs += [{"first": f"c_part_{i:02d}", "second": "c_part_70",
               "distance_mm": 0.0, "common_volume_mm3": float(i + 1)} for i in range(30)]
    joints = [{"joint": f"j_{i:02d}", "kind": "revolute", "unit": "degrees",
               "status": "complete", "range_degrees": [-40.0, 40.0], "step": 10.0,
               "sample_count": 9, "initial_degrees": 0.0, "pairs_measured": 2485,
               "pairs_moving": 900, "pairs": [
                   {"first": f"c_part_{i:02d}", "second": f"c_part_{i + 1:02d}",
                    "minimum_distance_mm": 0.0, "maximum_common_volume_mm3": float(i + 1),
                    "first_contact_degrees": -30.0}]} for i in range(18)]
    joints.append({"joint": "j_rail", "kind": "slider", "unit": "mm", "status": "incomplete",
                   "reason": "sweep_step_mm is not declared", "pairs": []})
    return clearance_value(pairs, sweep={"status": "incomplete", "step_degrees": 10.0,
                                         "step_mm": None, "joints": joints})


def _inventory() -> dict[str, Any]:
    rows = [{"component": f"c_part_{i:02d}", "source_output": f"part_{i:02d}",
             "appearance": ("shell", "mechanism", "accent")[i % 3],
             "source_facts": {"sharp_edges": {"edge_length_mm": 400.0,
                                              "sharp_convex_length_mm": float(i),
                                              "unresolved_edges": 0}}}
            for i in range(71)]
    return inventory_value(rows)


def _engine(reply: dict[str, Any]) -> FakeCadexd:
    clearance, inventory = _clearance(), _inventory()
    return FakeCadexd(replies={
        "rebuild": reply,
        "inspect": lambda args: inspect_reply(
            args, inventory if args.get("scope") == "inventory" else clearance),
    })


def test_a_215_output_rebuild_reply_fits_one_tool_result():
    reply = _biped_scale_reply()
    # The regression: the old view -- the reply minus `display`, with the
    # blocks whole -- is past the budget on the output lists alone.
    old = {k: v for k, v in reply.items() if k not in {"display", "id"}}
    assert len(json.dumps(old, indent=2, sort_keys=True)) > API_VIEW_CHAR_BUDGET

    bridge = Bridge(_engine(reply), initial_revision="rev-0")
    result = bridge.call("rebuild", {})
    text = result["content"][0]["text"]
    assert result["is_error"] is False
    assert len(text) <= API_VIEW_CHAR_BUDGET, len(text)
    view = json.loads(text)
    assert "live_outputs" not in view

    outputs = view["outputs"]
    assert outputs["count"] == 215 and "names" not in outputs
    assert outputs["by_kind"] == {
        "assembly assembly": 1, "assembly component_link": 71, "assembly joint": 69,
        "assembly mjcf": 1, "assembly solver_diagnostics": 1, "assembly task": 1,
        "part solid": 71}
    assert outputs["not_live"] == []
    assert "inspect scope=output" in outputs["note"]

    fit = view["fit"]
    assert fit["verdict"] == "fail"
    assert fit["pairs_checked"] == 2485 and fit["failing_count"] == 30
    assert len(fit["failing"]) == BUILD_VIEW_LIST_LIMIT
    assert fit["failing_omitted"] == 30 - BUILD_VIEW_LIST_LIMIT
    assert "inspect scope=clearance path=/pairs" in fit["failing_rest"]
    # Worst first: the largest common volume leads.
    assert [row["common_volume_mm3"] for row in fit["failing"][:3]] == [30.0, 29.0, 28.0]

    sweep = fit["sweep"]
    assert sweep["joints_checked"] == 19 and sweep["joints_complete"] == 18
    assert [joint["joint"] for joint in sweep["joints"]] == ["j_rail"]
    assert sweep["failing_count"] == 18 and len(sweep["failing"]) == BUILD_VIEW_LIST_LIMIT
    assert sweep["failing"][0]["joint"] == "j_17"

    inventory = view["inventory"]
    assert inventory["component_count"] == 71
    assert inventory["appearance"] == {"accent": 23, "mechanism": 24, "shell": 24}
    edges = inventory["printed_edges"]
    assert edges["measured_count"] == 71
    assert edges["sharp_convex_length_mm"] == sum(float(i) for i in range(71))
    assert [row["component"] for row in edges["sharpest"][:2]] == ["c_part_70", "c_part_69"]

    # The parent keeps every row: the turn report is not the model's view.
    assert len(bridge.state.last_fit["failing"]) == 30
    assert len(bridge.state.last_fit["sweep"]["joints"]) == 19
    assert len(bridge.state.last_inventory["appearance"]) == 71


def test_a_small_build_still_names_its_outputs_and_keeps_their_facts():
    bridge = Bridge(FakeCadexd(), initial_revision="rev-0")
    view = json.loads(bridge.call("write_script", {"source": "x"})["content"][0]["text"])
    outputs = view["outputs"]
    assert outputs["count"] == 1 and outputs["names"] == ["widget"]
    assert outputs["detail"] == [{"name": "widget", "facts": {"volume": 1000.0}}]
    assert BUILD_VIEW_NAME_LIMIT >= 1


def test_an_output_with_no_live_object_is_named():
    reply = accepted_reply("rebuild", "rev-1", outputs=["a", "b"])
    del reply["live_outputs"]["b"]
    bridge = Bridge(FakeCadexd(replies={"rebuild": reply}), initial_revision="rev-0")
    view = json.loads(bridge.call("rebuild", {})["content"][0]["text"])
    assert view["outputs"]["not_live"] == ["b"]
