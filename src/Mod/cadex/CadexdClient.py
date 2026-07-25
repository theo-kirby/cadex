# SPDX-License-Identifier: LGPL-2.1-or-later

"""Shell-side cadexd client (Phase 5.4).

One client per project root, spawned lazily on first use and killed on
document close / application exit. The client owns the child process and
its stdio protocol stream; requests are serialized (the session already
runs one tool at a time), cancellation polls every 50 ms and forwards a
``cancel`` frame, progress events feed the chat progress UI.

Crash policy: child death mid-request yields a ``CADEXD_CRASHED``
envelope, the client is marked dead, and the next request respawns the
child and replays ``open_project`` (the parameters panel already
self-heals from the resulting ``STALE_PROGRAM_REVISION`` /
``next_write_expected_revision`` flow).
"""

from __future__ import annotations

import atexit
import itertools
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from CadexTools import tool_failure
from CadexdProtocol import (
    CADEXD_CRASHED,
    MODELING_OPS,
    PROTOCOL_SCHEMA,
    decode_frame,
    encode_frame,
)

_CANCEL_POLL_SECONDS = 0.05
_DEFAULT_TIMEOUT_SECONDS = 120.0
_TIMEOUT_MARGIN_SECONDS = 60.0
_READY_TIMEOUT_SECONDS = 120.0


def _crash_envelope(op: str, message: str, **observed: Any) -> dict[str, Any]:
    return tool_failure(
        f"cadexd.{op}",
        CADEXD_CRASHED,
        "external_process",
        message,
        observed=dict(observed),
    )


def _default_command() -> list[str]:
    import FreeCAD as App

    from CadexScriptedRuntime import _freecadcmd

    executable = _freecadcmd(str(App.getHomePath()))
    module_root = Path(__file__).resolve().parent
    code = (
        f"import sys; sys.path.insert(0, {str(module_root)!r}); "
        "import cadexd; raise SystemExit(cadexd.main())"
    )
    return [str(executable), "-c", code]


class CadexdClient:
    """Owns one cadexd child for one project root."""

    def __init__(
        self,
        project_root: str | Path,
        *,
        budgets: Mapping[str, Any] | None = None,
        command: list[str] | None = None,
    ) -> None:
        self.project_root = str(project_root)
        self._budgets = dict(budgets or {})
        self._command = list(command) if command is not None else None
        self._process: subprocess.Popen | None = None
        self._frames: queue.Queue = queue.Queue()
        self._reader: threading.Thread | None = None
        self._sequence = itertools.count(1)
        self._request_lock = threading.Lock()
        self._open = False

    # -- lifecycle -------------------------------------------------------

    def _spawn(self) -> None:
        command = self._command if self._command is not None else _default_command()
        self._frames = queue.Queue()
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._reader = threading.Thread(
            target=self._read_frames, args=(self._process, self._frames),
            name="cadexd-client-reader", daemon=True,
        )
        self._reader.start()
        ready = self._next_frame(timeout=_READY_TIMEOUT_SECONDS)
        if not (
            isinstance(ready, dict)
            and isinstance(ready.get("event"), dict)
            and ready["event"].get("event") == "ready"
        ):
            self._mark_dead()
            raise RuntimeError(f"cadexd did not become ready: {ready!r}")

    @staticmethod
    def _read_frames(process: subprocess.Popen, frames: queue.Queue) -> None:
        try:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    frame = decode_frame(line)
                except Exception:
                    continue  # pre-hijack FreeCADCmd chatter
                frames.put(frame)
        finally:
            frames.put(None)  # EOF sentinel

    def _next_frame(self, *, timeout: float) -> dict[str, Any] | None:
        try:
            return self._frames.get(timeout=timeout)
        except queue.Empty:
            return {}

    def alive(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _mark_dead(self) -> None:
        process = self._process
        self._process = None
        self._open = False
        if process is not None and process.poll() is None:
            try:
                process.kill()
            except Exception:
                pass
        if process is not None:
            try:
                process.wait(timeout=10)
            except Exception:
                pass
            for stream in (process.stdin, process.stdout):
                try:
                    if stream is not None:
                        stream.close()
                except Exception:
                    pass

    def close(self) -> None:
        """Kill the child; used on document close and application exit."""

        with self._request_lock:
            process = self._process
            if process is not None and process.poll() is None:
                try:
                    process.stdin.write(
                        encode_frame(
                            {
                                "schema": PROTOCOL_SCHEMA,
                                "id": "close",
                                "op": "shutdown",
                            }
                        )
                    )
                    process.stdin.flush()
                    process.stdin.close()  # EOF doubles as the lifetime signal
                    process.wait(timeout=5)
                except Exception:
                    pass
            self._mark_dead()

    # -- requests --------------------------------------------------------

    def _send(self, request_id: str, op: str, args: Mapping[str, Any]) -> None:
        assert self._process is not None and self._process.stdin is not None
        frame = {
            "schema": PROTOCOL_SCHEMA,
            "id": request_id,
            "op": op,
            "args": dict(args),
        }
        self._process.stdin.write(encode_frame(frame))
        self._process.stdin.flush()

    def _ensure_open(self) -> dict[str, Any] | None:
        """Spawn + replay open_project when needed; envelope on failure."""

        if self.alive() and self._open:
            return None
        self._mark_dead()
        try:
            self._spawn()
        except Exception as exc:
            self._mark_dead()
            return _crash_envelope(
                "open_project",
                f"cadexd could not be started: {exc}",
                exception_type=exc.__class__.__name__,
            )
        opened = self._await_response(
            "open_project",
            {
                "project_root": self.project_root,
                **({"budgets": self._budgets} if self._budgets else {}),
            },
            cancellation_check=None,
            progress_callback=None,
            timeout=self._lifecycle_timeout(),
        )
        if not opened.get("ok"):
            self._mark_dead()
            return opened
        self._open = True
        return None

    def _lifecycle_timeout(self) -> float:
        budget = float(self._budgets.get("timeout_seconds") or 0.0)
        if budget > 0.0:
            return budget + _TIMEOUT_MARGIN_SECONDS
        return _DEFAULT_TIMEOUT_SECONDS + _TIMEOUT_MARGIN_SECONDS

    def _await_response(
        self,
        op: str,
        args: Mapping[str, Any],
        *,
        cancellation_check: Callable[[], bool] | None,
        progress_callback: Callable[[dict[str, Any]], None] | None,
        timeout: float,
    ) -> dict[str, Any]:
        request_id = f"shell-{next(self._sequence)}"
        try:
            self._send(request_id, op, args)
        except Exception as exc:
            self._mark_dead()
            return _crash_envelope(
                op,
                f"cadexd request could not be sent: {exc}",
                exception_type=exc.__class__.__name__,
            )
        deadline = time.monotonic() + timeout
        cancel_sent = False
        while True:
            frame = self._next_frame(timeout=_CANCEL_POLL_SECONDS)
            if frame is None:
                self._mark_dead()
                return _crash_envelope(
                    op, "The cadexd engine process died mid-request."
                )
            if frame:
                if isinstance(frame.get("event"), dict):
                    if progress_callback is not None:
                        progress_callback(dict(frame["event"]))
                    continue
                if frame.get("id") == request_id:
                    payload = dict(frame)
                    payload.pop("id", None)
                    return payload
                continue  # a stale response (e.g. late cancel ack)
            if (
                not cancel_sent
                and cancellation_check is not None
                and cancellation_check()
            ):
                try:
                    self._send(
                        f"shell-cancel-{next(self._sequence)}",
                        "cancel",
                        {"request_id": request_id},
                    )
                except Exception:
                    pass
                cancel_sent = True
            if time.monotonic() > deadline:
                self._mark_dead()
                return _crash_envelope(
                    op,
                    f"cadexd did not answer within {timeout:g} seconds; the "
                    "engine process was killed.",
                    timeout_seconds=timeout,
                )

    def request(
        self,
        op: str,
        args: Mapping[str, Any] | None = None,
        *,
        cancellation_check: Callable[[], bool] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Run one protocol request; returns the response payload."""

        if timeout is None:
            timeout = (
                self._lifecycle_timeout()
                if op in MODELING_OPS
                else _DEFAULT_TIMEOUT_SECONDS
            )
        with self._request_lock:
            not_open = self._ensure_open()
            if not_open is not None:
                return not_open
            return self._await_response(
                op,
                dict(args or {}),
                cancellation_check=cancellation_check,
                progress_callback=progress_callback,
                timeout=timeout,
            )


# -- per-project registry ----------------------------------------------------

_clients: dict[str, CadexdClient] = {}
_clients_lock = threading.Lock()


def client_for_project(
    project_root: str | Path,
    *,
    budgets: Mapping[str, Any] | None = None,
) -> CadexdClient:
    """The lazily-spawned client owning ``project_root``'s cadexd child."""

    key = str(project_root)
    with _clients_lock:
        client = _clients.get(key)
        if client is None:
            client = CadexdClient(key, budgets=budgets)
            _clients[key] = client
        elif budgets:
            client._budgets = dict(budgets)
        return client


def close_project(project_root: str | Path) -> None:
    with _clients_lock:
        client = _clients.pop(str(project_root), None)
    if client is not None:
        client.close()


def close_all() -> None:
    with _clients_lock:
        clients = list(_clients.values())
        _clients.clear()
    for client in clients:
        client.close()


atexit.register(close_all)
