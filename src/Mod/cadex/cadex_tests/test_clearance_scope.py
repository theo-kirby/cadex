# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import json
from types import SimpleNamespace

from CadexInspection import capture_inspection, complete_inspection
from cadex_assembly_worker import _measure_clearance
from cadex_project_worker import compute_project_digest
from test_inventory_scope import _store, _service, _component_output


def test_measurement_failure_keeps_every_pair_unknown():
    components = {name: SimpleNamespace() for name in ('a', 'b', 'c')}
    rows = _measure_clearance(components)
    assert [(r['first'], r['second']) for r in rows] == [('a', 'b'), ('a', 'c'), ('b', 'c')]
    assert all(r['distance_mm'] is None and r['common_volume_mm3'] is None and r['error'] for r in rows)


def test_measurements_do_not_move_the_content_digest(tmp_path):
    output = {'name': 'asm', 'domain': 'assembly', 'type': 'assembly', 'definition': {'operation': 'assembly'}}
    before = compute_project_digest(tmp_path, [output])
    output['clearance'] = [{'first': 'a', 'second': 'b', 'distance_mm': 1.0, 'common_volume_mm3': 0.0}]
    assert compute_project_digest(tmp_path, [output]) == before
    output['clearance'][0]['distance_mm'] = 2.0
    assert compute_project_digest(tmp_path, [output]) == before


def test_legacy_assembly_has_unknown_pairs_and_catalog_labels(tmp_path):
    root = _store(tmp_path, {'ok': True, 'outputs': [
        {'name': 'asm', 'type': 'assembly'},
        {'name': 'bolt', 'catalog': {'family': 'bolt', 'part_number': 'm3x12-socket'}},
        _component_output('a', 'bolt', position=[0, 0, 0]),
        _component_output('b', 'bolt', position=[0, 0, 1]),
    ]})
    captured = capture_inspection(_service(root), {'scope': 'clearance'})
    result = complete_inspection(captured)
    assert result['ok'], json.dumps(result)
    value = result['value']
    assert value['available'] is False
    row, = value['pairs']
    assert row['distance_mm'] is None and row['common_volume_mm3'] is None
    assert row['first_label'] == 'a label'
    assert row['first_catalog']['part_number'] == 'm3x12-socket'


def test_no_assembly_is_unavailable(tmp_path):
    root = _store(tmp_path, {'ok': True, 'outputs': []})
    result = complete_inspection(capture_inspection(_service(root), {'scope': 'clearance'}))
    assert result['ok'], json.dumps(result)
    assert result['value']['available'] is False
    assert result['value']['pairs'] == []


def test_unsolved_assembly_does_not_claim_a_solved_pose():
    rows = _measure_clearance({'a': object(), 'b': object()}, solved=False)
    assert rows[0]['distance_mm'] is None
    assert 'solved pose' in rows[0]['error']
