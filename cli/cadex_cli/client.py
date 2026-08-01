# SPDX-License-Identifier: LGPL-2.1-or-later

"""A cadexd client for a process that owns its terminal.

Derived from the two engine-side precedents rather than from the shell's
``cadexd_client.py``, which is GPL and may not be copied here (ADR-061):
``cadexd_latency_integration.py``'s ``_Stdio`` for the NDJSON loop and the
pre-hijack-chatter tolerance, and ``test_cadexd_lifecycle.py``'s
``_CadexdClient`` for the ready banner, the event-vs-response split, and
checking every reply against ``OP_RESPONSE_SPECS`` on the way through.

One request at a time, which is not a limitation the CLI is working around:
it is the whole shape of the thing. A pipeline step has one prompt, one
model loop and one project, so there is never a second writer — which is
also why :mod:`cadex_cli.bridge` can fill in ``expected_revision`` rather
than asking the model to.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from typing import Any

from .engine import Engine

#: A modelling op can legitimately take minutes (the drone in the routing
#: tests takes 17 s; a big fillet tree takes longer). The cap exists to stop
#: a wedged engine hanging a pipeline forever, not to bound honest work.
DEFAULT_TIMEOUT_SECONDS = 900.0

#: FreeCADCmd loads OCCT and every kept workbench before cadexd hijacks the
#: fds and announces itself. On a cold page cache that is not fast.
READY_TIMEOUT_SECONDS = 180.0

EventCallback = Callable[[dict[str, Any]], None]


class CadexdError(RuntimeError):
    """The engine could not be spoken to: spawn, EOF, timeout, or bad shape."""


class CadexdClient:
    """Spawn one ``cadexd`` and talk to it."""

    def __init__(
        self,
        engine: Engine,
        *,
        on_event: EventCallback | None = None,
        stderr: int | None = subprocess.DEVNULL,
    ) -> None:
        self.engine = engine
        self.on_event = on_event
        self._stderr = stderr
        self._process: subprocess.Popen[bytes] | None = None
        self._sequence = 0
        self._pending: dict[str, dict[str, Any]] = {}
        self._write_lock = threading.Lock()
        self._in_flight: str | None = None
        #: Every event frame seen, in order, for the report's benefit.
        self.events: list[dict[str, Any]] = []

    # -- lifecycle -------------------------------------------------------

    def start(self, timeout: float = READY_TIMEOUT_SECONDS) -> None:
        """Spawn the engine and block until it announces ``ready``."""

        if self._process is not None:
            raise CadexdError("This client already has an engine running.")
        command = [
            str(self.engine.freecadcmd),
            "-c",
            (
                f"import sys; sys.path.insert(0, {str(self.engine.module_dir)!r}); "
                "import cadexd; raise SystemExit(cadexd.main())"
            ),
        ]
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self._stderr,
                env={**os.environ, "PYTHONHASHSEED": "0"},
            )
        except OSError as exc:
            raise CadexdError(
                f"Could not start the engine ({self.engine.freecadcmd}): {exc}"
            ) from exc

        frame = self._read_frame(timeout)
        raw_event = frame.get("event")
        event: dict[str, Any] = raw_event if isinstance(raw_event, dict) else {}
        if event.get("event") != "ready":
            raise CadexdError(
                f"The engine's first frame was not a ready banner: {frame!r}"
            )

    def close(self) -> None:
        """Stop the engine, gracefully if it will, by force if it will not."""

        process, self._process = self._process, None
        if process is None:
            return
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        for stream in (process.stdin, process.stdout):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass

    def shutdown(self, timeout: float = 60.0) -> None:
        """Ask the engine to exit, then make sure it did."""

        if self._process is None or self._process.poll() is not None:
            self.close()
            return
        try:
            self.request("shutdown", timeout=timeout)
            self._process.wait(timeout=timeout)
        except (CadexdError, subprocess.TimeoutExpired, OSError):
            pass
        finally:
            self.close()

    def __enter__(self) -> CadexdClient:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.shutdown()

    # -- the wire --------------------------------------------------------

    def _read_frame(self, timeout: float) -> dict[str, Any]:
        process = self._process
        if process is None or process.stdout is None:
            raise CadexdError("No engine is running.")
        deadline = time.monotonic() + timeout
        while time.monotonic() <= deadline:
            line = process.stdout.readline()
            if not line:
                raise CadexdError(
                    "The engine closed its protocol stream. "
                    f"(exit status {process.poll()!r})"
                )
            line = line.strip()
            if not line:
                continue
            try:
                frame = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                # Whatever FreeCADCmd printed before cadexd hijacked the fds.
                continue
            if isinstance(frame, dict):
                return frame
        raise CadexdError(f"No frame from the engine within {timeout:g}s.")

    def _send(self, op: str, args: dict[str, Any] | None, request_id: str) -> None:
        process = self._process
        if process is None or process.stdin is None:
            raise CadexdError("No engine is running.")
        frame: dict[str, Any] = {
            "schema": self.engine.protocol.PROTOCOL_SCHEMA,
            "id": request_id,
            "op": op,
        }
        if args is not None:
            frame["args"] = args
        data = self.engine.protocol.encode_frame(frame)
        try:
            with self._write_lock:
                process.stdin.write(data)
                process.stdin.flush()
        except OSError as exc:
            raise CadexdError(f"Could not write to the engine: {exc}") from exc

    def _next_request_id(self) -> str:
        self._sequence += 1
        return f"cli-{self._sequence}"

    def request(
        self,
        op: str,
        args: dict[str, Any] | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """Send one request, collect its events, return the checked reply.

        The reply is shape-checked against *this engine's* own
        ``OP_RESPONSE_SPECS``. A violation is a hard error rather than a
        warning: a third client that quietly tolerates an undeclared key is
        a third client the protocol has stopped being a contract for.
        """

        request_id = self._next_request_id()
        self._send(op, args, request_id)
        self._in_flight = request_id
        try:
            frame = self._await(request_id, timeout)
        finally:
            self._in_flight = None
        problems = self.engine.protocol.validate_response(op, frame)
        if problems:
            raise CadexdError(
                f"The engine's {op} reply violates its own "
                "CadexdProtocol.OP_RESPONSE_SPECS:\n  " + "\n  ".join(problems)
            )
        return frame

    def _await(self, request_id: str, timeout: float) -> dict[str, Any]:
        stashed = self._pending.pop(request_id, None)
        if stashed is not None:
            return stashed
        deadline = time.monotonic() + timeout
        while True:
            frame = self._read_frame(max(0.1, deadline - time.monotonic()))
            if "event" in frame:
                self.events.append(frame)
                if self.on_event is not None:
                    self.on_event(frame)
                continue
            if frame.get("id") == request_id:
                return frame
            # A reply to something else — a cancel ack overtaking the request
            # it cancelled, most likely. Keep it; somebody asked for it.
            self._pending[str(frame.get("id"))] = frame

    def cancel(self, request_id: str | None = None) -> None:
        """Ask the engine to abandon the in-flight modelling run.

        Fire and forget: the ack and the cancelled request's own
        ``RUN_CANCELLED`` failure both come back through :meth:`request`'s
        loop. Safe to call from a signal handler, because writing the frame
        takes only the write lock and never the reader.
        """

        target = request_id or self._in_flight
        args = {"request_id": target} if target else None
        try:
            self._send("cancel", args, self._next_request_id())
        except CadexdError:
            pass

    @property
    def in_flight_request_id(self) -> str | None:
        """The request :meth:`request` is currently blocked on, if any."""

        return self._in_flight


def open_project(
    client: CadexdClient, project_root: Path, *, restore: bool = True
) -> dict[str, Any]:
    """``open_project``, with the failure turned into something readable.

    ``cadexd`` creates the root itself (``mkdir(parents=True,
    exist_ok=True)``), so ``--project`` may name a directory that does not
    exist yet — which is what makes ``cadex -p ... --project ./new`` a
    one-liner rather than a two-step.
    """

    reply = client.request("open_project", {"project_root": str(project_root),
                                            "restore": bool(restore)})
    if reply.get("ok") is not True:
        raise CadexdError(
            f"Could not open {project_root}: "
            f"{reply.get('error') or reply.get('failure_code') or reply}"
        )
    return reply
