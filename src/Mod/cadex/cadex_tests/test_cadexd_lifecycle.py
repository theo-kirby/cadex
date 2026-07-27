# SPDX-License-Identifier: LGPL-2.1-or-later

"""cadexd lifecycle CI (Phase 5.3, ctest ``CadexdLifecycle``).

Drives a real cadexd child (FreeCADCmd) over the cadex-cadexd-v1 stdio
protocol: open → put_asset (and the script that imports it) → write_script
(with display) → set_params → inspect → resolve_pin → kill -9 → respawn →
restore digest equality → explicit rebuild → cancel a slow script mid-run →
server stays serviceable → shutdown. Skipped when no FreeCADCmd binary is
available.
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
        # the parts they instance carry geometry and no placement.
        for component in ("base", "swing"):
            entry = display[component]
            assert entry["artifact_kind"] is None, entry
            assert isinstance(entry["placement"], list), entry
            assert len(entry["placement"]) == 16, entry
        for shape in ("plate", "arm"):
            entry = display[shape]
            assert entry["artifact_kind"] == "brep", entry
            assert entry["placement"] is None, entry

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
