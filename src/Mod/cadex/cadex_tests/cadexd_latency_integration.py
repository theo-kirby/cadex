# SPDX-FileCopyrightText: 2026 Cadex Authors
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

Two medians are reported for the accepting path, because the two shells
asked for different work:

- ``median_seconds`` — no ``display`` block: parse → worker → validate →
  accept. The pure engine number, comparable to the Qt 0.479 s baseline.
- ``median_display_seconds`` — with ``{"quality": "draft", "edges": false}``,
  i.e. exactly what the Blender shell requests mid-drag (ADR-019), so the
  engine half of that shell's 0.548 s stays measurable from this repo.

Bar for both: median ≤ 0.65 s (the decision-gate parity bar,
``docs/INTEGRATION.md``).

A third lane measures the **preview** path (ADR-055) over
``PREVIEW_BASELINE_SCRIPT`` — the same 24-hole/fillet/mesh-skin part, now in
a jointed assembly with a second slider that drives motion rather than
geometry. Both paths are measured on that one model, so
``median_assembly_seconds`` (accepting, draft display) and
``median_preview_seconds`` are the same work asked two ways rather than two
different models. ``first_preview_seconds`` is reported separately because it
pays the resident worker's spawn and its generation load — once per drag, not
once per frame — and hiding it would be reporting a number nobody
experiences. Bar: median ≤ 0.10 s, which is a frame rate rather than a parity
number: 10 fps is the floor below which "live" stops being an honest word.

A fourth lane measures **live mode** (ADR-109): the ``live_step`` round trip,
swept over batch size, on a project named by ``CADEX_LIVE_PROJECT``. It needs
a real project because it plays a *trained policy*, and a policy is an asset
— hours of stochastic GPU compute — that the engine can verify but has never
been able to produce (ADR-070, ADR-084); without one the lane reports
``live_skipped`` and does not fail the run. Bar: ``live_median_reported_seconds``
≤ 0.033 s for a 3-step batch, which is what a 30 Hz pump asks of a 100 Hz
task. The **sweep** is the honest part: if the median does not grow with the
batch size, the steps are not reaching the physics and the number is
measuring nothing (M9 hazard 18), so ``live_curve_moves_with_batch_size`` is
reported beside it. Measured here at 0.54 / 1.72 / 4.63 / 19.14 ms for
batches of 1 / 3 / 8 / 32 — near enough linear at ~0.6 ms a control step,
against 344 µs of physics.

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

#: The same part, in an assembly, with a second slider that drives motion
#: rather than geometry (ADR-055). Deliberately the same weight class as
#: ``BASELINE_SCRIPT`` -- the same 24 holes, the same fillet, the same mesh
#: skin -- so ``median_preview_seconds`` and ``median_assembly_seconds`` are
#: the same model measured two ways and not two different models.
#:
#: ``reach`` is a joint offset: it moves `lever` and changes no definition,
#: so it is previewable. ``hole`` is still there and still is not.
PREVIEW_BASELINE_SCRIPT = """
p = params(hole=num(2.5, unit="mm", min=1.0, max=4.0, step=0.1),
           reach=num(20.0, unit="mm", min=0.0, max=60.0, step=0.5))
base = part.box(120, 80, 8)
holes = [
    part.cylinder(p.hole, 16, origin=[10 + 18 * (i % 6), 12 + 18 * (i // 6), -4])
    for i in range(24)
]
plate = part.fillet(part.cut(base, holes), 1.0)
arm = part.box(60, 10, 10)
anchor = assembly.component(plate, grounded=True)
lever = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(anchor, "origin", offset=[p.reach, 20, 8]),
                   assembly.connector(lever, "origin"))
asm = assembly.assembly([anchor, lever], [j])
diag = assembly.solve(asm)
skin = mesh.from_shape(plate, linear_deflection=0.5)
result = {"plate": plate, "arm": arm, "anchor": anchor, "lever": lever,
          "j": j, "asm": asm, "diag": diag, "skin": skin}
"""

DRAGS = 10
PARITY_BAR_SECONDS = 0.65

#: A preview exists to be watchable, so its bar is a frame rate rather than a
#: parity number: 0.10 s is 10 fps, the floor below which "live" stops being
#: an honest word for it.
PREVIEW_BAR_SECONDS = 0.10
DRAFT_DISPLAY = {"quality": "draft", "edges": False}

#: The live lane (ADR-109), and the one thing it cannot synthesise: a policy
#: is an **asset** -- hours of stochastic GPU compute -- and the engine can
#: verify one but has never been able to produce one (ADR-070, ADR-084). So
#: this lane needs a real project with an accepted rollout in it, named by
#: ``CADEX_LIVE_PROJECT``, and reports ``live_skipped`` without one rather
#: than measuring a mechanism nobody trained.
LIVE_PROJECT_ENV = "CADEX_LIVE_PROJECT"

#: Batch sizes swept, in control steps. A sweep rather than one number
#: because a single point cannot tell "the plumbing is fast" from "the
#: measurement is measuring nothing": if the curve does not move with the
#: batch size, the steps are not reaching the physics (M9 hazard 18).
LIVE_BATCHES = (1, 3, 8, 32)

#: Steps measured per batch size. Deliberately below one episode's horizon
#: at every batch size -- an episode that terminates mid-sweep spends the
#: rest of its wall clock holding a fallen machine, and the median would be
#: reporting the hold rather than the round trip.
LIVE_STEPS_PER_BATCH = 240

#: The reported batch, and the bar. Three control steps is what a 30 Hz pump
#: asks of a 100 Hz task, so it is the size the shell actually sends;
#: 0.033 s is the same "10 fps is the floor" argument the preview bar makes,
#: with three times the headroom because the shell queues behind it.
LIVE_REPORTED_BATCH = 3
LIVE_BAR_SECONDS = 0.033


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


def _preview_drag(client: _Stdio, revision: str) -> list[float]:
    """``DRAGS`` ``preview_params`` calls; per-call seconds.

    The revision never moves, and that is the whole point: a preview answers
    a *candidate* without accepting it, so the same ``expected_revision``
    guards every call of a drag. The first call is excluded from the report's
    median and reported separately — it pays the resident worker's spawn and
    its generation load, which happens once per drag rather than once per
    frame.
    """

    durations: list[float] = []
    for index in range(DRAGS):
        started = time.perf_counter()
        answer = client.request(
            "preview_params",
            {
                "values": {"reach": 5.0 + 5.0 * index},
                "expected_revision": revision,
            },
        )
        durations.append(time.perf_counter() - started)
        assert answer.get("ok") is True, answer
        assert answer.get("previewable") is True, answer
        assert answer.get("revision") == revision, answer
    return durations


def _live_lane(executable: Path, module_dir: Path) -> dict:
    """The ``live_step`` round trip, swept over batch size (ADR-109).

    A **separate cadexd** on a **separate project**, because live mode is
    the one lane that cannot run on a script this file writes: it plays a
    trained policy, and a policy is an asset rather than a derivation.

    What is being measured is *plumbing* -- a control step of physics plus
    the JSON that carries its poses -- and the reason that is measurable at
    all is that the worker's episode loop blocks for credit rather than
    sleeping against a clock. A worker that paced itself to real time would
    make this lane a stopwatch on ``time.sleep`` and tell nobody anything.

    Each batch size gets a **fresh session at the same seed**, and the step
    budget stays inside one episode's horizon: a run that reset mid-sweep
    would fold a 1 s termination hold into the median and report the hold.
    """

    project = os.environ.get(LIVE_PROJECT_ENV) or ""
    if not project or not Path(project).is_dir():
        return {
            "live_skipped": (
                f"set {LIVE_PROJECT_ENV} to a project with an accepted "
                f"assembly.rollout in it; a policy is an asset and this "
                f"lane cannot synthesise one"
            )
        }

    client = _spawn(executable, module_dir)
    try:
        opened = client.request("open_project", {"project_root": project})
        if opened.get("ok") is not True:
            return {"live_skipped": f"open_project failed: "
                                    f"{opened.get('failure_code') or opened.get('error')}"}

        medians: dict[str, float] = {}
        samples: dict[str, list[float]] = {}
        opened_seconds = 0.0
        session: dict = {}
        for batch in LIVE_BATCHES:
            # Fresh per batch size, so every sweep point starts at step 0 of
            # the same episode and measures the same physics.
            client.request("live_close", {})
            started = time.perf_counter()
            session = client.request(
                "live_open", {"output": "", "seed": LIVE_SESSION_SEED}
            )
            opened_seconds = time.perf_counter() - started
            if session.get("live") is not True:
                return {"live_skipped": str(session.get("reason") or "no rollout")}

            durations: list[float] = []
            delivered = 0
            for _ in range(max(1, LIVE_STEPS_PER_BATCH // batch)):
                started = time.perf_counter()
                answer = client.request("live_step", {"steps": batch})
                durations.append(time.perf_counter() - started)
                delivered += len(answer.get("frames") or ())
                if answer.get("terminated"):
                    break
            medians[str(batch)] = statistics.median(durations)
            samples[str(batch)] = durations
            if delivered < len(durations) * batch:
                # Said out loud rather than left in the median: a sweep point
                # that lost frames is a sweep point measuring something else.
                medians[f"{batch}_frames_short"] = float(
                    len(durations) * batch - delivered
                )

        reported = medians[str(LIVE_REPORTED_BATCH)]
        # Hazard 18, checked rather than asserted in prose: the curve has to
        # move with the batch size or the batches are not reaching physics.
        moves = medians[str(LIVE_BATCHES[-1])] > 2.0 * medians[str(LIVE_BATCHES[0])]
        return {
            "live_open_seconds": round(opened_seconds, 4),
            "live_components": len(session.get("components") or ()),
            "live_control_hz": session.get("control_hz"),
            "live_batches": list(LIVE_BATCHES),
            "live_median_seconds": {
                key: round(value, 5) for key, value in medians.items()
            },
            "live_reported_batch": LIVE_REPORTED_BATCH,
            "live_median_reported_seconds": round(reported, 5),
            "live_bar_seconds": LIVE_BAR_SECONDS,
            "live_within_bar": reported <= LIVE_BAR_SECONDS,
            "live_curve_moves_with_batch_size": moves,
            # A p90 per batch rather than every sample: the sweep is 240
            # steps at each of four sizes, and 500 raw numbers on one line
            # is a report nobody reads. The tail is what a dropped frame or
            # a termination hold would show up in, so it is the part worth
            # keeping.
            "live_p90_seconds": {
                key: round(sorted(values)[int(0.9 * (len(values) - 1))], 5)
                for key, values in samples.items()
            },
            "live_samples": {key: len(values) for key, values in samples.items()},
        }
    finally:
        process = client._process
        if process.poll() is None:
            process.kill()
        process.wait(timeout=30)


#: The episode the live lane measures. A seed rather than the default,
#: because a measurement across a fall is a measurement of a fall.
LIVE_SESSION_SEED = 6


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

        # The same part in an assembly, measured two ways: the accepting path
        # on the geometry slider, and the preview path on the motion slider.
        assembled = client.request(
            "write_script",
            {"source": PREVIEW_BASELINE_SCRIPT, "expected_revision": revision},
        )
        assert assembled.get("ok") is True, assembled
        revision = str(assembled["model_state"]["next_write_expected_revision"])
        accepting, revision = _drag(client, revision, DRAFT_DISPLAY)
        previews = _preview_drag(client, revision)

        median = statistics.median(plain)
        display_median = statistics.median(drafted)
        assembly_median = statistics.median(accepting)
        # The first preview of a drag pays the spawn and the generation load;
        # every later one is what the user actually watches. Both reported --
        # hiding the first would be reporting a number nobody experiences.
        preview_median = statistics.median(previews[1:])
        live = _live_lane(executable, module_dir)
        report = {
            "ok": median <= PARITY_BAR_SECONDS
            and display_median <= PARITY_BAR_SECONDS
            and preview_median <= PREVIEW_BAR_SECONDS
            # A skipped live lane does not fail the run: it needs a trained
            # policy, and most machines running this have none.
            and live.get("live_within_bar", True),
            **live,
            "engine": engine,
            "engine_root": str(module_dir),
            "drags": DRAGS,
            "set_params_seconds": [round(value, 3) for value in plain],
            "median_seconds": round(median, 3),
            "set_params_display_seconds": [round(value, 3) for value in drafted],
            "median_display_seconds": round(display_median, 3),
            "assembly_set_params_display_seconds": [
                round(value, 3) for value in accepting
            ],
            "median_assembly_seconds": round(assembly_median, 3),
            "preview_seconds": [round(value, 4) for value in previews],
            "first_preview_seconds": round(previews[0], 3),
            "median_preview_seconds": round(preview_median, 4),
            "preview_speedup": round(assembly_median / max(preview_median, 1e-9), 1),
            "parity_bar_seconds": PARITY_BAR_SECONDS,
            "preview_bar_seconds": PREVIEW_BAR_SECONDS,
            "median_within_bar": median <= PARITY_BAR_SECONDS,
            "median_display_within_bar": display_median <= PARITY_BAR_SECONDS,
            "median_preview_within_bar": preview_median <= PREVIEW_BAR_SECONDS,
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
