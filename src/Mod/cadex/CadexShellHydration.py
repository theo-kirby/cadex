# SPDX-License-Identifier: LGPL-2.1-or-later

"""Shell-side hydration of accepted cadexd results (Phase 5.4).

After cadexd accepts a revision, the shell mirrors the accepted contract
into the live Qt document as flat display objects — ``Part::Feature`` via
``importBrep`` and ``Mesh::Feature`` via ``Mesh.read`` — inside ONE
transaction (one undo step), on the Qt document thread.

Objects are keyed by the existing xscript ownership tags
(``CadexScriptedDomains`` constants): find-or-create per accepted output,
revision tag updated on every pass. Garbage collection is
**contract-driven** — any tagged object whose output name left the
accepted contract is deleted together with its dependency closure — which
makes it robust across cadexd restarts and across the switchover from the
retired in-process publication path (stale native Bodies/links are swept
the same way).

Qt hydration uses BREP only: the Coin providers tessellate natively; the
5.1 tessellation buffers serve tests and the Phase 6 Blender shell.
"""

from __future__ import annotations

from typing import Any, Mapping

import CadexScriptedDomains as contracts
from CadexScriptedOwnership import delete_contained_objects

PROGRAM_ID = "project"

_TYPE_BY_KIND = {"brep": "Part::Feature", "mesh": "Mesh::Feature"}

_TAG_PROPERTIES = (
    contracts.PROP_PROGRAM_ID,
    contracts.PROP_PROGRAM_DOMAIN,
    contracts.PROP_PROGRAM_WORKBENCH,
    contracts.PROP_PROGRAM_REVISION,
    contracts.PROP_PROGRAM_OUTPUT,
)


def _properties(obj: Any) -> set[str]:
    return set(getattr(obj, "PropertiesList", []) or [])


def _tagged_objects(document: Any) -> list[Any]:
    return [
        obj
        for obj in list(getattr(document, "Objects", []) or [])
        if contracts.PROP_PROGRAM_ID in _properties(obj)
        and str(getattr(obj, contracts.PROP_PROGRAM_ID, "") or "") == PROGRAM_ID
    ]


def _output_name(obj: Any) -> str:
    return str(getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or "")


def _ensure_tags(obj: Any, *, domain: str, output: str, revision: str) -> None:
    for name in _TAG_PROPERTIES:
        if name not in _properties(obj):
            obj.addProperty(
                "App::PropertyString", name, "Cadex", "Cadex xscript ownership tag."
            )
    setattr(obj, contracts.PROP_PROGRAM_ID, PROGRAM_ID)
    setattr(obj, contracts.PROP_PROGRAM_DOMAIN, str(domain))
    setattr(obj, contracts.PROP_PROGRAM_WORKBENCH, "CadexProject")
    setattr(obj, contracts.PROP_PROGRAM_REVISION, str(revision))
    setattr(obj, contracts.PROP_PROGRAM_OUTPUT, str(output))


def _placement_from_matrix(values: Any) -> Any:
    import FreeCAD as App

    matrix = App.Matrix(*[float(value) for value in values])
    return App.Placement(matrix)


def _closure_of(roots: list[Any]) -> dict[str, Any]:
    """Names→objects reachable via Group membership and OutList dependencies."""

    closure: dict[str, Any] = {}
    stack = list(roots)
    while stack:
        obj = stack.pop()
        name = str(getattr(obj, "Name", "") or "")
        if not name or name in closure:
            continue
        closure[name] = obj
        stack.extend(list(getattr(obj, "Group", []) or []))
        stack.extend(list(getattr(obj, "OutList", []) or []))
    return closure


def _display_entry(display: Mapping[str, Any] | None, name: str) -> dict[str, Any]:
    if not isinstance(display, Mapping):
        return {}
    entry = display.get(name)
    return dict(entry) if isinstance(entry, Mapping) else {}


def hydrate_accepted_state(
    document: Any, payload: Mapping[str, Any]
) -> dict[str, Any]:
    """Mirror one accepted cadexd payload into the live document.

    ``payload`` is the accepted lifecycle response: ``outputs`` (the
    contract), ``revision``, and the per-output ``display`` block with
    absolute artifact paths. Runs in ONE transaction; raises on failure
    (the caller wraps that into ``SHELL_HYDRATION_FAILED`` — engine state
    is already accepted, the next success self-heals).
    """

    contract = [dict(item) for item in list(payload.get("outputs") or [])]
    display = payload.get("display")
    revision = str(payload.get("revision") or "")
    created: list[str] = []
    updated: list[str] = []

    transaction_open = False
    if hasattr(document, "openTransaction"):
        document.openTransaction("Cadex model update")
        transaction_open = True
    try:
        keep: list[Any] = []
        for item in contract:
            name = str(item.get("name") or "")
            domain = str(item.get("domain") or "")
            entry = _display_entry(display, name)
            kind = str(entry.get("artifact_kind") or "")
            type_id = _TYPE_BY_KIND.get(kind)
            if type_id is None:
                continue  # not displayable (solver diagnostics)
            existing = [
                obj for obj in _tagged_objects(document) if _output_name(obj) == name
            ]
            reusable = [
                obj
                for obj in existing
                if str(getattr(obj, "TypeId", "") or "") == type_id
            ]
            obj = reusable[0] if reusable else None
            if obj is None:
                obj = document.addObject(type_id, f"CadexModel_{name}")
                if obj is None:
                    raise RuntimeError(
                        f"FreeCAD did not create {type_id} for output {name!r}."
                    )
                created.append(str(obj.Name))
            else:
                updated.append(str(obj.Name))
            artifact_path = str(entry.get("artifact_path") or "")
            if kind == "brep":
                import Part

                shape = Part.Shape()
                shape.importBrep(artifact_path)
                if shape.isNull() or not shape.isValid():
                    raise RuntimeError(
                        f"Accepted BREP for output {name!r} did not import."
                    )
                obj.Shape = shape
                placement = entry.get("placement")
                if placement is not None:
                    obj.Placement = _placement_from_matrix(placement)
            else:
                import Mesh

                mesh = Mesh.Mesh()
                mesh.read(Filename=artifact_path)
                obj.Mesh = mesh
            _ensure_tags(obj, domain=domain, output=name, revision=revision)
            obj.Label = name
            keep.append(obj)

        # Contract-driven GC: every tagged object not kept this pass —
        # outputs that left the contract, duplicates, and any stale
        # publication-era native objects — goes, with its closure, unless
        # the closure member is still reachable from a kept object.
        keep_names = {str(obj.Name) for obj in keep}
        stale_roots = [
            obj
            for obj in _tagged_objects(document)
            if str(getattr(obj, "Name", "") or "") not in keep_names
        ]
        surviving = set(_closure_of(keep))
        stale = [
            obj
            for name, obj in _closure_of(stale_roots).items()
            if name not in surviving
        ]
        removed = delete_contained_objects(document, stale) if stale else []

        if hasattr(document, "recompute"):
            document.recompute()
        if transaction_open:
            document.commitTransaction()
            transaction_open = False
    finally:
        if transaction_open and hasattr(document, "abortTransaction"):
            try:
                document.abortTransaction()
            except Exception:
                pass
    return {
        "created": created,
        "updated": updated,
        "removed": removed,
        "revision": revision,
    }
