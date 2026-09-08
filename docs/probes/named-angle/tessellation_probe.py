# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Evidence-only orthographic projection; not a product renderer.

Run with PROJECT containing accepted-display.json from a protocol rebuild.
Only standard library imports. SVG painter ordering is not hidden-surface proof.
"""
import json
import math
from pathlib import Path
import struct
import sys

root = Path(sys.argv[1])
reply = json.loads((root / 'accepted-display.json').read_text())
assert reply['ok'] and reply['revision'] == reply['accepted_revision']
display = reply['display']
components = {}
triangles = []
for name, entry in display.items():
    if 'source_output' not in entry:
        continue
    tess = display[entry['source_output']]['tessellation']
    sidecar = json.loads(Path(tess['sidecar_path']).read_text())
    assert sidecar['schema'] == 'cadex-tessellation-v1'
    binary = Path(tess['artifact_path']).read_bytes()
    def unpack(key, code):
        layout = sidecar['layout'][key]
        return struct.unpack_from('<' + code * (layout['bytes'] // 4), binary, layout['offset'])
    raw = unpack('vertices', 'f')
    matrix = entry['placement']
    vertices = [tuple(sum(matrix[4*r+c] * raw[i+c] for c in range(3)) + matrix[4*r+3]
                      for r in range(3)) for i in range(0, len(raw), 3)]
    components[name] = {'source': entry['source_output'], 'placement': matrix,
                        'bounds_mm': [[min(v[j] for v in vertices) for j in range(3)],
                                      [max(v[j] for v in vertices) for j in range(3)]]}
    indices = unpack('triangles', 'I')
    triangles.extend((name, [vertices[j] for j in indices[i:i+3]]) for i in range(0, len(indices), 3))
assert components['base']['bounds_mm'] == [[0, 0, 0], [60, 60, 6]]
assert components['swing']['bounds_mm'] == [[12, 0, 6], [92, 8, 14]]
# Explicit world-axis convention: front looks along +Y, right along -X,
# top along -Z; iso camera lies on (1,-1,1), with world Z upright.
s2, s3, s6 = math.sqrt(2), math.sqrt(3), math.sqrt(6)
bases = {'front': ((1,0,0),(0,0,1),(0,-1,0)),
         'top': ((1,0,0),(0,1,0),(0,0,1)),
         'right': ((0,1,0),(0,0,1),(1,0,0)),
         'iso': ((1/s2,1/s2,0),(-1/s6,1/s6,2/s6),(1/s3,-1/s3,1/s3))}
out = root / 'review' / 'render-probe'
out.mkdir(parents=True, exist_ok=True)
summary = {'revision': reply['revision'], 'digest': reply['digest'], 'components': components,
           'triangles': len(triangles), 'views': {}}
for name, basis in bases.items():
    projected = [(label, [tuple(sum(p[j]*axis[j] for j in range(3)) for axis in basis) for p in points])
                 for label, points in triangles]
    all_points = [p for _, points in projected for p in points]
    lo = [min(p[j] for p in all_points) for j in range(2)]
    hi = [max(p[j] for p in all_points) for j in range(2)]
    scale = min(520/(hi[j]-lo[j]) for j in range(2))
    def screen(p):
        return (320+(p[0]-(lo[0]+hi[0])/2)*scale, 320-(p[1]-(lo[1]+hi[1])/2)*scale)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640">',
           '<rect width="640" height="640" fill="#f6f7fa"/>',
           f'<text x="24" y="28" font-family="sans-serif" font-size="18">{name} | base: blue, swing: orange | mm</text>']
    polygons = []
    for label, points in sorted(projected, key=lambda t: sum(p[2] for p in t[1])/3):
        xy = [screen(p) for p in points]
        color = '#77aadd' if label == 'base' else '#ee9955'
        coords = ' '.join(f'{x:.3f},{y:.3f}' for x,y in xy)
        svg.append(f'<polygon points="{coords}" fill="{color}" stroke="#25364a" stroke-width="0.7"/>')
        polygons.append({'label': label, 'xy': xy, 'color': color})
    svg.append('</svg>')
    (out / f'{name}.svg').write_text('\n'.join(svg)+'\n')
    summary['views'][name] = {'projection_bounds_mm': [lo,hi], 'polygons': polygons}
(out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps({'revision': reply['revision'], 'triangles': len(triangles), 'components': components,
                  'outputs': [str((out / f'{v}.svg').relative_to(root)) for v in bases]}))
