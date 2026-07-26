# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Mesh agent tools.

The agent never mutates the scene directly: it writes and edits the model
script (see model.py), and the scene is rebuilt from it. Definitions are
served to Claude Code through the MCP shim (see ``bridge.py``); executors run
on Blender's main thread only. Each executor returns ``(content, is_error)``
where content is a list of MCP content blocks (``{"type": "text", ...}`` or
``{"type": "image", ...}``).
"""

import json
import traceback

MAX_RESULT_CHARS = 4096

# describe_cad_api serves reference material the model asked for by name;
# truncating a domain's signatures at 4 KB would defeat its purpose.
_API_DOMAIN_CHARS = 16384

# Tools whose execution mutates the scene (drives per-turn undo batching).
MUTATING_TOOLS = {"write_script", "set_params", "edit_script", "rebuild_model"}

# Tools that reach the cadex engine; these are preflighted so a missing
# engine reports itself once, in a sentence, rather than as a traceback from
# deep inside process spawning. (Before ADR-030 this set was conditional on
# the scene's mode; there is one backend now.)
_ENGINE_TOOLS = {"get_script", "write_script", "set_params",
                 "edit_script", "inspect_model", "describe_cad_api",
                 "scene_summary", "rebuild_model", "import_geometry"}

TOOL_DEFS = [
    {
        "name": "get_script",
        "description": (
            "Return the current model script plus the declared parameters with "
            "their current values. Call this before editing an existing model."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "write_script",
        "description": (
            "Replace the entire model script and rebuild the scene from it. "
            "The script is the single source of truth for the model: it runs "
            "top-to-bottom with `bpy` available after the Model collection is "
            "cleared, so it must be deterministic and self-contained. Declare "
            "user-tunable parameters at the top with mesh_model.params(). The "
            "result reports the rebuilt objects, the parameters, and script "
            "stdout — or the traceback if the script failed (fix and rewrite)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string",
                            "description": "Full Python source of the model script."},
            },
            "required": ["content"],
        },
    },
    {
        "name": "set_params",
        "description": (
            "Set one or more declared parameter values (the same values the "
            "user's sliders control) and rebuild the scene. Use this instead "
            "of editing the script when only values change."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "params": {
                    "type": "object",
                    "description": "Map of parameter id to new value.",
                    "additionalProperties": True,
                },
            },
            "required": ["params"],
        },
    },
    {
        "name": "edit_script",
        "description": (
            "Cadex mode only. Apply exact string replacements to the "
            "project script instead of rewriting it whole, then rebuild. "
            "Each `old` must occur EXACTLY ONCE in the script or the whole "
            "edit is refused — include enough surrounding text to be "
            "unambiguous. Prefer this over write_script for small changes: "
            "it cannot accidentally drop the parts of the script you did "
            "not mean to touch."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "replacements": {
                    "type": "array",
                    "description": "Applied in order.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "old": {"type": "string",
                                    "description": "Exact text to replace; "
                                                   "must occur exactly once."},
                            "new": {"type": "string",
                                    "description": "Replacement text."},
                        },
                        "required": ["old", "new"],
                    },
                },
            },
            "required": ["replacements"],
        },
    },
    {
        "name": "rebuild_model",
        "description": (
            "Re-run the script the engine already holds, from scratch, and "
            "re-derive the declared parameters, their values and the geometry "
            "from it. Use it when the model and the engine have drifted: the "
            "scene does not match what get_script reports, the sliders show "
            "parameters the script no longer declares, or a set_params call "
            "failed for a parameter you did not send. It sends no script, so "
            "it cannot lose work — but it also cannot fix a script that is "
            "wrong; write_script does that."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "inspect_model",
        "description": (
            "Cadex mode only. Ask the engine about the model it holds: "
            "scope 'script' for the source, parameters and revisions, "
            "'document' for the published objects, 'object' with a target "
            "for one object's properties, 'output' for one accepted output's "
            "measured facts (volume, area, bounds, centre of mass, face and "
            "edge counts — omit the target to list every output), 'assets' "
            "for the external mesh files stored for mesh.import_file(). This "
            "is engine truth, unlike the tessellated copies in the Blender "
            "scene."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {"type": "string",
                          "description": "script | document | object | output "
                                         "| assets"},
                "target": {"type": "string",
                           "description": "Object name for scope=object; "
                                          "output name for scope=output."},
                "path": {"type": "string",
                         "description": "Sub-path within the scope, e.g. "
                                        "/revisions or /params."},
            },
            "required": ["scope"],
        },
    },
    {
        "name": "describe_cad_api",
        "description": (
            "Cadex mode only. Return the cadex engine's authoring contract "
            "for xscript project scripts: how a script must be shaped, and "
            "which functions each modelling domain offers. Call it with no "
            "arguments first for the overview and the function names, then "
            "with a domain name for that domain's full signatures, defaults "
            "and descriptions. This is served live by the engine, so it is "
            "always the truth about the version you are talking to — never "
            "guess an API from memory."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "One domain (e.g. part, mesh, assembly, "
                                   "partdesign, sketcher). Omit for the "
                                   "overview.",
                },
            },
        },
    },
    {
        "name": "get_attached_image",
        "description": (
            "Return an image the user attached to the chat, by index. The "
            "user's message notes which indices were attached. Use attached "
            "images as visual reference for the model you build."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer",
                          "description": "Attachment index from the user's message."},
            },
            "required": ["index"],
        },
    },
    {
        "name": "scene_summary",
        "description": (
            "Return a JSON summary of the current scene: every object with its type, "
            "transform, dimensions, modifier stack and materials. Call this to verify "
            "what the model script actually built."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "viewport_screenshot",
        "description": (
            "Render the current 3D viewport to a small PNG image and return it, so you "
            "can visually verify the scene. Unavailable when Blender runs headless; "
            "fall back to scene_summary in that case."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_size": {
                    "type": "integer",
                    "description": "Longest edge of the returned image in pixels (default 768).",
                },
            },
        },
    },
    {
        "name": "export_stl",
        "description": (
            "Export model parts as STL files for 3D printing, one file per "
            "object (binary STL, 1 Blender unit = 1 STL unit). By default "
            "exports every mesh object in the Model collection to a directory "
            "beside the .blend file (or a temporary directory when unsaved). "
            "Returns the written file paths and triangle counts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "objects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Object names to export (default: all mesh "
                                   "objects in the Model collection).",
                },
                "directory": {
                    "type": "string",
                    "description": "Output directory (created if missing).",
                },
            },
        },
    },
    {
        "name": "import_geometry",
        "description": (
            "Copy an external mesh file (STL, OBJ or PLY) from anywhere on "
            "disk into the model's asset store, so the script can import it "
            "with mesh.import_file(). Returns the stored name — pass that "
            "name, not the original path. Use this when the user points you "
            "at a component file; use inspect_model with scope 'assets' to "
            "see what is already stored (the user can also drop files in "
            "through File > Import Geometry)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string",
                         "description": "Path to the STL/OBJ/PLY file to import."},
                "name": {"type": "string",
                         "description": "Optional name to store it under "
                                        "(same format suffix; default: the "
                                        "source file's name). Re-using a "
                                        "stored name replaces that asset."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "focus_view",
        "description": (
            "Frame the named objects (or the whole scene if none are given) in the 3D "
            "viewport so the user can see them. No-op when Blender runs headless."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "objects": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
]


class Pending:
    """A tool call whose result arrives later.

    Returned by :func:`execute` instead of ``(content, is_error)`` when the
    work must not block Blender's main thread — today, the two cadex
    modeling tools, which run a user script inside the engine. The agent's
    drain loop polls it; :meth:`poll` returns None while in flight and the
    usual ``(content, is_error)`` pair when finished.
    """

    __slots__ = ("_poll",)

    def __init__(self, poll):
        self._poll = poll

    def poll(self):
        return self._poll()

    def wait(self, interval=0.01):
        """Block until the result is ready. Background mode and tests."""
        import time
        while True:
            outcome = self.poll()
            if outcome is not None:
                return outcome
            time.sleep(interval)


def list_tools():
    """Static tool definitions, safe to call from any thread."""
    return TOOL_DEFS


def _text(message):
    return [{"type": "text", "text": message}]


def _truncate(text, limit=MAX_RESULT_CHARS):
    if len(text) > limit:
        return text[:limit] + "\n[... output truncated ...]"
    return text


def execute(name, tool_input, agent=None):
    """Execute a tool on the main thread. Returns (content_blocks, is_error).
    ``agent`` is the calling Agent, for tools that need per-session state
    (attachments)."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return _text("Unknown tool: {:s}".format(name)), True
    if name in _ENGINE_TOOLS:
        from . import cadex_backend
        ok, reason, remedy = cadex_backend.preflight()
        if not ok:
            # A sentence the model can act on and relay, not a traceback
            # from deep inside process spawning -- and the same sentence in
            # the transcript, so the user is not waiting on a silence.
            _status(reason)
            return _text(reason + " " + remedy
                         + " Tell the user this; do not retry."), True
    try:
        if name in _AGENT_HANDLERS:
            return handler(tool_input, agent)
        return handler(tool_input)
    except Exception:
        return _text(_truncate(traceback.format_exc())), True


def _cancellation_check(agent):
    """The agent's per-turn cancel flag as a zero-argument predicate.

    Bound into the cadexd client, which polls it every 50 ms and forwards a
    ``cancel`` frame, so Escape during a long rebuild reaches the engine.
    """
    if agent is None:
        return None
    return agent.cancellation_check()


def execute_blocking(name, tool_input, agent=None):
    """:func:`execute`, resolving a :class:`Pending` before returning.

    For callers outside the agent's drain loop (tests, background mode).
    """
    result = execute(name, tool_input, agent=agent)
    return result.wait() if isinstance(result, Pending) else result


def _tool_get_script(_tool_input):
    import bpy
    from . import cadex_backend

    ok, report = cadex_backend.get_script_report(bpy.context.scene)
    return _text(_truncate(report)), not ok


def _deferred(started, render):
    """Wrap a cadex_backend Lifecycle (or an immediate outcome) for the agent.

    ``render(ok, report)`` turns the engine's verdict into MCP content.
    """
    from . import cadex_backend

    if not isinstance(started, cadex_backend.Lifecycle):
        return render(*started)

    def poll():
        outcome = started.poll()
        return None if outcome is None else render(*outcome)

    return Pending(poll)


def _status(message):
    """One line into the chat transcript, for the user rather than the model.

    cadex_backend's failure reports are written for the model: structured,
    detailed, and invisible to the person watching the panel. Without this a
    rejected revision looks exactly like a hang (cadex ADR-024).
    """
    try:
        from .agent import get_agent
        get_agent().history.add("status", message)
    except Exception:
        pass


def _first_line(report, limit=110):
    line = str(report or "").strip().splitlines()[0] if str(report).strip() else ""
    return line if len(line) <= limit else line[:limit - 1] + "\u2026"


def _render_write_script(ok, report):
    if not ok:
        _status("Engine rejected the script: " + _first_line(report))
        return _text(_truncate(
            "The engine REJECTED the script:\n" + report)), True
    return _text(_truncate(report)), False


def _tool_write_script(tool_input, agent=None):
    import bpy
    from . import cadex_backend

    source = tool_input.get("content", "")
    started = cadex_backend.begin_write_script(
        bpy.context.scene, source,
        cancelled=_cancellation_check(agent))
    if not isinstance(started, cadex_backend.Lifecycle):
        # Keep the attempted source visible when the engine never ran -- and
        # marked as not in the model, because it is not.
        cadex_backend.mirror_script_text(source, accepted=False)
    return _deferred(started, _render_write_script)


def _render_set_params(ok, report):
    if not ok:
        _status("Engine rejected the parameter change: " + _first_line(report))
        return _text(_truncate(report)), True
    return _text(_truncate(report)), False


def _tool_set_params(tool_input, agent=None):
    import bpy
    from . import cadex_backend

    updates = tool_input.get("params") or {}
    if not isinstance(updates, dict) or not updates:
        return _text("set_params needs a non-empty `params` object."), True
    return _deferred(
        cadex_backend.begin_set_params(
            bpy.context.scene, updates,
            cancelled=_cancellation_check(agent)),
        _render_set_params)


def _render_rebuild_model(ok, report):
    if not ok:
        _status("Engine could not re-run the stored script: "
                + _first_line(report))
        return _text(_truncate(
            "The engine could not re-run the stored script:\n" + report)), True
    return _text(_truncate(report)), False


def _tool_rebuild_model(_tool_input, agent=None):
    import bpy
    from . import cadex_backend

    return _deferred(
        cadex_backend.begin_rebuild_model(
            bpy.context.scene, cancelled=_cancellation_check(agent)),
        _render_rebuild_model)


def _tool_edit_script(tool_input, agent=None):
    import bpy
    from . import cadex_backend

    return _deferred(
        cadex_backend.begin_edit_script(
            bpy.context.scene, tool_input.get("replacements"),
            cancelled=_cancellation_check(agent)),
        _render_write_script)


def _tool_inspect_model(tool_input):
    import bpy
    from . import cadex_backend

    scope = str(tool_input.get("scope") or "").strip()
    if scope not in {"script", "document", "object", "output", "assets"}:
        return _text("inspect_model scope must be script, document, object, "
                     "output or assets."), True
    args = {"scope": scope}
    for key in ("target", "path"):
        value = str(tool_input.get(key) or "").strip()
        if value:
            args[key] = value
    payload = cadex_backend.inspect(bpy.context.scene, args)
    if payload.get("ok") is not True:
        return _text(_truncate("The engine refused the inspection: "
                               + str(payload.get("error") or payload))), True
    return _text(_truncate(json.dumps(payload.get("value"), indent=1,
                                      sort_keys=True, default=str))), False


def _tool_describe_cad_api(tool_input):
    import bpy
    from . import cadex_backend

    ok, payload = cadex_backend.describe_api(bpy.context.scene)
    if not ok:
        return _text("The engine could not describe its API:\n"
                     + str(payload.get("error") or payload)), True
    domain = str(tool_input.get("domain") or "").strip()
    if not domain:
        return _text(json.dumps(cadex_backend.api_overview(payload),
                                indent=1, sort_keys=True)), False
    found, block = cadex_backend.api_domain(payload, domain)
    if not found:
        return _text(block), True
    return _text(_truncate(json.dumps(block, indent=1, sort_keys=True),
                           _API_DOMAIN_CHARS)), False


def _tool_get_attached_image(tool_input, agent):
    from . import capture

    attachments = agent.attachments if agent is not None else []
    try:
        index = int(tool_input.get("index"))
    except (TypeError, ValueError):
        return _text("get_attached_image needs an integer `index`."), True
    if not 0 <= index < len(attachments):
        return _text("No attachment #{:d}; {:d} image(s) attached this "
                     "session.".format(index, len(attachments))), True
    image_b64, error = capture.image_file_png_base64(attachments[index]["path"])
    if image_b64 is None:
        return _text(error), True
    return [{"type": "image", "data": image_b64, "mimeType": "image/png"}], False


def _tool_scene_summary(_tool_input):
    """The scene, as the engine defines it.

    The Blender objects are tessellated display copies of the engine's
    outputs -- reporting them as "the scene" would invite the model to reason
    about the mirror instead of the model. So this reports engine truth, and
    says what the mirror is separately.
    """
    import bpy
    from . import cadex_backend
    ok, summary = cadex_backend.engine_summary(bpy.context.scene)
    if not ok:
        return _text(_truncate(str(summary))), True
    return _text(_truncate(json.dumps(summary, indent=1, sort_keys=True,
                                      default=str))), False


def _tool_viewport_screenshot(tool_input):
    from . import capture
    max_size = int(tool_input.get("max_size") or 768)
    image_b64, error = capture.screenshot_png_base64(max_size=max_size)
    if image_b64 is None:
        return _text(error), True
    return [{"type": "image", "data": image_b64, "mimeType": "image/png"}], False


def _resolve_objects(names):
    import bpy
    found, missing = [], []
    for name in names:
        obj = bpy.data.objects.get(name)
        (found if obj is not None else missing).append(obj if obj is not None else name)
    return found, missing


def _safe_filename(name):
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def _tool_export_stl(tool_input):
    import os
    import tempfile

    import bpy
    from . import model

    names = tool_input.get("objects") or []
    if names:
        objects, missing = _resolve_objects(names)
        if missing:
            return _text("Objects not found: {:s}".format(
                ", ".join(missing))), True
        non_mesh = [obj.name for obj in objects if obj.type != 'MESH']
        if non_mesh:
            return _text("Not mesh objects: {:s}".format(
                ", ".join(non_mesh))), True
    else:
        collection = bpy.data.collections.get(model.COLLECTION_NAME)
        objects = ([obj for obj in collection.all_objects if obj.type == 'MESH']
                   if collection is not None else [])
        if not objects:
            return _text("Nothing to export: no mesh objects in the Model "
                         "collection."), True

    directory = tool_input.get("directory") or ""
    if not directory:
        if bpy.data.filepath:
            directory = os.path.join(os.path.dirname(bpy.data.filepath), "stl")
        else:
            directory = os.path.join(tempfile.gettempdir(), "mesh_stl")
    directory = os.path.abspath(os.path.expanduser(directory))
    os.makedirs(directory, exist_ok=True)

    view_layer = bpy.context.view_layer
    previous_selection = [obj for obj in view_layer.objects if obj.select_get()]
    previous_active = view_layer.objects.active
    depsgraph = bpy.context.evaluated_depsgraph_get()

    lines = []
    try:
        for obj in objects:
            for other in view_layer.objects:
                other.select_set(False)
            obj.select_set(True)
            view_layer.objects.active = obj
            path = os.path.join(directory,
                                _safe_filename(obj.name) + ".stl")
            result = bpy.ops.wm.stl_export(
                filepath=path,
                export_selected_objects=True,
                apply_modifiers=True,
                global_scale=1.0,
            )
            if 'FINISHED' not in result:
                return _text("STL export failed for {:s}".format(obj.name)), True
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            mesh.calc_loop_triangles()
            triangles = len(mesh.loop_triangles)
            evaluated.to_mesh_clear()
            lines.append("{:s} -> {:s} ({:d} triangles)".format(
                obj.name, path, triangles))
    finally:
        for other in view_layer.objects:
            other.select_set(False)
        for obj in previous_selection:
            try:
                obj.select_set(True)
            except RuntimeError:
                pass
        view_layer.objects.active = previous_active

    return _text(_truncate(
        "Exported {:d} STL file(s):\n".format(len(lines)) + "\n".join(lines))), False


def _tool_import_geometry(tool_input):
    import os

    import bpy
    from . import cadex_backend

    path = str(tool_input.get("path") or "").strip()
    if not path:
        return _text("import_geometry needs the path of an STL, OBJ or PLY "
                     "file."), True
    path = os.path.abspath(os.path.expanduser(path))
    payload = cadex_backend.put_asset(bpy.context.scene, path,
                                      str(tool_input.get("name") or "").strip())
    if payload.get("ok") is not True:
        return _text(_truncate("The engine refused the import: "
                               + str(payload.get("error") or payload))), True
    stored = payload.get("assets") or []
    return _text(
        "Imported {:s} as {:s} ({:d} bytes). Reference it in the script with "
        "mesh.import_file(\"{:s}\").\nAssets now stored: {:s}".format(
            path, str(payload.get("name")), int(payload.get("bytes") or 0),
            str(payload.get("name")),
            ", ".join(str(item.get("name")) for item in stored) or "(none)"),
    ), False


def _tool_focus_view(tool_input):
    import bpy

    if bpy.app.background:
        return _text("No viewport available in background mode"), False

    names = tool_input.get("objects") or []
    if names:
        objects, missing = _resolve_objects(names)
        if not objects:
            return _text("Objects not found: {:s}".format(", ".join(missing))), True
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in set(objects))

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type != 'WINDOW':
                    continue
                with bpy.context.temp_override(window=window, area=area, region=region):
                    if names:
                        bpy.ops.view3d.view_selected()
                    else:
                        bpy.ops.view3d.view_all()
                return _text("View framed"), False
    return _text("No 3D viewport found"), True


_HANDLERS = {
    "get_script": _tool_get_script,
    "write_script": _tool_write_script,
    "set_params": _tool_set_params,
    "edit_script": _tool_edit_script,
    "rebuild_model": _tool_rebuild_model,
    "inspect_model": _tool_inspect_model,
    "describe_cad_api": _tool_describe_cad_api,
    "get_attached_image": _tool_get_attached_image,
    "scene_summary": _tool_scene_summary,
    "viewport_screenshot": _tool_viewport_screenshot,
    "export_stl": _tool_export_stl,
    "import_geometry": _tool_import_geometry,
    "focus_view": _tool_focus_view,
}

# Handlers that additionally receive the calling Agent.
_AGENT_HANDLERS = {"get_attached_image", "write_script", "set_params",
                   "edit_script", "rebuild_model"}
