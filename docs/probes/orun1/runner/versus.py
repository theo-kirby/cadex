# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""D4's bar: a new design against the sweep designs of its type rated Like or Love.

The judge is the frozen v2 (``pairwise.FROZEN``), called exactly as D1
measured it: one call per pair, the hero only, the side shown as ``A``
fixed by ``pairwise.order``. The opponents' heroes are the ones D1 judged:
each must hash to the value recorded in ``judge/v2-dev/summary.json`` or
``judge/v2-heldout/summary.json``, or nothing is called. Using a held-out
design as an opponent is what D4 prescribes; nothing is tuned on it.

DESIGN_DIR holds the new design's ``hero.png`` and ``receipt.json`` as
``render_set.py`` writes them from its project at the accepted revision.
The new design wins the bar when it wins a strict majority of its judged
comparisons. Results go to ``OUT/pairs.jsonl`` (resumable) and
``OUT/summary.json``.

    pixi run python docs/probes/orun1/runner/versus.py balancer \\
        ~/cadex-projects/orun1-d4/orun1-t1-balancer \\
        --out docs/probes/orun1/d4/t1-balancer
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pairwise  # noqa: E402
from metrics import RATINGS  # noqa: E402

VERSION = 'v2'
SWEEP_HEROES = Path.home() / 'cadex-projects/orun1-judge'
JUDGED = HERE.parent / 'judge'


def opponents(category: str, ratings_path: Path = RATINGS) -> dict[str, str]:
    """Sweep designs of ``category`` the owner rated Like or Love, with their split."""

    ratings = json.loads(ratings_path.read_text(encoding='utf-8'))
    return {d['id']: d['split'] for d in ratings['designs']
            if d['category'] == category and d['owner_verdict'] in ('like', 'love')}


def recorded_hashes() -> dict[str, str]:
    hashes = {}
    for split in ('dev', 'heldout'):
        summary = json.loads((JUDGED / f'{VERSION}-{split}/summary.json').read_text(encoding='utf-8'))
        hashes.update({d: v['sha256']['hero.png'] for d, v in summary['inputs'].items()})
    return hashes


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('category')
    parser.add_argument('design_dir', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--heroes', type=Path, default=SWEEP_HEROES)
    parser.add_argument('--claude', default=shutil.which('claude') or 'claude')
    args = parser.parse_args(argv)
    if pairwise.FROZEN.get(VERSION) != pairwise.instructions_sha256(VERSION):
        print(f'{VERSION} no longer matches its frozen hash', file=sys.stderr)
        return 2
    rivals = opponents(args.category)
    if not rivals:
        print(f'no Like or Love sweep design of category {args.category!r}', file=sys.stderr)
        return 2
    design_dir = args.design_dir.expanduser().resolve()
    receipt = json.loads((design_dir / 'receipt.json').read_text(encoding='utf-8'))
    design = receipt['project']
    if design in rivals:
        print(f'{design} is a sweep design', file=sys.stderr)
        return 2
    recorded = recorded_hashes()
    heroes = {d: args.heroes.expanduser() / ('dev' if s == 'dev' else 'heldout') / d / 'hero.png'
              for d, s in rivals.items()}
    stale = [d for d, p in heroes.items() if not p.exists() or sha256(p) != recorded[d]]
    if stale:
        print(f'opponent heroes differ from the ones D1 judged: {stale}', file=sys.stderr)
        return 2
    args.out.mkdir(parents=True, exist_ok=True)
    log = args.out / 'pairs.jsonl'
    done = pairwise.load(log)
    with tempfile.TemporaryDirectory(prefix='orun1-versus-') as tmp:
        inputs = Path(tmp)
        for d, hero in {design: design_dir / 'hero.png', **heroes}.items():
            (inputs / d).mkdir()
            shutil.copyfile(hero, inputs / d / 'hero.png')
        for rival in sorted(rivals):
            if tuple(sorted((design, rival))) in done:
                continue
            row = pairwise.judge_pair(args.claude, VERSION, inputs, design, rival)
            with log.open('a', encoding='utf-8') as fh:
                fh.write(json.dumps(row) + '\n')
            if row['winner'] is None:
                print(f'harness failure: {rival}: {row["errors"]}', file=sys.stderr, flush=True)
    results = list(pairwise.load(log).values())
    won = sorted(r['pair'][0] if r['pair'][0] != design else r['pair'][1]
                 for r in results if r['winner'] == design)
    lost = sorted(r['winner'] for r in results if r['winner'] != design)
    unjudged = sorted(set(rivals) - set(won) - set(lost))
    ratings = {d['id']: d['owner_verdict'] for d in
               json.loads(RATINGS.read_text(encoding='utf-8'))['designs']}
    summary = {
        'schema': 'orun1-versus-v1', 'version': VERSION, 'model': pairwise.MODEL,
        'instructions_sha256': pairwise.instructions_sha256(VERSION),
        'category': args.category, 'design': design,
        'accepted_revision': receipt['accepted_revision'], 'hero_sha256': sha256(design_dir / 'hero.png'),
        'opponents': {d: ratings[d] for d in sorted(rivals)},
        'won': won, 'lost': lost, 'unjudged': unjudged,
        'majority': len(won) * 2 > len(rivals) and not unjudged,
        'reasons': {r['pair'][0] if r['pair'][0] != design else r['pair'][1]: r['reason'] for r in results},
        'cost_usd': round(sum(r.get('total_cost_usd') or 0 for r in results), 2),
    }
    (args.out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('design', 'won', 'lost', 'unjudged', 'majority')}))
    return 0 if not unjudged else 1


if __name__ == '__main__':
    sys.exit(main())
