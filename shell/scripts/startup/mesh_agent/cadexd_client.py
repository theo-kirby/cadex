# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Blender-side client for the cadexd geometry service (cadex Phase 6).

cadexd is the headless xscript engine from the cadex repository: one
``FreeCADCmd`` child per open project speaking newline-delimited JSON over
stdio (schema ``cadex-cadexd-v1``). This module owns that child process —
spawn, ready banner, serialized request/response with progress events,
cancellation, crash envelopes — and nothing else. It never imports ``bpy``,
so it is testable outside Blender, and it never imports cadex code: the
process boundary is the integration contract (and the LGPL/GPL seam).

Requests block the calling thread (Blender's main thread, matching the Qt
shell's behavior); progress events invoke ``progress_callback`` inline.
A child that dies mid-request yields a ``CADEXD_CRASHED`` envelope and the
next request respawns the child and replays ``open_project``.
"""

import itertools
import json
import os
import queue
import shutil
import subprocess
import threading
import time

PROTOCOL_SCHEMA = "cadex-cadexd-v1"
MAX_FRAME_BYTES = 8 * 1024 * 1024

CADEXD_CRASHED = "CADEXD_CRASHED"
CADEXD_UNAVAILABLE = "CADEXD_UNAVAILABLE"

#: Ops that run the modeling pipeline and deserve the long budget.
#: ``put_asset`` copies a file the user picked into the project store; a
#: hundred-megabyte STL is not a 60-second read, and the engine serializes it
#: against an in-flight rebuild the same way.
#:
#: ``preview_params`` is deliberately **not** here. It writes nothing, and
#: queueing behind an in-flight modeling request is exactly what a drag's
#: preview should do when it meets the ``set_params`` that settles it
#: (ADR-055). Adding it would make the two refuse each other instead.
#: ``export_printable`` tessellates and writes one STL per ticked part, which
#: is minutes of work on a large assembly and emphatically not a 60-second
#: read. Ticking a part is not here and needs no tier: it writes the scene
#: and never reaches the engine at all (cadex ADR-158).
MODELING_OPS = frozenset(
    {"open_project", "write_script", "edit_script", "set_params", "rebuild",
     "put_asset", "link_part", "put_blueprint", "export_printable"}
)

_READY_TIMEOUT_SECONDS = 120.0
_READ_TIMEOUT_SECONDS = 60.0
_MODELING_TIMEOUT_SECONDS = 300.0
_POLL_SECONDS = 0.05

#: ``preview_params`` is a read op, but not a 60-second one: it exists to be
#: watched at a frame rate, and the engine already kills its resident worker
#: at 5 s (ADR-055). Waiting a minute for an optimisation whose fallback is
#: already debounced behind it would stall the drag it is meant to smooth.
_PREVIEW_TIMEOUT_SECONDS = 5.0


def _failure(op, code, message, **observed):
    envelope = {
        "ok": False,
        "tool": "cadexd." + op,
        "failure_code": code,
        "error": message,
    }
    if observed:
        envelope["observed"] = dict(observed)
    return envelope


#: The engine payload's discovery manifest (cadex ADR-020). Finding this
#: file is the whole of bundled discovery: it names the binary and the
#: module directory with manifest-relative, forward-slash paths, so no
#: platform layout has to be guessed at.
ENGINE_MANIFEST_NAME = "cadex-engine.json"
ENGINE_MANIFEST_SCHEMA = "cadex-engine-v1"

#: Wire protocol this client speaks; a payload must agree.
ENGINE_PROTOCOL = PROTOCOL_SCHEMA


def _executable(path):
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def read_engine_manifest(directory):
    """Parse ``<directory>/cadex-engine.json``.

    Returns ``(freecadcmd, module_dir)`` when the manifest is valid, this
    client speaks its protocol, and both paths exist; otherwise None. A
    manifest we do not recognise is refused rather than guessed at.
    """
    path = os.path.join(str(directory or ""), ENGINE_MANIFEST_NAME)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(manifest, dict):
        return None
    if manifest.get("schema") != ENGINE_MANIFEST_SCHEMA:
        return None
    if manifest.get("protocol") != ENGINE_PROTOCOL:
        return None
    base = os.path.dirname(os.path.abspath(path))
    freecadcmd = manifest.get("freecadcmd")
    module_dir = manifest.get("module_dir")
    if not isinstance(freecadcmd, str) or not isinstance(module_dir, str):
        return None
    freecadcmd = os.path.join(base, *freecadcmd.split("/"))
    module_dir = os.path.join(base, *module_dir.split("/"))
    if not _executable(freecadcmd) or not os.path.isdir(module_dir):
        return None
    return freecadcmd, module_dir


def engine_version(bundle_roots=()):
    """The bundled engine payload's ``version`` string, or ``""``.

    The manifest has always carried it (``build_engine_payload.sh`` writes
    CMake's PACKAGE_VERSION in) and :func:`read_engine_manifest` has always
    dropped it — that reader answers "can I run this payload", and its
    signature is pinned by two call sites and their tests, so the version
    gets its own small reader (ADR-151: the blueprint sheet's title block).
    Deliberately tolerant where the launcher is strict: a sheet's title is
    worth printing even off a payload this client would refuse to run.
    """
    override = os.path.expanduser(os.environ.get("MESH_CADEX_ENGINE", ""))
    for root in ([override] if override else []) + [str(r) for r in bundle_roots]:
        if not root:
            continue
        path = os.path.join(root, ENGINE_MANIFEST_NAME)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(manifest, dict):
            version = manifest.get("version")
            if isinstance(version, str) and version:
                return version
    return ""


def find_bundled_engine(bundle_roots=()):
    """First valid engine payload among ``bundle_roots``, or None.

    ``MESH_CADEX_ENGINE`` takes precedence, so a developer can point a
    shipped build at a local engine tree with one environment variable.
    """
    override = os.path.expanduser(os.environ.get("MESH_CADEX_ENGINE", ""))
    for root in ([override] if override else []) + [str(r) for r in bundle_roots]:
        if not root:
            continue
        found = read_engine_manifest(root)
        if found is not None:
            return found
    return None


def find_freecadcmd(explicit="", bundle_roots=()):
    """Locate the FreeCADCmd binary hosting cadexd, or None.

    Order (cadex ADR-020): explicit argument (add-on preference),
    ``MESH_FREECADCMD``, the bundled engine payload's manifest, PATH.
    """
    for candidate in (explicit, os.environ.get("MESH_FREECADCMD", "")):
        candidate = os.path.expanduser(candidate or "")
        if _executable(candidate):
            return candidate
    bundled = find_bundled_engine(bundle_roots)
    if bundled is not None:
        return bundled[0]
    # Installed trees vary in case: FreeCAD's own build produces FreeCADCmd,
    # conda-forge and most Linux distributions ship freecadcmd.
    for name in ("FreeCADCmd", "freecadcmd"):
        found = shutil.which(name)
        if found:
            return found
    return None


def cadexd_module_dir(freecadcmd, bundle_roots=()):
    """Directory holding cadexd.py, derived from the FreeCADCmd location.

    ``MESH_CADEXD_MODULE`` overrides. When the binary came from a bundled
    payload its manifest answers directly. Otherwise both installed layouts
    are tried: ``<prefix>/Mod/cadex`` beside ``<prefix>/bin/FreeCADCmd``
    (macOS/Linux) and ``<dir>/../Mod/cadex`` for the Windows root layout,
    where the binary sits at the install root rather than under ``bin``.
    """
    override = os.path.expanduser(os.environ.get("MESH_CADEXD_MODULE", ""))
    if override and os.path.isdir(override):
        return override
    bundled = find_bundled_engine(bundle_roots)
    if bundled is not None and os.path.abspath(bundled[0]) == os.path.abspath(
            str(freecadcmd or "")):
        return bundled[1]
    binary_dir = os.path.dirname(os.path.abspath(str(freecadcmd or "")))
    for prefix in (os.path.dirname(binary_dir), binary_dir):
        candidate = os.path.join(prefix, "Mod", "cadex")
        if os.path.isdir(candidate):
            return candidate
    return None


def preflight(explicit="", bundle_roots=()):
    """Is a usable cadex engine reachable? Returns ``(ok, reason, remedy)``.

    ``reason`` states what is wrong in one sentence and ``remedy`` what to
    do about it; both are empty when ok. The three surfaces that report
    engine availability -- the preferences panel, the chat panel in Cadex
    mode, and the first cadex tool call -- all phrase themselves from this,
    so a user never sees two different accounts of the same problem.
    """
    freecadcmd = find_freecadcmd(explicit, bundle_roots)
    if not freecadcmd:
        return (False,
                "The cadex engine (FreeCADCmd) could not be found.",
                "Cadex normally uses the engine bundled with it; to use a "
                "different build, set the engine path in Settings > AI "
                "or the MESH_FREECADCMD environment variable.")
    module_dir = cadexd_module_dir(freecadcmd, bundle_roots)
    if not module_dir:
        return (False,
                "Found the engine binary at {:s}, but not the cadexd Python "
                "module beside it.".format(freecadcmd),
                "Expected Mod/cadex next to the binary's directory or its "
                "parent. Point MESH_CADEXD_MODULE at the module directory, "
                "or choose a complete cadex engine build.")
    return True, "", ""


def resolve_engine(explicit="", bundle_roots=()):
    """``(freecadcmd, module_dir)`` for a usable engine, or ``(None, None)``."""
    freecadcmd = find_freecadcmd(explicit, bundle_roots)
    if not freecadcmd:
        return None, None
    return freecadcmd, cadexd_module_dir(freecadcmd, bundle_roots)


def default_command(freecadcmd, module_dir, blender_executable=""):
    bootstrap = (
        "import sys; sys.path.insert(0, {!r}); "
        "import cadexd; raise SystemExit(cadexd.main())"
    ).format(module_dir)
    if blender_executable:
        bootstrap = ("import os; os.environ['CADEX_BLENDER_EXECUTABLE'] = {!r}; "
                     .format(os.path.abspath(str(blender_executable)))) + bootstrap
    return [freecadcmd, "-c", bootstrap]


class CadexdClient:
    """Owns one cadexd child for one project root."""

    def __init__(self, project_root, command, budgets=None):
        self.project_root = str(project_root)
        self.command = list(command)
        self.budgets = dict(budgets or {})
        self._process = None
        self._frames = queue.Queue()
        self._sequence = itertools.count(1)
        self._lock = threading.Lock()
        self._open = False
        #: Progress events of the most recent request (for status display).
        self.last_events = []

    # -- lifecycle ---------------------------------------------------------

    def alive(self):
        return self._process is not None and self._process.poll() is None

    def _spawn(self):
        self._frames = queue.Queue()
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        reader = threading.Thread(
            target=self._read_frames, args=(self._process, self._frames),
            name="cadexd-reader", daemon=True)
        reader.start()
        deadline = time.monotonic() + _READY_TIMEOUT_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._mark_dead()
                raise RuntimeError("cadexd did not emit its ready banner in time")
            try:
                frame = self._frames.get(timeout=min(remaining, 1.0))
            except queue.Empty:
                continue
            if frame is None:
                self._mark_dead()
                raise RuntimeError("cadexd exited before becoming ready")
            event = frame.get("event")
            if isinstance(event, dict) and event.get("event") == "ready":
                return

    @staticmethod
    def _read_frames(process, frames):
        try:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    frame = json.loads(line.decode("utf-8"))
                except ValueError:
                    continue  # pre-hijack FreeCADCmd chatter
                if isinstance(frame, dict):
                    frames.put(frame)
        finally:
            frames.put(None)  # EOF sentinel

    def _mark_dead(self):
        process = self._process
        self._process = None
        self._open = False
        if process is not None:
            if process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass
            try:
                process.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                pass
            for stream in (process.stdin, process.stdout):
                try:
                    if stream is not None:
                        stream.close()
                except OSError:
                    pass

    def close(self):
        with self._lock:
            process = self._process
            if process is not None and process.poll() is None:
                try:
                    self._send("close", "shutdown", {})
                    process.stdin.close()  # EOF doubles as the lifetime signal
                    process.wait(timeout=5)
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    pass
            self._mark_dead()

    # -- requests ----------------------------------------------------------

    def _send(self, request_id, op, args):
        frame = {
            "schema": PROTOCOL_SCHEMA,
            "id": request_id,
            "op": op,
            "args": dict(args),
        }
        data = json.dumps(frame, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
        if len(data) > MAX_FRAME_BYTES:
            raise ValueError("request frame exceeds the 8 MB protocol cap")
        self._process.stdin.write(data + b"\n")
        self._process.stdin.flush()

    def _default_timeout(self, op):
        if op in MODELING_OPS:
            budget = float(self.budgets.get("timeout_seconds") or 0.0)
            return budget + 60.0 if budget > 0 else _MODELING_TIMEOUT_SECONDS
        if op == "preview_params":
            return _PREVIEW_TIMEOUT_SECONDS
        return _READ_TIMEOUT_SECONDS

    def _await_response(self, op, args, timeout, progress_callback,
                        cancellation_check):
        request_id = "mesh-{:d}".format(next(self._sequence))
        try:
            self._send(request_id, op, args)
        except (OSError, ValueError) as exc:
            self._mark_dead()
            return _failure(op, CADEXD_CRASHED,
                            "cadexd request could not be sent: {!s}".format(exc))
        deadline = time.monotonic() + timeout
        cancel_sent = False
        while True:
            try:
                frame = self._frames.get(timeout=_POLL_SECONDS)
            except queue.Empty:
                frame = {}
            if frame is None:
                self._mark_dead()
                return _failure(op, CADEXD_CRASHED,
                                "The cadexd engine process died mid-request.")
            if frame:
                event = frame.get("event")
                if isinstance(event, dict):
                    self.last_events.append(event)
                    if progress_callback is not None:
                        try:
                            progress_callback(dict(event))
                        except Exception:
                            pass
                    continue
                if frame.get("id") == request_id:
                    payload = dict(frame)
                    payload.pop("id", None)
                    return payload
                continue  # stale frame (e.g. late cancel ack)
            if (not cancel_sent and cancellation_check is not None
                    and cancellation_check()):
                try:
                    self._send("mesh-cancel-{:d}".format(next(self._sequence)),
                               "cancel", {"request_id": request_id})
                except (OSError, ValueError):
                    pass
                cancel_sent = True
            if time.monotonic() > deadline:
                self._mark_dead()
                return _failure(
                    op, CADEXD_CRASHED,
                    "cadexd did not answer within {:g} seconds; the engine "
                    "process was killed.".format(timeout),
                    timeout_seconds=timeout)

    def _start_child(self):
        """Spawn a fresh child. Returns a failure payload, or None."""
        self._mark_dead()
        try:
            self._spawn()
        except (OSError, RuntimeError) as exc:
            self._mark_dead()
            return _failure("open_project", CADEXD_UNAVAILABLE,
                            "cadexd could not be started: {!s}".format(exc),
                            command=self.command[0])
        return None

    def _ensure_open(self, progress_callback):
        if self.alive() and self._open:
            return None
        unavailable = self._start_child()
        if unavailable is not None:
            return unavailable
        args = {"project_root": self.project_root}
        if self.budgets:
            args["budgets"] = self.budgets
        opened = self._await_response(
            "open_project", args, self._default_timeout("open_project"),
            progress_callback, None)
        if opened.get("ok") is not True:
            self._mark_dead()
            return opened
        self._open = True
        self.open_payload = opened
        return None

    def _open_directly(self, args, timeout, progress_callback):
        """Serve a caller's own ``open_project`` — do not replay one first.

        Routing it through :meth:`_ensure_open` would send a *different*
        open first (this class builds its own args, so ``restore`` always
        defaults to true) and return that one's answer. The caller's
        arguments would never reach the engine, which is how the one escape
        from a failed restore -- opening with ``restore: False`` -- was
        unreachable in practice (ADR-044). It also sent every open twice.
        """
        if not self.alive():
            unavailable = self._start_child()
            if unavailable is not None:
                return unavailable
        self._open = False
        opened = self._await_response(
            "open_project", dict(args or {}), timeout, progress_callback, None)
        if opened.get("ok") is not True:
            self._mark_dead()
            return opened
        self._open = True
        self.open_payload = opened
        return opened

    def request(self, op, args=None, timeout=None, progress_callback=None,
                cancellation_check=None):
        """Run one protocol request; returns the response payload dict."""
        if timeout is None:
            timeout = self._default_timeout(op)
        with self._lock:
            self.last_events = []
            if op == "open_project":
                return self._open_directly(args, timeout, progress_callback)
            not_open = self._ensure_open(progress_callback)
            if not_open is not None:
                return not_open
            return self._await_response(op, dict(args or {}), timeout,
                                        progress_callback, cancellation_check)


# -- per-project registry ----------------------------------------------------

_clients = {}
_clients_lock = threading.Lock()


def client_for(project_root, command, budgets=None):
    """The client owning ``project_root``'s cadexd child (spawned lazily).

    Budgets are part of the reuse identity, not just the constructor: they
    are sent once, in ``open_project``, so a child opened with the old
    budgets would keep them for its whole life and a preference change
    would silently do nothing. A change respawns.
    """
    key = os.path.abspath(str(project_root))
    wanted = dict(budgets or {})
    with _clients_lock:
        client = _clients.get(key)
        if (client is None or client.command != list(command)
                or client.budgets != wanted):
            if client is not None:
                client.close()
            client = CadexdClient(key, command, budgets=wanted)
            _clients[key] = client
        return client


def close_all():
    with _clients_lock:
        clients = list(_clients.values())
        _clients.clear()
    for client in clients:
        client.close()


import atexit  # noqa: E402  (kept beside its sole use)

atexit.register(close_all)
