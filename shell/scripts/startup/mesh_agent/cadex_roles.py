# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The viewport paints each part in its appearance role (cadex ADR-449).

A Cadex robot is shell over skeleton (docs/DESIGN-LANGUAGE.md): bone shell,
graphite mechanism, one signal-orange accent, each role recoloured by the
assembly's palette. The engine's studio draws ``look``, the review hero and
the concept sheet in those colours; before this the viewport drew every part
in Blender's default grey, so the design the user saw was not the design the
agent judged.

Which part gets which colour is the engine's rule, not this module's: the
payload's studio process answers a ``blocks`` request that carries the
accepted ``display`` with an ``appearance`` table -- declared role, else
purchased is mechanism and printed is shell -- which is the table a render's
``summary.json`` holds (``CadexStudio.role_colours``). This module only turns
that table into three materials:

- one material per role, ``Cadex shell`` / ``Cadex mechanism`` /
  ``Cadex accent``, tagged ``cadex_role``, its colour the table's;
- linked to the **object**, never the mesh: forty screws share one mesh
  datablock (``cadex_hydrate._hydrate_components``) and can differ in role;
- never over a material the user put there: a slot holding a material with
  no ``cadex_role`` is left alone.

It runs once per accepted, settled revision, on a worker thread, and paints
back on the main thread; a drag's draft rebuilds keep the colours because
every mesh ``cadex_hydrate`` builds carries the one slot the object-linked
material lives in. With no inventory to tell printed from purchased and no
declared role, the table is empty and nothing is painted.
"""

import threading
import traceback

ROLE_PROP = "cadex_role"
MATERIAL_PREFIX = "Cadex "

#: Seconds between checks for a finished measurement.
POLL_SECONDS = 0.2


def _linear(hex_colour):
    """``#RRGGBB`` (sRGB) as the scene-linear RGB a material stores."""
    channels = []
    for index in (1, 3, 5):
        value = int(hex_colour[index:index + 2], 16) / 255.0
        channels.append(value / 12.92 if value <= 0.04045
                        else ((value + 0.055) / 1.055) ** 2.4)
    return tuple(channels)


def _material(role, hex_colour):
    import bpy
    name = MATERIAL_PREFIX + role
    material = bpy.data.materials.get(name)
    if material is None or material.get(ROLE_PROP) != role:
        material = bpy.data.materials.new(name)
        material[ROLE_PROP] = role
    rgba = (*_linear(hex_colour), 1.0)
    if tuple(round(c, 5) for c in material.diffuse_color) != tuple(round(c, 5) for c in rgba):
        material.diffuse_color = rgba
        tree = material.node_tree
        node = tree.nodes.get("Principled BSDF") if tree is not None else None
        if node is not None:
            node.inputs["Base Color"].default_value = rgba
    return material


def _ours(material):
    return material is not None and material.get(ROLE_PROP) is not None


def paint(colours):
    """Main thread: give every Model object its role's material.

    ``colours`` is the studio's ``appearance`` table. Returns
    ``{"painted": n, "cleared": n, "kept": [user-material objects]}``.
    """
    from . import cadex_hydrate
    rows = dict((colours or {}).get("objects") or {})
    collection = cadex_hydrate._model_collection()
    materials = {}
    painted, cleared, kept = 0, 0, []
    for obj in cadex_hydrate._cadex_objects(collection):
        if obj.name.endswith(cadex_hydrate.EDGE_SUFFIX) or obj.data is None:
            continue
        row = rows.get(str(obj.get(cadex_hydrate.OUTPUT_PROP) or ""))
        slot = obj.material_slots[0] if obj.material_slots else None
        if row is None:
            if slot is not None and slot.link == 'OBJECT' and _ours(slot.material):
                slot.material = None
                cleared += 1
            continue
        if slot is None:
            obj.data.materials.append(None)
            slot = obj.material_slots[0]
        if slot.material is not None and not _ours(slot.material):
            kept.append(obj.name)
            continue
        role = str(row.get("role") or "")
        key = (role, str(row.get("color") or ""))
        if key not in materials:
            materials[key] = _material(*key)
        if slot.link != 'OBJECT':
            slot.link = 'OBJECT'
        if slot.material is not materials[key]:
            slot.material = materials[key]
        painted += 1
    return {"painted": painted, "cleared": cleared, "kept": kept}


def measure(root, client, module_dir, revision):
    """Worker thread: the appearance table for ``revision``, or ``None``."""
    from . import cadex_backend
    result = cadex_backend.measure_blocks(root, client, module_dir, revision)
    if not result.get("ok"):
        print("cadex roles: no appearance for {:s}: {:s}".format(
            revision[:12], str(result.get("error") or "")))
        return None
    return result.get("appearance")


def refresh(scene):
    """Measure and paint now, on the calling (main) thread. For tests."""
    from . import cadex_backend
    root, client, module_dir = cadex_backend.measurement_context(scene)
    revision = str(cadex_backend.last_accepted(root).get("revision") or "")
    colours = measure(root, client, module_dir, revision)
    return paint(colours) if colours is not None else None


def _on_hydrate(payload, root, animate):
    """After a settled, accepted build: measure off the main thread, then paint.

    Mid-drag (``animate=False``) nothing runs: the objects keep the roles
    they had, and the settled refine repaints. In background mode nothing
    runs either -- a test drives :func:`refresh` -- because a studio process
    and two ``inspect`` reads per accept would sit in every gate timing.
    """
    import bpy
    from . import cadex_backend
    if not animate or bpy.app.background or not root:
        return None
    revision = str(payload.get("revision") or "")
    scene_name = bpy.context.scene.name
    _root, client, module_dir = cadex_backend.measurement_context(bpy.context.scene)
    box = {}

    def worker():
        try:
            box["colours"] = measure(root, client, module_dir, revision)
        except Exception:
            traceback.print_exc()

    thread = threading.Thread(target=worker, name="cadex-roles", daemon=True)
    thread.start()

    def poll():
        if thread.is_alive():
            return POLL_SECONDS
        scene = bpy.data.scenes.get(scene_name) or bpy.context.scene
        # A newer build, or another project, owns the viewport now.
        if (box.get("colours") is None or cadex_backend.project_root(scene) != root
                or cadex_backend.last_accepted(root).get("revision") != revision):
            return None
        try:
            paint(box["colours"])
        except Exception:
            traceback.print_exc()
        return None

    bpy.app.timers.register(poll, first_interval=POLL_SECONDS)
    return {"scheduled": revision}
