# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The blueprint store: rendered drawing sheets, attached to accepted revisions.

A blueprint sheet is a **stored deliverable** (ADR-150): the shell renders a
four-view PNG in the drawing-office style and hands it to the engine over
``put_blueprint``, because the engine is the sole writer of the project store
(docs/ARCHITECTURE.md) and a picture of an accepted revision belongs beside
that revision, not inside the ``.blend`` and not inside ``script.py``. Each
entry records the accepted ``(revision, digest)`` pair it was rendered from —
that pair is the whole of "attached to the script": the sheet documents a
script state, and a rebuild that moves the model leaves the old sheet
honestly labelled with the revision it drew.

A sheet may also carry a **name** (ADR-157) — ``"gearbox overview v1"`` —
and a name is an identity rather than a caption: re-rendering under the same
name stores the next **version** of that sheet, ``resolve_blueprint`` serves
the newest version by name, and the prune never drops a name's newest
version. That is what makes a blueprint revisable: the shell stores the
recipe it rendered from in ``meta``, reads it back by name, and re-renders
with the agent's edits on top.

Layout under one project root:

- ``blueprints/{ordinal:04d}-{slug or revision[:12]}.png`` — the sheets
  themselves, the slug being the name reduced to filename characters so an
  exported directory reads as the drawings it holds.
- ``blueprints/blueprints.json`` — the index (schema ``cadex-blueprint-v1``).

The shape is ``CadexScriptStore.record_history``'s deliberately: ordinals
count up forever, files are named by ordinal and revision prefix, the index
is pruned to a bound (:data:`BLUEPRINT_LIMIT`) that keeps the directory
readable rather than protecting disk, and old revisions' sheets are KEPT
until the bound pushes them out — history semantics, not latest-only.

Nothing here imports FreeCAD, so the store is exercised by the stubbed
pytest suite exactly as it runs under cadexd.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any
import uuid

from CadexScriptStore import (
    CadexProjectScriptStore,
    atomic_write_json,
    now_iso,
)

BLUEPRINT_SCHEMA = "cadex-blueprint-v1"
BLUEPRINT_DIR_NAME = "blueprints"
BLUEPRINT_INDEX_NAME = "blueprints.json"

#: Sheets kept, newest last. A bound on the directory's readability, exactly
#: as ``HISTORY_LIMIT`` is for the undo trail: old revisions' sheets stay
#: until the count pushes them out, so a project's recent drawing history
#: survives its rebuilds. **Named** sheets are additionally protected — each
#: name's newest version is kept past the bound (ADR-157), so the index can
#: hold a few more rows than this when many names are in play.
BLUEPRINT_LIMIT = 25

#: One rendered sheet is a few hundred KB; sixteen megabytes is a composite
#: nobody asked for, refused rather than stored.
MAX_BLUEPRINT_BYTES = 16 * 1024 * 1024

#: ``label`` is one line under a drawing, not a document.
MAX_LABEL_CHARS = 120

#: ``name`` is what a person calls the drawing — "gearbox overview v1" —
#: short enough to read in a listing and to survive as a filename slug.
MAX_NAME_CHARS = 60

#: ``meta`` is the renderer's own record (theme, views, sizes) *and*, since
#: ADR-157, the **recipe** the sheet can be re-rendered from — text panels
#: included. Bounded so the index stays an index; the shell trims its own
#: optional records before it hits this.
MAX_META_BYTES = 16 * 1024

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _blueprint_dir(project_root: Path | str) -> Path:
    return Path(project_root) / BLUEPRINT_DIR_NAME


def read_blueprints(project_root: Path | str) -> list[dict[str, Any]]:
    """Stored sheets, oldest first. Never raises on a bad index."""

    index = _blueprint_dir(project_root) / BLUEPRINT_INDEX_NAME
    try:
        data = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict) or data.get("schema") != BLUEPRINT_SCHEMA:
        return []
    entries = data.get("entries")
    return [dict(item) for item in entries or [] if isinstance(item, dict)]


def normalize_name(name: str) -> str:
    """The stored form of a sheet's name, or ``ValueError`` on a bad one.

    Whitespace collapses (a name is one line), control characters are
    refused rather than smuggled into an index a person reads, and the cap
    is :data:`MAX_NAME_CHARS`. An empty name is legal and means "unnamed" —
    the pre-ADR-157 sheet, which is a record and not a thing to revise.
    """

    text = " ".join(str(name or "").split())
    if not text:
        return ""
    if any(ord(char) < 32 or ord(char) == 127 for char in text):
        raise ValueError("A blueprint name is one line of plain text.")
    if len(text) > MAX_NAME_CHARS:
        raise ValueError(
            f"name is {len(text)} characters; the cap is {MAX_NAME_CHARS}. "
            "A name is what you call the drawing; the label is the caption."
        )
    return text


def name_slug(name: str) -> str:
    """A name reduced to filename characters, or ``""`` if nothing survives.

    Exports keep store filenames (``export --blueprints``), so this is what
    makes an exported directory read as the drawings it holds rather than as
    a column of revision prefixes.
    """

    out = []
    for char in str(name or "").lower():
        out.append(char if char.isalnum() and char.isascii() else "-")
    slug = "-".join(part for part in "".join(out).split("-") if part)
    return slug[:32].strip("-")


def _named(entry: Any) -> str:
    return str((entry or {}).get("name") or "").casefold()


def resolve_blueprint(
    project_root: Path | str, selector: str | int
) -> dict[str, Any] | None:
    """One stored sheet, by ordinal, name, revision prefix or filename.

    ``read_history_source``'s selector rules, plus the name: an exact
    ordinal wins, then an exact name (``"gearbox v1"`` — its **newest**
    version, or a pinned one with ``"gearbox v1@2"``), then a unique
    revision prefix, then the exact stored filename. Ambiguity is None, not
    a guess — and a name is never ambiguous, because its versions are
    ordered.
    """

    entries = read_blueprints(project_root)
    want = str(selector).strip().lower()
    if not want:
        return None
    matched = [e for e in entries if str(e.get("ordinal")) == want]
    if not matched:
        wanted_name, _, wanted_version = want.rpartition("@")
        if not wanted_name or not wanted_version.isdigit():
            wanted_name, wanted_version = want, ""
        named = [e for e in entries if _named(e) == wanted_name.strip()]
        if named and wanted_version:
            named = [e for e in named
                     if str(e.get("version") or "") == wanted_version]
        if named:
            return dict(named[-1])       # the newest version of that name
    if not matched:
        matched = [e for e in entries
                   if str(e.get("revision") or "").lower().startswith(want)]
    if not matched:
        matched = [e for e in entries
                   if str(e.get("file") or "").lower() == want]
    if len(matched) != 1:
        return None
    return dict(matched[-1])


def blueprint_path(project_root: Path | str, entry: dict[str, Any]) -> Path:
    return _blueprint_dir(project_root) / str(entry.get("file") or "")


def store_project_blueprint(
    project_root: Path | str,
    source_path: str,
    label: str = "",
    meta: dict[str, Any] | None = None,
    name: str = "",
) -> dict[str, Any]:
    """Copy one rendered PNG into ``blueprints/`` and index it.

    A path, not bytes, on ``put_asset``'s reasoning exactly: both halves
    share a filesystem, and the frame cap is 8 MB. Raises ``ValueError`` on
    every refusal; the op handler turns those into ``tool_failure``.

    ``name`` makes the sheet revisable (ADR-157): storing again under a name
    that already exists appends the next ``version`` of it rather than an
    unrelated row, and the prune below protects each name's newest version.
    An empty ``label`` takes the name, so a named sheet captions itself.

    Write order is PNG first, index second: a crash between the two leaves
    an unindexed file, never an index row pointing at nothing.
    """

    store = CadexProjectScriptStore(project_root)
    state = store.read_state()
    revision = str(state.get("accepted_revision") or "")
    if not revision:
        raise ValueError(
            "This project has no accepted revision yet, so there is nothing "
            "for a blueprint to document. Build the script first."
        )

    raw_source = str(source_path or "").strip()
    if not raw_source:
        raise ValueError("source_path must name a readable PNG file.")
    try:
        source = Path(raw_source).expanduser().resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"Could not read {raw_source!r}: {exc}") from exc
    if not source.is_file():
        raise ValueError(f"{raw_source!r} is not a regular file.")

    with source.open("rb") as handle:
        magic = handle.read(len(_PNG_MAGIC))
    if magic != _PNG_MAGIC:
        raise ValueError(
            f"{source.name!r} is not a PNG (bad magic bytes); the blueprint "
            "store holds rendered PNG sheets only."
        )
    size = source.stat().st_size
    if size > MAX_BLUEPRINT_BYTES:
        raise ValueError(
            f"{source.name!r} is {size} bytes; the blueprint store caps a "
            f"sheet at {MAX_BLUEPRINT_BYTES}."
        )

    name = normalize_name(name)
    label = str(label or "").strip() or name
    if len(label) > MAX_LABEL_CHARS:
        raise ValueError(
            f"label is {len(label)} characters; the cap is {MAX_LABEL_CHARS}."
        )
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise ValueError("meta must be a JSON object.")
    try:
        meta_encoded = json.dumps(meta, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"meta is not JSON-encodable: {exc}") from exc
    if len(meta_encoded.encode("utf-8")) > MAX_META_BYTES:
        raise ValueError(
            f"meta encodes to {len(meta_encoded)} bytes; the cap is "
            f"{MAX_META_BYTES}."
        )

    entries = read_blueprints(project_root)
    ordinal = int(entries[-1].get("ordinal") or 0) + 1 if entries else 1
    version = 1 + max(
        (int(entry.get("version") or 1) for entry in entries
         if name and _named(entry) == name.casefold()),
        default=0,
    )
    slug = name_slug(name)
    filename = "{:04d}-{:s}.png".format(ordinal, slug or revision[:12])

    directory = _blueprint_dir(project_root)
    directory.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    # Dot-prefixed and .tmp-suffixed, the store's convention: no reader ever
    # sees a half-copied sheet under its final name.
    temporary = directory / f".{filename}.{uuid.uuid4().hex}.tmp"
    try:
        shutil.copyfile(source, temporary)
        temporary.replace(directory / filename)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass

    entry = {
        "ordinal": ordinal,
        "name": name,
        "version": version,
        "revision": revision,
        "digest": str(state.get("accepted_digest") or ""),
        "file": filename,
        "bytes": size,
        "sha256": digest.hexdigest(),
        "created_at": now_iso(),
        "label": label,
        "outputs": sorted(
            str(item.get("name"))
            for item in (state.get("accepted_contract") or [])
            if isinstance(item, dict) and item.get("name")
        ),
        "meta": json.loads(meta_encoded),
    }
    entries.append(entry)

    # The bound keeps the directory readable; a *name* outranks it. A named
    # sheet is a thing the user comes back to and revises, so its newest
    # version survives however many unnamed sheets were rendered since —
    # otherwise "revise the drawing I made yesterday" fails on a busy day.
    keep = set(range(max(0, len(entries) - BLUEPRINT_LIMIT), len(entries)))
    newest_named: dict[str, int] = {}
    for index, item in enumerate(entries):
        if _named(item):
            newest_named[_named(item)] = index
    keep |= set(newest_named.values())
    for index, stale in enumerate(entries):
        if index in keep:
            continue
        try:
            (directory / str(stale.get("file") or "")).unlink()
        except OSError:
            pass
    entries = [item for index, item in enumerate(entries) if index in keep]
    atomic_write_json(
        directory / BLUEPRINT_INDEX_NAME,
        {"schema": BLUEPRINT_SCHEMA, "entries": entries},
    )
    return entry
