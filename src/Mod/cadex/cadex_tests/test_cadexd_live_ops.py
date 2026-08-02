# SPDX-License-Identifier: LGPL-2.1-or-later

"""The three live ops, at the protocol and dispatch level (ADR-109).

No worker is spawned here and none needs to be: what this file is about is
the half of live mode that runs in ``cadexd`` -- argument validation, the
read/modeling split, and the refusal shape. The half that runs physics is
:mod:`test_dynamics_live_hook` and the packaged gate.

**The refusal shape is the point.** A project with no accepted rollout is a
*state*, not an error: the user has not built one yet, and the panel should
say so rather than show a failure envelope. So every way ``live_open`` can
decline answers ``ok: true`` with ``live: false`` and a reason -- exactly
the shape ``preview_params`` refuses in (ADR-055) -- and the response spec
is pinned by op rather than by outcome, which means a refusal has to carry
the whole shape or it does not validate.
"""

from __future__ import annotations

import pytest

import CadexdProtocol as protocol
from cadexd import CadexdServer


def _request(op: str, args: dict | None = None, request_id: str = "r1") -> dict:
    frame = {"schema": protocol.PROTOCOL_SCHEMA, "id": request_id, "op": op}
    if args is not None:
        frame["args"] = args
    return frame


class _Harness:
    def __init__(self) -> None:
        self.frames: list[dict] = []
        self.server = CadexdServer(self.frames.append)

    def admit(self, op: str, args: dict | None = None, request_id: str = "r1"):
        line = protocol.encode_frame(_request(op, args, request_id))[:-1]
        return self.server.admit(line)

    def roundtrip(self, op: str, args: dict | None = None, request_id: str = "r1"):
        admitted = self.admit(op, args, request_id)
        assert admitted is not None
        self.server.dispatch(*admitted)
        return self.frames[-1]


# -- the request half --------------------------------------------------------


def test_live_ops_validate_their_arguments() -> None:
    for frame in (
        _request("live_open", {}),  # output is required
        _request("live_open", {"output": 1}),
        _request("live_open", {"output": "play", "seed": "6"}),
        _request("live_step", {}),  # steps is required
        _request("live_step", {"steps": "3"}),
        _request("live_step", {"steps": 3, "push": 4.0}),
        _request("live_open", {"output": "play", "steps": 3}),  # not its arg
    ):
        with pytest.raises(protocol.ProtocolError):
            protocol.validate_request(frame)

    for frame in (
        _request("live_open", {"output": "play"}),
        _request("live_open", {"output": "play", "seed": 6}),
        _request("live_step", {"steps": 3}),
        _request("live_step", {"steps": 3, "push": {"newtons": 1.0}}),
        _request("live_close", {}),
        _request("live_close"),
    ):
        request_id, op, _args = protocol.validate_request(frame)
        assert request_id == "r1" and op.startswith("live_")


def test_a_live_op_never_takes_the_modeling_lock() -> None:
    """A running simulation must not stop the AI editing the script.

    ``admit`` is where a modeling op claims exclusivity, and a live op
    passing through it untouched is the whole of what makes watching the
    machine compatible with changing it. Asserted through ``admit`` rather
    than by reading the frozenset, because membership is only load-bearing
    if it is what the dispatcher consults.
    """

    harness = _Harness()
    admitted = harness.admit("write_script", {"source": "x", "expected_revision": ""})
    assert admitted is not None  # the modeling op is now in flight

    for op, args in (
        ("live_open", {"output": "play"}),
        ("live_step", {"steps": 3}),
        ("live_close", {}),
    ):
        assert harness.admit(op, args, request_id="live") is not None, (
            f"{op} was refused while a modeling op was in flight; it is a "
            "read op and must queue behind one instead."
        )
    # ...where a second modeling op *is* refused, which is what says the
    # in-flight one was really in flight.
    assert harness.admit("rebuild", {}, request_id="r2") is None
    assert harness.frames[-1]["failure_code"] == protocol.CADEXD_BUSY


# -- the response half -------------------------------------------------------


def test_live_ops_refuse_before_a_project_is_open() -> None:
    harness = _Harness()
    for op, args in (
        ("live_open", {"output": "play"}),
        ("live_step", {"steps": 3}),
    ):
        answer = harness.roundtrip(op, args)
        assert answer["ok"] is False
        assert answer["failure_code"] == protocol.CADEXD_NOT_OPEN


def test_closing_a_session_that_was_never_open_is_fine() -> None:
    """Idempotent, and answerable without a project: it is a teardown.

    The shell calls it on every stop, on file close, and on add-on unload,
    and a teardown that can fail is a teardown that leaves a worker running.
    """

    harness = _Harness()
    answer = harness.roundtrip("live_close", {})
    assert answer["ok"] is True
    assert answer["closed"] is True
    assert answer["live"] is False
    assert not protocol.validate_response("live_close", answer)


def test_a_declined_live_open_carries_the_whole_response_shape() -> None:
    """A refusal the shell cannot parse is a refusal it cannot show."""

    from cadexd import _declined_live_open

    answer = {"id": "r1", **_declined_live_open("no accepted rollout")}
    assert answer["live"] is False
    assert answer["reason"]
    assert not protocol.validate_response("live_open", answer), (
        "a declined live_open must satisfy the same pinned response spec a "
        "successful one does; the spec is per op, not per outcome"
    )


def test_a_declined_live_step_carries_the_whole_response_shape() -> None:
    from cadexd import _declined_live_step

    answer = {"id": "r1", **_declined_live_step("no live session is open")}
    assert answer["frames"] == [] and answer["live"] is False
    assert not protocol.validate_response("live_step", answer)


def test_a_step_with_no_session_declines_rather_than_failing() -> None:
    harness = _Harness()
    harness.server._service = object()  # a project is open
    harness.server._project_root = "/nowhere"
    answer = harness.roundtrip("live_step", {"steps": 3})
    assert answer["ok"] is True and answer["live"] is False
    assert "no live session" in answer["reason"]


# -- the host-side session object --------------------------------------------


def test_the_session_bounds_a_step_before_it_reaches_the_worker() -> None:
    """An unbounded batch is an 8 MB frame cap waiting to be hit."""

    from CadexLiveSession import (
        MAX_STEPS_PER_REQUEST,
        CadexLiveSession,
        LiveSessionFailure,
    )

    session = CadexLiveSession("/nowhere")
    assert not session.is_open
    for steps in (0, -1, MAX_STEPS_PER_REQUEST + 1):
        with pytest.raises(LiveSessionFailure):
            session.step(steps, None)


def test_the_session_names_its_worker_and_never_imports_it() -> None:
    """The string is the architecture (ADR-055's rule, ADR-109's stakes)."""

    import CadexLiveSession as host

    assert host.ENTRY_MODULE == "cadex_live_worker"
    assert not hasattr(host, "cadex_live_worker")
