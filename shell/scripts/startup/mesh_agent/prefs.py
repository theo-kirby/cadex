# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The application's AI settings: their store, and their Preferences panel.

Cadex is an application, not an add-on, so its settings do not live in
``AddonPreferences`` (ADR-183). They live in a JSON file in the app's own
config directory, mirrored into a ``PropertyGroup`` on the WindowManager so
the Preferences window can draw them with ordinary ``layout.prop`` rows.
Every edit writes the file; the file is read once per session.

The panel registers into the **AI** section of the Preferences window —
a real entry on the left rail (``USER_SECTION_AI``; the C side is one enum
value and one RNA row, see ``docs/BLENDER-TREE.md`` §2b). ``bl_context`` is
the lowercased RNA identifier, which is how the Preferences editor homes
panels; nothing here says *where* the section sits — the RNA array does.
"""

import json
import os
import queue
import threading
import time

import bpy
from bpy.types import Menu, Operator, Panel, PropertyGroup

from . import harness

from .agent import (DEFAULT_CODEX_MODEL, DEFAULT_MODEL, DEFAULT_PI_MODEL,
                    DEFAULT_PROVIDER)

SETTINGS_BASENAME = "cadex_agent.json"

#: True while ``load`` is writing values into the group, so the per-property
#: update callbacks do not write the file back out once per field.
_loading = False
_loaded = False


def settings_path():
    return os.path.join(
        bpy.utils.user_resource('CONFIG', create=True), SETTINGS_BASENAME)


def _save(_self=None, _context=None):
    """Persist the group to disk. Doubles as every property's ``update``."""
    if _loading:
        return
    group = _group()
    if group is None:
        return
    data = {key: getattr(group, key) for key in _KEYS}
    try:
        with open(settings_path(), "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1, sort_keys=True)
    except OSError:
        # A read-only config dir loses persistence, not the session.
        pass


def load():
    """Read the file into the group. Unknown keys and stale enum values --
    a provider from an older build, say -- are dropped rather than raised:
    a settings file must never be able to break the app that wrote it."""
    global _loading, _loaded
    group = _group()
    if group is None:
        return
    _loaded = True
    try:
        with open(settings_path(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return
    if not isinstance(data, dict):
        return
    _loading = True
    try:
        for key in _KEYS:
            if key in data:
                try:
                    setattr(group, key, data[key])
                except (TypeError, ValueError):
                    pass
    finally:
        _loading = False


def _group():
    try:
        return bpy.context.window_manager.cadex_agent_settings
    except AttributeError:
        return None


def get():
    """The settings, loaded on first use. ``agent.get_prefs`` serves this."""
    if not _loaded:
        load()
    return _group()


class CadexAgentSettings(PropertyGroup):
    """One property per setting; names are the API the rest of the add-on
    reads (``get_prefs().provider`` and so on), unchanged from the
    AddonPreferences they replace."""

    provider: bpy.props.EnumProperty(
        name="Harness",
        description="Which agent CLI (and its subscription) runs the "
                    "assistant. Each drives the same Mesh tools; switching "
                    "starts a fresh conversation",
        items=(
            ('claude', "Claude Code",
             "Uses your Claude subscription via the `claude` CLI"),
            ('codex', "Codex",
             "Uses your ChatGPT subscription via the `codex` CLI"),
            ('pi', "pi",
             "Uses your pi install and whichever providers it is "
             "configured for"),
        ),
        default=DEFAULT_PROVIDER,
        update=_save,
    )
    model: bpy.props.StringProperty(
        name="Model", description="Claude model ID; empty uses the harness default",
        default=DEFAULT_MODEL, update=_save,
    )
    codex_model: bpy.props.StringProperty(
        name="Model", description="Codex model ID; empty uses the harness default",
        default=DEFAULT_CODEX_MODEL, update=_save,
    )
    claude_path: bpy.props.StringProperty(
        name="Claude Code Path",
        description="Path to the `claude` CLI binary (leave empty to auto-detect)",
        subtype='FILE_PATH',
        default="",
        update=_save,
    )
    codex_path: bpy.props.StringProperty(
        name="Codex Path",
        description="Path to the `codex` CLI binary (leave empty to auto-detect)",
        subtype='FILE_PATH',
        default="",
        update=_save,
    )
    pi_model: bpy.props.StringProperty(
        name="Model",
        description="pi model pattern, e.g. \"openrouter/moonshotai/kimi-k2.6\" "
                    "or \"*sonnet*\" (leave empty to use pi's own default "
                    "model)",
        default=DEFAULT_PI_MODEL,
        update=_save,
    )
    pi_path: bpy.props.StringProperty(
        name="pi Path",
        description="Path to the `pi` CLI binary (leave empty to auto-detect, "
                    "including nvm installs)",
        subtype='FILE_PATH',
        default="",
        update=_save,
    )
    freecadcmd_path: bpy.props.StringProperty(
        name="Cadex Engine (FreeCADCmd)",
        description="Leave empty to use the cadex engine bundled with the "
                    "app. Set this only to point at a different engine "
                    "build, e.g. when developing the engine itself",
        subtype='FILE_PATH',
        default="",
        update=_save,
    )
    engine_timeout_seconds: bpy.props.FloatProperty(
        name="Engine Timeout (s)",
        description="Wall-clock budget for one cadex engine script run. "
                    "0 leaves the engine's own default in force",
        default=0.0, min=0.0, max=3600.0,
        update=_save,
    )
    engine_memory_limit_mb: bpy.props.IntProperty(
        name="Engine Memory (MB)",
        description="Memory ceiling for one cadex engine script run. "
                    "0 leaves the engine's own default in force",
        default=0, min=0, max=131072,
        update=_save,
    )


_KEYS = tuple(CadexAgentSettings.__annotations__)


def _wrap_remedy(text, width=64):
    """Break the remedy sentence into label-sized lines (labels don't wrap)."""
    lines, current = [], ""
    for word in str(text or "").split():
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    return lines


# Snapshots are keyed by both harness and configured executable. Workers return
# plain data; only the timer touches Blender. No synchronous subprocess in draw.
_snapshots = {}
_pending = {}
_results = queue.Queue()
_logins = {}


def _key(prefs):
    return prefs.provider, getattr(prefs, prefs.provider + "_path", "")


def _redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {'PREFERENCES', 'CADEX_CHAT'}:
                area.tag_redraw()


def _pump():
    changed = False
    while True:
        try:
            key, token, result = _results.get_nowait()
        except queue.Empty:
            break
        if _pending.get(key) is not token:
            continue
        del _pending[key]
        _snapshots[key] = dict(result, checked=time.monotonic())
        changed = True
    for key, directory in list(_logins.items()):
        done = os.path.join(directory.name, 'done')
        if os.path.exists(done):
            directory.cleanup()
            del _logins[key]
            _snapshots.pop(key, None)
            _refresh(key)
            changed = True
    if changed:
        _redraw()
    return 0.25 if _pending or _logins else None


def _timer():
    if not bpy.app.timers.is_registered(_pump):
        bpy.app.timers.register(_pump, first_interval=0.25)


def _refresh(key):
    if key in _pending or key in _logins or not bpy.app.online_access:
        return
    token = object()
    _pending[key] = token
    # Capture this queue so a worker from an unregistered copy cannot publish
    # into a newly registered session.
    results = _results
    def work():
        results.put((key, token, harness.discover(*key)))
    threading.Thread(target=work, daemon=True, name="cadex-harness-discovery").start()
    _timer()


def snapshot(prefs):
    key = _key(prefs)
    result = _snapshots.get(key)
    if key not in _logins and (result is None or time.monotonic() - result['checked'] > 60):
        _refresh(key)
    return result


def model_unavailable(prefs):
    state = _snapshots.get(_key(prefs))
    selected = getattr(prefs, harness.MODEL_PROPERTIES[prefs.provider], '')
    return bool(selected and state and not state['error'] and
                selected not in {row[0] for row in state['models']})


def draw_model(layout, prefs):
    state = snapshot(prefs)
    selected = getattr(prefs, harness.MODEL_PROPERTIES[prefs.provider])
    label = 'Harness default'
    if selected:
        label = next((name for ident, name, _ in (state or {}).get('models', [])
                      if ident == selected), selected + ' (unavailable)' if state and not state['error'] else selected)
    layout.menu('CADEX_MT_harness_models', text=label)


def draw_account(layout, prefs, compact=False):
    state = snapshot(prefs)
    key = _key(prefs)
    if compact:
        layout.popover(panel='CADEX_PT_harness_account', text='', icon='USER')
        return
    column = layout.column(align=True)
    label = (state or {}).get('account', 'Checking account…')
    if not bpy.app.online_access and state is None:
        label = 'Online access disabled'
    for line in label.splitlines():
        column.label(text=line, icon='USER')
    if state and state['error']:
        for line in _wrap_remedy(state['error']):
            column.label(text=line, icon='ERROR')
    if key in _logins:
        column.label(text='Finish sign-in in Terminal, then close the harness.')
        if prefs.provider == 'pi':
            column.label(text='Use /login in pi to choose a provider.')
        column.operator('mesh_agent.harness_login_done', text="I've finished signing in")
    row = column.row(align=True)
    row.enabled = bpy.app.online_access
    login_row = row.row(align=True)
    login_row.enabled = key not in _logins
    login_row.operator('mesh_agent.harness_login', text='Sign in / Switch account', icon='USER')
    refresh_row = row.row(align=True)
    refresh_row.enabled = key not in _pending
    refresh_row.operator('mesh_agent.harness_refresh', text='Checking…' if key in _pending else 'Refresh', icon='FILE_REFRESH')


class CADEX_PT_harness_account(Panel):
    bl_space_type = 'CADEX_CHAT'
    bl_region_type = 'HEADER'
    bl_label = 'Harness account'

    def draw(self, context):
        prefs = get()
        if prefs is not None:
            draw_account(self.layout, prefs)


class CADEX_MT_harness_models(Menu):
    bl_label = 'Models available through this harness'
    bl_options = {'SEARCH_ON_KEY_PRESS'}

    def draw(self, context):
        prefs = get()
        if prefs is None:
            return
        state = snapshot(prefs)
        key = _key(prefs)
        rows = [('', 'Harness default', '')] + (state or {}).get('models', [])
        for ident, name, _description in rows:
            op = self.layout.operator('mesh_agent.harness_model', text=name)
            op.model = ident
            op.provider, op.path = key
        if state and state['error']:
            self.layout.label(text='Models unavailable — check Settings > AI', icon='ERROR')
        self.layout.separator()
        self.layout.operator('mesh_agent.harness_refresh', text='Refresh models', icon='FILE_REFRESH')


class MESH_AGENT_OT_harness_model(Operator):
    bl_idname = 'mesh_agent.harness_model'
    bl_label = 'Select model'
    model: bpy.props.StringProperty()
    provider: bpy.props.StringProperty()
    path: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, properties):
        state = _snapshots.get((properties.provider, properties.path), {})
        return next((description for ident, _name, description in state.get('models', [])
                     if ident == properties.model), 'Use the harness configured default')

    def execute(self, context):
        prefs = get()
        key = (self.provider, self.path)
        state = _snapshots.get(key, {})
        if prefs is None or _key(prefs) != key:
            return {'CANCELLED'}
        if self.model and self.model not in {row[0] for row in state.get('models', [])}:
            self.report({'WARNING'}, 'Model is no longer available. Refresh the models.')
            return {'CANCELLED'}
        setattr(prefs, harness.MODEL_PROPERTIES[self.provider], self.model)
        _redraw()
        return {'FINISHED'}


class MESH_AGENT_OT_harness_refresh(Operator):
    bl_idname = 'mesh_agent.harness_refresh'
    bl_label = 'Refresh account and models'

    def execute(self, context):
        prefs = get()
        if prefs is None or not bpy.app.online_access:
            return {'CANCELLED'}
        _refresh(_key(prefs))
        return {'FINISHED'}


class MESH_AGENT_OT_harness_login_done(Operator):
    bl_idname = 'mesh_agent.harness_login_done'
    bl_label = 'Finish sign-in and refresh'
    bl_description = 'Refresh after signing in or closing the Terminal window'

    def execute(self, context):
        prefs = get()
        if prefs is None:
            return {'CANCELLED'}
        key = _key(prefs)
        directory = _logins.pop(key, None)
        if directory:
            directory.cleanup()
        _snapshots.pop(key, None)
        _refresh(key)
        _redraw()
        return {'FINISHED'}


class MESH_AGENT_OT_harness_login(Operator):
    bl_idname = 'mesh_agent.harness_login'
    bl_label = 'Sign in to harness'
    bl_description = 'Open the selected harness in Terminal to sign in; Cadex refreshes when it exits'

    def execute(self, context):
        prefs = get()
        if prefs is None or not bpy.app.online_access:
            return {'CANCELLED'}
        key = _key(prefs)
        if key in _logins:
            return {'CANCELLED'}
        try:
            _logins[key] = harness.login(*key)
        except harness.DiscoveryError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        _snapshots.pop(key, None)
        _pending.pop(key, None)
        _timer()
        _redraw()
        return {'FINISHED'}


class USERPREF_PT_cadex_ai(Panel):
    """The AI section's one panel: assistant, model, paths, engine."""

    bl_space_type = 'PREFERENCES'
    bl_region_type = 'WINDOW'
    bl_context = "ai"
    bl_label = "AI Assistant"

    def draw(self, context):
        layout = self.layout
        prefs = get()
        if prefs is None:
            return

        layout.prop(prefs, "provider")
        draw_model(layout, prefs)
        draw_account(layout, prefs)
        layout.prop(prefs, prefs.provider + "_path")
        column = layout.column()
        if not bpy.app.online_access:
            column.label(
                text="Online access is disabled in Preferences > System > Network.",
                icon='ERROR')


class USERPREF_PT_cadex_engine(Panel):
    """The engine half of the AI section: override, budgets, and the
    resolved-engine row — what the app will actually run, and why not
    when it cannot. Same wording as the chat panel and the tool error,
    so one problem reads as one problem."""

    bl_space_type = 'PREFERENCES'
    bl_region_type = 'WINDOW'
    bl_context = "ai"
    bl_label = "Engine"

    def draw(self, context):
        from . import cadex_backend
        layout = self.layout
        prefs = get()
        if prefs is None:
            return

        layout.prop(prefs, "freecadcmd_path")
        budgets = layout.row(align=True)
        budgets.prop(prefs, "engine_timeout_seconds")
        budgets.prop(prefs, "engine_memory_limit_mb")

        ok, reason, remedy = cadex_backend.preflight()
        engine = layout.column(align=True)
        if ok:
            resolved, _module = cadex_backend.resolved_engine()
            engine.label(text="Cadex engine: " + (resolved or "found"),
                         icon='CHECKMARK')
        else:
            row = engine.row()
            row.alert = True
            row.label(text=reason, icon='ERROR')
            for line in _wrap_remedy(remedy):
                sub = engine.row()
                sub.enabled = False
                sub.label(text=line)


classes = (
    CadexAgentSettings,
    CADEX_MT_harness_models,
    CADEX_PT_harness_account,
    MESH_AGENT_OT_harness_model,
    MESH_AGENT_OT_harness_refresh,
    MESH_AGENT_OT_harness_login,
    MESH_AGENT_OT_harness_login_done,
    USERPREF_PT_cadex_ai,
    USERPREF_PT_cadex_engine,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.cadex_agent_settings = bpy.props.PointerProperty(
        type=CadexAgentSettings)


def unregister():
    global _loaded, _results
    _loaded = False
    if bpy.app.timers.is_registered(_pump):
        bpy.app.timers.unregister(_pump)
    _snapshots.clear()
    _pending.clear()
    _results = queue.Queue()
    for directory in _logins.values():
        directory.cleanup()
    _logins.clear()
    del bpy.types.WindowManager.cadex_agent_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
