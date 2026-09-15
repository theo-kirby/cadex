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


def test_provider_failure_the_call_returned_on_its_own_spends_its_slot(tmp_path):
    """A nonzero exit with a stream is a failed turn, not an interruption (ADR-355, ADR-356)."""
    calls = []
    report = runner.run('heron', project(tmp_path), 'fixture', executor(calls, 1))
    assert report['status'] == 'failed'
    assert len(report['turns']) == 1
    assert report['turns'][0]['continuations_used'] == 0
    assert report['turns'][0]['interruption'] is None and report['turns'][0]['slot_consumed']
    assert report['slots_spent'] == 1 and report['interrupted_calls'] == 0 and 'retry' not in report
    assert calls[-1][1] == 300 and '--timeout' in calls[-1][0]  # the smoke still runs


@pytest.mark.parametrize('code,kind', [('timeout', 'runner_timeout'), ('launch_failed', 'launch_failed')])
def test_runner_bound_kill_is_interrupted_and_returns_the_slot(tmp_path, code, kind):
    """Decision #44 / ADR-356: a call the runner cut off did not end on its own."""
    calls = []
    report = runner.run('heron', project(tmp_path), 'fixture', executor(calls, code))
    assert report['status'] == 'interrupted' and len(report['turns']) == 1
    row = report['turns'][0]
    assert row['status'] == 'interrupted' and row['slot_consumed'] is False and row['void'] is None
    assert row['interruption']['kind'] == kind and row['interruption']['slot_consumed'] is False
    assert row['interruption']['rule'] == 'ADR-356'
    assert row['interruption']['bound_seconds'] == (1800 if code == 'timeout' else None)
    assert row['continuations_used'] == 0
    assert report['slots_spent'] == 0 and report['void_calls'] == 0 and report['interrupted_calls'] == 1
    assert report['retry'] == {'rule': 'ADR-356', 'prompt': 'heron.create.prompt.txt', 'project': 'ot7-heron-b',
                               'note': 'Same frozen prompt, fresh project or fresh seed copy, '
                                       'only while the product agent is available.'}
    # The measurement is still read and hashed; no smoke runs; nothing else is dispatched.
    assert [Path(c[-1]).name for c, _ in calls if '--child-measure' in c] == ['turn-0']
    assert all('smoke' not in c for c, _ in calls) and row['static_fit']['failing_count'] == 7
    assert calls[0][1] == 1800 == report['turn_bound_seconds']
    with pytest.raises(FileExistsError):
        runner.run('heron', project(tmp_path), 'fixture', executor(calls, code))


def test_runner_timeout_on_a_continuation_keeps_the_completed_turns_and_returns_only_its_slot(tmp_path):
    calls = []
    fake = executor(calls)
    def execute(command, out, stem, timeout):
        result = fake(command, out, stem, timeout)
        if stem == 'turn' and out.name == 'turn-2':
            frames_file(out / 'transcript.jsonl', [SPOKE, SPOKE, SPOKE])  # killed mid-stream, no result
            result['exit_code'] = 'timeout'
            result['elapsed_seconds'] = 1800.0
        return result
    report = runner.run('heron', project(tmp_path), 'fixture', execute)
    assert [r['status'] for r in report['turns']] == ['completed', 'completed', 'interrupted']
    assert [r['continuations_used'] for r in report['turns']] == [0, 1, 1]
    assert report['slots_spent'] == 2 and report['interrupted_calls'] == 1 and report['void_calls'] == 0
    assert report['turns'][2]['interruption']['model_messages_before_kill'] == 3
    assert report['turns'][2]['interruption']['elapsed_seconds'] == 1800.0
    assert report['status'] == 'interrupted' and report['retry']['prompt'] == 'continue-2.prompt.txt'
    assert report['retry']['project'] == 'ot7-heron-b'
    assert len([c for c, _ in calls if '--child-turn' in c]) == 3


def test_runner_timeout_on_repair_spends_nothing_and_preserves_the_seed(tmp_path, monkeypatch):
    target = repair_seed(tmp_path, monkeypatch)
    before = runner.seed_identity(target)
    calls = []
    fake = executor(calls)
    def execute(command, out, stem, timeout):
        result = fake(command, out, stem, timeout)
        if stem == 'turn':
            frames_file(out / 'transcript.jsonl', [SPOKE])
            result['exit_code'] = 'timeout'
        return result
    report = runner.run('repair', target, 'fixture', execute)
    assert runner.seed_identity(target) == before == report['turns'][0]['accepted_after']
    row = report['turns'][0]
    assert row['status'] == 'interrupted' and row['slot_consumed'] is False and row['continuations_used'] == 0
    assert report['slots_spent'] == 0 and report['interrupted_calls'] == 1 and report['status'] == 'interrupted'
    assert report['retry'] == {'rule': 'ADR-356', 'prompt': 'repair.prompt.txt', 'project': 'ot7-heron-b',
                               'note': 'Same frozen prompt, fresh project or fresh seed copy, '
                                       'only while the product agent is available.'}
    assert row['repair_assessment']['status'] == 'unknown'  # after-measurement still retained
    classified = runner.classify(target / 'evidence/f4-repair/turn-0/transcript.jsonl')
    assert classified['void'] is None and classified['interruption']['kind'] == 'runner_timeout'
    assert classified['interruption']['model_messages_before_kill'] == 1


def test_interruption_is_not_a_limit_and_a_limit_is_not_an_interruption(tmp_path):
    assert runner.interruption({'exit_code': 0}, tmp_path / 'none.jsonl') is None
    assert runner.interruption({'exit_code': 3}, tmp_path / 'none.jsonl') is None
    assert runner.interruption({'exit_code': 1}, tmp_path / 'none.jsonl') is None
    # A limit that lands before the kill is void (ADR-355), which the runner checks first.
    calls = []
    report = runner.run('heron', project(tmp_path), 'fixture',
                        limited_executor(calls, void_at=0, mid_turn=True, exit_code='timeout'))
    assert report['status'] == 'void' and report['void_calls'] == 1 and report['interrupted_calls'] == 0
    assert report['turns'][0]['interruption'] is None


def test_captured_turn_keeps_every_frame_that_arrived_before_the_kill(tmp_path, monkeypatch):
    """The transcript is written frame by frame, so a kill mid-turn loses nothing received (ADR-356)."""
    from cadex_cli import __main__ as cli
    from cadex_cli import agent
    monkeypatch.setattr(agent, 'find_claude', lambda _: '/fixture/claude')
    monkeypatch.setattr(agent.ClaudeTurn, '__init__',
                        lambda self, **kwargs: setattr(self, 'session_id', '') or setattr(self, 'on_text', None))
    frames = [{'type': 'system', 'subtype': 'init', 'session_id': 's1'}, SPOKE, SPOKE]
    def provider(self, text, *, resume):
        result = agent.TurnResult()
        for frame in frames:
            result.frames.append(frame)
            self._absorb(frame, result)
        raise SystemExit('killed before the stream ended')  # SIGKILL never returns here
    monkeypatch.setattr(agent.ClaudeTurn, '_run_once', provider)
    def command(args, report, turn_factory):
        with pytest.raises(SystemExit):
            turn_factory().run('frozen')
        return 1
    monkeypatch.setattr(cli, 'command_prompt', command)
    monkeypatch.setattr(cli, 'main', lambda args: cli.command_prompt(None, None))
    runner.child_turn(tmp_path, tmp_path, runner.PROMPTS / 'heron.create.prompt.txt', 'fixture')
    assert runner.read_frames(tmp_path / 'transcript.jsonl') == frames
    assert runner.model_messages(tmp_path / 'transcript.jsonl') == 2


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
    monkeypatch.setattr(agent.ClaudeTurn, '__init__',
                        lambda self, **kwargs: setattr(self, 'session_id', '') or setattr(self, 'on_text', None))
    def provider(self, text, *, resume):
        seen.append(text)
        result = agent.TurnResult(ok=True)
        for frame in [{'type': 'result'}]:  # the real loop absorbs each frame as it arrives
            result.frames.append(frame)
            self._absorb(frame, result)
        return result
    monkeypatch.setattr(agent.ClaudeTurn, '_run_once', provider)
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


# ADR-355: a provider usage, session or credit limit is void — no slot spent,
# evidence kept, nothing further dispatched from that project.

LIMIT_TEXT = "You've hit your session limit · resets 8:20pm (America/New_York)"
REJECTED = {'type': 'rate_limit_event', 'rate_limit_info': {
    'status': 'rejected', 'resetsAt': 1789431600, 'rateLimitType': 'five_hour',
    'overageStatus': 'rejected', 'overageDisabledReason': 'out_of_credits'}}
SYNTHETIC = {'type': 'assistant', 'error': 'rate_limit', 'is_api_error_message': True,
             'message': {'model': '<synthetic>', 'role': 'assistant',
                         'content': [{'type': 'text', 'text': LIMIT_TEXT}]}}
LIMIT_RESULT = {'type': 'result', 'subtype': 'success', 'is_error': True, 'api_error_status': 429,
                'terminal_reason': 'api_error', 'total_cost_usd': 0, 'result': LIMIT_TEXT}
SPOKE = {'type': 'assistant', 'message': {'model': 'claude-fable-5', 'role': 'assistant',
                                          'content': [{'type': 'tool_use', 'name': 'mcp__cadex__rebuild'}]}}
CLEAN_RESULT = {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'done'}


def frames_file(path, frames):
    path.write_text(''.join(json.dumps(f) + '\n' for f in frames))


def limited_executor(calls, void_at=0, mid_turn=False, exit_code=1):
    fake = executor(calls)
    def execute(command, out, stem, timeout):
        result = fake(command, out, stem, timeout)
        index = int(out.name.split('-')[-1]) if out.name.startswith('turn-') else -1
        if stem == 'turn' and index == void_at:
            frames_file(out / 'transcript.jsonl',
                        ([SPOKE, SPOKE] if mid_turn else []) + [REJECTED, SYNTHETIC, LIMIT_RESULT])
            runner.write(out / 'turn.stdout.json', {'ok': False, 'error': LIMIT_TEXT, 'schema': 'cadex-cli-v1'})
            (out / 'turn.stderr.txt').write_text(LIMIT_TEXT + '\n')
            result['exit_code'] = exit_code
        return result
    return execute


def test_usage_limit_on_create_is_void_and_spends_nothing(tmp_path):
    target = project(tmp_path)
    calls = []
    report = runner.run('heron', target, 'fixture', limited_executor(calls))
    assert report['status'] == 'void'
    assert report['slots_spent'] == 0 and report['void_calls'] == 1
    assert report['retry'] == {'rule': 'ADR-355', 'prompt': 'heron.create.prompt.txt',
                               'project': 'ot7-heron-b', 'note': report['retry']['note']}
    [row] = report['turns']
    assert row['status'] == 'void' and row['slot_consumed'] is False
    assert row['continuations_used'] == 0
    assert row['void']['kind'] == 'usage_limit' and row['void']['cut_off_mid_turn'] is False
    assert {s['frame'] for s in row['void']['signals']} == {'rate_limit_event', 'assistant', 'result', 'envelope'}
    # One provider dispatch, the measurement still read, no smoke, evidence kept.
    assert len([cmd for cmd, _ in calls if '--child-turn' in cmd]) == 1
    assert len([cmd for cmd, _ in calls if '--child-measure' in cmd]) == 1
    assert not any('smoke' in cmd for cmd, _ in calls) and 'smoke' not in report
    artifacts = {a['path']: a for a in row['artifacts']}
    assert artifacts['transcript.jsonl'] == runner.digest(target / 'evidence/turn-0/transcript.jsonl')
    assert json.loads((target / 'evidence/attempt.json').read_text())['status'] == 'void'
    # The receipt stays; the retry is a fresh suffixed project, never a resume.
    with pytest.raises(FileExistsError):
        runner.run('heron', target, 'fixture', limited_executor(calls))
    assert len([cmd for cmd, _ in calls if '--child-turn' in cmd]) == 1


def test_usage_limit_mid_turn_on_a_continuation_is_void(tmp_path):
    calls = []
    report = runner.run('heron', project(tmp_path), 'fixture',
                        limited_executor(calls, void_at=2, mid_turn=True, exit_code=0))
    assert report['status'] == 'void'
    assert [r['status'] for r in report['turns']] == ['completed', 'completed', 'void']
    assert [r['continuations_used'] for r in report['turns']] == [0, 1, 1]
    assert [r['slot_consumed'] for r in report['turns']] == [True, True, False]
    assert report['slots_spent'] == 2 and report['void_calls'] == 1
    assert report['turns'][2]['void']['cut_off_mid_turn'] is True
    assert report['turns'][2]['void']['model_messages_before_limit'] == 2
    assert report['retry']['prompt'] == 'continue-2.prompt.txt'
    assert len([cmd for cmd, _ in calls if '--child-turn' in cmd]) == 3
    assert not any('smoke' in cmd for cmd, _ in calls)


def test_usage_limit_on_repair_is_void_and_preserves_seed(tmp_path, monkeypatch):
    target = repair_seed(tmp_path, monkeypatch)
    before = runner.seed_identity(target)
    calls = []
    report = runner.run('repair', target, 'fixture', limited_executor(calls))
    assert report['status'] == 'void'
    assert runner.seed_identity(target) == before == report['turns'][0]['accepted_after']
    assert report['turns'][0]['status'] == 'void'
    assert report['turns'][0]['continuations_used'] == 0 and report['slots_spent'] == 0
    assert report['retry']['project'] == 'ot7-heron-b'
    assert report['turns'][0]['repair_assessment']['status'] == 'unknown'
    assert 'repair-assessment.json' in {a['path'] for a in report['turns'][0]['artifacts']}
    assert [Path(cmd[-2]).name for cmd, _ in calls if '--child-turn' in cmd] == ['repair.prompt.txt']


def test_limit_warning_and_ordinary_errors_are_not_void(tmp_path):
    """A near-limit warning is not a limit; an unrelated provider error is a failed turn, not void."""
    calls = []
    fake = executor(calls)
    def execute(command, out, stem, timeout):
        result = fake(command, out, stem, timeout)
        if stem == 'turn':
            warning = dict(REJECTED, rate_limit_info=dict(REJECTED['rate_limit_info'], status='allowed_warning'))
            frames_file(out / 'transcript.jsonl', [warning, SPOKE, CLEAN_RESULT])
            runner.write(out / 'turn.stdout.json', {'ok': True, 'error': ''})
            (out / 'turn.stderr.txt').write_text('note: the rate limit window is 80% used\n')
        return result
    report = runner.run('heron', project(tmp_path), 'fixture', execute)
    assert report['status'] == 'exhausted' and report['slots_spent'] == 4
    assert all(r['void'] is None and r['slot_consumed'] for r in report['turns'])
    unrelated = tmp_path / 'unrelated'
    unrelated.mkdir()
    frames_file(unrelated / 'transcript.jsonl',
                [{'type': 'result', 'is_error': True, 'result': 'Could not start the claude CLI'}])
    runner.write(unrelated / 'turn.stdout.json', {'ok': False, 'error': 'Could not start the claude CLI'})
    assert runner.void_reason(unrelated / 'transcript.jsonl', unrelated / 'turn.stdout.json',
                              unrelated / 'turn.stderr.txt') is None


AUTH_FAILED = {'type': 'assistant', 'error': 'authentication_failed', 'is_api_error_message': True,
               'message': {'model': '<synthetic>', 'role': 'assistant',
                           'content': [{'type': 'text', 'text': 'Invalid API key · Please run /login'}]}}
AUTH_RESULT = {'type': 'result', 'subtype': 'success', 'is_error': True, 'api_error_status': 401,
               'terminal_reason': 'api_error', 'result': 'Invalid API key · Please run /login'}


def test_synthetic_error_frame_without_limit_evidence_is_not_void(tmp_path):
    """A `<synthetic>` frame is the CLI speaking, not a limit: an authentication failure spends its slot."""
    transcript, envelope, stderr = tmp_path / 't.jsonl', tmp_path / 'e.json', tmp_path / 's.txt'
    frames_file(transcript, [{'type': 'system', 'subtype': 'init'}, AUTH_FAILED, AUTH_RESULT])
    runner.write(envelope, {'ok': False, 'error': 'Invalid API key · Please run /login'})
    stderr.write_text('Invalid API key · Please run /login\n')
    assert runner.void_reason(transcript, envelope, stderr) is None
    assert runner.classify(transcript, envelope, stderr)['void'] is None
    # ...and through the runner it is an ordinary provider failure: the slot is spent, nothing is refunded.
    calls = []
    fake = executor(calls)
    def execute(command, out, stem, timeout):
        result = fake(command, out, stem, timeout)
        if stem == 'turn':
            frames_file(out / 'transcript.jsonl', [AUTH_FAILED, AUTH_RESULT])
            runner.write(out / 'turn.stdout.json', {'ok': False, 'error': 'Invalid API key · Please run /login'})
            (out / 'turn.stderr.txt').write_text('Invalid API key · Please run /login\n')
            result['exit_code'] = 1
        return result
    report = runner.run('heron', project(tmp_path), 'fixture', execute)
    assert report['status'] == 'failed' and report['void_calls'] == 0 and report['interrupted_calls'] == 0
    assert report['turns'][0]['void'] is None and report['turns'][0]['slot_consumed'] is True
    assert report['slots_spent'] == 1 and 'retry' not in report
    # An untagged synthetic frame that does carry limit text is still a limit.
    untagged = {'type': 'assistant', 'message': {'model': '<synthetic>', 'role': 'assistant',
                                                 'content': [{'type': 'text', 'text': LIMIT_TEXT}]}}
    frames_file(transcript, [untagged])
    assert runner.void_reason(transcript)['signals'] == [{'frame': 'assistant', 'error': None,
                                                          'model': '<synthetic>'}]
    assert runner.void_reason(transcript)['model_messages_before_limit'] == 0


@pytest.mark.parametrize('shape', ['stream', 'legacy', 'envelope_only', 'stderr_only'])
def test_void_reason_recognises_every_retained_limit_shape(tmp_path, shape):
    """The six ot7 calls came in two transcript shapes; the classifier reads both, and the text alone."""
    transcript, envelope, stderr = tmp_path / 't.jsonl', tmp_path / 'e.json', tmp_path / 's.txt'
    if shape == 'stream':
        frames_file(transcript, [{'type': 'system', 'subtype': 'init'}, REJECTED, SYNTHETIC, LIMIT_RESULT])
    elif shape == 'legacy':
        frames_file(transcript, [{'type': 'user'}, {'type': 'attachment'}, SYNTHETIC, {'type': 'last-prompt'}])
    elif shape == 'envelope_only':
        frames_file(transcript, [])
        runner.write(envelope, {'ok': False, 'error': LIMIT_TEXT})
        stderr.write_text('irrelevant\n')
    else:
        frames_file(transcript, [])
        stderr.write_text("Usage limit reached for this account\n")
    reason = runner.void_reason(transcript, envelope, stderr)
    assert reason['kind'] == 'usage_limit' and reason['rule'] == 'ADR-355'
    assert reason['slot_consumed'] is False and reason['cut_off_mid_turn'] is False
    assert runner.classify(transcript, envelope, stderr)['void'] == reason


@pytest.mark.parametrize('name,expected', [('ot7-heron', 'ot7-heron-b'), ('ot7-heron-b', 'ot7-heron-c'),
                                           ('ot7-heron-repair', 'ot7-heron-repair-b'),
                                           ('ot7-heron-repair-b', 'ot7-heron-repair-c')])
def test_retry_project_name(name, expected):
    assert runner.retry_project_name(name) == expected


def test_all_six_ot7_calls_are_classified_void():
    receipt = json.loads((PATH.parents[1] / 'attempts/void-calls.json').read_text())
    assert receipt['rule'] == 'ADR-355' and len(receipt['calls']) == 6
    assert all(call['void']['kind'] == 'usage_limit' and call['void']['slot_consumed'] is False
               for call in receipt['calls'])
    assert all(call['void']['cut_off_mid_turn'] is False for call in receipt['calls'])
    assert {call['transcript']['sha256'] for call in receipt['calls']} == {
        '7f4238888d0925e0fb3a5d2810843a3d01a7103a4155b3ea0ec0a7f07f4bd455',
        '5c41384de5d7c3b129467c5a63b9d6980de88507f02cd31ce7a4a6fed09cf19e',
        '75cedbfd888448b5568bc17abf8bd7afe36b8905ffdf34869ad95cc28465323e',
        '813e77ee6c0183c17e4a54dec380f83524ae4183ce763f0bfe7aab3ee9c0dedb',
        '01566753ac81f189b21cc565b300fc00f8d63e4cf63d985989d3663b6b490674',
        'b5b359ec0d0f5465cd1e8520701e3d7c17285881823ed028b03e13996434ea59'}
    assert sum(1 for call in receipt['calls'] if call['criterion'] == 'F4') == 3
