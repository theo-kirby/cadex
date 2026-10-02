# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Draw a design's judge inputs from its project at the accepted revision.

The set is ot10's (``docs/probes/ot10/README.md``, Procedure): the 1024 px
studio hero that ``cadex render`` writes, then the five ``look`` views
``iso``, ``iso_back``, ``front``, ``right`` and ``top``, drawn by the CLI
bridge's own ``look`` tool -- the pictures the product agent sees, not a
second renderer. Run it on an ``orun1-*`` copy, never on an original:
``cadex render`` re-accepts (ADR-476).

    pixi run python docs/probes/orun1/runner/render_set.py PROJECT OUTDIR
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / 'cli'))

from cadex_cli.bridge import Bridge  # noqa: E402
from cadex_cli.client import CadexdClient, open_project  # noqa: E402
from cadex_cli.engine import resolve_engine  # noqa: E402

LOOK_VIEWS = ('iso', 'iso_back', 'front', 'right', 'top')


def hero(project: Path, out: Path) -> dict:
    done = subprocess.run([str(REPO / 'cadex'), 'render', '--project', str(project), '--json'],
                          capture_output=True, text=True, timeout=3600)
    if done.returncode != 0:
        raise RuntimeError(f'cadex render exited {done.returncode}: {done.stderr[-600:]}')
    envelope = json.loads(done.stdout)
    shutil.copyfile(project / 'review/render/hero.png', out / 'hero.png')
    return envelope


def looks(project: Path, out: Path) -> dict:
    client = CadexdClient(resolve_engine(None))
    client.start()
    try:
        opened = open_project(client, project)
        bridge = Bridge(client, initial_revision=str(opened.get('revision') or ''))
        reply = bridge.call('look', {'views': list(LOOK_VIEWS)})
    finally:
        client.shutdown()
    if reply.get('is_error'):
        raise RuntimeError(f"look failed: {reply['content'][0]['text'][:600]}")
    facts = json.loads(reply['content'][0]['text'])
    images = [c for c in reply['content'] if c['type'] == 'image']
    if len(images) != len(LOOK_VIEWS):
        raise RuntimeError(f'look returned {len(images)} images for {len(LOOK_VIEWS)} views')
    for view, image in zip(LOOK_VIEWS, images):
        (out / f'look_{view}.png').write_bytes(base64.b64decode(image['data']))
    return facts


def renders(out: Path) -> list[Path]:
    """The judge's candidate order: hero, then the look views."""

    return [out / 'hero.png'] + [out / f'look_{v}.png' for v in LOOK_VIEWS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('project', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args(argv)
    project = args.project.expanduser().resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    rendered = hero(project, args.out)
    facts = looks(project, args.out)
    revision = json.loads((project / 'script.json').read_text())['accepted_attempt']['revision']
    receipt = {'project': project.name, 'accepted_revision': revision,
               'look_revision': facts.get('revision'),
               'render_ok': rendered.get('ok', rendered.get('exit_code') == 0),
               'renders': [p.name for p in renders(args.out)]}
    (args.out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    return 0


if __name__ == '__main__':
    sys.exit(main())
