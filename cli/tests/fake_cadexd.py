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


def inspect_reply(args: dict[str, Any], value: Any) -> dict[str, Any]:
    """An ``inspect`` response as the protocol pins it, with ``value``."""

    return {
        "ok": True,
        "scope": str(args.get("scope") or ""),
        "target": str(args.get("target") or ""),
        "path": str(args.get("path") or ""),
        "value": value,
        "page": {
            "kind": "object" if isinstance(value, dict) else "scalar",
            "offset": 0, "requested_limit": 50, "effective_limit": 50,
            "returned": len(value) if isinstance(value, (dict, list)) else 1,
            "total": len(value) if isinstance(value, (dict, list)) else 1,
            "next_offset": None,
        },
        "document": {"name": "Ephemeral", "uid": "doc", "object_count": 0},
        "surface": {
            "available": True, "domain": "project", "engine": "xscript",
            "surface_id": "xscript.project", "workbench": "PartWorkbench",
        },
        "result_json_bytes": 0,
    }


def clearance_value(
    pairs: list[dict[str, Any]] | None = None, *, revision: str = "rev-1",
    assembly: str = "asm",
) -> dict[str, Any]:
    """An ``inspect scope=clearance`` value: unavailable when no pairs."""

    return {
        "revision": revision,
        "assembly": assembly if pairs else "",
        "available": bool(pairs),
        "pose": "initial solved pose (not swept motion)",
        "pairs": list(pairs or []),
    }


def inventory_value(
    components: list[dict[str, Any]] | None = None, *, revision: str = "rev-1",
    assembly: str = "asm",
) -> dict[str, Any]:
    """An ``inspect scope=inventory`` value, rolled up the way the engine
    does it: ``catalog_counts`` by ``family/part_number`` over components
    with a catalog row, ``uncatalogued_sources`` the distinct source outputs
    of the rest. Unavailable (no assembly) when no components."""

    rows = list(components or [])
    counts: dict[str, int] = {}
    uncatalogued: set[str] = set()
    for row in rows:
        catalog = row.get("catalog")
        if isinstance(catalog, dict):
            key = f"{catalog.get('family', '')}/{catalog.get('part_number', '')}"
            counts[key] = counts.get(key, 0) + 1
        elif row.get("source_output"):
            uncatalogued.add(str(row["source_output"]))
    return {
        "revision": revision,
        "assembly": assembly if rows else "",
        "component_count": len(rows),
        "components": rows,
        "catalog_counts": dict(sorted(counts.items())),
        "uncatalogued_sources": sorted(uncatalogued),
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
        if reply is None and op == "inspect":
            # The bridge reads scope=clearance (ADR-346) and scope=inventory
            # (ADR-362) after every build; an unconfigured fake publishes no
            # assembly, so both are honestly unavailable rather than a
            # shape-check failure.
            scope = str((args or {}).get("scope") or "")
            value = inventory_value() if scope == "inventory" else clearance_value()
            reply = inspect_reply(dict(args or {}), value)
        if reply is None:
            reply = accepted_reply(op, "rev-1")
        frame = {"id": f"fake-{len(self.calls)}", **reply}
        problems = self.protocol.validate_response(op, frame)
        assert not problems, (op, problems)
        return frame

    def args_for(self, op: str) -> list[dict[str, Any]]:
        return [args for name, args in self.calls if name == op]
