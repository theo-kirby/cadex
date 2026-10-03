# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Score a judge against the owner's verdicts on the held-out set.

The three metrics D1 names (``.ouroboros/goal.md``), computed the way the
orun1 README pre-registers them:

- **pairwise agreement** over every held-out pair whose owner verdicts
  differ by two levels or more: the pair agrees when the higher-rated
  design has the strictly higher judge score. A tie is a disagreement and
  is also counted on its own.
- **Love over No**: every held-out Love scores strictly above every
  held-out No.
- **Kendall's tau-b** between owner verdict (0-3) and judge score over all
  held-out pairs, with its concordant, discordant and tied counts.

A design with no score is missing: it is dropped, and every metric names
the pairs it drops. ``split_verdicts`` reads either split, so a judge can
be built on ``dev``; the command line below scores ``heldout`` only.

    pixi run python docs/probes/orun1/runner/metrics.py SCORES_DIR --out summary.json
"""

from __future__ import annotations

import argparse
from itertools import combinations
import json
import math
from pathlib import Path
import sys

RATINGS = Path(__file__).resolve().parents[1] / 'sweep/ratings.json'
SCALE = {'love': 3, 'like': 2, 'meh': 1, 'no': 0}
BAR = 0.80
GAP = 2


def split_verdicts(split: str, ratings_path: Path = RATINGS) -> dict[str, int]:
    """Design id -> owner verdict on the 0-3 scale, for one split."""

    ratings = json.loads(ratings_path.read_text(encoding='utf-8'))
    return {d['id']: SCALE[d['owner_verdict']] for d in ratings['designs'] if d['split'] == split}


def heldout(ratings_path: Path = RATINGS) -> dict[str, int]:
    """Held-out design id -> owner verdict on the 0-3 scale."""

    return split_verdicts('heldout', ratings_path)


def pairwise(owner: dict[str, int], score: dict[str, float], gap: int = GAP) -> dict:
    """Order agreement over the pairs whose owner verdicts differ by ``gap`` or more."""

    pairs = [(a, b) for a, b in combinations(sorted(owner), 2) if abs(owner[a] - owner[b]) >= gap]
    agree, ties, disagree, dropped = [], [], [], []
    for a, b in pairs:
        if a not in score or b not in score:
            dropped.append([a, b])
            continue
        hi, lo = (a, b) if owner[a] > owner[b] else (b, a)
        (agree if score[hi] > score[lo] else ties if score[hi] == score[lo] else disagree).append([hi, lo])
    counted = len(agree) + len(ties) + len(disagree)
    rate = len(agree) / counted if counted else None
    return {'pairs': len(pairs), 'counted': counted, 'agree': len(agree), 'ties': len(ties),
            'disagree': len(disagree), 'agreement': rate,
            'meets_bar': rate is not None and rate >= BAR and not dropped,
            'tied_pairs': ties, 'disagreeing_pairs': disagree, 'dropped_pairs': dropped}


def love_over_no(owner: dict[str, int], score: dict[str, float]) -> dict:
    loves = sorted(d for d, v in owner.items() if v == SCALE['love'])
    nos = sorted(d for d, v in owner.items() if v == SCALE['no'])
    pairs = [(a, b) for a in loves for b in nos]
    dropped = [[a, b] for a, b in pairs if a not in score or b not in score]
    failed = [[a, b] for a, b in pairs if a in score and b in score and not score[a] > score[b]]
    return {'pairs': len(pairs), 'failed_pairs': failed, 'dropped_pairs': dropped,
            'holds': not failed and not dropped}


def kendall_tau_b(owner: dict[str, int], score: dict[str, float]) -> dict:
    """tau-b = (C - D) / sqrt((n0 - n1)(n0 - n2)) over the scored designs."""

    ids = sorted(owner)
    pairs = list(combinations(ids, 2))
    dropped = [[a, b] for a, b in pairs if a not in score or b not in score]
    concordant = discordant = tied_owner = tied_judge = tied_both = 0
    for a, b in pairs:
        if a not in score or b not in score:
            continue
        x, y = owner[a] - owner[b], score[a] - score[b]
        if x == 0 and y == 0:
            tied_both += 1
        elif x == 0:
            tied_owner += 1
        elif y == 0:
            tied_judge += 1
        elif (x > 0) == (y > 0):
            concordant += 1
        else:
            discordant += 1
    n0 = concordant + discordant + tied_owner + tied_judge + tied_both
    n1 = tied_owner + tied_both  # pairs tied in the owner's verdict
    n2 = tied_judge + tied_both  # pairs tied in the judge's score
    denom = math.sqrt((n0 - n1) * (n0 - n2))
    return {'pairs': len(pairs), 'counted': n0, 'concordant': concordant, 'discordant': discordant,
            'tied_owner_only': tied_owner, 'tied_judge_only': tied_judge, 'tied_both': tied_both,
            'tau_b': (concordant - discordant) / denom if denom else None, 'dropped_pairs': dropped}


def evaluate(owner: dict[str, int], score: dict[str, float]) -> dict:
    missing = sorted(d for d in owner if d not in score)
    return {'designs': len(owner), 'scored': len(owner) - len(missing), 'missing': missing,
            'pairwise_2plus': pairwise(owner, score), 'love_over_no': love_over_no(owner, score),
            'kendall': kendall_tau_b(owner, score)}


def scores_from(directory: Path, owner: dict[str, int]) -> dict[str, float]:
    """``<id>-score.json`` files written by a judge, keyed by design id."""

    found = {}
    for design in owner:
        path = directory / f'{design}-score.json'
        if path.exists():
            found[design] = json.loads(path.read_text(encoding='utf-8'))['total']
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('scores', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    owner = heldout()
    score = scores_from(args.scores, owner)
    result = {'owner_verdicts': owner, 'scores': score, **evaluate(owner, score)}
    args.out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    p, k = result['pairwise_2plus'], result['kendall']
    print(json.dumps({'agreement': p['agreement'], 'agree': p['agree'], 'ties': p['ties'],
                      'counted': p['counted'], 'love_over_no': result['love_over_no']['holds'],
                      'tau_b': k['tau_b'], 'tau_pairs': k['counted'], 'missing': result['missing']}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
