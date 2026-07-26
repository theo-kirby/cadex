# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Mesh app template: clean viewport on the left, Cadex Chat on the right,
Cadex Parameters under the viewport.

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
- **The top bar.** It carries the Cadex File and Edit menus rather than
  Blender's six (`mesh_agent.topbar`, ADR-041). A header's draw function is
  code, not screen data, so no `.blend` can carry it -- and the swap belongs
  to the product shell rather than to the add-on, so that `mesh_agent` in a
  stock Blender session leaves that session's top bar alone.

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


def _cadex_topbar():
    # Must run after the add-on is enabled: the menus the bar draws are
    # registered by `mesh_agent.register()`.
    from mesh_agent import topbar
    topbar.install()


def _apply():
    try:
        _ensure_agent_addon()
        _cadex_topbar()
    except Exception:
        import traceback
        traceback.print_exc()
    return None


@persistent
def load_handler(_):
    if bpy.app.background:
        return
    if not bpy.app.timers.is_registered(_apply):
        bpy.app.timers.register(_apply, first_interval=0.1)


def register():
    bpy.app.handlers.load_factory_startup_post.append(load_handler)


def unregister():
    if load_handler in bpy.app.handlers.load_factory_startup_post:
        bpy.app.handlers.load_factory_startup_post.remove(load_handler)
