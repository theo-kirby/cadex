# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Viewport picking → BREP pins (cadex Phase 6).

Hydrated cadex objects carry a ``cadex_face`` INT face attribute: the
1-based BREP face index for every tessellation triangle. Picking is
therefore a pure lookup — ray-cast to a polygon, read the attribute, ask
the engine to resolve ``{element_type: "face", index}`` against the
accepted revision's staged BREP (``resolve_pin``). The resolved pin
(`@face-N` of an output, with the engine's geometric details) is queued
and attached to the user's next chat message, mirroring how image
attachments are surfaced to the model.
"""

import json

from . import cadex_hydrate

#: Pins resolved since the last chat turn; drained by consume_pin_notes().
_pending_pins = []

#: Sentences queued beside those pins, saying what they are for. Drained by
#: the same call, so a gesture and its instruction can never separate.
_pending_requests = []


def face_index_of_polygon(obj, polygon_index):
    """The 1-based BREP face index behind one tessellation triangle."""
    if obj is None or obj.type != 'MESH':
        raise ValueError("Pick target is not a mesh object.")
    if str(obj.get(cadex_hydrate.KIND_PROP, "")) != "brep":
        raise ValueError(
            "Object {!s} is not a cadex BREP output; pins resolve on BREP "
            "outputs only.".format(obj.name))
    attribute = obj.data.attributes.get(cadex_hydrate.FACE_ATTRIBUTE)
    if attribute is None:
        raise ValueError(
            "Object {!s} carries no {:s} ID map.".format(
                obj.name, cadex_hydrate.FACE_ATTRIBUTE))
    if not 0 <= polygon_index < len(attribute.data):
        raise ValueError("Polygon index {:d} is out of range.".format(
            polygon_index))
    face_index = int(attribute.data[polygon_index].value)
    if face_index < 1:
        raise ValueError(
            "Polygon {:d} has no BREP face id.".format(polygon_index))
    return face_index


def resolve_polygon(scene, obj, polygon_index):
    """Polygon pick → engine pin. Returns (pin_dict | None, report).

    ``pin_dict``: {output, face_index, subelement, detail, revision}.
    """
    from . import cadex_backend
    output = str(obj.get(cadex_hydrate.OUTPUT_PROP, "") or "")
    if not output:
        return None, "Object {!s} is not a cadex output.".format(obj.name)
    try:
        face_index = face_index_of_polygon(obj, polygon_index)
    except ValueError as exc:
        return None, str(exc)
    payload = cadex_backend.resolve_pin(
        scene, output, {"element_type": "face", "index": face_index})
    if payload.get("ok") is not True:
        return None, "resolve_pin failed: {:s}".format(
            str(payload.get("error") or payload.get("failure_code") or "?"))
    subelements = list(payload.get("subelements") or [])
    details = list(payload.get("details") or [])
    pin = {
        "kind": "face",
        "output": output,
        "face_index": face_index,
        "subelement": str(subelements[0]) if subelements else
                      "Face{:d}".format(face_index),
        "detail": dict(details[0]) if details else {},
        "revision": str(payload.get("revision") or ""),
    }
    return pin, format_pin(pin)


def point_pin(obj, location, normal):
    """A picked point on any cadex output. Returns (pin_dict | None, report).

    The counterpart to :func:`resolve_polygon`, and deliberately far less
    clever: it asks the engine nothing. A face pin *names* something the
    engine can re-find; a point pin is just a place — which is all a cable
    port is (a point, and the way a wire leaves it), and all an imported
    mesh can offer, since an STL has no faces to name. That is why
    ``resolve_polygon`` refuses a mesh output and this does not.

    The hit arrives in world space while the script authors in the output's
    own space, so both are pushed back through the object's placement. They
    do *not* go back the same way: a point is ``M^-1 p``, but a normal is
    ``M^T n`` — the inverse of the inverse-transpose that carried it out to
    world space. Using the inverse for both is right for a translation and
    silently backwards under rotation, which is why the test placement
    rotates rather than only moving.

    ``pin_dict``: {kind, output, point, normal, detail, revision}.
    """

    output = str(obj.get(cadex_hydrate.OUTPUT_PROP, "") or "")
    if not output:
        return None, "Object {!s} is not a cadex output.".format(obj.name)
    local = obj.matrix_world.inverted_safe() @ location
    direction = obj.matrix_world.to_3x3().transposed() @ normal
    if direction.length <= 1.0e-12:
        return None, "The surface under the cursor has no usable normal."
    direction = direction.normalized()
    pin = {
        "kind": "point",
        "output": output,
        "point": [float(local.x), float(local.y), float(local.z)],
        "normal": [float(direction.x), float(direction.y),
                   float(direction.z)],
        "detail": {
            "point_mm": [float(local.x), float(local.y), float(local.z)],
            "normal": [float(direction.x), float(direction.y),
                       float(direction.z)],
            "object": obj.name,
            "artifact_kind": str(obj.get(cadex_hydrate.KIND_PROP, "") or ""),
        },
        "revision": str(obj.get(cadex_hydrate.REVISION_PROP, "") or ""),
    }
    return pin, format_pin(pin)


def format_pin(pin):
    if str(pin.get("kind") or "face") == "point":
        point = pin.get("point") or [0.0, 0.0, 0.0]
        normal = pin.get("normal") or [0.0, 0.0, 0.0]
        return ("a point on {:s}, [{:.2f}, {:.2f}, {:.2f}] mm, surface normal "
                "[{:.3f}, {:.3f}, {:.3f}]".format(
                    pin["output"], point[0], point[1], point[2],
                    normal[0], normal[1], normal[2]))
    detail = pin.get("detail") or {}
    parts = ["@face-{:d} of {:s}".format(pin["face_index"], pin["output"])]
    geometry = str(detail.get("geometry_type") or "")
    if geometry:
        parts.append(geometry)
    center = detail.get("center")
    if isinstance(center, (list, tuple)) and len(center) == 3:
        parts.append("center [{:.2f}, {:.2f}, {:.2f}] mm".format(*center))
    area = detail.get("area")
    if isinstance(area, (int, float)):
        parts.append("area {:.2f} mm^2".format(area))
    return ", ".join(parts)


def queue_pin(pin):
    _pending_pins.append(pin)


def queue_request(text):
    """Queue one sentence saying what to do with the pins (ADR-139).

    A pin says *which* subshape; it never says why it was picked. Measure is
    the first gesture that needs the second half, and it needs nothing more
    than the sentence — so this is a list of strings beside the pins rather
    than a second mechanism.
    """

    cleaned = str(text or "").strip()
    if cleaned:
        _pending_requests.append(cleaned)


def pending_pin_count():
    return len(_pending_pins)


def consume_pin_notes():
    """Prompt suffix describing pins picked since the last turn (drains)."""
    if not _pending_pins and not _pending_requests:
        return ""
    lines = ["[The user pinned {:s} — engine detail: {:s}]".format(
        format_pin(pin), json.dumps(pin.get("detail") or {}, default=str))
        for pin in _pending_pins]
    # After the pins, so the instruction reads against a list the model has
    # already been given rather than one it is about to be.
    lines.extend("[The user asked: {:s}]".format(text)
                 for text in _pending_requests)
    _pending_pins.clear()
    _pending_requests.clear()
    return "\n\n" + "\n".join(lines)


def viewport_region_at(areas, x, y):
    """The 3D viewport's WINDOW region under one window-space pixel, or None.

    The pick is started from a button in the chat header, so the area the
    operator is *invoked* from is never the viewport — it is the header's
    own area. The region has to be found from where the mouse ends up, not
    from where the click began, or the gesture cancels the instant it starts.
    """

    for area in areas:
        if getattr(area, "type", "") != 'VIEW_3D':
            continue
        for region in getattr(area, "regions", ()):
            if getattr(region, "type", "") != 'WINDOW':
                continue
            if (region.x <= x < region.x + region.width
                    and region.y <= y < region.y + region.height):
                return region
    return None


def _make_operators():
    import bpy
    from bpy_extras import view3d_utils

    class _EyedropperPick:
        """One click in the viewport, ray-cast, resolve, queue for the agent.

        Both pins share the gesture and differ only in what they make of the
        hit, so ``_resolve`` is the whole of the difference.
        """

        def invoke(self, context, event):
            if context.window is None:
                return {'CANCELLED'}
            context.window.cursor_modal_set('EYEDROPPER')
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        def modal(self, context, event):
            if event.type in {'RIGHTMOUSE', 'ESC'}:
                context.window.cursor_modal_restore()
                return {'CANCELLED'}
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                region = viewport_region_at(context.window.screen.areas,
                                            event.mouse_x, event.mouse_y)
                if region is None:
                    # Not over the viewport, so nothing to pick -- keep
                    # waiting rather than cancel. This is also what absorbs
                    # the release of the very click that started the modal,
                    # which lands on the button, not on the model.
                    return {'RUNNING_MODAL'}
                context.window.cursor_modal_restore()
                return self._pick(context, event, region)
            return {'RUNNING_MODAL'}

        def _pick(self, context, event, region):
            from . import agent as agent_module
            rv3d = getattr(region, "data", None)
            if rv3d is None:
                self.report({'WARNING'}, "No 3D region under the cursor")
                return {'CANCELLED'}
            coord = (event.mouse_x - region.x, event.mouse_y - region.y)
            origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
            direction = view3d_utils.region_2d_to_vector_3d(region, rv3d,
                                                            coord)
            depsgraph = context.evaluated_depsgraph_get()
            hit, location, normal, index, obj, _matrix = (
                context.scene.ray_cast(depsgraph, origin, direction))
            if not hit or obj is None:
                self.report({'INFO'}, "Nothing under the cursor")
                return {'CANCELLED'}
            pin, report = self._resolve(context, obj, index, location, normal)
            history = agent_module.get_agent().history
            if pin is None:
                self.report({'WARNING'}, report)
                history.add("status", "Pin failed: " + report)
                return {'CANCELLED'}
            queue_pin(pin)
            history.add("status", "Pinned " + report)
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    # CADEX_CHAT too: the pinned count is drawn in its
                    # header, and a header does not repaint on its own.
                    if area.type in {'VIEW_3D', 'PROPERTIES', 'CADEX_CHAT'}:
                        area.tag_redraw()
            return {'FINISHED'}

    class MESH_AGENT_OT_pick_pin(_EyedropperPick, bpy.types.Operator):
        bl_idname = "mesh_agent.pick_pin"
        bl_label = "Pin Face"
        bl_description = ("Click a face of the model to pin it for the "
                          "assistant")

        def _resolve(self, context, obj, index, _location, _normal):
            return resolve_polygon(context.scene, obj, index)

    class MESH_AGENT_OT_pick_point(_EyedropperPick, bpy.types.Operator):
        bl_idname = "mesh_agent.pick_point"
        bl_label = "Pin Point"
        bl_description = ("Click anywhere on the model to pin that point and "
                          "its surface direction for the assistant — works "
                          "on imported components, which have no faces to pin")

        def _resolve(self, _context, obj, _index, location, normal):
            return point_pin(obj, location, normal)

    return (MESH_AGENT_OT_pick_pin, MESH_AGENT_OT_pick_point)


_operator_cls = []


def register():
    import bpy
    _operator_cls[:] = _make_operators()
    for cls in _operator_cls:
        bpy.utils.register_class(cls)


def unregister():
    import bpy
    for cls in reversed(_operator_cls):
        bpy.utils.unregister_class(cls)
    _operator_cls.clear()
    _pending_pins.clear()
