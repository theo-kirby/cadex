# SPDX-License-Identifier: LGPL-2.1-or-later

"""A ``claude -p`` stand-in that replays a scripted turn.

Same idea as the shell's own mock backend, and for the same reason: the turn
loop is worth testing and tokens are not free. What is copied is only the
idea — the tool calls go through the **real bridge socket**, connecting
exactly the way :mod:`cadex_cli.mcp` does, so a test exercises the whole
socket → engine → MCP-content round trip and only the model is faked.

A scripted turn is a list of steps::

    ("text", "chunk")            -> streamed assistant text
    ("tool", "write_script", {}) -> a real bridge round trip
    ("done", "final summary")    -> the turn's result
"""

from __future__ import annotations

import json
from typing import Any

from cadex_cli.agent import TurnResult
from cadex_cli.mcp import bridge_request

SESSION_ID = "mock-session-0001"


class MockTurn:
    """Drop-in for :class:`cadex_cli.agent.ClaudeTurn` in the CLI's own seam."""

    #: Class attribute so a test can script a run without a factory closure.
    script: list[list[tuple]] = []

    def __init__(
        self,
        *,
        claude_path: str = "",
        model: str = "mock",
        system_prompt_text: str = "",
        socket_path: str = "",
        token: str = "",
        session_id: str = "",
        on_text: Any = None,
        cwd: Any = None,
        script: list[list[tuple]] | None = None,
    ) -> None:
        self.model = model
        self.system_prompt_text = system_prompt_text
        self.socket_path = socket_path
        self.token = token
        self.session_id = session_id or SESSION_ID
        self.on_text = on_text
        self.cwd = cwd
        self.script = list(script if script is not None else type(self).script)
        self.turns = 0
        #: Every ``(tool, reply)`` the "model" saw, for assertions.
        self.tool_results: list[tuple[str, dict[str, Any]]] = []
        self.prompts: list[str] = []

    def run(self, prompt: str) -> TurnResult:
        self.prompts.append(prompt)
        steps = self.script[self.turns] if self.turns < len(self.script) else []
        self.turns += 1
        result = TurnResult(ok=True, session_id=self.session_id)

        for step in steps:
            kind = step[0]
            if kind == "text":
                result.text += step[1]
                if self.on_text is not None:
                    self.on_text(step[1])
            elif kind == "tool":
                _, name, arguments = step
                reply = bridge_request(
                    self.socket_path,
                    self.token,
                    {"op": "call", "tool": name, "input": dict(arguments)},
                )
                self.tool_results.append((name, reply))
                result.frames.append(
                    {"type": "assistant", "session_id": self.session_id}
                )
            elif kind == "done":
                result.text = step[1]
                result.frames.append(
                    {
                        "type": "result",
                        "session_id": self.session_id,
                        "is_error": False,
                        "result": step[1],
                    }
                )
            elif kind == "fail":
                result.ok = False
                result.error = step[1]
        return result

    def last_payload(self, tool: str) -> dict[str, Any]:
        """The JSON the "model" was handed back for ``tool``."""

        for name, reply in reversed(self.tool_results):
            if name == tool:
                return json.loads(reply["content"][0]["text"])
        raise KeyError(tool)

    def cleanup(self) -> None:
        pass


def turn_factory(script: list[list[tuple]]) -> Any:
    """A factory the CLI can call, holding onto the instance it built."""

    made: list[MockTurn] = []

    def build(**kwargs: Any) -> MockTurn:
        turn = MockTurn(script=script, **kwargs)
        made.append(turn)
        return turn

    build.made = made  # type: ignore[attr-defined]
    return build
