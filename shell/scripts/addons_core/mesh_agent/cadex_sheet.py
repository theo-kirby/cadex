# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Compose a blueprint sheet: which views, what each cell shows, how they
tile, and the drawing-sheet dressing around them (ADR-151).

ADR-150's sheet was fixed: four views, one 2x2 grid, nothing per cell. This
module is what makes it composable — the agent names the views (the named
orthos, the three-quarter, a custom azimuth/elevation, or the parameters
panel), gives each cell its own hidden outputs, exploded factor, section
override and part-name callouts, and picks a layout. The default is the
**triptych** (:data:`DEFAULT_VIEWS`), on a 16:9 sheet (ADR-153).

Three responsibilities, three groups of functions:

- **the spec** — :func:`normalize_views` and :func:`choose_layout` turn the
  tool's free-form input into validated specs and a layout template, refusing
  in full sentences that carry the fix. Structural only: no scene, no bpy.
- **the tiling** — :func:`layout_rects` places the cells by shared integer
  boundary arrays, so no-gap/no-overlap holds by construction, at any size.
  :func:`zone_grid`, :func:`title_lines` and :func:`cell_legend` are the
  dressing arithmetic: the page grid with border zone marks (1, 2, 3 along
  the top, A, B, C down the left — a drawing office's zones, not graph
  paper), the title texts, and the caption.
- **the scene state** — the bpy half. :func:`snapshot_state` captures the
  live presentation ONCE, :func:`apply_view_state` puts one cell's overrides
  on the scene (hides by ``hide_set`` — ``hide_viewport`` is the hydrate
  path's channel; explode, then section, in that order, because the wire
  clip bakes the plane in each object's own frame), and
  :func:`restore_state` is one flat, exception-hardened restore — not
  per-view undo stacks, so a failure on view 3 of 5 still restores from the
  original snapshot. :func:`_dress_sheet` draws the dressing over the
  composited tile field in a second offscreen pass, with the blf recipe the
  in-tree font tests prove.

The pure half — everything above ``-- the bpy half --`` — imports no
``bpy`` (it may import :mod:`capture`'s pure tables). It is the half the
headless suite pins and the half Phase 12 keeps.
"""

import math

#: The most views one sheet takes. Sheets are cheap: compose another rather
#: than cram.
MAX_VIEWS = 6

LAYOUTS = ("auto", "single", "row", "column", "grid", "hero", "triptych",
           "mosaic")

#: The mosaic's grid never exceeds this many rows or columns: with at most
#: six views, a finer grid is empty space pretending to be composition.
MAX_GRID = 6

#: The sheet's default proportions (ADR-153): a 16:9 field, the shape of
#: the screens the sheet is read on. ``aspect`` is optional — any
#: ``"width:height"`` string works, and ``"auto"`` keeps the pre-ADR-153
#: shapes (square fields; a row or column as wide or tall as its cells; a
#: mosaic shaped like its grid). The mosaic alone defaults to ``auto``,
#: because its shape IS the agent's grid.
DEFAULT_ASPECT = "16:9"

#: How much of the sheet's width the hero cell takes, on the right.
HERO_FRACTION = 2.0 / 3.0

#: What an omitted ``views`` means (the owner-chosen default, ADR-151
#: addendum): front, top and bottom stacked down the left third, the
#: three-quarter perspective filling the centre third, and the same
#: perspective spun 180 degrees about Z — the rear three-quarter — fully
#: exploded in the right third. The renderer drops the explode override
#: gracefully when the model declares no exploded view (or a simulation is
#: baked), so the default never refuses a plain part.
DEFAULT_VIEWS = (
    {"view": "front"},
    {"view": "top"},
    {"view": "bottom"},
    {"view": "three-quarter"},
    {"view": "custom", "azimuth": 225.0, "elevation": 25.0, "explode": 1.0},
)

#: Dressing alphas, all on the theme's line colour (white), all fainter than
#: the model lines. Tuned against the windowed probe's PNGs.
SUB_GRID_ALPHA = 0.05
ZONE_GRID_ALPHA = 0.12
FRAME_ALPHA = 0.5
LABEL_ALPHA = 0.45
TITLE_ALPHA = 0.6

#: Callout dressing (ADR-153): the part names and their leader lines are
#: content, not dressing, so they sit above the dressing alphas.
CALLOUT_TEXT_ALPHA = 0.85
CALLOUT_LINE_ALPHA = 0.55

#: The wider fit a callout cell renders with, so the part names have a band
#: of ground to sit on either side of the model.
CALLOUT_FIT_MARGIN = 1.45

#: Narrower than this, a cell has no label band worth the name — the text
#: lands on the model instead of beside it (measured on a 256 px sheet,
#: whose triptych columns are 85 px). Such a cell drops its callouts and
#: says so, rather than drawing them over the part.
CALLOUT_MIN_WIDTH = 240

#: The keys one view object may carry, flat on purpose: a schema one nesting
#: level deep is a schema the model fills correctly.
SPEC_KEYS = ("view", "azimuth", "elevation", "projection", "hide", "only",
             "explode", "section", "section_offset_mm", "section_flip",
             "hero", "cell", "span", "callouts")

_SECTION_AXES = ("X", "Y", "Z")


# -- the pure half: no bpy, no scene ----------------------------------------

def margin_px(sheet_size):
    """The margin band's width: scales with the sheet, floored so the zone
    labels stay legible at 256."""

    return max(20, int(sheet_size) // 40)


def _view_names():
    from . import capture
    return tuple(capture.NAMED_VIEWS)


def display_color(linear_rgb):
    """A linear theme colour as the viewport shows it: sRGB-encoded.

    The tiles come back from ``draw_view3d`` colour-managed, while an
    offscreen ``clear`` takes raw values — clearing with the linear theme
    ground gave the sheet a visibly darker margin band (the probe measured
    it, and the owner asked for one uniform colour). The renderer prefers
    sampling the composited field itself; this is the deterministic
    fallback, and the half a pure test can pin.
    """

    def encode(channel):
        channel = max(0.0, min(1.0, float(channel)))
        if channel <= 0.0031308:
            return 12.92 * channel
        return 1.055 * channel ** (1.0 / 2.4) - 0.055

    return tuple(encode(channel) for channel in linear_rgb)


def sheet_aspect(aspect, template):
    """The tile field's width:height as a ratio: ``(ratio, "")`` or
    ``(None, "")`` for the layout-derived shape, or ``(None, refusal)``.

    An omitted ``aspect`` means :data:`DEFAULT_ASPECT` — except for the
    mosaic, whose shape is the agent's grid and stays ``auto`` unless the
    agent says otherwise.
    """

    if aspect is None:
        aspect = "auto" if template == "mosaic" else DEFAULT_ASPECT
    text = str(aspect).strip().lower()
    if text == "auto":
        return None, ""
    parts = text.split(":")
    width = height = 0.0
    if len(parts) == 2:
        try:
            width, height = float(parts[0]), float(parts[1])
        except ValueError:
            width = height = 0.0
    if width <= 0.0 or height <= 0.0:
        return None, ("aspect must be 'width:height' (like '16:9') or "
                      "'auto' to follow the layout; got {!r}.".format(aspect))
    ratio = width / height
    if not 0.2 <= ratio <= 5.0:
        return None, ("aspect {!r} is extreme; keep width:height between "
                      "1:5 and 5:1.".format(aspect))
    return ratio, ""


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def normalize_views(raw, output_names):
    """The tool's ``views`` input into validated specs: ``(specs, "")`` or
    ``(None, refusal)``.

    Structural validation only — everything checkable without a scene.
    Defaults filled: an omitted ``views`` is :data:`DEFAULT_VIEWS`.
    Duplicates are allowed on purpose (front-with-housing-hidden beside a
    plain front is a legitimate sheet). Each spec is ready for
    ``capture.fit_view`` (it carries ``name``/``up``/``ortho`` and either
    ``direction`` or ``azimuth``/``elevation``) plus the per-cell overrides.
    """

    from . import capture

    outputs = tuple(str(name) for name in (output_names or ()))
    defaults = raw is None
    if defaults:
        raw = [dict(item) for item in DEFAULT_VIEWS]
    if not isinstance(raw, (list, tuple)):
        return None, ("views must be a list of view objects; got {:s}. Omit "
                      "it for the default sheet.".format(
                          type(raw).__name__))
    if not raw:
        return None, ("views is empty; omit it for the default sheet, or "
                      "name at least one view.")
    if len(raw) > MAX_VIEWS:
        return None, ("make_blueprint takes at most {:d} views; got {:d}. "
                      "Compose two sheets instead.".format(MAX_VIEWS,
                                                           len(raw)))

    specs = []
    hero_at = None
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            return None, ("views[{:d}] must be an object naming a view; got "
                          "{!r}.".format(index, item))
        unknown = sorted(set(item) - set(SPEC_KEYS))
        if unknown:
            return None, ("views[{:d}] carries unknown key(s) {:s}; the keys "
                          "are: {:s}.".format(index,
                                              ", ".join(map(repr, unknown)),
                                              ", ".join(SPEC_KEYS)))

        name = str(item.get("view") or "").strip()
        named = capture.NAMED_VIEWS.get(name)
        if named is None and name not in ("custom", "params"):
            return None, ("Unknown view {!r} in views[{:d}]; one of: {:s}, "
                          "custom with azimuth/elevation, or params for "
                          "the parameters panel.".format(
                              name, index, ", ".join(_view_names())))

        hero = bool(item.get("hero"))
        if hero:
            if hero_at is not None:
                return None, ("views[{:d}] and views[{:d}] are both flagged "
                              "hero; a sheet has one hero cell. Drop "
                              "one.".format(hero_at, index))
            hero_at = index

        # Mosaic placement: cell = [row, column], 1-based from the
        # top-left (the zone marks' reading order); span = [rows, columns].
        cell = item.get("cell")
        span = item.get("span")
        if span is not None and cell is None:
            return None, ("views[{:d}] carries span but no cell; place "
                          "the cell first ([row, column], 1-based from "
                          "the top-left).".format(index))

        def _pair(value):
            return (isinstance(value, (list, tuple)) and len(value) == 2
                    and all(isinstance(part, int)
                            and not isinstance(part, bool)
                            and part >= 1 for part in value))

        if cell is not None:
            if not _pair(cell):
                return None, ("views[{:d}].cell must be [row, column], "
                              "1-based integers from the "
                              "top-left.".format(index))
            if span is None:
                span = (1, 1)
            elif not _pair(span):
                return None, ("views[{:d}].span must be [rows, columns], "
                              "each at least 1.".format(index))
            if (cell[0] + span[0] - 1 > MAX_GRID
                    or cell[1] + span[1] - 1 > MAX_GRID):
                return None, ("A mosaic goes up to {:d} rows and {:d} "
                              "columns; views[{:d}] reaches past "
                              "that.".format(MAX_GRID, MAX_GRID, index))

        # The parameters panel (ADR-153): a cell of the sheet, not of the
        # model — it renders the declared parameters as labelled sliders
        # at their current values, so it takes placement keys and nothing
        # that steers a camera or the scene.
        if name == "params":
            taken = sorted(key for key in ("azimuth", "elevation",
                                           "projection", "hide", "only",
                                           "explode", "section",
                                           "section_offset_mm",
                                           "section_flip", "callouts")
                           if item.get(key) is not None)
            if taken:
                return None, ("views[{:d}] is the parameters panel; it "
                              "takes only cell, span and hero — drop "
                              "{:s}.".format(index, ", ".join(taken)))
            spec = {"view": "params", "up": (0.0, 0.0, 1.0), "ortho": True,
                    "name": "parameters", "label": "parameters",
                    "hide": (), "only": (), "explode": None,
                    "section": None, "hero": hero, "callouts": None}
            if cell is not None:
                spec["cell"] = (int(cell[0]), int(cell[1]))
                spec["span"] = (int(span[0]), int(span[1]))
            specs.append(spec)
            continue

        has_angles = "azimuth" in item or "elevation" in item
        if named is not None and has_angles:
            return None, ("views[{:d}] is {!r} but carries azimuth/"
                          "elevation; angles belong to view 'custom' "
                          "only.".format(index, name))
        if name == "custom":
            if not ("azimuth" in item and "elevation" in item):
                return None, ("views[{:d}] is custom but does not give both "
                              "azimuth and elevation; give both angles in "
                              "degrees.".format(index))
            if not (_is_number(item["azimuth"])
                    and _is_number(item["elevation"])):
                return None, ("views[{:d}]'s azimuth/elevation must be "
                              "numbers in degrees.".format(index))

        projection = item.get("projection")
        if projection is not None and projection not in ("ortho",
                                                         "perspective"):
            return None, ("views[{:d}].projection is {!r}; 'ortho' or "
                          "'perspective'.".format(index, projection))

        hide = item.get("hide")
        if hide is None:
            hide = ()
        if not isinstance(hide, (list, tuple)) or any(
                not isinstance(entry, str) for entry in hide):
            return None, ("views[{:d}].hide must be a list of declared "
                          "output names.".format(index))
        missing = [entry for entry in hide if entry not in outputs]
        if missing:
            return None, ("views[{:d}].hide names no declared output: "
                          "{:s}. Outputs: {:s}.".format(
                              index,
                              ", ".join(map(repr, missing)),
                              ", ".join(outputs)
                              or "none are declared yet; rebuild first"))

        # `only` is the isolate: show just these outputs, hide the rest --
        # a gearbox cell that names two gears instead of hiding fourteen.
        # Normalized here into the SAME hide tuple the apply path already
        # honours, so isolating costs the state machinery nothing.
        only = item.get("only")
        if only is not None:
            if hide:
                return None, ("views[{:d}] carries both hide and only; "
                              "only already hides everything else. Use "
                              "one.".format(index))
            if (not isinstance(only, (list, tuple)) or not only
                    or any(not isinstance(entry, str) for entry in only)):
                return None, ("views[{:d}].only must be a non-empty list "
                              "of declared output names.".format(index))
            missing = [entry for entry in only if entry not in outputs]
            if missing:
                return None, ("views[{:d}].only names no declared output: "
                              "{:s}. Outputs: {:s}.".format(
                                  index,
                                  ", ".join(map(repr, missing)),
                                  ", ".join(outputs)
                                  or "none are declared yet; rebuild "
                                     "first"))
            shown = set(only)
            hide = tuple(name for name in outputs if name not in shown)

        explode = item.get("explode")
        if explode is not None:
            if not _is_number(explode) or not 0.0 <= float(explode) <= 1.0:
                return None, ("views[{:d}].explode is {!r}; the factor runs "
                              "0 (assembled) to 1 (fully "
                              "exploded).".format(index, explode))
            explode = float(explode)

        section_raw = item.get("section")
        offset = item.get("section_offset_mm")
        flip = item.get("section_flip")
        if section_raw is None:
            if offset is not None or flip is not None:
                return None, ("views[{:d}] carries section_offset_mm/"
                              "section_flip but no section axis; set "
                              "section to X, Y or Z.".format(index))
            section = None
        elif str(section_raw).lower() == "off":
            if offset is not None or flip is not None:
                return None, ("views[{:d}] lifts the section (section: "
                              "'off') but still carries section_offset_mm/"
                              "section_flip; drop them.".format(index))
            section = "off"
        elif str(section_raw).upper() in _SECTION_AXES:
            if offset is not None and not _is_number(offset):
                return None, ("views[{:d}].section_offset_mm must be a "
                              "number in mm.".format(index))
            section = {"axis": str(section_raw).upper(),
                       "offset_mm": float(offset) if offset is not None
                       else None,
                       "flip": bool(flip)}
        else:
            return None, ("views[{:d}].section is {!r}; one of X, Y, Z, or "
                          "'off' to lift a live cut in this "
                          "cell.".format(index, section_raw))

        # Callouts: the part names with leader lines. Omitted, they switch
        # on with an exploded cell — :func:`callouts_active` is the rule.
        callouts = item.get("callouts")
        if callouts is not None and not isinstance(callouts, bool):
            return None, ("views[{:d}].callouts must be true or "
                          "false.".format(index))

        if named is not None:
            label = name
            spec = {
                "view": name,
                "up": tuple(named["up"]),
                "ortho": (named["ortho"] if projection is None
                          else projection == "ortho"),
            }
            if "direction" in named:
                spec["direction"] = tuple(named["direction"])
            else:
                spec["azimuth"] = float(named["azimuth"])
                spec["elevation"] = float(named["elevation"])
        else:
            azimuth = float(item["azimuth"])
            elevation = float(item["elevation"])
            label = "custom {:g}/{:g}".format(azimuth, elevation)
            spec = {
                "view": "custom",
                "azimuth": azimuth,
                "elevation": elevation,
                "up": (0.0, 0.0, 1.0),
                "ortho": (projection == "ortho" if projection is not None
                          else False),
            }
        spec.update({
            "name": label,
            "label": label,
            "hide": tuple(hide),
            "only": tuple(only) if only else (),
            "explode": explode,
            "section": section,
            "hero": hero,
            "callouts": callouts,
        })
        if cell is not None:
            spec["cell"] = (int(cell[0]), int(cell[1]))
            spec["span"] = (int(span[0]), int(span[1]))
        specs.append(spec)
    if defaults:
        # The default right column reads as what it is, not as its angles.
        specs[-1]["name"] = specs[-1]["label"] = "exploded"
    return tuple(specs), ""


def choose_layout(layout, specs):
    """``(template, hero_index, "")`` or ``(None, None, refusal)``.

    ``auto``: mosaic when the views carry cell placements; single for one
    view; hero when a view is flagged hero or exactly one perspective sits
    among orthos; row for two; grid otherwise. A hero template with one
    view degenerates to single. A mosaic's placements are checked here —
    every view placed, no two overlapping — because the tiling invariant
    the templates hold by construction, freeform placement must hold by
    refusal (ADR-152). Holes are allowed on purpose: an empty grid cell is
    uniform ground, and asymmetry is what the mosaic is for.
    """

    layout = str(layout or "auto")
    if layout not in LAYOUTS:
        return None, None, ("Unknown layout {!r}; one of: {:s}.".format(
            layout, ", ".join(LAYOUTS)))

    count = len(specs)
    placed = [index for index, spec in enumerate(specs)
              if spec.get("cell") is not None]
    if placed and len(placed) != count:
        unplaced = next(index for index in range(count)
                        if index not in placed)
        return None, None, ("A mosaic places every view by cell, but "
                            "views[{:d}] has none; give every view a cell "
                            "([row, column]) or drop them "
                            "all.".format(unplaced))
    if placed and layout not in ("auto", "mosaic"):
        return None, None, ("The views carry cell placements; use layout "
                            "'mosaic' (or 'auto'), not "
                            "{!r}.".format(layout))
    if layout == "mosaic" and not placed:
        return None, None, ("Layout 'mosaic' places views by cell; give "
                            "every view a cell ([row, column], 1-based "
                            "from the top-left) and an optional span.")
    if placed:
        taken = {}
        for index, spec in enumerate(specs):
            row0, col0 = spec["cell"]
            row_span, col_span = spec["span"]
            for row in range(row0, row0 + row_span):
                for col in range(col0, col0 + col_span):
                    if (row, col) in taken:
                        return None, None, (
                            "views[{:d}] and views[{:d}] overlap on the "
                            "mosaic at row {:d}, column {:d}; cells and "
                            "spans must not overlap.".format(
                                taken[(row, col)], index, row, col))
                    taken[(row, col)] = index
        return "mosaic", None, ""

    flagged = [index for index, spec in enumerate(specs) if spec.get("hero")]
    perspectives = [index for index, spec in enumerate(specs)
                    if not spec["ortho"]]

    if layout == "auto":
        if count == 1:
            template = "single"
        elif flagged or len(perspectives) == 1:
            template = "hero"
        elif count == 2:
            template = "row"
        else:
            template = "grid"
    else:
        template = layout
    if template == "single" and count > 1:
        return None, None, ("Layout 'single' takes one view; got {:d}. Use "
                            "row, column, grid or hero.".format(count))
    if template == "triptych" and count < 3:
        return None, None, ("Layout 'triptych' takes at least 3 views (the "
                            "last two fill the centre and right columns); "
                            "got {:d}. Use row or single.".format(count))
    if template == "hero" and count == 1:
        template = "single"

    hero_index = None
    if template == "hero":
        if flagged:
            hero_index = flagged[0]
        elif len(perspectives) == 1:
            hero_index = perspectives[0]
        else:
            hero_index = count - 1
    return template, hero_index, ""


def _boundaries(total, cells):
    """Shared integer boundaries: ``cells + 1`` positions spanning exactly
    ``[0, total]``, so adjacent rects share an edge by construction."""

    return [int(round(index * total / float(cells)))
            for index in range(cells + 1)]


def layout_rects(template, count, max_size, hero=None, cells=None,
                 aspect=None):
    """``(rects, width, height)`` — one ``(x, y, w, h)`` per view, in view
    order, ``y`` measured from the BOTTOM (the buffer layout).

    ``cells`` drives the ``mosaic`` template: one ``(row, col, row_span,
    col_span)`` per view, 1-based from the top-left, already
    overlap-checked by :func:`choose_layout`. The grid's extent is inferred
    from the placements (no separate rows/columns knob to disagree with
    them) and a grid cell no view claims stays uniform ground.

    ``max_size`` is the tile field's longest edge; the margin band is the
    caller's to add. ``aspect`` is the field's width:height ratio from
    :func:`sheet_aspect`; ``None`` keeps each template's own shape — a
    square field, a row or column as wide or tall as its cells, a mosaic
    shaped like its grid. ``hero`` places the flagged view's cell: the
    right :data:`HERO_FRACTION` of the field at full height, the small
    views stacked top-down in the left column.
    """

    size = max(8, int(max_size))
    count = max(1, int(count))

    def field(ratio):
        if ratio is None:
            return size, size
        if ratio >= 1.0:
            return size, max(8, int(round(size / ratio)))
        return max(8, int(round(size * ratio))), size

    if template == "mosaic" and cells:
        rows = max(row + row_span - 1
                   for row, _col, row_span, _col_span in cells)
        columns = max(col + col_span - 1
                      for _row, col, _row_span, col_span in cells)
        width, height = field(aspect if aspect is not None
                              else columns / float(rows))
        xs = _boundaries(width, columns)
        ys = _boundaries(height, rows)
        rects = []
        for row, col, row_span, col_span in cells:
            top0, top1 = ys[row - 1], ys[row - 1 + row_span]
            rects.append((xs[col - 1], height - top1,
                          xs[col - 1 + col_span] - xs[col - 1],
                          top1 - top0))
        return rects, width, height

    if template == "single" or count == 1:
        width, height = field(aspect)
        return [(0, 0, width, height)], width, height

    if template == "row":
        width, height = field(aspect if aspect is not None
                              else float(count))
        xs = _boundaries(width, count)
        return ([(xs[i], 0, xs[i + 1] - xs[i], height)
                 for i in range(count)], width, height)

    if template == "column":
        width, height = field(aspect if aspect is not None
                              else 1.0 / count)
        ys = _boundaries(height, count)
        # View order runs top to bottom; the buffer's y runs bottom-up.
        return ([(0, height - ys[i + 1], width, ys[i + 1] - ys[i])
                 for i in range(count)], width, height)

    if template == "hero":
        width, height = field(aspect)
        hero = count - 1 if hero is None else int(hero)
        hero_width = int(round(width * HERO_FRACTION))
        left_width = width - hero_width
        ys = _boundaries(height, count - 1)
        rects = [None] * count
        rects[hero] = (left_width, 0, hero_width, height)
        slot = 0
        for index in range(count):
            if index == hero:
                continue
            rects[index] = (0, height - ys[slot + 1], left_width,
                            ys[slot + 1] - ys[slot])
            slot += 1
        return rects, width, height

    if template == "triptych":
        if count == 2:
            # choose_layout refuses this; called directly, degrade to a row
            # rather than tile two columns of a three-column field.
            return layout_rects("row", count, size, aspect=aspect)
        # Three equal columns: views[:-2] stack down the left, views[-2]
        # fills the centre at full height, views[-1] the right.
        width, height = field(aspect)
        xs = _boundaries(width, 3)
        ys = _boundaries(height, count - 2)
        rects = [(0, height - ys[index + 1], xs[1],
                  ys[index + 1] - ys[index])
                 for index in range(count - 2)]
        rects.append((xs[1], 0, xs[2] - xs[1], height))
        rects.append((xs[2], 0, xs[3] - xs[2], height))
        return rects, width, height

    # grid: near-square, the partial last row widened to span (no hole).
    width, height = field(aspect)
    columns = int(math.ceil(math.sqrt(count)))
    rows = int(math.ceil(count / float(columns)))
    ys = _boundaries(height, rows)
    rects = []
    placed = 0
    for row in range(rows):
        in_row = min(columns, count - placed)
        xs = _boundaries(width, in_row)
        top0, top1 = ys[row], ys[row + 1]
        for cell in range(in_row):
            rects.append((xs[cell], height - top1, xs[cell + 1] - xs[cell],
                          top1 - top0))
            placed += 1
    return rects, width, height


def callouts_active(spec):
    """Whether a cell gets part-name callouts: an explicit ``callouts``
    wins; omitted, they switch on with an exploded cell (factor > 0) — the
    classic exploded diagram names its parts."""

    flag = spec.get("callouts")
    if flag is not None:
        return bool(flag)
    explode = spec.get("explode")
    return explode is not None and float(explode) > 0.0


def callout_layout(anchors, rect_w, rect_h, text_size, top_pad=0.0):
    """Place one cell's part-name callouts: ``(entries, dropped)``.

    ``anchors`` is ``[(name, x, y)]`` in CELL-local pixels (``y`` from the
    bottom, the buffer layout). Labels go to the side their anchor is on,
    stack top-down at a minimum spacing, and drop — counted, so the
    caption can say so — when the cell cannot fit them all. Each entry is
    ``{"name", "side", "label_x", "label_y", "anchor"}`` with ``label_x``
    the OUTER text edge (left side: the text begins there; right side: it
    ends there). The bpy half measures the glyphs and draws the leader
    from the text's inner edge, through an elbow, to the anchor.

    ``top_pad`` keeps the top rows clear of the cell's view label.
    """

    text_size = float(text_size)
    pad = max(4.0, text_size * 0.4)
    low = pad
    high = float(rect_h) - pad - text_size - float(top_pad)
    spacing = text_size + 6.0
    if high <= low or rect_w < CALLOUT_MIN_WIDTH:
        return (), len(anchors)
    capacity = int((high - low) / spacing) + 1

    entries = []
    dropped = 0
    for side in ("left", "right"):
        mine = [(name, x, y) for name, x, y in anchors
                if (x < rect_w / 2.0) == (side == "left")]
        mine.sort(key=lambda anchor: -anchor[2])
        if len(mine) > capacity:
            dropped += len(mine) - capacity
            mine = mine[:capacity]
        placed = []
        previous = None
        for name, ax, ay in mine:
            y = min(max(ay - text_size / 2.0, low), high)
            if previous is not None:
                y = min(y, previous - spacing)
            y = max(y, low)
            placed.append({"name": name, "side": side,
                           "label_x": pad if side == "left"
                           else rect_w - pad,
                           "label_y": y, "anchor": (ax, ay)})
            previous = y
        # The bottom clamp can stack rows onto each other; walk back up.
        # Capacity guarantees the walk stays under ``high``.
        for index in range(len(placed) - 2, -1, -1):
            floor = placed[index + 1]["label_y"] + spacing
            if placed[index]["label_y"] < floor:
                placed[index]["label_y"] = floor
        entries.extend(placed)
    return tuple(entries), dropped


def param_rows(specs, values):
    """Engine ``param_specs`` plus current values, as drawable rows.

    Mirrors ``cadex_backend._bridge_params``'s range defaulting on
    purpose, so the panel shows the sliders the user actually has: an
    undeclared min/max becomes the same usable range the sidebar shows.
    Each row: ``{"name", "label", "value_text", "fraction", "min",
    "max"}``, the fraction clamped to [0, 1].
    """

    rows = []
    for spec in specs or ():
        name = str(spec.get("name") or "")
        if not name:
            continue
        try:
            default = float(spec.get("default") or 0.0)
        except (TypeError, ValueError):
            default = 0.0
        low = spec.get("min")
        high = spec.get("max")
        if low is None:
            low = 0.0 if default >= 0.0 else default * 4.0
        if high is None:
            high = default * 4.0 if default > 0.0 else 1.0
        low, high = float(low), float(high)
        if high <= low:
            high = low + 1.0
        label = (str(spec.get("label") or "")
                 or name.replace("_", " ").title())
        unit = str(spec.get("unit") or "")
        value = values.get(name, default) if values else default
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = default
        fraction = (value - low) / (high - low)
        fraction = max(0.0, min(1.0, fraction))
        text = "{:g}".format(value)
        if unit:
            text += " " + unit
        rows.append({"name": name, "label": label, "value_text": text,
                     "fraction": fraction, "min": low, "max": high})
    return tuple(rows)


def params_panel_layout(count, width, height):
    """How a params cell divides into rows: ``{"pad", "row_height",
    "text_size", "shown", "more"}``.

    ``shown`` rows are drawn; when they do not all fit, the last visible
    slot becomes a ``+N more`` line and ``more`` counts what it covers.
    """

    width, height = int(width), int(height)
    pad = max(10, min(width, height) // 18)
    usable = max(1.0, height - 2.0 * pad)
    row_height = max(24.0, min(46.0, usable / max(1, int(count))))
    fits = max(0, int(usable // row_height))
    shown = min(int(count), fits)
    if shown < count and shown > 0:
        shown -= 1
    return {"pad": pad, "row_height": row_height,
            "text_size": max(9.0, min(14.0, row_height * 0.38)),
            "shown": shown, "more": int(count) - shown}


def zone_grid(width, height):
    """The page grid's geometry, over the WHOLE sheet.

    Zone pitch snapped to a round pixel count; a finer sub-grid at a fifth
    of it; columns numbered ``1..`` along the top band and rows lettered
    ``A..`` down the left band, the way a drawing office divides a sheet
    (the owner chose zones over per-view mm graph paper). All positions in
    buffer coordinates: x from the left, y from the BOTTOM.
    """

    width, height = int(width), int(height)
    pitch = max(40, int(round(width / 80.0)) * 10)
    sub = pitch / 5.0

    verticals = [float(x) for x in range(pitch, width, pitch)]
    horizontals = [float(height - y) for y in range(pitch, height, pitch)]
    sub_verticals = [index * sub
                     for index in range(1, int(math.ceil(width / sub)))
                     if index % 5]
    sub_horizontals = [height - index * sub
                       for index in range(1, int(math.ceil(height / sub)))
                       if index % 5]

    columns = []
    for index in range(int(math.ceil(width / float(pitch)))):
        left, right = index * pitch, min((index + 1) * pitch, width)
        columns.append((str(index + 1), (left + right) / 2.0))
    rows = []
    for index in range(int(math.ceil(height / float(pitch)))):
        top0, top1 = index * pitch, min((index + 1) * pitch, height)
        rows.append((chr(ord("A") + index % 26),
                     height - (top0 + top1) / 2.0))
    return {
        "pitch": pitch,
        "sub_pitch": sub,
        "verticals": verticals,
        "horizontals": horizontals,
        "sub_verticals": sub_verticals,
        "sub_horizontals": sub_horizontals,
        "columns": columns,
        "rows": rows,
    }


def title_lines(project, version, revision, date, theme):
    """The two text groups of the title dressing.

    Top-left: the project name. Bottom-right: the application line —
    ``CADEX <version>``, the revision this sheet is attached to, the date
    and the theme. A missing version reads ``dev`` rather than nothing:
    a sheet from a source tree should say so.
    """

    right = "CADEX {:s}".format(str(version or "").strip() or "dev")
    revision = str(revision or "").strip()
    if revision:
        right += "  ·  rev {:s}".format(revision[:12])
    if date:
        right += "  ·  {:s}".format(str(date))
    if theme:
        right += "  ·  {:s}".format(str(theme))
    lines = []
    project = str(project or "").strip()
    if project:
        lines.append({"corner": "top-left", "text": project})
    lines.append({"corner": "bottom-right", "text": right})
    return tuple(lines)


#: What each named view is, for the caption. The quadrant wording ADR-150
#: used lives on in ``capture.quadrant_legend`` for render_views.
VIEW_DESCRIPTIONS = {
    "front": "front (camera on -Y)",
    "back": "back (camera on +Y)",
    "left": "left (camera on -X)",
    "right": "right (camera on +X)",
    "top": "top (looking down)",
    "bottom": "bottom (looking up)",
    "three-quarter": ("three-quarter perspective (azimuth 45 deg, "
                      "elevation 25 deg)"),
}


def cell_legend(specs, rects):
    """One sentence per cell, naming its place, its view and its overrides.

    Returned as text rather than relied on from the pixels: the caption is
    what the agent reads back, and it must say what each cell shows even
    when the cell labels are too small to read.
    """

    width = max(x + w for x, _y, w, _h in rects)
    height = max(y + h for _x, y, _w, h in rects)
    areas = [w * h for _x, _y, w, h in rects]
    largest = max(areas)
    parts = []
    for index, (spec, rect) in enumerate(zip(specs, rects)):
        x, y, w, h = rect
        cx, cy = x + w / 2.0, y + h / 2.0
        if len(rects) == 1:
            where = "full sheet"
        else:
            words = []
            if areas[index] == largest and areas.count(largest) == 1:
                words.append("large")
            # Horizontal placement by which field edges the cell touches:
            # a centre column touches neither, whatever its centre rounds to.
            if x == 0 and x + w == width:
                words.append("full width")
            elif x + w == width:
                words.append("right")
            elif x == 0:
                words.append("left")
            else:
                words.append("centre")
            if h < height:
                words.append("top" if cy > 2.0 * height / 3.0 else
                             "bottom" if cy < height / 3.0 else "middle")
            where = ", ".join(words)

        if spec["view"] == "params":
            described = "parameters panel"
        elif spec["view"] == "custom":
            described = "custom {:s} (azimuth {:g} deg, elevation {:g} deg)".format(
                "ortho" if spec["ortho"] else "perspective",
                spec["azimuth"], spec["elevation"])
        else:
            described = VIEW_DESCRIPTIONS.get(spec["view"], spec["view"])
        if spec.get("only"):
            notes = ["only {:s} shown".format(", ".join(spec["only"]))]
        else:
            notes = ["{:s} hidden".format(name) for name in spec["hide"]]
        if spec.get("explode") is not None:
            notes.append("exploded {:g}".format(spec["explode"]))
        section = spec.get("section")
        if section == "off":
            notes.append("section lifted")
        elif isinstance(section, dict):
            note = "cut on {:s}".format(section["axis"])
            if section.get("offset_mm") is not None:
                note += " at {:g} mm".format(section["offset_mm"])
            if section.get("flip"):
                note += ", flipped"
            notes.append(note)
        if spec["view"] != "params" and callouts_active(spec):
            notes.append("parts named")
        sentence = "cell {:d} ({:s}): {:s}".format(index + 1, where,
                                                   described)
        if notes:
            sentence += ", " + ", ".join(notes)
        parts.append(sentence)
    return "; ".join(parts)


def spec_meta(spec):
    """The JSON-safe record of one spec, for ``put_blueprint``'s ``meta``."""

    if spec["view"] == "params":
        meta = {"view": "params", "label": spec["label"]}
        if spec.get("cell") is not None:
            meta["cell"] = list(spec["cell"])
            meta["span"] = list(spec["span"])
        if spec.get("hero"):
            meta["hero"] = True
        return meta

    meta = {
        "view": spec["view"],
        "label": spec["label"],
        "projection": "ortho" if spec["ortho"] else "perspective",
    }
    if spec.get("callouts") is not None:
        meta["callouts"] = bool(spec["callouts"])
    if spec["view"] == "custom":
        meta["azimuth"] = spec["azimuth"]
        meta["elevation"] = spec["elevation"]
    if spec.get("only"):
        meta["only"] = list(spec["only"])   # hide is only's derived complement
    elif spec["hide"]:
        meta["hide"] = list(spec["hide"])
    if spec.get("cell") is not None:
        meta["cell"] = list(spec["cell"])
        meta["span"] = list(spec["span"])
    if spec.get("explode") is not None:
        meta["explode"] = spec["explode"]
    section = spec.get("section")
    if section == "off":
        meta["section"] = "off"
    elif isinstance(section, dict):
        meta["section"] = dict(section)
    if spec.get("hero"):
        meta["hero"] = True
    return meta


# -- the bpy half -----------------------------------------------------------

def _scene_flag(scene, key):
    """A scene IDProperty report as a plain dict, or None."""

    if key not in scene:
        return None
    value = scene[key]
    try:
        return value.to_dict()
    except AttributeError:
        return dict(value)


def snapshot_state(scene):
    """Everything a composed sheet may change, captured ONCE before the loop.

    One flat snapshot rather than per-view undo stacks: whatever views 1..k
    did before view k+1 failed, the restore is always "put back what was
    here before view 1".
    """

    from . import cadex_explode
    from . import cadex_section

    explode = cadex_explode.settings(scene)
    section = cadex_section.settings(scene)
    return {
        "explode": ({"show": bool(explode.show),
                     "factor": float(explode.factor)}
                    if explode is not None else None),
        "section": ({"show": bool(section.show), "axis": str(section.axis),
                     "offset": float(section.offset),
                     "flip": bool(section.flip)}
                    if section is not None else None),
        "explode_flag": _scene_flag(scene, cadex_explode.SCENE_FLAG),
        "section_flag": _scene_flag(scene, cadex_section.SCENE_FLAG),
        "hides": {},           # {output: {"solid": was_hidden, "edges": ...}}
        "applied_hides": set(),  # outputs the CURRENT view hides
        "touched": set(),        # views currently overridden: explode/section
        "explode_ever": False,   # any view changed the factor at any point
    }


def _restore_hide(collection, name, prior):
    from . import cadex_hydrate

    for edges, key in ((False, "solid"), (True, "edges")):
        if key not in prior:
            continue
        obj = cadex_hydrate._find(collection, name, edges=edges)
        if obj is not None:
            obj.hide_set(bool(prior[key]))


def _apply_hides(scene, wanted, snapshot):
    """Hide this view's outputs, unhide what the previous view hid.

    ``hide_set``, never ``hide_viewport``: that channel is owned by
    ``cadex_hydrate._hide_instanced_sources``'s marker protocol, and both
    ``model_bbox``'s ``visible_get()`` and ``draw_view3d``'s depsgraph
    respect ``hide_set``. Each object's prior state is recorded once, on
    first touch, and the Edges child is hidden with its solid — parenting
    does not propagate visibility.
    """

    from . import cadex_hydrate

    try:
        collection = cadex_hydrate._model_collection()
    except Exception:
        return
    wanted = set(wanted)
    applied = snapshot["applied_hides"]
    for name in sorted(applied - wanted):
        _restore_hide(collection, name, snapshot["hides"].get(name) or {})
    for name in sorted(wanted - applied):
        prior = snapshot["hides"].get(name)
        record = prior is None
        if record:
            prior = {}
        for edges, key in ((False, "solid"), (True, "edges")):
            obj = cadex_hydrate._find(collection, name, edges=edges)
            if obj is None:
                continue
            if record:
                prior[key] = bool(obj.hide_get())
            obj.hide_set(True)
        if record:
            snapshot["hides"][name] = prior
    snapshot["applied_hides"] = wanted


def _restore_explode(scene, snapshot):
    from . import cadex_explode

    saved = snapshot.get("explode")
    group = cadex_explode.settings(scene)
    if group is None or saved is None:
        return
    with cadex_explode.quiet():
        group.show = bool(saved["show"])
        group.factor = float(saved["factor"])
    if saved["show"]:
        cadex_explode.refresh(scene)
    else:
        cadex_explode.clear(scene)


def _apply_explode(scene, value, snapshot):
    """Returns True when this call changed the exploded poses."""

    from . import cadex_explode

    group = cadex_explode.settings(scene)
    if group is None:
        return False
    if value is None:
        if "explode" in snapshot["touched"]:
            _restore_explode(scene, snapshot)
            snapshot["touched"].discard("explode")
            return True
        return False
    with cadex_explode.quiet():
        group.show = True
        group.factor = float(value)
    cadex_explode.refresh(scene)
    snapshot["touched"].add("explode")
    snapshot["explode_ever"] = True
    return True


def _restore_section(scene, snapshot):
    from . import cadex_section

    saved = snapshot.get("section")
    group = cadex_section.settings(scene)
    if group is None or saved is None:
        return
    with cadex_section.quiet():
        group.show = bool(saved["show"])
        group.axis = str(saved["axis"])
        group.offset = float(saved["offset"])
        group.flip = bool(saved["flip"])
    if saved["show"]:
        cadex_section.refresh(scene)
    else:
        cadex_section.clear(scene)


def _apply_section(scene, value, snapshot, explode_changed):
    """Always AFTER the explode: the wire clip bakes the plane in each
    object's OWN frame, so a component the explode just moved needs its
    clip recomputed (the ``_finish_preview`` ordering)."""

    from . import cadex_section

    group = cadex_section.settings(scene)
    if group is None:
        return
    if value is None:
        if "section" in snapshot["touched"]:
            _restore_section(scene, snapshot)
            snapshot["touched"].discard("section")
        elif explode_changed and group.show:
            cadex_section.refresh(scene)
        return
    if value == "off":
        with cadex_section.quiet():
            group.show = False
        cadex_section.refresh(scene)   # show False routes through clear()
        snapshot["touched"].add("section")
        return
    with cadex_section.quiet():
        group.show = True
        group.axis = str(value["axis"])
        group.flip = bool(value.get("flip"))
        offset = value.get("offset_mm")
        if offset is None:
            bounds = cadex_section.model_bounds()
            offset = (cadex_section.centre_offset(bounds, group.axis)
                      if bounds is not None else 0.0)
        group.offset = float(offset)
    cadex_section.refresh(scene)
    snapshot["touched"].add("section")


def apply_view_state(scene, spec, snapshot):
    """Put ONE cell's overrides on the scene, in the load-bearing order:
    hides, explode, section, settle. The caller measures ``model_bbox()``
    after this, so each cell's camera fits that cell's own state."""

    import bpy

    _apply_hides(scene, spec.get("hide") or (), snapshot)
    explode_changed = _apply_explode(scene, spec.get("explode"), snapshot)
    _apply_section(scene, spec.get("section"), snapshot, explode_changed)
    # Measured necessity (_isolate_model records it): bounds and modifier
    # results are recomputed during evaluation, and draw_view3d runs before
    # the event loop would get round to it.
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get()


def restore_state(scene, snapshot):
    """One flat restore from the original snapshot. Idempotent, and
    exception-hardened per phase: a failure unhiding must not cost the
    explode restore, and so on down."""

    import traceback

    import bpy
    from . import cadex_explode
    from . import cadex_hydrate
    from . import cadex_section

    try:
        collection = cadex_hydrate._model_collection()
        for name in sorted(snapshot.get("hides") or {}):
            _restore_hide(collection, name, snapshot["hides"][name])
        snapshot["hides"] = {}
        snapshot["applied_hides"] = set()
    except Exception:
        traceback.print_exc()

    try:
        if "explode" in snapshot["touched"]:
            _restore_explode(scene, snapshot)
            snapshot["touched"].discard("explode")
    except Exception:
        traceback.print_exc()

    try:
        if "section" in snapshot["touched"]:
            _restore_section(scene, snapshot)
            snapshot["touched"].discard("section")
        elif (snapshot.get("explode_ever")
              and (snapshot.get("section") or {}).get("show")):
            # A live section's wire clips were recomputed against exploded
            # poses mid-loop; the explode restore above moved the components
            # back, so the clips need one more pass at the solved poses.
            cadex_section.refresh(scene)
    except Exception:
        traceback.print_exc()

    try:
        for key, saved in ((cadex_explode.SCENE_FLAG,
                            snapshot.get("explode_flag")),
                           (cadex_section.SCENE_FLAG,
                            snapshot.get("section_flag"))):
            if saved is None:
                if key in scene:
                    del scene[key]
            else:
                scene[key] = saved
    except Exception:
        traceback.print_exc()

    try:
        bpy.context.view_layer.update()
        bpy.context.evaluated_depsgraph_get()
    except Exception:
        traceback.print_exc()


def validate_against_model(scene, specs):
    """The checks that need the scene: returns "" or the refusal.

    Runs BEFORE the background refusal, so a bad spec is refused for what
    is wrong with it even where nothing can render (gate-testable), and a
    valid spec still refuses headless in the unchanged sentence.
    """

    from . import cadex_animate
    from . import cadex_backend
    from . import cadex_explode
    from . import cadex_section

    wants_explode = [index for index, spec in enumerate(specs)
                     if spec.get("explode") is not None]
    if wants_explode:
        index = wants_explode[0]
        if cadex_explode.settings(scene) is None:
            return ("views[{:d}].explode: this file predates the exploded "
                    "view; save and reopen it.".format(index))
        # The direct-refresh path bypasses toggle(), so its two refusals are
        # re-checked here, in toggle()'s own sentences.
        if cadex_animate.SCENE_FLAG in scene:
            return ("views[{:d}].explode: A simulation is baked on these "
                    "components; clear the simulation first, then "
                    "explode.".format(index))
        root = cadex_backend.project_root(scene)
        display = dict(cadex_backend.last_accepted(root).get("display")
                       or {})
        entry, reason = cadex_explode.exploded_entry(display)
        if entry is None:
            return "views[{:d}].explode: {:s}".format(index, reason)

    wants_section = [index for index, spec in enumerate(specs)
                     if spec.get("section") is not None]
    if wants_section and cadex_section.settings(scene) is None:
        return ("views[{:d}].section: this file predates the section view; "
                "save and reopen it.".format(wants_section[0]))

    wants_params = [index for index, spec in enumerate(specs)
                    if spec["view"] == "params"]
    if wants_params:
        state = cadex_backend.cached_script_state(scene)
        if state is None or not getattr(state, "specs", None):
            return ("views[{:d}] asks for the parameters panel, but the "
                    "project script declares no parameters.".format(
                        wants_params[0]))
    return ""


def callout_anchors(names, hidden, fitted, width, height):
    """Each visible output's centre, projected into CELL pixels.

    ``fitted`` is :func:`capture.fit_view`'s dict for this cell — the
    anchors are measured through the same matrices the tile renders with,
    so a name points at the pixels its part occupies. Solids only: the
    Edges child traces the same geometry.
    """

    import bpy  # noqa: F401 -- the collection lookups need a live session
    from mathutils import Vector

    from . import cadex_hydrate
    from . import capture

    try:
        collection = cadex_hydrate._model_collection()
    except Exception:
        return []
    hidden = set(hidden or ())
    anchors = []
    for name in names:
        if name in hidden:
            continue
        obj = cadex_hydrate._find(collection, name, edges=False)
        if obj is None or not obj.visible_get():
            continue
        matrix = obj.matrix_world
        centre = Vector((0.0, 0.0, 0.0))
        for corner in obj.bound_box:
            centre += matrix @ Vector(corner)
        centre /= 8.0
        ndc = capture.project(fitted["view"], fitted["window"],
                              tuple(centre))
        if ndc is None:
            continue
        anchors.append((name,
                        (ndc[0] + 1.0) / 2.0 * width,
                        (ndc[1] + 1.0) / 2.0 * height))
    return anchors


_font_id = None


def _font():
    """The bundled DejaVuSansMono, or the default font id 0."""

    global _font_id

    if _font_id is None:
        import blf
        import bpy
        loaded = -1
        try:
            path = bpy.utils.system_resource(
                'DATAFILES', path="fonts/DejaVuSansMono.woff2")
            if path:
                loaded = blf.load(path)
        except Exception:
            loaded = -1
        _font_id = loaded if loaded >= 0 else 0
    return _font_id


def _draw_lines(segments, color, alpha, width=1.0):
    """Flat 2D segments in pixel space, through the dimension overlay's
    shader idiom (POLYLINE with the UNIFORM_COLOR fallback)."""

    import gpu
    from gpu_extras.batch import batch_for_shader

    from . import cadex_dimension

    shader, polyline = cadex_dimension._line_shader()
    if shader is None or not segments:
        return
    points = []
    for x1, y1, x2, y2 in segments:
        points.append((float(x1), float(y1)))
        points.append((float(x2), float(y2)))
    batch = batch_for_shader(shader, 'LINES', {"pos": points})
    shader.bind()
    shader.uniform_float("color", tuple(color) + (float(alpha),))
    if polyline:
        viewport = gpu.state.viewport_get()
        shader.uniform_float("viewportSize",
                             (float(viewport[2]), float(viewport[3])))
        shader.uniform_float("lineWidth", float(width))
    batch.draw(shader)


def _draw_text(font_id, text, x, y, size, color, alpha):
    import blf

    blf.size(font_id, float(size))      # this build's blf.size is two-arg
    blf.color(font_id, color[0], color[1], color[2], float(alpha))
    blf.position(font_id, float(x), float(y), 0.0)
    blf.draw(font_id, text)


def _text_width(font_id, text, size):
    import blf

    blf.size(font_id, float(size))
    return blf.dimensions(font_id, text)[0]


def _shorten(font_id, text, size, max_width):
    """Ellipsize to fit: a 256 px sheet cannot carry a long project name."""

    if _text_width(font_id, text, size) <= max_width:
        return text
    while len(text) > 1 and _text_width(font_id, text + "…",
                                        size) > max_width:
        text = text[:-1]
    return text + "…"


def _draw_params_tile(width, height, rows, colors, background):
    """One params cell as a flat FLOAT RGBA buffer, tile-shaped.

    The declared parameters as labelled slider rows: label left, current
    value right, a track under them with the knob at the value's fraction
    of its range. ``background`` is the cell's ground in DISPLAY space —
    the caller samples it off a rendered 3D tile so this cell matches the
    others (the ADR-151 uniform-ground lesson); rows that do not fit
    collapse into one ``+N more`` line.
    """

    import gpu
    from mathutils import Matrix

    width, height = int(width), int(height)
    layout = params_panel_layout(len(rows), width, height)
    pad = float(layout["pad"])
    row_h = layout["row_height"]
    text_size = layout["text_size"]
    line = tuple(colors["line"])
    background = tuple(background)[:3] + (1.0,)
    font_id = _font()

    offscreen = gpu.types.GPUOffScreen(width, height)
    try:
        with offscreen.bind():
            framebuffer = gpu.state.active_framebuffer_get()
            framebuffer.clear(color=background)
            gpu.state.blend_set('ALPHA')
            gpu.state.viewport_set(0, 0, width, height)
            gpu.matrix.load_matrix(Matrix.Identity(4))
            gpu.matrix.load_projection_matrix(Matrix((
                (2.0 / width, 0.0, 0.0, -1.0),
                (0.0, 2.0 / height, 0.0, -1.0),
                (0.0, 0.0, -1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0))))

            inner_left = pad
            inner_right = width - pad
            for index in range(layout["shown"]):
                row = rows[index]
                top = height - pad - index * row_h
                baseline = top - text_size * 1.25
                track_y = top - row_h * 0.72
                label = _shorten(font_id, row["label"], text_size,
                                 (inner_right - inner_left) * 0.62)
                _draw_text(font_id, label, inner_left, baseline,
                           text_size, line, 0.8)
                value = row["value_text"]
                value_w = _text_width(font_id, value, text_size)
                _draw_text(font_id, value, inner_right - value_w,
                           baseline, text_size, line, 0.9)
                knob_x = inner_left + row["fraction"] * (inner_right
                                                         - inner_left)
                _draw_lines([(inner_left, track_y, inner_right, track_y)],
                            line, 0.22)
                if knob_x > inner_left:
                    _draw_lines([(inner_left, track_y, knob_x, track_y)],
                                line, 0.6, width=2.0)
                _draw_lines([(knob_x, track_y - 4.0, knob_x,
                              track_y + 4.0)], line, 0.95, width=2.0)
            if layout["more"]:
                text = "+{:d} more parameter{:s}".format(
                    layout["more"], "" if layout["more"] == 1 else "s")
                _draw_text(font_id, text, inner_left, pad, text_size,
                           line, 0.5)

            gpu.state.blend_set('NONE')
            out = framebuffer.read_color(0, 0, width, height, 4, 0,
                                         'FLOAT')
        out.dimensions = width * height * 4
        return list(out)
    finally:
        offscreen.free()


def _dress_sheet(pixels, field_w, field_h, margin, colors, grid, titles,
                 cell_labels, background=None, callouts=()):
    """The composited tile field into a dressed sheet; returns
    ``(sheet_pixels, sheet_w, sheet_h)``.

    One sheet-sized offscreen, the recipe the in-tree blf test proves
    (bind, clear, explicit viewport, identity + pixel-orthographic
    projection), the tile field as a textured quad inset by the margin,
    then the page grid, the zone marks, the cell labels and the titles over
    it — all in the theme's line colour, all fainter than the model lines.

    ``background`` is the margin band's colour in DISPLAY space — the
    caller samples it off the composited field so the band and the tiles
    are one uniform colour (the owner's ask; the tiles are colour-managed
    and a raw theme clear read as a darker border). Omitted, it falls back
    to :func:`display_color` of the theme ground.
    """

    import blf
    import gpu
    from gpu_extras.batch import batch_for_shader
    from mathutils import Matrix

    sheet_w = field_w + 2 * margin
    sheet_h = field_h + 2 * margin
    if background is None:
        background = display_color(colors["background"])
    background = tuple(background)[:3] + (1.0,)
    line = tuple(colors["line"])

    data = gpu.types.Buffer('FLOAT', field_w * field_h * 4, pixels)
    texture = gpu.types.GPUTexture((field_w, field_h), format='RGBA32F',
                                   data=data)
    font_id = _font()
    zone_size = max(9.0, margin * 0.5)
    label_size = max(10.0, margin * 0.55)
    title_size = max(11.0, margin * 0.6)

    offscreen = gpu.types.GPUOffScreen(sheet_w, sheet_h)
    try:
        with offscreen.bind():
            framebuffer = gpu.state.active_framebuffer_get()
            framebuffer.clear(color=background)
            gpu.state.blend_set('ALPHA')
            gpu.state.viewport_set(0, 0, sheet_w, sheet_h)
            gpu.matrix.load_matrix(Matrix.Identity(4))
            gpu.matrix.load_projection_matrix(Matrix((
                (2.0 / sheet_w, 0.0, 0.0, -1.0),
                (0.0, 2.0 / sheet_h, 0.0, -1.0),
                (0.0, 0.0, -1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0))))

            # The tile field, inset by the margin band.
            image_shader = gpu.shader.from_builtin('IMAGE')
            x0, y0 = float(margin), float(margin)
            x1, y1 = x0 + field_w, y0 + field_h
            quad = batch_for_shader(
                image_shader, 'TRIS',
                {"pos": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
                 "texCoord": [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0),
                              (0.0, 1.0)]},
                indices=[(0, 1, 2), (2, 3, 0)])
            image_shader.bind()
            image_shader.uniform_sampler("image", texture)
            quad.draw(image_shader)

            # The page grid: faint sub-grid, zone lines, the sheet frame.
            _draw_lines([(x, 0.0, x, sheet_h)
                         for x in grid["sub_verticals"]]
                        + [(0.0, y, sheet_w, y)
                           for y in grid["sub_horizontals"]],
                        line, SUB_GRID_ALPHA)
            _draw_lines([(x, 0.0, x, sheet_h) for x in grid["verticals"]]
                        + [(0.0, y, sheet_w, y)
                           for y in grid["horizontals"]],
                        line, ZONE_GRID_ALPHA)
            _draw_lines([(x0, y0, x1, y0), (x1, y0, x1, y1),
                         (x1, y1, x0, y1), (x0, y1, x0, y0)],
                        line, FRAME_ALPHA)

            # The title texts are fitted first, because the zone numbers
            # must yield to them: a column number under the project title
            # collides with it (measured in the probe). The bottom-right
            # line drops its middle segments (rev, date, theme -- never the
            # CADEX mark) until it fits a small sheet.
            fitted_titles = []
            title_end = float(margin)
            for entry in titles:
                text = entry["text"]
                if entry["corner"] == "top-left":
                    text = _shorten(font_id, text, title_size,
                                    (sheet_w - 2.0 * margin) / 2.0)
                    title_end = (margin + 8.0
                                 + _text_width(font_id, text, title_size))
                else:
                    parts = text.split("  ·  ")
                    while (len(parts) > 1
                           and _text_width(font_id, "  ·  ".join(parts),
                                           title_size)
                           > sheet_w - 2.0 * margin):
                        parts.pop(1)
                    text = "  ·  ".join(parts)
                fitted_titles.append({"corner": entry["corner"],
                                      "text": text})

            # Zone marks: numbers along the top band, letters down the left.
            for label, x in grid["columns"]:
                width = _text_width(font_id, label, zone_size)
                if x - width / 2.0 < title_end:
                    continue
                _draw_text(font_id, label, x - width / 2.0,
                           sheet_h - margin + (margin - zone_size) / 2.0,
                           zone_size, line, LABEL_ALPHA)
            for label, y in grid["rows"]:
                width = _text_width(font_id, label, zone_size)
                _draw_text(font_id, label, (margin - width) / 2.0,
                           y - zone_size / 2.0, zone_size, line,
                           LABEL_ALPHA)

            # Per-cell view names, in each cell's top-left corner.
            for text, x, y in cell_labels:
                _draw_text(font_id, text, x, y, label_size, line,
                           LABEL_ALPHA)

            # Part-name callouts (ADR-153): the leader runs from the
            # text's inner edge, through an elbow, to the part — measured
            # here, because only the glyphs know where the text ends.
            callout_size = max(9.0, margin * 0.45)
            for entry in callouts:
                text = entry["name"]
                text_w = _text_width(font_id, text, callout_size)
                ax, ay = entry["anchor"]
                if entry["side"] == "left":
                    text_x = entry["label_x"]
                    inner = text_x + text_w + 5.0
                    elbow = max(min(inner + 12.0, ax - 3.0), inner)
                else:
                    text_x = entry["label_x"] - text_w
                    inner = text_x - 5.0
                    elbow = min(max(inner - 12.0, ax + 3.0), inner)
                mid = entry["label_y"] + callout_size * 0.35
                _draw_lines([(inner, mid, elbow, mid),
                             (elbow, mid, ax, ay),
                             (ax - 2.0, ay - 2.0, ax + 2.0, ay + 2.0),
                             (ax - 2.0, ay + 2.0, ax + 2.0, ay - 2.0)],
                            line, CALLOUT_LINE_ALPHA, width=1.2)
                _draw_text(font_id, text, text_x, entry["label_y"],
                           callout_size, line, CALLOUT_TEXT_ALPHA)

            # The titles: project top-left, the CADEX line bottom-right.
            for entry in fitted_titles:
                text = entry["text"]
                if entry["corner"] == "top-left":
                    _draw_text(font_id, text, float(margin),
                               sheet_h - margin + (margin - title_size)
                               / 2.0, title_size, line, TITLE_ALPHA)
                else:
                    width = _text_width(font_id, text, title_size)
                    _draw_text(font_id, text, sheet_w - margin - width,
                               (margin - title_size) / 2.0, title_size,
                               line, TITLE_ALPHA)

            gpu.state.blend_set('NONE')
            out = framebuffer.read_color(0, 0, sheet_w, sheet_h, 4, 0,
                                         'FLOAT')
        out.dimensions = sheet_w * sheet_h * 4
        dressed = list(out)
    finally:
        offscreen.free()

    # The blf glyph cache lands with its own alpha; the sheet is opaque by
    # definition, so force it (the bl_pyapi_blf fix-up, in FLOAT).
    dressed[3::4] = [1.0] * (sheet_w * sheet_h)
    return dressed, sheet_w, sheet_h
