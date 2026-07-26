# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Headers for the two Cadex editors.

These live in the add-on rather than in `shell/scripts/startup/bl_ui/`
deliberately: `bl_ui` is inherited Blender and conservative, `mesh_agent` is
ours. The cost is that a Cadex editor draws an empty header with the add-on
disabled -- acceptable, because the add-on is what the editors are *for*, and
nothing in the product works without it.
"""

import bpy
from bpy.types import Header

from . import agent as agent_module


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


class CADEX_PARAMS_HT_header(Header):
    bl_space_type = 'CADEX_PARAMS'

    def draw(self, context):
        layout = self.layout
        layout.template_header()


classes = (
    CADEX_CHAT_HT_header,
    CADEX_PARAMS_HT_header,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
