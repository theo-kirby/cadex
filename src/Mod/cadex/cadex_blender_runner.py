# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Blender geometry subprocess boundary (ADR-185), imported only by workers.

No bpy import, shell module or UI dependency. The executable is host-supplied,
never chosen by a recipe. The child can read its runtime and one input file,
write one scratch directory, and cannot access the network. Unsupported OS
sandboxes fail closed. No project files or host credentials enter the child.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys

from CadexScriptedProcess import run_process

MAX_FACETS = 250_000
MAX_BYTES = 64 * 1024 * 1024
TIMEOUT_SECONDS = 90.0
MEMORY_BYTES = 2 * 1024**3


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def executable() -> Path:
    value = os.environ.get("CADEX_BLENDER_EXECUTABLE", "")
    path = Path(value).expanduser()
    if not value or not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("mesh.blender needs CADEX_BLENDER_EXECUTABLE set to an absolute "
                         "Blender/Cadex executable path; the Cadex shell supplies its own.")
    return path.resolve()


@lru_cache(maxsize=4)
def _binary_digest(path: str, size: int, modified: int) -> str:
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def runtime_identity() -> str:
    binary = executable()
    stat = binary.stat()
    # The executable and our evaluator both affect output, even when the
    # recipe pins the same numeric Blender version. No machine paths are hashed.
    material = _binary_digest(str(binary), stat.st_size, stat.st_mtime_ns)
    material += hashlib.sha256(Path(__file__).with_name("cadex_blender_worker.py").read_bytes()).hexdigest()
    return hashlib.sha256(material.encode()).hexdigest()


def _runtime_root(binary: Path) -> Path:
    for parent in binary.parents:
        if parent.suffix == ".app":
            return parent
    # Linux Blender distributions keep executable, libraries and versioned
    # scripts under one install directory. Never expose all of / or a home.
    parent = binary.parent
    if parent == Path("/usr/bin"):
        return Path("/usr")
    if parent in (Path("/"), Path.home(), Path("/bin")):
        raise ValueError("Install Blender in its own runtime directory.")
    return parent


def sandbox_command(binary: Path, script: Path, request: Path, work: Path) -> list[str]:
    command = [str(binary), "--background", "--factory-startup", "--disable-autoexec",
               "--threads", "1", "--python-exit-code", "1", "--python", str(script),
               "--", str(request), str(work / "output.json")]
    runtime = _runtime_root(binary)
    if sys.platform == "darwin":
        sandbox = Path("/usr/bin/sandbox-exec")
        if not sandbox.is_file():
            raise ValueError("mesh.blender requires macOS sandbox-exec; refusing unsandboxed execution.")
        literal = lambda path: json.dumps(str(path))
        profile = "\n".join([
            "(version 1)", "(deny default)",
            "(allow file-read-metadata)",
            '(allow file-read* (literal "/"))',
            '(allow file-read* (subpath "/System") (subpath "/usr/lib") '
            '(subpath "/usr/share") (subpath "/Library/Apple"))',
            f"(allow file-read* (subpath {literal(runtime)}) "
            f"(literal {literal(script)}) (literal {literal(request)}))",
            f"(allow file-read* file-write* (subpath {literal(work)}))",
            '(allow file-read* file-write* (literal "/dev/null") (literal "/dev/urandom") '
            '(literal "/dev/random"))',
            f"(allow process-exec (literal {literal(binary)}))",
            "(allow sysctl-read)", "(allow mach-lookup)", "(allow signal (target self))",
        ])
        return [str(sandbox), "-p", profile, *command]
    if sys.platform.startswith("linux"):
        sandbox = shutil.which("bwrap")
        if not sandbox:
            raise ValueError("mesh.blender requires bubblewrap (bwrap); refusing unsandboxed execution.")
        wrapper = [sandbox, "--unshare-all", "--die-with-parent", "--new-session",
                   "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
        roots = [Path("/usr"), Path("/lib"), Path("/lib64"), runtime]
        mounted = []
        for root in roots:
            if root.exists() and not any(root == old or old in root.parents for old in mounted):
                wrapper += ["--ro-bind", str(root), str(root)]
                mounted.append(root)
        wrapper += ["--ro-bind", str(script), str(script),
                    "--ro-bind", str(request), str(request),
                    "--bind", str(work), str(work), "--chdir", str(work)]
        return [*wrapper, *command]
    raise ValueError("mesh.blender has no OS sandbox on this platform; refusing execution.")


def validate_geometry(data):
    """Validate the untrusted child result before giving triangles to Mesh."""
    if not isinstance(data, dict):
        raise ValueError("Blender must return a mesh record.")
    vertices, triangles = data.get("vertices"), data.get("triangles")
    if not isinstance(vertices, list) or not 3 <= len(vertices) <= MAX_FACETS * 3:
        raise ValueError("Blender output needs 3..750000 vertices.")
    if not isinstance(triangles, list) or not 1 <= len(triangles) <= MAX_FACETS:
        raise ValueError("Blender output needs 1..250000 triangles.")
    for point in vertices:
        if (not isinstance(point, (list, tuple)) or len(point) != 3 or
                any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e9 for v in point)):
            raise ValueError("Blender output coordinates must be finite millimetres within +/-1e9.")
    for triangle in triangles:
        if (not isinstance(triangle, (list, tuple)) or len(triangle) != 3 or
                any(type(i) is not int or not 0 <= i < len(vertices) for i in triangle) or
                len(set(triangle)) != 3):
            raise ValueError("Blender output has an invalid triangle index.")
        a, b, c = (vertices[i] for i in triangle)
        u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
        if sum(x*x for x in cross) == 0:
            raise ValueError("Blender output contains a zero-area triangle.")
    return {"vertices": vertices, "triangles": triangles}


def run_recipe(root: Path, source: str, properties: dict, inputs: dict) -> dict:
    binary = executable()
    identity = runtime_identity()
    request_data = {"schema": "cadex-blender-recipe-v1", "source": source,
                    "version": properties["version"], "seed": properties["seed"],
                    "values": properties["values"], "inputs": inputs}
    encoded = _json(request_data)
    if len(encoded.encode()) > MAX_BYTES:
        raise ValueError("Blender recipe inputs exceed 64 MiB; use a coarser tessellation.")
    key = hashlib.sha256((identity + encoded).encode()).hexdigest()
    job = (root / "blender" / key).resolve()
    accepted = job / "validated.json"
    if accepted.is_file():
        return validate_geometry(json.loads(accepted.read_text()))
    job.mkdir(parents=True, exist_ok=True)
    # Only scratch is writable by the child, not its inputs or the validated
    # cache. A recipe cannot poison another recipe or any project artifact.
    work = job / "scratch"
    work.mkdir()
    request = job / "request.json"
    request.write_text(encoded)
    script = Path(__file__).with_name("cadex_blender_worker.py").resolve()
    command = sandbox_command(binary, script, request, work)
    environment = {"HOME": str(work), "TMPDIR": str(work), "TMP": str(work),
                   "TEMP": str(work), "PATH": "/usr/bin:/bin", "LANG": "C",
                   "PYTHONNOUSERSITE": "1", "PYTHONHASHSEED": "0",
                   "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
    process = run_process(command, cwd=work, environment=environment,
                          cancellation_check=None, timeout_seconds=TIMEOUT_SECONDS,
                          memory_limit_bytes=MEMORY_BYTES, own_process_group=False)
    if not process.get("started") or process.get("returncode") != 0:
        reason = ("timed out" if process.get("timed_out") else
                  "exceeded 2 GiB" if process.get("memory_exceeded") else
                  process.get("error") or process.get("stderr") or process.get("stdout"))
        raise ValueError(f"Blender recipe failed (exit {process.get('returncode')}): "
                         f"{str(reason)[-4000:]} {process.get('stdout', '')[-2000:]}")
    output = work / "output.json"
    if output.is_symlink() or not output.is_file() or output.stat().st_size > MAX_BYTES:
        raise ValueError("Blender did not produce a bounded mesh output.")
    geometry = validate_geometry(json.loads(output.read_text()))
    accepted.write_text(_json(geometry))
    return geometry
