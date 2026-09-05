# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The Blueprint Editor: a window of its own for drafts and stored sheets.

ADR-178 made the sheet a live **draft** — `make_blueprint` renders and
stores nothing, ``save_blueprint`` (or Save here) is the decision, and a
clicked view cell becomes an ``@cell-N`` pin in the next chat message.
ADR-179 gives it the window the owner asked for: ``CADEX_BLUEPRINT``, a
space type of its own, so the drawing is a peer of the viewport rather
than a mode of it. Every editor area carries its **own selection** — the
live draft, or any sheet in the project's blueprint store — so two
windows can show two drawings side by side. The controls live in the
editor's header (the sheet menu, the pager, Save and Export), and the
window's ground is the theme of the sheet it is showing.

The viewport keeps exactly one blueprint thing: the ADR-150 restyle
(``blueprint_view``), which is a look, not a document. The ADR-178
in-viewport draft display and the ADR-177 in-viewport browser are both
gone; this window is where drawings live now.

Selections are per-space and session-only, keyed by the space pointer: a
space type registered in C cannot grow Python properties, a saved file
reopens on the draft (or the newest stored sheet), and the durable thing
is the store, not the view state. Clicks arrive through two add-on
keymap items on the **Window** keymap — a custom space installs no
keymap of its own, but unhandled clicks bubble to the window handlers,
and ``poll`` limits both operators to this editor.

On a bundle built before the C++ half, :data:`EDITOR_AVAILABLE` goes
False and everything that needs the space type stands down (the
``wiring_ui`` arrangement); the draft, the queue and the tools still
work, which is what keeps the suite green on an old binary.

Mechanics are otherwise ADR-178's: module-level ``POST_PIXEL`` handler,
lazy ``gpu``/``blf``, textures image→numpy→``gpu.types.Buffer`` so no
datablock rides into a save, and the handler invisible to offscreen
renders by construction (``offscreen.draw_view3d`` passes no
``bContext``), so a shown sheet can never leak into a render. The pure
half — everything above ``-- the bpy half --`` — imports no ``bpy`` and
is the half Phase 12 keeps.
"""

import os

#: The editor's space type (C++ side: ``space_cadex_blueprint``).
SPACE_TYPE = 'CADEX_BLUEPRINT'

#: Empty space held around the fitted sheet, in region pixels.
MARGIN_PX = 24.0

#: Seconds of quiet after a model change before the draft re-renders.
RERENDER_DELAY = 0.9

#: The store layout, as ``CadexBlueprints`` (engine-side) lays it out.
#: Names, not imports: that module is engine-side.
STORE_DIR = "blueprints"
INDEX_NAME = "blueprints.json"
INDEX_SCHEMA = "cadex-blueprint-v1"

#: False when this bundle has no Blueprint Editor to draw in.
EDITOR_AVAILABLE = True


# -- the pure half: no bpy ---------------------------------------------------

def fit_rect(image_size, region_size, margin=MARGIN_PX):
    """Centre ``image_size`` in ``region_size`` minus margins, aspect kept.

    Returns ``(x, y, w, h)`` in region pixels. A degenerate image fills the
    available field rather than dividing by zero.
    """

    image_w, image_h = (float(image_size[0]), float(image_size[1]))
    region_w, region_h = (float(region_size[0]), float(region_size[1]))
    margin = float(margin)
    avail_w = max(1.0, region_w - 2.0 * margin)
    avail_h = max(1.0, region_h - 2.0 * margin)
    if image_w <= 0.0 or image_h <= 0.0:
        return (margin, margin, avail_w, avail_h)
    scale = min(avail_w / image_w, avail_h / image_h)
    width = image_w * scale
    height = image_h * scale
    return ((region_w - width) / 2.0, (region_h - height) / 2.0,
            width, height)


def cell_rects(rects, margin):
    """The view cells in SHEET pixels: the compose step's rects are
    field-relative (the margin band is added around them at dress time), so
    the margin is added back here, once, and every consumer hit-tests in one
    coordinate space. ``y`` is up from the sheet's bottom edge, which is
    Blender's region convention too — no flip anywhere."""

    margin = float(margin)
    return tuple((margin + float(r[0]), margin + float(r[1]),
                  float(r[2]), float(r[3])) for r in rects or ())


def sheet_point(point, drawn_rect, image_size):
    """A region-pixel ``point`` mapped into sheet pixels, or ``None`` when
    it misses the drawn sheet. ``drawn_rect`` is :func:`fit_rect`'s."""

    x, y = float(point[0]), float(point[1])
    rx, ry, rw, rh = (float(v) for v in drawn_rect)
    if rw <= 0.0 or rh <= 0.0:
        return None
    if not (rx <= x <= rx + rw and ry <= y <= ry + rh):
        return None
    return ((x - rx) / rw * float(image_size[0]),
            (y - ry) / rh * float(image_size[1]))


def hit_cell(point, cells):
    """The index of the cell containing a sheet-pixel ``point``, else
    ``None``. ``cells`` is :func:`cell_rects`' output; ties go to the first
    cell in view order, which is also the order the captions number."""

    if point is None:
        return None
    x, y = float(point[0]), float(point[1])
    for index, (cx, cy, cw, ch) in enumerate(cells):
        if cx <= x <= cx + cw and cy <= y <= cy + ch:
            return index
    return None


def map_rect(cell_rect, drawn_rect, image_size):
    """A sheet-pixel cell rect mapped into region pixels, for drawing the
    hover and tag outlines over the fitted sheet."""

    image_w = max(1.0, float(image_size[0]))
    image_h = max(1.0, float(image_size[1]))
    rx, ry, rw, rh = (float(v) for v in drawn_rect)
    cx, cy, cw, ch = (float(v) for v in cell_rect)
    sx, sy = rw / image_w, rh / image_h
    return (rx + cx * sx, ry + cy * sy, cw * sx, ch * sy)


def draft_caption(label, cell_count, saved=None):
    """One line naming the draft and whether the store holds it."""

    parts = [str(label or "").strip() or "untitled draft"]
    parts.append("{:d} cell{:s}".format(int(cell_count),
                                        "" if int(cell_count) == 1 else "s"))
    if saved and saved.get("name"):
        parts.append("saved as {!r} v{:d}".format(
            str(saved["name"]), int(saved.get("version") or 1)))
    elif saved:
        parts.append("saved")
    else:
        parts.append("draft \N{EM DASH} not saved")
    return " \N{MIDDLE DOT} ".join(parts)


def stored_caption(entry, position, count):
    """One line naming a stored sheet: label, version when it is a named
    (revisable) sheet, place in the store, and the day it was rendered."""

    entry = entry or {}
    label = str(entry.get("label") or entry.get("name") or "sheet").strip()
    parts = [label]
    if str(entry.get("name") or "").strip():
        parts[0] = "{:s} v{:d}".format(label, int(entry.get("version") or 1))
    parts.append("{:d}/{:d}".format(int(position), int(count)))
    day = str(entry.get("created_at") or "")[:10]
    if day:
        parts.append(day)
    return " \N{MIDDLE DOT} ".join(parts)


def section_note(index, spec):
    """The prompt line one tagged cell becomes (the ``cadex_pick`` idiom):
    the model is told which cell, in its own numbering, with the cell's
    spec as ground truth for what that section shows."""

    import json

    label = str((spec or {}).get("label") or (spec or {}).get("view") or "view")
    return ("[The user pinned @cell-{:d} ({:s}) of the blueprint draft on "
            "their screen \N{EM DASH} cell spec: {:s}. Treat it as the "
            "section they mean, and revise the draft with make_blueprint "
            "(the current recipe plus what they ask).]".format(
                int(index) + 1, label,
                json.dumps(spec or {}, default=str)))


def wrap_index(index, count):
    """``index`` wrapped into ``0..count-1``; 0 when there is nothing."""

    count = int(count)
    if count <= 0:
        return 0
    return int(index) % count


def read_index(root):
    """The stored-sheet entries of one project root: ``(entries, error)``.

    Straight off the disk — ``<root>/blueprints/blueprints.json`` — never
    over the protocol: the inspect pager stubs any value over 1 KiB and a
    real store's list always is, which is exactly how the ADR-177 browser
    once showed a full folder as empty. A missing folder or index is an
    empty store, not an error; a malformed index is an error.
    """

    import json

    path = os.path.join(str(root or ""), STORE_DIR, INDEX_NAME)
    if not root or not os.path.isfile(path):
        return (), ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        return (), "Could not read the drawing index: {:s}".format(str(exc))
    if not isinstance(data, dict) or data.get("schema") != INDEX_SCHEMA:
        return (), "The drawing index is not a {:s} file.".format(INDEX_SCHEMA)
    return tuple(entry for entry in (data.get("entries") or ())
                 if isinstance(entry, dict)), ""


def selection_options(draft_exists, entries):
    """The selector's rows, newest stored sheet first: ``(ordinal, label)``
    pairs, ordinal ``-1`` for the draft. Pure, so the suite can pin the
    order without a window."""

    options = []
    if draft_exists:
        options.append((-1, "Draft"))
    for position in range(len(entries) - 1, -1, -1):
        entry = entries[position]
        options.append((int(entry.get("ordinal") or (position + 1)),
                        stored_caption(entry, position + 1, len(entries))))
    return tuple(options)


# -- the bpy half ------------------------------------------------------------

_draw_handle = None
_keymap_items = []
_operator_classes = ()
_header_class = None
_menu_class = None
#: The live draft: None, or the dict :func:`set_draft` installs (the
#: compose step's payload plus "label", "root" and "saved").
_draft = None
#: Cells clicked since the last chat turn: [(index, spec), ...]. Drained by
#: :func:`consume_section_notes`, exactly like ``cadex_pick``'s pins.
_pending_sections = []
#: space pointer -> {"kind": 'draft'} or {"kind": 'stored', "ordinal": int}.
#: Session state on purpose (see the module docstring).
_selections = {}
#: (space pointer, cell index) under the pointer, for the hover outline.
_hover = None
_rerender_pending = False
#: The model changed while no editor showed the draft: catch up on draw.
_outdated = False
#: The stored-sheet list, cached per project root; the draw handler only
#: reads it (a stale root schedules a timer).
_state = {"root": None, "entries": (), "error": ""}
_pending_relist = False
#: path -> GPUTexture, or False for a load that failed.
_textures = {}
_TEXTURE_CACHE_LIMIT = 6


def _project_root(scene):
    from . import cadex_backend
    try:
        return str(cadex_backend.project_root(scene) or "")
    except Exception:
        return ""


def draft():
    """The live draft dict, or None. Callers must not mutate it."""

    return _draft


def has_draft(scene=None):
    return _draft is not None


# -- selection ---------------------------------------------------------------

def selection(space):
    """This editor's selection, defaulted: the draft when one exists, else
    the newest stored sheet, else the draft placeholder."""

    state = _selections.get(space.as_pointer()) if space is not None else None
    if state is not None:
        return state
    if _draft is None and _state["entries"]:
        entry = _state["entries"][-1]
        return {"kind": "stored",
                "ordinal": int(entry.get("ordinal") or len(_state["entries"]))}
    return {"kind": "draft"}


def select(space, ordinal):
    """Point one editor at the draft (``ordinal=-1``) or a stored sheet."""

    if space is None:
        return
    if int(ordinal) < 0:
        _selections[space.as_pointer()] = {"kind": "draft"}
    else:
        _selections[space.as_pointer()] = {"kind": "stored",
                                           "ordinal": int(ordinal)}
    _redraw()


def _stored_entry(sel):
    """The store entry a selection points at, with its position, or
    ``(None, 0)`` when the store moved under it."""

    if sel.get("kind") != "stored":
        return None, 0
    for position, entry in enumerate(_state["entries"]):
        if int(entry.get("ordinal") or 0) == int(sel.get("ordinal") or -2):
            return entry, position + 1
    return None, 0


def step(space, delta):
    """Cycle this editor through draft + stored sheets, newest first."""

    _relist_now()
    options = selection_options(_draft is not None, _state["entries"])
    if not options:
        return
    sel = selection(space)
    current = -1 if sel["kind"] == "draft" else int(sel.get("ordinal") or -1)
    ordinals = [ordinal for ordinal, _label in options]
    try:
        at = ordinals.index(current)
    except ValueError:
        at = 0
    select(space, ordinals[wrap_index(at + int(delta), len(ordinals))])


# -- the draft ---------------------------------------------------------------

def set_draft(scene, sheet, label=""):
    """Install a freshly rendered sheet as the draft.

    ``sheet`` is ``capture.render_blueprint``'s payload; its temp PNG now
    belongs to the draft (nothing else deletes it). Every editor whose
    selection is the draft shows it on next redraw; nothing here touches
    the viewport (ADR-179 — the drawing has a window of its own).
    """

    global _draft, _hover, _outdated

    previous = _draft
    _outdated = False          # this render IS the current model
    _draft = {
        "path": str(sheet.get("path") or ""),
        "rects": [list(rect) for rect in sheet.get("rects") or ()],
        "margin": float(sheet.get("margin") or 0.0),
        "size": [int(v) for v in (sheet.get("size") or (0, 0))],
        "views": [dict(view) for view in sheet.get("views") or ()],
        "recipe": dict(sheet.get("recipe") or {}),
        "theme": str(sheet.get("theme") or ""),
        "legend": str(sheet.get("legend") or ""),
        "note": str(sheet.get("note") or ""),
        "label": str(label or ""),
        "root": _project_root(scene),
        "saved": None,
    }
    _hover = None
    # The renderer reuses one temp path; the texture cache must not.
    _textures.pop(_draft["path"], None)
    if previous and previous.get("path") not in ("", _draft["path"]):
        try:
            os.remove(previous["path"])
        except OSError:
            pass
    _redraw()


def clear_draft(scene=None):
    global _draft, _hover
    if _draft and _draft.get("path"):
        _textures.pop(_draft["path"], None)
        try:
            os.remove(_draft["path"])
        except OSError:
            pass
    _draft = None
    _hover = None
    _pending_sections.clear()
    _redraw()


def editor_open():
    """True while some area anywhere is a Blueprint Editor."""

    import bpy

    try:
        windows = bpy.context.window_manager.windows
    except Exception:
        return False
    for window in windows or ():
        for area in getattr(window.screen, "areas", ()) or ():
            if getattr(area, "type", "") == SPACE_TYPE:
                return True
    return False


def _editor_showing_draft():
    import bpy

    if not EDITOR_AVAILABLE or _draft is None:
        return False
    try:
        windows = bpy.context.window_manager.windows
    except Exception:
        return False
    for window in windows or ():
        for area in getattr(window.screen, "areas", ()) or ():
            if getattr(area, "type", "") != SPACE_TYPE:
                continue
            for space in area.spaces:
                if getattr(space, "type", "") == SPACE_TYPE \
                        and selection(space)["kind"] == "draft":
                    return True
    return False


# -- tagging -----------------------------------------------------------------

def queue_section(index):
    """Queue one clicked cell for the next chat message. Returns the note's
    human name (``@cell-N``) for the transcript, or "" for a bad index."""

    if _draft is None:
        return ""
    views = _draft.get("views") or []
    index = int(index)
    if not 0 <= index < len(views):
        return ""
    spec = dict(views[index])
    _pending_sections.append((index, spec))
    _redraw()
    return "@cell-{:d} ({:s})".format(
        index + 1, str(spec.get("label") or spec.get("view") or "view"))


def pending_section_count():
    return len(_pending_sections)


def tagged_cells():
    """Indexes with a queued pin, for the draw handler's outlines."""

    return tuple(index for index, _spec in _pending_sections)


def consume_section_notes():
    """Prompt suffix describing cells tagged since the last turn (drains)."""

    if not _pending_sections:
        return ""
    lines = [section_note(index, spec) for index, spec in _pending_sections]
    _pending_sections.clear()
    _redraw()
    return "\n\n" + "\n".join(lines)


# -- the store ---------------------------------------------------------------

def save_draft(scene, name=None):
    """Store the current draft in the project through ``put_blueprint``.

    The one write path — the ``save_blueprint`` tool and the header's Save
    button both land here. Returns ``(payload, error)``: exactly one is
    truthy. The draft stays selected, marked saved, and keeps tracking the
    model; save again after the next change and the store keeps the next
    version under the same name (ADR-157).
    """

    from . import cadex_backend
    from . import cadex_sheet

    if _draft is None:
        return None, ("There is no draft to save \N{EM DASH} render one "
                      "with make_blueprint first.")
    path = _draft.get("path") or ""
    if not os.path.isfile(path):
        return None, ("The draft's rendered file is gone (a temp sweep?); "
                      "render it again with make_blueprint, then save.")
    name = str(name if name is not None else _draft.get("label") or "").strip()
    meta = cadex_sheet.trim_meta(
        {"theme": _draft.get("theme") or "",
         "size": list(_draft.get("size") or ()),
         "layout": str((_draft.get("recipe") or {}).get("layout") or ""),
         "aspect": str((_draft.get("recipe") or {}).get("aspect") or ""),
         "rects": list(_draft.get("rects") or ()),
         "views": list(_draft.get("views") or ()),
         "recipe": dict(_draft.get("recipe") or {})},
        cadex_sheet.MAX_STORED_META_BYTES)
    payload = cadex_backend.put_blueprint(scene, path, label=name,
                                          meta=meta, name=name)
    if payload.get("ok") is not True:
        return None, ("The engine refused the blueprint: "
                      + str(payload.get("error") or payload))

    stored = next((dict(item) for item in payload.get("blueprints") or []
                   if isinstance(item, dict)
                   and item.get("file") == payload.get("name")), {})
    _draft["saved"] = {"name": name,
                       "version": int(stored.get("version") or 1),
                       "file": str(payload.get("name") or ""),
                       "revision": str(payload.get("revision") or "")}
    if name:
        _draft["label"] = name
    invalidate(scene)
    return payload, ""


def invalidate(scene=None):
    """The store changed under us (a sheet was just saved): re-list."""

    import bpy

    _state.update(root=None, entries=(), error="")
    _relist_now(scene or getattr(bpy.context, "scene", None))
    _redraw()


def _relist_now(scene=None):
    import bpy

    scene = scene or getattr(bpy.context, "scene", None)
    root = _project_root(scene)
    entries, error = read_index(root)
    _state.update(root=root, entries=entries, error=error)
    kept = {_sheet_path(root, entry) for entry in entries}
    if _draft is not None:
        kept.add(_draft.get("path"))
    for path in [path for path in _textures if path not in kept]:
        del _textures[path]
    return entries, error


def _sheet_path(root, entry):
    return os.path.join(root, STORE_DIR, str((entry or {}).get("file") or ""))


def _schedule_relist():
    """A stale store list noticed mid-draw: re-read from a timer, never
    from the draw callback itself (it is disk IO)."""

    import bpy

    global _pending_relist
    if _pending_relist:
        return
    _pending_relist = True

    def run():
        global _pending_relist
        _pending_relist = False
        try:
            _relist_now()
            _redraw()
        except Exception:
            import traceback
            traceback.print_exc()
        return None

    try:
        bpy.app.timers.register(run, first_interval=0.0)
    except Exception:
        _pending_relist = False


# -- live re-render ----------------------------------------------------------

def rerender(scene):
    """Draw the draft again from its own recipe, against the model as it is
    now. Returns ``(ok, message)``; a refusal (headless, no model) keeps
    the old draft on screen."""

    from . import capture
    from . import cadex_blueprint

    if _draft is None:
        return False, "There is no draft to re-render."
    recipe = dict(_draft.get("recipe") or {})
    sheet, error = capture.render_blueprint(
        theme=str(recipe.get("theme") or cadex_blueprint.DEFAULT_THEME),
        max_size=int(recipe.get("max_size") or 1024),
        views=recipe.get("views"),
        layout=str(recipe.get("layout") or "auto"),
        aspect=str(recipe.get("aspect")) if recipe.get("aspect") else None,
        label=_draft.get("label") or "")
    if sheet is None:
        return False, str(error)
    set_draft(scene, sheet, label=_draft.get("label") or "")
    return True, ""


def _on_hydrate(_payload, _root, _animate):
    """The view-registry hook: an accepted rebuild landed, so the draft is
    a drawing of a model that no longer exists. Re-render after a quiet
    moment — debounced, because a slider drag hydrates many times a second
    and a sheet render costs real time."""

    global _outdated

    if _draft is None:
        return
    _outdated = True
    _schedule_rerender()


def _schedule_rerender():
    import bpy

    global _rerender_pending

    already = _rerender_pending
    _rerender_pending = True
    _schedule_rerender.deadline = _now() + RERENDER_DELAY
    if already:
        return
    _redraw()

    def run():
        global _rerender_pending, _outdated
        remaining = _schedule_rerender.deadline - _now()
        if remaining > 0.0:
            return min(remaining, RERENDER_DELAY)
        _rerender_pending = False
        try:
            scene = bpy.context.scene
            # Only render while some editor is showing the draft; hidden,
            # the _outdated mark stays and the next draw catches up. A
            # fresh agent render mid-wait clears the mark: no-op.
            if _draft is not None and _outdated and _editor_showing_draft():
                ok, message = rerender(scene)
                if ok:
                    _outdated = False
                elif message:
                    print("mesh_agent: draft re-render refused:", message)
            _redraw()
        except Exception:
            import traceback
            traceback.print_exc()
        return None

    try:
        bpy.app.timers.register(run, first_interval=RERENDER_DELAY)
    except Exception:
        _rerender_pending = False


def _now():
    import time

    return time.monotonic()


def _redraw():
    import bpy

    try:
        windows = bpy.context.window_manager.windows
    except Exception:
        return
    for window in windows or ():
        for area in getattr(window.screen, "areas", ()) or ():
            if getattr(area, "type", "") in {SPACE_TYPE, 'CADEX_CHAT'}:
                area.tag_redraw()


# -- drawing -----------------------------------------------------------------

def _texture(path):
    """One sheet PNG as a GPUTexture. The landing screen's loader: pixels
    go image -> numpy -> gpu buffer and the datablock is removed, so
    nothing rides into the user's next save."""

    cached = _textures.get(path)
    if cached is not None:
        return cached or None

    import bpy
    import gpu
    import numpy

    if len(_textures) >= _TEXTURE_CACHE_LIMIT:
        _textures.clear()
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
    _textures[path] = texture
    return texture or None


def _draw_quad(shader_name, rect, color=None, texture=None, style='TRIS'):
    import gpu
    from gpu_extras.batch import batch_for_shader

    x, y, w, h = rect
    points = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    shader = gpu.shader.from_builtin(shader_name)
    if texture is not None:
        batch = batch_for_shader(
            shader, 'TRIS',
            {"pos": points, "texCoord": [(0, 0), (1, 0), (1, 1), (0, 1)]},
            indices=[(0, 1, 2), (0, 2, 3)])
        shader.bind()
        shader.uniform_sampler("image", texture)
    else:
        batch = batch_for_shader(
            shader, style, {"pos": points},
            indices=[(0, 1, 2), (0, 2, 3)] if style == 'TRIS' else None)
        shader.bind()
        shader.uniform_float("color", color)
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


def _theme_colors(theme):
    from . import cadex_blueprint

    table = cadex_blueprint.THEMES
    return table.get(str(theme or ""), table[cadex_blueprint.DEFAULT_THEME])


def _shown(space, scene):
    """What one editor shows: ``(kind, payload, caption, theme)`` where
    payload is the draft dict or ``(path, size)`` for a stored sheet, or
    ``(None, message, ...)`` for an empty state."""

    sel = selection(space)
    if sel["kind"] == "draft":
        if _draft is None:
            return ("empty",
                    "No draft yet \N{EM DASH} ask for a blueprint and it "
                    "draws here, live. Nothing is stored until you save.",
                    "", None)
        caption = draft_caption(_draft.get("label"),
                                len(_draft.get("views") or ()),
                                _draft.get("saved"))
        if _rerender_pending or _outdated:
            caption += (" \N{MIDDLE DOT} re-rendering"
                        "\N{HORIZONTAL ELLIPSIS}")
        return ("draft", _draft, caption, _draft.get("theme"))
    entry, position = _stored_entry(sel)
    if entry is None:
        message = _state["error"] or ("That stored sheet is gone; pick "
                                      "another from the menu.")
        if not _state["entries"] and not _state["error"]:
            message = ("No stored drawings yet \N{EM DASH} save a draft "
                       "and it lands here.")
        return ("empty", message, "", None)
    theme = str((entry.get("meta") or {}).get("theme") or "")
    return ("stored",
            (_sheet_path(_state["root"], entry),
             (entry.get("meta") or {}).get("size")),
            stored_caption(entry, position, len(_state["entries"])),
            theme)


def _draw():
    import bpy

    context = bpy.context
    space = getattr(context, "space_data", None)
    region = getattr(context, "region", None)
    scene = getattr(context, "scene", None)
    if (space is None or region is None or scene is None
            or getattr(space, "type", "") != SPACE_TYPE
            or getattr(region, "type", "") != 'WINDOW'):
        return

    import blf
    import gpu

    if _state["root"] != _project_root(scene):
        _schedule_relist()
    if _outdated and not _rerender_pending \
            and selection(space)["kind"] == "draft":
        _schedule_rerender()

    kind, payload, caption, theme = _shown(space, scene)
    colors = _theme_colors(theme)
    ground = tuple(colors["background"])
    ink = tuple(colors["line"])
    width, height = float(region.width), float(region.height)
    try:
        scale = float(context.preferences.system.ui_scale)
    except Exception:
        scale = 1.0

    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('NONE')
    try:
        _draw_quad('UNIFORM_COLOR', (0.0, 0.0, width, height),
                   color=ground + (1.0,))

        def centred(message):
            size = 14.0 * scale
            _text(blf, (width - _text_width(blf, size, message)) / 2.0,
                  height / 2.0, size, ink, message, alpha=0.8)

        if kind == "empty":
            centred(str(payload))
            return

        if kind == "draft":
            path, size = payload["path"], payload["size"]
        else:
            path, size = payload
        texture = _texture(path)
        if texture is None:
            centred("The sheet's file could not be read: "
                    + os.path.basename(str(path)))
            return
        if not size:
            size = (texture.width, texture.height)

        rect = fit_rect(size, (width, height), MARGIN_PX * scale)
        _draw_quad('IMAGE', rect, texture=texture)
        _draw_quad('UNIFORM_COLOR', rect, color=ink + (0.5,),
                   style='LINE_LOOP')

        text_size = 12.0 * scale
        if kind == "draft":
            # The cells: a faint outline under the pointer, a firm one plus
            # its @cell-N handle on every cell queued for the next message.
            cells = cell_rects(payload["rects"], payload["margin"])
            key = space.as_pointer()
            if _hover is not None and _hover[0] == key \
                    and 0 <= _hover[1] < len(cells):
                _draw_quad('UNIFORM_COLOR',
                           map_rect(cells[_hover[1]], rect, size),
                           color=ink + (0.35,), style='LINE_LOOP')
            for index in tagged_cells():
                if not 0 <= index < len(cells):
                    continue
                drawn = map_rect(cells[index], rect, size)
                _draw_quad('UNIFORM_COLOR', drawn, color=ink + (0.9,),
                           style='LINE_LOOP')
                _text(blf, drawn[0] + 4.0 * scale,
                      drawn[1] + drawn[3] - text_size - 4.0 * scale,
                      text_size, ink, "@cell-{:d}".format(index + 1),
                      alpha=0.9)

        x, y = rect[0], rect[1] - text_size - 6.0 * scale
        if y < 4.0:
            y = 4.0
        _text(blf, x, y, text_size, ink, caption, alpha=0.9)
        if kind == "draft":
            hint = "click a view to tag it for the chat"
            _text(blf, rect[0] + rect[2] - _text_width(blf, text_size, hint),
                  y, text_size, ink, hint, alpha=0.5)
    finally:
        gpu.state.blend_set('NONE')
        gpu.state.depth_test_set('LESS_EQUAL')


def _drawn_rect_for(space, region):
    """The fitted sheet rect for a region, or None when nothing fits."""

    import bpy

    sel = selection(space)
    if sel["kind"] == "draft":
        if _draft is None:
            return None, None
        size = _draft["size"]
    else:
        entry, _position = _stored_entry(sel)
        if entry is None:
            return None, None
        size = (entry.get("meta") or {}).get("size")
        if not size:
            return None, None
    try:
        scale = float(bpy.context.preferences.system.ui_scale)
    except Exception:
        scale = 1.0
    return fit_rect(size, (region.width, region.height),
                    MARGIN_PX * scale), size


# -- chrome ------------------------------------------------------------------

def _make_classes():
    import bpy
    from bpy.types import Header, Menu, Operator

    class MESH_AGENT_OT_blueprint_select(Operator):
        """Show the draft (ordinal -1) or a stored sheet in this editor."""

        bl_idname = "mesh_agent.blueprint_select"
        bl_label = "Show Blueprint"
        bl_options = {'INTERNAL'}

        ordinal: bpy.props.IntProperty(name="Ordinal", default=-1)

        def execute(self, context):
            _relist_now(context.scene)
            select(context.space_data, self.ordinal)
            return {'FINISHED'}

    class MESH_AGENT_OT_blueprint_step(Operator):
        """Cycle this editor through the draft and the stored sheets."""

        bl_idname = "mesh_agent.blueprint_step"
        bl_label = "Next Blueprint"
        bl_options = {'INTERNAL'}

        delta: bpy.props.IntProperty(name="Delta", default=1)

        def execute(self, context):
            step(context.space_data, self.delta)
            return {'FINISHED'}

    class MESH_AGENT_OT_draft_click(Operator):
        """Tag the view cell under the pointer for the next chat message."""

        bl_idname = "mesh_agent.draft_click"
        bl_label = "Tag Drawing Section"
        bl_options = {'INTERNAL'}

        @classmethod
        def poll(cls, context):
            space = getattr(context, "space_data", None)
            return (space is not None
                    and getattr(space, "type", "") == SPACE_TYPE)

        def invoke(self, context, event):
            space = context.space_data
            region = context.region
            if (region is None or getattr(region, "type", "") != 'WINDOW'
                    or selection(space)["kind"] != "draft"
                    or _draft is None):
                return {'PASS_THROUGH'}
            drawn, size = _drawn_rect_for(space, region)
            if drawn is None:
                return {'PASS_THROUGH'}
            point = sheet_point((event.mouse_region_x, event.mouse_region_y),
                                drawn, size)
            index = hit_cell(point, cell_rects(_draft["rects"],
                                               _draft["margin"]))
            if index is None:
                return {'PASS_THROUGH'}
            handle = queue_section(index)
            if handle:
                from . import history
                history.add("status",
                            "Tagged {:s} of the draft".format(handle))
            return {'FINISHED'}

    class MESH_AGENT_OT_draft_hover(Operator):
        """Track the hovered view cell (outline only)."""

        bl_idname = "mesh_agent.draft_hover"
        bl_label = "Drawing Hover"
        bl_options = {'INTERNAL'}

        @classmethod
        def poll(cls, context):
            space = getattr(context, "space_data", None)
            return (space is not None
                    and getattr(space, "type", "") == SPACE_TYPE)

        def invoke(self, context, event):
            global _hover
            space = context.space_data
            region = context.region
            index = None
            if (region is not None
                    and getattr(region, "type", "") == 'WINDOW'
                    and selection(space)["kind"] == "draft"
                    and _draft is not None):
                drawn, size = _drawn_rect_for(space, region)
                if drawn is not None:
                    point = sheet_point(
                        (event.mouse_region_x, event.mouse_region_y),
                        drawn, size)
                    index = hit_cell(point, cell_rects(_draft["rects"],
                                                       _draft["margin"]))
            hover = None if index is None else (space.as_pointer(), index)
            if hover != _hover:
                _hover = hover
                if region is not None:
                    region.tag_redraw()
            return {'PASS_THROUGH'}

    class MESH_AGENT_OT_draft_save(Operator):
        """Store the draft in the project (the same write save_blueprint
        makes); saving again after a change stores the next version."""

        bl_idname = "mesh_agent.draft_save"
        bl_label = "Save Drawing"

        @classmethod
        def poll(cls, context):
            return has_draft()

        def execute(self, context):
            payload, error = save_draft(context.scene)
            if error:
                self.report({'ERROR'}, error)
                return {'CANCELLED'}
            saved = (_draft or {}).get("saved") or {}
            self.report({'INFO'}, "Stored {:s}".format(
                "{!r} v{:d}".format(saved["name"], saved["version"])
                if saved.get("name") else str(payload.get("name") or "sheet")))
            return {'FINISHED'}

    class MESH_AGENT_OT_draft_export(Operator):
        """Write the shown sheet's PNG anywhere on disk (the store is
        untouched)."""

        bl_idname = "mesh_agent.draft_export"
        bl_label = "Export Drawing"

        filepath: bpy.props.StringProperty(subtype='FILE_PATH')
        filter_glob: bpy.props.StringProperty(default="*.png",
                                              options={'HIDDEN'})

        @classmethod
        def poll(cls, context):
            space = getattr(context, "space_data", None)
            if space is None or getattr(space, "type", "") != SPACE_TYPE:
                return has_draft()
            kind, _payload, _caption, _theme = _shown(space, context.scene)
            return kind != "empty"

        def _source(self, context):
            space = getattr(context, "space_data", None)
            if space is not None and getattr(space, "type", "") == SPACE_TYPE:
                sel = selection(space)
                if sel["kind"] == "stored":
                    entry, _position = _stored_entry(sel)
                    if entry is not None:
                        return (_sheet_path(_state["root"], entry),
                                str(entry.get("label") or entry.get("name")
                                    or "blueprint"))
            if _draft is not None:
                return (_draft.get("path") or "",
                        _draft.get("label") or "blueprint")
            return "", ""

        def invoke(self, context, _event):
            _path, stem = self._source(context)
            self.filepath = "".join(
                ch if ch.isalnum() or ch in "-_ " else "-"
                for ch in (stem or "blueprint")).strip() + ".png"
            context.window_manager.fileselect_add(self)
            return {'RUNNING_MODAL'}

        def execute(self, context):
            import shutil

            source, _stem = self._source(context)
            if not source or not os.path.isfile(source):
                self.report({'ERROR'}, "There is no rendered sheet to export.")
                return {'CANCELLED'}
            path = self.filepath
            if not path.lower().endswith(".png"):
                path += ".png"
            try:
                shutil.copyfile(source, path)
            except OSError as exc:
                self.report({'ERROR'}, "Could not write {:s}: {:s}".format(
                    path, str(exc)))
                return {'CANCELLED'}
            self.report({'INFO'}, "Exported " + path)
            return {'FINISHED'}

    class MESH_AGENT_MT_blueprint_sheets(Menu):
        """The selector: the draft, then the stored sheets, newest first."""

        bl_idname = "MESH_AGENT_MT_blueprint_sheets"
        bl_label = "Blueprint"

        def draw(self, context):
            layout = self.layout
            _relist_now(context.scene)
            options = selection_options(_draft is not None,
                                        _state["entries"])
            if not options:
                layout.label(text="No drawings yet")
                return
            for ordinal, label in options:
                row = layout.operator(MESH_AGENT_OT_blueprint_select.bl_idname,
                                      text=label,
                                      icon='GREASEPENCIL' if ordinal < 0
                                      else 'FILE_IMAGE')
                row.ordinal = ordinal

    operators = (MESH_AGENT_OT_blueprint_select,
                 MESH_AGENT_OT_blueprint_step,
                 MESH_AGENT_OT_draft_click, MESH_AGENT_OT_draft_hover,
                 MESH_AGENT_OT_draft_save, MESH_AGENT_OT_draft_export)

    class CADEX_BLUEPRINT_HT_header(Header):
        bl_space_type = SPACE_TYPE

        def draw(self, context):
            layout = self.layout
            layout.template_header()

            space = context.space_data
            sel = selection(space)
            if sel["kind"] == "draft":
                current = "Draft" if _draft is not None else "No draft"
            else:
                entry, position = _stored_entry(sel)
                current = (stored_caption(entry, position,
                                          len(_state["entries"]))
                           if entry is not None else "\N{EM DASH}")
            layout.menu(MESH_AGENT_MT_blueprint_sheets.bl_idname,
                        text=current)
            row = layout.row(align=True)
            row.operator(MESH_AGENT_OT_blueprint_step.bl_idname,
                         text="", icon='TRIA_LEFT').delta = -1
            row.operator(MESH_AGENT_OT_blueprint_step.bl_idname,
                         text="", icon='TRIA_RIGHT').delta = 1

            layout.separator_spacer()
            if sel["kind"] == "draft" and _draft is not None:
                if pending_section_count():
                    layout.label(text="{:d} tagged".format(
                        pending_section_count()))
                layout.operator(MESH_AGENT_OT_draft_save.bl_idname,
                                text="Save", icon='FILE_TICK')
            layout.operator(MESH_AGENT_OT_draft_export.bl_idname,
                            text="Export", icon='EXPORT')

    return operators, CADEX_BLUEPRINT_HT_header, MESH_AGENT_MT_blueprint_sheets


def register():
    import bpy

    global _draw_handle, _operator_classes, _header_class, _menu_class
    global EDITOR_AVAILABLE

    operators, header, menu = _make_classes()

    # Operators and the menu name no space type: always registered, so the
    # save/export tools work even on a bundle without the editor.
    for cls in operators:
        bpy.utils.register_class(cls)
    bpy.utils.register_class(menu)
    _operator_classes = operators
    _menu_class = menu

    # A rebuild makes the draft a drawing of a model that no longer
    # exists: the registry hook is what keeps "live" true. Registered on
    # every bundle — with no editor open it only marks the draft outdated.
    from . import cadex_views
    cadex_views.register_view(name="drawings", order=70,
                              on_hydrate=_on_hydrate)

    # Everything below needs the C++ half. On a bundle built before it,
    # stand down quietly (the wiring_ui arrangement) — the draft, the
    # queue and the tools all still work.
    space_rna = getattr(bpy.types, "SpaceCadexBlueprint", None)
    if space_rna is None:
        EDITOR_AVAILABLE = False
        return
    EDITOR_AVAILABLE = True

    try:
        bpy.utils.register_class(header)
        _header_class = header
    except Exception:
        EDITOR_AVAILABLE = False
        return

    if _draw_handle is None:
        _draw_handle = space_rna.draw_handler_add(
            _draw, (), 'WINDOW', 'POST_PIXEL')

    install_keymaps()


def install_keymaps():
    """Clicks and hover: a custom space installs no keymap of its own, so
    the items ride the Window keymap and `poll` limits them to this
    editor; unhandled clicks bubble up to window handlers.

    Idempotent, and callable after ``register()``: at launch this package
    registers before ``keyconfigs.addon`` exists (ADR-183), so the package
    ``__init__`` retries this from a timer until it returns True. Without
    the editor there is nothing to click, so that counts as done.
    """
    import bpy

    if not EDITOR_AVAILABLE or _keymap_items:
        return True
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig is None:
        return False
    keymap = keyconfig.keymaps.new(name="Window", space_type='EMPTY')
    for idname, key, value in (
            ("mesh_agent.draft_click", 'LEFTMOUSE', 'PRESS'),
            ("mesh_agent.draft_hover", 'MOUSEMOVE', 'ANY')):
        _keymap_items.append(
            (keymap, keymap.keymap_items.new(idname, key, value)))
    return True


def unregister():
    import bpy

    global _draw_handle, _operator_classes, _header_class, _menu_class

    from . import cadex_views
    cadex_views.unregister_view("drawings")

    if _draw_handle is not None:
        space_rna = getattr(bpy.types, "SpaceCadexBlueprint", None)
        if space_rna is not None:
            try:
                space_rna.draw_handler_remove(_draw_handle, 'WINDOW')
            except Exception:
                pass
        _draw_handle = None
    for keymap, item in _keymap_items:
        try:
            keymap.keymap_items.remove(item)
        except Exception:
            pass
    _keymap_items.clear()
    if _header_class is not None:
        try:
            bpy.utils.unregister_class(_header_class)
        except Exception:
            pass
        _header_class = None
    if _menu_class is not None:
        try:
            bpy.utils.unregister_class(_menu_class)
        except Exception:
            pass
        _menu_class = None
    for cls in reversed(_operator_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
    _operator_classes = ()
    _pending_sections.clear()
    _selections.clear()
    _textures.clear()
    _state.update(root=None, entries=(), error="")
