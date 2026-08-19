# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Draw the model as white lines on a drawing-office background.

A blueprint is how engineering shapes have been *read* for a century: light
outlines on a flat dark ground, no shading to mistake for geometry, a grid to
carry scale. This module restyles the viewport that way — solids in one flat
theme colour, every object silhouetted in white, the true BREP edge wires
(the ``<output> Edges`` children ``cadex_hydrate`` already draws) in white
over them, on a blueprint-blue, cutting-mat-green or grey ground.

**It is a view, not a feature** (the ADR-148 shape, exactly, and the first
view registered through ``cadex_views`` rather than hand-wired — ADR-150).
Nothing here reaches the engine, nothing is written to the script, and the
accepted revision is the same revision with the blueprint on as with it off.
What it changes is ``space.shading`` and ``space.overlay`` — per-viewport
draw state, no object and no mesh touched, which is why it layers over the
section and the exploded view by construction: a sectioned or exploded
blueprint is just those views drawn in this style.

The one non-obvious dependency, measured in the draw engine rather than
assumed: the Edges wires are drawn by the *overlay* wireframe pass
(``overlay_wireframe.hh`` skips every wire object when overlays are off), so
this view must switch ``overlay.show_overlays`` ON — the product look keeps
it off — and therefore explicitly holds every sub-overlay it does not want
at False. Any sub-overlay missing from :func:`shading_values` would appear
uninvited. ``wireframe_color_type='OBJECT'`` makes those wires white for
free because no module writes ``obj.color`` (objects default to white); the
collision cage's wires ride the same rule and go white under a blueprint,
which is cosmetic and accepted.

The pure half — everything above ``-- the bpy half --`` — imports no
``bpy``. The themes and the exact field table are what the gate asserts,
and the half Phase 12 keeps.
"""

#: On the scene while the blueprint is on: the report the panel draws from.
SCENE_FLAG = "cadex_blueprint"

#: The look this view replaced, captured once when it switches on and
#: restored when it switches off. On the scene so it survives a save and a
#: reopen with the blueprint on.
SAVED_KEY = "cadex_blueprint_saved"

#: Grid spacing, in model units (mm).
GRID_MM = 10.0

DEFAULT_THEME = "blueprint"

#: RGB 3-tuples — viewport shading colors are RGB in RNA, not RGBA.
#: ``background`` is the ground, ``solid`` the one flat colour every solid is
#: drawn in (readable against the ground, never competing with the lines),
#: ``line`` the outline and wire colour.
THEMES = {
    "blueprint": {
        "background": (0.032, 0.082, 0.230),
        "solid": (0.070, 0.150, 0.350),
        "line": (1.0, 1.0, 1.0),
    },
    "cutting_mat": {
        "background": (0.045, 0.170, 0.130),
        "solid": (0.080, 0.245, 0.190),
        "line": (1.0, 1.0, 1.0),
    },
    "grey": {
        "background": (0.125, 0.125, 0.125),
        "solid": (0.235, 0.235, 0.235),
        "line": (1.0, 1.0, 1.0),
    },
}

#: The startup product look, as the gate pins it (SOLID / MATCAP / overlays
#: off) plus stock defaults for every other field this view touches. The
#: fallback only: :func:`clear` restores the captured look, and reaches for
#: this table when there is nothing captured to restore — a file saved by an
#: older build, or a snapshot lost to hand-editing.
PRODUCT_LOOK = {
    "shading.type": 'SOLID',
    "shading.light": 'MATCAP',
    "shading.color_type": 'MATERIAL',
    "shading.single_color": (0.8, 0.8, 0.8),
    "shading.show_object_outline": True,
    "shading.object_outline_color": (0.0, 0.0, 0.0),
    "shading.wireframe_color_type": 'THEME',
    "shading.background_type": 'THEME',
    "shading.background_color": (0.05, 0.05, 0.05),
    "shading.show_cavity": False,
    "shading.show_shadows": False,
    "shading.show_specular_highlight": True,
    "shading.show_xray": False,
    "overlay.show_overlays": False,
    "overlay.show_floor": True,
    "overlay.show_ortho_grid": True,
    "overlay.grid_scale": 1.0,
    "overlay.show_axis_x": True,
    "overlay.show_axis_y": True,
    "overlay.show_axis_z": False,
    "overlay.show_cursor": True,
    "overlay.show_text": True,
    "overlay.show_stats": False,
    "overlay.show_annotation": True,
    "overlay.show_extras": True,
    "overlay.show_relationship_lines": True,
    "overlay.show_outline_selected": True,
    "overlay.show_object_origins": True,
    "overlay.show_motion_paths": True,
    "overlay.show_bones": True,
    "overlay.show_wireframes": False,
}


# -- the pure half: no bpy, no scene ----------------------------------------

def theme_names():
    """The theme identifiers, default first."""

    return (DEFAULT_THEME,) + tuple(sorted(name for name in THEMES
                                           if name != DEFAULT_THEME))


def shading_values(theme=DEFAULT_THEME, grid=True):
    """Every field the blueprint writes, as ``{"owner.attr": value}``.

    One table rather than imperative writes, because the table is the
    contract three parties share: :func:`refresh` applies it, the capture in
    :func:`_save_look` reads exactly these fields and no others, and the
    gate asserts the styled viewport equals it. ``shading.type`` is first
    and stays first — enum fields like ``color_type`` validate against the
    current type, so it must land before them.

    Every sub-overlay is explicitly present, almost all of them False: the
    blueprint is the only view that turns ``overlay.show_overlays`` on, and
    a sub-overlay left to its stored value would draw whatever the user last
    had there.
    """

    colors = THEMES[str(theme or DEFAULT_THEME)]
    grid = bool(grid)
    return {
        "shading.type": 'SOLID',
        "shading.light": 'FLAT',
        "shading.color_type": 'SINGLE',
        "shading.single_color": tuple(colors["solid"]),
        "shading.show_object_outline": True,
        "shading.object_outline_color": tuple(colors["line"]),
        # The Edges wires read ``obj.color``, which nothing sets, so every
        # wire renders in the object default -- white.
        "shading.wireframe_color_type": 'OBJECT',
        "shading.background_type": 'VIEWPORT',
        "shading.background_color": tuple(colors["background"]),
        "shading.show_cavity": False,
        "shading.show_shadows": False,
        "shading.show_specular_highlight": False,
        "shading.show_xray": False,
        # ON, or the Edges wires do not draw at all (overlay_wireframe.hh
        # skips wire objects when overlays are off) -- and therefore every
        # sub-overlay is pinned below.
        "overlay.show_overlays": True,
        "overlay.show_floor": grid,
        "overlay.show_ortho_grid": grid,
        "overlay.grid_scale": GRID_MM,
        "overlay.show_axis_x": False,
        "overlay.show_axis_y": False,
        "overlay.show_axis_z": False,
        "overlay.show_cursor": False,
        "overlay.show_text": False,
        "overlay.show_stats": False,
        "overlay.show_annotation": False,
        "overlay.show_extras": False,
        "overlay.show_relationship_lines": False,
        "overlay.show_outline_selected": False,
        "overlay.show_object_origins": False,
        "overlay.show_motion_paths": False,
        "overlay.show_bones": False,
        # Facet wires would fight the true BREP edges; the whole point of
        # riding the Edges children is that they are the real model edges.
        "overlay.show_wireframes": False,
    }


# -- the bpy half -----------------------------------------------------------

#: Guard against an update callback that assigns to another property of the
#: same group and re-enters this module through its update callback.
_settling = False


def settings(scene=None):
    """The scene's blueprint settings, or None on a file older than this."""

    import bpy
    scene = scene or bpy.context.scene
    return getattr(scene, "cadex_blueprint", None)


def enabled(scene=None):
    group = settings(scene)
    return bool(group and group.show)


def _spaces():
    """Every 3D viewport space, through ``bpy.data.screens``.

    Not through ``window_manager.windows``: the gate runs ``--background``,
    where there are no windows but the loaded screens and their spaces are
    real and hold the styling exactly as a windowed session would.
    """

    import bpy
    found = []
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            space = area.spaces.active
            if space is not None:
                found.append(space)
    return found


def _read_field(space, field):
    owner_name, attr = field.split(".", 1)
    value = getattr(getattr(space, owner_name), attr)
    return _plain(value)


def _plain(value):
    """A color comes out of RNA (and out of an IDProperty) as an array type;
    copy it to a tuple. Enums are strings, and a string is NOT a tuple of
    its characters."""

    if isinstance(value, str):
        return value
    try:
        return tuple(value)
    except TypeError:
        return value


def _apply_fields(space, values):
    for field in values:
        owner_name, attr = field.split(".", 1)
        try:
            setattr(getattr(space, owner_name), attr, values[field])
        except (TypeError, ValueError):
            # A field this build does not know (older/newer Blender): skip
            # it rather than lose the rest of the look.
            pass


def _save_look(scene, space):
    """Capture the look once, before the first apply. Idempotent: a second
    refresh while the blueprint is on must not capture the blueprint."""

    if SAVED_KEY in scene:
        return
    scene[SAVED_KEY] = {field: _read_field(space, field)
                        for field in shading_values()}


def _saved_look(scene):
    """The captured look, or :data:`PRODUCT_LOOK` if nothing was captured."""

    saved = scene.get(SAVED_KEY)
    if not saved:
        return dict(PRODUCT_LOOK)
    found = {}
    for field in PRODUCT_LOOK:
        if field in saved.keys():
            found[field] = _plain(saved[field])
        else:
            found[field] = PRODUCT_LOOK[field]
    return found


def refresh(scene=None):
    """Make every viewport agree with the settings. The one entry point."""

    import bpy

    scene = scene or bpy.context.scene
    group = settings(scene)
    if group is None or not group.show:
        return clear(scene)

    values = shading_values(group.theme, group.grid)
    spaces = _spaces()
    for space in spaces:
        _save_look(scene, space)
        _apply_fields(space, values)

    report = {
        "shown": True,
        "theme": str(group.theme),
        "grid": bool(group.grid),
        "viewports": len(spaces),
    }
    scene[SCENE_FLAG] = report
    return report


def clear(scene=None, forget=True):
    """Put the viewport look back and forget the capture.

    Restores the captured look — or :data:`PRODUCT_LOOK`, the pinned startup
    styling, when the view is marked on but its capture is lost — to every
    viewport. A clear when the blueprint was never applied (neither flag on
    the scene) touches nothing: a settings write while the view is off must
    not restyle a viewport this module never styled.
    """

    import bpy
    scene = scene or bpy.context.scene

    restored = 0
    if SAVED_KEY in scene or SCENE_FLAG in scene:
        saved = _saved_look(scene)
        for space in _spaces():
            _apply_fields(space, saved)
            restored += 1

    if forget:
        if SAVED_KEY in scene:
            del scene[SAVED_KEY]
        if SCENE_FLAG in scene:
            del scene[SCENE_FLAG]
    return {"shown": False, "restored": restored}


def suspend(scene=None):
    """Take the styling off for the duration of a render; returns an undo.

    ``render_views`` answers "what did I build" (ADR-124), and white lines
    on drawing-office blue are not what was built — the plain look comes
    back for the shot, without forgetting the capture or the settings, and
    the undo re-applies the blueprint. ``render_blueprint`` is the renderer
    that wants this styling and deliberately does not suspend it.
    """

    import bpy

    scene = scene or bpy.context.scene
    if not enabled(scene):
        return None

    saved = _saved_look(scene)
    for space in _spaces():
        _apply_fields(space, saved)

    def restore():
        try:
            refresh(scene)
        except Exception:
            import traceback
            traceback.print_exc()

    return restore


def present(space, theme=DEFAULT_THEME):
    """Style ONE space for an offscreen render; returns an undo callable.

    ``render_blueprint``'s half of the module: apply the theme to the space
    it is about to draw through — grid off, a sheet carries its own scale —
    and put back exactly what was there. Independent of the toggle and of
    the scene capture: rendering a sheet must not disturb a viewport that
    has the blueprint on, or one that does not.
    """

    values = shading_values(theme, grid=False)
    saved = {field: _read_field(space, field) for field in values}
    _apply_fields(space, values)

    def restore():
        _apply_fields(space, saved)

    return restore


def toggle(on=None, scene=None):
    """Turn the blueprint on or off. Returns the resulting report."""

    import bpy
    scene = scene or bpy.context.scene
    group = settings(scene)
    if group is None:
        return {"shown": False,
                "message": "This file predates the blueprint view; save and "
                           "reopen it."}

    global _settling
    want = (not group.show) if on is None else bool(on)
    if not want:
        group.show = False           # its update callback clears the scene
        return {"shown": False}

    _settling = True
    try:
        group.show = True
    finally:
        _settling = False
    return refresh(scene)


def _on_setting_changed(_self, context):
    if _settling:
        return
    try:
        refresh(getattr(context, "scene", None))
    except Exception:
        import traceback
        traceback.print_exc()


def _register_settings():
    import bpy

    class CadexBlueprintSettings(bpy.types.PropertyGroup):
        """How the blueprint is drawn. Saved in the file, like any view
        state."""

        show: bpy.props.BoolProperty(
            name="Blueprint",
            description="Draw the model as white outlines on a drawing-"
                        "office background",
            default=False,
            update=_on_setting_changed,
        )
        theme: bpy.props.EnumProperty(
            name="Theme",
            description="The ground the lines are drawn on",
            items=(('blueprint', "Blueprint", "White lines on blueprint blue"),
                   ('cutting_mat', "Cutting Mat",
                    "White lines on cutting-mat green"),
                   ('grey', "Grey", "White lines on neutral grey")),
            default=DEFAULT_THEME,
            update=_on_setting_changed,
        )
        grid: bpy.props.BoolProperty(
            name="Grid",
            description="Draw a {:.0f} mm grid under the model".format(GRID_MM),
            default=True,
            update=_on_setting_changed,
        )

    bpy.utils.register_class(CadexBlueprintSettings)
    bpy.types.Scene.cadex_blueprint = bpy.props.PointerProperty(
        type=CadexBlueprintSettings)
    return CadexBlueprintSettings


_settings_class = None


def register():
    global _settings_class
    _settings_class = _register_settings()
    from . import cadex_views
    cadex_views.register_view(name="blueprint", order=60, suspend=suspend)


def unregister():
    import bpy
    global _settings_class
    from . import cadex_views
    cadex_views.unregister_view("blueprint")
    try:
        del bpy.types.Scene.cadex_blueprint
    except Exception:
        pass
    if _settings_class is not None:
        bpy.utils.unregister_class(_settings_class)
        _settings_class = None
