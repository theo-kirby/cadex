# SPDX-License-Identifier: LGPL-2.1-or-later

"""Write the accepted model out as STEP / STL / BREP files.

The engine already stages a detached BREP per declared output and hands back
its absolute path in the reply's ``display`` block; converting one is a few
lines of OCCT that FreeCAD already wraps. So this does the obvious thing: it
runs a short ``FreeCADCmd -c`` against **the engine the CLI resolved**, reads
each staged ``.brep``, and exports it. No second geometry kernel, no
in-process FreeCAD, and no reason for a conversion here to disagree with the
one the engine would do.

**This is one seam on purpose.** Everything the conversion needs is a plan
of ``(source, format, destination)`` triples; nothing else in the CLI knows
how a file gets written. When ``export_model`` becomes a protocol op — it
should, and it is not this PR — :func:`export_outputs` becomes a request
instead of a subprocess and nothing above it changes.

**STEP files are not reproducible and must not be hashed.** AP214 embeds a
generation timestamp, so two exports of an identical model differ byte for
byte. A pipeline that wants to know whether the geometry moved compares the
engine's own content ``digest``, which is what it is for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Iterable, Mapping

from .engine import Engine

#: What a BREP output can be written as. Kept small deliberately: STEP for
#: anything downstream that does solids, STL for meshing and printing, BREP
#: for a lossless round trip back into the engine.
FORMATS = ("step", "stl", "brep")

FORMAT_SUFFIXES = {"step": ".step", "stl": ".stl", "brep": ".brep"}

#: The banner the in-engine half prints its result on.
RESULT_MARKER = "CADEX-CLI-EXPORT "

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


class ExportError(RuntimeError):
    """The conversion could not be run, or the engine reported it failed."""


@dataclass
class ExportedOutput:
    """One declared output and the files written for it."""

    name: str
    kind: str
    files: dict[str, str] = field(default_factory=dict)
    skipped: str = ""

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "files": dict(self.files),
        }
        if self.skipped:
            payload["skipped"] = self.skipped
        return payload


def parse_formats(raw: str | Iterable[str] | None) -> list[str]:
    """``"step,stl"`` → ``["step", "stl"]``, validated."""

    if raw is None:
        return ["step", "stl"]
    if isinstance(raw, str):
        wanted = [item.strip().lower() for item in raw.split(",")]
    else:
        wanted = [str(item).strip().lower() for item in raw]
    chosen: list[str] = []
    for item in wanted:
        if not item:
            continue
        if item not in FORMATS:
            raise ExportError(
                f"Unknown export format {item!r}; known: {', '.join(FORMATS)}."
            )
        if item not in chosen:
            chosen.append(item)
    if not chosen:
        raise ExportError("No export formats requested.")
    return chosen


def safe_stem(name: str) -> str:
    """A filename stem from an output name, without inventing collisions."""

    stem = _UNSAFE.sub("_", str(name)).strip("._-")
    return stem or "output"


#: The environment variable the in-engine half reads its plan path from.
#:
#: The plan travels in the environment rather than in ``argv`` because
#: ``FreeCADCmd`` has no ``argv`` to give it: it takes *files*, and runs an
#: argument as Python only when no such file exists
#: (``Application::processCmdLineFiles``). That is also why the exporter is
#: written to a real file rather than passed with ``-c``. The `-c` route
#: works — the ``pixi run cadexd`` task uses it — but only by accident of
#: length: the code is stat()ed as a path first, so any *component* of it
#: longer than ``NAME_MAX`` (255 bytes, and newlines do not delimit
#: components) makes the probe fail with ENAMETOOLONG and the process dies
#: with a bare "Application unexpectedly terminated". A script grows past
#: that; a path never does.
PLAN_ENV = "CADEX_CLI_EXPORT_PLAN"

#: Runs *inside* the engine. Reads a plan, exports, prints one JSON line.
#: `Part.Shape().read()` takes the detached BREP the engine staged, so the
#: shape that is exported is the shape that was accepted -- not a re-run of
#: the script that produced it.
_EXPORTER = r"""
import json, os, traceback

plan = json.load(open(os.environ["CADEX_CLI_EXPORT_PLAN"], "r"))
written, failures = [], []
try:
    import Part
except Exception as exc:
    print("CADEX-CLI-EXPORT " + json.dumps(
        {"ok": False, "error": "Part is not importable: %s" % exc}))
    raise SystemExit(1)

for job in plan:
    try:
        shape = Part.Shape()
        shape.read(job["source"])
        for target in job["targets"]:
            fmt, path = target["format"], target["path"]
            if fmt == "step":
                shape.exportStep(path)
            elif fmt == "stl":
                shape.exportStl(path)
            elif fmt == "brep":
                shape.exportBrep(path)
            else:
                raise ValueError("unknown format %r" % fmt)
            written.append({"name": job["name"], "format": fmt, "path": path})
    except Exception as exc:
        failures.append({"name": job["name"], "error": "%s: %s" % (
            exc.__class__.__name__, exc), "traceback": traceback.format_exc()})

print("CADEX-CLI-EXPORT " + json.dumps(
    {"ok": not failures, "written": written, "failures": failures}))
"""


def export_plan(
    display: Mapping[str, Any], out_dir: Path, formats: list[str]
) -> tuple[list[dict[str, Any]], list[ExportedOutput]]:
    """Turn a ``display`` block into a conversion plan and its report rows.

    Outputs with no BREP artifact are reported as skipped rather than
    silently dropped: an assembly component places another output's geometry
    and has none of its own, a mesh output is a ``.ply``, and a solve
    diagnostic is not geometry at all. A caller who sees three outputs and
    two files should be told which one and why.
    """

    plan: list[dict[str, Any]] = []
    rows: list[ExportedOutput] = []
    for name in sorted(display):
        entry = display.get(name)
        if not isinstance(entry, Mapping):
            continue
        kind = str(entry.get("artifact_kind") or "") or "none"
        source = str(entry.get("artifact_path") or "")
        if kind != "brep" or not source:
            rows.append(
                ExportedOutput(
                    name=name,
                    kind=kind,
                    skipped=(
                        "not a BREP output"
                        if kind != "brep"
                        else "no staged artifact"
                    ),
                )
            )
            continue
        stem = safe_stem(name)
        targets = [
            {
                "format": fmt,
                "path": str(Path(out_dir) / f"{stem}{FORMAT_SUFFIXES[fmt]}"),
            }
            for fmt in formats
        ]
        plan.append({"name": name, "source": source, "targets": targets})
        rows.append(ExportedOutput(name=name, kind=kind))
    return plan, rows


def export_outputs(
    engine: Engine,
    display: Mapping[str, Any],
    out_dir: Path | str,
    formats: list[str] | None = None,
    *,
    timeout: float = 600.0,
) -> list[ExportedOutput]:
    """Write every BREP output in ``display`` into ``out_dir``."""

    chosen = formats or ["step", "stl"]
    destination = Path(out_dir).expanduser()
    destination.mkdir(parents=True, exist_ok=True)
    plan, rows = export_plan(display, destination, chosen)
    if not plan:
        return rows

    by_name = {row.name: row for row in rows}
    with tempfile.TemporaryDirectory(prefix="cadex-cli-export-") as scratch:
        plan_path = Path(scratch) / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        script_path = Path(scratch) / "cadex_cli_export.py"
        script_path.write_text(_EXPORTER, encoding="utf-8")
        try:
            completed = subprocess.run(
                [str(engine.freecadcmd), str(script_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, PLAN_ENV: str(plan_path)},
            )
        except OSError as exc:
            raise ExportError(f"Could not run the engine to export: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ExportError(f"The export timed out after {timeout:g}s.") from exc

    report = _parse_result(completed.stdout, completed.stderr, completed.returncode)
    for item in report.get("written") or []:
        row = by_name.get(str(item.get("name") or ""))
        if row is not None:
            row.files[str(item.get("format"))] = str(item.get("path"))
    failures = report.get("failures") or []
    if failures:
        detail = "; ".join(
            f"{item.get('name')}: {item.get('error')}" for item in failures
        )
        raise ExportError(f"The engine could not export: {detail}")
    return rows


def _parse_result(stdout: str, stderr: str, returncode: int) -> dict[str, Any]:
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if line.startswith(RESULT_MARKER):
            try:
                return json.loads(line[len(RESULT_MARKER) :])
            except ValueError:
                break
    tail = "\n".join((stderr or "").strip().splitlines()[-20:])
    raise ExportError(
        f"The engine's exporter printed no result (exit {returncode})."
        + (f"\n{tail}" if tail else "")
    )
