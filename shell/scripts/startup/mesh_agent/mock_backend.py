# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Mock backend replaying scripted turns without spawning `claude` or touching the
network. Tool-call steps go through the *real* TCP bridge — connecting exactly
like the MCP shim does — so tests exercise the full socket → main-thread → reply
round trip. Enabled by MESH_AGENT_MOCK=1 or by injecting via Agent.backend_factory.
"""

import threading

from .mcp_shim import bridge_request

# A scripted turn is a list of steps:
#   ("text", "chunk")            -> streamed text delta
#   ("tool", name, {input})      -> real bridge round trip; result recorded
#   ("result", is_error, "text") -> final result event


def default_script():
    """Canned demo: write a parametric cube model script. Used when
    MESH_AGENT_MOCK=1.

    A real xscript project script, because the engine is what runs it: the
    bpy version this replaced was a script the engine would refuse (ADR-123).
    """
    return [[
        ("text", "Building a demo cube.\n"),
        ("tool", "write_script",
         {"content": "p = params(size=num(20.0, unit='mm', min=5.0,\n"
                     "                    max=80.0, label='Size'))\n"
                     "cube = part.box(p.size, p.size, p.size)\n"
                     "result = {'cube': cube}\n"}),
        ("tool", "scene_summary", {}),
        ("text", "Done - added MeshAgentCube with a Size slider."),
        ("result", False, "Done - added MeshAgentCube with a Size slider."),
    ]]


class MockBackend:
    is_mock = True

    def __init__(self, script=None, bridge_port=None, bridge_token=None):
        self.script = script if script is not None else default_script()
        self.bridge_port = bridge_port
        self.bridge_token = bridge_token
        self.session_id = "mock-session"
        self.tool_results = []  # (tool_name, reply_dict) seen by the "model"
        self.prompts = []  # prompts as the "model" would receive them
        self._turn_index = 0
        self._cancelled = False

    def start_turn(self, prompt, events):
        self.prompts.append(prompt)
        if self._turn_index >= len(self.script):
            steps = [("result", True, "Mock script exhausted")]
        else:
            steps = self.script[self._turn_index]
        self._turn_index += 1
        thread = threading.Thread(target=self._run, args=(steps, events),
                                  daemon=True, name="mesh-agent-mock")
        thread.start()

    def _run(self, steps, events):
        tool_id = 0
        for step in steps:
            if self._cancelled:
                break
            kind = step[0]
            if kind == "text":
                events.put(("stream", {
                    "type": "stream_event",
                    "session_id": self.session_id,
                    "event": {
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": step[1]},
                    },
                }))
            elif kind == "tool":
                _, name, tool_input = step
                tool_id += 1
                events.put(("stream", {
                    "type": "assistant",
                    "session_id": self.session_id,
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "tool_use",
                                     "id": "mock_tool_{:d}".format(tool_id),
                                     "name": "mcp__mesh__" + name,
                                     "input": tool_input}],
                    },
                }))
                # Real bridge round trip, same as the MCP shim.
                reply = bridge_request(self.bridge_port, self.bridge_token,
                                       {"op": "call", "tool": name,
                                        "input": tool_input})
                self.tool_results.append((name, reply))
            elif kind == "result":
                _, is_error, text = step
                events.put(("stream", {
                    "type": "result",
                    "subtype": "success" if not is_error else "error",
                    "is_error": is_error,
                    "result": text,
                    "session_id": self.session_id,
                }))
        events.put(("exit", 0, ""))

    def cancel(self):
        self._cancelled = True
