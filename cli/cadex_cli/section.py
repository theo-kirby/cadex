# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Named world-plane cuts of the accepted tessellation; no kernel imports."""
import html
import json
import math
from pathlib import Path
import time

from .inventory import InventoryError
from .render import snapshot

PLANES = {'XY': (0, 1, 2), 'XZ': (0, 2, 1), 'YZ': (1, 2, 0)}
TOLERANCE = 1e-6  # mm; endpoint grid, also conservative plane-contact refusal
APPROXIMATION = ('Standard tessellation cut in the initial solved world pose, mm; not exact BREP. '
                 'Closed contours filled even-odd per object preserve cavities. No union across objects. '
                 'Plane contacts within 1e-6 mm and open/branched cuts are unsupported; '
                 'no solid-validity or self-intersection certification. Shell visibility is unavailable.')


def contours(triangles, plane, offset):
    """Return closed planar loops or an explicit unsupported/empty status."""
    u, v, normal = PLANES[plane]
    edges = set()
    for _, tri in triangles:
        distances = [p[normal] - offset for p in tri]
        if min(distances) > TOLERANCE or max(distances) < -TOLERANCE:
            continue
        if any(abs(d) <= TOLERANCE for d in distances):
            return {'status': 'unsupported', 'reason': 'plane contacts a tessellation vertex/edge/face', 'contours_mm': []}
        points = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if distances[i] * distances[j] < 0:
                t = distances[i] / (distances[i] - distances[j])
                points.append(tuple(round((tri[i][a] + t*(tri[j][a]-tri[i][a])) / TOLERANCE)
                                    for a in (u, v)))
        if len(points) == 2:
            edge = tuple(sorted(points))
            if edge[0] == edge[1] or edge in edges:
                return {'status': 'unsupported', 'reason': 'collapsed or duplicate cut segment', 'contours_mm': []}
            edges.add(edge)
    if not edges:
        return {'status': 'empty', 'contours_mm': []}
    neighbors = {}
    for a, b in sorted(edges):
        neighbors.setdefault(a, []).append(b)
        neighbors.setdefault(b, []).append(a)
    if any(len(adj) != 2 for adj in neighbors.values()):
        return {'status': 'unsupported', 'reason': 'open or branched cut contour', 'contours_mm': []}
    loops = []
    remaining = set(neighbors)
    for start in sorted(neighbors):
        if start not in remaining:
            continue
        loop, previous, current = [], None, start
        while True:
            remaining.remove(current)
            loop.append([x*TOLERANCE for x in current])
            nxt = next(p for p in neighbors[current] if p != previous)
            previous, current = current, nxt
            if current == start:
                break
        loops.append(loop)
    return {'status': 'ok', 'contours_mm': loops}


def section_snapshot(triangles, summary, plane, offset):
    if plane not in PLANES or not math.isfinite(offset) or abs(offset) > 1e9:
        raise InventoryError('section: invalid plane or offset')
    start = time.perf_counter()
    objects, index = {}, 0
    for name, obj in summary['objects'].items():
        count = obj['triangles']
        objects[name] = {**obj, **contours(triangles[index:index+count], plane, offset)}
        index += count
    statuses = {o['status'] for o in objects.values()}
    status = 'unsupported' if 'unsupported' in statuses else ('ok' if 'ok' in statuses else 'empty')
    return {**summary, 'plane': plane, 'offset_mm': offset, 'units': 'mm',
            'axes': list(plane.lower()), 'status': status, 'available': status != 'unsupported', 'objects': objects,
            'approximation': APPROXIMATION,
            'limits': {**summary['limits'], 'endpoint_grid_mm': TOLERANCE},
            'section_seconds': time.perf_counter() - start}


def svg(summary):
    points = [p for obj in summary['objects'].values() for loop in obj['contours_mm'] for p in loop]
    lo, hi = ([fn(p[a] for p in points) for a in (0, 1)] for fn in (min, max)) if points else ([0, 0], [1, 1])
    scale = 448 / max(hi[a]-lo[a] for a in (0, 1))
    paths = []
    for name, obj in summary['objects'].items():
        commands = []
        for loop in obj['contours_mm']:
            for i, p in enumerate(loop):
                x = 256 + (p[0]-(lo[0]+hi[0])/2)*scale
                y = 256 - (p[1]-(lo[1]+hi[1])/2)*scale
                commands.append(f'{"M" if i == 0 else "L"}{x:.6f},{y:.6f}')
            commands.append('Z')
        if commands:
            paths.append(f'<path d="{" ".join(commands)}" fill="rgb{tuple(obj["color"])}" '
                         f'fill-rule="evenodd" stroke="#172332" stroke-width="1"><title>{html.escape(name)}</title></path>')
    label = html.escape(f'{summary["plane"]} {summary["offset_mm"]:g} mm | {summary["status"]} | tessellation cut')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="552" viewBox="0 0 512 552">'
            f'<title>{label} | accepted {summary["revision"]}</title><rect width="512" height="552" fill="#f6f7fa"/>'
            + ''.join(paths) + f'<text x="16" y="536" font-size="12">{label}</text></svg>\n')


def write_section(client, root, *, plane, offset, expected_revision=None):
    start = time.perf_counter()
    triangles, source = snapshot(client.request('rebuild', {'display': {'quality': 'standard', 'edges': False}}))
    if expected_revision is not None and source['revision'] != expected_revision:
        raise InventoryError('section: accepted revision differs from expected revision')
    source['acquisition_seconds'] = time.perf_counter() - start
    summary = section_snapshot(triangles, source, plane, offset)
    relative = f'review/section/{source["revision"]}/{plane}-{offset:.17g}'
    summary['path'] = relative + '/section.svg'
    content = svg(summary)
    directory = Path(root) / relative
    try:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'section.svg').write_text(content, encoding='utf-8')
        path = directory / 'summary.json'
        path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        raise InventoryError('section: cannot write artifacts: ' + str(exc)) from exc
    return path, summary
