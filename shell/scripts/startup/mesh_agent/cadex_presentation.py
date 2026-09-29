# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The studio hero and concept sheet, in the Training editor (cadex ADR-452).

``cadex render`` (and a walk, per revision) leaves the project's
presentation under ``review/render/``: ``hero.png``, the 1024 px studio
image, and ``sheet.png``, the concept sheet, beside the ``summary.json``
that names them (docs/CLI.md, ADR-430). The review dashboard shows them;
this module shows the same files in the app and can make them:

- **Which render** is the dashboard's rule: the accepted revision's own
  ``review/render/<revision>/`` when it drew a sheet, else the project's
  last ``review/render/``, a render with a sheet before one without. The
  panel says whether it is of this design or an older one, so a sheet
  drawn for an earlier design never reads as this one.
- **Render Now** runs the engine's studio (``CadexStudio.py``, kind
  ``render``, through ``cadex_studio``) on the accepted revision the
  viewport shows, with the measured fit and inventory, into
  ``review/render/`` -- the files ``cadex render`` writes, drawn by the
  same code. Seconds of work, so it runs on a worker thread.
- **Open Hero / Open Sheet** hand the PNG to the system's viewer.

Reading is file-only and keyed on ``(mtime, size)`` through ``cadex_runs``.
"""

import os
import threading
import time
import traceback

import bpy
from bpy.types import Operator, Panel

from . import cadex_runs

PRESENTATION_DIR = "review/render"
PRESENTATION_FILES = ("hero", "sheet")
#: Seconds between checks for a finished render.
POLL_SECONDS = 0.25
#: The hero thumbnail's size in the panel, in UI units.
THUMBNAIL_SCALE = 9.0

#: What the last Render Now did: ``{"state": "rendering"|"done"|"failed",
#: "error", "seconds", "root"}``. Session state, one render at a time.
_status = {}
_previews = None


def _source(root, accepted):
    """``(relative directory, summary)`` of the render to present, or ``(None, None)``."""
    candidates = [PRESENTATION_DIR]
    if len(accepted) == 64 and accepted.isalnum():
        candidates.insert(0, PRESENTATION_DIR + "/" + accepted)
    found = []
    for relative in candidates:
        summary = cadex_runs._read_json(os.path.join(root, *relative.split("/"), "summary.json"))
        if summary and isinstance(summary.get("revision"), str):
            found.append((relative, summary))
    with_sheet = [item for item in found if isinstance(item[1].get("sheet"), dict)]
    return (with_sheet or found or [(None, None)])[0]


def presentation(root):
    """The render to present: revision, relation, files and sheet numbers.

    ``files`` maps ``hero``/``sheet`` to an absolute path, offered only when
    the summary names the image at its own path and the file is there.
    """
    accepted = cadex_runs.accepted_revision(root) if root else ""
    relative, summary = _source(root or "", accepted)
    if summary is None:
        return {"available": False,
                "reason": "No render yet: Render Now draws the hero and the sheet."}
    files = {}
    for key in PRESENTATION_FILES:
        block = summary.get(key)
        path = os.path.join(root, *relative.split("/"), key + ".png")
        if isinstance(block, dict) and block.get("path") == relative + "/" + key + ".png" \
                and os.path.isfile(path):
            files[key] = path
    revision = summary["revision"]
    relation = ("unknown" if not accepted else
                "current" if revision == accepted else "historical")
    return {"available": bool(files), "revision": revision, "relation": relation,
            "source": relative, "files": files,
            "numbers": (summary.get("sheet") or {}).get("numbers") or {}}


def render_request(root, accepted, clearance, inventory_value):
    """The studio request Render Now sends; what ``cadex render`` draws."""
    revision = str(accepted.get("revision") or "")
    return {"kind": "render",
            "reply": {"ok": True, "revision": revision, "accepted_revision": revision,
                      "digest": accepted.get("digest") or None,
                      "display": accepted.get("display") or {}},
            "clearance": clearance, "inventory_value": inventory_value,
            "out_dir": os.path.join(root, *PRESENTATION_DIR.split("/")),
            "project_root": root, "relative_dir": PRESENTATION_DIR}


def _render(root, client, module_dir, accepted):
    """Worker thread (or the gate): one studio render; returns its result."""
    from . import cadex_backend, cadex_studio
    try:
        clearance, inventory = cadex_backend.measured_values(
            root, client, str(accepted.get("revision") or ""))
    except Exception:
        return {"ok": False, "error": traceback.format_exc(limit=2)}
    return cadex_studio.run(render_request(root, accepted, clearance, inventory),
                            module_dir=module_dir)


def _context(scene):
    """Main thread: what a render needs, or an error sentence."""
    from . import cadex_backend
    root, client, module_dir = cadex_backend.measurement_context(scene)
    accepted = cadex_backend.last_accepted(root)
    if not accepted.get("revision") or not accepted.get("display"):
        return None, "Nothing accepted to render yet: build the model first."
    return (root, client, module_dir, accepted), None


def render_now(scene):
    """Render on the calling thread. For the gate, where timers do not fire."""
    context, error = _context(scene)
    if context is None:
        return {"ok": False, "error": error}
    return _render(*context)


def _redraw():
    manager = getattr(bpy.context, "window_manager", None)
    for window in getattr(manager, "windows", ()) or ():
        for area in window.screen.areas:
            if area.type == 'CADEX_TRAINING':
                area.tag_redraw()


class CADEX_TRAINING_OT_render_presentation(Operator):
    """Draw the studio hero and concept sheet of the accepted design, as cadex render does"""

    bl_idname = "mesh_agent.render_presentation"
    bl_label = "Render Now"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return _status.get("state") != "rendering"

    def execute(self, context):
        prepared, error = _context(context.scene)
        if prepared is None:
            self.report({'WARNING'}, error)
            return {'CANCELLED'}
        started = time.perf_counter()
        _status.clear()
        _status.update(state="rendering", root=prepared[0], error="", seconds=None)
        box = {}

        def worker():
            try:
                box["result"] = _render(*prepared)
            except Exception:
                box["result"] = {"ok": False, "error": traceback.format_exc(limit=2)}

        thread = threading.Thread(target=worker, name="cadex-presentation", daemon=True)
        thread.start()

        def poll():
            if thread.is_alive():
                return POLL_SECONDS
            result = box.get("result") or {}
            _status.update(state="done" if result.get("ok") else "failed",
                           error=str(result.get("error") or ""),
                           seconds=time.perf_counter() - started)
            _redraw()
            return None

        bpy.app.timers.register(poll, first_interval=POLL_SECONDS)
        _redraw()
        return {'FINISHED'}


class CADEX_TRAINING_OT_open_presentation(Operator):
    """Open this image in the system's viewer"""

    bl_idname = "mesh_agent.open_presentation"
    bl_label = "Open"
    bl_options = {'INTERNAL'}

    kind: bpy.props.EnumProperty(items=[("hero", "Hero", ""), ("sheet", "Sheet", "")])

    def execute(self, context):
        from . import cadex_backend
        path = presentation(cadex_backend.project_root(context.scene))
        path = (path.get("files") or {}).get(self.kind)
        if not path:
            self.report({'WARNING'}, "There is no {:s} on disk.".format(self.kind))
            return {'CANCELLED'}
        bpy.ops.wm.path_open(filepath=path)
        return {'FINISHED'}


def _thumbnail(path):
    """A preview icon for ``path``, reloaded when the file changes."""
    global _previews
    if _previews is None:
        from bpy.utils import previews
        _previews = previews.new()
    try:
        stat = os.stat(path)
    except OSError:
        return 0
    key = "{:s}:{:d}:{:d}".format(path, stat.st_mtime_ns, stat.st_size)
    if key not in _previews:
        _previews.load(key, path, 'IMAGE')
    return _previews[key].icon_id


class CADEX_TRAINING_PT_presentation(Panel):
    """The design's studio hero and concept sheet, as the review dashboard shows them."""

    bl_space_type = 'CADEX_TRAINING'
    bl_region_type = 'WINDOW'
    bl_label = "Renders"

    def draw(self, context):
        from . import cadex_backend
        layout = self.layout
        root = cadex_backend.project_root(context.scene)
        shown = presentation(root)
        if shown["available"]:
            relation = {"current": "this design",
                        "historical": "an older design"}.get(shown["relation"], "unknown design")
            head = layout.row()
            head.label(text="{:s} ({:s})".format(relation, shown["revision"][:12]),
                       icon='CHECKMARK' if shown["relation"] == "current" else 'TIME')
            hero = shown["files"].get("hero")
            if hero:
                icon = _thumbnail(hero)
                if icon:
                    layout.template_icon(icon_value=icon, scale=THUMBNAIL_SCALE)
            buttons = layout.row(align=True)
            for key in PRESENTATION_FILES:
                if key in shown["files"]:
                    op = buttons.operator(CADEX_TRAINING_OT_open_presentation.bl_idname,
                                          text="Open " + key.title(), icon='IMAGE_DATA')
                    op.kind = key
            numbers = shown["numbers"]
            if numbers:
                column = layout.column(align=True)
                column.enabled = False
                for key in sorted(numbers)[:8]:
                    value = numbers[key]
                    column.label(text="{:s}  {:s}".format(
                        key, "-" if value is None else "{:.4g}".format(value)
                        if isinstance(value, (int, float)) else str(value)))
        else:
            note = layout.row()
            note.enabled = False
            note.label(text=shown["reason"])
        state = _status.get("state") if _status.get("root") == root else None
        row = layout.row()
        row.operator(CADEX_TRAINING_OT_render_presentation.bl_idname,
                     text="Rendering..." if state == "rendering" else "Render Now",
                     icon='RENDER_STILL')
        if state == "failed":
            alert = layout.row()
            alert.alert = True
            alert.label(text=(_status.get("error") or "the render failed")[:160], icon='ERROR')
        elif state == "done" and _status.get("seconds") is not None:
            note = layout.row()
            note.enabled = False
            note.label(text="rendered in {:.1f} s".format(_status["seconds"]))


classes = (CADEX_TRAINING_OT_render_presentation, CADEX_TRAINING_OT_open_presentation,
           CADEX_TRAINING_PT_presentation)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    global _previews
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    if _previews is not None:
        from bpy.utils import previews
        previews.remove(_previews)
        _previews = None
    _status.clear()
