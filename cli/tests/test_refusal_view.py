# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""What the model reads of a refusal, and the lib-part page (ADR-618, ADR-619).

On cbase-deinonychus-a a ``solver_error`` refusal was 293,000 characters:
125 components' placement matrices, then a stderr made of OCCT's progress
meter. The agent harness kept the first and last 5,000, and the solver's
message and the joints it blamed were in the cut middle.
"""

from __future__ import annotations

import io
import json
from typing import Any

from cadex_cli import mcp
from cadex_cli.bridge import (
    API_VIEW_CHAR_BUDGET,
    Bridge,
    REFUSAL_STDERR_CHARS,
    api_index,
    api_section,
    api_sections,
    refusal_view,
)

from fake_cadexd import FakeCadexd


class _Host:
    def __init__(self, bridge: Bridge) -> None:
        self.bridge = bridge

    def instructions(self) -> str:
        return ""

    def tools(self) -> list[dict[str, Any]]:
        return self.bridge.tools()

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.bridge.call(tool, arguments)

    def idle(self) -> None:
        pass


def _solver_refusal(components: int = 125) -> dict[str, Any]:
    placement = {"matrix": [1.0, 0.0, 0.0, 0.0] * 4, "position_mm": [0.0, 0.0, 0.0]}
    satisfied = [{"joint": f"j{i}", "status": "satisfied", "constraints": [{}] * 6}
                 for i in range(60)]
    return {
        "ok": False,
        "tool": "xscript.project.write_script",
        "error": "The isolated native Assembly solver rejected the graph with "
                 "solver_error (code -1). The solver said: 'Singular Jacobian'.",
        "failure_code": "DOMAIN_CANDIDATE_FAILED",
        "failure_stage": "external_process",
        "domain_failure_stage": "native_solver",
        "observed": {
            "details": {
                "stage": "native_solver",
                "solver_message": "Singular Jacobian",
                "implicated_joints": [{"joint": "knee_l", "status": "conflicting"}],
                "component_placements": {f"c{i}": placement for i in range(components)},
                "native": {"available": True, "joints": satisfied + [
                    {"joint": "knee_l", "status": "conflicting", "constraints": [{}]}]},
                "joint_outputs": [f"j{i}" for i in range(61)],
            },
            "stderr": "\r\t\t\t\t\t\t(1 %)\t" * 40_000 + "Solve failed: Singular Jacobian\n",
            "stdout": "leg length 120\n",
            "traceback": "Traceback (most recent call last):\n" + "  frame\n" * 2000,
        },
        "normalized": {}, "requested": {}, "candidates": [], "allowed_values": [],
        "native_diagnostics": [],
        "retry": {"same_call": False, "required_changes": []},
        "state_change": {},
    }


def test_a_solver_refusal_keeps_its_diagnosis_and_drops_the_bulk() -> None:
    raw = _solver_refusal()
    assert len(json.dumps(raw, indent=2)) > 250_000
    view = refusal_view(raw)
    text = json.dumps(view, indent=2, sort_keys=True)
    assert len(text) < 15_000, len(text)

    details = view["observed"]["details"]
    assert details["solver_message"] == "Singular Jacobian"
    assert details["implicated_joints"] == [{"joint": "knee_l", "status": "conflicting"}]
    assert details["component_placements"]["count"] == 125
    assert details["native"]["joints"] == [
        {"joint": "knee_l", "status": "conflicting", "constraints": [{}]}
    ]
    assert details["native"]["satisfied_joint_count"] == 60
    assert details["joint_outputs_omitted"] > 0
    # The progress meter is gone; the line the solver printed is not.
    assert view["observed"]["stderr"] == "Solve failed: Singular Jacobian"
    assert view["observed"]["stdout"] == "leg length 120\n"
    assert view["observed"]["traceback"].startswith("[")
    assert len(view["observed"]["traceback"]) <= REFUSAL_STDERR_CHARS + 60
    # Every envelope key survives, and the engine's reply is untouched.
    assert set(view) == set(raw)
    assert len(raw["observed"]["details"]["component_placements"]) == 125


def test_the_bridge_hands_the_model_the_bounded_refusal() -> None:
    client = FakeCadexd(replies={"write_script": _solver_refusal()})
    with Bridge(client, initial_revision="rev-1") as bridge:
        stream = io.StringIO()
        mcp.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
             "params": {"name": "write_script", "arguments": {"source": "result = {}"}}},
            _Host(bridge), stream,
        )
    result = json.loads(stream.getvalue())["result"]
    assert result["isError"] is True
    text = result["content"][0]["text"]
    assert len(text) < 15_000
    view = json.loads(text)
    assert view["failure_code"] == "DOMAIN_CANDIDATE_FAILED"
    assert view["observed"]["details"]["solver_message"] == "Singular Jacobian"


def test_a_successful_reply_is_not_a_refusal() -> None:
    reply = {"ok": True, "observed": {"stderr": "\r\t(5 %)\t"}}
    assert refusal_view({**reply, "ok": False})["observed"]["stderr"] == ""
    assert refusal_view({"ok": False, "error": "x"}) == {"ok": False, "error": "x"}


def _contract() -> dict[str, Any]:
    method = {"name": "actuator", "signature": "(joint, *, control_nmm='0')",
              "description": "A torque motor on joint.\n\nMore text " + "x" * 3000}
    return {
        "ok": True,
        "domains": {"part": {"exports": [{"name": "box"}]}},
        "library": {
            "exports": [{"name": "qdd"}],
            "catalog": {"qdd": {}},
            "notes": "n",
            "part_classes": [
                {"name": "QddPart", "description": "A placed QDD.",
                 "returned_by": ["lib.qdd"], "attributes": ["body", "spec"],
                 "methods": [method, {"name": "bay", "signature": "()", "description": "b"}]},
            ],
        },
    }


def test_library_parts_is_a_section_of_its_own() -> None:
    reply = _contract()
    assert api_sections(reply) == ["part", "library", "library_parts"]

    index = api_index(reply)
    assert index["library"]["part_classes"] == {"QddPart": ["actuator", "bay"]}
    assert "library_parts" in index["sections"]

    library = api_section(reply, "library")
    assert "part_classes" not in library

    page = api_section(reply, "library_parts")
    assert page["section"] == "library_parts"
    qdd = page["part_classes"][0]
    assert qdd["returned_by"] == ["lib.qdd"]
    assert qdd["methods"][0] == {"name": "actuator", "signature": "(joint, *, control_nmm='0')",
                                 "description": "A torque motor on joint."}
    assert "path=/library/part_classes/C/methods/M/description" in page["descriptions"]
    assert len(json.dumps(page, indent=2)) < API_VIEW_CHAR_BUDGET


def test_an_engine_without_part_classes_has_no_such_section() -> None:
    reply = _contract()
    del reply["library"]["part_classes"]
    assert api_sections(reply) == ["part", "library"]
