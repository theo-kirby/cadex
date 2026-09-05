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

One thing survives, because it cannot live in a .blend:

- **Suppressing the splash** (ADR-042). It is a `UserDef` flag that has to
  be set from the load handler -- `creator.c` reads the flag immediately
  after `WM_init`.

The add-on enable that used to sit beside it is gone (ADR-183): the
assistant is application code in `scripts/startup/mesh_agent` now, registered
by the script loader like `bl_ui`, so there is nothing to enable.

To re-author the layout: launch, arrange it by hand, `File > Defaults > Save
Startup File`, then copy
`<config>/Mesh/startup.blend` over the one beside this file. Do it in one
commit -- every re-save is a new git-LFS object and the old one is never
reclaimed.
"""

import bpy
from bpy.app.handlers import persistent


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


@persistent
def load_handler(_):
    if bpy.app.background:
        return
    _hide_splash()


def register():
    bpy.app.handlers.load_factory_startup_post.append(load_handler)


def unregister():
    if load_handler in bpy.app.handlers.load_factory_startup_post:
        bpy.app.handlers.load_factory_startup_post.remove(load_handler)
