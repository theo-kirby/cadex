# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The studio renderer as a separate process (ADR-445).

``CadexStudio`` is engine code that ``cadexd`` never imports: the CLI loads it
by path, and the shell -- which may import no cadex code -- runs it as a child
process with a JSON request file. These tests pin that process contract and
the two facts that make it one: the service's closure does not reach the
renderer, and the payload installs it. What the renderer draws is tested
through the CLI, in ``cli/tests/test_render.py``, ``test_look.py``,
``test_sheet.py`` and ``test_scene_palette.py``.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import sys

import CadexFitReport
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


def _reply(tmp_path):
    """A floor, a 20 mm printed body on it and a purchased pin beside it."""
    revision = 'a' * 64
    display = {}
    for name, size, z0 in (('floor', (1000, 1000, 2), -2), ('body', (20, 20, 20), 0), ('pin', (5, 5, 30), 0)):
        display[name] = {'artifact_kind': 'brep', 'placement': None, 'tessellation': _mesh(tmp_path, name, size, z0)}
        display['c_' + name] = {'artifact_kind': None, 'placement': IDENTITY, 'tessellation': None,
                                'source_output': name}
    display['c_pin']['placement'] = [1, 0, 0, 30, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    return {'ok': True, 'revision': revision, 'accepted_revision': revision, 'digest': 'd' * 64,
            'display': display}


FIT = {'failing': [{'first': 'c_floor', 'status': 'world geometry'}]}
INVENTORY = {'available': True, 'uncatalogued_sources': ['body', 'floor'],
             'appearance': {'c_pin': 'accent'}, 'palette': {'accent': '#FF0000'}}


def _request(tmp_path, kind, **extra):
    return {'schema': CadexStudio.REQUEST_SCHEMA, 'kind': kind, 'reply': _reply(tmp_path),
            'fit': FIT, 'inventory': INVENTORY, 'out_dir': str(tmp_path / 'out'), **extra}


def _run(tmp_path, request):
    path = tmp_path / 'request.json'
    path.write_text(json.dumps(request))
    done = subprocess.run([sys.executable, str(MODULE_DIR / 'CadexStudio.py'), str(path)],
                          capture_output=True, text=True, timeout=300)
    return done.returncode, json.loads(done.stdout.strip().splitlines()[-1])


def test_a_look_runs_as_a_process_and_returns_the_agents_facts(tmp_path):
    code, result = _run(tmp_path, _request(tmp_path, 'look', views=['hero']))
    assert code == 0 and result['ok'] is True and result['schema'] == CadexStudio.RESULT_SCHEMA
    facts = result['facts']
    assert facts['views'] == ['hero'] and facts['left_out_as_environment'] == ['c_floor']
    assert facts['components_drawn'] == 2 and 'accent #FF0000' in facts['colours']
    assert set(facts['measures']) == {'hardware_silhouette_share', 'sharp_outside_edge_share', 'material_count'}
    (image,) = result['files']
    assert Path(image).name == 'hero.png' and Path(image).read_bytes().startswith(PNG)


def test_the_process_look_is_the_in_process_look(tmp_path):
    """One implementation: the shell's child process and the CLI's loaded module agree."""
    _, result = _run(tmp_path, _request(tmp_path, 'look', views=['iso']))
    facts, shots = CadexStudio.look_report(_reply(tmp_path), FIT, INVENTORY, ['iso'])
    assert result['facts'] == json.loads(json.dumps(facts))
    assert Path(result['files'][0]).read_bytes() == shots[0][1]


def test_a_render_writes_the_review_set(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    code, result = _run(tmp_path, _request(tmp_path, 'render', project_root=str(root),
                                           relative_dir='review/render'))
    assert code == 0 and result['ok'] is True
    names = sorted(Path(p).name for p in result['files'])
    assert names == ['front.svg', 'hero.png', 'iso.svg', 'right.svg', 'sheet.png', 'summary.json', 'top.svg']
    summary = result['summary']
    assert summary['hero']['path'] == 'review/render/hero.png' and summary['environment'] == ['c_floor']
    assert summary['appearance']['c_pin'] == {'role': 'accent', 'color': '#FF0000', 'source': 'declared'}
    # No accepted attempt to read a mass from: the sheet says so rather than guessing.
    assert summary['sheet']['numbers']['mass_kg'] is None


def test_a_refusal_is_a_result_not_a_traceback(tmp_path):
    code, result = _run(tmp_path, _request(tmp_path, 'look', views=['sideways']))
    assert code == 1 and result['ok'] is False and 'unknown view' in result['error']
    code, result = _run(tmp_path, {**_request(tmp_path, 'look'), 'out_dir': 'relative/dir'})
    assert code == 1 and 'absolute' in result['error']
    code, result = _run(tmp_path, {**_request(tmp_path, 'render')})
    assert code == 1 and 'project_root' in result['error']
    missing = tmp_path / 'missing.json'
    done = subprocess.run([sys.executable, str(MODULE_DIR / 'CadexStudio.py'), str(missing)],
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 2 and json.loads(done.stdout)['ok'] is False


#: Raw ``inspect`` values, as the shell reads them with its paged reader.
CLEARANCE = {'available': True, 'revision': 'a' * 64, 'assembly': 'asm', 'pose': 'solved',
             'pairs': [{'first': 'c_body', 'second': 'c_pin', 'distance_mm': 0.0, 'common_volume_mm3': 5.0}],
             'world_geometry': [{'component': 'c_floor', 'reason': 'declared floor'}]}
INVENTORY_VALUE = {'assembly': 'asm', 'revision': 'a' * 64, 'palette': {'accent': '#FF0000'},
                   'components': [{'component': 'c_pin', 'source_output': 'pin', 'appearance': 'accent'},
                                  {'component': 'c_body', 'source_output': 'body'},
                                  {'component': 'c_floor', 'source_output': 'floor'}],
                   'catalog_counts': {'pin/p1': 1}, 'uncatalogued_sources': ['body', 'floor']}


def test_blocks_are_built_from_raw_values_as_the_cli_builds_them(tmp_path):
    """ADR-447: the shell sends raw values; the blocks equal the CLI's in-process ones."""
    code, result = _run(tmp_path, {'schema': CadexStudio.REQUEST_SCHEMA, 'kind': 'blocks',
                                   'clearance': CLEARANCE, 'inventory_value': INVENTORY_VALUE})
    assert code == 0 and result['ok'] is True
    assert result['fit'] == json.loads(json.dumps(CadexFitReport.fit_summary(CLEARANCE)))
    assert result['inventory'] == json.loads(json.dumps(CadexFitReport.inventory_summary(INVENTORY_VALUE)))
    assert result['fit']['verdict'] == 'fail'
    assert {row['status'] for row in result['fit']['failing']} == {'intersection', 'world geometry'}
    assert result['inventory']['appearance'] == {'c_pin': 'accent'}
    # ...with the bounded views a build reply shows the model (ADR-435).
    assert result['fit_view'] == json.loads(json.dumps(CadexFitReport.fit_view(CadexFitReport.fit_summary(CLEARANCE))))
    assert result['inventory_view']['appearance'] == {'accent': 1}


def test_a_look_from_raw_values_leaves_the_floor_out_and_returns_its_blocks(tmp_path):
    request = {**_request(tmp_path, 'look', views=['iso']), 'fit': None, 'inventory': None,
               'clearance': CLEARANCE, 'inventory_value': INVENTORY_VALUE}
    code, result = _run(tmp_path, request)
    assert code == 0 and result['facts']['left_out_as_environment'] == ['c_floor']
    assert 'accent #FF0000' in result['facts']['colours']
    assert result['fit']['verdict'] == 'fail' and result['inventory']['assembly'] == 'asm'


def test_a_malformed_raw_value_is_refused_not_raised(tmp_path):
    bad = {**CLEARANCE, 'world_geometry': [{'reason': 'a row with no component'}], 'pairs': []}
    code, result = _run(tmp_path, {'schema': CadexStudio.REQUEST_SCHEMA, 'kind': 'blocks', 'clearance': bad})
    assert code == 1 and result['error'].startswith('blocks: malformed inspect value: KeyError')


def test_the_service_never_imports_the_renderer_and_the_payload_ships_it():
    """cadexd dispatches serially; a 12 s render inside it would stall the slider drag."""
    assert not {'CadexStudio', 'CadexFitReport'} & set(_engine_closure())
    cmake = (MODULE_DIR / 'CMakeLists.txt').read_text(encoding='utf-8')
    assert '    CadexStudio.py\n' in cmake and '    CadexFitReport.py\n' in cmake
