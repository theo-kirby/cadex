# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The evidence collector spends only the frozen continuation budget."""
import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / 'docs/probes/ot7/runner/run.py'
spec = importlib.util.spec_from_file_location('ot7_runner', PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def project(tmp_path):
    root = tmp_path / 'cadex-projects'
    root.mkdir()
    return root / 'ot7-heron'


def executor(calls, turn_code=0):
    def execute(command, out, stem, timeout):
        calls.append((command, timeout))
        if stem == 'turn':
            # The prompt slot is durable before the provider is invoked.
            receipt = json.loads((out.parent / 'attempt.json').read_text())
            assert receipt['turns'][-1]['status'] == 'started'
            (out / 'transcript.jsonl').write_text('{"type":"result"}\n')
        elif stem == 'measurement':
            runner.write(out / 'fit.json', {'verdict': 'fail', 'failing_count': 7, 'pairs_checked': 10})
            runner.write(out / 'clearance.json', {'pairs': [], 'clearance_sweep': {'status': 'incomplete'}})
            runner.write(out / 'inventory.json', {'component_count': 3})
        elif stem == 'smoke':
            runner.write(out / 'smoke.json', {'verdict': 'fail'})
        return {'exit_code': turn_code if stem == 'turn' else 0, 'elapsed_seconds': 0.01}
    return execute


def test_fourth_continuation_is_impossible_even_after_restart(tmp_path):
    target = project(tmp_path)
    calls = []
    report = runner.run('heron', target, 'fixture', executor(calls))
    turns = [cmd for cmd, _ in calls if '--child-turn' in cmd]
    assert [Path(cmd[-2]).name for cmd in turns] == runner.frozen('heron')
    assert len(turns) == 4  # one create plus exactly three continuations
    assert report['status'] == 'exhausted'
    assert [r['continuations_used'] for r in report['turns']] == [0, 1, 2, 3]
    for row in report['turns']:
        assert row['static_fit']['failing_count'] == 7
        artifacts = {a['path']: a for a in row['artifacts']}
        assert {'transcript.jsonl', 'clearance.json', 'fit.json', 'inventory.json'} <= artifacts.keys()
        assert artifacts['transcript.jsonl']['sha256'] == runner.digest(target / 'evidence/turn-0/transcript.jsonl')['sha256']
    assert report['smoke']['artifacts'][0]['path'] == 'smoke.json'
    with pytest.raises(FileExistsError):
        runner.run('heron', target, 'fixture', executor(calls))
    assert len([cmd for cmd, _ in calls if '--child-turn' in cmd]) == 4


@pytest.mark.parametrize('code', [1, 'timeout', 'launch_failed'])
def test_provider_failure_stops_without_spending_continuations(tmp_path, code):
    calls = []
    report = runner.run('heron', project(tmp_path), 'fixture', executor(calls, code))
    assert report['status'] == 'interrupted'
    assert len(report['turns']) == 1
    assert report['turns'][0]['continuations_used'] == 0
    assert calls[-1][1] == 300 and '--timeout' in calls[-1][0]


@pytest.mark.parametrize('design,name', [('heron', 'continue-3.prompt.txt'),
                                          ('repair', 'repair.prompt.txt')])
def test_changed_prompt_cannot_launch(tmp_path, monkeypatch, design, name):
    prompts = tmp_path / 'prompts'
    prompts.mkdir()
    for file in runner.PROMPTS.iterdir():
        (prompts / file.name).write_bytes(file.read_bytes())
    (prompts / name).write_text('changed')
    monkeypatch.setattr(runner, 'PROMPTS', prompts)
    target = project(tmp_path)
    with pytest.raises(ValueError, match='frozen prompt changed'):
        runner.run(design, target, 'fixture')
    assert not target.exists()


def test_unfrozen_automatic_nudge_cannot_reach_provider(tmp_path, monkeypatch):
    from cadex_cli import __main__ as cli
    from cadex_cli import agent
    seen = []
    monkeypatch.setattr(agent, 'find_claude', lambda _: '/fixture/claude')
    monkeypatch.setattr(agent.ClaudeTurn, '__init__', lambda self, **kwargs: None)
    def provider(self, text):
        seen.append(text)
        return agent.TurnResult(ok=True, frames=[{'type': 'result'}])
    monkeypatch.setattr(agent.ClaudeTurn, 'run', provider)
    def command(args, report, turn_factory):
        turn = turn_factory()
        assert turn.run('frozen').ok
        assert not turn.run('unfrozen').ok
        return 1
    monkeypatch.setattr(cli, 'command_prompt', command)
    monkeypatch.setattr(cli, 'main', lambda args: cli.command_prompt(None, None))
    runner.child_turn(tmp_path, tmp_path, runner.PROMPTS / 'heron.create.prompt.txt', 'fixture')
    assert seen == ['frozen']
    assert (tmp_path / 'blocked-followup.json').exists()
    assert json.loads((tmp_path / 'transcript.jsonl').read_text()) == {'type': 'result'}


def test_timeout_kills_the_process_group_and_retains_output(tmp_path):
    result = runner.execute([runner.sys.executable, '-u', '-c',
                             'import time; print("started"); time.sleep(30)'],
                            tmp_path, 'turn', 0.3)
    assert result['exit_code'] == 'timeout'
    assert result['elapsed_seconds'] < 3
    assert 'started' in (tmp_path / 'turn.stdout.json').read_text()


def repair_seed(tmp_path, monkeypatch):
    target = project(tmp_path)
    target.mkdir()
    (target / 'evidence').mkdir()
    (target / 'script.py').write_text('known seed fixture\n')
    metadata = {'accepted_revision': 'first-revision', 'working_revision': 'first-revision',
                'accepted_digest': 'ce35f4d3ae95b082ec54d862d8bc2fbfe59898cd37ddb30d4416918bfbc9603c',
                'param_values': {}, 'board_values': [], 'cage_values': [],
                'mount_values': [], 'net_values': []}
    runner.write(target / 'script.json', metadata)
    repo = tmp_path / 'repo'
    retained = repo / 'docs/probes/ot7/retained'
    retained.mkdir(parents=True)
    runner.write(retained / 'repair-refusal.json', {'seed': {
        'script_sha256': runner.digest(target / 'script.py')['sha256'],
        'accepted_revision': 'first-revision'}})
    monkeypatch.setattr(runner, 'REPO', repo)
    return target


def test_repair_preserves_seed_and_collects_one_frozen_fresh_turn(tmp_path, monkeypatch):
    target = repair_seed(tmp_path, monkeypatch)
    before = runner.seed_identity(target)
    calls = []
    fake = executor(calls)
    def execute(command, out, stem, timeout):
        result = fake(command, out, stem, timeout)
        if stem == 'measurement':
            # Known answer: before has seven failures, after has none.
            runner.write(out / 'fit.json', {'verdict': 'fail' if out.name == 'before' else 'pass',
                         'failing_count': 7 if out.name == 'before' else 0, 'pairs_checked': 10})
        return result
    report = runner.run('repair', target, 'fixture', execute)
    assert runner.seed_identity(target) == before
    assert report['seed'] == before == report['turns'][0]['accepted_after']
    assert report['before']['seed_unchanged']
    assert report['turns'][0]['static_fit']['failing_count'] == 0
    assert report['turns'][0]['repair_assessment']['status'] == 'unknown'
    assert report['before']['repair_assessment']['status'] == 'unknown'
    artifacts = {a['path']: a for a in report['turns'][0]['artifacts']}
    assessment_path = target / 'evidence/f4-repair/turn-0/repair-assessment.json'
    assert artifacts['repair-assessment.json'] == runner.digest(assessment_path)
    assert report['turns'][0]['continuations_used'] == 1
    assert [Path(cmd[-2]).name for cmd, _ in calls if '--child-turn' in cmd] == ['repair.prompt.txt']
    assert [Path(cmd[-1]).name for cmd, _ in calls if '--child-measure' in cmd] == ['before', 'turn-0']
    assert all('smoke' not in cmd for cmd, _ in calls)
    assert {'clearance.json', 'fit.json'} <= {a['path'] for a in report['before']['artifacts']}
    with pytest.raises(FileExistsError):
        runner.run('repair', target, 'fixture', execute)
    assert len(calls) == 3


@pytest.mark.parametrize('change', ['script', 'accepted_revision', 'accepted_digest', 'param_values'])
def test_repair_rejects_changed_seed_before_dispatch(tmp_path, monkeypatch, change):
    target = repair_seed(tmp_path, monkeypatch)
    if change == 'script':
        (target / 'script.py').write_text('changed')
    else:
        metadata = json.loads((target / 'script.json').read_text())
        metadata[change] = {'width': 42} if change == 'param_values' else 'changed'
        runner.write(target / 'script.json', metadata)
    with pytest.raises(ValueError, match='seed identity'):
        runner.run('repair', target, 'fixture')
    assert not (target / 'evidence/f4-repair').exists()


@pytest.mark.parametrize('failure', ['missing', 'error', 'mutation'])
def test_repair_never_calls_provider_without_unchanged_before_evidence(tmp_path, monkeypatch, failure):
    target = repair_seed(tmp_path, monkeypatch)
    calls = []
    fake = executor(calls)
    def execute(command, out, stem, timeout):
        result = fake(command, out, stem, timeout)
        if failure == 'missing':
            (out / 'fit.json').unlink()
        elif failure == 'error':
            result['exit_code'] = 1
        else:
            (target / 'script.py').write_text('unexpected read mutation')
        return result
    report = runner.run('repair', target, 'fixture', execute)
    assert report['status'] == 'before_unavailable'
    assert report['turns'] == []
    assert len(calls) == 1


def test_repair_child_uses_frozen_prompt_without_resume(tmp_path, monkeypatch):
    from cadex_cli import __main__ as cli
    seen = []
    monkeypatch.setattr(cli, 'main', lambda args: seen.extend(args) or 0)
    assert runner.child_turn(tmp_path, tmp_path, runner.PROMPTS / 'repair.prompt.txt', 'fixture') == 0
    assert '--resume' not in seen
    assert seen[seen.index('-p') + 1] == (runner.PROMPTS / 'repair.prompt.txt').read_text()


@pytest.mark.parametrize('late_page_error', [False, True])
def test_measurement_child_keeps_late_failures_and_sweep_evidence(tmp_path, monkeypatch,
                                                                 late_page_error):
    """Exercise the real reader/fit summary, not the runner's fake executor."""
    from contextlib import contextmanager
    from cadex_cli import __main__ as cli
    from cadex_cli.inventory import InventoryError

    calls = []
    clear = {'first': 'base', 'second': 'link', 'distance_mm': 1.0,
             'common_volume_mm3': 0.0}
    overlap = {'first': 'servo', 'second': 'cheek', 'distance_mm': 0.0,
               'common_volume_mm3': 248.2}
    missed = {'first': 'horn', 'second': 'link', 'distance_mm': 0.2,
              'common_volume_mm3': 0.0, 'intent': {'kind': 'contact'}}
    sweep = {'status': 'incomplete', 'joints': [
        {'joint': 'knee', 'elapsed_seconds': 1.25, 'reason': 'runtime bound',
         'pairs': [{'first': 'thigh', 'second': 'shin', 'minimum_distance_mm': 0.0,
                    'maximum_common_volume_mm3': 12.0, 'first_contact_degrees': 30.0}]}]}
    inventory = {'components': [{'component': 'servo', 'catalog': {'part_number': 'MG90S'}}]}

    class Client:
        def request(self, op, args):
            assert op == 'inspect'  # No rebuild or acceptance is permitted.
            assert args['target'] == ''
            calls.append((args['scope'], args['path'], args['offset']))
            key = calls[-1]
            pages = {
                ('clearance', '', 0): ({'available': True, 'revision': 'accepted',
                    'pairs': {'type': 'array', 'inspect_path': '/pairs'},
                    'clearance_sweep': {'type': 'object', 'inspect_path': '/clearance_sweep'},
                    'world_geometry': [{'component': 'floor', 'reason': 'world plane'}]}, None),
                ('clearance', '/pairs', 0): ([clear], 1),
                ('clearance', '/pairs', 1): ([overlap, missed], None),
                ('clearance', '/clearance_sweep', 0): (sweep, None),
                ('inventory', '', 0): (inventory, None),
            }
            if late_page_error and key == ('clearance', '/pairs', 1):
                return {'ok': False, 'error': 'late page unavailable'}
            value, next_offset = pages[key]
            return {'ok': True, 'value': value, 'page': {'next_offset': next_offset}}

    @contextmanager
    def session(args, report, *, restore):
        assert restore is False
        assert args.project == str(tmp_path)
        yield None, Client()

    monkeypatch.setattr(cli, '_engine_session', session)
    if late_page_error:
        with pytest.raises(InventoryError, match='late page unavailable'):
            runner.child_measure(tmp_path, tmp_path)
        assert not (tmp_path / 'fit.json').exists()
        assert not (tmp_path / 'clearance.json').exists()
        assert ('inventory', '', 0) not in calls
        return

    assert runner.child_measure(tmp_path, tmp_path) == 0
    raw = json.loads((tmp_path / 'clearance.json').read_text())
    fit = json.loads((tmp_path / 'fit.json').read_text())
    assert raw['pairs'] == [clear, overlap, missed]
    assert raw['clearance_sweep'] == sweep
    assert fit['revision'] == 'accepted'
    assert fit['verdict'] == 'fail' and fit['pairs_checked'] == 3
    assert fit['failing_count'] == 3
    assert [(r['first'], r['second'], r['status'], r['distance_mm'], r['common_volume_mm3'])
            for r in fit['failing']] == [
        ('servo', 'cheek', 'intersection', 0.0, 248.2),
        ('horn', 'link', 'missed contact', 0.2, 0.0),
        ('floor', '', 'world geometry', None, None)]
    assert json.loads((tmp_path / 'inventory.json').read_text()) == inventory
    assert calls == [('clearance', '', 0), ('clearance', '/pairs', 0),
                     ('clearance', '/pairs', 1), ('clearance', '/clearance_sweep', 0),
                     ('inventory', '', 0)]


def test_measurement_child_keeps_later_nested_sweep_pages(tmp_path, monkeypatch):
    """A later joint's later pair page carries the worst swept collision."""
    from contextlib import contextmanager
    from cadex_cli import __main__ as cli

    calls = []
    clear = {'first': 'base', 'second': 'link', 'minimum_distance_mm': 1.0,
             'maximum_common_volume_mm3': 0.0, 'first_contact_degrees': None}
    worst = {'first': 'thigh', 'second': 'shin', 'minimum_distance_mm': 0.0,
             'maximum_common_volume_mm3': 12.0, 'first_contact_degrees': 30.0}
    first_joint = {'joint': 'hip', 'elapsed_seconds': 0.5, 'pairs': [clear]}
    later_joint = {'joint': 'knee', 'elapsed_seconds': 1.25, 'pairs': [clear, worst]}
    joints_path = '/clearance_sweep/joints'
    pairs_path = joints_path + '/1/pairs'
    pages = {
        ('clearance', '', 0): ({'available': True, 'revision': 'accepted', 'pairs': [],
            'clearance_sweep': {'status': 'complete', 'joints': {
                'type': 'array', 'inspect_path': joints_path}}}, None),
        ('clearance', joints_path, 0): ([first_joint], 1),
        ('clearance', joints_path, 1): ([{**later_joint, 'pairs': {
            'type': 'array', 'inspect_path': pairs_path}}], None),
        ('clearance', pairs_path, 0): ([clear], 1),
        ('clearance', pairs_path, 1): ([worst], None),
        ('inventory', '', 0): ({'components': []}, None),
    }

    class Client:
        def request(self, op, args):
            assert op == 'inspect' and args['target'] == ''
            key = (args['scope'], args['path'], args['offset'])
            calls.append(key)
            value, next_offset = pages[key]
            return {'ok': True, 'value': value, 'page': {'next_offset': next_offset}}

    @contextmanager
    def session(args, report, *, restore):
        assert restore is False
        yield None, Client()

    monkeypatch.setattr(cli, '_engine_session', session)
    assert runner.child_measure(tmp_path, tmp_path) == 0
    raw = json.loads((tmp_path / 'clearance.json').read_text())
    assert raw['clearance_sweep'] == {
        'status': 'complete', 'joints': [first_joint, later_joint]}
    assert raw['clearance_sweep']['joints'][1]['pairs'][1] == worst
    assert calls == list(pages)


def repair_geometry(gap=0.0, volume=0.0):
    return {'available': True, 'revision': 'accepted', 'world_geometry': [],
            'pairs': [{'first': first, 'second': second, 'distance_mm': gap,
                       'common_volume_mm3': volume}
                      for first, second in runner.REPAIR_ATTACHMENTS]}


def test_repair_assessment_catches_unflagged_original_horn_gaps():
    from cadex_cli.clearance import fit_summary
    value = repair_geometry(gap=0.2)
    assert fit_summary(value)['failing_count'] == 0
    result = runner.repair_assessment(value, 'accepted')
    assert result['status'] == 'fail'
    assert [r['reason'] for r in result['attachments']] == ['missed contact'] * 2
    assert [r['distance_mm'] for r in result['attachments']] == [0.2, 0.2]
    assert [r['common_volume_mm3'] for r in result['attachments']] == [0.0, 0.0]


def test_repair_assessment_pass_requires_static_fit_and_both_contacts():
    value = repair_geometry(gap=0.001)
    for row in value['pairs']:
        row['intent'] = {'kind': 'contact'}
        row['first'], row['second'] = row['second'], row['first']
    assert runner.repair_assessment(value, 'accepted')['status'] == 'pass'
    value['world_geometry'] = [{'component': 'floor', 'reason': 'world plane'}]
    assert runner.repair_assessment(value, 'accepted')['status'] == 'fail'
    value['world_geometry'] = []
    value['pairs'].append({'first': 'servo', 'second': 'cheek', 'distance_mm': 0.0,
                           'common_volume_mm3': 248.2})
    result = runner.repair_assessment(value, 'accepted')
    assert result['status'] == 'fail'
    assert result['static_fit']['failing'][0]['common_volume_mm3'] == 248.2


@pytest.mark.parametrize('change', ['missing', 'renamed', 'duplicate', 'nan', 'error',
                                  'revision', 'unavailable', 'world_missing'])
def test_repair_assessment_missing_attachment_evidence_is_unknown(change):
    value = repair_geometry()
    for row in value['pairs']:
        row['intent'] = {'kind': 'contact'}
    # Static summary passes; attachment evidence must still be present and valid.
    if change == 'missing':
        value['pairs'].pop()
    elif change == 'renamed':
        value['pairs'][0]['first'] = 'replacement_horn'
    elif change == 'duplicate':
        value['pairs'].append(dict(value['pairs'][0]))
    elif change == 'nan':
        value['pairs'][0]['distance_mm'] = float('nan')
    elif change == 'error':
        value['pairs'][0]['error'] = 'kernel failed'
    elif change == 'revision':
        value['revision'] = 'stale'
    elif change == 'unavailable':
        value['available'] = False
    else:
        del value['world_geometry']
    result = runner.repair_assessment(value, 'accepted')
    assert result['status'] != 'pass'
    assert any(row['status'] == 'unknown' for row in result['attachments'])


def test_repair_assessment_overlap_cannot_count_as_contact():
    result = runner.repair_assessment(repair_geometry(volume=0.002), 'accepted')
    assert result['status'] == 'fail'
    assert all(row['reason'] == 'intersection' for row in result['attachments'])


def test_repair_assessment_failed_measurement_ignores_leftover_report(tmp_path):
    runner.write(tmp_path / 'clearance.json', repair_geometry())
    result = runner.retain_repair_assessment(tmp_path, 'accepted', False)
    assert result['status'] == 'unknown'
    assert json.loads((tmp_path / 'repair-assessment.json').read_text()) == result


def test_repair_assessment_retains_unknown_nonfinite_measurements(tmp_path):
    value = repair_geometry()
    value['pairs'][0]['distance_mm'] = float('nan')
    (tmp_path / 'clearance.json').write_text(json.dumps(value))
    result = runner.retain_repair_assessment(tmp_path, 'accepted', True)
    assert result['attachments'][0]['status'] == 'unknown'
    assert result['attachments'][0]['distance_mm'] is None
    assert json.loads((tmp_path / 'repair-assessment.json').read_text()) == result
