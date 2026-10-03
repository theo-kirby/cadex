# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Draw one split's judge inputs: copy each sweep project, then render it.

For every design of ``--split`` with no ``receipt.json`` under ``OUT/<id>``
yet: copy ``sweep-<id>`` to ``orun1-<prefix>-<id>`` (the original stays
read-only; ``cadex render`` re-accepts, ADR-476) and draw its inputs with
``render_set.py``. A copy left by an interrupted draw is replaced. The
renders stay outside the repository; only their receipts and hashes are
published, by the judge that reads them.

    pixi run python docs/probes/orun1/runner/draw_set.py --split dev \\
        --out ~/cadex-projects/orun1-judge/dev --jobs 2
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from metrics import split_verdicts  # noqa: E402

PROJECTS = Path.home() / 'cadex-projects'
PREFIX = {'dev': 'dev', 'heldout': 'ho'}


def draw_one(design: str, split: str, out: Path) -> str:
    inputs = out / design
    if (inputs / 'receipt.json').exists():
        return f'{design}: already drawn'
    copy = PROJECTS / f'orun1-{PREFIX[split]}-{design}'
    if copy.exists():
        shutil.rmtree(copy)
    shutil.copytree(PROJECTS / f'sweep-{design}', copy, symlinks=True)
    inputs.mkdir(parents=True, exist_ok=True)
    drawn = subprocess.run([sys.executable, str(HERE / 'render_set.py'), str(copy), str(inputs)],
                           capture_output=True, text=True)
    if drawn.returncode != 0:
        return f'{design}: render failed: {drawn.stderr[-600:]}'
    return f'{design}: drawn'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--split', choices=sorted(PREFIX), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args(argv)
    out = args.out.expanduser().resolve()
    designs = sorted(split_verdicts(args.split))
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for line in pool.map(lambda d: draw_one(d, args.split, out), designs):
            print(line, flush=True)
    missing = [d for d in designs if not (out / d / 'receipt.json').exists()]
    print(json.dumps({'designs': len(designs), 'missing': missing}))
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
