# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bounded, project-local evidence collection for the frozen ot7 attempts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
from pathlib import Path
import re
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[4]
PROMPTS = REPO / 'docs/probes/ot7/prompts'
sys.path.insert(0, str(REPO / 'cli'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def digest(path):
    return {'path': path.name, 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def frozen(design):
    names = (['repair.prompt.txt'] if design == 'repair' else
             [f'{design}.create.prompt.txt'] + [f'continue-{i}.prompt.txt' for i in range(1, 4)])
    table = dict(re.findall(r'\| `([^`]+\.prompt\.txt)` \| .*? \| \d+ \| `([a-f0-9]{64})`',
                            (PROMPTS / 'README.md').read_text()))
    for name in names:
        if digest(PROMPTS / name)['sha256'] != table[name]:
            raise ValueError(f'frozen prompt changed: {name}')
    return names


def child_turn(project, out, prompt, model):
    from cadex_cli import __main__ as cli
    from cadex_cli.agent import ClaudeTurn, TurnResult, find_claude

    original = cli.command_prompt

    class CapturedTurn(ClaudeTurn):
        def __init__(self, **kwargs):
            kwargs['claude_path'] = find_claude('')
            super().__init__(**kwargs)
            self.invoked = False

        def run(self, text):
            if self.invoked:
                write(out / 'blocked-followup.json', {'reason': 'Only the frozen prompt is authorized.'})
                return TurnResult(error='unfrozen automatic follow-up blocked')
            self.invoked = True
            result = super().run(text)
            with (out / 'transcript.jsonl').open('w') as stream:
                for frame in result.frames:
                    stream.write(json.dumps(frame) + '\n')
            return result

    cli.command_prompt = lambda args, report: original(args, report, turn_factory=CapturedTurn)
    args = ['--project', str(project), '--json', '--model', model,
            '--out', str(out / 'exports'), '-p', prompt.read_text()]
    if prompt.name.startswith('continue-'):
        args.append('--resume')
    try:
        return cli.main(args)
    finally:
        cli.command_prompt = original


def child_measure(project, out):
    from cadex_cli import __main__ as cli
    from cadex_cli.clearance import fit_summary
    from cadex_cli.inventory import _read_path
    from cadex_cli.report import RunReport
    args = cli.build_parser().parse_args(['clearance', '--project', str(project)])
    with cli._engine_session(args, RunReport(), restore=False) as (_, client):
        value = _read_path(client, {'scope': 'clearance', 'target': ''}, '')
        write(out / 'clearance.json', value)
        write(out / 'fit.json', fit_summary(value))
        write(out / 'inventory.json', _read_path(client, {'scope': 'inventory', 'target': ''}, ''))
    return 0


LIMIT_TEXT = re.compile(r"hit your [a-z ]*limit|session limit|usage limit|rate limit|"
                        r"out of credits|credit balance|insufficient credits", re.I)


def read_frames(path):
    frames = []
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        return frames
    for line in lines:
        try:
            frame = json.loads(line)
        except ValueError:
            continue
        if isinstance(frame, dict):
            frames.append(frame)
    return frames


def void_reason(transcript, envelope=None, stderr=None):
    """Why a call is void under ADR-355, or None when it reached the model and ended on its own.

    A provider usage, session or credit limit is recognised from any of the
    shapes the retained ot7 calls carry: a rejected ``rate_limit_event``, a
    synthetic assistant frame tagged ``rate_limit``, an HTTP 429 error result,
    or limit text in the CLI envelope or stderr. A limit that lands after the
    model has already spoken is still void: the turn did not end on its own.
    """
    signals, spoke = [], 0
    for frame in read_frames(transcript):
        kind = frame.get('type')
        if kind == 'rate_limit_event':
            info = frame.get('rate_limit_info') or {}
            if info.get('status') == 'rejected':
                signals.append({'frame': 'rate_limit_event', 'status': 'rejected',
                                'limit': info.get('rateLimitType'), 'resets_at': info.get('resetsAt')})
        elif kind == 'assistant':
            if frame.get('error') == 'rate_limit' or (frame.get('message') or {}).get('model') == '<synthetic>':
                signals.append({'frame': 'assistant', 'error': frame.get('error'),
                                'model': (frame.get('message') or {}).get('model')})
            else:
                spoke += 1 if not signals else 0
        elif kind == 'result' and frame.get('is_error'):
            text = frame.get('result') if isinstance(frame.get('result'), str) else ''
            if frame.get('api_error_status') == 429 or LIMIT_TEXT.search(text):
                signals.append({'frame': 'result', 'api_error_status': frame.get('api_error_status'),
                                'text': text[:200]})
    # The CLI envelope's error field is empty on an ordinary turn; stderr is
    # consulted only when no envelope was written, so progress output that
    # happens to mention a limit cannot void a completed turn.
    text = None
    if envelope is not None and Path(envelope).is_file():
        try:
            text = str(json.loads(Path(envelope).read_text()).get('error') or '')
        except (ValueError, AttributeError):
            text = None
    if text is None and stderr is not None and Path(stderr).is_file():
        text = '\n'.join(Path(stderr).read_text(errors='replace').strip().splitlines()[-20:])
    if text and LIMIT_TEXT.search(text):
        signals.append({'frame': 'envelope' if envelope and Path(envelope).is_file() else 'stderr',
                        'text': text.strip()[:200]})
    if not signals:
        return None
    return {'kind': 'usage_limit', 'rule': 'ADR-355', 'slot_consumed': False,
            'cut_off_mid_turn': spoke > 0, 'model_messages_before_limit': spoke,
            'signals': signals}


def retry_project_name(name):
    """The fresh, letter-suffixed project a void call is retried in (ADR-355)."""
    match = re.fullmatch(r'(.*)-([a-y])', name)
    return f'{match.group(1)}-{chr(ord(match.group(2)) + 1)}' if match else f'{name}-b'


def classify(transcript, envelope=None, stderr=None):
    transcript = Path(transcript)
    if envelope is None and (transcript.parent / 'turn.stdout.json').is_file():
        envelope = transcript.parent / 'turn.stdout.json'
    if stderr is None and (transcript.parent / 'turn.stderr.txt').is_file():
        stderr = transcript.parent / 'turn.stderr.txt'
    return {'transcript': digest(transcript), 'void': void_reason(transcript, envelope, stderr)}


def execute(command, out, stem, timeout):
    start = time.monotonic()
    with (out / f'{stem}.stdout.json').open('w') as stdout, (out / f'{stem}.stderr.txt').open('w') as stderr:
        try:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            code = 'timeout'
        except OSError as exc:
            stderr.write(str(exc))
            code = 'launch_failed'
    return {'exit_code': code, 'elapsed_seconds': time.monotonic() - start}


REPAIR_ATTACHMENTS = (
    ('comp_horn_shoulder', 'comp_upper_arm'),
    ('comp_horn_elbow', 'comp_forearm'),
)


def repair_assessment(value, expected_revision):
    """Assess original attachments even when the seed declares no contact intent.

    This is evidence interpretation, never a design declaration or acceptance.
    Renamed/replaced components require separate evidence; do not infer identity.
    """
    from cadex_cli.clearance import fit_summary, pair_status, MAXIMUM_COMMON_VOLUME_MM3

    value = value if isinstance(value, dict) else {}
    valid = (bool(expected_revision) and value.get('revision') == expected_revision
             and value.get('available') is True and isinstance(value.get('pairs'), list)
             and bool(value['pairs']) and isinstance(value.get('world_geometry'), list))
    summary = fit_summary(value) if valid else None
    static = summary['verdict'] if summary else 'unknown'
    attachments = []
    for first, second in REPAIR_ATTACHMENTS:
        rows = [row for row in value.get('pairs', []) if isinstance(row, dict)
                and {row.get('first'), row.get('second')} == {first, second}] if valid else []
        item = {'first': first, 'second': second, 'status': 'unknown',
                'reason': 'Missing, duplicate, or unverified accepted pair evidence.'}
        if len(rows) == 1:
            row = rows[0]
            status = pair_status(dict(row, intent={'kind': 'contact'}),
                                 0.1, MAXIMUM_COMMON_VOLUME_MM3)
            item.update(status='pass' if status == 'clear' else
                        'unknown' if status == 'unknown' else 'fail', reason=status,
                        distance_mm=row.get('distance_mm'),
                        common_volume_mm3=row.get('common_volume_mm3'))
        attachments.append(item)
    statuses = [static] + [item['status'] for item in attachments]
    return {'revision': value.get('revision'), 'expected_revision': expected_revision,
            'status': 'fail' if 'fail' in statuses else
                      'pass' if all(s == 'pass' for s in statuses) else 'unknown',
            'static_fit': summary, 'attachments': attachments,
            'contact_tolerance_mm': 0.001,
            'maximum_common_volume_mm3': MAXIMUM_COMMON_VOLUME_MM3,
            'scope': 'Static geometry only; not proof of an agent repair or swept fit.'}


def retain_repair_assessment(out, revision, measurement_ok):
    try:
        value = json.loads((out / 'clearance.json').read_text()) if measurement_ok else None
    except (OSError, ValueError):
        value = None
    assessment = repair_assessment(value, revision)
    # Unknown numeric evidence stays in the raw report; receipt JSON remains finite.
    assessment = json.loads(json.dumps(assessment), parse_constant=lambda _: None)
    write(out / 'repair-assessment.json', assessment)
    return assessment


def run(design, project, model, execute_call=execute):
    names = frozen(design)
    project = project.resolve()
    if project.is_relative_to(REPO) or project.parent.name != 'cadex-projects' or not project.name.startswith('ot7-'):
        raise ValueError('Use a new ot7-* project in the external cadex-projects directory.')
    repair = design == 'repair'
    if repair:
        seed = seed_identity(project)
        validate_seed(seed)
    else:
        project.mkdir()
    # Exclusive evidence creation guards the preserved seed against redispatch.
    evidence = project / 'evidence' / 'f4-repair' if repair else project / 'evidence'
    evidence.mkdir()
    receipt = {'schema': 'ot7-design-evidence-v1', 'design': design, 'project': project.name,
               'model': model, 'actor_design_edits': 0, 'turns': [], 'status': 'running',
               'slots_spent': 0, 'void_calls': 0}
    save = lambda: write(evidence / 'attempt.json', receipt)
    save()
    if repair:
        receipt['seed'] = seed
        save()
        before = evidence / 'before'
        before.mkdir()
        receipt['before'] = execute_call(
            [sys.executable, str(Path(__file__).resolve()), '--child-measure', str(project), str(before)],
            before, 'measurement', 300)
        receipt['before']['repair_assessment'] = retain_repair_assessment(
            before, seed['metadata']['accepted_revision'], receipt['before']['exit_code'] == 0)
        receipt['before']['artifacts'] = [digest(p) for p in sorted(before.iterdir()) if p.is_file()]
        # Measurement must preserve the complete metadata and script bytes.
        receipt['before']['seed_unchanged'] = seed_identity(project) == seed
        if (receipt['before']['exit_code'] != 0 or
                not all((before / name).is_file() for name in ('fit.json', 'clearance.json')) or
                not receipt['before']['seed_unchanged']):
            receipt['status'] = 'before_unavailable'
            save()
            return receipt
        save()
    continuations = 0
    for index, name in enumerate(names):
        out = evidence / f'turn-{index}'
        out.mkdir()
        prompt = out / name
        prompt.write_bytes((PROMPTS / name).read_bytes())
        counts = repair or index > 0  # the create prompt is not a continuation
        row = {'index': index, 'continuations_used': continuations + counts,
               'prompt': digest(prompt), 'status': 'started'}
        receipt['turns'].append(row)
        save()  # Persist the slot before launching the provider; a void call gives it back.
        row['turn'] = execute_call([sys.executable, str(Path(__file__).resolve()), '--child-turn',
                                   str(project), str(out), str(prompt), model], out, 'turn', 1800)
        row['void'] = void_reason(out / 'transcript.jsonl', out / 'turn.stdout.json', out / 'turn.stderr.txt')
        row['measurement'] = execute_call([sys.executable, str(Path(__file__).resolve()), '--child-measure',
                                          str(project), str(out)], out, 'measurement', 300)
        if (out / 'fit.json').exists():
            fit = json.loads((out / 'fit.json').read_text())
            row['static_fit'] = {key: fit[key] for key in ('verdict', 'failing_count', 'pairs_checked')}
        if row['void']:
            # ADR-355: no model saw the prompt, or the turn did not end on its
            # own. The slot is unspent, the evidence stays, and nothing else is
            # dispatched from this project.
            row['status'] = 'void'
            row['slot_consumed'] = False
            row['continuations_used'] = continuations
            receipt['void_calls'] += 1
        else:
            row['status'] = 'completed'
            row['slot_consumed'] = True
            continuations += counts
            receipt['slots_spent'] += 1
        if repair:
            row['accepted_after'] = seed_identity(project)
            row['repair_assessment'] = retain_repair_assessment(
                out, row['accepted_after']['metadata'].get('accepted_revision'),
                row['measurement']['exit_code'] == 0)
        row['artifacts'] = [digest(p) for p in sorted(out.iterdir()) if p.is_file()]
        save()
        if row['void']:
            receipt['status'] = 'void'
            receipt['retry'] = {'rule': 'ADR-355', 'prompt': name, 'project': retry_project_name(project.name),
                                'note': 'Same frozen prompt, fresh project or fresh seed copy, '
                                        'only while the product agent is available.'}
            break
        # Provider failures and ambiguous interrupted turns stop this attempt.
        if row['turn']['exit_code'] not in (0, 3) or (out / 'blocked-followup.json').exists():
            receipt['status'] = 'interrupted'
            break
    else:
        receipt['status'] = 'exhausted'
    if repair or receipt['status'] == 'void':
        save()
        return receipt
    # One bounded smoke, even on a failing fit; it never modifies the design.
    smoke = evidence / 'smoke'
    smoke.mkdir()
    receipt['smoke'] = execute_call([str(REPO / 'cadex'), 'smoke', '--project', str(project),
                                    '--out', str(smoke), '--seconds', '1', '--timeout', '240', '--json'],
                                   smoke, 'smoke', 300)
    receipt['smoke']['artifacts'] = [digest(p) for p in sorted(smoke.iterdir()) if p.is_file()]
    save()
    return receipt


def seed_identity(project):
    return {'script_sha256': digest(project / 'script.py')['sha256'],
            'metadata': json.loads((project / 'script.json').read_text())}


def validate_seed(seed):
    original = json.loads((REPO / 'docs/probes/ot7/retained/repair-refusal.json').read_text())['seed']
    metadata = seed['metadata']
    if (seed['script_sha256'] != original['script_sha256'] or
            metadata.get('accepted_revision') != original['accepted_revision'] or
            metadata.get('working_revision') != original['accepted_revision'] or
            metadata.get('accepted_digest') != 'ce35f4d3ae95b082ec54d862d8bc2fbfe59898cd37ddb30d4416918bfbc9603c' or
            any(metadata.get(key) != value for key, value in
                {'board_values': [], 'cage_values': [], 'mount_values': [],
                 'net_values': [], 'param_values': {}}.items())):
        raise ValueError('F4 requires the preserved first Heron seed identity.')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child-turn':
        sys.exit(child_turn(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]))
    if len(sys.argv) > 1 and sys.argv[1] == '--child-measure':
        sys.exit(child_measure(Path(sys.argv[2]), Path(sys.argv[3])))
    if len(sys.argv) > 1 and sys.argv[1] == '--classify':
        # Read-only: is a retained call void under ADR-355? Takes a transcript
        # and, optionally, the CLI envelope and stderr beside it.
        print(json.dumps(classify(*sys.argv[2:5]), indent=2))
        sys.exit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('design', choices=['heron', 'robin', 'plover', 'repair'])
    parser.add_argument('project', type=Path)
    parser.add_argument('--model', default='claude-fable-5')
    args = parser.parse_args()
    print(json.dumps(run(args.design, args.project, args.model), indent=2))
