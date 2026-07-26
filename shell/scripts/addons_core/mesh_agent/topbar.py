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

Everything the menus point at is stock: `wm.open_mainfile`, `wm.save_mainfile`
and the rest are the operators Blender ships, and Import/Export are Blender's
own menus, so a format added by an enabled add-on appears here without this
file knowing about it. The document is the `.blend` (ADR-033): it carries the
script mirror, the parameter specs and the engine project id, so File > Save
saves the model.
"""

import bpy
from bpy.types import Menu


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
