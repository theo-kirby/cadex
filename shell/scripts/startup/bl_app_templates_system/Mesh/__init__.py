# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Mesh app template: clean viewport on the left, chat editor on the right,
parameters under the viewport.

Launch with: blender --app-template Mesh

The three columns are three *editors* now (ADR-035), so the layout is finally
expressible as a saved screen -- which it was not while they were Properties
editors told apart by geometry. There is still no curated startup.blend, so
the factory startup is reshaped in Python shortly after load:

- extra workspaces removed, the remaining one renamed "Simple"
- every area closed except the 3D viewport, which is then split 50/50 with a
  Cadex Chat editor
- a Cadex Parameters editor split off the bottom of the viewport, one tick
  later: two ``screen.area_split`` calls cannot share a tick, because area
  geometry only refreshes between redraws (ADR-034)
- scene emptied, viewport chrome off, top bar blanked

All of it runs from a deferred, retrying timer because neither the add-on
search paths nor the window layout are ready while startup is still running.
"""

import bpy
from bpy.app.handlers import persistent

# Original draw functions of headers overridden in Simple mode, kept for the
# Pro-mode restore.
_ui_overrides = {}


def _ensure_agent_addon():
    # Must run deferred: addon paths aren't registered yet while the app
    # template's own register() executes during startup.
    import addon_utils
    try:
        addon_utils.enable("mesh_agent", default_set=False)
    except Exception:
        import traceback
        traceback.print_exc()


def _remove_other_workspaces(window):
    keep = window.workspace
    doomed = [workspace for workspace in bpy.data.workspaces
              if workspace != keep]
    if doomed:
        bpy.data.batch_remove(doomed)
    if keep.name != "Simple":
        keep.name = "Simple"


def _collapse_to_viewport(window):
    """Close every area except the largest 3D viewport."""
    screen = window.screen
    for _ in range(32):
        areas = list(screen.areas)
        if len(areas) <= 1:
            break
        viewports = [area for area in areas if area.type == 'VIEW_3D']
        keep = max(viewports or areas, key=lambda area: area.width * area.height)
        target = next((area for area in areas if area is not keep), None)
        if target is None:
            break
        try:
            with bpy.context.temp_override(window=window, screen=screen,
                                           area=target):
                bpy.ops.screen.area_close()
        except Exception:
            break


def _empty_scene():
    if bpy.data.objects:
        bpy.data.batch_remove(list(bpy.data.objects))


def _reregister_with_draw(cls, draw):
    # Like poll, draw is captured at registration time, so re-register.
    bpy.utils.unregister_class(cls)
    cls.draw = draw
    bpy.utils.register_class(cls)


def _blank_topbar():
    """Blank the top menu bar.

    There is no saved-screen equivalent: `bScreen.flag` carries
    SCREEN_COLLAPSE_STATUSBAR but no topbar counterpart, so this cannot move
    into a startup.blend.
    """
    if "topbar" in _ui_overrides:
        return
    cls = bpy.types.TOPBAR_HT_upper_bar
    _ui_overrides["topbar"] = cls.draw

    def _draw_nothing(_self, _context):
        pass

    _reregister_with_draw(cls, _draw_nothing)


def _set_area_type(window, area, area_type):
    # Area type changes need a window in the context; from a bare timer the
    # assignment appears to succeed but the space data never switches.
    with bpy.context.temp_override(window=window, screen=window.screen,
                                   area=area):
        area.type = area_type


def _style_viewport(window, area):
    space = area.spaces.active
    # Region-visibility updates need a full window context; timers run
    # without one, so provide it explicitly or the update crashes.
    with bpy.context.temp_override(window=window, screen=window.screen,
                                   area=area):
        space.show_region_ui = False
        space.show_region_tool_header = False
        space.show_region_toolbar = False
        space.show_region_header = False
        space.overlay.show_overlays = False
        space.shading.type = 'SOLID'
        space.shading.light = 'MATCAP'
        try:
            space.shading.studio_light = 'toon_light.exr'
        except TypeError:
            # Matcap not bundled in this build; keep the default.
            pass


_attempts = [0]
_applied = [False]


def _apply_simple_ui():
    """Timer callback, running a small state machine over several ticks.

    Each tick re-derives the current state from the area types on the screen,
    so a step that failed simply retries. Multiple ticks are required because
    area geometry only updates between redraws, and right after the startup
    file loads the windows are not fully realized at all (operator polls
    fail).
    """
    if _applied[0]:
        return None
    _attempts[0] += 1
    if _attempts[0] > 40:
        return None
    try:
        _ensure_agent_addon()
        window = bpy.context.window_manager.windows[0]
        screen = window.screen
        types = sorted(area.type for area in screen.areas)

        if types == ['CADEX_CHAT', 'CADEX_PARAMS', 'VIEW_3D']:
            viewport = next(a for a in screen.areas if a.type == 'VIEW_3D')
            _empty_scene()
            _blank_topbar()
            _style_viewport(window, viewport)
            _applied[0] = True
            return None

        if types == ['CADEX_CHAT', 'VIEW_3D']:
            # Split the parameters off the viewport. This is the second split
            # and it gets a tick of its own -- see the module docstring.
            viewport = next(a for a in screen.areas if a.type == 'VIEW_3D')
            before = {a.as_pointer() for a in screen.areas}
            with bpy.context.temp_override(window=window, screen=screen,
                                           area=viewport):
                bpy.ops.screen.area_split(direction='HORIZONTAL', factor=0.3)
            fresh = [a for a in screen.areas if a.as_pointer() not in before]
            if fresh:
                _set_area_type(window, fresh[0], 'CADEX_PARAMS')
            return 0.1

        if types == ['VIEW_3D', 'VIEW_3D']:
            # Fresh split: the right half becomes the chat editor.
            _set_area_type(window,
                           max(screen.areas, key=lambda area: area.x),
                           'CADEX_CHAT')
            return 0.1

        _remove_other_workspaces(window)
        _collapse_to_viewport(window)
        if len(screen.areas) == 1 and screen.areas[0].type == 'VIEW_3D':
            with bpy.context.temp_override(window=window, screen=screen,
                                           area=screen.areas[0]):
                bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
            return 0.1
    except Exception:
        import traceback
        traceback.print_exc()
    return 0.2


@persistent
def load_handler(_):
    if bpy.app.background:
        return
    _attempts[0] = 0
    _applied[0] = False
    if not bpy.app.timers.is_registered(_apply_simple_ui):
        bpy.app.timers.register(_apply_simple_ui, first_interval=0.3)


def register():
    bpy.app.handlers.load_factory_startup_post.append(load_handler)


def unregister():
    if load_handler in bpy.app.handlers.load_factory_startup_post:
        bpy.app.handlers.load_factory_startup_post.remove(load_handler)
