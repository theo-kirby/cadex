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
