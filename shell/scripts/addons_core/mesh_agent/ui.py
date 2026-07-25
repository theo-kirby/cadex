# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Chat panel in the 3D Viewport sidebar, plus its operators."""

import os
import textwrap

import bpy
from bpy.types import Operator, Panel

from . import agent as agent_module


class MESH_AGENT_OT_chat_send(Operator):
    bl_idname = "mesh_agent.chat_send"
    bl_label = "Send"
    bl_description = "Send the message to the assistant"

    @classmethod
    def poll(cls, context):
        return not agent_module.get_agent().busy

    def execute(self, context):
        wm = context.window_manager
        prompt = wm.mesh_chat_input
        agent = agent_module.get_agent()
        if agent.start_turn(prompt):
            wm.mesh_chat_input = ""
        return {'FINISHED'}


class MESH_AGENT_OT_chat_cancel(Operator):
    bl_idname = "mesh_agent.chat_cancel"
    bl_label = "Stop"
    bl_description = "Cancel the current assistant turn"

    @classmethod
    def poll(cls, context):
        return agent_module.get_agent().busy

    def execute(self, context):
        agent_module.get_agent().cancel()
        return {'FINISHED'}


class MESH_AGENT_OT_attach_image(Operator):
    bl_idname = "mesh_agent.attach_image"
    bl_label = "Attach Image"
    bl_description = "Attach an image file to your next message"

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(
        default="*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff;*.exr",
        options={'HIDDEN'})

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if agent_module.get_agent().attach_image(self.filepath) < 0:
            self.report({'WARNING'}, "Could not read image file")
            return {'CANCELLED'}
        return {'FINISHED'}


class MESH_AGENT_OT_paste_image(Operator):
    bl_idname = "mesh_agent.paste_image"
    bl_label = "Paste Image"
    bl_description = "Attach the image on the clipboard to your next message"

    def execute(self, context):
        import subprocess
        import sys
        import tempfile

        if sys.platform != "darwin":
            self.report({'WARNING'},
                        "Clipboard image paste is only supported on macOS "
                        "for now; use Attach Image instead")
            return {'CANCELLED'}

        handle, path = tempfile.mkstemp(suffix=".png", prefix="mesh_paste_")
        os.close(handle)
        script = (
            'set png_data to the clipboard as «class PNGf»\n'
            'set out_file to open for access POSIX file "{:s}" '
            'with write permission\n'
            'write png_data to out_file\n'
            'close access out_file'.format(path))
        result = subprocess.run(["osascript", "-e", script],
                                capture_output=True, timeout=10)
        if result.returncode != 0 or not os.path.getsize(path):
            os.remove(path)
            self.report({'WARNING'}, "No image on the clipboard")
            return {'CANCELLED'}
        if agent_module.get_agent().attach_image(path) < 0:
            self.report({'WARNING'}, "Could not read the pasted image")
            return {'CANCELLED'}
        return {'FINISHED'}


class MESH_AGENT_OT_chat_clear(Operator):
    bl_idname = "mesh_agent.chat_clear"
    bl_label = "Clear Chat"
    bl_description = "Clear the chat transcript"

    @classmethod
    def poll(cls, context):
        return not agent_module.get_agent().busy

    def execute(self, context):
        agent = agent_module.get_agent()
        agent.history.clear()
        agent.history.save_to_text_block()
        return {'FINISHED'}


_ROLE_ICONS = {
    "user": 'USER',
    "assistant": 'LIGHT',
    "status": 'INFO',
}


class VIEW3D_PT_mesh_params(Panel):
    # Hosted in the chat column the same way as the chat panel below: the
    # Properties editor's Tool tab mirrors the viewport's "Tool"-category
    # sidebar panels.
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_order = 0
    bl_label = "Parameters"

    @classmethod
    def poll(cls, context):
        from . import model
        return bool(model.load_specs(context.scene))

    def draw(self, context):
        from . import model
        layout = self.layout
        group = getattr(context.scene, "mesh_params", None)
        if group is None:
            layout.label(text="Parameters load after rebuild", icon='INFO')
            return
        column = layout.column()
        for spec in model.load_specs(context.scene):
            if hasattr(group, spec["id"]):
                column.prop(group, spec["id"],
                            slider=spec["type"] in {'FLOAT', 'INT'})


class VIEW3D_PT_mesh_chat(Panel):
    # The Properties editor's Tool tab mirrors the viewport's "Tool"-category
    # sidebar panels (see WorkSpaceButtonsPanel in bl_ui/properties_workspace.py),
    # which lets the Mesh template host this panel as a full-height chat column:
    # a Properties editor pinned to the Tool tab, with the other tool panels
    # hidden while Simple mode is active. The viewport sidebar itself stays
    # closed in Simple mode, so the panel effectively appears only there.
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_order = 1
    bl_options = {'HIDE_HEADER'}
    bl_label = "Chat"

    def draw(self, context):
        layout = self.layout
        agent = agent_module.get_agent()

        # The model selector. It takes effect at the next turn; the
        # conversation itself continues. It edits the add-on preference, so it
        # is also the default for future sessions. (The mode dropdown that sat
        # above it is gone with the local modes -- ADR-030.)
        selectors = layout.column(align=True)
        prefs = agent_module.get_prefs()
        if prefs is not None:
            selectors.prop(prefs, "model", text="")

        # Face picking feeds BREP pins to the next message.
        from . import cadex_backend, cadex_pick
        pending = cadex_pick.pending_pin_count()
        selectors.operator(
            "mesh_agent.pick_pin", icon='EYEDROPPER',
            text="Pin Face" if not pending
            else "Pin Face ({:d} pinned)".format(pending))
        # One warning row, not a wall of text: the remedy lives in the
        # add-on preferences, which is where the fix is applied.
        ok, reason, _remedy = cadex_backend.preflight()
        if not ok:
            warning = layout.row()
            warning.alert = True
            warning.label(text=reason, icon='ERROR')

        # Rough character wrap width from the region width (~7 px per char,
        # minus panel padding). blf-measured wrapping can come later.
        wrap = max(24, int(context.region.width / 7.2) - 6)

        for message in agent.history.messages[-40:]:
            if message.role == "status":
                row = layout.row()
                row.enabled = False
                row.label(text=message.text, icon='INFO')
                continue
            box = layout.box()
            column = box.column(align=True)
            first = True
            for paragraph in message.text.split("\n"):
                for line in textwrap.wrap(paragraph, wrap) or [""]:
                    if first:
                        column.label(text=line, icon=_ROLE_ICONS[message.role])
                        first = False
                    else:
                        column.label(text=line)

        if agent.busy:
            row = layout.row()
            row.label(text="Thinking…", icon='SORTTIME')
            row.operator(MESH_AGENT_OT_chat_cancel.bl_idname,
                         text="", icon='CANCEL')


def draw_chat_input_header(self, context):
    """Replacement draw for PROPERTIES_HT_header while Simple mode is active
    (installed by the Mesh app template, which also flips the header region to
    the bottom of the area): a dropdown for the hidden properties tabs plus
    the chat input anchored at the bottom of the column."""
    layout = self.layout
    agent = agent_module.get_agent()

    # The other properties tabs, tucked behind a dropdown instead of the
    # navigation bar's icon strip.
    layout.prop(context.space_data, "context", text="", icon_only=True)

    # Make the text field absorb the remaining header width.
    ui_scale = context.preferences.system.ui_scale or 1.0
    total_units = context.region.width / (20.0 * ui_scale)
    field = layout.row(align=True)
    field.ui_units_x = max(8.0, total_units - 11.0)
    field.prop(context.window_manager, "mesh_chat_input", text="")

    attach = layout.row(align=True)
    pending = agent.pending_attachment_count()
    attach.operator(MESH_AGENT_OT_attach_image.bl_idname, icon='FILE_IMAGE',
                    text="{:d}".format(pending) if pending else "")
    attach.operator(MESH_AGENT_OT_paste_image.bl_idname, text="",
                    icon='PASTEDOWN')

    if agent.busy:
        layout.operator(MESH_AGENT_OT_chat_cancel.bl_idname,
                        text="", icon='CANCEL')
    else:
        layout.operator(MESH_AGENT_OT_chat_send.bl_idname,
                        text="", icon='PLAY')
    layout.operator(MESH_AGENT_OT_chat_clear.bl_idname, text="", icon='TRASH')


classes = (
    MESH_AGENT_OT_chat_send,
    MESH_AGENT_OT_chat_cancel,
    MESH_AGENT_OT_chat_clear,
    MESH_AGENT_OT_attach_image,
    MESH_AGENT_OT_paste_image,
    VIEW3D_PT_mesh_params,
    VIEW3D_PT_mesh_chat,
)


def register():
    bpy.types.WindowManager.mesh_chat_input = bpy.props.StringProperty(
        name="Message",
        description="Ask the assistant to build or change something",
        default="",
    )
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.WindowManager.mesh_chat_input
