# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""A turn says what it cost, and says so when the model only pretended to
call a tool (ADR-523, the shell parity ledger's ``agent.py`` row).

Both are read off the frames Claude Code already streams: its ``result``
frame's ``total_cost_usd``, ``duration_ms`` and ``usage``, and any tool-call
markup in the model's prose. The browser half — the cost on the turn's
status line — is in ``test_dashboard_writes.py``.
"""

from __future__ import annotations

import json

import pytest

from cadex_cli.__main__ import IMITATED_WARNING, command_prompt, describe_usage
from cadex_cli.agent import imitated_tool_call, turn_usage
from cadex_cli.report import EXIT_OK, EXIT_REJECTED, RunReport

from mock_backend import turn_factory
from test_turn_loop import BRACKET, _args

PRICED = {"total_cost_usd": 0.4213, "duration_ms": 12500,
          "usage": {"input_tokens": 120, "cache_creation_input_tokens": 3000,
                    "cache_read_input_tokens": 45000, "output_tokens": 800}}


def _text(text: str) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def test_usage_is_summed_over_every_result_frame() -> None:
    nudged = {"type": "result", "total_cost_usd": 0.1, "duration_ms": 500,
              "usage": {"input_tokens": 10, "output_tokens": 5}}
    usage = turn_usage([_text("hi"), {"type": "result", **PRICED}, nudged])
    assert usage == {"input_tokens": 3130, "cached_tokens": 45000, "output_tokens": 805,
                     "cost_usd": 0.5213, "duration_ms": 13000, "results": 2}
    assert describe_usage(usage) == "3,130 in, 45,000 cached, 805 out tokens, $0.52, 13.0 s"


def test_an_unpriced_turn_is_not_a_free_one() -> None:
    usage = turn_usage([{"type": "result", "usage": {"input_tokens": 7, "output_tokens": 3}}])
    assert usage["cost_usd"] is None and usage["output_tokens"] == 3
    assert "$" not in describe_usage(usage)
    # No frame reported anything: no usage at all, not a row of zeros.
    assert turn_usage([{"type": "result", "result": "done"}, _text("x")]) == {}
    assert turn_usage([{"type": "result", "total_cost_usd": True, "usage": "lots"}]) == {}


def test_tool_call_markup_in_prose_is_named() -> None:
    assert imitated_tool_call([_text('I will look: <invoke name="mcp__cadex__look">')])
    assert imitated_tool_call([_text("<function_calls>\n<invoke>")])
    assert not imitated_tool_call([_text("I called look and the bracket is fine.")])
    # A real call is a tool_use block, never text; and a result frame is not prose.
    assert not imitated_tool_call([
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "look", "input": {}}]}},
        {"type": "result", "result": '<invoke name="look">'}])


@pytest.mark.usefixtures("engine")
def test_the_envelope_carries_the_turns_cost(tmp_path, capsys) -> None:
    script = [[("tool", "write_script", {"source": BRACKET}), ("done", "Built it.", PRICED)]]
    report = RunReport()
    assert command_prompt(_args(tmp_path), report, turn_factory=turn_factory(script)) == EXIT_OK
    assert report.usage == {"input_tokens": 3120, "cached_tokens": 45000, "output_tokens": 800,
                            "cost_usd": 0.4213, "duration_ms": 12500, "results": 1}
    assert report.to_json()["usage"] == report.usage
    assert " · turn: 3,120 in, 45,000 cached, 800 out tokens, $0.42, 12.5 s" in capsys.readouterr().err
    assert IMITATED_WARNING not in report.notes


@pytest.mark.usefixtures("engine")
def test_a_turn_that_wrote_its_tool_call_as_text_says_so(tmp_path, capsys) -> None:
    script = [[("text", 'Building it. <invoke name="mcp__cadex__write_script">\n'),
               ("done", "Built the bracket.")]]
    report = RunReport()
    assert command_prompt(_args(tmp_path), report, turn_factory=turn_factory(script)) == EXIT_REJECTED
    assert report.notes[-1] == IMITATED_WARNING
    assert " ✗ " + IMITATED_WARNING in capsys.readouterr().err
    # No result frame priced it, so the envelope carries no usage.
    assert "usage" not in report.to_json()
    json.dumps(report.to_json())
