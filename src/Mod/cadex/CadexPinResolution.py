# SPDX-License-Identifier: LGPL-2.1-or-later

"""Headless pin resolution against the accepted revision's staged BREP.

Phase 5.2: resolve ``{output, selection}`` without a live document. The
accepted attempt directory (recorded in ``script.json`` as
``accepted_attempt``; pinned, never garbage-collected while referenced)
holds the worker report and the exported BREP artifacts; ``importBrep``
preserves the exact 1-based Face/Edge enumeration the worker serialized, so
selections resolve on the same topology that ``face_details`` /
``edge_details`` described.

Two selection forms:

- **Fingerprint query** — the shared ``CadexSubshapeQuery`` vocabulary
  (geometry_type, normal, radius, areas, near_point, expected_count,
  ``{"type": "all_edges"}``). Since Phase 10b the five index-taking part ops
  speak it too, so a pin and a script argument name geometry the same way.
- **Direct index** — ``{"element_type": "face"|"edge", "index": N}`` for
  the client picking path (triangle → face_ranges → index happens
  client-side against the 5.1 tessellation sidecar).

``CadexReferenceContracts.resolve_interface`` stays the document-bound
twin; this module never touches a live document.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from CadexTools import tool_failure

TOOL_NAME = "cadexd.resolve_pin"

_ELEMENT_TYPES = frozenset({"face", "edge"})


def _failure(code: str, message: str, **details: Any) -> dict[str, Any]:
    return tool_failure(TOOL_NAME, code, "precondition", message, **details)


def _accepted_attempt_dir(root: Path, state: Mapping[str, Any]) -> Path:
    attempt = state.get("accepted_attempt")
    if not isinstance(attempt, Mapping) or not str(attempt.get("staging") or ""):
        raise ValueError(
            "The project has no locatable accepted attempt; accept a revision "
            "first (pre-5.2 acceptances must be re-accepted once)."
        )
    staging = (root / str(attempt["staging"])).resolve()
    if root.resolve() not in staging.parents or not staging.is_dir():
        raise ValueError("The accepted attempt directory is missing.")
    return staging


def _load_worker_report(staging: Path) -> dict[str, Any]:
    result_path = staging / "result.json"
    if not result_path.is_file():
        raise ValueError(
            f"The accepted attempt has no worker report at {result_path}."
        )
    report = json.loads(result_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("ok") is not True:
        raise ValueError("The accepted attempt's worker report is not usable.")
    return report


def _accepted_output_item(
    report: Mapping[str, Any], output: str
) -> dict[str, Any]:
    for item in list(report.get("outputs") or []):
        if isinstance(item, Mapping) and str(item.get("name") or "") == output:
            return dict(item)
    raise KeyError(output)


def _import_staged_shape(staging: Path, item: Mapping[str, Any]) -> Any:
    import Part

    artifact = str(item.get("artifact_path") or "")
    path = (staging / artifact).resolve()
    if staging.resolve() not in path.parents or not path.is_file():
        raise ValueError(
            f"Accepted BREP artifact for output {item.get('name')!r} is missing."
        )
    shape = Part.Shape()
    shape.importBrep(str(path))
    if shape.isNull() or not shape.isValid():
        raise ValueError(
            f"Accepted BREP artifact for output {item.get('name')!r} is invalid."
        )
    return shape


def _resolve_direct_index(
    shape: Any, selection: Mapping[str, Any]
) -> tuple[list[str], list[dict[str, Any]]]:
    from CadexSubshapeQuery import subshape_geometry

    kind = str(selection.get("element_type") or "")
    if kind not in _ELEMENT_TYPES:
        raise ValueError("selection.element_type must be 'face' or 'edge'.")
    raw_index = selection.get("index")
    if isinstance(raw_index, bool) or not isinstance(raw_index, int):
        raise ValueError("selection.index must be a 1-based integer.")
    collection = list(shape.Faces if kind == "face" else shape.Edges)
    if not 1 <= raw_index <= len(collection):
        raise ValueError(
            f"selection.index {raw_index} is outside 1..{len(collection)} "
            f"for this shape's {kind}s."
        )
    detail = subshape_geometry(
        shape, kind, raw_index, collection[raw_index - 1]
    )
    return [str(detail["name"])], [detail]


def resolve_pin(
    project_root: str | Path,
    output: str,
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve one selection against the accepted revision's staged BREP."""

    from CadexScriptStore import CadexProjectScriptStore
    from CadexSubshapeQuery import SubshapeSelectionError, query_subelements

    root = Path(str(project_root))
    clean_output = str(output or "")
    if not clean_output:
        return _failure("PIN_OUTPUT_INVALID", "output must be a non-empty name.")
    if not isinstance(selection, Mapping) or not selection:
        return _failure(
            "PIN_SELECTION_INVALID",
            "selection must be a non-empty fingerprint query or "
            "{element_type, index}.",
            requested={"output": clean_output, "selection": selection},
        )

    store = CadexProjectScriptStore(root)
    state = store.read_state()
    accepted_revision = str(state.get("accepted_revision") or "")
    if not accepted_revision:
        return _failure(
            "NO_ACCEPTED_REVISION",
            "The project has no accepted revision to resolve pins against.",
        )
    contract = [
        dict(item)
        for item in list(state.get("accepted_contract") or [])
        if isinstance(item, Mapping)
    ]
    contract_item = next(
        (item for item in contract if str(item.get("name") or "") == clean_output),
        None,
    )
    if contract_item is None:
        return _failure(
            "UNKNOWN_PIN_OUTPUT",
            f"Output {clean_output!r} is not in the accepted contract.",
            requested={"output": clean_output},
            observed={"accepted_outputs": [str(item.get("name")) for item in contract]},
        )
    try:
        staging = _accepted_attempt_dir(root, state)
        report = _load_worker_report(staging)
    except ValueError as exc:
        return _failure("PIN_ARTIFACT_MISSING", str(exc))
    try:
        item = _accepted_output_item(report, clean_output)
    except KeyError:
        return _failure(
            "PIN_ARTIFACT_MISSING",
            f"The accepted worker report has no output {clean_output!r}.",
        )
    if str(item.get("artifact_kind") or "") != "brep":
        return _failure(
            "UNSUPPORTED_PIN_TARGET",
            f"Output {clean_output!r} is {item.get('artifact_kind') or 'not'} "
            "artifact-backed; pins resolve on BREP outputs only.",
            observed={"artifact_kind": item.get("artifact_kind")},
        )
    try:
        shape = _import_staged_shape(staging, item)
    except ValueError as exc:
        return _failure("PIN_ARTIFACT_MISSING", str(exc))

    direct_index = set(map(str, selection)) == {"element_type", "index"}
    try:
        if direct_index:
            subelements, details = _resolve_direct_index(shape, selection)
        else:
            subelements, details = query_subelements(shape, dict(selection))
    except SubshapeSelectionError as exc:
        return _failure(
            "PIN_SELECTION_UNRESOLVED",
            str(exc),
            requested={"output": clean_output, "selection": dict(selection)},
            observed=dict(exc.details),
        )
    except ValueError as exc:
        return _failure(
            "PIN_SELECTION_INVALID",
            str(exc),
            requested={"output": clean_output, "selection": dict(selection)},
        )
    return {
        "ok": True,
        "output": clean_output,
        "revision": accepted_revision,
        "subelements": [str(name) for name in subelements],
        "details": [dict(detail) for detail in details],
    }
