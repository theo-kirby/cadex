# SPDX-License-Identifier: LGPL-2.1-or-later

"""cadexd lifecycle CI (Phase 5.3, ctest ``CadexdLifecycle``).

Drives a real cadexd child (FreeCADCmd) over the cadex-cadexd-v1 stdio
protocol: open → write_script (with display) → set_params → inspect →
resolve_pin → kill -9 → respawn → restore digest equality → explicit
rebuild → cancel a slow script mid-run → server stays serviceable →
shutdown. Skipped when no FreeCADCmd binary is available.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]


def _packaged_engine():
    """Resolve a packaged engine payload from ``CADEX_ENGINE_ROOT``.

    Set by ctest ``CadexEnginePayloadSmoke`` (ADR-023) so this same test
    runs against the *shipped* tree -- reading its manifest exactly as the
    Blender shell does, which is strictly stronger than running it against
    a build directory that happens to be laid out correctly.
    """
    root = os.environ.get("CADEX_ENGINE_ROOT", "").strip()
    if not root:
        return None, None
    manifest_path = Path(root) / "cadex-engine.json"
    if not manifest_path.is_file():
        raise AssertionError(
            f"CADEX_ENGINE_ROOT={root!r} has no cadex-engine.json; the "
            "payload's manifest is its discovery contract (ADR-020)."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest.get("schema") == "cadex-engine-v1", manifest
    assert manifest.get("protocol") == SCHEMA, manifest
    base = manifest_path.parent
    binary = base.joinpath(*str(manifest["freecadcmd"]).split("/"))
    module_dir = base.joinpath(*str(manifest["module_dir"]).split("/"))
    assert binary.is_file(), binary
    assert module_dir.is_dir(), module_dir
    return binary, module_dir


SCHEMA = "cadex-cadexd-v1"

_PACKAGED_BINARY, _PACKAGED_MODULE_DIR = _packaged_engine()
CADEX_ROOT = _PACKAGED_MODULE_DIR or Path(__file__).resolve().parent.parent
_FREECADCMD_CANDIDATES = (
    REPO_ROOT / ".pixi" / "envs" / "default" / "bin" / "FreeCADCmd",
    REPO_ROOT / "build" / "release" / "bin" / "FreeCADCmd",
)
FREECADCMD = _PACKAGED_BINARY or next(
    (candidate for candidate in _FREECADCMD_CANDIDATES if candidate.is_file()), None
)

def _validate_response(op: str, frame: dict) -> list[str]:
    """Shape-check one response against the engine under test.

    ``CadexdProtocol`` is loaded from ``CADEX_ROOT``, so when this test runs
    against a *packaged* payload it validates against that payload's own
    contract rather than the source tree's (ADR-023).
    """

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_cadexd_protocol_under_test", CADEX_ROOT / "CadexdProtocol.py"
    )
    assert spec and spec.loader, CADEX_ROOT
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_response(op, frame)


MIXED_SCRIPT = """
p = params(width=num(30, unit="mm", min=10, max=90, step=1))
plate = part.box(p.width, 18, 4)
base = assembly.component(plate, grounded=True)
top = assembly.component(plate, placement=[0, 0, 4])
asm = assembly.assembly([base, top])
diag = assembly.solve(asm)
skin = mesh.from_shape(plate, linear_deflection=0.5)
result = {"plate": plate, "base": base, "top": top, "asm": asm,
          "diag": diag, "skin": skin}
"""

SLOW_SCRIPT = """
blobs = [part.sphere(5.0, center=[i * 3.0, 0.0, 0.0]) for i in range(60)]
result = {"blob": part.fuse(blobs)}
"""


class _CadexdClient:
    """Minimal test client: one frame per line, events collected aside."""

    def __init__(self, process: subprocess.Popen) -> None:
        self.process = process
        self.events: list[dict] = []
        self._responses: dict[str, dict] = {}
        self._sequence = 0

    def _read_frame(self, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError("No cadexd frame within the timeout.")
            line = self.process.stdout.readline()
            if not line:
                raise EOFError("cadexd closed its protocol stream.")
            line = line.strip()
            if not line:
                continue
            try:
                frame = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                # Anything FreeCADCmd printed before the fd hijack.
                continue
            if isinstance(frame, dict):
                return frame

    def wait_ready(self, timeout: float = 120.0) -> dict:
        frame = self._read_frame(timeout)
        assert frame.get("event", {}).get("event") == "ready", frame
        return frame["event"]

    def send(self, op: str, args: dict | None = None) -> str:
        self._sequence += 1
        request_id = f"t{self._sequence}"
        frame = {"schema": SCHEMA, "id": request_id, "op": op}
        if args is not None:
            frame["args"] = args
        data = json.dumps(frame).encode("utf-8") + b"\n"
        self.process.stdin.write(data)
        self.process.stdin.flush()
        return request_id

    def wait_response(self, request_id: str, timeout: float = 300.0) -> dict:
        if request_id in self._responses:
            return self._responses.pop(request_id)
        deadline = time.monotonic() + timeout
        while True:
            frame = self._read_frame(max(0.1, deadline - time.monotonic()))
            if "event" in frame:
                self.events.append(frame)
                continue
            if frame.get("id") == request_id:
                return frame
            self._responses[str(frame.get("id"))] = frame

    def request(self, op: str, args: dict | None = None, timeout: float = 300.0) -> dict:
        """Send one request and check the reply against the pinned shape.

        Checking here rather than in each assertion means every op this
        lifecycle already drives also gates the response contract, and a
        fixture that has drifted from the running engine fails against the
        engine rather than against itself (Phase 9, ADR-025).
        """

        frame = self.wait_response(self.send(op, args), timeout)
        problems = _validate_response(op, frame)
        assert not problems, (
            f"cadexd {op} response violates CadexdProtocol.OP_RESPONSE_SPECS:\n  "
            + "\n  ".join(problems)
            + "\nIf the contract genuinely moved, update OP_RESPONSE_SPECS, "
            "the response table in docs/INTEGRATION.md, the golden fixture in "
            "cadex_tests/response_schemas/, and the Blender shell."
        )
        return frame

    def wait_event(self, name: str, request_id: str, timeout: float = 120.0) -> dict:
        for frame in self.events:
            if (
                frame.get("id") == request_id
                and frame.get("event", {}).get("event") == name
            ):
                return frame
        deadline = time.monotonic() + timeout
        while True:
            frame = self._read_frame(max(0.1, deadline - time.monotonic()))
            if "event" not in frame:
                self._responses[str(frame.get("id"))] = frame
                continue
            self.events.append(frame)
            if (
                frame.get("id") == request_id
                and frame.get("event", {}).get("event") == name
            ):
                return frame


def _spawn_cadexd() -> _CadexdClient:
    command = [
        str(FREECADCMD),
        "-c",
        (
            f"import sys; sys.path.insert(0, {str(CADEX_ROOT)!r}); "
            "import cadexd; raise SystemExit(cadexd.main())"
        ),
    ]
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "PYTHONHASHSEED": "0"},
    )
    client = _CadexdClient(process)
    client.wait_ready()
    return client


def _stop(client: _CadexdClient | None) -> None:
    if client is None:
        return
    process = client.process
    if process.poll() is None:
        process.kill()
    process.wait(timeout=30)
    for stream in (process.stdin, process.stdout):
        try:
            stream.close()
        except Exception:
            pass


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_lifecycle_end_to_end() -> None:
    root = Path(tempfile.mkdtemp(prefix="cadexd-lifecycle-ci-"))
    client = respawned = None
    try:
        client = _spawn_cadexd()

        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        assert opened["restore"] == {"performed": False}
        assert opened["script"]["script_present"] is False

        # describe_api serves the authoring contract through the protocol.
        api = client.request("describe_api")
        assert api["ok"] is True and api["domain"] == "project"

        # write_script with display: accept payload + display block.
        written = client.request(
            "write_script",
            {
                "source": MIXED_SCRIPT,
                "expected_revision": "",
                "display": {"quality": "standard"},
            },
        )
        assert written["ok"] is True, written
        accepted_digest = written["digest"]
        assert written["model_state"]["status"] == "accepted"
        display = written["display"]
        plate = display["plate"]
        assert plate["artifact_kind"] == "brep"
        assert Path(plate["artifact_path"]).is_file()
        assert Path(plate["tessellation"]["artifact_path"]).is_file()
        assert Path(plate["tessellation"]["sidecar_path"]).is_file()
        assert display["skin"]["artifact_kind"] == "mesh"
        assert display["top"]["placement"] is not None
        assert display["diag"]["artifact_kind"] is None

        # set_params: revision-guarded value patch.
        stale = client.request(
            "set_params", {"values": {"width": 42}, "expected_revision": "bogus"}
        )
        assert stale["ok"] is False
        assert stale["failure_code"] == "STALE_PROGRAM_REVISION"
        patched = client.request(
            "set_params",
            {
                "values": {"width": 42},
                "expected_revision": written["model_state"][
                    "next_write_expected_revision"
                ],
            },
        )
        assert patched["ok"] is True, patched
        patched_digest = patched["digest"]
        assert patched_digest != accepted_digest

        # inspect: script + document scopes live off the ephemeral document.
        script_view = client.request(
            "inspect", {"scope": "script", "path": "/revisions"}
        )
        assert script_view["ok"] is True, script_view
        assert script_view["value"]["accepted_revision"] == patched["revision"]
        document_view = client.request("inspect", {"scope": "document"})
        assert document_view["ok"] is True
        assert document_view["value"]["object_count"] > 0
        selection_view = client.request("inspect", {"scope": "selection"})
        assert selection_view["failure_code"] == "CADEXD_PROTOCOL_ERROR"

        # resolve_pin against the accepted staged BREP.
        pin = client.request(
            "resolve_pin",
            {
                "output": "plate",
                "selection": {
                    "element_type": "face",
                    "geometry_type": "Plane",
                    "near_point": [21.0, 9.0, 4.0],
                    "max_distance": 0.5,
                    "expected_count": 1,
                },
            },
        )
        assert pin["ok"] is True, pin
        assert pin["subelements"], pin

        # kill -9: the shell-owned child dies without ceremony.
        client.process.send_signal(signal.SIGKILL)
        client.process.wait(timeout=30)

        # Respawn + open: the restore pass re-proves restart determinism.
        respawned = _spawn_cadexd()
        reopened = respawned.request("open_project", {"project_root": str(root)})
        assert reopened["ok"] is True, reopened
        assert reopened["restore"]["performed"] is True
        assert reopened["restore"]["matches_accepted"] is True
        assert reopened["restore"]["digest"] == patched_digest

        # Explicit rebuild reproduces the accepted digest.
        rebuilt = respawned.request("rebuild")
        assert rebuilt["ok"] is True, rebuilt
        assert rebuilt["digest"] == patched_digest

        # Cancel a slow script mid-run; the server stays serviceable.
        expected = rebuilt["model_state"]["next_write_expected_revision"]
        slow_id = respawned.send(
            "write_script",
            {"source": SLOW_SCRIPT, "expected_revision": expected},
        )
        respawned.wait_event("cadex_domain_worker_started", slow_id)
        time.sleep(1.0)
        cancel_id = respawned.send("cancel", {"request_id": slow_id})
        cancelled = respawned.wait_response(slow_id)
        assert cancelled["ok"] is False, cancelled
        assert cancelled["failure_code"] == "RUN_CANCELLED", cancelled
        ack = respawned.wait_response(cancel_id, timeout=30)
        assert ack == {"id": cancel_id, "ok": True, "cancelled": slow_id}

        # Recover with the accepted script (same output contract): the
        # server is fully serviceable and reproduces the accepted digest.
        recovered = respawned.request(
            "write_script",
            {
                "source": MIXED_SCRIPT,
                "expected_revision": cancelled["model_state"][
                    "next_write_expected_revision"
                ],
            },
        )
        assert recovered["ok"] is True, recovered
        assert recovered["digest"] == patched_digest, recovered

        # Graceful shutdown.
        done = respawned.request("shutdown", timeout=60)
        assert done["ok"] is True
        assert respawned.process.wait(timeout=60) == 0
    finally:
        _stop(client)
        _stop(respawned)
        shutil.rmtree(root, ignore_errors=True)
