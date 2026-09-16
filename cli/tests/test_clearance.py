# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
import json
import pytest
from cadex_cli.__main__ import main
from cadex_cli.client import CadexdClient, open_project
from cadex_cli.bridge import Bridge, _sweep_line
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
            assert op == 'inspect'
            if arguments['scope'] == 'inventory':
                return _bounded_page({'revision': 'accepted', 'assembly': 'asm',
                                      'components': [], 'catalog_counts': {},
                                      'uncatalogued_sources': []}, arguments)
            assert arguments['scope'] == 'clearance'
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
    # The swept half prints beside it, with the joint each overlap is
    # through and the reason for every joint that was not swept (ADR-366).
    assert 'sweep  unavailable: No published sweep for this accepted revision.' in lines
    swept = RunReport(project_root='/p', fit=fit_summary({
        'available': True, 'pairs': [], 'clearance_sweep': {
            'status': 'incomplete', 'joints': [
                {'joint': 'knee', 'kind': 'revolute', 'unit': 'degrees',
                 'status': 'complete', 'pairs': [
                     {'first': 'thigh', 'second': 'shin',
                      'minimum_distance_mm': 0.0,
                      'maximum_common_volume_mm3': 42.5,
                      'first_contact_degrees': -55.0}]},
                {'joint': 'rail', 'kind': 'slider', 'unit': 'mm',
                 'status': 'incomplete', 'reason': 'sweep_step_mm is not declared'}]}}))
    printed = human_lines(swept)
    assert 'sweep  fail  1 of 2 joint(s) swept  1 failing pair(s)' in printed
    assert '  rail unswept: sweep_step_mm is not declared' in printed
    assert ('  thigh ∩ shin through knee: intersection  '
            'min 0 mm  max common 42.5 mm³') in printed
    assert swept.to_json()['fit']['sweep']['failing_count'] == 1


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
    assert 'A joint reported `skipped` is suppressed' in path.read_text()


def test_sweep_report_says_complete_coverage_of_suppressed_joints_is_not_a_sweep(
        tmp_path, monkeypatch):
    """Complete coverage of joints that were all suppressed is not a mechanism
    that was swept, and the written report has to say so in the same words the
    build reply's block does (ADR-371)."""

    from conftest import SOURCE_MODULE_DIR
    monkeypatch.syspath_prepend(str(SOURCE_MODULE_DIR))
    from CadexInspection import _bounded_page
    published = {'revision': 'accepted', 'assembly': 'asm', 'pairs': [],
                 'clearance_sweep': {'status': 'complete', 'joints': [
                     {'joint': 'knee', 'kind': 'revolute', 'unit': 'degrees',
                      'status': 'skipped', 'reason': 'the assembly suppresses this '
                      'revolute joint, so the solver ignores it and it holds no '
                      'range to sweep'}]}}

    class Client:
        def request(self, op, arguments):
            return _bounded_page(published, arguments)

    path, _ = write_clearance(Client(), tmp_path, sweep=True)
    text = path.read_text()
    assert 'Coverage: complete. Every limited joint the accepted assembly '\
           'declares is suppressed' in text
    assert 'holds no range to sweep' in text


def test_sweep_command_on_legacy_project_keeps_accepted_identity(engine, tmp_path, capsys):
    root = tmp_path / 'project'
    with CadexdClient(engine) as client:
        open_project(client, root)
        assert client.request('write_script', {'source': RIG, 'expected_revision': ''})['ok']
    before = (root / 'script.json').read_bytes()
    attempts = {p: p.read_bytes() for p in root.rglob('result.json')}
    assert main(['clearance', '--sweep', '--project', str(root), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['ok']
    # RIG has no joint at all, so since ADR-367 the engine publishes complete
    # coverage of an empty set. The report must not let that read as a swept
    # mechanism: it says which of the two it is, in the coverage line.
    report = (root / 'docs/clearance-sweep.md').read_text()
    assert 'Coverage: complete. The accepted assembly declares no limited joint' in report
    assert 'angle_limits_degrees or length_limits_mm for a swept check to exist.' in report
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


HINGE = '''
plate = part.box(40, 20, 4)
arm = part.box(30, 6, 6)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[12, 0, 20]),
                   assembly.connector(swing, "origin"),
                   angle_limits_degrees=[0, 10])
asm = assembly.assembly([base, swing], [j]%s)
diag = assembly.solve(asm)
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag}
'''


@pytest.mark.parametrize('step,verdict', [
    (', sweep_step_degrees=5', 'pass'), ('', 'incomplete'),
])
def test_build_reply_carries_the_published_joint_sweep(
    engine, tmp_path, step, verdict,
):
    """The blind spot ot7's F5 create turn measured (ADR-366).

    That turn accepted an arm whose two hinges declared limits and whose
    assembly declared no step, so nothing was swept -- and the reply said
    nothing about it, because the fit block was the solved pose only. Here
    the same design shape is built both ways against the real engine: the
    static verdict passes either way, and the reply's `fit.sweep` is the
    difference between a measured range and a joint checked at one pose.
    """

    root = tmp_path / ('swept' if step else 'unswept')
    with CadexdClient(engine) as client:
        open_project(client, root)
        with Bridge(client, initial_revision='') as bridge:
            reply = bridge.call('write_script', {'source': HINGE % step})
            (call,) = bridge.state.calls
        payload = json.loads(reply['content'][0]['text'])
        assert payload['ok'] is True, payload
        fit = payload['fit']
        # Static fit passes in both builds: the arm clears the plate by
        # 16 mm at the solved pose, which is exactly why the swept half has
        # to speak for itself.
        assert (fit['verdict'], fit['failing_count']) == ('pass', 0)
        sweep = fit['sweep']
        assert sweep['verdict'] == verdict
        assert sweep['failing_count'] == 0 and sweep['failing'] == []
        if step:
            assert sweep['coverage'] == 'complete' and sweep['step_degrees'] == 5
            assert (sweep['joints_checked'], sweep['joints_complete']) == (1, 1)
            (joint,) = sweep['joints']
            assert (joint['joint'], joint['kind'], joint['unit']) == (
                'j', 'revolute', 'degrees')
            assert joint['range_degrees'] == [0, 10] and joint['sample_count'] == 3
            assert joint['minimum_distance_mm'] == pytest.approx(16, abs=1e-6)
            assert joint['maximum_common_volume_mm3'] == 0
            assert 'first_contact' not in joint and 'note' not in sweep
        else:
            # The F5 shape exactly: a limited hinge and no declared step.
            # Since ADR-367 the engine still publishes coverage, so the reply
            # names *which* joint went unchecked and why, rather than only
            # that a sweep is absent.
            assert sweep['coverage'] == 'incomplete'
            assert (sweep['joints_checked'], sweep['joints_complete']) == (1, 0)
            (joint,) = sweep['joints']
            assert (joint['joint'], joint['kind'], joint['status']) == (
                'j', 'revolute', 'incomplete')
            assert 'sweep_step_degrees is not declared' in joint['reason']
            assert joint['pairs_measured'] == 0
            assert sweep['step_degrees'] is None and 'reason' not in sweep
            assert sweep['note'].startswith('Coverage means measurements exist')
            assert _sweep_line(sweep) == 'sweep incomplete: 1 of 1 joint(s) unswept'
        # The same block the progress line and the turn report read.
        assert call.fit == fit
        _, value = write_clearance(client, root, sweep=True)
        assert fit_summary(value)['sweep'] == sweep


def test_sweep_summary_names_every_pair_that_overlaps_through_the_motion():
    """Known answer: one hinge overlaps two pairs, one slider is unswept.

    `knee`'s sweep is complete and two of its three pairs interpenetrate
    somewhere in [-90, 20] degrees; `rail` is a limited slider the assembly
    declared no `sweep_step_mm` for. The block fails on the overlaps, names
    each with the joint and the angle it first touched at, and still carries
    the unswept joint's reason -- a failure never hides missing coverage.
    """

    sweep = {'status': 'incomplete', 'step_degrees': 5, 'step_mm': None,
             'joints': [
                 {'joint': 'knee', 'kind': 'revolute', 'unit': 'degrees',
                  'status': 'complete', 'step': 5, 'sample_count': 23,
                  'range_degrees': [-90, 20], 'initial_degrees': 0,
                  'elapsed_seconds': 2.5, 'pairs': [
                      {'first': 'thigh', 'second': 'shin',
                       'minimum_distance_mm': 0.0,
                       'maximum_common_volume_mm3': 42.5,
                       'first_contact_degrees': -55.0},
                      {'first': 'shin', 'second': 'foot',
                       'minimum_distance_mm': 0.0,
                       'maximum_common_volume_mm3': 0.25,
                       'first_contact_degrees': -70.0},
                      {'first': 'thigh', 'second': 'foot',
                       'minimum_distance_mm': 3.5,
                       'maximum_common_volume_mm3': 0.0,
                       'first_contact_degrees': None},
                  ]},
                 {'joint': 'rail', 'kind': 'slider', 'unit': 'mm',
                  'status': 'incomplete',
                  'reason': 'sweep_step_mm is not declared on the assembly, '
                            'so this limited slider joint was not swept'},
             ]}
    fit = fit_summary({'available': True, 'pairs': [], 'clearance_sweep': sweep})
    block = fit['sweep']
    assert block['verdict'] == 'fail' and fit['verdict'] == 'pass'
    assert (block['joints_checked'], block['joints_complete']) == (2, 1)
    assert [(f['joint'], f['first'], f['second'], f['maximum_common_volume_mm3'],
             f['first_contact_degrees']) for f in block['failing']] == [
        ('knee', 'thigh', 'shin', 42.5, -55.0),
        ('knee', 'shin', 'foot', 0.25, -70.0)]
    knee, rail = block['joints']
    assert knee['minimum_distance_mm'] == 0.0
    assert knee['maximum_common_volume_mm3'] == 42.5
    # First contact is the earliest sample any pair touched at, with the pair.
    assert knee['first_contact'] == {
        'value': -70.0, 'unit': 'degrees', 'pair': ['shin', 'foot']}
    assert knee['pairs_measured'] == 3 and knee['range_degrees'] == [-90, 20]
    assert rail['status'] == 'incomplete' and 'sweep_step_mm' in rail['reason']
    assert rail['minimum_distance_mm'] is None and rail['pairs_measured'] == 0
    assert block['note'].startswith('Coverage means measurements exist')
    # A volume under the maximum is not an overlap, and a measurement the
    # engine could not take is not a fit.
    for hole in ({'minimum_distance_mm': None, 'maximum_common_volume_mm3': None},
                 {'minimum_distance_mm': -1.0, 'maximum_common_volume_mm3': 0.0},
                 {'minimum_distance_mm': float('nan'), 'maximum_common_volume_mm3': 0.0},
                 {'minimum_distance_mm': 0.0, 'maximum_common_volume_mm3': -1e-9}):
        holed = {'status': 'complete', 'joints': [
            {'joint': 'knee', 'kind': 'revolute', 'unit': 'degrees',
             'status': 'complete', 'pairs': [
                 {'first': 'a', 'second': 'b', 'first_contact_degrees': -30.0,
                  **hole}]}]}
        only = fit_summary({'available': True, 'pairs': [],
                            'clearance_sweep': holed})['sweep']
        assert only['verdict'] == 'fail', hole
        assert only['failing'][0]['status'] == 'unknown' and only['failing'][0]['error']
        # A negative joint coordinate is an angle, not a hole in the report.
        assert only['joints'][0]['first_contact']['value'] == -30.0


def test_a_suppressed_joint_is_not_missing_coverage(tmp_path, monkeypatch):
    """Known answer: one swept hinge, one suppressed one (ADR-371).

    A suppressed joint is not an edge of the mechanism -- the solver ignores
    it -- so it has no range to sweep and nothing about it is missing. Before
    this, the engine handed it to the child anyway, the child refused it, and
    one suppressed joint held the whole block at `incomplete` with a reason
    that read as an unsupported *kind*: the agent was told to fix coverage it
    could not fix.
    """

    sweep = {'status': 'complete', 'step_degrees': 5, 'step_mm': None, 'joints': [
        {'joint': 'knee', 'kind': 'revolute', 'unit': 'degrees', 'status': 'complete',
         'step': 5, 'sample_count': 23, 'range_degrees': [-90, 20], 'initial_degrees': 0,
         'elapsed_seconds': 2.5, 'pairs': [
             {'first': 'thigh', 'second': 'shin', 'minimum_distance_mm': 3.5,
              'maximum_common_volume_mm3': 0.0, 'first_contact_degrees': None}]},
        {'joint': 'spare', 'kind': 'revolute', 'unit': 'degrees', 'status': 'skipped',
         'reason': 'the assembly suppresses this revolute joint, so the solver '
                   'ignores it and it holds no range to sweep'},
    ]}
    block = fit_summary({'available': True, 'revision': 'r', 'assembly': 'asm',
                         'pairs': [], 'clearance_sweep': sweep})['sweep']
    assert block['verdict'] == 'pass'
    assert (block['joints_checked'], block['joints_complete'],
            block['joints_skipped']) == (2, 1, 1)
    # A pass says what it swept and what it did not judge, and says neither in
    # the other's words.
    assert _sweep_line(block) == 'sweep pass: 1 joint(s) swept; 1 suppressed'
    assert 'note' not in block and 'reason' not in block
    assert block['joints'][1]['status'] == 'skipped'
    assert 'suppresses this revolute joint' in block['joints'][1]['reason']
    # An unswept joint beside them is still missing coverage, and the counts
    # keep the two apart.
    holed = {'status': 'incomplete', 'joints': sweep['joints'] + [
        {'joint': 'rail', 'kind': 'slider', 'unit': 'mm', 'status': 'incomplete',
         'reason': 'sweep_step_mm is not declared on the assembly, so this '
                   'limited slider joint was not swept'}]}
    mixed = fit_summary({'available': True, 'pairs': [], 'clearance_sweep': holed})['sweep']
    assert mixed['verdict'] == 'incomplete'
    assert (mixed['joints_checked'], mixed['joints_complete'],
            mixed['joints_skipped']) == (3, 1, 1)
    assert _sweep_line(mixed) == 'sweep incomplete: 1 of 2 joint(s) unswept; 1 suppressed'


@pytest.mark.parametrize('published,verdict,reason,coverage,line', [
    (None, 'unavailable', 'No published sweep for this accepted revision.',
     'unavailable', 'sweep unavailable: no published sweep'),
    ({'status': 'unavailable', 'joints': [], 'reason': 'declare the steps'},
     'unavailable', 'declare the steps',
     'unavailable', 'sweep unavailable: no published sweep'),
    ({'status': 'complete', 'joints': []}, 'unavailable',
     'The accepted assembly declares no limited joint',
     'complete', 'sweep unavailable: no limited joint'),
    # Rows, and still nothing judged: every limited joint is suppressed
    # (ADR-371). That is not the same statement as declaring none, so it does
    # not borrow that one's words, and it is not a pass either.
    ({'status': 'complete', 'joints': [
        {'joint': 'knee', 'kind': 'revolute', 'unit': 'degrees', 'status': 'skipped',
         'reason': 'the assembly suppresses this revolute joint, so the solver '
                   'ignores it and it holds no range to sweep'}]},
     'unavailable', 'Every limited joint the accepted assembly declares is suppressed',
     'complete', 'sweep unavailable: every limited joint suppressed (1)'),
])
def test_a_sweep_with_nothing_measured_is_never_a_pass(
        published, verdict, reason, coverage, line):
    value = {'available': True, 'revision': 'r', 'assembly': 'asm', 'pairs': [
        {'first': 'a', 'second': 'b', 'distance_mm': 5.0, 'common_volume_mm3': 0.0}]}
    if published is not None:
        value['clearance_sweep'] = published
    fit = fit_summary(value)
    assert fit['verdict'] == 'pass'  # the solved pose is clear and stays so
    assert fit['sweep']['verdict'] == verdict
    assert reason in fit['sweep']['reason']
    # Nothing measured either way: the suppressed case has a row and still
    # judges no joint, so `joints_skipped` is what accounts for it.
    assert fit['sweep']['failing'] == []
    rows = (published or {}).get('joints') or []
    assert len(fit['sweep']['joints']) == len(rows)
    assert fit['sweep']['joints_skipped'] == len(rows)
    assert all(row['pairs_measured'] == 0 for row in fit['sweep']['joints'])
    assert fit['sweep']['note'].startswith('Coverage means measurements exist')
    # The two facts that share this verdict do not share a phrase (ADR-368):
    # `coverage` is what tells a revision an older engine accepted apart from
    # a current one with nothing that moves within a range.
    assert fit['sweep']['coverage'] == coverage
    assert _sweep_line(fit['sweep']) == line


WELD_RIG = '''
block = part.box(10, 10, 10)
a = assembly.component(block, grounded=True)
b = assembly.component(block, placement=[11.2, 0, 0])
c = assembly.component(block, placement=[30, 0, 0])
weld_gap = assembly.joint(
    "fixed",
    assembly.connector(a, "origin"),
    assembly.connector(b, "origin", offset={"position": [11.2, 0, 0]}),
    label="weld_gap")
weld_touching = assembly.joint(
    "fixed",
    assembly.connector(a, "origin"),
    assembly.connector(c, "origin", offset={"position": [-10.0, 0, 0]}),
    label="weld_touching")
asm = assembly.assembly([a, b, c], [weld_gap, weld_touching],
                        contacts=[(a, c)], clearances=[(a, b, 0.5)])
diag = assembly.solve(asm)
print("every part fits: nothing overlaps and every clearance is met")
result = {"block": block, "a": a, "b": b, "c": c, "asm": asm, "diag": diag,
          "weld_gap": weld_gap, "weld_touching": weld_touching}
'''


def test_a_weld_holding_nothing_is_reported_while_every_fit_check_passes(engine, tmp_path):
    """Heron's third ot6 defect, as its own design declared it (ADR-370).

    A pair welded rigidly together, declared a clearance and measured apart:
    the declaration is met, so all four fit checks pass and the script prints
    that everything fits — and the reply still carries the gap under the weld
    with the joint that asserts it, which is where that defect is nameable.
    ADR-379 briefly failed this pair for the declaration itself; ADR-380
    withdrew that, because a weld fixes a pose without requiring contact.
    """

    root = tmp_path / 'weld'
    with CadexdClient(engine) as client:
        open_project(client, root)
        with Bridge(client, initial_revision='') as bridge:
            reply = bridge.call('write_script', {'source': WELD_RIG})
        payload = json.loads(reply['content'][0]['text'])
        assert payload['ok'], payload
        fit = payload['fit']
        # Rigidly separated by 1.2 mm and declared to stay 0.5 mm clear: the
        # pair satisfies what it declared and fails nothing (ADR-380).
        assert fit['verdict'] == 'pass' and fit['failing'] == []
        attachments = fit['attachments']
        assert attachments['verdict'] == 'reported'
        assert attachments['pairs_checked'] == 2 and attachments['reported_count'] == 1
        gap, = attachments['reported']
        assert (gap['first'], gap['second']) == ('a', 'b')
        assert gap['status'] == 'not touching'
        assert gap['joints'] == ['weld_gap']
        assert gap['distance_mm'] == pytest.approx(1.2)
        assert 'never a fit failure' in attachments['note']
        assert 'fixed joint' in attachments['source']
        path, value = write_clearance(client, root)
        report = path.read_text()
        assert 'Fixed-joint attachments: 2 pair(s) measured, 1 not touching' in report
        assert 'weld_gap): not touching, 1.2' in report.replace('1.1999999999999993', '1.2')
        # Both facts about the pair are published, and the detail cell joins
        # them: rigidly held by this joint, and declared to run 0.5 mm clear.
        assert '| clear |' in report
        assert 'declared minimum 0.5 mm, and welded by weld_gap' in report
        pair, = [r for r in value['pairs'] if {r['first'], r['second']} == {'a', 'b'}]
        assert pair['intent'] == {'kind': 'clearance', 'minimum_mm': 0.5,
                                  'joints': ['weld_gap']}
        assert pair['fit_failures'] == []
        assert fit_summary(value)['attachments'] == attachments
        assert fit_summary(value)['failing'] == fit['failing']


def test_an_assembly_with_no_weld_and_a_revision_without_the_report_say_so():
    """Absence of a fixed joint and absence of the report are different facts."""

    from cadex_cli.clearance import attachment_summary
    pairs = [{'first': 'a', 'second': 'b', 'distance_mm': 1.0, 'common_volume_mm3': 0.0}]
    none = attachment_summary({'available': True, 'pairs': pairs, 'attachments': []})
    assert none['verdict'] == 'none' and none['pairs_checked'] == 0
    assert 'no unsuppressed fixed joint' in none['reason']
    legacy = attachment_summary({'available': True, 'pairs': pairs})
    assert legacy['verdict'] == 'unavailable'
    assert 'accepted by an engine that measured no fixed-joint pair' in legacy['reason']
    assert legacy['reported'] == [] and legacy['reported_count'] == 0
    assert fit_summary({'available': True, 'pairs': pairs})['attachments'] == legacy
    touching = attachment_summary({'attachments': [
        {'first': 'a', 'second': 'b', 'joints': ['w'], 'status': 'touching',
         'distance_mm': 0.0, 'common_volume_mm3': 0.0}]})
    assert touching['verdict'] == 'touching' and touching['reported'] == []
    assert 'note' not in touching
    unknown = attachment_summary({'attachments': [
        {'first': 'a', 'second': 'b', 'joints': ['w'], 'status': 'unknown',
         'distance_mm': None, 'common_volume_mm3': None, 'reason': 'unmeasured pair'}]})
    assert unknown['verdict'] == 'unknown' and unknown['reported_count'] == 1


@pytest.mark.parametrize('attachments,phrase', [
    (None, ''),
    ({'pairs_checked': 0, 'reported_count': 0}, ''),
    ({'pairs_checked': 12, 'reported_count': 2}, '  welded: 2 of 12 pair(s) not touching'),
])
def test_the_progress_line_says_what_the_welds_hold(attachments, phrase):
    from cadex_cli.bridge import _fit_line
    fit = {'verdict': 'pass', 'failing_count': 0, 'pairs_checked': 105}
    if attachments is not None:
        fit['attachments'] = attachments
    assert _fit_line(fit) == 'fit pass: 0 failing of 105 pair(s)' + phrase


FLUSH_RIG = '''
block = part.box(10, 10, 10)
a = assembly.component(block, grounded=True)
b = assembly.component(block, placement=[10, 0, 0])
joints = [assembly.joint(
    "fixed",
    assembly.connector(a, "origin"),
    assembly.connector(b, "origin", offset={"position": [-10.0, 0, 0]}),
    label="fix_ab")] if WELDED else []
asm = assembly.assembly([a, b], joints)
diag = assembly.solve(asm)
result = {"block": block, "a": a, "b": b, "asm": asm, "diag": diag}
if joints:
    result["fix_ab"] = joints[0]
'''


def test_a_welded_pair_mounted_flush_is_not_a_failing_fit_check(engine, tmp_path):
    """Finch's 32 ot6 "below clearance" rows, in miniature (ADR-372).

    Two components an unsuppressed fixed joint welds together, mounted face
    to face and declaring nothing: before this the default 0.1 mm undeclared
    gap failed them at 0.0 mm for doing what the joint asked, and the only
    escape was a `contacts=` declaration repeating the weld. The same rig
    without the joint still fails, which is what says the joint is the
    difference and not the distance.
    """

    reports = {}
    for welded in (True, False):
        root = tmp_path / ('welded' if welded else 'loose')
        with CadexdClient(engine) as client:
            open_project(client, root)
            with Bridge(client, initial_revision='') as bridge:
                reply = bridge.call('write_script', {
                    'source': f'WELDED = {welded}\n' + FLUSH_RIG})
            payload = json.loads(reply['content'][0]['text'])
            assert payload['ok'], payload
            path, value = write_clearance(client, root)
            reports[welded] = (payload['fit'], path.read_text(), fit_summary(value))
    fit, report, reread = reports[True]
    assert fit['verdict'] == 'pass' and fit['failing'] == []
    assert fit['counts'] == {'clear': 1, 'intersection': 0, 'below clearance': 0, 'unknown': 0}
    assert fit['attachments']['verdict'] == 'touching'
    assert 'welded by fix_ab' in report
    assert reread == fit
    fit, report, _ = reports[False]
    assert fit['verdict'] == 'fail'
    failure, = fit['failing']
    assert failure['status'] == 'below clearance'
    assert failure['distance_mm'] == 0.0 and 'intent' not in failure
    assert fit['attachments']['verdict'] == 'none'
    assert 'welded by' not in report


@pytest.mark.parametrize('intent,status', [
    ({'kind': 'attached', 'minimum_mm': 0.0, 'joints': ['fix_ab']}, 'clear'),
    # An older reader has no `attached` branch; the published minimum is what
    # makes it reach the same verdict anyway.
    ({'kind': 'attached'}, 'clear'),
    ({'kind': 'contact'}, 'clear'),
    ({}, 'below clearance'),
])
def test_an_attached_pair_is_clear_at_zero_and_still_fails_on_overlap(intent, status):
    from cadex_cli.clearance import MAXIMUM_COMMON_VOLUME_MM3, MINIMUM_CLEARANCE_MM, pair_status
    row = {'first': 'a', 'second': 'b', 'distance_mm': 0.0, 'common_volume_mm3': 0.0,
           'intent': intent}
    assert pair_status(row, MINIMUM_CLEARANCE_MM, MAXIMUM_COMMON_VOLUME_MM3) == status
    assert pair_status({**row, 'common_volume_mm3': 4.07}, MINIMUM_CLEARANCE_MM,
                       MAXIMUM_COMMON_VOLUME_MM3) == 'intersection'
    assert pair_status({**row, 'distance_mm': None, 'common_volume_mm3': None,
                        'error': 'unmeasured'}, MINIMUM_CLEARANCE_MM,
                       MAXIMUM_COMMON_VOLUME_MM3) == 'unknown'


def test_a_welded_pair_does_not_define_the_joint_it_cannot_move():
    """Known answer: the weld reads 0.0 mm at every sample, and is not the joint's.

    The engine's own fixture, summarised: `knee` sweeps [20, 70] degrees,
    `horn` is welded to `shin` and touching it, and nothing the hinge moves
    ever comes closer than 1.47 mm. Rolling the weld into the joint's numbers
    would report a 0.0 mm minimum and first contact at 20 degrees -- the
    bottom of the range, where the sweep merely started -- and bury the one
    number the block exists to carry. `pairs_moving` says how many pairs the
    three facts were read over (ADR-374).
    """

    def joint(*pairs):
        return {'status': 'complete', 'step_degrees': 5, 'step_mm': None,
                'joints': [{'joint': 'knee', 'kind': 'revolute', 'unit': 'degrees',
                            'status': 'complete', 'step': 5, 'sample_count': 11,
                            'range_degrees': [20, 70], 'initial_degrees': 20,
                            'pairs': list(pairs)}]}

    weld = {'first': 'horn', 'second': 'shin', 'relative_motion': False,
            'minimum_distance_mm': 0.0, 'maximum_common_volume_mm3': 0.0,
            'first_contact_degrees': 20.0}
    swept = {'first': 'thigh', 'second': 'shin', 'relative_motion': True,
             'minimum_distance_mm': 1.472964, 'maximum_common_volume_mm3': 0.0,
             'first_contact_degrees': None}
    block = fit_summary({'available': True, 'pairs': [],
                         'clearance_sweep': joint(weld, swept)})['sweep']
    row = block['joints'][0]
    assert (row['pairs_measured'], row['pairs_moving']) == (2, 1)
    assert row['minimum_distance_mm'] == 1.472964
    assert row['maximum_common_volume_mm3'] == 0.0
    # No pair this hinge moves ever touches, so it has no first contact to
    # name -- and saying nothing is the honest answer, not 20 degrees.
    assert 'first_contact' not in row
    # Nothing failed: the weld is a fit the design asked for (ADR-372), and
    # the swept block agrees with the static one about it.
    assert (block['verdict'], block['failing_count']) == ('pass', 0)

    # A row from a revision accepted before ADR-374 carries no flag, so it
    # counts as moving and the block reads exactly as it did then.
    legacy = joint({k: v for k, v in weld.items() if k != 'relative_motion'},
                   {k: v for k, v in swept.items() if k != 'relative_motion'})
    older = fit_summary({'available': True, 'pairs': [],
                         'clearance_sweep': legacy})['sweep']['joints'][0]
    assert (older['pairs_measured'], older['pairs_moving']) == (2, 2)
    assert older['minimum_distance_mm'] == 0.0
    assert older['first_contact'] == {'value': 20.0, 'unit': 'degrees',
                                      'pair': ['horn', 'shin']}


def test_an_unbounded_wheel_is_missing_coverage_beside_a_hinge_that_swept_clean():
    """Known answer: a balancer's two wheels, and one bounded hinge (ADR-375).

    A joint that declares no limits can still move, and before this the
    engine dropped it before it reached a row: the block read `sweep pass: 1
    joint(s) swept` while the two parts that turn against the chassis had
    been measured at the solved pose and nowhere else. It is a coverage hole
    and reads as one, with the declaration to add named per joint.
    """

    from cadex_cli.clearance import SWEEP_NO_JOINTS

    def unbounded(name, kind, unit, limit):
        return {'joint': name, 'kind': kind, 'unit': unit, 'status': 'incomplete',
                'reason': f'this {kind} joint declares no limits, so the assembly states no '
                          f'range to sweep it through and the pairs it moves were measured at '
                          f'the solved pose only; declare {limit} for it to be swept'}

    sweep = {'status': 'incomplete', 'step_degrees': 5, 'step_mm': None, 'joints': [
        {'joint': 'pitch', 'kind': 'revolute', 'unit': 'degrees', 'status': 'complete',
         'step': 5, 'sample_count': 13, 'range_degrees': [-30, 30], 'initial_degrees': 0,
         'elapsed_seconds': 1.5, 'pairs': [
             {'first': 'chassis', 'second': 'mast', 'minimum_distance_mm': 2.0,
              'maximum_common_volume_mm3': 0.0, 'first_contact_degrees': None,
              'relative_motion': True}]},
        unbounded('wheel_left', 'revolute', 'degrees', 'angle_limits_degrees'),
        unbounded('wheel_right', 'revolute', 'degrees', 'angle_limits_degrees'),
    ]}
    block = fit_summary({'available': True, 'revision': 'r', 'assembly': 'asm',
                         'pairs': [], 'clearance_sweep': sweep})['sweep']
    assert block['verdict'] == 'incomplete'
    # Neither complete nor suppressed: the two wheels are coverage that is
    # actually missing, which is what `checked - complete - skipped` counts.
    assert (block['joints_checked'], block['joints_complete'],
            block['joints_skipped']) == (3, 1, 0)
    assert _sweep_line(block) == 'sweep incomplete: 2 of 3 joint(s) unswept'
    assert block['note'] and 'nothing failing' not in block['note']
    for row in block['joints'][1:]:
        assert row['pairs_measured'] == 0 and row['pairs_moving'] == 0
        assert row['minimum_distance_mm'] is None and 'first_contact' not in row
        assert 'declare angle_limits_degrees' in row['reason']
    # Nothing failed: missing coverage is not an overlap, and the block does
    # not invent one.
    assert block['failing_count'] == 0 and block['failing'] == []
    # And the empty sweep no longer offers an unlimited joint as a reason it
    # found nothing to check, because such a joint now has a row of its own.
    assert 'welded or suppressed' in SWEEP_NO_JOINTS and 'unlimited' not in SWEEP_NO_JOINTS


#: The hinge of ADR-378's reproduction, measured on real OCCT solids by
#: `cadex_tests/test_joint_fit_sweep.py`'s grazing fixture: two unit spheres,
#: the fixed centre 12.04 mm from the hinge axis and the moving centre 10 mm
#: from it, swept from the solved 20 degrees to 90 degrees at 1 degree. The
#: centres meet at 90 degrees exactly 2.04 mm apart, so the surfaces close to
#: 0.04 mm and never touch. The solved pose is 10.7516 mm clear.
_GRAZE_STATIC = 10.751593998165479
_GRAZE_MINIMUM = 0.03999999999999915


def _graze_value(pair_row, *, joint_pair=None, **row):
    """One hinge, one pair, the grazing numbers -- the shape a build reply reads."""

    first, second = pair_row['first'], pair_row['second']
    swept = {'first': joint_pair[0] if joint_pair else first,
             'second': joint_pair[1] if joint_pair else second,
             'relative_motion': True,
             'minimum_distance_mm': _GRAZE_MINIMUM,
             'maximum_common_volume_mm3': 0.0,
             'first_contact_degrees': None, **row}
    return {'available': True, 'revision': 'graze', 'assembly': 'asm',
            'pose': 'initial solved pose', 'pairs': [pair_row],
            'clearance_sweep': {
                'status': 'complete', 'step_degrees': 1, 'step_mm': None,
                'joints': [{'joint': 'hinge', 'kind': 'revolute',
                            'unit': 'degrees', 'status': 'complete', 'step': 1,
                            'sample_count': 71, 'range_degrees': [20, 90],
                            'initial_degrees': 20.0, 'pairs': [swept]}]}}


def test_a_gap_the_motion_closes_fails_the_swept_check():
    """Known answer: clear at the solved pose, 0.04 mm through the range.

    The measurement is the engine's, from the real-solid fixture named above.
    Before ADR-378 the swept block could only fail on interpenetration or an
    unmeasured pair, so it printed this 0.04 mm beside `verdict: pass` -- a
    quarter of the 0.1 mm gap the solved-pose block holds the very same
    undeclared pair to, at a pose the solved-pose block cannot see.
    """

    row = {'first': 'fixed', 'second': 'moving',
           'distance_mm': _GRAZE_STATIC, 'common_volume_mm3': 0.0}
    fit = fit_summary(_graze_value(row))
    # The solved pose is genuinely clear: this failure exists only because
    # the sweep looked somewhere else.
    assert fit['verdict'] == 'pass' and fit['failing_count'] == 0
    block = fit['sweep']
    assert block['verdict'] == 'fail'
    assert block['thresholds']['minimum_clearance_mm'] == 0.1
    (bad,) = block['failing']
    assert (bad['joint'], bad['first'], bad['second'], bad['status']) == (
        'hinge', 'fixed', 'moving', 'below clearance')
    assert bad['minimum_distance_mm'] == _GRAZE_MINIMUM
    assert bad['maximum_common_volume_mm3'] == 0.0
    # Both numbers, so the reply says what closed and from where.
    assert bad['minimum_mm'] == 0.1 and bad['distance_mm'] == _GRAZE_STATIC
    assert 'intent' not in bad
    # The joint's own row is unchanged by the verdict.
    assert block['joints'][0]['minimum_distance_mm'] == _GRAZE_MINIMUM


def test_the_swept_minimum_is_the_one_the_solved_pose_held_the_pair_to():
    """A declared `clearances=` minimum travels with the pair into the sweep."""

    base = {'first': 'fixed', 'second': 'moving',
            'distance_mm': _GRAZE_STATIC, 'common_volume_mm3': 0.0}
    # Declared at 0.02 mm, so 0.04 mm through the range is what the design
    # asked for and nothing fails.
    loose = dict(base, intent={'kind': 'clearance', 'minimum_mm': 0.02})
    assert fit_summary(_graze_value(loose))['sweep']['verdict'] == 'pass'
    # Declared at 2 mm, and the motion closes to a fiftieth of it.
    tight = dict(base, intent={'kind': 'clearance', 'minimum_mm': 2.0})
    block = fit_summary(_graze_value(tight))['sweep']
    assert block['verdict'] == 'fail'
    (bad,) = block['failing']
    assert bad['minimum_mm'] == 2.0
    assert bad['intent'] == {'kind': 'clearance', 'minimum_mm': 2.0}
    # ...and the caller's own default moves it too, the way it moves the
    # solved-pose block's.
    assert fit_summary(_graze_value(base), minimum=0.01)['sweep']['verdict'] == 'pass'


def test_the_swept_check_adds_to_the_solved_pose_check_and_never_repeats_it():
    """Four pairs the sweep must leave alone, each for its own reason."""

    base = {'first': 'fixed', 'second': 'moving',
            'distance_mm': _GRAZE_STATIC, 'common_volume_mm3': 0.0}
    # A pair the design declares as touching is not held to a gap here
    # either -- exactly as at the solved pose.
    for intent in ({'kind': 'contact'},
                   {'kind': 'attached', 'minimum_mm': 0.0, 'joints': ['weld']}):
        touching = dict(base, distance_mm=0.0, intent=intent)
        assert fit_summary(_graze_value(touching))['sweep']['verdict'] == 'pass', intent
    # A pair this joint does not move repeats its solved-pose number at every
    # sample (ADR-374); that number is the solved-pose block's to judge.
    rigid = _graze_value(base, relative_motion=False)
    assert fit_summary(rigid)['sweep']['verdict'] == 'pass'
    # A pair that already fails at the solved pose is named there, once.
    failing = dict(base, distance_mm=0.05)
    whole = fit_summary(_graze_value(failing))
    assert whole['verdict'] == 'fail' and whole['failing_count'] == 1
    assert whole['sweep']['verdict'] == 'pass'
    # An overlap through the motion is still an overlap, and outranks this.
    overlapping = _graze_value(base, maximum_common_volume_mm3=5.0,
                               first_contact_degrees=80.0)
    (bad,) = fit_summary(overlapping)['sweep']['failing']
    assert bad['status'] == 'intersection' and bad['first_contact_degrees'] == 80.0
    # A swept pair with no solved-pose row has no intent and no verdict to
    # read, so it is judged by none of this.
    orphan = _graze_value(base, joint_pair=('other', 'part'))
    assert fit_summary(orphan)['sweep']['verdict'] == 'pass'


@pytest.mark.parametrize('intent,status', [
    # Rigidly held by a weld and declared to run 0.05 mm clear: two facts
    # about one pair, both true, and the declared minimum is what judges it
    # (ADR-380, withdrawing ADR-379). 0.2 mm clears 0.05 mm.
    ({'kind': 'clearance', 'minimum_mm': 0.05, 'joints': ['weld_horn']}, 'clear'),
    # The declared minimum is really consulted: a wider one fails.
    ({'kind': 'clearance', 'minimum_mm': 0.5, 'joints': ['weld_horn']},
     'below clearance'),
    # The same declaration on a pair nothing welds reads exactly the same.
    ({'kind': 'clearance', 'minimum_mm': 0.05}, 'clear'),
    ({'kind': 'clearance', 'minimum_mm': 0.5}, 'below clearance'),
    # A contact declaration means touching, so the weld's joints on it
    # change nothing.
    ({'kind': 'contact', 'joints': ['weld_horn']}, 'missed contact'),
    ({'kind': 'attached', 'minimum_mm': 0.0, 'joints': ['weld_horn']}, 'clear'),
])
def test_a_clearance_declared_on_a_welded_pair_is_judged_by_its_minimum(intent, status):
    """A weld fixes a relative pose; it does not require contact (ADR-380).

    `comp_horn_shoulder` is welded to `comp_upper_arm` by `weld_horn_shoulder`
    and declared a 0.05 mm clearance in the same script; the solids measure
    0.2 mm apart. ADR-379 called that a contradiction and failed it at every
    gap. It is not one — a board rigidly held over its standoffs is welded
    and meant to stay apart — so the reader is back to the declared minimum,
    and what names a horn floating off its link is `attachments`.
    """

    from cadex_cli.clearance import MAXIMUM_COMMON_VOLUME_MM3, MINIMUM_CLEARANCE_MM, pair_status
    row = {'first': 'comp_horn_shoulder', 'second': 'comp_upper_arm',
           'distance_mm': 0.19999999999999732, 'common_volume_mm3': 0.0,
           'intent': intent}
    def status_of(**changes):
        return pair_status({**row, **changes}, MINIMUM_CLEARANCE_MM,
                           MAXIMUM_COMMON_VOLUME_MM3)
    assert status_of() == status
    if intent['kind'] == 'clearance':
        # Rigidly separated well beyond the minimum, or right down on it:
        # a declaration that is met is met, welded or not.
        assert status_of(distance_mm=5.0) == 'clear'
    # Overlap is still overlap, and an unmeasured pair is still unknown.
    assert status_of(common_volume_mm3=4.07) == 'intersection'
    assert status_of(distance_mm=None, common_volume_mm3=None,
                     error='unmeasured') == 'unknown'


def test_a_welded_pair_that_meets_its_declared_minimum_reaches_the_reply_clear(tmp_path):
    """The regression ADR-380 exists for, in the block the agent actually reads.

    Two components a fixed joint holds rigidly 2 mm apart, declared to keep
    0.5 mm: no failing check, and the report joins both facts on the row —
    the joint that holds them and the minimum they were given. Beside it, the
    same shape below its minimum still fails `below clearance`.
    """

    from cadex_cli.clearance import fit_summary, write_clearance
    value = {
        'available': True, 'revision': 'f03054d6', 'assembly': 'heron_assembly',
        'pose': 'initial solved pose (not swept motion)',
        'pairs': [
            {'first': 'comp_board', 'second': 'comp_deck',
             'distance_mm': 2.0, 'common_volume_mm3': 0.0,
             'intent': {'kind': 'clearance', 'minimum_mm': 0.5,
                        'joints': ['weld_standoff']},
             'fit_failures': []},
            {'first': 'comp_shroud', 'second': 'comp_pulley',
             'distance_mm': 0.2, 'common_volume_mm3': 0.0,
             'intent': {'kind': 'clearance', 'minimum_mm': 0.5,
                        'joints': ['weld_shroud']},
             'fit_failures': ['below clearance']},
        ],
    }
    fit = fit_summary(value)
    assert fit['verdict'] == 'fail' and fit['failing_count'] == 1
    assert fit['counts']['clear'] == 1 and fit['counts']['below clearance'] == 1
    failure, = fit['failing']
    assert (failure['first'], failure['second']) == ('comp_shroud', 'comp_pulley')
    assert failure['status'] == 'below clearance'
    # No note: there is no contradiction to explain, only a gap to close.
    assert 'note' not in fit

    class _OnePage:
        def request(self, op, arguments):
            assert op == 'inspect' and arguments['scope'] == 'clearance'
            return {'ok': True, 'value': value, 'page': {'next_offset': None}}

    path, _ = write_clearance(_OnePage(), root=tmp_path, sweep=False)
    report = path.read_text()
    assert 'clearance under weld' not in report
    assert 'declared minimum 0.5 mm, and welded by weld_standoff' in report
    assert '| clear |' in report and '| below clearance |' in report
