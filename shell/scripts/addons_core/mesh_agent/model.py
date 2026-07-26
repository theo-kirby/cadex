# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Parameter sliders and the script mirror.

What is left of this module after ADR-030 is the Blender-side plumbing
around a script that runs *somewhere else*: the text block in
``bpy.data.texts["model.py"]`` that mirrors the engine's script, and the
dynamically registered PropertyGroup at ``scene.mesh_params`` that renders
the engine's ``param_specs`` as native sliders.

Values live in the scene's ID properties (saved with the .blend) and are
keyed by parameter id, so they survive script edits that keep ids stable.
The specs are saved as JSON in a scene property so sliders can be restored
on file load without asking the engine.

Dragging a slider triggers a debounced rebuild, which is a
revision-guarded ``set_params`` to the engine — not an ``exec()`` here.
This module used to hold a second, local implementation that ran the script
against ``bpy`` inside Blender, together with the ``mesh_cad`` library it
called and the geometry validator that checked its output. All of it is
gone (ADR-030); ``rebuild()`` has one path.
"""

import json
import traceback

from . import model_api

SCRIPT_NAME = "model.py"
COLLECTION_NAME = "Model"
SPECS_PROP = "mesh_model_specs"
PARAMS_ATTR = "mesh_params"

# Stamped on the text datablock (an ID property, so it saves with the .blend):
# the digest of the source the engine last mirrored into the buffer. The
# difference between it and the buffer's current digest is a hand edit that
# the engine has not seen.
DIGEST_PROP = "cadex_mirrored_digest"

# Currently registered dynamic PropertyGroup and the specs JSON it was built
# from (used to skip re-registration when the declarations are unchanged —
# important because a slider being dragged must not have its class swapped).
_group_cls = [None]
_group_specs_json = [None]

_specs_cache = {}


# -- script text -----------------------------------------------------------

def get_script():
    import bpy
    text = bpy.data.texts.get(SCRIPT_NAME)
    return text.as_string() if text is not None else ""


def ensure_script_text():
    """The mirror datablock, created empty if this file has none yet.

    The script view is a toggle now (ADR-039), and a button that greys itself
    out on a fresh file is worse than one that opens an empty editor.
    """
    import bpy
    text = bpy.data.texts.get(SCRIPT_NAME)
    if text is None:
        text = bpy.data.texts.new(SCRIPT_NAME)
        text.use_fake_user = True
    return text


def source_digest(source):
    """The digest the dirty marking compares. Not the engine's revision."""
    import hashlib
    return hashlib.sha256((source or "").encode("utf-8")).hexdigest()


def mirrored_digest(text=None):
    """Digest stamped on the buffer when the engine last wrote it, or ""."""
    if text is None:
        import bpy
        text = bpy.data.texts.get(SCRIPT_NAME)
    if text is None:
        return ""
    return str(text.get(DIGEST_PROP, "") or "")


def script_is_dirty():
    """True when the buffer has been hand-edited since the engine wrote it.

    An unstamped buffer counts as clean: a file saved before ADR-039 has no
    stamp, and calling every one of those dirty would put a false alert in
    front of users who have changed nothing.
    """
    stamped = mirrored_digest()
    return bool(stamped) and source_digest(get_script()) != stamped


def set_script(source, stamp=True):
    """Mirror the engine's source into the buffer. True when it changed.

    Two things it must not do. It must not rewrite the buffer when the source
    is already there -- `clear()` + `write()` sends the cursor to the end of
    the file (verified), and the mirror is refreshed on every accepted request,
    so a slider drag would fight anyone reading the script. And when it does
    rewrite, it puts the cursor back.

    The digest it stamps is of the buffer as the engine last wrote it, which is
    what `script_is_dirty` needs: `as_string()` round-trips `write()` exactly,
    so a hand edit is the only thing that can move it.

    ``stamp=False`` is for a source the engine *refused*: keep it in the buffer
    so the user can fix it, but leave the stamp on the last accepted source, so
    the buffer goes on reading as modified. Stamping a rejected source would
    label a script the model does not have as "matches the model".
    """
    text = ensure_script_text()
    digest = source_digest(source)
    if text.as_string() == source:
        # Still stamp: this may be the first mirror into a buffer that already
        # happened to hold the engine's source (a reopened file), and without
        # the stamp it would read as neither clean nor dirty.
        if stamp:
            text[DIGEST_PROP] = digest
        return False
    line, character = text.current_line_index, text.current_character
    text.clear()
    text.write(source)
    try:
        text.cursor_set(line, character=character, select=False)
    except (RuntimeError, TypeError, ValueError):
        # A shorter script than before: the old cursor is off the end.
        pass
    if stamp:
        text[DIGEST_PROP] = digest
    return True


# -- parameter storage -----------------------------------------------------

def load_specs(scene):
    raw = scene.get(SPECS_PROP, "")
    if not raw:
        return []
    cached = _specs_cache.get(raw)
    if cached is None:
        try:
            cached = json.loads(raw)
        except ValueError:
            cached = []
        _specs_cache.clear()
        _specs_cache[raw] = cached
    return cached


# The registered PropertyGroup at scene.mesh_params is the canonical value
# store (its backing system ID properties save with the .blend and survive
# class re-registration). While it writes values programmatically, update
# callbacks are suspended so no rebuild loop starts.
_suspend_updates = [False]


def stored_values(scene):
    group = getattr(scene, PARAMS_ATTR, None)
    if group is None:
        return {}
    values = {}
    for key in type(group).bl_rna.properties.keys():
        if key in {"rna_type", "name"}:
            continue
        value = getattr(group, key)
        if hasattr(value, "__len__") and not isinstance(value, str):
            value = list(value)
        values[key] = value
    return values


def _store_values(scene, specs, effective):
    group = getattr(scene, PARAMS_ATTR, None)
    if group is None:
        return
    _suspend_updates[0] = True
    try:
        for spec in specs:
            key = spec["id"]
            if key in effective and hasattr(group, key):
                setattr(group, key, effective[key])
    finally:
        _suspend_updates[0] = False


def get_values(scene):
    """Effective values for the declared parameters (spec defaults filled in)."""
    values = stored_values(scene)
    return {spec["id"]: model_api.clamp(spec, values.get(spec["id"], spec["default"]))
            for spec in load_specs(scene)}


def apply_values(updates):
    """Validate and store parameter values, without rebuilding.

    Split from :func:`set_values` so the cadex backend can store the values
    on the main thread and then run the engine request off it.
    Returns (ok, report).
    """
    import bpy
    scene = bpy.context.scene
    specs = {spec["id"]: spec for spec in load_specs(scene)}
    unknown = [key for key in updates if key not in specs]
    if unknown:
        return False, ("Unknown parameter(s): {:s}. Declared: {:s}".format(
            ", ".join(unknown), ", ".join(specs) or "(none)"))
    ensure_group(load_specs(scene))
    group = getattr(scene, PARAMS_ATTR, None)
    if group is None:
        return False, "No parameters declared by the model script."
    _suspend_updates[0] = True
    try:
        for key, value in updates.items():
            setattr(group, key, model_api.clamp(specs[key], value))
    finally:
        _suspend_updates[0] = False
    return True, ""


def set_values(updates):
    """Set parameter values (validated against the saved specs) and rebuild.
    Returns (ok, report)."""
    ok, report = apply_values(updates)
    if not ok:
        return False, report
    return rebuild()


# -- dynamic property group ------------------------------------------------

def _on_param_update(_self, _context):
    if _suspend_updates[0]:
        return
    _schedule_rebuild()


def _schedule_rebuild():
    import bpy
    if bpy.app.background:
        rebuild()
        return
    if not bpy.app.timers.is_registered(_debounced_rebuild):
        bpy.app.timers.register(_debounced_rebuild, first_interval=0.15)


# The last slider rebuild's failure, or "". Session state: a drag that failed
# is a fact about right now, not about the file, so it is deliberately not
# saved. It exists because a drag has no operator report to land in -- the
# debounce timer runs outside any operator, so the failure used to reach the
# console and nowhere else, which is how a permanently wedged slider could look
# like a slider that simply did nothing (ADR-039).
_last_error = [""]


def last_error():
    return _last_error[0]


def record_error(report):
    _last_error[0] = str(report or "")


def clear_last_error():
    _last_error[0] = ""


def _debounced_rebuild():
    import bpy
    try:
        ok, report = rebuild()
        if ok:
            _last_error[0] = ""
            try:
                bpy.ops.ed.undo_push(message="Mesh: adjust parameters")
            except RuntimeError:
                pass
        elif report:
            _last_error[0] = report
            print("mesh model rebuild failed:\n" + report)
    except Exception:
        _last_error[0] = traceback.format_exc().strip().splitlines()[-1]
        traceback.print_exc()
    # The parameters editor draws `last_error()`, and nothing else repaints it.
    from . import agent as agent_module
    agent_module._tag_redraw()
    return None


def _make_property(spec):
    import bpy
    common = {
        "name": spec.get("name") or spec["id"],
        "description": spec.get("description", ""),
        "update": _on_param_update,
    }
    if spec["type"] == 'FLOAT':
        return bpy.props.FloatProperty(default=spec["default"],
                                       min=spec["min"], max=spec["max"],
                                       **common)
    if spec["type"] == 'INT':
        return bpy.props.IntProperty(default=spec["default"],
                                     min=spec["min"], max=spec["max"],
                                     **common)
    if spec["type"] == 'BOOL':
        return bpy.props.BoolProperty(default=spec["default"], **common)
    if spec["type"] == 'COLOR':
        return bpy.props.FloatVectorProperty(subtype='COLOR', size=3,
                                             min=0.0, max=1.0,
                                             default=tuple(spec["default"]),
                                             **common)
    return None


def _unregister_group():
    import bpy
    if _group_cls[0] is not None:
        if hasattr(bpy.types.Scene, PARAMS_ATTR):
            delattr(bpy.types.Scene, PARAMS_ATTR)
        try:
            bpy.utils.unregister_class(_group_cls[0])
        except RuntimeError:
            pass
        _group_cls[0] = None
        _group_specs_json[0] = None


def ensure_group(specs):
    """(Re-)register the PropertyGroup backing the parameter sliders. No-op
    when the declarations are unchanged, so slider drags never swap the class
    under themselves."""
    import bpy
    specs_json = json.dumps(specs)
    if _group_cls[0] is not None and _group_specs_json[0] == specs_json:
        return
    _unregister_group()
    if not specs:
        return
    annotations = {}
    for spec in specs:
        prop = _make_property(spec)
        if prop is not None:
            annotations[spec["id"]] = prop
    cls = type("MESH_PG_model_params", (bpy.types.PropertyGroup,),
               {"__annotations__": annotations})
    bpy.utils.register_class(cls)
    setattr(bpy.types.Scene, PARAMS_ATTR,
            bpy.props.PointerProperty(type=cls))
    _group_cls[0] = cls
    _group_specs_json[0] = specs_json


# -- the Model collection --------------------------------------------------

def _model_collection(scene):
    import bpy
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
    if collection.name not in scene.collection.children:
        scene.collection.children.link(collection)
    return collection


def rebuild():
    """Rebuild the scene from the model script. Returns (ok, report).

    One path: the script belongs to the cadexd engine, so slider values
    become one revision-guarded ``set_params`` request and the engine's
    tessellation is hydrated back.
    """
    from . import cadex_backend
    return cadex_backend.rebuild_from_sliders()


# -- lifecycle -------------------------------------------------------------

def on_load():
    """Restore the parameter sliders from the saved specs after file load,
    without re-running the script (the scene already holds its result)."""
    import bpy
    try:
        ensure_group(load_specs(bpy.context.scene))
    except Exception:
        traceback.print_exc()


def register():
    pass


def unregister():
    _unregister_group()
