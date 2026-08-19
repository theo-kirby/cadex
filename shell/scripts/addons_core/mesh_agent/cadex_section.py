# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Cut the model open in the viewport, so the inside can be looked at.

A bore that does not break through, a wall left 0.4 mm thick, a pocket that
missed the boss it was meant to clear: none of these show on the outside of a
solid, and the only tool the shell had for them was `inspect` and arithmetic.
This module puts a plane through the model and takes the near half away.

**It is a view, not a feature.** Nothing here reaches the engine, nothing here
is written to the script, and the accepted revision is the same revision with
the section on as with it off — which is what `docs/VISION.md` requires of
anything that is not the script. What it changes is the *display mirror* in
the Model collection, exactly as ``cadex_collision`` changes what is drawn
beside it.

Two mechanisms, because the model is drawn as two kinds of object:

- **the solids** get a Boolean DIFFERENCE modifier against one hidden cutter
  box. The cut face is *capped* — the boolean closes the surface it opens, so
  a cut bracket reads as solid material with a ring where the bore is, rather
  than as the inside of an empty shell. That capping is the whole reason this
  is a boolean and not the viewport's own clipping planes, which cannot fill
  what they open, are per-region view state that no screenshot carries, and
  cannot be exercised in the `--background` gate at all.
- **the edge wires** get a geometry-nodes modifier that deletes points on the
  far side of the same plane. A Boolean cannot help a mesh with no faces in
  it, and edges left uncut would hang in the air where the material they
  outline has gone.

Both are **modifiers**, and that is load-bearing: ``cadex_hydrate`` finds an
object by ``cadex_output`` and swaps its mesh datablock rather than rebuilding
the object, so a modifier survives every rebuild, every slider drag and every
settled refine without this module hearing about it. What it does have to hear
about is a *new* object — an output that was not in the last contract — which
is why ``cadex_backend.hydrate`` calls :func:`refresh`.

The pure half — everything above ``-- the bpy half --`` — imports no ``bpy``.
It is where the plane and the cutter's placement are worked out, which is the
arithmetic that can be silently wrong, and it is the half Phase 12 keeps.
"""

#: Collection name. A **sibling** of "Model" at the scene root, never a child:
#: ``cadex_hydrate``'s contract GC walks ``collection.all_objects``, which
#: recurses, and removes every tagged object that is not in the pass's keep
#: set. ``cadex_collision`` says this at length and it is as load-bearing here.
COLLECTION_NAME = "Section"

#: The one cutter object. A unit cube, placed by a scale+translation matrix,
#: so the whole plane lives in ``obj.matrix_world`` and there is no mesh to
#: rebuild when the offset moves.
CUTTER_NAME = "Section Cutter"

#: The modifier name on both kinds of object. One name is the whole cleanup
#: story: :func:`clear` removes every modifier called this, wherever it is.
MODIFIER_NAME = "Cadex Section"

#: The shared geometry-nodes group that clips the edge wires.
CLIP_GROUP_NAME = "Cadex Section Clip"

#: On the scene while the section is on: the report the panel draws from.
SCENE_FLAG = "cadex_section"

#: Slack added to the cutter, in model units (mm), so that a cutter face never
#: lands exactly on a model face — a coplanar boolean is the one input an
#: exact solver has no good answer for.
MARGIN_MM = 1.0

AXES = ('X', 'Y', 'Z')


# -- the pure half: no bpy, no scene ----------------------------------------

def axis_index(axis):
    """0, 1 or 2 for 'X', 'Y', 'Z'."""

    return AXES.index(str(axis).upper())


def plane_normal(axis, flip=False):
    """Unit normal pointing into the half that is **taken away**.

    Unflipped, the normal is the positive axis: the material above the plane
    goes, and you look down the axis into what is left. Flip swaps which half
    survives, which is the only thing a person ever wants to say about a
    section they are already looking at.
    """

    index = axis_index(axis)
    sign = -1.0 if flip else 1.0
    return tuple(sign if position == index else 0.0 for position in range(3))


def axis_span(bbox, axis):
    """``(low, high)`` of the model on this axis."""

    index = axis_index(axis)
    low, high = bbox
    return float(low[index]), float(high[index])


def centre_offset(bbox, axis):
    """Halfway through the model on this axis — where a new cut starts.

    A section that opens on the middle of the part shows something on the
    first frame. A section that opens at the origin shows the whole part, or
    none of it, depending on where the part happens to sit.
    """

    low, high = axis_span(bbox, axis)
    return (low + high) / 2.0


def diagonal(bbox):
    """Length of the bounding box's space diagonal."""

    low, high = bbox
    return sum((float(high[axis]) - float(low[axis])) ** 2
               for axis in range(3)) ** 0.5


def cutter_size(bbox):
    """Edge length of the cutter cube.

    Twice the diagonal plus slack: the cube is centred half its own edge back
    from the plane, so this guarantees it covers the whole of the removed half
    however the plane is turned, without ever being so large that the exact
    solver is asked to intersect a millimetre part with a kilometre box.
    """

    return 2.0 * diagonal(bbox) + 4.0 * MARGIN_MM


def plane_point(bbox, axis, offset):
    """A point on the cutting plane: the model's centre, moved to ``offset``."""

    low, high = bbox
    index = axis_index(axis)
    return tuple(float(offset) if position == index
                 else (float(low[position]) + float(high[position])) / 2.0
                 for position in range(3))


def cutter_matrix(bbox, axis, offset, flip=False):
    """Rows of the 4x4 that places the unit-cube cutter over the removed half.

    Scale on the diagonal, translation in the last column: a cube of side
    :func:`cutter_size` whose near face is the cutting plane and whose body
    covers everything :func:`plane_normal` points at.
    """

    size = cutter_size(bbox)
    point = plane_point(bbox, axis, offset)
    normal = plane_normal(axis, flip)
    centre = tuple(point[position] + normal[position] * size / 2.0
                   for position in range(3))
    return tuple(
        tuple(size if column == row else 0.0 for column in range(3))
        + (centre[row],)
        for row in range(3)
    ) + ((0.0, 0.0, 0.0, 1.0),)


def is_kept(point, axis, offset, flip=False):
    """Does world-space ``point`` survive the cut?

    The semantic statement of what this module does, in one line, so the gate
    can assert the geometry it gets back against the rule rather than against
    a second copy of the arithmetic.
    """

    index = axis_index(axis)
    return (float(point[index]) <= float(offset) if not flip
            else float(point[index]) >= float(offset))


def clear_of_model(bbox, axis, offset):
    """Is the plane past one end of the model, so the cut says nothing?

    Not an error and not clamped: a slider that refuses to leave the model is
    a slider that lies about where the model is. The panel says so instead.
    """

    low, high = axis_span(bbox, axis)
    return not (low < float(offset) < high)


# -- the bpy half -----------------------------------------------------------

#: Guard against an update callback that assigns to another property of the
#: same group and re-enters this module through its update callback.
_settling = False


def settings(scene=None):
    """The scene's section settings, or None on a file older than this."""

    import bpy
    scene = scene or bpy.context.scene
    return getattr(scene, "cadex_section", None)


def enabled(scene=None):
    group = settings(scene)
    return bool(group and group.show)


def _collection(scene, create=True):
    import bpy
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        if not create:
            return None
        collection = bpy.data.collections.new(COLLECTION_NAME)
    if collection.name not in scene.collection.children and create:
        scene.collection.children.link(collection)
    return collection


def _unit_cube():
    """A 1 mm cube mesh, shared by nothing else and rebuilt only if lost."""

    import bpy
    mesh = bpy.data.meshes.get(CUTTER_NAME)
    if mesh is not None:
        return mesh
    mesh = bpy.data.meshes.new(CUTTER_NAME)
    corners = [(x - 0.5, y - 0.5, z - 0.5)
               for z in (0, 1) for y in (0, 1) for x in (0, 1)]
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4),
             (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    mesh.from_pydata(corners, [], faces)
    mesh.update()
    return mesh


def cutter(scene=None, create=True):
    """The hidden cutter object, made if it is not there yet.

    Hidden by the eye rather than deleted from the view layer, and the
    difference matters both ways: a boolean operand is evaluated whatever its
    visibility (measured, not assumed), while ``scene.ray_cast`` skips a
    hidden object — so the box wrapped around the model can never steal the
    face pick that ``cadex_pick`` is there to make.
    """

    import bpy
    scene = scene or bpy.context.scene
    obj = bpy.data.objects.get(CUTTER_NAME)
    if obj is None:
        if not create:
            return None
        obj = bpy.data.objects.new(CUTTER_NAME, _unit_cube())
    collection = _collection(scene, create=True)
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    obj.hide_render = True
    obj.hide_select = True
    obj.display_type = 'WIRE'
    try:
        obj.hide_set(True)
    except Exception:
        # No view layer to hide it in (some background contexts). The
        # boolean does not care, and nothing else looks at it.
        pass
    return obj


def _clip_group():
    """The geometry-nodes group that deletes points past the plane.

    Built once and shared by every wire object. It takes the plane in the
    object's **own** coordinates — geometry nodes read ``Position`` locally,
    and a component instance's wire child sits at the component's placement —
    so :func:`_ensure_clip` converts before it assigns. Doing the conversion
    in Python keeps the group at eight nodes and keeps the one piece of
    arithmetic in the language the rest of this module is written in.
    """

    import bpy
    group = bpy.data.node_groups.get(CLIP_GROUP_NAME)
    if group is not None:
        return group

    group = bpy.data.node_groups.new(CLIP_GROUP_NAME, 'GeometryNodeTree')
    interface = group.interface
    interface.new_socket("Geometry", in_out='INPUT',
                         socket_type='NodeSocketGeometry')
    interface.new_socket("Geometry", in_out='OUTPUT',
                         socket_type='NodeSocketGeometry')
    interface.new_socket("Origin", in_out='INPUT',
                         socket_type='NodeSocketVector')
    interface.new_socket("Normal", in_out='INPUT',
                         socket_type='NodeSocketVector')

    nodes, links = group.nodes, group.links
    group_in = nodes.new('NodeGroupInput')
    group_out = nodes.new('NodeGroupOutput')
    position = nodes.new('GeometryNodeInputPosition')
    offset = nodes.new('ShaderNodeVectorMath')
    offset.operation = 'SUBTRACT'
    projection = nodes.new('ShaderNodeVectorMath')
    projection.operation = 'DOT_PRODUCT'
    beyond = nodes.new('FunctionNodeCompare')
    beyond.data_type = 'FLOAT'
    beyond.operation = 'GREATER_THAN'
    delete = nodes.new('GeometryNodeDeleteGeometry')
    delete.domain = 'POINT'
    delete.mode = 'ALL'

    for index, node in enumerate((group_in, position, offset, projection,
                                  beyond, delete, group_out)):
        node.location = (index * 180, 0)

    links.new(position.outputs["Position"], offset.inputs[0])
    links.new(group_in.outputs["Origin"], offset.inputs[1])
    links.new(offset.outputs["Vector"], projection.inputs[0])
    links.new(group_in.outputs["Normal"], projection.inputs[1])
    links.new(projection.outputs["Value"], beyond.inputs[0])
    links.new(beyond.outputs["Result"], delete.inputs["Selection"])
    links.new(group_in.outputs["Geometry"], delete.inputs["Geometry"])
    links.new(delete.outputs["Geometry"], group_out.inputs["Geometry"])
    return group


def _socket_identifiers(group):
    """``{socket name: RNA identifier}`` for the group's inputs.

    Blender 5 exposes a nodes modifier's inputs as generated RNA structs at
    ``modifier.properties.inputs.<identifier>.value``, and the identifier is
    ``Socket_<n>`` rather than the name. Looked up rather than hard-coded: the
    numbering depends on the order the sockets were declared in.
    """

    found = {}
    for item in group.interface.items_tree:
        if getattr(item, "item_type", "") != 'SOCKET':
            continue
        if getattr(item, "in_out", "") != 'INPUT':
            continue
        found.setdefault(item.name, item.identifier)
    return found


def model_objects():
    """``(solids, wires)`` of the hydrated model, or two empty lists."""

    from . import cadex_hydrate
    try:
        collection = cadex_hydrate._model_collection()
    except Exception:
        return [], []
    solids, wires = [], []
    for obj in cadex_hydrate._cadex_objects(collection):
        if obj.type != 'MESH':
            continue
        if obj.name.endswith(cadex_hydrate.EDGE_SUFFIX):
            wires.append(obj)
        else:
            solids.append(obj)
    return solids, wires


def _ensure_boolean(obj, cutter_object):
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is None or modifier.type != 'BOOLEAN':
        if modifier is not None:
            obj.modifiers.remove(modifier)
        modifier = obj.modifiers.new(MODIFIER_NAME, 'BOOLEAN')
    modifier.operation = 'DIFFERENCE'
    # EXACT rather than MANIFOLD: a tessellated BREP is usually a closed
    # manifold and usually is not the interesting case. The one that matters
    # is a mesh-domain import, which may be neither, and EXACT is the solver
    # that answers for both.
    modifier.solver = 'EXACT'
    modifier.object = cutter_object
    modifier.show_render = False
    modifier.show_viewport = True
    return modifier


def _ensure_clip(obj, origin, normal):
    """Put the plane on a wire object's clip modifier, in its own frame."""

    from mathutils import Vector

    group = _clip_group()
    modifier = obj.modifiers.get(MODIFIER_NAME)
    if modifier is None or modifier.type != 'NODES':
        if modifier is not None:
            obj.modifiers.remove(modifier)
        modifier = obj.modifiers.new(MODIFIER_NAME, 'NODES')
    modifier.node_group = group
    modifier.show_render = False
    modifier.show_viewport = True

    inverse = obj.matrix_world.inverted_safe()
    local_origin = inverse @ Vector(origin)
    local_normal = (obj.matrix_world.to_3x3().inverted_safe().transposed()
                    @ Vector(normal))
    if local_normal.length > 0.0:
        local_normal = local_normal.normalized()

    identifiers = _socket_identifiers(group)
    inputs = modifier.properties.inputs
    getattr(inputs, identifiers["Origin"]).value = tuple(local_origin)
    getattr(inputs, identifiers["Normal"]).value = tuple(local_normal)
    obj.update_tag()
    return modifier


def model_bounds():
    """World-space bounds of the model **as built**, ignoring this cut.

    Deliberately not ``capture.model_bbox``, which reads ``obj.bound_box`` --
    and ``bound_box`` reflects *evaluated* geometry, so with the section on it
    returns the bounds of the half that survived. Measured, not assumed: a
    20 mm cube cut at z = 5 reports a top of 5.

    Every number this module derives from the model would then feed back on
    the cut that produced it -- the centre of the axis would drift into the
    kept half on each rebuild, and the offset a person is dragging would be
    measured against a range that moves as they drag it. So this reads the
    mesh datablocks instead, which is the shape the engine published and the
    shape the offset means something against.
    """

    import numpy as np

    from . import cadex_hydrate

    try:
        collection = cadex_hydrate._model_collection()
    except Exception:
        return None
    low = [float("inf")] * 3
    high = [float("-inf")] * 3
    seen = False
    for obj in cadex_hydrate._cadex_objects(collection):
        mesh = obj.data
        if obj.type != 'MESH' or mesh is None or not mesh.vertices:
            continue
        if obj.name.endswith(cadex_hydrate.EDGE_SUFFIX):
            continue          # the wires trace the solids; measuring adds nothing
        # ADR-049: an instanced source is hidden and drawn through its
        # components, so measuring it would size the cut to geometry nobody
        # can see -- the same reason ``capture.model_bbox`` skips it.
        if not obj.visible_get():
            continue
        coordinates = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", coordinates)
        points = coordinates.reshape(-1, 3)
        matrix = np.array(obj.matrix_world.transposed(), dtype=np.float64)
        world = points @ matrix[:3, :3] + matrix[3, :3]
        low = [min(low[axis], float(world[:, axis].min())) for axis in range(3)]
        high = [max(high[axis], float(world[:, axis].max())) for axis in range(3)]
        seen = True
    return (tuple(low), tuple(high)) if seen else None


def _model_bbox():
    return model_bounds()


def refresh(scene=None):
    """Make the scene agree with the settings. The one entry point.

    Called on every accepted response as well as on every settings change,
    because an output that has just entered the contract is a brand-new
    object with no modifier on it, and a section that quietly stopped
    applying to the newest part is worse than no section.
    """

    import bpy
    from mathutils import Matrix

    scene = scene or bpy.context.scene
    group = settings(scene)
    if group is None or not group.show:
        return clear(scene)

    bbox = _model_bbox()
    if bbox is None:
        clear(scene, forget=False)
        report = {"shown": False, "reason": "no model"}
        scene[SCENE_FLAG] = report
        return report

    axis, offset, flip = group.axis, float(group.offset), bool(group.flip)
    box = cutter(scene)
    box.matrix_world = Matrix(cutter_matrix(bbox, axis, offset, flip))

    solids, wires = model_objects()
    for obj in solids:
        _ensure_boolean(obj, box)
    origin = plane_point(bbox, axis, offset)
    normal = plane_normal(axis, flip)
    for obj in wires:
        _ensure_clip(obj, origin, normal)

    low, high = axis_span(bbox, axis)
    report = {
        "shown": True,
        "axis": axis,
        "offset": offset,
        "flip": flip,
        "solids": len(solids),
        "wires": len(wires),
        "span": [low, high],
        "clear": clear_of_model(bbox, axis, offset),
    }
    scene[SCENE_FLAG] = report
    return report


def clear(scene=None, forget=True):
    """Take the section off everything and remove what drew it.

    Walks ``bpy.data.objects`` rather than the Model collection: the object an
    outdated modifier is sitting on may have left the contract, been moved, or
    come in from a file saved with the section on, and one name is the whole
    cleanup story only if the sweep is over everything.
    """

    import bpy
    scene = scene or bpy.context.scene

    removed = 0
    for obj in bpy.data.objects:
        modifier = obj.modifiers.get(MODIFIER_NAME) if obj.modifiers else None
        if modifier is not None:
            obj.modifiers.remove(modifier)
            removed += 1

    box = bpy.data.objects.get(CUTTER_NAME)
    if box is not None:
        mesh = box.data
        bpy.data.objects.remove(box)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is not None and not collection.all_objects:
        bpy.data.collections.remove(collection)
    group = bpy.data.node_groups.get(CLIP_GROUP_NAME)
    if group is not None and group.users == 0:
        bpy.data.node_groups.remove(group)

    if forget and SCENE_FLAG in scene:
        del scene[SCENE_FLAG]
    return {"shown": False, "cleared": removed}


def suspend(scene=None):
    """Turn the section off for the duration of a render; returns an undo.

    ``render_views`` answers "what did I build", frames the Model collection
    itself and hides every overlay to do it (ADR-124). A cut model is not what
    was built, so it is suspended there for the same reason the collision cage
    is hidden there — and left alone in ``viewport_screenshot``, which answers
    the other question: what is the user looking at.
    """

    suspended = []
    for obj in _all_sectioned():
        modifier = obj.modifiers.get(MODIFIER_NAME)
        if modifier is not None and modifier.show_viewport:
            modifier.show_viewport = False
            suspended.append(obj.name)

    # Bounds are recomputed during evaluation, and the caller's next act is
    # to measure the model to fit cameras to it. Without this the first
    # render frames the half that was still cut when it asked -- the same
    # class of miss ``_isolate_model`` records having measured.
    if suspended:
        import bpy
        bpy.context.view_layer.update()
        bpy.context.evaluated_depsgraph_get()

    def restore():
        import bpy
        for name in suspended:
            obj = bpy.data.objects.get(name)
            modifier = obj.modifiers.get(MODIFIER_NAME) if obj else None
            if modifier is not None:
                modifier.show_viewport = True

    return restore


def _all_sectioned():
    import bpy
    return [obj for obj in bpy.data.objects
            if obj.modifiers and obj.modifiers.get(MODIFIER_NAME) is not None]


def toggle(on=None, scene=None):
    """Turn the section on or off. Returns the resulting report."""

    import bpy
    scene = scene or bpy.context.scene
    group = settings(scene)
    if group is None:
        return {"shown": False,
                "message": "This file predates the section view; save and "
                           "reopen it."}

    global _settling
    want = (not group.show) if on is None else bool(on)
    if not want:
        group.show = False           # its update callback clears the scene
        return {"shown": False}

    bbox = _model_bbox()
    if bbox is None:
        return {"shown": False,
                "message": ("There is no model in the viewport to cut. "
                            "Rebuild first.")}

    _settling = True
    try:
        group.offset = centre_offset(bbox, group.axis)
        group.show = True
    finally:
        _settling = False
    return refresh(scene)


def _on_setting_changed(_self, context):
    if _settling:
        return
    try:
        refresh(getattr(context, "scene", None))
    except Exception:
        import traceback
        traceback.print_exc()


def _on_axis_changed(self, context):
    """Re-centre when the axis changes: the ranges are not the same.

    An offset that cut the middle of a 40 mm part on Z is off the end of a
    6 mm part on Y, so keeping the number would trade one axis's useful cut
    for another axis's blank viewport.
    """

    global _settling
    if _settling:
        return
    bbox = _model_bbox()
    if bbox is not None:
        _settling = True
        try:
            self.offset = centre_offset(bbox, self.axis)
        finally:
            _settling = False
    _on_setting_changed(self, context)


def _register_settings():
    import bpy

    class CadexSectionSettings(bpy.types.PropertyGroup):
        """Where the cutting plane is. Saved in the file, like any view state."""

        show: bpy.props.BoolProperty(
            name="Section",
            description="Cut the model open on a plane so the inside is visible",
            default=False,
            update=_on_setting_changed,
        )
        axis: bpy.props.EnumProperty(
            name="Axis",
            description="Which axis the cutting plane is square to",
            items=(('X', "X", "Cut across X"),
                   ('Y', "Y", "Cut across Y"),
                   ('Z', "Z", "Cut across Z")),
            default='Z',
            update=_on_axis_changed,
        )
        offset: bpy.props.FloatProperty(
            name="Offset",
            description="Where the plane sits along the axis, in mm",
            default=0.0,
            step=100,           # 1 mm per drag step, not 0.01
            precision=2,
            update=_on_setting_changed,
        )
        flip: bpy.props.BoolProperty(
            name="Flip",
            description="Keep the other half",
            default=False,
            update=_on_setting_changed,
        )

    bpy.utils.register_class(CadexSectionSettings)
    bpy.types.Scene.cadex_section = bpy.props.PointerProperty(
        type=CadexSectionSettings)
    return CadexSectionSettings


_settings_class = None


def _hydrate_hook(_payload, _root, _animate):
    """The registry hook (ADR-148): an output that has just entered the
    contract is a NEW object, and a new object has no modifier on it.
    Everything else about the section survives a rebuild by itself --
    ``cadex_hydrate`` swaps the mesh datablock and keeps the object. Mid-drag
    it refreshes rather than clearing: the cut is computed from the shape in
    front of you -- the dimension trade, not the collision one."""

    return refresh() if enabled() else None


def _preview_hook(scene):
    """A pose-only preview moved objects without rehydrating them, and the
    wire clip carries the plane in each object's OWN frame -- so a component
    that just moved is cut on the plane it was at before. The solids need
    nothing: their cutter is in world space and does not move."""

    if enabled(scene):
        refresh(scene)


def register():
    global _settings_class
    _settings_class = _register_settings()
    from . import cadex_views
    cadex_views.register_view(name="section", order=30,
                              on_hydrate=_hydrate_hook,
                              on_preview=_preview_hook,
                              suspend=suspend)


def unregister():
    import bpy
    global _settings_class
    from . import cadex_views
    cadex_views.unregister_view("section")
    try:
        del bpy.types.Scene.cadex_section
    except Exception:
        pass
    if _settings_class is not None:
        bpy.utils.unregister_class(_settings_class)
        _settings_class = None
