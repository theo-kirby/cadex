# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The ot7 collector, reused for run ot8 (ADR-400).

Two things this extension must not get wrong. **Slot accounting**: an ot8
design gets one initial prompt and at most three continuations, and only a
turn that reached the model and ended on its own spends one -- void,
interrupted and unreached calls spend nothing, exactly as in ot7.
**Preserving prior evidence**: two of the three ot8 designs start from a copy
of an ot7 project, which arrives carrying that project's own ``evidence/``
directory and its accepted design; the attempt must write beside them, refuse
a copy that is not the pinned baseline, and leave both untouched.
"""
import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / 'docs/probes/ot7/runner/run.py'
spec = importlib.util.spec_from_file_location('ot8_runner', PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

BASELINE = {'plover': {'script': 'the accepted biped fixture\n',
                       'revision': 'plover-revision', 'digest': 'plover-digest'},
            'robin': {'script': 'the accepted balancer fixture\n',
                      'revision': 'robin-revision', 'digest': 'robin-digest'}}


def project(tmp_path, name='ot8-heron'):
    root = tmp_path / 'cadex-projects'
    root.mkdir(exist_ok=True)
    return root / name


def executor(calls, turn_code=0, smoke_code=0):
    def execute(command, out, stem, timeout):
        calls.append((command, timeout))
        if stem == 'turn':
            # The prompt slot is durable before the provider is invoked.
            receipt = json.loads((out.parent / 'attempt.json').read_text())
            assert receipt['turns'][-1]['status'] == 'started'
            (out / 'transcript.jsonl').write_text('{"type":"result"}\n')
        elif stem == 'measurement':
            runner.write(out / 'fit.json', {'verdict': 'pass', 'failing_count': 0,
                                            'pairs_checked': 406})
            runner.write(out / 'clearance.json', {'pairs': []})
            runner.write(out / 'inventory.json', {'component_count': 29})
        elif stem == 'smoke':
            runner.write(out / 'smoke.json', {'verdict': 'fail' if smoke_code else 'pass'})
            return {'exit_code': smoke_code, 'elapsed_seconds': 0.01}
        return {'exit_code': turn_code if stem == 'turn' else 0, 'elapsed_seconds': 0.01}
    return execute


def seeded(tmp_path, monkeypatch, design='plover'):
    """A copy of an ot7 baseline, as the operator prepares one: the accepted
    design, and the source project's own evidence directory riding along."""
    target = project(tmp_path, f'ot8-{design}')
    target.mkdir()
    pin = BASELINE[design]
    (target / 'script.py').write_text(pin['script'])
    runner.write(target / 'script.json', {
        'accepted_revision': pin['revision'], 'working_revision': pin['revision'],
        'accepted_digest': pin['digest'], 'param_values': {'leg_len': 40.0},
        'board_values': [], 'cage_values': [], 'mount_values': [], 'net_values': []})
    inherited = target / 'evidence'
    inherited.mkdir()
    runner.write(inherited / 'attempt.json', {'schema': 'ot7-design-evidence-v1',
                                              'design': design, 'project': f'ot7-{design}-x',
                                              'turns': [], 'status': 'exhausted'})
    (inherited / 'turn-0').mkdir()
    (inherited / 'turn-0' / 'transcript.jsonl').write_text('{"type":"result"}\n')
    baselines = tmp_path / 'baselines.json'
    runner.write(baselines, {'baselines': {name: {
        'project': f'ot7-{name}-x', 'role': 'seed',
        'script_sha256': runner.digest(target / 'script.py')['sha256']
        if name == design else 'other',
        'accepted_revision': BASELINE[name]['revision'],
        'accepted_digest': BASELINE[name]['digest']} for name in BASELINE}})
    monkeypatch.setattr(runner, 'OT8_BASELINES', baselines)
    return target


# ---------------------------------------------------------------- slots


def test_the_arm_gets_one_create_and_exactly_three_continuations(tmp_path):
    target = project(tmp_path)
    calls = []
    report = runner.run('heron', target, 'fixture', executor(calls), run_id='ot8')
    turns = [cmd for cmd, _ in calls if '--child-turn' in cmd]
    assert [Path(cmd[-2]).name for cmd in turns] == runner.frozen('heron', 'ot8')
    assert len(turns) == 4
    assert report['run'] == 'ot8' and report['status'] == 'exhausted'
    assert [r['continuations_used'] for r in report['turns']] == [0, 1, 2, 3]
    assert report['slots_spent'] == 4
    assert report['remaining'] == {'completed': 4, 'continuations_used': 3,
                                   'continuations_unspent': 0, 'next_prompt': None,
                                   'closed': None}
    # The prompts came from ot8's freeze, byte for byte.
    for name in runner.frozen('heron', 'ot8'):
        index = runner.frozen('heron', 'ot8').index(name)
        assert (target / f'evidence/turn-{index}' / name).read_bytes() == \
            (runner.OT8_PROMPTS / name).read_bytes()
    with pytest.raises(FileExistsError):
        runner.run('heron', target, 'fixture', executor(calls), run_id='ot8')


@pytest.mark.parametrize('code,kind', [('timeout', 'runner_timeout'),
                                       ('launch_failed', 'launch_failed')])
def test_an_interrupted_ot8_call_spends_no_slot_and_retries_in_an_ot8_project(tmp_path, code, kind):
    calls = []
    report = runner.run('heron', project(tmp_path), 'fixture', executor(calls, code), run_id='ot8')
    row = report['turns'][0]
    assert row['status'] == 'interrupted' and row['slot_consumed'] is False
    assert row['interruption']['kind'] == kind and row['continuations_used'] == 0
    assert report['slots_spent'] == 0 and report['interrupted_calls'] == 1
    assert report['retry']['project'] == 'ot8-heron-b'
    assert report['retry']['prompt'] == 'heron.create.prompt.txt'


def test_a_void_ot8_call_spends_no_slot(tmp_path):
    calls = []
    def execute(command, out, stem, timeout):
        result = executor(calls)(command, out, stem, timeout)
        if stem == 'turn':
            (out / 'transcript.jsonl').write_text(json.dumps(
                {'type': 'rate_limit_event',
                 'rate_limit_info': {'status': 'rejected', 'rateLimitType': 'five_hour'}}) + '\n')
        return result
    report = runner.run('heron', project(tmp_path), 'fixture', execute, run_id='ot8')
    row = report['turns'][0]
    assert row['status'] == 'void' and row['slot_consumed'] is False
    assert report['slots_spent'] == 0 and report['void_calls'] == 1
    # The project is closed by the void call and its unspent budget moves with
    # the frozen prompt to the retry project, rather than being counted here.
    assert report['remaining']['closed'] == 'void'
    assert report['retry']['project'] == 'ot8-heron-b'
    assert report['retry']['prompt'] == 'heron.create.prompt.txt'


def test_an_unreached_ot8_call_keeps_its_prompt_next_in_the_same_project(tmp_path):
    calls = []
    def execute(command, out, stem, timeout):
        result = executor(calls)(command, out, stem, timeout)
        if stem == 'turn':
            (out / 'transcript.jsonl').write_text('')
            runner.write(out / 'turn.stdout.json', {'error': 'open_project refused', 'session_id': ''})
            result['exit_code'] = 2
        return result
    report = runner.run('heron', project(tmp_path), 'fixture', execute, run_id='ot8')
    row = report['turns'][0]
    assert row['status'] == 'unreached' and row['slot_consumed'] is False
    assert report['slots_spent'] == 0 and report['unreached_calls'] == 1
    assert report['status'] == 'paused' and 'retry' not in report
    assert report['remaining']['next_prompt'] == 'heron.create.prompt.txt'
    assert report['remaining']['continuations_unspent'] == 3


def test_a_seeded_ot8_design_spends_its_first_prompt_and_keeps_three(tmp_path, monkeypatch):
    target = seeded(tmp_path, monkeypatch, 'robin')
    calls = []
    report = runner.run('robin', target, 'fixture', executor(calls), run_id='ot8')
    assert [Path(cmd[-2]).name for cmd, _ in calls if '--child-turn' in cmd] == \
        ['resolve.prompt.txt']
    assert report['slots_spent'] == 1 and report['status'] == 'paused'
    assert report['remaining'] == {'completed': 1, 'continuations_used': 0,
                                   'continuations_unspent': 3,
                                   'next_prompt': 'continue-1.prompt.txt', 'closed': None}
    resumed = runner.resume(target, executor(calls), turns=3)
    assert [r['continuations_used'] for r in resumed['turns']] == [0, 1, 2, 3]
    assert resumed['status'] == 'exhausted' and resumed['slots_spent'] == 4
    with pytest.raises(ValueError, match='exhausted'):
        runner.resume(target, executor(calls))


def test_an_ot8_receipt_records_its_run_and_an_ot7_one_still_reads_as_ot7():
    assert runner.remaining({'design': 'heron', 'run': 'ot8', 'turns': [], 'status': 'running'}
                            )['next_prompt'] == 'heron.create.prompt.txt'
    assert runner.remaining({'design': 'robin', 'run': 'ot8', 'turns': [], 'status': 'running'}
                            )['next_prompt'] == 'resolve.prompt.txt'
    # A receipt written before ADR-400 has no `run` key and is ot7's.
    assert runner.remaining({'design': 'robin', 'turns': [], 'status': 'running'}
                            )['next_prompt'] == 'robin.create.prompt.txt'


# ------------------------------------------------- preserving prior evidence


def test_a_seeded_attempt_writes_beside_the_copys_evidence_and_leaves_it_alone(tmp_path, monkeypatch):
    target = seeded(tmp_path, monkeypatch)
    inherited = runner.digest(target / 'evidence/attempt.json')
    before = runner.seed_identity(target)
    calls = []
    report = runner.run('plover', target, 'fixture', executor(calls), run_id='ot8')
    assert (target / 'evidence/g3-rebuild/attempt.json').is_file()
    assert runner.digest(target / 'evidence/attempt.json') == inherited
    assert (target / 'evidence/turn-0/transcript.jsonl').read_text() == '{"type":"result"}\n'
    assert runner.attempt_dir(target).name == 'g3-rebuild'
    # The design is unchanged by every measurement the attempt took.
    assert runner.seed_identity(target) == before == report['seed']
    assert report['before']['seed_unchanged'] is True
    assert report['turns'][0]['accepted_after'] == before


def test_a_seeded_attempt_measures_and_smokes_the_baseline_before_any_turn(tmp_path, monkeypatch):
    target = seeded(tmp_path, monkeypatch)
    calls = []
    runner.run('plover', target, 'fixture', executor(calls), run_id='ot8')
    def kind(command):
        if command[0].endswith('cadex'):
            return command[1]
        return 'measurement' if '--child-measure' in command else 'turn'
    assert [kind(command) for command, _ in calls][:3] == ['measurement', 'smoke', 'turn']
    receipt = json.loads((target / 'evidence/g3-rebuild/attempt.json').read_text())
    assert receipt['before']['smoke']['evidence_dir'] == 'smoke-before'
    assert {a['path'] for a in receipt['before']['smoke']['artifacts']} == {'smoke.json'}
    assert {a['path'] for a in receipt['before']['artifacts']} >= {'fit.json', 'inventory.json'}
    assert 'repair_assessment' not in receipt['before']


def test_a_failing_baseline_smoke_is_evidence_and_never_a_gate(tmp_path, monkeypatch):
    """G3 and G4 exist because these baselines fail this smoke; a failure here
    must reach the report rather than stop the experiment."""
    target = seeded(tmp_path, monkeypatch, 'robin')
    calls = []
    report = runner.run('robin', target, 'fixture', executor(calls, smoke_code=1), run_id='ot8')
    assert report['before']['smoke']['exit_code'] == 1
    assert report['status'] == 'paused' and report['slots_spent'] == 1
    assert [Path(cmd[-2]).name for cmd, _ in calls if '--child-turn' in cmd] == \
        ['resolve.prompt.txt']


@pytest.mark.parametrize('change', ['script', 'accepted_revision', 'accepted_digest',
                                    'working_revision'])
def test_a_seeded_attempt_refuses_a_copy_that_is_not_the_pinned_baseline(tmp_path, monkeypatch,
                                                                        change):
    target = seeded(tmp_path, monkeypatch)
    if change == 'script':
        (target / 'script.py').write_text('a copy of something else\n')
    else:
        metadata = json.loads((target / 'script.json').read_text())
        metadata[change] = 'changed'
        runner.write(target / 'script.json', metadata)
    with pytest.raises(ValueError, match='identity'):
        runner.run('plover', target, 'fixture', run_id='ot8')
    assert not (target / 'evidence/g3-rebuild').exists()
    assert (target / 'evidence/attempt.json').is_file()  # the copy's own is untouched


def test_a_seeded_attempt_that_cannot_measure_its_baseline_sends_no_prompt(tmp_path, monkeypatch):
    target = seeded(tmp_path, monkeypatch)
    calls = []
    def execute(command, out, stem, timeout):
        result = executor(calls)(command, out, stem, timeout)
        if stem == 'measurement':
            (out / 'fit.json').unlink()
        return result
    report = runner.run('plover', target, 'fixture', execute, run_id='ot8')
    assert report['status'] == 'before_unavailable' and report['turns'] == []
    assert not any('--child-turn' in cmd for cmd, _ in calls)


def test_a_mutating_baseline_measurement_sends_no_prompt(tmp_path, monkeypatch):
    target = seeded(tmp_path, monkeypatch)
    calls = []
    def execute(command, out, stem, timeout):
        result = executor(calls)(command, out, stem, timeout)
        if stem == 'smoke':
            (target / 'script.py').write_text('an unexpected mutation\n')
        return result
    report = runner.run('plover', target, 'fixture', execute, run_id='ot8')
    assert report['before']['seed_unchanged'] is False
    assert report['status'] == 'before_unavailable' and report['turns'] == []
    assert not any('--child-turn' in cmd for cmd, _ in calls)


def test_an_ot8_attempt_refuses_an_ot7_project_name_and_the_reverse(tmp_path):
    with pytest.raises(ValueError, match='ot8-'):
        runner.run('heron', project(tmp_path, 'ot7-heron-c'), 'fixture', run_id='ot8')
    with pytest.raises(ValueError, match='ot7-'):
        runner.run('heron', project(tmp_path, 'ot8-heron'), 'fixture')
    assert not (tmp_path / 'cadex-projects/ot7-heron-c').exists()
    assert not (tmp_path / 'cadex-projects/ot8-heron').exists()


def test_a_changed_ot8_prompt_cannot_launch_and_ot7s_freeze_is_independent(tmp_path, monkeypatch):
    prompts = tmp_path / 'prompts'
    prompts.mkdir()
    for file in runner.OT8_PROMPTS.iterdir():
        (prompts / file.name).write_bytes(file.read_bytes())
    (prompts / 'continue-3.prompt.txt').write_text('changed')
    monkeypatch.setattr(runner, 'OT8_PROMPTS', prompts)
    target = project(tmp_path)
    with pytest.raises(ValueError, match='frozen prompt changed'):
        runner.run('heron', target, 'fixture', run_id='ot8')
    assert not target.exists()
    # ot7's freeze reads its own directory and is unaffected.
    assert runner.frozen('heron') == ['heron.create.prompt.txt', 'continue-1.prompt.txt',
                                      'continue-2.prompt.txt', 'continue-3.prompt.txt']


def test_an_interim_smoke_on_a_seeded_ot8_attempt_spends_no_slot(tmp_path, monkeypatch):
    """G3's smoke against the accepted pin is a measurement, not a design turn."""
    target = seeded(tmp_path, monkeypatch)
    calls = []
    runner.run('plover', target, 'fixture', executor(calls), run_id='ot8')
    taken = runner.smoke(target, executor(calls))
    assert taken['smoke']['slot_consumed'] is False
    assert taken['smoke']['evidence_dir'] == 'smoke-interim'
    assert taken['remaining']['continuations_unspent'] == 3
    receipt = json.loads((target / 'evidence/g3-rebuild/attempt.json').read_text())
    assert receipt['slots_spent'] == 1
    assert [s['evidence_dir'] for s in receipt['interim_smokes']] == ['smoke-interim']


# ------------------------------------------------------ the contract document


def _contract():
    return (Path(__file__).resolve().parents[2] / 'docs/probes/ot8/README.md').read_text()


def test_the_contract_names_the_schedule_the_collector_actually_dispatches():
    """G1's document and the collector may not drift apart."""
    text = _contract()
    for design, criterion in [('heron', 'G2 arm'), ('plover', 'G3 biped'), ('robin', 'G4 balancer')]:
        first = runner.frozen(design, 'ot8')[0]
        assert f'| {criterion} | `{first}` |' in text, criterion
    assert 'one initial product prompt and at most three\ncontinuations' in text


def test_the_contract_pins_the_same_baselines_the_collector_refuses_without():
    text = _contract()
    pins = json.loads(runner.OT8_BASELINES.read_text())['baselines']
    assert set(pins) == {'heron', 'plover', 'robin'}
    for design, pin in pins.items():
        assert f"| `{pin['project']}` | `{pin['accepted_revision'][:8]}…` | " \
               f"`{pin['accepted_digest'][:8]}…` |" in text, design
        if pin['role'] == 'seed':
            assert runner.SEEDED[('ot8', design)]['prompt'] == runner.frozen(design, 'ot8')[0]
        else:
            assert ('ot8', design) not in runner.SEEDED


def test_the_contract_ledger_says_what_each_class_of_call_costs():
    text = _contract()
    for column, spends in [('completed', True), ('failed', True), ('void', False),
                           ('interrupted', False), ('unreached', False)]:
        row = next((line for line in text.splitlines()
                    if line.startswith(f'| **{column}**')), None)
        assert row is not None, column
        assert ('**spent**' in row) is spends, column
        assert ('unspent' in row) is not spends, column
    # The three unspent classes are the collector's own, by rule.
    assert 'ADR-355' in text and 'ADR-356' in text and 'ADR-386' in text
