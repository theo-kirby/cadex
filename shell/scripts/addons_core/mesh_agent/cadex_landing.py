# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The landing screen: a start page drawn inside the 3D viewport (ADR-167).

Not a popup. ADR-042 removed Blender's modal splash and stays removed; this
is the FreeCAD-style alternative -- the empty viewport at startup becomes a
start page (example-project card, New/Open/Tutorial), while the chat column
stays live beside it. Sending a chat message, opening a file, or pressing
Escape puts the viewport back.

Mechanics follow ``cadex_dimension`` exactly: a module-level POST_PIXEL draw
handler, shaders fetched lazily so ``--background`` never touches the gpu
module, and geometry split into pure functions (:func:`landing_layout`,
:func:`hit_test`) the suite can drive without a window. Clicks arrive
through two add-on keymap items on the 3D View -- a left-click dispatcher
that consumes the click while the screen is up, and a mouse-move updater for
hover -- rather than a modal operator, so nothing is grabbed and the rest of
the window keeps working.

The demo project ships in ``demo/`` beside this file (``drone.blend`` plus
its ``drone.cadex`` store, sanitized: no transcript, no machine paths, the
one linked node group made local). Opening it always copies first -- the
bundle is never opened in place, so a save can never write into the app.
"""

import os
import shutil

__all__ = (
    "landing_layout",
    "hit_test",
    "show",
    "dismiss",
    "visible",
    "demo_source",
    "demo_destination",
    "register",
    "unregister",
)

# Actions, in the order the action column draws them. The example-project
# card is a fourth, larger hit target above the fold. There is deliberately
# no "Start Chatting" button: the chat is already open beside the page and
# typing into it dismisses the page, so a button would be the redundant way
# to say so.
ACTIONS = (
    ("new", "New File"),
    ("open", "Open…"),
    ("tutorial", "Tutorial"),
)

DEMO_DIR_NAME = "demo"
DEMO_STEM = "drone"
DEMO_CARD_NAME = "card.png"
LOGO_NAME = "landing_logo.png"
#: Where "click to open a copy" lands. A fresh numbered stem each time, so a
#: demo the user changed and saved is never overwritten by the next click.
DEMO_HOME = ("Documents", "Cadex Demo")

CARD_ASPECT = 0.625  # the shipped card.png is 1152x720
#: Corner radii, in unscaled pixels -- the widget theme's rounding, writ a
#: little larger for the card.
BUTTON_RADIUS = 6.0
CARD_RADIUS = 10.0

# The colours are the running theme's, read in _palette() -- the page keeps
# the app's own two-tone grey and follows a theme change for free. These are
# only the stand-ins for a session with no readable theme.
_FALLBACK = {
    "scrim": (0.138, 0.138, 0.138),
    "panel": (0.220, 0.220, 0.220),
    "panel_hover": (0.300, 0.300, 0.300),
    "outline": (0.360, 0.360, 0.360),
    "outline_hover": (0.540, 0.540, 0.540),
    "text": (0.900, 0.900, 0.900),
    "dim": (0.580, 0.580, 0.580),
}
_SCRIM_ALPHA = 0.96

_visible = False
_shown_this_session = False
_hover = None
_draw_handle = None
_keymap_items = []
_textures = {}  # filename -> GPUTexture, or False for a load that failed
_palette_cache = None
_version_text = None
_quieted_spaces = []


# -- pure geometry ------------------------------------------------------------

def landing_layout(width, height, scale=1.0):
    """Every rect and anchor of the landing screen, in region pixels.

    Pure, so the suite can assert the hit targets without a window: y is up
    from the region bottom, rects are ``(x, y, w, h)``. The content column
    shrinks to fit small regions rather than clipping.
    """

    width = max(1.0, float(width))
    height = max(1.0, float(height))
    s = max(0.1, float(scale))

    def build(s):
        pad = 28.0 * s
        gap = 14.0 * s
        button_w = 236.0 * s
        button_h = 44.0 * s
        title_h = 52.0 * s
        subtitle_h = 18.0 * s
        overline_h = 14.0 * s
        caption_h = 16.0 * s
        hint_h = 14.0 * s

        two_column = width >= (700.0 * s)
        content_w = min(width - 2.0 * pad, 900.0 * s)
        if two_column:
            card_w = content_w - button_w - 2.0 * gap
        else:
            card_w = content_w
        card_w = max(120.0 * s, card_w)
        card_h = card_w * CARD_ASPECT

        header_h = title_h + 6.0 * s + subtitle_h
        logo_s = header_h  # the mark spans the wordmark + tagline block
        body_h = max(card_h + overline_h + gap + caption_h + gap,
                     (button_h + gap) * len(ACTIONS)) if two_column else (
            card_h + overline_h + gap + caption_h + gap
            + (button_h + gap) * len(ACTIONS))
        total_h = header_h + 2.0 * gap + body_h + gap + hint_h
        return {
            "pad": pad, "gap": gap, "button_w": button_w,
            "button_h": button_h, "title_h": title_h,
            "subtitle_h": subtitle_h, "overline_h": overline_h,
            "caption_h": caption_h, "hint_h": hint_h,
            "two_column": two_column, "content_w": content_w,
            "card_w": card_w, "card_h": card_h, "header_h": header_h,
            "logo_s": logo_s, "total_h": total_h,
        }

    m = build(s)
    if m["total_h"] > height - 2.0 * m["pad"]:
        s *= max(0.35, (height - 2.0 * m["pad"]) / m["total_h"])
        m = build(s)

    gap = m["gap"]
    left = (width - m["content_w"]) / 2.0
    top = height - (height - m["total_h"]) / 2.0

    title_y = top - m["title_h"]
    subtitle_y = title_y - 6.0 * s - m["subtitle_h"]
    text_left = left + m["logo_s"] + 16.0 * s
    body_top = subtitle_y - 2.0 * gap

    overline_y = body_top - m["overline_h"]
    card_y = overline_y - gap * 0.5 - m["card_h"]
    card = (left, card_y, m["card_w"], m["card_h"])
    caption_y = card_y - gap * 0.5 - m["caption_h"]

    if m["two_column"]:
        buttons_x = left + m["content_w"] - m["button_w"]
        buttons_top = body_top
    else:
        buttons_x = left
        buttons_top = caption_y - gap

    buttons = []
    y = buttons_top
    for action_id, label in ACTIONS:
        y -= m["button_h"]
        buttons.append({
            "id": action_id,
            "label": label,
            "rect": (buttons_x, y, m["button_w"], m["button_h"]),
        })
        y -= gap

    bottom = min(caption_y - m["caption_h"], y)
    hint_y = bottom - gap - m["hint_h"]

    return {
        "scale": s,
        "two_column": m["two_column"],
        "logo": {"rect": (left, subtitle_y - 4.0 * s,
                          m["logo_s"], m["logo_s"])},
        "title": {"pos": (text_left, title_y), "size": m["title_h"]},
        "version": {"size": m["subtitle_h"]},
        "subtitle": {"pos": (text_left, subtitle_y), "size": m["subtitle_h"]},
        "overline": {"pos": (left, overline_y), "size": m["overline_h"]},
        "card": {"rect": card},
        "caption": {"pos": (left, caption_y), "size": m["caption_h"]},
        "buttons": buttons,
        "hint": {"pos": (left, hint_y), "size": m["hint_h"]},
    }


def _inside(rect, x, y):
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh


def hit_test(layout, x, y):
    """The action id under (x, y), or None. ``demo`` is the card."""

    if _inside(layout["card"]["rect"], x, y):
        return "demo"
    for button in layout["buttons"]:
        if _inside(button["rect"], x, y):
            return button["id"]
    return None


def rounded_rect_points(rect, radius, segments=6):
    """A rounded rectangle as a convex CCW polygon, in pixels. Pure.

    Counter-clockwise from the bottom-left arc, ``segments + 1`` points per
    corner; a radius at or under half a pixel degenerates to the four
    corners. Convex, so a fan from point 0 triangulates it.
    """

    import math

    x, y, w, h = rect
    r = max(0.0, min(float(radius), w / 2.0, h / 2.0))
    if r <= 0.5:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    points = []
    corners = ((x + r, y + r, 180.0), (x + w - r, y + r, 270.0),
               (x + w - r, y + h - r, 0.0), (x + r, y + h - r, 90.0))
    for cx, cy, start in corners:
        for i in range(segments + 1):
            angle = math.radians(start + 90.0 * i / segments)
            points.append((cx + r * math.cos(angle),
                           cy + r * math.sin(angle)))
    return points


def _fan_indices(points):
    return [(0, i, i + 1) for i in range(1, len(points) - 1)]


# -- demo project -------------------------------------------------------------

def demo_source():
    """(blend_path, store_path) of the shipped demo, or (None, None)."""

    root = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        DEMO_DIR_NAME)
    blend = os.path.join(root, DEMO_STEM + ".blend")
    store = os.path.join(root, DEMO_STEM + ".cadex")
    if os.path.isfile(blend) and os.path.isdir(store):
        return blend, store
    return None, None


def demo_destination():
    """A fresh (blend_path, store_path) pair under the demo home.

    The stems must match -- the engine project root is derived from the
    .blend name -- and must be new, so a saved demo session is never
    clobbered by the next click.
    """

    home = os.path.join(os.path.expanduser("~"), *DEMO_HOME)
    stem = DEMO_STEM
    counter = 1
    while True:
        blend = os.path.join(home, stem + ".blend")
        store = os.path.join(home, stem + ".cadex")
        if not os.path.exists(blend) and not os.path.exists(store):
            return blend, store
        counter += 1
        stem = "{}-{}".format(DEMO_STEM, counter)


def open_demo():
    """Copy the shipped demo out of the bundle and open the copy.

    Returns (ok, message): the message is a chat status line on success and
    the refusal on failure.
    """

    import bpy

    source_blend, source_store = demo_source()
    if source_blend is None:
        return False, ("The demo project is not in this build; "
                       "open a file or start from a prompt instead.")
    blend, store = demo_destination()
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    shutil.copy2(source_blend, blend)
    shutil.copytree(source_store, store)
    dismiss()
    bpy.ops.wm.open_mainfile(filepath=blend)
    return True, ("Opened the example project — a ducted-fan drone — "
                  "as your copy at {}. Move a parameter slider, or ask for "
                  "a change.".format(blend))


# -- state --------------------------------------------------------------------

def visible():
    return _visible


def _quiet_viewport_gizmos():
    """Hide the navigation gizmos under the start page, remembering what to
    put back. The blueprint view's trade, one field instead of a table."""

    import bpy

    try:
        windows = bpy.context.window_manager.windows
    except Exception:
        return
    for window in windows or ():
        for area in getattr(window.screen, "areas", ()) or ():
            if getattr(area, "type", "") != 'VIEW_3D':
                continue
            for space in area.spaces:
                if getattr(space, "type", "") == 'VIEW_3D':
                    _quieted_spaces.append((space, bool(space.show_gizmo)))
                    space.show_gizmo = False


def _restore_viewport_gizmos():
    # A space from before a file load is a dead reference by now; the new
    # file's own spaces were never touched, so skipping it is correct.
    for space, value in _quieted_spaces:
        try:
            space.show_gizmo = value
        except Exception:
            pass
    _quieted_spaces.clear()


def show():
    """Put the landing screen up (once per session from register)."""

    global _visible, _shown_this_session, _palette_cache

    _shown_this_session = True
    if _visible:
        return
    _visible = True
    _palette_cache = None  # re-read the theme each time the page comes up
    _add_draw_handler()
    _quiet_viewport_gizmos()
    _redraw()


def dismiss():
    """Take it down. Safe to call twice, and from any of the exits."""

    global _visible, _hover

    if not _visible:
        return
    _visible = False
    _hover = None
    _remove_draw_handler()
    _restore_viewport_gizmos()
    _redraw()


def maybe_show_on_startup():
    """Arrange to show on a fresh interactive session.

    Deferred through a timer, and not as a nicety: register() runs in the
    restricted context where ``bpy.data`` is ``_RestrictData`` and reading
    ``filepath`` raises -- the template's own ``_apply`` deferral, for the
    same reason. By the time the timer fires, a session launched onto a
    real file (double-click, CLI argument) has its filepath set and is
    left alone; a timer never fires under ``--background`` at all.
    """

    import bpy

    if bpy.app.background or _shown_this_session:
        return

    def decide():
        if bpy.app.background or _shown_this_session:
            return None
        if not bpy.data.filepath:
            show()
        return None

    bpy.app.timers.register(decide, first_interval=0.2)


def on_file_loaded():
    """A file was read: a real one dismisses, the startup file does not."""

    import bpy

    if bpy.data.filepath:
        dismiss()


# -- drawing ------------------------------------------------------------------

def _redraw():
    import bpy

    try:
        windows = bpy.context.window_manager.windows
    except Exception:
        return
    for window in windows or ():
        for area in getattr(window.screen, "areas", ()) or ():
            if getattr(area, "type", "") == 'VIEW_3D':
                area.tag_redraw()


def _fill_shader():
    import gpu

    try:
        return gpu.shader.from_builtin('UNIFORM_COLOR')
    except Exception:
        return None


def _palette():
    """The page's colours, read from the running theme (cached per show).

    The operator's ask, verbatim: no palette of its own — the app's two-tone
    grey. Widget fills composite ``wcol_regular.inner`` over the scrim at
    the theme's own alpha, so a translucent widget theme reads the same
    here as in a real panel; hover brightens, the way the widgets do.
    """

    global _palette_cache

    if _palette_cache is not None:
        return _palette_cache

    import bpy

    palette = dict(_FALLBACK)
    try:
        theme = bpy.context.preferences.themes[0]
        wcol = theme.user_interface.wcol_regular
        back = tuple(theme.view_3d.space.gradients.high_gradient)[:3]
        scrim = tuple(c * 0.92 for c in back)
        inner = tuple(wcol.inner)
        inner_alpha = inner[3] if len(inner) > 3 else 1.0
        panel = tuple(inner[i] * inner_alpha + scrim[i] * (1.0 - inner_alpha)
                      for i in range(3))
        text = tuple(wcol.text)[:3]
        outline = tuple(wcol.outline)[:3]
        palette.update(
            scrim=scrim,
            panel=panel,
            panel_hover=tuple(min(1.0, c + 0.07) for c in panel),
            outline=outline,
            outline_hover=tuple(min(1.0, c + 0.25) for c in outline),
            text=tuple(min(1.0, c + 0.10) for c in text),
            dim=tuple(c * 0.72 for c in text),
        )
    except Exception:
        pass
    _palette_cache = palette
    return palette


def _version():
    """The stamped product version, cached; "" outside a stamped bundle."""

    global _version_text

    if _version_text is None:
        import bpy

        text = ""
        try:
            path = os.path.join(os.path.dirname(bpy.app.binary_path), "..",
                                "Resources", "cadex_version.txt")
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.readline().strip()
        except Exception:
            text = ""
        _version_text = text
    return _version_text


def _gpu_texture(relative_path):
    """A shipped PNG as a GPUTexture, loaded once, never a datablock left
    behind: pixels go image -> numpy -> gpu.types.Buffer and the image is
    removed, so nothing rides along into the user's next save."""

    cached = _textures.get(relative_path)
    if cached is not None:
        return cached or None

    import bpy
    import gpu
    import numpy

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        *relative_path.split("/"))
    texture = False
    image = None
    try:
        image = bpy.data.images.load(path, check_existing=False)
        width, height = image.size
        pixels = numpy.empty(width * height * 4, dtype=numpy.float32)
        image.pixels.foreach_get(pixels)
        buffer = gpu.types.Buffer('FLOAT', width * height * 4, pixels)
        texture = gpu.types.GPUTexture((width, height), format='RGBA16F',
                                       data=buffer)
    except Exception:
        texture = False
    finally:
        if image is not None:
            try:
                bpy.data.images.remove(image)
            except Exception:
                pass
    _textures[relative_path] = texture
    return texture or None


def _draw_fill(shader, batch_for_shader, points, color, alpha=1.0):
    batch = batch_for_shader(shader, 'TRIS', {"pos": points},
                             indices=_fan_indices(points))
    shader.bind()
    shader.uniform_float("color", (color[0], color[1], color[2], alpha))
    batch.draw(shader)


def _draw_border(shader, batch_for_shader, points, color, alpha=1.0):
    batch = batch_for_shader(shader, 'LINE_LOOP', {"pos": points})
    shader.bind()
    shader.uniform_float("color", (color[0], color[1], color[2], alpha))
    batch.draw(shader)


def _draw_image(batch_for_shader, texture, rect, radius=0.0):
    """A textured quad, its corners rounded by geometry: the polygon's own
    UVs crop the image, so no mask pass and no premultiply games."""

    import gpu

    x, y, w, h = rect
    points = rounded_rect_points(rect, radius)
    uvs = [((px - x) / w, (py - y) / h) for px, py in points]
    shader = gpu.shader.from_builtin('IMAGE')
    batch = batch_for_shader(shader, 'TRIS',
                             {"pos": points, "texCoord": uvs},
                             indices=_fan_indices(points))
    shader.bind()
    shader.uniform_sampler("image", texture)
    batch.draw(shader)


def _text(blf, x, y, size, color, message, alpha=1.0):
    try:
        blf.size(0, size)
    except TypeError:
        blf.size(0, size, 72)
    blf.color(0, color[0], color[1], color[2], alpha)
    blf.position(0, x, y, 0.0)
    blf.draw(0, message)


def _text_width(blf, size, message):
    try:
        blf.size(0, size)
    except TypeError:
        blf.size(0, size, 72)
    return float(blf.dimensions(0, message)[0])


def _draw():
    import bpy

    if not _visible:
        return
    if bpy.data.filepath:
        return  # a real file is open; the next event dismisses for good
    region = getattr(bpy.context, "region", None)
    if region is None or getattr(bpy.context, "region_data", None) is None:
        return

    import blf
    import gpu
    from gpu_extras.batch import batch_for_shader

    shader = _fill_shader()
    if shader is None:
        return

    pal = _palette()
    width, height = float(region.width), float(region.height)
    try:
        scale = float(bpy.context.preferences.system.ui_scale)
    except Exception:
        scale = 1.0
    layout = landing_layout(width, height, scale)
    s = layout["scale"]

    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')
    try:
        _draw_fill(shader, batch_for_shader,
                   [(0.0, 0.0), (width, 0.0), (width, height),
                    (0.0, height)],
                   pal["scrim"], _SCRIM_ALPHA)

        # Header: the mark, the wordmark, the stamped version, the tagline.
        logo = _gpu_texture(LOGO_NAME)
        if logo is not None:
            _draw_image(batch_for_shader, logo, layout["logo"]["rect"])
        tx, ty = layout["title"]["pos"]
        title_size = layout["title"]["size"]
        _text(blf, tx, ty, title_size, pal["text"], "Cadex")
        version = _version()
        if version:
            offset = _text_width(blf, title_size, "Cadex") + 14.0 * s
            _text(blf, tx + offset, ty, layout["version"]["size"],
                  pal["dim"], version)
        sx, sy = layout["subtitle"]["pos"]
        _text(blf, sx, sy, layout["subtitle"]["size"], pal["dim"],
              "AI-native CAD")

        # The demo card.
        card = layout["card"]["rect"]
        card_points = rounded_rect_points(card, CARD_RADIUS * s)
        ox, oy = layout["overline"]["pos"]
        _text(blf, ox, oy, layout["overline"]["size"], pal["dim"],
              "EXAMPLE PROJECT")
        texture = _gpu_texture(DEMO_DIR_NAME + "/" + DEMO_CARD_NAME)
        hovered = _hover == "demo"
        if texture is not None:
            _draw_image(batch_for_shader, texture, card, CARD_RADIUS * s)
        else:
            _draw_fill(shader, batch_for_shader, card_points, pal["panel"])
        _draw_border(shader, batch_for_shader, card_points,
                     pal["outline_hover"] if hovered else pal["outline"],
                     1.0 if hovered else 0.8)
        cx, cy = layout["caption"]["pos"]
        _text(blf, cx, cy, layout["caption"]["size"],
              pal["text"] if hovered else pal["dim"],
              "Ducted-fan drone")

        # The action column.
        for button in layout["buttons"]:
            rect = button["rect"]
            is_hover = _hover == button["id"]
            points = rounded_rect_points(rect, BUTTON_RADIUS * s)
            _draw_fill(shader, batch_for_shader, points,
                       pal["panel_hover"] if is_hover else pal["panel"])
            _draw_border(shader, batch_for_shader, points,
                         pal["outline_hover"] if is_hover
                         else pal["outline"],
                         1.0 if is_hover else 0.65)
            size = 15.0 * s
            label = button["label"]
            bx, by, bw, bh = rect
            label_w = _text_width(blf, size, label)
            ly = by + (bh - size) / 2.0 + 2.0 * s
            _text(blf, bx + (bw - label_w) / 2.0, ly, size,
                  pal["text"] if is_hover else pal["dim"], label)
            if button["id"] == "tutorial":
                tag_size = 11.0 * s
                tag_w = _text_width(blf, tag_size, "soon")
                _text(blf, bx + bw - tag_w - 10.0 * s, ly, tag_size,
                      pal["dim"], "soon", alpha=0.8)

        hx, hy = layout["hint"]["pos"]
        _text(blf, hx, hy, layout["hint"]["size"], pal["dim"],
              "Esc to skip", alpha=0.9)
    finally:
        gpu.state.blend_set('NONE')
        gpu.state.depth_test_set('LESS_EQUAL')


def _add_draw_handler():
    import bpy

    global _draw_handle

    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw, (), 'WINDOW', 'POST_PIXEL')


def _remove_draw_handler():
    """Guarded, and safe to call twice: it runs on every dismiss and on
    unload (the cadex_dimension rule -- a handle left behind outlives the
    module it points into)."""

    import bpy

    global _draw_handle

    if _draw_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        except Exception:
            pass
        _draw_handle = None


# -- input --------------------------------------------------------------------

def _region_layout(context):
    import bpy

    region = getattr(context, "region", None)
    if region is None:
        return None
    try:
        scale = float(bpy.context.preferences.system.ui_scale)
    except Exception:
        scale = 1.0
    return landing_layout(float(region.width), float(region.height), scale)


def _make_operators():
    import bpy
    from bpy.types import Operator

    class MESH_AGENT_OT_landing_click(Operator):
        """Dispatch a click on the landing screen.

        Consumes every left press in the viewport while the screen is up --
        the screen owns the region, the way any start page does -- and runs
        the action under the cursor, if any.
        """

        bl_idname = "mesh_agent.landing_click"
        bl_label = "Landing Screen Click"
        bl_options = {'INTERNAL'}

        @classmethod
        def poll(cls, context):
            return _visible

        def invoke(self, context, event):
            layout = _region_layout(context)
            if layout is None:
                return {'CANCELLED'}
            action = hit_test(layout, event.mouse_region_x,
                              event.mouse_region_y)
            if action == "demo":
                try:
                    ok, message = open_demo()
                except Exception as exc:
                    self.report({'WARNING'}, "Demo failed to open: " + str(exc))
                    return {'CANCELLED'}
                if not ok:
                    self.report({'WARNING'}, message)
                    return {'CANCELLED'}
                try:
                    from . import agent as agent_module
                    agent_module.get_agent().history.add("status", message)
                except Exception:
                    pass
                return {'FINISHED'}
            if action == "new":
                dismiss()
                # The startup file behind this screen already is the new
                # file; only a dirtied or renamed session needs the reload.
                if bpy.data.filepath or bpy.data.is_dirty:
                    bpy.ops.wm.read_homefile('INVOKE_DEFAULT')
                return {'FINISHED'}
            if action == "open":
                dismiss()
                bpy.ops.wm.open_mainfile('INVOKE_DEFAULT')
                return {'FINISHED'}
            if action == "tutorial":
                self.report({'INFO'},
                            "The tutorial is on its way — not in this "
                            "build yet.")
                return {'FINISHED'}
            return {'CANCELLED'}  # scrim: consumed, nothing behind it moves

    class MESH_AGENT_OT_landing_hover(Operator):
        """Track which landing action is under the cursor (hover styling)."""

        bl_idname = "mesh_agent.landing_hover"
        bl_label = "Landing Screen Hover"
        bl_options = {'INTERNAL'}

        @classmethod
        def poll(cls, context):
            return _visible

        def invoke(self, context, event):
            global _hover

            layout = _region_layout(context)
            if layout is not None:
                action = hit_test(layout, event.mouse_region_x,
                                  event.mouse_region_y)
                if action != _hover:
                    _hover = action
                    region = getattr(context, "region", None)
                    if region is not None:
                        region.tag_redraw()
            return {'PASS_THROUGH'}

    class MESH_AGENT_OT_landing_dismiss(Operator):
        """Close the landing screen (Escape, and anything else that wants
        the viewport back)."""

        bl_idname = "mesh_agent.landing_dismiss"
        bl_label = "Close Landing Screen"
        bl_options = {'INTERNAL'}

        @classmethod
        def poll(cls, context):
            return _visible

        def execute(self, context):
            dismiss()
            return {'FINISHED'}

    return (MESH_AGENT_OT_landing_click, MESH_AGENT_OT_landing_hover,
            MESH_AGENT_OT_landing_dismiss)


_operator_classes = ()


def register():
    import bpy

    global _operator_classes

    _operator_classes = _make_operators()
    for cls in _operator_classes:
        bpy.utils.register_class(cls)

    # Input reaches the screen through the add-on keymap, not a modal grab:
    # three items on the 3D View, all no-ops the moment `poll` fails.
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig is not None:
        keymap = keyconfig.keymaps.new(name="3D View", space_type='VIEW_3D')
        for idname, key, value in (
                ("mesh_agent.landing_click", 'LEFTMOUSE', 'PRESS'),
                ("mesh_agent.landing_hover", 'MOUSEMOVE', 'ANY'),
                ("mesh_agent.landing_dismiss", 'ESC', 'PRESS')):
            _keymap_items.append(
                (keymap, keymap.keymap_items.new(idname, key, value)))

    maybe_show_on_startup()


def unregister():
    import bpy

    global _operator_classes, _palette_cache
    global _version_text, _shown_this_session

    dismiss()
    _remove_draw_handler()
    for keymap, item in _keymap_items:
        try:
            keymap.keymap_items.remove(item)
        except Exception:
            pass
    _keymap_items.clear()
    for cls in reversed(_operator_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
    _operator_classes = ()
    _textures.clear()
    _palette_cache = None
    _version_text = None
    _shown_this_session = False
