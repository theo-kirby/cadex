# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The concept sheet (ot10 A6, ADR-430): one PNG that presents a design.

The studio hero on the left; on the right the design's name, its key numbers
(mass, servo count, size), its palette, three orthographic line views and
A1's proxies. Drawn by :func:`render.write_render` beside the hero it reuses,
from the same accepted snapshot, with no dependency beyond the renderer's own
depth pass: the line views are its object and crease boundaries, and the
lettering is a 5x7 bitmap face defined here.

Independently authored LGPL client code.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

WIDTH, HEIGHT = 1536, 1024
#: The orthographic views the sheet draws as lines, in the order it lays them out.
LINE_VIEWS = ('front', 'right', 'top')
LINE_SIZE = 204
#: Two faces of one object meeting at more than this draw a line.
LINE_CREASE_DEGREES = 35.0
PAPER = (246, 245, 241)
INK = (43, 47, 54)
MUTED = (122, 126, 133)
RULE = (214, 212, 206)
#: The catalog family whose placed components the sheet counts as servos.
SERVO_FAMILY = 'servo'

# A 5x7 face: each glyph is seven rows, most significant bit leftmost.
_FONT_ROWS = {
    'A': '.###. #...# #...# ##### #...# #...# #...#',
    'B': '####. #...# #...# ####. #...# #...# ####.',
    'C': '.###. #...# #.... #.... #.... #...# .###.',
    'D': '####. #...# #...# #...# #...# #...# ####.',
    'E': '##### #.... #.... ####. #.... #.... #####',
    'F': '##### #.... #.... ####. #.... #.... #....',
    'G': '.###. #...# #.... #.### #...# #...# .####',
    'H': '#...# #...# #...# ##### #...# #...# #...#',
    'I': '.###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.',
    'J': '..### ...#. ...#. ...#. ...#. #..#. .##..',
    'K': '#...# #..#. #.#.. ##... #.#.. #..#. #...#',
    'L': '#.... #.... #.... #.... #.... #.... #####',
    'M': '#...# ##.## #.#.# #.#.# #...# #...# #...#',
    'N': '#...# #...# ##..# #.#.# #..## #...# #...#',
    'O': '.###. #...# #...# #...# #...# #...# .###.',
    'P': '####. #...# #...# ####. #.... #.... #....',
    'Q': '.###. #...# #...# #...# #.#.# #..#. .##.#',
    'R': '####. #...# #...# ####. #.#.. #..#. #...#',
    'S': '.#### #.... #.... .###. ....# ....# ####.',
    'T': '##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..',
    'U': '#...# #...# #...# #...# #...# #...# .###.',
    'V': '#...# #...# #...# #...# #...# .#.#. ..#..',
    'W': '#...# #...# #...# #.#.# #.#.# #.#.# .#.#.',
    'X': '#...# #...# .#.#. ..#.. .#.#. #...# #...#',
    'Y': '#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..',
    'Z': '##### ....# ...#. ..#.. .#... #.... #####',
    '0': '.###. #...# #..## #.#.# ##..# #...# .###.',
    '1': '..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.',
    '2': '.###. #...# ....# ...#. ..#.. .#... #####',
    '3': '##### ...#. ..#.. ...#. ....# #...# .###.',
    '4': '...#. ..##. .#.#. #..#. ##### ...#. ...#.',
    '5': '##### #.... ####. ....# ....# #...# .###.',
    '6': '..##. .#... #.... ####. #...# #...# .###.',
    '7': '##### ....# ...#. ..#.. .#... .#... .#...',
    '8': '.###. #...# #...# .###. #...# #...# .###.',
    '9': '.###. #...# #...# .#### ....# ...#. .##..',
    '.': '..... ..... ..... ..... ..... .##.. .##..',
    ',': '..... ..... ..... ..... .##.. ..#.. .#...',
    '-': '..... ..... ..... .###. ..... ..... .....',
    '+': '..... ..#.. ..#.. ##### ..#.. ..#.. .....',
    '=': '..... ..... ##### ..... ##### ..... .....',
    '/': '....# ....# ...#. ..#.. .#... #.... #....',
    ':': '..... .##.. .##.. ..... .##.. .##.. .....',
    '%': '##..# ##..# ...#. ..#.. .#... #..## #..##',
    '(': '...#. ..#.. .#... .#... .#... ..#.. ...#.',
    ')': '.#... ..#.. ...#. ...#. ...#. ..#.. .#...',
    '_': '..... ..... ..... ..... ..... ..... #####',
    '#': '.#.#. .#.#. ##### .#.#. ##### .#.#. .#.#.',
    '?': '.###. #...# ....# ...#. ..#.. ..... ..#..',
    ' ': '..... ..... ..... ..... ..... ..... .....',
}
FONT = {ch: tuple(row for row in rows.split()) for ch, rows in _FONT_ROWS.items()}


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

    def text(self, x, y, text, scale, colour):
        """Draws ``text`` upper-cased in the 5x7 face; returns the x after it."""
        for ch in str(text).upper():
            for j, row in enumerate(FONT.get(ch, FONT['?'])):
                for i, bit in enumerate(row):
                    if bit == '#':
                        self.rect(x + i * scale, y + j * scale, scale, scale, colour)
            x += 6 * scale
        return x


def text_width(text, scale):
    return max(0, 6 * scale * len(str(text)) - scale)


def fitted_scale(text, width, largest):
    """The largest scale up to ``largest`` at which ``text`` fits ``width``."""
    for scale in range(largest, 0, -1):
        if text_width(text, scale) <= width:
            return scale
    return 1


def line_view(triangles, summary, names, basis, *, size=LINE_SIZE):
    """An orthographic line drawing: ``(rgb pixels, details)``.

    Every pixel is 2x2 subsamples of the renderer's own depth pass, keyed by
    object and flat face normal. A subsample is ink where the nearest surface
    changes object, meets the backdrop (the silhouette, drawn on both sides
    so it reads heavier), or turns by more than LINE_CREASE_DEGREES within
    one object; coverage is then box-filtered to grey, which antialiases it.
    """
    from . import render
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
    render._require(bool(prepared), 'nothing to draw in a line view')
    samples = render.SUPERSAMPLE
    owner, shading, visits = render._depth_pass(prepared, basis, render._frame(prepared, basis, 0.06),
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
    from . import render
    sheet = Canvas(WIDTH, HEIGHT, PAPER)
    scale = HEIGHT / hero_size
    render._require(scale == 1, 'the sheet is laid out for a 1024 px hero')
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
    return render.png(sheet.pixels, WIDTH, HEIGHT)
