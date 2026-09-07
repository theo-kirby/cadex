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

from .inventory import InventoryError

SIZE = 512
MAX_BYTES = 32 * 1024 * 1024
MAX_VERTICES = 300_000
MAX_PLACED_VERTICES = 600_000
MAX_TRIANGLES = 100_000
MAX_SAMPLES = 20_000_000  # bounding-box pixel visits per view, including overdraw
IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
s2, s3, s6 = math.sqrt(2), math.sqrt(3), math.sqrt(6)
BASES = {
    'front': ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    'top': ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    'right': ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
    'iso': ((1/s2, 1/s2, 0), (-1/s6, 1/s6, 2/s6), (1/s3, -1/s3, 1/s3)),
}
PALETTE = [(91, 157, 205), (230, 151, 76), (115, 182, 135), (180, 134, 200)]
LIMITS = {'buffer_bytes': MAX_BYTES, 'triangles': MAX_TRIANGLES, 'vertices_per_source': MAX_VERTICES,
          'placed_vertices': MAX_PLACED_VERTICES,
          'pixel_visits_per_view': MAX_SAMPLES, 'image_size': SIZE}
APPROXIMATION = ('Opaque standard tessellation, initial solved pose; 512px pixel-center depth, '
                 'flat lighting, no transparency, edges, dimensions or subpixel guarantees. '
                 'Shell-only visibility is not carried by the protocol. Placed source copies '
                 'are excluded; all other published triangle geometry is shown.')


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
    cache, triangles, objects = {}, [], {}
    budget = 0
    placed_vertices = 0

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
            _require(count // 12 <= (MAX_VERTICES if key == 'vertices' else MAX_TRIANGLES),
                     key + ' count budget exceeded')
            arrays.append(list(struct.iter_unpack('<' + code * 3, data[offset:offset+count])))
        vertices, indices = arrays
        _require(all(math.isfinite(x) and abs(x) <= 1e9 for v in vertices for x in v),
                 'nonfinite or excessive coordinates')
        _require(len(indices) <= MAX_TRIANGLES and
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
            _require(len(triangles) + len(indices) <= MAX_TRIANGLES, 'triangle budget exceeded')
            if not indices:
                continue
            color = PALETTE[len(objects) % len(PALETTE)]
            triangles.extend((color, tuple(points[i] for i in tri)) for tri in indices)
            objects[name] = {'source': source, 'placement': matrix, 'color': color,
                             'bounds_mm': [[fn(p[j] for p in points) for j in range(3)]
                                           for fn in (min, max)]}
    except (OSError, KeyError, TypeError, ValueError, struct.error) as exc:
        raise InventoryError('render: malformed or unreadable display: ' + str(exc)) from exc
    _require(bool(triangles), 'no published triangle geometry')
    return triangles, {'revision': revision, 'digest': reply.get('digest'), 'objects': objects,
                       'triangles': len(triangles), 'snapshot_bytes': budget,
                       'approximation': APPROXIMATION, 'limits': LIMITS}


def rasterize(triangles, basis):
    projected = [(color, [tuple(sum(p[j]*axis[j] for j in range(3)) for axis in basis)
                          for p in points]) for color, points in triangles]
    points = [p for _, tri in projected for p in tri]
    lo, hi = ([fn(p[j] for p in points) for j in range(2)] for fn in (min, max))
    extent = max(hi[j] - lo[j] for j in range(2))
    _require(extent > 0, 'zero projected extent')
    scale = (SIZE - 64) / extent
    pixels = bytearray(bytes((246, 247, 250)) * SIZE * SIZE)
    depth = [-math.inf] * (SIZE * SIZE)
    samples = 0
    for color, tri in projected:
        a, b, c = [(SIZE/2 + (p[0]-(lo[0]+hi[0])/2)*scale,
                    SIZE/2 - (p[1]-(lo[1]+hi[1])/2)*scale, p[2]) for p in tri]
        area = (b[1]-c[1])*(a[0]-c[0]) + (c[0]-b[0])*(a[1]-c[1])
        if abs(area) < 1e-12:
            continue
        xmin, xmax = max(0, math.floor(min(a[0], b[0], c[0]))), min(SIZE-1, math.ceil(max(a[0], b[0], c[0])))
        ymin, ymax = max(0, math.floor(min(a[1], b[1], c[1]))), min(SIZE-1, math.ceil(max(a[1], b[1], c[1])))
        samples += (xmax-xmin+1)*(ymax-ymin+1)
        _require(samples <= MAX_SAMPLES, 'pixel work budget exceeded')
        u, v = ([tri[1][j]-tri[0][j] for j in range(3)], [tri[2][j]-tri[0][j] for j in range(3)])
        normal = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        norm = math.sqrt(sum(n*n for n in normal))
        light = (.25, -.45, math.sqrt(.735))
        shade = .55 + .45 * abs(sum(n*l for n, l in zip(normal, light))) / norm if norm else 1
        rgb = bytes(round(channel * shade) for channel in color)
        for y in range(ymin, ymax+1):
            for x in range(xmin, xmax+1):
                w0 = ((b[1]-c[1])*(x+.5-c[0]) + (c[0]-b[0])*(y+.5-c[1])) / area
                w1 = ((c[1]-a[1])*(x+.5-c[0]) + (a[0]-c[0])*(y+.5-c[1])) / area
                w2 = 1-w0-w1
                if min(w0, w1, w2) < -1e-10:
                    continue
                z = w0*a[2] + w1*b[2] + w2*c[2]
                i = y*SIZE+x
                # Equal-depth ties are stable in sorted output/triangle order.
                if z > depth[i]:
                    depth[i] = z
                    pixels[3*i:3*i+3] = rgb
    return pixels, {'projection_bounds_mm': [lo, hi], 'pixel_visits': samples,
                    'covered_pixels': sum(d > -math.inf for d in depth)}


def png(pixels):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data))
    rows = b''.join(b'\0' + pixels[y*SIZE*3:(y+1)*SIZE*3] for y in range(SIZE))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', SIZE, SIZE, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def write_render(client, root):
    start = time.perf_counter()
    reply = client.request('rebuild', {'display': {'quality': 'standard', 'edges': False}})
    triangles, summary = snapshot(reply)
    summary['acquisition_seconds'] = time.perf_counter() - start
    start = time.perf_counter()
    files, summary['views'] = {}, {}
    for name, basis in BASES.items():
        pixels, details = rasterize(triangles, basis)
        encoded = base64.b64encode(png(pixels)).decode('ascii')
        title = html.escape(f"{name} | accepted {summary['revision']} | tessellation preview")
        files[name + '.svg'] = (f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="552" viewBox="0 0 512 552">'
                               f'<title>{title}</title><rect width="512" height="552" fill="#f6f7fa"/>'
                               f'<image width="512" height="512" href="data:image/png;base64,{encoded}"/>'
                               f'<text x="16" y="536" font-family="sans-serif" font-size="12">'
                               f'{name} | {summary["revision"][:12]} | tessellation preview</text></svg>\n')
        summary['views'][name] = {**details, 'basis': basis, 'path': f'review/render/{name}.svg'}
    summary['render_seconds'] = time.perf_counter() - start
    files['summary.json'] = json.dumps(summary, indent=2) + '\n'
    # Do not leave partial new views on geometry/render refusal.
    directory = Path(root) / 'review' / 'render'
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (directory / name).write_text(content, encoding='utf-8')
    except OSError as exc:
        raise InventoryError('render: cannot write views: ' + str(exc)) from exc
    return directory / 'summary.json', summary
