# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The reward curve, drawn in the Training editor. The shell's first plot.

``cadex_training.py`` reads ``training-progress.json`` and its panel shows
the numbers; this module draws the ``curve`` field the trainer now
publishes — ``[[iteration, reward_per_step], ...]``, capped at 512 pairs —
as a line in the bottom of the ``CADEX_TRAINING`` editor's window region.
The floating panel keeps the top of the region; the plot takes the bottom
``PLOT_FRACTION`` and nothing overlaps.

**The dependency is one-way and stays that way.** This module imports
``cadex_training`` for ``read_progress``; ``cadex_training`` never imports
this — the gate pins that module's import set to exactly ``{json, os,
bpy}``, and a lazy import of a plot would trip it. That is also the
degradation story: a ``progress.json`` written by a trainer from before
the ``curve`` field has no curve, ``curve_from`` returns ``[]``, and the
editor is panel-only — correct by construction, no version check anywhere.

**There is still no train button.** This module registers no operator and
owns no timer: the agent dispatches runs, ``cadex_training.poll`` already
tags the area for redraw when the file moves, and everything here is a
readout of a file some trainer somewhere is writing.

The pure half — everything above ``-- the bpy half --`` — imports ``math``
and nothing else, and is where every number that can be wrong lives. It is
exercised by ``bl_mesh_agent.py``, the suite that needs no engine; the
draw handler itself follows ``cadex_dimension`` line for line (shader
fetched on first draw, never at import, because ``gpu.shader.from_builtin``
raises under ``--background``, which is where the gates run).
"""

import math

#: Fewer points than this is a dot, not a curve. The first iteration of a
#: run draws nothing; the second draws a line.
CURVE_MIN_POINTS = 2

#: Below this many pixels on either side the region is a sliver — somebody
#: parked the editor in a corner — and a plot would be axis labels
#: overlapping a frame. The panel still draws; the plot waits.
MIN_REGION_PX = 220

#: The bottom fraction of the region the plot owns. The floating panel
#: hangs from the top of the region and a long checkpoint list reaches
#: about half way down; 0.42 keeps them apart on the editor's default
#: proportions.
PLOT_FRACTION = 0.42

#: Pixels between the plot frame and the region edges, and between the
#: frame and its tick labels.
MARGIN_PX = 18.0
TICK_LABEL_PAD_PX = 6.0

#: Matches the force-arrow overlay in ``cadex_live`` and the dimension
#: text in ``cadex_dimension``.
TEXT_SIZE_PX = 11

#: The curve, in the editors' accent orange (``cadex_live``'s force
#: arrows); the frame and ticks in a grey that reads on the editor's
#: background without shouting.
CURVE_COLOR = (1.0, 0.42, 0.12)
FRAME_COLOR = (0.62, 0.62, 0.62)
BEST_COLOR = (0.35, 0.85, 0.35)
PLOT_ALPHA = 0.9

#: Half-size of the best-so-far marker's cross, in pixels.
BEST_MARK_PX = 4.0


def curve_from(report):
    """The report's curve as ``[(iteration, reward), ...]``, or ``[]``.

    ``[]`` for absent, not-a-list, and malformed alike — a file written by
    an older trainer, a truncated pair, a NaN — because the plot's job is
    to be invisible when there is nothing sound to draw, exactly as the
    panel's is when there is no run.
    """

    if not isinstance(report, dict):
        return []
    rows = report.get("curve")
    if not isinstance(rows, list):
        return []
    points = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            return []
        try:
            iteration = int(row[0])
            reward = float(row[1])
        except (TypeError, ValueError):
            return []
        if not math.isfinite(reward):
            return []
        points.append((iteration, reward))
    return points


def axis_ticks(low, high, count=4):
    """About ``count`` round values covering ``[low, high]``, ascending.

    The 1/2/5 ladder every plotting library climbs, written out because
    this module's whole dependency budget is ``math``.
    """

    if not (math.isfinite(low) and math.isfinite(high)) or high <= low:
        return []
    raw = (high - low) / max(count, 1)
    magnitude = 10.0 ** math.floor(math.log10(raw))
    for factor in (1.0, 2.0, 5.0, 10.0):
        step = factor * magnitude
        if raw <= step:
            break
    first = math.ceil(low / step) * step
    ticks = []
    value = first
    while value <= high + step * 1.0e-9:
        # Snap "-0.0" and float dust so labels read as the round numbers
        # they are.
        ticks.append(round(value, 10) + 0.0)
        value += step
    return ticks


def _tick_label(value):
    return "{:+.3g}".format(value)


def plot_layout(width, height, points, *, best_iteration=-1, total=0):
    """Everything the draw handler draws, in region pixels, or ``None``.

    ``None`` when there is no curve to speak of or no room to draw one —
    the two cases the handler early-exits on, split out so the gate can
    assert both without a region in the room. The dict carries:

    - ``frame``: ``(x0, y0, x1, y1)`` of the plot rectangle;
    - ``polyline``: the curve, as ``[(x, y), ...]``, x monotone;
    - ``best``: the best-so-far marker's ``(x, y)``, or ``None``;
    - ``zero``: the y pixel of reward zero, or ``None`` when zero is
      outside the y-range;
    - ``ticks``: ``[(y_pixel, label), ...]`` for the y axis.

    y = 0 is the bottom of the region, which is ``POST_PIXEL``'s frame.
    """

    if len(points) < CURVE_MIN_POINTS:
        return None
    if width < MIN_REGION_PX or height < MIN_REGION_PX:
        return None

    x0 = MARGIN_PX + 34.0  # room for tick labels left of the frame
    y0 = MARGIN_PX
    x1 = float(width) - MARGIN_PX
    y1 = float(height) * PLOT_FRACTION
    if x1 - x0 < 40.0 or y1 - y0 < 40.0:
        return None

    iterations = [point[0] for point in points]
    rewards = [point[1] for point in points]
    x_low = float(min(iterations))
    # The frame spans the run as *asked for*, so a live curve grows into
    # it rather than rescaling every iteration.
    x_high = float(max(max(iterations), total - 1))
    if x_high <= x_low:
        return None
    y_low, y_high = min(rewards), max(rewards)
    if y_high - y_low < 1.0e-12:
        # A flat curve is still information; pad the range so the line
        # draws mid-frame rather than dividing by zero.
        pad = max(abs(y_low) * 0.1, 0.5)
        y_low -= pad
        y_high += pad

    def x_at(iteration):
        return x0 + (float(iteration) - x_low) / (x_high - x_low) * (x1 - x0)

    def y_at(reward):
        return y0 + (float(reward) - y_low) / (y_high - y_low) * (y1 - y0)

    best = None
    if best_iteration >= 0:
        candidates = [point for point in points
                      if point[0] == int(best_iteration)]
        if candidates:
            best = (x_at(candidates[0][0]), y_at(candidates[0][1]))

    return {
        "frame": (x0, y0, x1, y1),
        "polyline": [(x_at(i), y_at(r)) for i, r in points],
        "best": best,
        "zero": y_at(0.0) if y_low < 0.0 < y_high else None,
        "ticks": [(y_at(value), _tick_label(value))
                  for value in axis_ticks(y_low, y_high)],
    }


# ------------------------------ the bpy half ------------------------------

#: Guarded exactly as ``cadex_dimension``'s is: a handle left behind
#: outlives the module it points into and raises on the next reload.
_draw_handle = None
_shader = None


def _line_shader():
    """``(shader, is_polyline)``, fetched on first draw and never at import
    — ``gpu.shader.from_builtin`` raises under ``--background``, which is
    where the gate runs."""

    global _shader

    if _shader is None:
        import gpu

        for name in ('POLYLINE_UNIFORM_COLOR', 'UNIFORM_COLOR'):
            try:
                _shader = (gpu.shader.from_builtin(name),
                           name.startswith('POLYLINE'))
                break
            except Exception:
                continue
    return _shader or (None, False)


def _layout_for_context():
    """The current region's plot layout, or ``None``. The handler's whole
    early exit, split from ``_draw`` so a probe can call it headless."""

    import bpy

    from . import cadex_training

    region = getattr(bpy.context, "region", None)
    scene = getattr(bpy.context, "scene", None)
    if region is None or scene is None:
        return None
    report = cadex_training.read_progress(scene)
    if report is None:
        return None
    points = curve_from(report)
    return plot_layout(
        int(region.width), int(region.height), points,
        best_iteration=int(report.get("best_iteration", -1) or -1),
        total=int(report.get("total") or 0),
    )


def _draw():
    layout = _layout_for_context()
    if layout is None:
        return

    import blf
    import gpu
    from gpu_extras.batch import batch_for_shader

    shader, polyline = _line_shader()
    if shader is None:
        return

    x0, y0, x1, y1 = layout["frame"]
    frame_points = [(x0, y0), (x1, y0), (x1, y0), (x1, y1),
                    (x1, y1), (x0, y1), (x0, y1), (x0, y0)]
    tick_points = []
    for y, _label in layout["ticks"]:
        tick_points.extend([(x0 - 4.0, y), (x0, y)])
    if layout["zero"] is not None:
        tick_points.extend([(x0, layout["zero"]), (x1, layout["zero"])])

    curve_points = []
    previous = None
    for point in layout["polyline"]:
        if previous is not None:
            curve_points.extend([previous, point])
        previous = point
    best = layout["best"]
    best_points = []
    if best is not None:
        bx, by = best
        best_points = [(bx - BEST_MARK_PX, by), (bx + BEST_MARK_PX, by),
                       (bx, by - BEST_MARK_PX), (bx, by + BEST_MARK_PX)]

    gpu.state.blend_set('ALPHA')
    try:
        shader.bind()
        if polyline:
            viewport = gpu.state.viewport_get()
            shader.uniform_float("viewportSize",
                                 (float(viewport[2]), float(viewport[3])))
        for points, color, width_px in (
                (frame_points + tick_points, FRAME_COLOR, 1.0),
                (curve_points, CURVE_COLOR, 1.8),
                (best_points, BEST_COLOR, 1.8)):
            if not points:
                continue
            shader.uniform_float("color", color + (PLOT_ALPHA,))
            if polyline:
                shader.uniform_float("lineWidth", width_px)
            batch_for_shader(shader, 'LINES', {"pos": points}).draw(shader)
    finally:
        gpu.state.blend_set('NONE')

    try:
        blf.size(0, TEXT_SIZE_PX)
    except TypeError:
        blf.size(0, TEXT_SIZE_PX, 72)
    blf.color(0, FRAME_COLOR[0], FRAME_COLOR[1], FRAME_COLOR[2], PLOT_ALPHA)
    for y, label in layout["ticks"]:
        text_width = blf.dimensions(0, label)[0]
        blf.position(0, x0 - text_width - TICK_LABEL_PAD_PX, y - 4.0, 0.0)
        blf.draw(0, label)


def _add_draw_handler():
    import bpy

    global _draw_handle

    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceCadexTraining.draw_handler_add(
            _draw, (), 'WINDOW', 'POST_PIXEL')


def _remove_draw_handler():
    """Guarded, and safe to call twice: unregister runs on reload too."""

    import bpy

    global _draw_handle

    if _draw_handle is not None:
        try:
            bpy.types.SpaceCadexTraining.draw_handler_remove(
                _draw_handle, 'WINDOW')
        except Exception:
            pass
        _draw_handle = None


def register():
    # Registered for the add-on's whole life rather than per-run: the
    # handler's first act is the same read_progress the panel's poll makes,
    # so with no run in flight a redraw costs one cached stat and draws
    # nothing.
    _add_draw_handler()


def unregister():
    _remove_draw_handler()
    global _shader
    _shader = None
