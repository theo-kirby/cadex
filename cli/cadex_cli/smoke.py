# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Bounded smoke orchestration over retained accepted artifacts (ADR-352).

The dynamics child uses the engine's MuJoCo interpreter; a trusted FreeCAD
adapter measures exact BREP at the recorded component poses. Neither child
executes a project script. A measured failure is a verdict, not rejection
of the accepted design. Missing evidence or timeout is a command failure.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

from .engine import Engine
from .export import ExportedOutput
from .train import TASK_KIND, TrainError, find_task

#: The child, run by path under :func:`smoke_interpreter`.
SMOKE_SCRIPT = Path(__file__).resolve().with_name("smoke_runner.py")
MJCF_KIND = "assembly_mjcf_xml"
RECEIPT_NAME = "smoke.json"

#: The rollout the ot6 close-out checked by hand: Finch held standing for
#: two seconds (ADR-335). Long enough for a resting contact to settle, short
#: enough that a free base that is falling has clearly not stopped.
DEFAULT_SECONDS = 2.0
DEFAULT_MODE = "hold"
#: MuJoCo's soft contact lets a resting part sink about 0.1--0.2 mm at the
#: default ``solref`` (0.15 mm on Finch's soles, 0.18 mm on a 50 g block);
#: 0.5 mm is above that and below any burial worth a design turn.
DEFAULT_PENETRATION_MM = 0.5
#: A held pose settles to micrometres per second; a design still moving
#: faster than this at the end is not resting.
DEFAULT_REST_SPEED_MM_S = 10.0
#: A free base that has turned this far from its accepted pose fell over; it
#: did not hold (ADR-377). Measured: Finch standing ended 9e-06 degrees from
#: its keyframe attitude and the resting-block fixture 0, while the retained
#: ot6 balancer given no torque lay 101.3 degrees over after two seconds.
#: Thirty is orders of magnitude above every settled measurement and well
#: under any topple.
DEFAULT_MAX_TILT_DEGREES = 30.0
DEFAULT_FPS = 50
#: The charter's bound (ADR-341): a smoke rollout is over inside five
#: minutes of wall time, or it is a failure with the reason.
MAXIMUM_TIMEOUT_S = 300.0
DEFAULT_TIMEOUT_S = MAXIMUM_TIMEOUT_S


class SmokeError(RuntimeError):
    """The rollout could not run: no model, no interpreter, or past the bound."""


def smoke_interpreter(engine: Engine) -> Path:
    """The engine's own Python, which carries ``mujoco``; else this one."""

    beside = engine.freecadcmd.parent / "python"
    if beside.is_file():
        return beside
    return Path(sys.executable)


def find_model(outputs: Sequence[ExportedOutput], name: str = "") -> ExportedOutput:
    """The one exported MJCF model, or the one ``name`` picks."""

    models = [row for row in outputs if row.kind == MJCF_KIND and row.files.get("xml")]
    if name:
        for row in models:
            if row.name == name:
                return row
        raise SmokeError(
            f"--model {name}: the accepted revision exports no MJCF model by "
            "that name" + (f" (it has: {', '.join(r.name for r in models)})." if models else ".")
        )
    if not models:
        raise SmokeError(
            "the accepted revision exports no MJCF model: declare one with "
            "assembly.mjcf(...) and put it in result."
        )
    if len(models) > 1:
        raise SmokeError(
            "the accepted revision exports more than one MJCF model; pick one "
            "with --model NAME: " + ", ".join(r.name for r in models) + "."
        )
    return models[0]


def find_optional_task(outputs: Sequence[ExportedOutput], name: str = "") -> ExportedOutput | None:
    """The exported task, when there is exactly one or ``name`` picks it.

    A design without a task still smokes -- there is just nothing declared
    to terminate on -- so "none" is an answer here where ``cadex train``
    refuses.
    """

    tasks = [row for row in outputs if row.kind == TASK_KIND and row.files.get("json")]
    if not tasks and not name:
        return None
    try:
        return find_task(outputs, name)
    except TrainError as exc:
        raise SmokeError(str(exc)) from exc


def smoke_command(
    python: Path | str,
    *,
    model: Path | str,
    task: Path | str | None,
    out: Path | str,
    seconds: float,
    mode: str,
    penetration_mm: float,
    rest_speed_mm_s: float,
    max_tilt_degrees: float,
    fps: int,
) -> list[str]:
    command = [
        str(python), str(SMOKE_SCRIPT),
        "--model", str(model),
        "--out", str(out),
        "--seconds", f"{float(seconds):g}",
        "--mode", str(mode),
        "--penetration-mm", f"{float(penetration_mm):g}",
        "--rest-speed-mm-s", f"{float(rest_speed_mm_s):g}",
        "--max-tilt-degrees", f"{float(max_tilt_degrees):g}",
        "--fps", str(int(fps)),
    ]
    if task:
        command += ["--task", str(task)]
    return command


def run_smoke(command: Sequence[str], *, receipt: Path | str, timeout: float) -> dict[str, Any]:
    """Run the child inside ``timeout`` seconds and read the receipt it wrote."""

    import math
    if not math.isfinite(timeout) or timeout <= 0 or timeout > MAXIMUM_TIMEOUT_S:
        raise SmokeError(f"the smoke bound must be within (0, {MAXIMUM_TIMEOUT_S:g}] seconds.")
    try:
        completed = subprocess.run(
            list(command), capture_output=True, text=True, timeout=timeout,
        )
    except OSError as exc:
        raise SmokeError(f"could not run the smoke rollout: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SmokeError(
            f"the smoke rollout ran past its bound of {timeout:g} s and was killed; "
            "shorten --seconds or raise --timeout (at most "
            f"{MAXIMUM_TIMEOUT_S:g})."
        ) from exc
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()
        reason = tail[-1] if tail else f"exit {completed.returncode}"
        raise SmokeError(f"the smoke rollout failed: {reason}")
    path = Path(receipt)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SmokeError(f"the smoke rollout wrote no readable receipt at {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("verdict") not in ("pass", "fail"):
        raise SmokeError(f"{path} is not a smoke receipt.")
    return value


def smoke_cell(receipt: dict[str, Any]) -> str:
    """The ``PROGRESS.md`` numbers cell: the verdict and what failed."""

    verdict = str(receipt.get("verdict") or "")
    head = "smoke {:s} {:g} s {:s}".format(
        verdict, float(receipt.get("seconds") or 0.0), str(receipt.get("mode") or ""))
    failing = [str(item) for item in receipt.get("failing") or []]
    if not failing:
        return head
    return head + ": " + "; ".join(failing[:3]) + (
        f" (+{len(failing) - 3} more)" if len(failing) > 3 else "")


def retained_bundle(root: Path, destination: Path) -> tuple[dict, dict, dict]:
    try:
        return _retained_bundle(root, destination)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SmokeError(f"cannot read retained smoke artifacts: {exc}") from exc


def _retained_bundle(root: Path, destination: Path) -> tuple[dict, dict, dict]:
    """Copy digest-checked accepted artifacts without restoring or accepting."""
    import hashlib
    import shutil

    state = json.loads((root / "script.json").read_text())
    pin = state.get("accepted_attempt") or {}
    staging = (root / str(pin.get("staging") or "")).resolve()
    if (state.get("schema") != "cadex-project-script-v1" or not state.get("accepted_revision") or pin.get("revision") != state["accepted_revision"]
            or not staging.is_relative_to((root / "script_artifacts").resolve())):
        raise SmokeError("no valid retained accepted attempt")
    result = json.loads((staging / "result.json").read_text())
    if not result.get("ok") or result.get("digest") != state.get("accepted_digest"):
        raise SmokeError("retained result does not match the accepted digest")
    destination = destination.resolve()
    if destination == root or any(destination.is_relative_to(root / protected) for protected in ("script_artifacts", "assets", ".git")):
        raise SmokeError("--out must not overwrite the project root or accepted artifacts")
    destination.mkdir(parents=True, exist_ok=True)
    for filename in ("smoke.json", "smoke-dynamics.json", "smoke-trace.json", "smoke-geometry.json"):
        (destination / filename).unlink(missing_ok=True)
    display = {}
    items = {item["name"]: item for item in result["outputs"]}
    for name, item in items.items():
        if not item.get("artifact_path"):
            continue
        source = (staging / item["artifact_path"]).resolve()
        if not source.is_relative_to(staging) or not source.is_file():
            raise SmokeError(f"missing or escaping retained artifact: {name}")
        if item.get("artifact_sha256") and hashlib.sha256(source.read_bytes()).hexdigest() != item["artifact_sha256"]:
            raise SmokeError(f"retained artifact digest mismatch: {name}")
        target = destination / source.name
        if target.is_symlink() or target.resolve().is_relative_to(staging):
            raise SmokeError(f"unsafe smoke output: {target.name}")
        target.unlink(missing_ok=True)
        shutil.copyfile(source, target)
        display[name] = {"artifact_kind": item.get("artifact_kind"), "artifact_path": str(target)}
    return state, items, display


def check_geometry(engine: Engine, *, items: dict, display: dict, model_name: str,
                   out: Path, timeout: float, maximum_volume: float) -> dict:
    """Trusted FreeCAD child reads detached solids and numeric poses only."""
    import os
    import tempfile

    if timeout <= 0:
        raise SmokeError("exact smoke geometry exceeded the shared wall-time bound")
    model = items[model_name]
    components = model["assembly_data"]["component_outputs"]
    geometry = []
    for name in components:
        component = items[name]
        source = display.get(component.get("source_output"), {})
        if source.get("artifact_kind") != "brep":
            raise SmokeError(f"exact smoke geometry unavailable for {name}")
        geometry.append({"name": name, "path": source["artifact_path"]})
    assembly = items[model["assembly_data"]["assembly_output"]]
    plan = {"geometry": geometry, "static": assembly.get("clearance", []),
            "trace": str(out / "smoke-trace.json"), "out": str(out / "smoke-geometry.json"),
            "maximum_volume_mm3": maximum_volume}
    with tempfile.TemporaryDirectory(prefix="cadex-smoke-") as temp:
        plan_path = Path(temp) / "plan.json"
        plan_path.write_text(json.dumps(plan))
        try:
            completed = subprocess.run(
                [str(engine.freecadcmd), str(Path(__file__).with_name("smoke_geometry.py"))],
                env={**os.environ, "CADEX_SMOKE_GEOMETRY_PLAN": str(plan_path)},
                capture_output=True, text=True, timeout=max(0.001, timeout))
        except subprocess.TimeoutExpired as exc:
            raise SmokeError("exact smoke geometry exceeded the shared wall-time bound") from exc
    path = out / "smoke-geometry.json"
    if completed.returncode or not path.is_file():
        raise SmokeError("exact smoke geometry failed: " + (completed.stderr or completed.stdout)[-1500:])
    value = json.loads(path.read_text())
    if value.get("error"):
        raise SmokeError(value["error"])
    return value
