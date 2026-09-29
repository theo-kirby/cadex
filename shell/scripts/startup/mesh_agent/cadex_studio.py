# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
The engine's shared client code, reached across a process boundary.

The engine payload ships two things every front end needs and this add-on
may not import (cadex ADR-445 to ADR-448):

- ``Mod/cadex/CadexStudio.py`` -- the studio renderer behind ``look``, and
  the ``fit`` and ``inventory`` blocks a build reply carries. It is RUN, as a
  child process of the payload's own Python, with one JSON request file
  (``cadex-studio-request-v1``, docs/INTEGRATION.md); one JSON line comes
  back on stdout.
- ``Mod/cadex/CadexAgentGuidance.md`` -- the design language and the rules
  for proving a design with measurements. It is READ, as text, and pasted
  into the system prompt with this add-on's tool names filled in.

Nothing here touches ``bpy``: every function is safe on a worker thread.
"""

import json
import os
import re
import subprocess
import sys
import tempfile

#: A render is ~12 s on a large robot and a look a few seconds per view; a
#: process that runs past this has hung.
STUDIO_TIMEOUT_SECONDS = 300
REQUEST_SCHEMA = "cadex-studio-request-v1"
STUDIO_SCRIPT = "CadexStudio.py"
GUIDANCE_FILE = "CadexAgentGuidance.md"
GUIDANCE_MARKER = "<!-- guidance -->\n"

#: This add-on's tool name for every placeholder the guidance uses.
SHELL_TOOL_NAMES = {
    "look": "look",
    "inspect": "inspect_model",
    "write_script": "write_script",
    "edit_script": "edit_script",
    "set_params": "set_params",
    "rebuild": "rebuild_model",
}


def engine_module_dir():
    """The engine's ``Mod/cadex`` directory this install resolves, or ``""``."""
    from . import cadex_backend
    try:
        _freecadcmd, module_dir = cadex_backend.resolved_engine()
    except Exception:
        return ""
    return module_dir or ""


def studio_python(module_dir):
    """The payload's own interpreter, else this process's.

    A payload lays out ``bin/python`` beside ``Mod/cadex``. A development
    engine (a source tree named by preference) has none, and the studio
    needs only the standard library, so Blender's Python serves.
    """
    payload_python = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(module_dir))), "bin", "python")
    if os.path.isfile(payload_python) and os.access(payload_python, os.X_OK):
        return payload_python
    return sys.executable


def run(request, module_dir=None, timeout=STUDIO_TIMEOUT_SECONDS):
    """Run one studio request; always returns a result dict with ``ok``.

    ``request`` is everything but ``schema``. A refusal from the studio is
    returned as it came; a process that could not be run, crashed or hung
    becomes ``{"ok": False, "error": ...}`` in the same shape.
    """
    module_dir = module_dir or engine_module_dir()
    script = os.path.join(module_dir, STUDIO_SCRIPT) if module_dir else ""
    if not script or not os.path.isfile(script):
        return {"ok": False, "error": "The engine payload has no {:s}; rebuild the "
                "engine (pixi run build-engine) or update Cadex.".format(STUDIO_SCRIPT)}
    handle, path = tempfile.mkstemp(prefix="cadex-studio-", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(dict(request, schema=REQUEST_SCHEMA), stream)
        try:
            done = subprocess.run([studio_python(module_dir), script, path],
                                  capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "The studio ran past {:d} s and was stopped."
                    .format(timeout)}
        except OSError as exc:
            return {"ok": False, "error": "The studio could not start: {:s}".format(str(exc))}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    try:
        result = json.loads(lines[-1])
    except (IndexError, ValueError):
        return {"ok": False, "error": "The studio exited {:d} with no result: {:s}".format(
            done.returncode, (done.stderr or "").strip()[-400:])}
    if not isinstance(result, dict) or "ok" not in result:
        return {"ok": False, "error": "The studio's result has no ok field."}
    return result


def guidance(module_dir=None, names=None):
    """The engine's agent guidance with this add-on's tool names filled in.

    Raises ``ValueError`` when the file is missing, has no marker, or uses a
    placeholder this add-on does not fill: an engine newer than the shell.
    """
    module_dir = module_dir or engine_module_dir()
    path = os.path.join(module_dir, GUIDANCE_FILE) if module_dir else ""
    try:
        with open(path, encoding="utf-8") as stream:
            text = stream.read()
    except OSError as exc:
        raise ValueError("no agent guidance in the engine payload: {:s}".format(str(exc)))
    _head, marker, body = text.partition(GUIDANCE_MARKER)
    if not marker:
        raise ValueError("{:s} has no guidance marker".format(path))
    for placeholder, name in (names or SHELL_TOOL_NAMES).items():
        body = body.replace("{{" + placeholder + "}}", name)
    left = sorted(set(re.findall(r"\{\{(\w+)\}\}", body)))
    if left:
        raise ValueError("{:s} uses placeholders this shell does not fill: {:s}".format(
            path, ", ".join(left)))
    return body
