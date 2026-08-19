# SPDX-License-Identifier: LGPL-2.1-or-later

"""cadexd lifecycle CI (Phase 5.3, ctest ``CadexdLifecycle``).

Drives a real cadexd child (FreeCADCmd) over the cadex-cadexd-v1 stdio
protocol: open → put_asset (and the script that imports it) → write_script
(with display) → set_params → inspect → resolve_pin → kill -9 → respawn →
restore digest equality → explicit rebuild → cancel a slow script mid-run →
server stays serviceable → shutdown. Skipped when no FreeCADCmd binary is
available.

Plus the two server-level refusals the happy path never reaches: a modeling
request colliding with one in flight (``CADEXD_BUSY``) and an open whose
restore pass cannot reproduce the accepted model (``CADEXD_RESTORE_FAILED``,
both of its shapes). Every frame here is checked against the engine under
test's own ``SERVER_FAILURE_SPEC``, which is how ADR-055 found four keys the
server sent and the spec did not declare.
"""

from __future__ import annotations

import hashlib
import json
import math
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
scan = mesh.import_file("tetra.stl")
result = {"plate": plate, "base": base, "top": top, "asm": asm,
          "diag": diag, "skin": skin, "scan": scan}
"""

SLOW_SCRIPT = """
blobs = [part.sphere(5.0, center=[i * 3.0, 0.0, 0.0]) for i in range(60)]
result = {"blob": part.fuse(blobs)}
"""

#: A jointed assembly, solved. ``swing`` is declared at [0, 0, 40] and the
#: revolute joint pulls it onto the base connector's [12, 0, 4] offset, so a
#: run that merely *doesn't crash* is still distinguishable from one where
#: the solver actually ran.
#:
#: No live test built a joint before this one, which is exactly why
#: ``assembly.joint`` could sit broken headless: Assembly/Preferences.py
#: imported FreeCADGui at module scope, so ``import Preferences`` raised in a
#: BUILD_GUI=OFF engine, JointObject's ImportError guard turned Preferences
#: into None, and solveIfAllowed died on 'NoneType' has no attribute
#: 'preferences' (ADR-047).
JOINT_SCRIPT = """
plate = part.box(40, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[12, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag}
"""

#: The jointed assembly above, exploded in two staged moves — the second
#: move reuses the component the first one lifted, which is what makes the
#: staged (cumulative) semantics of the display record observable.
EXPLODED_VIEW_SCRIPT = """
plate = part.box(40, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[12, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
boom = assembly.exploded_view(asm, [
    {"components": [swing], "transform": [0, 0, 30]},
    {"components": [swing], "transform": [20, 0, 0]},
])
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "boom": boom}
"""

#: The jointed assembly above, driven. Every script containing
#: ``assembly.simulation(...)`` failed at publication until ADR-048, because
#: the publisher read ``simulation_trace_preview`` and no code anywhere
#: wrote it. 0..1 s at a 0.05 s step is 21 frames -- enough for a middle
#: frame to be a distinct one.
SIMULATION_SCRIPT = """
plate = part.box(40, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[12, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
spin = assembly.motion(j, "2 * pi * time")
sim = assembly.simulation(asm, [spin], end_time_s=1.0, time_step_s=0.05)
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "spin": spin, "sim": sim}
"""

#: Two parameters over one jointed assembly, one of each kind. ``reach`` is a
#: joint offset: it moves a solved component and changes no geometry, so it
#: is previewable. ``width`` feeds ``part.box``, so it changes `plate`'s
#: definition and must be refused — a placement-only reply for it would be a
#: lie (ADR-055).
PREVIEW_SCRIPT = """
p = params(reach=num(12, unit="mm", min=0, max=30, step=1),
           width=num(40, unit="mm", min=10, max=90, step=1))
plate = part.box(p.width, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[p.reach, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag}
"""

#: The same mechanism as a *dynamics* run (ADR-077). No motion formula: the
#: arm has mass, the hinge axis is horizontal, and gravity does the rest.
#: The connector offsets rotate both JCS 90 degrees about X so the joint's
#: +Z -- FreeCAD's axis convention -- is horizontal; a vertical hinge under
#: vertical gravity produces no torque and would sit there looking solved.
DYNAMICS_SCRIPT = """
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
b1 = assembly.body(base, density_kg_m3=2700)
b2 = assembly.body(swing, density_kg_m3=7850)
sim = assembly.dynamics(asm, [b1, b2], end_time_s=1.0, frames_per_second=30)
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "sim": sim}
"""

#: M3's exit criterion, end to end (docs/MUJOCO.md M3, phase 6). A hinged
#: mast on a post, level to start with and hanging out over a floor slab it
#: is not jointed to. Nothing prescribes its motion and nothing but contact
#: stops it: it swings down under gravity, slaps the slab, bounces twice at
#: the restitution it was given, and settles.
#:
#: Every M3 code path is load-bearing here. Without the geoms it passes
#: through the slab; without the explicit joint exclusion it collides with
#: the post it is hinged to and never gets started; without the finer
#: solver step the bouncing contact is refused; and under MuJoCo's default
#: Euler integrator a mechanism this shape gains energy rather than losing
#: it. The slab is a separate grounded component precisely so that the
#: exclusion covers the mast and post and leaves the landing surface out.
TOPPLE_SCRIPT = """
slab = part.box(600, 400, 20)
tower = part.box(60, 60, 200)
mast = part.box(300, 40, 40)
floor = assembly.component(slab, grounded=True)
post = assembly.component(tower, placement=[40, 170, 20], grounded=True)
column = assembly.component(mast, placement=[70, 180, 200])
hinge = assembly.joint("revolute",
                       assembly.connector(post, "origin",
                                          offset={"position": [30, 30, 200],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": -90}),
                       assembly.connector(column, "origin",
                                          offset={"position": [20, 20, 20],
                                                  "axis": [1, 0, 0],
                                                  "angle_degrees": -90}))
asm = assembly.assembly([floor, post, column], [hinge])
diag = assembly.solve(asm)
sim = assembly.dynamics(asm, [
    assembly.body(floor, density_kg_m3=7850,
                  collision=assembly.collision("box", size_mm=[600, 400, 20],
                                               offset=[300, 200, 10],
                                               friction=0.9, restitution=0.3)),
    assembly.body(post, density_kg_m3=7850,
                  collision=assembly.collision("box", size_mm=[60, 60, 200],
                                               offset=[30, 30, 100], friction=0.9)),
    assembly.body(column, density_kg_m3=700,
                  collision=assembly.collision("box", size_mm=[300, 40, 40],
                                               offset=[150, 20, 20],
                                               friction=0.9, restitution=0.3)),
], end_time_s=2.5, frames_per_second=60, solver_step_s=0.0005)
result = {"slab": slab, "tower": tower, "mast": mast, "floor": floor,
          "post": post, "column": column, "hinge": hinge, "asm": asm,
          "diag": diag, "sim": sim}
"""

TETRA_STL = """solid tetra
facet normal 0 0 -1
 outer loop
  vertex 0 0 0
  vertex 4 0 0
  vertex 0 4 0
 endloop
endfacet
facet normal 0 -1 0
 outer loop
  vertex 0 0 0
  vertex 0 0 4
  vertex 4 0 0
 endloop
endfacet
facet normal -1 0 0
 outer loop
  vertex 0 0 0
  vertex 0 4 0
  vertex 0 0 4
 endloop
endfacet
facet normal 1 1 1
 outer loop
  vertex 4 0 0
  vertex 0 0 4
  vertex 0 4 0
 endloop
endfacet
endsolid tetra
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
    # Outside the project store: put_asset's whole job is getting it inside.
    incoming_dir = Path(tempfile.mkdtemp(prefix="cadexd-incoming-"))
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

        # put_asset: external geometry enters the store through the protocol,
        # never by the shell writing the store itself (ADR-043).
        incoming = incoming_dir / "Tetra.STL"
        incoming.write_text(TETRA_STL, encoding="utf-8")
        empty = client.request("inspect", {"scope": "assets"})
        assert empty["ok"] is True and empty["value"]["asset_count"] == 0
        stored = client.request(
            "put_asset", {"source_path": str(incoming), "name": "tetra.stl"}
        )
        assert stored["ok"] is True, stored
        assert stored["name"] == "tetra.stl"
        assert stored["bytes"] == len(TETRA_STL.encode("utf-8"))
        assert (root / "assets" / "tetra.stl").is_file()
        assert [item["name"] for item in stored["assets"]] == ["tetra.stl"]
        rejected = client.request(
            "put_asset", {"source_path": str(incoming), "name": "../escape.stl"}
        )
        assert rejected["ok"] is False, rejected
        assert rejected["failure_code"] == "ASSET_REJECTED", rejected
        listed = client.request("inspect", {"scope": "assets"})
        assert listed["ok"] is True, listed
        assert listed["value"]["assets"][0]["sha256"] == stored["sha256"]
        # No accepted revision yet, so output scope has nothing to serve.
        no_outputs = client.request("inspect", {"scope": "output"})
        assert no_outputs["ok"] is True and no_outputs["value"]["ok"] is False

        # write_script with display: accept payload + display block. The
        # script imports the asset put_asset just stored.
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
        assert display["scan"]["artifact_kind"] == "mesh"
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

        # output scope: the accepted revision's per-output facts, asked for
        # long after the rebuild that produced them (ADR-043).
        outputs_view = client.request("inspect", {"scope": "output"})
        assert outputs_view["ok"] is True, outputs_view
        by_name = {item["name"]: item for item in outputs_view["value"]["outputs"]}
        assert by_name["plate"]["domain"] == "part"
        assert by_name["scan"]["artifact_kind"] == "mesh"
        plate_facts = client.request(
            "inspect", {"scope": "output", "target": "plate", "path": "/facts"}
        )
        assert plate_facts["ok"] is True, plate_facts
        assert plate_facts["value"]["shape_type"] == "Solid"
        scan_facts = client.request(
            "inspect", {"scope": "output", "target": "scan", "path": "/facts/facets"}
        )
        assert scan_facts["ok"] is True and scan_facts["value"] == 4

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
        shutil.rmtree(incoming_dir, ignore_errors=True)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_solves_a_jointed_assembly() -> None:
    """A joint builds, and the solver moves the component it constrains.

    Drives a real joint through a real engine because that is the only
    thing that would have caught ADR-047: the assembly suites validate
    arguments under a stubbed FreeCAD, so they never reach the FreeCAD
    import that was broken, and nothing else in the repository built a
    joint at all.
    """

    root = Path(tempfile.mkdtemp(prefix="cadexd-joint-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script", {"source": JOINT_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, written

        display = written["display"]
        # The joint is a declared output and it published.
        assert "j" in display, sorted(display)

        # Components carry a solved placement and no geometry of their own;
        # the parts they instance carry geometry and no placement. Which is
        # why a component has to name its source: without source_output an
        # entry with no tessellation looks like nothing to draw (ADR-049).
        for component, source in (("base", "plate"), ("swing", "arm")):
            entry = display[component]
            assert entry["artifact_kind"] is None, entry
            assert isinstance(entry["placement"], list), entry
            assert len(entry["placement"]) == 16, entry
            assert entry["source_output"] == source, entry
        for shape in ("plate", "arm"):
            entry = display[shape]
            assert entry["artifact_kind"] == "brep", entry
            assert entry["placement"] is None, entry
            # Only components carry it; presence is the test.
            assert "source_output" not in entry, entry

        # The solver ran: `swing` was declared at [0, 0, 40] and the revolute
        # joint put it on the base connector's [12, 0, 4] offset instead. A
        # run that only avoided the crash would leave it where it was
        # declared, so this is the assertion that has teeth.
        translation = [round(value, 6)
                       for value in written["display"]["swing"]["placement"][3::4]]
        assert translation == [12.0, 0.0, 4.0, 1.0], translation

        grounded = [round(value, 6)
                    for value in written["display"]["base"]["placement"][3::4]]
        assert grounded == [0.0, 0.0, 0.0, 1.0], grounded

        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_serves_an_exploded_view_display_record() -> None:
    """An exploded-view output carries its display key over the wire (ADR-149).

    The engine computed staged moves, final placements and leader lines
    since the op existed, and all of it died inside the worker: the display
    entry was all-nulls and no shell code could read it. This pins the wire
    shape the shell's factor slider interpolates — the validator cannot pin
    list-element shapes, so the stage/pose/line internals are asserted here.
    """

    root = Path(tempfile.mkdtemp(prefix="cadexd-exploded-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script",
            {"source": EXPLODED_VIEW_SCRIPT, "expected_revision": ""},
        )
        assert written["ok"] is True, written
        assert _validate_response("write_script", written) == []

        display = written["display"]
        entry = display["boom"]
        record = entry["exploded_view"]
        assert isinstance(record, dict), entry
        assert set(record) == {
            "assembly_output", "bounds", "stages", "final_poses", "lines",
        }, sorted(record)
        assert record["assembly_output"] == "asm"
        assert len(record["bounds"]["center_mm"]) == 3, record["bounds"]
        assert record["bounds"]["diagonal_mm"] > 0.0, record["bounds"]

        # Only the exploded-view entry carries the key; presence is the test,
        # exactly as it is for source_output/measurement/mesh_check/stress.
        for name in ("plate", "arm", "base", "swing", "j", "asm", "diag"):
            assert "exploded_view" not in display[name], name

        # Two staged moves on one component, cumulative: the second stage's
        # pose continues from the first rather than restarting from solved.
        stages = record["stages"]
        assert [stage["move_index"] for stage in stages] == [0, 1], stages
        for stage in stages:
            assert stage["kind"] == "normal", stage
            assert stage["component_outputs"] == ["swing"], stage
            pose = stage["poses"]["swing"]
            assert len(pose["position_mm"]) == 3, pose
            assert len(pose["quaternion_xyzw"]) == 4, pose
        solved = display["swing"]["placement"]
        solved_position = [round(value, 6) for value in solved[3::4]][:3]
        first = stages[0]["poses"]["swing"]["position_mm"]
        second = stages[1]["poses"]["swing"]["position_mm"]
        assert first == pytest.approx(
            [solved_position[0], solved_position[1], solved_position[2] + 30.0]
        ), (solved_position, first)
        assert second == pytest.approx(
            [first[0] + 20.0, first[1], first[2]]
        ), (first, second)

        # Every component has a factor-1 endpoint, moved or not, and the
        # unmoved one's endpoint IS its solved placement.
        final_poses = record["final_poses"]
        assert set(final_poses) == {"base", "swing"}, sorted(final_poses)
        assert final_poses["swing"]["position_mm"] == pytest.approx(second)
        base_solved = [round(value, 6) for value in display["base"]["placement"][3::4]][:3]
        assert final_poses["base"]["position_mm"] == pytest.approx(base_solved)

        # One leader line per component reference, flattened in move order.
        lines = record["lines"]
        assert len(lines) == 2, lines
        for line in lines:
            assert set(line) == {"component_output", "start_mm", "end_mm"}, line
            assert line["component_output"] == "swing", line
            assert len(line["start_mm"]) == 3 and len(line["end_mm"]) == 3, line

        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_stores_and_serves_a_blueprint() -> None:
    """A rendered sheet enters the store over the wire and reads back (ADR-150).

    Refuse-before-accept, store, list, target, sha256 round trip. The entry
    keys are pinned here because the validator cannot pin list-element
    shapes — the exploded-view precedent.
    """

    # A real 1x1 PNG: the magic check must pass on honest bytes.
    import base64

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    root = Path(tempfile.mkdtemp(prefix="cadexd-blueprint-ci-"))
    incoming_dir = Path(tempfile.mkdtemp(prefix="cadexd-blueprint-in-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        sheet = incoming_dir / "sheet.png"
        sheet.write_bytes(png_bytes)

        # Before the first accepted revision there is nothing to document.
        refused = client.request("put_blueprint", {"source_path": str(sheet)})
        assert refused["ok"] is False, refused
        assert refused["failure_code"] == "BLUEPRINT_REJECTED", refused
        assert "no accepted revision" in str(refused.get("error")), refused

        written = client.request(
            "write_script",
            {"source": "result = {'plate': part.box(20, 10, 4)}",
             "expected_revision": ""},
        )
        assert written["ok"] is True, written
        accepted_revision = str(written["accepted_revision"])

        # ...and a non-PNG is refused by its bytes, not its suffix.
        impostor = incoming_dir / "impostor.png"
        impostor.write_bytes(b"JFIF nothing PNG about this")
        rejected = client.request(
            "put_blueprint", {"source_path": str(impostor)})
        assert rejected["ok"] is False, rejected
        assert rejected["failure_code"] == "BLUEPRINT_REJECTED", rejected

        stored = client.request(
            "put_blueprint",
            {"source_path": str(sheet), "label": "the plate, three-quarter",
             "meta": {"theme": "blueprint", "views": ["front"]}},
        )
        assert stored["ok"] is True, stored
        assert stored["revision"] == accepted_revision, stored
        assert stored["bytes"] == len(png_bytes), stored
        assert stored["sha256"] == hashlib.sha256(png_bytes).hexdigest()
        assert stored["name"] == "0001-{:s}.png".format(accepted_revision[:12])
        entry = stored["blueprints"][-1]
        # The entry keys the shell and the CLI read; a drifted key fails
        # here rather than at a user.
        assert set(entry) == {
            "ordinal", "revision", "digest", "file", "bytes", "sha256",
            "created_at", "label", "outputs", "meta",
        }, sorted(entry)
        assert entry["revision"] == accepted_revision, entry
        assert entry["outputs"] == ["plate"], entry
        assert entry["meta"] == {"theme": "blueprint", "views": ["front"]}
        stored_file = root / "blueprints" / entry["file"]
        assert stored_file.is_file()
        assert hashlib.sha256(stored_file.read_bytes()).hexdigest() == stored["sha256"]

        # inspect scope=blueprint: the listing, then the sheet's store path.
        listing = client.request("inspect", {"scope": "blueprint"})
        assert listing["ok"] is True, listing
        assert listing["value"]["blueprint_count"] == 1, listing
        one = client.request(
            "inspect", {"scope": "blueprint", "target": "1"})
        assert one["ok"] is True, one
        served_path = one["value"]["path"]
        # The engine serves the sheet resolved (the containment check needs
        # it); on macOS that unfolds /var into /private/var.
        assert Path(served_path) == stored_file.resolve(), one
        assert one["value"]["blueprint"]["sha256"] == stored["sha256"], one
        missing = client.request(
            "inspect", {"scope": "blueprint", "target": "no-such"})
        assert missing["ok"] is True and missing["value"]["ok"] is False, missing

        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(incoming_dir, ignore_errors=True)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_publishes_a_simulation() -> None:
    """A driven assembly publishes, and retains a readable trace.

    The publisher has always demanded ``simulation_trace_preview`` and the
    worker never emitted it, so this failed for every simulation script ever
    written (ADR-048). Nothing caught it because no live test ran one.

    Also the shell's contract for playback: the trace is a real file on a
    path the response hands out, and its frames carry the times and the
    per-component placements a bake needs.
    """

    root = Path(tempfile.mkdtemp(prefix="cadexd-simulation-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script", {"source": SIMULATION_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, written

        entry = written["display"]["sim"]
        assert entry["artifact_kind"] == "assembly_simulation_json", entry

        trace = json.loads(
            Path(entry["artifact_path"]).read_text(encoding="utf-8")
        )
        frames = trace["frames"]
        # 0.0 .. 1.0 inclusive at a 0.05 s step is 21 solver frames, plus
        # the input frame the solver did not produce.
        assert len(frames) == 22, len(frames)
        assert trace["parameters"]["frames_per_second"] == 30
        assert trace["parameters"]["time_step_s"] == 0.05

        # Frame 0 is the input pose and carries no time; the rest are the
        # solver's, in order. Playback keys on the time, not the index --
        # at 0.05 s and 30 fps the two disagree by 1.5x.
        assert frames[0]["frame_kind"] == "input"
        assert frames[0]["nominal_time_s"] is None
        times = [frame["nominal_time_s"] for frame in frames[1:]]
        assert times == sorted(times), times
        assert times[0] == 0.0 and times[-1] == pytest.approx(1.0)

        # Every frame poses every component, in the compact position +
        # xyzw-quaternion form the shell's bake reads (NOT a 4x4 matrix,
        # and NOT Blender's wxyz order).
        for frame in frames:
            placements = frame["component_placements"]
            assert set(placements) == {"base", "swing"}, placements
            for pose in placements.values():
                assert len(pose["position_mm"]) == 3, pose
                assert len(pose["rotation_xyzw"]) == 4, pose

        # The motion actually moved something: `swing` is driven, `base` is
        # grounded. Without this the trace could be 22 identical frames.
        def _pose(frame, name):
            pose = frame["component_placements"][name]
            return (tuple(pose["position_mm"]), tuple(pose["rotation_xyzw"]))

        assert len({_pose(frame, "swing") for frame in frames}) > 1, (
            "the driven component never moved"
        )
        assert len({_pose(frame, "base") for frame in frames}) == 1, (
            "the grounded component moved"
        )

        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_publishes_a_dynamics_run() -> None:
    """A mechanism with mass falls, through the whole pipeline (ADR-077).

    The end-to-end claim of slice M2: an ``assembly.dynamics`` script runs
    OndselSolver for the placements, MuJoCo for the motion, and publishes
    through the path ``assembly.simulation`` already used -- one artifact
    kind, one output type, no protocol change and no change in the shell.

    It is also the only place the translator meets a *real* Ondsel solve.
    The unit fixtures are composed forwards from known joint coordinates, so
    they prove the inverse against MuJoCo's kinematics but share a
    convention with the builder. Here the connector frames and the solved
    placements both come from FreeCAD, and the first solved frame has to
    reproduce those placements to the micrometre -- which is pose parity,
    on data neither half of the translator chose.
    """

    root = Path(tempfile.mkdtemp(prefix="cadexd-dynamics-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script", {"source": DYNAMICS_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, written

        entry = written["display"]["sim"]
        assert entry["artifact_kind"] == "assembly_simulation_json", entry
        trace = json.loads(Path(entry["artifact_path"]).read_text(encoding="utf-8"))
        assert trace["schema"] == "cadex-assembly-simulation-trace-v1"
        # The same schema the kinematics solver writes, with no motions.
        assert trace["motion_outputs"] == []

        frames = trace["frames"]
        # 0..1 s at 30 fps is 31 samples, plus the untimed input frame.
        assert len(frames) == 32, len(frames)
        assert frames[0]["frame_kind"] == "input"
        assert frames[0]["nominal_time_s"] is None
        # There is a solved frame AT start_time, before any stepping. Getting
        # this wrong puts the entire run one frame late and nothing errors.
        assert frames[1]["nominal_time_s"] == 0.0
        assert frames[-1]["nominal_time_s"] == pytest.approx(1.0)

        # Every component in every frame. cadex_animate skips a missing one
        # and Blender interpolates the gap, so a part that stops moving looks
        # like a physics result.
        for frame in frames:
            assert set(frame["component_placements"]) == {"base", "swing"}, frame

        # Pose parity against the real solve: FreeCAD placed the components,
        # MuJoCo reproduced them.
        for name in ("base", "swing"):
            solved = written["display"][name]["placement"]
            first = frames[1]["component_placements"][name]
            assert first["position_mm"] == pytest.approx(
                [solved[3], solved[7], solved[11]], abs=1.0e-6
            ), name
        assert frames[0]["component_placements"] == frames[1]["component_placements"]

        # It swung. Under gravity, with mass, and nothing prescribing it.
        # The arm's origin sits *on* the hinge axis, so its position never
        # moves however far it falls -- the rotation is the observable, and
        # a test written on the height would have passed on a model that did
        # nothing at all.
        turns = [
            2.0
            * math.acos(
                min(
                    1.0,
                    abs(
                        sum(
                            first * second
                            for first, second in zip(
                                frames[1]["component_placements"]["swing"][
                                    "rotation_xyzw"
                                ],
                                frame["component_placements"]["swing"][
                                    "rotation_xyzw"
                                ],
                                strict=True,
                            )
                        )
                    ),
                )
            )
            for frame in frames[1:]
        ]
        assert max(turns) > 0.5, turns
        # ...and it *accelerated* from rest rather than being placed along a
        # path: three samples in, the angle has grown as t², which is what
        # a constant torque on a mass does and what no prescribed motion in
        # this script could have produced. Measured 0.095, 0.393, 0.882 rad.
        assert turns[1] > 0.0
        assert turns[2] / turns[1] == pytest.approx(4.0, abs=0.5), turns[:4]
        assert turns[3] / turns[1] == pytest.approx(9.0, abs=1.0), turns[:4]
        # Nothing is aliased: no sample turns more than half a circle from
        # the last, which is the limit above which no de-flipping recovers
        # the orientation.
        steps = [
            abs(later - earlier)
            for earlier, later in zip(turns, turns[1:], strict=False)
        ]
        assert max(steps) < math.pi, max(steps)
        assert len({tuple(
            frame["component_placements"]["base"]["position_mm"]
        ) for frame in frames}) == 1, "the grounded component moved"

        # The evidence the model can act on: exact masses, the tree, and
        # what any closure gave up.
        dynamics = trace["dynamics"]
        assert dynamics["solver"] == "mujoco"
        assert dynamics["closures"] == []
        assert [body["component_output"] for body in dynamics["bodies"]] == [
            "base",
            "swing",
        ]
        masses = {
            item["component_output"]: item["mass_kg"]
            for item in dynamics["inertials"]
        }
        # 60x60x6 mm of aluminium and 80x8x8 mm of steel, exactly.
        assert masses["base"] == pytest.approx(2700.0 * 0.06 * 0.06 * 0.006, rel=1e-9)
        assert masses["swing"] == pytest.approx(7850.0 * 0.08 * 0.008 * 0.008, rel=1e-9)

        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


def _store_snapshot(root: Path) -> dict:
    """Every file under the project store, with its size and mtime_ns."""

    return {
        str(path.relative_to(root)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_preview_params_answers_a_pose_only_slider_over_the_protocol() -> None:
    """The resident preview worker, through the real protocol (ADR-055).

    The op is a read-only oracle in front of ``set_params``: it answers a
    pose-only parameter change with solved placements and writes nothing. The
    store snapshot is the assertion that matters — it is what makes "a
    resident process cannot affect the model" checkable rather than argued.
    """

    root = Path(tempfile.mkdtemp(prefix="cadexd-preview-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        assert client.request("open_project", {"project_root": str(root)})["ok"]
        written = client.request(
            "write_script", {"source": PREVIEW_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, written
        revision = written["model_state"]["next_write_expected_revision"]
        accepted_digest = written["digest"]
        # The accepted model puts `swing` on the declared offset.
        declared = [
            round(value, 6) for value in written["display"]["swing"]["placement"][3::4]
        ]
        assert declared == [12.0, 0.0, 4.0, 1.0], written

        before = _store_snapshot(root)

        # A pose-only slider: previewable, and the solver really ran -- the
        # revolute joint puts `swing` on the offset the parameter names.
        posed = client.request(
            "preview_params",
            {"values": {"reach": 25}, "expected_revision": revision},
            timeout=120,
        )
        assert posed["ok"] is True, posed
        assert posed["previewable"] is True, posed
        assert posed["revision"] == revision, posed
        assert set(posed["placements"]) == {"base", "swing"}, posed
        assert len(posed["placements"]["swing"]) == 16, posed
        swing = [round(value, 6) for value in posed["placements"]["swing"][3::4]]
        assert swing == [25.0, 0.0, 4.0, 1.0], posed

        # A second preview reuses the resident worker: same generation, no
        # reload, and the answer tracks the parameter.
        again = client.request(
            "preview_params",
            {"values": {"reach": 3}, "expected_revision": revision},
            timeout=120,
        )
        assert again["previewable"] is True, again
        assert [round(v, 6) for v in again["placements"]["swing"][3::4]] == [
            3.0,
            0.0,
            4.0,
            1.0,
        ], again

        # A slider that changes geometry is refused by name rather than
        # answered with a placement that would be a lie.
        shaped = client.request(
            "preview_params",
            {"values": {"width": 61}, "expected_revision": revision},
            timeout=120,
        )
        assert shaped["previewable"] is False, shaped
        assert shaped["placements"] == {}, shaped
        assert "plate" in shaped["reason"], shaped

        # A stale revision is declined, not served.
        stale = client.request(
            "preview_params",
            {"values": {"reach": 9}, "expected_revision": "bogus"},
            timeout=120,
        )
        assert stale["previewable"] is False, stale
        assert "bogus" in stale["reason"], stale

        # THE invariant: a burst of previews wrote nothing at all. Not one
        # file added, not one byte or mtime moved.
        after = _store_snapshot(root)
        assert sorted(set(after) - set(before)) == [], (before, after)
        assert [name for name in before if before[name] != after.get(name)] == []
        assert after == before

        # The accepting path still owns the model: an ordinary set_params
        # after a burst of previews reproduces exactly what it always did,
        # and the previews left no trace in the digest.
        settled = client.request(
            "set_params", {"values": {"reach": 25}, "expected_revision": revision}
        )
        assert settled["ok"] is True, settled
        assert settled["digest"] != accepted_digest, settled
        moved = [
            round(value, 6) for value in settled["display"]["swing"]["placement"][3::4]
        ]
        assert moved == swing, (settled, posed)

        # And the generation was killed by that set_params: the next preview
        # re-loads against the new working revision rather than answering
        # from the model that no longer exists.
        next_revision = settled["model_state"]["next_write_expected_revision"]
        assert next_revision != revision, settled
        reloaded = client.request(
            "preview_params",
            {"values": {"reach": 30}, "expected_revision": next_revision},
            timeout=120,
        )
        assert reloaded["previewable"] is True, reloaded
        assert [round(v, 6) for v in reloaded["placements"]["swing"][3::4]] == [
            30.0,
            0.0,
            4.0,
            1.0,
        ], reloaded

        assert client.request("shutdown", timeout=60)["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_a_second_modeling_request_is_refused_as_busy() -> None:
    """The BUSY refusal is a declared frame, and it names what it waited on.

    Nothing drove this before: the lifecycle validates every frame it
    receives, but it never *collided* two modeling requests, so the server
    sent ``busy_request_id`` where ``SERVER_FAILURE_SPEC`` declares
    ``busy_with`` and no test could tell (ADR-055). Previews collide with
    in-flight modeling by design, which is what stops this being latent.
    """

    root = Path(tempfile.mkdtemp(prefix="cadexd-busy-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        assert client.request("open_project", {"project_root": str(root)})["ok"]

        slow_id = client.send(
            "write_script", {"source": SLOW_SCRIPT, "expected_revision": ""}
        )
        client.wait_event("cadex_domain_worker_started", slow_id)

        # A modeling op is refused while one is in flight; `request` shape-checks
        # the refusal against SERVER_FAILURE_SPEC on the way through.
        busy = client.request("rebuild", timeout=30)
        assert busy["ok"] is False, busy
        assert busy["failure_code"] == "CADEXD_BUSY", busy
        assert busy["busy_with"] == slow_id, busy

        cancel_id = client.send("cancel", {"request_id": slow_id})
        cancelled = client.wait_response(slow_id)
        assert cancelled["failure_code"] == "RUN_CANCELLED", cancelled
        assert client.wait_response(cancel_id, timeout=30)["cancelled"] == slow_id
        # A read-only op was never refused, only queued — the distinction
        # `preview_params` will rely on.
        assert client.request("describe_api", timeout=60)["ok"] is True

        assert client.request("shutdown", timeout=60)["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_a_broken_store_reports_a_declared_restore_failure() -> None:
    """Both ways an open's restore pass fails, and both frames validated.

    ``CADEXD_RESTORE_FAILED`` has two shapes — ``observed`` when the store
    runs but reproduces a different digest, ``restore_failure`` when it does
    not run at all and no accepted source is left to fall back to. Neither
    key was declared, because the shell gate drives only the first and the
    engine suite drove neither (ADR-055).
    """

    root = Path(tempfile.mkdtemp(prefix="cadexd-restore-ci-"))
    client = mismatched = unrunnable = None
    try:
        client = _spawn_cadexd()
        assert client.request("open_project", {"project_root": str(root)})["ok"]
        written = client.request(
            "write_script", {"source": JOINT_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, written
        accepted_digest = written["digest"]
        assert client.request("shutdown", timeout=60)["ok"] is True
        client.process.wait(timeout=60)

        # (1) A hand edit behind the engine's back: the script still runs, and
        # reproduces a digest that is not the accepted one.
        script_path = root / "script.py"
        source = script_path.read_text(encoding="utf-8")
        script_path.write_text(
            source.replace("part.box(40, 20, 4)", "part.box(41, 20, 4)"),
            encoding="utf-8",
        )
        mismatched = _spawn_cadexd()
        refused = mismatched.request(
            "open_project", {"project_root": str(root)}, timeout=120
        )
        assert refused["ok"] is False, refused
        assert refused["failure_code"] == "CADEXD_RESTORE_FAILED", refused
        assert refused["observed"]["accepted_digest"] == accepted_digest, refused
        assert refused["observed"]["restored_digest"] != accepted_digest, refused
        assert mismatched.request("shutdown", timeout=60)["ok"] is True
        mismatched.process.wait(timeout=60)

        # (2) A store whose working source does not run *and* whose accepted
        # revision's pinned source is gone: nothing left to restore from.
        script_path.write_text(
            "raise RuntimeError('broken store')\n", encoding="utf-8"
        )
        state = json.loads((root / "script.json").read_text(encoding="utf-8"))
        pinned = root / str(state["accepted_attempt"]["staging"]) / "request.json"
        assert pinned.is_file(), pinned
        pinned.unlink()

        unrunnable = _spawn_cadexd()
        broken = unrunnable.request(
            "open_project", {"project_root": str(root)}, timeout=120
        )
        assert broken["ok"] is False, broken
        assert broken["failure_code"] == "CADEXD_RESTORE_FAILED", broken
        assert broken["restore_failure"]["ok"] is not True, broken
        assert unrunnable.request("shutdown", timeout=60)["ok"] is True
    finally:
        _stop(client)
        _stop(mismatched)
        _stop(unrunnable)
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_publishes_a_mechanism_that_topples_lands_and_stops() -> None:
    """M3's exit criterion: a thing falls over correctly (docs/MUJOCO.md M3).

    M2's dynamics gate proved a mechanism with mass can fall. Its bodies had
    no geometry at all -- ``model.ngeom == 0`` was an assertion -- so nothing
    could touch anything and nothing could stop. This is the same pipeline
    with contact in it, and the three claims in the name are three
    assertions:

    * **topples** -- the mast leaves level and swings through 40 degrees
      under gravity alone, with no motion formula anywhere in the script;
    * **lands** -- it stops descending at the angle its own geometry allows
      on a slab it is not jointed to, rather than passing through it;
    * **stops** -- and the last half second of the trace is motionless to
      the micro-degree, having bounced first, which is what says the
      restitution did something and then stopped doing it.

    A trace where the mast simply never moved would satisfy "stops" alone,
    which is why the bounce is asserted too.
    """

    root = Path(tempfile.mkdtemp(prefix="cadexd-topple-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened
        written = client.request(
            "write_script", {"source": TOPPLE_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, written

        entry = written["display"]["sim"]
        assert entry["artifact_kind"] == "assembly_simulation_json", entry
        trace = json.loads(Path(entry["artifact_path"]).read_text(encoding="utf-8"))
        assert trace["schema"] == "cadex-assembly-simulation-trace-v1"
        assert trace["motion_outputs"] == []
        dynamics = trace["dynamics"]
        assert dynamics["solver"] == "mujoco"

        # The mast is hinged to the post, so those two are excluded from
        # each other; the slab is not jointed to anything, which is what
        # leaves it available to be landed on.
        assert dynamics["contact_exclusions"] == [["column", "post"]]
        assert {entry["component_output"] for entry in dynamics["collisions"]} == {
            "floor",
            "post",
            "column",
        }

        frames = trace["frames"]
        # 0..2.5 s at 60 fps is 151 samples plus the untimed input frame.
        assert len(frames) == 152, len(frames)

        def lean(frame: dict) -> float:
            """The mast's rotation about the hinge axis, in degrees."""

            x, y, z, w = frame["component_placements"]["column"]["rotation_xyzw"]
            return math.degrees(2.0 * math.atan2(y, w))

        angles = [lean(frame) for frame in frames[1:]]

        # Topples: level at t=0, and forty degrees over by the end.
        assert angles[0] == pytest.approx(0.0, abs=1.0e-9)
        assert angles[-1] == pytest.approx(41.35, abs=1.0)

        # Lands and bounces: the lean rises to a first peak, comes back
        # measurably, and rises again. A mast that swung down and stayed
        # down would be monotonic and would fail here.
        peak = max(range(len(angles)), key=lambda index: angles[index])
        rebound = min(angles[peak:])
        assert angles[peak] - rebound > 5.0, (angles[peak], rebound)
        assert max(angles[peak:]) > rebound + 5.0

        # Stops: motionless over the last half second, to the micro-degree.
        settled = angles[-30:]
        assert max(settled) - min(settled) < 1.0e-6, settled

        # And it never went through the slab: the slab's top is at z = 20
        # and the mast's own frame sits on its underside.
        heights = [
            frame["component_placements"]["column"]["position_mm"][2]
            for frame in frames[1:]
        ]
        assert min(heights) > 20.0, min(heights)
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


#: M5's exit criterion, in the gate that counts (docs/MUJOCO.md M5). The
#: mechanism is DYNAMICS_SCRIPT's, exported rather than simulated: the point
#: of this one is the *packaged* path, so it asserts what the payload
#: produced and leaves the stock-MuJoCo comparison to
#: test_dynamics_mjcf_live, which runs against the same payload.
MJCF_SCRIPT = """
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=2700,
                  collision=assembly.collision("box", size_mm=[60, 60, 6],
                                               offset=[30, 30, 3])),
    assembly.body(swing, density_kg_m3=7850,
                  collision=assembly.collision("box", size_mm=[80, 8, 8],
                                               offset=[40, 4, 4])),
])
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "model": model}
"""


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_exports_an_mjcf_model() -> None:
    """The model leaves the building, through the packaged engine (ADR-081).

    M5's shippable capability: design a mechanism in Cadex, export MJCF with
    exact inertias. This is the ninth gate test and it exists because a
    source tree that passes proves nothing about a payload -- ADR-023's rule,
    and the one that caught the dangling ``bin/python`` in M0. What it adds
    over the unit suites is that the file was written by the engine a user
    actually runs, with mujoco resolved out of the payload's own
    environment.

    No protocol change is involved and none should appear here: the export
    arrives as an ordinary output with an ``artifact_kind`` the shell has
    never heard of, which ``cadex_hydrate`` skips for want of a
    tessellation and ``cadex_animate`` skips for want of the simulation
    kind.
    """

    root = Path(tempfile.mkdtemp(prefix="cadexd-mjcf-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script", {"source": MJCF_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, written

        entry = written["display"]["model"]
        assert entry["artifact_kind"] == "assembly_mjcf_xml", entry
        # An export is not display geometry and must not pretend to be:
        # cadex_hydrate skips any entry without a tessellation, which is
        # what keeps this invisible to a shell that was never changed.
        assert entry["tessellation"] is None
        assert entry["placement"] is None

        path = Path(entry["artifact_path"])
        raw = path.read_bytes()
        assert path.name == "model-model.xml", path.name
        text = raw.decode("utf-8")

        # One self-contained file. No STL sidecar, no asset directory, and
        # nothing outside it referenced.
        assert text.startswith('<mujoco model="cadex-assembly">')
        assert "file=" not in text
        assert list(path.parent.glob("*.stl")) == []

        # The three things that make it the model rather than a model.
        assert "<inertial " in text, "exact OCCT inertia must survive the file"
        assert '<key name="solved"' in text, "it must open at the solved pose"
        assert text.count("<geom") == 2, "collision geometry, and only that"

        # M3's solver decisions travel with it: a file that lost one would
        # integrate differently from the engine that wrote it.
        assert 'integrator="implicitfast"' in text
        assert '<flag island="disable"/>' in text

        # Exact masses, computed here rather than read out of the artifact:
        # 60x60x6 mm of aluminium and 80x8x8 mm of steel.
        for mass in (2700.0 * 0.06 * 0.06 * 0.006, 7850.0 * 0.08 * 0.008 * 0.008):
            assert f'mass="{mass:.6g}"' in text, mass

        # It published. A new output type with no publication branch would
        # have failed the accept rather than reaching this line, and the
        # native type is the one _NATIVE_TYPE_BY_OUTPUT declares.
        live = written["live_outputs"]["model"]
        assert live["domain"] == "assembly"
        assert live["output_type"] == "mjcf"
        assert live["type_id"] == "App::FeaturePython"

        # The engine verified its own output before writing it: a file that
        # reloaded as a different model, or lost its OCCT inertia to the
        # writer's six significant figures, is a DynamicsError and never an
        # artifact. Re-checked here on the payload's bytes.
        reloaded = _reload_mjcf(text)
        assert reloaded is None or reloaded == 3, reloaded

        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


TASK_SCRIPT = """
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
motor = assembly.actuator(j, kind="motor", control_nmm="120*sin(2*pi*time)",
                          torque_limit_nmm=400)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=2700),
    assembly.body(swing, density_kg_m3=7850),
], actuators=[motor], observations=[
    assembly.observation(j, "position", name="angle"),
    assembly.observation(swing, "centre_of_mass", name="com"),
    assembly.observation(motor, "actuator_force", name="effort"),
])
job = assembly.task(model, actions=[motor],
                    reward=[assembly.reward("-(com_z - 60)^2", weight=1.0e-4,
                                            label="lift"),
                            assembly.reward("abs(effort)", weight=-1.0e-6,
                                            label="control_cost")],
                    episode_seconds=1.0, control_hz=50, label="lift")
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "model": model, "job": job}
"""


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_writes_a_training_task() -> None:
    """A task leaves the building, through the packaged engine (ADR-083).

    M6's shippable capability: design a mechanism in Cadex, get a trainable
    environment out. This is the tenth gate test and it exists for ADR-023's
    reason -- a source tree that passes proves nothing about a payload, the
    rule that caught the dangling ``bin/python`` in M0. What it adds over
    the unit suites is that the bundle and the model beside it were written
    by the engine a user actually runs, with mujoco resolved out of the
    payload's own environment.

    No protocol change is involved and none should appear here: the bundle
    arrives as an ordinary output with an ``artifact_kind`` the shell has
    never heard of, which ``cadex_hydrate`` skips for want of a tessellation
    and ``cadex_animate`` skips for want of the simulation kind.
    """

    root = Path(tempfile.mkdtemp(prefix="cadexd-task-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script", {"source": TASK_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, written

        entry = written["display"]["job"]
        assert entry["artifact_kind"] == "assembly_training_task_json", entry
        assert entry["tessellation"] is None
        assert entry["placement"] is None

        path = Path(entry["artifact_path"])
        assert path.name == "job-task.json", path.name
        bundle = json.loads(path.read_text(encoding="utf-8"))
        assert bundle["schema"] == "cadex-training-task-v1"

        # The model it references is the *other* output's retained file, by
        # a relative path and a digest. Two artifacts that only mean
        # anything together, and this is what makes that checkable.
        model_path = path.parent.parent / bundle["model"]["path"]
        assert bundle["model"]["path"] == "outputs/model-model.xml"
        assert model_path.exists()
        assert bundle["model"]["sha256"] == hashlib.sha256(
            model_path.read_bytes()
        ).hexdigest()

        # The observation vector is MuJoCo's: the channels are sensors in
        # the exported file, and a component channel reads the frame the
        # assembly solver placed rather than the inertial one.
        text = model_path.read_text(encoding="utf-8")
        assert "<sensor>" in text
        assert '<jointpos joint="j" name="obs/0"' in text
        assert [
            channel
            for record in bundle["observations"]
            for channel in record["channels"]
        ] == ["angle", "com_x", "com_y", "com_z", "effort"]

        # Degrees and millimetres reach the trainer as scale factors, so
        # nothing outside this engine has to know a conversion.
        scales = {record["name"]: record["unit"] for record in bundle["observations"]}
        assert scales == {"angle": "deg", "com": "mm", "effort": "nmm"}

        # The action range came off the mechanism rather than a default.
        action = bundle["actions"][0]
        assert (action["low"], action["high"]) == (-400.0, 400.0)
        assert action["source"] == "torque_limit_nmm"
        assert action["unit"] == "nmm"

        # The episode is a whole number of solver steps per action.
        episode = bundle["episode"]
        assert episode["control_hz"] == 50
        assert episode["max_steps"] == 50
        assert episode["reset_keyframe"] == "solved"
        assert episode["solver_steps_per_action"] >= 1

        # It published, and the native type is the one
        # _NATIVE_TYPE_BY_OUTPUT declares.
        live = written["live_outputs"]["job"]
        assert live["domain"] == "assembly"
        assert live["output_type"] == "task"
        assert live["type_id"] == "App::FeaturePython"

        # The engine ran one episode from this bundle before publishing it,
        # so a spec that could not execute never became an artifact.
        # Re-checked here on the payload's own bytes.
        assert _run_task_episode(bundle, model_path) in (None, 50)

        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


def _run_task_episode(bundle: dict, model_path: Path) -> int | None:
    """Steps a stock reload runs, or ``None`` where mujoco is absent.

    Same bonus-check status as :func:`_reload_mjcf` and for the same reason:
    this module is the packaged gate and runs wherever ``FreeCADCmd`` is,
    which is not necessarily where the test environment has ``mujoco``. The
    claim itself is in ``test_dynamics_task_live``.
    """

    try:
        import mujoco
    except Exception:
        return None
    model = mujoco.MjModel.from_xml_string(
        model_path.read_text(encoding="utf-8")
    )
    data = mujoco.MjData(model)
    key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "solved")
    mujoco.mj_resetDataKeyframe(model, data, key)
    episode = bundle["episode"]
    for _ in range(int(episode["max_steps"])):
        for _ in range(int(episode["solver_steps_per_action"])):
            mujoco.mj_step(model, data)
    assert len(data.sensordata) == sum(
        int(record["dim"]) for record in bundle["observations"]
    )
    return int(episode["max_steps"])


def _reload_mjcf(text: str) -> int | None:
    """Body count after a stock reload, or ``None`` where mujoco is absent.

    This module is the packaged gate and runs wherever ``FreeCADCmd`` is,
    which is not necessarily where the test environment has ``mujoco``. The
    engine that wrote the file has it by construction -- the payload build
    hard-fails without it -- so the reload here is a bonus check rather than
    the claim, and the claim itself is in ``test_dynamics_mjcf_live``.
    """

    try:
        import mujoco
    except Exception:
        return None
    return int(mujoco.MjModel.from_xml_string(text).nbody)


#: The M7 script: the M6 task, plus the policy declared against it. The
#: digest is substituted once the weights exist, which is the real authoring
#: order -- train, store, paste the digest ``put_asset`` reported.
POLICY_SCRIPT = TASK_SCRIPT.replace(
    'result = {"plate"',
    """gait = assembly.policy(job, weights="walk.cxpolicy",
                       sha256="__SHA256__", label="gait")
result = {"gait": gait, "plate\"""",
)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_verifies_a_trained_policy_and_ships_no_trainer() -> None:
    """A policy comes home through the packaged engine (ADR-084).

    M7's shippable capability, and the eleventh gate test. It exists for
    ADR-023's reason -- a source tree that passes proves nothing about a
    payload, the rule that caught the dangling ``bin/python`` in M0 -- and
    what it adds over the unit suites is that the weights were stored,
    staged, decoded and verified by the engine a user actually runs.

    It also asserts the **negative**, which is the half that would otherwise
    rot silently: **no jax and no mjx anywhere in the staged payload.**
    Training is offboard by design (ADR-075), the engine verifies a policy
    and never produces one, and the day that stops being true the payload
    grows a machine-learning framework without anybody deciding to.

    No protocol change is involved and none should appear here: the weights
    arrive through ``put_asset``, which performs no suffix check of its own,
    and the receipt is an ordinary output with an ``artifact_kind`` the
    shell has never heard of.
    """

    import dynamics_policy_fixtures as pf

    root = Path(tempfile.mkdtemp(prefix="cadexd-policy-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script", {"source": TASK_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, written
        revision = str(written["revision"])
        bundle_path = Path(written["display"]["job"]["artifact_path"])
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

        # The container is built against the bundle the *payload* wrote, so
        # the digests being checked are the ones it really produced.
        container = pf.policy_container(
            {"bundle": bundle,
             "task_sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest()},
            normalise=True,
        )
        weights = root.parent / "walk.cxpolicy"
        weights.write_bytes(container["blob"])

        stored = client.request(
            "put_asset", {"source_path": str(weights), "name": "walk.cxpolicy"}
        )
        assert stored["ok"] is True, stored
        assert stored["sha256"] == container["sha256"]

        written = client.request(
            "write_script",
            {"source": POLICY_SCRIPT.replace("__SHA256__", container["sha256"]),
             "expected_revision": revision},
        )
        assert written["ok"] is True, json.dumps(written)[:4000]

        entry = written["display"]["gait"]
        assert entry["artifact_kind"] == "assembly_policy_receipt_json", entry
        assert entry["tessellation"] is None
        assert entry["placement"] is None

        receipt = json.loads(
            Path(entry["artifact_path"]).read_text(encoding="utf-8")
        )
        assert receipt["schema"] == "cadex-policy-receipt-v1"
        assert receipt["policy_sha256"] == container["sha256"]
        assert receipt["task_sha256"] == hashlib.sha256(
            bundle_path.read_bytes()
        ).hexdigest()
        assert receipt["model_sha256"] == bundle["model"]["sha256"]
        assert receipt["witness_samples"] >= 8
        assert receipt["witness_error"] < 1.0e-4

        live = written["live_outputs"]["gait"]
        assert live["domain"] == "assembly"
        assert live["output_type"] == "policy"
        assert live["type_id"] == "App::FeaturePython"

        _assert_no_training_framework()

        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)


def _assert_no_training_framework() -> None:
    """No jax and no mjx anywhere in the staged payload (ADR-084).

    The negative M7 owes, checked where it can actually be false.
    ``test_engine_purity_guardrails`` asserts the *source* imports none of
    this; a payload is a relocated conda environment, and things arrive in
    one by dependency rather than by import, so it is a different claim.

    A no-op without ``CADEX_ENGINE_ROOT`` -- there is no payload to inspect
    and the source-tree claim is already made elsewhere -- which is why this
    rides inside the gate test rather than standing as a twelfth one that
    would skip.
    """

    raw = os.environ.get("CADEX_ENGINE_ROOT", "").strip()
    if not raw:
        return
    root = Path(raw).resolve()
    offenders = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_dir()
        and path.name in {"jax", "jaxlib", "mjx", "flax", "optax", "brax"}
    )
    assert not offenders, (
        f"the staged payload carries a training framework: {offenders}. "
        "Training is offboard (ADR-075, ADR-084); the engine verifies a "
        "policy and never produces one."
    )
    assert not list(root.rglob("cadex_train.py")), (
        "training/cadex_train.py reached the payload; no CMake rule should "
        "install it (ADR-084)."
    )


#: The M8 script: the M7 policy, played. The rollout is declared with
#: ``frames_per_second=25`` against a 50 Hz task, which is one frame per two
#: control steps -- a rate that divides, chosen so the frame count below is
#: arithmetic rather than an observation.
ROLLOUT_SCRIPT = POLICY_SCRIPT.replace(
    'result = {"gait": gait, "plate"',
    """play = assembly.rollout(gait, frames_per_second=25, label="walk")
result = {"play": play, "gait": gait, "plate\"""",
)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for cadexd CI."
)
def test_cadexd_plays_a_trained_policy_into_a_simulation_trace() -> None:
    """A learned gait leaves the building (ADR-085), and it is the twelfth gate.

    M8's shippable capability, and the end of the MuJoCo arc: design a
    mechanism in Cadex, train a policy for it offboard, and get back a
    simulation trace of that policy driving that mechanism. It exists for
    ADR-023's reason -- a source tree that passes proves nothing about a
    payload, the rule that caught the dangling ``bin/python`` in M0.

    **No protocol change and no shell diff, and this is where that is
    proved.** The rollout arrives as ``assembly_simulation_json``, the
    artifact kind ``cadex_animate`` has baked since ADR-050, carried by an
    output type the shell already knows. What changed is what is *in* the
    trace, not how it travels -- so the whole of M8 is invisible to a shell
    nobody touched.

    A random-weight container is enough here: this gate is about the path,
    and whether the gait is any *good* is what ``test_dynamics_policy_live``
    asserts with a real training run in the middle.
    """

    import dynamics_policy_fixtures as pf

    root = Path(tempfile.mkdtemp(prefix="cadexd-rollout-ci-"))
    client = None
    try:
        client = _spawn_cadexd()
        opened = client.request("open_project", {"project_root": str(root)})
        assert opened["ok"] is True, opened

        written = client.request(
            "write_script", {"source": TASK_SCRIPT, "expected_revision": ""}
        )
        assert written["ok"] is True, written
        revision = str(written["revision"])
        bundle_path = Path(written["display"]["job"]["artifact_path"])
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

        container = pf.policy_container(
            {"bundle": bundle,
             "task_sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest()},
            normalise=True,
        )
        weights = root.parent / "walk.cxpolicy"
        weights.write_bytes(container["blob"])
        stored = client.request(
            "put_asset", {"source_path": str(weights), "name": "walk.cxpolicy"}
        )
        assert stored["ok"] is True, stored

        written = client.request(
            "write_script",
            {"source": ROLLOUT_SCRIPT.replace("__SHA256__", container["sha256"]),
             "expected_revision": revision},
        )
        assert written["ok"] is True, json.dumps(written)[:4000]

        entry = written["display"]["play"]
        # The artifact kind the shell has baked since ADR-050. A rollout is
        # not a new kind of thing to the shell; it is a trace.
        assert entry["artifact_kind"] == "assembly_simulation_json", entry

        trace = json.loads(
            Path(entry["artifact_path"]).read_text(encoding="utf-8")
        )
        assert trace["schema"] == "cadex-assembly-simulation-trace-v1"
        assert trace["component_outputs"] == ["base", "swing"]
        # An empty list, and it has to be present: the publisher reads
        # motion_outputs from every simulation.
        assert trace["motion_outputs"] == []

        # One second at 50 Hz sampled every second control step: 50 // 2 + 1
        # solver frames, plus the untimed input frame in front of them.
        assert len(trace["frames"]) == 27
        assert trace["frames"][0]["frame_kind"] == "input"
        assert trace["frames"][0]["nominal_time_s"] is None
        assert trace["parameters"]["frames_per_second"] == 25
        assert trace["parameters"]["start_time_s"] == 0.0
        assert trace["parameters"]["end_time_s"] == pytest.approx(1.0)
        for frame in trace["frames"]:
            assert sorted(frame["component_placements"]) == ["base", "swing"]

        # The three digests that make a policy, a task and a model mean
        # anything together, restated in the trace so it can be checked
        # without opening the receipt beside it.
        policy = trace["policy"]
        assert policy["policy_sha256"] == container["sha256"]
        assert policy["task_sha256"] == hashlib.sha256(
            bundle_path.read_bytes()
        ).hexdigest()
        assert policy["model_sha256"] == bundle["model"]["sha256"]
        assert policy["step_count"] == 50
        assert policy["truncated"] is True
        assert sorted(term["label"] for term in policy["reward_totals"]) == [
            "control_cost", "lift"
        ]

        # It published as a simulation, which is what keeps it under the
        # "exactly one" rule and inside the shell's existing bake.
        live = written["live_outputs"]["play"]
        assert live["domain"] == "assembly"
        assert live["output_type"] == "simulation"

        _assert_no_training_framework()

        done = client.request("shutdown", timeout=60)
        assert done["ok"] is True
    finally:
        _stop(client)
        shutil.rmtree(root, ignore_errors=True)
