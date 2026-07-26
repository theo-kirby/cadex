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


# -- writing slider values back into the script's declarations ---------------

#: Significant digits kept when a slider value becomes a script literal.
#: Blender's FloatProperty is single-precision, so a slider reading 3.6 in the
#: panel holds 3.5999999046325684, and writing *that* into someone's script is
#: not a defensible thing to do. Six digits is under the float32 noise floor and
#: still readable.
#:
#: It is deliberately coarser than float32's ~7.2 digits, so the literal can sit
#: ~1e-7 of its magnitude away from the slider -- irrelevant against OCCT's own
#: tolerance, and it does not touch the current build at all, because the stored
#: value goes on shadowing the default it was written from
#: (`cadex_backend.apply_slider_defaults`).
_DEFAULT_DIGITS = 6


def rounded_value(value):
    """One slider value as it will be written to the script."""
    return float("{:.{:d}g}".format(float(value), _DEFAULT_DIGITS))


def format_default(value):
    """The literal text for a rewritten ``num()`` default."""
    return repr(rounded_value(value))


def _num_call_name(node):
    import ast
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _params_call(tree):
    """The script's single ``params(...)`` call node, or None."""
    import ast
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _num_call_name(node.func) == "params":
            return node
    return None


def _line_offsets(data):
    offsets = [0]
    for index, byte in enumerate(data):
        if byte == 0x0A:
            offsets.append(index + 1)
    return offsets


def rewrite_defaults(source, values):
    """``source`` with each declared ``num()`` default set to its slider value.

    Returns ``(new_source, changes)`` where changes is a list of
    ``(name, old_text, new_text)``. Raises :class:`ValueError` with a
    user-facing sentence when the declarations cannot be rewritten safely.

    Splices the source rather than unparsing the tree. `ast.unparse` would
    return a canonical rewrite of the *whole* script -- comments gone, layout
    reflowed -- and this script is the artifact the user reads and diffs. Only
    the default's own source span is touched, so everything else, down to the
    spacing inside the `num()` call, is exactly as it was.
    """
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(
            "The script does not parse, so its defaults cannot be "
            "rewritten: {:s}".format(str(exc))) from None

    call = _params_call(tree)
    if call is None:
        raise ValueError("This script declares no params(...) call.")
    if call.args or any(keyword.arg is None for keyword in call.keywords):
        # `params(**declarations)` hides the names from static reading, and
        # guessing which literal belongs to which slider is exactly the kind
        # of guess that silently corrupts a script.
        raise ValueError(
            "This script builds its parameters dynamically; only literal "
            "params(name=num(...)) declarations can be rewritten.")

    data = source.encode("utf-8")
    starts = _line_offsets(data)

    def span(node):
        # ast columns are utf-8 byte offsets, and a label or description may
        # well hold a non-ASCII character.
        return (starts[node.lineno - 1] + node.col_offset,
                starts[node.end_lineno - 1] + node.end_col_offset)

    edits = []
    changes = []
    skipped = []
    for keyword in call.keywords:
        name = str(keyword.arg)
        if name not in values:
            continue
        declaration = keyword.value
        if not (isinstance(declaration, ast.Call)
                and _num_call_name(declaration.func) == "num"):
            skipped.append(name)
            continue
        target = None
        if declaration.args:
            target = declaration.args[0]
        else:
            target = next((item.value for item in declaration.keywords
                           if item.arg == "default"), None)
        if target is None:
            skipped.append(name)
            continue
        start, end = span(target)
        old_text = data[start:end].decode("utf-8")
        new_text = format_default(values[name])
        if old_text == new_text:
            continue
        edits.append((start, end, new_text))
        changes.append((name, old_text, new_text))

    if skipped and not changes:
        raise ValueError(
            "No parameter default could be rewritten ({:s} "
            "{:s} not declared with num(...)).".format(
                ", ".join(sorted(skipped)),
                "is" if len(skipped) == 1 else "are"))

    # Back to front, so each splice leaves the earlier offsets valid.
    for start, end, new_text in sorted(edits, reverse=True):
        data = data[:start] + new_text.encode("utf-8") + data[end:]
    return data.decode("utf-8"), changes


def defaults_differ_from_sliders(scene):
    """True when some slider sits away from its declared default.

    Cheap enough for a draw handler -- it compares the bridged specs against
    the stored values and never parses the script. Rounded on both sides, or
    float32 noise would leave the button lit for ever after it was pressed.
    """
    values = get_values(scene)
    for spec in load_specs(scene):
        name = spec["id"]
        if name not in values:
            continue
        if rounded_value(values[name]) != rounded_value(spec["default"]):
            return True
    return False


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
