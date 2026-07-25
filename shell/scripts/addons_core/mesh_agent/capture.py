# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Viewport capture for the agent: offscreen render, downscaled, base64 PNG."""

import base64
import os
import tempfile


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
