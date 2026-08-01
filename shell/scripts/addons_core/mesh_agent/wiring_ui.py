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


#: The fraction of the viewport a freshly split Wiring editor takes. The same
#: split the parameters editor uses (``ui.PARAMS_SPLIT``), vertically: a
#: harness is wide.
WIRING_SPLIT = 0.5


def wiring_area(screen):
    """The Wiring editor on this screen, or None.

    ``NODE_EDITOR`` is a *shared* space type — the compositor and any other
    node tree live in it too — so the type alone is not the predicate. A
    toggle that matched on it would close somebody else's editor and report
    that it had closed ours. The same discriminating-predicate idea as
    ``spaces.script_area``, which will not claim a Text Editor showing some
    other text.
    """

    for area in screen.areas:
        if area.type != 'NODE_EDITOR':
            continue
        space = area.spaces.active
        if space is not None and getattr(space, "tree_type", "") == \
                wiring.CadexWiringTree.bl_idname:
            return area
    return None


class MESH_AGENT_OT_toggle_wiring(bpy.types.Operator):
    bl_idname = "mesh_agent.toggle_wiring"
    bl_label = "Wiring"
    bl_description = "Show or hide the harness as a node graph"

    # No poll. A file whose engine has no harness yet is exactly when someone
    # wants to look at the wiring editor and find out; `ensure_tree` makes the
    # empty tree and the header says what it is waiting for.

    def execute(self, context):
        window = context.window
        screen = window.screen

        area = wiring_area(screen)
        if area is not None:
            try:
                with context.temp_override(window=window, screen=screen,
                                           area=area):
                    bpy.ops.screen.area_close()
            except RuntimeError:
                # area_close's poll fails when no neighbour can absorb it.
                self.report({'WARNING'}, "The wiring editor cannot be closed")
                return {'CANCELLED'}
            return {'FINISHED'}

        tree = wiring.ensure_tree(context.scene)
        viewports = [a for a in screen.areas if a.type == 'VIEW_3D']
        if not viewports:
            self.report({'WARNING'}, "No viewport to split")
            return {'CANCELLED'}
        viewport = max(viewports, key=lambda a: a.width * a.height)
        before = {a.as_pointer() for a in screen.areas}
        try:
            with context.temp_override(window=window, screen=screen,
                                       area=viewport):
                bpy.ops.screen.area_split(direction='VERTICAL',
                                          factor=WIRING_SPLIT)
        except RuntimeError:
            self.report({'WARNING'}, "No room for the wiring editor")
            return {'CANCELLED'}
        fresh = [a for a in screen.areas if a.as_pointer() not in before]
        if not fresh:
            self.report({'WARNING'}, "No room for the wiring editor")
            return {'CANCELLED'}
        area = fresh[0]
        # This order is the fix, not a style choice. `ui_type` carries the
        # tree idname into `snode->tree_idname`, and
        # `rna_SpaceNodeEditor_node_tree_poll` rejects the assignment below
        # unless the two already agree -- so a `node_tree =` first would be
        # silently dropped. And an area-type change needs a window in the
        # context or it no-ops just as quietly (`spaces.MESH_AGENT_OT_show_
        # script` learned that one first).
        with context.temp_override(window=window, screen=screen, area=area):
            area.ui_type = wiring.CadexWiringTree.bl_idname
        space = area.spaces.active
        if space is not None:
            space.node_tree = tree
        # `get_from_context` would attach it on the next redraw anyway; this
        # is the same answer one frame earlier, and it is what makes the
        # operator testable without a draw.
        wiring.arm_sync(context.scene)
        return {'FINISHED'}


class CADEX_WIRING_HT_header(bpy.types.Header):
    bl_space_type = 'NODE_EDITOR'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Wiring", icon='NODETREE')
        # Always drawn, tree or no tree. It used to be inside the `is None`
        # branch below, which meant a fresh file had no way to populate the
        # graph at all -- the one control that fills it was hidden until it
        # was already full.
        layout.operator(MESH_AGENT_OT_sync_wiring.bl_idname, text="",
                        icon='FILE_REFRESH')
        wiring.arm_sync(context.scene)
        tree = _tree(context)
        if tree is None:
            layout.label(text="reading the model…")
            return
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
        wiring.arm_sync(context.scene)
        tree = _tree(context)
        if tree is None:
            column = layout.column(align=True)
            column.label(text="Reading the model…", icon='SORTTIME')
            column.operator(MESH_AGENT_OT_sync_wiring.bl_idname,
                            icon='FILE_REFRESH')
            return
        if tree.cadex_error:
            row = layout.row()
            row.alert = True
            row.label(text=tree.cadex_error[:60], icon='ERROR')
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
        wiring.arm_sync(context.scene)
        tree = _tree(context)
        if tree is None:
            return
        if not tree.nodes:
            layout.label(text="No boards yet.")
            layout.operator(MESH_AGENT_OT_sync_wiring.bl_idname,
                            icon='FILE_REFRESH')
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
    # Registered whether or not the space type exists: the button under the
    # chat box draws unconditionally, and an operator missing from
    # `bpy.types` is a red row in the UI rather than a disabled one. It
    # reports "No viewport to split" on a bundle with no node editor.
    bpy.utils.register_class(MESH_AGENT_OT_toggle_wiring)
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
    for cls in (MESH_AGENT_OT_toggle_wiring, MESH_AGENT_OT_sync_wiring):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            pass
