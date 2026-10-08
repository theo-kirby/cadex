# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""ot10 A8 (ADR-444): every presented image is drawn on the viewport's dark prototype mat.

One palette source (ADR-445): the engine's ``CadexStudio.PALETTE``, which the
studio renderer, ``look``, the concept sheet and the rollout video draw with,
in the CLI and the shell alike. The browser cannot import Python, so the
viewport's ``environment.js`` and the page's ``review.css`` carry the same
colours, and these tests fail if either drifts from the engine's table.
"""
import re
import shutil
from pathlib import Path

from cadex_cli import video
from cadex_cli.studio import STUDIO as render

# The palette, the sheet chrome and the renderer are one engine module now.
scene = sheet = render
CLI = Path(video.__file__).resolve().parent
STATIC = CLI / 'review_static'


def _hex(rgb):
    return '#%02x%02x%02x' % tuple(rgb)


def _viewport():
    """The viewport's colours, parsed here independently of :mod:`scene`."""
    environment = (STATIC / 'environment.js').read_text()
    tile = re.search(r'tile:\s*\{\s*tileA:\s*"(#\w{6})",\s*tileB:\s*"(#\w{6})",\s*line:\s*"(#\w{6})"', environment)
    bg = re.search(r'scene:\s*\{\s*bg:\s*0x(\w{6})', environment)
    return {'bg': '#' + bg.group(1), 'tile_a': tile.group(1), 'tile_b': tile.group(2), 'line': tile.group(3)}


def test_the_renderer_palette_is_the_viewports_palette():
    viewport = _viewport()
    assert {k: _hex(scene.PALETTE[k]) for k in viewport} == viewport
    # ...and the viewport's is the charter's dark prototype floor.
    assert viewport == {'bg': '#141414', 'tile_a': '#1c1c1c', 'tile_b': '#232323', 'line': '#3a3a3a'}
    # The floor module's fallback tile, which paints the mat before a palette
    # is passed, holds the same three colours.
    floor = (STATIC / 'floor.js').read_text()
    fallback = re.search(r'FALLBACK_TILE = \{\s*tileA:\s*"(#\w{6})",\s*tileB:\s*"(#\w{6})",\s*line:\s*"(#\w{6})"', floor)
    assert list(fallback.groups()) == [viewport['tile_a'], viewport['tile_b'], viewport['line']]
    # The sheet's chrome is the page's: paper --bg, ink --ink, muted --ink-2, rules --rule.
    css = re.search(r':root\s*\{(.*?)\}', (STATIC / 'review.css').read_text(), re.S).group(1)
    tokens = dict(re.findall(r'--([\w-]+):\s*(#\w{6})\b', css))
    assert (_hex(sheet.PAPER), _hex(sheet.INK), _hex(sheet.MUTED), _hex(sheet.RULE)) == \
        (tokens['bg'], tokens['ink'], tokens['ink-2'], tokens['rule'])
    assert tokens['bg'] == viewport['bg']


def _fraction(text):
    numerator, _, denominator = text.partition('/')
    return float(numerator) / float(denominator or 1)


def test_the_grid_is_the_viewports_grid():
    """Both floors are true size (ADR-604): one metre a square, the same line width."""
    floor = (STATIC / 'floor.js').read_text()
    pitch = re.search(r'export const GRID_PITCH = ([\d.]+);', floor).group(1)
    assert float(pitch) * 1000 == scene.GRID_PITCH_MM == 1000
    line = re.search(r'export const LINE_FRACTION = ([\d.\s/]+);', floor).group(1)
    assert _fraction(line) == scene.LINE_FRACTION == 5 / 256
    # No framing-dependent ladder is left on either side.
    assert 'PITCH_LADDER' not in floor and not hasattr(scene, 'grid_pitch_mm')
    # The texture draws its lines at that fraction of the pitch, and nothing finer.
    assert 'ctx.lineWidth = LINE_FRACTION * M' in floor and 'chooseGridPitch' not in floor


def test_the_engine_mat_is_a_metre_a_square_at_every_framing():
    """A 20 mm cube framed at 400 mm, and the same cube in a 4 m frame, both
    stand on 1000 mm squares; only how much of a square shows changes."""
    prepared = _scene_triangles()
    for span in (400.0, 4000.0):
        bounds = ([-span / 2, -span / 2], [span / 2, span / 2])
        _pixels, details = render.studio(prepared, render.HERO, bounds=bounds, size=48,
                                         shadow=render._contact_shadow(prepared))
        assert details['floor'] == {'kind': 'prototype mat', 'pitch_mm': 1000.0, 'z_mm': 0.0}
    # Lines every metre and only there: a ray landing on x = 1000 is on a
    # line, one landing on x = 500 (where a 4 m frame's old ladder drew one) is not.
    top = render.BASES['top']
    for span in (400.0, 4000.0):
        backdrop = render._floor(top, ([-span / 2 + 1000, -span / 2 + 250],
                                       [span / 2 + 1000, span / 2 + 250]), 64, 0.0)
        assert backdrop(32, 32, 1.0) != scene.PALETTE['bg']
        line = backdrop(31, 32, 1.0), backdrop(32, 32, 1.0)
        assert any(max(c) > max(scene.PALETTE['tile_b']) for c in line), span
    backdrop = render._floor(top, ([500 - 200, 250 - 200], [500 + 200, 250 + 200]), 64, 0.0)
    assert all(max(backdrop(x, 32, 1.0)) <= max(scene.PALETTE['tile_b']) for x in range(28, 36))


def test_no_cli_module_carries_a_colour_of_its_own_for_the_scene():
    """The light backdrop and paper are gone; no second Python copy of a scene colour."""
    for path in (CLI / 'render.py', CLI / 'studio.py', CLI / 'video.py'):
        source = path.read_text()
        assert 'BACKDROP' not in source and '#f6f7fa' not in source, path.name
        for colour in _viewport().values():
            assert colour not in source.lower(), (path.name, colour)
    assert not (CLI / 'scene.py').exists() and not (CLI / 'sheet.py').exists()


def _scene_triangles(size=(20.0, 20.0, 20.0)):
    """A 20 mm bone cube standing on z = 0."""
    v = [(i * size[0], j * size[1], k * size[2]) for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
             (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return render._prepare([((render.ROLE_COLORS['shell'], render.FINISH['shell']),
                              [tuple(v[i] for i in f) for f in faces])])


def _draw(prepared, basis=render.HERO, size=160):
    shadow = render._contact_shadow(prepared)
    return render.studio(prepared, basis, bounds=render._frame(prepared, basis, 0.10), size=size, shadow=shadow)


def _at(pixels, size, x, y):
    return tuple(pixels[3 * (y * size + x):3 * (y * size + x) + 3])


def test_the_hero_stands_on_the_mat_and_fades_into_the_scene():
    prepared = _scene_triangles()
    size = 160
    pixels, details = _draw(prepared, size=size)
    assert details['floor'] == {'kind': 'prototype mat', 'pitch_mm': 1000.0, 'z_mm': 0.0}
    mat = {scene.PALETTE['tile_a'], scene.PALETTE['tile_b']}
    colours = {_at(pixels, size, x, y) for y in range(size) for x in range(size)}
    # The checker's two tiles both appear unshaded, and the grid line is drawn
    # (blended, since it is antialiased) between them and the line colour.
    assert mat <= colours
    line = scene.PALETTE['line']
    assert any(max(c) > max(scene.PALETTE['tile_b']) + 8 and max(c) <= max(line) and max(c) - min(c) == 0
               for c in colours)
    # Nothing on the floor is lighter than the grid line: no light backdrop.
    floor_pixels = [c for c in colours if max(c) - min(c) == 0 and max(c) < 100]
    assert floor_pixels and max(max(c) for c in floor_pixels) <= max(line)
    # A level view sees no floor: the plain scene background, edge to edge.
    front, info = _draw(prepared, render.BASES['front'], size=64)
    assert info['floor'] == {'kind': 'scene background'}
    assert _at(front, 64, 0, 0) == _at(front, 64, 63, 63) == scene.PALETTE['bg']


def test_the_mat_fades_towards_the_scene_background_with_distance():
    """Far floor (the top of a hero) dims towards the background; near floor keeps its tiles."""
    prepared = _scene_triangles()
    size = 160
    pixels, _ = _draw(prepared, size=size)
    bg = scene.PALETTE['bg'][0]
    tiles = (scene.PALETTE['tile_a'][0] + scene.PALETTE['tile_b'][0]) / 2
    top = [_at(pixels, size, x, 0)[0] for x in range(size)]
    assert bg < sum(top) / size < tiles - 4
    # ...and past the fade every pixel is the background exactly.
    backdrop = render._floor(render.HERO, ([-10, -10], [10, 10]), 64, 0.0)
    assert backdrop(0, -2000, 1.0) == scene.PALETTE['bg']
    assert backdrop(32, 32, 1.0) != scene.PALETTE['bg']


def test_the_images_follow_the_palette_when_it_changes(monkeypatch):
    """Change the engine's palette and the renderer draws the new colours."""
    changed = {**render.PALETTE, 'tile_a': (0x40, 0x10, 0x10), 'bg': (0x10, 0x20, 0x40)}
    monkeypatch.setattr(render, 'PALETTE', changed)
    size = 160
    pixels, _ = _draw(_scene_triangles(), size=size)
    colours = {_at(pixels, size, x, y) for y in range(size) for x in range(size)}
    assert (0x40, 0x10, 0x10) in colours  # the changed tile, unshaded near the design
    front, _ = _draw(_scene_triangles(), render.BASES['front'], size=32)
    assert _at(front, 32, 0, 0) == (0x10, 0x20, 0x40)


def test_the_studio_video_identity_covers_the_engine_renderer(tmp_path, monkeypatch):
    before = video.studio_digest()
    changed = tmp_path / 'CadexStudio.py'
    shutil.copyfile(render.__file__, changed)
    changed.write_text(changed.read_text() + '\n')
    monkeypatch.setattr(render, '__file__', str(changed))
    assert video.studio_digest() != before
