# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Run ot10's frozen judge over the orun1 held-out set: the D1 baseline.

For each held-out design with no ``baseline/<id>-score.json`` yet: copy its
sweep project to ``orun1-ho-<id>`` (the original stays read-only), draw the
ot10 input set with ``render_set.py``, score it with
``docs/probes/ot10/runner/judge.py`` unchanged, and write the score with the
design id and the render receipt beside it. A design that already has a
score is never judged again: each is measured once (README, D1 baseline).

A copy left behind by an interrupted run with no score is replaced, since
nothing was measured from it. A harness failure writes no score and is
reported; rerunning picks up only what is missing.

    pixi run python docs/probes/orun1/runner/baseline.py --jobs 3
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))

from metrics import heldout  # noqa: E402
from render_set import renders  # noqa: E402

OUT = HERE.parent / 'baseline'
PROJECTS = Path.home() / 'cadex-projects'
JUDGE = REPO / 'docs/probes/ot10/runner/judge.py'


def score_one(design: str, work: Path) -> str:
    target = OUT / f'{design}-score.json'
    if target.exists():
        return f'{design}: already scored, not re-judged'
    copy = PROJECTS / f'orun1-ho-{design}'
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(PROJECTS / f'sweep-{design}', copy, symlinks=True)
    inputs = work / design
    inputs.mkdir(parents=True, exist_ok=True)
    drawn = subprocess.run([sys.executable, str(HERE / 'render_set.py'), str(copy), str(inputs)],
                           capture_output=True, text=True)
    if drawn.returncode != 0:
        return f'{design}: render failed: {drawn.stderr[-600:]}'
    raw = work / f'{design}-judge.json'
    judged = subprocess.run([sys.executable, str(JUDGE), '--out', str(raw), *map(str, renders(inputs))],
                            capture_output=True, text=True)
    if judged.returncode != 0:
        return f'{design}: judge harness failure: {judged.stderr[-600:]}'
    result = json.loads(raw.read_text(encoding='utf-8'))
    result['design'] = design
    result['receipt'] = json.loads((inputs / 'receipt.json').read_text(encoding='utf-8'))
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return f"{design}: total {result['total']}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--work', type=Path, default=None)
    args = parser.parse_args(argv)
    work = args.work or Path(tempfile.mkdtemp(prefix='orun1-baseline-'))
    designs = sorted(heldout())
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for line in pool.map(lambda d: score_one(d, work), designs):
            print(line, flush=True)
    missing = [d for d in designs if not (OUT / f'{d}-score.json').exists()]
    print(json.dumps({'designs': len(designs), 'missing': missing}))
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
