# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Mesh app template: clean viewport on the left, full-height chat column on the
right.

Launch with: blender --app-template Mesh

There is no curated startup.blend yet; the factory startup is reshaped in
Python shortly after load:
- extra workspaces removed, the remaining one renamed "Simple"
- every screen area closed except the 3D viewport, which is then split 50/50
  with a Properties editor pinned to the Tool tab — that editor hosts the chat
  panel as a full-height column (other tool-tab panels are hidden)
- a parameters area split off the bottom of the viewport: a second Properties
  editor on the same Tool tab, headerless, hosting the parameter sliders and
  nothing else (the two panels sort themselves out by area — see
  ``mesh_agent.ui._column_role``). It is an area rather than a panel in the
  chat column so the user can close and reopen it; the chat input bar carries
  the toggle. Opening it lives in the add-on
  (``mesh_agent.ui.open_params_area``) because the toggle operator needs the
  same code.
- scene emptied, grid floor off, axis lines kept

All of this runs from a deferred, retrying timer because neither the add-on
search paths nor the window layout are ready while startup is still running.
A hand-authored startup.blend can replace the layout part in Phase 2.
"""

import bpy
from bpy.app.handlers import persistent

# Panels that make up the chat column and the parameters area; everything
# else in the Tool category gets hidden.
MESH_PANELS = {"VIEW3D_PT_mesh_chat", "VIEW3D_PT_mesh_params"}

# Original poll functions of foreign panels hidden in Simple mode, kept for
# the Phase 2 Pro-mode toggle to restore.
_hidden_panel_polls = {}

# Original draw functions of headers overridden in Simple mode (topbar menus,
# properties header), likewise kept for the Pro-mode restore.
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


def _all_panel_classes():
    stack = [bpy.types.Panel]
    seen = set()
    while stack:
        for sub in stack.pop().__subclasses__():
            if sub not in seen:
                seen.add(sub)
                stack.append(sub)
                yield sub


def _hide_foreign_tool_panels():
    """Hide the other "Tool"-category panels (Active Tool options, Workspace,
    Custom Properties, ...) that the Properties editor's Tool tab mirrors, so
    the chat column and the parameters area stay clean."""
    for cls in list(_all_panel_classes()):
        if (getattr(cls, "bl_space_type", None) != 'VIEW_3D'
                or getattr(cls, "bl_region_type", None) != 'UI'
                or getattr(cls, "bl_category", "") != "Tool"
                or cls.__name__ in MESH_PANELS
                or cls in _hidden_panel_polls):
            continue
        try:
            # Poll is captured at registration, so re-register to change it.
            bpy.utils.unregister_class(cls)
            _hidden_panel_polls[cls] = cls.__dict__.get("poll")
            cls.poll = classmethod(lambda _cls, _context: False)
            bpy.utils.register_class(cls)
        except Exception:
            _hidden_panel_polls.pop(cls, None)


def _reregister_with_draw(cls, draw):
    # Like poll, draw is captured at registration time, so re-register.
    bpy.utils.unregister_class(cls)
    cls.draw = draw
    bpy.utils.register_class(cls)


def _override_headers():
    """Blank out the top menu bar and turn the Properties header into the
    chat input bar (the header region itself is flipped to the bottom of the
    area in _style_props)."""
    if "topbar" not in _ui_overrides:
        cls = bpy.types.TOPBAR_HT_upper_bar
        _ui_overrides["topbar"] = cls.draw

        def _draw_nothing(_self, _context):
            pass

        _reregister_with_draw(cls, _draw_nothing)
    if "props_header" not in _ui_overrides:
        from mesh_agent import ui as mesh_ui
        cls = bpy.types.PROPERTIES_HT_header
        _ui_overrides["props_header"] = cls.draw
        _reregister_with_draw(cls, mesh_ui.draw_chat_input_header)


def _style_props(window, area):
    """Flip the header (the chat input bar) to the bottom of the chat column
    and hide the tab icon strip; the tabs live in a header dropdown instead."""
    screen = window.screen
    header = next((r for r in area.regions if r.type == 'HEADER'), None)
    if header is not None and header.alignment != 'BOTTOM':
        with bpy.context.temp_override(window=window, screen=screen,
                                       area=area, region=header):
            bpy.ops.screen.region_flip()
    nav = next((r for r in area.regions if r.type == 'NAVIGATION_BAR'), None)
    if nav is not None and nav.width > 1:
        with bpy.context.temp_override(window=window, screen=screen,
                                       area=area, region=nav):
            bpy.ops.screen.region_toggle(region_type='NAVIGATION_BAR')


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
    """Timer callback, running a small state machine over several ticks:
    collapse to a single viewport, split it, then assign the right half to the
    chat column. Multiple ticks are required because area geometry (x/width)
    only updates between redraws, and right after the startup file loads the
    windows aren't fully realized at all (operator polls fail). Each tick
    re-derives the current state, so failed steps retry naturally."""
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
        import os
        _debug = bool(os.environ.get("MESH_TEMPLATE_DEBUG"))
        if _debug:
            print("mesh-template tick", _attempts[0], "win", len(bpy.context.window_manager.windows),
                  "screen", screen.name, types,
                  [(a.type, getattr(a.spaces.active, "type", "?"), a.x, a.width)
                   for a in screen.areas])

        if types == ['PROPERTIES', 'VIEW_3D']:
            # Final state reached; make sure the chat column is on the right.
            # Snapshot the areas once: every access to screen.areas creates
            # fresh Python wrappers, so identity checks are only valid within
            # a single snapshot.
            areas = list(screen.areas)
            right = max(areas, key=lambda area: area.x)
            left = next(area for area in areas if area is not right)
            if right.type != 'PROPERTIES':
                # Swap sides; space data updates on the next tick, so re-enter.
                if _debug:
                    print("mesh-template: swapping sides")
                _set_area_type(window, right, 'PROPERTIES')
                _set_area_type(window, left, 'VIEW_3D')
                return 0.1
            if getattr(left.spaces.active, "type", "") != 'VIEW_3D':
                # Area type changed but its space data hasn't caught up yet.
                if _debug:
                    print("mesh-template: left space lagging:",
                          "left", left.type, repr(left.spaces.active),
                          "right", right.type, repr(right.spaces.active))
                _set_area_type(window, left, 'VIEW_3D')
                return 0.1
            if _debug:
                print("mesh-template: finalizing")
            try:
                right.spaces.active.context = 'TOOL'
            except (AttributeError, TypeError) as ex:
                if _debug:
                    print("mesh-template: tool tab failed:", ex)
            _empty_scene()
            _hide_foreign_tool_panels()
            _override_headers()
            _style_viewport(window, left)
            _style_props(window, right)
            # Last, so the two-area checks above are done with: this adds a
            # third area under the viewport. It finishes on its own timer.
            from mesh_agent import ui as mesh_ui
            mesh_ui.open_params_area(window)
            _applied[0] = True
            if _debug:
                print("mesh-template: applied")
            return None

        if types == ['VIEW_3D', 'VIEW_3D']:
            # Fresh split: turn one half into the chat column; next tick (with
            # settled geometry) verifies it ended up on the right.
            _set_area_type(window,
                           max(screen.areas, key=lambda area: area.x),
                           'PROPERTIES')
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
