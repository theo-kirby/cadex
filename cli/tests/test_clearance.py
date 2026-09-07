# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import json
import pytest
from cadex_cli.__main__ import main
from cadex_cli.client import CadexdClient, open_project
from cadex_cli.clearance import pair_status, write_clearance

RIG = '''
block = part.box(10, 10, 10)
a = assembly.component(block, grounded=True)
b = assembly.component(block, placement=[9, 0, 0], grounded=True)
c = assembly.component(block, placement=[20, 0, 0], grounded=True)
asm = assembly.assembly([a, b, c])
diag = assembly.solve(asm)
result = {"block": block, "a": a, "b": b, "c": c, "asm": asm, "diag": diag}
'''


def test_real_pairs_and_threshold_changes_without_rebuild(engine, tmp_path, capsys):
    root = tmp_path / 'project'
    with CadexdClient(engine) as client:
        open_project(client, root)
        reply = client.request('write_script', {'source': RIG, 'expected_revision': ''})
        assert reply['ok'], reply
        before = (root / 'script.json').read_bytes()
        path, value = write_clearance(client, root, minimum=2)
        rows = {(r['first'], r['second']): r for r in value['pairs']}
        assert rows['a', 'b']['common_volume_mm3'] == pytest.approx(100)
        assert rows['a', 'b']['status'] == 'intersection'
        assert rows['b', 'c']['distance_mm'] == pytest.approx(1)
        assert rows['b', 'c']['status'] == 'below clearance'
        assert rows['a', 'c']['distance_mm'] == pytest.approx(10)
        assert rows['a', 'c']['status'] == 'clear'
        _, changed = write_clearance(client, root, minimum=0.5, maximum_volume=101)
        assert [r['status'] for r in changed['pairs']] == ['below clearance', 'clear', 'clear']
        assert (root / 'script.json').read_bytes() == before
        assert path.is_file()
    attempts = sorted(root.rglob('result.json'))
    assert main(['clearance', '--project', str(root), '--json']) == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope['ok'], envelope
    assert sorted(root.rglob('result.json')) == attempts
    assert 'intersection' in path.read_text()


@pytest.mark.parametrize('row', [{}, {'distance_mm': 0, 'common_volume_mm3': None},
                                 {'distance_mm': float('nan'), 'common_volume_mm3': 0}])
def test_unmeasured_pairs_are_never_clear(row):
    assert pair_status(row, 0, 0) == 'unknown'


@pytest.mark.parametrize('minimum,maximum', [(-1, 0), (0, float('inf')), (float('nan'), 0)])
def test_invalid_thresholds_refuse_before_inspection(tmp_path, minimum, maximum):
    with pytest.raises(ValueError):
        write_clearance(None, tmp_path, minimum=minimum, maximum_volume=maximum)


def test_reversed_publication_order_keeps_pair_identity(engine, tmp_path):
    root = tmp_path / 'reversed'
    with CadexdClient(engine) as client:
        open_project(client, root)
        source = RIG.replace('"a": a, "b": b, "c": c', '"c": c, "b": b, "a": a')
        reply = client.request('write_script', {'source': source, 'expected_revision': ''})
        assert reply['ok'], reply
        _, value = write_clearance(client, root, minimum=2)
        rows = {(r['first'], r['second']): r for r in value['pairs']}
        assert rows['b', 'a']['common_volume_mm3'] == pytest.approx(100)
        assert rows['c', 'b']['distance_mm'] == pytest.approx(1)
        assert rows['c', 'a']['status'] == 'clear'


def test_clearance_resolves_all_real_pager_previews(monkeypatch, tmp_path):
    from conftest import SOURCE_MODULE_DIR
    monkeypatch.syspath_prepend(str(SOURCE_MODULE_DIR))
    import CadexInspection
    rows = [{'first': f'a{i}', 'second': 'b', 'first_label': 'x' * 1400,
             'first_catalog': {'family': 'bolt', 'part_number': 'm3x12-socket'},
             'distance_mm': i, 'common_volume_mm3': 0} for i in range(60)]
    raw = {'revision': 'f' * 64, 'assembly': 'asm', 'available': True, 'pairs': rows}
    class Client:
        def request(self, op, arguments):
            assert op == 'inspect' and arguments['scope'] == 'clearance'
            return CadexInspection._bounded_page(raw, arguments)
    path, value = write_clearance(Client(), tmp_path)
    assert len(value['pairs']) == 60
    assert all(row['first_label'] == 'x' * 1400 for row in value['pairs'])
    assert 'a59' in path.read_text() and 'bolt/m3x12-socket' in path.read_text()
