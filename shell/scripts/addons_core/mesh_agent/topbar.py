# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Cadex top bar: File and Edit, and nothing that says Blender.

The app template blanked the whole upper bar (ADR-037), which took
`File > Open / Save / Save As / Import / Export` with it, and Preferences,
which has no other door in the product -- the model selector is in the chat
header, but the engine path, the tool-call cap and the run budgets are add-on
preferences and were unreachable.

What comes back is two menus, not the bar: the stock bar also carries the
Blender menu (splash, about, system), Render, the workspace tabs and the
scene/view-layer pickers. A CAD app has nothing to render, ships one
workspace, and shows one scene.

The menus live here rather than in `shell/scripts/startup/bl_ui/` for the
reason `spaces.py` gives: `bl_ui` is inherited Blender and conservative,
`mesh_agent` is ours. Nothing upstream is edited -- `install()` swaps the
header's draw at runtime, and only the app template calls it, so the add-on
loaded into a stock Blender session leaves that session's top bar alone.

Almost everything the menus point at is stock: `wm.open_mainfile`,
`wm.save_mainfile` and the rest are the operators Blender ships, and
Import/Export are Blender's own menus, so a format added by an enabled add-on
appears here without this file knowing about it. The document is the `.blend`
(ADR-033): it carries the script mirror, the parameter specs and the engine
project id, so File > Save saves the model.

The exception is `Import Geometry...` (ADR-043), the first non-stock row in
this menu. It has to be ours: stock Import loads a mesh into the *Blender*
scene, which in Cadex is a display mirror of the engine's outputs and not the
model. Importing geometry into the model means putting the file in the engine
project's asset store, which only the engine may write -- so the row calls a
`put_asset` op, and the model then names the stored asset from the script.

`Link Part...` and `Refresh Linked Parts` are its lossless siblings
(ADR-138), and they are ours for the same reason plus one of their own:
what they bring in is not a file at all but *another Cadex model's accepted
output*, pulled straight out of that project's store as the exact solid it
holds. Both go through one op, `link_part`, and refreshing is that op called
again -- so there is one engine surface behind two rows, and the second row
is a loop over the first.

`Export Printable Parts...` is the way back out (cadex ADR-156), and it is
ours for `Import Geometry`'s reason exactly: stock Export writes the Blender
scene, which here is a display mirror, so a slicer would be handed a
tessellation instead of the model. The engine writes the STLs off the
accepted solids, one per part ticked in the Parameters editor, each at its
own origin. Running it twice is where the second operator comes in: the
engine refuses rather than overwriting, and the refusal names the files, so
the Overwrite / Keep Both dialog is built from the answer instead of from a
directory listing this side is not allowed to take.
"""

import bpy
from bpy.types import Menu, Operator

from . import agent as agent_module


class MESH_AGENT_OT_import_asset(Operator):
    bl_idname = "mesh_agent.import_asset"
    bl_label = "Import Geometry"
    bl_description = ("Copy an STL, OBJ or PLY file into this model's assets "
                      "so the script can build with it")

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default="*.stl;*.obj;*.ply",
                                          options={'HIDDEN'})

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from . import cadex_backend

        payload = cadex_backend.put_asset(context.scene, self.filepath)
        history = agent_module.get_agent().history
        if payload.get("ok") is not True:
            report = str(payload.get("error") or payload)
            history.add("status", "Could not import geometry: " + report)
            self.report({'WARNING'}, report.splitlines()[0] if report else
                        "Import failed")
            return {'CANCELLED'}
        # Name the stored asset, because that name -- not the path the user
        # picked -- is what mesh.import_file() takes.
        history.add("status",
                    "Imported {:s} into this model's assets. Ask for it by "
                    "name: mesh.import_file(\"{:s}\").".format(
                        self.filepath, str(payload.get("name") or "")))
        return {'FINISHED'}


#: Candidate output names from the last `Link Part...` pick, and the project
#: they came from. Module state rather than operator properties because the
#: enum step is a *second* operator: Blender's file browser owns the first
#: one's lifetime, and nothing survives it.
_link_pending = {"source": "", "candidates": ()}


def _link_source_from(path):
    """The project root a picked path names, or "".

    A user picks the thing they think of as the other model: its `.blend`.
    That derives its project root exactly as `cadex_backend.project_root`
    does, so the two can never disagree. Picking the `.cadex` directory
    itself, or a file inside it, works too -- somebody who knows where the
    project is should not have to go and find the .blend.
    """
    import os

    path = os.path.abspath(os.path.expanduser(str(path or "")))
    if not path:
        return ""
    if path.endswith(".blend"):
        return os.path.splitext(path)[0] + ".cadex"
    if path.endswith(".cadex") and os.path.isdir(path):
        return path
    parent = os.path.dirname(path)
    if parent.endswith(".cadex") and os.path.isdir(parent):
        return parent
    if os.path.isdir(path):
        return path
    return ""


class MESH_AGENT_OT_link_part(Operator):
    bl_idname = "mesh_agent.link_part"
    bl_label = "Link Part"
    bl_description = ("Bring a part built in another Cadex model into this "
                      "one, as the exact solid that model accepted")

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default="*.blend;*.cadex",
                                          options={'HIDDEN'})

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        from . import cadex_backend

        history = agent_module.get_agent().history
        source = _link_source_from(self.filepath)
        if not source:
            history.add("status",
                        "That is not a Cadex model: pick another model's "
                        ".blend file, or its .cadex project folder.")
            self.report({'WARNING'}, "Not a Cadex model")
            return {'CANCELLED'}

        # Ask with no output named: the refusal is what carries the list of
        # what that project publishes, so one round trip both validates the
        # project and populates the choice.
        payload = cadex_backend.link_part(context.scene, source)
        candidates = [str(item) for item in (payload.get("candidates") or [])]
        if not candidates:
            report = str(payload.get("error") or payload)
            history.add("status", "Could not link a part: " + report)
            self.report({'WARNING'}, report.splitlines()[0] if report else
                        "Link failed")
            return {'CANCELLED'}

        _link_pending["source"] = source
        _link_pending["candidates"] = tuple(candidates)
        return bpy.ops.mesh_agent.choose_linked_part('INVOKE_DEFAULT')


def _pending_candidates(_self, _context):
    return [(name, name, "") for name in _link_pending["candidates"]]


class MESH_AGENT_OT_choose_linked_part(Operator):
    bl_idname = "mesh_agent.choose_linked_part"
    bl_label = "Which part?"
    bl_description = "Choose which of that model's parts to link"

    output: bpy.props.EnumProperty(name="Part", items=_pending_candidates)

    def invoke(self, context, _event):
        if not _link_pending["candidates"]:
            return {'CANCELLED'}
        # One candidate is not a choice; skip the dialog entirely.
        if len(_link_pending["candidates"]) == 1:
            self.output = _link_pending["candidates"][0]
            return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        from . import cadex_backend

        history = agent_module.get_agent().history
        source = _link_pending["source"]
        output = str(self.output or "")
        if not source or not output:
            return {'CANCELLED'}

        payload = cadex_backend.link_part(context.scene, source, output=output)
        if payload.get("ok") is not True:
            report = str(payload.get("error") or payload)
            history.add("status", "Could not link a part: " + report)
            self.report({'WARNING'}, report.splitlines()[0] if report else
                        "Link failed")
            return {'CANCELLED'}
        name = str(payload.get("name") or "")
        # Name the stored container, because that name -- not the project the
        # user picked -- is what part.import_part() takes.
        history.add("status",
                    "Linked {:s} from {:s}. Ask for it by name: "
                    "part.import_part(\"{:s}\").".format(
                        output, source, name))
        return {'FINISHED'}


class MESH_AGENT_OT_refresh_linked_parts(Operator):
    bl_idname = "mesh_agent.refresh_linked_parts"
    bl_label = "Refresh Linked Parts"
    bl_description = ("Re-pull every part this model links from another "
                      "model, and rebuild if any of them moved")

    def execute(self, context):
        from . import cadex_backend

        history = agent_module.get_agent().history
        ok, report = cadex_backend.refresh_linked_parts(context.scene)
        history.add("status", report or "Nothing to refresh.")
        if not ok:
            self.report({'WARNING'},
                        (report or "Refresh failed").splitlines()[0])
            return {'CANCELLED'}
        return {'FINISHED'}


#: What an export refused for a collision: the conflict dialog's whole input.
_export_pending = {"files": ()}


def _report_export(operator, payload):
    """Land one export reply in both channels. Returns the operator result.

    Both, not one: the status bar is where the user is looking, and the
    history is where the *model* is looking — an AI asked "did that print
    job come out" has no other way to know.
    """
    history = agent_module.get_agent().history
    if payload.get("ok") is not True:
        report = str(payload.get("error") or payload)
        history.add("status", "Could not export printable parts: " + report)
        operator.report({'WARNING'},
                        report.splitlines()[0] if report else "Export failed")
        return {'CANCELLED'}
    files = [str(item.get("file") or "") for item in
             list(payload.get("files") or []) if isinstance(item, dict)]
    message = "Wrote {:d} STL file(s) into {:s}/: {:s}.".format(
        len(files), str(payload.get("directory") or "print"), ", ".join(files))
    history.add("status", message)
    operator.report({'INFO'}, message)
    return {'FINISHED'}


class MESH_AGENT_OT_export_printable(Operator):
    bl_idname = "mesh_agent.export_printable"
    bl_label = "Export Printable Parts"
    bl_description = ("Write one STL per part marked printable, at its own "
                      "origin, into this model's print folder")

    # No REGISTER/UNDO: this writes the engine's project store, not the
    # scene, so there is nothing for Ctrl-Z to give back.

    def execute(self, context):
        from . import cadex_backend

        payload = cadex_backend.export_printable(context.scene)
        if str(payload.get("failure_code") or "") == "PRINT_FILES_EXIST":
            observed = payload.get("observed")
            existing = (observed or {}).get("existing") if isinstance(
                observed, dict) else None
            _export_pending["files"] = tuple(str(name) for name in
                                             (existing or ()))
            # The refusal IS the question: it came back naming the files, so
            # one round trip both checked and populated the dialog.
            return bpy.ops.mesh_agent.resolve_print_conflict('INVOKE_DEFAULT')
        return _report_export(self, payload)


class MESH_AGENT_OT_resolve_print_conflict(Operator):
    bl_idname = "mesh_agent.resolve_print_conflict"
    bl_label = "These parts are already exported"
    bl_description = "Overwrite the STLs already in print/, or keep both"

    conflict: bpy.props.EnumProperty(
        name="Then",
        items=(('overwrite', "Overwrite",
                "Replace the files already in print/"),
               ('keep_both', "Keep Both",
                "Write beside them, as <name>-002.stl")),
        default='overwrite',
    )

    def invoke(self, context, _event):
        if not _export_pending["files"]:
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, _context):
        layout = self.layout
        layout.label(text="Already in print/:", icon='ERROR')
        for name in _export_pending["files"]:
            row = layout.row()
            row.enabled = False
            row.label(text=name)
        layout.prop(self, "conflict", expand=True)

    def execute(self, context):
        from . import cadex_backend

        if not _export_pending["files"]:
            return {'CANCELLED'}
        _export_pending["files"] = ()
        return _report_export(
            self,
            cadex_backend.export_printable(context.scene,
                                           conflict=str(self.conflict)))


class CADEX_MT_file(Menu):
    bl_label = "File"

    def draw(self, context):
        layout = self.layout

        # INVOKE_DEFAULT, not EXEC: `wm.read_homefile`'s invoke is what raises
        # the "Save changes?" dialog. And `app_template` is deliberately left
        # unset -- unset means "the template already in force" (`wm_files.cc`,
        # `wm_homefile_read_exec`), so New lands back in the Cadex layout
        # rather than in stock Blender.
        layout.operator_context = 'INVOKE_DEFAULT'
        layout.operator("wm.read_homefile", text="New", icon='FILE_NEW')

        layout.operator_context = 'INVOKE_AREA'
        layout.operator("wm.open_mainfile", text="Open...", icon='FILE_FOLDER')
        layout.menu("TOPBAR_MT_file_open_recent")
        layout.operator("wm.revert_mainfile")

        layout.separator()

        # Save on an unsaved file has no path to write to, so it has to open
        # the browser; on a saved one it must not. Stock does the same.
        layout.operator_context = ('EXEC_AREA' if context.blend_data.is_saved
                                   else 'INVOKE_AREA')
        layout.operator("wm.save_mainfile", text="Save", icon='FILE_TICK')

        layout.operator_context = 'INVOKE_AREA'
        layout.operator("wm.save_as_mainfile", text="Save As...")
        layout.operator("wm.save_as_mainfile", text="Save Copy...").copy = True

        layout.separator()

        # Ours, and first: importing *into the model* is the thing a CAD user
        # means by Import here. The stock menus below load into the Blender
        # scene, which is the display mirror (ADR-043).
        layout.operator("mesh_agent.import_asset", text="Import Geometry...",
                        icon='IMPORT')
        # ...and its lossless sibling: a part from another Cadex model, as the
        # solid that model accepted rather than a mesh of it (ADR-138).
        layout.operator("mesh_agent.link_part", text="Link Part...",
                        icon='LINKED')
        layout.operator("mesh_agent.refresh_linked_parts",
                        text="Refresh Linked Parts", icon='FILE_REFRESH')
        # ...and the way out: the parts marked printable in the Parameters
        # editor, as one STL each, written by the engine off the accepted
        # solid rather than off this scene's display mirror (cadex ADR-156).
        # Ours for Import Geometry's reason exactly — stock Export writes the
        # mirror, and the mirror is not the model.
        layout.operator("mesh_agent.export_printable",
                        text="Export Printable Parts...", icon='EXPORT')

        layout.separator()

        layout.menu("TOPBAR_MT_file_import", icon='IMPORT')
        layout.menu("TOPBAR_MT_file_export", icon='EXPORT')

        layout.separator()

        layout.operator("wm.quit_blender", text="Quit", icon='QUIT')


class CADEX_MT_edit(Menu):
    bl_label = "Edit"

    def draw(self, _context):
        layout = self.layout

        layout.operator("ed.undo", icon='LOOP_BACK')
        layout.operator("ed.redo", icon='LOOP_FORWARDS')

        layout.separator()

        # The only way into the add-on preferences: the engine path, the
        # tool-call cap and the run budgets live there (`__init__.py`).
        layout.operator("screen.userpref_show", text="Preferences...",
                        icon='PREFERENCES')


class CADEX_MT_editor_menus(Menu):
    bl_idname = "CADEX_MT_editor_menus"
    bl_label = ""

    def draw(self, _context):
        layout = self.layout
        layout.menu("CADEX_MT_file")
        layout.menu("CADEX_MT_edit")


def draw_upper_bar(header, context):
    """Replacement for `TOPBAR_HT_upper_bar.draw` (installed, not registered).

    The topbar's header draws once per alignment. The right-hand pass is where
    the scene and view-layer pickers went; Cadex has nothing to put there, so
    it draws nothing and the menus sit alone on the left.
    """
    if context.region.alignment == 'RIGHT':
        return
    # `draw_collapsible` folds the menus into one icon when the window is too
    # narrow for them, which is the stock behaviour and free.
    CADEX_MT_editor_menus.draw_collapsible(context, header.layout)


# ---------------------------------------------------------------------------
# Installing over the stock header
# ---------------------------------------------------------------------------

#: The stock draw, while ours is installed; None when it is not.
_stock_draw = None


def _reregister_with_draw(cls, draw):
    # Like poll, draw is captured at registration time, so re-register.
    bpy.utils.unregister_class(cls)
    cls.draw = draw
    bpy.utils.register_class(cls)


def installed():
    return _stock_draw is not None


def install():
    """Put the Cadex menus on the top bar. Idempotent."""
    global _stock_draw
    if _stock_draw is not None:
        return
    cls = bpy.types.TOPBAR_HT_upper_bar
    _stock_draw = cls.draw
    _reregister_with_draw(cls, draw_upper_bar)


def uninstall():
    """Give the stock bar back. Idempotent."""
    global _stock_draw
    if _stock_draw is None:
        return
    draw, _stock_draw = _stock_draw, None
    _reregister_with_draw(bpy.types.TOPBAR_HT_upper_bar, draw)


classes = (
    MESH_AGENT_OT_import_asset,
    MESH_AGENT_OT_link_part,
    MESH_AGENT_OT_choose_linked_part,
    MESH_AGENT_OT_refresh_linked_parts,
    MESH_AGENT_OT_export_printable,
    MESH_AGENT_OT_resolve_print_conflict,
    CADEX_MT_file,
    CADEX_MT_edit,
    CADEX_MT_editor_menus,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    # Before the menus go: a header pointing at menu classes that are no
    # longer registered draws a row of errors, and disabling the add-on is
    # exactly when that would happen.
    uninstall()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
