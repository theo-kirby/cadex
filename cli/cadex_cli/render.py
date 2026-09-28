# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bounded orthographic review of accepted triangles, with per-pixel depth.

Independently authored LGPL client code. No graphics runtime or new dependency.
SVG wraps a lossless CPU image; it is a tessellation preview, not a CAD drawing.
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

from . import sheet
from .inventory import InventoryError

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
BACKDROP_TOP = (208, 211, 216)
BACKDROP_BOTTOM = (243, 243, 241)
PALETTE = [(91, 157, 205), (230, 151, 76), (115, 182, 135), (180, 134, 200)]
LIMITS = {'buffer_bytes': MAX_BYTES, 'triangles': MAX_TRIANGLES, 'input_triangles': MAX_INPUT_TRIANGLES,
          'vertices_per_source': MAX_VERTICES,
          'placed_vertices': MAX_PLACED_VERTICES,
          'pixel_visits_per_view': MAX_SAMPLES, 'image_size': SIZE, 'hero_size': HERO_SIZE}
APPROXIMATION = ('Opaque standard tessellation, initial solved pose, orthographic; studio-lit '
                 '(key, fill, rim; normals smoothed below a crease angle), 2x2 supersampled, on a '
                 'seamless backdrop with a contact shadow measured from the geometry; no '
                 'transparency, edges or dimensions. Environment geometry the fit names is left '
                 'out. Shell-only visibility is not carried by the protocol. Placed source copies '
                 'are excluded. Above the drawn triangle budget, vertices are clustered on a '
                 'grid (summary: decimation).')


def _require(condition, message):
    if not condition:
        raise InventoryError('render: ' + message)


def snapshot(reply):
    """Copy and validate all geometry before any subsequent engine request."""
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
        raise InventoryError('render: malformed or unreadable display: ' + str(exc)) from exc
    _require(bool(parts), 'no published triangle geometry')
    decimation = None
    if raw_triangles > MAX_TRIANGLES:
        extent = max(max(p[j] for *_, points, _ in parts for p in points)
                     - min(p[j] for *_, points, _ in parts for p in points) for j in range(3))
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
        decimation = {'input_triangles': raw_triangles, 'cell_mm': cell,
                      'cell_fraction_of_extent': cell / extent}
    for name, source, matrix, points, indices in parts:
        color = PALETTE[len(objects) % len(PALETTE)]
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


def _contact_shadow(prepared):
    """A soft shadow on the floor under the design, as a function of (x, y).

    Measured, not painted: a top-down map of how high the lowest surface
    over each cell sits above the floor, turned into a tight dark contact
    term (what touches the floor) and a wide soft term (what hovers over
    it), each blurred. Returns ``(floor_z, lookup)``.
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
    floor, tall = lo[2], max(hi[2] - lo[2], 1e-9)
    near = [math.exp(-(z - floor) / (0.05 * tall)) if z < math.inf else 0.0 for z in lowest]
    wide = [math.exp(-(z - floor) / tall) if z < math.inf else 0.0 for z in lowest]
    near = _blur(near, width, height, max(1, round(0.012 * extent / cell)))
    wide = _blur(wide, width, height, max(1, round(0.07 * extent / cell)))

    def lookup(x, y):
        i, j = int((x - x0) / cell), int((y - y0) / cell)
        if not (0 <= i < width and 0 <= j < height):
            return 1.0
        k = j * width + i
        return max(0.45, 1.0 - 0.45 * near[k] - 0.35 * wide[k])
    return floor, lookup


def studio(prepared, basis, *, bounds, size, samples=SUPERSAMPLE, shadow=None):
    """A lit, antialiased image of prepared triangles on a seamless backdrop.

    Orthographic along ``basis``; ``bounds`` is the framed projection window.
    Every pixel is ``samples`` squared subsamples: a depth pass keeps the
    nearest triangle per subsample, then only visible subsamples are shaded
    (key, fill and rim light, Blinn specular per role finish, normals
    interpolated across the triangle), and the rest take the backdrop, with
    ``shadow`` (from :func:`_contact_shadow`) darkening the floor under the
    design when the camera is above it.
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
    image, covered = bytearray(3 * size * size), 0
    inv = 1.0 / (samples * samples)
    for oy in range(size):
        f = (oy + .5) / size
        back = [BACKDROP_TOP[c] + (BACKDROP_BOTTOM[c] - BACKDROP_TOP[c]) * f for c in range(3)]
        sy = cy0 - (oy + .5 - size / 2) * extent / size
        for ox in range(size):
            bg = back
            if lookup is not None:
                sx = cx0 + (ox + .5 - size / 2) * extent / size
                along = (floor_z - sx*rz - sy*uz) / tz
                dark = lookup(sx*rx + sy*ux + along*tx, sx*ry + sy*uy + along*ty)
                if dark < 1.0:
                    bg = [c * dark for c in back]
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
                   'contact_shadow': lookup is not None}


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


def look(triangles, summary, views, *, focus=(), exclude=(), purchased=None, appearance=None,
         palette=None, size=LOOK_SIZE):
    """The agent's own views of a snapshot: PNG bytes per requested view.

    ``exclude`` names objects left out entirely (environment geometry: a floor
    would otherwise set the framing and shrink the design to a speck);
    ``focus`` names the objects the view is framed on, with everything else
    still drawn; ``purchased``, ``appearance`` and ``palette`` choose each
    object's material (see :func:`materials`). Every view is a studio image
    (:func:`studio`); ``hero`` is the presentation view.
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
    shadow = _contact_shadow(prepared)
    shots = []
    for view in views:
        basis = LOOK_VIEWS[view]
        bounds = _frame(framed, basis, 0.10 if view == 'hero' else 0.04)
        pixels, details = studio(prepared, basis, bounds=bounds, size=size, shadow=shadow)
        details['materials'] = sorted({'#%02X%02X%02X' % looks[name][1] for name in names})
        shots.append((view, png(pixels, size), details))
    return shots


def classify(summary, fit=None, inventory=None):
    """``(environment, purchased)`` for a snapshot, from the fit and inventory blocks.

    Environment is the world geometry the fit names (a floor); purchased is
    every object whose source no inventory row calls uncatalogued, or
    ``None`` when there is no inventory to say.
    """
    environment = {str(row.get('first') or '') for row in (fit or {}).get('failing') or []
                   if row.get('status') == 'world geometry'} & set(summary['objects'])
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
            raise InventoryError(f'render: invalid palette colour {text!r} for {role}') from exc
    return appearance, palette


def _published_blocks(client):
    """The fit and inventory blocks for the accepted revision; ``None`` for either unreadable."""
    from .clearance import read_fit
    from .inventory import read_inventory_summary
    blocks = []
    for read in (read_fit, read_inventory_summary):
        try:
            blocks.append(read(client))
        except Exception:  # a render with no inventory still draws, in index colours
            blocks.append(None)
    return blocks


def acquire_snapshot(client):
    start = time.perf_counter()
    reply = client.request('rebuild', {'display': {'quality': 'standard', 'edges': False}})
    triangles, summary = snapshot(reply)
    summary['acquisition_seconds'] = time.perf_counter() - start
    return triangles, summary


def write_render(client, root, *, expected_revision=None, accepted_snapshot=None):
    triangles, source = accepted_snapshot if accepted_snapshot is not None else acquire_snapshot(client)
    summary = dict(source)
    if expected_revision is not None:
        _require(summary['revision'] == expected_revision, 'accepted revision differs from rollout')
    relative_dir = 'review/render' + (f'/{expected_revision}' if expected_revision else '')
    fit, inventory = _published_blocks(client)
    environment, purchased = classify(summary, fit, inventory)
    appearance, palette = declared(inventory)
    looks = materials(summary, purchased=purchased, appearance=appearance, palette=palette)
    names = [name for name in summary['objects'] if name not in environment]
    _require(any(summary['objects'][n]['triangles'] for n in names),
             'nothing to draw once environment geometry is left out')
    summary['environment'] = sorted(environment)
    summary['appearance'] = {name: {'role': looks[name][0], 'color': '#%02X%02X%02X' % looks[name][1],
                                    'source': ('declared' if name in appearance else
                                               'supplier' if purchased is not None else 'index')}
                             for name in names}
    summary['palette'] = {role: '#%02X%02X%02X' % tuple(rgb)
                          for role, rgb in {**ROLE_COLORS, **palette}.items()}
    start = time.perf_counter()
    prepared = _prepare(_studio_parts(triangles, summary, names, looks))
    shadow = _contact_shadow(prepared)
    files, summary['views'] = {}, {}
    for name, basis in BASES.items():
        pixels, details = studio(prepared, basis, bounds=_frame(prepared, basis, 0.08), size=SIZE, shadow=shadow)
        encoded = base64.b64encode(png(pixels)).decode('ascii')
        title = html.escape(f"{name} | accepted {summary['revision']} | tessellation preview")
        files[name + '.svg'] = (f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="552" viewBox="0 0 512 552">'
                               f'<title>{title}</title><rect width="512" height="552" fill="#f6f7fa"/>'
                               f'<image width="512" height="512" href="data:image/png;base64,{encoded}"/>'
                               f'<text x="16" y="536" font-family="sans-serif" font-size="12">'
                               f'{name} | {summary["revision"][:12]} | tessellation preview</text></svg>\n')
        summary['views'][name] = {**details, 'basis': basis, 'path': f'{relative_dir}/{name}.svg'}
    # The studio hero (DESIGN-LANGUAGE.md section 7): one PNG, the design's
    # presented image rather than a review view.
    hero_start = time.perf_counter()
    pixels, details = studio(prepared, HERO, bounds=_frame(prepared, HERO, 0.10), size=HERO_SIZE, shadow=shadow)
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
    lines = {view: sheet.line_view(triangles, summary, names, BASES[view])[0] for view in sheet.LINE_VIEWS}
    numbers = sheet.key_numbers(root, summary, names, inventory, environment)
    roles = {entry['role'] for entry in summary['appearance'].values()}
    files['sheet.png'] = sheet.compose(pixels, HERO_SIZE, lines, numbers, summary['palette'], roles,
                                       summary['proxies'], summary['revision'])
    summary['sheet'] = {'path': f'{relative_dir}/sheet.png', 'size': [sheet.WIDTH, sheet.HEIGHT],
                        'revision': summary['revision'], 'digest': summary.get('digest'),
                        'line_views': list(sheet.LINE_VIEWS), 'numbers': numbers,
                        'seconds': time.perf_counter() - sheet_start}
    files['summary.json'] = json.dumps(summary, indent=2) + '\n'
    # Do not leave partial new views on geometry/render refusal.
    directory = Path(root) / relative_dir
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            if isinstance(content, bytes):
                (directory / name).write_bytes(content)
            else:
                (directory / name).write_text(content, encoding='utf-8')
    except OSError as exc:
        raise InventoryError('render: cannot write views: ' + str(exc)) from exc
    return directory / 'summary.json', summary


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
