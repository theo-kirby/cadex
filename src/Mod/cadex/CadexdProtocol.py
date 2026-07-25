# SPDX-License-Identifier: LGPL-2.1-or-later

"""cadexd wire protocol: NDJSON codec, op registry, failure codes (ADR-017).

Pure Python with zero FreeCAD imports so every contract here is testable
under the stubbed pytest suite. Schema ``cadex-cadexd-v1``:

- Request  ``{"schema": ..., "id": ..., "op": ..., "args": {...}}``
- Response ``{"id": ..., "ok": ..., ...payload}`` where the payload of a
  lifecycle op is exactly the accept payload / ``tool_failure`` envelope the
  in-process session tool produced (plus the per-output ``display`` block).
- Event    ``{"id": ..., "event": {...}}`` — the pipeline's progress events.

One frame per line; frames above :data:`MAX_FRAME_BYTES` are protocol
errors. Binary artifacts are referenced by filesystem path, never inlined.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

PROTOCOL_SCHEMA = "cadex-cadexd-v1"
MAX_FRAME_BYTES = 8 * 1024 * 1024
MAX_REQUEST_ID_CHARS = 128

# Server-level failure codes (tool-level codes flow through unchanged).
CADEXD_PROTOCOL_ERROR = "CADEXD_PROTOCOL_ERROR"
CADEXD_BUSY = "CADEXD_BUSY"
CADEXD_NOT_OPEN = "CADEXD_NOT_OPEN"
CADEXD_CRASHED = "CADEXD_CRASHED"
CADEXD_RESTORE_FAILED = "CADEXD_RESTORE_FAILED"

#: Ops that mutate engine state; at most one may be in flight.
MODELING_OPS = frozenset(
    {"open_project", "write_script", "edit_script", "set_params", "rebuild"}
)
#: Read-only ops; these queue behind an in-flight modeling op.
READ_OPS = frozenset({"describe_api", "resolve_pin", "inspect"})
#: Control ops; handled out of band by the reader.
CONTROL_OPS = frozenset({"cancel", "shutdown"})

#: op → (required {name: type}, optional {name: type}). Deep validation
#: stays in the pipeline; this rejects only structurally wrong requests.
OP_ARG_SPECS: dict[str, tuple[dict[str, type], dict[str, type]]] = {
    "open_project": ({"project_root": str}, {"budgets": dict, "restore": bool}),
    "describe_api": ({}, {}),
    "write_script": (
        {"source": str, "expected_revision": str},
        {"display": dict},
    ),
    "edit_script": (
        {"replacements": list, "expected_revision": str},
        {"display": dict},
    ),
    "set_params": (
        {"values": dict, "expected_revision": str},
        {"display": dict},
    ),
    "rebuild": ({}, {"display": dict}),
    "resolve_pin": ({"output": str, "selection": dict}, {}),
    "inspect": (
        {"scope": str},
        {"target": str, "path": str, "offset": int, "limit": int, "attach": bool},
    ),
    "cancel": ({}, {"request_id": str}),
    "shutdown": ({}, {}),
}

assert set(OP_ARG_SPECS) == MODELING_OPS | READ_OPS | CONTROL_OPS


class ProtocolError(ValueError):
    """A structurally invalid frame; carries the request id when known."""

    def __init__(self, message: str, *, request_id: str | None = None) -> None:
        self.request_id = request_id
        super().__init__(message)


def failure(code: str, message: str, **details: Any) -> dict[str, Any]:
    """A server-level failure envelope (tool envelopes pass through as-is)."""

    return {
        "ok": False,
        "failure_code": str(code),
        "error": str(message),
        **details,
    }


def encode_frame(payload: Mapping[str, Any]) -> bytes:
    """Encode one frame as a newline-terminated JSON line."""

    data = json.dumps(
        dict(payload),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode("utf-8")
    if len(data) > MAX_FRAME_BYTES:
        raise ProtocolError(
            f"Frame of {len(data)} bytes exceeds the {MAX_FRAME_BYTES}-byte cap."
        )
    return data + b"\n"


def decode_frame(line: bytes | str) -> dict[str, Any]:
    """Decode one NDJSON line into a frame object."""

    if isinstance(line, str):
        line = line.encode("utf-8")
    if len(line) > MAX_FRAME_BYTES:
        raise ProtocolError(
            f"Frame of {len(line)} bytes exceeds the {MAX_FRAME_BYTES}-byte cap."
        )
    try:
        value = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtocolError(f"Frame is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ProtocolError("Every frame must be one JSON object.")
    return value


def validate_request(frame: Mapping[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Validate one request frame; return ``(request_id, op, args)``."""

    raw_id = frame.get("id")
    request_id = raw_id if isinstance(raw_id, str) else None
    if not request_id or len(request_id) > MAX_REQUEST_ID_CHARS:
        raise ProtocolError(
            f"Request id must be a non-empty string of at most "
            f"{MAX_REQUEST_ID_CHARS} characters.",
            request_id=request_id,
        )
    if frame.get("schema") != PROTOCOL_SCHEMA:
        raise ProtocolError(
            f"Request schema must be {PROTOCOL_SCHEMA!r}.", request_id=request_id
        )
    unknown_fields = set(frame) - {"schema", "id", "op", "args"}
    if unknown_fields:
        raise ProtocolError(
            f"Request carries unknown fields: {sorted(unknown_fields)}.",
            request_id=request_id,
        )
    op = frame.get("op")
    if not isinstance(op, str) or op not in OP_ARG_SPECS:
        raise ProtocolError(
            f"Unknown op {op!r}; supported: {sorted(OP_ARG_SPECS)}.",
            request_id=request_id,
        )
    args = frame.get("args", {})
    if not isinstance(args, dict):
        raise ProtocolError("args must be an object.", request_id=request_id)
    required, optional = OP_ARG_SPECS[op]
    unknown_args = set(args) - set(required) - set(optional)
    if unknown_args:
        raise ProtocolError(
            f"{op} does not accept args: {sorted(unknown_args)}.",
            request_id=request_id,
        )
    for name, expected in required.items():
        if name not in args:
            raise ProtocolError(
                f"{op} requires args.{name}.", request_id=request_id
            )
        if not isinstance(args[name], expected) or isinstance(args[name], bool) != (
            expected is bool
        ):
            raise ProtocolError(
                f"{op} args.{name} must be {expected.__name__}.",
                request_id=request_id,
            )
    for name, expected in optional.items():
        if name not in args or args[name] is None:
            continue
        if not isinstance(args[name], expected) or isinstance(args[name], bool) != (
            expected is bool
        ):
            raise ProtocolError(
                f"{op} args.{name} must be {expected.__name__}.",
                request_id=request_id,
            )
    return request_id, op, dict(args)
