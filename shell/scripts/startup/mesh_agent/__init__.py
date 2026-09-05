# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
The Cadex assistant: chat-driven model building, run by an agent CLI.

The assistant runs the user's installed agent CLI (Claude Code by default,
using their existing login) and drives the live session through a curated
tool set exposed over MCP. See agent.py for the threading model.

**Application code, not an add-on** (ADR-183). This package lives in
``scripts/startup``, so Blender's script loader imports it and calls
``register()`` at every launch -- background and ``--factory-startup``
included -- exactly as it does ``bl_ui``. There is no ``bl_info``, nothing
to enable, and nothing in the Add-ons list: the assistant is the product,
and a product is not optional. Its settings live in ``prefs.py`` -- a JSON
file of our own plus the AI section of the Preferences window -- not in
``AddonPreferences``, which only exists for add-ons.

Two consequences of registering this early, both handled here:

- ``keyconfigs.addon`` does not exist yet (``WM_keyconfig_init`` runs after
  the script loader), so the landing screen's and the drawings editor's
  keymap items are installed by a deferred timer below rather than in their
  ``register()``.
- The test harnesses re-register the package from source after unloading
  the bundled copy, so ``register()``/``unregister()`` are idempotent.
"""

import bpy
from bpy.app.handlers import persistent

from . import agent as agent_module
from . import cadex_backend as cadex_backend_module
from . import cadex_blueprint as cadex_blueprint_module
from . import cadex_drawings as cadex_drawings_module
from . import cadex_live as cadex_live_module
from . import cadex_pick as cadex_pick_module
from . import cadex_explode as cadex_explode_module
from . import cadex_landing as cadex_landing_module
from . import cadex_section as cadex_section_module
from . import cadex_terminal_pick as cadex_terminal_pick_module
from . import cadex_views as cadex_views_module
from . import cadex_wire_path as cadex_wire_path_module
from . import cadex_training as cadex_training_module
from . import cadex_training_plot as cadex_training_plot_module
from . import model as model_module
from . import prefs as prefs_module
from . import spaces
from . import wiring as wiring_module
from . import wiring_ui as wiring_ui_module
from . import topbar as topbar_module
from . import ui


@persistent
def _save_pre_handler(filepath):
    agent_module.get_agent().save_state()
    # Last moment before the write, and bpy.data.filepath still names the
    # OLD file here, so this is the only point at which a Save-As can record
    # which project currently holds the model -- and the value lands inside
    # the file being written, so a duplicate opened in a fresh session knows
    # it too (ADR-046). The destination is handed to us, and it has to be
    # passed on: without it every ordinary save looks like a Save-As and
    # overwrites the hint with the file's own root (ADR-155).
    try:
        cadex_backend_module.remember_source_root(bpy.context.scene, filepath)
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
    # A real file replacing the startup scene takes the landing screen down
    # (ADR-167); the startup file itself leaves it alone.
    cadex_landing_module.on_file_loaded()


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


def _install_keymaps():
    """Deferred keymap install, retried until the addon keyconfig exists.

    ``keyconfigs.addon`` is created by ``WM_keyconfig_init``, which runs
    after the script loader has already called this package's ``register()``
    (``wm_init_exit.cc``). Registering the items from a timer is the same
    trade the Mesh app template makes for its own late work, and both
    installers are idempotent, so a session re-register costs nothing.
    """
    from . import cadex_drawings
    from . import cadex_landing
    done = cadex_landing.install_keymaps()
    done = cadex_drawings.install_keymaps() and done
    return None if done else 0.1


#: True while this package is registered. The script loader registers it at
#: every launch; the test harnesses unregister that copy and register their
#: own from source. Idempotence is what makes both callers safe.
_registered = False


def register():
    global _registered
    if _registered:
        return
    _registered = True
    prefs_module.register()
    model_module.register()
    cadex_backend_module.register()
    cadex_pick_module.register()
    # The view registry first (ADR-150): collision and dimensions are
    # installed here because they own no register() of their own; section,
    # explode and blueprint add themselves from theirs, below.
    cadex_views_module.install()
    # The section view owns one PropertyGroup on the scene and nothing else
    # (ADR-148); registering it before ui.py is what lets a panel draw it.
    cadex_section_module.register()
    # The exploded view owns one PropertyGroup on the scene and nothing else
    # (ADR-149), on the section view's exact terms and for the same reason
    # here: before ui.py, so a panel can draw it.
    cadex_explode_module.register()
    # ...and the blueprint view (ADR-150), the fifth of the kind and the
    # first registered through cadex_views rather than hand-wired.
    cadex_blueprint_module.register()
    # The stored-drawings browser rides the blueprint's settings group
    # (ADR-177), so it registers right after it.
    cadex_drawings_module.register()
    cadex_terminal_pick_module.register()
    cadex_wire_path_module.register()
    cadex_training_module.register()
    cadex_training_plot_module.register()
    wiring_module.register()
    ui.register()
    spaces.register()
    # The file operators the native menu bar calls (ADR-166); the File and
    # Edit menus themselves are the OS's, built in GHOST_SystemCocoa.mm.
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
    # The landing screen last of all (ADR-167): it names no space type, so
    # it cannot take the loop down, and its register is what decides whether
    # this session opens onto the start page.
    cadex_landing_module.register()
    bpy.app.handlers.save_pre.append(_save_pre_handler)
    bpy.app.handlers.save_post.append(_save_post_handler)
    bpy.app.handlers.load_post.append(_load_post_handler)
    bpy.app.handlers.frame_change_post.append(_frame_change_handler)
    # At launch the addon keyconfig does not exist yet; in a session
    # re-register it does and the timer resolves on its first tick. No
    # timer in background -- there is no event loop to run it and no
    # input for a keymap to catch.
    if not bpy.app.background:
        if not bpy.app.timers.is_registered(_install_keymaps):
            bpy.app.timers.register(_install_keymaps, first_interval=0.0)


def unregister():
    global _registered
    if not _registered:
        return
    _registered = False
    if bpy.app.timers.is_registered(_install_keymaps):
        bpy.app.timers.unregister(_install_keymaps)
    if _save_pre_handler in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(_save_pre_handler)
    if _save_post_handler in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(_save_post_handler)
    if _load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_post_handler)
    if _frame_change_handler in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(_frame_change_handler)
    cadex_landing_module.unregister()
    cadex_live_module.unregister()
    # The dimension overlay owns a draw handler and nothing else, so it needs
    # teardown but no registration (ADR-139). A handle left behind outlives
    # the module it points into and raises on the next reload.
    from . import cadex_dimension as _cadex_dimension_module
    _cadex_dimension_module.unregister()
    wiring_ui_module.unregister()
    topbar_module.unregister()
    spaces.unregister()
    ui.unregister()
    wiring_module.unregister()
    cadex_training_plot_module.unregister()
    cadex_training_module.unregister()
    cadex_wire_path_module.unregister()
    cadex_terminal_pick_module.unregister()
    cadex_drawings_module.unregister()
    cadex_blueprint_module.unregister()
    cadex_explode_module.unregister()
    cadex_section_module.unregister()
    cadex_views_module.uninstall()
    cadex_pick_module.unregister()
    cadex_backend_module.unregister()
    model_module.unregister()
    prefs_module.unregister()
    agent_module.shutdown_agent()
