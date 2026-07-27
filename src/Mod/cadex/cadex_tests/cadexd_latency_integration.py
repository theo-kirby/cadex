# SPDX-License-Identifier: LGPL-2.1-or-later

"""Engine-only slider-drag latency bar (Phase 7 C0).

Run it directly — it needs no FreeCAD in-process, only a built engine::

    pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py

Succeeds the Qt-era ``cadexd_shell_switchover_integration.py`` measurement
(median 0.479 s, ADR-018) as the durable latency regression bar. That test
drove ``CadexSession`` → ``CadexdClient`` → hydration into a live FreeCAD
document; all three die with the Qt shell (ADR-021), so the evidence is
re-established here **client-agnostically**: the same 24-hole/fillet/
mesh-skin baseline part and the same 10 ``set_params`` drags, driven over
raw ``cadex-cadexd-v1`` NDJSON by the minimal client below. No
``CadexdClient``, no hydration, no shell.

Two medians are reported, because the two shells asked for different work:

- ``median_seconds`` — no ``display`` block: parse → worker → validate →
  accept. The pure engine number, comparable to the Qt 0.479 s baseline.
- ``median_display_seconds`` — with ``{"quality": "draft", "edges": false}``,
  i.e. exactly what the Blender shell requests mid-drag (ADR-019), so the
  engine half of that shell's 0.548 s stays measurable from this repo.

Bar for both: median ≤ 0.65 s (the decision-gate parity bar,
``docs/INTEGRATION.md``).

**Which engine.** By default this measures the dev tree: the built
``FreeCADCmd`` plus ``src/Mod/cadex`` on ``sys.path``. Set
``CADEX_ENGINE_ROOT`` to a staged payload and it measures the *shipped*
engine instead, resolving the binary and the module dir out of
``cadex-engine.json`` exactly the way ``test_cadexd_lifecycle.py`` and the
Blender shell do — a source tree that meets the bar proves nothing about a
payload (ADR-023). The report names the engine it measured (``engine``,
``engine_root``), so the two runs are told apart in a log::

    pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py
    CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 \
        pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

CADEX_ROOT = Path(__file__).resolve().parent.parent
if str(CADEX_ROOT) not in sys.path:
    sys.path.insert(0, str(CADEX_ROOT))

from CadexdProtocol import PROTOCOL_SCHEMA, decode_frame, encode_frame

REPO_ROOT = Path(__file__).resolve().parents[4]
_FREECADCMD_CANDIDATES = (
    REPO_ROOT / "build" / "release" / "bin" / "FreeCADCmd",
    REPO_ROOT / ".pixi" / "envs" / "default" / "bin" / "FreeCADCmd",
)


def _packaged_engine():
    """Resolve ``(binary, module_dir)`` from ``CADEX_ENGINE_ROOT``, or None.

    The manifest is the payload's discovery contract (ADR-020); reading it
    here rather than guessing the layout is what makes this measurement the
    *shipped* engine's and not a build directory's.
    """
    root = os.environ.get("CADEX_ENGINE_ROOT", "").strip()
    if not root:
        return None, None
    manifest_path = Path(root) / "cadex-engine.json"
    if not manifest_path.is_file():
        raise SystemExit(
            f"CADEX_ENGINE_ROOT={root!r} has no cadex-engine.json; the "
            "payload's manifest is its discovery contract (ADR-020)."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest.get("schema") == "cadex-engine-v1", manifest
    assert manifest.get("protocol") == PROTOCOL_SCHEMA, manifest
    base = manifest_path.parent
    binary = base.joinpath(*str(manifest["freecadcmd"]).split("/"))
    module_dir = base.joinpath(*str(manifest["module_dir"]).split("/"))
    assert binary.is_file(), binary
    assert module_dir.is_dir(), module_dir
    return binary, module_dir

#: The switchover baseline, verbatim: 24 holes, a fillet, and a mesh skin.
BASELINE_SCRIPT = """
p = params(hole=num(2.5, unit="mm", min=1.0, max=4.0, step=0.1))
base = part.box(120, 80, 8)
holes = [
    part.cylinder(p.hole, 16, origin=[10 + 18 * (i % 6), 12 + 18 * (i // 6), -4])
    for i in range(24)
]
plate = part.fillet(part.cut(base, holes), 1.0)
skin = mesh.from_shape(plate, linear_deflection=0.5)
result = {"plate": plate, "skin": skin}
"""

DRAGS = 10
PARITY_BAR_SECONDS = 0.65
DRAFT_DISPLAY = {"quality": "draft", "edges": False}


class _Stdio:
    """The whole client: NDJSON in, NDJSON out, events dropped."""

    def __init__(self, process: subprocess.Popen) -> None:
        self._process = process
        self._sequence = 0

    def _read_frame(self, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() <= deadline:
            line = self._process.stdout.readline()
            if not line:
                raise EOFError("cadexd closed its protocol stream.")
            if not line.strip():
                continue
            try:
                return decode_frame(line.strip())
            except Exception:
                continue  # pre-hijack FreeCADCmd chatter
        raise TimeoutError("No cadexd frame within the timeout.")

    def wait_ready(self, timeout: float = 120.0) -> None:
        frame = self._read_frame(timeout)
        assert frame.get("event", {}).get("event") == "ready", frame

    def request(self, op: str, args: dict | None = None, timeout: float = 300.0) -> dict:
        self._sequence += 1
        request_id = f"bench-{self._sequence}"
        frame = {"schema": PROTOCOL_SCHEMA, "id": request_id, "op": op}
        if args is not None:
            frame["args"] = args
        self._process.stdin.write(encode_frame(frame))
        self._process.stdin.flush()
        deadline = time.monotonic() + timeout
        while True:
            answer = self._read_frame(max(0.1, deadline - time.monotonic()))
            if "event" in answer:
                continue
            if answer.get("id") == request_id:
                return answer


def _spawn(executable: Path, module_dir: Path) -> _Stdio:
    process = subprocess.Popen(
        [
            str(executable),
            "-c",
            (
                f"import sys; sys.path.insert(0, {str(module_dir)!r}); "
                "import cadexd; raise SystemExit(cadexd.main())"
            ),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "PYTHONHASHSEED": "0"},
    )
    client = _Stdio(process)
    client.wait_ready()
    return client


def _drag(client: _Stdio, revision: str, display: dict | None) -> tuple[list[float], str]:
    """``DRAGS`` revision-guarded ``set_params`` calls; per-call seconds."""

    durations: list[float] = []
    for index in range(DRAGS):
        args = {
            "values": {"hole": 1.5 + 0.2 * index},
            "expected_revision": revision,
        }
        if display is not None:
            args["display"] = dict(display)
        started = time.perf_counter()
        patched = client.request("set_params", args)
        durations.append(time.perf_counter() - started)
        assert patched.get("ok") is True, patched
        revision = str(patched["model_state"]["next_write_expected_revision"])
    return durations, revision


def main() -> int:
    packaged_binary, packaged_module_dir = _packaged_engine()
    executable = packaged_binary or next(
        (candidate for candidate in _FREECADCMD_CANDIDATES if candidate.is_file()), None
    )
    module_dir = packaged_module_dir or CADEX_ROOT
    engine = "payload" if packaged_binary is not None else "dev-tree"
    if executable is None:
        print(
            "CADEX-LATENCY "
            + json.dumps({"ok": False, "skipped": "no FreeCADCmd binary"}),
            flush=True,
        )
        return 0

    root = Path(tempfile.mkdtemp(prefix="cadexd-latency-"))
    client = None
    try:
        client = _spawn(executable, module_dir)

        opened = client.request("open_project", {"project_root": str(root)})
        assert opened.get("ok") is True, opened

        written = client.request(
            "write_script", {"source": BASELINE_SCRIPT, "expected_revision": ""}
        )
        assert written.get("ok") is True, written
        revision = str(written["model_state"]["next_write_expected_revision"])

        plain, revision = _drag(client, revision, None)
        drafted, revision = _drag(client, revision, DRAFT_DISPLAY)

        median = statistics.median(plain)
        display_median = statistics.median(drafted)
        report = {
            "ok": median <= PARITY_BAR_SECONDS
            and display_median <= PARITY_BAR_SECONDS,
            "engine": engine,
            "engine_root": str(module_dir),
            "drags": DRAGS,
            "set_params_seconds": [round(value, 3) for value in plain],
            "median_seconds": round(median, 3),
            "set_params_display_seconds": [round(value, 3) for value in drafted],
            "median_display_seconds": round(display_median, 3),
            "parity_bar_seconds": PARITY_BAR_SECONDS,
            "median_within_bar": median <= PARITY_BAR_SECONDS,
            "median_display_within_bar": display_median <= PARITY_BAR_SECONDS,
        }
    finally:
        if client is not None:
            process = client._process
            if process.poll() is None:
                process.kill()
            process.wait(timeout=30)
            for stream in (process.stdin, process.stdout):
                try:
                    stream.close()
                except Exception:
                    pass
        shutil.rmtree(root, ignore_errors=True)

    print("CADEX-LATENCY " + json.dumps(report, sort_keys=True), flush=True)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
