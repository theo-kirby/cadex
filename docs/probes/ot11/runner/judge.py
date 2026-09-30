# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Score one seed's filmstrip on the frozen ot11 rubric, blind.

This is the judging procedure that ``docs/probes/ot11/README.md`` freezes.
Each call is a fresh Claude Code process in a new, empty directory outside
the repository. It gets one tool (``Read``), no MCP servers, no skills, no
user settings, hooks, memory or ``CLAUDE.md``, and exactly one readable
directory, holding the seed's two filmstrip sheets copied as
``overview.png`` and ``detail.png``. Its system prompt is ``INSTRUCTIONS``
followed by the README's rubric block, byte for byte; its one message is the
behaviour's intent paragraph from ``contract.json`` and the two file paths.
It sees nothing else: no reward, no metric, no seed number, no project, no
report, no prompt and no other seed's frames.

The sheets are the ones ``cadex evaluate`` drew: they are read through the
evaluation's own report, and a sheet whose digest is not the one the report
records is refused. Only the contract's judged seeds are judged.

Three calls are made per seed, and a trait scores the median of the three.
A reply that carries no scores is retried once. A second failure, a refusal,
an error from the harness or an answer from any model but the pinned one is
**not a score**: nothing is written to ``--out``, the attempts are kept
beside it as ``<out>.failed.json`` and the exit code is 2.

    pixi run python docs/probes/ot11/runner/judge.py walk \\
        --evaluation PROJECT/evaluations/<revision>-<policy> --seed 1101 \\
        --label w2-2 --out judge-w2-2-seed-1101.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import tempfile

OT11 = Path(__file__).resolve().parents[1]
README = OT11 / 'README.md'
CONTRACT = OT11 / 'contract.json'
SCHEMA = 'ot11-judge-v1'
MODEL = 'claude-opus-5-5'
EFFORT = 'high'
CALLS = 3
TRAITS = ('V1', 'V2', 'V3', 'V4')
SHEETS = ('overview', 'detail')
CALL_SECONDS = 1800
START, END = '<!-- rubric:start -->\n', '<!-- rubric:end -->'
INSTRUCTIONS = (
    'You are judging the motion of a small robot in a physics simulation '
    'from a filmstrip. You are given a paragraph saying what the robot was '
    'asked to do, and two images: an overview sheet and a detail sheet. Each '
    'sheet is twelve frames, read left to right and top to bottom, and every '
    'frame carries its simulation time in seconds at its bottom left. Read '
    'both images with the Read tool before scoring. Then reply with one JSON '
    'object and nothing else, of the form {"V1": {"score": 0, "reason": "one '
    'sentence"}, ...} with keys V1 to V4 and integer scores 0 to 3.\n\n'
)


class JudgeError(RuntimeError):
    """The harness did not return a score. Never a verdict."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding='utf-8'))


def rubric(text: str | None = None) -> str:
    """The frozen rubric block of the README, exactly as the judge sees it."""

    text = README.read_text(encoding='utf-8') if text is None else text
    start, end = text.index(START) + len(START), text.index(END)
    return text[start:end]


def system_prompt() -> str:
    return INSTRUCTIONS + rubric()


def user_prompt(intent: str, overview: Path, detail: Path) -> str:
    return '\n'.join([
        'What the robot was asked to do:', intent, '',
        f'Overview sheet: {overview}', f'Detail sheet: {detail}', '',
        'Read both, then reply with the JSON object only.',
    ])


def command(claude: str, prompt: str, sheet_dir: Path) -> list[str]:
    return [
        claude, '-p', prompt,
        '--model', MODEL,  # no --fallback-model: a refused model is not a score
        '--effort', EFFORT,
        '--output-format', 'json',
        '--system-prompt', system_prompt(),
        '--tools', 'Read',
        '--allowedTools', 'Read',
        '--strict-mcp-config',
        '--disable-slash-commands',
        '--setting-sources', 'project',
        '--no-session-persistence',
        '--add-dir', str(sheet_dir),
    ]


def parse(reply: str) -> dict[str, dict]:
    """The judge's scores from its final text, or JudgeError."""

    match = re.search(r'\{.*\}', reply, re.S)
    if not match:
        raise JudgeError('no JSON object in reply')
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise JudgeError(f'reply is not JSON: {exc}') from exc
    if not isinstance(data, dict) or set(data) != set(TRAITS):
        raise JudgeError('reply must have exactly the keys V1..V4')
    for trait in TRAITS:
        row = data[trait]
        score = row.get('score') if isinstance(row, dict) else None
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 3:
            raise JudgeError(f'{trait}: score must be an integer 0..3')
    return {t: {'score': data[t]['score'], 'reason': str(data[t].get('reason', ''))} for t in TRAITS}


def read_envelope(stdout: str, returncode: int = 0, stderr: str = '') -> tuple[dict, dict]:
    """``(scores, receipt)`` from one call's JSON envelope, or JudgeError.

    An error, a refusal and an answer from a model that is not the pinned
    one all stop here, before anything is read as a score.
    """

    if returncode != 0:
        raise JudgeError(f'claude exited {returncode}: {(stderr or stdout)[-400:]}')
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise JudgeError(f'claude wrote no JSON envelope: {exc}') from exc
    if not isinstance(envelope, dict):
        raise JudgeError('claude wrote no JSON envelope')
    if envelope.get('is_error'):
        raise JudgeError(f"claude reported an error: {str(envelope.get('result'))[:400]}")
    if envelope.get('stop_reason') == 'refusal':
        raise JudgeError(f"the model refused: {str(envelope.get('result'))[:400]}")
    models = sorted(envelope.get('modelUsage') or {})
    if models != [MODEL]:
        raise JudgeError(f'answered by {models or "no named model"}, not by {MODEL} alone')
    receipt = {k: envelope.get(k) for k in (
        'session_id', 'duration_ms', 'num_turns', 'total_cost_usd', 'stop_reason', 'modelUsage')}
    return parse(str(envelope.get('result') or '')), {'reply': envelope.get('result'), **receipt}


def aggregate(calls: list[dict[str, dict]], bar: dict) -> dict:
    """The median of each trait over the calls, their total, and the bar."""

    medians = {t: int(statistics.median(c[t]['score'] for c in calls)) for t in TRAITS}
    total = sum(medians.values())
    return {'medians': medians, 'total': total,
            'meets_bar': total >= bar['total_min'] and min(medians.values()) >= bar['trait_min']}


def sheets(evaluation: Path, seed: int, frozen: dict) -> tuple[dict, dict[str, Path]]:
    """One judged seed's two sheets, and what the evaluation says they are.

    Read through the evaluation's report: the seed must be one the contract
    judges, the film must be ready, and each sheet on disk must be the one
    the report recorded.
    """

    judge = frozen['judge']
    if seed not in judge['judged_seeds']:
        raise JudgeError(f"seed {seed} is not a judged seed; the contract judges "
                         + ', '.join(map(str, judge['judged_seeds'])))
    report = json.loads((evaluation / 'evaluation.json').read_text(encoding='utf-8'))
    film = report.get('film') or {}
    if film.get('state') != 'ready':
        raise JudgeError(f"this evaluation's film is {film.get('state') or 'not drawn'}")
    rows = [row for row in film.get('seeds') or [] if row.get('seed') == seed]
    if len(rows) != 1:
        raise JudgeError(f'seed {seed} was not filmed in this evaluation')
    (row,), paths, facts = rows, {}, []
    for kind in SHEETS:
        sheet = row[kind]
        if sheet.get('frames') != judge['filmstrip'][kind]['frames']:
            raise JudgeError(f"the {kind} has {sheet.get('frames')} frames, "
                             f"not the {judge['filmstrip'][kind]['frames']} the contract states")
        path = evaluation / str(sheet['file'])
        if path.parent != evaluation or sha256(path.read_bytes()) != sheet['sha256']:
            raise JudgeError(f'{path.name} is not the sheet this evaluation recorded')
        paths[kind] = path
        facts.append({'sheet': kind, 'sha256': sheet['sha256'], 'frames': sheet['frames'],
                      'times_s': sheet['times_s'], 'view': sheet['view'],
                      **({'follows': sheet.get('follows')} if kind == 'detail' else {})})
    return {
        'evaluation': {key: report.get(key) for key in (
            'schema', 'verdict', 'accepted_revision', 'policy_sha256', 'task_sha256', 'model_sha256')},
        'seed': seed, 'trace_sha256': row['trace_sha256'],
        'film_style_sha256': film.get('style_sha256'), 'sheets': facts,
    }, paths


def one_call(claude: str, intent: str, paths: dict[str, Path]) -> tuple[dict, dict]:
    with tempfile.TemporaryDirectory(prefix='ot11-judge-') as work:
        work = Path(work)
        sheet_dir = work / 'filmstrip'
        sheet_dir.mkdir()
        copies = {kind: sheet_dir / f'{kind}.png' for kind in SHEETS}
        for kind, target in copies.items():
            shutil.copyfile(paths[kind], target)
        argv = command(claude, user_prompt(intent, copies['overview'], copies['detail']), sheet_dir)
        done = subprocess.run(argv, cwd=work, capture_output=True, text=True, timeout=CALL_SECONDS,
                              env={k: v for k, v in os.environ.items() if not k.startswith('CADEX_')})
    return read_envelope(done.stdout, done.returncode, done.stderr)


def judge_seed(claude: str, intent: str, paths: dict[str, Path], call=one_call) -> tuple[list, list, str | None]:
    """``(scores, raw, failure)``: three scored calls, or why there is no score."""

    calls, raw = [], []
    for _ in range(CALLS):
        for attempt in (1, 2):
            try:
                scores, receipt = call(claude, intent, paths)
                break
            except (JudgeError, subprocess.TimeoutExpired) as exc:
                raw.append({'error': str(exc), 'attempt': attempt})
                if attempt == 2:
                    return calls, raw, str(exc)
        calls.append(scores)
        raw.append({'scores': scores, **receipt})
    return calls, raw, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    frozen = contract()
    parser.add_argument('behaviour', choices=sorted(frozen['behaviours']))
    parser.add_argument('--evaluation', type=Path, required=True,
                        help='the directory cadex evaluate wrote, with its film')
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--label', default='', help="the receipt's name for the policy; never shown to the judge")
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--claude', default=shutil.which('claude') or 'claude')
    args = parser.parse_args(argv)
    judge = frozen['judge']
    block = rubric()
    if sha256(block.encode('utf-8')) != judge['rubric_sha256']:
        print('judge: the README rubric is not the one contract.json pins', file=sys.stderr)
        return 2
    if (judge['model'], judge['fallback'], judge['calls'], tuple(judge['traits'])) != (MODEL, None, CALLS, TRAITS):
        print('judge: this runner is not the procedure contract.json states', file=sys.stderr)
        return 2
    intent = frozen['behaviours'][args.behaviour]['intent']
    try:
        facts, paths = sheets(args.evaluation.resolve(), args.seed, frozen)
    except (JudgeError, OSError, KeyError, ValueError) as exc:
        print(f'judge: {exc}', file=sys.stderr)
        return 2
    calls, raw, failure = judge_seed(args.claude, intent, paths)
    result = {
        'schema': SCHEMA, 'label': args.label, 'behaviour': args.behaviour,
        'model': MODEL, 'fallback': None, 'effort': EFFORT, 'calls': CALLS,
        'rubric_sha256': judge['rubric_sha256'],
        'instructions_sha256': sha256(INSTRUCTIONS.encode('utf-8')),
        'intent_sha256': sha256(intent.encode('utf-8')),
        'bar': judge['bar'], **facts,
    }
    failed = args.out.with_name(args.out.name + '.failed.json')
    if failure is not None:
        failed.write_text(json.dumps({**result, 'state': 'no score', 'error': failure, 'raw': raw},
                                     indent=2) + '\n', encoding='utf-8')
        print(f'judge: harness failure, not a score: {failure}', file=sys.stderr)
        return 2
    result.update(aggregate(calls, judge['bar']))
    result['raw'] = raw
    args.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    failed.unlink(missing_ok=True)
    print(json.dumps({key: result[key] for key in ('medians', 'total', 'meets_bar')}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
