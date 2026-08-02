# SPDX-License-Identifier: LGPL-2.1-or-later

"""Stub coverage for the cadexd protocol and server dispatch (Phase 5.3)."""

from __future__ import annotations

import json

import pytest

import CadexdProtocol as protocol
from cadexd import CadexdServer


# -- codec -------------------------------------------------------------------


def test_frame_roundtrip() -> None:
    frame = {"schema": protocol.PROTOCOL_SCHEMA, "id": "r1", "op": "shutdown"}
    encoded = protocol.encode_frame(frame)
    assert encoded.endswith(b"\n")
    assert protocol.decode_frame(encoded[:-1]) == frame


def test_frame_cap_is_enforced_both_ways() -> None:
    huge = {"schema": protocol.PROTOCOL_SCHEMA, "payload": "x" * (8 * 1024 * 1024)}
    with pytest.raises(protocol.ProtocolError):
        protocol.encode_frame(huge)
    with pytest.raises(protocol.ProtocolError):
        protocol.decode_frame(b"x" * (protocol.MAX_FRAME_BYTES + 1))


def test_decode_rejects_non_object_frames() -> None:
    with pytest.raises(protocol.ProtocolError):
        protocol.decode_frame(b"[1, 2]")
    with pytest.raises(protocol.ProtocolError):
        protocol.decode_frame(b"not json")


# -- op registry -------------------------------------------------------------


def test_op_list_is_pinned() -> None:
    assert set(protocol.OP_ARG_SPECS) == {
        "open_project",
        "describe_api",
        "write_script",
        "edit_script",
        "set_params",
        "rebuild",
        "put_asset",
        "resolve_pin",
        "inspect",
        "preview_params",
        "live_open",
        "live_step",
        "live_close",
        "cancel",
        "shutdown",
    }
    # A read op, and the membership is load-bearing: preview_params writes
    # nothing, and queueing behind an in-flight modeling request is exactly
    # what should happen when a drag's preview meets the set_params that
    # settles it (ADR-055).
    assert "preview_params" in protocol.READ_OPS
    assert "preview_params" not in protocol.MODELING_OPS
    # The same for the three live ops, and a sharper reason (ADR-109): a
    # live session writes nothing at all, and a running simulation that
    # blocked the AI from editing the script would make watching the
    # mechanism and changing it mutually exclusive.
    for op in ("live_open", "live_step", "live_close"):
        assert op in protocol.READ_OPS
        assert op not in protocol.MODELING_OPS
    assert protocol.MODELING_OPS == {
        "open_project",
        "write_script",
        "edit_script",
        "set_params",
        "rebuild",
        # Writes the project store; modeling so it cannot race the staging
        # a rebuild does out of that same directory (ADR-043).
        "put_asset",
    }


def _request(op: str, args: dict | None = None, request_id: str = "r1") -> dict:
    frame: dict = {"schema": protocol.PROTOCOL_SCHEMA, "id": request_id, "op": op}
    if args is not None:
        frame["args"] = args
    return frame


def test_validate_request_happy_path() -> None:
    request_id, op, args = protocol.validate_request(
        _request("write_script", {"source": "result = {}", "expected_revision": ""})
    )
    assert (request_id, op) == ("r1", "write_script")
    assert args["source"] == "result = {}"


@pytest.mark.parametrize(
    "frame",
    [
        {"id": "r1", "op": "shutdown"},  # missing schema
        {"schema": protocol.PROTOCOL_SCHEMA, "op": "shutdown"},  # missing id
        _request("no_such_op"),
        _request("write_script", {"source": "x"}),  # missing expected_revision
        _request("write_script", {"source": 4, "expected_revision": ""}),
        _request("set_params", {"values": [], "expected_revision": ""}),
        _request("inspect", {"scope": "script", "bogus": 1}),
        _request("open_project", {"project_root": "/x", "restore": "yes"}),
        {**_request("shutdown"), "extra": True},
    ],
)
def test_validate_request_rejects_malformed(frame: dict) -> None:
    with pytest.raises(protocol.ProtocolError):
        protocol.validate_request(frame)


def test_validate_request_keeps_request_id_when_known() -> None:
    with pytest.raises(protocol.ProtocolError) as info:
        protocol.validate_request(_request("no_such_op", request_id="r9"))
    assert info.value.request_id == "r9"


# -- server dispatch (fake pipeline, no FreeCAD) -----------------------------


class _Harness:
    def __init__(self, run_lifecycle=None, resolve_pin=None) -> None:
        self.frames: list[dict] = []
        self.server = CadexdServer(
            self.frames.append,
            run_lifecycle=run_lifecycle,
            resolve_pin=resolve_pin,
        )

    def admit(self, op: str, args: dict | None = None, request_id: str = "r1"):
        line = protocol.encode_frame(_request(op, args, request_id))[:-1]
        return self.server.admit(line)

    def roundtrip(self, op: str, args: dict | None = None, request_id: str = "r1"):
        admitted = self.admit(op, args, request_id)
        assert admitted is not None
        self.server.dispatch(*admitted)
        return self.frames[-1]


def test_protocol_error_is_answered_inline() -> None:
    harness = _Harness()
    assert harness.server.admit(b"not json") is None
    assert harness.frames[-1]["failure_code"] == "CADEXD_PROTOCOL_ERROR"


def test_modeling_ops_require_an_open_project() -> None:
    harness = _Harness()
    response = harness.roundtrip(
        "write_script", {"source": "result = {}", "expected_revision": ""}
    )
    assert response["failure_code"] == "CADEXD_NOT_OPEN"
    assert response["id"] == "r1"


def test_second_modeling_request_is_refused_busy() -> None:
    harness = _Harness()
    first = harness.admit(
        "write_script",
        {"source": "result = {}", "expected_revision": ""},
        request_id="r1",
    )
    assert first is not None
    refused = harness.admit(
        "set_params",
        {"values": {}, "expected_revision": ""},
        request_id="r2",
    )
    assert refused is None
    busy = harness.frames[-1]
    assert busy["id"] == "r2"
    assert busy["failure_code"] == "CADEXD_BUSY"
    # Read-only requests still queue.
    assert harness.admit("describe_api", request_id="r3") is not None
    # Completing the first request frees the slot.
    harness.server.dispatch(*first)
    assert (
        harness.admit(
            "set_params",
            {"values": {}, "expected_revision": ""},
            request_id="r4",
        )
        is not None
    )


def test_lifecycle_payload_flows_verbatim_with_display_block(tmp_path) -> None:
    staging = tmp_path / "attempt-1"
    (staging / "outputs").mkdir(parents=True)
    accept_payload = {
        "ok": True,
        "tool": "xscript.project.write_script",
        "outputs": [{"name": "plate", "type": "solid", "domain": "part"}],
        "digest": "ab" * 32,
        "revision": "cd" * 32,
        "model_state": {"status": "accepted"},
    }

    def fake_lifecycle(_service, tool, args, **kwargs):
        assert tool == "xscript.project.write_script"
        sink = kwargs.get("result_sink")
        if sink is not None:
            sink["prepared"] = {"staging": str(staging)}
            sink["validated"] = {
                "outputs": [
                    {
                        "name": "plate",
                        "artifact_kind": "brep",
                        "artifact_path": "outputs/output-000.brep",
                        "display": {
                            "artifact_kind": "tessellation",
                            "artifact_path": "display/display-000.tess.bin",
                            "sidecar_path": "display/display-000.tess.json",
                        },
                    }
                ]
            }
        return dict(accept_payload)

    harness = _Harness(run_lifecycle=fake_lifecycle)
    harness.server._service = object()
    harness.server._project_root = tmp_path
    response = harness.roundtrip(
        "write_script", {"source": "result = {}", "expected_revision": ""}
    )
    for key, value in accept_payload.items():
        assert response[key] == value
    display = response["display"]["plate"]
    assert display["artifact_kind"] == "brep"
    assert display["artifact_path"] == str(staging / "outputs/output-000.brep")
    assert display["tessellation"]["artifact_path"] == str(
        staging / "display/display-000.tess.bin"
    )
    assert display["placement"] is None


def test_failure_envelope_flows_verbatim() -> None:
    envelope = {
        "ok": False,
        "failure_code": "STALE_PROGRAM_REVISION",
        "failure_stage": "precondition",
        "error": "The project script changed after inspection.",
    }
    harness = _Harness(run_lifecycle=lambda *a, **k: dict(envelope))
    harness.server._service = object()
    response = harness.roundtrip(
        "write_script", {"source": "result = {}", "expected_revision": "zz"}
    )
    for key, value in envelope.items():
        assert response[key] == value
    assert "display" not in response


def test_cancel_routes_to_the_inflight_cancellation_check() -> None:
    harness = _Harness()
    observed: dict = {}

    def fake_lifecycle(_service, _tool, _args, **kwargs):
        check = kwargs["cancellation_check"]
        observed["before"] = check()
        # A cancel frame arriving on the reader thread mid-run:
        assert harness.admit("cancel", {}, request_id="rc") is None
        observed["after"] = check()
        return {"ok": False, "failure_code": "RUN_CANCELLED", "cancelled": True}

    harness.server._injected_run_lifecycle = fake_lifecycle
    harness.server._service = object()
    admitted = harness.admit(
        "write_script", {"source": "result = {}", "expected_revision": ""}
    )
    harness.server.dispatch(*admitted)
    assert observed == {"before": False, "after": True}
    cancel_ack = next(frame for frame in harness.frames if frame.get("id") == "rc")
    assert cancel_ack == {"id": "rc", "ok": True, "cancelled": "r1"}
    assert harness.frames[-1]["failure_code"] == "RUN_CANCELLED"


def test_cancel_without_inflight_request_acks_none() -> None:
    harness = _Harness()
    assert harness.admit("cancel", {}, request_id="rc") is None
    assert harness.frames[-1] == {"id": "rc", "ok": True, "cancelled": None}


def test_inspect_selection_scope_is_rejected_shell_side() -> None:
    harness = _Harness()
    harness.server._service = object()
    response = harness.roundtrip("inspect", {"scope": "selection"})
    assert response["failure_code"] == "CADEXD_PROTOCOL_ERROR"
    assert "shell-side" in response["error"]


def test_progress_events_are_forwarded_with_the_request_id() -> None:
    def fake_lifecycle(_service, _tool, _args, **kwargs):
        kwargs["progress_callback"]({"event": "cadex_domain_worker_started"})
        return {"ok": False, "failure_code": "X", "error": "x"}

    harness = _Harness(run_lifecycle=fake_lifecycle)
    harness.server._service = object()
    harness.roundtrip(
        "write_script", {"source": "result = {}", "expected_revision": ""}
    )
    event = next(frame for frame in harness.frames if "event" in frame)
    assert event["id"] == "r1"
    assert event["event"]["event"] == "cadex_domain_worker_started"


def test_shutdown_sets_the_flag() -> None:
    harness = _Harness()
    response = harness.roundtrip("shutdown")
    assert response["ok"] is True
    assert harness.server.shutdown_requested is True


def test_handler_exception_becomes_an_envelope_and_frees_the_slot() -> None:
    def broken(*_a, **_k):
        raise RuntimeError("boom")

    harness = _Harness(run_lifecycle=broken)
    harness.server._service = object()
    response = harness.roundtrip(
        "write_script", {"source": "result = {}", "expected_revision": ""}
    )
    assert response["failure_code"] == "CADEXD_PROTOCOL_ERROR"
    assert "boom" in response["error"]
    # Slot freed: a new modeling request is admitted.
    assert (
        harness.admit(
            "set_params", {"values": {}, "expected_revision": ""}, request_id="r5"
        )
        is not None
    )
