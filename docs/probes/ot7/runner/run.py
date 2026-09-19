# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bounded, project-local evidence collection for the frozen ot7 attempts."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
#: A frozen prompt is dispatched only while the five-hour window reads at or
#: under this, in percent (ADR-358): one completed turn moved a window from
#: 8 % to 57 % and another from 8 % to 63 %, so a turn that starts above about
#: 45 % is cut off by the session limit and void.
WINDOW_BOUND_PERCENT = 45
WINDOW_PROBE_BOUND_SECONDS = 120
#: The effort level every turn of an attempt is launched at (ADR-359). The
#: CLI's own default is `high`; a create turn at `high` spent 24 of its 30
#: minutes in three thinking-only messages that each hit the per-message
#: output cap, so the collector dispatches at `medium` unless told otherwise.
#: Recorded in the receipt with the cap and the bound, and reused by every
#: continuation of the same attempt.
EFFORT_LEVEL = 'medium'
WINDOW_PROBE_TEXT = 'Reply with the single word ok.'


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


def settings(effort=EFFORT_LEVEL):
    """The effective per-turn settings, as the receipt records them."""
    from cadex_cli.agent import default_max_output_tokens
    return {'effort': effort, 'max_output_tokens': default_max_output_tokens(),
            'turn_bound_seconds': TURN_BOUND_SECONDS}


def child_turn(project, out, prompt, model, effort=EFFORT_LEVEL):
    from cadex_cli import __main__ as cli
    from cadex_cli.agent import EFFORT_ENV, ClaudeTurn, TurnResult, find_claude

    os.environ[EFFORT_ENV] = effort

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


def window_reading(execute_call, out, stem, model):
    """Read the five-hour window from a one-word probe's first ``rate_limit_event``
    frame (ADR-358). The probe carries no project, no tools and no MCP server,
    so it is not a product-agent call and spends no slot; its stream is kept
    beside the receipt. A reading with no frame, or a rejected one, is not
    evidence of room, and ``dispatch`` treats it as no room.

    The probe is itself a model call on the product agent's model, so its own
    outcome is the direct reading and the five-hour number is only a forecast
    (ADR-364). Every unified window the provider names is kept, because the
    binding limit is often not the five-hour one: on 2026-09-16 at 14:29 UTC
    ``claude-fable-5`` refused this probe outright with ``five_hour`` at 1 %,
    because ``seven_day_overage_included`` was at 100 % with overage disabled
    at the organisation level.

    A stream carries more than one ``rate_limit_event`` frame and their order
    is the provider's, not ours (ADR-369): at 14:29 UTC the rejected frame
    came first, and at 17:02 UTC the same account put an *allowed* five-hour
    frame in front of it. So the windows are merged across every frame, and
    **the reading's frame is the one that bound the call, whichever way the
    provider ordered them** (ADR-376): on a probe the provider refused, the
    frame that did the rejecting; on a probe that answered, the frame that
    allowed it. Reading ``infos[0]`` on an answered probe let frame order
    alone decide the verdict — this organisation has overage disabled, so a
    rejected ``seven_day_overage_included`` frame rides along on every probe,
    and with it in front the gate read ``status: rejected`` at 8 % and
    deferred a prompt the account had room for. ``resets_at`` is the
    schedule of the window ``rate_limit_type`` names and dates nothing else —
    an account or organisation setting is not bound by it in either
    direction.
    """
    from cadex_cli.agent import ClaudeUnavailable, find_claude
    blank = {'status': None, 'five_hour_percent': None, 'resets_at': None,
             'frame': None, 'windows': {}, 'rate_limit_type': None, 'refused': None,
             'disabled_reason': None, 'resets_at_is': None}
    try:
        binary = find_claude('')
    except ClaudeUnavailable as exc:
        return dict(blank, probe=None, error=str(exc))
    command = [binary, '-p', WINDOW_PROBE_TEXT, '--output-format', 'stream-json', '--verbose',
               '--model', model, '--tools', '', '--system-prompt', WINDOW_PROBE_TEXT]
    stream = out / f'{stem}.stdout.json'
    reading = dict(blank, probe=execute_call(command, out, stem, WINDOW_PROBE_BOUND_SECONDS))
    # The probe's own stream is classified by the same rule as a design call's
    # (ADR-355): a probe the provider refused on a limit is a refusal whatever
    # any window frame says about headroom. A probe that answered is never a
    # refusal, so a stray rejected frame — an organisation with overage
    # disabled emits one beside an ordinary allowed window — cannot close the
    # gate on an account that in fact has room.
    reading['refused'] = None if probe_answered(reading['probe'], stream) else void_reason(stream)
    infos = [frame.get('rate_limit_info') or {} for frame in read_frames(stream)
             if frame.get('type') == 'rate_limit_event']
    if not infos:
        return reading
    # The frame that bound the call is the reading, in both directions
    # (ADR-369 for the refusal, ADR-376 for its mirror): on a refused probe
    # the frame that rejected, on an answered one the frame that allowed.
    # Position in the stream decides nothing, because it is the provider's
    # and it varies between two probes of the same account minutes apart.
    # A probe with no frame of the kind it needs falls back to the first.
    rejected = [info for info in infos if info.get('status') == 'rejected']
    allowed = [info for info in infos if info.get('status') != 'rejected']
    if reading['refused']:
        info = rejected[-1] if rejected else infos[0]
    else:
        info = allowed[0] if allowed else infos[0]
    # The reading's own frame is authoritative for every window it names; the
    # others only contribute the names it leaves out, which is how the full
    # window that refused reaches a receipt whose frame does not list it.
    windows = {}
    for each in [other for other in infos if other is not info] + [info]:
        windows.update({name: round(float(value['utilization']) * 100)
                        for name, value in (each.get('unifiedWindows') or {}).items()
                        if isinstance(value, dict) and value.get('utilization') is not None})
    percent = windows.get('five_hour')
    if percent is None and info.get('rateLimitType') == 'five_hour' and info.get('utilization') is not None:
        percent = round(float(info['utilization']) * 100)
    named = (info.get('unifiedWindows') or {}).get(info.get('rateLimitType')) or {}
    resets = named.get('resetsAt') or info.get('resetsAt')
    reading.update(
        status=info.get('status'), frame=info, rate_limit_type=info.get('rateLimitType'),
        windows=windows, five_hour_percent=percent,
        disabled_reason=info.get('overageDisabledReason'),
        resets_at=None if resets is None else datetime.fromtimestamp(resets, timezone.utc).isoformat())
    if reading['refused'] and reading['resets_at']:
        cause = reading['disabled_reason']
        reading['resets_at_is'] = (
            f"the schedule of the {reading['rate_limit_type']} usage window"
            + (f", not a date for the {cause} setting that refused this probe" if cause
               else ', not a date for the refusal'))
    return reading


def probe_answered(probe, stream):
    """Whether the probe call reached the model and returned its own answer."""
    if (probe or {}).get('exit_code') != 0:
        return False
    results = [f for f in read_frames(stream) if f.get('type') == 'result']
    return bool(results) and not any(f.get('is_error') for f in results)


def window_has_room(reading, bound_percent):
    """Only a frame the provider allowed, read at or under the bound, is room —
    and only when the probe call itself was not refused on a limit (ADR-364).
    A per-model or longer-window limit refuses the call with the five-hour
    number still low, so the number alone is not evidence of room."""
    return (not reading.get('refused')
            and reading.get('status') in ('allowed', 'allowed_warning')
            and reading.get('five_hour_percent') is not None
            and reading['five_hour_percent'] <= bound_percent)


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


def unreached_reason(turn, transcript, envelope):
    """Why a call never reached the model for a local reason, or None (ADR-386).

    The charter counts only a turn that reached the model and ended on its
    own. A usage limit is void (ADR-355) and a runner kill is an interruption
    (ADR-356); both are provider-side. This is the third way a frozen prompt
    can fail to be sent: the CLI refused before it opened a provider session
    at all, so no model saw the prompt. The ot7 case that found it is a
    project whose accepted script does not rebuild byte-identically, which
    makes ``open_project``'s restore pass refuse in six seconds.

    The evidence is the absence of a provider stream together with the CLI's
    own envelope: an error, and no session id. Both are required, so an
    ordinary provider failure -- an ``authentication_failed`` synthetic frame,
    which is a stream -- stays a failed turn and spends its slot, and a call
    that crashed after the model spoke stays failed too. A call that wrote no
    envelope proves nothing and is left failed, on the same rule that missing
    evidence never means a passing result.
    """
    if turn.get('exit_code') in (0, 3, 'timeout', 'launch_failed'):
        return None
    if read_frames(transcript):
        return None
    envelope = Path(envelope)
    if not envelope.is_file():
        return None
    try:
        reply = json.loads(envelope.read_text())
    except ValueError:
        return None
    if not isinstance(reply, dict):
        return None
    error = str(reply.get('error') or '').strip()
    if not error or str(reply.get('session_id') or ''):
        return None
    return {'kind': 'never_reached_model', 'rule': 'ADR-386', 'slot_consumed': False,
            'exit_code': turn.get('exit_code'), 'elapsed_seconds': turn.get('elapsed_seconds'),
            'provider_frames': 0, 'error': error[:400]}


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
    turn = {}
    if not void:
        # The runner's own exit code lives in the attempt receipt beside the
        # turn directory; without it a call can only be classified void or not.
        try:
            receipt = json.loads((transcript.parent.parent / 'attempt.json').read_text())
            index = int(transcript.parent.name.split('-')[-1])
            turn = receipt['turns'][index].get('turn') or {}
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            turn = {}
        cut_off = interruption(turn, transcript) if turn else None
    never = None
    if not void and not cut_off and envelope is not None:
        never = unreached_reason(turn, transcript, envelope)
    return {'transcript': digest(transcript) if transcript.is_file() else None,
            'void': void, 'interruption': cut_off, 'unreached': never}


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


def run(design, project, model, execute_call=execute, turns=None, window_bound=None,
        effort=EFFORT_LEVEL):
    """Start an attempt: create the project (or validate the seed), then
    dispatch up to ``turns`` frozen prompts. A design attempt dispatches its
    whole schedule by default; a repair dispatches the repair prompt alone,
    because one completed turn uses about half a five-hour window, and its
    continuations follow one per window through ``resume``. With a
    ``window_bound`` (percent), every prompt is preceded by a window probe and
    is dispatched only while the reading shows room (ADR-358); ``None`` reads
    nothing, for fixtures that fake the provider, and the command line always
    passes a bound. ``effort`` is the level every turn of the attempt is
    launched at (ADR-359); the receipt's ``settings`` records it."""
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
               'slots_spent': 0, 'void_calls': 0, 'interrupted_calls': 0, 'unreached_calls': 0,
               'turn_bound_seconds': TURN_BOUND_SECONDS, 'settings': settings(effort)}
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
    return dispatch(receipt, project, evidence, execute_call, turns, window_bound)


def evidence_dir(project, repair):
    return project / 'evidence' / 'f4-repair' if repair else project / 'evidence'


def remaining(receipt):
    """What the frozen schedule still holds for a receipt: only turns that
    ended on their own spend a slot, the first prompt is not a continuation,
    and a void, interrupted or failed row closes the project (ADR-355,
    ADR-356). An unreached row is skipped entirely (ADR-386): the prompt was
    never sent, so the same one is still next in the same project. Computed
    from the rows, never from the receipt's status, so a receipt written
    under the superseded one-slot repair rule reads right."""
    names = frozen(receipt['design'])
    # An unreached call never sent its prompt, so it is transparent here: it
    # neither closes the project nor advances the schedule (ADR-386).
    rows = [row for row in receipt['turns'] if row['status'] != 'unreached']
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


def dispatch(receipt, project, evidence, execute_call, turns, window_bound=None):
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
        reading = None
        if window_bound is not None:
            # ADR-358: the window is read before the slot is persisted and the
            # turn directory exists, so a deferral leaves nothing to resume
            # around. The probe's stream stays beside the receipt.
            probes = evidence / 'window'
            probes.mkdir(exist_ok=True)
            readings = receipt.setdefault('window_readings', [])
            reading = window_reading(execute_call, probes, f'turn-{index}-probe-{len(readings)}',
                                     receipt['model'])
            reading.update(prompt=name, bound_percent=window_bound,
                           read_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                           dispatched=window_has_room(reading, window_bound))
            readings.append(reading)
            if not reading['dispatched']:
                receipt['status'] = 'paused'
                receipt['deferred'] = {'rule': 'ADR-355/ADR-358', 'prompt': name,
                                       'five_hour_percent': reading['five_hour_percent'],
                                       'resets_at': reading['resets_at'],
                                       'note': 'Design turns wait for the product agent: the window '
                                               'showed no room, so the prompt was not sent and no '
                                               'slot was touched. Resume after the reset.'}
                break
            receipt.pop('deferred', None)
        out = evidence / f'turn-{index}'
        # An unreached call (ADR-386) leaves its receipt behind and the same
        # prompt is re-sent into the same project, so the retry gets its own
        # directory rather than overwriting the evidence of why it failed.
        retry = 0
        while out.exists():
            retry += 1
            out = evidence / f'turn-{index}-retry-{retry}'
        out.mkdir()
        prompt = out / name
        prompt.write_bytes((PROMPTS / name).read_bytes())
        counts = index > 0  # the create or repair prompt is not a continuation
        row = {'index': index, 'continuations_used': continuations + counts,
               'prompt': digest(prompt), 'status': 'started', 'window': reading,
               'model': receipt['model'], 'evidence_dir': out.name}
        receipt['turns'].append(row)
        write(evidence / 'attempt.json', receipt)  # Persist the slot before launching the provider; a void call gives it back.
        # Every turn of an attempt runs at the effort its receipt records
        # (ADR-359); a receipt written before that field existed ran at the
        # CLI's own default.
        effort = receipt.setdefault('settings', settings('high'))['effort']
        row['settings'] = dict(receipt['settings'])
        row['turn'] = execute_call([sys.executable, str(Path(__file__).resolve()), '--child-turn',
                                   '--effort', effort, str(project), str(out), str(prompt),
                                   receipt['model']], out, 'turn', TURN_BOUND_SECONDS)
        row['void'] = void_reason(out / 'transcript.jsonl', out / 'turn.stdout.json', out / 'turn.stderr.txt')
        row['interruption'] = None if row['void'] else interruption(row['turn'], out / 'transcript.jsonl')
        row['unreached'] = (None if row['void'] or row['interruption'] else
                            unreached_reason(row['turn'], out / 'transcript.jsonl',
                                             out / 'turn.stdout.json'))
        row['measurement'] = execute_call([sys.executable, str(Path(__file__).resolve()), '--child-measure',
                                          str(project), str(out)], out, 'measurement',
                                         MEASUREMENT_BOUND_SECONDS)
        if (out / 'fit.json').exists():
            fit = json.loads((out / 'fit.json').read_text())
            row['static_fit'] = {key: fit[key] for key in ('verdict', 'failing_count', 'pairs_checked')}
            # The swept half the same reply carried (ADR-366), so a receipt
            # says what the agent saw about motion without opening the raw
            # report beside it. Absent on a receipt measured before ADR-366.
            if isinstance(fit.get('sweep'), dict):
                row['swept_fit'] = {key: fit['sweep'][key] for key in (
                    'verdict', 'coverage', 'joints_checked', 'joints_complete',
                    'failing_count')}
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
        elif row['unreached']:
            # ADR-386: the CLI refused before a provider session existed, so
            # no model saw the prompt. The slot is unspent and the project is
            # not closed -- the same prompt is next, in this same project,
            # once whatever refused it is fixed.
            row['status'] = 'unreached'
            row['slot_consumed'] = False
            row['continuations_used'] = continuations
            receipt['unreached_calls'] = receipt.get('unreached_calls', 0) + 1
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
        if row['unreached']:
            # The prompt is still unspent and still next, so the attempt is
            # paused rather than closed: no fresh project, no retry naming.
            receipt['status'] = 'paused'
            receipt['blocked'] = {'rule': 'ADR-386', 'prompt': name,
                                  'evidence_dir': out.name,
                                  'error': row['unreached']['error'],
                                  'note': 'The CLI refused before a provider session existed, so no '
                                          'model saw this prompt and no slot was spent. Re-send the '
                                          'same prompt into this same project with `resume`, once '
                                          'the refusal it names is fixed.'}
            break
        receipt.pop('blocked', None)
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


def resume(project, execute_call=execute, turns=1, window_bound=None, model=None):
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
    # A deferred first prompt (ADR-358) has a receipt and no rows yet; there
    # is no snapshot to hold the design against until a turn has run.
    last = receipt['turns'][-1] if receipt['turns'] else {}
    if last.get('accepted_after') and design_identity(project) != last['accepted_after']:
        raise ValueError('the design changed since its last turn; only a product-agent turn may change it')
    if receipt['status'] == 'exhausted':
        receipt['ruling'] = ('ADR-357: status "exhausted" was written under the superseded one-slot '
                             'repair rule; the first prompt is not a continuation and the schedule '
                             'holds three continuations after it.')
    if model and model != receipt['model']:
        previous = receipt['model']
        for row in receipt['turns']:
            row.setdefault('model', previous)
        receipt.setdefault('model_changes', []).append({
            'from': previous, 'to': model, 'before_turn': len(receipt['turns']),
            'changed_at': datetime.now(timezone.utc).isoformat(timespec='seconds')})
        receipt['model'] = model
        write(evidence / 'attempt.json', receipt)
    return dispatch(receipt, project, evidence, execute_call, turns, window_bound)


def reclassify(project):
    """Re-read a retained attempt's own evidence and correct its accounting (ADR-386).

    The unreached class arrived after ot7 had already collected calls under
    it, so the receipts that recorded one as a completed, slot-spending turn
    are wrong about a slot the model never saw. This reads each retained
    turn's own stream and envelope back and demotes only the rows that the
    evidence proves never reached the model. A completed turn is never
    touched, because a stream with a model message in it can never satisfy
    ``unreached_reason``. The superseded receipt is kept beside the corrected
    one rather than deleted.
    """
    project = Path(project).resolve()
    evidence = next((d for d in (project / 'evidence' / 'f4-repair', project / 'evidence')
                     if (d / 'attempt.json').is_file()), None)
    if evidence is None:
        raise ValueError('no attempt to reclassify')
    receipt = json.loads((evidence / 'attempt.json').read_text())
    corrected = []
    for row in receipt['turns']:
        if row['status'] != 'completed':
            continue
        out = evidence / str(row.get('evidence_dir') or f"turn-{row['index']}")
        never = unreached_reason(row.get('turn') or {}, out / 'transcript.jsonl',
                                 out / 'turn.stdout.json')
        if not never:
            continue
        row['status'] = 'unreached'
        row['unreached'] = never
        row['slot_consumed'] = False
        row.setdefault('evidence_dir', out.name)
        receipt['slots_spent'] = max(receipt.get('slots_spent', 0) - 1, 0)
        receipt['unreached_calls'] = receipt.get('unreached_calls', 0) + 1
        corrected.append({'index': row['index'], 'evidence_dir': out.name,
                          'error': never['error']})
    if not corrected:
        return {'project': project.name, 'corrected': [], 'receipt': receipt}
    # A stale status is what the correction is for: a receipt that closed as
    # `failed` on a call the model never saw closed on nothing. The status is
    # taken from the rows, and the rows below an unreached one never ran, so
    # their continuation counts are unaffected.
    if receipt['turns'][-1]['status'] == 'unreached':
        receipt['status'] = 'paused'
        receipt.pop('retry', None)
        last = corrected[-1]
        receipt['blocked'] = {'rule': 'ADR-386', 'prompt': receipt['turns'][-1]['prompt']['path'],
                              'evidence_dir': last['evidence_dir'], 'error': last['error'],
                              'note': 'Reclassified from the retained evidence: the CLI refused '
                                      'before a provider session existed, so no model saw this '
                                      'prompt and no slot was spent. Re-send the same prompt into '
                                      'this same project with `resume`, once the refusal it names '
                                      'is fixed.'}
    receipt['remaining'] = remaining(receipt)
    receipt.setdefault('reclassifications', []).append(
        {'rule': 'ADR-386', 'at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
         'turns': corrected})
    superseded = evidence / 'attempt.superseded.json'
    index = 1
    while superseded.exists():
        index += 1
        superseded = evidence / f'attempt.superseded-{index}.json'
    superseded.write_text((evidence / 'attempt.json').read_text())
    write(evidence / 'attempt.json', receipt)
    return {'project': project.name, 'corrected': corrected,
            'superseded': superseded.name, 'remaining': receipt['remaining']}


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
        effort = [EFFORT_LEVEL]
        if sys.argv[2:3] == ['--effort']:
            effort, sys.argv[2:4] = [sys.argv[3]], []
        sys.exit(child_turn(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5], *effort))
    if len(sys.argv) > 1 and sys.argv[1] == '--child-measure':
        sys.exit(child_measure(Path(sys.argv[2]), Path(sys.argv[3])))
    if len(sys.argv) > 1 and sys.argv[1] == '--classify':
        # Read-only: is a retained call void under ADR-355, or interrupted
        # under ADR-356? Takes a transcript and, optionally, the CLI envelope
        # and stderr beside it; the exit code comes from attempt.json.
        print(json.dumps(classify(*sys.argv[2:5]), indent=2))
        sys.exit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('design', choices=['heron', 'robin', 'plover', 'repair', 'resume', 'remaining',
                                           'reclassify', 'window'],
                        help='a frozen design to start; `resume` dispatches the next continuation '
                             'on an existing project; `remaining` only reads what its schedule holds; '
                             '`reclassify` re-reads a retained attempt\'s evidence and corrects its accounting; '
                             '`window` only reads the five-hour window and dispatches nothing')
    parser.add_argument('project', type=Path, nargs='?')
    parser.add_argument('--model', default=None,
                        help='model for a new attempt or explicit resume override; omitted resumes preserve the receipt model')
    parser.add_argument('--effort', default=EFFORT_LEVEL, choices=['low', 'medium', 'high', 'xhigh', 'max'],
                        help=f'the effort level every turn of a new attempt is launched at (default '
                             f'{EFFORT_LEVEL}, ADR-359); a resume reuses what its receipt records')
    parser.add_argument('--turns', type=int, default=None,
                        help='prompts to dispatch in this invocation (default: the whole schedule '
                             'for a design, one for a repair or a resume)')
    parser.add_argument('--window-bound', type=int, default=WINDOW_BOUND_PERCENT, metavar='PERCENT',
                        help='dispatch a prompt only while a probe reads the five-hour window at or '
                             f'under this (default {WINDOW_BOUND_PERCENT}); the reading is kept in the receipt')
    args = parser.parse_args()
    if args.design == 'window':
        out = Path(os.environ.get('TMPDIR', '/tmp')) / f'ot7-window-{os.getpid()}'
        out.mkdir()
        reading = window_reading(execute, out, 'probe', args.model or 'claude-fable-5')
        reading['room'] = window_has_room(reading, args.window_bound)
        print(json.dumps({k: v for k, v in reading.items() if k != 'frame'}, indent=2))
    elif args.project is None:
        parser.error(f'{args.design} needs a project')
    elif args.design == 'remaining':
        evidence = next(d for d in (args.project / 'evidence' / 'f4-repair', args.project / 'evidence')
                        if (d / 'attempt.json').is_file())
        print(json.dumps(remaining(json.loads((evidence / 'attempt.json').read_text())), indent=2))
    elif args.design == 'reclassify':
        print(json.dumps(reclassify(args.project), indent=2))
    elif args.design == 'resume':
        print(json.dumps(resume(args.project, turns=args.turns or 1,
                                window_bound=args.window_bound, model=args.model), indent=2))
    else:
        print(json.dumps(run(args.design, args.project, args.model or 'claude-fable-5', turns=args.turns,
                             window_bound=args.window_bound, effort=args.effort), indent=2))
