# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Compact JSON-friendly summary of the current scene for the agent."""


def _vec(value, digits=4):
    return [round(component, digits) for component in value]


def summarize(max_objects=200):
    import bpy

    scene = bpy.context.scene
    objects = []
    for obj in list(scene.objects)[:max_objects]:
        entry = {
            "name": obj.name,
            "type": obj.type,
            "location": _vec(obj.location),
            "rotation_euler": _vec(obj.rotation_euler),
            "scale": _vec(obj.scale),
            "dimensions": _vec(obj.dimensions),
        }
        if obj.parent is not None:
            entry["parent"] = obj.parent.name
        if obj.hide_viewport or not obj.visible_get():
            entry["hidden"] = True
        if obj.modifiers:
            entry["modifiers"] = [
                {"name": mod.name, "type": mod.type} for mod in obj.modifiers
            ]
        materials = [slot.material.name for slot in obj.material_slots
                     if slot.material is not None]
        if materials:
            entry["materials"] = materials
        objects.append(entry)

    summary = {
        "scene": scene.name,
        "object_count": len(scene.objects),
        "objects": objects,
    }
    if len(scene.objects) > max_objects:
        summary["note"] = "Only the first {:d} objects are listed".format(max_objects)
    return summary
