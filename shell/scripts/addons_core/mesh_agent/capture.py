# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Viewport capture for the agent: offscreen render, downscaled, base64 PNG.

Two questions, two functions. ``screenshot_png_base64`` answers *what does
the user see* -- their viewport, their camera, their overlays. ``render_views``
answers *what did I build*: four fitted cameras around the Model collection,
composited into one image, with the user's session deliberately excluded
(ADR-124).

The camera arithmetic is in ``view_matrices``, which imports no ``bpy`` and
returns plain tuples -- the same split ``cadex_collision`` keeps between its
``extents_mm`` table and its overlay. That is the half the headless suite can
test, and the half Phase 12 re-binds rather than re-designs.
"""

import base64
import math
import os
import tempfile

# The four views, in the order they are composited (reading order in a 2x2
# grid). ``direction`` points from the model to the camera; ``up`` is the
# world axis that ends up pointing up in the image.
VIEWS = (
    {"name": "front", "quadrant": "top-left",
     "direction": (0.0, -1.0, 0.0), "up": (0.0, 0.0, 1.0), "ortho": True},
    {"name": "right", "quadrant": "top-right",
     "direction": (1.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0), "ortho": True},
    {"name": "top", "quadrant": "bottom-left",
     "direction": (0.0, 0.0, 1.0), "up": (0.0, 1.0, 0.0), "ortho": True},
    {"name": "three-quarter", "quadrant": "bottom-right",
     "azimuth": 45.0, "elevation": 25.0, "up": (0.0, 0.0, 1.0), "ortho": False},
)

# Every view a composed sheet can ask for by name (ADR-151). The four in
# VIEWS above stay the render_views contract; this table is the superset the
# sheet's ``views`` argument validates against. ``_direction``/``_basis``
# already handle every entry, including the top/bottom up-flip.
NAMED_VIEWS = {
    "front": {"name": "front",
              "direction": (0.0, -1.0, 0.0), "up": (0.0, 0.0, 1.0),
              "ortho": True},
    "back": {"name": "back",
             "direction": (0.0, 1.0, 0.0), "up": (0.0, 0.0, 1.0),
             "ortho": True},
    "left": {"name": "left",
             "direction": (-1.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0),
             "ortho": True},
    "right": {"name": "right",
              "direction": (1.0, 0.0, 0.0), "up": (0.0, 0.0, 1.0),
              "ortho": True},
    "top": {"name": "top",
            "direction": (0.0, 0.0, 1.0), "up": (0.0, 1.0, 0.0),
            "ortho": True},
    "bottom": {"name": "bottom",
               "direction": (0.0, 0.0, -1.0), "up": (0.0, 1.0, 0.0),
               "ortho": True},
    "three-quarter": {"name": "three-quarter",
                      "azimuth": 45.0, "elevation": 25.0,
                      "up": (0.0, 0.0, 1.0), "ortho": False},
}

# Vertical field of view of the perspective view, in degrees.
HERO_FOV = 40.0

# How much empty space to leave around the model, as a scale on the fit.
MARGIN = 1.08


# -- the pure half: no bpy, plain tuples ------------------------------------

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _normalized(v):
    length = math.sqrt(_dot(v, v))
    if length < 1e-12:
        return (0.0, 0.0, 1.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def _direction(view):
    """Unit vector from the model towards the camera."""

    if "direction" in view:
        return _normalized(view["direction"])
    # Azimuth is measured from the front (-Y) towards +X, elevation up from
    # the ground plane -- the way a turntable is described, not the way a
    # spherical coordinate is.
    azimuth = math.radians(float(view.get("azimuth") or 0.0))
    elevation = math.radians(float(view.get("elevation") or 0.0))
    return _normalized((
        math.sin(azimuth) * math.cos(elevation),
        -math.cos(azimuth) * math.cos(elevation),
        math.sin(elevation),
    ))


def _corners(bbox):
    (x0, y0, z0), (x1, y1, z1) = bbox
    return tuple((x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1))


def _basis(direction, up):
    """Right-handed camera basis: +x right, +y up, +z towards the viewer."""

    z_axis = _normalized(direction)
    if abs(_dot(z_axis, _normalized(up))) > 0.999:
        up = (0.0, 1.0, 0.0) if abs(z_axis[2]) > 0.5 else (0.0, 0.0, 1.0)
    x_axis = _normalized(_cross(up, z_axis))
    y_axis = _cross(z_axis, x_axis)
    return x_axis, y_axis, z_axis


def _look_at(eye, basis):
    x_axis, y_axis, z_axis = basis
    return (
        (x_axis[0], x_axis[1], x_axis[2], -_dot(x_axis, eye)),
        (y_axis[0], y_axis[1], y_axis[2], -_dot(y_axis, eye)),
        (z_axis[0], z_axis[1], z_axis[2], -_dot(z_axis, eye)),
        (0.0, 0.0, 0.0, 1.0),
    )


def _ortho_window(half_width, half_height, near, far):
    return (
        (1.0 / half_width, 0.0, 0.0, 0.0),
        (0.0, 1.0 / half_height, 0.0, 0.0),
        (0.0, 0.0, -2.0 / (far - near), -(far + near) / (far - near)),
        (0.0, 0.0, 0.0, 1.0),
    )


def _perspective_window(fov_y, aspect, near, far):
    focal = 1.0 / math.tan(math.radians(fov_y) / 2.0)
    return (
        (focal / aspect, 0.0, 0.0, 0.0),
        (0.0, focal, 0.0, 0.0),
        (0.0, 0.0, (far + near) / (near - far), 2.0 * far * near / (near - far)),
        (0.0, 0.0, -1.0, 0.0),
    )


def transform(matrix, point):
    """Apply a 4x4 row-major matrix to a 3-point; returns (x, y, z, w)."""

    x, y, z = point[0], point[1], point[2]
    return tuple(row[0] * x + row[1] * y + row[2] * z + row[3] for row in matrix)


def project(view_matrix, window_matrix, point):
    """World point to normalised device coordinates, or None if behind."""

    camera = transform(view_matrix, point)
    clip = transform(window_matrix, camera)
    if abs(clip[3]) < 1e-12:
        return None
    return (clip[0] / clip[3], clip[1] / clip[3], clip[2] / clip[3])


def fit_view(view, bbox, aspect=1.0, margin=MARGIN):
    """Fit ONE camera to a world bounding box, at one cell's aspect.

    ``view`` is a VIEWS/NAMED_VIEWS-shaped dict (``direction`` or
    ``azimuth``/``elevation``, ``up``, ``ortho``); ``bbox`` is
    ((min_x, min_y, min_z), (max_x, max_y, max_z)); ``aspect`` is the
    width/height of the one tile this camera fills. Returns the dict
    ``render_views`` has always consumed, ready for ``draw_view3d``.

    No bpy: this is arithmetic on the bounding box, and it is what the
    headless suite checks. ``view_matrices`` is now a wrapper over this,
    one call per VIEWS entry (ADR-151).
    """

    (x0, y0, z0), (x1, y1, z1) = bbox
    centre = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)
    corners = _corners(bbox)
    radius = max(math.sqrt(_dot(_sub(c, centre), _sub(c, centre))) for c in corners)
    if radius < 1e-9:
        # A point, an empty collection, or a single vertex: frame a unit box
        # so the render is a picture of nothing rather than a division by zero.
        radius = 0.5
    aspect = float(aspect) if aspect and aspect > 0 else 1.0

    direction = _direction(view)
    basis = _basis(direction, view["up"])
    if view["ortho"]:
        distance = radius * 3.0
        eye = tuple(centre[i] + direction[i] * distance for i in range(3))
        view_matrix = _look_at(eye, basis)
        local = [transform(view_matrix, corner) for corner in corners]
        # The floor is what keeps a flat model -- a plate seen edge-on,
        # or the degenerate box above -- from dividing by zero here.
        floor = radius * 1e-3
        half_width = max(max(abs(p[0]) for p in local) * margin, floor)
        half_height = max(max(abs(p[1]) for p in local) * margin, floor)
        if half_width / half_height < aspect:
            half_width = half_height * aspect
        else:
            half_height = half_width / aspect
        window = _ortho_window(max(half_width, 1e-6), max(half_height, 1e-6),
                               distance - radius * 2.0, distance + radius * 2.0)
    else:
        half_v = math.radians(HERO_FOV) / 2.0
        half_h = math.atan(math.tan(half_v) * aspect)
        distance = radius * margin / math.sin(min(half_v, half_h))
        eye = tuple(centre[i] + direction[i] * distance for i in range(3))
        view_matrix = _look_at(eye, basis)
        window = _perspective_window(
            HERO_FOV, aspect,
            max(distance - radius * 2.0, distance * 0.01),
            distance + radius * 2.0)
    built = {
        "name": view["name"],
        "ortho": view["ortho"],
        "direction": direction,
        "eye": eye,
        "distance": distance,
        "view": view_matrix,
        "window": window,
    }
    if "quadrant" in view:
        built["quadrant"] = view["quadrant"]
    return built


def view_matrices(bbox, aspect=1.0, margin=MARGIN):
    """Fit the four cameras to a world bounding box.

    ``bbox`` is ((min_x, min_y, min_z), (max_x, max_y, max_z)); ``aspect`` is
    the width/height of ONE tile, not of the composite. Returns a tuple of
    dicts carrying the view name, its quadrant, and its ``view``/``window``
    matrices as row-major tuples ready for ``GPUOffScreen.draw_view3d``.

    No bpy: this is arithmetic on the bounding box, and it is what the
    headless suite checks.
    """

    return tuple(fit_view(view, bbox, aspect=aspect, margin=margin)
                 for view in VIEWS)


def quadrant_legend(views=None):
    """One sentence naming what is in each quadrant.

    Returned as text rather than drawn into the image: labelling the pixels
    would need ``blf`` and a font, and buys nothing a caption cannot say.
    """

    views = views if views is not None else view_matrices(((0, 0, 0), (1, 1, 1)))
    described = {
        "front": "front (camera on -Y, looking along +Y)",
        "right": "right (camera on +X, looking along -X)",
        "top": "top (camera on +Z, looking down)",
        "three-quarter": "three-quarter perspective (azimuth 45 deg, elevation 25 deg)",
    }
    return "; ".join(
        "{:s}: {:s}".format(view["quadrant"], described.get(view["name"], view["name"]))
        for view in views)


def _find_view3d():
    import bpy

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type == 'WINDOW':
                    return window, area, area.spaces.active, region
    return None, None, None, None


def image_file_png_base64(path, max_size=1024):
    """Load an image file, downscale it if needed, and return it as
    (base64_png, None) or (None, error_message). Works headless."""
    import bpy

    if not path or not os.path.isfile(path):
        return None, "Image file not found: {!s}".format(path)
    try:
        image = bpy.data.images.load(path)
    except RuntimeError as ex:
        return None, "Could not load image: {!s}".format(ex)
    try:
        width, height = image.size
        if width == 0 or height == 0:
            return None, "Unreadable image: {!s}".format(path)
        largest = max(width, height)
        if largest > max_size:
            scale = max_size / largest
            image.scale(max(8, int(width * scale)), max(8, int(height * scale)))
        tmp = os.path.join(tempfile.gettempdir(), "mesh_agent_attach_tmp.png")
        image.filepath_raw = tmp
        image.file_format = 'PNG'
        image.save()
        with open(tmp, "rb") as file:
            data = file.read()
        os.remove(tmp)
    finally:
        bpy.data.images.remove(image)
    return base64.b64encode(data).decode("ascii"), None


def screenshot_png_base64(max_size=768):
    """Return (base64_png, None) or (None, error_message)."""
    import bpy

    if bpy.app.background:
        return None, ("Viewport capture is unavailable in background mode; "
                      "use scene_summary instead.")

    window, area, space, region = _find_view3d()
    if space is None:
        return None, "No 3D viewport found; use scene_summary instead."

    import gpu

    scale = min(1.0, max_size / max(region.width, region.height, 1))
    width = max(8, int(region.width * scale))
    height = max(8, int(region.height * scale))

    region_3d = space.region_3d
    offscreen = gpu.types.GPUOffScreen(width, height)
    try:
        offscreen.draw_view3d(
            bpy.context.scene,
            bpy.context.view_layer,
            space,
            region,
            region_3d.view_matrix,
            region_3d.window_matrix,
            do_color_management=True,
        )
        with offscreen.bind():
            framebuffer = gpu.state.active_framebuffer_get()
            pixel_buffer = framebuffer.read_color(0, 0, width, height, 4, 0, 'FLOAT')
        pixel_buffer.dimensions = width * height * 4
        pixels = [value for value in pixel_buffer]
    finally:
        offscreen.free()

    image = bpy.data.images.new("mesh_agent_capture", width, height, alpha=True)
    try:
        image.pixels.foreach_set(pixels)
        path = os.path.join(tempfile.gettempdir(), "mesh_agent_capture.png")
        image.filepath_raw = path
        image.file_format = 'PNG'
        image.save()
        with open(path, "rb") as file:
            data = file.read()
        os.remove(path)
    finally:
        bpy.data.images.remove(image)

    return base64.b64encode(data).decode("ascii"), None


# -- render_views: four fitted cameras, one image (ADR-124) -----------------

def model_bbox():
    """World-space bounding box of the Model collection, or None if empty."""

    from . import model
    import bpy
    from mathutils import Vector

    collection = bpy.data.collections.get(model.COLLECTION_NAME)
    if collection is None:
        return None
    low = [float("inf")] * 3
    high = [float("-inf")] * 3
    seen = False
    for obj in collection.all_objects:
        if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}:
            continue
        # Hidden objects are skipped, and the reason is ADR-049: hydration
        # hides a source solid and instances components off it, so measuring
        # the source too would fit the cameras to geometry nobody can see.
        if not obj.visible_get():
            continue
        matrix = obj.matrix_world
        for corner in obj.bound_box:
            point = matrix @ Vector(corner)
            for axis in range(3):
                low[axis] = min(low[axis], point[axis])
                high[axis] = max(high[axis], point[axis])
            seen = True
    if not seen:
        return None
    return (tuple(low), tuple(high))


def _isolate_model(view_layer, keep=()):
    """Hide every root collection except Model; returns an undo callable.

    The Collision cage and the section-cage overlay are siblings of Model at
    the scene root exactly so they can be swept as a unit (cadex_collision's
    docstring says why they must not be children). That makes isolating the
    model one loop over the root layer collections.

    ``keep`` names sibling collections that stay in shot — the blueprint
    sheet keeps the exploded leader lines, because it deliberately renders
    the current presentation (ADR-150).
    """

    from . import model

    import bpy

    kept = {model.COLLECTION_NAME} | set(keep)
    changed = []
    for layer in view_layer.layer_collection.children:
        if layer.collection.name in kept:
            continue
        if not layer.hide_viewport:
            layer.hide_viewport = True
            changed.append(layer)

    # Measured, not assumed: without this the cage is still in shot.
    # ``hide_viewport`` on a layer collection is a runtime flag that the
    # view layer syncs lazily, and ``draw_view3d`` runs before the event
    # loop would have got round to it, so the first render came back with
    # a collection we had just hidden still in it.
    if changed:
        view_layer.update()
        bpy.context.evaluated_depsgraph_get()

    def restore():
        for layer in changed:
            layer.hide_viewport = False
        if changed:
            view_layer.update()

    return restore


def _present_model(space):
    """Solid studio shading with no overlays; returns an undo callable."""

    shading, overlay = space.shading, space.overlay
    saved = {
        "type": shading.type,
        "light": shading.light,
        "studio_light": shading.studio_light,
        "color_type": shading.color_type,
        "show_overlays": overlay.show_overlays,
        "background_type": getattr(shading, "background_type", None),
    }
    shading.type = 'SOLID'
    shading.light = 'STUDIO'
    shading.color_type = 'MATERIAL'
    overlay.show_overlays = False

    def restore():
        shading.type = saved["type"]
        shading.light = saved["light"]
        try:
            shading.studio_light = saved["studio_light"]
        except (TypeError, ValueError):
            pass
        shading.color_type = saved["color_type"]
        overlay.show_overlays = saved["show_overlays"]
        if saved["background_type"] is not None:
            try:
                shading.background_type = saved["background_type"]
            except (TypeError, ValueError):
                pass

    return restore


def _tile_pixels(space, region, width, height, view_matrix, window_matrix):
    import bpy
    import gpu
    from mathutils import Matrix

    offscreen = gpu.types.GPUOffScreen(width, height)
    try:
        offscreen.draw_view3d(
            bpy.context.scene,
            bpy.context.view_layer,
            space,
            region,
            Matrix(view_matrix),
            Matrix(window_matrix),
            do_color_management=True,
        )
        with offscreen.bind():
            framebuffer = gpu.state.active_framebuffer_get()
            pixel_buffer = framebuffer.read_color(0, 0, width, height, 4, 0, 'FLOAT')
        pixel_buffer.dimensions = width * height * 4
        return list(pixel_buffer)
    finally:
        offscreen.free()


def composite_rects(tiles, canvas_width, canvas_height):
    """Flat RGBA tile buffers into one canvas buffer, by rect (ADR-151).

    ``tiles`` is ``[(pixels, (x, y, w, h))]``: bottom-up row-major buffers,
    rects in canvas pixels with ``y`` measured from the bottom — the layout
    the buffers themselves use, so a copy is a row slice and the per-pixel
    work stays in C. A None buffer leaves its rect on the ground colour.
    """

    out = [0.0] * (canvas_width * canvas_height * 4)
    stride = canvas_width * 4
    for tile, (x, y, w, h) in tiles:
        if tile is None:
            continue
        tile_stride = w * 4
        for row in range(h):
            src = row * tile_stride
            dst = (y + row) * stride + x * 4
            out[dst:dst + tile_stride] = tile[src:src + tile_stride]
    return out


def composite_2x2(tiles, tile_width, tile_height):
    """Four flat RGBA row-major (bottom-up) tile buffers into one buffer.

    Plain pixel arithmetic, in the order VIEWS declares: top-left, top-right,
    bottom-left, bottom-right. A wrapper over :func:`composite_rects` with
    the four quadrant rects; the pure suite pins the equivalence.
    """

    width, height = tile_width * 2, tile_height * 2
    placement = ((0, 1), (1, 1), (0, 0), (1, 0))  # (column, row-from-bottom)
    rects = [(column * tile_width, row * tile_height, tile_width, tile_height)
             for column, row in placement]
    out = composite_rects(list(zip(tiles, rects)), width, height)
    return out, width, height


def render_views(max_size=1024):
    """Four fitted views of the model, composited 2x2. (base64_png, None).

    Not a screenshot: the cameras are computed from the Model collection's
    bounding box and the user's overlays and sibling collections are hidden
    for the duration. What comes back is a picture of the model, at a known
    orientation, whatever the user's viewport happens to be showing.
    """

    import bpy

    if bpy.app.background:
        return None, ("Multi-view rendering is unavailable in background mode; "
                      "use scene_summary instead.")

    window, area, space, region = _find_view3d()
    if space is None:
        return None, "No 3D viewport found; use scene_summary instead."

    # Every registered view that knows how to suspend is suspended here, for
    # the reason the sibling collections are hidden here (ADR-148, ADR-149):
    # a cut, spread or restyled model is not what was built, and this is the
    # tool that answers "what did I build". ``viewport_screenshot`` answers
    # the other question and leaves them alone. It goes FIRST, before the
    # model is measured, because ``bound_box`` reads evaluated geometry --
    # cameras fitted while a cut was on would frame the half of the part
    # that survived it.
    from . import cadex_views

    undo_views = cadex_views.suspend_for_render()
    tile = max(8, int(max_size) // 2)
    undo_isolation = _isolate_model(bpy.context.view_layer)
    undo_presentation = _present_model(space)
    try:
        bbox = model_bbox()
        if bbox is None:
            return None, ("The Model collection is empty, so there is nothing "
                          "to render; check scene_summary for what the engine "
                          "built.")
        views = view_matrices(bbox, aspect=1.0)
        tiles = [_tile_pixels(space, region, tile, tile, view["view"], view["window"])
                 for view in views]
    finally:
        undo_presentation()
        undo_isolation()
        undo_views()

    pixels, width, height = composite_2x2(tiles, tile, tile)

    image = bpy.data.images.new("mesh_agent_views", width, height, alpha=True)
    try:
        image.pixels.foreach_set(pixels)
        path = os.path.join(tempfile.gettempdir(), "mesh_agent_views.png")
        image.filepath_raw = path
        image.file_format = 'PNG'
        image.save()
        with open(path, "rb") as file:
            data = file.read()
        os.remove(path)
    finally:
        bpy.data.images.remove(image)

    return base64.b64encode(data).decode("ascii"), None


# -- render_blueprint: the composed, dressed sheet (ADR-150, ADR-151) --------

def render_blueprint(theme="blueprint", max_size=1024, views=None,
                     layout="auto", aspect=None, label=""):
    """Agent-composed fitted views, styled and dressed as a blueprint sheet.

    Returns ``({"path", "base64", "legend", "views", "recipe", "layout",
    "rects", "size", "version", "project", "note"}, None)`` or
    ``(None, error)``.
    The PNG lands in a temp file because its home is the project store: the
    caller hands the path to ``put_blueprint`` and the engine copies it in
    (the shell never writes the store).

    ``views``/``layout`` are the ADR-151 composition surface, validated by
    ``cadex_sheet`` — and validated FIRST, before the background refusal,
    so a bad spec is refused for what is wrong with it even in the headless
    gate, while a valid spec still refuses headless in the unchanged
    sentence.

    Deliberately does **not** suspend the section or the exploded view —
    the contrast with ``render_views``: that tool answers "what did I
    build" and reassembles everything first (ADR-124); this one draws the
    *current presentation* as a sheet, per-view overrides layered on top of
    it and restored from one flat snapshot afterwards. Only the sibling
    overlays that are not presentation (the collision cage, the
    section-cage rings) are hidden, and the exploded leader lines stay in
    shot.
    """

    import time

    import bpy

    from . import cadex_backend
    from . import cadex_blueprint
    from . import cadex_explode
    from . import cadex_section
    from . import cadex_sheet
    from . import cadexd_client

    scene = bpy.context.scene
    root = cadex_backend.project_root(scene)
    accepted = cadex_backend.last_accepted(root)
    display = dict(accepted.get("display") or {})

    defaults_used = views is None
    specs, error = cadex_sheet.normalize_views(views, sorted(display))
    if error:
        return None, error
    if defaults_used:
        if str(layout or "auto") == "auto":
            layout = "triptych"
        # The default sheet's right column is the exploded rear
        # three-quarter — but only when there is an explosion to draw.
        # A plain part (or a baked simulation) gets the same view
        # unexploded, never a refusal: the default must work everywhere.
        from . import cadex_animate

        entry, _reason = cadex_explode.exploded_entry(display)
        if entry is None or cadex_animate.SCENE_FLAG in scene:
            specs = tuple(
                dict(spec, explode=None, name="rear three-quarter",
                     label="rear three-quarter", title="rear three-quarter")
                if spec.get("explode") is not None else spec
                for spec in specs)
    template, hero_index, error = cadex_sheet.choose_layout(layout, specs)
    if error:
        return None, error
    ratio, error = cadex_sheet.sheet_aspect(aspect, template)
    if error:
        return None, error
    error = cadex_sheet.validate_against_model(scene, specs)
    if error:
        return None, error

    if bpy.app.background:
        return None, ("Blueprint rendering is unavailable in background "
                      "mode; use scene_summary instead.")

    window, area, space, region = _find_view3d()
    if space is None:
        return None, "No 3D viewport found; use scene_summary instead."

    cells = None
    if template == "mosaic":
        cells = [(spec["cell"][0], spec["cell"][1],
                  spec["span"][0], spec["span"][1]) for spec in specs]
    rects, field_w, field_h = cadex_sheet.layout_rects(
        template, len(specs), max(8, int(max_size)), hero=hero_index,
        cells=cells, aspect=ratio,
        aspects=[spec.get("aspect") for spec in specs])
    margin = cadex_sheet.margin_px(max(field_w, field_h))
    label_size = max(10.0, margin * 0.55)
    theme_colors = cadex_blueprint.THEMES[
        str(theme or cadex_blueprint.DEFAULT_THEME)]

    notes = []
    callouts = []
    tiles = [None] * len(specs)
    snapshot = cadex_sheet.snapshot_state(scene)
    undo_isolation = _isolate_model(bpy.context.view_layer,
                                    keep={cadex_explode.COLLECTION_NAME})
    undo_presentation = cadex_blueprint.present(space, theme)
    try:
        for index, (spec, rect) in enumerate(zip(specs, rects)):
            if spec["view"] in cadex_sheet.PANEL_VIEWS:
                continue   # a sheet cell, not a scene state; drawn below
            cadex_sheet.apply_view_state(scene, spec, snapshot)
            bbox = model_bbox()
            if bbox is None:
                if spec["hide"]:
                    return None, ("views[{:d}] hides every visible output; "
                                  "nothing to draw in that "
                                  "cell.".format(index))
                return None, ("The Model collection is empty, so there is "
                              "nothing to draw; check scene_summary for "
                              "what the engine built.")
            if isinstance(spec.get("section"), dict):
                report = dict(scene.get(cadex_section.SCENE_FLAG) or {})
                if report.get("clear"):
                    # The section module's own doctrine: a plane past the
                    # model says nothing, but it is not an error.
                    notes.append("views[{:d}]'s section offset is clear of "
                                 "the model, so that cell shows the whole "
                                 "part".format(index))
            x, y, w, h = rect
            named = cadex_sheet.callouts_active(spec)
            # The wider fit buys the label band; a cell too narrow to
            # carry one gets the normal fit and the drop note below.
            roomy = named and w >= cadex_sheet.CALLOUT_MIN_WIDTH
            fitted = fit_view(spec, bbox, aspect=w / float(h),
                              margin=(cadex_sheet.CALLOUT_FIT_MARGIN
                                      if roomy else MARGIN))
            tiles[index] = (_tile_pixels(space, region, w, h,
                                         fitted["view"], fitted["window"]),
                            rect)
            if named:
                anchors = cadex_sheet.callout_anchors(
                    sorted(display), spec["hide"], fitted, w, h)
                entries, dropped = cadex_sheet.callout_layout(
                    anchors, w, h, max(9.0, margin * 0.45),
                    top_pad=label_size + 8.0)
                for entry in entries:
                    entry = dict(entry)
                    ax, ay = entry["anchor"]
                    entry["anchor"] = (margin + x + ax, margin + y + ay)
                    entry["label_x"] += margin + x
                    entry["label_y"] += margin + y
                    callouts.append(entry)
                if dropped:
                    notes.append("views[{:d}]: {:d} part name(s) dropped "
                                 "-- the cell is too small for all its "
                                 "callouts".format(index, dropped))
    finally:
        cadex_sheet.restore_state(scene, snapshot)
        undo_presentation()
        undo_isolation()

    # The panel cells, after the scene is back as it was: they draw the
    # declared sliders or the agent's own words, not the model, on the same
    # sampled ground as the rendered tiles (the ADR-151 uniform-ground
    # lesson).
    panel_cells = [(index, spec, rect) for index, (spec, rect)
                   in enumerate(zip(specs, rects))
                   if spec["view"] in cadex_sheet.PANEL_VIEWS]
    if panel_cells:
        sample = next((tile for tile in tiles if tile is not None), None)
        ground = (tuple(sample[0][0:3])
                  if sample is not None and any(sample[0][0:3])
                  else cadex_sheet.display_color(
                      theme_colors["background"]))
        rows = None
        for index, spec, rect in panel_cells:
            if spec["view"] == "text":
                pixels, dropped = cadex_sheet._draw_text_tile(
                    rect[2], rect[3], spec.get("text") or "", theme_colors,
                    ground, top_pad=label_size + 8.0)
                tiles[index] = (pixels, rect)
                if dropped:
                    notes.append("views[{:d}]: {:d} line(s) of text did not "
                                 "fit -- give the panel a taller cell or "
                                 "fewer words".format(index, dropped))
                continue
            if rows is None:
                from . import model as model_module

                state = cadex_backend.cached_script_state(scene)
                try:
                    stored = model_module.stored_values(scene)
                except Exception:
                    stored = {}
                rows = cadex_sheet.param_rows(
                    list(getattr(state, "specs", None) or []),
                    dict(stored or {}))
            tiles[index] = (cadex_sheet._draw_params_tile(
                rect[2], rect[3], rows, theme_colors, ground,
                top_pad=label_size + 8.0), rect)

    field_pixels = composite_rects([tile for tile in tiles
                                    if tile is not None],
                                   field_w, field_h)

    project = os.path.basename(os.path.normpath(root))
    if project.endswith(".cadex"):
        project = project[:-len(".cadex")]
    version = cadexd_client.engine_version(cadex_backend.bundle_roots())
    revision = str(accepted.get("revision") or "")
    titles = cadex_sheet.title_lines(
        project if not label else "{:s} — {:s}".format(project, label),
        version, revision, time.strftime("%Y-%m-%d"), theme)

    cell_labels = [(spec["label"],
                    margin + rect[0] + 6,
                    margin + rect[1] + rect[3] - 6 - label_size)
                   for spec, rect in zip(specs, rects)]
    # One uniform ground: the margin band takes the colour the tiles
    # actually came back in (colour-managed), sampled off the field's
    # corner pixel — the theme value pushed through display_color is only
    # the fallback for a corner a model somehow reached.
    ground = tuple(field_pixels[0:3])
    if all(value == 0.0 for value in ground):
        ground = cadex_sheet.display_color(theme_colors["background"])
    sheet_w = field_w + 2 * margin
    sheet_h = field_h + 2 * margin
    pixels, width, height = cadex_sheet._dress_sheet(
        field_pixels, field_w, field_h, margin, theme_colors,
        cadex_sheet.zone_grid(sheet_w, sheet_h), titles, cell_labels,
        background=ground, callouts=callouts)

    image = bpy.data.images.new("mesh_agent_blueprint", width, height, alpha=True)
    try:
        image.pixels.foreach_set(pixels)
        path = os.path.join(tempfile.gettempdir(), "mesh_agent_blueprint.png")
        image.filepath_raw = path
        image.file_format = 'PNG'
        image.save()
        with open(path, "rb") as file:
            data = file.read()
    finally:
        bpy.data.images.remove(image)

    sheet_aspect_text = (str(aspect) if aspect is not None
                         else ("auto" if template == "mosaic"
                               else cadex_sheet.DEFAULT_ASPECT))
    return {
        "path": path,
        "base64": base64.b64encode(data).decode("ascii"),
        "legend": cadex_sheet.cell_legend(specs, rects),
        "views": [cadex_sheet.spec_meta(spec) for spec in specs],
        # What this sheet can be drawn again from (ADR-157). The template
        # rather than the requested layout, and the specs rather than the
        # raw input, so a revision starts from what was *drawn* -- including
        # the default sheet, which is how "change one cell of the default"
        # works without the agent restating the other four.
        "recipe": cadex_sheet.sheet_recipe(specs, theme, template,
                                           sheet_aspect_text, max_size),
        "layout": template,
        "aspect": sheet_aspect_text,
        "rects": [list(rect) for rect in rects],
        "size": [width, height],
        "version": version,
        "project": project,
        "note": "; ".join(notes),
    }, None
