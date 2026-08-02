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
#: ``put_asset`` writes the project store rather than the document, but it
#: belongs here and not in :data:`READ_OPS`: membership is what makes it
#: mutually exclusive with an in-flight rebuild, so an asset can never land
#: half-copied while ``_stage_project_assets`` is reading (ADR-043).
MODELING_OPS = frozenset(
    {
        "open_project",
        "write_script",
        "edit_script",
        "set_params",
        "rebuild",
        "put_asset",
    }
)
#: Read-only ops; these queue behind an in-flight modeling op.
#:
#: ``preview_params`` belongs here and emphatically not in
#: :data:`MODELING_OPS`: it writes nothing, and queueing behind an in-flight
#: modeling op is exactly the wanted behaviour when a drag's preview collides
#: with the settle-time ``set_params`` behind it (ADR-055).
#:
#: The three live ops are here for the same reason and a sharper one
#: (ADR-109): a live session writes nothing at all -- no store, no
#: publication, no trace -- and a running simulation that *blocked* the AI
#: from editing the script would make watching the machine and changing it
#: mutually exclusive, which is the opposite of the point.
READ_OPS = frozenset(
    {
        "describe_api",
        "resolve_pin",
        "inspect",
        "preview_params",
        "live_open",
        "live_step",
        "live_close",
    }
)
#: Control ops; handled out of band by the reader.
CONTROL_OPS = frozenset({"cancel", "shutdown"})

#: op → (required {name: type}, optional {name: type}). Deep validation
#: stays in the pipeline; this rejects only structurally wrong requests.
OP_ARG_SPECS: dict[str, tuple[dict[str, type], dict[str, type]]] = {
    "open_project": ({"project_root": str}, {"budgets": dict, "restore": bool}),
    "describe_api": ({}, {}),
    # `replace` is the caller saying it means to drop outputs the accepted
    # revision declares. Without it a write_script that would remove one is
    # refused, because write_script replaces THE whole project script and
    # "add a part" is an easy way to ask for exactly that by accident
    # (ADR-045).
    "write_script": (
        {"source": str, "expected_revision": str},
        {"display": dict, "replace": bool},
    ),
    "edit_script": (
        {"replacements": list, "expected_revision": str},
        {"display": dict},
    ),
    # `nets` is the connection table's stored rows (ADR-065): a **full row
    # list**, not a patch, which is what lets the wiring editor add and
    # delete wires. One op rather than a second `set_nets`, because "set the
    # values of declared controls without the AI" is one concept and a slider
    # and a wire are both instances of it. A nets-only edit sends `values`
    # empty.
    "set_params": (
        {"values": dict, "expected_revision": str},
        {"display": dict, "nets": list},
    ),
    "rebuild": ({}, {"display": dict}),
    # A path, not bytes: the asset budget is 128 MB and the frame cap is 8 MB.
    # Both halves share a filesystem and the protocol already relies on it
    # (``inspect scope=image`` hands back a store path).
    "put_asset": ({"source_path": str}, {"name": str}),
    "resolve_pin": ({"output": str, "selection": dict}, {}),
    "inspect": (
        {"scope": str},
        {"target": str, "path": str, "offset": int, "limit": int, "attach": bool},
    ),
    # Read-only, and the only op that answers a *candidate* rather than the
    # model: solved placements for a parameter change that moved nothing but
    # poses. Same guard as set_params, because a preview of a revision the
    # caller is not looking at is worse than no preview (ADR-055).
    "preview_params": ({"values": dict, "expected_revision": str}, {}),
    # Live mode (ADR-109). `output` names the accepted revision's rollout;
    # `seed` is the first episode's, and every auto-reset after it counts up
    # from there so a session can be described by one number.
    #
    # `variation` asks whether the episode is played as the bundle declares
    # it -- randomisation, reset variation and the task's own shoves -- or
    # calm: one fixed machine at the solved pose with nothing pushing it
    # (ADR-110). It defaults **true** here because the op's job is to play
    # the task, and a calm session is a simplification the caller asks for;
    # the panel defaults its checkbox off and always sends the field, so
    # there is one default in one place.
    "live_open": ({"output": str}, {"seed": int, "variation": bool}),
    # `steps` is control steps to advance, and the reply carries one frame
    # per step: the shell owns the clock, so this is the whole of how time
    # passes. `push` is the user's shove -- newtons at an azimuth about
    # world +X (ADR-107), for a duration, at one component's centre of mass.
    "live_step": ({"steps": int}, {"push": dict}),
    "live_close": ({}, {}),
    "cancel": ({}, {"request_id": str}),
    "shutdown": ({}, {}),
}

assert set(OP_ARG_SPECS) == MODELING_OPS | READ_OPS | CONTROL_OPS

#: Keys on every response frame, success or failure.
RESPONSE_ENVELOPE_KEYS = frozenset({"id", "ok"})

#: A *tool-level* failure is one envelope regardless of op:
#: ``(required, optional)`` beyond :data:`RESPONSE_ENVELOPE_KEYS`. The agent
#: reads ``failure_code``, ``observed`` and ``retry`` and acts on them, so
#: they are contract, not diagnostics.
FAILURE_RESPONSE_SPEC: tuple[frozenset[str], frozenset[str]] = (
    frozenset(
        {
            "tool",
            "error",
            "failure_code",
            "failure_stage",
            "observed",
            "normalized",
            "requested",
            "retry",
            "candidates",
            "allowed_values",
            "native_diagnostics",
            "state_change",
        }
    ),
    # `model_state` rides along on a modeling op; `domain_failure_stage`
    # names the pipeline stage when the failure came from a domain worker
    # rather than the lifecycle itself.
    frozenset({"model_state", "domain_failure_stage"}),
)

#: A *server-level* failure — the codes above, produced by :func:`failure`
#: before any tool runs — is deliberately smaller: there is no tool, no
#: stage and no document state to report. Collapsing the two would let a
#: bare ``{ok, failure_code, error}`` pass as a pipeline failure the agent
#: expects to be able to act on.
#:
#: The optional set is what the server actually sends: ``busy_with`` names
#: the in-flight modeling request a ``CADEXD_BUSY`` refused for,
#: ``exception_type`` names the class of an exception a handler did not
#: expect, and ``restore_failure`` / ``observed`` carry the two ways an open
#: can fail its restore pass — the payload of a script that would not run,
#: and the digests that disagreed. Declared because a key the server sends
#: and the spec does not name is a key the shell may not read (ADR-055).
SERVER_FAILURE_SPEC: tuple[frozenset[str], frozenset[str]] = (
    frozenset({"error", "failure_code"}),
    frozenset(
        {
            "op",
            "request_id",
            "detail",
            "busy_with",
            "exception_type",
            "restore_failure",
            "observed",
        }
    ),
)

SERVER_FAILURE_CODES = frozenset(
    {
        CADEXD_PROTOCOL_ERROR,
        CADEXD_BUSY,
        CADEXD_NOT_OPEN,
        CADEXD_CRASHED,
        CADEXD_RESTORE_FAILED,
    }
)

#: Keys shared by every successful modeling-op response.
_MODELING_RESPONSE_REQUIRED = frozenset(
    {
        "tool",
        "revision",
        "accepted_revision",
        "digest",
        "model_state",
        "outputs",
        "live_outputs",
        "removed",
    }
)

#: op → (required, optional) keys of a **successful** response, beyond
#: :data:`RESPONSE_ENVELOPE_KEYS`. ``OP_ARG_SPECS`` pins requests; this pins
#: replies, so either side of the protocol can be replaced independently
#: (ADR-025). Nested shapes the shell actually reads are in
#: :data:`NESTED_RESPONSE_SPECS`.
OP_RESPONSE_SPECS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "open_project": (
        frozenset({"schema", "project_root", "budgets", "restore", "script"}),
        frozenset({"manifest"}),
    ),
    "describe_api": (
        frozenset(
            {
                "domain",
                "domains",
                "engine",
                "instructions",
                "program_schema",
                "result_contract",
                "revision_rule",
                "source_globals",
                "parameters",
                # The connection vocabulary (ADR-065), beside `parameters`
                # and for the same reason: a table the script declares and
                # something outside it sets.
                "connections",
                "mutation_selection",
            }
        ),
        frozenset(),
    ),
    # `display` rides along whenever the run staged geometry, which is every
    # script that declares an output — not only when `display` was requested.
    # `stdout` is the script's own output: always sent, empty for a script that
    # printed nothing, and optional here only so a shell written against the
    # older shape still validates (ADR-044).
    "write_script": (_MODELING_RESPONSE_REQUIRED, frozenset({"display", "stdout"})),
    "edit_script": (_MODELING_RESPONSE_REQUIRED, frozenset({"display", "stdout"})),
    "set_params": (_MODELING_RESPONSE_REQUIRED, frozenset({"display", "stdout"})),
    "rebuild": (_MODELING_RESPONSE_REQUIRED, frozenset({"display", "stdout"})),
    # The stored file's identity, plus the whole listing: one round trip
    # answers "did it land" and "what is importable now".
    "put_asset": (
        frozenset({"name", "bytes", "sha256", "assets"}),
        frozenset(),
    ),
    "resolve_pin": (
        frozenset({"output", "revision", "subelements", "details"}),
        frozenset(),
    ),
    "inspect": (
        frozenset(
            {
                "scope",
                "target",
                "path",
                "value",
                "page",
                "document",
                "surface",
                "result_json_bytes",
            }
        ),
        frozenset(),
    ),
    # `placements` is {output_name: [16 floats]} -- flat arrays, so there is
    # no nested object shape to pin and no NESTED_RESPONSE_SPECS entry.
    # `reason` rides only on a refusal, and is for the log and the shell's
    # latch, never for the user.
    "preview_params": (
        frozenset({"placements", "revision", "previewable"}),
        frozenset({"reason"}),
    ),
    # `live` rides on every live reply, successful or refused, and is the
    # one place a refusal says why: a project with no accepted rollout is a
    # state rather than an error, exactly as `previewable: false` is.
    # `policy` is WHICH policy is about to play -- its script label, the
    # asset filename and the digest the engine just re-checked (ADR-111).
    # Without it a live session is anonymous: the shell can say a machine is
    # standing and cannot say what is driving it, and two policies that
    # differ by an hour of GPU look identical in the viewport. That was a
    # real question asked of a real session, and the answer took reading the
    # project's script.
    "live_open": (
        frozenset({"live", "components", "control_hz", "frames_per_second",
                   "actuator_channels", "episode_seconds", "policy"}),
        frozenset({"reason"}),
    ),
    "live_step": (
        frozenset({"live", "frames", "step", "time_s", "terminated",
                   "termination", "reset_count"}),
        frozenset({"reason"}),
    ),
    "live_close": (frozenset({"live", "closed"}), frozenset()),
    "cancel": (frozenset({"cancelled"}), frozenset()),
    "shutdown": (frozenset({"shutting_down"}), frozenset()),
}

assert set(OP_RESPONSE_SPECS) == set(OP_ARG_SPECS)

#: Nested response shapes the Blender shell reads by name. Keyed by a dotted
#: path; ``*`` matches one level of mapping keys (an output name).
NESTED_RESPONSE_SPECS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    # Which policy a live session is playing (ADR-111). `label` is the
    # script's own name for it, `weights` the asset filename, `sha256` the
    # digest the engine re-checked before handing it to the worker, and
    # `trained_label` what the trainer called the run that produced it --
    # which is the one field that distinguishes two checkpoints of the same
    # file name. Every key is present and empty on a refusal, as everywhere
    # else in this table.
    "policy": (
        frozenset({"label", "weights", "sha256", "trained_label"}),
        frozenset(),
    ),
    # `source_output` rides only on component entries: the declared output
    # whose geometry this one places (ADR-049). Optional because every other
    # output kind has no source to name.
    "display.*": (
        frozenset({"artifact_kind", "artifact_path", "placement", "tessellation"}),
        frozenset({"source_output"}),
    ),
    "display.*.tessellation": (
        frozenset(
            {"artifact_kind", "artifact_path", "sidecar_path", "counts", "deflection", "quality"}
        ),
        frozenset(),
    ),
    "display.*.tessellation.counts": (
        frozenset({"faces", "edges", "triangles", "vertices", "edge_vertices"}),
        frozenset(),
    ),
    "model_state": (
        frozenset(
            {
                "status",
                "accepted_is_current",
                "next_write_expected_revision",
                "verification_goal",
            }
        ),
        frozenset(),
    ),
    "live_outputs.*": (
        frozenset({"object_name", "label", "type_id", "output_type"}),
        frozenset({"domain", "derived_state", "stale_reason", "source_revision",
                   "facts", "operation_diagnostics", "mesh_data", "assembly_data"}),
    ),
    "script": (
        frozenset(
            {
                "script_present",
                "source",
                "source_characters",
                "params",
                "revisions",
                "accepted",
                "latest_candidate",
                "updated_at",
            }
        ),
        frozenset(),
    ),
    # A performed restore also reports the digest it re-derived and that it
    # matched; a skipped one carries neither. `repaired_from_accepted` appears
    # only when the working script would not run and the accepted revision's
    # own source was used instead (ADR-044).
    "restore": (
        frozenset({"performed"}),
        frozenset({"digest", "matches_accepted", "repaired_from_accepted"}),
    ),
    "budgets": (frozenset({"timeout_seconds", "memory_limit_mb"}), frozenset()),
}


def _check_keys(
    where: str,
    value: Any,
    spec: tuple[frozenset[str], frozenset[str]],
    problems: list[str],
) -> None:
    if not isinstance(value, Mapping):
        problems.append(f"{where}: expected an object, got {type(value).__name__}")
        return
    required, optional = spec
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required - optional)
    if missing:
        problems.append(f"{where}: missing {missing}")
    if unknown:
        problems.append(f"{where}: unexpected {unknown}")


def validate_response(op: str, frame: Mapping[str, Any]) -> list[str]:
    """Return a list of shape violations for one response frame.

    Empty means the frame matches the pinned contract. Shape only: key
    presence and nesting, never values.
    """

    problems: list[str] = []
    if op not in OP_RESPONSE_SPECS:
        return [f"unknown op {op!r}"]
    if "id" not in frame:
        problems.append("response: missing ['id']")
    ok = frame.get("ok")
    if not isinstance(ok, bool):
        problems.append("response: 'ok' must be a bool")
        return problems

    if ok:
        required, optional = OP_RESPONSE_SPECS[op]
    elif frame.get("failure_code") in SERVER_FAILURE_CODES:
        required, optional = SERVER_FAILURE_SPEC
    else:
        required, optional = FAILURE_RESPONSE_SPEC
    _check_keys(
        f"{op} response",
        {k: v for k, v in frame.items() if k not in RESPONSE_ENVELOPE_KEYS},
        (required, optional),
        problems,
    )
    if not ok:
        return problems

    for path, nested in NESTED_RESPONSE_SPECS.items():
        for where, value in _resolve_path(frame, path.split(".")):
            _check_keys(f"{op} {where}", value, nested, problems)
    return problems


def _resolve_path(value: Any, parts: list[str]) -> list[tuple[str, Any]]:
    """Walk a dotted path, expanding ``*`` over mapping keys.

    Absent keys yield nothing: presence is the outer spec's business, and a
    ``None`` placeholder (an output with no display artifact) is not a shape
    violation.
    """

    found: list[tuple[str, Any]] = [("", value)]
    for part in parts:
        step: list[tuple[str, Any]] = []
        for where, current in found:
            if not isinstance(current, Mapping):
                continue
            if part == "*":
                step.extend(
                    (f"{where}.{key}" if where else str(key), item)
                    for key, item in current.items()
                    if item is not None
                )
            elif current.get(part) is not None:
                step.append((f"{where}.{part}" if where else part, current[part]))
        found = step
    return found


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
