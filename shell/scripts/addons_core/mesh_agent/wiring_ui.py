# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Chrome for the Wiring editor (ADR-066).

Everything here binds to ``NODE_EDITOR``, and that is the one thing in the
add-on that can fail to register: a ``Panel`` or ``Header`` naming a space
type Blender did not register raises ``RuntimeError: Region not found in
space type`` — and an exception in ``register()`` aborts the whole loop,
which is exactly how ADR-036 once made the top-bar menus disappear. So the
module registers under a guard, sets :data:`EDITOR_AVAILABLE` False on the
first failure, and returns. On a bundle built before the C++ half of ADR-066
the rest of the add-on is unaffected and the wiring model, its sync and its
push all still work headlessly — which is what makes the Python half
testable before the shell is rebuilt.

No ``bl_ui/space_node.py`` is restored. That module is 1,277 lines of
shader/geometry/compositor UI whose header draws a tree-type selector, an ID
template and a "Use Nodes" toggle, none of which a harness wants; and
ADR-035 already set the precedent that headers live here rather than in the
inherited ``bl_ui``. The header below is ours, so none of that comes back.
"""

import bpy

from . import wiring


#: False when this bundle has no node editor to hang the chrome on.
EDITOR_AVAILABLE = True


def _tree(context):
    tree = getattr(context.scene, "cadex_wiring", None)
    if tree is None:
        return None
    space = getattr(context, "space_data", None)
    if space is not None and getattr(space, "tree_type", "") not in (
            "", wiring.CadexWiringTree.bl_idname):
        return None
    return tree


class MESH_AGENT_OT_sync_wiring(bpy.types.Operator):
    """Re-read the harness from the engine and redraw the graph."""

    bl_idname = "mesh_agent.sync_wiring"
    bl_label = "Sync Wiring"
    bl_description = ("Rebuild the graph from the engine's accepted revision. "
                      "Node positions are kept")
    bl_options = {'REGISTER'}

    def execute(self, context):
        if wiring.sync_from_engine(context.scene, force=True):
            return {'FINISHED'}
        tree = getattr(context.scene, "cadex_wiring", None)
        self.report({'WARNING'}, str(getattr(tree, "cadex_error", "")
                                     or "No wiring to read."))
        return {'CANCELLED'}


class CADEX_WIRING_HT_header(bpy.types.Header):
    bl_space_type = 'NODE_EDITOR'

    def draw(self, context):
        layout = self.layout
        tree = _tree(context)
        if tree is None:
            layout.label(text="Wiring")
            return
        layout.label(text="Wiring", icon='NODETREE')
        layout.operator(MESH_AGENT_OT_sync_wiring.bl_idname, text="", icon='FILE_REFRESH')
        row = layout.row(align=True)
        row.label(text="{:d} boards".format(len(tree.nodes)))
        row.label(text="{:d} wires".format(len(wiring.stored_rows(tree))))
        if tree.cadex_pending:
            layout.label(text="applying…", icon='SORTTIME')
        if not tree.cadex_editable:
            sub = layout.row()
            sub.alert = True
            sub.label(text="read-only", icon='LOCKED')
        if tree.cadex_error:
            sub = layout.row()
            sub.alert = True
            sub.label(text=tree.cadex_error[:80], icon='ERROR')


class CADEX_WIRING_PT_connection(bpy.types.Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Cadex"
    bl_label = "Connection"

    def draw(self, context):
        layout = self.layout
        tree = _tree(context)
        if tree is None:
            layout.label(text="No project wiring.")
            return
        layout.prop(tree, "new_gauge_mm")
        if not tree.cadex_editable:
            column = layout.column(align=True)
            column.alert = True
            column.label(text="This script predates nets(...).", icon='INFO')
            for line in (
                "Its connections are reconstructed from the",
                "cable/bundle/solder calls it makes, so nothing",
                "outside the script names a row to edit. Ask the",
                "assistant to declare them with nets(ports=...,",
                "wires=...) to make this editable.",
            ):
                sub = column.row()
                sub.enabled = False
                sub.label(text=line)
            return
        selected = [socket for node in tree.nodes
                    for socket in list(node.inputs) + list(node.outputs)
                    if node.select and socket.is_linked]
        if not selected:
            layout.label(text="Select a board to toggle its joints.")
            return
        box = layout.box()
        box.label(text="Solder")
        for socket in selected[:24]:
            box.prop(socket, "soldered", text=socket.terminal)


class CADEX_WIRING_PT_boards(bpy.types.Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Cadex"
    bl_label = "Boards"

    def draw(self, context):
        layout = self.layout
        tree = _tree(context)
        if tree is None:
            return
        for node in tree.nodes:
            row = layout.row(align=True)
            row.label(text=str(getattr(node, "port", "")), icon='MESH_CUBE')
            row.label(text=str(getattr(node, "cadex_output", "")))


#: Class name dictated by the inherited keymap: ``blender_default.py`` binds
#: Shift-A to ``op_menu("NODE_MT_add", ...)``. The name is free to take
#: because ``bl_ui.space_node`` is not in ``bl_ui``'s module list and so the
#: stock geometry/shader add menu is never registered. Do not rename it.
class NODE_MT_add(bpy.types.Menu):
    bl_label = "Add"

    def draw(self, _context):
        layout = self.layout
        layout.label(text="Boards come from the script.", icon='INFO')
        layout.operator(MESH_AGENT_OT_sync_wiring.bl_idname, icon='FILE_REFRESH')


_SPACE_BOUND = (
    CADEX_WIRING_HT_header,
    CADEX_WIRING_PT_connection,
    CADEX_WIRING_PT_boards,
    NODE_MT_add,
)


def register():
    global EDITOR_AVAILABLE

    bpy.utils.register_class(MESH_AGENT_OT_sync_wiring)
    EDITOR_AVAILABLE = True
    for cls in _SPACE_BOUND:
        try:
            bpy.utils.register_class(cls)
        except (RuntimeError, ValueError):
            # No node editor in this build. Everything else stays up.
            EDITOR_AVAILABLE = False
            return


def unregister():
    for cls in reversed(_SPACE_BOUND):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            pass
    try:
        bpy.utils.unregister_class(MESH_AGENT_OT_sync_wiring)
    except (RuntimeError, ValueError):
        pass
