# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The studio renderer: accepted tessellation to lit images, the concept sheet, and the design proxies.

One implementation for every client (ADR-445). The CLI and the dashboard
load this file by path, as they load ``CadexdProtocol``; it has no process
entry of its own (ADR-529). It is **not** a
cadexd op: ``cadexd`` dispatches serially, and a 12 s render inside it would
stall the slider drag queued behind it. Nothing in the service imports it.

Pure standard library -- no numpy, no graphics runtime: a CPU rasteriser that
writes its own PNGs. Formerly ``cli/cadex_cli/{render,sheet,scene}.py``
(ADR-239, ADR-406, ADR-412, ADR-430, ADR-444); moved here unchanged in what it
draws.

- Review views and ``look``: orthographic, studio-lit, 2x2 supersampled, on the
  review viewport's dark prototype mat, with a measured contact shadow.
- The concept sheet: the hero, key numbers, palette, three line views and A1's
  proxies, lettered in Noto Sans, read from the TrueType file beside this module.
- The print-bed hero: every printed part seated on its largest flat face,
  packed onto as many beds as it takes, numbered, beside a parts list of the
  purchased hardware (ADR-569).
- :data:`PALETTE`: the dark scene every presented image stands on. The review
  dashboard's ``environment.js`` and ``review.css`` carry the same colours for
  the browser, and ``cli/tests/test_scene_palette.py`` holds them equal to
  this table: this is the source, those are copies checked against it.
"""
from __future__ import annotations

import base64
import html
import json
import math
from pathlib import Path
import struct
import time
import zlib


class StudioError(RuntimeError):
    """A render refused: invalid or excessive geometry, or an unwritable result."""


# --- The dark prototype scene (ot10 A8, ADR-444) -----------------------------

#: The scene as RGB triples: ``bg`` (the viewport's sky and the page's
#: ``--bg``), the mat's ``tile_a``/``tile_b`` checker and major ``line``, and
#: the chrome's ``ink``, ``ink_2`` and ``rule``.
PALETTE = {
    'bg': (20, 20, 20),
    'tile_a': (28, 28, 28),
    'tile_b': (35, 35, 35),
    'line': (58, 58, 58),
    'ink': (237, 237, 237),
    'ink_2': (154, 154, 154),
    'rule': (58, 58, 58),
}
#: The mat's grid pitch, in millimetres: one square a metre on a side at
#: every framing, in every image and video the engine draws (ADR-604). The
#: viewport's ``floor.js`` paints its mat at the same ``GRID_PITCH`` (1 m),
#: so a design reads at true size against the floor wherever it is shown.
GRID_PITCH_MM = 1000.0
#: A major line is 5/256 of its pitch wide, as ``floor.js`` paints it (its
#: ``LINE_FRACTION``).
LINE_FRACTION = 5 / 256


def hex_colour(rgb):
    return '#%02x%02x%02x' % tuple(rgb)


# --- The studio renderer (ADR-239, ADR-406, ADR-412) -------------------------

SIZE = 512
MAX_BYTES = 32 * 1024 * 1024
MAX_VERTICES = 300_000
# hex2 (2026-09-25), a 12-servo hexapod, is 110,688 placed triangles; 100k refused it.
# hex3 (2026-09-26), the same robot with filleted brackets, is 589,268, and the
# 400k cap refused it too (ADR-410). What is read is bounded at the INPUT caps;
# what is drawn is bounded at MAX_TRIANGLES by clustering vertices into a grid
# cell a fraction of a pixel wide, doubled until the model fits.
MAX_PLACED_VERTICES = 4_000_000
MAX_INPUT_TRIANGLES = 2_000_000
MAX_TRIANGLES = 400_000
#: The first clustering cell, as a fraction of the model's largest extent:
#: a quarter of a pixel at SIZE, so the first pass changes no pixel.
FIRST_CELL_FRACTION = 1.0 / (4 * SIZE)
MAX_SAMPLES = 20_000_000  # bounding-box pixel visits per SIZE view, including overdraw; scales with image area
IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
s2, s3, s6 = math.sqrt(2), math.sqrt(3), math.sqrt(6)
BASES = {
    'front': ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    'top': ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    'right': ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    'iso': ((1/s2, 1/s2, 0), (-1/s6, 1/s6, 2/s6), (1/s3, -1/s3, 1/s3)),
}
#: What the agent's `look` tool may ask for: the four review views plus the
#: opposite three-quarter view, so the far side of a design is not unseen.
LOOK_VIEWS = {**BASES, 'iso_back': ((-1/s2, -1/s2, 0), (1/s6, -1/s6, 2/s6), (-1/s3, 1/s3, 1/s3))}
LOOK_SIZE = 768


def camera(azimuth_deg, elevation_deg):
    """An orthographic basis (right, up, toward the viewer) for a camera
    ``azimuth_deg`` round from the front (-Y) towards +X and
    ``elevation_deg`` above the floor."""
    a, e = math.radians(azimuth_deg), math.radians(elevation_deg)
    right = (math.cos(a), math.sin(a), 0.0)
    toward = (math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e))
    up = (toward[1]*right[2] - toward[2]*right[1], toward[2]*right[0] - toward[0]*right[2],
          toward[0]*right[1] - toward[1]*right[0])
    return right, up, toward


#: The studio hero (docs/DESIGN-LANGUAGE.md section 7): a low three-quarter
#: view, 20 degrees above the floor and 35 degrees round from the front.
HERO = camera(35.0, 20.0)
LOOK_VIEWS['hero'] = HERO
HERO_SIZE = 1024
#: Subsamples per axis: every studio image is drawn at twice its size and
#: box-filtered down, which is what antialiases its edges.
SUPERSAMPLE = 2
#: The appearance roles and their default colours (DESIGN-LANGUAGE.md
#: section 2): bone shell, graphite mechanism, signal-orange accent. A part
#: with no declared role is `mechanism` when purchased and `shell` when
#: printed; being purchased is otherwise not a colour.
ROLE_COLORS = {'shell': (233, 230, 223), 'mechanism': (47, 50, 55), 'accent': (242, 106, 27)}
#: Per role: (specular strength, Blinn exponent). Satin shell, harder mechanism.
FINISH = {'shell': (0.16, 20.0), 'mechanism': (0.30, 16.0), 'accent': (0.22, 28.0)}
#: A tessellation corner keeps its face's normal when the smoothed normal
#: turns further than this from it: fillets shade smooth, box edges stay crisp.
CREASE_DEGREES = 40.0
#: A1's frozen bars for the proxies (docs/probes/ot10/contract.json;
#: test_ot10_contract holds them equal). P2 is a BREP measure, read from the
#: inventory rather than the image.
PROXY_BARS = {'hardware_silhouette_share': {'max': 0.2}, 'sharp_outside_edge_share': {'max': 0.25},
              'material_count': {'min': 2, 'max': 3}}
#: The hero is measured at this size, whatever size it is drawn at.
PROXY_SIZE = 512
#: The floor every studio image stands on is the review viewport's dark
#: prototype mat (ot10 A8, ADR-444): its colours come from :data:`PALETTE`, which
#: reads them out of the viewport's own ``environment.js``. The mat fades into
#: the scene background between these multiples of the framed extent,
#: measured on the floor from the point under the image centre.
FLOOR_FADE = (0.75, 1.9)
INDEX_PALETTE = [(91, 157, 205), (230, 151, 76), (115, 182, 135), (180, 134, 200)]
LIMITS = {'buffer_bytes': MAX_BYTES, 'triangles': MAX_TRIANGLES, 'input_triangles': MAX_INPUT_TRIANGLES,
          'vertices_per_source': MAX_VERTICES,
          'placed_vertices': MAX_PLACED_VERTICES,
          'pixel_visits_per_view': MAX_SAMPLES, 'image_size': SIZE, 'hero_size': HERO_SIZE}
APPROXIMATION = ('Opaque standard tessellation, initial solved pose, orthographic; studio-lit '
                 '(key, fill, rim; normals smoothed below a crease angle), 2x2 supersampled, on the '
                 'review viewport\'s dark prototype mat with a contact shadow measured from the geometry; no '
                 'transparency, edges or dimensions. Environment geometry the fit names is left '
                 'out. Shell-only visibility is not carried by the protocol. Placed source copies '
                 'are excluded. Above the drawn triangle budget, vertices are clustered on a '
                 'grid (summary: decimation).')


def _require(condition, message):
    if not condition:
        raise StudioError('render: ' + message)


def snapshot(reply, environment=()):
    """Copy and validate all geometry before any subsequent engine request.

    ``environment`` names world geometry (see :func:`world`). It is still
    read and clustered, but it does not size the clustering grid: a 3 m
    floor under a 300 mm robot drew the robot on a 1.46 mm grid
    (ot10-hexapod-12, ADR-439).
    """
    _require(reply.get('ok') is True, str(reply.get('error') or 'rebuild failed'))
    revision = reply.get('revision')
    _require(isinstance(revision, str) and len(revision) == 64 and
             revision == reply.get('accepted_revision'), 'no matching accepted revision')
    display = reply.get('display')
    _require(isinstance(display, dict) and len(display) <= 4096, 'invalid/excessive display')
    _require(all(isinstance(e, dict) for e in display.values()), 'invalid display entry')
    _require(all(isinstance(e.get('source_output', ''), str) for e in display.values()),
             'invalid component source')
    sources = {e['source_output'] for e in display.values() if e.get('source_output')}
    cache, triangles, objects, parts = {}, [], {}, []
    budget = 0
    placed_vertices = 0
    raw_triangles = 0

    def read(path, limit):
        nonlocal budget
        with Path(path).open('rb') as stream:
            data = stream.read(min(limit, MAX_BYTES - budget) + 1)
        budget += len(data)
        _require(len(data) <= limit and budget <= MAX_BYTES, 'display buffers exceed byte budget')
        return data

    def geometry(source):
        if source in cache:
            return cache[source]
        _require(source in display, 'missing component source ' + source)
        tess = display[source].get('tessellation')
        _require(isinstance(tess, dict), 'missing tessellation for ' + source)
        side = json.loads(read(tess['sidecar_path'], 4 * 1024 * 1024))
        _require(isinstance(side, dict) and isinstance(side.get('layout'), dict),
                 'invalid tessellation sidecar')
        _require(side.get('schema') == 'cadex-tessellation-v1' and
                 side.get('byte_order') == 'little', 'unsupported tessellation format')
        data = read(tess['artifact_path'], MAX_BYTES)
        arrays = []
        for key, dtype, code in [('vertices', 'f32', 'f'), ('triangles', 'u32', 'I')]:
            layout = side['layout'][key]
            _require(isinstance(layout, dict), 'invalid ' + key + ' layout')
            offset, count = layout['offset'], layout['bytes']
            _require(type(offset) is int and type(count) is int and offset >= 0 and
                     count >= 0 and offset % 4 == 0 and count % 12 == 0 and
                     offset + count <= len(data) and layout['dtype'] == dtype,
                     'invalid ' + key + ' layout')
            _require(count // 12 <= (MAX_VERTICES if key == 'vertices' else MAX_INPUT_TRIANGLES),
                     key + ' count budget exceeded')
            arrays.append(list(struct.iter_unpack('<' + code * 3, data[offset:offset+count])))
        vertices, indices = arrays
        _require(all(math.isfinite(x) and abs(x) <= 1e9 for v in vertices for x in v),
                 'nonfinite or excessive coordinates')
        _require(len(indices) <= MAX_INPUT_TRIANGLES and
                 all(max(t) < len(vertices) for t in indices), 'invalid/excessive triangle indices')
        cache[source] = vertices, indices
        return vertices, indices

    try:
        for name, entry in sorted(display.items()):
            if name in sources:
                continue
            source = entry.get('source_output', name)
            if source == name and not entry.get('tessellation'):
                _require(entry.get('artifact_kind') not in {'brep', 'mesh'},
                         'missing tessellation for ' + name)
                continue
            vertices, indices = geometry(source)
            placed_vertices += len(vertices)
            _require(placed_vertices <= MAX_PLACED_VERTICES, 'placed vertex budget exceeded')
            matrix = entry.get('placement')
            _require(matrix is not None or source == name, 'component has no solved placement')
            matrix = IDENTITY if matrix is None else matrix
            _require(isinstance(matrix, list) and len(matrix) == 16 and
                     all(isinstance(x, (int, float)) and math.isfinite(x) and abs(x) <= 1e9
                         for x in matrix) and matrix[12:] == [0, 0, 0, 1], 'invalid placement')
            points = [tuple(sum(matrix[4*r+c]*v[c] for c in range(3)) + matrix[4*r+3]
                            for r in range(3)) for v in vertices]
            _require(all(abs(x) <= 1e9 for v in points for x in v), 'excessive placed coordinates')
            raw_triangles += len(indices)
            _require(raw_triangles <= MAX_INPUT_TRIANGLES, 'triangle budget exceeded')
            if not indices:
                continue
            parts.append((name, source, matrix, points, indices))
    except (OSError, KeyError, TypeError, ValueError, struct.error) as exc:
        raise StudioError('render: malformed or unreadable display: ' + str(exc)) from exc
    _require(bool(parts), 'no published triangle geometry')
    decimation = None
    if raw_triangles > MAX_TRIANGLES:
        drawn = [part for part in parts if part[0] not in environment] or parts
        extent = max(max(p[j] for *_, points, _ in drawn for p in points)
                     - min(p[j] for *_, points, _ in drawn for p in points) for j in range(3))
        _require(extent > 0, 'zero model extent')
        cell = extent * FIRST_CELL_FRACTION
        while True:
            clustered = [_cluster(points, indices, cell) for *_, points, indices in parts]
            kept = sum(len(tris) for tris in clustered)
            if kept <= MAX_TRIANGLES:
                break
            _require(cell < extent, 'triangle budget exceeded')
            cell *= 2.0
        parts = [(*part[:4], tris) for part, tris in zip(parts, clustered)]
        decimation = {'input_triangles': raw_triangles, 'cell_mm': cell, 'extent_mm': extent,
                      'cell_fraction_of_extent': cell / extent,
                      'extent_excludes': sorted({part[0] for part in parts} - {part[0] for part in drawn})}
    for name, source, matrix, points, indices in parts:
        color = INDEX_PALETTE[len(objects) % len(INDEX_PALETTE)]
        first = len(triangles)
        triangles.extend((color, tuple(points[i] for i in tri)) for tri in indices)
        objects[name] = {'triangles': len(indices), 'first': first, 'source': source, 'placement': matrix, 'color': color,
                         'bounds_mm': [[fn(p[j] for p in points) for j in range(3)]
                                       for fn in (min, max)]}
    return triangles, {'revision': revision, 'digest': reply.get('digest'), 'objects': objects,
                       'triangles': len(triangles), 'snapshot_bytes': budget,
                       'decimation': decimation,
                       'approximation': APPROXIMATION, 'limits': LIMITS}


def _cluster(points, indices, cell):
    """Indices re-pointed at one vertex per grid cell; collapsed triangles dropped.

    Each vertex maps to the first vertex seen in its cell, so an edge shorter
    than the cell vanishes and the triangles on it with it. Duplicates, which
    two faces of a thin wall can become, are kept once.
    """
    representative, first_in = [], {}
    for index, point in enumerate(points):
        key = (math.floor(point[0] / cell), math.floor(point[1] / cell), math.floor(point[2] / cell))
        representative.append(first_in.setdefault(key, index))
    kept, seen = [], set()
    for tri in indices:
        a, b, c = (representative[i] for i in tri)
        if a == b or b == c or a == c:
            continue
        key = tuple(sorted((a, b, c)))
        if key in seen:
            continue
        seen.add(key)
        kept.append((a, b, c))
    return kept


def png(pixels, size=SIZE, height=None):
    """8-bit RGB PNG bytes, ``size`` wide and ``height`` (default ``size``) tall."""
    height = size if height is None else height

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data))
    rows = b''.join(b'\0' + pixels[y*size*3:(y+1)*size*3] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', size, height, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def materials(summary, *, purchased=None, appearance=None, palette=None):
    """``object -> (role, rgb)``: what each object is drawn in.

    ``appearance`` maps an object to its declared role (A3's hook: xscript
    declares it, inventory carries it); ``palette`` overrides a role's
    colour. Undeclared objects fall back on ``purchased``: mechanism if
    bought, shell if printed. With neither, each object keeps its index
    colour from the snapshot, which is all a design with no inventory says.
    """
    appearance, colours = dict(appearance or {}), {**ROLE_COLORS, **dict(palette or {})}
    unknown = sorted({str(r) for r in appearance.values()} - set(ROLE_COLORS))
    _require(not unknown, 'unknown appearance role ' + ', '.join(unknown) +
             '; roles: ' + ', '.join(ROLE_COLORS))
    result = {}
    for name, item in summary['objects'].items():
        role = appearance.get(name)
        if role is None and purchased is not None:
            role = 'mechanism' if name in purchased else 'shell'
        result[name] = (role or 'shell', tuple(colours[role]) if role else tuple(item['color']))
    return result


def _prepare(parts):
    """Per drawn triangle: its corners and a normal per corner, in world space.

    Each corner's normal averages the faces sharing that vertex whose normals
    lie within CREASE_DEGREES of this face's own, weighted by area: large
    radii shade as the curves they are, and a box keeps its edges however its
    faces happen to be split into triangles.
    """
    limit = math.cos(math.radians(CREASE_DEGREES))
    prepared = []
    for material, tris in parts:
        index, around, faces = {}, [], []
        for points in tris:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = points
            ux, uy, uz, vx, vy, vz = bx-ax, by-ay, bz-az, cx-ax, cy-ay, cz-az
            n = (uy*vz - uz*vy, uz*vx - ux*vz, ux*vy - uy*vx)
            length = math.sqrt(n[0]*n[0] + n[1]*n[1] + n[2]*n[2])
            if length == 0:
                continue
            face = (n[0]/length, n[1]/length, n[2]/length, length)
            corners = []
            for p in points:
                k = index.get(p)
                if k is None:
                    k = index[p] = len(around)
                    around.append([])
                around[k].append(face)
                corners.append(k)
            faces.append((points, face, corners))
        for points, face, corners in faces:
            fx, fy, fz, _ = face
            normals = []
            for k in corners:
                x = y = z = 0.0
                for gx, gy, gz, weight in around[k]:
                    if gx*fx + gy*fy + gz*fz >= limit:
                        x += gx*weight; y += gy*weight; z += gz*weight
                length = math.sqrt(x*x + y*y + z*z)
                normals.append((x/length, y/length, z/length))
            prepared.append((material, points, normals))
    return prepared


def _blur(grid, width, height, radius):
    """Two separable box passes over a row-major grid: close to a Gaussian."""
    if radius < 1:
        return grid
    for _ in range(2):
        for across in (True, False):
            lines, length = (height, width) if across else (width, height)
            out = [0.0] * len(grid)
            for line in range(lines):
                at = (lambda i: line*width + i) if across else (lambda i: i*width + line)
                values = [grid[at(i)] for i in range(length)]
                total, span = 0.0, 2*radius + 1
                prefix = [0.0]
                for v in values:
                    total += v
                    prefix.append(total)
                for i in range(length):
                    lo_i, hi_i = max(0, i - radius), min(length, i + radius + 1)
                    out[at(i)] = (prefix[hi_i] - prefix[lo_i]) / span
            grid = out
    return grid


def _contact_shadow(prepared, floor=None):
    """A soft shadow on the floor under the design, as a function of (x, y).

    Measured, not painted: a top-down map of how high the lowest surface
    over each cell sits above the floor, turned into a tight dark contact
    term (what touches the floor) and a wide soft term (what hovers over
    it), each blurred. The floor is the design's lowest point unless
    ``floor`` names one (a rollout's, fixed across its frames). Returns
    ``(floor_z, lookup)``.
    """
    points = [p for _, tri, _ in prepared for p in tri]
    lo = [min(p[j] for p in points) for j in range(3)]
    hi = [max(p[j] for p in points) for j in range(3)]
    extent = max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], 1e-9)
    margin, cells = 0.3 * extent, 160
    x0, y0 = lo[0] - margin, lo[1] - margin
    cell = (max(hi[0] - lo[0], hi[1] - lo[1]) + 2 * margin) / cells
    width = int((hi[0] - lo[0] + 2 * margin) / cell) + 1
    height = int((hi[1] - lo[1] + 2 * margin) / cell) + 1
    lowest = [math.inf] * (width * height)
    for _, tri, _ in prepared:
        # Corners and centroid always land: a sliver thinner than a cell
        # (a leg seen from above) must still cast its shadow.
        centre = tuple(sum(p[j] for p in tri) / 3 for j in range(3))
        for x, y, z in (*tri, centre):
            k = int((y - y0) / cell) * width + int((x - x0) / cell)
            if z < lowest[k]:
                lowest[k] = z
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
        area = (bx-ax)*(cy-ay) - (cx-ax)*(by-ay)
        if abs(area) < cell * cell:
            continue
        for j in range(int((min(ay, by, cy) - y0) / cell), int((max(ay, by, cy) - y0) / cell) + 1):
            py = y0 + (j + .5) * cell
            for i in range(int((min(ax, bx, cx) - x0) / cell), int((max(ax, bx, cx) - x0) / cell) + 1):
                px = x0 + (i + .5) * cell
                w1 = ((px-ax)*(cy-ay) - (cx-ax)*(py-ay)) / area
                w2 = ((bx-ax)*(py-ay) - (px-ax)*(by-ay)) / area
                if w1 < 0 or w2 < 0 or w1 + w2 > 1:
                    continue
                z = az + w1*(bz-az) + w2*(cz-az)
                if z < lowest[j*width + i]:
                    lowest[j*width + i] = z
    floor = lo[2] if floor is None else min(floor, lo[2])
    tall = max(hi[2] - floor, 1e-9)
    near = [math.exp(-(z - floor) / (0.05 * tall)) if z < math.inf else 0.0 for z in lowest]
    wide = [math.exp(-(z - floor) / tall) if z < math.inf else 0.0 for z in lowest]
    near = _blur(near, width, height, max(1, round(0.012 * extent / cell)))
    wide = _blur(wide, width, height, max(1, round(0.07 * extent / cell)))

    def lookup(x, y):
        i, j = int((x - x0) / cell), int((y - y0) / cell)
        if not (0 <= i < width and 0 <= j < height):
            return 1.0
        k = j * width + i
        # Deeper than a light backdrop needs: on the dark mat (ADR-444) a
        # tile has little brightness to lose, so the same share reads faint.
        return max(0.2, 1.0 - 0.65 * near[k] - 0.45 * wide[k])
    return floor, lookup


def _floor(basis, bounds, size, floor_z):
    """``pixel(ox, oy, dark) -> rgb``: the dark prototype mat behind a view.

    The mat is the viewport's (:data:`PALETTE`): a ``tile_a``/``tile_b``
    checker one grid pitch square, major lines on every multiple of the pitch
    anchored at the world origin (so a walk slides over a fixed grid), fading
    into the scene background with distance. The pitch is
    :data:`GRID_PITCH_MM` at every framing: a metre is a metre in every
    image, as in the viewport (ADR-604). Every orthographic ray meets the floor plane
    at a point linear in the pixel, so each line's coverage of a pixel is
    exact to first order: that is what antialiases the grid. ``dark`` is the
    contact shadow's multiplier at the pixel. A view that cannot see the
    floor (level or from below) gets the plain background.
    """
    palette = PALETTE
    bg = palette['bg']
    right, up, toward = basis
    rx, ry, rz = right; ux, uy, uz = up; tx, ty, tz = toward
    if floor_z is None or tz <= 0.05:
        return lambda ox, oy, dark: bg
    lo, hi = bounds
    extent = max(hi[0] - lo[0], hi[1] - lo[1])
    step = extent / size
    cx0, cy0 = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    pitch = GRID_PITCH_MM
    half = pitch * LINE_FRACTION / 2

    def at(sx, sy):
        along = (floor_z - sx*rz - sy*uz) / tz
        return sx*rx + sy*ux + along*tx, sx*ry + sy*uy + along*ty
    mx, my = at(cx0, cy0)
    ax, ay = at(cx0 + step, cy0)
    bx, by = at(cx0, cy0 + step)
    # The floor footprint of one pixel along each world axis.
    wx = abs(ax - mx) + abs(bx - mx) or 1e-9
    wy = abs(ay - my) + abs(by - my) or 1e-9
    near, far = FLOOR_FADE[0] * extent, FLOOR_FADE[1] * extent
    tile_a, tile_b, line = palette['tile_a'], palette['tile_b'], palette['line']

    def pixel(ox, oy, dark):
        sx = cx0 + (ox + .5 - size / 2) * step
        sy = cy0 - (oy + .5 - size / 2) * step
        fx, fy = at(sx, sy)
        distance = math.hypot(fx - mx, fy - my)
        if distance >= far:
            return bg
        i, j = math.floor(fx / pitch), math.floor(fy / pitch)
        base = tile_a if (i + j) % 2 == 0 else tile_b
        dx, dy = fx - pitch * round(fx / pitch), fy - pitch * round(fy / pitch)
        cover_x = min(1.0, max(0.0, (half - abs(dx)) / wx + 0.5))
        cover_y = min(1.0, max(0.0, (half - abs(dy)) / wy + 0.5))
        cover = cover_x + cover_y - cover_x * cover_y
        mat = [(base[c] + (line[c] - base[c]) * cover) * dark for c in range(3)]
        if distance <= near:
            return mat
        f = (distance - near) / (far - near)
        f = f * f * (3 - 2 * f)
        return [mat[c] + (bg[c] - mat[c]) * f for c in range(3)]
    return pixel


def studio(prepared, basis, *, bounds, size, samples=SUPERSAMPLE, shadow=None):
    """A lit, antialiased image of prepared triangles on the dark prototype mat.

    Orthographic along ``basis``; ``bounds`` is the framed projection window.
    Every pixel is ``samples`` squared subsamples: a depth pass keeps the
    nearest triangle per subsample, then only visible subsamples are shaded
    (key, fill and rim light, Blinn specular per role finish, normals
    interpolated across the triangle), and the rest take the floor
    (:func:`_floor`), with ``shadow`` (from :func:`_contact_shadow`)
    darkening it under the design when the camera is above it.
    """
    right, up, toward = basis
    lo, hi = bounds
    extent = max(hi[0] - lo[0], hi[1] - lo[1])
    n = size * samples
    cx0, cy0 = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    rx, ry, rz = right; ux, uy, uz = up; tx, ty, tz = toward
    owner, shading, visits = _depth_pass(prepared, basis, bounds, size, samples)
    # Lights in view space: x right, y up, z towards the viewer.
    key = _unit((-0.45, 0.6, 0.66)); fill = _unit((0.8, 0.05, 0.6))
    half = _unit((key[0], key[1], key[2] + 1.0))
    floor_z, lookup = shadow if shadow is not None and tz > 0.05 else (None, None)
    # The mat lies at the shadow's floor, or under the design's lowest point
    # when no shadow was measured.
    mat_z = shadow[0] if shadow is not None else min((p[2] for _, tri, _ in prepared for p in tri), default=0.0)
    backdrop = _floor(basis, bounds, size, mat_z)
    image, covered = bytearray(3 * size * size), 0
    inv = 1.0 / (samples * samples)
    for oy in range(size):
        sy = cy0 - (oy + .5 - size / 2) * extent / size
        for ox in range(size):
            dark = 1.0
            if lookup is not None:
                sx = cx0 + (ox + .5 - size / 2) * extent / size
                along = (floor_z - sx*rz - sy*uz) / tz
                dark = lookup(sx*rx + sy*ux + along*tx, sx*ry + sy*uy + along*ty)
            bg = backdrop(ox, oy, dark)
            r = g = b = 0.0
            for dj in range(samples):
                row = (oy * samples + dj) * n + ox * samples
                for k in range(row, row + samples):
                    t = owner[k]
                    if t < 0:
                        r += bg[0]; g += bg[1]; b += bg[2]
                        continue
                    covered += 1
                    (rgb, finish), ax, ay, w1x, w1y, w2x, w2y, vn = shading[t]
                    px, py = k % n + .5 - ax, k // n + .5 - ay
                    w1 = min(1.0, max(0.0, px*w1x + py*w1y))
                    w2 = min(1.0 - w1, max(0.0, px*w2x + py*w2y))
                    w0 = 1.0 - w1 - w2
                    (a0, a1, a2), (b0, b1, b2), (c0, c1, c2) = vn
                    nx, ny, nz = w0*a0 + w1*b0 + w2*c0, w0*a1 + w1*b1 + w2*c1, w0*a2 + w1*b2 + w2*c2
                    length = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
                    if nz < 0:
                        length = -length
                    nx, ny, nz = nx/length, ny/length, nz/length
                    diffuse = (0.36 + 0.08 * ny + 0.58 * max(0.0, nx*key[0] + ny*key[1] + nz*key[2])
                               + 0.20 * max(0.0, nx*fill[0] + ny*fill[1] + nz*fill[2]))
                    gloss = finish[0] * max(0.0, nx*half[0] + ny*half[1] + nz*half[2]) ** finish[1]
                    # A sheen of the studio's sky, strongest on a hard finish: what
                    # keeps graphite from reading as a black hole.
                    glow = 255.0 * (gloss + 0.28 * (1.0 - nz) ** 3 + finish[0] * 0.25 * (0.5 + 0.5 * ny))
                    r += min(255.0, rgb[0]*diffuse + glow)
                    g += min(255.0, rgb[1]*diffuse + glow)
                    b += min(255.0, rgb[2]*diffuse + glow)
            at = 3 * (oy * size + ox)
            image[at] = round(r * inv); image[at+1] = round(g * inv); image[at+2] = round(b * inv)
    return image, {'projection_bounds_mm': [list(lo), list(hi)], 'pixel_visits': visits,
                   'covered_pixels': round(covered * inv), 'samples_per_pixel': samples * samples,
                   'contact_shadow': lookup is not None,
                   'floor': ({'kind': 'prototype mat', 'pitch_mm': GRID_PITCH_MM,
                              'z_mm': mat_z} if tz > 0.05 else {'kind': 'scene background'})}


def _depth_pass(prepared, basis, bounds, size, samples):
    """``(owner, shading, visits)``: the nearest triangle per subsample.

    ``owner`` holds an index into ``shading`` (or -1 for backdrop), whose
    entries are ``(material, ax, ay, w1x, w1y, w2x, w2y, view_normals)``:
    the screen plane each visible subsample reads its weights back from.
    Triangles with no normals (a measurement pass) carry ``None`` for them.
    """
    right, up, toward = basis
    lo, hi = bounds
    extent = max(hi[0] - lo[0], hi[1] - lo[1])
    _require(extent > 0, 'zero projected extent')
    n = size * samples
    scale = n / extent
    cx0, cy0 = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    depth, owner = [-math.inf] * (n * n), [-1] * (n * n)
    shading, visits = [], 0
    budget = MAX_SAMPLES * (size / SIZE) ** 2
    rx, ry, rz = right; ux, uy, uz = up; tx, ty, tz = toward
    for material, tri, normals in prepared:
        s = [(n/2 + ((p[0]*rx + p[1]*ry + p[2]*rz) - cx0) * scale,
              n/2 - ((p[0]*ux + p[1]*uy + p[2]*uz) - cy0) * scale,
              p[0]*tx + p[1]*ty + p[2]*tz) for p in tri]
        (ax, ay, az), (bx, by, bz), (qx, qy, qz) = s
        area = (bx-ax)*(qy-ay) - (qx-ax)*(by-ay)
        if abs(area) < 1e-12:
            continue
        # z as a plane over the screen, and the barycentric weights of b and
        # c as two more; the shading pass reads them back per subsample.
        w1x, w1y = (qy-ay) / area, -(qx-ax) / area
        w2x, w2y = -(by-ay) / area, (bx-ax) / area
        dzdx = (bz-az)*w1x + (qz-az)*w2x
        dzdy = (bz-az)*w1y + (qz-az)*w2y
        t = len(shading)
        vn = None if normals is None else [
            (m[0]*rx + m[1]*ry + m[2]*rz, m[0]*ux + m[1]*uy + m[2]*uz, m[0]*tx + m[1]*ty + m[2]*tz)
            for m in normals]
        shading.append((material, ax, ay, w1x, w1y, w2x, w2y, vn))
        top, mid, bot = sorted(s, key=lambda v: v[1])
        j0, j1 = max(0, math.ceil(top[1] - .5)), min(n, math.ceil(bot[1] - .5))
        for j in range(j0, j1):
            py = j + .5
            xl = top[0] + (py - top[1]) * (bot[0] - top[0]) / (bot[1] - top[1])
            if py < mid[1]:
                xr = top[0] + (py - top[1]) * (mid[0] - top[0]) / (mid[1] - top[1])
            else:
                xr = mid[0] + (py - mid[1]) * (bot[0] - mid[0]) / (bot[1] - mid[1]) if bot[1] > mid[1] else mid[0]
            if xr < xl:
                xl, xr = xr, xl
            i0, i1 = max(0, math.ceil(xl - .5)), min(n, math.ceil(xr - .5))
            if i1 <= i0:
                continue
            visits += i1 - i0
            z = az + (i0 + .5 - ax) * dzdx + (py - ay) * dzdy
            row = j * n
            for k in range(row + i0, row + i1):
                if z > depth[k]:
                    depth[k] = z
                    owner[k] = t
                z += dzdx
        _require(visits <= budget, 'pixel work budget exceeded')
    return owner, shading, visits


def design_proxies(triangles, summary, *, exclude=(), purchased=None, appearance=None, palette=None):
    """A1's image proxies of the drawn design, measured in the hero view.

    P1 ``hardware_silhouette_share``: of the hero pixels the design covers,
    the fraction whose front-most surface is a purchased component (``None``
    when there is no inventory to say what was purchased). P3
    ``material_count``: the distinct colours of the objects visible in the
    hero. Both are frozen in docs/probes/ot10/README.md with their bars;
    the hero is measured at PROXY_SIZE by a depth pass alone, so ``look``
    and review report the same numbers whatever size they draw at.
    ``exclude`` and the material arguments are :func:`look`'s.
    """
    looks = materials(summary, purchased=purchased, appearance=appearance, palette=palette)
    names = [name for name in summary['objects'] if name not in exclude]
    prepared = [(name, points, None) for name in names
                for _, points in triangles[summary['objects'][name]['first']:
                                           summary['objects'][name]['first'] + summary['objects'][name]['triangles']]]
    owner, shading, _ = _depth_pass(prepared, HERO, _frame(prepared, HERO, 0.10), PROXY_SIZE, SUPERSAMPLE)
    pixels = {}
    for t in owner:
        if t >= 0:
            name = shading[t][0]
            pixels[name] = pixels.get(name, 0) + 1
    covered = sum(pixels.values())
    hardware = None if purchased is None else sum(c for name, c in pixels.items() if name in purchased)
    share = None if hardware is None or not covered else hardware / covered
    colours = sorted({'#%02X%02X%02X' % tuple(looks[name][1]) for name in pixels})
    p1, p3 = PROXY_BARS['hardware_silhouette_share'], PROXY_BARS['material_count']
    return {
        'view': 'hero', 'size': PROXY_SIZE, 'samples_per_pixel': SUPERSAMPLE * SUPERSAMPLE,
        'definitions': 'docs/probes/ot10/README.md',
        'hardware_silhouette_share': {
            'value': None if share is None else round(share, 4), 'bar': dict(p1),
            'meets': None if share is None else share <= p1['max'],
            'design_subsamples': covered, 'hardware_subsamples': hardware,
            **({} if purchased is not None else {'reason': 'no inventory to tell purchased from printed'}),
        },
        'material_count': {
            'value': len(colours), 'materials': colours, 'bar': dict(p3),
            'meets': p3['min'] <= len(colours) <= p3['max'],
        },
    }


def edge_proxy(inventory, environment=()):
    """A1's P2 ``sharp_outside_edge_share`` from the inventory block (ADR-415).

    Sharp convex edge length over total solid edge length, summed over the
    printed components as the engine measured them. ``environment`` names
    the world geometry the fit reports (a floor): it is uncatalogued but
    not printed, so it is left out here as P1 and ``look`` leave it out of
    the picture (ADR-424). ``None`` with a reason when there is no
    inventory to say what was printed, or when a printed part carries no
    edge measurement (zero would be a false pass). With no printed edges
    at all the share is 0, as frozen. ``unresolved_edges`` counts edges the
    engine could not evaluate: they are in the total and never sharp, so a
    nonzero count makes the share a lower bound.
    """
    bar = PROXY_BARS['sharp_outside_edge_share']
    edges = (inventory or {}).get('printed_edges') if inventory and inventory.get('available', True) else None
    if not isinstance(edges, dict):
        return {'value': None, 'bar': dict(bar), 'meets': None,
                'reason': 'no inventory to tell printed from purchased'}
    left_out = set(environment)
    counted = {name: own for name, own in edges['by_component'].items() if name not in left_out}
    unmeasured = [name for name in edges['unmeasured'] if name not in left_out]
    total = sum(own['edge_length_mm'] for own in counted.values())
    sharp = sum(own['sharp_convex_length_mm'] for own in counted.values())
    result = {'bar': dict(bar), 'edge_length_mm': round(total, 3),
              'sharp_convex_length_mm': round(sharp, 3),
              'unresolved_edges': sum(own['unresolved_edges'] for own in counted.values()),
              'printed_components': len(counted) + len(unmeasured),
              'left_out_as_environment': sorted(left_out & (set(edges['by_component']) | set(edges['unmeasured'])))}
    if unmeasured:
        return {**result, 'value': None, 'meets': None, 'unmeasured': unmeasured,
                'reason': 'printed parts with no edge measurement: ' + ', '.join(unmeasured)}
    share = sharp / total if total else 0.0
    return {**result, 'value': round(share, 4), 'meets': share <= bar['max']}


def _unit(v):
    length = math.sqrt(sum(c*c for c in v))
    return tuple(c / length for c in v)


def _frame(prepared, basis, pad):
    right, up = basis[0], basis[1]
    xs = [p[0]*right[0] + p[1]*right[1] + p[2]*right[2] for _, tri, _ in prepared for p in tri]
    ys = [p[0]*up[0] + p[1]*up[1] + p[2]*up[2] for _, tri, _ in prepared for p in tri]
    lo, hi = [min(xs), min(ys)], [max(xs), max(ys)]
    margin = pad * max(hi[0] - lo[0], hi[1] - lo[1])
    return [lo[0] - margin, lo[1] - margin], [hi[0] + margin, hi[1] + margin]


def _studio_parts(triangles, summary, drawn_names, looks):
    parts = []
    for name in drawn_names:
        item = summary['objects'][name]
        role, rgb = looks[name]
        tris = [points for _, points in triangles[item['first']:item['first'] + item['triangles']]]
        parts.append(((rgb, FINISH[role]), tris))
    return parts


def world_top(triangles, summary, environment):
    """The top of the world geometry ``environment`` names, or ``None`` without any.

    Where the mat is laid (ADR-604): the design's own floor is never drawn,
    and the mat stands in for it at its top face.
    """
    tops = [p[2] for name in environment if name in summary['objects']
            for _, tri in triangles[summary['objects'][name]['first']:
                                    summary['objects'][name]['first'] + summary['objects'][name]['triangles']]
            for p in tri]
    return max(tops) if tops else None


def look(triangles, summary, views, *, focus=(), exclude=(), purchased=None, appearance=None,
         palette=None, size=LOOK_SIZE):
    """The agent's own views of a snapshot: PNG bytes per requested view.

    ``exclude`` names objects left out entirely (environment geometry: a floor
    would otherwise set the framing and shrink the design to a speck);
    ``focus`` names the objects the view is framed on, with everything else
    still drawn; ``purchased``, ``appearance`` and ``palette`` choose each
    object's material (see :func:`materials`). Every view is a studio image
    (:func:`studio`); ``hero`` is the presentation view. The mat lies at
    the top of the excluded world geometry when there is any.
    """
    objects = summary['objects']
    unknown = sorted(set(focus) - set(objects))
    _require(not unknown, 'unknown focus ' + ', '.join(unknown) + '; drawable: ' + ', '.join(sorted(objects)))
    _require(all(v in LOOK_VIEWS for v in views),
             'unknown view; choose from ' + ', '.join(LOOK_VIEWS))
    looks = materials(summary, purchased=purchased, appearance=appearance, palette=palette)
    names = [name for name in objects if name not in exclude]
    framed_names = [name for name in names if not focus or name in focus]
    _require(bool(framed_names) and any(objects[n]['triangles'] for n in framed_names),
             'nothing to draw once environment geometry is left out')
    prepared = _prepare(_studio_parts(triangles, summary, names, looks))
    framed = prepared if not focus else _prepare(_studio_parts(triangles, summary, framed_names, looks))
    shadow = _contact_shadow(prepared, floor=world_top(triangles, summary, exclude))
    shots = []
    for view in views:
        basis = LOOK_VIEWS[view]
        bounds = _frame(framed, basis, 0.10 if view == 'hero' else 0.04)
        pixels, details = studio(prepared, basis, bounds=bounds, size=size, shadow=shadow)
        details['materials'] = sorted({'#%02X%02X%02X' % looks[name][1] for name in names})
        shots.append((view, png(pixels, size), details))
    return shots


def world(fit):
    """The names the fit block calls world geometry (a declared floor)."""
    return {str(row.get('first') or '') for row in (fit or {}).get('failing') or []
            if row.get('status') == 'world geometry'}


def classify(summary, fit=None, inventory=None):
    """``(environment, purchased)`` for a snapshot, from the fit and inventory blocks.

    Environment is the world geometry the fit names (a floor); purchased is
    every object whose source no inventory row calls uncatalogued, or
    ``None`` when there is no inventory to say.
    """
    environment = world(fit) & set(summary['objects'])
    purchased = None
    if inventory and inventory.get('available', True) and 'uncatalogued_sources' in inventory:
        printed = set(inventory.get('uncatalogued_sources') or [])
        purchased = {name for name, item in summary['objects'].items() if item['source'] not in printed}
    return environment, purchased


def declared(inventory):
    """``(appearance, palette)`` the script declared, as the inventory block carries them.

    ``appearance`` is component -> role for the components that declare
    one; ``palette`` is role -> rgb for the roles the assembly recoloured
    (ADR-413). Both are empty for a design that declares nothing, or when
    there is no readable inventory, and :func:`materials` then falls back
    on supplier.
    """
    if not inventory or not inventory.get('available', True):
        return {}, {}
    appearance = {str(k): str(v) for k, v in dict(inventory.get('appearance') or {}).items()}
    palette = {}
    for role, colour in dict(inventory.get('palette') or {}).items():
        text = str(colour)
        _require(len(text) == 7 and text[0] == '#', f'invalid palette colour {text!r} for {role}')
        try:
            palette[str(role)] = tuple(int(text[i:i + 2], 16) for i in (1, 3, 5))
        except ValueError as exc:
            raise StudioError(f'render: invalid palette colour {text!r} for {role}') from exc
    return appearance, palette


def describe_proxies(proxies):
    """One line for a report: each proxy's value against its bar."""
    p1, p3 = proxies['hardware_silhouette_share'], proxies['material_count']

    def share(proxy):
        if proxy['value'] is None:
            return 'unmeasured (' + proxy['reason'] + ')'
        text = '{:.1%} ({:s} {:.0%})'.format(proxy['value'], 'meets' if proxy['meets'] else 'over',
                                             proxy['bar']['max'])
        if proxy.get('unresolved_edges'):
            text += ', a lower bound: {:d} edge(s) unresolved'.format(proxy['unresolved_edges'])
        return text
    edges = ''
    if 'sharp_outside_edge_share' in proxies:
        edges = '; sharp printed outside edges ' + share(proxies['sharp_outside_edge_share'])
    return 'hardware share of hero silhouette {:s}{:s}; {:d} material(s) {:s} ({:s} {:d}-{:d})'.format(
        share(p1), edges, p3['value'], ', '.join(p3['materials']), 'meets' if p3['meets'] else 'outside',
        p3['bar']['min'], p3['bar']['max'])


# --- The concept sheet (ot10 A6, ADR-430) ------------------------------------

WIDTH, HEIGHT = 1536, 1024
#: The orthographic views the sheet draws as lines, in the order it lays them out.
LINE_VIEWS = ('front', 'right', 'top')
LINE_SIZE = 204
#: Two faces of one object meeting at more than this draw a line.
LINE_CREASE_DEGREES = 35.0
#: The sheet is drawn on the dark scene (ot10 A8, ADR-444): paper is the
#: viewport's background, and ink, muted ink and rules are the review page's
#: ``--ink``, ``--ink-2`` and ``--rule``, all read by :data:`PALETTE` from the
#: files the dashboard itself loads.
PAPER = PALETTE['bg']
INK = PALETTE['ink']
MUTED = PALETTE['ink_2']
RULE = PALETTE['rule']
#: The catalog family whose placed components the sheet counts as servos.
SERVO_FAMILY = 'servo'

# --- The type face (orun4 H1, ADR-568) ---------------------------------------
#
# Every caption, label and clock the renders draw is set in Noto Sans Regular,
# a plain open sans-serif (SIL OFL 1.1, docs/PROVENANCE.md), shipped beside
# this module as a TrueType file cut down to the characters drawn. It is read
# and rasterised here in the standard library: the outlines' quadratic curves
# are flattened, and each pixel's ink is the outline's exact horizontal
# coverage averaged over FONT_ROWS_PER_PIXEL scanlines.

FONT_FILE = Path(__file__).resolve().with_name('NotoSans-Regular-subset.ttf')
#: A text ``scale`` sets capitals ``CAP_UNITS * scale`` px tall, the height the
#: retired 5x7 face drew them, so every layout keeps its rows.
CAP_UNITS = 7
FONT_ROWS_PER_PIXEL = 5
#: Straight segments per quadratic curve: enough at the sizes drawn here.
CURVE_STEPS = 6


class Face:
    """A TrueType face: character map, advances and glyph outlines."""

    def __init__(self, data):
        self.data = data
        count = struct.unpack_from('>H', data, 4)[0]
        self.tables = {}
        for i in range(count):
            tag, _sum, offset, length = struct.unpack_from('>4sIII', data, 12 + 16 * i)
            self.tables[tag.decode('latin-1')] = (offset, length)
        head = self.tables['head'][0]
        self.units_per_em = struct.unpack_from('>H', data, head + 18)[0]
        long_loca = struct.unpack_from('>h', data, head + 50)[0] == 1
        glyphs = struct.unpack_from('>H', data, self.tables['maxp'][0] + 4)[0]
        metrics = struct.unpack_from('>H', data, self.tables['hhea'][0] + 34)[0]
        loca = self.tables['loca'][0]
        if long_loca:
            self.loca = struct.unpack_from('>%dI' % (glyphs + 1), data, loca)
        else:
            self.loca = tuple(2 * v for v in struct.unpack_from('>%dH' % (glyphs + 1), data, loca))
        hmtx = self.tables['hmtx'][0]
        advances = [struct.unpack_from('>H', data, hmtx + 4 * i)[0] for i in range(metrics)]
        self.advances = advances + [advances[-1]] * (glyphs - metrics)
        self.cap_height = struct.unpack_from('>h', data, self.tables['OS/2'][0] + 88)[0]
        self.cmap = self._cmap()
        self._outlines = {}

    def _cmap(self):
        data, base = self.data, self.tables['cmap'][0]
        found = {}
        for i in range(struct.unpack_from('>H', data, base + 2)[0]):
            platform, encoding, offset = struct.unpack_from('>HHI', data, base + 4 + 8 * i)
            at = base + offset
            if (platform, encoding) not in ((3, 1), (0, 3)) or struct.unpack_from('>H', data, at)[0] != 4:
                continue
            segments = struct.unpack_from('>H', data, at + 6)[0] // 2
            ends = struct.unpack_from('>%dH' % segments, data, at + 14)
            starts = struct.unpack_from('>%dH' % segments, data, at + 16 + 2 * segments)
            deltas = struct.unpack_from('>%dh' % segments, data, at + 16 + 4 * segments)
            ranges_at = at + 16 + 6 * segments
            ranges = struct.unpack_from('>%dH' % segments, data, ranges_at)
            for k in range(segments):
                for code in range(starts[k], min(ends[k], 0xFFFE) + 1):
                    if ranges[k] == 0:
                        glyph = (code + deltas[k]) & 0xFFFF
                    else:
                        where = ranges_at + 2 * k + ranges[k] + 2 * (code - starts[k])
                        glyph = struct.unpack_from('>H', data, where)[0]
                        glyph = (glyph + deltas[k]) & 0xFFFF if glyph else 0
                    if glyph:
                        found[chr(code)] = glyph
            return found
        raise StudioError('the type face has no Unicode character map')

    def outline(self, glyph):
        """The glyph's closed contours as polylines in font units, y up."""
        if glyph not in self._outlines:
            self._outlines[glyph] = self._read(glyph)
        return self._outlines[glyph]

    def _read(self, glyph):
        data = self.data
        start, end = self.loca[glyph], self.loca[glyph + 1]
        if start == end:
            return []
        at = self.tables['glyf'][0] + start
        contours = struct.unpack_from('>h', data, at)[0]
        at += 10
        if contours < 0:
            return self._composite(at)
        ends = struct.unpack_from('>%dH' % contours, data, at)
        at += 2 * contours
        at += 2 + struct.unpack_from('>H', data, at)[0]
        count = ends[-1] + 1 if contours else 0
        flags = []
        while len(flags) < count:
            flag = data[at]
            at += 1
            repeat = 1
            if flag & 8:
                repeat += data[at]
                at += 1
            flags.extend([flag] * repeat)
        coordinates = []
        for short, same in ((2, 16), (4, 32)):
            value, values = 0, []
            for flag in flags[:count]:
                if flag & short:
                    step = data[at]
                    at += 1
                    value += step if flag & same else -step
                elif not flag & same:
                    value += struct.unpack_from('>h', data, at)[0]
                    at += 2
                values.append(value)
            coordinates.append(values)
        points = [(x, y, bool(f & 1)) for x, y, f in zip(coordinates[0], coordinates[1], flags)]
        result, first = [], 0
        for last in ends:
            result.append(_flatten(points[first:last + 1]))
            first = last + 1
        return result

    def _composite(self, at):
        data, result = self.data, []
        while True:
            flags, glyph = struct.unpack_from('>HH', data, at)
            at += 4
            if flags & 1:
                dx, dy = struct.unpack_from('>hh', data, at)
                at += 4
            else:
                dx, dy = struct.unpack_from('>bb', data, at)
                at += 2
            a, b, c, d = 1.0, 0.0, 0.0, 1.0
            if flags & 8:
                a = d = struct.unpack_from('>h', data, at)[0] / 16384
                at += 2
            elif flags & 0x40:
                a, d = (v / 16384 for v in struct.unpack_from('>hh', data, at))
                at += 4
            elif flags & 0x80:
                a, b, c, d = (v / 16384 for v in struct.unpack_from('>hhhh', data, at))
                at += 8
            _require(flags & 2, 'the type face has a composite glyph placed by point, which is not read')
            for contour in self.outline(glyph):
                result.append([(a * x + c * y + dx, b * x + d * y + dy) for x, y in contour])
            if not flags & 0x20:
                return result

    def glyph(self, ch):
        return self.cmap.get(ch) or self.cmap['?']


def _flatten(points):
    """A closed TrueType contour, on- and off-curve points, as a polyline."""
    if not points:
        return []
    n = len(points)
    start = next((i for i, p in enumerate(points) if p[2]), None)
    if start is None:  # every point off the curve: begin between the first two
        (x0, y0, _), (x1, y1, _) = points[0], points[1 % n]
        points, start = [((x0 + x1) / 2, (y0 + y1) / 2, True)] + list(points), 0
        n += 1
    ring = points[start:] + points[:start]
    line = [ring[0][:2]]
    control = None
    for x, y, on in ring[1:] + ring[:1]:
        if on:
            if control is None:
                line.append((x, y))
            else:
                line.extend(_curve(line[-1], control, (x, y)))
                control = None
        elif control is None:
            control = (x, y)
        else:
            middle = ((control[0] + x) / 2, (control[1] + y) / 2)
            line.extend(_curve(line[-1], control, middle))
            control = (x, y)
    return line


def _curve(p0, p1, p2):
    out = []
    for k in range(1, CURVE_STEPS + 1):
        t = k / CURVE_STEPS
        u = 1 - t
        out.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return out


FACE = Face(FONT_FILE.read_bytes())
_GLYPHS = {}


def _em_px(scale):
    return CAP_UNITS * scale * FACE.units_per_em / FACE.cap_height


def _coverage(glyph, scale):
    """``(left, top, width, height, alpha)``: the glyph's ink at ``scale``, relative to
    its pen position on the capital line; alpha is one byte per pixel."""
    key = (glyph, scale)
    if key in _GLYPHS:
        return _GLYPHS[key]
    k = _em_px(scale) / FACE.units_per_em
    cap = CAP_UNITS * scale
    contours = [[(x * k, cap - y * k) for x, y in c] for c in FACE.outline(glyph) if len(c) > 1]
    if not contours:
        _GLYPHS[key] = (0, 0, 0, 0, b'')
        return _GLYPHS[key]
    xs = [x for c in contours for x, _ in c]
    ys = [y for c in contours for _, y in c]
    left, top = math.floor(min(xs)), math.floor(min(ys))
    width, height = math.ceil(max(xs)) - left + 1, math.ceil(max(ys)) - top
    edges = []
    for c in contours:
        for (x0, y0), (x1, y1) in zip(c, c[1:] + c[:1]):
            if y0 != y1:
                edges.append((x0 - left, y0 - top, x1 - left, y1 - top))
    ink = [0.0] * (width * height)
    share = 1.0 / FONT_ROWS_PER_PIXEL
    for row in range(height):
        base = row * width
        for sub in range(FONT_ROWS_PER_PIXEL):
            y = row + (sub + 0.5) * share
            crossings = []
            for x0, y0, x1, y1 in edges:
                if (y0 <= y < y1) or (y1 <= y < y0):
                    crossings.append((x0 + (y - y0) * (x1 - x0) / (y1 - y0), 1 if y1 > y0 else -1))
            crossings.sort()
            winding = 0
            for (xa, step), (xb, _) in zip(crossings, crossings[1:]):
                winding += step
                if winding and xb > xa:
                    _span(ink, base, width, xa, xb, share)
    alpha = bytes(min(255, round(255 * v)) for v in ink)
    _GLYPHS[key] = (left, top, width, height, alpha)
    return _GLYPHS[key]


def _span(ink, base, width, xa, xb, weight):
    """Adds ``weight`` times the exact cover of ``[xa, xb)`` to one pixel row."""
    xa, xb = max(0.0, xa), min(float(width), xb)
    i = int(xa)
    while i < width and i < xb:
        cover = min(xb, i + 1) - max(xa, i)
        if cover > 0:
            ink[base + i] += cover * weight
        i += 1


def advance_px(text, scale):
    """The pen's travel across ``text`` at ``scale``, in px."""
    k = _em_px(scale) / FACE.units_per_em
    return sum(FACE.advances[FACE.glyph(ch)] for ch in str(text)) * k


class Canvas:
    """An RGB image in a bytearray, with the few marks the sheet needs."""

    def __init__(self, width, height, fill):
        self.width, self.height = width, height
        self.pixels = bytearray(bytes(fill) * (width * height))

    def rect(self, x, y, w, h, colour):
        x0, y0, x1, y1 = max(0, x), max(0, y), min(self.width, x + w), min(self.height, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(colour) * (x1 - x0)
        for j in range(y0, y1):
            at = 3 * (j * self.width + x0)
            self.pixels[at:at + len(row)] = row

    def paste(self, x, y, pixels, w, h):
        for j in range(h):
            at = 3 * ((y + j) * self.width + x)
            self.pixels[at:at + 3 * w] = pixels[3 * j * w:3 * (j + 1) * w]

    def line(self, x0, y0, x1, y1, colour, width=1):
        """A straight mark ``width`` px thick from ``(x0, y0)`` to ``(x1, y1)``."""
        steps = max(1, round(max(abs(x1 - x0), abs(y1 - y0))))
        for i in range(steps + 1):
            t = i / steps
            self.rect(round(x0 + (x1 - x0) * t) - width // 2, round(y0 + (y1 - y0) * t) - width // 2,
                      width, width, colour)

    def text(self, x, y, text, scale, colour):
        """Draws ``text`` in the face, capitals ``CAP_UNITS * scale`` px tall with
        their top at ``y``; returns the x after it."""
        pen = float(x)
        k = _em_px(scale) / FACE.units_per_em
        for ch in str(text):
            glyph = FACE.glyph(ch)
            left, top, w, h, alpha = _coverage(glyph, scale)
            ox, oy = round(pen) + left, y + top
            for j in range(h):
                yy = oy + j
                if not 0 <= yy < self.height:
                    continue
                for i in range(w):
                    a = alpha[j * w + i]
                    xx = ox + i
                    if a and 0 <= xx < self.width:
                        at = 3 * (yy * self.width + xx)
                        for c in range(3):
                            self.pixels[at + c] = (self.pixels[at + c] * (255 - a) + colour[c] * a + 127) // 255
            pen += FACE.advances[glyph] * k
        return round(pen)


def text_width(text, scale):
    return round(advance_px(text, scale))


def fitted_scale(text, width, largest):
    """The largest scale up to ``largest`` at which ``text`` fits ``width``."""
    for scale in range(largest, 0, -1):
        if text_width(text, scale) <= width:
            return scale
    return 1


def line_view(triangles, summary, names, basis, *, size=LINE_SIZE, bounds=None):
    """An orthographic line drawing: ``(rgb pixels, details)``.

    Every pixel is 2x2 subsamples of the renderer's own depth pass, keyed by
    object and flat face normal. A subsample is ink where the nearest surface
    changes object, meets the backdrop (the silhouette, drawn on both sides
    so it reads heavier), or turns by more than LINE_CREASE_DEGREES within
    one object; coverage is then box-filtered to grey, which antialiases it.
    ``bounds`` is the square projected window to draw, framed on the
    drawing when omitted; a blueprint passes its own so every view shares
    one scale.
    """
    prepared = []
    for index, name in enumerate(names):
        item = summary['objects'][name]
        for _, tri in triangles[item['first']:item['first'] + item['triangles']]:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
            ux, uy, uz, vx, vy, vz = bx - ax, by - ay, bz - az, cx - ax, cy - ay, cz - az
            n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
            length = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])
            if length:
                prepared.append(((index, (n[0] / length, n[1] / length, n[2] / length)), tri, None))
    _require(bool(prepared), 'nothing to draw in a line view')
    samples = SUPERSAMPLE
    owner, shading, visits = _depth_pass(prepared, basis, bounds or _frame(prepared, basis, 0.06),
                                                size, samples)
    n = size * samples
    crease = math.cos(math.radians(LINE_CREASE_DEGREES))
    ink = bytearray(n * n)
    for j in range(n):
        row = j * n
        for i in range(n):
            k = row + i
            a = owner[k]
            for k2 in ((k + 1) if i + 1 < n else -1, (k + n) if j + 1 < n else -1):
                if k2 < 0:
                    continue
                b = owner[k2]
                if a == b:
                    continue
                if a < 0 or b < 0:
                    ink[k] = ink[k2] = 1
                    continue
                (oa, na), (ob, nb) = shading[a][0], shading[b][0]
                if oa != ob or na[0] * nb[0] + na[1] * nb[1] + na[2] * nb[2] < crease:
                    ink[k] = 1
    image, drawn = bytearray(3 * size * size), 0
    share = 1.0 / (samples * samples)
    for y in range(size):
        for x in range(size):
            c = 0
            for dj in range(samples):
                at = (y * samples + dj) * n + x * samples
                c += sum(ink[at:at + samples])
            c *= share
            drawn += c > 0
            p = 3 * (y * size + x)
            for q in range(3):
                image[p + q] = round(PAPER[q] + (INK[q] - PAPER[q]) * c)
    return image, {'size': size, 'pixel_visits': visits, 'ink_pixels': drawn,
                   'crease_degrees': LINE_CREASE_DEGREES}


def design_mass(root, revision, environment):
    """``(kg, reason)``: the design's mass from the accepted dynamics model.

    Read from the accepted attempt's own ``result.json`` -- the MJCF
    output's per-component inertials, which the engine verified against
    MuJoCo when it published them -- and summed over every component but
    the environment. ``kg`` is ``None`` and ``reason`` says why when there
    is no model to read, or the pinned attempt is not the ``revision``
    drawn.
    """
    root = Path(root)
    try:
        state = json.loads((root / 'script.json').read_text(encoding='utf-8'))
        pin = state.get('accepted_attempt') or {}
        staging = (root / str(pin.get('staging') or '')).resolve()
        if (state.get('accepted_revision') != revision or pin.get('revision') != revision
                or not pin.get('staging')
                or not staging.is_relative_to((root / 'script_artifacts').resolve())):
            return None, 'the accepted attempt is not the revision drawn'
        result = json.loads((staging / 'result.json').read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return None, 'no readable accepted attempt'
    if result.get('digest') != state.get('accepted_digest'):
        return None, 'the accepted attempt does not carry the accepted digest'
    for output in result.get('outputs') or []:
        if not isinstance(output, dict) or output.get('type') != 'mjcf':
            continue
        inertials = ((output.get('assembly_data') or {}).get('dynamics') or {}).get('inertials')
        if isinstance(inertials, list) and inertials:
            try:
                return sum(float(row['mass_kg']) for row in inertials
                           if row.get('component_output') not in environment), None
            except (KeyError, TypeError, ValueError):
                return None, 'the dynamics model carries an unreadable inertial'
    return None, 'the accepted revision publishes no dynamics model'


def key_numbers(root, summary, names, inventory, environment):
    """The sheet's numbers: name, mass, servo count and size, each with its source."""
    mass, why = design_mass(root, summary['revision'], set(environment))
    servos = None
    if inventory and inventory.get('available', True) and 'catalog_counts' in inventory:
        servos = sum(int(count) for key, count in dict(inventory['catalog_counts']).items()
                     if str(key).split('/', 1)[0] == SERVO_FAMILY)
    lo = [min(summary['objects'][n]['bounds_mm'][0][j] for n in names) for j in range(3)]
    hi = [max(summary['objects'][n]['bounds_mm'][1][j] for n in names) for j in range(3)]
    numbers = {
        'name': Path(root).resolve().name,
        'mass_kg': None if mass is None else round(mass, 4),
        'servo_count': servos,
        'size_mm': [round(hi[j] - lo[j], 1) for j in range(3)],
        'sources': {'mass_kg': 'accepted dynamics model (MJCF inertials), environment excluded',
                    'servo_count': f'inventory catalog_counts, family {SERVO_FAMILY!r}',
                    'size_mm': 'accepted solids, environment excluded, X x Y x Z'},
    }
    if mass is None:
        numbers['mass_reason'] = why
    if servos is None:
        numbers['servo_reason'] = 'no readable inventory'
    return numbers


def _figure(value, unit, digits):
    return 'N/A' if value is None else f'{value:.{digits}f} {unit}'


def compose(hero, hero_size, lines, numbers, palette, roles, proxies, revision):
    """The sheet as PNG bytes. ``lines`` maps each of LINE_VIEWS to its pixels."""
    sheet = Canvas(WIDTH, HEIGHT, PAPER)
    scale = HEIGHT / hero_size
    _require(scale == 1, 'the sheet is laid out for a 1024 px hero')
    sheet.paste(0, 0, hero, hero_size, hero_size)
    x0, width = hero_size + 40, WIDTH - hero_size - 80
    name = numbers['name']
    sheet.text(x0, 40, name, fitted_scale(name, width, 5), INK)
    sheet.text(x0, 96, 'Cadex concept sheet', 2, MUTED)
    sheet.text(x0, 120, 'rev ' + revision[:12], 2, MUTED)
    sheet.rect(x0, 152, width, 2, RULE)
    size = ' x '.join(f'{v:.0f}' for v in numbers['size_mm']) + ' mm'
    rows = (('mass', _figure(numbers['mass_kg'], 'kg', 2)),
            ('servos', 'N/A' if numbers['servo_count'] is None else str(numbers['servo_count'])),
            ('size  w x d x h', size))
    y = 170
    for label, value in rows:
        sheet.text(x0, y, label, 2, MUTED)
        sheet.text(x0, y + 20, value, fitted_scale(value, width, 4), INK)
        y += 64
    sheet.rect(x0, y + 4, width, 2, RULE)
    y += 20
    sheet.text(x0, y, 'palette', 2, MUTED)
    shown = [role for role in ('shell', 'mechanism', 'accent') if role in roles]
    swatch = (width - 24 * max(0, len(shown) - 1)) // max(1, len(shown))
    for index, role in enumerate(shown):
        x = x0 + index * (swatch + 24)
        colour = palette[role]
        rgb = tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))
        sheet.rect(x - 1, y + 21, swatch + 2, 58, RULE)
        sheet.rect(x, y + 22, swatch, 56, rgb)
        sheet.text(x, y + 88, role, 2, INK)
        sheet.text(x, y + 108, colour, 2, MUTED)
    y += 140
    sheet.rect(x0, y, width, 2, RULE)
    y += 16
    gap = width - 2 * LINE_SIZE
    spots = {'front': (x0, y), 'right': (x0 + LINE_SIZE + gap, y), 'top': (x0, y + LINE_SIZE + 32)}
    for view in LINE_VIEWS:
        x, top = spots[view]
        sheet.paste(x, top, lines[view], LINE_SIZE, LINE_SIZE)
        sheet.text(x, top + LINE_SIZE + 6, view, 2, MUTED)
    x, top = spots['right'][0], spots['top'][1] + 20
    sheet.text(x, top, 'measures', 2, MUTED)
    for index, (label, key) in enumerate((('hardware', 'hardware_silhouette_share'),
                                          ('sharp edges', 'sharp_outside_edge_share'))):
        value = (proxies.get(key) or {}).get('value')
        sheet.text(x, top + 28 + 44 * index, label, 2, MUTED)
        sheet.text(x, top + 48 + 44 * index, 'N/A' if value is None else f'{value:.0%}', 2, INK)
    count = (proxies.get('material_count') or {}).get('value')
    sheet.text(x, top + 116, 'materials', 2, MUTED)
    sheet.text(x, top + 136, 'N/A' if count is None else str(count), 2, INK)
    return png(sheet.pixels, WIDTH, HEIGHT)


# --- The blueprint sheet: a dimensioned multi-view drawing (ADR-516) ---------

#: The views a blueprint may draw: the three orthographic line views and the
#: two three-quarter views. Line drawings all, on the dark floor.
BLUEPRINT_VIEWS = ('front', 'right', 'top', 'iso', 'iso_back')
#: The default sheet, row-major on a 2x2 grid: top above front and right
#: beside front is the third-angle arrangement, with the iso in the spare cell.
BLUEPRINT_DEFAULT_VIEWS = ('top', 'iso', 'front', 'right')
BLUEPRINT_MAX_VIEWS = 4
BLUEPRINT_ORTHO = ('front', 'right', 'top')
BLUEPRINT_MAX_NAME = 60
BLUEPRINT_MAX_NOTES = 400
#: Balloons on one sheet. More parts than this are named by size, largest first.
BLUEPRINT_MAX_CALLOUTS = 12
BLUEPRINT_RECIPE_SCHEMA = 'cadex-blueprint-recipe-v1'
BLUEPRINT_RECIPE_KEYS = ('name', 'views', 'callouts', 'dimensions', 'notes')
#: A declared measurement shorter than this on paper is not drawn in that view.
BLUEPRINT_MIN_DIMENSION_PX = 24
_BP_MARGIN, _BP_COLUMN, _BP_PAD = 24, 384, 64
BLUEPRINT_APPROXIMATION = ('orthographic line drawing of the standard tessellation at the solved '
                           'pose; overall extents are measured on that tessellation, declared '
                           'measurements are the engine\'s own numbers')


def blueprint_recipe(raw):
    """The validated recipe a sheet is drawn from, refusing in sentences that carry the fix.

    ``name`` is the sheet's identity and title; ``views`` 1 to 4 of
    :data:`BLUEPRINT_VIEWS`; ``callouts`` true, false or a list of part
    names to balloon; ``dimensions`` true or false; ``notes`` a short text.
    The result is what the store keeps in ``meta``, so a sheet re-renders.
    """
    _require(isinstance(raw, dict), 'a blueprint recipe is an object')
    unknown = sorted(set(raw) - set(BLUEPRINT_RECIPE_KEYS) - {'schema'})
    _require(not unknown, 'unknown blueprint key(s) ' + ', '.join(unknown) + '; it takes ' +
             ', '.join(BLUEPRINT_RECIPE_KEYS))
    name = ' '.join(str(raw.get('name') or '').split())
    _require(0 < len(name) <= BLUEPRINT_MAX_NAME,
             f'a blueprint needs a name of 1 to {BLUEPRINT_MAX_NAME} characters, e.g. "gearbox overview"')
    views = raw.get('views')
    views = list(BLUEPRINT_DEFAULT_VIEWS) if views is None else views
    _require(isinstance(views, list) and 0 < len(views) <= BLUEPRINT_MAX_VIEWS and
             all(view in BLUEPRINT_VIEWS for view in views) and len(set(views)) == len(views),
             f'views is 1 to {BLUEPRINT_MAX_VIEWS} distinct names from ' + ', '.join(BLUEPRINT_VIEWS))
    callouts = raw.get('callouts', True)
    _require(isinstance(callouts, bool) or isinstance(callouts, list) and
             all(isinstance(item, str) and item for item in callouts) and
             len(callouts) <= BLUEPRINT_MAX_CALLOUTS,
             f'callouts is true, false or a list of at most {BLUEPRINT_MAX_CALLOUTS} part names')
    dimensions = raw.get('dimensions', True)
    _require(isinstance(dimensions, bool), 'dimensions is true or false')
    notes = ' '.join(str(raw.get('notes') or '').split())
    _require(len(notes) <= BLUEPRINT_MAX_NOTES, f'notes is at most {BLUEPRINT_MAX_NOTES} characters')
    return {'schema': BLUEPRINT_RECIPE_SCHEMA, 'name': name, 'views': list(views),
            'callouts': callouts if isinstance(callouts, bool) else list(callouts),
            'dimensions': dimensions, 'notes': notes}


def _paper_text(text):
    """``text`` in the sheet's face: a diameter is written as the face's slashed O."""
    for sign in ('\N{DIAMETER SIGN}', '\N{EMPTY SET}'):
        text = str(text).replace(sign, '\N{LATIN CAPITAL LETTER O WITH STROKE}')
    return ''.join(ch if ch in FACE.cmap else '?' for ch in text)


def _wrap(text, scale, width):
    lines, line = [], ''
    for word in str(text).split():
        trial = (line + ' ' + word).strip()
        if line and text_width(trial, scale) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


def _dimension(sheet, a, b, text, offset=(0, 0), side=None):
    """A dimension line from ``a`` to ``b`` (pixels) with ticks and its number beside it:
    ``side`` is ``below``, ``above``, ``right`` or ``left`` of the line, by default
    below a horizontal one and right of a vertical one."""
    (ax, ay), (bx, by) = a, b
    ox, oy = offset
    if ox or oy:  # extension lines out to an offset dimension line
        sheet.line(ax, ay, ax + ox, ay + oy, MUTED)
        sheet.line(bx, by, bx + ox, by + oy, MUTED)
        ax, ay, bx, by = ax + ox, ay + oy, bx + ox, by + oy
    sheet.line(ax, ay, bx, by, INK)
    for x, y in ((ax, ay), (bx, by)):
        sheet.line(x - 4, y + 4, x + 4, y - 4, INK, 2)
    mx, my = (ax + bx) / 2, (ay + by) / 2
    width = text_width(text, 2)
    side = side or ('below' if abs(bx - ax) >= abs(by - ay) else 'right')
    at = {'below': (mx - width / 2, my + 6), 'above': (mx - width / 2, my - 20),
          'right': (mx + 8, my - 7), 'left': (mx - 8 - width, my - 7)}[side]
    sheet.text(round(at[0]), round(at[1]), text, 2, INK)


def _measurement_ends(record, toward, right):
    """The two world points a declared measurement is drawn between, or ``None``."""
    kind = record.get('kind')
    if kind in ('diameter', 'radius'):
        centre, radius, normal = record.get('center_mm'), record.get('radius_mm'), record.get('normal')
        if not (isinstance(centre, list) and isinstance(radius, (int, float)) and isinstance(normal, list)):
            return None
        # In the circle's plane and in the paper's: its projection is true length.
        d = (normal[1]*toward[2] - normal[2]*toward[1], normal[2]*toward[0] - normal[0]*toward[2],
             normal[0]*toward[1] - normal[1]*toward[0])
        d = _unit(d) if math.sqrt(sum(c * c for c in d)) > 1e-6 else tuple(right)
        far = [centre[i] + radius * d[i] for i in range(3)]
        near = list(centre) if kind == 'radius' else [centre[i] - radius * d[i] for i in range(3)]
        return near, far
    anchors = record.get('anchors_mm')
    if kind == 'angle' or not (isinstance(anchors, list) and len(anchors) == 2):
        return None
    return anchors[0], anchors[1]


def blueprint_sheet(triangles, summary, names, recipe, *, measurements=(), placed=False,
                    project='', version=1, date=''):
    """``(png bytes, facts)``: one dimensioned multi-view drawing sheet.

    ``names`` are the objects drawn (environment left out). Every view shares
    one scale, so a millimetre is the same length in each; orthographic views
    carry the overall extents, and each declared measurement (``measurements``,
    ``[(output, record)]`` from the display block) is drawn once, in the first
    orthographic view where it reads, when ``placed`` is false -- a placed
    design's measurement points are in its part's own frame, so they are
    listed, never drawn somewhere they are not. Callouts are numbered
    balloons on the first three-quarter view (else the first view), keyed in
    the parts list. The title block names the sheet, its version, the
    revision, the digest, the date and the scale.
    """
    recipe = blueprint_recipe(recipe)
    objects = summary['objects']
    names = [name for name in names if objects[name]['triangles']]
    _require(bool(names), 'nothing to draw once environment geometry is left out')
    if isinstance(recipe['callouts'], list):
        unknown = sorted(set(recipe['callouts']) - set(names))
        _require(not unknown, 'unknown callout ' + ', '.join(unknown) + '; drawable: ' + ', '.join(names))
    views = recipe['views']
    points = {name: [p for _, tri in triangles[objects[name]['first']:objects[name]['first'] +
                                              objects[name]['triangles']] for p in tri]
              for name in names}
    allpoints = [p for name in names for p in points[name]]

    def project_on(basis, p):
        right, up = basis[0], basis[1]
        return (p[0]*right[0] + p[1]*right[1] + p[2]*right[2], p[0]*up[0] + p[1]*up[1] + p[2]*up[2])

    spans = {}
    for view in views:
        uv = [project_on(LOOK_VIEWS[view], p) for p in allpoints]
        spans[view] = ([min(u for u, _ in uv), min(v for _, v in uv)],
                       [max(u for u, _ in uv), max(v for _, v in uv)])
    cols = 1 if len(views) == 1 else 2
    rows = 1 if len(views) <= 2 else 2
    area_w = WIDTH - 3 * _BP_MARGIN - _BP_COLUMN
    area_h = HEIGHT - 2 * _BP_MARGIN
    cell_w, cell_h = area_w // cols, area_h // rows
    side = min(cell_w, cell_h) - 2 * _BP_PAD
    extent = max(max(hi[0] - lo[0], hi[1] - lo[1]) for lo, hi in spans.values())
    _require(extent > 0, 'zero projected extent')
    scale = side / (extent * 1.04)  # px per mm, every view
    sheet = Canvas(WIDTH, HEIGHT, PAPER)
    sheet.rect(_BP_MARGIN // 2, _BP_MARGIN // 2, WIDTH - _BP_MARGIN, 2, RULE)
    sheet.rect(_BP_MARGIN // 2, HEIGHT - _BP_MARGIN // 2 - 2, WIDTH - _BP_MARGIN, 2, RULE)
    sheet.rect(_BP_MARGIN // 2, _BP_MARGIN // 2, 2, HEIGHT - _BP_MARGIN, RULE)
    sheet.rect(WIDTH - _BP_MARGIN // 2 - 2, _BP_MARGIN // 2, 2, HEIGHT - _BP_MARGIN, RULE)

    callout_view = next((v for v in views if v not in BLUEPRINT_ORTHO), views[0])
    if recipe['callouts'] is False:
        balloon = []
    elif isinstance(recipe['callouts'], list):
        balloon = list(recipe['callouts'])
    else:
        def bulk(name):
            lo, hi = objects[name]['bounds_mm']
            return -(hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2])
        balloon = sorted(names, key=bulk)[:BLUEPRINT_MAX_CALLOUTS] if len(names) > 1 else []
    drawable = [(output, record) for output, record in measurements if not placed]
    pending = list(range(len(drawable)))
    facts_views, dims, callouts, drawn_measurements = {}, [], [], set()
    for index, view in enumerate(views):
        basis = LOOK_VIEWS[view]
        cx0 = _BP_MARGIN + (index % cols) * cell_w
        cy0 = _BP_MARGIN + (index // cols) * cell_h
        sheet.rect(cx0, cy0, cell_w - 8, 1, RULE)
        sheet.text(cx0 + 6, cy0 + 8, view.replace('_', ' '), 2, MUTED)
        x0, y0 = cx0 + (cell_w - side) // 2, cy0 + (cell_h - side) // 2
        lo, hi = spans[view]
        cu, cv = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        half = side / scale / 2
        pixels, _ = line_view(triangles, summary, names, basis, size=side,
                              bounds=([cu - half, cv - half], [cu + half, cv + half]))
        sheet.paste(x0, y0, pixels, side, side)

        def to_px(p, basis=basis, x0=x0, y0=y0, cu=cu, cv=cv):
            u, v = project_on(basis, p)
            return (x0 + side / 2 + (u - cu) * scale, y0 + side / 2 - (v - cv) * scale)

        left, right = x0 + side / 2 + (lo[0] - cu) * scale, x0 + side / 2 + (hi[0] - cu) * scale
        top, bottom = y0 + side / 2 - (hi[1] - cv) * scale, y0 + side / 2 - (lo[1] - cv) * scale
        facts_views[view] = {'span_mm': [round(hi[0] - lo[0], 3), round(hi[1] - lo[1], 3)],
                             'cell': [cx0, cy0, cell_w, cell_h]}
        if recipe['dimensions'] and view in BLUEPRINT_ORTHO:
            width_mm, height_mm = hi[0] - lo[0], hi[1] - lo[1]
            _dimension(sheet, (left, bottom), (right, bottom), f'{width_mm:.1f}', (0, 22))
            _dimension(sheet, (right, top), (right, bottom), f'{height_mm:.1f}', (22, 0))
            axes = {'front': 'XZ', 'right': 'YZ', 'top': 'XY'}[view]
            dims += [{'view': view, 'source': 'overall', 'axis': axes[0], 'mm': round(width_mm, 3)},
                     {'view': view, 'source': 'overall', 'axis': axes[1], 'mm': round(height_mm, 3)}]
            above, beside = top, left  # declared dimensions stack above and left of the outline
            for k in list(pending):
                output, record = drawable[k]
                ends = _measurement_ends(record, basis[2], basis[0])
                if ends is None:
                    continue
                a, b = to_px(ends[0]), to_px(ends[1])
                if math.hypot(b[0] - a[0], b[1] - a[1]) < BLUEPRINT_MIN_DIMENSION_PX:
                    continue
                text = _paper_text(record.get('text') or '')
                dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
                if record.get('kind') in ('diameter', 'radius'):
                    # Across the circle where it is, the number above its far end.
                    _dimension(sheet, a, b, text, side='above')
                elif dy <= 0.05 * dx:  # horizontal on paper: lifted above the outline
                    above -= 30
                    _dimension(sheet, a, b, text, (0, above - min(a[1], b[1])), 'above')
                elif dx <= 0.05 * dy:  # vertical on paper: out to the left of it
                    beside -= 22
                    _dimension(sheet, a, b, text, (beside - min(a[0], b[0]), 0), 'left')
                else:
                    _dimension(sheet, a, b, text)
                pending.remove(k)
                drawn_measurements.add(k)
                dims.append({'view': view, 'source': 'declared', 'output': output,
                             'kind': record.get('kind'), 'text': record.get('text'),
                             'mm': record.get('value_mm')})
        if view == callout_view and balloon:
            anchors = []
            for name in balloon:
                lo3, hi3 = objects[name]['bounds_mm']
                anchors.append((name, to_px([(lo3[i] + hi3[i]) / 2 for i in range(3)])))
            sides = {'l': [], 'r': []}
            for number, (name, (ax, ay)) in enumerate(anchors, 1):
                sides['l' if ax < x0 + side / 2 else 'r'].append((ay, ax, number, name))
            for key, column in sides.items():
                bx = cx0 + 8 if key == 'l' else cx0 + cell_w - 8 - 8 - 26
                floor_y = cy0 + 30
                for ay, ax, number, name in sorted(column):
                    by = max(floor_y, min(round(ay) - 9, cy0 + cell_h - 26))
                    floor_y = by + 22
                    sheet.rect(bx, by, 26, 18, RULE)
                    sheet.rect(bx + 1, by + 1, 24, 16, PAPER)
                    label = str(number)
                    sheet.text(bx + 13 - text_width(label, 2) // 2, by + 2, label, 2, INK)
                    edge = bx + 26 if key == 'l' else bx
                    sheet.line(edge, by + 9, ax, ay, MUTED)
                    sheet.rect(round(ax) - 2, round(ay) - 2, 5, 5, INK)
                    callouts.append({'number': number, 'name': name, 'view': view})
    callouts.sort(key=lambda item: item['number'])

    # The right column: what the sheet is, notes, the parts list, the
    # measurements, and the title block at the foot.
    x, width = WIDTH - _BP_MARGIN - _BP_COLUMN, _BP_COLUMN
    sheet.rect(x - 12, _BP_MARGIN, 2, HEIGHT - 2 * _BP_MARGIN, RULE)
    sheet.text(x, _BP_MARGIN + 8, 'Cadex blueprint', 2, MUTED)
    title = _paper_text(recipe['name'])
    title_lines = _wrap(title, 4, width)[:2] if text_width(title, 4) > width else [title]
    y = _BP_MARGIN + 36
    for line in title_lines:
        sheet.text(x, y, line, fitted_scale(line, width, 4), INK)
        y += 36
    sheet.rect(x, y, width, 2, RULE)
    y += 14
    if recipe['notes']:
        sheet.text(x, y, 'notes', 2, MUTED)
        y += 22
        for line in _wrap(_paper_text(recipe['notes']), 2, width)[:8]:
            sheet.text(x, y, line, 2, INK)
            y += 18
        y += 8
    if callouts:
        sheet.text(x, y, 'parts', 2, MUTED)
        y += 22
        for item in callouts:
            number = str(item['number'])
            sheet.text(x + text_width('00', 2) - text_width(number, 2), y, number, 2, INK)
            sheet.text(x + 40, y, _paper_text(item['name'])[:28], 2, INK)
            y += 18
        y += 8
    listed = list(measurements)
    if listed:
        sheet.text(x, y, 'measurements' + ('' if not placed else '  (listed, part frame)'), 2, MUTED)
        y += 22
        for output, record in listed[:8]:
            text = _paper_text(record.get('text') or '')
            label = _paper_text(record.get('label') or output)[:30 - len(text) // 2]
            sheet.text(x, y, label, 2, INK)
            sheet.text(x + width - text_width(text, 2), y, text, 2, INK)
            y += 18
    block = [('sheet', f"{title[:22]} v{int(version)}"), ('project', _paper_text(project)[:28] or '-'),
             ('revision', summary['revision'][:12]), ('digest', str(summary.get('digest') or '')[:12] or '-'),
             ('date', _paper_text(date) or '-'), ('scale', f'{scale:.3f} px/mm all views'),
             ('units', 'mm'), ('views', 'third angle' if tuple(views) == BLUEPRINT_DEFAULT_VIEWS else
                                        'orthographic')]
    row_h = 26
    top = HEIGHT - _BP_MARGIN - row_h * len(block)
    sheet.rect(x, top - 2, width, 2, INK)
    for k, (label, value) in enumerate(block):
        ry = top + k * row_h
        sheet.text(x + 4, ry + 7, label, 2, MUTED)
        sheet.text(x + 120, ry + 7, value, fitted_scale(value, width - 124, 2), INK)
        sheet.rect(x, ry + row_h - 1, width, 1, RULE)
    facts = {'ok': True, 'name': recipe['name'], 'version': int(version), 'revision': summary['revision'],
             'views': views, 'scale_px_per_mm': round(scale, 4), 'view_spans': facts_views,
             'dimensions': dims, 'callouts': callouts,
             'measurements': {'declared': len(listed), 'drawn': len(drawn_measurements),
                              'listed_only': len(listed) - len(drawn_measurements),
                              'why_listed': ('the design places components, so measurement points are '
                                             'in a part frame' if placed and listed else
                                             'no orthographic view shows it legibly'
                                             if len(listed) > len(drawn_measurements) else '')},
             'size': [WIDTH, HEIGHT], 'approximation': BLUEPRINT_APPROXIMATION}
    return png(sheet.pixels, WIDTH, HEIGHT), facts


def blueprint_report(reply, fit, inventory, recipe, *, project='', version=1, date=''):
    """``(png bytes, facts)``: :func:`blueprint_sheet` from an accepted reply and its blocks."""
    triangles, summary = snapshot(reply, world(fit))
    environment, _ = classify(summary, fit, inventory)
    names = [name for name in summary['objects'] if name not in environment]
    display = reply.get('display') or {}
    measurements = sorted((str(name), entry['measurement']) for name, entry in display.items()
                          if isinstance(entry, dict) and isinstance(entry.get('measurement'), dict))
    placed = any(isinstance(entry, dict) and entry.get('source_output') for entry in display.values())
    return blueprint_sheet(triangles, summary, names, recipe, measurements=measurements, placed=placed,
                           project=project, version=version, date=date)


# --- The print-bed hero: the printable parts laid out flat (orun4 H2, ADR-569) --

#: The bed the printable parts are laid out on, X x Y x Z in millimetres: a
#: common 256 mm desktop printer. It is the picture's assumption, not a
#: slicer's: Cadex does not slice (charter B3), and a part taller than Z is
#: named rather than refused.
BED_MM = (256.0, 256.0, 256.0)
#: Clear space between two parts, and between a part and the bed's edge.
BED_GAP_MM = 6.0
#: The bed plate's thickness, colour and finish: a dark spring-steel sheet,
#: lighter than the mat it stands on so every bed reads as one.
BED_PLATE_MM = 3.0
BED_RGB = (74, 77, 82)
BED_FINISH = (0.10, 12.0)
#: Space between two beds in one picture, as a fraction of the bed's side.
BED_SPACING = 0.12
#: The picture: a square studio shot of the beds and a parts column beside it.
BED_IMAGE = (1536, 1024)
#: The shot looks down at the beds from a front three-quarter, steep enough that
#: no part hides another and low enough that heights still read.
BED_VIEW = camera(20.0, 50.0)
#: Triangles whose normals and planes agree to these tolerances are one flat face.
FLAT_NORMAL_BINS = 400
FLAT_PLANE_MM = 0.05
#: Flat faces tried as the seat, largest first.
FLAT_CANDIDATES = 64
BED_APPROXIMATION = ('each printed part seated on its largest flat face (the face it can rest '
                     'on with nothing below it) and turned to its smallest footprint, then '
                     'packed onto as many beds as it takes by MaxRects with a fixed gap; a '
                     'picture of a layout, not a slicer\'s '
                     'plate: no supports, brim or orientation for strength are considered')


def printed_parts(summary, fit=None, inventory=None):
    """The drawn objects a person prints, in summary order.

    A part is printed when the inventory calls its source uncatalogued and
    no catalog part was cut to make it (``derived_catalog_sources``: that is
    a purchased part, modified). World geometry the fit names is never a
    part. Without a readable inventory there is no telling, and it refuses.
    """
    _require(bool(inventory) and inventory.get('available', True) and 'uncatalogued_sources' in inventory,
             'no inventory to tell printed parts from purchased ones')
    derived = {str(row.get('source_output') or '') for row in inventory.get('derived_catalog_sources') or []
               if isinstance(row, dict)}
    printed = {str(s) for s in inventory.get('uncatalogued_sources') or []} - derived
    environment = world(fit)
    return [name for name, item in summary['objects'].items()
            if item['source'] in printed and name not in environment and item['triangles']]


def purchased_rows(inventory):
    """``[(count, text)]``: the purchased hardware, from the inventory's catalog roll-up."""
    rows = []
    for key, count in sorted(dict(inventory.get('catalog_counts') or {}).items()):
        family, _, part = str(key).partition('/')
        rows.append((int(count), f'{family} {part}' if part else family))
    for row in inventory.get('derived_catalog_sources') or []:
        if isinstance(row, dict):
            rows.append((1, '{:s} {:s}, cut'.format(str(row.get('family') or ''),
                                                    str(row.get('part_number') or ''))))
    return rows


def _rotate(points, matrix):
    (a, b, c), (d, e, f), (g, h, i) = matrix
    return [(a*x + b*y + c*z, d*x + e*y + f*z, g*x + h*y + i*z) for x, y, z in points]


def _onto_down(s):
    """The rotation taking unit vector ``s`` onto -Z (Rodrigues)."""
    t = (0.0, 0.0, -1.0)
    v = (s[1]*t[2] - s[2]*t[1], s[2]*t[0] - s[0]*t[2], s[0]*t[1] - s[1]*t[0])
    c = s[0]*t[0] + s[1]*t[1] + s[2]*t[2]
    if c < -1 + 1e-9:  # s is +Z: turn it over about X
        return ((1, 0, 0), (0, -1, 0), (0, 0, -1))
    k = 1.0 / (1.0 + c)
    vx = ((0, -v[2], v[1]), (v[2], 0, -v[0]), (-v[1], v[0], 0))
    sq = [[sum(vx[r][m] * vx[m][q] for m in range(3)) for q in range(3)] for r in range(3)]
    return tuple(tuple((r == q) + vx[r][q] + k * sq[r][q] for q in range(3)) for r in range(3))


def _hull(points):
    """The 2D convex hull of ``points``, counter-clockwise (monotone chain)."""
    pts = sorted(set(points))
    if len(pts) < 3:
        return pts

    def turn(o, a, b):
        return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and turn(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and turn(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def lay_flat(tris):
    """``(tris, facts)``: one part as it would print, its footprint from the origin.

    The seat is the largest flat face the part can rest on -- every vertex
    on or above its plane -- turned to face the bed; with none (a part all
    curves) the part keeps its assembled attitude. It is then turned about
    the vertical to its smallest footprint rectangle (an edge of the
    footprint's convex hull lies along it), long side along X, and moved so
    its footprint starts at the origin on the bed.
    """
    faces = {}
    for a, b, c in tris:
        ux, uy, uz, vx, vy, vz = b[0]-a[0], b[1]-a[1], b[2]-a[2], c[0]-a[0], c[1]-a[1], c[2]-a[2]
        n = (uy*vz - uz*vy, uz*vx - ux*vz, ux*vy - uy*vx)
        length = math.sqrt(n[0]*n[0] + n[1]*n[1] + n[2]*n[2])
        if length == 0:
            continue
        n = (n[0]/length, n[1]/length, n[2]/length)
        d = n[0]*a[0] + n[1]*a[1] + n[2]*a[2]
        key = (round(n[0]*FLAT_NORMAL_BINS), round(n[1]*FLAT_NORMAL_BINS), round(n[2]*FLAT_NORMAL_BINS),
               round(d / FLAT_PLANE_MM / 4))
        face = faces.setdefault(key, [0.0, n, d])
        face[0] += length / 2
    points = list({p for tri in tris for p in tri})
    seat, area = None, 0.0
    for size, n, d in sorted(faces.values(), key=lambda f: -f[0])[:FLAT_CANDIDATES]:
        # An outward face has every vertex on its inner side; winding is not
        # trusted, so a face with every vertex on its outer side seats too.
        far = max(n[0]*p[0] + n[1]*p[1] + n[2]*p[2] for p in points)
        near = min(n[0]*p[0] + n[1]*p[1] + n[2]*p[2] for p in points)
        if far <= d + FLAT_PLANE_MM:
            seat, area = n, size
        elif near >= d - FLAT_PLANE_MM:
            seat, area = (-n[0], -n[1], -n[2]), size
        if seat is not None:
            break
    turn = _onto_down(seat) if seat is not None else ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    points = _rotate(points, turn)
    hull = _hull([(p[0], p[1]) for p in points])
    best = (math.inf, 0.0)
    for i in range(len(hull)):
        (x0, y0), (x1, y1) = hull[i], hull[(i + 1) % len(hull)]
        theta = -math.atan2(y1 - y0, x1 - x0)
        cs, sn = math.cos(theta), math.sin(theta)
        xs = [cs*x - sn*y for x, y in hull]
        ys = [sn*x + cs*y for x, y in hull]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if w * h < best[0] - 1e-9:
            best = (w * h, theta if w >= h else theta + math.pi / 2)
    theta = best[1]
    cs, sn = math.cos(theta), math.sin(theta)
    matrix = tuple(tuple(sum(((cs, -sn, 0), (sn, cs, 0), (0, 0, 1))[r][m] * turn[m][q] for m in range(3))
                         for q in range(3)) for r in range(3))
    placed = _rotate(points, ((cs, -sn, 0), (sn, cs, 0), (0, 0, 1)))
    lo = [min(p[j] for p in placed) for j in range(3)]
    hi = [max(p[j] for p in placed) for j in range(3)]
    out = []
    for tri in tris:
        out.append(tuple((x - lo[0], y - lo[1], z - lo[2]) for x, y, z in _rotate(tri, matrix)))
    return out, {'footprint_mm': [hi[0] - lo[0], hi[1] - lo[1]], 'height_mm': hi[2] - lo[2],
                 'seat': 'largest flat face' if seat is not None else 'as assembled (no flat face)',
                 'seat_area_mm2': round(area, 1)}


def _maxrects_place(free, w, d):
    """The best free spot for ``w`` x ``d`` (either way round): ``(x, y, turned)`` or ``None``.

    Best short side fit: the spot whose leftover is smallest on its
    tighter side, then on its other side, then nearest the origin.
    """
    best, spot = None, None
    for x, y, fw, fd in free:
        for turned, (pw, pd) in ((False, (w, d)), (True, (d, w))):
            if pw <= fw + 1e-9 and pd <= fd + 1e-9:
                score = (min(fw - pw, fd - pd), max(fw - pw, fd - pd), y, x)
                if best is None or score < best:
                    best, spot = score, (x, y, turned)
    return spot


def _maxrects_split(free, x, y, w, d):
    """The free rectangles left once ``(x, y, w, d)`` is taken, none inside another."""
    out = []
    for fx, fy, fw, fd in free:
        if x >= fx + fw - 1e-9 or x + w <= fx + 1e-9 or y >= fy + fd - 1e-9 or y + d <= fy + 1e-9:
            out.append((fx, fy, fw, fd))
            continue
        if x > fx + 1e-9:
            out.append((fx, fy, x - fx, fd))
        if x + w < fx + fw - 1e-9:
            out.append((x + w, fy, fx + fw - x - w, fd))
        if y > fy + 1e-9:
            out.append((fx, fy, fw, y - fy))
        if y + d < fy + fd - 1e-9:
            out.append((fx, y + d, fw, fy + fd - y - d))

    def inside(a, b):
        return (a[0] >= b[0] - 1e-9 and a[1] >= b[1] - 1e-9 and a[0] + a[2] <= b[0] + b[2] + 1e-9
                and a[1] + a[3] <= b[1] + b[3] + 1e-9)
    return [r for i, r in enumerate(out)
            if not any(j != i and inside(r, o) and (not inside(o, r) or j < i) for j, o in enumerate(out))]


def pack_beds(footprints, bed=BED_MM, gap=BED_GAP_MM):
    """``[(bed, x, y, turned)]`` per footprint: the parts on as few beds as it takes.

    MaxRects, largest part first, each part grown by ``gap`` on its far
    sides inside a bed shrunk by ``gap`` on its near ones: so two parts are
    at least ``gap`` apart and every part ``gap`` inside the edge. A part
    may be turned a quarter. A part too big for any bed gets a bed of its
    own at the gap. Positions are the footprint's corner nearest the bed's
    origin, in that bed's millimetres; a turned part's footprint is its
    ``(depth, width)``.
    """
    area = (bed[0] - gap, bed[1] - gap)
    order = sorted(range(len(footprints)), key=lambda i: (-footprints[i][0] * footprints[i][1], i))
    beds, result = [], [None] * len(footprints)
    for i in order:
        w, d = footprints[i][0] + gap, footprints[i][1] + gap
        for index, free in enumerate(beds):
            spot = free is not None and _maxrects_place(free, w, d)
            if spot:
                break
        else:
            fresh = [(gap, gap, area[0], area[1])]
            spot = _maxrects_place(fresh, w, d)
            if not spot:
                beds.append(None)
                result[i] = (len(beds) - 1, gap, gap, False)
                continue
            beds.append(fresh)
            index = len(beds) - 1
        x, y, turned = spot
        pw, pd = (d, w) if turned else (w, d)
        beds[index] = _maxrects_split(beds[index], x, y, pw, pd)
        result[i] = (index, x, y, turned)
    return result


def _plate(x0, y0, w, d, t):
    """A box ``w`` x ``d`` x ``t`` whose top is at z = 0, as outward triangles."""
    x1, y1, z0 = x0 + w, y0 + d, -t
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)]
    quads = ((4, 5, 6, 7), (3, 2, 1, 0), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    return [tri for a, b, e, f in quads for tri in ((c[a], c[b], c[e]), (c[a], c[e], c[f]))]


def print_bed(triangles, summary, fit, inventory, *, name='', bed=BED_MM, gap=BED_GAP_MM, size=HERO_SIZE):
    """``(png bytes, facts)``: the print-bed hero of one snapshot.

    Every printed part (:func:`printed_parts`) is laid flat
    (:func:`lay_flat`), packed onto as many beds as it takes
    (:func:`pack_beds`), drawn in its own look on the dark mat with its
    number over it, and listed beside the beds with the purchased hardware
    the inventory names. ``facts`` is JSON-ready: per part its number,
    bed, position, footprint and seat, and the hardware rows.
    """
    environment, purchased = classify(summary, fit, inventory)
    appearance, palette = declared(inventory)
    looks = materials(summary, purchased=purchased, appearance=appearance, palette=palette)
    names = printed_parts(summary, fit, inventory)
    _require(bool(names), 'the inventory names no printed part to lay on a bed')
    parts = []
    for name_ in names:
        item = summary['objects'][name_]
        tris = [points for _, points in triangles[item['first']:item['first'] + item['triangles']]]
        flat, facts = lay_flat(tris)
        parts.append({'name': name_, 'source': item['source'], 'tris': flat, **facts})
    placements = pack_beds([p['footprint_mm'] for p in parts], bed, gap)
    count = 1 + max(at[0] for at in placements)
    columns = math.ceil(math.sqrt(count))
    pitch = (bed[0] * (1 + BED_SPACING), bed[1] * (1 + BED_SPACING))

    def origin(index):
        return (index % columns) * pitch[0], -(index // columns) * pitch[1]
    drawn, rows = [], []
    for number, (part, (index, x, y, turned)) in enumerate(zip(parts, placements), 1):
        ox, oy = origin(index)
        w, d = part['footprint_mm']
        if turned:
            tris = [tuple((d - py + x + ox, px + y + oy, pz) for px, py, pz in tri) for tri in part['tris']]
            w, d = d, w
        else:
            tris = [tuple((px + x + ox, py + y + oy, pz) for px, py, pz in tri) for tri in part['tris']]
        role, rgb = looks[part['name']]
        drawn.append(((rgb, FINISH[role]), tris))
        rows.append({'number': number, 'component': part['name'], 'source': part['source'], 'bed': index + 1,
                     'position_mm': [round(x, 2), round(y, 2)], 'footprint_mm': [round(w, 2), round(d, 2)],
                     'height_mm': round(part['height_mm'], 2), 'turned': turned, 'seat': part['seat'],
                     'seat_area_mm2': part['seat_area_mm2'],
                     'fits_bed': (w <= bed[0] - 2 * gap + 1e-9 and d <= bed[1] - 2 * gap + 1e-9
                                  and part['height_mm'] <= bed[2] + 1e-9)})
    plates = [((BED_RGB, BED_FINISH), _plate(*origin(i), bed[0], bed[1], BED_PLATE_MM)) for i in range(count)]
    prepared = _prepare(plates + drawn)
    basis = BED_VIEW
    bounds = _frame(prepared, basis, 0.04)
    pixels, details = studio(prepared, basis, bounds=bounds, size=size, shadow=_contact_shadow(prepared))
    hardware = purchased_rows(inventory)
    image = _compose_bed(pixels, size, basis, bounds, rows, hardware, count, bed, name, summary['revision'],
                         [origin(i) for i in range(count)])
    facts = {'revision': summary['revision'], 'bed_mm': list(bed), 'gap_mm': gap, 'beds': count,
             'parts': rows, 'hardware': [{'count': c, 'part': text} for c, text in hardware],
             'not_fitting': [r['component'] for r in rows if not r['fits_bed']],
             'view': {'basis': basis, 'projection_bounds_mm': details['projection_bounds_mm']},
             'approximation': BED_APPROXIMATION}
    return image, facts


def _compose_bed(pixels, size, basis, bounds, rows, hardware, count, bed, name, revision, origins):
    """The print-bed picture: the beds, each part's number over it, and the parts column."""
    width, height = BED_IMAGE
    _require(size == height, 'the print-bed picture is laid out for a 1024 px shot')
    sheet = Canvas(width, height, PAPER)
    sheet.paste(0, 0, pixels, size, size)
    right, up, _ = basis
    (lo, hi) = bounds
    extent = max(hi[0] - lo[0], hi[1] - lo[1])
    cx0, cy0 = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2

    def screen(p):
        return (size / 2 + (sum(p[j] * right[j] for j in range(3)) - cx0) * size / extent,
                size / 2 - (sum(p[j] * up[j] for j in range(3)) - cy0) * size / extent)
    badges = []
    for row in rows:
        ox, oy = origins[row['bed'] - 1]
        x, y = row['position_mm']
        w, d = row['footprint_mm']
        # On the footprint's centre, half way up: footprints never overlap,
        # and a badge that still lands on an earlier one steps down clear of it.
        sx, sy = screen((ox + x + w / 2, oy + y + d / 2, row['height_mm'] / 2))
        label = str(row['number'])
        tw = text_width(label, 2)
        bx, by = round(sx - tw / 2) - 6, round(sy) - 10
        while any(bx < ax + aw + 2 and ax < bx + tw + 14 and by < ay + 24 and ay < by + 24 for ax, ay, aw in badges):
            by += 6
        badges.append((bx, by, tw + 12))
        sheet.rect(bx, by, tw + 12, 22, PALETTE['bg'])
        sheet.text(bx + 6, by + 4, label, 2, INK)
    if count > 1:
        for index, (ox, oy) in enumerate(origins):
            sx, sy = screen((ox, oy, 0.0))
            sheet.text(round(sx), round(sy) + 8, f'bed {index + 1}', 2, MUTED)
    x0, column = size + 40, width - size - 80
    title = name or 'print beds'
    sheet.text(x0, 40, title, fitted_scale(title, column, 5), INK)
    sheet.text(x0, 96, 'Cadex print beds', 2, MUTED)
    sheet.text(x0, 120, 'rev ' + revision[:12], 2, MUTED)
    sheet.rect(x0, 152, column, 2, RULE)
    beds = '{:d} bed{:s}, {:.0f} x {:.0f} mm'.format(count, '' if count == 1 else 's', bed[0], bed[1])
    sheet.text(x0, 170, beds, fitted_scale(beds, column, 3), INK)
    sheet.text(x0, 200, 'each part on its largest flat face', 2, MUTED)
    y = 236
    sheet.text(x0, y, 'printed', 2, MUTED)
    y += 26
    room = (height - 40 - y) // 22 - 3 - min(len(hardware), 8)
    shown = rows if len(rows) <= room else rows[:max(1, room - 1)]
    for row in shown:
        sheet.text(x0, y, str(row['number']), 2, INK)
        size_text = '{:.0f} x {:.0f} x {:.0f}'.format(*row['footprint_mm'], row['height_mm'])
        flag = '' if row['fits_bed'] else '  too big'
        label = row['source'] + flag
        sheet.text(x0 + 36, y, label, fitted_scale(label, column - 36 - text_width(size_text, 2) - 16, 2), INK)
        sheet.text(x0 + column - text_width(size_text, 2), y, size_text, 2, MUTED)
        y += 22
    if len(shown) < len(rows):
        sheet.text(x0 + 36, y, f'+ {len(rows) - len(shown)} more', 2, MUTED)
        y += 22
    y += 10
    sheet.rect(x0, y, column, 2, RULE)
    y += 18
    sheet.text(x0, y, 'purchased', 2, MUTED)
    y += 26
    if not hardware:
        sheet.text(x0, y, 'none in the inventory', 2, MUTED)
    room = (height - 30 - y) // 22
    listed = hardware if len(hardware) <= room else hardware[:max(1, room - 1)]
    for amount, text in listed:
        sheet.text(x0, y, f'{amount} x', 2, MUTED)
        sheet.text(x0 + 52, y, text, fitted_scale(text, column - 52, 2), INK)
        y += 22
    if len(listed) < len(hardware):
        sheet.text(x0 + 52, y, f'+ {len(hardware) - len(listed)} more', 2, MUTED)
    return png(sheet.pixels, width, height)


# --- The two whole jobs: a review render and an agent's look -----------------

#: What a look is, in one line, for the model reading it.
LOOK_APPROXIMATION = ('orthographic studio render of the tessellation at the solved pose: lit, '
                      'antialiased, contact shadow; no edges, dimensions or transparency')
#: The views a look draws when it names none, and the most it may name.
LOOK_DEFAULT_VIEWS = ('iso', 'iso_back')
LOOK_MAX_VIEWS = 5


def look_report(reply, fit, inventory, views=LOOK_DEFAULT_VIEWS, focus=()):
    """``(facts, shots)``: what an agent's ``look`` returns (ADR-406).

    ``reply`` is an accepted modelling or ``rebuild`` reply carrying its
    display block; ``fit`` and ``inventory`` are the blocks published for it,
    either ``None`` when unreadable. World geometry the fit names is left
    out; each part is drawn in its declared appearance role, in the
    assembly's palette (ADR-413), and an undeclared part by supplier. Focus
    names may be outputs as well as the components that place them.
    ``facts`` is JSON-ready; ``shots`` is ``[(view, png_bytes, details)]``.
    """
    views, focus = [str(v) for v in views], [str(v) for v in focus]
    _require(0 < len(views) <= LOOK_MAX_VIEWS,
             f'look takes 1 to {LOOK_MAX_VIEWS} views of ' + ', '.join(LOOK_VIEWS))
    triangles, summary = snapshot(reply, world(fit))
    environment, purchased = classify(summary, fit, inventory)
    appearance, palette = declared(inventory)
    by_source = {item['source']: name for name, item in summary['objects'].items()}
    focus_objects = [by_source.get(name, name) for name in focus]
    shots = look(triangles, summary, views, focus=focus_objects, exclude=environment,
                 purchased=purchased, appearance=appearance, palette=palette)
    proxies = design_proxies(triangles, summary, exclude=environment, purchased=purchased,
                             appearance=appearance, palette=palette)
    proxies['sharp_outside_edge_share'] = edge_proxy(inventory, environment)
    facts = {
        'ok': True,
        'revision': summary['revision'],
        'views': [view for view, _, _ in shots],
        'focus': focus,
        'left_out_as_environment': sorted(environment),
        'colours': (
            'by appearance role: ' + ', '.join(
                '{:s} #{:02X}{:02X}{:02X}'.format(role, *rgb)
                for role, rgb in {**ROLE_COLORS, **palette}.items())
            + f'; {len(appearance)} component(s) declare a role, the rest are drawn '
              'shell if printed and mechanism if purchased'
            if purchased is not None else
            'index palette (no inventory to tell printed from purchased)'
        ),
        'components_drawn': len(summary['objects']) - len(environment & set(summary['objects'])),
        # The design-language measures (docs/DESIGN-LANGUAGE.md): how much of
        # the hero silhouette is bought hardware, how much printed outside
        # edge is left sharp, and how many materials it shows, each against
        # its bar.
        'measures': {
            key: {k: proxies[key][k] for k in ('value', 'bar', 'meets')}
            for key in ('hardware_silhouette_share', 'sharp_outside_edge_share', 'material_count')
        },
        'triangles': summary['triangles'],
        'approximation': LOOK_APPROXIMATION,
    }
    return facts, shots


def _appearance_rows(names, looks, appearance, purchased):
    """Per drawn object: its role, colour and where the role came from."""
    return {name: {'role': looks[name][0], 'color': '#%02X%02X%02X' % looks[name][1],
                   'source': ('declared' if name in appearance else
                              'supplier' if purchased is not None else 'index')}
            for name in names}


def _palette_hex(palette):
    return {role: '#%02X%02X%02X' % tuple(rgb) for role, rgb in {**ROLE_COLORS, **palette}.items()}


def _scene(triangles, source, fit, inventory):
    """The drawn scene of a snapshot, as every studio image of it sees it.

    ``(summary, names, environment, purchased, appearance, palette,
    prepared, shadow)``: ``summary`` is ``source`` with its environment,
    appearance rows and palette added; ``names`` the objects drawn.
    """
    summary = dict(source)
    environment, purchased = classify(summary, fit, inventory)
    appearance, palette = declared(inventory)
    looks = materials(summary, purchased=purchased, appearance=appearance, palette=palette)
    names = [name for name in summary['objects'] if name not in environment]
    _require(any(summary['objects'][n]['triangles'] for n in names),
             'nothing to draw once environment geometry is left out')
    summary['environment'] = sorted(environment)
    summary['appearance'] = _appearance_rows(names, looks, appearance, purchased)
    summary['palette'] = _palette_hex(palette)
    prepared = _prepare(_studio_parts(triangles, summary, names, looks))
    # The world geometry is never drawn; the mat is laid at its top (ADR-604).
    shadow = _contact_shadow(prepared, floor=world_top(triangles, summary, environment))
    return summary, names, environment, purchased, appearance, palette, prepared, shadow


def _hero(prepared, shadow):
    return studio(prepared, HERO, bounds=_frame(prepared, HERO, 0.10), size=HERO_SIZE, shadow=shadow)


def hero(triangles, source, fit, inventory):
    """``(png bytes, facts)``: the studio hero of one snapshot alone.

    The same picture :func:`render_files` draws as ``hero.png``, without the
    review views and the sheet around it: what a passed evaluation presents.
    """
    summary, _names, _env, _purchased, _appearance, _palette, prepared, shadow = _scene(
        triangles, source, fit, inventory)
    pixels, details = _hero(prepared, shadow)
    return png(pixels, HERO_SIZE), {'revision': summary['revision'], 'basis': HERO, 'size': HERO_SIZE,
                                    'environment': summary['environment'],
                                    'projection_bounds_mm': details['projection_bounds_mm']}


def render_files(triangles, source, root, fit, inventory, relative_dir):
    """``(files, summary)``: the review render of one snapshot, not yet written.

    Four studio SVG views, the 1024 px hero, the concept sheet and
    ``summary.json``, keyed by file name; paths inside the summary are under
    ``relative_dir``. ``root`` is the project root, read only for the sheet's
    mass. Nothing is written, so a refusal leaves no partial views.
    """
    start = time.perf_counter()
    summary, names, environment, purchased, appearance, palette, prepared, shadow = _scene(
        triangles, source, fit, inventory)
    files, summary['views'] = {}, {}
    paper, caption = hex_colour(PALETTE['bg']), hex_colour(PALETTE['ink_2'])
    for name, basis in BASES.items():
        pixels, details = studio(prepared, basis, bounds=_frame(prepared, basis, 0.08), size=SIZE, shadow=shadow)
        encoded = base64.b64encode(png(pixels)).decode('ascii')
        title = html.escape(f"{name} | accepted {summary['revision']} | tessellation preview")
        files[name + '.svg'] = (f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="552" viewBox="0 0 512 552">'
                               f'<title>{title}</title><rect width="512" height="552" fill="{paper}"/>'
                               f'<image width="512" height="512" href="data:image/png;base64,{encoded}"/>'
                               f'<text x="16" y="536" font-family="sans-serif" font-size="12" fill="{caption}">'
                               f'{name} | {summary["revision"][:12]} | tessellation preview</text></svg>\n')
        summary['views'][name] = {**details, 'basis': basis, 'path': f'{relative_dir}/{name}.svg'}
    # The studio hero (DESIGN-LANGUAGE.md section 7): one PNG, the design's
    # presented image rather than a review view.
    hero_start = time.perf_counter()
    pixels, details = _hero(prepared, shadow)
    files['hero.png'] = png(pixels, HERO_SIZE)
    summary['hero'] = {**details, 'basis': HERO, 'size': HERO_SIZE, 'path': f'{relative_dir}/hero.png',
                       'seconds': time.perf_counter() - hero_start}
    summary['render_seconds'] = time.perf_counter() - start
    summary['proxies'] = design_proxies(triangles, summary, exclude=environment, purchased=purchased,
                                        appearance=appearance, palette=palette)
    summary['proxies']['sharp_outside_edge_share'] = edge_proxy(inventory, environment)
    # The concept sheet (ot10 A6, ADR-430): the hero just drawn, the key
    # numbers, the palette and three line views, as one PNG.
    sheet_start = time.perf_counter()
    lines = {view: line_view(triangles, summary, names, BASES[view])[0] for view in LINE_VIEWS}
    numbers = key_numbers(root, summary, names, inventory, environment)
    roles = {entry['role'] for entry in summary['appearance'].values()}
    files['sheet.png'] = compose(pixels, HERO_SIZE, lines, numbers, summary['palette'], roles,
                                 summary['proxies'], summary['revision'])
    summary['sheet'] = {'path': f'{relative_dir}/sheet.png', 'size': [WIDTH, HEIGHT],
                        'revision': summary['revision'], 'digest': summary.get('digest'),
                        'line_views': list(LINE_VIEWS), 'numbers': numbers,
                        'seconds': time.perf_counter() - sheet_start}
    files['summary.json'] = json.dumps(summary, indent=2) + '\n'
    return files, summary


def write_files(directory, files):
    """Write ``render_files``' output into ``directory``; returns the paths written."""
    directory = Path(directory)
    written = []
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            path = directory / name
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding='utf-8')
            written.append(path)
    except OSError as exc:
        raise StudioError('render: cannot write views: ' + str(exc)) from exc
    return written
