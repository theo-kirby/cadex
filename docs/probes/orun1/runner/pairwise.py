# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""orun1's pairwise judge: which of two robots would the owner rate higher.

A judge version is ``VERSIONS[name]``: its instructions, its inputs (which
of a design's renders it sees) and its effort. The model is always
``claude-opus-5-5`` with no fallback. One call compares one unordered pair
of designs; which design is shown as ``A`` is fixed per pair by a hash of
the version name and the two ids, so position is balanced and reproducible.
A design's score is the fraction of its comparisons it won.

Each call is a fresh Claude Code process in a new, empty directory outside
the repository, isolated the way ot10's judge is (``Read`` only, no MCP, no
user settings, hooks, memory or ``CLAUDE.md``). The renders are copied in
as ``A-N.png`` and ``B-N.png``: the judge never sees a design id, a thesis,
the agent's notes, a project or a verdict. A reply that does not parse is
retried once; a second failure leaves the pair unjudged and is reported.

Results are appended to ``OUT/pairs.jsonl`` as they arrive, so a rerun
judges only what is missing. ``OUT/summary.json`` holds the scores and the
D1 metrics for the split.

    pixi run python docs/probes/orun1/runner/pairwise.py --version v1 \\
        --split dev --inputs ~/cadex-projects/orun1-judge/dev \\
        --out docs/probes/orun1/judge/v1-dev --jobs 8
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from metrics import evaluate, split_verdicts  # noqa: E402

MODEL = 'claude-opus-5-5'

V1_INSTRUCTIONS = """\
You are judging the design of two small robots, A and B, from renders. Each \
was designed to be 3D-printed around hobby servos, controller boards, \
batteries and sensors. They may be different kinds of robot (an arm, a \
walker, a balancer, something else). Decide which one a particular owner \
would rate higher. This owner's taste:

- They like robots that read as engineered machines: visible, ordered \
structure; the real actuators, boards, batteries and cables laid out with \
order and on purpose; fasteners, panels, horns and seams as detail; a \
sensor (a camera, a range sensor, a sensor slot) as a real part.
- An enclosed body is fine when it is hard-surface: flat panels, chamfers, \
crisp edges, visible fastening.
- They dislike the mascot archetype: a soft, rounded, pillow-like box or \
blob body with a visor face or dot eyes, over short stubby limbs, with \
boxes hanging off it. Any face or pair of eyes counts against a design.
- They dislike parts that look stuck on, unsupported or arbitrary, and \
prefer structure and limbs whose shape looks load-carrying and purposeful.
- Finish alone earns nothing: smooth shading, colour and a clean render do \
not make a design good.

Judge the design, not the kind of robot, the camera or the background. \
Read every image with the Read tool first. Then reply with one JSON object \
and nothing else: {"winner": "A" or "B", "reason": "one sentence"}.
"""

# v2 changes two things, each motivated by v1's misses on the dev split
# (README, "Judge v1 on dev"): v1 marked a plain, clean design down for
# showing no hardware, and it ranked a committed character below the
# generic soft box with a visor because both "had a face".
V2_INSTRUCTIONS = """\
You are judging the design of two small robots, A and B, from renders. Each \
was designed to be 3D-printed around hobby servos, controller boards, \
batteries and sensors. They may be different kinds of robot (an arm, a \
walker, a balancer, something else). Decide which one a particular owner \
would rate higher. This owner's taste:

- Above all they reward a resolved, intentional whole: a form where every \
part looks designed for its place and the robot reads as one considered \
object. That can be reached several ways, and each is good: an exposed, \
ordered mechanism (real actuators, boards, batteries and cables laid out \
on purpose, horns, fasteners and seams as detail); a crisp hard-surface \
enclosure (flat panels, chamfers, visible fastening, a sensor as a real \
part); or a clean, minimal form with simple, well-proportioned volumes and \
nothing decorative. Do not prefer a design because more of its parts, \
fasteners or detail are visible; a plain design loses only when it is \
also vague or badly proportioned.
- Their strongest dislike is one specific archetype: a generic soft, \
rounded, pillow-like box as the body, with a visor slot, a face or dot \
eyes, over short or thin limbs, with blocks hanging off or under it. It \
looks neither engineered nor characterful. A face or eyes count against \
any design, but a fully committed character whose whole form follows one \
idea is better than that generic box.
- They dislike parts that look stuck on, unsupported or arbitrary, and \
prefer structure and limbs whose shape looks load-carrying and purposeful.
- Finish alone earns nothing: smooth shading, colour and a clean render do \
not make a design good.

Judge the design, not the kind of robot, the camera or the background. \
Read every image with the Read tool first. Then reply with one JSON object \
and nothing else: {"winner": "A" or "B", "reason": "one sentence"}.
"""

VERSIONS = {
    'v1': {'instructions': V1_INSTRUCTIONS, 'views': ('hero.png',), 'effort': 'high'},
    'v2': {'instructions': V2_INSTRUCTIONS, 'views': ('hero.png',), 'effort': 'high'},
}

# The version frozen in the README before any held-out call (D1), and the
# hash of its instructions. Only a frozen version may judge ``heldout``,
# and only into a directory that holds no result yet: each version is
# measured on the held-out set once.
FROZEN = {'v2': '0ebb596584eb1203a5706ab40c9e4799b24a0dbbf7d1d5a644eb1215d68708ab'}


class JudgeError(RuntimeError):
    pass


def instructions_sha256(version: str) -> str:
    return hashlib.sha256(VERSIONS[version]['instructions'].encode('utf-8')).hexdigest()


def order(version: str, a: str, b: str, mirror: bool = False) -> tuple[str, str]:
    """The pair as shown (A, B): balanced, and the same on every run.

    ``mirror`` swaps every pair's sides: a replicate that measures how much
    of a version's result is position and call noise.
    """

    a, b = sorted((a, b))
    flip = bool(hashlib.sha256(f'{version}|{a}|{b}'.encode()).digest()[0] & 1) != mirror
    return (b, a) if flip else (a, b)


def parse(reply: str) -> dict:
    match = re.search(r'\{.*\}', reply, re.S)
    if not match:
        raise JudgeError('no JSON object in reply')
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise JudgeError(f'reply is not JSON: {exc}') from exc
    if not isinstance(data, dict) or data.get('winner') not in ('A', 'B'):
        raise JudgeError('winner must be "A" or "B"')
    return {'winner': data['winner'], 'reason': str(data.get('reason', ''))}


def one_call(claude: str, version: str, shown_a: list[Path], shown_b: list[Path]) -> tuple[dict, dict]:
    spec = VERSIONS[version]
    with tempfile.TemporaryDirectory(prefix='orun1-judge-') as work:
        work = Path(work)
        images = work / 'images'
        images.mkdir()
        lines = []
        for label, renders in (('A', shown_a), ('B', shown_b)):
            lines.append(f'Robot {label}:')
            for i, render in enumerate(renders, 1):
                target = images / f'{label}-{i}.png'
                shutil.copyfile(render, target)
                lines.append(f'- {target}')
            lines.append('')
        lines.append('Read all of them, then reply with the JSON object only.')
        argv = [
            claude, '-p', '\n'.join(lines),
            '--model', MODEL,  # no --fallback-model: a refused model is not a verdict
            '--effort', spec['effort'],
            '--output-format', 'json',
            '--system-prompt', spec['instructions'],
            '--tools', 'Read',
            '--allowedTools', 'Read',
            '--strict-mcp-config',
            '--setting-sources', 'project',
            '--no-session-persistence',
            '--add-dir', str(images),
        ]
        done = subprocess.run(argv, cwd=work, capture_output=True, text=True, timeout=1800,
                              env={k: v for k, v in os.environ.items() if not k.startswith('CADEX_')})
    if done.returncode != 0:
        raise JudgeError(f'claude exited {done.returncode}: {done.stderr[-400:] or done.stdout[-400:]}')
    envelope = json.loads(done.stdout)
    if envelope.get('is_error'):
        raise JudgeError(f"claude reported an error: {str(envelope.get('result'))[:400]}")
    receipt = {k: envelope.get(k) for k in ('duration_ms', 'num_turns', 'total_cost_usd')}
    return parse(str(envelope.get('result') or '')), receipt


def judge_pair(claude: str, version: str, inputs: Path, a: str, b: str, mirror: bool = False) -> dict:
    shown_a, shown_b = order(version, a, b, mirror)
    views = VERSIONS[version]['views']
    errors = []
    for attempt in (1, 2):
        try:
            verdict, receipt = one_call(claude, version, [inputs / shown_a / v for v in views],
                                        [inputs / shown_b / v for v in views])
            winner = shown_a if verdict['winner'] == 'A' else shown_b
            return {'pair': sorted((a, b)), 'shown_a': shown_a, 'shown_b': shown_b, 'winner': winner,
                    'picked': verdict['winner'], 'reason': verdict['reason'], 'errors': errors, **receipt}
        except (JudgeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
            errors.append(str(exc)[:400])
    return {'pair': sorted((a, b)), 'shown_a': shown_a, 'shown_b': shown_b, 'winner': None, 'errors': errors}


def scores(designs: list[str], results: list[dict]) -> dict[str, float]:
    """Each design's fraction of judged comparisons won."""

    won = {d: 0 for d in designs}
    played = {d: 0 for d in designs}
    for r in results:
        if r.get('winner') is None:
            continue
        for d in r['pair']:
            played[d] += 1
        won[r['winner']] += 1
    return {d: won[d] / played[d] for d in designs if played[d]}


def load(path: Path) -> dict[tuple[str, str], dict]:
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    return {tuple(r['pair']): r for r in rows if r.get('winner')}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--version', choices=sorted(VERSIONS), required=True)
    parser.add_argument('--split', choices=('dev', 'heldout'), required=True)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--mirror', action='store_true', help='swap every pair\'s sides (a replicate)')
    parser.add_argument('--claude', default=shutil.which('claude') or 'claude')
    args = parser.parse_args(argv)
    inputs = args.inputs.expanduser().resolve()
    if args.split == 'heldout':
        if FROZEN.get(args.version) != instructions_sha256(args.version) or args.mirror:
            print(f'{args.version} is not a frozen version: it may not judge heldout', file=sys.stderr)
            return 2
        if (args.out / 'pairs.jsonl').exists() and not (args.out / 'summary.json').exists():
            pass  # an interrupted held-out run resumes; nothing was measured from it yet
        elif args.out.exists() and any(args.out.iterdir()):
            print(f'{args.out} already holds a held-out result: it is measured once', file=sys.stderr)
            return 2
    args.out.mkdir(parents=True, exist_ok=True)
    owner = split_verdicts(args.split)
    designs = sorted(owner)
    views = VERSIONS[args.version]['views']
    absent = [f'{d}/{v}' for d in designs for v in views if not (inputs / d / v).exists()]
    if absent:
        print(f'missing inputs: {absent}', file=sys.stderr)
        return 2
    log = args.out / 'pairs.jsonl'
    done = load(log)
    todo = [p for p in combinations(designs, 2) if p not in done]
    lock = threading.Lock()

    def run(pair: tuple[str, str]) -> None:
        row = judge_pair(args.claude, args.version, inputs, *pair, mirror=args.mirror)
        with lock:
            with log.open('a', encoding='utf-8') as fh:
                fh.write(json.dumps(row) + '\n')
            if row['winner'] is None:
                print(f'harness failure: {pair}: {row["errors"]}', file=sys.stderr, flush=True)

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(run, todo))
    results = list(load(log).values())
    pairs = list(combinations(designs, 2))
    score = scores(designs, results)
    picked_a = sum(1 for r in results if r['picked'] == 'A')
    receipts = {d: json.loads((inputs / d / 'receipt.json').read_text(encoding='utf-8')) for d in designs}
    summary = {
        'schema': 'orun1-pairwise-v1', 'version': args.version, 'split': args.split, 'mirror': args.mirror, 'model': MODEL,
        'effort': VERSIONS[args.version]['effort'], 'views': list(views),
        'instructions_sha256': instructions_sha256(args.version),
        'pairs': len(pairs), 'judged': len(results),
        'unjudged': [list(p) for p in pairs if p not in load(log)],
        'position_a_rate': picked_a / len(results) if results else None,
        'cost_usd': round(sum(r.get('total_cost_usd') or 0 for r in results), 2),
        'inputs': {d: {'accepted_revision': receipts[d]['accepted_revision'],
                       'sha256': {v: hashlib.sha256((inputs / d / v).read_bytes()).hexdigest() for v in views}}
                   for d in designs},
        'owner_verdicts': owner, 'scores': score, **evaluate(owner, score),
    }
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    p, k = summary['pairwise_2plus'], summary['kendall']
    print(json.dumps({'agreement': p['agreement'], 'agree': p['agree'], 'ties': p['ties'],
                      'counted': p['counted'], 'love_over_no': summary['love_over_no']['holds'],
                      'tau_b': k['tau_b'], 'tau_pairs': k['counted'], 'judged': len(results),
                      'unjudged': len(summary['unjudged']), 'position_a_rate': summary['position_a_rate']}))
    return 0 if not summary['unjudged'] else 1


if __name__ == '__main__':
    sys.exit(main())
