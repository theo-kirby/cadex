# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Named world-plane cuts of the accepted tessellation; no kernel imports."""
import html
import json
import math
from pathlib import Path
import time

from .inventory import InventoryError
from .render import acquire_snapshot

PLANES = {'XY': (0, 1, 2), 'XZ': (0, 2, 1), 'YZ': (1, 2, 0)}
TOLERANCE = 1e-6  # mm; endpoint grid, also conservative plane-contact refusal
MAX_DERIVED_CANDIDATES = 48  # a work bound on the sibling planes, never on the centres
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
            'objects_cut': sum(1 for o in objects.values() if o['status'] == 'ok'),
            'approximation': APPROXIMATION,
            'limits': {**summary['limits'], 'endpoint_grid_mm': TOLERANCE},
            'section_seconds': time.perf_counter() - start}


def offset_candidates(summary, plane):
    """Offsets worth cutting at, read off the accepted bounds; caller ranks.

    A constant offset cuts whatever happens to be there: on a mechanism whose
    moving part sits entirely off the chosen plane, the cut is real, the
    overall status is `ok`, and the part the run exists to look at is missing
    from it. Each object's bounding-box centre is a plane that certainly
    passes through *that* object, so the candidates are those centres plus the
    whole geometry's, ordered by how many objects' bounds the plane crosses,
    then by nearness to the overall centre. Bounds are not the solid: a
    candidate can still cut a cavity and come back empty, so this ordering
    decides nothing -- `derived_section` cuts every candidate and compares
    the cuts (ADR-273). What it is still fit for is a tiebreak, and the
    order the sibling planes are dropped in when there are too many.

    A centre is also the plane a part is most likely to be symmetric about,
    and a tessellation puts vertices and edges exactly on its own symmetry
    plane -- so the candidate with the best coverage is systematically the
    one `contours` refuses for plane contact, and the derivation falls back
    to a plane that misses the part it was reaching for (ADR-270). Each
    centre therefore travels with two quarter-span siblings, still strictly
    inside the same bounds and so still certain to cross them, ranked after
    the centre they came from: the centre stays the drawing of choice, and a
    seam on it costs a few millimetres rather than the part.
    """
    normal = PLANES[plane][2]
    spans = [(obj['bounds_mm'][0][normal], obj['bounds_mm'][1][normal])
             for obj in summary['objects'].values() if obj.get('bounds_mm')]
    if not spans:
        raise InventoryError('section: no accepted bounds to derive an offset from')
    overall = (min(lo for lo, _ in spans), max(hi for _, hi in spans))
    centre = (overall[0] + overall[1]) / 2

    def coverage(offset):
        return sum(1 for lo, hi in spans if lo < offset < hi)

    # Rounded to a micron so the artifact directory a run writes is readable
    # and two runs of the same geometry agree on it. A candidate reached both
    # as a centre and as a sibling keeps the centre's rank.
    candidates = {}
    for lo, hi in (overall, *spans):
        middle, quarter = (lo + hi) / 2, (hi - lo) / 4
        for sibling, offset in enumerate((middle, middle - quarter, middle + quarter)):
            offset = round(offset, 3)
            candidates[offset] = min(candidates.get(offset, 1), min(sibling, 1))
    ordered = sorted(candidates, key=lambda offset: (-coverage(offset), candidates[offset],
                                                     abs(offset - centre), offset))
    # Every centre is kept, however poorly its plane covers the rest (ADR-273).
    # Truncating this list by coverage undoes the whole point of deriving it:
    # on ot4-swing2 the mount-hardware cluster filled all eight places a
    # narrower bound allowed, and the four planes that cut `cmp_swing_arm` --
    # the moving part the rig exists to look at -- were never cut at all. The
    # bound is a work bound, so it applies to the siblings, and only once an
    # assembly has more distinct centres than a few dozen contour passes.
    centres = [offset for offset in ordered if not candidates[offset]]
    siblings = [offset for offset in ordered if candidates[offset]]
    keep = set(centres) | set(siblings[:max(0, MAX_DERIVED_CANDIDATES - len(centres))])
    return [offset for offset in ordered if offset in keep]


def derived_section(triangles, summary, plane):
    """The candidate offset that cuts the most objects, ties to the best-ranked.

    The ordering above is read off bounding boxes, and bounds are not the
    solid: a plane can cross an object's box and come back `empty` because it
    passed through a cavity, or through the gap between two lobes. Taking the
    first candidate whose *overall* status is `ok` inherits that blindness
    twice over, because `ok` means only that *some* object was cut -- so a
    plane through a dense cluster of fasteners beat a plane through the one
    moving part, and nothing in the derivation noticed (ADR-273).

    So every candidate is cut, and the cuts are compared on the one thing a
    reader of the drawing can check: how many objects actually came back with
    contours. A cut `contours` refuses is not a drawing, so an available cut
    wins over an unavailable one regardless of count; the bounds ordering
    survives only as the tiebreak it was always fit to be. This costs one
    contour pass per candidate, each the pass the caller used to run anyway.
    """
    candidates = offset_candidates(summary, plane)
    cuts = [{**section_snapshot(triangles, summary, plane, offset),
             'offset_source': 'derived', 'offset_candidates_mm': candidates}
            for offset in candidates]
    return max(enumerate(cuts), key=lambda c: (c[1]['available'], c[1]['objects_cut'], -c[0]))[1]


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
    # The count is on the face of the drawing because a section is as much a
    # claim about what it did not reach as about what it shows: `ok` alone
    # cannot tell a reader that four of ten parts are missing from the page.
    label = html.escape(f'{summary["plane"]} {summary["offset_mm"]:g} mm | {summary["status"]} | '
                        f'{summary["objects_cut"]}/{len(summary["objects"])} objects cut | tessellation cut')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="552" viewBox="0 0 512 552">'
            f'<title>{label} | accepted {summary["revision"]}</title><rect width="512" height="552" fill="#f6f7fa"/>'
            + ''.join(paths) + f'<text x="16" y="536" font-size="12">{label}</text></svg>\n')


def write_section(client, root, *, plane, offset=None, expected_revision=None, accepted_snapshot=None):
    """Cut at `offset`, or -- with `offset=None` -- where the geometry is."""
    triangles, source = accepted_snapshot if accepted_snapshot is not None else acquire_snapshot(client)
    if expected_revision is not None and source['revision'] != expected_revision:
        raise InventoryError('section: accepted revision differs from expected revision')
    if offset is None:
        summary = derived_section(triangles, source, plane)
        offset = summary['offset_mm']
    else:
        summary = {**section_snapshot(triangles, source, plane, offset), 'offset_source': 'explicit'}
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
