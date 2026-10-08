# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The studio renderer's standing (ADR-445, ADR-529).

``CadexStudio`` is engine code that ``cadexd`` never imports: the CLI and the
dashboard load it by path. The child-process entry the Blender shell ran
(``cadex-studio-request-v1``) left with the shell (ADR-529). These tests pin
the two facts that make the module what it is -- the service's closure does
not reach it, and the payload installs it -- plus the review set it draws in
process. What the renderer draws is tested through the CLI, in
``cli/tests/test_render.py``, ``test_look.py``, ``test_sheet.py`` and
``test_scene_palette.py``.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct

import CadexStudio
from test_engine_purity_guardrails import _engine_closure

MODULE_DIR = Path(CadexStudio.__file__).resolve().parent
IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
PNG = b'\x89PNG\r\n\x1a\n'


def _mesh(tmp_path, name, size, z0=0.0):
    x, y, z = size
    vertices = [(i * x, j * y, z0 + k * z) for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    triangles = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
                 (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    data = b''.join(struct.pack('<3f', *v) for v in vertices)
    data += b''.join(struct.pack('<3I', *t) for t in triangles)
    binary, side = tmp_path / f'{name}.bin', tmp_path / f'{name}.json'
    binary.write_bytes(data)
    side.write_text(json.dumps({
        'schema': 'cadex-tessellation-v1', 'byte_order': 'little',
        'layout': {'vertices': {'offset': 0, 'bytes': 12 * len(vertices), 'dtype': 'f32'},
                   'triangles': {'offset': 12 * len(vertices), 'bytes': 12 * len(triangles),
                                 'dtype': 'u32'}}}))
    return {'artifact_kind': 'tessellation', 'artifact_path': str(binary), 'sidecar_path': str(side)}


def _reply(tmp_path, lift=0.0):
    """A floor, a 20 mm printed body on it and a purchased pin beside it,
    both ``lift`` mm above the floor's top face."""
    revision = 'a' * 64
    display = {}
    for name, size, z0 in (('floor', (1000, 1000, 2), -2), ('body', (20, 20, 20), lift), ('pin', (5, 5, 30), lift)):
        display[name] = {'artifact_kind': 'brep', 'placement': None, 'tessellation': _mesh(tmp_path, name, size, z0)}
        display['c_' + name] = {'artifact_kind': None, 'placement': IDENTITY, 'tessellation': None,
                                'source_output': name}
    display['c_pin']['placement'] = [1, 0, 0, 30, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    return {'ok': True, 'revision': revision, 'accepted_revision': revision, 'digest': 'd' * 64,
            'display': display}


FIT = {'failing': [{'first': 'c_floor', 'status': 'world geometry'}]}
INVENTORY = {'available': True, 'uncatalogued_sources': ['body', 'floor'],
             'appearance': {'c_pin': 'accent'}, 'palette': {'accent': '#FF0000'}}



def test_a_render_draws_the_review_set_in_process(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    triangles, source = CadexStudio.snapshot(_reply(tmp_path), CadexStudio.world(FIT))
    files, summary = CadexStudio.render_files(triangles, source, str(root), FIT, INVENTORY, 'review/render')
    assert sorted(files) == ['front.svg', 'hero.png', 'iso.svg', 'right.svg', 'sheet.png', 'summary.json', 'top.svg']
    assert files['hero.png'].startswith(PNG)
    assert summary['hero']['path'] == 'review/render/hero.png' and summary['environment'] == ['c_floor']
    assert summary['appearance']['c_pin'] == {'role': 'accent', 'color': '#FF0000', 'source': 'declared',
                                              'finish': 'purchased', 'catalog': None}
    # The floor is never drawn: the mat stands in for it at its top face, a
    # metre a square (ADR-604).
    assert summary['hero']['floor'] == {'kind': 'prototype mat', 'pitch_mm': 1000.0, 'z_mm': 0.0}
    # No accepted attempt to read a mass from: the sheet says so rather than guessing.
    assert summary['sheet']['numbers']['mass_kg'] is None
    written = CadexStudio.write_files(tmp_path / 'out', files)
    assert json.loads((tmp_path / 'out' / 'summary.json').read_text())['revision'] == summary['revision']
    assert len(written) == 7


def test_the_mat_lies_at_the_top_of_the_world_geometry_not_under_the_design(tmp_path):
    """A design whose initial pose stands 5 mm above its floor is drawn 5 mm
    above the mat, in the hero and in a look, and the floor itself is not drawn."""
    triangles, source = CadexStudio.snapshot(_reply(tmp_path, lift=5.0), CadexStudio.world(FIT))
    _image, facts = CadexStudio.hero(triangles, source, FIT, INVENTORY)
    assert facts['environment'] == ['c_floor']
    _facts, shots = CadexStudio.look_report(_reply(tmp_path, lift=5.0), FIT, INVENTORY, ['hero', 'iso'])
    assert {view: details['floor']['z_mm'] for view, _png, details in shots} == {'hero': 0.0, 'iso': 0.0}
    # The 1 m floor slab would frame a metre; the shot frames the 30 mm design.
    width = shots[0][2]['projection_bounds_mm'][1][0] - shots[0][2]['projection_bounds_mm'][0][0]
    assert width < 100


def test_the_look_names_what_it_left_out(tmp_path):
    facts, shots = CadexStudio.look_report(_reply(tmp_path), FIT, INVENTORY, ['hero'])
    assert facts['views'] == ['hero'] and facts['left_out_as_environment'] == ['c_floor']
    assert facts['components_drawn'] == 2 and 'accent #FF0000' in facts['colours']
    assert shots[0][1].startswith(PNG)


def test_the_service_never_imports_the_renderer_and_the_payload_ships_it():
    """cadexd dispatches serially; a 12 s render inside it would stall the slider drag."""
    assert not {'CadexStudio', 'CadexFitReport'} & set(_engine_closure())
    cmake = (MODULE_DIR / 'CMakeLists.txt').read_text(encoding='utf-8')
    assert '    CadexStudio.py\n' in cmake and '    CadexFitReport.py\n' in cmake


def test_the_shells_process_entry_stays_gone():
    """ADR-529: no client runs the renderer as a child process, so it has no entry."""
    for name in ('REQUEST_SCHEMA', 'RESULT_SCHEMA', 'run_request', 'main', 'role_colours', 'display_objects'):
        assert not hasattr(CadexStudio, name), name
    text = (MODULE_DIR / 'CadexStudio.py').read_text(encoding='utf-8')
    assert 'cadex-studio-request-v1' not in text and "__name__ == '__main__'" not in text
