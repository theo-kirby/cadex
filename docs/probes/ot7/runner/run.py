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

#: The wall-clock bound on one product-agent call. A call killed here is an
#: interruption, not a turn that ended on its own (ADR-356).
TURN_BOUND_SECONDS = 1800
MEASUREMENT_BOUND_SECONDS = 300


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def digest(path):
    return {'path': path.name, 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def frozen(design):
    # The first prompt is the create prompt, or the repair prompt on the
    # preserved seed; each is followed by the same three continuations
    # (ADR-357: the repair prompt is not itself a continuation).
    first = 'repair.prompt.txt' if design == 'repair' else f'{design}.create.prompt.txt'
    names = [first] + [f'continue-{i}.prompt.txt' for i in range(1, 4)]
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

        def _absorb(self, frame, result):
            # Written as each frame arrives, so a call killed at the runner's
            # bound keeps every frame it had produced (ADR-356). A stale-session
            # retry appends its stream after the first attempt's.
            with (out / 'transcript.jsonl').open('a') as stream:
                stream.write(json.dumps(frame) + '\n')
            super()._absorb(frame, result)

        def run(self, text):
            if self.invoked:
                write(out / 'blocked-followup.json', {'reason': 'Only the frozen prompt is authorized.'})
                return TurnResult(error='unfrozen automatic follow-up blocked')
            self.invoked = True
            return super().run(text)

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


def frame_text(message):
    """The text blocks of an assistant message, joined; empty when there are none."""
    content = message.get('content')
    if isinstance(content, str):
        return content
    return ' '.join(block.get('text', '') for block in (content or [])
                    if isinstance(block, dict) and block.get('type') == 'text')


def void_reason(transcript, envelope=None, stderr=None):
    """Why a call is void under ADR-355, or None when it reached the model and ended on its own.

    A provider usage, session or credit limit is recognised from any of the
    shapes the retained ot7 calls carry: a rejected ``rate_limit_event``, a
    synthetic assistant frame tagged ``error: rate_limit`` (or, untagged,
    carrying limit text), an HTTP 429 error result, or limit text in the CLI
    envelope or stderr. A synthetic frame alone is not evidence: an
    ``authentication_failed`` frame is an ordinary failure and spends its slot.
    A limit that lands after the model has already spoken is still void: the
    turn did not end on its own.
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
            message = frame.get('message') or {}
            synthetic = message.get('model') == '<synthetic>'
            # A synthetic frame is the CLI speaking, not the model, so it never
            # counts as a model message; but only explicit limit evidence makes
            # it a limit. An authentication or other synthetic error is an
            # ordinary provider failure and spends its slot (ADR-355).
            if frame.get('error') == 'rate_limit' or (synthetic and LIMIT_TEXT.search(frame_text(message))):
                signals.append({'frame': 'assistant', 'error': frame.get('error'),
                                'model': message.get('model')})
            elif not synthetic:
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


def model_messages(transcript):
    """How many assistant frames the model itself produced (synthetic ones are the CLI's)."""
    return sum(1 for frame in read_frames(transcript) if frame.get('type') == 'assistant'
               and (frame.get('message') or {}).get('model') != '<synthetic>')


def interruption(turn, transcript, bound_seconds=TURN_BOUND_SECONDS):
    """Why a call did not end on its own, or None when it did (ADR-356).

    A call the runner killed at its wall-clock bound, or one whose child never
    launched, is an interrupted execution: no frozen-prompt slot is consumed,
    the evidence stays, and the same prompt is retried in a fresh project or
    seed copy. It is recorded apart from a provider usage limit (ADR-355),
    which is void for a different reason. A provider error that the call
    returned on its own (a nonzero exit with a stream) is neither: it is a
    failed turn and spends its slot.
    """
    code = turn.get('exit_code')
    if code not in ('timeout', 'launch_failed'):
        return None
    return {'kind': 'runner_timeout' if code == 'timeout' else 'launch_failed',
            'rule': 'ADR-356', 'slot_consumed': False,
            'bound_seconds': bound_seconds if code == 'timeout' else None,
            'elapsed_seconds': turn.get('elapsed_seconds'),
            'model_messages_before_kill': model_messages(transcript)}


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
    void = void_reason(transcript, envelope, stderr)
    cut_off = None
    if not void:
        # The runner's own exit code lives in the attempt receipt beside the
        # turn directory; without it a call can only be classified void or not.
        turn = {}
        try:
            receipt = json.loads((transcript.parent.parent / 'attempt.json').read_text())
            index = int(transcript.parent.name.split('-')[-1])
            turn = receipt['turns'][index].get('turn') or {}
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            turn = {}
        cut_off = interruption(turn, transcript) if turn else None
    return {'transcript': digest(transcript) if transcript.is_file() else None,
            'void': void, 'interruption': cut_off}


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


def run(design, project, model, execute_call=execute, turns=None):
    """Start an attempt: create the project (or validate the seed), then
    dispatch up to ``turns`` frozen prompts. A design attempt dispatches its
    whole schedule by default; a repair dispatches the repair prompt alone,
    because one completed turn uses about half a five-hour window, and its
    continuations follow one per window through ``resume``."""
    names = frozen(design)
    project = project.resolve()
    if project.is_relative_to(REPO) or project.parent.name != 'cadex-projects' or not project.name.startswith('ot7-'):
        raise ValueError('Use a new ot7-* project in the external cadex-projects directory.')
    repair = design == 'repair'
    if turns is None:
        turns = 1 if repair else len(names)
    if repair:
        seed = seed_identity(project)
        validate_seed(seed)
    else:
        project.mkdir()
    # Exclusive evidence creation guards the preserved seed against redispatch.
    evidence = evidence_dir(project, repair)
    evidence.mkdir()
    receipt = {'schema': 'ot7-design-evidence-v1', 'design': design, 'project': project.name,
               'model': model, 'actor_design_edits': 0, 'turns': [], 'status': 'running',
               'slots_spent': 0, 'void_calls': 0, 'interrupted_calls': 0,
               'turn_bound_seconds': TURN_BOUND_SECONDS}
    save = lambda: write(evidence / 'attempt.json', receipt)
    save()
    if repair:
        receipt['seed'] = seed
        save()
        before = evidence / 'before'
        before.mkdir()
        receipt['before'] = execute_call(
            [sys.executable, str(Path(__file__).resolve()), '--child-measure', str(project), str(before)],
            before, 'measurement', MEASUREMENT_BOUND_SECONDS)
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
    return dispatch(receipt, project, evidence, execute_call, turns)


def evidence_dir(project, repair):
    return project / 'evidence' / 'f4-repair' if repair else project / 'evidence'


def remaining(receipt):
    """What the frozen schedule still holds for a receipt: only turns that
    ended on their own spend a slot, the first prompt is not a continuation,
    and a void, interrupted or failed row closes the project (ADR-355,
    ADR-356). Computed from the rows, never from the receipt's status, so a
    receipt written under the superseded one-slot repair rule reads right."""
    names = frozen(receipt['design'])
    rows = receipt['turns']
    completed = [row for row in rows if row['status'] == 'completed']
    closed = None
    if rows and rows[-1]['status'] != 'completed':
        closed = rows[-1]['status']
    elif receipt['status'] in ('failed', 'before_unavailable'):
        closed = receipt['status']
    elif len(completed) != len(rows):
        closed = 'unfinished'
    unspent = names[len(rows):] if closed is None else []
    return {'completed': len(completed), 'continuations_used': max(len(completed) - 1, 0),
            'continuations_unspent': len(unspent) - (1 if unspent and not rows else 0),
            'next_prompt': unspent[0] if unspent else None, 'closed': closed}


def dispatch(receipt, project, evidence, execute_call, turns):
    names = frozen(receipt['design'])
    repair = receipt['design'] == 'repair'
    left = remaining(receipt)
    if left['closed'] or not left['next_prompt']:
        raise ValueError(f"nothing to dispatch: {left['closed'] or 'exhausted'}")
    continuations = left['continuations_used']
    first = names.index(left['next_prompt'])
    receipt['status'] = 'running'
    for index in range(first, min(first + turns, len(names))):
        name = names[index]
        out = evidence / f'turn-{index}'
        out.mkdir()
        prompt = out / name
        prompt.write_bytes((PROMPTS / name).read_bytes())
        counts = index > 0  # the create or repair prompt is not a continuation
        row = {'index': index, 'continuations_used': continuations + counts,
               'prompt': digest(prompt), 'status': 'started'}
        receipt['turns'].append(row)
        write(evidence / 'attempt.json', receipt)  # Persist the slot before launching the provider; a void call gives it back.
        row['turn'] = execute_call([sys.executable, str(Path(__file__).resolve()), '--child-turn',
                                   str(project), str(out), str(prompt), receipt['model']], out, 'turn',
                                  TURN_BOUND_SECONDS)
        row['void'] = void_reason(out / 'transcript.jsonl', out / 'turn.stdout.json', out / 'turn.stderr.txt')
        row['interruption'] = None if row['void'] else interruption(row['turn'], out / 'transcript.jsonl')
        row['measurement'] = execute_call([sys.executable, str(Path(__file__).resolve()), '--child-measure',
                                          str(project), str(out)], out, 'measurement',
                                         MEASUREMENT_BOUND_SECONDS)
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
        elif row['interruption']:
            # ADR-356: the runner cut the call off, so it did not end on its
            # own. The slot is unspent and the call is counted apart from
            # void calls.
            row['status'] = 'interrupted'
            row['slot_consumed'] = False
            row['continuations_used'] = continuations
            receipt['interrupted_calls'] += 1
        else:
            row['status'] = 'completed'
            row['slot_consumed'] = True
            continuations += counts
            receipt['slots_spent'] += 1
        # The design identity after the turn, so a resume can prove nothing
        # but a product-agent turn changed the design in between.
        row['accepted_after'] = seed_identity(project) if repair else design_identity(project)
        if repair:
            row['repair_assessment'] = retain_repair_assessment(
                out, row['accepted_after']['metadata'].get('accepted_revision'),
                row['measurement']['exit_code'] == 0)
        row['artifacts'] = [digest(p) for p in sorted(out.iterdir()) if p.is_file()]
        write(evidence / 'attempt.json', receipt)
        if row['void'] or row['interruption']:
            receipt['status'] = 'void' if row['void'] else 'interrupted'
            receipt['retry'] = {'rule': 'ADR-355' if row['void'] else 'ADR-356', 'prompt': name,
                                'project': retry_project_name(project.name),
                                'note': 'Same frozen prompt, fresh project or fresh seed copy, '
                                        'only while the product agent is available.'}
            break
        # A provider failure the call returned on its own, or a blocked
        # follow-up, ends this attempt with its slot spent.
        if row['turn']['exit_code'] not in (0, 3) or (out / 'blocked-followup.json').exists():
            receipt['status'] = 'failed'
            break
    else:
        left = remaining(receipt)
        if left['next_prompt']:
            # This invocation's turns are done and the schedule is not: the
            # next continuation goes through ``resume``, in a later window.
            receipt['status'] = 'paused'
        else:
            receipt['status'] = 'exhausted'
    receipt['remaining'] = remaining(receipt)
    if repair or receipt['status'] not in ('exhausted', 'failed'):
        write(evidence / 'attempt.json', receipt)
        return receipt
    # One bounded smoke, even on a failing fit; it never modifies the design.
    smoke = evidence / 'smoke'
    smoke.mkdir()
    receipt['smoke'] = execute_call([str(REPO / 'cadex'), 'smoke', '--project', str(project),
                                    '--out', str(smoke), '--seconds', '1', '--timeout', '240', '--json'],
                                   smoke, 'smoke', MEASUREMENT_BOUND_SECONDS)
    receipt['smoke']['artifacts'] = [digest(p) for p in sorted(smoke.iterdir()) if p.is_file()]
    write(evidence / 'attempt.json', receipt)
    return receipt


def resume(project, execute_call=execute, turns=1):
    """Dispatch the next frozen continuation on a project whose every earlier
    turn ended on its own, without replaying any of them (ADR-357). Refuses a
    project closed by a void, interrupted or failed call (those retry on a
    fresh copy), an exhausted one, and one whose design changed since its
    last turn (the actor never edits a design)."""
    project = project.resolve()
    evidence = next((d for d in (project / 'evidence' / 'f4-repair', project / 'evidence')
                     if (d / 'attempt.json').is_file()), None)
    if evidence is None:
        raise ValueError('no attempt to resume: start one with the design name')
    receipt = json.loads((evidence / 'attempt.json').read_text())
    left = remaining(receipt)
    if left['closed']:
        raise ValueError(f"cannot resume a project closed by a {left['closed']} call; "
                         f"retry on a fresh copy ({retry_project_name(project.name)})")
    if not left['next_prompt']:
        raise ValueError('exhausted: the first prompt and all three continuations reached the model')
    last = receipt['turns'][-1]
    if last.get('accepted_after') and design_identity(project) != last['accepted_after']:
        raise ValueError('the design changed since its last turn; only a product-agent turn may change it')
    if receipt['status'] == 'exhausted':
        receipt['ruling'] = ('ADR-357: status "exhausted" was written under the superseded one-slot '
                             'repair rule; the first prompt is not a continuation and the schedule '
                             'holds three continuations after it.')
    return dispatch(receipt, project, evidence, execute_call, turns)


def design_identity(project):
    """The seed identity when the project has a script, else None (a design
    attempt that never built has no script to snapshot)."""
    return (seed_identity(project) if (project / 'script.py').is_file()
            and (project / 'script.json').is_file() else None)


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
        # Read-only: is a retained call void under ADR-355, or interrupted
        # under ADR-356? Takes a transcript and, optionally, the CLI envelope
        # and stderr beside it; the exit code comes from attempt.json.
        print(json.dumps(classify(*sys.argv[2:5]), indent=2))
        sys.exit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('design', choices=['heron', 'robin', 'plover', 'repair', 'resume', 'remaining'],
                        help='a frozen design to start; `resume` dispatches the next continuation '
                             'on an existing project; `remaining` only reads what its schedule holds')
    parser.add_argument('project', type=Path)
    parser.add_argument('--model', default='claude-fable-5')
    parser.add_argument('--turns', type=int, default=None,
                        help='prompts to dispatch in this invocation (default: the whole schedule '
                             'for a design, one for a repair or a resume)')
    args = parser.parse_args()
    if args.design == 'remaining':
        evidence = next(d for d in (args.project / 'evidence' / 'f4-repair', args.project / 'evidence')
                        if (d / 'attempt.json').is_file())
        print(json.dumps(remaining(json.loads((evidence / 'attempt.json').read_text())), indent=2))
    elif args.design == 'resume':
        print(json.dumps(resume(args.project, turns=args.turns or 1), indent=2))
    else:
        print(json.dumps(run(args.design, args.project, args.model, turns=args.turns), indent=2))
