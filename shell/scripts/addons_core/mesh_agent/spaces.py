# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Headers for the two Cadex editors, and the Text Editor's script view.

These live in the add-on rather than in `shell/scripts/startup/bl_ui/`
deliberately: `bl_ui` is inherited Blender and conservative, `mesh_agent` is
ours. The cost is that a Cadex editor draws an empty header with the add-on
disabled -- acceptable, because the add-on is what the editors are *for*, and
nothing in the product works without it.
"""

import bpy
from bpy.types import Header, Operator, Panel

from . import agent as agent_module
from . import ui as ui_module


class CADEX_CHAT_HT_header(Header):
    bl_space_type = 'CADEX_CHAT'

    def draw(self, context):
        layout = self.layout
        layout.template_header()

        # The model selector takes effect at the next turn; the conversation
        # itself continues. It edits the add-on preference, so it is also the
        # default for future sessions. (The mode dropdown that sat above it is
        # gone with the local modes -- ADR-030.)
        prefs = agent_module.get_prefs()
        if prefs is not None:
            layout.prop(prefs, "model", text="")

        # Face picking feeds BREP pins to the next message.
        from . import cadex_pick
        pending = cadex_pick.pending_pin_count()
        layout.operator(
            "mesh_agent.pick_pin", icon='EYEDROPPER',
            text="Pin Face" if not pending
            else "Pin Face ({:d} pinned)".format(pending))

        layout.separator_spacer()
        layout.operator(MESH_AGENT_OT_show_script.bl_idname, text="",
                        icon='TEXT')


class CADEX_PARAMS_HT_header(Header):
    bl_space_type = 'CADEX_PARAMS'

    def draw(self, context):
        layout = self.layout
        layout.template_header()


# ---------------------------------------------------------------------------
# The script view: the stock Text Editor, pointed at the mirror.
# ---------------------------------------------------------------------------

# `model.py` is already mirrored into a text datablock with a fake user
# (`model.set_script`), so the script needs no editor of its own -- the Text
# Editor brings syntax highlighting, line numbers and find for free.


def script_text():
    from . import model
    return bpy.data.texts.get(model.SCRIPT_NAME)


class MESH_AGENT_OT_show_script(Operator):
    bl_idname = "mesh_agent.show_script"
    bl_label = "Script"
    bl_description = ("Show the model script in a Text Editor")

    @classmethod
    def poll(cls, context):
        return script_text() is not None

    def execute(self, context):
        text = script_text()
        window = context.window
        screen = window.screen

        area = next((a for a in screen.areas if a.type == 'TEXT_EDITOR'), None)
        if area is None:
            viewports = [a for a in screen.areas if a.type == 'VIEW_3D']
            if not viewports:
                self.report({'WARNING'}, "No viewport to split")
                return {'CANCELLED'}
            viewport = max(viewports, key=lambda a: a.width * a.height)
            before = {a.as_pointer() for a in screen.areas}
            try:
                with context.temp_override(window=window, screen=screen,
                                           area=viewport):
                    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
            except RuntimeError:
                self.report({'WARNING'}, "No room for the script")
                return {'CANCELLED'}
            fresh = [a for a in screen.areas if a.as_pointer() not in before]
            if not fresh:
                self.report({'WARNING'}, "No room for the script")
                return {'CANCELLED'}
            area = fresh[0]
            # Area type changes need a window in the context; without one the
            # assignment appears to succeed but the space data never switches.
            with context.temp_override(window=window, screen=screen,
                                       area=area):
                area.type = 'TEXT_EDITOR'

        space = area.spaces.active
        space.text = text
        space.show_line_numbers = True
        space.show_syntax_highlight = True
        space.show_word_wrap = False
        return {'FINISHED'}


class CADEX_PT_script(Panel):
    """Sidebar panel in the Text Editor, next to the model script."""

    bl_space_type = 'TEXT_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Cadex"
    bl_label = "Model Script"

    @classmethod
    def poll(cls, context):
        space = context.space_data
        text = script_text()
        return text is not None and space is not None and space.text == text

    def draw(self, context):
        layout = self.layout

        # Be honest about which way the mirror points. `get_script` reads this
        # buffer, so the assistant sees a hand edit immediately; `write_script`
        # goes to the engine, which does not. Blender text datablocks have no
        # read-only flag to enforce it with, so say it rather than pretend.
        column = layout.column(align=True)
        column.label(text="The engine's script, mirrored here.", icon='INFO')
        note = column.column(align=True)
        note.enabled = False
        note.label(text="Edits are visible to the assistant")
        note.label(text="but reach the engine only on Apply.")

        layout.operator(ui_module.MESH_AGENT_OT_adopt_script.bl_idname,
                        text="Apply to Model", icon='FILE_REFRESH')


classes = (
    MESH_AGENT_OT_show_script,
    CADEX_CHAT_HT_header,
    CADEX_PARAMS_HT_header,
    CADEX_PT_script,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
