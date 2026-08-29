# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Dragging a routed wire onto the path you wanted (ADR-118).

``part.cable`` searches its route on every rebuild, and that is what makes a
wire follow the components it connects instead of going stale. What it left
the user with is a search they can only steer through its cost function: when
the route comes back legal but ugly, the levers are ``avoid``, ``slack`` and
``clearance_mm``, and none of them says "go *there*".

This is the gesture that says it. **Edit Wire Path** builds the published
route as a real Blender curve, **Confirm** reads the control points back and
asks the assistant to write them into that one ``part.cable`` call as
``waypoints=``, and **Cancel** throws the curve away and leaves the script
untouched.

**The control points are a real curve object**, in a sibling collection built
the way ``cadex_collision.py`` builds its overlay. That is the whole reason
there is no gizmo code here: G/R/S, axis constraints, snapping, proportional
edit and the N-panel's numeric fields are Blender's, and they all work on a
``POLY`` curve's control points for free.

**The stub knots are excluded from what is editable, and the engine is what
excludes them.** It publishes the whole centreline as ``path`` and the part a
user may author as ``waypoints``, so nothing here has to know how many
collinear knots a stand-off stub is written as — a number that has already
changed once (ADR-114). Those knots hold the lead straight through the joint
that grips it, so letting the user drag them would fight the joint; letting
the engine own them is what keeps both ends of an authored wire riding their
terminals, so a slider that moves a board still moves the wire.

**It queues a note; it does not write script** — ADR-067's rule, reused. What
is different from the terminal pick is only that this one *starts the turn*
itself, with a fixed prompt: there is nothing for the user to type, and the
edit the assistant has to make is a single named argument on a single named
call.
"""

import json

import bpy

from . import cadex_hydrate


#: Dragged paths waiting to be handed to a turn. Drained by
#: ``agent.start_turn`` beside the pin and terminal queues.
_pending_paths = []

#: The collection the editable curve lives in — a sibling of Model at the
#: scene root, exactly as the collision overlay's is, so the hydrate GC never
#: sees it and nothing else in the add-on has to know it exists.
COLLECTION_NAME = "Wire Path"

#: Object properties: which row this curve is the path of, and its endpoints.
ROW_PROP = "cadex_wire_row"
ENDS_PROP = "cadex_wire_ends"

#: What the assistant is asked to do when Confirm is pressed. Fixed text: the
#: user has pressed one button and typed nothing, so this is the whole prompt.
CONFIRM_PROMPT = (
    "Add the waypoints I just dragged to that wire's part.cable call."
)

#: A path with more interior points than this is a slip of the hand — a
#: subdivided curve, or the wrong object — rather than an authored route.
MAX_WAYPOINTS = 64



# ---------------------------------------------------------------------------
# the queue


def queue_wire_path(entry):
    _pending_paths.append(entry)


def pending_path_count():
    return len(_pending_paths)


def clear_paths():
    _pending_paths.clear()


def consume_wire_path_notes():
    """Prompt suffix describing paths dragged since the last turn (drains).

    Worded as an instruction to make one targeted edit, because that is what
    it is: the coordinates are the user's, the call is already in the script,
    and the only thing missing is the argument. It says *which* call by naming
    the row and both endpoints, so a project with six wires between the same
    two boards still has exactly one candidate.

    It also says the thing the user cannot see: a hand-placed waypoint does
    not move when a parameter does. ADR-118 accepted that rather than
    designing it away, so the note is where it gets said out loud.
    """

    if not _pending_paths:
        return ""
    lines = []
    for entry in _pending_paths:
        lines.append(
            "[The user DRAGGED a path for the wire {row!r} (from {a} to {b}). "
            "These are {count} interior waypoints in the same coordinates the "
            "ports resolve in, taken off the curve they moved:\n"
            "  waypoints={points}\n"
            "Add exactly that waypoints= argument to that one part.cable call "
            "and change nothing else. When waypoints= is given the route is "
            "NOT searched: slack and cell_mm stop applying, the ends still "
            "ride their terminals, and the path is still checked against "
            "avoid and against min_bend_radius_mm. Tell the user, in one "
            "sentence, that a hand-placed path does not move when a parameter "
            "moves a component — the ends will follow but the middle will "
            "not.]".format(
                row=entry.get("row", ""),
                a=entry.get("a", ""),
                b=entry.get("b", ""),
                count=len(entry.get("points") or []),
                points=json.dumps(entry.get("points") or []),
            )
        )
    _pending_paths.clear()
    return "\n\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# finding the row a curve belongs to


def _collection(scene, create=True):
    """The Wire Path collection, a sibling of Model at the scene root."""

    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        if not create:
            return None
        collection = bpy.data.collections.new(COLLECTION_NAME)
    if collection.name not in scene.collection.children:
        if not create:
            return collection
        scene.collection.children.link(collection)
    return collection


def path_object(scene=None):
    """The curve currently being edited, if there is one."""

    scene = scene if scene is not None else bpy.context.scene
    if scene is None:
        return None
    collection = _collection(scene, create=False)
    if collection is None:
        return None
    for obj in collection.objects:
        if obj.type == 'CURVE' and ROW_PROP in obj:
            return obj
    return None


def clear(scene=None):
    """Remove the curve and forget it. The whole cleanup story."""

    scene = scene or bpy.context.scene
    collection = _collection(scene, create=False)
    if collection is None:
        return 0
    removed = 0
    for obj in list(collection.objects):
        data = obj.data
        bpy.data.objects.remove(obj)
        if data is not None and data.users == 0:
            bpy.data.curves.remove(data)
        removed += 1
    return removed


def _wiring_rows(scene):
    """The stored row table the canvas is holding, or an empty list."""

    from . import wiring

    tree = getattr(scene, "cadex_wiring", None)
    if tree is None:
        return [], None
    return wiring.stored_rows(tree), tree


def _selected_row(context):
    """Which wire the user means: **the active object in the viewport**.

    The wire itself, clicked in the 3D view, and not a link on the wiring
    canvas. Two reasons, and the second is the one that settled it.

    A cable is a hydrated output like any other, so one object *is* one wire,
    unambiguously. Its name gives the row by the ``wire_<name>`` convention
    ``nets(...)`` scripts use, and a script predating ``nets(...)`` names the
    row after the output itself, so one lookup covers both.

    The node editor cannot answer the question at all. **A Blender
    ``NodeLink`` carries no selection state** — its whole RNA is
    ``from_node``/``from_socket``/``to_node``/``to_socket`` plus
    ``is_hidden``/``is_muted``/``is_valid`` — so "the selected wire" does not
    exist there, and the nearest thing, two selected board nodes, is ambiguous
    the moment a harness runs more than one signal between the same two
    boards, which is the normal case. That is also the right answer for the
    gesture: the path is dragged in 3D, so it is picked in 3D.
    """

    scene = getattr(context, "scene", None)
    if scene is None:
        return None
    obj = getattr(context, "active_object", None)
    output = str(obj.get(cadex_hydrate.OUTPUT_PROP) or "") if obj is not None else ""
    if not output:
        return None
    rows, _tree = _wiring_rows(scene)
    for row in rows:
        name = str(row.get("name") or "")
        if output in (name, "wire_" + name):
            return row
    return None


def _interior(row):
    """The handles a user may drag, from the row the engine published.

    The engine publishes the split rather than the spine alone (ADR-118), so
    there is no stub-knot arithmetic here and nothing that has to know how
    many knots a stand-off is written as: ``waypoints`` *is* the editable
    part, and it is exactly what goes back into ``waypoints=``.

    A straight run has an empty interior and still needs something to grab,
    so it gets the midpoint of its own centreline — one handle, which is the
    smallest authored path there is.
    """

    interior = [list(point) for point in (row.get("waypoints") or [])]
    if interior:
        return interior
    path = [list(point) for point in (row.get("path") or [])]
    if len(path) < 2:
        return []
    first, last = path[0], path[-1]
    return [[(first[k] + last[k]) / 2.0 for k in range(3)]]


# ---------------------------------------------------------------------------
# the operators


class MESH_AGENT_OT_edit_wire_path(bpy.types.Operator):
    """Open the active cable's route as a curve you can drag."""

    bl_idname = "mesh_agent.edit_wire_path"
    bl_label = "Edit Wire Path"
    bl_description = ("Open the active cable's route as an editable curve; "
                      "drag its points, then press Confirm")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Defensive about the context rather than trusting it: this runs on
        # every redraw of the chat row, including during a draw with no
        # window, and a poll that raises takes the whole panel with it.
        if getattr(context, "mode", 'OBJECT') not in ('OBJECT', 'EDIT_CURVE'):
            return False
        return _selected_row(context) is not None

    def execute(self, context):
        row = _selected_row(context)
        if row is None:
            self.report({'ERROR'},
                        "Click the wire in the viewport first — this edits "
                        "the route of the active cable.")
            return {'CANCELLED'}
        if str(row.get("kind") or "") == "bundle":
            # ADR-115 §4, and structural rather than advisory: the engine
            # publishes a bundle conductor with an empty interior because the
            # route belongs to the bundle, so authoring one conductor's path
            # would silently be authoring all of them.
            self.report(
                {'ERROR'},
                "That is one conductor of a bundle, and a bundle's route "
                "belongs to the whole lay. Change it in the script.")
            return {'CANCELLED'}
        points = _interior(row)
        if not points:
            self.report(
                {'ERROR'},
                "That wire has no published route to edit. Rebuild the model "
                "so the engine republishes it — a project accepted before "
                "this feature existed carries no route until it rebuilds.")
            return {'CANCELLED'}

        clear(context.scene)
        name = str(row.get("name") or "?")
        curve = bpy.data.curves.new("Wire Path " + name, 'CURVE')
        curve.dimensions = '3D'
        spline = curve.splines.new('POLY')
        # `new` starts a spline with one point already in it.
        spline.points.add(len(points) - 1)
        for index, point in enumerate(points):
            spline.points[index].co = (point[0], point[1], point[2], 1.0)

        obj = bpy.data.objects.new("Wire Path ▸ " + name, curve)
        obj[ROW_PROP] = name
        obj[ENDS_PROP] = json.dumps(
            [str(row.get("a") or ""), str(row.get("b") or "")])
        # Drawn like the collision overlay -- wire, in front, never rendered --
        # but *selectable*, because unlike that overlay this one exists to be
        # grabbed.
        obj.display_type = 'WIRE'
        obj.hide_render = True
        obj.show_in_front = True
        obj.hide_select = False
        _collection(context.scene).objects.link(obj)

        for other in context.selected_objects:
            other.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        try:
            bpy.ops.object.mode_set(mode='EDIT')
        except RuntimeError:
            # Headless, or a context that will not take a mode change. The
            # curve is there and selected either way, which is the part that
            # matters; the user can enter Edit Mode themselves.
            pass
        self.report(
            {'INFO'},
            "Drag the {:d} point(s) of {:s}, then press Confirm Wire "
            "Path.".format(len(points), name))
        return {'FINISHED'}


class MESH_AGENT_OT_confirm_wire_path(bpy.types.Operator):
    """Send the dragged path to the assistant and delete the curve."""

    bl_idname = "mesh_agent.confirm_wire_path"
    bl_label = "Confirm Wire Path"
    bl_description = ("Ask the assistant to write the dragged path into that "
                      "wire's part.cable call")
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        from . import agent as agent_module

        if agent_module.get_agent().busy:
            return False
        return path_object(getattr(context, "scene", None)) is not None

    def execute(self, context):
        from . import agent as agent_module

        obj = path_object(context.scene)
        if obj is None:
            self.report({'ERROR'}, "There is no wire path open to confirm.")
            return {'CANCELLED'}
        matrix = obj.matrix_world
        points = []
        for spline in obj.data.splines:
            for point in spline.points:
                world = matrix @ point.co.to_3d()
                points.append([round(float(value), 5) for value in world])
        if not points:
            self.report({'ERROR'}, "That curve has no points left to send.")
            return {'CANCELLED'}
        if len(points) > MAX_WAYPOINTS:
            self.report(
                {'ERROR'},
                "That curve carries {:d} points and a hand-authored path is "
                "capped at {:d}. Delete points, or press Cancel and steer the "
                "search with avoid= instead.".format(len(points),
                                                     MAX_WAYPOINTS))
            return {'CANCELLED'}

        try:
            ends = json.loads(str(obj.get(ENDS_PROP) or "[]"))
        except ValueError:
            ends = []
        row = str(obj.get(ROW_PROP) or "")
        queue_wire_path({
            "row": row,
            "a": ends[0] if len(ends) > 0 else "",
            "b": ends[1] if len(ends) > 1 else "",
            "points": points,
        })

        # Back to Object Mode before the object is removed: removing the
        # object the session is editing leaves the mode pointing at nothing.
        if context.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError:
                pass
        clear(context.scene)

        # One click and no typing, so the turn is started here rather than
        # left in the box -- the same way the send button and the input
        # field's confirm callback start one.
        if not agent_module.get_agent().start_turn(CONFIRM_PROMPT):
            self.report({'WARNING'},
                        "The path is queued; it will ride the next message.")
            return {'FINISHED'}
        self.report({'INFO'},
                    "Sent {:d} waypoints for {:s}.".format(len(points), row))
        return {'FINISHED'}


class MESH_AGENT_OT_cancel_wire_path(bpy.types.Operator):
    """Throw the dragged path away and leave the script alone."""

    bl_idname = "mesh_agent.cancel_wire_path"
    bl_label = "Cancel Wire Path"
    bl_description = ("Discard the dragged path; the script and the routed "
                      "wire are left exactly as they were")
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return path_object(getattr(context, "scene", None)) is not None

    def execute(self, context):
        # An explicit operator rather than "delete the object yourself": the
        # third state of this gesture is *abandoning* it, and a state you
        # reach by knowing which object to delete is not a state the UI has.
        if context.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except RuntimeError:
                pass
        removed = clear(context.scene)
        self.report({'INFO'},
                    "Wire path discarded." if removed else "Nothing to discard.")
        return {'FINISHED'}


classes = (
    MESH_AGENT_OT_edit_wire_path,
    MESH_AGENT_OT_confirm_wire_path,
    MESH_AGENT_OT_cancel_wire_path,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    _pending_paths.clear()
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
