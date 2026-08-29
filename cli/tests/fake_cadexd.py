# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A cadexd that answers from a table instead of from OCCT.

The MCP shim, the bridge and the revision injection are all pure protocol
plumbing; running a real engine to test them would make a fast suite slow
and a deterministic one weather-dependent. So the tests that are *about the
plumbing* drive this, and the tests that are about geometry drive the real
thing (``test_client.py``, ``test_export.py``).

It is not a loose mock. It loads the real ``CadexdProtocol`` and its replies
are shape-checked against ``OP_RESPONSE_SPECS`` by the same
:meth:`CadexdClient.request` path production uses, so a fixture that drifts
from the contract fails here rather than passing here and failing live.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cadex_cli.engine import Engine
from cadex_cli.protocol import load_protocol

from conftest import SOURCE_MODULE_DIR


def fake_engine(module_dir: Path | None = None) -> Engine:
    """An :class:`Engine` with a real protocol and a binary nobody runs."""

    return Engine(
        freecadcmd=Path("/nonexistent/FreeCADCmd"),
        module_dir=module_dir or SOURCE_MODULE_DIR,
        source="fake",
    )


def _model_state(revision: str) -> dict[str, Any]:
    return {
        "status": "accepted",
        "accepted_is_current": True,
        "next_write_expected_revision": revision,
        "verification_goal": "",
    }


def accepted_reply(
    tool: str, revision: str, *, digest: str = "d" * 64, outputs: list[str] | None = None
) -> dict[str, Any]:
    """A successful modelling response, shaped as the protocol pins it."""

    names = outputs or ["widget"]
    return {
        "ok": True,
        "tool": tool,
        "revision": revision,
        "accepted_revision": revision,
        "digest": digest,
        "model_state": _model_state(revision),
        "outputs": [{"name": name, "type": "solid", "domain": "part"} for name in names],
        "live_outputs": {
            name: {
                "object_name": f"Obj_{name}",
                "label": name,
                "type_id": "Part::Feature",
                "output_type": "solid",
                "facts": {"volume": 1000.0},
            }
            for name in names
        },
        "removed": [],
        "stdout": "",
        "display": {
            name: {
                "artifact_kind": "brep",
                "artifact_path": f"/staging/{name}.brep",
                "placement": None,
                "tessellation": None,
            }
            for name in names
        },
    }


def rejected_reply(revision: str, *, error: str = "no") -> dict[str, Any]:
    """A tool-level refusal — which still moves the working revision."""

    return {
        "ok": False,
        "tool": "xscript.project.write_script",
        "error": error,
        "failure_code": "SCRIPT_REJECTED",
        "failure_stage": "execute",
        "observed": {},
        "normalized": {},
        "requested": {},
        "retry": False,
        "candidates": [],
        "allowed_values": [],
        "native_diagnostics": [],
        "state_change": "none",
        "model_state": _model_state(revision),
    }


@dataclass
class FakeCadexd:
    """A :class:`~cadex_cli.client.CadexdClient` stand-in for the bridge.

    Records every ``(op, args)`` it was asked for, which is how a test
    asserts what the bridge sent rather than only what it returned.
    """

    engine: Engine = field(default_factory=fake_engine)
    #: op → reply, or op → callable(args) → reply.
    replies: dict[str, Any] = field(default_factory=dict)
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.protocol = load_protocol(self.engine.module_dir)

    def request(
        self, op: str, args: dict[str, Any] | None = None, **_kwargs: Any
    ) -> dict[str, Any]:
        self.calls.append((op, dict(args or {})))
        reply = self.replies.get(op)
        if callable(reply):
            reply = reply(dict(args or {}))
        if reply is None:
            reply = accepted_reply(op, "rev-1")
        frame = {"id": f"fake-{len(self.calls)}", **reply}
        problems = self.protocol.validate_response(op, frame)
        assert not problems, (op, problems)
        return frame

    def args_for(self, op: str) -> list[dict[str, Any]]:
        return [args for name, args in self.calls if name == op]
