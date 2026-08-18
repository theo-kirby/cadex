# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
The cadex backend: xscript modeling through a cadexd child (cadex Phase 6).

When the scene's mode selects the cadex backend, the model script is an
**xscript project script** owned by the cadexd engine's project store, not
a locally exec()ed bpy script. This module is the seam between mesh_agent
and that engine:

- lazy per-project session: spawn cadexd (``cadexd_client``), open the
  project root (beside the .blend), rebuild once to hydrate the viewport;
- ``write_script`` / ``set_params`` proxy the engine's lifecycle ops and
  hydrate the returned tessellation into the Model collection
  (``cadex_hydrate``);
- the engine's declared parameters are bridged into the same
  ``scene.mesh_params`` PropertyGroup the local path uses, so the existing
  sliders panel renders them; a slider drag lands in
  ``rebuild_from_sliders()`` (via model.py's debounced rebuild dispatch)
  and becomes a revision-guarded ``set_params`` request.

The engine source of truth is mirrored into ``bpy.data.texts["model.py"]``
for the script view; editing that text has no effect until it is written
back through ``write_script``.
"""

import json
import os
import tempfile
import threading
import time
import traceback

from . import cadexd_client
from . import cadex_animate
from . import cadex_hydrate

ROOT_PROP = "mesh_cadex_root"

#: The project root this file's model lived in when it was last written.
#: Recorded in ``save_pre`` and therefore saved *inside* the resulting
#: .blend, which is what lets a Save-As'd or duplicated file say where its
#: imported geometry came from (ADR-046). Deliberately NOT consulted by
#: :func:`project_root`: it is a migration hint, never a root.
SOURCE_PROP = "mesh_cadex_source_root"

#: The mesh formats the engine stages for ``mesh.import_file`` (cadex
#: ``CadexScriptedRuntime._ASSET_SUFFIXES``). Mirrored here only to decide
#: which files are worth offering to ``put_asset``, which re-validates every
#: one of them; the shell never decides what the engine will accept.
ASSET_SUFFIXES = (".stl", ".obj", ".ply")

#: A part built in another project (cadex ADR-138): the container `link_part`
#: writes into the store and `part.import_part` reads back.
#:
#: A separate name rather than a fourth member of ``ASSET_SUFFIXES``, and the
#: reason is the comment above: that tuple mirrors the engine's
#: ``_ASSET_SUFFIXES`` by name, that set is exactly three, and a mirror that
#: quietly grew a member would make its own docstring false. The engine keeps
#: these apart for the same reason (four constants, one union).
LINKED_PART_SUFFIX = ".cxpart"

#: What a Save-As must carry into the new project. Assets are *inputs* — the
#: script names them and cannot run without them — so a file built on any of
#: them has no recovery path if they are left behind (ADR-046). A linked part
#: is an input on exactly those terms, so it is here.
#:
#: Not the engine's whole stored union: a ``.cxpolicy`` and its provenance
#: pair are not carried today, which is a real gap and a pre-existing one
#: (ADR-084 shipped before ADR-046's carry-forward existed). Naming it here
#: rather than widening this silently, because carrying trained weights on
#: every Save-As is its own decision.
CARRIED_ASSET_SUFFIXES = ASSET_SUFFIXES + (LINKED_PART_SUFFIX,)

#: Progressive display (cadex INTEGRATION.md): slider drags request a
#: coarse, edge-free tessellation to stay under the latency parity bar;
#: once the drag settles, a background ``rebuild`` re-streams the standard
#: tessellation with edges (see ``_schedule_refine``).
DISPLAY_REQUEST = {"quality": "standard", "edges": True}
DRAG_DISPLAY = {"quality": "draft", "edges": False}
REFINE_DELAY_SECONDS = 0.8

#: Wall-clock seconds spent turning an accepted response into viewport
#: objects, oldest first. Hydration runs on the main thread inside
#: :meth:`Lifecycle.poll`, so whatever share of a drag it takes is a share
#: no amount of engine work can remove -- and until this was measured
#: nobody knew whether that share was 2% or 40%. The gate reports it as
#: ``hydrate_seconds``.
_hydrate_seconds = []


def hydrate_timings(reset=False):
    """Recorded hydration durations, oldest first; optionally clear them."""
    global _hydrate_seconds
    recorded = list(_hydrate_seconds)
    if reset:
        _hydrate_seconds = []
    return recorded


def hydrate(payload, animate=True):
    """Turn one accepted response into viewport objects. The only entry point.

    Three call sites used to reach into ``cadex_hydrate.hydrate_display``
    with the same two arguments unpacked from the same payload -- the open
    path, a lifecycle accept, and the settled refine. Collapsing them means
    anything that has to happen on every accepted revision happens once,
    here, rather than in whichever of the three someone remembered.

    ``animate=False`` skips the simulation bake. Mid-drag responses pass it:
    a drag re-runs the whole script, simulation included, and re-baking
    10 000 frames per debounce tick to show a shape change is the wrong
    trade. The settled refine bakes.

    A failed bake never costs you the geometry -- hydration has already
    happened and stands on its own, which is why ``cadex_animate`` is a
    sibling module and not part of ``cadex_hydrate``.

    ``hydrate_display`` keeps its own signature and its own tests; this is
    the payload-shaped wrapper over it.
    """

    started = time.perf_counter()
    try:
        hydration = cadex_hydrate.hydrate_display(
            payload.get("display") or {}, payload.get("revision") or "")
    finally:
        _hydrate_seconds.append(time.perf_counter() - started)
    if animate:
        try:
            hydration["simulation"] = cadex_animate.apply(payload)
        except Exception:
            hydration["simulation"] = {"baked": False,
                                       "error": traceback.format_exc()}
            traceback.print_exc()

    # The collision overlay (ADR-091), on the same terms as the bake: a
    # sibling module, wrapped, so a malformed collision record costs the
    # overlay and never the geometry.
    #
    # Mid-drag (``animate=False``) it CLEARS rather than lags. The shapes it
    # draws are attached to a model that is being re-solved every debounce
    # tick, and a wire cage left over from the previous shape is worse than
    # no wire cage -- this whole feature exists because collision geometry
    # in the wrong place is invisible. Same trade the bake already makes.
    try:
        import bpy
        from . import cadex_collision
        root = project_root(bpy.context.scene)
        if animate:
            state = _state_for(root)
            state.accepted = {"display": payload.get("display") or {},
                              "revision": str(payload.get("revision") or "")}
            hydration["collision"] = cadex_collision.apply(payload, root)
        elif cadex_collision.enabled():
            cadex_collision.clear()
            hydration["collision"] = {"shown": False, "reason": "mid-drag"}
    except Exception:
        hydration["collision"] = {"shown": False,
                                  "error": traceback.format_exc()}
        traceback.print_exc()

    # The dimension overlay (ADR-139), on the same terms again. It refreshes
    # its records on EVERY response, mid-drag included, and does not clear the
    # way collision does: a dimension is measured on the shape in front of you
    # and re-published with it, so mid-drag the numbers are current rather
    # than lagging. That is the opposite trade from a wire cage, for the
    # opposite reason -- a cage left over from the previous shape is wrong,
    # and a number recomputed for this one is right.
    try:
        from . import cadex_dimension
        hydration["dimensions"] = cadex_dimension.apply(payload)
    except Exception:
        hydration["dimensions"] = {"shown": False,
                                   "error": traceback.format_exc()}
        traceback.print_exc()
    return hydration


def last_accepted(root=None):
    """The last accepted response's ``{display, revision}`` for this project.

    What lets the overlay be switched on between rebuilds instead of
    requiring one.
    """

    import bpy
    root = root or project_root(bpy.context.scene)
    return dict(_state_for(root).accepted or {})


def mjcf_validation_evidence(root=None):
    """``model_evidence`` read off the mjcf publication object (path B).

    The reader the trace cannot replace: a model that is mjcf-only has no
    trace at all, and a **rollout's** trace carries the small evidence dict
    without the ``collisions`` block.

    Nothing new crosses the boundary. This is ``inspect scope="object"`` on
    a property the engine already publishes, read through ``_inspect_full``,
    which already follows the pager and already concatenates
    ``kind == "string"`` pages -- which is exactly what a ~6 KiB JSON string
    property needs and is why this cost no protocol change.

    Cached on the project state by accepted revision: one round trip per
    revision, not one per redraw.
    """

    import bpy
    from . import cadex_collision

    root = root or project_root(bpy.context.scene)
    state = _state_for(root)
    accepted = dict(state.accepted or {})
    revision = str(accepted.get("revision") or "")
    cached_revision, cached = state.collision_evidence
    if cached is not None and cached_revision == revision and revision:
        return cached

    wanted = cadex_collision.mjcf_outputs(accepted.get("display") or {})
    if not wanted:
        return None

    client = _client(root)
    # The objects page carries `label` beside `name`, so the output we want
    # is found without a request per object: a published output's label IS
    # its declared name. The scan below is the fallback for a publisher that
    # ever stops being true of.
    identities = _inspect_full(client, "document", "/objects") or []
    targets = [str(item.get("name")) for item in identities
               if isinstance(item, dict) and str(item.get("label") or "") in wanted]
    if not targets:
        targets = [str(item.get("name")) for item in identities
                   if isinstance(item, dict)
                   and str(item.get("type") or "") == "App::FeaturePython"]

    for target in targets:
        value = _inspect_full(
            client, "object",
            "/properties/CadexAssemblyMjcfValidation/value", target)
        if not isinstance(value, str) or not value:
            continue
        try:
            evidence = (json.loads(value) or {}).get("dynamics")
        except ValueError:
            continue
        if isinstance(evidence, dict) and evidence.get("collisions"):
            state.collision_evidence = (revision, evidence)
            return evidence
    state.collision_evidence = (revision, None)
    return None


STALE_REVISION_CODE = "STALE_PROGRAM_REVISION"
RESTORE_FAILED_CODE = "CADEXD_RESTORE_FAILED"

#: Session-scoped fallback roots for unsaved .blend files, keyed by scene
#: name so each scene keeps one stable engine project per Blender run.
_unsaved_roots = {}

#: Cached engine state per project root: revision guard, specs, values.
_states = {}


class _State:
    def __init__(self):
        self.revision = ""
        self.specs = []       # engine param_specs, verbatim
        self.values = {}
        #: The source as the engine last reported it. Kept so Revert can put
        #: the buffer back without a round trip (ADR-039) -- the buffer is the
        #: only other copy, and a hand edit is what Revert undoes.
        self.source = ""
        self.script_present = False
        self.opened = False
        #: The engine's restore block from the last open (ADR-017): what
        #: it re-ran and whether the digest matched.
        self.restore = {}
        #: Non-empty while this project is open WITHOUT a proven restore
        #: (ADR-044). Rides on every tool result from such a project so the
        #: caller cannot mistake a rewrite-in-progress for a healthy model.
        self.restore_warning = ""
        #: The last accepted response's ``display`` block and revision, so
        #: the collision overlay (ADR-091) can be switched on between
        #: rebuilds without asking for one. Just those two keys -- the whole
        #: payload holds artifact paths and stdout nobody needs kept alive.
        self.accepted = {}
        #: ``model_evidence`` for ``self.accepted["revision"]``, cached
        #: because path B is a round trip and a redraw is not a reason to
        #: take one. Keyed by revision, so an accepted rebuild invalidates it
        #: by construction rather than by anyone remembering to.
        self.collision_evidence = ("", None)


def _preferences():
    try:
        import bpy
        addon = bpy.context.preferences.addons.get(__package__)
        return addon.preferences if addon is not None else None
    except Exception:
        return None


def _prefs_freecadcmd():
    prefs = _preferences()
    return str(getattr(prefs, "freecadcmd_path", "") or "") if prefs else ""


def engine_budgets():
    """Sandbox budgets for one engine script run, from the add-on prefs.

    Empty when both are zero: the engine then applies its own defaults
    (cadex CadexEngineSettings), which is the right answer for a user who
    has never thought about budgets.
    """
    prefs = _preferences()
    if prefs is None:
        return {}
    timeout = float(getattr(prefs, "engine_timeout_seconds", 0.0) or 0.0)
    memory_mb = int(getattr(prefs, "engine_memory_limit_mb", 0) or 0)
    budgets = {}
    if timeout > 0.0:
        budgets["timeout_seconds"] = timeout
    if memory_mb > 0:
        budgets["memory_limit_mb"] = memory_mb
    return budgets


def project_root(scene):
    """The engine project root for this scene.

    Saved .blend: ``<dir>/<stem>.cadex`` beside the file — **derived every
    time, never cached**. Caching it in ``scene[ROOT_PROP]`` (as Phase 6
    did) turned the derived value into an indistinguishable user override,
    so Save-As kept pointing the new file at the old file's engine project.
    ``ROOT_PROP`` now means one thing only: a root the user chose.

    Unsaved: one stable temporary root per scene for the session.
    """
    import bpy
    explicit = str(scene.get(ROOT_PROP, "") or "")
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    if bpy.data.filepath:
        stem = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        return os.path.join(os.path.dirname(bpy.data.filepath),
                            stem + ".cadex")
    key = scene.name
    root = _unsaved_roots.get(key)
    if root is None or not os.path.isdir(root):
        root = tempfile.mkdtemp(prefix="mesh-cadex-")
        _unsaved_roots[key] = root
    return root


def remember_source_root(scene):
    """Record the project root this file is about to be written away from.

    Called from ``save_pre``, where ``bpy.data.filepath`` still names the
    *old* file: what gets stored is the root that holds the model right now,
    and it is stored before the write, so it travels into the new file.
    Save-As is the case that needs it, but the first save of an unsaved
    file -- temp root to ``<stem>.cadex`` -- is the same move and loses its
    imported geometry the same way, so it gets the same hint.
    """
    if scene is None:
        return
    try:
        scene[SOURCE_PROP] = project_root(scene)
    except Exception:
        pass


def source_root(scene):
    """Where this file's model was before it got its current name, or "".

    The hint saved into the .blend first, because it survives a restart and
    a plain file-manager copy. The session's own open roots are the fallback
    for a file that was never saved with this add-on's handler installed.
    Only a root that is not the current one, and that has imported geometry
    in it, is worth reporting.
    """
    try:
        current = os.path.abspath(project_root(scene))
    except Exception:
        return ""
    remembered = ""
    try:
        remembered = str(scene.get(SOURCE_PROP, "") or "")
    except Exception:
        pass
    for candidate in [remembered] + list(open_roots()):
        if not candidate:
            continue
        candidate = os.path.abspath(candidate)
        if candidate != current and _assets_in(candidate):
            return candidate
    return ""


def _assets_in(root):
    """Absolute paths of the carryable input files in one project root.

    The only directory of the store the shell ever reads, and it reads it
    only to hand the paths back to ``put_asset``. What is in there is not
    derived state: it is the files the user handed us, which the shell is
    what supplied in the first place. The walk mirrors the engine's staging
    walk -- flat, known suffixes, no symlinks -- so it never offers a file a
    run would skip (ADR-046).

    ``.cxpart`` is in the set the same way and for the same reason: a script
    that says ``part.import_part("sensor.cxpart")`` cannot run without it,
    so a Save-As that left it behind would break exactly the recovery ADR-046
    exists to keep (ADR-138).
    """
    directory = os.path.join(root, "assets")
    if not os.path.isdir(directory):
        return []
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return []
    found = []
    for name in names:
        path = os.path.join(directory, name)
        if os.path.islink(path) or not os.path.isfile(path):
            continue
        if os.path.splitext(name)[1].lower() not in CARRIED_ASSET_SUFFIXES:
            continue
        found.append(path)
    return found


def _state_for(root):
    state = _states.get(root)
    if state is None:
        state = _State()
        _states[root] = state
    return state


def bundle_roots():
    """Directories that may hold the engine payload shipped inside Mesh.

    Mesh installs the payload beside its own scripts (cadex ADR-023):
    ``Blender.app/Contents/Resources/cadex`` on macOS, ``<install>/cadex``
    on Linux and Windows. Both are probed from ``bpy.app.binary_path`` so
    the add-on finds its engine with no configuration at all.
    """
    try:
        import bpy
        binary = bpy.app.binary_path
    except Exception:
        return ()
    if not binary:
        return ()
    binary_dir = os.path.dirname(os.path.abspath(binary))
    roots = [
        os.path.join(binary_dir, "cadex"),
        # macOS: MacOS/Blender -> Contents/Resources/cadex
        os.path.join(os.path.dirname(binary_dir), "Resources", "cadex"),
    ]
    try:
        import bpy
        # Portable/versioned layouts put resources under a version directory.
        resource = bpy.utils.resource_path('LOCAL')
        if resource:
            roots.append(os.path.join(resource, "cadex"))
    except Exception:
        pass
    return tuple(root for root in roots if os.path.isdir(root))


def preflight():
    """Engine availability for this install. Returns ``(ok, reason, remedy)``."""
    return cadexd_client.preflight(_prefs_freecadcmd(), bundle_roots())


def resolved_engine():
    """``(freecadcmd, module_dir)`` this install would use, for display."""
    return cadexd_client.resolve_engine(_prefs_freecadcmd(), bundle_roots())


def _client(root):
    freecadcmd, module_dir = cadexd_client.resolve_engine(
        _prefs_freecadcmd(), bundle_roots())
    if not freecadcmd or not module_dir:
        _ok, reason, remedy = preflight()
        raise RuntimeError(reason + " " + remedy)
    return cadexd_client.client_for(
        root, cadexd_client.default_command(freecadcmd, module_dir),
        budgets=engine_budgets())


def _progress(event):
    kind = str(event.get("event") or "")
    if kind:
        print("cadexd:", kind)


def _adopt_script_state(scene, script_state, preserve_local=False):
    """Cache revision/specs/values from one engine script-state block and
    mirror them into the scene (sliders + script text).

    ``preserve_local`` is for the open path. Opening a project that holds no
    script at all must not erase what the .blend remembers: a duplicated or
    Save-As'd file names a project root that does not exist, the engine
    creates it empty (``open_project`` mkdirs), and bridging that emptiness
    back would overwrite the saved specs with ``[]`` and unregister the
    slider group -- destroying the only copy of the parameter declarations
    the file still had. An engine that *has* a script is always authoritative,
    including when that script declares no parameters.
    """
    root = project_root(scene)
    state = _state_for(root)
    params = dict(script_state.get("params") or {})
    revisions = dict(script_state.get("revisions") or {})
    state.revision = str(revisions.get("working_revision") or "")
    state.specs = [dict(spec) for spec in list(params.get("specs") or [])]
    state.values = {str(key): value
                    for key, value in dict(params.get("values") or {}).items()}
    state.script_present = bool(script_state.get("script_present"))
    if preserve_local and not state.script_present \
            and scene_remembers_a_model(scene):
        # Nothing to adopt, and everything to lose. The block for an empty
        # project carries source="" -- a str, so it would clear the script
        # mirror as well as the specs, and the mirror is exactly what
        # adopt_saved_script() rebuilds the project from.
        return
    source = script_state.get("source")
    if isinstance(source, str):
        state.source = source
        mirror_script_text(source)
    _bridge_params(scene, state)


def cached_script_state(scene):
    """The cached engine state for this scene's project, or None.

    Read-only, and deliberately does not open the project: the callers are
    panel draws and Revert, none of which should spawn an engine.
    """
    try:
        return _states.get(project_root(scene))
    except Exception:
        return None


def mirror_script_text(source, accepted=True):
    """Put ``source`` in the script buffer. ``accepted`` marks it engine truth.

    A source the engine refused is mirrored with ``accepted=False``: it stays
    on screen to be fixed, but it does not get the clean stamp.
    """
    from . import model
    if not model.set_script(source, stamp=accepted):
        return
    # The mirror is written outside agent turns too (`ensure_open`, a rebuild,
    # an adopt), and a Text Editor showing it will not repaint on its own.
    from . import agent as agent_module
    agent_module._tag_redraw()


def _bridge_params(scene, state):
    """Engine param_specs → the scene.mesh_params sliders (Blender specs)."""
    from . import model
    bridged = []
    values = {}
    for spec in state.specs:
        name = str(spec.get("name") or "")
        if not name:
            continue
        default = float(spec.get("default") or 0.0)
        low = spec.get("min")
        high = spec.get("max")
        if low is None:
            low = 0.0 if default >= 0.0 else default * 4.0
        if high is None:
            high = default * 4.0 if default > 0.0 else 1.0
        label = str(spec.get("label") or "") or name.replace("_", " ").title()
        unit = str(spec.get("unit") or "")
        if unit:
            label = "{:s} ({:s})".format(label, unit)
        bridged.append({
            "id": name,
            "type": 'FLOAT',
            "default": default,
            "min": float(low),
            "max": float(high),
            "name": label,
            "description": str(spec.get("description") or ""),
        })
        value = state.values.get(name, default)
        values[name] = float(value)
    scene[model.SPECS_PROP] = json.dumps(bridged)
    model.ensure_group(bridged)
    model._store_values(scene, bridged, values)


def _revision_from_payload(scene, payload):
    """Track the engine's revision guard from any lifecycle payload."""
    state = _state_for(project_root(scene))
    model_state = payload.get("model_state")
    if isinstance(model_state, dict):
        revision = str(model_state.get("next_write_expected_revision") or "")
        if revision:
            state.revision = revision


#: Page size for :func:`_inspect_full`. The engine caps ``limit`` at 50.
_INSPECT_PAGE = 50


def _resolve_stub(client, scope, value, target=""):
    """Re-read one previewed value, if that is what this is.

    ``inspect`` replaces any value over 1 KiB with a marker carrying the
    JSON Pointer to reach it -- ``{"type": "array", "item_count": 11,
    "inspect_path": "/params/specs"}``. Nothing in a script-state payload
    legitimately looks like that, so the pair of keys is the test.
    """
    if isinstance(value, dict) and "inspect_path" in value and "type" in value:
        return _inspect_full(client, scope, str(value["inspect_path"]), target)
    return value


def _inspect_full(client, scope, path, target=""):
    """The whole value at ``path``, following the pager and the previews.

    ``inspect`` is the *assistant's* reader: it bounds every result at 32 KiB
    by paging containers and by replacing anything over 1 KiB with a stub
    (:func:`_resolve_stub`). That is right for a model reading a payload it
    has to pay for, and wrong for the shell, which needs the specs it turns
    into sliders and the source it mirrors -- whole, or not at all.

    So the shell follows what the pager and the stubs point at. This used to
    read the top page and take it at face value: correct for a one-parameter
    test fixture, and silently empty for every real model, which is how it
    survived (the ADR-027 golden for ``inspect`` has one parameter in it).

    Returns ``None`` if the first page fails.
    """
    offset = 0
    whole = None
    while True:
        args = {"scope": scope, "path": path, "offset": offset,
                "limit": _INSPECT_PAGE}
        if target:
            args["target"] = target
        result = client.request("inspect", args)
        if result.get("ok") is not True:
            return whole
        value = result.get("value")
        page = dict(result.get("page") or {})
        kind = str(page.get("kind") or "")
        if kind == "mapping":
            merged = dict(whole or {})
            for key, item in dict(value or {}).items():
                merged[key] = _resolve_stub(client, scope, item, target)
            whole = merged
        elif kind == "array":
            merged = list(whole or [])
            merged.extend(_resolve_stub(client, scope, item, target)
                          for item in list(value or []))
            whole = merged
        elif kind == "string":
            whole = (whole or "") + str(value or "")
        else:
            return value
        next_offset = page.get("next_offset")
        if next_offset is None:
            return whole
        offset = int(next_offset)


def _refresh_script_state(scene):
    """Re-read engine script state (source, specs, values, revisions)."""
    client = _client(project_root(scene))
    state = _inspect_full(client, "script", "")
    # `script_present` is the cheapest proof that a whole script-state block
    # came back rather than an error body or a truncated page. Adopting one of
    # those would bridge empty specs over good ones.
    if not isinstance(state, dict) or "script_present" not in state:
        return False
    _adopt_script_state(scene, state)
    return True


def ensure_open(scene, unrestored_ok=False):
    """Open the scene's engine project (idempotent). Returns (ok, report).

    The open runs the engine's **restore pass**: cadexd re-executes the
    accepted script into a fresh ephemeral document and asserts that the
    resulting content digest equals the accepted one. That is the guarantee
    cadex docs/ARCHITECTURE.md makes for every open — "delete the document,
    re-run the script, get a byte-equivalent model back" — and Phase 6 was
    quietly opting out of it with ``restore: False`` to save a script run.
    A model whose script no longer reproduces it is a corrupt model, and
    the user should be told at open, not at the next edit.

    A failed restore is a first-class error: ``CADEXD_RESTORE_FAILED`` says
    the stored script and the stored digest disagree, which needs a human,
    not a retry.

    ``unrestored_ok`` is the one exception, and it is what makes that error
    survivable. The failure report tells the caller to rewrite the script —
    but every tool, ``write_script`` included, comes through here, so the
    remedy was gated behind the thing it remedies and the project was shut
    for good (ADR-044). Callers that *replace* the stored script rather than
    build on it pass ``unrestored_ok=True``; the project is then reopened
    with ``restore: False``, and the returned report is a warning, not an
    error. Everything that would build on an unproven model still refuses.
    """
    root = project_root(scene)
    state = _state_for(root)
    client = _client(root)
    if state.opened and client.alive():
        return True, state.restore_warning
    opened = client.request(
        "open_project",
        {"project_root": root, "restore": True},
        progress_callback=_progress)
    if opened.get("ok") is not True:
        if str(opened.get("failure_code") or "") == RESTORE_FAILED_CODE:
            report = _restore_failure_report(root, opened)
            if not unrestored_ok:
                return False, report
            return _open_unrestored(scene, root, state, client, report)
        return False, _failure_report("open_project", opened)
    state.restore_warning = ""
    state.opened = True
    state.restore = dict(opened.get("restore") or {})
    _adopt_script_state(scene, dict(opened.get("script") or {}),
                        preserve_local=True)
    if state.script_present:
        # The restore pass proved the model; this second run is purely to
        # get the tessellation for the viewport. cadexd's open_project has
        # no display argument yet (cadex A1), so it costs one more script
        # run per open -- measured in the gate report as open_seconds.
        rebuilt = client.request(
            "rebuild", {"display": dict(DISPLAY_REQUEST)},
            progress_callback=_progress)
        if rebuilt.get("ok") is not True:
            return False, _failure_report("rebuild", rebuilt)
        _revision_from_payload(scene, rebuilt)
        hydrate(rebuilt)
        _refresh_script_state(scene)
    return True, ""


def _open_unrestored(scene, root, state, client, report):
    """Reopen a project whose restore pass failed, for a rewrite.

    No rebuild and no hydration: the stored script does not run, so there is
    no model to show and asking for one would only fail a second time. The
    script state still comes back, which is what the caller needs in order
    to write a replacement.
    """
    opened = client.request(
        "open_project",
        {"project_root": root, "restore": False},
        progress_callback=_progress)
    if opened.get("ok") is not True:
        return False, _failure_report("open_project", opened)
    state.opened = True
    state.restore = dict(opened.get("restore") or {})
    state.restore_warning = (
        report + "\n\nThe project was opened WITHOUT restoring, so that the "
        "script can be replaced. Nothing is published until a write_script "
        "succeeds; the accepted geometry is untouched until then.")
    _adopt_script_state(scene, dict(opened.get("script") or {}),
                        preserve_local=True)
    return True, state.restore_warning


def _restore_failure_report(root, payload):
    """CADEXD_RESTORE_FAILED, said plainly.

    The engine could not reproduce the accepted model from the stored
    script. Retrying cannot help: either the script was edited outside
    Mesh, or the model was accepted under a different engine build.
    """
    lines = [
        "The cadex engine could not restore this model.",
        "Its stored script no longer reproduces the geometry that was "
        "accepted, so the project store at {:s} is inconsistent.".format(root),
        str(payload.get("error") or ""),
    ]
    observed = payload.get("observed")
    if observed:
        lines.append("Digests: " + json.dumps(observed, default=str))
    inner = payload.get("restore_failure")
    if isinstance(inner, dict) and inner.get("error"):
        lines.append("The re-run failed with: " + str(inner["error"]))
    lines.append(
        "Rewrite the script to rebuild the model, or restore a backup of "
        "the .cadex directory. Retrying the same open will not help.")
    return "\n".join(line for line in lines if line)


def _failure_report(op, payload):
    parts = ["cadexd {:s} failed".format(op)]
    code = str(payload.get("failure_code") or "")
    if code:
        parts[0] += " [{:s}]".format(code)
    error = str(payload.get("error") or "")
    if error:
        parts.append(error)
    for key in ("requested", "observed", "lint", "orphans"):
        value = payload.get(key)
        if value:
            parts.append("{:s}: {:s}".format(key, json.dumps(value, default=str)))
    stdout = str(payload.get("stdout") or "")
    if stdout.strip():
        parts.append("script stdout:\n" + stdout.strip())
    return "\n".join(parts)


def _accept_report(payload, hydration):
    outputs = list(payload.get("outputs") or [])
    lines = ["Accepted revision {:s}: {:d} output(s): {:s}".format(
        str(payload.get("revision") or "?"), len(outputs),
        ", ".join(sorted(str(item.get("name")) for item in outputs))
        or "(none)")]
    if hydration:
        moved = (len(hydration.get("created") or [])
                 + len(hydration.get("updated") or []))
        lines.append("Viewport: {:d} object(s) hydrated, {:d} removed.".format(
            moved, len(hydration.get("removed") or [])))
    stdout = str(payload.get("stdout") or "")
    if stdout.strip():
        lines.append("stdout:\n" + stdout.strip())
    return "\n".join(lines)


class Lifecycle:
    """One revision-guarded modeling request, off the main thread.

    The engine runs the user's script in a sandboxed worker; that takes
    from half a second to (with a heavy script) minutes, and blocking
    Blender's main thread for it freezes the whole application. So the
    request runs on a worker thread — the same shape ``_schedule_refine``
    has used since Phase 6 — while every ``bpy`` touch (state adoption,
    hydration) stays on the main thread inside :meth:`poll`.

    Usage is a poll loop: :meth:`poll` returns None while in flight and
    ``(ok, report)`` when finished. ``cancelled`` is a zero-argument
    predicate; when it turns true the client forwards a ``cancel`` frame
    and the engine answers ``RUN_CANCELLED``.

    A ``STALE_PROGRAM_REVISION`` refusal (the engine's guard after a
    respawn or a background refine) is retried once with the engine's
    declared expectation.
    """

    def __init__(self, scene, op, args, display=None, guarded=True,
                 cancelled=None, on_accept=None):
        #: Main-thread callback run once, after a successful hydration.
        self.on_accept = on_accept
        self._scene = scene
        self._op = str(op)
        self._args = dict(args)
        self._display = dict(display or DISPLAY_REQUEST)
        self._guarded = bool(guarded)
        self._cancelled = cancelled
        self._root = project_root(scene)
        self._state = _state_for(self._root)
        self._client = _client(self._root)
        self._attempt = 0
        self._thread = None
        self._result = {}
        self._start()

    def _start(self):
        """Main thread: snapshot the guard and hand the request to a worker."""
        request_args = dict(self._args)
        if self._guarded:
            request_args["expected_revision"] = self._state.revision
        request_args["display"] = dict(self._display)
        self._result = {}
        client, op = self._client, self._op
        result, cancelled = self._result, self._cancelled

        def worker():
            try:
                result["payload"] = client.request(
                    op, request_args, progress_callback=_progress,
                    cancellation_check=cancelled)
            except Exception:
                result["payload"] = {
                    "ok": False,
                    "failure_code": "MESH_CLIENT_ERROR",
                    "error": traceback.format_exc(),
                }

        self._thread = threading.Thread(target=worker, name="cadex-lifecycle",
                                        daemon=True)
        self._thread.start()

    def poll(self):
        """Main thread. None while in flight, else ``(ok, report)``."""
        if self._thread.is_alive():
            return None
        payload = self._result.get("payload") or {}
        if payload.get("ok") is not True:
            previous = self._state.revision
            _revision_from_payload(self._scene, payload)
            stale = str(payload.get("failure_code") or "") == STALE_REVISION_CODE
            if (stale and self._attempt == 0
                    and self._state.revision != previous):
                self._attempt += 1
                self._start()
                return None
            return False, _failure_report(self._op, payload)
        _revision_from_payload(self._scene, payload)
        try:
            # A draft display is a mid-drag response: re-baking the whole
            # simulation on every debounce tick to show a shape change is
            # the wrong trade. The settled refine, which asks for standard
            # quality, bakes.
            hydration = hydrate(
                payload,
                animate=str(self._display.get("quality") or "") != "draft")
        except Exception:
            return False, ("The engine accepted the revision but viewport "
                           "hydration failed:\n" + traceback.format_exc())
        if self.on_accept is not None:
            self.on_accept()
        return True, _accept_report(payload, hydration)

    def wait(self, interval=0.01):
        """Block until finished. For background mode and direct callers."""
        while True:
            outcome = self.poll()
            if outcome is not None:
                return outcome
            time.sleep(interval)


def begin_lifecycle(scene, op, args, display=None, guarded=True,
                    cancelled=None, on_accept=None, unrestored_ok=False):
    """Start a modeling request. Returns ``(False, report)`` if the project
    could not be opened, else a :class:`Lifecycle` to poll."""
    ok, report = ensure_open(scene, unrestored_ok=unrestored_ok)
    if not ok:
        return False, report
    _cancel_refine(project_root(scene))
    # A *queued* drag is stale the moment the agent writes: its values were
    # captured against a revision this request is about to move. An
    # in-flight one is left alone -- it already holds the client and will
    # finish in a moment.
    _supersede_drag(project_root(scene))
    return Lifecycle(scene, op, args, display=display, guarded=guarded,
                     cancelled=cancelled, on_accept=on_accept)


# -- the agent's two modeling tools, in begin/poll form ----------------------

def begin_write_script(scene, source, replace=False, cancelled=None):
    """Start a ``write_script``. Returns a :class:`Lifecycle` or (ok, report).

    The one op that runs on an unrestored project: it replaces the stored
    script outright, so it neither reads nor builds on the model the restore
    pass could not prove, and it is the documented way out of that state
    (ADR-044).
    """
    def accepted():
        # The rewrite ran and was accepted, so the store is consistent again:
        # this revision is both the working and the accepted one.
        _state_for(project_root(scene)).restore_warning = ""
        _refresh_script_state(scene)

    args = {"source": source}
    if replace:
        args["replace"] = True
    return begin_lifecycle(
        scene, "write_script", args, cancelled=cancelled,
        on_accept=accepted, unrestored_ok=True)


def begin_set_params(scene, updates, cancelled=None):
    """Validate + store slider values, then start a ``set_params``.

    Returns a :class:`Lifecycle` or an immediate ``(ok, report)``.
    """
    from . import model
    ok, report = ensure_open(scene)
    if not ok:
        return False, report
    ok, report = model.apply_values(updates)
    if not ok:
        return False, report
    root = project_root(scene)
    state = _state_for(root)
    if not state.script_present:
        return True, "No project script yet; nothing to rebuild."
    values = _slider_values(scene, state)
    if not values:
        return False, "The project script declares no parameters."

    def accepted():
        state.values.update(values)
        _schedule_refine(scene)

    return begin_lifecycle(scene, "set_params", {"values": values},
                           cancelled=cancelled, on_accept=accepted)


def wiring_state(scene):
    """The harness as a graph: ``inspect scope="wiring"`` (ADR-065).

    Through :func:`_inspect_full` rather than one ``inspect`` call, because
    a seven-component harness exceeds both the 50-key page and the 1 KiB
    stub — the same reason the parameter specs go through it, and the same
    bug that made ``_bridge_params`` silently empty for every real model.
    """

    ok, report = ensure_open(scene)
    if not ok:
        return {"ok": False, "error": str(report)}
    return _inspect_full(_client(project_root(scene)), "wiring", "")


def begin_set_nets(scene, rows, cancelled=None):
    """Start a connection-table edit. Returns ``(ok, report)``.

    The same op the sliders use, because "set the values of declared controls
    without the AI" is one concept (ADR-065): ``set_params`` with an empty
    ``values`` patch and the complete row list. A net change adds and removes
    cables rather than moving poses, so there is nothing ``preview_params``
    could answer and no draft-quality pass worth taking — it goes straight to
    the accepting path, and schedules the same settle-time refine.
    """

    return begin_set_tables(scene, nets=rows, cancelled=cancelled)


def begin_set_tables(scene, nets=None, boards=None, mounts=None, cages=None,
                     cancelled=None):
    """Start one ``set_params`` carrying whichever declared tables changed.

    One op and one re-execute, because a rename that moves a terminal *and*
    the wires addressing it is one edit (ADR-120). ``values`` is empty: a
    table edit leaves the sliders alone, and the engine reads that as "leave
    them" rather than as the refusal it still is when ``values`` is the only
    thing asked for.

    **Returns a report, never a Lifecycle** (ADR-122). It used to return the
    raw object, and its one caller threw it away — so nothing ever called
    ``poll()``, so ``_revision_from_payload`` never ran, so the shell's
    cached ``expected_revision`` still named the revision before the first
    apply and **every push after the first was refused with
    ``STALE_PROGRAM_REVISION``** with nobody reading the refusal. The request
    now goes into a slot the pump below drives to completion, exactly as a
    slider drag has been driven since Phase 6.
    """

    ok, report = ensure_open(scene)
    if not ok:
        return False, report
    root = project_root(scene)
    state = _state_for(root)
    if not state.script_present:
        return True, "No project script yet; nothing to edit."
    args = {"values": {}}
    if nets is not None:
        args["nets"] = list(nets)
    if boards is not None:
        args["boards"] = list(boards)
    if mounts is not None:
        args["mounts"] = list(mounts)
    if cages is not None:
        args["cages"] = list(cages)
    if len(args) == 1:
        return True, "No change."
    return _queue_wiring(scene, root, args)


# -- the wiring pump: one table push in flight, the newest one queued --------
#
# The exact shape of ``_drags``/``_drag_pump`` above and for the same reasons:
# at most one request in flight per project root, the next one queued, polled
# on a timer, and ``project_root`` re-checked before hydrating so a Save-As
# mid-flight cannot repaint the new file.
#
# It differs from the drag slot in one way, and it is the canvas that dictates
# it: a push carries the **whole** table, so a second push arriving while one
# is in flight *replaces* the queued payload rather than starting a second
# request. There is nothing to coalesce -- the newest table supersedes.

_wirings = {}


def _wiring_slot(root):
    slot = _wirings.get(root)
    if slot is None:
        slot = {"lifecycle": None, "queued": None, "requests": 0,
                "outcome": None}
        _wirings[root] = slot
    return slot


def _queue_wiring(scene, root, args):
    """Fill the slot and start pumping. Returns ``(True, "applying")``."""

    import bpy

    slot = _wiring_slot(root)
    if slot.get("lifecycle") is not None:
        slot["queued"] = dict(args)
        return True, "applying"
    started = _start_wiring(scene, root, slot, args)
    if isinstance(started, tuple):
        return started
    if not bpy.app.background:
        bpy.app.timers.register(lambda: _wiring_pump(root), first_interval=0.02)
    return True, "applying"


def _start_wiring(scene, root, slot, args):
    """Begin one table push. A ``(ok, report)`` tuple means it never started."""

    slot["queued"] = None
    started = begin_lifecycle(scene, "set_params", dict(args))
    if not isinstance(started, Lifecycle):
        return started
    slot["lifecycle"] = started
    slot["requests"] = int(slot.get("requests") or 0) + 1
    return None


def _wiring_pump(root):
    """Main thread. Poll the in-flight push; start the queued one after it.

    The one completion path (ADR-122). ``Lifecycle.on_accept`` used to carry
    half of this and was never reached, which is why ``cadex_pending`` stuck
    at "applying…" and the settle-time refine never fired.
    """

    import bpy
    from . import agent as agent_module
    from . import model

    slot = _wirings.get(root)
    if slot is None:
        return None
    lifecycle = slot.get("lifecycle")
    if lifecycle is None:
        return None

    scene = bpy.context.scene
    if project_root(scene) != root:
        slot["lifecycle"] = None
        slot["queued"] = None
        return None

    outcome = lifecycle.poll()
    if outcome is None:
        return 0.02

    ok, report = outcome
    slot["lifecycle"] = None
    slot["outcome"] = (ok, report)
    try:
        from . import wiring

        wiring.on_push_finished(scene, ok, report)
    except Exception:
        traceback.print_exc()
    if ok:
        _schedule_refine(scene)
    elif report:
        # A timer has no operator to report through; ADR-039's panel is where
        # a failure that happened outside a click belongs.
        model.record_error(report)
        print("mesh wiring push failed:\n" + report)
    agent_module._tag_redraw()

    queued = slot.get("queued")
    if queued is not None:
        started = _start_wiring(scene, root, slot, queued)
        if isinstance(started, tuple):
            return None
        return 0.02
    return None


def wiring_apply_now(root=None):
    """Drive the wiring pump to completion synchronously. Test-facing.

    The peer of :func:`drag_now`'s and :func:`refine_now`'s blocking forms:
    ``bpy.app.timers`` do not fire under ``--background``, so the gate suites
    drain the slot themselves. Returns ``(ok, report)`` of the last push, or
    ``(True, "")`` when there was nothing in flight.
    """

    import bpy

    root = root or project_root(bpy.context.scene)
    slot = _wirings.get(root)
    if slot is None:
        return True, ""
    # Ticks of the pump, not a ``Lifecycle.wait()`` followed by one: the pump
    # owns the single completion path, and polling a lifecycle twice would
    # hydrate the same payload twice.
    while slot.get("lifecycle") is not None:
        if _wiring_pump(root) is not None:
            time.sleep(0.01)
    return slot.get("outcome") or (True, "")


def wiring_stats(root=None, reset=False):
    """``{requests, queued, in_flight}`` for the gate. Test-facing."""

    import bpy
    root = root or project_root(bpy.context.scene)
    slot = _wiring_slot(root)
    stats = {
        "requests": int(slot.get("requests") or 0),
        "queued": slot.get("queued") is not None,
        "in_flight": slot.get("lifecycle") is not None,
    }
    if reset:
        slot["requests"] = 0
    return stats


def pump_wiring_once(root=None):
    """Run one wiring-pump tick by hand. Test-facing, like ``pump_drag_once``."""

    import bpy
    return _wiring_pump(root or project_root(bpy.context.scene))


def begin_set_boards(scene, rows, cancelled=None):
    """Start a terminal-table edit. Returns ``(ok, report)``.

    The third table through the one op (ADR-120), and the reason a measured
    terminal no longer costs a chat turn: a pick writes a canonical row
    straight into ``board_values`` instead of queueing a note for the
    assistant to transcribe. Like a net change it adds and removes geometry
    rather than moving poses, so there is nothing ``preview_params`` could
    answer — it goes to the accepting path and schedules the same
    settle-time refine.

    A row may carry ``frame: "world"``. That is the pick's own measurement,
    in the only frame a viewport click has; the engine converts it through
    the inverse of that component's placement chain and writes the canonical
    board-frame row back, so the shell never has to know a board's frame.
    """

    return begin_set_tables(scene, boards=rows, cancelled=cancelled)


def begin_set_mounts(scene, rows, cancelled=None):
    """Start a mount-table edit. Returns ``(ok, report)``.

    The fourth table through the one op (ADR-126), on ``begin_set_boards``'s
    terms exactly: a full row list, a ``frame: "world"`` row converted by the
    engine because a viewport click has no other frame to measure in, and the
    single-slot pump driving it to completion so the second mount defined on
    one component is not refused in silence (ADR-122).
    """

    return begin_set_tables(scene, mounts=rows, cancelled=cancelled)


def begin_set_cages(scene, rows, cancelled=None):
    """Start a section-cage edit. Returns ``(ok, report)``.

    The fifth table through the one op (ADR-127), and the one that most
    needs the single-slot pump: a ring drag is a stream of transform events,
    so the overlay accumulates and **Apply** sends the whole table once.
    """

    return begin_set_tables(scene, cages=rows, cancelled=cancelled)


def script_cages(scene):
    """The cage table as the engine holds it: ``(cages, rows)``.

    ``cages`` carries each declared cage's frame — axis, origin, up — which
    is what the overlay needs to put a ring on its spine, and ``rows`` is the
    table Apply replaces wholesale.
    """

    block = _script_block(scene, "cages")
    if block is None:
        return None, None
    return (
        [dict(entry) for entry in list(block.get("cages") or [])
         if isinstance(entry, dict)],
        [dict(row) for row in list(block.get("rows") or []) if isinstance(row, dict)],
    )


def _script_block(scene, key):
    """One block of ``inspect scope="script"``, or None."""

    ok, _report = ensure_open(scene)
    if not ok:
        return None
    payload = _inspect_full(_client(project_root(scene)), "script", "")
    if not isinstance(payload, dict) or payload.get("ok") is False:
        return None
    value = payload.get("value") if isinstance(payload.get("value"), dict) else payload
    block = value.get(key) if isinstance(value, dict) else None
    return block if isinstance(block, dict) else None


def script_mounts(scene):
    """The mount table as the engine holds it: ``(components, rows)``.

    Read through ``inspect scope="script"``, which is where the mount table
    lives beside the parameters — a pick has to know the whole table because
    ``set_params(mounts=...)`` replaces it wholesale.
    """

    block = _script_block(scene, "mounts")
    if block is None:
        return None, None
    return (
        [str(name) for name in list(block.get("components") or [])],
        [dict(row) for row in list(block.get("rows") or []) if isinstance(row, dict)],
    )


def _slider_values(scene, state):
    """Current slider values for the engine's declared parameters."""
    from . import model
    stored = model.stored_values(scene)
    return {str(spec.get("name")): float(stored[str(spec.get("name"))])
            for spec in state.specs
            if str(spec.get("name") or "") in stored}


def _lifecycle(scene, op, args, display=None, guarded=True):
    """Blocking form of :func:`begin_lifecycle`; one code path underneath."""
    started = begin_lifecycle(scene, op, args, display=display,
                              guarded=guarded)
    if not isinstance(started, Lifecycle):
        return started
    return started.wait()


def write_script(scene, source):
    """Replace THE project script through the engine. Returns (ok, report)."""
    ok, report = _lifecycle(scene, "write_script", {"source": source})
    if ok:
        _refresh_script_state(scene)
    else:
        # Keep the attempted source visible, and marked as not in the model.
        mirror_script_text(source, accepted=False)
    return ok, report


def begin_slider_rebuild(scene):
    """Start the slider-drag request. A :class:`Lifecycle`, or (ok, report).

    The non-blocking half of :func:`rebuild_from_sliders`, so the drag pump
    can poll it instead of the main thread sitting inside it for half a
    second per debounce tick.

    ``on_accept`` carries what the blocking form used to do after ``if ok:``
    -- adopt the values and schedule the settled refine -- so both callers
    genuinely share one code path rather than two that agree today.
    """

    ok, report = ensure_open(scene)
    if not ok:
        return False, report
    state = _state_for(project_root(scene))
    if not state.script_present:
        return True, "No project script yet; nothing to rebuild."
    # Read at start time, not at queue time: that is what makes coalescing
    # need no value queue (see note_drag).
    values = _slider_values(scene, state)
    if not values:
        return False, "The project script declares no parameters."

    def accepted():
        state.values.update(values)
        _schedule_refine(scene)

    return begin_lifecycle(scene, "set_params", {"values": values},
                           display=DRAG_DISPLAY, on_accept=accepted)


def rebuild_from_sliders():
    """The slider-drag path: current slider values → one set_params request.

    Called from model.rebuild()'s backend dispatch (background mode, or
    model.set_values() from the set_params tool). Returns (ok, report).
    """
    started = begin_slider_rebuild(bpy_scene())
    if not isinstance(started, Lifecycle):
        return started
    return started.wait()


# -- the drag pump: one in flight, the rest coalesced ------------------------

#: Past this, an in-flight drag is cancelled when a newer one is waiting.
#: Below it the in-flight result is about to arrive and is nearly current,
#: and cancelling would freeze the viewport for another whole round trip;
#: above it a stale request is holding the client lock while the user has
#: already dragged well past the value it is computing.
DRAG_CANCEL_AFTER_SECONDS = 1.0

#: One drag slot **per project root**, the exact twin of ``_refines`` and
#: for the same reason: a drag started in one .blend must never hydrate
#: into another.
_drags = {}


def _drag_slot(root):
    slot = _drags.get(root)
    if slot is None:
        slot = {"lifecycle": None, "queued": False, "superseded": False,
                "started": 0.0, "requests": 0}
        _drags[root] = slot
    return slot


def _supersede_drag(root):
    """Drop a *queued* drag; leave an in-flight one alone.

    Called when the agent starts its own modeling request. The queued drag
    is stale by definition -- the agent is about to move the revision -- and
    a superseded drag is not a failure, so it must not reach
    ``model._last_error`` (ADR-039 state stays in model.py).
    """

    slot = _drags.get(root)
    if slot is not None and slot.get("queued"):
        slot["queued"] = False
        slot["superseded"] = True


def note_drag(scene, on_finish=None):
    """Register a slider change. At most one request in flight per project.

    **Coalescing needs no value queue.** ``begin_slider_rebuild`` reads the
    live PropertyGroup when it *starts*, so restarting after the in-flight
    request completes automatically picks up the newest values and drops
    every intermediate one. A 50-event burst becomes at most one in-flight
    request plus a boolean.
    """

    from . import agent as agent_module

    root = project_root(scene)
    slot = _drag_slot(root)

    # Defer while the agent is mid-turn: otherwise the drag's
    # expected_revision snapshot goes stale behind the agent's write and
    # burns the one-shot retry on every single drag.
    if agent_module.get_agent().busy:
        slot["queued"] = True
        return

    if slot.get("lifecycle") is not None:
        slot["queued"] = True
        return

    _start_drag(scene, root, slot, on_finish)


def _start_drag(scene, root, slot, on_finish=None):
    import bpy

    slot["queued"] = False
    slot["superseded"] = False
    started = begin_slider_rebuild(scene)
    if not isinstance(started, Lifecycle):
        if on_finish is not None:
            on_finish(*started)
        return
    slot["lifecycle"] = started
    slot["started"] = time.monotonic()
    slot["requests"] = int(slot.get("requests") or 0) + 1
    slot["on_finish"] = on_finish

    def pump():
        return _drag_pump(root)

    if not bpy.app.background:
        bpy.app.timers.register(pump, first_interval=0.02)


def _drag_pump(root):
    """Main thread. Poll the in-flight drag; restart for a queued one.

    Modelled on ``_schedule_refine``'s poll, including its re-check of
    ``project_root`` before hydrating: ``Lifecycle.poll`` hydrates
    unconditionally, so a drag that lands after a Save-As must not repaint
    the new file with the old file's geometry.
    """

    import bpy
    from . import agent as agent_module
    from . import model

    slot = _drags.get(root)
    if slot is None:
        return None
    lifecycle = slot.get("lifecycle")
    if lifecycle is None:
        return None

    scene = bpy.context.scene
    if project_root(scene) != root:
        slot["lifecycle"] = None
        slot["queued"] = False
        return None

    # A stale in-flight request holds the client lock while the user drags
    # past it; a nearly-finished one is worth waiting for. See the constant.
    if (slot.get("queued")
            and time.monotonic() - slot["started"] > DRAG_CANCEL_AFTER_SECONDS):
        slot["superseded"] = True

    outcome = lifecycle.poll()
    if outcome is None:
        return 0.02

    ok, report = outcome
    slot["lifecycle"] = None
    superseded = slot.pop("superseded", False)
    on_finish = slot.pop("on_finish", None)

    if ok:
        model.clear_last_error()
    elif not superseded and report:
        # A superseded drag is not a failure and must not be reported as
        # one; anything else is exactly what ADR-039's panel exists for.
        model.record_error(report)
        print("mesh model rebuild failed:\n" + report)
    if on_finish is not None:
        on_finish(ok, report)
    agent_module._tag_redraw()

    if slot.get("queued") and not agent_module.get_agent().busy:
        _start_drag(scene, root, slot)
        return None
    # Settled. The engine killed its preview generation when it accepted
    # this, and a new drag deserves a fresh answer rather than the previous
    # one's latch (ADR-055).
    _clear_preview_latch(root)
    return None


# -- the preview path: in front of the drag, never instead of it -------------

#: ~30 Hz. A 33 ms engine behind the 150 ms debounce would still be a 150 ms
#: drag, so the preview gets its own dispatch: at most one in flight, fired
#: on this interval, intermediate values dropped, **never debounced**
#: (ADR-055). The settle-time ``set_params`` and the standard refine behind
#: it are untouched — the preview rides in front of them, it does not
#: replace them.
PREVIEW_INTERVAL_SECONDS = 1.0 / 30.0

#: One preview slot per project root, like ``_drags`` and ``_refines``.
_previews = {}


def _preview_slot(root):
    slot = _previews.get(root)
    if slot is None:
        slot = {"thread": None, "result": {}, "dirty": False, "pumping": False,
                "latched": False, "latched_for": frozenset(), "reason": "",
                "values": None, "pending_changed": frozenset(),
                "in_flight_changed": frozenset(),
                "requests": 0, "applied": 0, "seconds": []}
        _previews[root] = slot
    return slot


def _accepted_values(state):
    """The model's effective parameter values as accepted.

    ``state.values`` alone is not it: a script that has only ever been
    written carries no stored values at all — the defaults live in its
    ``num()`` declarations and nothing writes them down until a ``set_params``
    does. Falling back to the specs' defaults is the same resolution
    ``_bridge_params`` uses to seed the sliders, which is what makes "this
    slider moved" mean the same thing here as it does there.
    """

    resolved = {}
    for spec in state.specs:
        name = str(spec.get("name") or "")
        if not name:
            continue
        resolved[name] = float(
            (state.values or {}).get(name, spec.get("default") or 0.0)
        )
    return resolved


def note_preview(scene):
    """A slider moved: keep the preview pump running. Cheap and best-effort.

    Called from the property update alongside the debounced rebuild, not
    instead of it. Everything here is an optimisation, so every failure path
    ends in "stop previewing and let the debounce answer" — a preview must
    never reach ``model._last_error``.
    """

    import bpy

    try:
        root = project_root(scene)
        state = _state_for(root)
        if not state.script_present:
            return
        slot = _preview_slot(root)
        values = _slider_values(scene, state)
        if not values:
            return
        # Which sliders moved since the last time we looked. The latch is per
        # parameter: "this slider is not previewable" cannot change while the
        # same slider is being dragged, but it says nothing about the next
        # one. Seeded from the *accepted* values, so the first change of a
        # drag reports the one slider that moved rather than all of them.
        previous = slot.get("values")
        if previous is None:
            previous = _accepted_values(state)
        changed = frozenset(
            name for name in values if previous.get(name) != values[name]
        )
        slot["values"] = dict(values)
        slot["pending_changed"] = slot.get("pending_changed",
                                           frozenset()) | changed
        if slot["latched"] and changed and not (changed <= slot["latched_for"]):
            slot["latched"] = False
            slot["latched_for"] = frozenset()
            slot["reason"] = ""
        slot["dirty"] = True
        if slot["pumping"] or bpy.app.background:
            return
        slot["pumping"] = True
        bpy.app.timers.register(lambda: _preview_pump(root),
                                first_interval=0.0)
    except Exception:
        traceback.print_exc()


def _preview_pump(root):
    """Main thread. Poll the in-flight preview, then start the next one."""

    import bpy

    slot = _previews.get(root)
    if slot is None:
        return None
    try:
        scene = bpy.context.scene
        if project_root(scene) != root:
            slot["pumping"] = False
            return None

        thread = slot.get("thread")
        if thread is not None:
            if thread.is_alive():
                return PREVIEW_INTERVAL_SECONDS
            _finish_preview(scene, root, slot)

        if slot["latched"] or not slot["dirty"]:
            slot["pumping"] = False
            return None
        # The accepting run holds the client's lock, and a preview that
        # blocks on it would land after the answer it was trying to
        # anticipate. Wait a tick.
        if _drag_slot(root).get("lifecycle") is not None:
            return PREVIEW_INTERVAL_SECONDS
        _start_preview(scene, root, slot)
        return PREVIEW_INTERVAL_SECONDS
    except Exception:
        # An optimisation that raises into a timer is worse than no
        # optimisation: stop, say so on the console, leave the debounce to it.
        traceback.print_exc()
        slot["pumping"] = False
        slot["thread"] = None
        slot["latched"] = True
        return None


def _start_preview(scene, root, slot):
    """Send one ``preview_params`` off the main thread.

    Values are read **here**, at start time, which is what drops every
    intermediate one: the same trick that lets the drag pump coalesce without
    a queue.
    """

    state = _state_for(root)
    values = _slider_values(scene, state)
    if not values:
        slot["dirty"] = False
        return
    slot["dirty"] = False
    # What this request is asking about, so a refusal latches the sliders
    # that caused it and not every slider the script declares.
    slot["in_flight_changed"] = slot.get("pending_changed") or frozenset()
    slot["pending_changed"] = frozenset()
    slot["requests"] = int(slot.get("requests") or 0) + 1
    slot["result"] = {}
    result = slot["result"]
    client = _client(root)
    args = {"values": values, "expected_revision": state.revision}
    started = time.monotonic()

    def worker():
        try:
            result["payload"] = client.request("preview_params", args)
        except Exception:
            result["payload"] = {"ok": False, "error": traceback.format_exc()}
        result["seconds"] = time.monotonic() - started

    thread = threading.Thread(target=worker, name="cadex-preview", daemon=True)
    slot["thread"] = thread
    thread.start()


def _finish_preview(scene, root, slot):
    """Main thread. Apply the poses, or latch previews off for this drag."""

    from . import cadex_hydrate

    slot["thread"] = None
    payload = (slot.get("result") or {}).get("payload") or {}
    seconds = float((slot.get("result") or {}).get("seconds") or 0.0)
    slot["seconds"].append(round(seconds, 4))

    if payload.get("ok") is not True or payload.get("previewable") is not True:
        # Latched for the remainder of *this* parameter's drag: the answer
        # cannot change while the same slider is being dragged, so re-asking
        # every 33 ms is pure waste. Never recorded as an error -- the
        # debounced set_params behind this is the real answer (ADR-055).
        slot["latched"] = True
        slot["latched_for"] = (slot.get("in_flight_changed")
                               or frozenset(slot.get("values") or {}))
        slot["reason"] = str(payload.get("reason") or payload.get("error") or "")
        return

    # A preview answered against a revision the model has since left is not
    # wrong, it is late: an accepting run landed while it was in flight and
    # already posed the viewport correctly.
    if str(payload.get("revision") or "") != _state_for(root).revision:
        return
    slot["applied"] += cadex_hydrate.apply_placements(payload.get("placements"))


def preview_stats(root=None, reset=False):
    """``{requests, applied, latched, reason, in_flight, seconds}``. Test-facing."""
    import bpy
    root = root or project_root(bpy.context.scene)
    slot = _preview_slot(root)
    thread = slot.get("thread")
    stats = {
        "requests": int(slot.get("requests") or 0),
        "applied": int(slot.get("applied") or 0),
        "latched": bool(slot.get("latched")),
        "reason": str(slot.get("reason") or ""),
        "in_flight": thread is not None and thread.is_alive(),
        "seconds": list(slot.get("seconds") or []),
    }
    if reset:
        slot.update({"requests": 0, "applied": 0, "seconds": [],
                     "latched": False, "latched_for": frozenset(),
                     "reason": "", "values": None,
                     "pending_changed": frozenset(),
                     "in_flight_changed": frozenset()})
    return stats


def pump_preview_once(root=None):
    """Run one preview-pump tick by hand. Test-facing.

    ``bpy.app.timers`` do not fire under ``--background``, so the gate drives
    the pump itself — the same arrangement ``pump_drag_once`` uses.
    """
    import bpy
    return _preview_pump(root or project_root(bpy.context.scene))


def _clear_preview_latch(root):
    """The drag settled: the next one gets a fresh answer."""
    slot = _previews.get(root)
    if slot is not None:
        slot["latched"] = False
        slot["latched_for"] = frozenset()
        slot["reason"] = ""


def drag_stats(root=None, reset=False):
    """``{requests, queued, in_flight}`` for the gate. Test-facing."""
    import bpy
    root = root or project_root(bpy.context.scene)
    slot = _drag_slot(root)
    stats = {
        "requests": int(slot.get("requests") or 0),
        "queued": bool(slot.get("queued")),
        "in_flight": slot.get("lifecycle") is not None,
    }
    if reset:
        slot["requests"] = 0
    return stats


def pump_drag_once(root=None):
    """Run one drag-pump tick by hand. Test-facing.

    ``bpy.app.timers`` do not fire under ``--background``, so the gate
    drives the pump itself.
    """
    import bpy
    return _drag_pump(root or project_root(bpy.context.scene))


def bpy_scene():
    import bpy
    return bpy.context.scene


# -- post-drag display refinement -------------------------------------------

#: One refine slot **per project root**: a drag burst keeps rescheduling
#: (generation counter); an in-flight refine is cancelled by the next
#: modeling request. Keyed by root because a single global slot let a
#: refine started for one .blend hydrate into whichever project happened to
#: be current when it landed.
_refines = {}


def _refine_slot(root):
    slot = _refines.get(root)
    if slot is None:
        slot = {"generation": 0, "cancel": None}
        _refines[root] = slot
    return slot


def _cancel_refine(root=None):
    """Cancel the in-flight refine for ``root`` (or every root)."""
    slots = ([_refines[root]] if root in _refines
             else [] if root is not None else list(_refines.values()))
    for slot in slots:
        event = slot.get("cancel")
        if event is not None:
            event.set()


def refine_now(scene):
    """Synchronously re-stream the standard tessellation. (ok, report)."""
    ok, report = ensure_open(scene)
    if not ok:
        return False, report
    return _lifecycle(scene, "rebuild", {}, display=DISPLAY_REQUEST,
                      guarded=False)


def _schedule_refine(scene):
    """After a coarse drag settles, refine the display in the background.

    The engine request runs on a worker thread (the client serializes and
    supports mid-run cancel); hydration happens back on the main thread
    via a polling timer. Skipped in background mode (tests drive
    ``refine_now`` explicitly)."""
    import bpy
    if bpy.app.background:
        return
    root = project_root(scene)
    slot = _refine_slot(root)
    slot["generation"] += 1
    generation = slot["generation"]
    scene_name = scene.name

    def fire():
        if slot["generation"] != generation:
            return None  # a newer drag rescheduled the refine
        cancel_event = threading.Event()
        slot["cancel"] = cancel_event
        result = {}

        def worker():
            result["payload"] = _client(root).request(
                "rebuild", {"display": dict(DISPLAY_REQUEST)},
                cancellation_check=cancel_event.is_set)

        thread = threading.Thread(target=worker, name="cadex-refine",
                                  daemon=True)
        thread.start()

        def poll():
            if thread.is_alive():
                return 0.2
            payload = result.get("payload") or {}
            scene_now = bpy.data.scenes.get(scene_name) or bpy.context.scene
            _revision_from_payload(scene_now, payload)
            if (payload.get("ok") is True
                    and slot["generation"] == generation
                    and not cancel_event.is_set()
                    # The project this refine belongs to must still be the
                    # scene's project: Save-As or opening another .blend
                    # between the drag and the refine must not repaint the
                    # new file with the old file's geometry.
                    and project_root(scene_now) == root):
                try:
                    hydrate(payload)
                except Exception:
                    traceback.print_exc()
            return None

        bpy.app.timers.register(poll, first_interval=0.1)
        return None

    bpy.app.timers.register(fire, first_interval=REFINE_DELAY_SECONDS)


def get_script_report(scene):
    """The get_script tool body for the cadex backend.

    Reads on an unrestored project too: rewriting a script you are not
    allowed to read is not a recovery path (ADR-044).
    """
    ok, report = ensure_open(scene, unrestored_ok=True)
    if not ok:
        return False, report
    state = _state_for(project_root(scene))
    from . import model
    source = model.get_script()
    if not state.script_present and not source.strip():
        return True, "(the project script is empty — no model yet)"
    lines = [source]
    if state.values:
        lines.append("\nCurrent parameter values: "
                     + json.dumps(state.values, sort_keys=True))
    lines.append("Engine revision: " + (state.revision or "(none)"))
    if state.restore_warning:
        lines.append("\n" + state.restore_warning)
    return True, "\n".join(lines)


def begin_edit_script(scene, replacements, cancelled=None):
    """Start an ``edit_script``. Returns a :class:`Lifecycle` or (ok, report).

    The engine applies each ``{old, new}`` replacement to THE project
    script under the same revision guard as a full write, and refuses any
    ``old`` that does not occur exactly once. That refusal is the point:
    an ambiguous edit is a bug the model should see, not a coin flip.
    """
    if not isinstance(replacements, list) or not replacements:
        return False, "edit_script needs a non-empty `replacements` array."
    cleaned = []
    for index, item in enumerate(replacements):
        if not isinstance(item, dict) or set(item) != {"old", "new"}:
            return False, ("replacements[{:d}] must have exactly the keys "
                           "old and new.".format(index))
        cleaned.append({"old": str(item["old"]), "new": str(item["new"])})
    return begin_lifecycle(
        scene, "edit_script", {"replacements": cleaned}, cancelled=cancelled,
        on_accept=lambda: _refresh_script_state(scene))


def inspect(scene, args):
    """One engine ``inspect`` request. Returns the payload verbatim.

    ``scope=history`` reads on an unrestored project too: a store the
    restore pass could not prove is exactly when the previous versions are
    worth reading (ADR-045).
    """
    unrestored_ok = str(dict(args).get("scope") or "") == "history"
    ok, report = ensure_open(scene, unrestored_ok=unrestored_ok)
    if not ok:
        return {"ok": False, "error": report}
    return _client(project_root(scene)).request("inspect", dict(args))


def begin_restore_version(scene, selector, cancelled=None):
    """Write a stored version back over the current script (ADR-045).

    Revert is deliberately not a new engine op: a version *is* a script, so
    putting one back is the ``write_script`` that already exists. That keeps
    the round trip honest -- the restored script re-runs, re-publishes and
    is re-accepted like any other, rather than being trusted because it used
    to work.

    ``replace`` is passed because reverting is precisely the case where
    dropping current outputs is intended.
    """
    selector = str(selector).strip()
    if not selector:
        return False, ("Which version? Inspect scope=history for the list.")
    ok, report = ensure_open(scene, unrestored_ok=True)
    if not ok:
        return False, report
    # Through the pager, not a single inspect: any value over 1 KiB comes
    # back as a marker, and a script is always over 1 KiB. Reading `value`
    # directly would restore a stub as if it were the script.
    whole = _inspect_full(_client(project_root(scene)), "history", "",
                          target=selector)
    source = str((whole or {}).get("source") or "") if isinstance(whole, dict) else ""
    if not source.strip():
        return False, (
            "No stored version matches {!r}, or its source could not be "
            "read. Inspect scope=history for the list of versions.".format(
                selector))
    return begin_write_script(scene, source, replace=True, cancelled=cancelled)


def put_asset(scene, source_path, name=""):
    """Copy one STL/OBJ/PLY into the project store. Payload verbatim.

    The shell never writes the store itself (docs/ARCHITECTURE.md), so
    dropping a component into a model is a protocol op like everything else.
    The returned `name` is what the model passes to `mesh.import_file()`.
    """
    ok, report = ensure_open(scene)
    if not ok:
        return {"ok": False, "error": report}
    args = {"source_path": str(source_path)}
    if name:
        args["name"] = str(name)
    return _client(project_root(scene)).request("put_asset", args)


def link_part(scene, source_project, output="", name=""):
    """Pull one accepted solid out of another project. Payload verbatim.

    One op, not an export from there and an import here: *this* project
    pulls, the other one is only read, and it does not have to be open --
    which is what makes this work between two .blend files without either
    window knowing about the other (cadex ADR-138).

    Omitting ``output`` is how the caller asks what that project declares:
    the refusal carries the names in ``candidates``.

    Refreshing is this same call with the same arguments. It does **not**
    rebuild: the caller issues the ordinary rebuild afterwards, so new
    geometry lands as one normal accepted revision with one undo step.
    """
    ok, report = ensure_open(scene)
    if not ok:
        return {"ok": False, "error": report}
    args = {"source_project": str(source_project)}
    if output:
        args["output"] = str(output)
    if name:
        args["name"] = str(name)
    return _client(project_root(scene)).request("link_part", args)


def linked_parts(scene):
    """The ``.cxpart`` containers this project holds, newest listing first.

    Read through ``inspect scope=assets`` rather than off the filesystem,
    because the engine is the store's sole reader (docs/ARCHITECTURE.md) and
    what is importable is its answer, not a directory listing's.
    """
    names = stored_asset_names(scene)
    if names is None:
        return []
    return sorted(name for name in names
                  if str(name).lower().endswith(LINKED_PART_SUFFIX))


def refresh_linked_parts(scene):
    """Re-pull every linked part, then rebuild once if anything moved.

    Returns ``(ok, report)``. A refresh that finds nothing moved rebuilds
    nothing on purpose: a no-op that re-accepted the model would put a
    meaningless revision in the undo trail every time somebody checked.

    The rebuild is the ordinary one, which is what keeps a refresh safe --
    the new geometry lands as one accepted revision, with one undo step, and
    a script that no longer builds against the new shape is refused by name
    rather than leaving a half-updated model.
    """
    names = linked_parts(scene)
    if not names:
        return True, "This model has no linked parts."

    moved, unchanged, refused = [], [], []
    for name in names:
        sources = _linked_part_source(scene, name)
        if not sources:
            refused.append("{:s} (its source project is not recorded)".format(name))
            continue
        source_project, output = sources
        if not os.path.isdir(source_project):
            refused.append(
                "{:s} (the project it came from is no longer at {:s})".format(
                    name, source_project))
            continue
        payload = link_part(scene, source_project, output=output, name=name)
        if payload.get("ok") is not True:
            refused.append("{:s} ({:s})".format(
                name, str(payload.get("error") or "refused")))
        elif payload.get("changed"):
            moved.append("{:s}: {:s} → {:s}".format(
                name,
                str(payload.get("previous_revision") or "?")[:8],
                str(payload.get("source_revision") or "?")[:8]))
        else:
            unchanged.append(name)

    lines = []
    if moved:
        lines.append("Updated: " + "; ".join(moved))
    if unchanged:
        lines.append("Already current: " + ", ".join(unchanged) + ".")
    if refused:
        lines.append("Could NOT refresh: " + "; ".join(refused))
    if not moved:
        return not refused, "\n".join(lines)

    ok, report = rebuild_model(scene)
    if not ok:
        lines.append(
            "The parts were updated, but this model no longer builds against "
            "them: " + str(report or "").splitlines()[0])
        lines.append(
            "Refresh again from the project that owns the part, or fix the "
            "script -- the refusal above names what broke.")
        return False, "\n".join(lines)
    lines.append("Model rebuilt.")
    return not refused, "\n".join(lines)


def _linked_part_source(scene, name):
    """``(source_project, output)`` out of one stored container's header.

    The header is read here rather than asked of the engine because it is
    what the container *is*: a magic line, a length and a JSON object, in a
    file this project owns. Reading fourteen bytes and one object needs no
    round trip and no engine module -- and the path it yields is a **hint**,
    checked by the caller, never trusted (the standing ``SOURCE_PROP`` has).
    """
    path = os.path.join(project_root(scene), "assets", str(name))
    try:
        with open(path, "rb") as handle:
            magic = handle.read(8)
            if magic != b"CXPART1\n":
                return None
            length = int.from_bytes(handle.read(8), "little")
            if not 0 < length <= 4 * 1024 * 1024:
                return None
            header = json.loads(handle.read(length).decode("ascii"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    source = header.get("source") if isinstance(header, dict) else None
    if not isinstance(source, dict):
        return None
    root = str(source.get("project_root") or "")
    output = str(source.get("output") or "")
    if not root or not output:
        return None
    return root, output


def engine_summary(scene):
    """What the engine actually holds, for scene_summary in cadex mode.

    The generic scene_summary walks bpy.data and reports Blender objects.
    In cadex mode those objects are a *display mirror* of engine geometry:
    their names are engine output names but their meshes are tessellations,
    their modifier stacks are empty by construction, and nothing about them
    is the model. Reporting them to the model as "the scene" invites it to
    reason about the mirror. This reports the engine instead.
    """
    ok, report = ensure_open(scene)
    if not ok:
        return False, report
    root = project_root(scene)
    state = _state_for(root)
    client = _client(root)
    summary = {
        "source": "cadex engine (not the Blender scene)",
        "project_root": root,
        "script_present": state.script_present,
        "revision": state.revision,
        "parameters": dict(state.values),
    }
    document = client.request("inspect", {"scope": "document"})
    if document.get("ok") is True:
        summary["document"] = document.get("value")
    script = client.request("inspect", {"scope": "script",
                                        "path": "/revisions"})
    if script.get("ok") is True:
        summary["revisions"] = script.get("value")
    # What external geometry is already staged: the names mesh.import_file()
    # takes. Without this the model has no way to know a component is there.
    assets = client.request("inspect", {"scope": "assets"})
    if assets.get("ok") is True:
        summary["assets"] = assets.get("value")
    summary["viewport_mirror"] = _mirror_note()
    return True, summary


def _mirror_note():
    """What Blender is showing, stated as the mirror it is."""
    try:
        import bpy
        from . import model
        collection = bpy.data.collections.get(model.COLLECTION_NAME)
        names = sorted(obj.name for obj in collection.all_objects) \
            if collection is not None else []
    except Exception:
        names = []
    return {
        "objects": names,
        "note": ("Tessellated display copies of the engine's outputs. Their "
                 "meshes are approximations for the viewport; the model is "
                 "the script and the engine's BREP."),
    }


# -- the engine's authoring contract, served on demand ----------------------

#: describe_api's answer, cached for the session. The API is a property of
#: the engine build, not of a project, so one cache serves every project.
_api_cache = {}

#: Keys of describe_api that describe *how to write a script* rather than
#: which functions exist. Small (about 2 KB together) and always included.
_CONTRACT_KEYS = (
    "engine", "program_schema", "instructions", "source_globals",
    "parameters", "result_contract", "revision_rule", "mutation_selection",
)


def describe_api(scene):
    """The engine's full ``describe_api`` payload, cached. (ok, payload)."""
    if _api_cache.get("payload") is not None:
        return True, _api_cache["payload"]
    ok, report = ensure_open(scene)
    if not ok:
        return False, {"error": report}
    payload = _client(project_root(scene)).request("describe_api")
    if payload.get("ok") is not True:
        return False, payload
    _api_cache["payload"] = payload
    return True, payload


def api_overview(payload):
    """The compact block: the authoring contract + what each domain offers.

    describe_api is ~33 KB, ~31 KB of which is per-function signatures for
    five domains. That cannot go in a system prompt, and pasting a hand-
    written summary there is what produced the drift this replaces. So the
    model gets the contract in full plus, per domain, its output types and
    its function *names* -- enough to know what exists and to ask for the
    one domain it needs.
    """
    overview = {key: payload[key] for key in _CONTRACT_KEYS if key in payload}
    domains = {}
    for name, block in sorted(dict(payload.get("domains") or {}).items()):
        if not isinstance(block, dict):
            continue
        domains[name] = {
            "api_global": block.get("api_global", name),
            "accepted_output_types": block.get("accepted_output_types") or [],
            "functions": sorted(
                str(item.get("name") or "")
                for item in list(block.get("exports") or [])
                if isinstance(item, dict) and item.get("name")),
        }
    overview["domains"] = domains
    overview["how_to_read_this"] = (
        "Each domain is a global in the script (see api_global). This is "
        "the function list only; call describe_cad_api with a domain name "
        "for full signatures, defaults and descriptions before using one "
        "you are unsure of.")
    return overview


def api_domain(payload, domain):
    """One domain's full block, or (False, message) naming the real ones."""
    domains = dict(payload.get("domains") or {})
    block = domains.get(str(domain or ""))
    if block is None:
        return False, ("Unknown domain {!r}. The engine serves: {:s}.".format(
            domain, ", ".join(sorted(domains))))
    return True, block


def _first_sentence(text):
    """The first sentence of a docstring, whitespace-normalised."""
    text = " ".join(str(text or "").split())
    end = text.find(". ")
    return text if end < 0 else text[:end + 1]


def compact_domain(block):
    """One domain's block with every signature but only summary prose.

    A domain's full block is dominated by its docstrings -- `part` is 34 KB
    and `assembly` 54 KB, mostly semantics -- so serving it whole is what
    made the two largest domains unreadable (ADR-123). The compact form
    keeps the contract (which global, which output types, the domain notes)
    and every export's name and signature, and cuts each description to its
    first sentence. The long form is still reachable per function, which is
    the only granularity at which it fits.
    """
    compact = {
        "api_global": block.get("api_global"),
        "accepted_output_types": list(block.get("accepted_output_types") or []),
        "exports": [
            {
                "name": item.get("name"),
                "signature": item.get("signature"),
                "summary": _first_sentence(item.get("description")),
            }
            for item in list(block.get("exports") or [])
            if isinstance(item, dict)
        ],
    }
    notes = block.get("notes")
    if notes:
        compact["notes"] = notes
    compact["how_to_read_this"] = (
        "Signatures are complete; each summary is the first sentence of a "
        "longer description. Call describe_cad_api again with this domain "
        "and functions=[...] for the full description of the ones you are "
        "about to use.")
    return compact


def api_functions(block, names):
    """Full, untouched entries for named exports of one domain block.

    (True, [entry, ...]) or (False, message) naming the miss, in the style
    api_domain uses for an unknown domain.
    """
    exports = {}
    for item in list(block.get("exports") or []):
        if isinstance(item, dict) and item.get("name"):
            exports[str(item["name"])] = item
    picked = []
    for name in names:
        entry = exports.get(str(name))
        if entry is None:
            return False, (
                "Unknown function {!r} in {!s}. That domain exports: "
                "{:s}.".format(name, block.get("api_global"),
                               ", ".join(sorted(exports))))
        picked.append(entry)
    return True, picked


def resolve_pin(scene, output, selection):
    """Resolve one pick/selection against the accepted BREP. Returns the
    engine's response payload verbatim (ok/failure envelope)."""
    ok, report = ensure_open(scene)
    if not ok:
        return {"ok": False, "error": report}
    client = _client(project_root(scene))
    return client.request(
        "resolve_pin", {"output": str(output), "selection": dict(selection)})


def close_all():
    """Drop every engine session: children, cached state, pending refines."""
    _cancel_refine()
    cadexd_client.close_all()
    _states.clear()
    _refines.clear()
    _wirings.clear()


def open_roots():
    """Project roots this session currently holds engine state for."""
    return sorted(_states)


def scene_remembers_a_model(scene):
    """Does the .blend itself still carry a model the engine has lost?

    The specs cache and the ``model.py`` mirror both save with the file, so
    either one is enough to rebuild the project from what is in front of us.
    """
    from . import model
    try:
        if model.load_specs(scene):
            return True
        return bool((model.get_script() or "").strip())
    except Exception:
        return False


def orphaned_project(scene):
    """This file names an engine project with no script in it.

    Two ways to know, and both are needed. Once the project is open,
    ``script_present`` comes over the protocol and is authoritative --
    ``os.path.isdir`` is useless by then, because ``open_project`` creates
    the root it was handed.

    Before any open there is no state to ask, and Save-As leaves exactly
    that gap: ``on_file_changed`` drops every session a moment after the new
    name takes effect, so the file that most needs the offer -- the one just
    saved under a new name -- was the only one that never got it. The chat's
    "Rebuild From Saved Script" button was unreachable until something else
    happened to open the project, and the status line that would have said
    so does not survive a new conversation. Whether the root *exists* is not
    store knowledge: the shell is what chooses it (:func:`project_root`).
    """
    try:
        root = project_root(scene)
    except Exception:
        return False
    state = _states.get(root)
    if state is None or not state.opened:
        empty = not os.path.isdir(root)
    else:
        empty = not state.script_present
    # Last, and only when it can change the answer: this one parses the
    # saved specs, and it runs on every panel draw.
    return empty and scene_remembers_a_model(scene)


def begin_rebuild_model(scene, cancelled=None):
    """Start a full re-run of the *stored* script. Lifecycle or (ok, report).

    The way out when the model in the viewport and the engine have drifted --
    a script the engine holds but this file never hydrated, a slider group
    built from stale declarations, or (before ADR-039) a store whose values
    outlived their parameters. It re-derives everything from the engine's own
    stored source, so it sends no source from the shell and cannot itself be
    the thing that is stale.

    ``guarded=False`` is not optional: ``rebuild``'s ``OP_ARG_SPECS`` entry is
    ``({}, {"display": dict})`` and rejects ``expected_revision`` -- which is
    right, because re-running what is stored has nothing to be stale against.
    """
    def accepted():
        # The point of the operation: whatever the shell believed about specs,
        # values and source is replaced by what the engine just re-derived.
        _refresh_script_state(scene)
        from . import model
        model.clear_last_error()

    return begin_lifecycle(scene, "rebuild", {}, display=DISPLAY_REQUEST,
                           guarded=False, cancelled=cancelled,
                           on_accept=accepted)


def rebuild_model(scene):
    """Blocking :func:`begin_rebuild_model`. Returns (ok, report)."""
    started = begin_rebuild_model(scene)
    if not isinstance(started, Lifecycle):
        return started
    return started.wait()


def apply_slider_defaults(scene):
    """Write the current slider values into the script as the new defaults.

    The sliders are an override layer over what the script declares: move one
    and the value lives in the store, while `num(36.0, ...)` in the source still
    says 36. This collapses the layer -- each declared parameter's default
    becomes the value the slider is sitting at, in the script itself, which is
    the artifact that gets committed and diffed.

    Rewritten from the **engine's** source, not the buffer, so the button does
    exactly one thing; a hand-edited buffer is refused rather than swept along,
    because `write_script` refreshes the mirror and would take the edits with it.

    The geometry does not move: the store keeps its parameter values, and a
    stored value shadows the default it was just written from, so the rebuild
    this triggers computes the same shapes and reports the same content digest.
    That also absorbs the rounding in `model.format_default` -- the literal in
    the script is the readable form of the value, not the value being built.
    Returns (ok, report).
    """
    from . import model

    ok, report = ensure_open(scene)
    if not ok:
        return False, report
    state = _state_for(project_root(scene))
    if not state.script_present or not state.source:
        return False, "There is no project script to set defaults on yet."
    if model.script_is_dirty():
        return False, ("The script buffer has unapplied edits. Apply or revert "
                       "them first, then set the defaults.")
    values = model.get_values(scene)
    if not values:
        return False, "The project script declares no parameters."
    try:
        source, changes = model.rewrite_defaults(state.source, values)
    except ValueError as exc:
        return False, str(exc)
    if not changes:
        return True, "Every parameter default already matches its slider."
    ok, report = write_script(scene, source)
    if not ok:
        return False, report
    return True, "{:s}\n{:s}".format(
        report,
        "\n".join("{:s}: {:s} -> {:s}".format(name, old, new)
                  for name, old, new in changes))


def stored_asset_names(scene):
    """Names ``mesh.import_file`` can already resolve here, or None if unknown.

    Over the protocol, because what the engine will stage is the engine's
    answer to give. None means the question could not be asked -- an
    unopenable project -- and the caller should carry everything rather than
    assume the project is empty.
    """
    ok, _report = ensure_open(scene)
    if not ok:
        return None
    payload = _client(project_root(scene)).request("inspect", {"scope": "assets"})
    if payload.get("ok") is not True:
        return None
    value = payload.get("value") or {}
    return {str(entry.get("name") or "")
            for entry in list(value.get("assets") or [])}


def migrate_assets(scene):
    """Carry the previous project's imported geometry into this one.

    Save-As mints a new project root and carries nothing across. For
    everything the engine *derives* -- staged artifacts, accepted revisions,
    the undo trail -- that is the right answer, and ADR-043's Save-As note
    says why: they are reproducible from the script, and copying them would
    fork a model's history behind the user's back. Assets are not derived.
    They are inputs the user supplied, the script names them by name, and a
    script that imports one cannot run at all without it -- so "re-run the
    saved script into a new project" was never a recovery for any model
    built on external geometry. It failed on the first import (ADR-046).

    Every file goes in through ``put_asset``, one at a time: cadexd stays
    the sole writer of the store, so the 64-file / 128 MB budget is enforced
    where it is defined and nothing can land half-copied under its final
    name. Returns (ok, report); ``ok`` is False only if a file was refused,
    and the report is "" when there was nothing to carry.
    """
    origin = source_root(scene)
    if not origin:
        return True, ""
    sources = _assets_in(origin)
    if not sources:
        return True, ""
    have = stored_asset_names(scene)
    carried, refused = [], []
    for path in sources:
        name = os.path.basename(path)
        if have is not None and name in have:
            continue
        payload = put_asset(scene, path, name=name)
        if payload.get("ok") is True:
            carried.append(name)
        else:
            refused.append("{:s} ({:s})".format(
                name, str(payload.get("error") or "refused")))
    lines = []
    if carried:
        lines.append("Carried {:d} imported file(s) over from {:s}: {:s}.".format(
            len(carried), os.path.basename(origin), ", ".join(carried)))
    if refused:
        lines.append("Could NOT carry: " + "; ".join(refused))
    return not refused, "\n".join(lines)


def adopt_saved_script(scene):
    """Rebuild this file's engine project from the script saved in the .blend.

    For the duplicated / Save-As'd file: the new project root is empty, but
    the file still carries the script mirror. Writing it back through the
    normal ``write_script`` path gives the new project its own accepted
    revision and digest -- a genuine sibling of the original, not a copy of
    its artifacts. Returns (ok, report).

    The imported geometry comes across first (:func:`migrate_assets`),
    because the script cannot run without it. A refusal there is reported
    but not fatal: the write is still attempted, and if the missing file was
    one the script needs, the engine names it -- which is a better error
    than anything this function could invent.
    """
    from . import model
    source = (model.get_script() or "").strip()
    if not source:
        return False, "This file carries no saved script to adopt."
    _ok, carried = migrate_assets(scene)
    ok, report = write_script(scene, source)
    if carried:
        report = carried + "\n" + report
    return ok, report


def on_file_changed(scene=None):
    """A different .blend is now current: file load, or Save-As.

    Returns a status line for the chat when this file has no engine project,
    else "". Every cadexd child is closed and all cached engine state is
    dropped, so the next request opens the project the current file actually
    names -- rather than reusing the child that was spawned for the previous
    one.

    The old ``.cadex`` directory is deliberately **not** copied to the new
    name. Copying an engine project on Save-As would duplicate BREP
    artifacts behind the user's back and silently fork the model's history;
    saying what happened and offering to re-run the saved script is the
    honest option. Its *imported geometry* is the exception, and comes
    across when the script is adopted (:func:`migrate_assets`, ADR-046):
    assets are inputs, not derived state, and the script cannot re-run
    without them.

    The check is on the *current* file, not on whether some previous root
    happened to be open. Gating on that missed the commonest case entirely:
    duplicate a .blend in the file manager, open it in a fresh session, and
    there is no previous root to compare against.
    """
    previous = [root for root in open_roots() if os.path.isdir(root)]
    close_all()
    if scene is None:
        return ""
    try:
        current = project_root(scene)
    except Exception:
        return ""
    if os.path.isdir(current) or not scene_remembers_a_model(scene):
        return ""
    stale = [root for root in previous
             if os.path.abspath(root) != os.path.abspath(current)]
    where = (" The original model stays in {:s}.".format(
        os.path.basename(stale[0])) if stale else "")
    return ("This file has no engine project yet ({:s}).{:s} Press "
            "\"Rebuild From Saved Script\" to re-run the script saved in this "
            "file into a new project; any geometry you imported comes across "
            "with it. The original's revision history stays where it is.".format(
                os.path.basename(current), where))


# -- live mode (ADR-109) -----------------------------------------------------

# Three thin passes to the client, deliberately thin. Everything that makes
# live mode a session -- the clock, the frame queue, the poses, the push --
# is in `cadex_live`, and everything physical is on the far side of the
# process boundary. What is left here is that live mode reaches the engine
# through the same client, the same registry and the same per-project child
# as every other op, rather than through a second route.


def live_open(root, args):
    """Start a live session on the accepted rollout. Never raises for the
    ordinary refusals: a project with no rollout answers `live: false`."""
    return _client(root).request("live_open", dict(args or {}))


def live_step(root, args):
    """Advance the running episode and take the frames it produced.

    Called from `cadex_live`'s pump thread, one at a time. It queues behind
    an in-flight modeling request rather than refusing one, which is what a
    read op does and what keeps watching the mechanism compatible with
    changing it.
    """
    return _client(root).request("live_step", dict(args or {}))


def live_close(root):
    """End the session. Idempotent, so every teardown path may call it."""
    return _client(root).request("live_close", {})


def register():
    pass


def unregister():
    close_all()
