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
        "output": output,
        "face_index": face_index,
        "subelement": str(subelements[0]) if subelements else
                      "Face{:d}".format(face_index),
        "detail": dict(details[0]) if details else {},
        "revision": str(payload.get("revision") or ""),
    }
    return pin, format_pin(pin)


def format_pin(pin):
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


def pending_pin_count():
    return len(_pending_pins)


def consume_pin_notes():
    """Prompt suffix describing pins picked since the last turn (drains)."""
    if not _pending_pins:
        return ""
    lines = ["[The user pinned {:s} — engine detail: {:s}]".format(
        format_pin(pin), json.dumps(pin.get("detail") or {}, default=str))
        for pin in _pending_pins]
    _pending_pins.clear()
    return "\n\n" + "\n".join(lines)


def _make_operator():
    import bpy
    from bpy_extras import view3d_utils

    class MESH_AGENT_OT_pick_pin(bpy.types.Operator):
        bl_idname = "mesh_agent.pick_pin"
        bl_label = "Pin Face"
        bl_description = ("Click a face of the model to pin it for the "
                          "assistant")

        def invoke(self, context, event):
            if context.area is None or context.area.type != 'VIEW_3D':
                self.report({'WARNING'}, "Use the 3D viewport to pick")
                return {'CANCELLED'}
            context.window.cursor_modal_set('EYEDROPPER')
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        def modal(self, context, event):
            if event.type in {'RIGHTMOUSE', 'ESC'}:
                context.window.cursor_modal_restore()
                return {'CANCELLED'}
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                context.window.cursor_modal_restore()
                return self._pick(context, event)
            return {'RUNNING_MODAL'}

        def _pick(self, context, event):
            from . import agent as agent_module
            region = context.region
            rv3d = context.region_data
            if region is None or rv3d is None:
                self.report({'WARNING'}, "No 3D region under the cursor")
                return {'CANCELLED'}
            coord = (event.mouse_region_x, event.mouse_region_y)
            origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
            direction = view3d_utils.region_2d_to_vector_3d(region, rv3d,
                                                            coord)
            depsgraph = context.evaluated_depsgraph_get()
            hit, _location, _normal, index, obj, _matrix = (
                context.scene.ray_cast(depsgraph, origin, direction))
            if not hit or obj is None:
                self.report({'INFO'}, "Nothing under the cursor")
                return {'CANCELLED'}
            pin, report = resolve_polygon(context.scene, obj, index)
            history = agent_module.get_agent().history
            if pin is None:
                self.report({'WARNING'}, report)
                history.add("status", "Pin failed: " + report)
                return {'CANCELLED'}
            queue_pin(pin)
            history.add("status", "Pinned " + report)
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type in {'VIEW_3D', 'PROPERTIES'}:
                        area.tag_redraw()
            return {'FINISHED'}

    return MESH_AGENT_OT_pick_pin


_operator_cls = [None]


def register():
    import bpy
    _operator_cls[0] = _make_operator()
    bpy.utils.register_class(_operator_cls[0])


def unregister():
    import bpy
    if _operator_cls[0] is not None:
        bpy.utils.unregister_class(_operator_cls[0])
        _operator_cls[0] = None
    _pending_pins.clear()
