# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Headers for the six Cadex editors, and the Text Editor's script view.

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

        # The assistant and model selectors take effect at the next turn.
        # Changing the model continues the conversation; changing the
        # assistant starts a fresh one (one CLI cannot resume another's
        # session, and the agent says so in the transcript). Both edit the
        # add-on preference, so they are also the default for future
        # sessions. (The mode dropdown that sat above them is gone with the
        # local modes -- ADR-030.)
        prefs = agent_module.get_prefs()
        if prefs is not None:
            layout.prop(prefs, "provider", text="")
            model_prop = {"codex": "codex_model", "pi": "pi_model"}.get(
                prefs.provider, "model")
            layout.prop(prefs, model_prop,
                        text="",
                        placeholder="pi's default model"
                        if model_prop == "pi_model" else "")

        # The door to the rest of the settings (CLI paths, engine override,
        # budgets): the AI section of the Preferences window (ADR-183). The
        # app menu's Settings... opens the same window; the gear puts the
        # answer to "where are the settings" inside the editor they affect,
        # and lands on the right rail entry.
        props = layout.operator("screen.userpref_show", text="",
                                icon='PREFERENCES')
        if props is not None:
            try:
                props.section = 'AI'
            except TypeError:
                # A binary built before the AI rail entry: open wherever.
                pass

        # The header carries *state*, not actions. Every button that does
        # something sits in one row under the message box (ui.draw_chat_
        # buttons) -- including the two pin gestures, which used to be here
        # and were the last thing splitting the chat's controls across two
        # places. What is left of them here is the count, which is status:
        # it says what the next message will carry.
        from . import cadex_drawings
        from . import cadex_pick
        pending = (cadex_pick.pending_pin_count()
                   + cadex_drawings.pending_section_count())
        if pending:
            layout.label(text="{:d} pinned".format(pending))


class CADEX_PARAMS_HT_header(Header):
    bl_space_type = 'CADEX_PARAMS'

    def draw(self, context):
        layout = self.layout
        layout.template_header()


# The four editors ADR-108 split out of the parameters one. Each needs a
# header class of its own or its header region draws nothing at all -- not
# even the editor-type dropdown, which is how a user changes an area back.
# `template_header()` and no more: the header carries state, and none of
# these four has any that is not already in its panels.


class CADEX_ENV_HT_header(Header):
    bl_space_type = 'CADEX_ENV'

    def draw(self, context):
        self.layout.template_header()


class CADEX_POLICY_HT_header(Header):
    bl_space_type = 'CADEX_POLICY'

    def draw(self, context):
        self.layout.template_header()


class CADEX_TRAINING_HT_header(Header):
    bl_space_type = 'CADEX_TRAINING'

    def draw(self, context):
        self.layout.template_header()


class CADEX_LIVE_HT_header(Header):
    bl_space_type = 'CADEX_LIVE'

    def draw(self, context):
        self.layout.template_header()


# ---------------------------------------------------------------------------
# The script view: the stock Text Editor, pointed at the mirror.
# ---------------------------------------------------------------------------

# `model.py` is already mirrored into a text datablock with a fake user
# (`model.set_script`), so the script needs no editor of its own -- the Text
# Editor brings syntax highlighting, line numbers and find for free. It is
# opened like any editor: Blender's editor dropdown, then the text dropdown
# (ADR-165 removed the open-a-view operators; the tiling manager is the one
# way to arrange the screen).


def script_text():
    from . import model
    return bpy.data.texts.get(model.SCRIPT_NAME)


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
    MESH_AGENT_OT_revert_script,
    CADEX_CHAT_HT_header,
    CADEX_PARAMS_HT_header,
    CADEX_ENV_HT_header,
    CADEX_POLICY_HT_header,
    CADEX_TRAINING_HT_header,
    CADEX_LIVE_HT_header,
    CADEX_PT_script,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
