# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Mesh app template: clean viewport top-left (the landing screen on a fresh
launch, ADR-167), Cadex Chat as the right third of the window, and Cadex
Parameters beside an Outliner under the viewport (ADR-168).

Launch with: blender --app-template Mesh

**The layout is `startup.blend`, not code.** It became expressible as a saved
screen when the chat and parameter columns became real editor types (ADR-035):
a saved screen can only record area *types*, and until then the area types
were lying -- all three columns were Properties editors, told apart at draw
time by comparing their coordinates. What used to be a 340-line retrying timer
state machine that split areas, monkeypatched two header draw functions and
re-registered every foreign Tool panel with `poll -> False` is now a file, and
this module is what is left over (ADR-037).

Two things survive, because neither can live in a .blend:

- **Enabling the add-on.** `preferences.addons` is `UserDef`, not `Main`, so a
  startup file cannot carry it. Shipping a `Mesh/userpref.blend` would work
  and would also pin the user's theme, paths, keymap and autosave -- so this
  stays four lines of Python instead.
- **Suppressing the splash** (ADR-042). It is a `UserDef` flag, and the one
  thing here that has to run in the load handler rather than the timer --
  `creator.c` reads the flag immediately after `WM_init`.

To re-author the layout: launch, arrange it by hand, `File > Defaults > Save
Startup File`, then copy
`<config>/Mesh/startup.blend` over the one beside this file. Do it in one
commit -- every re-save is a new git-LFS object and the old one is never
reclaimed.
"""

import bpy
from bpy.app.handlers import persistent


def _ensure_agent_addon():
    # Must run deferred: add-on paths are not registered yet while the app
    # template's own register() executes during startup.
    import addon_utils
    try:
        addon_utils.enable("mesh_agent", default_set=False)
    except Exception:
        import traceback
        traceback.print_exc()


def _hide_splash():
    """No Blender splash on startup (ADR-042).

    Must run from the handler rather than the timer: the check is
    `U.uiflag & USER_SPLASH_DISABLE` in `wm_init_splash_show_on_startup_check`
    (`wm_init_exit.cc`), read from `creator.cc` right after `WM_init` -- which
    is after this handler and long before any timer fires.

    The dirty flag is put back deliberately. Preferences auto-save on exit
    when dirty, and this is the product deciding what it launches into, not
    the user editing a preference: writing it into `userpref.blend` would
    reach through the shared profile into stock Blender sessions too. It costs
    nothing to re-apply, because this runs on every startup.
    """
    preferences = bpy.context.preferences
    if not preferences.view.show_splash:
        return
    was_dirty = preferences.is_dirty
    preferences.view.show_splash = False
    preferences.is_dirty = was_dirty


def _apply():
    try:
        _ensure_agent_addon()
    except Exception:
        import traceback
        traceback.print_exc()
    return None


@persistent
def load_handler(_):
    if bpy.app.background:
        return
    _hide_splash()
    if not bpy.app.timers.is_registered(_apply):
        bpy.app.timers.register(_apply, first_interval=0.1)


def register():
    bpy.app.handlers.load_factory_startup_post.append(load_handler)


def unregister():
    if load_handler in bpy.app.handlers.load_factory_startup_post:
        bpy.app.handlers.load_factory_startup_post.remove(load_handler)
