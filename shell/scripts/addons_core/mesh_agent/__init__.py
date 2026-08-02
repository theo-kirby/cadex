# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Mesh Agent: chat-driven scene building, powered by Claude Code.

The assistant runs `claude -p` (the user's installed Claude Code CLI, using
their existing login) and drives the live Blender session through a curated
tool set exposed over MCP. See agent.py for the threading model.
"""

bl_info = {
    "name": "Mesh Agent",
    "description": "Chat assistant that builds and edits the scene",
    "author": "Mesh",
    "version": (0, 1),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Mesh",
    "support": "OFFICIAL",
    "category": "3D View",
}

import bpy
from bpy.app.handlers import persistent

from . import agent as agent_module
from . import cadex_backend as cadex_backend_module
from . import cadex_live as cadex_live_module
from . import cadex_pick as cadex_pick_module
from . import cadex_terminal_pick as cadex_terminal_pick_module
from . import cadex_training as cadex_training_module
from . import model as model_module
from . import spaces
from . import wiring as wiring_module
from . import wiring_ui as wiring_ui_module
from . import topbar as topbar_module
from . import ui


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


class MeshAgentPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    model: bpy.props.EnumProperty(
        name="Model",
        description="Claude model used by the assistant",
        items=(
            ('claude-fable-5', "Fable (most capable)", "Best quality, newest model"),
            ('claude-opus-4-8', "Opus", "High quality"),
            ('claude-sonnet-4-6', "Sonnet (balanced)", "Good quality, faster"),
            ('claude-haiku-4-5', "Haiku (fastest)", "Snappy simple edits"),
        ),
        default='claude-fable-5',
    )
    claude_path: bpy.props.StringProperty(
        name="Claude Code Path",
        description="Path to the `claude` CLI binary (leave empty to auto-detect)",
        subtype='FILE_PATH',
        default="",
    )
    max_tool_calls: bpy.props.IntProperty(
        name="Tool Call Limit",
        description="Maximum tool calls the assistant may make in one turn",
        default=agent_module.DEFAULT_TOOL_CAP,
        min=1, max=200,
    )
    freecadcmd_path: bpy.props.StringProperty(
        name="Cadex Engine (FreeCADCmd)",
        description="Leave empty to use the cadex engine bundled with Mesh. "
                    "Set this only to point Cadex mode at a different engine "
                    "build, e.g. when developing the engine itself",
        subtype='FILE_PATH',
        default="",
    )

    engine_timeout_seconds: bpy.props.FloatProperty(
        name="Engine Timeout (s)",
        description="Wall-clock budget for one cadex engine script run. "
                    "0 leaves the engine's own default in force",
        default=0.0, min=0.0, max=3600.0,
    )
    engine_memory_limit_mb: bpy.props.IntProperty(
        name="Engine Memory (MB)",
        description="Memory ceiling for one cadex engine script run. "
                    "0 leaves the engine's own default in force",
        default=0, min=0, max=131072,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "model")
        layout.prop(self, "claude_path")
        layout.prop(self, "max_tool_calls")
        layout.prop(self, "freecadcmd_path")
        budgets = layout.row(align=True)
        budgets.prop(self, "engine_timeout_seconds")
        budgets.prop(self, "engine_memory_limit_mb")

        # Resolved engine row: what Cadex mode will actually run, and why
        # not when it cannot. Same wording as the chat panel and the tool
        # error, so one problem reads as one problem.
        ok, reason, remedy = cadex_backend_module.preflight()
        engine = layout.column(align=True)
        if ok:
            resolved, _module = cadex_backend_module.resolved_engine()
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

        column = layout.column()
        column.label(
            text="Uses your Claude Code login; run `claude` once in a "
                 "terminal to sign in.", icon='INFO')
        if not bpy.app.online_access:
            column.label(
                text="Online access is disabled in Preferences > System > Network.",
                icon='ERROR')


@persistent
def _save_pre_handler(_filepath):
    agent_module.get_agent().save_state()
    # Last moment before the write, and bpy.data.filepath still names the
    # OLD file here, so this is the only point at which a Save-As can record
    # which project currently holds the model -- and the value lands inside
    # the file being written, so a duplicate opened in a fresh session knows
    # it too (ADR-046).
    try:
        cadex_backend_module.remember_source_root(bpy.context.scene)
    except Exception:
        pass


@persistent
def _save_post_handler(_filepath):
    # Save-As renames the file, and the engine project root is derived from
    # the file name: the child spawned for the old root is no longer this
    # file's engine. Drop it, and say so if the model was left behind.
    _report_file_change()


@persistent
def _load_post_handler(_filepath):
    agent_module.get_agent().load_state()
    # Restore parameter sliders from the specs saved in the scene.
    model_module.on_load()
    # A different file is current; its engine project is a different one.
    # Without this, opening a second .blend leaks the first file's cadexd
    # child and can answer from the wrong project store.
    _report_file_change()


#: Cadex editors whose contents depend on `scene.frame_current`. Parameters
#: is deliberately absent: a slider does not move with the timeline.
_FRAME_DRIVEN_EDITORS = frozenset({'CADEX_POLICY', 'CADEX_LIVE'})


@persistent
def _frame_change_handler(*_args):
    # The Policy Outputs bars are drawn from `scene.frame_current`, and
    # `match_region_with_redraws` (screen_ops.cc) has no case for any Cadex
    # space type: playback tags the 3D viewport and leaves these editors
    # showing whichever frame they last drew. Adding those cases would be
    # `docs/BLENDER-TREE.md` §2b lines against inherited Blender; tagging
    # from the add-on is free and does the same job. That trade survived
    # ADR-108 unchanged -- four more editors is four more strings here, and
    # still zero lines in screen_ops.cc.
    #
    # Tag only -- no property writes. A frame-change handler that assigned
    # to the scene would re-enter the depsgraph on every frame of playback.
    try:
        windows = bpy.context.window_manager.windows
    except Exception:
        return
    for window in windows:
        screen = getattr(window, "screen", None)
        if screen is None:
            continue
        for area in screen.areas:
            if area.type in _FRAME_DRIVEN_EDITORS:
                area.tag_redraw()


def _report_file_change():
    try:
        scene = bpy.context.scene
    except Exception:
        scene = None
    try:
        note = cadex_backend_module.on_file_changed(scene)
    except Exception:
        return
    if note:
        agent_module.get_agent().history.add("status", note)


classes = (
    MeshAgentPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    model_module.register()
    cadex_backend_module.register()
    cadex_pick_module.register()
    cadex_terminal_pick_module.register()
    cadex_training_module.register()
    wiring_module.register()
    ui.register()
    spaces.register()
    # Registers the menus; the app template is what puts them on the bar
    # (topbar.install), so a stock Blender session keeps its own top bar.
    topbar_module.register()
    # Last, and the only one allowed to stand down: a Panel or Header
    # naming an unregistered space type raises "Region not found in
    # space type" and aborts the whole registration loop, which is how
    # the top-bar menus once disappeared (ADR-036). On a bundle built
    # before ADR-066 re-registered the node editor, this leaves
    # EDITOR_AVAILABLE False and everything else working.
    wiring_ui_module.register()
    # ...and live mode, for the same reason and the same way:
    # its panels name CADEX_LIVE, and an add-on loaded against
    # a bundle built before ADR-108 would otherwise take the
    # whole registration loop down with it.
    cadex_live_module.register()
    bpy.app.handlers.save_pre.append(_save_pre_handler)
    bpy.app.handlers.save_post.append(_save_post_handler)
    bpy.app.handlers.load_post.append(_load_post_handler)
    bpy.app.handlers.frame_change_post.append(_frame_change_handler)


def unregister():
    if _save_pre_handler in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(_save_pre_handler)
    if _save_post_handler in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(_save_post_handler)
    if _load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_post_handler)
    if _frame_change_handler in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(_frame_change_handler)
    cadex_live_module.unregister()
    wiring_ui_module.unregister()
    topbar_module.unregister()
    spaces.unregister()
    ui.unregister()
    wiring_module.unregister()
    cadex_training_module.unregister()
    cadex_terminal_pick_module.unregister()
    cadex_pick_module.unregister()
    cadex_backend_module.unregister()
    model_module.unregister()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    agent_module.shutdown_agent()
