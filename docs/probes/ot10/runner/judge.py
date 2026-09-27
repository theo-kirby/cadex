# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Score one candidate robot on the frozen ot10 rubric, blind.

This is the judging procedure that ``docs/probes/ot10/README.md`` freezes.
Each call is a fresh Claude Code process in a new, empty directory outside
the repository. It gets one tool (``Read``), no MCP servers, no user
settings, hooks, memory or ``CLAUDE.md``, and exactly two readable
directories: the owner's core reference images, read in place and never
copied, and a directory holding the candidate's renders renamed
``candidate-N.png``. Its system prompt is ``INSTRUCTIONS`` followed by the
README's rubric block, byte for byte. It sees nothing else: not the design
language, not the project, not the prompt that made the design.

Three calls are made per candidate, and a trait scores the median of the
three. A reply that does not parse is retried once; a second failure is a
harness failure and exits non-zero with no score written.

    pixi run python docs/probes/ot10/runner/judge.py \\
        --out score.json RENDER.png [RENDER.png ...]
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

REPO = Path(__file__).resolve().parents[4]
README = REPO / 'docs/probes/ot10/README.md'
REFERENCES = REPO / 'reference/images/1-core'
MODEL = 'claude-opus-5-5'
EFFORT = 'high'
CALLS = 3
TRAITS = ('T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7')
START, END = '<!-- rubric:start -->\n', '<!-- rubric:end -->'
INSTRUCTIONS = (
    'You are an industrial designer judging the appearance of a small robot '
    'designed to be 3D-printed around hobby servos. You are given reference '
    'images of the target design quality and images of one candidate robot. '
    'Read every reference image and every candidate image with the Read tool '
    'before scoring. Then reply with one JSON object and nothing else, of the '
    'form {"T1": {"score": 0, "reason": "one sentence"}, ...} with keys T1 to '
    'T7 and integer scores 0 to 3.\n\n'
)


class JudgeError(RuntimeError):
    pass


def rubric(text: str | None = None) -> str:
    """The frozen rubric block of the README, exactly as the judge sees it."""

    text = README.read_text(encoding='utf-8') if text is None else text
    start, end = text.index(START) + len(START), text.index(END)
    return text[start:end]


def system_prompt() -> str:
    return INSTRUCTIONS + rubric()


def rubric_sha256() -> str:
    return hashlib.sha256(rubric().encode('utf-8')).hexdigest()


def references(directory: Path = REFERENCES) -> list[Path]:
    found = sorted(p for p in directory.iterdir() if p.suffix.lower() in {'.jpg', '.jpeg', '.png'})
    if len(found) != 10:
        raise JudgeError(f'expected the ten core references in {directory}, found {len(found)}')
    return found


def user_prompt(refs: list[Path], candidates: list[Path]) -> str:
    lines = ['Reference images (the target quality):']
    lines += [f'- {p}' for p in refs]
    lines += ['', 'Candidate images (the robot to score):']
    lines += [f'- {p}' for p in candidates]
    lines += ['', 'Read all of them, then reply with the JSON object only.']
    return '\n'.join(lines)


def command(claude: str, prompt: str, ref_dir: Path, candidate_dir: Path) -> list[str]:
    return [
        claude, '-p', prompt,
        '--model', MODEL,  # no --fallback-model: a refused model is not a score
        '--effort', EFFORT,
        '--output-format', 'json',
        '--system-prompt', system_prompt(),
        '--tools', 'Read',
        '--allowedTools', 'Read',
        '--strict-mcp-config',
        '--setting-sources', 'project',
        '--no-session-persistence',
        '--add-dir', str(ref_dir),
        '--add-dir', str(candidate_dir),
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
        raise JudgeError('reply must have exactly the keys T1..T7')
    for trait in TRAITS:
        row = data[trait]
        score = row.get('score') if isinstance(row, dict) else None
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 3:
            raise JudgeError(f'{trait}: score must be an integer 0..3')
    return {t: {'score': data[t]['score'], 'reason': str(data[t].get('reason', ''))} for t in TRAITS}


def aggregate(calls: list[dict[str, dict]]) -> dict:
    medians = {t: int(statistics.median(c[t]['score'] for c in calls)) for t in TRAITS}
    return {'medians': medians, 'total': sum(medians.values())}


def one_call(claude: str, refs: list[Path], renders: list[Path]) -> tuple[dict, dict]:
    with tempfile.TemporaryDirectory(prefix='ot10-judge-') as work:
        work = Path(work)
        candidate_dir = work / 'candidate'
        candidate_dir.mkdir()
        candidates = []
        for i, render in enumerate(renders, 1):
            target = candidate_dir / f'candidate-{i}{render.suffix.lower()}'
            shutil.copyfile(render, target)
            candidates.append(target)
        argv = command(claude, user_prompt(refs, candidates), refs[0].parent, candidate_dir)
        done = subprocess.run(argv, cwd=work, capture_output=True, text=True, timeout=1800,
                              env={k: v for k, v in os.environ.items() if not k.startswith('CADEX_')})
    if done.returncode != 0:
        raise JudgeError(f'claude exited {done.returncode}: {done.stderr[-400:] or done.stdout[-400:]}')
    envelope = json.loads(done.stdout)
    if envelope.get('is_error'):
        raise JudgeError(f"claude reported an error: {str(envelope.get('result'))[:400]}")
    receipt = {k: envelope.get(k) for k in ('session_id', 'duration_ms', 'num_turns', 'total_cost_usd', 'modelUsage')}
    return parse(str(envelope.get('result') or '')), {'reply': envelope.get('result'), **receipt}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('renders', nargs='+', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--claude', default=shutil.which('claude') or 'claude')
    parser.add_argument('--references', type=Path, default=REFERENCES)
    args = parser.parse_args(argv)
    refs = references(args.references)
    renders = [p.resolve() for p in args.renders]
    calls, raw = [], []
    for _ in range(CALLS):
        for attempt in (1, 2):
            try:
                scores, receipt = one_call(args.claude, refs, renders)
                break
            except (JudgeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
                raw.append({'error': str(exc), 'attempt': attempt})
                if attempt == 2:
                    print(f'judge: harness failure: {exc}', file=sys.stderr)
                    return 2
        calls.append(scores)
        raw.append({'scores': scores, **receipt})
    result = {
        'schema': 'ot10-judge-v1', 'model': MODEL, 'effort': EFFORT, 'calls': CALLS,
        'rubric_sha256': rubric_sha256(),
        'references': [p.name for p in refs],
        'candidates': [{'name': f'candidate-{i}{p.suffix.lower()}', 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                       for i, p in enumerate(renders, 1)],
        **aggregate(calls), 'raw': raw,
    }
    args.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'medians': result['medians'], 'total': result['total']}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
