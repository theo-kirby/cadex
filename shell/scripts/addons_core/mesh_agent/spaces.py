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

        # Picking feeds pins to the next message. Two gestures, one queue:
        # a face pin names a BREP face the engine can re-find, a point pin is
        # a place and a direction, which is the only thing an imported mesh
        # can offer and exactly what a part.cable port is. The count sits
        # beside them rather than inside one button's label, because it
        # counts both.
        from . import cadex_pick
        layout.operator("mesh_agent.pick_pin", icon='EYEDROPPER',
                        text="Pin Face")
        layout.operator("mesh_agent.pick_point", icon='CURSOR',
                        text="Pin Point")
        pending = cadex_pick.pending_pin_count()
        if pending:
            layout.label(text="{:d} pinned".format(pending))

        # The script view's button is in the row under the message box, beside
        # the parameters toggle (ui.draw_chat_buttons). It used to be a plain
        # opener here as well, which meant two buttons for one view and only
        # one of them able to close it -- and the spacer that pushed it to the
        # right goes with it, having nothing left to push.


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


def script_area(screen):
    """The Text Editor on this screen showing the script mirror, or None.

    Not "any Text Editor": the toggle must not close one the user opened on
    some other text, and must not claim to be open when it is showing one.
    """
    text = script_text()
    if text is None:
        return None
    for area in screen.areas:
        if area.type != 'TEXT_EDITOR':
            continue
        space = area.spaces.active
        if space is not None and space.text == text:
            return area
    return None


class MESH_AGENT_OT_show_script(Operator):
    bl_idname = "mesh_agent.show_script"
    bl_label = "Script"
    bl_description = "Show or hide the model script in a Text Editor"

    # No poll. A file with no mirror yet is exactly when someone wants to see
    # what the script is, and a greyed-out button answers that with nothing;
    # `model.ensure_script_text` makes the empty mirror instead.

    def execute(self, context):
        from . import model
        window = context.window
        screen = window.screen

        open_area = script_area(screen)
        if open_area is not None:
            try:
                with context.temp_override(window=window, screen=screen,
                                           area=open_area):
                    bpy.ops.screen.area_close()
            except RuntimeError:
                # area_close's poll fails when no neighbour can absorb it.
                self.report({'WARNING'}, "The script view cannot be closed")
                return {'CANCELLED'}
            return {'FINISHED'}

        text = model.ensure_script_text()
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


class MESH_AGENT_OT_revert_script(Operator):
    bl_idname = "mesh_agent.revert_script"
    bl_label = "Revert to Model"
    bl_description = ("Throw away the edits in this buffer and put the "
                      "engine's script back")

    @classmethod
    def poll(cls, context):
        from . import model
        return model.script_is_dirty()

    def execute(self, context):
        from . import cadex_backend
        from . import model

        # The engine's cached state, not a fresh request: the buffer diverged
        # from a source the shell already has, and Revert is the cheap escape
        # from a typo. Rebuild Model is the button for "ask the engine again".
        state = cadex_backend.cached_script_state(context.scene)
        if state is None or not state.script_present or not state.source:
            self.report({'WARNING'},
                        "The engine holds no script to revert to")
            return {'CANCELLED'}
        model.set_script(state.source)
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
        from . import cadex_backend
        from . import model
        layout = self.layout

        # Be honest about which way the mirror points, and about whether it
        # currently *is* a mirror. `get_script` reads this buffer, so the
        # assistant sees a hand edit immediately; the engine does not, until
        # Apply. Blender text datablocks have no read-only flag to enforce that
        # with, so the panel says which of three states the buffer is in --
        # silently diverged is the one thing it must never be (ADR-039).
        state = cadex_backend.cached_script_state(context.scene)
        engine_has_script = state is not None and state.script_present
        dirty = model.script_is_dirty()

        if dirty or (not engine_has_script and model.get_script().strip()):
            box = layout.box().column(align=True)
            row = box.row()
            row.alert = True
            row.label(text="Modified — not applied" if dirty
                      else "Not in the model yet", icon='ERROR')
            note = box.column(align=True)
            note.enabled = False
            note.label(text="The assistant sees these edits;")
            note.label(text="the model does not, until Apply.")
            # Why the last attempt did not take, when there was one. The full
            # report is in the transcript; one line is what fits here.
            failure = model.last_error()
            if failure:
                alert = box.row()
                alert.alert = True
                alert.label(text=ui_module.first_line(failure), icon='INFO')
            box.operator(ui_module.MESH_AGENT_OT_adopt_script.bl_idname,
                         text="Apply to Model", icon='FILE_REFRESH')
            if dirty:
                box.operator(MESH_AGENT_OT_revert_script.bl_idname,
                             text="Revert to Model", icon='LOOP_BACK')
            return

        column = layout.column(align=True)
        column.label(text="Matches the model.", icon='CHECKMARK')
        layout.operator(ui_module.MESH_AGENT_OT_rebuild_model.bl_idname,
                        text="Rebuild Model", icon='FILE_REFRESH')


classes = (
    MESH_AGENT_OT_show_script,
    MESH_AGENT_OT_revert_script,
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
