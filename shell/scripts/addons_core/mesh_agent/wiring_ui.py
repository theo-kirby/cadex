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


class MESH_AGENT_OT_apply_wiring(bpy.types.Operator):
    """Send the canvas to the engine: one rebuild, however many edits."""

    bl_idname = "mesh_agent.apply_wiring"
    bl_label = "Apply"
    bl_description = ("Rebuild the model from the wires and terminals on this "
                      "canvas. One re-execute, however many you have drawn")
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        # Only while nothing is in flight. A push carries the whole table, so
        # a second Apply on top of one that has not answered would send a
        # table built against a revision the first is about to move.
        tree = getattr(getattr(context, "scene", None), "cadex_wiring", None)
        return tree is not None and not tree.cadex_pending

    def execute(self, context):
        ok, report = wiring.push(context.scene)
        if not ok:
            self.report({'ERROR'}, str(report))
            return {'CANCELLED'}
        self.report({'INFO'}, str(report or "applying…"))
        return {'FINISHED'}


class MESH_AGENT_OT_sync_wiring(bpy.types.Operator):
    """Throw the canvas away and re-read the harness from the engine.

    Relabelled Revert by ADR-122 and otherwise unchanged: it was always
    "rebuild the graph from the accepted revision", and once the canvas can
    hold edits that were never sent, that *is* discarding them. The idname
    stays — ``bl_mesh_agent.py`` asserts exact idnames on the button row, and
    a rename would be a second change wearing the first one's clothes.
    """

    bl_idname = "mesh_agent.sync_wiring"
    bl_label = "Revert"
    bl_description = ("Discard anything drawn here and rebuild the graph from "
                      "the engine's accepted revision. Node positions are kept")
    bl_options = {'REGISTER'}

    def execute(self, context):
        if wiring.sync_from_engine(context.scene, force=True):
            return {'FINISHED'}
        tree = getattr(context.scene, "cadex_wiring", None)
        self.report({'WARNING'}, str(getattr(tree, "cadex_error", "")
                                     or "No wiring to read."))
        return {'CANCELLED'}


def _draw_apply_revert(layout, tree):
    """The pair, drawn the same way wherever it appears (ADR-122).

    Apply alerts while the canvas is dirty, which is the only signal in the
    editor that anything is owed to the engine — a drawn wire looks exactly
    like an applied one, and that is the point of the canvas being a
    projection.
    """

    row = layout.row(align=True)
    row.enabled = bool(tree.cadex_editable)
    apply_row = row.row(align=True)
    apply_row.alert = bool(tree.cadex_dirty)
    apply_row.operator(MESH_AGENT_OT_apply_wiring.bl_idname, text="Apply",
                       icon='CHECKMARK')
    row.operator(MESH_AGENT_OT_sync_wiring.bl_idname, text="Revert",
                 icon='LOOP_BACK')


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
        _draw_apply_revert(layout, tree)
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
        _draw_apply_revert(layout, tree)
        if tree.cadex_pending:
            layout.label(text="applying…", icon='SORTTIME')
        elif tree.cadex_dirty:
            row = layout.row()
            row.label(text="Not applied yet.", icon='INFO')
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
        # The solder checkboxes moved onto the socket rows themselves
        # (ADR-122), where the terminal they belong to is. What is left here
        # is the count, so "did that tick take" has an answer that does not
        # need a node selected.
        # Keyed <port>.<terminal>, because two boards may both have an `sda`
        # and a terminal is two sockets.
        soldered = {"{:s}.{:s}".format(node.port, socket.terminal)
                    for node in tree.nodes
                    for socket in list(node.inputs) + list(node.outputs)
                    if socket.is_linked and socket.soldered}
        layout.label(text="{:d} soldered terminal(s)".format(len(soldered)),
                     icon='SNAP_MIDPOINT')


def _active_socket(tree):
    """The terminal the sidebar acts on: the selected node's, by name.

    Blender has no "active socket" for a custom node, so the panel keys on
    the node's own ``cadex_terminal`` string — which the list below sets when
    a row is clicked. A terminal is two sockets and they are mirrored, so
    either answers.
    """

    for node in tree.nodes:
        if not node.select or not getattr(node, "board", ""):
            continue
        wanted = str(getattr(node, "cadex_terminal", "") or "")
        for socket in list(node.inputs) + list(node.outputs):
            name = str(getattr(socket, "terminal", "") or "")
            if name and (name == wanted or not wanted):
                return node, socket
    return None, None


class MESH_AGENT_OT_rename_terminal(bpy.types.Operator):
    """Rename one terminal, and every wire addressing it, in one edit."""

    bl_idname = "mesh_agent.rename_terminal"
    bl_label = "Rename Terminal"
    bl_description = ("Rename this terminal; the wires addressing it follow "
                      "in the same rebuild")
    bl_options = {'REGISTER'}

    name: bpy.props.StringProperty(name="Name", default="")

    def execute(self, context):
        tree = _tree(context)
        if tree is None:
            return {'CANCELLED'}
        node, socket = _active_socket(tree)
        if node is None or socket is None:
            self.report({'ERROR'}, "Select a board and a terminal first.")
            return {'CANCELLED'}
        name = wiring.clean_terminal_name(self.name)
        if not name:
            self.report({'ERROR'}, "A terminal needs a lower_snake_case name.")
            return {'CANCELLED'}
        ok, report = wiring.rename_terminal(
            tree, node, str(socket.terminal), name)
        if not ok:
            self.report({'ERROR'}, str(report))
            return {'CANCELLED'}
        return {'FINISHED'}


class MESH_AGENT_OT_delete_terminal(bpy.types.Operator):
    """Drop one terminal from its board's table."""

    bl_idname = "mesh_agent.delete_terminal"
    bl_label = "Delete Terminal"
    bl_description = ("Remove this terminal from the board's table; any wire "
                      "on it goes with it")
    bl_options = {'REGISTER'}

    def execute(self, context):
        tree = _tree(context)
        if tree is None:
            return {'CANCELLED'}
        node, socket = _active_socket(tree)
        if node is None or socket is None:
            self.report({'ERROR'}, "Select a board and a terminal first.")
            return {'CANCELLED'}
        ok, report = wiring.delete_terminal(tree, node, str(socket.terminal))
        if not ok:
            self.report({'ERROR'}, str(report))
            return {'CANCELLED'}
        return {'FINISHED'}


class MESH_AGENT_OT_select_terminal(bpy.types.Operator):
    """Make one terminal of the selected board the active one."""

    bl_idname = "mesh_agent.select_terminal"
    bl_label = "Terminal"
    bl_description = "Show this terminal's row below"
    bl_options = {'REGISTER'}

    name: bpy.props.StringProperty(name="Name", default="")

    def execute(self, context):
        tree = _tree(context)
        board = _selected_board(tree) if tree is not None else None
        if board is None:
            return {'CANCELLED'}
        board.cadex_terminal = str(self.name)
        return {'FINISHED'}


def _selected_board(tree):
    """The selected node that is a board, or None."""

    for node in tree.nodes:
        if node.select and str(getattr(node, "port", "") or ""):
            return node
    return None


def _terminals_of(node):
    """One socket per terminal, in declared order — the board as a list.

    The canvas needs two columns to be draggable and this does not, so this
    is where a board reads as the single list of terminals it actually is
    (ADR-122). Either socket of a pair answers: they are mirrored on every
    edit.
    """

    found = []
    seen = set()
    for socket in list(node.outputs) + list(node.inputs):
        name = str(getattr(socket, "terminal", "") or "")
        if not name or name in seen:
            continue
        seen.add(name)
        found.append(socket)
    return found


class CADEX_WIRING_PT_terminal(bpy.types.Panel):
    """The selected board's terminals, and the active one's row.

    The list is the answer to "which of these two ``sda`` rows is the
    terminal" (ADR-122): the canvas has to draw a terminal twice because
    ``tree.links.new`` refuses a same-direction link, and the sidebar does
    not, so the board reads here as one row per terminal with its solder
    checkbox and — for the active one — the numbers
    ``set_params(boards=...)`` writes back.
    """

    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Cadex"
    bl_label = "Terminal"

    def draw(self, context):
        layout = self.layout
        tree = _tree(context)
        if tree is None:
            return
        board = _selected_board(tree)
        if board is not None:
            box = layout.box()
            box.label(text=str(board.label or board.port), icon='MESH_CUBE')
            column = box.column(align=True)
            for socket in _terminals_of(board):
                row = column.row(align=True)
                row.prop(socket, "soldered", text="", icon='SNAP_MIDPOINT')
                sub = row.row(align=True)
                sub.enabled = bool(tree.cadex_editable)
                sub.operator(
                    MESH_AGENT_OT_select_terminal.bl_idname,
                    text=str(socket.terminal),
                    depress=(str(board.cadex_terminal) == socket.terminal),
                ).name = str(socket.terminal)
                if socket.is_linked:
                    row.label(text="", icon='LINKED')

        node, socket = _active_socket(tree)
        if node is None or socket is None:
            layout.label(text="Select a board to see its terminals.")
            return
        column = layout.column(align=True)
        column.prop(node, "cadex_terminal", text="Terminal")
        if not getattr(socket, "has_row", False):
            sub = column.row()
            sub.enabled = False
            sub.label(text="Stated by a selector; its row is the geometry's.",
                      icon='LOCKED')
            return
        editable = bool(getattr(node, "board_editable", False))
        body = layout.column(align=True)
        body.enabled = editable
        body.prop(socket, "origin")
        body.prop(socket, "axis")
        body.prop(socket, "hole_dia")
        body.prop(socket, "depth")
        if not editable:
            return
        row = layout.row(align=True)
        row.operator(MESH_AGENT_OT_rename_terminal.bl_idname,
                     text="Rename").name = str(socket.terminal)
        row.operator(MESH_AGENT_OT_delete_terminal.bl_idname, text="Delete",
                     icon='X')


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
            if getattr(node, "board_editable", False):
                row.label(text="", icon='GREASEPENCIL')


#: Class name dictated by the inherited keymap: ``blender_default.py`` binds
#: Shift-A to ``op_menu("NODE_MT_add", ...)``. The name is free to take
#: because ``bl_ui.space_node`` is not in ``bl_ui``'s module list and so the
#: stock geometry/shader add menu is never registered. Do not rename it.
class NODE_MT_add(bpy.types.Menu):
    bl_label = "Add"

    def draw(self, _context):
        layout = self.layout
        layout.label(text="Boards come from the script.", icon='INFO')
        layout.operator(MESH_AGENT_OT_apply_wiring.bl_idname, icon='CHECKMARK')
        layout.operator(MESH_AGENT_OT_sync_wiring.bl_idname, icon='LOOP_BACK')


_SPACE_BOUND = (
    CADEX_WIRING_HT_header,
    CADEX_WIRING_PT_connection,
    CADEX_WIRING_PT_terminal,
    CADEX_WIRING_PT_boards,
    NODE_MT_add,
)

#: Registered whether or not the space type exists, like the toggle: they are
#: reachable from a script and from the test suite, and an operator missing
#: from ``bpy.types`` is a red row rather than a disabled one.
_ALWAYS = (
    MESH_AGENT_OT_apply_wiring,
    MESH_AGENT_OT_sync_wiring,
    MESH_AGENT_OT_rename_terminal,
    MESH_AGENT_OT_delete_terminal,
    MESH_AGENT_OT_select_terminal,
)


def register():
    global EDITOR_AVAILABLE

    # Registered whether or not the space type exists: the button under the
    # chat box draws unconditionally, and an operator missing from
    # `bpy.types` is a red row in the UI rather than a disabled one. It
    # reports "No viewport to split" on a bundle with no node editor.
    for cls in _ALWAYS:
        bpy.utils.register_class(cls)
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
    for cls in reversed(_ALWAYS):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            pass
