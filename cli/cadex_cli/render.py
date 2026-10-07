# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""``cadex render``: the review render of the accepted revision, as a CLI job.

What this module does is client work: rebuild for the accepted display, read
the fit and inventory blocks, and write the files. The drawing -- the studio
views, the hero, the concept sheet and the design proxies -- is the engine's
``CadexStudio`` (ADR-445), loaded by :mod:`studio`, so the shell draws with
the same code.

Independently authored LGPL client code.
"""
from __future__ import annotations

from pathlib import Path
import time

from .inventory import InventoryError
from .studio import STUDIO


def describe_proxies(proxies):
    """One line for a report: each proxy's value against its bar."""
    return STUDIO.describe_proxies(proxies)


def _published_blocks(client):
    """The fit and inventory blocks for the accepted revision; ``None`` for either unreadable."""
    from .clearance import read_fit
    from .inventory import read_inventory_summary
    blocks = []
    for read in (read_fit, read_inventory_summary):
        try:
            blocks.append(read(client))
        except Exception:  # a render with no inventory still draws, in index colours
            blocks.append(None)
    return blocks


def acquire_snapshot(client):
    start = time.perf_counter()
    reply = client.request('rebuild', {'display': {'quality': 'standard', 'edges': False}})
    # The accepted revision's fit names the floor, which must not size the
    # clustering grid; a fit that cannot be read leaves every part sizing it.
    fit = None
    if reply.get('ok') is True:
        from .clearance import read_fit
        try:
            fit = read_fit(client)
        except Exception:
            pass
    try:
        triangles, summary = STUDIO.snapshot(reply, STUDIO.world(fit))
    except STUDIO.StudioError as exc:
        raise InventoryError(str(exc)) from exc
    summary['acquisition_seconds'] = time.perf_counter() - start
    return triangles, summary


def write_render(client, root, *, expected_revision=None, accepted_snapshot=None):
    triangles, source = accepted_snapshot if accepted_snapshot is not None else acquire_snapshot(client)
    if expected_revision is not None and source['revision'] != expected_revision:
        raise InventoryError('render: accepted revision differs from rollout')
    relative_dir = 'review/render' + (f'/{expected_revision}' if expected_revision else '')
    fit, inventory = _published_blocks(client)
    directory = Path(root) / relative_dir
    try:
        # Drawn whole before anything is written: a refusal leaves no partial views.
        files, summary = STUDIO.render_files(triangles, source, root, fit, inventory, relative_dir)
        STUDIO.write_files(directory, files)
    except STUDIO.StudioError as exc:
        raise InventoryError(str(exc)) from exc
    return directory / 'summary.json', summary


def retained_snapshot(root, fit=None):
    """``(triangles, summary)`` of the accepted revision, read from what its attempt retained.

    No rebuild: a rebuild reply's ``display`` is the attempt's outputs with
    their paths made absolute (``cadexd._display_block``), and this builds
    the same block from the retained ``result.json``, so a command that must
    not run the script (``cadex evaluate``) draws what ``cadex render``
    would. ``fit`` names the world geometry, as for :func:`acquire_snapshot`.
    """
    from .smoke import retained_attempt
    try:
        state, staging, result = retained_attempt(Path(root))
    except Exception as exc:  # noqa: BLE001 - one reason, whatever was unreadable
        raise InventoryError(f'cannot read the retained accepted attempt: {exc}') from exc
    display = {}
    for item in result.get('outputs') or []:
        name = str(item.get('name') or '')
        entry = {'artifact_kind': item.get('artifact_kind') or None,
                 'placement': item.get('solved_placement_matrix'), 'tessellation': None}
        if item.get('source_output'):
            entry['source_output'] = str(item['source_output'])
        tessellation = item.get('display')
        if isinstance(tessellation, dict):
            paths = {}
            for key in ('artifact_path', 'sidecar_path'):
                path = (staging / str(tessellation.get(key) or '')).resolve()
                if not path.is_relative_to(staging):
                    raise InventoryError(f'retained tessellation for {name} escapes its attempt')
                paths[key] = str(path)
            entry['tessellation'] = {**tessellation, **paths}
        display[name] = entry
    revision = str(state['accepted_revision'])
    try:
        return STUDIO.snapshot({'ok': True, 'revision': revision, 'accepted_revision': revision,
                                'digest': state.get('accepted_digest'), 'display': display},
                               STUDIO.world(fit))
    except STUDIO.StudioError as exc:
        raise InventoryError(str(exc)) from exc
