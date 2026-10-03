# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A ``claude`` executable that replays a scripted turn, for a *child* ``cadex -p``.

:mod:`mock_backend` replaces the turn inside the test's own process; a
turn the dashboard starts runs in a child ``cadex`` it cannot reach, so
this stands where the ``claude`` binary stands instead — found on
``PATH``, given the same argv :class:`cadex_cli.agent.ClaudeTurn` gives
the real one, and answering in the same ``stream-json`` frames. Its tool
calls go down the real bridge socket named in the ``--mcp-config`` it was
handed, as :mod:`mock_backend`'s do; only the model is faked.

``CADEX_FAKE_CLAUDE_SCRIPT`` names a JSON list of steps::

    ["text", "chunk"]                 streamed assistant text
    ["tool", "write_script", {...}]   a real bridge round trip
    ["wait", "/path/to/gate"]         block until that file exists (120 s)
    ["done", "final words"]           the turn's result

and ``CADEX_FAKE_CLAUDE_SEEN``, when set, receives the prompt it was given.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

from cadex_cli.mcp import bridge_request

SESSION_ID = "fake-claude-session-0001"


def _emit(frame: dict) -> None:
    sys.stdout.write(json.dumps({"session_id": SESSION_ID, **frame}) + "\n")
    sys.stdout.flush()


def main(argv: list[str]) -> int:
    config = json.loads(Path(argv[argv.index("--mcp-config") + 1]).read_text(encoding="utf-8"))
    shim = next(iter(config["mcpServers"].values()))["args"]
    socket_path, token = shim[shim.index("--socket") + 1], shim[shim.index("--token") + 1]
    seen = os.environ.get("CADEX_FAKE_CLAUDE_SEEN")
    if seen:
        Path(seen).write_text(argv[argv.index("-p") + 1], encoding="utf-8")
    steps = json.loads(Path(os.environ["CADEX_FAKE_CLAUDE_SCRIPT"]).read_text(encoding="utf-8"))
    for step in steps:
        kind = step[0]
        if kind == "text":
            _emit({"type": "assistant", "message": {"content": [{"type": "text", "text": step[1]}]}})
        elif kind == "tool":
            bridge_request(socket_path, token, {"op": "call", "tool": step[1], "input": step[2]})
            _emit({"type": "assistant", "message": {"content": []}})
        elif kind == "wait":
            deadline = time.monotonic() + 120.0
            while not Path(step[1]).exists():
                if time.monotonic() > deadline:
                    return 3
                time.sleep(0.05)
        elif kind == "done":
            _emit({"type": "result", "is_error": False, "result": step[1]})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
