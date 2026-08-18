# SPDX-License-Identifier: LGPL-2.1-or-later

"""The ``.cxpart`` container: one project's accepted solid, in another project.

A linked part is how a part built in project A reaches project B (ADR-138).
Not a Python import and not a live link: **one content-addressed file** in
B's ``assets/`` directory, travelling the path an imported STL already
travels, but carrying an exact OCCT solid instead of triangles plus the
script that made it.

Building one is pure file reading. The accepted solid is already a file on
disk — ``accepted_attempt`` in A's ``script.json`` names a pinned,
never-garbage-collected staging directory holding ``request.json`` (the
exact source that ran) and ``outputs/output-NNN.brep`` — so
:func:`build_linked_part` needs no FreeCAD, no worker, no OCCT call, and
project A does not have to be open.

The container mirrors ``.cxpolicy`` (ADR-084 §5), for that container's
reasons exactly::

    CXPART1\\n | <u64 LE header length> | <canonical JSON header> | <BREP bytes>

A length-prefixed header and a raw byte range are readable inside the
``--safe-mode`` sandbox by fifteen lines that parse no archive format, which
is what a file the engine reads on a script's say-so has to be.

This module is FreeCAD-free and kernel-neutral. It is in the engine's import
closure — ``cadexd``'s ``link_part`` op builds a container with it — *and*
staged by filename into the project worker bundle, where
``part.import_part`` reads one back. Both halves are pure Python, which is
what makes being in two places free (the same standing ``CadexNets`` and
``CadexBoards`` have).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

#: The schema the container declares, and the version a reader checks first.
LINKED_PART_SCHEMA = "cadex-linked-part-v1"

#: The container's first bytes. A magic line rather than a suffix check,
#: because the store accepts the suffix and this is what says the bytes are
#: what the name claimed.
LINKED_PART_MAGIC = b"CXPART1\n"

#: The container's own byte cap, and it is half of something rather than a
#: round number: the project store's whole asset budget is 128 MB
#: (``_MAX_ASSET_BYTES``), so a 64 MiB ceiling on one linked part is the
#: statement that no single part may fill a project. For scale, the BREP of
#: the sensor module this feature was built for is 40 KB — four orders of
#: magnitude under the cap — and a solid approaching it is a tessellated
#: import somebody meant to keep as a mesh.
MAXIMUM_CXPART_BYTES = 64 * 1024 * 1024

#: An 8-byte little-endian length is what the container writes, so this is
#: the largest header that can be declared before the bytes are trusted.
_MAXIMUM_HEADER_BYTES = 4 * 1024 * 1024


class LinkedPartError(ValueError):
    """A container could not be built or read; the message names the cause.

    ``candidates`` carries the source project's declared output names when
    the refusal is "that is not one of them", so the caller can offer the
    list instead of making the user guess it.
    """

    def __init__(self, message: str, *, candidates: Any = ()) -> None:
        self.candidates = [str(item) for item in candidates]
        super().__init__(str(message))


def _canonical_header(header: Mapping[str, Any]) -> bytes:
    """One header as the only bytes it can be.

    Sorted keys, no whitespace, ASCII and no NaN — the exact form
    ``_atomic_json`` writes and ``encode_policy`` encodes — so two engines
    linking the same accepted revision produce the same file, and the
    consuming project's digest is about the part rather than about when it
    was pulled.
    """

    return json.dumps(
        dict(header),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")


def encode_linked_part(header: Mapping[str, Any], brep: bytes) -> bytes:
    """One header and one BREP byte range, as the bytes that are the part."""

    payload = _canonical_header(header)
    return b"".join(
        (LINKED_PART_MAGIC, len(payload).to_bytes(8, "little"), payload, bytes(brep))
    )


def decode_linked_part(
    blob: bytes, *, context: str = "this linked part"
) -> tuple[dict[str, Any], bytes]:
    """The inverse of :func:`encode_linked_part`, refusing everything malformed.

    Every length is checked against the bytes that are actually there before
    it is used: this is the one function here that reads a file a script
    named rather than a value the engine computed. The BREP's own SHA-256 is
    verified against the header, which is the same authentication
    ``configure_part_references`` performs on a host-staged snapshot — a
    linked part crossed a process boundary too, and further.
    """

    data = bytes(blob)
    if len(data) > MAXIMUM_CXPART_BYTES:
        raise LinkedPartError(
            f"{context} is {len(data)} bytes; the limit for one linked part "
            f"is {MAXIMUM_CXPART_BYTES} bytes."
        )
    if not data.startswith(LINKED_PART_MAGIC):
        raise LinkedPartError(
            f"{context} does not begin with the {LINKED_PART_SCHEMA} magic "
            "line. A .cxpart file is what the link_part op writes; an STL, a "
            "raw BREP export or a renamed file of any other kind is not one."
        )
    offset = len(LINKED_PART_MAGIC)
    if len(data) < offset + 8:
        raise LinkedPartError(f"{context} is truncated: it carries no header length.")
    header_bytes = int.from_bytes(data[offset : offset + 8], "little")
    offset += 8
    if header_bytes > _MAXIMUM_HEADER_BYTES or len(data) < offset + header_bytes:
        raise LinkedPartError(
            f"{context} declares a {header_bytes}-byte header that is not there."
        )
    try:
        header = json.loads(data[offset : offset + header_bytes].decode("ascii"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise LinkedPartError(f"{context} has an unreadable header: {exc}.") from exc
    if not isinstance(header, dict):
        raise LinkedPartError(f"{context} header must be one JSON object.")
    if str(header.get("schema") or "") != LINKED_PART_SCHEMA:
        raise LinkedPartError(
            f"{context} declares schema {header.get('schema')!r}; this engine "
            f"reads {LINKED_PART_SCHEMA}."
        )
    brep = data[offset + header_bytes :]
    if not brep:
        raise LinkedPartError(f"{context} carries a header and no BREP bytes.")
    expected = str(header.get("shape_sha256") or "")
    actual = hashlib.sha256(brep).hexdigest()
    if expected != actual:
        raise LinkedPartError(
            f"{context} does not match its own header: the BREP hashes to "
            f"{actual}, the header records {expected}. The file was modified "
            "or truncated after it was written; link it again."
        )
    return dict(header), brep


def read_linked_part(path: str | Path) -> tuple[dict[str, Any], bytes]:
    """One stored ``.cxpart`` file as ``(header, brep_bytes)``, authenticated."""

    file_path = Path(str(path))
    try:
        size = file_path.stat().st_size
    except OSError as exc:
        raise LinkedPartError(f"Could not read {file_path.name!r}: {exc}.") from exc
    if size > MAXIMUM_CXPART_BYTES:
        raise LinkedPartError(
            f"{file_path.name!r} is {size} bytes; the limit for one linked "
            f"part is {MAXIMUM_CXPART_BYTES} bytes."
        )
    try:
        blob = file_path.read_bytes()
    except OSError as exc:
        raise LinkedPartError(f"Could not read {file_path.name!r}: {exc}.") from exc
    return decode_linked_part(blob, context=f"{file_path.name!r}")


def _accepted_state(root: Path) -> dict[str, Any]:
    from CadexScriptStore import CadexProjectScriptStore

    try:
        return CadexProjectScriptStore(root).read_state()
    except RuntimeError as exc:
        raise LinkedPartError(f"'{root}' has an unreadable project store: {exc}") from exc


def source_outputs(source_root: str | Path) -> list[dict[str, Any]]:
    """The source project's accepted contract, for offering a choice of output.

    The shell's Link Part flow asks the engine what A declares rather than
    reading A's ``script.json`` itself: the engine is the sole reader of a
    project store (docs/ARCHITECTURE.md), and that stays true of a store the
    session does not have open.
    """

    root = Path(str(source_root)).expanduser()
    state = _accepted_state(root)
    return [
        {
            "name": str(item.get("name") or ""),
            "type": str(item.get("type") or ""),
            "domain": str(item.get("domain") or ""),
        }
        for item in list(state.get("accepted_contract") or [])
        if isinstance(item, Mapping)
    ]


def build_linked_part(source_root: str | Path, output: str) -> bytes:
    """Read project A's accepted solid and return the ``.cxpart`` bytes.

    Pure file reading, and that is the whole reason this feature is cheap:
    the accepted attempt directory is pinned (``prune_artifacts`` resolves
    ``accepted_attempt`` and skips it explicitly), so the exact BREP that was
    accepted, and the exact source that produced it, are both sitting on disk
    under A's root. Nothing here imports FreeCAD, opens a document, or runs a
    worker, and project A may be closed — or open in another session — while
    it happens.
    """

    from CadexPinResolution import (
        accepted_attempt_dir,
        accepted_output_item,
        load_worker_report,
    )

    root = Path(str(source_root)).expanduser()
    if not root.is_dir():
        raise LinkedPartError(f"'{root}' is not a project directory.")
    clean_output = str(output or "").strip()
    state = _accepted_state(root)
    if not str(state.get("accepted_revision") or ""):
        raise LinkedPartError(
            f"'{root}' has no accepted revision; open it and accept one first."
        )
    contract = [
        dict(item)
        for item in list(state.get("accepted_contract") or [])
        if isinstance(item, Mapping)
    ]
    names = [str(item.get("name") or "") for item in contract]
    declared = next(
        (item for item in contract if str(item.get("name") or "") == clean_output),
        None,
    )
    if declared is None:
        raise LinkedPartError(
            f"'{clean_output}' is not an output of '{root}'; it declares: "
            f"{', '.join(names) or '(nothing)'}.",
            candidates=names,
        )
    try:
        staging = accepted_attempt_dir(root, state)
        report = load_worker_report(staging)
    except ValueError as exc:
        raise LinkedPartError(
            f"'{root}' has no locatable accepted attempt (pre-5.2 acceptances "
            f"must be re-accepted once): {exc}"
        ) from exc
    try:
        record = accepted_output_item(report, clean_output)
    except KeyError:
        raise LinkedPartError(
            f"'{root}' accepted no artifact for output '{clean_output}'; "
            "re-accept the project once."
        ) from None
    if str(record.get("artifact_kind") or "") != "brep":
        raise LinkedPartError(
            f"'{clean_output}' is a {str(declared.get('type') or 'non-solid')} "
            "output, not a solid; only BREP outputs can be linked.",
            candidates=names,
        )
    facts = record.get("facts") if isinstance(record.get("facts"), Mapping) else {}
    shape_type = str(dict(facts).get("shape_type") or "")
    if shape_type and shape_type != "Solid":
        raise LinkedPartError(
            f"'{clean_output}' is a {shape_type} output, not a solid; only "
            "solid BREP outputs can be linked.",
            candidates=names,
        )
    artifact = (staging / str(record.get("artifact_path") or "")).resolve()
    if staging.resolve() not in artifact.parents or not artifact.is_file():
        raise LinkedPartError(
            f"'{root}' has no accepted BREP file for output '{clean_output}' "
            f"at {record.get('artifact_path')!r}."
        )
    brep = artifact.read_bytes()

    from CadexScriptStore import CadexProjectScriptStore

    header = {
        "schema": LINKED_PART_SCHEMA,
        "source": {
            # A hint for refresh, never load-bearing (the standing
            # ``mesh_cadex_source_root`` has in ADR-046): the part is fully
            # usable with A deleted, and only refresh needs this path.
            "project_root": str(root.resolve()),
            "project_title": root.stem,
            "output": clean_output,
            "revision": str(state.get("accepted_revision") or ""),
            "digest": str(state.get("accepted_digest") or ""),
            "output_type": str(declared.get("type") or ""),
        },
        # Carried and not yet read. These are what a parameter override
        # (``part.import_part("s.cxpart", bore=6)``) needs, and what makes a
        # linked part *rebuildable* rather than baked. Recording them now
        # costs bytes and avoids a container version bump later; saying so
        # here is the difference between a decision and an oversight.
        "params": {
            str(key): value
            for key, value in dict(state.get("param_values") or {}).items()
        },
        "param_specs": [
            dict(item)
            for item in list(state.get("param_specs") or [])
            if isinstance(item, Mapping)
        ],
        "script": CadexProjectScriptStore(root).read_accepted_source(),
        "shape_sha256": hashlib.sha256(brep).hexdigest(),
        "brep_bytes": len(brep),
    }
    blob = encode_linked_part(header, brep)
    if len(blob) > MAXIMUM_CXPART_BYTES:
        raise LinkedPartError(
            f"'{clean_output}' is {len(blob) // (1024 * 1024)} MB; the limit "
            f"for one linked part is {MAXIMUM_CXPART_BYTES // (1024 * 1024)} MB."
        )
    return blob
