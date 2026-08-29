# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Document-side content digest over one program's published base outputs.

This is a DIAGNOSTIC digest: it hashes what actually lives in the FreeCAD
document (native TypeIds, exported live BREP bytes, persisted definitions,
live placements), so it will NOT equal the worker's staged-artifact digest
(``cadex-project-digest-v1``). Its one guarantee is determinism: publishing
the same accepted revision into the same document twice yields the same
value, so drift between two publishes of one revision is observable.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from typing import Any

import CadexScriptedDomains as contracts
from CadexScriptedDomainPublication import PROP_DEFINITION, PROP_OUTPUT_TYPE

SCHEMA = "cadex-document-digest-v1"
_PLACEMENT_DECIMALS = 9
_MATRIX_FIELDS = (
    "A11", "A12", "A13", "A14",
    "A21", "A22", "A23", "A24",
    "A31", "A32", "A33", "A34",
    "A41", "A42", "A43", "A44",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _shape_sha256(shape: Any) -> str:
    handle, path = tempfile.mkstemp(prefix="cadex-digest-", suffix=".brep")
    os.close(handle)
    try:
        shape.exportBrep(path)
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _placement_values(obj: Any) -> list[float] | None:
    placement = getattr(obj, "Placement", None)
    if placement is None or not hasattr(placement, "toMatrix"):
        return None
    matrix = placement.toMatrix()
    return [
        round(float(getattr(matrix, name)), _PLACEMENT_DECIMALS)
        for name in _MATRIX_FIELDS
    ]


def _digest_entries(doc: Any, program_id: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for obj in list(getattr(doc, "Objects", []) or []):
        properties = list(getattr(obj, "PropertiesList", []) or [])
        if contracts.PROP_PROGRAM_ID not in properties:
            continue
        if str(getattr(obj, contracts.PROP_PROGRAM_ID, "") or "") != str(program_id):
            continue
        output_name = str(getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or "")
        if not output_name or "." in output_name:
            continue
        entry: dict[str, Any] = {
            "output_name": output_name,
            "domain": str(getattr(obj, contracts.PROP_PROGRAM_DOMAIN, "") or ""),
            "output_type": str(getattr(obj, PROP_OUTPUT_TYPE, "") or ""),
            "object_type": str(getattr(obj, "TypeId", "") or ""),
        }
        # Only objects that OWN a Shape property contribute geometry bytes.
        # Link-style objects expose a computed Shape derived from their target
        # whose BREP serialization is not byte-stable across recreations; their
        # persisted definition already pins the linked identity.
        shape = getattr(obj, "Shape", None) if "Shape" in properties else None
        has_shape = (
            shape is not None
            and not getattr(shape, "isNull", lambda: True)()
        )
        if has_shape:
            entry["shape_sha256"] = _shape_sha256(shape)
        else:
            entry["payload_sha256"] = hashlib.sha256(
                str(getattr(obj, PROP_DEFINITION, "") or "").encode("utf-8")
            ).hexdigest()
        placement = _placement_values(obj)
        if placement is not None:
            entry["placement"] = placement
        entries.append(entry)
    entries.sort(key=lambda entry: entry["output_name"])
    return entries


def document_digest(doc: Any, program_id: str = "project") -> str:
    """SHA-256 over the live document objects owned by ``program_id``.

    One entry per tagged base output (``CadexXScriptOutputName`` without a
    ``.``): output name, domain, declared output type, native TypeId, then
    either the SHA-256 of the object's Shape exported to BREP (when the object
    owns a Shape property holding a non-null shape) or the SHA-256 of its
    persisted definition string, plus the placement matrix rounded to 1e-9
    when the object has one. Entries are sorted by output name and hashed
    under schema ``cadex-document-digest-v1``.
    """

    material = _canonical_json(
        {"schema": SCHEMA, "outputs": _digest_entries(doc, str(program_id))}
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
