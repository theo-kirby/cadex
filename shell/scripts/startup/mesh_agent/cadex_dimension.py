# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Draw a declared measurement as an architectural dimension (cadex ADR-139).

The engine publishes a measurement as two exact anchor points in model space
and a formatted number (``part.measurement``; the record arrives on the
response's ``display`` entry). This module draws it: an extension line at each
anchor, a dimension line between them, and the number in the middle with the
line broken around it.

**Everything except the two anchors is computed in screen space**, and that is
the whole design rather than an implementation detail:

- the number is always upright and always the same size, at any zoom;
- the dimension line's offset direction is perpendicular *on the screen*, so
  it can never go edge-on however you orbit;
- extension gaps, ticks and text padding are pixel constants, so a dimension
  on a 2 mm boss and one on a 2 m beam read identically.

The cost, stated rather than discovered: a dimension draws over the part
rather than behind it (``depth_test_set('NONE')``, as the force arrows in
``cadex_live`` already do). Architectural drawings do not occlude their
dimensions either.

**The degenerate case is handled, not avoided.** Look straight down the
measured axis and the two anchors project to nearly the same pixel. Below
``MINIMUM_SPAN_PX`` this stops being a dimension and becomes a *leader* -- a
short stub and the number. The value is never lost at any viewing angle, which
is the whole point of the feature.

Unlike ``cadex_collision`` and ``cadex_cage``, this overlay creates **no
Blender objects**. So it needs no sibling collection and cannot be swept by
``cadex_hydrate``'s contract GC -- the trap both of those had to design around
does not exist here.

The pure half -- everything above ``-- the bpy half --`` -- imports no ``bpy``
and is where every number that can be wrong lives. It is exercised by
``bl_mesh_agent.py``, the suite that needs no engine.
"""

import math

#: How far the dimension line sits off the line joining the two anchors.
OFFSET_PX = 24.0

#: The gap between an anchor and where its extension line starts. Drafting
#: convention, and it also stops the extension line from hiding the very
#: feature it points at.
EXTENSION_GAP_PX = 5.0

#: How far an extension line runs past the dimension line.
EXTENSION_OVERRUN_PX = 6.0

#: Half-length of the slash tick at each end of the dimension line. Slashes
#: rather than arrowheads: two segments each instead of three, and they stay
#: legible at the sizes this overlay actually draws at.
TICK_PX = 5.0

#: Clear space left either side of the number when the dimension line is
#: broken around it.
TEXT_PAD_PX = 5.0

#: Text height. Matches the force-arrow overlay in ``cadex_live``.
TEXT_SIZE_PX = 13

#: Below this on-screen span a dimension is edge-on and becomes a leader.
#: Twelve pixels is about where two extension lines and a tick stop being
#: distinguishable from a single blob.
MINIMUM_SPAN_PX = 12.0

#: The leader's stub length, and the direction it leaves the anchor in
#: (up and to the right, in screen pixels).
LEADER_PX = 22.0
LEADER_DIRECTION = (0.7071067811865476, 0.7071067811865476)

#: Samples around a circle when picking the diameter that reads widest on
#: screen. Sixteen rather than a closed form for the projected ellipse's major
#: axis: the same answer to within a pixel, and it cannot be got subtly wrong.
DIAMETER_SAMPLES = 16

#: Line colour, and the alpha the overlay draws at.
DIMENSION_COLOR = (0.95, 0.75, 0.15)
DIMENSION_ALPHA = 0.95


# -- the pure half: no bpy --------------------------------------------------


def _length(vector):
    return math.hypot(float(vector[0]), float(vector[1]))


def _unit2d(vector):
    """``vector`` normalised, or None when it has no direction to give."""

    magnitude = _length(vector)
    if magnitude <= 1.0e-9:
        return None
    return (float(vector[0]) / magnitude, float(vector[1]) / magnitude)


def perpendicular(vector):
    """The screen-space perpendicular, rotated a quarter turn anticlockwise.

    One deterministic choice of the two, and it rotates *continuously* with
    the axis as you orbit, so the dimension line sweeps around the part rather
    than flipping between sides. The only place continuity breaks is where the
    axis itself vanishes, and that case has already become a leader.
    """

    unit = _unit2d(vector)
    if unit is None:
        return None
    return (-unit[1], unit[0])


def text_angle(axis):
    """The angle to draw the number at, in radians, never upside down.

    Text follows the dimension line, as it does on a drawing sheet -- a
    horizontal number sitting in the break of a vertical line reads as a
    mistake. Angles outside (-90 deg, +90 deg] are turned by half a turn, so
    the text flips exactly once as the line passes vertical and is legible
    either side of it.
    """

    unit = _unit2d(axis)
    if unit is None:
        return 0.0
    angle = math.atan2(unit[1], unit[0])
    if angle > math.pi / 2.0:
        angle -= math.pi
    elif angle <= -math.pi / 2.0:
        angle += math.pi
    return angle


def _offset(point, direction, distance):
    return (float(point[0]) + direction[0] * float(distance),
            float(point[1]) + direction[1] * float(distance))


def _segment(start, end):
    return (float(start[0]), float(start[1]), float(end[0]), float(end[1]))


def leader_geometry(at, text_width_px):
    """A stub and a number, for a dimension that is edge-on to the camera.

    Used when the two anchors land within ``MINIMUM_SPAN_PX`` of each other --
    you are looking down the measured axis. There is no dimension to draw and
    an honest overlay says the value anyway rather than dropping it.
    """

    tip = _offset(at, LEADER_DIRECTION, LEADER_PX)
    shelf = (tip[0] + float(text_width_px) + 2.0 * TEXT_PAD_PX, tip[1])
    return {
        "kind": "leader",
        "segments": [_segment(at, tip), _segment(tip, shelf)],
        "text_at": (tip[0] + TEXT_PAD_PX, tip[1] + TEXT_PAD_PX),
        "text_angle": 0.0,
    }


def dimension_geometry(start2d, end2d, text_width_px, offset_px=OFFSET_PX):
    """One dimension's whole drawing, in pixels.

    ``start2d``/``end2d`` are the projected anchors and ``text_width_px`` is
    what the font reports for the number -- passed in rather than measured
    here, because measuring it needs ``blf`` and this half has no Blender.

    Returns ``{kind, segments, text_at, text_angle}``, where ``segments`` is a
    flat list of ``(x1, y1, x2, y2)`` in region pixels::

        A ●╌╌╌┐                    ┌╌╌╌● B     the anchors, untouched
              │                    │
              ├──── 40.00 mm ──────┤           the dimension line, broken
              │                    │           around the number
    """

    axis = (float(end2d[0]) - float(start2d[0]),
            float(end2d[1]) - float(start2d[1]))
    span = _length(axis)
    if span < MINIMUM_SPAN_PX:
        return leader_geometry(start2d, text_width_px)

    along = _unit2d(axis)
    across = perpendicular(axis)
    segments = []

    # The two extension lines: from just clear of the anchor, out past the
    # dimension line by the overrun.
    for anchor in (start2d, end2d):
        segments.append(_segment(
            _offset(anchor, across, EXTENSION_GAP_PX),
            _offset(anchor, across, float(offset_px) + EXTENSION_OVERRUN_PX)))

    first = _offset(start2d, across, float(offset_px))
    last = _offset(end2d, across, float(offset_px))
    middle = ((first[0] + last[0]) / 2.0, (first[1] + last[1]) / 2.0)

    # The dimension line, broken around the number. When the number is wider
    # than the span there is no line left to draw and the two halves collapse
    # to nothing -- which is correct, and is why this clamps at zero rather
    # than drawing a line that runs backwards through its own label.
    half_gap = float(text_width_px) / 2.0 + TEXT_PAD_PX
    half_span = span / 2.0
    if half_gap < half_span:
        segments.append(_segment(first, _offset(middle, along, -half_gap)))
        segments.append(_segment(_offset(middle, along, half_gap), last))

    # A slash tick at each end, at 45 degrees to the dimension line.
    tick = _unit2d((along[0] + across[0], along[1] + across[1]))
    for end in (first, last):
        segments.append(_segment(_offset(end, tick, -TICK_PX),
                                 _offset(end, tick, TICK_PX)))

    return {
        "kind": "dimension",
        "segments": segments,
        "text_at": _offset(middle, across, TEXT_PAD_PX),
        "text_angle": text_angle(axis),
    }


def radius_geometry(center2d, rim2d, text_width_px):
    """A radius dimension: centre to rim, ticked at the rim, ``R…`` alongside.

    The drawing convention for fillets, arcs and bores dimensioned as radii:
    the line starts at the centre and ends on the material, so it never
    overshoots the way a diameter line would on a fillet. Falls back to a
    leader at the centre when the circle is edge-on.
    """

    axis = (float(rim2d[0]) - float(center2d[0]),
            float(rim2d[1]) - float(center2d[1]))
    if _length(axis) < MINIMUM_SPAN_PX:
        return leader_geometry(center2d, text_width_px)

    along = _unit2d(axis)
    across = perpendicular(axis)
    middle = ((float(center2d[0]) + float(rim2d[0])) / 2.0,
              (float(center2d[1]) + float(rim2d[1])) / 2.0)
    tick = _unit2d((along[0] + across[0], along[1] + across[1]))
    segments = [
        _segment(center2d, rim2d),
        _segment(_offset(rim2d, tick, -TICK_PX), _offset(rim2d, tick, TICK_PX)),
    ]
    return {
        "kind": "radius",
        "segments": segments,
        "text_at": _offset(middle, across, TEXT_PAD_PX),
        "text_angle": text_angle(axis),
    }


#: The angle arc's radius, and how many chords approximate it. Chords rather
#: than a shader arc so the arc rides the same LINES batch every other
#: dimension line does.
ANGLE_ARC_PX = 26.0
ANGLE_ARC_SEGMENTS = 24


def angle_geometry(vertex2d, first2d, second2d, text_width_px):
    """An angle dimension: two rays from the vertex, an arc between them,
    the degrees on the arc's bisector.

    ``first2d``/``second2d`` are the projected ray endpoints the engine
    published. The arc always spans the *measured* opening (the short way
    around, which is what the rays bound), and the text stays upright — an
    angle's number reads horizontally on a drawing sheet. Falls back to a
    leader at the vertex when either ray is edge-on.
    """

    rays = []
    for end in (first2d, second2d):
        ray = (float(end[0]) - float(vertex2d[0]),
               float(end[1]) - float(vertex2d[1]))
        unit = _unit2d(ray)
        if _length(ray) < MINIMUM_SPAN_PX or unit is None:
            return leader_geometry(vertex2d, text_width_px)
        rays.append((ray, unit))

    segments = [_segment(vertex2d, first2d), _segment(vertex2d, second2d)]

    start = math.atan2(rays[0][1][1], rays[0][1][0])
    sweep = math.atan2(rays[1][1][1], rays[1][1][0]) - start
    while sweep <= -math.pi:
        sweep += 2.0 * math.pi
    while sweep > math.pi:
        sweep -= 2.0 * math.pi

    arc_radius = min(ANGLE_ARC_PX,
                     0.8 * min(_length(rays[0][0]), _length(rays[1][0])))
    steps = max(2, int(round(ANGLE_ARC_SEGMENTS * abs(sweep) / math.pi)))
    previous = None
    for index in range(steps + 1):
        angle = start + sweep * index / float(steps)
        point = (float(vertex2d[0]) + arc_radius * math.cos(angle),
                 float(vertex2d[1]) + arc_radius * math.sin(angle))
        if previous is not None:
            segments.append(_segment(previous, point))
        previous = point

    bisector = start + sweep / 2.0
    text_at = (float(vertex2d[0])
               + (arc_radius + TEXT_PAD_PX) * math.cos(bisector)
               - float(text_width_px) / 2.0,
               float(vertex2d[1])
               + (arc_radius + TEXT_PAD_PX) * math.sin(bisector))
    return {
        "kind": "angle",
        "segments": segments,
        "text_at": text_at,
        "text_angle": 0.0,
    }


def circle_points(center_mm, normal, radius_mm, segments=DIAMETER_SAMPLES):
    """A ring of 3D points around a circle, for the caller to project.

    Diameter is the one measurement whose anchors are view-dependent: a circle
    has infinitely many diameters and the legible one is whichever faces you.
    So the engine publishes the circle rather than a pair of points, and the
    endpoints are chosen per frame by :func:`widest_diameter`.
    """

    axis = _unit3d(normal) or (0.0, 0.0, 1.0)
    first = _unit3d(_cross(axis, _least_parallel_axis(axis))) or (1.0, 0.0, 0.0)
    second = _cross(axis, first)
    ring = []
    for index in range(int(segments)):
        angle = 2.0 * math.pi * index / float(segments)
        cosine, sine = math.cos(angle), math.sin(angle)
        ring.append(tuple(
            float(center_mm[axis_index])
            + float(radius_mm) * (cosine * first[axis_index]
                                  + sine * second[axis_index])
            for axis_index in range(3)))
    return ring


def widest_diameter(points2d):
    """The projected ring's widest diameter, as ``(start2d, end2d)``.

    Only opposite pairs are candidates -- a diameter joins ``i`` to
    ``i + n/2`` -- so this is n/2 comparisons rather than n squared, and it
    cannot accidentally return a chord. Points the caller could not project
    (behind the camera) come in as None and disqualify their pair; when every
    pair is disqualified there is nothing to draw and this returns None.
    """

    count = len(points2d)
    if count < 2:
        return None
    best, widest = None, -1.0
    for index in range(count // 2):
        near, far = points2d[index], points2d[index + count // 2]
        if near is None or far is None:
            continue
        width = _length((float(far[0]) - float(near[0]),
                         float(far[1]) - float(near[1])))
        if width > widest:
            best, widest = (near, far), width
    return best


def _unit3d(vector):
    if vector is None or len(vector) < 3:
        return None
    magnitude = math.sqrt(sum(float(value) ** 2 for value in vector[:3]))
    if magnitude <= 1.0e-9:
        return None
    return tuple(float(value) / magnitude for value in vector[:3])


def _cross(left, right):
    return (left[1] * right[2] - left[2] * right[1],
            left[2] * right[0] - left[0] * right[2],
            left[0] * right[1] - left[1] * right[0])


def _least_parallel_axis(vector):
    """The world axis furthest from ``vector``, so the cross product is stable.

    Building a circle's in-plane basis from a fixed reference breaks when the
    circle's normal happens to *be* that reference -- a bore drilled down Z is
    the single most common thing anyone measures, so the naive choice fails on
    the first real model rather than on an exotic one.
    """

    smallest = min(range(3), key=lambda index: abs(float(vector[index])))
    return tuple(1.0 if index == smallest else 0.0 for index in range(3))


def transformed(point_mm, placement):
    """``point_mm`` through a 16-float row-major placement matrix.

    An output that an assembly places carries a solved placement, and the
    anchors the engine published are in the output's *own* frame. Skipping
    this puts a dimension on an assembled part in the wrong place -- the
    single most likely wrong answer in the whole feature, so it is one
    function with one test rather than three call sites doing it inline.
    """

    if not placement or len(placement) < 16:
        return (float(point_mm[0]), float(point_mm[1]), float(point_mm[2]))
    x, y, z = (float(value) for value in point_mm[:3])
    values = [float(value) for value in placement]
    return (
        values[0] * x + values[1] * y + values[2] * z + values[3],
        values[4] * x + values[5] * y + values[6] * z + values[7],
        values[8] * x + values[9] * y + values[10] * z + values[11],
    )


def records_from_display(display_map):
    """Every measurement in one response's ``display`` block, ready to draw.

    The engine puts a ``measurement`` key on the display entry of any output
    whose type is ``measurement`` (ADR-139), the same way ADR-049 put
    ``source_output`` on a component's. Entries without one are every other
    output and are skipped, so this reads the response the shell already has
    rather than asking a question.

    The subject's placement is resolved here, once, rather than at draw time:
    it changes when the model rebuilds, not when the camera moves.
    """

    records = []
    for name in sorted(display_map or {}):
        entry = (display_map or {}).get(name) or {}
        measurement = entry.get("measurement")
        if not isinstance(measurement, dict):
            continue
        subject = str(measurement.get("subject") or "")
        placement = ((display_map.get(subject) or {}).get("placement")
                     if subject else None)
        record = {
            "output": str(name),
            "kind": str(measurement.get("kind") or ""),
            "label": str(measurement.get("label") or ""),
            "text": str(measurement.get("text") or ""),
            "value_mm": float(measurement.get("value_mm") or 0.0),
            "subject": subject,
        }
        anchors = measurement.get("anchors_mm") or []
        if len(anchors) >= 2:
            record["anchors_mm"] = [transformed(anchors[0], placement),
                                    transformed(anchors[1], placement)]
        vertex = measurement.get("vertex_mm")
        if vertex is not None:
            record["vertex_mm"] = transformed(vertex, placement)
        center = measurement.get("center_mm")
        if center is not None:
            record["ring_mm"] = [
                transformed(point, placement)
                for point in circle_points(center,
                                           measurement.get("normal"),
                                           measurement.get("radius_mm") or 0.0)]
        records.append(record)
    return records


# -- the bpy half -----------------------------------------------------------
#
# ``bpy`` is imported inside each function, never at module scope, exactly as
# ``cadex_collision`` and ``cadex_cage`` do it. That is what keeps the pure
# half above genuinely runnable without Blender.

#: On the scene while the overlay is on: ``{count, revision}``. The header
#: button polls on its presence, exactly as ``cadex_collision.SCENE_FLAG``
#: does, so "is it showing" is one key rather than a second piece of state
#: that can disagree with the first.
SCENE_FLAG = "cadex_dimensions"

#: The records to draw, and the revision they came off. Module level rather
#: than on the scene: the draw handler runs on every redraw of every viewport,
#: and re-parsing a JSON scene property at that rate is the one thing that
#: would make this overlay cost something. Refreshed by :func:`apply` on each
#: accepted revision, which is the only moment they can change.
_records = []
_revision = ""

#: Guarded exactly as ``cadex_live``'s pair is: a handle left behind outlives
#: the module it points into and raises on the next add-on reload.
_draw_handle = None
_shader = None


def _line_shader():
    """``(shader, is_polyline)``, fetched on first draw and never at import.

    ``gpu.shader.from_builtin`` raises "requires the gpu module to be
    initialized" under ``--background``, so a module-scope shader would break
    every headless gate run — which is where this overlay's own tests live.
    """

    global _shader

    if _shader is None:
        import gpu

        for name in ('POLYLINE_UNIFORM_COLOR', 'UNIFORM_COLOR'):
            try:
                _shader = (gpu.shader.from_builtin(name),
                           name.startswith('POLYLINE'))
                break
            except Exception:
                continue
    return _shader or (None, False)


def records():
    """What the overlay would draw right now. The gate suite's entry point."""

    return [dict(record) for record in _records]


def enabled():
    import bpy

    scene = getattr(bpy.context, "scene", None)
    return scene is not None and SCENE_FLAG in scene


def _projected(region, rv3d, point):
    from bpy_extras import view3d_utils
    from mathutils import Vector

    at = view3d_utils.location_3d_to_region_2d(region, rv3d, Vector(point))
    return None if at is None else (float(at[0]), float(at[1]))


def _text_width(text):
    import blf

    try:
        blf.size(0, TEXT_SIZE_PX)
    except TypeError:
        blf.size(0, TEXT_SIZE_PX, 72)  # the three-argument form, on older builds
    return float(blf.dimensions(0, str(text))[0])


def drawing_for(record, region, rv3d):
    """One record's screen-space drawing, or None when it cannot be drawn.

    Split out from the draw handler so the gate can drive it with a made-up
    region and view matrix and assert what comes back — including the
    down-the-axis case, which is the one a person can only check by orbiting.
    """

    text = str(record.get("text") or "")
    kind = str(record.get("kind") or "")
    if kind in ("diameter", "radius"):
        ring = record.get("ring_mm") or []
        if not ring:
            return None
        ends = widest_diameter([_projected(region, rv3d, point) for point in ring])
        if ends is None:
            return None
        start2d, end2d = ends
        if kind == "radius":
            # The projected widest diameter's midpoint is the projected
            # centre, so the radius line runs centre-to-rim with no second
            # projection to disagree with the first.
            center2d = ((start2d[0] + end2d[0]) / 2.0,
                        (start2d[1] + end2d[1]) / 2.0)
            drawing = radius_geometry(center2d, end2d, _text_width(text))
            drawing["text"] = text
            return drawing
    elif kind == "angle":
        vertex = record.get("vertex_mm")
        anchors = record.get("anchors_mm") or []
        if vertex is None or len(anchors) < 2:
            return None
        vertex2d = _projected(region, rv3d, vertex)
        first2d = _projected(region, rv3d, anchors[0])
        second2d = _projected(region, rv3d, anchors[1])
        if vertex2d is None or first2d is None or second2d is None:
            return None
        drawing = angle_geometry(vertex2d, first2d, second2d,
                                 _text_width(text))
        drawing["text"] = text
        return drawing
    else:
        anchors = record.get("anchors_mm") or []
        if len(anchors) < 2:
            return None
        start2d = _projected(region, rv3d, anchors[0])
        end2d = _projected(region, rv3d, anchors[1])
        if start2d is None or end2d is None:
            return None  # behind the camera
    drawing = dimension_geometry(start2d, end2d, _text_width(text))
    drawing["text"] = text
    return drawing


def _draw():
    import bpy

    if not _records or not enabled():
        return
    region = getattr(bpy.context, "region", None)
    rv3d = getattr(bpy.context, "region_data", None)
    if region is None or rv3d is None:
        return

    import blf
    import gpu
    from gpu_extras.batch import batch_for_shader

    drawings = []
    for record in _records:
        try:
            drawing = drawing_for(record, region, rv3d)
        except Exception:
            drawing = None
        if drawing is not None:
            drawings.append(drawing)
    if not drawings:
        return

    points = []
    for drawing in drawings:
        for x1, y1, x2, y2 in drawing["segments"]:
            points.extend([(x1, y1), (x2, y2)])

    shader, polyline = _line_shader()
    if shader is not None and points:
        batch = batch_for_shader(shader, 'LINES', {"pos": points})
        shader.bind()
        shader.uniform_float("color", DIMENSION_COLOR + (DIMENSION_ALPHA,))
        if polyline:
            viewport = gpu.state.viewport_get()
            shader.uniform_float("viewportSize",
                                 (float(viewport[2]), float(viewport[3])))
            shader.uniform_float("lineWidth", 1.5)
        gpu.state.blend_set('ALPHA')
        # A dimension draws over the part rather than behind it, the same
        # choice `cadex_live`'s force arrows make. A drawing sheet does not
        # occlude its dimensions either.
        gpu.state.depth_test_set('NONE')
        try:
            batch.draw(shader)
        finally:
            gpu.state.blend_set('NONE')
            gpu.state.depth_test_set('LESS_EQUAL')

    for drawing in drawings:
        _text_width(drawing["text"])  # re-applies the size this font id draws at
        blf.color(0, DIMENSION_COLOR[0], DIMENSION_COLOR[1],
                  DIMENSION_COLOR[2], DIMENSION_ALPHA)
        at = drawing["text_at"]
        angle = float(drawing.get("text_angle") or 0.0)
        rotated = abs(angle) > 1.0e-6
        if rotated:
            blf.enable(0, blf.ROTATION)
            blf.rotation(0, angle)
        blf.position(0, at[0], at[1], 0.0)
        blf.draw(0, drawing["text"])
        if rotated:
            blf.disable(0, blf.ROTATION)


def _add_draw_handler():
    import bpy

    global _draw_handle

    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw, (), 'WINDOW', 'POST_PIXEL')


def _remove_draw_handler():
    """Guarded, and safe to call twice: it runs on every hide and on unload."""

    import bpy

    global _draw_handle

    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        except Exception:
            pass
        _draw_handle = None


def _redraw():
    import bpy

    for window in getattr(bpy.context.window_manager, "windows", ()) or ():
        for area in getattr(window.screen, "areas", ()) or ():
            if getattr(area, "type", "") == 'VIEW_3D':
                area.tag_redraw()


def apply(payload):
    """Take the measurements off one accepted response. Returns a report.

    Called from ``cadex_backend.hydrate`` on the same terms as the collision
    overlay: wrapped, so a malformed measurement record costs the dimensions
    and never the geometry.

    It refreshes the records whether or not the overlay is showing. Turning it
    on then costs a redraw rather than a round trip, and — more to the point —
    a stale dimension is worse than an absent one, so the records must not be
    allowed to outlive the revision they were measured on.
    """

    import bpy

    global _records, _revision

    _records = records_from_display(payload.get("display") or {})
    _revision = str(payload.get("revision") or "")
    scene = getattr(bpy.context, "scene", None)
    if scene is not None and SCENE_FLAG in scene:
        scene[SCENE_FLAG] = {"count": len(_records), "revision": _revision}
    _redraw()
    return {"shown": enabled(), "count": len(_records), "revision": _revision}


def clear():
    """Take the overlay down and forget what it was drawing."""

    import bpy

    global _records, _revision

    _records, _revision = [], ""
    scene = getattr(bpy.context, "scene", None)
    if scene is not None and SCENE_FLAG in scene:
        del scene[SCENE_FLAG]
    _remove_draw_handler()
    _redraw()
    return {"shown": False, "count": 0}


def toggle():
    """Show or hide the dimensions. Returns a report with a message."""

    import bpy

    scene = getattr(bpy.context, "scene", None)
    if scene is None:
        return {"shown": False, "count": 0, "message": "No scene."}
    if SCENE_FLAG in scene:
        report = clear()
        report["message"] = "Dimensions hidden."
        return report
    scene[SCENE_FLAG] = {"count": len(_records), "revision": _revision}
    _add_draw_handler()
    _redraw()
    message = (
        "Showing {:d} dimension(s).".format(len(_records)) if _records else
        "No dimensions declared. Add one with part.measurement(...) and "
        "rebuild.")
    return {"shown": True, "count": len(_records), "message": message}


def unregister():
    """Add-on teardown. The handler must not outlive the module it calls."""

    _remove_draw_handler()
