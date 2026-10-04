# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""A project's accepted revisions, and going back through them (orun2 D2, ADR-506).

The engine keeps the undo trail: ``script_history/`` in the project root,
every accepted source as a plain ``.py`` file and ``history.json`` indexing
them, oldest first (ADR-045), each entry now with the values it was accepted
with (ADR-506). This module only *reads* that trail. Putting a version back
is the engine's ordinary ``write_script`` (and ``set_params`` for its
values), run by ``cadex revision``, so a restored version re-runs and is
re-accepted like anything else rather than trusted because it used to work.

"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

HISTORY_DIR = "script_history"
HISTORY_INDEX = "history.json"
def read_history(root: Path | str) -> list[dict[str, Any]]:
    """The accepted revisions, oldest first; empty when there is no trail."""

    path = Path(root).expanduser() / HISTORY_DIR / HISTORY_INDEX
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = data.get("entries") if isinstance(data, dict) else None
    return [dict(item) for item in entries or [] if isinstance(item, dict)]


def select(entries: list[Mapping[str, Any]], selector: str) -> dict[str, Any]:
    """One entry by ordinal or by a unique revision prefix; ``ValueError`` if none.

    The same rule the engine's ``inspect scope=history`` applies, so a
    selector read out of either listing means the same version.
    """

    want = str(selector or "").strip().lower()
    if not want:
        raise ValueError("name a revision: its ordinal or a revision prefix.")
    matched = [entry for entry in entries if str(entry.get("ordinal")) == want]
    if not matched:
        matched = [entry for entry in entries
                   if str(entry.get("revision") or "").startswith(want)]
    if len(matched) != 1:
        raise ValueError(
            f"no single stored revision matches {selector!r}"
            + (f" ({len(matched)} do)." if matched else ".")
            + " `cadex revision list` shows the trail."
        )
    return dict(matched[0])


def previous(entries: list[Mapping[str, Any]], revision: str) -> dict[str, Any]:
    """The version accepted before ``revision`` last was; ``ValueError`` if none."""

    for index in range(len(entries) - 1, -1, -1):
        if str(entries[index].get("revision") or "") == revision:
            for earlier in reversed(entries[:index]):
                if str(earlier.get("revision") or "") != revision:
                    return dict(earlier)
            break
    else:
        raise ValueError(f"revision {revision[:12] or '(none)'} is not in the stored trail.")
    raise ValueError(f"no revision was accepted before {revision[:12]}: nothing to go back to.")


def read_source(root: Path | str, entry: Mapping[str, Any]) -> str:
    """The stored source of one entry; ``ValueError`` when its file is gone."""

    name = Path(str(entry.get("file") or "")).name
    path = Path(root).expanduser() / HISTORY_DIR / name
    try:
        source = path.read_text(encoding="utf-8") if name else ""
    except OSError:
        source = ""
    if not source.strip():
        raise ValueError(f"the stored source of revision {entry.get('ordinal')} is missing.")
    return source
