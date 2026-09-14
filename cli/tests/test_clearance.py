# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import json
import pytest
from cadex_cli.__main__ import main
from cadex_cli.client import CadexdClient, open_project
from cadex_cli.bridge import Bridge
from cadex_cli.clearance import (
    bounds_agreement, fit_summary, pair_status, write_clearance,
)

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


def test_a_script_that_prints_no_overlap_gets_the_overlap_in_its_reply(engine, tmp_path):
    """The transaction F1 names (ADR-346): stdout is a claim, `fit` the evidence.

    Blocks a and b share 100 mm³ and the script says they do not. Through the
    bridge the model is handed both, and the fit block is computed from the
    published measurements -- the same rows `cadex clearance` reports --
    never from what the script printed.
    """
    root = tmp_path / 'printed'
    lying = RIG.replace('diag = assembly.solve(asm)',
                        'diag = assembly.solve(asm)\nprint("fit check: no overlap")')
    with CadexdClient(engine) as client:
        open_project(client, root)
        with Bridge(client, initial_revision='') as bridge:
            reply = bridge.call('write_script', {'source': lying})
            (call,) = bridge.state.calls
        assert reply['is_error'] is False
        payload = json.loads(reply['content'][0]['text'])
        assert payload['ok'] is True
        assert 'fit check: no overlap' in payload['stdout']
        fit = payload['fit']
        assert fit['verdict'] == 'fail'
        assert fit['pairs_checked'] == 3 and fit['failing_count'] == 1
        assert fit['counts'] == {'clear': 2, 'intersection': 1, 'below clearance': 0, 'unknown': 0}
        (failing,) = fit['failing']
        assert (failing['first'], failing['second']) == ('a', 'b')
        assert failing['status'] == 'intersection'
        assert failing['common_volume_mm3'] == pytest.approx(100)
        assert failing['distance_mm'] == pytest.approx(0)
        assert fit['revision'] == payload['accepted_revision']
        assert fit['assembly'] == 'asm'
        assert call.fit == fit
        # The same numbers `cadex clearance` writes, because they are the
        # same published rows.
        _, value = write_clearance(client, root)
        rows = {(r['first'], r['second']): r for r in value['pairs']}
        assert rows['a', 'b']['common_volume_mm3'] == pytest.approx(failing['common_volume_mm3'])
        assert fit_summary(value)['failing'] == fit['failing']


def test_fit_summary_counts_an_unmeasured_pair_as_failing():
    value = {'available': True, 'revision': 'r', 'assembly': 'asm', 'pose': 'p', 'pairs': [
        {'first': 'a', 'second': 'b', 'distance_mm': None, 'common_volume_mm3': None,
         'error': 'Assembly solver did not produce a solved pose'},
        {'first': 'a', 'second': 'c', 'distance_mm': 0.05, 'common_volume_mm3': 0.0},
        {'first': 'b', 'second': 'c', 'distance_mm': 3.0, 'common_volume_mm3': 0.0},
    ]}
    fit = fit_summary(value)
    assert fit['verdict'] == 'fail'
    assert fit['counts'] == {'clear': 1, 'intersection': 0, 'below clearance': 1, 'unknown': 1}
    assert [(f['first'], f['second'], f['status']) for f in fit['failing']] == [
        ('a', 'b', 'unknown'), ('a', 'c', 'below clearance')]
    assert fit['failing'][0]['error'].startswith('Assembly solver')
    assert fit['thresholds'] == {'minimum_clearance_mm': 0.1, 'maximum_common_volume_mm3': 1e-6}
    assert fit_summary(value, minimum=0.01)['counts']['below clearance'] == 0


def test_fit_summary_names_every_failing_pair_however_many_there_are():
    """The charter asks for every failing pair in the reply, not the first N.

    Ninety pairs, sixty of them failing -- thirty intersections and thirty
    below the minimum -- each with its own distance and volume: every one
    comes back by name with its own numbers, in measurement order, and
    nothing in the block says "truncated" or points elsewhere.
    """

    pairs = []
    for i in range(90):
        kind = i % 3  # 0: intersection, 1: below clearance, 2: clear
        pairs.append({
            'first': f'p{i}', 'second': f'q{i}',
            'distance_mm': (0.0, 0.001 * (i + 1), 5.0 + i)[kind],
            'common_volume_mm3': 0.5 + i if kind == 0 else 0.0,
        })
    expected = [(r['first'], r['second'], r['distance_mm'], r['common_volume_mm3'])
                for i, r in enumerate(pairs) if i % 3 != 2]
    assert len(expected) == 60
    fit = fit_summary({'available': True, 'pairs': pairs})
    assert fit['verdict'] == 'fail'
    assert fit['pairs_checked'] == 90 and fit['failing_count'] == 60
    assert fit['counts'] == {'clear': 30, 'intersection': 30, 'below clearance': 30, 'unknown': 0}
    assert [(f['first'], f['second'], f['distance_mm'], f['common_volume_mm3'])
            for f in fit['failing']] == expected
    assert 'failing_truncated' not in fit and 'note' not in fit


@pytest.mark.parametrize('late_read_failure', [False, True])
def test_build_reply_resolves_late_fit_pages_or_reports_unavailable(
    monkeypatch, protocol, late_read_failure,
):
    """A clear first page cannot conceal failures or an unreadable later page."""
    from types import SimpleNamespace
    from conftest import SOURCE_MODULE_DIR
    monkeypatch.syspath_prepend(str(SOURCE_MODULE_DIR))
    from CadexInspection import _bounded_page

    pairs = [{'first': 'base', 'second': f'link{i}', 'distance_mm': 2.0,
              'common_volume_mm3': 0.0} for i in range(60)]
    pairs[57].update(distance_mm=None, common_volume_mm3=None,
                     error='Kernel could not measure this pair')
    pairs[58].update(distance_mm=0.0, common_volume_mm3=248.2)
    pairs[59].update(distance_mm=0.2, intent={'kind': 'contact'})
    published = {'available': True, 'revision': 'accepted', 'assembly': 'asm',
                 'pairs': pairs, 'world_geometry': [
                     {'component': 'environment', 'reason': 'declared world geometry'}]}
    requests = []

    class Client:
        engine = SimpleNamespace(protocol=protocol)

        def request(self, op, arguments):
            requests.append((op, dict(arguments)))
            if op == 'write_script':
                return {'ok': True, 'accepted_revision': 'accepted',
                        'model_state': {'next_write_expected_revision': 'accepted'},
                        'stdout': 'all parts fit'}
            assert op == 'inspect' and arguments['scope'] == 'clearance'
            if (late_read_failure and arguments['path'] == '/pairs'
                    and arguments['offset'] > 0):
                return {'ok': False, 'error': 'late measurement page unreadable'}
            return _bounded_page(published, arguments)

    bridge = Bridge(Client(), initial_revision='before')
    reply = bridge.call('write_script', {'source': 'fixture'})
    payload = json.loads(reply['content'][0]['text'])
    assert not reply['is_error'] and payload['ok']
    assert payload['accepted_revision'] == bridge.state.revision == 'accepted'
    assert payload['stdout'] == 'all parts fit'
    assert any(args.get('path') == '/pairs' and args.get('offset', 0) > 0
               for op, args in requests if op == 'inspect')
    assert [op for op, _ in requests].count('write_script') == 1
    fit = payload['fit']
    assert bridge.state.last_fit == bridge.state.calls[0].fit == fit
    if late_read_failure:
        assert fit['verdict'] == 'unavailable'
        assert 'late measurement page unreadable' in fit['error']
        assert fit['pairs_checked'] == 0
    else:
        assert fit['verdict'] == 'fail' and fit['pairs_checked'] == 60
        assert fit['counts'] == {'clear': 57, 'intersection': 1, 'below clearance': 0,
                                 'unknown': 1, 'missed contact': 1, 'world geometry': 1}
        assert fit['failing_count'] == 4
        assert [(f['first'], f['second'], f['status']) for f in fit['failing']] == [
            ('base', 'link57', 'unknown'), ('base', 'link58', 'intersection'),
            ('base', 'link59', 'missed contact'), ('environment', '', 'world geometry')]
        assert fit['failing'][0]['error'] == pairs[57]['error']
        assert fit['failing'][1]['common_volume_mm3'] == 248.2
        assert fit['failing'][2]['distance_mm'] == 0.2
        assert fit['failing'][2]['intent'] == {'kind': 'contact'}


def test_the_prose_report_prints_the_fit_and_each_failing_pair():
    from cadex_cli.report import RunReport, human_lines
    report = RunReport(project_root='/p', fit=fit_summary({'available': True, 'pairs': [
        {'first': 'a', 'second': 'b', 'distance_mm': 0.0, 'common_volume_mm3': 100.0},
        {'first': 'a', 'second': 'c', 'distance_mm': None, 'common_volume_mm3': None,
         'error': 'Component has no measurable shape'},
    ]}))
    lines = human_lines(report)
    assert 'fit    fail  2 failing of 2 pair(s)' in lines
    assert '  a ∩ b: intersection  distance 0 mm  common 100 mm³' in lines
    assert '  a ∩ c: unknown  distance — mm  common — mm³' in lines
    assert report.to_json()['fit']['failing_count'] == 2
    unavailable = RunReport(fit={'verdict': 'unavailable', 'error': 'store unreadable'})
    assert 'fit    unavailable: store unreadable' in human_lines(unavailable)
    assert 'fit' not in RunReport().to_json()


def test_fit_summary_without_an_assembly_is_unavailable_not_passing():
    fit = fit_summary({'available': False, 'pairs': [], 'revision': 'r', 'assembly': ''})
    assert fit['verdict'] == 'unavailable' and fit['pairs_checked'] == 0
    assert fit_summary(None)['verdict'] == 'unavailable'


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


def _box(lo, hi):
    return {'bounds_mm': [list(lo), list(hi)]}


def _pair(distance, volume, status='clear'):
    return {'first': 'a', 'second': 'b', 'distance_mm': distance,
            'common_volume_mm3': volume, 'status': status}


DISJOINT = {'a': _box((0, 0, 0), (10, 10, 10)), 'b': _box((50, 0, 0), (60, 10, 10))}
OVERLAP = {'a': _box((0, 0, 0), (10, 10, 10)), 'b': _box((8, 0, 0), (18, 10, 10))}


def test_bounds_agreement_passes_on_consistent_pairs():
    """Two comparisons per pair, and a truthful report satisfies both."""
    check = bounds_agreement([_pair(40.0, 0.0)], DISJOINT)
    assert check['status'] == 'pass'
    assert (check['comparisons'], check['pairs_compared']) == (2, 1)
    assert check['failures'] == []
    overlapping = bounds_agreement([_pair(0.0, 150.0, 'intersection')], OVERLAP)
    assert overlapping['status'] == 'pass', overlapping   # ceiling is 2x10x10


def test_bounds_agreement_catches_the_origin_frame_defect():
    """The ADR-241 defect: bodies measured at the origin, so a disjoint pair
    reports an intersection and no clearance. Both comparisons must fail."""
    check = bounds_agreement([_pair(0.0, 1000.0, 'intersection')], DISJOINT)
    assert check['status'] == 'fail'
    assert check['failure_count'] == 2
    assert {failure['check'] for failure in check['failures']} == {'distance', 'volume'}
    assert check['worst_distance_excess_mm'] == pytest.approx(40.0, abs=1e-2)
    assert check['worst_volume_excess_mm3'] == pytest.approx(1000.0, abs=1e-2)


def test_bounds_agreement_catches_a_volume_larger_than_the_box_overlap():
    check = bounds_agreement([_pair(0.0, 5000.0, 'intersection')], OVERLAP)
    assert check['status'] == 'fail' and check['failure_count'] == 1
    assert check['failures'][0]['check'] == 'volume'


@pytest.mark.parametrize('pairs, objects, reason', [
    ([_pair(40.0, 0.0)], {}, 'nothing rendered'),
    ([_pair(None, None, 'unknown')], DISJOINT, 'no measurement'),
    ([_pair(40.0, 0.0)], {'a': DISJOINT['a']}, 'one side undrawn'),
])
def test_bounds_agreement_skips_what_it_cannot_compare(pairs, objects, reason):
    """Absence of a surface is never a pass and never a failure."""
    check = bounds_agreement(pairs, objects)
    assert check['status'] == 'unavailable', reason
    assert check['comparisons'] == 0 and not check['failures']


@pytest.mark.parametrize('tolerance', [float('nan'), float('inf'), -1.0])
def test_bounds_agreement_refuses_an_unusable_tolerance(tolerance):
    with pytest.raises(ValueError):
        bounds_agreement([_pair(40.0, 0.0)], DISJOINT, tolerance_mm=tolerance)


def test_bounds_agreement_tolerates_tessellation_resolution():
    """f32 bounds at ~100 mm disagree by ~1e-5 mm; that is not a defect."""
    check = bounds_agreement([_pair(40.0 - 3.05e-6, 0.0)], DISJOINT)
    assert check['status'] == 'pass'


def test_fit_intent_survives_acceptance_and_reopen(engine, tmp_path):
    source = RIG.replace('placement=[9, 0, 0]', 'placement=[10.2, 0, 0]').replace(
        'asm = assembly.assembly([a, b, c])',
        'asm = assembly.assembly([a, b, c], contacts=[(a, b)], clearances=[(b, c, 0.5)])')
    source = source.replace('grounded=True)', 'grounded=True, world=True)', 1)
    root = tmp_path / 'intent'
    with CadexdClient(engine) as client:
        open_project(client, root)
        with Bridge(client, initial_revision='') as bridge:
            reply = bridge.call('write_script', {'source': source})
        payload = json.loads(reply['content'][0]['text'])
        assert payload['ok'], payload
        fit = payload['fit']
        assert fit['verdict'] == 'fail'
        failures = {(r['first'], r['second']): r for r in fit['failing']}
        assert failures['a', 'b']['status'] == 'missed contact'
        assert failures['a', 'b']['distance_mm'] == pytest.approx(0.2)
        assert failures['b', 'c']['status'] == 'intersection'
        assert failures['a', '']['status'] == 'world geometry'
    before = json.loads((root / 'script.json').read_text())
    with CadexdClient(engine) as client:
        open_project(client, root)
        path, value = write_clearance(client, root)
        assert 'contact within 0.001 mm' in path.read_text()
        assert 'declared minimum 0.5 mm' in path.read_text()
        assert fit_summary(value) == fit
    after = json.loads((root / 'script.json').read_text())
    for key in ('accepted_revision', 'accepted_digest', 'accepted_attempt'):
        assert after[key] == before[key]


@pytest.mark.parametrize('status', ['complete', 'incomplete', None])
def test_sweep_report_reads_every_paged_fact_without_rebuilding(tmp_path, monkeypatch, status):
    from conftest import SOURCE_MODULE_DIR
    monkeypatch.syspath_prepend(str(SOURCE_MODULE_DIR))
    from CadexInspection import _bounded_page
    sweep = {'status': status, 'step_degrees': 5, 'step_mm': 0.5, 'elapsed_seconds': 2.5,
             'joints': [{'joint': 'hinge', 'kind': 'revolute', 'unit': 'degrees', 'step': 5,
                         'status': status, 'elapsed_seconds': 2.4,
                         'reason': 'pose budget exceeded' if status == 'incomplete' else '',
                         'pairs': [{'first': 'base', 'second': f'link{i}',
                                    'minimum_distance_mm': 0, 'maximum_common_volume_mm3': i,
                                    'first_contact_degrees': 30} for i in range(60)]},
                        {'joint': 'slide', 'kind': 'slider', 'unit': 'mm', 'step': 0.5,
                         'status': 'complete', 'elapsed_seconds': 0.1, 'range_mm': [-4, 10],
                         'initial_mm': 8, 'pairs': [{'first': 'base', 'second': 'rod',
                                    'minimum_distance_mm': 0, 'maximum_common_volume_mm3': 3.4,
                                    'first_contact_mm': -2}]}]}
    published = {'revision': 'accepted', 'assembly': 'asm', 'pairs': []}
    if status:
        published['clearance_sweep'] = sweep

    class Client:
        def request(self, op, arguments):
            assert op == 'inspect' and arguments['scope'] == 'clearance'
            return _bounded_page(published, arguments)

    path, value = write_clearance(Client(), tmp_path, sweep=True)
    rendered = json.loads(path.read_text().split('```json\n')[1].split('\n```')[0])
    assert path.name == 'clearance-sweep.md'
    if status:
        assert rendered == sweep == value['clearance_sweep']
    else:
        assert rendered['status'] == 'unavailable'
    assert 'not that fit passes' in path.read_text()
    assert '`first_contact_mm` are in mm' in path.read_text()


def test_sweep_command_on_legacy_project_keeps_accepted_identity(engine, tmp_path, capsys):
    root = tmp_path / 'project'
    with CadexdClient(engine) as client:
        open_project(client, root)
        assert client.request('write_script', {'source': RIG, 'expected_revision': ''})['ok']
    before = (root / 'script.json').read_bytes()
    attempts = {p: p.read_bytes() for p in root.rglob('result.json')}
    assert main(['clearance', '--sweep', '--project', str(root), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['ok']
    assert 'Coverage: unavailable' in (root / 'docs/clearance-sweep.md').read_text()
    assert (root / 'script.json').read_bytes() == before
    assert {p: p.read_bytes() for p in root.rglob('result.json')} == attempts


@pytest.mark.parametrize('declared', [False, True])
@pytest.mark.parametrize('gap,failed', [
    (0.1, False), (0.09999999999999952, False),
    (0.09999999999999039, False), (0.1 - 5e-10, False),
    (0.1 - 2e-9, True), (0.0999, True), (0.05, True),
])
def test_minimum_noise_static_and_swept_reports(tmp_path, declared, gap, failed):
    import copy
    row = {'first': 'a', 'second': 'b', 'distance_mm': gap, 'common_volume_mm3': 0.0}
    if declared:
        row['intent'] = {'kind': 'clearance', 'minimum_mm': 0.1}
    sweep = {'status': 'complete', 'joints': [{'joint': 'slide', 'status': 'complete',
             'pairs': [{'first': 'a', 'second': 'b', 'minimum_distance_mm': gap,
                        'maximum_common_volume_mm3': 0.0, 'first_contact_mm': None}]}]}
    published = {'revision': 'accepted', 'assembly': 'asm', 'available': True,
                 'pairs': [row], 'clearance_sweep': sweep}
    class Client:
        def request(self, op, arguments):
            return {'ok': True, 'value': copy.deepcopy(published)}
    # A declared minimum overrides the caller's stricter default.
    minimum = 0.5 if declared else 0.1
    assert fit_summary(published, minimum=minimum)['failing_count'] == int(failed)
    path, value = write_clearance(Client(), tmp_path, minimum=minimum)
    assert value['pairs'][0]['status'] == ('below clearance' if failed else 'clear')
    assert value['pairs'][0]['distance_mm'] == gap
    assert '1e-09 mm' in path.read_text()
    path, value = write_clearance(Client(), tmp_path, minimum=minimum, sweep=True)
    rendered = json.loads(path.read_text().split('```json\n')[1].split('\n```')[0])
    assert rendered == sweep == value['clearance_sweep']
    assert published['pairs'][0] == row


def test_override_minimum_uses_absolute_not_relative_slack():
    row = {'distance_mm': 0.4999999999999995, 'common_volume_mm3': 0.0}
    assert pair_status(row, 0.5, 1e-6) == 'clear'
    assert pair_status(dict(row, distance_mm=0.4999), 0.5, 1e-6) == 'below clearance'
    # A large threshold must not enlarge the allowance through relative isclose.
    assert pair_status(dict(row, distance_mm=1e6 - 1e-4), 1e6, 1e-6) == 'below clearance'
