# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Spread an assembly apart in the viewport, so how it goes together shows.

An assembled mechanism hides its own construction: the bore is inside the
housing, the pin is inside the bore, and a screenshot of the solved state
says nothing about what stacks on what. The engine has always been able to
say — ``assembly.exploded_view`` computes staged moves, final placements and
leader lines — and until ADR-149 all of it died inside the worker. Now the
display entry of that output carries the record, and this module is the
client: a toggle plus a factor slider from 0 (assembled) to 1 (fully
exploded), interpolated live with no engine round trip.

**It is a view, not a feature** (the ADR-148 shape, exactly). Nothing here
reaches the engine, nothing is written to the script, and the accepted
revision is the same revision with the explosion on as with it off. What it
changes is ``matrix_world`` on the component instances — the channel the
hydrate path already owns and re-writes on every rebuild, which is why
``cadex_backend.hydrate`` calls :func:`refresh` after it: engine poses land
first, the explosion is re-applied from the *new* record after, always in
that order. Deliberately not delta channels or F-Curves: their interaction
with ``matrix_world`` assignment is undocumented, and a baked simulation
already owns the animation system — which is why :func:`toggle` refuses
while one is baked rather than pretending the two can share an object.

The moves are **engine-declared**: the AI authors them in the script, the
worker validates them against FreeCAD's own exploded-view graph, and this
module invents no geometry — it interpolates between poses the engine
published and draws the leader lines the engine measured.

The pure half — everything above ``-- the bpy half --`` — imports no ``bpy``
and no ``mathutils``. It is where the staged windows, the slerp and the line
growth are worked out, which is the arithmetic that can be silently wrong,
and it is the half Phase 12 keeps.
"""

import math

#: Collection name. A **sibling** of "Model" at the scene root, never a
#: child: ``cadex_hydrate``'s contract GC walks ``collection.all_objects``,
#: which recurses, and removes every tagged object not in the pass's keep
#: set. The wire object below carries no ``cadex_output`` tag either — two
#: fences, the same reasoning ``cadex_collision`` records at length.
COLLECTION_NAME = "Exploded"

#: The one leader-line object. Real geometry rather than a GPU draw handler
#: (the dimension precedent) because the lines must survive a
#: ``--background`` gate run and appear in renders — the collision cage's
#: trade, made for the collision cage's reason.
LINES_NAME = "Exploded Lines"

#: On the scene while the explosion is on: the report the panel draws from.
SCENE_FLAG = "cadex_explode"


# -- the pure half: no bpy, no mathutils ------------------------------------

def exploded_entry(display_map):
    """The one exploded view in a display map, per the one-output rule.

    Returns ``((name, record), "")`` when exactly one display entry carries
    an ``exploded_view`` record, and ``(None, reason)`` otherwise — with the
    multiple-views reason naming every candidate, so the refusal tells the
    user which outputs are fighting (the two-simulations rule of
    ``cadex_animate``, applied here).
    """

    found = [(name, (display_map or {})[name]["exploded_view"])
             for name in sorted(display_map or {})
             if isinstance((display_map or {}).get(name), dict)
             and isinstance(display_map[name].get("exploded_view"), dict)]
    if not found:
        return None, "This model declares no exploded view."
    if len(found) > 1:
        return None, ("This model declares {:d} exploded views ({:s}); the "
                      "viewport can play one. Keep one in the script.".format(
                          len(found),
                          ", ".join(name for name, _record in found)))
    return found[0], ""


def stage_window(index, count):
    """``(start, end)`` of stage ``index``'s slice of the 0..1 factor."""

    return float(index) / float(count), float(index + 1) / float(count)


def decompose_matrix16(values):
    """Row-major 16-float placement matrix to ``(position, quaternion_xyzw)``.

    The factor-0 endpoint: every component's display entry carries its solved
    placement in exactly this form, and hand-rolling the conversion (rather
    than reaching for mathutils) keeps the endpoint in the half a unit test
    can reach. Shepperd's branch method, so the largest diagonal term is the
    one divided by and a 180-degree pose costs no precision.
    """

    values = [float(value) for value in values]
    row = lambda index: values[index * 4:index * 4 + 4]  # noqa: E731
    m00, m01, m02, _ = row(0)
    m10, m11, m12, _ = row(1)
    m20, m21, m22, _ = row(2)
    position = (values[3], values[7], values[11])
    trace = m00 + m11 + m22
    if trace > 0.0:
        s = (trace + 1.0) ** 0.5 * 2.0
        quaternion = ((m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s,
                      0.25 * s)
    elif m00 >= m11 and m00 >= m22:
        s = (1.0 + m00 - m11 - m22) ** 0.5 * 2.0
        quaternion = (0.25 * s, (m01 + m10) / s, (m02 + m20) / s,
                      (m21 - m12) / s)
    elif m11 >= m22:
        s = (1.0 + m11 - m00 - m22) ** 0.5 * 2.0
        quaternion = ((m01 + m10) / s, 0.25 * s, (m12 + m21) / s,
                      (m02 - m20) / s)
    else:
        s = (1.0 + m22 - m00 - m11) ** 0.5 * 2.0
        quaternion = ((m02 + m20) / s, (m12 + m21) / s, 0.25 * s,
                      (m10 - m01) / s)
    return position, quaternion


def _lerp3(a, b, s):
    return tuple(a[axis] + (b[axis] - a[axis]) * s for axis in range(3))


def _slerp(a, b, s):
    """Spherical interpolation, xyzw, with the hemisphere flip.

    q and -q are the same orientation and the engine normalizes without
    de-flipping (``cadex_animate._continuous`` records the same hazard on
    the trace path); interpolating across a flip takes the long way round.
    """

    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0.0:
        b = tuple(-value for value in b)
        dot = -dot
    if dot > 0.9995:                       # nearly parallel: lerp + renorm
        blended = tuple(x + (y - x) * s for x, y in zip(a, b))
        length = sum(value * value for value in blended) ** 0.5
        return tuple(value / length for value in blended) if length else a
    theta = math.acos(max(-1.0, min(1.0, dot)))
    sin_theta = math.sin(theta)
    weight_a = math.sin((1.0 - s) * theta) / sin_theta
    weight_b = math.sin(s * theta) / sin_theta
    return tuple(x * weight_a + y * weight_b for x, y in zip(a, b))


def poses_at(t, solved_poses, stages):
    """Every component's ``(position, quaternion_xyzw)`` at factor ``t``.

    Stage *i* of *N* animates over t in [i/N, (i+1)/N]; a component moves
    inside its own windows, holds outside them, and carries earlier stages
    forward — the record's stage poses are already cumulative, so "carry"
    is just taking the last completed stage's pose as the next lerp start.
    Components no stage names sit at their solved pose at every factor.
    """

    t = max(0.0, min(1.0, float(t)))
    count = len(stages)
    result = dict(solved_poses)
    for index, stage in enumerate(stages):
        start, end = stage_window(index, count)
        for name in sorted(stage.get("poses") or {}):
            if name not in result:
                continue
            pose = stage["poses"][name]
            target = (tuple(float(v) for v in pose["position_mm"]),
                      tuple(float(v) for v in pose["quaternion_xyzw"]))
            if t >= end:
                result[name] = target
            elif t > start:
                s = (t - start) / (end - start)
                position, quaternion = result[name]
                result[name] = (_lerp3(position, target[0], s),
                                _slerp(quaternion, target[1], s))
            # t <= start: hold whatever the earlier stages left.
    return result


def component_progress(t, stages):
    """Each moved component's own 0..1 progress at factor ``t``.

    A component named by two of four stages is halfway when its first move
    has landed and its second has not started, whatever the global factor
    says — this is what the leader lines grow with.
    """

    t = max(0.0, min(1.0, float(t)))
    count = len(stages)
    windows = {}
    done = {}
    for index, stage in enumerate(stages):
        start, end = stage_window(index, count)
        for name in stage.get("poses") or {}:
            windows[name] = windows.get(name, 0) + 1
            if t >= end:
                share = 1.0
            elif t > start:
                share = (t - start) / (end - start)
            else:
                share = 0.0
            done[name] = done.get(name, 0.0) + share
    return {name: done[name] / windows[name] for name in windows}


def line_points_at(t, lines, progress):
    """The leader segments to draw at factor ``t``, grown, zero-length ones
    dropped.

    The record flattens lines in move order, so the k-th line of a component
    is the k-th move that named it: it grows over slice [k/m, (k+1)/m] of
    that component's own progress, which keeps each line growing exactly
    while its move is animating.
    """

    totals = {}
    for line in lines or []:
        name = str(line["component_output"])
        totals[name] = totals.get(name, 0) + 1
    seen = {}
    segments = []
    for line in lines or []:
        name = str(line["component_output"])
        index = seen.get(name, 0)
        seen[name] = index + 1
        share = float(progress.get(name, 0.0)) * totals[name] - index
        share = max(0.0, min(1.0, share))
        if share <= 0.0:
            continue
        start = tuple(float(value) for value in line["start_mm"])
        end = tuple(float(value) for value in line["end_mm"])
        segments.append((start, _lerp3(start, end, share)))
    return segments


# -- the bpy half -----------------------------------------------------------

#: Guard against an update callback that assigns to another property of the
#: same group and re-enters this module through its update callback.
_settling = False


def settings(scene=None):
    """The scene's explosion settings, or None on a file older than this."""

    import bpy
    scene = scene or bpy.context.scene
    return getattr(scene, "cadex_explode", None)


def enabled(scene=None):
    group = settings(scene)
    return bool(group and group.show)


def _accepted_display(scene=None):
    """The last *settled* response's display map — never a preview's.

    ``cadex_backend`` records ``{display, revision}`` only on accepting
    responses, and the preview path drops exploded views engine-side
    (``skip_derived``), so this is both the freshest record there is and
    the only one there could be.
    """

    import bpy
    from . import cadex_backend
    scene = scene or bpy.context.scene
    root = cadex_backend.project_root(scene)
    return dict(cadex_backend.last_accepted(root).get("display") or {})


def _solved_poses(display_map, component_names):
    """``{component: (position, quaternion)}`` from the display placements.

    The factor-0 endpoint is the component's own solved ``placement`` — the
    matrix the hydrate path wrote — not anything this record carries, so 0
    means "exactly as built" by construction rather than by agreement.
    """

    poses = {}
    for name in component_names:
        entry = display_map.get(name) or {}
        placement = entry.get("placement")
        if isinstance(placement, list) and len(placement) == 16:
            poses[name] = decompose_matrix16(placement)
    return poses


def _matrix_of(position, quaternion_xyzw):
    from mathutils import Matrix, Quaternion, Vector
    x, y, z, w = (float(value) for value in quaternion_xyzw)
    matrix = Quaternion((w, x, y, z)).to_matrix().to_4x4()
    matrix.translation = Vector(position)
    return matrix


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


def _rebuild_lines(scene, segments):
    """Replace the leader-line wire with this factor's segments."""

    import bpy

    obj = bpy.data.objects.get(LINES_NAME)
    if not segments:
        _remove_lines()
        return 0

    vertices = []
    edges = []
    for start, end in segments:
        vertices.extend((start, end))
        edges.append((len(vertices) - 2, len(vertices) - 1))
    mesh = bpy.data.meshes.new(LINES_NAME)
    mesh.from_pydata(vertices, edges, [])
    mesh.update()

    if obj is None:
        obj = bpy.data.objects.new(LINES_NAME, mesh)
        obj.display_type = 'WIRE'
        obj.hide_select = True
        _collection(scene).objects.link(obj)
    else:
        previous = obj.data
        obj.data = mesh
        if previous is not None and previous.users == 0:
            bpy.data.meshes.remove(previous)
    return len(segments)


def _remove_lines():
    import bpy
    obj = bpy.data.objects.get(LINES_NAME)
    if obj is not None:
        mesh = obj.data
        bpy.data.objects.remove(obj)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is not None and not collection.all_objects:
        bpy.data.collections.remove(collection)


def _apply_poses(poses):
    """Write ``matrix_world`` on every posed component that is drawn.

    The wire children are parented to their components with an identity
    parent inverse, so they follow for free — exactly as they do on the
    hydrate and preview paths.
    """

    from . import cadex_hydrate

    try:
        collection = cadex_hydrate._model_collection()
    except Exception:
        return 0
    moved = 0
    for name in sorted(poses):
        obj = cadex_hydrate._find(collection, name, edges=False)
        if obj is None:
            continue
        obj.matrix_world = _matrix_of(*poses[name])
        moved += 1
    return moved


def refresh(scene=None):
    """Make the scene agree with the settings. The one entry point.

    Called on every accepted response as well as on every settings change,
    because engine poses land first (``hydrate``/``apply_placements`` write
    ``matrix_world``) and the explosion must be re-applied after them, from
    whatever record the response carried — a rebuild that moved a bore
    10 mm moves the exploded bore 10 mm too, on the same response.
    """

    import bpy

    scene = scene or bpy.context.scene
    group = settings(scene)
    if group is None or not group.show:
        return clear(scene)

    display = _accepted_display(scene)
    entry, reason = exploded_entry(display)
    if entry is None:
        _remove_lines()
        report = {"shown": False, "reason": reason}
        scene[SCENE_FLAG] = report
        return report

    name, record = entry
    stages = list(record.get("stages") or [])
    solved = _solved_poses(display, list(record.get("final_poses") or {}))
    factor = float(group.factor)
    moved = _apply_poses(poses_at(factor, solved, stages))
    segments = line_points_at(factor, record.get("lines") or [],
                              component_progress(factor, stages))
    drawn = _rebuild_lines(scene, segments)

    report = {
        "shown": True,
        "output": name,
        "assembly": str(record.get("assembly_output") or ""),
        "factor": factor,
        "stages": len(stages),
        "components": moved,
        "lines": drawn,
    }
    scene[SCENE_FLAG] = report
    return report


def clear(scene=None, forget=True):
    """Reassemble the model and remove what drew the explosion.

    Restoring is writing each component's solved display placement back —
    the same channel, the same source of truth the hydrate path uses — so
    off is not "roughly where it was", it is the matrix the engine
    published.
    """

    import bpy
    scene = scene or bpy.context.scene

    display = _accepted_display(scene)
    entry, _reason = exploded_entry(display)
    restored = 0
    if entry is not None:
        _name, record = entry
        solved = _solved_poses(display, list(record.get("final_poses") or {}))
        restored = _apply_poses(solved)
    _remove_lines()

    if forget and SCENE_FLAG in scene:
        del scene[SCENE_FLAG]
    return {"shown": False, "restored": restored}


def suspend(scene=None):
    """Reassemble for the duration of a render; returns an undo.

    ``render_views`` answers "what did I build", and an exploded model is
    not what was built — the section view is suspended there on the same
    reasoning (ADR-124, ADR-148), and ``viewport_screenshot`` leaves both
    alone because it answers what the user is looking at.
    """

    import bpy

    if not enabled(scene):
        return lambda: None

    clear(scene, forget=False)
    # The caller's next act is to measure the model and fit cameras to it,
    # and bounds are recomputed during evaluation — without this the first
    # render frames the spread the components were still at when it asked.
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get()

    def restore():
        try:
            refresh(scene)
        except Exception:
            import traceback
            traceback.print_exc()

    return restore


def toggle(on=None, scene=None):
    """Turn the explosion on or off. Returns the resulting report."""

    import bpy
    from . import cadex_animate

    scene = scene or bpy.context.scene
    group = settings(scene)
    if group is None:
        return {"shown": False,
                "message": "This file predates the exploded view; save and "
                           "reopen it."}

    global _settling
    want = (not group.show) if on is None else bool(on)
    if not want:
        group.show = False           # its update callback clears the scene
        return {"shown": False}

    # F-Curves on the basis channels and matrix_world writes cannot share an
    # object honestly: the depsgraph re-evaluates the action over whatever
    # this module writes, at its own times. Mutual exclusion, not layering.
    if cadex_animate.SCENE_FLAG in scene:
        return {"shown": False,
                "message": ("A simulation is baked on these components; "
                            "clear the simulation first, then explode.")}

    entry, reason = exploded_entry(_accepted_display(scene))
    if entry is None:
        return {"shown": False, "message": reason}

    _settling = True
    try:
        if group.factor <= 0.0:
            group.factor = 1.0       # 0 on the first frame shows nothing
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


def _register_settings():
    import bpy

    class CadexExplodeSettings(bpy.types.PropertyGroup):
        """How far apart the assembly is. Saved in the file, like any view
        state."""

        show: bpy.props.BoolProperty(
            name="Exploded",
            description="Spread the assembly along its declared explosion "
                        "moves, so how it goes together is visible",
            default=False,
            update=_on_setting_changed,
        )
        factor: bpy.props.FloatProperty(
            name="Factor",
            description="0 is assembled, 1 is fully exploded",
            default=1.0,
            min=0.0,
            max=1.0,
            update=_on_setting_changed,
        )

    bpy.utils.register_class(CadexExplodeSettings)
    bpy.types.Scene.cadex_explode = bpy.props.PointerProperty(
        type=CadexExplodeSettings)
    return CadexExplodeSettings


_settings_class = None


def _hydrate_hook(_payload, _root, _animate):
    """The registry hook (ADR-149), ordered AFTER the section's and for a
    sharper reason than a new object: hydrate just wrote every component's
    SOLVED matrix_world, and an explosion that is on must be re-applied on
    top of those fresh poses — from the record THIS response carried, so a
    rebuild that moved a part moves its exploded pose on the same response.
    Order is the contract: engine poses first, explosion after, always."""

    return refresh() if enabled() else None


def _preview_hook(scene):
    """``apply_placements`` just wrote solved preview poses over the exploded
    ones, so re-apply the explosion — from the last SETTLED record, whose
    endpoints are stale against this drag by design (the preview path drops
    exploded views engine-side). The settled rebuild behind the drag
    refreshes the endpoints through the hydrate hook above."""

    if enabled(scene):
        refresh(scene)


def register():
    global _settings_class
    _settings_class = _register_settings()
    from . import cadex_views
    cadex_views.register_view(name="explode", order=40,
                              on_hydrate=_hydrate_hook,
                              on_preview=_preview_hook,
                              suspend=suspend)


def unregister():
    import bpy
    global _settings_class
    from . import cadex_views
    cadex_views.unregister_view("explode")
    try:
        del bpy.types.Scene.cadex_explode
    except Exception:
        pass
    if _settings_class is not None:
        bpy.utils.unregister_class(_settings_class)
        _settings_class = None
