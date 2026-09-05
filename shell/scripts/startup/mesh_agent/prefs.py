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

import bpy
from bpy.types import Panel, PropertyGroup

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
    a model id from an older build, say -- are dropped rather than raised:
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
        name="Assistant",
        description="Which agent CLI (and its subscription) runs the "
                    "assistant. Each drives the same Mesh tools; switching "
                    "starts a fresh conversation",
        items=(
            ('claude', "Claude Code (Anthropic)",
             "Uses your Claude subscription via the `claude` CLI"),
            ('codex', "Codex (OpenAI)",
             "Uses your ChatGPT subscription via the `codex` CLI"),
            ('pi', "pi (multi-provider)",
             "Uses your pi install and whichever providers it is "
             "configured for"),
        ),
        default=DEFAULT_PROVIDER,
        update=_save,
    )
    model: bpy.props.EnumProperty(
        name="Model",
        description="Claude model used by the assistant",
        items=(
            ('claude-fable-5', "Fable (default)", "Most capable, newest model"),
            ('claude-opus-5', "Opus", "High quality"),
            ('claude-sonnet-4-6', "Sonnet (balanced)", "Good quality, faster"),
            ('claude-haiku-4-5', "Haiku (fastest)", "Snappy simple edits"),
        ),
        default=DEFAULT_MODEL,
        update=_save,
    )
    codex_model: bpy.props.EnumProperty(
        name="Model",
        description="OpenAI model used by the assistant",
        items=(
            ('gpt-5.5', "GPT-5.5 (default)", "Best quality"),
            ('gpt-5.4', "GPT-5.4", "Good quality"),
            ('gpt-5.4-mini', "GPT-5.4 mini (fastest)", "Snappy simple edits"),
        ),
        default=DEFAULT_CODEX_MODEL,
        update=_save,
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
        # One model picker and one path field at a time — the ones that
        # belong to the chosen assistant.
        if prefs.provider == 'codex':
            layout.prop(prefs, "codex_model")
            layout.prop(prefs, "codex_path")
        elif prefs.provider == 'pi':
            layout.prop(prefs, "pi_model")
            layout.prop(prefs, "pi_path")
        else:
            layout.prop(prefs, "model")
            layout.prop(prefs, "claude_path")

        column = layout.column()
        if prefs.provider == 'codex':
            column.label(
                text="Uses your ChatGPT login; run `codex` once in a "
                     "terminal to sign in.", icon='INFO')
        elif prefs.provider == 'pi':
            column.label(
                text="Uses your pi providers; run `pi` once in a terminal "
                     "to configure them.", icon='INFO')
        else:
            column.label(
                text="Uses your Claude Code login; run `claude` once in a "
                     "terminal to sign in.", icon='INFO')
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
    USERPREF_PT_cadex_ai,
    USERPREF_PT_cadex_engine,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.cadex_agent_settings = bpy.props.PointerProperty(
        type=CadexAgentSettings)


def unregister():
    global _loaded
    _loaded = False
    del bpy.types.WindowManager.cadex_agent_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
