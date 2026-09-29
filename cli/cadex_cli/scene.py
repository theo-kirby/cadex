# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The dark prototype scene every presented image is drawn in (ot10 A8, ADR-444).

There is one palette source, and it is the review viewport's own: the scene
background and the mat's tiles and major line are read from ``PALETTE`` in
``review_static/environment.js``, and the chrome's ink and rule from the
``:root`` tokens in ``review_static/review.css``. The studio hero, ``look``,
the concept sheet and the rollout video take their colours from here, so an
image and the viewport cannot drift apart: change the viewport and the images
follow it. Nothing here is a second copy of a colour.

Independently authored LGPL client code.
"""
from __future__ import annotations

from pathlib import Path
import re

STATIC_DIR = Path(__file__).resolve().parent / 'review_static'
SOURCES = (STATIC_DIR / 'environment.js', STATIC_DIR / 'review.css')


def _rgb(hex6):
    return tuple(int(hex6[i:i + 2], 16) for i in (0, 2, 4))


def _read():
    environment = SOURCES[0].read_text(encoding='utf-8')
    block = re.search(r'export const PALETTE = \{(.*?)\n\};', environment, re.S)
    if block is None:
        raise RuntimeError('environment.js: no PALETTE block')
    body = block.group(1)
    tile = re.search(r'tile:\s*\{(.*?)\}', body, re.S).group(1)
    scene = re.search(r'scene:\s*\{(.*?)\}', body, re.S).group(1)

    def colour(text, key, pattern):
        found = re.search(key + r':\s*' + pattern, text)
        if found is None:
            raise RuntimeError(f'environment.js: PALETTE has no {key}')
        return _rgb(found.group(1).lower())
    css = SOURCES[1].read_text(encoding='utf-8')
    root = re.search(r':root\s*\{(.*?)\}', css, re.S).group(1)

    def token(name):
        found = re.search(r'--' + name + r':\s*#([0-9a-fA-F]{6})\b', root)
        if found is None:
            raise RuntimeError(f'review.css: :root has no --{name}')
        return _rgb(found.group(1).lower())
    return {
        'bg': colour(scene, 'bg', r'0x([0-9a-fA-F]{6})'),
        'tile_a': colour(tile, 'tileA', r'"#([0-9a-fA-F]{6})"'),
        'tile_b': colour(tile, 'tileB', r'"#([0-9a-fA-F]{6})"'),
        'line': colour(tile, 'line', r'"#([0-9a-fA-F]{6})"'),
        'ink': token('ink'),
        'ink_2': token('ink-2'),
        'rule': token('rule'),
    }


#: The scene as RGB triples: ``bg`` (the viewport's sky and the page's
#: ``--bg``), the mat's ``tile_a``/``tile_b`` checker and major ``line``, and
#: the chrome's ``ink``, ``ink_2`` and ``rule``.
PALETTE = _read()
#: The viewport's grid pitches (``floor.js`` ``PITCH_LADDER``), in millimetres.
PITCH_LADDER_MM = (10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000)
#: A major line is 5/256 of its pitch wide, as ``floor.js`` paints it
#: (5 px of a 512 px texture spanning two pitches).
LINE_FRACTION = 5 / 256


def grid_pitch_mm(span_mm, want=5):
    """The mat's pitch for a shot spanning ``span_mm``: ``floor.js`` ``chooseGridPitch``."""
    target = max(1e-4, span_mm) / max(1, want)
    best = PITCH_LADDER_MM[0]
    for pitch in PITCH_LADDER_MM:
        if pitch <= target:
            best = pitch
    return best


def hex_colour(rgb):
    return '#%02x%02x%02x' % tuple(rgb)
