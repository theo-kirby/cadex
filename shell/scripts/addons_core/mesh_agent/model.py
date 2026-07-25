# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Model script runtime: the parametric core of Mesh.

The scene is defined by a single Python script stored in
``bpy.data.texts["model.py"]`` — the source of truth. The agent edits the
script (never the scene); rebuilding clears the "Model" collection and runs
the script top-to-bottom with that collection active, so a rebuild is
idempotent and the scene can always be regenerated with different parameter
values.

Parameters declared through ``mesh_model.params()`` (see model_api.py) are
mirrored into a dynamically registered PropertyGroup at ``scene.mesh_params``
so they render as native sliders; dragging one triggers a debounced rebuild.
Values live in the scene's ID properties (saved with the .blend) and are keyed
by parameter id, so they survive script edits that keep ids stable. The specs
themselves are saved as JSON in a scene property so sliders can be restored on
file load without re-running the script.
"""

import contextlib
import io
import json
import traceback

from . import model_api

SCRIPT_NAME = "model.py"
COLLECTION_NAME = "Model"
SPECS_PROP = "mesh_model_specs"
PARAMS_ATTR = "mesh_params"

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


def set_script(source):
    import bpy
    text = bpy.data.texts.get(SCRIPT_NAME)
    if text is None:
        text = bpy.data.texts.new(SCRIPT_NAME)
        text.use_fake_user = True
    text.clear()
    text.write(source)


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


def _debounced_rebuild():
    import bpy
    try:
        ok, report = rebuild()
        if ok:
            try:
                bpy.ops.ed.undo_push(message="Mesh: adjust parameters")
            except RuntimeError:
                pass
        elif report:
            print("mesh model rebuild failed:\n" + report)
    except Exception:
        traceback.print_exc()
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


# -- rebuild ---------------------------------------------------------------

def _model_collection(scene):
    import bpy
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
    if collection.name not in scene.collection.children:
        scene.collection.children.link(collection)
    return collection


def _clear_collection(collection):
    import bpy
    doomed = list(collection.all_objects) + list(collection.children_recursive)
    if doomed:
        bpy.data.batch_remove(doomed)
    # Drop the now-unused meshes/materials from the previous build; anything
    # that must survive (chat transcript, the model script) has a fake user.
    bpy.data.orphans_purge(do_recursive=True)


def _find_layer_collection(layer_collection, name):
    if layer_collection.collection.name == name:
        return layer_collection
    for child in layer_collection.children:
        found = _find_layer_collection(child, name)
        if found is not None:
            return found
    return None


def _adopt_new_objects(collection, names_before):
    """Move objects the script linked elsewhere into the Model collection so
    the next rebuild can clear them."""
    import bpy
    allowed = {collection.name}
    allowed.update(child.name for child in collection.children_recursive)
    for obj in list(bpy.data.objects):
        if obj.name in names_before:
            continue
        users = list(obj.users_collection)
        if not any(user.name in allowed for user in users):
            collection.objects.link(obj)
        for user in users:
            if user.name not in allowed:
                user.objects.unlink(obj)


def rebuild():
    """Rebuild the scene from the model script. Returns (ok, report).

    Backend dispatch: when the scene's mode selects the cadex backend, the
    script belongs to the cadexd engine — slider values become one
    revision-guarded ``set_params`` request and the engine's tessellation
    is hydrated back (cadex_backend.rebuild_from_sliders). Otherwise the
    local path clears the Model collection and exec()s the script; on
    failure the report is the traceback and the previous parameter
    declarations are kept."""
    import bpy
    from . import modes
    if modes.backend_kind(bpy.context.scene) == "cadexd":
        from . import cadex_backend
        return cadex_backend.rebuild_from_sliders()
    scene = bpy.context.scene
    source = get_script()

    collection = _model_collection(scene)
    _clear_collection(collection)

    if not source.strip():
        scene[SPECS_PROP] = json.dumps([])
        ensure_group([])
        return True, "Script is empty; scene cleared."

    layer = _find_layer_collection(bpy.context.view_layer.layer_collection,
                                   collection.name)
    if layer is not None:
        bpy.context.view_layer.active_layer_collection = layer

    names_before = {obj.name for obj in bpy.data.objects}
    model_api._begin(stored_values(scene))
    buffer = io.StringIO()
    error = None
    try:
        code = compile(source, SCRIPT_NAME, "exec")
        namespace = {"__name__": "__main__"}
        with contextlib.redirect_stdout(buffer):
            exec(code, namespace, namespace)
    except Exception:
        error = traceback.format_exc()
    specs, effective = model_api._end()

    if error is not None:
        output = buffer.getvalue().strip()
        return False, (output + "\n" + error if output else error)

    _adopt_new_objects(collection, names_before)

    scene[SPECS_PROP] = json.dumps(specs)
    ensure_group(specs)
    _store_values(scene, specs, effective)

    lines = ["Rebuilt OK: {:d} object(s): {:s}".format(
        len(collection.all_objects),
        ", ".join(sorted(obj.name for obj in collection.all_objects)) or "(none)")]
    if specs:
        lines.append("Parameters: " + "; ".join(
            _describe_param(spec, effective[spec["id"]]) for spec in specs))
    output = buffer.getvalue().strip()
    if output:
        lines.append("stdout:\n" + output)
    return True, "\n".join(lines)


def _describe_param(spec, value):
    if spec["type"] in {'FLOAT', 'INT'}:
        return "{:s}={!s} [{!s}..{!s}]".format(
            spec["id"], value, spec["min"], spec["max"])
    return "{:s}={!s}".format(spec["id"], value)


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
    import sys
    from . import cad_api
    # Make `from mesh_model import ...` and `import mesh_cad` work inside
    # model scripts.
    sys.modules["mesh_model"] = model_api
    sys.modules["mesh_cad"] = cad_api


def unregister():
    import sys
    _unregister_group()
    sys.modules.pop("mesh_model", None)
    sys.modules.pop("mesh_cad", None)
