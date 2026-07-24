# SPDX-License-Identifier: LGPL-2.1-or-later

"""Asynchronous lifecycle for workbench-qualified XScript v2 programs.

This module deliberately separates artifact/process work from live-document
publication.  The session captures bounded state on the document thread,
performs all source, persistence, worker, geometry, mesh, and point validation
off-thread, then calls :func:`publish_candidate` once with detached values.
"""

from __future__ import annotations

from array import array
import ast
from dataclasses import dataclass
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence
import uuid

from CadexTools import tool_failure
import CadexScriptedDomains as contracts
from cadex_domain_api import create_domain_api

WORKER_SCHEMA = "cadex-xscript-domain-worker-v2"
_PROGRAM_ID = re.compile(r"^[0-9a-f]{32}$")
_PROGRAM_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9 ._-]{0,119}$")
_ASYNC_PUBLICATION_KEY = "_cadex_domain_publication"
_STRUCTURED_DEFINITION_LIMIT = 1_000_000
_MAX_REFERENCE_SHAPES = 128
_MAX_REFERENCE_BREP_BYTES = 256 * 1024 * 1024
_MAX_REFERENCE_FACT_SUBELEMENTS = 32
_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_SKETCHER_GRAPH_ID = re.compile(r"^[gc][1-9][0-9]*$")
_SKETCHER_MAX_UNDERCONSTRAINT_SUGGESTIONS = 128
_SKETCHER_MAX_EQUALITY_DIAGNOSTIC_GEOMETRY = 64
_SKETCHER_MAX_PROFILE_OPEN_VERTICES = 128
_SKETCHER_MAX_PROFILE_ENDPOINT_MATCHES = 8
_SKETCHER_SUGGESTION_POSITION_TOLERANCE_MM = 1.0e-6
_SKETCHER_SUGGESTION_ANGLE_TOLERANCE_DEGREES = 0.5
_SKETCHER_SUGGESTION_EQUALITY_TOLERANCE_MM = 1.0e-6
_SKETCHER_PROFILE_ENDPOINT_MATCH_TOLERANCE_MM = 1.0e-6
_ASSEMBLY_SIMULATION_TRACE_SCHEMA = "cadex-assembly-simulation-trace-v1"
_MAX_ASSEMBLY_SIMULATION_TRACE_BYTES = 64 * 1024 * 1024
_ASSEMBLY_EXPLODED_VIEW_SCHEMA = "cadex-assembly-exploded-view-v1"
_MAX_ASSEMBLY_HIERARCHY_JSON_BYTES = 8 * 1024 * 1024

# Worker attempts are deliberately self-contained.  Keep this manifest exact:
# staging an unrelated domain implementation would weaken the same-domain
# boundary even though the source sandbox cannot import arbitrary modules.
_DOMAIN_WORKER_BUNDLES: dict[str, tuple[str, ...]] = {
    "partdesign": (
        "cadex_partdesign_api.py",
        "cadex_partdesign_worker.py",
        "cadex_sketcher_api.py",
        "cadex_sketcher_worker.py",
        "cadex_part_worker.py",
    ),
    "part": (
        "cadex_part_api.py",
        "cadex_part_worker.py",
    ),
    "assembly": (
        "cadex_assembly_api.py",
        "cadex_assembly_worker.py",
        "cadex_part_worker.py",
    ),
    "sketcher": (
        "cadex_sketcher_api.py",
        "cadex_sketcher_worker.py",
        "cadex_part_worker.py",
    ),
    # The project domain stages every capability domain plus the shared
    # domain-worker helpers; its entry module replaces cadex_domain_worker as
    # the staged worker.py (see _stage_worker_bundle).
    "project": (
        "cadex_domain_worker.py",
        "cadex_project_api.py",
        "cadex_sketcher_api.py",
        "cadex_sketcher_worker.py",
        "cadex_part_api.py",
        "cadex_part_worker.py",
        "cadex_partdesign_api.py",
        "cadex_partdesign_worker.py",
        "cadex_assembly_api.py",
        "cadex_assembly_worker.py",
    ),
}
_SKETCHER_GEOMETRY_OPERATIONS = frozenset(
    {
        "point",
        "line",
        "arc",
        "circle",
        "ellipse",
        "elliptic_arc",
        "hyperbolic_arc",
        "parabolic_arc",
        "bspline",
        "external_geometry",
    }
)
_SKETCHER_CONSTRAINT_KINDS = frozenset(
    {
        "coincident",
        "horizontal",
        "vertical",
        "parallel",
        "perpendicular",
        "tangent",
        "distance",
        "distance_x",
        "distance_y",
        "angle",
        "angle_via_point",
        "radius",
        "diameter",
        "equal",
        "point_on_object",
        "symmetric",
        "block",
        "weight",
        "snells_law",
        "internal_alignment",
        "group",
        "text",
    }
)


class DomainRuntimeFailure(RuntimeError):
    def __init__(self, payload: Mapping[str, Any]):
        self.payload = dict(payload)
        super().__init__(str(self.payload.get("error") or "XScript domain failure."))


def _failure(
    tool_name: str,
    code: str,
    stage: str,
    message: str,
    **details: Any,
) -> dict[str, Any]:
    return tool_failure(
        tool_name,
        code,
        stage,
        message,
        requested=dict(details.pop("requested", {}) or {}),
        observed=dict(details.pop("observed", {}) or {}),
        **details,
    )


def _raise(
    tool_name: str,
    code: str,
    stage: str,
    message: str,
    **details: Any,
) -> None:
    raise DomainRuntimeFailure(_failure(tool_name, code, stage, message, **details))


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(
                dict(payload),
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Could not read {label} at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} at {path} must contain one JSON object.")
    return value


def _stage_worker_bundle(
    module_root: Path, staging: Path, domain: str
) -> tuple[str, ...]:
    """Copy only the isolated runner and the active domain's declared modules."""

    clean_domain = str(domain or "").strip().lower()
    domain_files = _DOMAIN_WORKER_BUNDLES.get(clean_domain)
    if domain_files is None:
        raise ValueError(
            f"XScript domain {clean_domain!r} has no isolated worker bundle."
        )
    filenames = (
        "cadex_domain_api.py",
        *domain_files,
    )
    if len(filenames) != len(set(filenames)):
        raise RuntimeError(
            f"XScript domain {clean_domain!r} has duplicate worker dependencies."
        )
    entry_module = (
        "cadex_project_worker.py" if clean_domain == "project"
        else "cadex_domain_worker.py"
    )
    copied = ("worker.py", *filenames)
    sources = (entry_module, *filenames)
    for source_name, target_name in zip(sources, copied, strict=True):
        source = module_root / source_name
        if source.parent != module_root or not source.is_file():
            raise RuntimeError(
                f"Required XScript worker dependency {source_name!r} is missing."
            )
        shutil.copyfile(source, staging / target_name)
    return copied


def _engine_pack(
    engine: str, domain: str
) -> contracts.XScriptWorkbenchPack | None:
    """Resolve a domain pack for a scripted engine ("xscript" or "xscript")."""

    if engine == "xscript":
        registry = contracts.XSCRIPT_WORKBENCH_PACKS
    elif engine == "xscript":
        try:
            import CadexScriptedDomains as xdomains
        except Exception:
            return None
        registry = xdomains.XSCRIPT_WORKBENCH_PACKS
    else:
        return None
    return next(
        (candidate for candidate in registry.values() if candidate.domain == domain),
        None,
    )


def parse_domain_tool(
    tool_name: str,
) -> tuple[contracts.XScriptWorkbenchPack, str] | None:
    name = str(tool_name or "")
    parts = name.split(".")
    if len(parts) != 3:
        return None
    engine, domain, operation = parts
    if operation not in contracts.LIFECYCLE_OPERATIONS:
        return None
    pack = _engine_pack(engine, domain)
    return (pack, operation) if pack is not None else None


def _program_directory(project_root: str | Path, domain: str, program_id: str) -> Path:
    root = Path(project_root) / "xscript"
    canonical = root / domain / program_id
    if canonical.exists() or domain != "partdesign":
        return canonical
    v1_directory = root / program_id
    return v1_directory if v1_directory.is_dir() else canonical


def _manifest_path(project_root: str | Path, domain: str, program_id: str) -> Path:
    return _program_directory(project_root, domain, program_id) / "program.json"


def _program_directories(project_root: str | Path, domain: str) -> list[Path]:
    root = Path(project_root) / "xscript"
    canonical_root = root / domain
    result = (
        [
            path
            for path in canonical_root.iterdir()
            if path.is_dir() and _PROGRAM_ID.fullmatch(path.name)
        ]
        if canonical_root.is_dir()
        else []
    )
    if domain == "partdesign" and root.is_dir():
        result.extend(
            path
            for path in root.iterdir()
            if path.is_dir()
            and _PROGRAM_ID.fullmatch(path.name)
            and path not in result
        )
    return result


def _load_manifest(
    project_root: str | Path,
    pack: contracts.XScriptWorkbenchPack,
    program_id: str,
) -> dict[str, Any]:
    path = _manifest_path(project_root, pack.domain, program_id)
    if not path.is_file() and pack.domain == "partdesign":
        v1_path = path.parent / "manifest.json"
        if v1_path.is_file():
            path = v1_path
    if not path.is_file():
        raise FileNotFoundError(
            f"No {pack.title} XScript program has id {program_id}."
        )
    manifest = contracts.migrate_program_manifest(
        _read_json(path, "XScript program manifest"),
        artifact_directory=path.parent,
    )
    if str(manifest.get("program_id") or "") != program_id:
        raise ValueError(f"Program manifest id does not match directory {program_id}.")
    if str(manifest.get("domain") or "") != pack.domain:
        raise ValueError(
            f"Program {program_id} belongs to domain {manifest.get('domain')!r}, "
            f"not {pack.domain!r}."
        )
    return manifest


def _assembly_live_output_state(obj: Any) -> dict[str, Any]:
    """Capture bounded accepted evidence used by model-facing inspect_program."""

    output_type = str(getattr(obj, "CadexXScriptOutputType", "") or "")
    property_names = {
        "joint": ("CadexAssemblyJointValidation",),
        "motion": ("CadexAssemblyMotionValidation",),
        "simulation": (
            "CadexAssemblySimulationValidation",
            "CadexSimulationTracePreview",
        ),
        "exploded_view": ("CadexAssemblyExplodedViewValidation",),
        "solver_diagnostics": ("CadexSolverDiagnostics",),
    }.get(output_type, ())
    result: dict[str, Any] = {"output_type": output_type} if output_type else {}
    accepted: dict[str, Any] = {}
    for property_name in property_names:
        raw = str(getattr(obj, property_name, "") or "")
        if not raw:
            continue
        encoded_bytes = len(raw.encode("utf-8", errors="replace"))
        key = (
            "trace_preview"
            if property_name == "CadexSimulationTracePreview"
            else "validation"
        )
        if encoded_bytes > 64 * 1024:
            accepted[key] = {
                "omitted": True,
                "json_bytes": encoded_bytes,
                "reason": "Accepted live evidence exceeds the 64 KiB inspection bound.",
            }
            continue
        try:
            accepted[key] = json.loads(raw)
        except (TypeError, ValueError) as exc:
            accepted[f"{key}_error"] = f"{type(exc).__name__}: {exc}"
    if accepted:
        result["accepted_state"] = accepted
    return result


def _live_programs(doc: Any, domain: str) -> list[dict[str, Any]]:
    programs: dict[str, dict[str, Any]] = {}
    for obj in list(getattr(doc, "Objects", []) or []):
        properties = set(getattr(obj, "PropertiesList", []) or [])
        if not {contracts.PROP_PROGRAM_ID, contracts.PROP_PROGRAM_DOMAIN} <= properties:
            continue
        if str(getattr(obj, contracts.PROP_PROGRAM_DOMAIN, "") or "") != domain:
            continue
        program_id = str(getattr(obj, contracts.PROP_PROGRAM_ID, "") or "")
        if not program_id:
            continue
        item = programs.setdefault(
            program_id,
            {"program_id": program_id, "revisions": set(), "outputs": []},
        )
        revision = str(getattr(obj, contracts.PROP_PROGRAM_REVISION, "") or "")
        if revision:
            item["revisions"].add(revision)
        output = {
            "name": str(getattr(obj, contracts.PROP_PROGRAM_OUTPUT, "") or ""),
            "object_name": str(getattr(obj, "Name", "") or ""),
            "label": str(getattr(obj, "Label", "") or ""),
            "type_id": str(getattr(obj, "TypeId", "") or ""),
            "derived_state": str(getattr(obj, "CadexDerivedState", "") or ""),
            "stale_reason": str(getattr(obj, "CadexStaleReason", "") or ""),
            "source_revision": str(getattr(obj, "CadexSourceRevision", "") or ""),
        }
        if domain == "assembly":
            output.update(_assembly_live_output_state(obj))
        item["outputs"].append(output)
    result: list[dict[str, Any]] = []
    for program_id in sorted(programs):
        item = programs[program_id]
        item["revisions"] = sorted(item["revisions"])
        item["outputs"] = sorted(item["outputs"], key=lambda output: output["name"])
        result.append(item)
    return result


def _document_objects(doc: Any) -> list[dict[str, str]]:
    return [
        {
            "name": str(getattr(obj, "Name", "") or ""),
            "label": str(getattr(obj, "Label", "") or ""),
            "type_id": str(getattr(obj, "TypeId", "") or ""),
        }
        for obj in list(getattr(doc, "Objects", []) or [])[:10_000]
    ]


def capture_operation_state(
    service: Any,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Capture document-affine state without artifact I/O or geometry work."""

    parsed = parse_domain_tool(tool_name)
    if parsed is None:
        _raise(tool_name, "UNKNOWN_DOMAIN_TOOL", "surface", "Unknown domain tool.")
    pack, operation = parsed
    doc = service._active_document()
    if operation != "describe_api" and doc is None:
        _raise(tool_name, "NO_DOCUMENT", "precondition", "No active FreeCAD document.")
    from CadexModelingSurface import resolve_service_surface

    resolution = resolve_service_surface(service, service.active_workbench_name())
    if (
        resolution.engine != pack.engine
        or resolution.workbench != pack.workbench
        or resolution.domain != pack.domain
        or not resolution.available
    ):
        _raise(
            tool_name,
            "DOMAIN_SURFACE_CHANGED",
            "surface",
            "The active workbench and modeling engine no longer authorize this domain.",
            observed=resolution.summary(),
        )
    scope = service.project_scope_snapshot()
    from CadexPreferences import load_settings

    settings = load_settings()
    timeout = float(getattr(settings, "scripted_timeout_seconds", 0.0) or 0.0)
    memory_mb = int(getattr(settings, "scripted_memory_limit_mb", 0) or 0)
    if timeout <= 0.0 or memory_mb <= 0:
        _raise(
            tool_name,
            "INVALID_SCRIPTED_BUDGET",
            "precondition",
            "XScript requires positive worker timeout and memory limits.",
            observed={"timeout_seconds": timeout, "memory_limit_mb": memory_mb},
        )
    try:
        import FreeCAD as App

        freecad_home = str(App.getHomePath())
    except Exception as exc:
        _raise(
            tool_name,
            "FREECAD_UNAVAILABLE",
            "precondition",
            f"FreeCAD is unavailable: {exc}",
        )
    live = _live_programs(doc, pack.domain) if doc is not None else []
    for item in live:
        if len(item["revisions"]) > 1:
            _raise(
                tool_name,
                "LIVE_PROGRAM_REVISION_SPLIT",
                "precondition",
                f"Live outputs for program {item['program_id']} have different revisions.",
                observed=item,
            )
    return {
        "tool_name": tool_name,
        "operation": operation,
        "arguments": dict(arguments),
        "pack": pack,
        "project_root": str(scope.get("root") or ""),
        "project_id": str(scope.get("project_id") or ""),
        "document_name": str(getattr(doc, "Name", "") or ""),
        "document_uid": str(getattr(doc, "Uid", "") or ""),
        "document_revision": (
            str(service.provider_document_revision()) if doc is not None else ""
        ),
        "document_objects": _document_objects(doc) if doc is not None else [],
        "live_programs": live,
        "surface": resolution.summary(),
        "freecad_home": freecad_home,
        "timeout_seconds": timeout,
        "memory_limit_bytes": memory_mb * 1024 * 1024,
    }


def _validate_stable_references(
    value: Any, captured: Mapping[str, Any], path: str
) -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_stable_references(item, captured, f"{path}[{index}]")
        return
    if not isinstance(value, dict):
        return
    if set(value) != {"document_uid", "object_name"}:
        for key, item in value.items():
            _validate_stable_references(item, captured, f"{path}.{key}")
        return
    document_uid = str(value.get("document_uid") or "")
    object_name = str(value.get("object_name") or "")
    if document_uid != str(captured.get("document_uid") or ""):
        raise ValueError(f"{path} refers to a different document uid.")
    names = {str(item.get("name") or "") for item in captured["document_objects"]}
    if object_name not in names:
        raise ValueError(f"{path} refers to missing object {object_name!r}.")


def _apply_replacements(source: str, replacements: Any) -> str:
    if not isinstance(replacements, list) or not replacements:
        raise ValueError("replacements must be a non-empty array.")
    result = source
    for index, replacement in enumerate(replacements):
        if not isinstance(replacement, dict) or set(replacement) != {"old", "new"}:
            raise ValueError(f"replacements[{index}] must contain exactly old and new.")
        old = str(replacement["old"])
        new = str(replacement["new"])
        count = result.count(old)
        if count != 1:
            raise ValueError(
                f"replacements[{index}].old must occur exactly once; found {count}."
            )
        result = result.replace(old, new, 1)
    return result


def _merge_patch(base: Mapping[str, Any], patch: Any) -> dict[str, Any]:
    if not isinstance(patch, dict) or not patch:
        raise ValueError("patch must be a non-empty object.")
    result = dict(base)
    for key, value in patch.items():
        if value is None:
            result.pop(str(key), None)
        else:
            result[str(key)] = value
    return result


#: UI-only slider metadata fields one input control may declare.
_CONTROL_TEXT_FIELDS = ("label", "unit", "description")
_CONTROL_NUMERIC_FIELDS = ("min", "max", "step")
_CONTROL_FIELDS = frozenset(_CONTROL_TEXT_FIELDS) | frozenset(_CONTROL_NUMERIC_FIELDS)


def _invalid_controls(tool_name: str, reason: str, **observed: Any) -> None:
    _raise(
        tool_name,
        "INVALID_PARAMETER_CONTROLS",
        "schema",
        f"input_controls is invalid: {reason}",
        observed=observed,
    )


def clean_parameter_controls(
    tool_name: str, value: Any, inputs: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the UI slider metadata map against the current inputs.

    Controls never affect geometry or the program revision; values are only
    checked for internal consistency (finite numbers, positive step, min < max).
    The current input value is deliberately NOT required to lie inside
    [min, max] — the panel widens displayed bounds instead.
    """

    if value is None:
        return {}
    if not isinstance(value, dict):
        _invalid_controls(tool_name, "input_controls must be an object.")
    controls = json.loads(
        json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False)
    )
    unknown = sorted(set(controls) - set(inputs))
    if unknown:
        _raise(
            tool_name,
            "UNKNOWN_CONTROL_PARAMETER",
            "schema",
            f"input_controls names inputs that do not exist: {unknown}.",
            observed={
                "unknown_inputs": unknown,
                "inputs": sorted(inputs),
            },
        )
    cleaned: dict[str, Any] = {}
    for name, control in controls.items():
        if not isinstance(control, dict):
            _invalid_controls(
                tool_name, f"control for {name!r} must be an object.", parameter=name
            )
        unknown_fields = sorted(set(control) - _CONTROL_FIELDS)
        if unknown_fields:
            _invalid_controls(
                tool_name,
                f"control for {name!r} has unknown fields {unknown_fields}; "
                f"allowed fields are {sorted(_CONTROL_FIELDS)}.",
                parameter=name,
                unknown_fields=unknown_fields,
            )
        entry: dict[str, Any] = {}
        for field in _CONTROL_TEXT_FIELDS:
            if field in control:
                if not isinstance(control[field], str):
                    _invalid_controls(
                        tool_name,
                        f"control field {name}.{field} must be a string.",
                        parameter=name,
                        field=field,
                    )
                entry[field] = control[field]
        for field in _CONTROL_NUMERIC_FIELDS:
            if field in control:
                number = control[field]
                if (
                    isinstance(number, bool)
                    or not isinstance(number, (int, float))
                    or not math.isfinite(number)
                ):
                    _invalid_controls(
                        tool_name,
                        f"control field {name}.{field} must be a finite number.",
                        parameter=name,
                        field=field,
                    )
                entry[field] = float(number)
        if "step" in entry and entry["step"] <= 0:
            _invalid_controls(
                tool_name,
                f"control field {name}.step must be greater than zero.",
                parameter=name,
                step=entry["step"],
            )
        if "min" in entry and "max" in entry and entry["min"] >= entry["max"]:
            _invalid_controls(
                tool_name,
                f"control for {name!r} requires min < max.",
                parameter=name,
                min=entry["min"],
                max=entry["max"],
            )
        cleaned[name] = entry
    return cleaned


def _merge_controls_patch(target: Any, patch: Any) -> Any:
    """Apply an RFC 7396 JSON merge patch (recursive; null deletes a key).

    Controls are one level deep, so this lets a patch tweak a single field
    (``{"radius": {"max": 20}}``) or drop one (``{"radius": {"unit": null}}``)
    without resending the whole control, and drop a whole control with a
    top-level ``{"radius": null}``.
    """
    if not isinstance(patch, dict):
        return patch
    result = dict(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        name = str(key)
        if value is None:
            result.pop(name, None)
        else:
            result[name] = _merge_controls_patch(result.get(name), value)
    return result


def prune_controls(controls: Any, inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Silently drop controls for inputs that no longer exist.

    This is the whole stale-metadata story: a source edit or set_inputs patch
    that removes or renames an input simply loses that input's slider metadata.
    """

    if not isinstance(controls, dict):
        return {}
    return {
        name: dict(control)
        for name, control in controls.items()
        if name in inputs and isinstance(control, dict)
    }


def _freecadcmd(freecad_home: str) -> Path:
    names = (
        ("FreeCADCmd.exe", "freecadcmd.exe")
        if sys.platform == "win32"
        else (
            "FreeCADCmd",
            "freecadcmd",
        )
    )
    for name in names:
        path = Path(freecad_home) / "bin" / name
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"No windowless FreeCADCmd executable exists under {freecad_home!r}."
    )


def _new_manifest(
    pack: contracts.XScriptWorkbenchPack,
    program_id: str,
    label: str,
) -> dict[str, Any]:
    return {
        "schema": pack.program_schema,
        "version": contracts.PROGRAM_VERSION,
        "program_id": program_id,
        "domain": pack.domain,
        "workbench": pack.workbench,
        "label": label,
        "source": "",
        "input_schema": {},
        "inputs": {},
        "input_controls": {},
        "expected_outputs": [],
        "working_revision": "",
        "accepted_revision": "",
        "accepted_contract": None,
        "live_outputs": {},
        "latest_candidate": None,
        "created_at": time.time(),
    }


def _input_references(value: Any) -> list[dict[str, str]]:
    """Return unique stable references in deterministic input traversal order."""

    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def walk(item: Any) -> None:
        if isinstance(item, list):
            for child in item:
                walk(child)
            return
        if not isinstance(item, dict):
            return
        if set(item) == {"document_uid", "object_name"}:
            reference = {
                "document_uid": str(item.get("document_uid") or ""),
                "object_name": str(item.get("object_name") or ""),
            }
            key = (reference["document_uid"], reference["object_name"])
            if key not in seen:
                seen.add(key)
                result.append(reference)
            return
        for child in item.values():
            walk(child)

    walk(value)
    if len(result) > _MAX_REFERENCE_SHAPES:
        raise ValueError(
            f"A program may reference at most {_MAX_REFERENCE_SHAPES} document objects."
        )
    return result


def abandon_prepared_candidate(prepared: Mapping[str, Any]) -> None:
    """Remove unpublished staging for a candidate that could not be finalized."""

    staging = Path(str(prepared.get("staging") or ""))
    if staging.name and staging.parent.name == ".staging" and staging.is_dir():
        shutil.rmtree(staging)


def _assembly_reference_contract(service: Any, obj: Any) -> dict[str, Any]:
    """Capture bounded identity/semantic metadata without traversing geometry."""

    import CadexReferenceContracts as reference_contracts
    import CadexScriptedPublication as scripted_publication

    properties = set(getattr(obj, "PropertiesList", []) or [])
    program_id = str(getattr(obj, contracts.PROP_PROGRAM_ID, "") or "")
    program_domain = str(getattr(obj, contracts.PROP_PROGRAM_DOMAIN, "") or "")
    published = reference_contracts.published_object(obj)
    source_kind = "shape"
    if bool(
        getattr(obj, "isDerivedFrom", lambda _type: False)("Assembly::AssemblyObject")
    ):
        source_kind = "assembly"
    elif str(getattr(obj, "TypeId", "") or "") == "PartDesign::Body":
        source_kind = "partdesign_body"
    elif bool(
        getattr(obj, "isDerivedFrom", lambda _type: False)("App::Part")
    ) and not bool(getattr(obj, "isDerivedFrom", lambda _type: False)("Part::Feature")):
        source_kind = "part"
    elif program_id:
        source_kind = f"xscript_{program_domain or 'output'}"
    elif published is not None:
        source_kind = "scripted_publication"
    transient_topology = bool(program_id or published is not None)
    semantic_only = published is not None
    interfaces: dict[str, Any] = {}
    source_revision = ""
    if published is not None:
        source_revision = str(
            getattr(published, scripted_publication.PROP_REVISION, "") or ""
        )
        try:
            root = scripted_publication.model_root_for(published)
            raw_interfaces = json.loads(
                str(getattr(root, scripted_publication.PROP_INTERFACES, "{}") or "{}")
            )
        except (scripted_publication.PublicationError, ValueError) as exc:
            raise RuntimeError(
                f"Scripted component {getattr(obj, 'Name', '')!r} has invalid "
                f"published-interface metadata: {exc}"
            ) from exc
        if not isinstance(raw_interfaces, dict):
            raise RuntimeError(
                f"Scripted component {getattr(obj, 'Name', '')!r} has a non-object "
                "published-interface table."
            )
        output_key = str(
            getattr(published, scripted_publication.PROP_OUTPUT_KEY, "") or ""
        )
        names = [
            str(name)
            for name, definition in raw_interfaces.items()
            if isinstance(definition, dict)
            and str(definition.get("output") or "") == output_key
        ]
        if len(names) > 64:
            raise RuntimeError(
                f"Scripted component {getattr(obj, 'Name', '')!r} exposes more than "
                "64 published interfaces."
            )
        for name in sorted(names):
            try:
                resolved = reference_contracts.resolve_interface(service, obj, name)
            except reference_contracts.ReferenceContractError as exc:
                raise RuntimeError(
                    f"Published interface {name!r} on component "
                    f"{getattr(obj, 'Name', '')!r} is invalid: {exc}"
                ) from exc
            interfaces[name] = {
                "model_id": str(resolved.get("model_id") or ""),
                "publication_name": str(resolved.get("publication_name") or ""),
                "output_key": str(resolved.get("output_key") or ""),
                "selection": dict(resolved.get("selection") or {}),
                "subelements": list(resolved.get("subelements") or []),
                "geometry": list(resolved.get("geometry") or []),
            }
    elif program_id:
        source_revision = str(getattr(obj, contracts.PROP_PROGRAM_REVISION, "") or "")
    return {
        "source_kind": source_kind,
        "source_program_id": program_id
        if contracts.PROP_PROGRAM_ID in properties
        else "",
        "source_program_domain": program_domain,
        "source_revision": source_revision,
        "transient_topology": transient_topology,
        "requires_semantic_interfaces": semantic_only,
        "published_interfaces": interfaces,
    }


def capture_reference_inputs(
    service: Any, prepared: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Copy validated shape or mesh inputs on the document thread.

    No BREP/BMS serialization, artifact I/O, geometry generation, or solver work
    is performed here. The detached kernels are serialized and validated by the
    background lifecycle after this callback returns.
    """

    requirements = list(prepared.get("reference_requirements") or [])
    if not requirements:
        return []
    domain = prepared["pack"].domain
    if domain not in {
        "partdesign",
        "part",
        "assembly",
        "sketcher",
    }:
        return []
    from CadexModelingSurface import resolve_service_surface

    live = resolve_service_surface(service, service.active_workbench_name())
    expected = prepared["surface"]
    if (live.workbench, live.engine, live.surface_id) != (
        str(expected.get("workbench") or ""),
        str(expected.get("engine") or ""),
        str(expected.get("surface_id") or ""),
    ):
        raise RuntimeError(
            "The workbench or modeling engine changed before reference capture."
        )
    doc = service._active_document()
    if doc is None or str(getattr(doc, "Name", "") or "") != prepared["document_name"]:
        raise RuntimeError("The active document changed before reference capture.")
    if str(getattr(doc, "Uid", "") or "") != prepared["document_uid"]:
        raise RuntimeError(
            "The active document identity changed before reference capture."
        )
    if str(service.provider_document_revision()) != prepared["document_revision"]:
        raise RuntimeError(
            "The document changed before reference capture; retry on live state."
        )
    snapshots: list[dict[str, Any]] = []
    for index, reference in enumerate(requirements):
        object_name = str(reference["object_name"])
        obj = doc.getObject(object_name)
        if obj is None:
            raise RuntimeError(
                f"{prepared['pack'].title} input reference {object_name!r} "
                "disappeared before capture."
            )
        if domain == "assembly" and str(
            getattr(obj, contracts.PROP_PROGRAM_ID, "") or ""
        ) == str(
            prepared.get("program_id") or ""
        ):
            raise RuntimeError(
                f"{prepared['pack'].title} input reference {object_name!r} is an "
                "output of the same program and would create a cyclic dependency."
            )
        if domain == "assembly":
            owner_resolver = getattr(service, "_partdesign_body_for_feature", None)
            owner = owner_resolver(obj) if callable(owner_resolver) else None
            if owner is not None and owner is not obj:
                raise RuntimeError(
                    f"Assembly input reference {object_name!r} is a feature inside "
                    f"Part Design Body {getattr(owner, 'Name', '')!r}; reference the "
                    "Body itself as the standalone component."
                )
            if str(getattr(obj, "TypeId", "") or "") == "App::Link":
                import CadexReferenceContracts as reference_contracts

                if reference_contracts.published_object(obj) is None:
                    target = getattr(obj, "LinkedObject", None)
                    raise RuntimeError(
                        f"Assembly input reference {object_name!r} is a generic App::Link. "
                        "Reference its exact LinkedObject instead so the program owns one "
                        f"unambiguous occurrence (suggested object: "
                        f"{getattr(target, 'Name', '<missing>')!r})."
                    )
        shape = getattr(obj, "Shape", None)
        if shape is None:
            raise RuntimeError(
                f"{prepared['pack'].title} input reference {object_name!r} "
                f"({getattr(obj, 'TypeId', '')}) "
                "does not expose a Shape."
            )
        if bool(shape.isNull()):
            raise RuntimeError(
                f"{prepared['pack'].title} input reference {object_name!r} has a null Shape."
            )
        try:
            detached = shape.copy()
        except Exception as exc:
            raise RuntimeError(
                f"Could not detach Shape from {prepared['pack'].title} input "
                f"reference {object_name!r}: {exc}"
            ) from exc
        assembly_contract = (
            _assembly_reference_contract(service, obj)
            if domain in {"assembly", "sketcher"}
            else {}
        )
        if domain == "assembly":
            from CadexAssemblyHierarchy import capture_bom_identity

            assembly_contract.update(capture_bom_identity(obj))
        assembly_hierarchy = None
        if domain == "assembly" and assembly_contract.get("source_kind") in {
            "assembly",
            "part",
        }:
            from CadexAssemblyHierarchy import capture_assembly_hierarchy

            assembly_hierarchy = capture_assembly_hierarchy(
                obj,
                detach_shapes=True,
                leaf_contract=lambda source: _assembly_reference_contract(
                    service, source
                ),
            )
        snapshots.append(
            {
                "document_uid": str(reference["document_uid"]),
                "object_name": object_name,
                "label": str(getattr(obj, "Label", "") or ""),
                "type_id": str(getattr(obj, "TypeId", "") or ""),
                "shape_type": str(getattr(shape, "ShapeType", "") or ""),
                "reference_artifact_kind": "brep",
                "detached_shape": detached,
                "snapshot_index": index,
                **(
                    {"assembly_hierarchy": assembly_hierarchy}
                    if assembly_hierarchy is not None
                    else {}
                ),
                **assembly_contract,
            }
        )
    if str(service.provider_document_revision()) != prepared["document_revision"]:
        raise RuntimeError(
            "The document changed during reference capture; retry on live state."
        )
    return snapshots


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finalize_assembly_hierarchy(
    hierarchy: Mapping[str, Any],
    *,
    staging: Path,
    reference_index: int,
) -> tuple[dict[str, Any], int]:
    """Serialize detached hierarchy shapes away from the document thread."""

    from CadexAssemblyHierarchy import ASSEMBLY_HIERARCHY_SCHEMA
    from cadex_part_worker import part_shape_facts

    if str(hierarchy.get("schema") or "") != ASSEMBLY_HIERARCHY_SCHEMA:
        raise ValueError("An Assembly source hierarchy has an unsupported schema.")
    raw_nodes = hierarchy.get("nodes")
    detached_shapes = hierarchy.get("_detached_shapes")
    if not isinstance(raw_nodes, list) or not isinstance(detached_shapes, dict):
        raise ValueError("An Assembly source hierarchy snapshot is malformed.")
    nodes = [dict(node) for node in raw_nodes]
    node_ids = [str(node.get("node_id") or "") for node in nodes]
    if not node_ids or len(node_ids) != len(set(node_ids)):
        raise ValueError("An Assembly source hierarchy has invalid node identities.")
    unexpected_shapes = set(str(key) for key in detached_shapes) - set(node_ids)
    if unexpected_shapes:
        raise ValueError(
            "An Assembly source hierarchy contains detached shapes for unknown nodes."
        )
    relative_root = Path("references") / f"reference-{reference_index:03d}-hierarchy"
    target_root = staging / relative_root
    if detached_shapes:
        target_root.mkdir(parents=True, exist_ok=False)
    total_bytes = 0
    for node in nodes:
        node_id = str(node["node_id"])
        shape = detached_shapes.get(node_id)
        expected = bool(node.pop("has_shape_artifact", False))
        if expected is not (shape is not None):
            raise ValueError(
                f"Assembly hierarchy node {node_id!r} changed its detached-shape state."
            )
        if shape is None:
            continue
        if bool(shape.isNull()) or not bool(shape.isValid()):
            raise ValueError(
                f"Assembly hierarchy node {node_id!r} has an invalid detached Shape."
            )
        relative = relative_root / f"{node_id}.brep"
        target = staging / relative
        shape.exportBrep(str(target))
        if not target.is_file() or target.stat().st_size <= 0:
            raise RuntimeError(
                f"Could not serialize Assembly hierarchy node {node_id!r} as BREP."
            )
        artifact_bytes = int(target.stat().st_size)
        total_bytes += artifact_bytes
        digest = _sha256_file(target)
        node["shape_artifact"] = {
            "artifact_path": str(relative),
            "artifact_sha256": digest,
            "artifact_bytes": artifact_bytes,
            "shape_type": str(getattr(shape, "ShapeType", "") or ""),
            "facts": part_shape_facts(
                shape,
                max_subelements=_MAX_REFERENCE_FACT_SUBELEMENTS,
            ),
        }
    descriptor = {
        key: value
        for key, value in hierarchy.items()
        if key not in {"nodes", "_detached_shapes"}
    }
    descriptor["nodes"] = nodes
    encoded = json.dumps(
        descriptor,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > _MAX_ASSEMBLY_HIERARCHY_JSON_BYTES:
        raise ValueError(
            "The authenticated Assembly source hierarchy exceeds the 8 MiB metadata limit. "
            "Remove unrelated scalar properties or split the source into smaller modules."
        )
    return descriptor, total_bytes


def finalize_candidate(
    prepared: dict[str, Any],
    snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    """Stage detached inputs, bind the revision, and persist the working candidate."""

    if prepared.get("finalized"):
        return prepared
    requirements = list(prepared.get("reference_requirements") or [])
    if len(snapshots) != len(requirements):
        abandon_prepared_candidate(prepared)
        raise ValueError(
            f"Reference capture returned {len(snapshots)} shapes; expected {len(requirements)}."
        )
    by_key = {
        (str(item.get("document_uid") or ""), str(item.get("object_name") or "")): item
        for item in snapshots
    }
    if len(by_key) != len(snapshots):
        abandon_prepared_candidate(prepared)
        raise ValueError("Reference capture returned duplicate object identities.")
    staging = Path(str(prepared["staging"]))
    worker_references: list[dict[str, Any]] = []
    resolved_references: list[dict[str, Any]] = []
    total_bytes = 0
    try:
        if requirements:
            reference_root = staging / "references"
            reference_root.mkdir(parents=True, exist_ok=False)
            for index, requirement in enumerate(requirements):
                key = (
                    str(requirement["document_uid"]),
                    str(requirement["object_name"]),
                )
                snapshot = by_key.get(key)
                if snapshot is None:
                    raise ValueError(
                        f"Reference capture omitted document object {key[1]!r}."
                    )
                hierarchy_descriptor = None
                if snapshot.get("assembly_hierarchy") is not None:
                    hierarchy_descriptor, hierarchy_bytes = (
                        _finalize_assembly_hierarchy(
                            snapshot["assembly_hierarchy"],
                            staging=staging,
                            reference_index=index,
                        )
                    )
                    total_bytes += hierarchy_bytes
                    if total_bytes > _MAX_REFERENCE_BREP_BYTES:
                        raise ValueError(
                            "Referenced Assembly hierarchy artifacts exceed the 256 MiB "
                            "detached-input limit."
                        )
                reference_contract = {
                    name: snapshot.get(name)
                    for name in (
                        "source_kind",
                        "source_program_id",
                        "source_program_domain",
                        "source_revision",
                        "transient_topology",
                        "requires_semantic_interfaces",
                        "published_interfaces",
                        "document_file_name",
                        "bom_properties",
                    )
                    if snapshot.get(name) not in (None, "", {}, [])
                }
                if hierarchy_descriptor is not None:
                    reference_contract["assembly_hierarchy"] = hierarchy_descriptor
                reference_contract_sha256 = ""
                if reference_contract:
                    reference_contract_sha256 = hashlib.sha256(
                        json.dumps(
                            reference_contract,
                            ensure_ascii=True,
                            sort_keys=True,
                            separators=(",", ":"),
                            allow_nan=False,
                        ).encode("utf-8")
                    ).hexdigest()
                artifact_kind = str(snapshot.get("reference_artifact_kind") or "brep")
                if artifact_kind == "brep":
                    from cadex_part_worker import part_shape_facts

                    shape = snapshot.get("detached_shape")
                    if shape is None or shape.isNull() or not shape.isValid():
                        raise ValueError(
                            f"Referenced object {key[1]!r} did not produce a valid "
                            "detached Shape."
                        )
                    relative = Path("references") / f"reference-{index:03d}.brep"
                    target = staging / relative
                    shape.exportBrep(str(target))
                    if not target.is_file() or target.stat().st_size <= 0:
                        raise RuntimeError(
                            f"Could not serialize referenced object {key[1]!r} as BREP."
                        )
                    total_bytes += target.stat().st_size
                    if total_bytes > _MAX_REFERENCE_BREP_BYTES:
                        raise ValueError(
                            "Referenced shapes exceed the 256 MiB detached-input limit."
                        )
                    digest = _sha256_file(target)
                    facts = part_shape_facts(
                        shape,
                        max_subelements=_MAX_REFERENCE_FACT_SUBELEMENTS,
                    )
                    metadata = {
                        "document_uid": key[0],
                        "object_name": key[1],
                        "label": str(snapshot.get("label") or ""),
                        "type_id": str(snapshot.get("type_id") or ""),
                        "shape_type": str(getattr(shape, "ShapeType", "") or ""),
                        "brep_sha256": digest,
                        "brep_bytes": int(target.stat().st_size),
                        "facts": facts,
                        **reference_contract,
                    }
                    worker_reference = {
                        "document_uid": key[0],
                        "object_name": key[1],
                        "shape_type": metadata["shape_type"],
                        "brep_sha256": digest,
                        "artifact_path": str(relative),
                        "label": metadata["label"],
                        "type_id": metadata["type_id"],
                        "facts": facts,
                        **reference_contract,
                    }
                else:
                    raise ValueError(
                        f"Reference capture returned unsupported artifact kind "
                        f"{artifact_kind!r}."
                    )
                if reference_contract_sha256:
                    metadata["reference_contract_sha256"] = reference_contract_sha256
                resolved_references.append(metadata)
                worker_references.append(worker_reference)
        contract_revision = str(prepared["contract_revision"])
        revision = (
            contracts.program_revision_with_references(
                contract_revision=contract_revision,
                references=resolved_references,
            )
            if resolved_references
            else contract_revision
        )
        if prepared["base_revision"] and revision == prepared["base_revision"]:
            _raise(
                str(prepared["tool_name"]),
                "PROGRAM_REVISION_UNCHANGED",
                "precondition",
                "The requested update and all referenced document shapes match the "
                "existing working revision.",
                observed={"current_revision": revision},
            )
        request = dict(prepared["worker_request"])
        request["revision"] = revision
        request["document_references"] = worker_references
        _atomic_json(staging / "request.json", request)
        candidate = {
            "attempt_id": str(prepared["attempt_id"]),
            "revision": revision,
            "base_revision": str(prepared["base_revision"]),
            "status": "prepared",
            "created_at": time.time(),
        }
        if resolved_references:
            candidate["resolved_references"] = resolved_references
        manifest = dict(prepared["manifest"])
        manifest.update(
            {
                "source": prepared["source"],
                "input_schema": prepared["input_schema"],
                "inputs": prepared["inputs"],
                "expected_outputs": prepared["expected_outputs"],
                "working_revision": revision,
                "latest_candidate": candidate,
                "updated_at": time.time(),
            }
        )
        _atomic_json(
            Path(str(prepared["program_directory"])) / "program.json", manifest
        )
        prepared.update(
            {
                "revision": revision,
                "resolved_references": resolved_references,
                "manifest": manifest,
                "worker_request": request,
                "finalized": True,
            }
        )
        return prepared
    except Exception:
        if not prepared.get("finalized"):
            abandon_prepared_candidate(prepared)
        raise


def prepare_candidate(captured: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and stage one candidate away from the document thread."""

    pack: contracts.XScriptWorkbenchPack = captured["pack"]
    operation = str(captured["operation"])
    tool_name = str(captured["tool_name"])
    arguments = dict(captured["arguments"])
    project_root = Path(str(captured["project_root"]))
    staging: Path | None = None
    try:
        if operation == "create_program":
            label = str(arguments.get("program_name") or "").strip()
            if not _PROGRAM_NAME.fullmatch(label):
                raise ValueError(
                    "program_name must start with a letter and contain at most 120 "
                    "letters, numbers, spaces, dots, underscores, or hyphens."
                )
            for directory in _program_directories(project_root, pack.domain):
                for path in (directory / "program.json", directory / "manifest.json"):
                    if not path.is_file():
                        continue
                    try:
                        other = contracts.migrate_program_manifest(
                            _read_json(path, "XScript program manifest"),
                            artifact_directory=directory,
                        )
                    except ValueError:
                        continue
                    if str(other.get("label") or "") == label:
                        raise ValueError(
                            f"A {pack.title} XScript program named {label!r} already exists."
                        )
            program_id = uuid.uuid4().hex
            manifest = _new_manifest(pack, program_id, label)
            source = str(arguments.get("source") or "")
            input_schema = arguments.get("input_schema")
            inputs = arguments.get("inputs")
            expected_outputs = arguments.get("expected_outputs")
            base_revision = ""
        else:
            program_id = str(arguments.get("program_id") or "").strip().lower()
            if not _PROGRAM_ID.fullmatch(program_id):
                raise ValueError(
                    "program_id must be a 32-character lowercase hexadecimal id."
                )
            manifest = _load_manifest(project_root, pack, program_id)
            base_revision = str(manifest.get("working_revision") or "")
            expected_revision = str(arguments.get("expected_revision") or "")
            if expected_revision != base_revision:
                _raise(
                    tool_name,
                    "STALE_PROGRAM_REVISION",
                    "precondition",
                    f"The {pack.title} XScript program changed after inspection.",
                    requested={"expected_revision": expected_revision},
                    observed={"current_revision": base_revision},
                    required_changes=[{"inspect_program": program_id}],
                )
            if manifest.get("migration_required") and operation != "reconfigure_program":
                action = f"{pack.engine}.{pack.domain}.reconfigure_program"
                _raise(
                    tool_name,
                    "PROGRAM_RECONFIGURATION_REQUIRED",
                    "precondition",
                    "This saved program uses a source contract that is not executable "
                    "by the active XScript domain runtime. Replace its complete v2 "
                    "source, input contract, inputs, and outputs before editing or "
                    "regenerating it.",
                    requested={"program_id": program_id},
                    observed={
                        "working_revision": base_revision,
                        "accepted_revision": str(
                            manifest.get("accepted_revision") or ""
                        ),
                        "accepted_live_state_preserved": bool(
                            manifest.get("accepted_revision")
                        ),
                        "imported_from_schema": str(
                            manifest.get("imported_from_schema") or ""
                        ),
                    },
                    required_changes=[
                        {
                            "tool": action,
                            "expected_revision": base_revision,
                            "replace": [
                                "source",
                                "input_schema",
                                "inputs",
                                "expected_outputs",
                            ],
                        }
                    ],
                )
            source = str(manifest.get("source") or "")
            input_schema = manifest.get("input_schema")
            inputs = manifest.get("inputs")
            expected_outputs = manifest.get("expected_outputs")
            if operation == "edit_source":
                source = _apply_replacements(source, arguments.get("replacements"))
            elif operation == "set_inputs":
                inputs = _merge_patch(dict(inputs or {}), arguments.get("patch"))
            elif operation == "reconfigure_program":
                source = str(arguments.get("source") or "")
                input_schema = arguments.get("input_schema")
                inputs = arguments.get("inputs")
                expected_outputs = arguments.get("expected_outputs")
                for key in (
                    "migration_required",
                    "migration_reason",
                    "migration_action",
                ):
                    manifest.pop(key, None)
            else:
                raise ValueError(
                    f"Operation {operation!r} does not prepare a candidate."
                )
        clean = contracts.validate_program_contract(
            pack,
            source=source,
            input_schema=input_schema,
            inputs=inputs,
            expected_outputs=expected_outputs,
        )
        _validate_stable_references(clean["inputs"], captured, "inputs")
        # Resolve the worker before changing persisted program state. A missing
        # FreeCADCmd is a precondition failure, not a durable working revision.
        freecadcmd_executable = _freecadcmd(str(captured["freecad_home"]))
        contract_revision = contracts.program_revision(domain=pack.domain, **clean)
        reference_requirements = _input_references(clean["inputs"])
        attempt_id = f"{int(time.time() * 1000):013d}-{uuid.uuid4().hex}"
        program_directory = _program_directory(project_root, pack.domain, program_id)
        staging = project_root / "xscript" / pack.domain / ".staging" / attempt_id
        staging.mkdir(parents=True, exist_ok=False)
        module_root = Path(__file__).resolve().parent
        _stage_worker_bundle(module_root, staging, pack.domain)
        request = {
            "schema": WORKER_SCHEMA,
            "program_schema": pack.program_schema,
            "engine": pack.engine,
            "api_global": pack.api_global,
            "program_id": program_id,
            "revision": "",
            "domain": pack.domain,
            "workbench": pack.workbench,
            "document_name": str(captured["document_name"]),
            "document_uid": str(captured["document_uid"]),
            "document_objects": list(captured["document_objects"]),
            "source": clean["source"],
            "inputs": clean["inputs"],
            "expected_outputs": clean["expected_outputs"],
            "api_exports": list(pack.api_exports),
            "output_types": list(pack.output_types),
            "max_operations": 200_000,
            "max_seconds": float(captured["timeout_seconds"]),
            "memory_limit_bytes": int(captured["memory_limit_bytes"]),
            "cpu_limit_seconds": max(1, int(float(captured["timeout_seconds"]))),
            "output_limit_bytes": 256 * 1024 * 1024,
        }
        prepared = {
            "tool_name": tool_name,
            "operation": operation,
            "pack": pack,
            "program_id": program_id,
            "program_name": str(manifest["label"]),
            "revision": "",
            "contract_revision": contract_revision,
            "base_revision": base_revision,
            "accepted_revision_before": str(manifest.get("accepted_revision") or ""),
            "accepted_contract_before": manifest.get("accepted_contract"),
            "live_outputs_before": dict(manifest.get("live_outputs") or {}),
            "source": clean["source"],
            "input_schema": clean["input_schema"],
            "inputs": clean["inputs"],
            "expected_outputs": clean["expected_outputs"],
            "manifest": manifest,
            "program_directory": str(program_directory),
            "staging": str(staging),
            "attempt_id": attempt_id,
            "freecadcmd_executable": str(freecadcmd_executable),
            "timeout_seconds": float(captured["timeout_seconds"]),
            "memory_limit_bytes": int(captured["memory_limit_bytes"]),
            "document_name": str(captured["document_name"]),
            "document_uid": str(captured["document_uid"]),
            "document_revision": str(captured["document_revision"]),
            "document_objects": list(captured["document_objects"]),
            "surface": dict(captured["surface"]),
            "reference_requirements": reference_requirements,
            "worker_request": request,
            "finalized": False,
        }
        return prepared if reference_requirements else finalize_candidate(prepared, [])
    except DomainRuntimeFailure:
        raise
    except Exception as exc:
        if staging is not None and staging.is_dir():
            shutil.rmtree(staging)
        _raise(
            tool_name,
            "PROGRAM_CONTRACT_INVALID",
            "schema",
            str(exc),
            requested=arguments,
            observed={"domain": pack.domain, "operation": operation},
        )


def _worker_environment(prepared: Mapping[str, Any]) -> dict[str, str]:
    staging = str(prepared["staging"])
    preserved = (
        "COMSPEC",
        "LANG",
        "LC_ALL",
        "LD_LIBRARY_PATH",
        "PATH",
        "PATHEXT",
        "SystemRoot",
        "WINDIR",
    )
    environment = {
        name: os.environ[name]
        for name in preserved
        if str(os.environ.get(name) or "").strip()
    }
    environment.update(
        {
            "HOME": staging,
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
            "TEMP": staging,
            "TMP": staging,
            "TMPDIR": staging,
            "CADEX_XSCRIPT_DOMAIN_REQUEST": str(Path(staging) / "request.json"),
            "CADEX_XSCRIPT_DOMAIN_RESULT": str(Path(staging) / "result.json"),
        }
    )
    if sys.platform == "win32":
        drive, tail = os.path.splitdrive(staging)
        environment["USERPROFILE"] = staging
        if drive:
            environment["HOMEDRIVE"] = drive
            environment["HOMEPATH"] = tail or "\\"
    return environment


def execute_candidate(
    prepared: Mapping[str, Any],
    *,
    cancellation_check: Callable[[], bool] | None,
) -> dict[str, Any]:
    from CadexScriptedProcess import run_process

    code = (
        "import os,runpy,sys;"
        "sys.path.insert(0,os.getcwd());"
        "runpy.run_path('worker.py',run_name='__main__')"
    )
    process = run_process(
        [str(prepared["freecadcmd_executable"]), "--safe-mode", "-c", code],
        cwd=str(prepared["staging"]),
        environment=_worker_environment(prepared),
        cancellation_check=cancellation_check,
        timeout_seconds=float(prepared["timeout_seconds"]),
        memory_limit_bytes=int(prepared["memory_limit_bytes"]),
    )
    if not process.get("started"):
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_WORKER_START_FAILED",
            "external_process",
            f"The isolated domain worker could not start: {process.get('error')}",
            observed=process,
        )
    if process.get("cancelled"):
        return _failure(
            str(prepared["tool_name"]),
            "RUN_CANCELLED",
            "external_process",
            "XScript domain execution was cancelled.",
            observed=process,
            cancelled=True,
        )
    if process.get("timed_out"):
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_EXECUTION_TIMEOUT",
            "external_process",
            f"XScript domain execution exceeded {prepared['timeout_seconds']:g} seconds.",
            observed=process,
        )
    if process.get("memory_exceeded"):
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_MEMORY_LIMIT_EXCEEDED",
            "external_process",
            "XScript domain execution exceeded its memory limit.",
            observed=process,
        )
    result_path = Path(str(prepared["staging"])) / "result.json"
    if not result_path.is_file():
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_WORKER_NO_RESULT",
            "external_process",
            "The isolated domain worker exited without a result.",
            observed=process,
        )
    try:
        report = _read_json(result_path, "domain worker result")
    except ValueError as exc:
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_WORKER_RESULT_INVALID",
            "external_process",
            str(exc),
            observed=process,
        )
    if not report.get("ok"):
        domain_details = (
            dict(report.get("details") or {})
            if isinstance(report.get("details"), Mapping)
            else {}
        )
        domain_failure_stage = str(domain_details.get("stage") or "").strip()
        correction = str(domain_details.get("correction") or "").strip()
        return _failure(
            str(prepared["tool_name"]),
            "DOMAIN_CANDIDATE_FAILED",
            "external_process",
            str(report.get("error") or "The domain worker rejected the candidate."),
            observed={
                "exception_type": report.get("exception_type"),
                "details": report.get("details"),
                "traceback": report.get("traceback"),
                "stdout": report.get("stdout") or process.get("stdout"),
                "stderr": process.get("stderr"),
                "elapsed_seconds": process.get("elapsed_seconds"),
            },
            **(
                {"domain_failure_stage": domain_failure_stage}
                if domain_failure_stage
                else {}
            ),
            required_changes=[correction] if correction else [],
        )
    report["process"] = process
    return report


_BREP_OUTPUT_TYPES = frozenset(
    {
        "solid",
        "shell",
        "face",
        "wire",
        "compound",
        "surface",
        "fill",
        "blend",
        "extension",
        "loft",
        "brep",
        "curve",
    }
)


def _validate_shape_class(output_type: str, facts: Mapping[str, Any]) -> None:
    shape_type = str(facts.get("shape_type") or "")
    counts = {
        "solid": int(facts.get("solids") or 0),
        "shell": int(facts.get("shells") or 0),
        "face": int(facts.get("faces") or 0),
        "wire": int(facts.get("wires") or 0),
    }
    expected_shape_types = {
        "solid": "Solid",
        "shell": "Shell",
        "face": "Face",
        "wire": "Wire",
    }
    if (
        output_type in expected_shape_types
        and shape_type != expected_shape_types[output_type]
    ):
        raise ValueError(
            f"A {output_type} output must have exact OCC ShapeType "
            f"{expected_shape_types[output_type]}, not {shape_type or '<missing>'}."
        )
    if output_type in counts and counts[output_type] != 1:
        raise ValueError(
            f"A {output_type} output must contain exactly one {output_type}."
        )
    if output_type == "compound" and shape_type != "Compound":
        raise ValueError("A compound output must have OCC ShapeType Compound.")
    if output_type in {"surface", "fill", "blend", "extension", "loft"} and not (
        counts["face"] or counts["shell"] or counts["solid"]
    ):
        raise ValueError(
            f"A {output_type} output must contain a face, shell, or solid."
        )


def _detached_shape_facts(shape: Any, *, max_subelements: int) -> dict[str, Any]:
    from cadex_part_worker import part_shape_facts

    return part_shape_facts(shape, max_subelements=max_subelements)


def _finite_vector(value: Any, label: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must be [x, y, z].")
    if any(isinstance(item, bool) for item in value):
        raise ValueError(f"{label} must contain numbers, not booleans.")
    result = [float(item) for item in value]
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{label} must contain finite coordinates.")
    return result


def _staged_artifact_path(
    prepared: Mapping[str, Any],
    relative: Any,
    *,
    context: str,
    maximum_bytes: int = 256 * 1024 * 1024,
) -> Path:
    root = Path(str(prepared["staging"])).resolve()
    raw = str(relative or "")
    candidate = root / raw
    path = candidate.resolve()
    if (
        not raw
        or root not in path.parents
        or not path.is_file()
        or candidate.is_symlink()
    ):
        raise ValueError(f"{context} does not resolve to a staged artifact.")
    try:
        relative_parts = candidate.relative_to(root).parts
    except ValueError as exc:
        raise ValueError(f"{context} is outside candidate staging.") from exc
    cursor = root
    for part in relative_parts[:-1]:
        cursor /= part
        if cursor.is_symlink():
            raise ValueError(f"{context} traverses a staged symlink.")
    size = path.stat().st_size
    if not 1 <= size <= maximum_bytes:
        raise ValueError(f"{context} must contain 1-{maximum_bytes} artifact bytes.")
    return path


def _finite_matrix(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 16:
        raise ValueError(f"{label} must contain exactly 16 matrix values.")
    if any(isinstance(item, bool) for item in value):
        raise ValueError(f"{label} must contain numbers, not booleans.")
    try:
        result = [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain only finite matrix values.") from exc
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{label} must contain only finite matrix values.")
    return result


def _assembly_placement_fact(value: Any, label: str) -> dict[str, Any]:
    fields = {
        "position_mm",
        "rotation_axis",
        "rotation_angle_degrees",
        "matrix",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(
            f"{label} must contain exactly position_mm, rotation_axis, "
            "rotation_angle_degrees, and matrix."
        )
    position = _finite_vector(value.get("position_mm"), f"{label}.position_mm")
    axis = _finite_vector(value.get("rotation_axis"), f"{label}.rotation_axis")
    raw_angle = value.get("rotation_angle_degrees")
    if isinstance(raw_angle, bool):
        raise ValueError(f"{label}.rotation_angle_degrees must be finite.")
    try:
        angle = float(raw_angle)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}.rotation_angle_degrees must be finite.") from exc
    if not math.isfinite(angle):
        raise ValueError(f"{label}.rotation_angle_degrees must be finite.")
    return {
        "position_mm": position,
        "rotation_axis": axis,
        "rotation_angle_degrees": angle,
        "matrix": _finite_matrix(value.get("matrix"), f"{label}.matrix"),
    }


def _assembly_native_placement_from_matrix(value: Any, label: str) -> Any:
    """Build a detached FreeCAD placement from one authenticated matrix."""

    import FreeCAD as App

    values = _finite_matrix(value, label)
    matrix = App.Matrix()
    for name, number in zip(
        (
            "A11",
            "A12",
            "A13",
            "A14",
            "A21",
            "A22",
            "A23",
            "A24",
            "A31",
            "A32",
            "A33",
            "A34",
            "A41",
            "A42",
            "A43",
            "A44",
        ),
        values,
        strict=True,
    ):
        setattr(matrix, name, number)
    return App.Placement(matrix)


def _assembly_native_declared_placement(value: Any, label: str) -> Any:
    """Reauthorize the normalized placement form exported by the Assembly API."""

    import FreeCAD as App

    if not isinstance(value, dict) or set(value) != {"position", "rotation"}:
        raise ValueError(f"{label} must contain exactly position and rotation.")
    if not isinstance(value.get("position"), list) or any(
        isinstance(item, bool) for item in value["position"]
    ):
        raise ValueError(f"{label}.position must contain three finite numbers.")
    position = _finite_vector(value.get("position"), f"{label}.position")
    rotation = value.get("rotation")
    if (
        not isinstance(rotation, list)
        or len(rotation) != 4
        or any(isinstance(item, bool) for item in rotation)
    ):
        raise ValueError(f"{label}.rotation must contain four numbers.")
    try:
        quaternion = [float(item) for item in rotation]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}.rotation must contain finite numbers.") from exc
    if not all(math.isfinite(item) for item in quaternion):
        raise ValueError(f"{label}.rotation must contain finite numbers.")
    magnitude = math.sqrt(sum(item * item for item in quaternion))
    if not math.isclose(magnitude, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError(f"{label}.rotation must be a normalized quaternion.")
    return App.Placement(App.Vector(*position), App.Rotation(*quaternion))


def _assembly_native_matrix(value: Any) -> list[float]:
    matrix = value.toMatrix()
    return [
        float(getattr(matrix, name))
        for name in (
            "A11",
            "A12",
            "A13",
            "A14",
            "A21",
            "A22",
            "A23",
            "A24",
            "A31",
            "A32",
            "A33",
            "A34",
            "A41",
            "A42",
            "A43",
            "A44",
        )
    ]


def _assembly_close_numbers(
    observed: Sequence[Any],
    expected: Sequence[Any],
    label: str,
    *,
    absolute_tolerance: float = 1.0e-8,
) -> list[float]:
    if any(isinstance(item, bool) for item in (*observed, *expected)):
        raise ValueError(f"{label} must contain numbers, not booleans.")
    try:
        actual = [float(item) for item in observed]
        wanted = [float(item) for item in expected]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain finite numbers.") from exc
    if len(actual) != len(wanted) or not all(
        math.isfinite(item) for item in (*actual, *wanted)
    ):
        raise ValueError(f"{label} has invalid numeric cardinality or values.")
    if any(
        not math.isclose(
            left,
            right,
            rel_tol=1.0e-10,
            abs_tol=absolute_tolerance,
        )
        for left, right in zip(actual, wanted, strict=True)
    ):
        raise ValueError(f"{label} disagrees with independently derived native state.")
    return actual


def _assembly_validate_placement_fact(
    value: Any,
    expected: Any,
    label: str,
) -> dict[str, Any]:
    fact = _assembly_placement_fact(value, label)
    _assembly_close_numbers(
        fact["matrix"],
        _assembly_native_matrix(expected),
        f"{label}.matrix",
    )
    _assembly_close_numbers(
        fact["position_mm"],
        [expected.Base.x, expected.Base.y, expected.Base.z],
        f"{label}.position_mm",
    )
    _assembly_close_numbers(
        fact["rotation_axis"],
        [
            expected.Rotation.Axis.x,
            expected.Rotation.Axis.y,
            expected.Rotation.Axis.z,
        ],
        f"{label}.rotation_axis",
    )
    _assembly_close_numbers(
        [fact["rotation_angle_degrees"]],
        [math.degrees(float(expected.Rotation.Angle))],
        f"{label}.rotation_angle_degrees",
    )
    return fact


def _assembly_compatibility(
    kind: str, connectors: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    geometry = [str(item.get("geometry_type") or "") for item in connectors]
    axis_capable = {"line", "circle", "plane", "cylinder", "cone", "component_origin"}
    rotary = {"circle", "cylinder", "cone"}
    linear = {"line", "plane"}
    criteria = "any valid connector geometry"
    compatible = all(geometry)
    if kind in {"revolute", "cylindrical", "screw", "gears", "belt"}:
        criteria = "both connectors must define axes"
        compatible = all(item in axis_capable for item in geometry)
    elif kind == "slider":
        criteria = "both connectors must define linear axes or plane normals"
        compatible = all(item in linear | {"component_origin"} for item in geometry)
    elif kind == "rack_pinion":
        criteria = "one linear connector and one circular/cylindrical connector"
        compatible = any(item in linear for item in geometry) and any(
            item in rotary for item in geometry
        )
    elif kind in {"parallel", "perpendicular", "angle"}:
        criteria = "both connectors must define orientations"
        compatible = all(item in axis_capable for item in geometry)
    return {
        "ok": compatible,
        "joint_type": kind,
        "criteria": criteria,
        "resolved_geometry_types": geometry,
    }


def _assembly_frame_z_axis(frame: Mapping[str, Any]) -> tuple[float, float, float]:
    matrix = _finite_matrix(frame.get("matrix"), "Assembly connector local frame")
    return (matrix[2], matrix[6], matrix[10])


def _assembly_parallel_axes(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> bool:
    axis1 = _assembly_frame_z_axis(first)
    axis2 = _assembly_frame_z_axis(second)
    norm1 = math.sqrt(sum(item * item for item in axis1))
    norm2 = math.sqrt(sum(item * item for item in axis2))
    if norm1 <= 1.0e-12 or norm2 <= 1.0e-12:
        return False
    dot = sum(a * b for a, b in zip(axis1, axis2, strict=True)) / (norm1 * norm2)
    return abs(dot) >= 1.0 - 1.0e-7


def _assembly_joint_dependency_issues(
    joint_data: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    sliders = [
        (name, data)
        for name, data in joint_data.items()
        if data.get("kind") == "slider" and not bool(data.get("suppressed"))
    ]
    issues: list[dict[str, Any]] = []
    for name, data in joint_data.items():
        kind = str(data.get("kind") or "")
        if kind not in {"rack_pinion", "screw"} or bool(data.get("suppressed")):
            continue
        connectors = list(data.get("connectors") or [])
        compatible_slider = None
        for slider_name, slider_data in sliders:
            slider_connectors = list(slider_data.get("connectors") or [])
            if any(
                connector.get("component_output")
                == slider_connector.get("component_output")
                and _assembly_parallel_axes(
                    dict(connector.get("local_frame") or {}),
                    dict(slider_connector.get("local_frame") or {}),
                )
                for connector in connectors
                for slider_connector in slider_connectors
            ):
                compatible_slider = slider_name
                break
        if compatible_slider is None:
            issues.append(
                {
                    "code": "missing_collinear_slider",
                    "joint_output": name,
                    "joint_type": kind,
                    "component_outputs": [
                        str(item.get("component_output") or "") for item in connectors
                    ],
                    "available_slider_outputs": [item[0] for item in sliders],
                    "requirement": (
                        "FreeCAD's native RackPinion and Screw joints require a "
                        "non-suppressed Slider joint sharing one component with a "
                        "collinear local connector +Z axis."
                    ),
                    "suggestion": (
                        "Create and return an api.joint('slider', ...) for the rack "
                        "or screw component, align both connector +Z axes, and include "
                        "both joints in api.assembly."
                    ),
                }
            )
    return issues


def _assembly_limits(value: Any, label: str) -> list[float | None] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{label} must be null or a two-endpoint array.")
    result: list[float | None] = []
    for index, item in enumerate(value):
        if item is None:
            result.append(None)
            continue
        if isinstance(item, bool):
            raise ValueError(f"{label}[{index}] must be a finite number or null.")
        number = float(item)
        if not math.isfinite(number):
            raise ValueError(f"{label}[{index}] must be finite.")
        result.append(number)
    if result == [None, None]:
        raise ValueError(f"{label} cannot disable both endpoints; use null instead.")
    if result[0] is not None and result[1] is not None and result[0] > result[1]:
        raise ValueError(f"{label} minimum must not exceed maximum.")
    return result


def _assembly_motion_formula(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 512
        or not value.isascii()
    ):
        raise ValueError(
            f"{label} must be a non-empty ASCII expression of at most 512 characters."
        )
    if "**" in value:
        raise ValueError(f"{label} must use canonical native '^' power syntax.")
    try:
        tree = ast.parse(value.replace("^", "**"), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"{label} has invalid expression syntax.") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > 128:
        raise ValueError(f"{label} exceeds the expression complexity limit.")
    functions = {"abs", "asin", "arcsin", "arctan", "cos", "sin"}
    names = {"time", "initialValue", "pi"} | functions
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.UAdd,
        ast.USub,
    )
    for node in nodes:
        if not isinstance(node, allowed):
            raise ValueError(
                f"{label} contains unsupported expression element "
                f"{type(node).__name__}."
            )
        if isinstance(node, ast.Constant) and (
            isinstance(node.value, bool)
            or not isinstance(node.value, (int, float))
            or not math.isfinite(float(node.value))
        ):
            raise ValueError(f"{label} contains an invalid numeric constant.")
        if isinstance(node, ast.Name) and node.id not in names:
            raise ValueError(f"{label} contains unknown name {node.id!r}.")
        if isinstance(node, ast.Call) and (
            not isinstance(node.func, ast.Name)
            or node.func.id not in functions
            or len(node.args) != 1
            or node.keywords
        ):
            raise ValueError(f"{label} contains an unsupported function call.")
    return value


def _assembly_compact_placement(value: Any, label: str) -> dict[str, list[float]]:
    if not isinstance(value, dict) or set(value) != {
        "position_mm",
        "rotation_xyzw",
    }:
        raise ValueError(f"{label} must contain exactly position_mm and rotation_xyzw.")
    position = value.get("position_mm")
    rotation = value.get("rotation_xyzw")
    if not isinstance(position, list) or len(position) != 3:
        raise ValueError(f"{label}.position_mm must contain three numbers.")
    if not isinstance(rotation, list) or len(rotation) != 4:
        raise ValueError(f"{label}.rotation_xyzw must contain four numbers.")
    try:
        clean_position = [float(item) for item in position]
        clean_rotation = [float(item) for item in rotation]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain only finite numbers.") from exc
    if not all(math.isfinite(item) for item in (*clean_position, *clean_rotation)):
        raise ValueError(f"{label} must contain only finite numbers.")
    magnitude = math.sqrt(sum(item * item for item in clean_rotation))
    if not math.isclose(magnitude, 1.0, rel_tol=1.0e-10, abs_tol=1.0e-10):
        raise ValueError(f"{label}.rotation_xyzw must be normalized.")
    return {"position_mm": clean_position, "rotation_xyzw": clean_rotation}


def _assembly_quaternion_multiply(
    first: list[float], second: list[float]
) -> list[float]:
    x1, y1, z1, w1 = first
    x2, y2, z2, w2 = second
    return [
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    ]


def _assembly_quaternion_rotate(
    quaternion: list[float], vector: list[float]
) -> list[float]:
    rotated = _assembly_quaternion_multiply(
        _assembly_quaternion_multiply(quaternion, [*vector, 0.0]),
        [-quaternion[0], -quaternion[1], -quaternion[2], quaternion[3]],
    )
    return rotated[:3]


def _assembly_relative_compact_placement(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> tuple[list[float], list[float]]:
    first_position = list(first["position_mm"])
    second_position = list(second["position_mm"])
    first_rotation = list(first["rotation_xyzw"])
    second_rotation = list(second["rotation_xyzw"])
    inverse = [
        -first_rotation[0],
        -first_rotation[1],
        -first_rotation[2],
        first_rotation[3],
    ]
    relative_position = _assembly_quaternion_rotate(
        inverse,
        [second_position[index] - first_position[index] for index in range(3)],
    )
    relative_rotation = _assembly_quaternion_multiply(inverse, second_rotation)
    magnitude = math.sqrt(sum(value * value for value in relative_rotation))
    return relative_position, [value / magnitude for value in relative_rotation]


def _assembly_motion_observations(
    frames: list[dict[str, Any]],
    motion_records: list[dict[str, Any]],
    joint_records: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for record in motion_records:
        connectors = list(joint_records[str(record["joint_output"])]["connectors"])
        first_component = str(connectors[0]["component_output"])
        second_component = str(connectors[1]["component_output"])
        initial_position, initial_rotation = _assembly_relative_compact_placement(
            frames[0]["component_placements"][first_component],
            frames[0]["component_placements"][second_component],
        )
        maximum_translation = 0.0
        maximum_rotation = 0.0
        for frame in frames[1:]:
            position, rotation = _assembly_relative_compact_placement(
                frame["component_placements"][first_component],
                frame["component_placements"][second_component],
            )
            maximum_translation = max(
                maximum_translation,
                math.sqrt(
                    sum(
                        (position[index] - initial_position[index]) ** 2
                        for index in range(3)
                    )
                ),
            )
            dot = abs(
                sum(initial_rotation[index] * rotation[index] for index in range(4))
            )
            maximum_rotation = max(
                maximum_rotation,
                math.degrees(2.0 * math.acos(max(-1.0, min(1.0, dot)))),
            )
        observations.append(
            {
                **record,
                "component_outputs": [first_component, second_component],
                "time_dependent": bool(re.search(r"\btime\b", str(record["formula"]))),
                "maximum_relative_translation_mm": maximum_translation,
                "maximum_relative_rotation_degrees": maximum_rotation,
            }
        )
    return observations


def _validate_assembly_exploded_views(
    prepared: Mapping[str, Any],
    views: Sequence[dict[str, Any]],
    *,
    assembly_item: Mapping[str, Any],
    assembly_definition: Mapping[str, Any],
    by_name: Mapping[str, dict[str, Any]],
    component_names: Sequence[str],
    component_placements: Mapping[str, Mapping[str, Any]],
    component_sources: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Independently derive every native exploded move from authenticated BREPs."""

    if not views:
        return []

    import FreeCAD as App
    import Part

    worker_references = {
        (
            str(item.get("document_uid") or ""),
            str(item.get("object_name") or ""),
        ): item
        for item in list(
            dict(prepared.get("worker_request") or {}).get("document_references") or []
        )
        if isinstance(item, Mapping)
    }
    source_shapes: dict[tuple[str, str], Any] = {}
    native_placements: dict[str, Any] = {}
    component_centers: dict[str, list[float]] = {}
    bounds_minimum = [math.inf, math.inf, math.inf]
    bounds_maximum = [-math.inf, -math.inf, -math.inf]
    for component_name in component_names:
        component_item = by_name[component_name]
        component_data = component_item.get("assembly_data")
        if not isinstance(component_data, Mapping):
            raise ValueError(
                f"Component output {component_name!r} has no exploded-view source data."
            )
        source = component_data.get("source")
        if not isinstance(source, Mapping):
            raise ValueError(
                f"Component output {component_name!r} has no exploded-view source identity."
            )
        key = (
            str(source.get("document_uid") or ""),
            str(source.get("object_name") or ""),
        )
        resolved = component_sources.get(component_name)
        descriptor = worker_references.get(key)
        if resolved is None or descriptor is None:
            raise ValueError(
                f"Component output {component_name!r} has no authenticated staged BREP."
            )
        path = _staged_artifact_path(
            prepared,
            descriptor.get("artifact_path"),
            context=f"Component output {component_name!r} exploded-view source",
        )
        digest = _sha256_file(path)
        if digest != str(descriptor.get("brep_sha256") or "") or digest != str(
            resolved.get("brep_sha256") or ""
        ):
            raise ValueError(
                f"Component output {component_name!r} source BREP changed after "
                "revision binding."
            )
        shape = source_shapes.get(key)
        if shape is None:
            shape = Part.Shape()
            shape.importBrep(str(path))
            if shape.isNull() or not shape.isValid():
                raise ValueError(
                    f"Component output {component_name!r} staged BREP is invalid."
                )
            source_shapes[key] = shape
        placement = _assembly_native_placement_from_matrix(
            component_placements[component_name]["matrix"],
            f"Component output {component_name!r} solved placement",
        )
        placed_shape = shape.copy()
        # App::Link occurrences apply their own Placement to the linked
        # topological shape and deliberately do not compound the source
        # object's Placement. Mirror that native occurrence behavior exactly.
        placed_shape.Placement = placement
        bounds = placed_shape.BoundBox
        if not bool(bounds.isValid()):
            raise ValueError(
                f"Component output {component_name!r} has invalid solved bounds."
            )
        minimum = [float(bounds.XMin), float(bounds.YMin), float(bounds.ZMin)]
        maximum = [float(bounds.XMax), float(bounds.YMax), float(bounds.ZMax)]
        center = [(minimum[index] + maximum[index]) / 2.0 for index in range(3)]
        for index in range(3):
            bounds_minimum[index] = min(bounds_minimum[index], minimum[index])
            bounds_maximum[index] = max(bounds_maximum[index], maximum[index])
        native_placements[component_name] = placement
        component_centers[component_name] = center
    assembly_center = [
        (bounds_minimum[index] + bounds_maximum[index]) / 2.0 for index in range(3)
    ]
    assembly_diagonal = math.sqrt(
        sum((bounds_maximum[index] - bounds_minimum[index]) ** 2 for index in range(3))
    )
    if not math.isfinite(assembly_diagonal) or assembly_diagonal <= 1.0e-12:
        raise ValueError("The authenticated Assembly source bounds are degenerate.")

    component_index = {name: index for index, name in enumerate(component_names)}
    summaries: list[dict[str, Any]] = []
    for view_item in views:
        view_name = str(view_item["name"])
        definition = view_item.get("definition")
        if (
            not isinstance(definition, dict)
            or definition.get("domain") != "assembly"
            or definition.get("operation") != "exploded_view"
            or definition.get("output_type") != "exploded_view"
            or definition.get("arguments") != [assembly_definition]
        ):
            raise ValueError(
                f"Exploded-view output {view_name!r} does not consume the returned "
                "assembly graph."
            )
        properties = definition.get("properties")
        if (
            not isinstance(properties, dict)
            or set(properties) - {"moves", "label"}
            or "moves" not in properties
        ):
            raise ValueError(
                f"Exploded-view output {view_name!r} has malformed properties."
            )
        if "label" in properties and (
            not isinstance(properties["label"], str)
            or not properties["label"]
            or properties["label"] != properties["label"].strip()
            or len(properties["label"]) > 120
        ):
            raise ValueError(
                f"Exploded-view output {view_name!r} has an invalid normalized label."
            )
        definition_moves = properties["moves"]
        if (
            not isinstance(definition_moves, list)
            or not 1 <= len(definition_moves) <= 64
        ):
            raise ValueError(
                f"Exploded-view output {view_name!r} must contain 1-64 moves."
            )
        data = view_item.get("assembly_data")
        required_data_fields = {
            "schema",
            "assembly_output",
            "moves",
            "assembly_bounds",
            "final_component_placements",
            "line_count",
            "native_readback",
        }
        if not isinstance(data, dict) or set(data) != required_data_fields:
            raise ValueError(
                f"Exploded-view output {view_name!r} has malformed native evidence."
            )
        if data.get("schema") != _ASSEMBLY_EXPLODED_VIEW_SCHEMA or str(
            data.get("assembly_output") or ""
        ) != str(assembly_item["name"]):
            raise ValueError(
                f"Exploded-view output {view_name!r} has the wrong schema or assembly."
            )
        reported_bounds = data.get("assembly_bounds")
        if not isinstance(reported_bounds, dict) or set(reported_bounds) != {
            "center_mm",
            "diagonal_mm",
        }:
            raise ValueError(
                f"Exploded-view output {view_name!r} has malformed assembly bounds."
            )
        _assembly_close_numbers(
            reported_bounds["center_mm"],
            assembly_center,
            f"Exploded-view output {view_name!r} assembly center",
        )
        _assembly_close_numbers(
            [reported_bounds["diagonal_mm"]],
            [assembly_diagonal],
            f"Exploded-view output {view_name!r} assembly diagonal",
        )
        move_records = data.get("moves")
        if not isinstance(move_records, list) or len(move_records) != len(
            definition_moves
        ):
            raise ValueError(
                f"Exploded-view output {view_name!r} move evidence is incomplete."
            )
        current_placements = {
            name: placement.copy() for name, placement in native_placements.items()
        }
        expected_move_types: list[str] = []
        expected_reference_paths: list[list[str]] = []
        moved_names: list[str] = []
        reference_count = 0
        for move_index, (definition_move, record) in enumerate(
            zip(definition_moves, move_records, strict=True)
        ):
            context = f"Exploded-view output {view_name!r} move {move_index}"
            if not isinstance(definition_move, dict) or not isinstance(record, dict):
                raise ValueError(f"{context} must be an object.")
            kind = str(definition_move.get("kind") or "")
            definition_fields = (
                {"kind", "components", "transform"}
                if kind == "normal"
                else {"kind", "components", "radial_distance_mm"}
                if kind == "radial"
                else set()
            )
            record_fields = (
                {
                    "move_index",
                    "kind",
                    "component_outputs",
                    "transform",
                    "movement_transform",
                    "changed_component_outputs",
                    "final_placements",
                    "line_segments",
                }
                if kind == "normal"
                else {
                    "move_index",
                    "kind",
                    "component_outputs",
                    "radial_distance_mm",
                    "movement_transform",
                    "changed_component_outputs",
                    "final_placements",
                    "line_segments",
                }
                if kind == "radial"
                else set()
            )
            if (
                set(definition_move) != definition_fields
                or set(record) != record_fields
            ):
                raise ValueError(f"{context} has malformed fields or move type.")
            component_outputs = record.get("component_outputs")
            if (
                not isinstance(component_outputs, list)
                or not component_outputs
                or any(not isinstance(name, str) for name in component_outputs)
                or len(component_outputs) != len(set(component_outputs))
                or any(name not in component_index for name in component_outputs)
            ):
                raise ValueError(f"{context} has invalid component outputs.")
            component_definitions = definition_move.get("components")
            if component_definitions != [
                by_name[name].get("definition") for name in component_outputs
            ]:
                raise ValueError(
                    f"{context} does not reference the exact declared components in order."
                )
            if (
                type(record.get("move_index")) is not int
                or record.get("move_index") != move_index
                or record.get("kind") != kind
            ):
                raise ValueError(f"{context} changed its index or kind.")
            reference_count += len(component_outputs)
            if reference_count > 256:
                raise ValueError(
                    f"Exploded-view output {view_name!r} exceeds 256 component references."
                )
            movement = None
            radial_distance = None
            if kind == "normal":
                declared_transform = definition_move["transform"]
                if record.get("transform") != declared_transform:
                    raise ValueError(f"{context} changed its declared transform.")
                movement = _assembly_native_declared_placement(
                    declared_transform,
                    f"{context} transform",
                )
            else:
                raw_distance = definition_move["radial_distance_mm"]
                if isinstance(raw_distance, bool):
                    raise ValueError(f"{context} radial distance must be numeric.")
                try:
                    radial_distance = float(raw_distance)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"{context} radial distance must be numeric."
                    ) from exc
                if (
                    not math.isfinite(radial_distance)
                    or not 0.0 < radial_distance <= 1.0e6
                    or record.get("radial_distance_mm") != raw_distance
                ):
                    raise ValueError(f"{context} has an invalid radial distance.")
                movement = App.Placement(
                    App.Vector(radial_distance, 0.0, 0.0), App.Rotation()
                )
            _assembly_validate_placement_fact(
                record.get("movement_transform"),
                movement,
                f"{context} native movement",
            )
            final_placements = record.get("final_placements")
            line_segments = record.get("line_segments")
            if (
                not isinstance(final_placements, dict)
                or set(final_placements) != set(component_outputs)
                or not isinstance(line_segments, list)
                or len(line_segments) != len(component_outputs)
                or record.get("changed_component_outputs") != component_outputs
            ):
                raise ValueError(
                    f"{context} has incomplete placement or explosion-line evidence."
                )
            expected_reference_paths.append(
                [
                    f"CandidateComponent{component_index[name]}."
                    for name in component_outputs
                ]
            )
            expected_move_types.append("Normal" if kind == "normal" else "Radial")
            for component_name, line in zip(
                component_outputs, line_segments, strict=True
            ):
                previous = current_placements[component_name]
                if kind == "normal":
                    updated = movement * previous
                else:
                    assert radial_distance is not None
                    factor = 4.0 * radial_distance / assembly_diagonal
                    displacement = [
                        (
                            component_centers[component_name][axis]
                            - assembly_center[axis]
                        )
                        * factor
                        for axis in range(3)
                    ]
                    updated = previous.copy()
                    updated.Base = updated.Base + App.Vector(*displacement)
                previous_matrix = _assembly_native_matrix(previous)
                updated_matrix = _assembly_native_matrix(updated)
                if all(
                    math.isclose(left, right, rel_tol=1.0e-10, abs_tol=1.0e-10)
                    for left, right in zip(previous_matrix, updated_matrix, strict=True)
                ):
                    raise ValueError(
                        f"{context} component {component_name!r} has no measurable move."
                    )
                _assembly_validate_placement_fact(
                    final_placements[component_name],
                    updated,
                    f"{context} component {component_name!r} final placement",
                )
                if not isinstance(line, dict) or set(line) != {
                    "component_output",
                    "start_mm",
                    "end_mm",
                    "length_mm",
                }:
                    raise ValueError(
                        f"{context} component {component_name!r} line is malformed."
                    )
                if line.get("component_output") != component_name:
                    raise ValueError(
                        f"{context} explosion line belongs to the wrong component."
                    )
                start = component_centers[component_name]
                delta = updated * previous.inverse()
                end_vector = delta.multVec(App.Vector(*start))
                end = [float(end_vector.x), float(end_vector.y), float(end_vector.z)]
                _assembly_close_numbers(
                    line.get("start_mm"),
                    start,
                    f"{context} component {component_name!r} line start",
                )
                _assembly_close_numbers(
                    line.get("end_mm"),
                    end,
                    f"{context} component {component_name!r} line end",
                )
                length = math.dist(start, end)
                _assembly_close_numbers(
                    [line.get("length_mm")],
                    [length],
                    f"{context} component {component_name!r} line length",
                )
                if length <= 1.0e-10:
                    raise ValueError(
                        f"{context} component {component_name!r} line has zero length."
                    )
                current_placements[component_name] = updated
                if component_name not in moved_names:
                    moved_names.append(component_name)
        final_component_placements = data.get("final_component_placements")
        if not isinstance(final_component_placements, dict) or set(
            final_component_placements
        ) != set(component_names):
            raise ValueError(
                f"Exploded-view output {view_name!r} final component graph is incomplete."
            )
        for component_name in component_names:
            _assembly_validate_placement_fact(
                final_component_placements[component_name],
                current_placements[component_name],
                f"Exploded-view output {view_name!r} component "
                f"{component_name!r} complete final placement",
            )
        if (
            type(data.get("line_count")) is not int
            or data.get("line_count") != reference_count
        ):
            raise ValueError(
                f"Exploded-view output {view_name!r} line count is inconsistent."
            )
        readback = data.get("native_readback")
        expected_readback = {
            "view_group_type": "Assembly::ViewGroup",
            "view_proxy_class": "ExplodedView",
            "step_proxy_classes": ["ExplodedViewStep"] * len(definition_moves),
            "move_types": expected_move_types,
            "reference_paths": expected_reference_paths,
        }
        if readback != expected_readback:
            raise ValueError(
                f"Exploded-view output {view_name!r} native object readback changed."
            )
        summaries.append(
            {
                "exploded_view_output": view_name,
                "move_count": len(definition_moves),
                "component_reference_count": reference_count,
                "moved_component_outputs": moved_names,
                "line_count": reference_count,
                "assembly_bounds": dict(reported_bounds),
            }
        )
    return summaries


def _assembly_hierarchy_contract(
    resolved_reference: Mapping[str, Any], *, context: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    descriptor = resolved_reference.get("assembly_hierarchy")
    if not isinstance(descriptor, dict) or descriptor.get("schema") != (
        "cadex-assembly-source-hierarchy-v1"
    ):
        raise ValueError(f"{context} has no authenticated Assembly hierarchy.")
    nodes = descriptor.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError(f"{context} Assembly hierarchy has no nodes.")
    node_by_id = {
        str(node.get("node_id") or ""): node for node in nodes if isinstance(node, dict)
    }
    if len(node_by_id) != len(nodes) or "" in node_by_id:
        raise ValueError(f"{context} Assembly hierarchy has duplicate node identities.")
    root = node_by_id.get(str(descriptor.get("root_node_id") or ""))
    if root is None or str(root.get("kind") or "") not in {"assembly", "part"}:
        raise ValueError(
            f"{context} Assembly hierarchy has an invalid container root node."
        )
    paths = descriptor.get("occurrence_paths")
    if not isinstance(paths, list) or any(
        not isinstance(item, dict) or not str(item.get("path") or "") for item in paths
    ):
        raise ValueError(f"{context} Assembly hierarchy has invalid occurrence paths.")
    return descriptor, node_by_id


def _assembly_hierarchy_path(
    resolved_reference: Mapping[str, Any],
    stable_path: str,
    *,
    context: str,
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], dict[str, Any]]]]:
    descriptor, node_by_id = _assembly_hierarchy_contract(
        resolved_reference, context=context
    )
    declared_paths = {
        str(item.get("path") or "")
        for item in list(descriptor.get("occurrence_paths") or [])
    }
    if stable_path not in declared_paths:
        raise ValueError(
            f"{context} uses occurrence_path {stable_path!r}, which is not in the "
            "authenticated source hierarchy."
        )
    current = node_by_id[str(descriptor["root_node_id"])]
    chain: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for segment in stable_path.split("/"):
        occurrences = list(current.get("occurrences") or [])
        occurrence = next(
            (
                item
                for item in occurrences
                if isinstance(item, dict) and str(item.get("name") or "") == segment
            ),
            None,
        )
        if occurrence is None:
            raise ValueError(
                f"{context} occurrence_path {stable_path!r} disagrees with its node graph."
            )
        source = node_by_id.get(str(occurrence.get("source_node_id") or ""))
        if source is None:
            raise ValueError(
                f"{context} occurrence_path reaches a missing source node."
            )
        chain.append((occurrence, source))
        current = source
    return descriptor, chain


def _assembly_hierarchy_leaf_metadata(node: Mapping[str, Any]) -> dict[str, Any]:
    contract = node.get("reference_contract")
    result = dict(contract) if isinstance(contract, dict) else {}
    artifact = node.get("shape_artifact")
    result["facts"] = (
        dict(artifact.get("facts") or {}) if isinstance(artifact, dict) else {}
    )
    result["type_id"] = str(node.get("type_id") or "")
    result["source_kind"] = str(node.get("kind") or "")
    return result


def _assembly_expected_native_reference(
    component_data: Mapping[str, Any],
    chain: list[tuple[dict[str, Any], dict[str, Any]]],
    worker_chain: Any,
    *,
    stable_path: str,
    element: str,
    anchor: str,
    context: str,
) -> tuple[str, list[str], str]:
    if not isinstance(worker_chain, list) or len(worker_chain) != len(chain):
        raise ValueError(f"{context} has malformed native hierarchy evidence.")
    component_native_name = str(component_data.get("native_name") or "")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", component_native_name):
        raise ValueError(f"{context} component has no valid native object identity.")
    target_name = component_native_name
    prefix_names: list[str] = []
    locked = False
    previous_native_type = str(component_data.get("native_type_id") or "")
    if previous_native_type not in {"Assembly::AssemblyLink", "App::Link"}:
        raise ValueError(
            f"{context} component has unsupported native hierarchy root type "
            f"{previous_native_type!r}."
        )
    previous_rigid = (
        not bool(component_data.get("flexible"))
        if previous_native_type == "Assembly::AssemblyLink"
        else True
    )
    for index, ((occurrence, source), evidence) in enumerate(
        zip(chain, worker_chain, strict=True)
    ):
        if not isinstance(evidence, dict):
            raise ValueError(f"{context} native hierarchy step {index} is malformed.")
        expected_type = (
            "Assembly::AssemblyLink"
            if str(occurrence.get("link_mode") or "") == "assembly_link"
            else "App::Link"
        )
        native_name = str(evidence.get("native_name") or "")
        expected_live = previous_native_type in {
            "Assembly::AssemblyLink",
            "Assembly::AssemblyObject",
        }
        expected = {
            "stable_name": str(occurrence.get("name") or ""),
            "source_node_id": str(source.get("node_id") or ""),
            "source_kind": str(source.get("kind") or ""),
            "native_type_id": expected_type,
            "container_type_id": previous_native_type,
            "container_rigid": (
                previous_rigid
                if previous_native_type == "Assembly::AssemblyLink"
                else None
            ),
            "live_occurrence": expected_live,
        }
        for field, expected_value in expected.items():
            if evidence.get(field) != expected_value:
                raise ValueError(
                    f"{context} native hierarchy step {index} changed {field!r}."
                )
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", native_name):
            raise ValueError(
                f"{context} native hierarchy step {index} has an invalid object name."
            )
        if locked:
            prefix_names.append(native_name)
        elif previous_native_type == "Assembly::AssemblyLink":
            if previous_rigid:
                locked = True
                prefix_names.append(native_name)
            else:
                target_name = native_name
                prefix_names = []
        else:
            locked = True
            prefix_names.append(native_name)
        previous_native_type = expected_type
        previous_rigid = bool(occurrence.get("rigid", True))
    prefix = ".".join(prefix_names)
    subelements = [
        (f"{prefix}.{value}" if prefix and value else f"{prefix}." if prefix else value)
        for value in (element, anchor)
    ]
    mode = "prefixed_rigid_boundary" if prefix else "direct_exposed_occurrence"
    return target_name, subelements, mode


def _validate_assembly_execution(
    prepared: Mapping[str, Any],
    execution: Mapping[str, Any],
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Reauthorize a worker-produced native Assembly graph and diagnostics."""

    validation = execution.get("assembly_validation")
    if not isinstance(validation, dict):
        raise ValueError("The Assembly worker returned no native validation summary.")
    by_type: dict[str, list[dict[str, Any]]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for item in outputs:
        by_type.setdefault(str(item.get("type") or ""), []).append(item)
        by_name[str(item.get("name") or "")] = item
    if len(by_type.get("assembly", [])) != 1:
        raise ValueError(
            "An Assembly candidate must contain exactly one assembly output."
        )
    if len(by_type.get("solver_diagnostics", [])) != 1:
        raise ValueError(
            "An Assembly candidate must contain exactly one solver_diagnostics output."
        )
    components = by_type.get("component_link", [])
    joints = by_type.get("joint", [])
    motions = by_type.get("motion", [])
    simulations = by_type.get("simulation", [])
    exploded_views = by_type.get("exploded_view", [])
    if not components:
        raise ValueError(
            "An Assembly candidate must contain at least one component_link."
        )
    if bool(motions) != bool(simulations) or len(simulations) > 1:
        raise ValueError(
            "Assembly motion outputs require exactly one simulation output, and a "
            "simulation requires at least one motion output."
        )
    assembly_item = by_type["assembly"][0]
    diagnostics_item = by_type["solver_diagnostics"][0]
    assembly_definition = assembly_item.get("definition")
    if (
        not isinstance(assembly_definition, dict)
        or assembly_definition.get("domain") != "assembly"
        or assembly_definition.get("operation") != "assembly"
        or assembly_definition.get("output_type") != "assembly"
    ):
        raise ValueError("The assembly output has an invalid declarative definition.")
    assembly_properties = assembly_definition.get("properties")
    if not isinstance(assembly_properties, dict):
        raise ValueError("The assembly output definition has no graph properties.")
    assembly_data = assembly_item.get("assembly_data")
    if not isinstance(assembly_data, dict):
        raise ValueError("The assembly output has no validated graph metadata.")
    returned_component_names = [str(item["name"]) for item in components]
    returned_joint_names = [str(item["name"]) for item in joints]
    returned_motion_names = [str(item["name"]) for item in motions]
    component_names = [
        str(item) for item in list(assembly_data.get("component_outputs") or [])
    ]
    joint_names = [str(item) for item in list(assembly_data.get("joint_outputs") or [])]
    if len(component_names) != len(set(component_names)) or set(component_names) != set(
        returned_component_names
    ):
        raise ValueError(
            "The assembly graph components do not exactly match returned component outputs."
        )
    if len(joint_names) != len(set(joint_names)) or set(joint_names) != set(
        returned_joint_names
    ):
        raise ValueError(
            "The assembly graph joints do not exactly match returned joint outputs."
        )
    if str(assembly_data.get("diagnostics_output") or "") != str(
        diagnostics_item["name"]
    ):
        raise ValueError("The assembly graph points to the wrong diagnostics output.")
    if simulations:
        graph_motion_names = [
            str(item) for item in list(assembly_data.get("motion_outputs") or [])
        ]
        if len(graph_motion_names) != len(set(graph_motion_names)) or set(
            graph_motion_names
        ) != set(returned_motion_names):
            raise ValueError(
                "The assembly graph motions do not exactly match returned motion outputs."
            )
        if str(assembly_data.get("simulation_output") or "") != str(
            simulations[0]["name"]
        ):
            raise ValueError(
                "The assembly graph points to the wrong simulation output."
            )
    elif "motion_outputs" in assembly_data or "simulation_output" in assembly_data:
        raise ValueError("The assembly graph reports an undeclared simulation.")
    returned_exploded_view_names = [str(item["name"]) for item in exploded_views]
    if exploded_views:
        graph_exploded_view_names = [
            str(item) for item in list(assembly_data.get("exploded_view_outputs") or [])
        ]
        if (
            len(graph_exploded_view_names) != len(set(graph_exploded_view_names))
            or graph_exploded_view_names != returned_exploded_view_names
        ):
            raise ValueError(
                "The assembly graph exploded views do not exactly match returned "
                "exploded_view outputs in declaration order."
            )
    elif "exploded_view_outputs" in assembly_data:
        raise ValueError("The assembly graph reports an undeclared exploded view.")
    graph_component_definitions = assembly_properties.get("components")
    graph_joint_definitions = assembly_properties.get("joints")
    if not isinstance(graph_component_definitions, list) or len(
        graph_component_definitions
    ) != len(component_names):
        raise ValueError("The assembly definition has the wrong component graph.")
    if not isinstance(graph_joint_definitions, list) or len(
        graph_joint_definitions
    ) != len(joint_names):
        raise ValueError("The assembly definition has the wrong joint graph.")
    for index, output_name in enumerate(component_names):
        if graph_component_definitions[index] != by_name[output_name].get("definition"):
            raise ValueError(
                f"The assembly graph component {output_name!r} does not match its "
                "returned definition."
            )
    for index, output_name in enumerate(joint_names):
        if graph_joint_definitions[index] != by_name[output_name].get("definition"):
            raise ValueError(
                f"The assembly graph joint {output_name!r} does not match its "
                "returned definition."
            )

    diagnostics_definition = diagnostics_item.get("definition")
    if (
        not isinstance(diagnostics_definition, dict)
        or diagnostics_definition.get("domain") != "assembly"
        or diagnostics_definition.get("operation") != "solve"
        or diagnostics_definition.get("output_type") != "solver_diagnostics"
        or diagnostics_definition.get("arguments") != [assembly_definition]
    ):
        raise ValueError(
            "The solver_diagnostics output does not solve the returned assembly graph."
        )
    diagnostics_properties = diagnostics_definition.get("properties")
    if not isinstance(diagnostics_properties, dict) or not isinstance(
        diagnostics_properties.get("require_solved"), bool
    ):
        raise ValueError(
            "The solver_diagnostics definition has no boolean require_solved policy."
        )
    diagnostics_assembly_data = diagnostics_item.get("assembly_data")
    if diagnostics_assembly_data != {"assembly_output": str(assembly_item["name"])}:
        raise ValueError("The solver_diagnostics output belongs to the wrong assembly.")

    references = {
        (str(item.get("document_uid") or ""), str(item.get("object_name") or "")): item
        for item in list(prepared.get("resolved_references") or [])
    }
    grounded_set: set[str] = set()
    component_placements: dict[str, dict[str, Any]] = {}
    component_sources: dict[str, dict[str, Any]] = {}
    component_metadata: dict[str, dict[str, Any]] = {}
    for item in components:
        name = str(item["name"])
        data = item.get("assembly_data")
        if not isinstance(data, dict):
            raise ValueError(f"Component output {name!r} has no assembly metadata.")
        if str(data.get("assembly_output") or "") != str(assembly_item["name"]):
            raise ValueError(
                f"Component output {name!r} belongs to the wrong assembly."
            )
        definition = item.get("definition")
        if (
            not isinstance(definition, dict)
            or definition.get("domain") != "assembly"
            or definition.get("operation") != "component"
            or definition.get("output_type") != "component_link"
        ):
            raise ValueError(f"Component output {name!r} has an invalid definition.")
        arguments = definition.get("arguments")
        properties = definition.get("properties")
        if (
            not isinstance(arguments, list)
            or len(arguments) != 1
            or not isinstance(properties, dict)
        ):
            raise ValueError(f"Component output {name!r} has a malformed definition.")
        source = data.get("source")
        if not isinstance(source, dict) or set(source) != {
            "document_uid",
            "object_name",
        }:
            raise ValueError(
                f"Component output {name!r} has an invalid source identity."
            )
        if source != arguments[0]:
            raise ValueError(
                f"Component output {name!r} source changed after source evaluation."
            )
        key = (str(source["document_uid"]), str(source["object_name"]))
        resolved = references.get(key)
        if resolved is None:
            raise ValueError(
                f"Component output {name!r} uses an unauthenticated source {key[1]!r}."
            )
        facts = data.get("source_facts")
        if not isinstance(facts, dict) or int(facts.get("solids") or 0) < 1:
            raise ValueError(
                f"Component output {name!r} source must contain at least one solid."
            )
        reported = dict(resolved.get("facts") or {})
        for field in ("solids", "faces", "edges", "vertices"):
            if int(facts.get(field, -1)) != int(reported.get(field, -2)):
                raise ValueError(
                    f"Component output {name!r} source topology disagrees with the "
                    f"host snapshot ({field})."
                )
        if str(data.get("source_type_id") or "") != str(
            resolved.get("type_id") or ""
        ) or str(data.get("source_kind") or "") != str(
            resolved.get("source_kind") or "shape"
        ):
            raise ValueError(
                f"Component output {name!r} source type metadata disagrees with "
                "the authenticated host snapshot."
            )
        if (
            not isinstance(properties.get("grounded"), bool)
            or bool(data.get("grounded")) is not properties["grounded"]
        ):
            raise ValueError(
                f"Component output {name!r} grounding metadata was altered."
            )
        declared_flexible = properties.get("flexible", False)
        if (
            not isinstance(declared_flexible, bool)
            or bool(data.get("flexible", False)) is not declared_flexible
        ):
            raise ValueError(
                f"Component output {name!r} flexible-subassembly metadata was altered."
            )
        if declared_flexible and bool(properties["grounded"]):
            raise ValueError(
                f"Component output {name!r} cannot be both flexible and grounded."
            )
        source_kind = str(resolved.get("source_kind") or "shape")
        if declared_flexible and source_kind != "assembly":
            raise ValueError(
                f"Component output {name!r} marked a non-Assembly source as flexible."
            )
        native_name = str(data.get("native_name") or "")
        native_type_id = str(data.get("native_type_id") or "")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", native_name):
            raise ValueError(
                f"Component output {name!r} has no native object identity."
            )
        hierarchy_descriptor = resolved.get("assembly_hierarchy")
        if hierarchy_descriptor is not None:
            descriptor, _node_by_id = _assembly_hierarchy_contract(
                resolved, context=f"Component output {name!r} source"
            )
            root_node = _node_by_id[str(descriptor["root_node_id"])]
            root_kind = str(root_node.get("kind") or "")
            expected_paths = [
                str(item["path"]) for item in list(descriptor["occurrence_paths"])
            ]
            hierarchy_digest = hashlib.sha256(
                json.dumps(
                    descriptor,
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest()
            expected_native_type = (
                "Assembly::AssemblyLink" if source_kind == "assembly" else "App::Link"
            )
            if (
                source_kind not in {"assembly", "part"}
                or root_kind != source_kind
                or native_type_id != expected_native_type
                or str(data.get("hierarchy_sha256") or "") != hierarchy_digest
                or int(data.get("occurrence_path_count", -1)) != len(expected_paths)
                or data.get("occurrence_paths") != expected_paths
            ):
                raise ValueError(
                    f"Component output {name!r} hierarchy metadata disagrees with "
                    "the authenticated host snapshot."
                )
            solved_occurrences = data.get("solved_occurrences")
            if not isinstance(solved_occurrences, list) or len(
                solved_occurrences
            ) != len(expected_paths):
                raise ValueError(
                    f"Component output {name!r} has incomplete stable-path solve evidence."
                )
            for path, occurrence_state in zip(
                expected_paths, solved_occurrences, strict=True
            ):
                if (
                    not isinstance(occurrence_state, dict)
                    or str(occurrence_state.get("occurrence_path") or "") != path
                ):
                    raise ValueError(
                        f"Component output {name!r} changed occurrence solve order."
                    )
                _descriptor, path_chain = _assembly_hierarchy_path(
                    resolved,
                    path,
                    context=f"Component output {name!r}",
                )
                occurrence, leaf = path_chain[-1]
                expected_leaf_type = (
                    "Assembly::AssemblyLink"
                    if str(occurrence.get("link_mode") or "") == "assembly_link"
                    else "App::Link"
                )
                expected_live = (
                    all(
                        str(parent_occurrence.get("link_mode") or "") == "assembly_link"
                        for parent_occurrence, _source in path_chain[:-1]
                    )
                    and source_kind == "assembly"
                )
                if (
                    str(occurrence_state.get("source_node_id") or "")
                    != str(leaf.get("node_id") or "")
                    or str(occurrence_state.get("source_kind") or "")
                    != str(leaf.get("kind") or "")
                    or str(occurrence_state.get("source_label") or "")
                    != str(leaf.get("label") or "")
                    or str(occurrence_state.get("native_type_id") or "")
                    != expected_leaf_type
                    or occurrence_state.get("live_occurrence") is not expected_live
                    or str(occurrence_state.get("native_target_mode") or "")
                    not in {
                        "component_root",
                        "prefixed_rigid_boundary",
                        "direct_exposed_occurrence",
                    }
                ):
                    raise ValueError(
                        f"Component output {name!r} occurrence {path!r} solve "
                        "evidence disagrees with its authenticated hierarchy."
                    )
                if expected_live:
                    _assembly_placement_fact(
                        occurrence_state.get("local_placement"),
                        f"Component output {name!r} occurrence {path!r} local placement",
                    )
                    _assembly_placement_fact(
                        occurrence_state.get("global_placement"),
                        f"Component output {name!r} occurrence {path!r} global placement",
                    )
                elif (
                    occurrence_state.get("local_placement") is not None
                    or occurrence_state.get("global_placement") is not None
                ):
                    raise ValueError(
                        f"Component output {name!r} occurrence {path!r} claimed a "
                        "live placement behind an App::Link boundary."
                    )
        else:
            if declared_flexible:
                raise ValueError(
                    f"Component output {name!r} is flexible without an authenticated hierarchy."
                )
            if (
                str(data.get("hierarchy_sha256") or "")
                or int(data.get("occurrence_path_count", -1)) != 0
                or data.get("occurrence_paths") != []
                or "solved_occurrences" in data
            ):
                raise ValueError(
                    f"Component output {name!r} reported an undeclared hierarchy."
                )
            if native_type_id != "App::Link":
                raise ValueError(
                    f"Component output {name!r} has the wrong native link type."
                )
        initial = _assembly_placement_fact(
            data.get("initial_placement"),
            f"Component output {name!r} initial placement",
        )
        declared_placement = properties.get("placement")
        if not isinstance(declared_placement, dict) or initial["position_mm"] != list(
            declared_placement.get("position") or []
        ):
            raise ValueError(
                f"Component output {name!r} initial placement disagrees with its "
                "definition."
            )
        solved = _assembly_placement_fact(
            data.get("solved_placement"),
            f"Component output {name!r} solved placement",
        )
        if (
            _finite_matrix(
                item.get("solved_placement_matrix"),
                f"Component output {name!r} publication placement",
            )
            != solved["matrix"]
        ):
            raise ValueError(
                f"Component output {name!r} has inconsistent solved placement data."
            )
        component_placements[name] = solved
        component_sources[name] = resolved
        component_metadata[name] = data
        if bool(data.get("grounded")):
            grounded_set.add(name)

    joint_records: dict[str, dict[str, Any]] = {}
    for item in joints:
        name = str(item["name"])
        data = item.get("assembly_data")
        if not isinstance(data, dict):
            raise ValueError(f"Joint output {name!r} has no assembly metadata.")
        if str(data.get("assembly_output") or "") != str(assembly_item["name"]):
            raise ValueError(f"Joint output {name!r} belongs to the wrong assembly.")
        definition = item.get("definition")
        if (
            not isinstance(definition, dict)
            or definition.get("domain") != "assembly"
            or definition.get("operation") != "joint"
            or definition.get("output_type") != "joint"
        ):
            raise ValueError(f"Joint output {name!r} has an invalid definition.")
        properties = definition.get("properties")
        if not isinstance(properties, dict):
            raise ValueError(f"Joint output {name!r} has no definition properties.")
        kind = str(properties.get("kind") or "")
        native_types = {
            "fixed": "Fixed",
            "revolute": "Revolute",
            "cylindrical": "Cylindrical",
            "slider": "Slider",
            "ball": "Ball",
            "distance": "Distance",
            "parallel": "Parallel",
            "perpendicular": "Perpendicular",
            "angle": "Angle",
            "rack_pinion": "RackPinion",
            "screw": "Screw",
            "gears": "Gears",
            "belt": "Belt",
        }
        native_type = native_types.get(kind)
        if native_type is None:
            raise ValueError(f"Joint output {name!r} has unsupported kind {kind!r}.")
        if str(data.get("kind") or "") != kind:
            raise ValueError(
                f"Joint output {name!r} changed kind after source evaluation."
            )
        if str(data.get("native_type") or "") != native_type:
            raise ValueError(
                f"Joint output {name!r} reports the wrong native joint type."
            )
        parameters = properties.get("parameters")
        if not isinstance(parameters, dict) or data.get("parameters") != parameters:
            raise ValueError(f"Joint output {name!r} parameter metadata was altered.")
        parameter_names = {
            "distance": {"distance_mm"},
            "angle": {"angle_degrees"},
            "rack_pinion": {"pitch_radius_mm"},
            "screw": {"thread_pitch_mm"},
            "gears": {"radius1_mm", "radius2_mm"},
            "belt": {"radius1_mm", "radius2_mm"},
        }.get(kind, set())
        if set(parameters) != parameter_names:
            raise ValueError(
                f"Joint output {name!r} parameters must be exactly "
                f"{sorted(parameter_names)} for {kind}."
            )
        for parameter_name, value in parameters.items():
            if isinstance(value, bool) or not math.isfinite(float(value)):
                raise ValueError(
                    f"Joint output {name!r} parameter {parameter_name!r} must be finite."
                )
            number = float(value)
            if parameter_name in {"radius1_mm", "radius2_mm"} and number <= 0.0:
                raise ValueError(
                    f"Joint output {name!r} physical radii must be greater than zero."
                )
            if (
                parameter_name in {"pitch_radius_mm", "thread_pitch_mm"}
                and abs(number) <= 1.0e-12
            ):
                raise ValueError(
                    f"Joint output {name!r} signed motion parameter must be non-zero."
                )
        length_limits = _assembly_limits(
            properties.get("length_limits_mm"),
            f"Joint output {name!r} length_limits_mm",
        )
        angle_limits = _assembly_limits(
            properties.get("angle_limits_degrees"),
            f"Joint output {name!r} angle_limits_degrees",
        )
        if data.get("length_limits_mm") != length_limits:
            raise ValueError(f"Joint output {name!r} length limits were altered.")
        if data.get("angle_limits_degrees") != angle_limits:
            raise ValueError(f"Joint output {name!r} angle limits were altered.")
        if length_limits is not None and kind not in {"slider", "cylindrical"}:
            raise ValueError(f"Joint output {name!r} has inapplicable length limits.")
        if angle_limits is not None and kind not in {"revolute", "cylindrical"}:
            raise ValueError(f"Joint output {name!r} has inapplicable angle limits.")
        suppressed = properties.get("suppressed")
        if (
            not isinstance(suppressed, bool)
            or bool(data.get("suppressed")) != suppressed
        ):
            raise ValueError(f"Joint output {name!r} suppression metadata was altered.")
        compatibility = data.get("compatibility")
        if (
            not isinstance(compatibility, dict)
            or compatibility.get("ok") is not True
            or str(compatibility.get("joint_type") or "") != kind
        ):
            raise ValueError(
                f"Joint output {name!r} has invalid compatibility metadata."
            )
        readback = data.get("native_readback")
        if not isinstance(readback, dict):
            raise ValueError(f"Joint output {name!r} has no native property readback.")
        if (
            str(readback.get("native_type") or "") != native_type
            or readback.get("suppressed") is not suppressed
            or readback.get("length_limits_mm") != length_limits
            or readback.get("angle_limits_degrees") != angle_limits
        ):
            raise ValueError(
                f"Joint output {name!r} native property readback disagrees."
            )
        for parameter_name, value in parameters.items():
            try:
                readback_value = float(readback.get(parameter_name))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Joint output {name!r} native readback for "
                    f"{parameter_name!r} is not a finite number."
                ) from exc
            if not math.isfinite(readback_value) or readback_value != float(value):
                raise ValueError(
                    f"Joint output {name!r} native readback for "
                    f"{parameter_name!r} disagrees."
                )
        connectors = data.get("connectors")
        if not isinstance(connectors, list) or len(connectors) != 2:
            raise ValueError(
                f"Joint output {name!r} must contain two connector frames."
            )
        if connectors != item.get("connector_frames"):
            raise ValueError(
                f"Joint output {name!r} connector metadata is inconsistent."
            )
        definition_connectors = definition.get("arguments")
        if (
            not isinstance(definition_connectors, list)
            or len(definition_connectors) != 2
        ):
            raise ValueError(
                f"Joint output {name!r} definition must contain two connectors."
            )
        for index, connector in enumerate(connectors, start=1):
            if not isinstance(connector, dict):
                raise ValueError(
                    f"Joint output {name!r} connector {index} must be an object."
                )
            component_name = str(connector.get("component_output") or "")
            if component_name not in component_names:
                raise ValueError(
                    f"Joint output {name!r} connector {index} refers to unknown "
                    f"component {component_name!r}."
                )
            connector_definition = definition_connectors[index - 1]
            if (
                not isinstance(connector_definition, dict)
                or connector_definition.get("domain") != "assembly"
                or connector_definition.get("operation") != "connector"
                or connector_definition.get("output_type") != "connector"
            ):
                raise ValueError(
                    f"Joint output {name!r} connector {index} has an invalid definition."
                )
            if connector_definition.get("arguments") != [
                by_name[component_name].get("definition")
            ]:
                raise ValueError(
                    f"Joint output {name!r} connector {index} does not consume "
                    f"component output {component_name!r}."
                )
            connector_properties = connector_definition.get("properties")
            if not isinstance(connector_properties, dict):
                raise ValueError(
                    f"Joint output {name!r} connector {index} has no properties."
                )
            selection = connector_properties.get("selection")
            if connector.get("selection") != selection or not isinstance(
                selection, dict
            ):
                raise ValueError(
                    f"Joint output {name!r} connector {index} selection was altered."
                )
            mode = str(selection.get("type") or "")
            source_metadata = component_sources[component_name]
            occurrence_path_value = connector_properties.get("occurrence_path")
            if occurrence_path_value is not None and (
                not isinstance(occurrence_path_value, str) or not occurrence_path_value
            ):
                raise ValueError(
                    f"Joint output {name!r} connector {index} has an invalid "
                    "occurrence_path declaration."
                )
            occurrence_path = str(occurrence_path_value or "")
            hierarchy_path_chain = None
            if occurrence_path:
                _descriptor, hierarchy_path_chain = _assembly_hierarchy_path(
                    source_metadata,
                    occurrence_path,
                    context=f"Joint output {name!r} connector {index}",
                )
                source_metadata = _assembly_hierarchy_leaf_metadata(
                    hierarchy_path_chain[-1][1]
                )
            elif bool(component_metadata[component_name].get("flexible")):
                raise ValueError(
                    f"Joint output {name!r} connector {index} targets a flexible "
                    "subassembly without one stable internal occurrence_path."
                )
            if connector.get("occurrence_path") != (
                occurrence_path if occurrence_path else None
            ):
                raise ValueError(
                    f"Joint output {name!r} connector {index} occurrence path was altered."
                )
            if mode == "component_origin":
                if selection != {"type": "component_origin"}:
                    raise ValueError(
                        f"Joint output {name!r} connector {index} has a malformed "
                        "component-origin selection."
                    )
                if source_metadata.get("requires_semantic_interfaces"):
                    raise ValueError(
                        f"Joint output {name!r} connector {index} bypassed a required "
                        "published interface."
                    )
                expected_element = ""
                expected_geometry_type = "component_origin"
            elif mode == "exact_subelement":
                expected_element = str(selection.get("subelement") or "")
                match = re.fullmatch(
                    r"(Face|Edge|Vertex)([1-9][0-9]*)", expected_element
                )
                if match is None:
                    raise ValueError(
                        f"Joint output {name!r} connector {index} has an invalid exact "
                        "subelement."
                    )
                if source_metadata.get("transient_topology"):
                    raise ValueError(
                        f"Joint output {name!r} connector {index} uses transient topology "
                        "instead of a semantic interface."
                    )
                count_name = {
                    "Face": "faces",
                    "Edge": "edges",
                    "Vertex": "vertices",
                }[match.group(1)]
                available = int(
                    dict(source_metadata.get("facts") or {}).get(count_name, 0)
                )
                if int(match.group(2)) > available:
                    raise ValueError(
                        f"Joint output {name!r} connector {index} selects "
                        f"{expected_element}, but the authenticated source has only "
                        f"{available} {count_name}."
                    )
                expected_geometry_type = str(connector.get("geometry_type") or "")
                if not expected_geometry_type:
                    raise ValueError(
                        f"Joint output {name!r} connector {index} has no resolved "
                        "geometry type."
                    )
            elif mode == "published_interface":
                interface_name = str(selection.get("interface_name") or "")
                interface = dict(
                    dict(source_metadata.get("published_interfaces") or {}).get(
                        interface_name
                    )
                    or {}
                )
                subelements = list(interface.get("subelements") or [])
                geometry = list(interface.get("geometry") or [])
                if not interface or len(subelements) > 1 or len(geometry) > 1:
                    raise ValueError(
                        f"Joint output {name!r} connector {index} does not resolve one "
                        "authenticated published interface."
                    )
                expected_element = str(subelements[0]) if subelements else ""
                expected_geometry_type = str(
                    (geometry[0] if geometry else {}).get("geometry_type")
                    or ("component_origin" if not expected_element else "")
                )
                expected_semantic = {
                    "type": "published_interface",
                    "interface_name": interface_name,
                    "model_id": str(interface.get("model_id") or ""),
                    "publication_name": str(interface.get("publication_name") or ""),
                    "output_key": str(interface.get("output_key") or ""),
                }
                if connector.get("semantic_selection") != expected_semantic:
                    raise ValueError(
                        f"Joint output {name!r} connector {index} lost its "
                        "authenticated semantic identity."
                    )
            else:
                raise ValueError(
                    f"Joint output {name!r} connector {index} uses unsupported "
                    f"selection type {mode!r}."
                )
            if mode == "published_interface":
                semantic = connector.get("semantic_selection")
                if (
                    not isinstance(semantic, dict)
                    or semantic.get("type") != "published_interface"
                    or semantic.get("interface_name") != selection.get("interface_name")
                ):
                    raise ValueError(
                        f"Joint output {name!r} connector {index} lost its semantic identity."
                    )
            if str(connector.get("element") or "") != expected_element:
                raise ValueError(
                    f"Joint output {name!r} connector {index} resolved the wrong element."
                )
            requested_anchor = connector_properties.get("anchor")
            if requested_anchor is not None and mode != "exact_subelement":
                raise ValueError(
                    f"Joint output {name!r} connector {index} applies an anchor to "
                    "a non-exact selection."
                )
            expected_anchor = str(requested_anchor or expected_element)
            if str(connector.get("anchor") or "") != expected_anchor:
                raise ValueError(
                    f"Joint output {name!r} connector {index} resolved the wrong anchor."
                )
            if hierarchy_path_chain is not None:
                (
                    expected_native_component,
                    expected_native_subelements,
                    expected_target_mode,
                ) = _assembly_expected_native_reference(
                    component_metadata[component_name],
                    hierarchy_path_chain,
                    connector.get("native_hierarchy_chain"),
                    stable_path=occurrence_path,
                    element=expected_element,
                    anchor=expected_anchor,
                    context=f"Joint output {name!r} connector {index}",
                )
            else:
                expected_native_component = str(
                    component_metadata[component_name].get("native_name") or ""
                )
                expected_native_subelements = [expected_element, expected_anchor]
                expected_target_mode = "component_root"
                if connector.get("native_hierarchy_chain") != []:
                    raise ValueError(
                        f"Joint output {name!r} connector {index} reported an "
                        "undeclared native hierarchy."
                    )
            if str(connector.get("native_target_mode") or "") != expected_target_mode:
                raise ValueError(
                    f"Joint output {name!r} connector {index} changed native target mode."
                )
            native_reference = connector.get("native_reference")
            if (
                not isinstance(native_reference, dict)
                or str(native_reference.get("component") or "")
                != expected_native_component
                or list(native_reference.get("subelements") or [])
                != expected_native_subelements
            ):
                raise ValueError(
                    f"Joint output {name!r} connector {index} native reference disagrees."
                )
            for frame_name in ("offset", "local_frame", "global_frame"):
                frame = _assembly_placement_fact(
                    connector.get(frame_name),
                    f"Joint output {name!r} connector {index} {frame_name}",
                )
                if frame_name == "offset":
                    declared_offset = connector_properties.get("offset")
                    if not isinstance(declared_offset, dict) or frame[
                        "position_mm"
                    ] != list(declared_offset.get("position") or []):
                        raise ValueError(
                            f"Joint output {name!r} connector {index} offset "
                            "disagrees with its definition."
                        )
            if str(connector.get("geometry_type") or "") != expected_geometry_type:
                raise ValueError(
                    f"Joint output {name!r} connector {index} reports the wrong "
                    "geometry type."
                )

        expected_compatibility = _assembly_compatibility(kind, connectors)
        if compatibility != expected_compatibility:
            raise ValueError(
                f"Joint output {name!r} compatibility metadata was altered."
            )
        joint_records[name] = data

    exploded_view_summaries = _validate_assembly_exploded_views(
        prepared,
        exploded_views,
        assembly_item=assembly_item,
        assembly_definition=assembly_definition,
        by_name=by_name,
        component_names=component_names,
        component_placements=component_placements,
        component_sources=component_sources,
    )

    simulation_summary = None
    if simulations:
        simulation_item = simulations[0]
        simulation_name = str(simulation_item["name"])
        simulation_definition = simulation_item.get("definition")
        if (
            not isinstance(simulation_definition, dict)
            or simulation_definition.get("domain") != "assembly"
            or simulation_definition.get("operation") != "simulation"
            or simulation_definition.get("output_type") != "simulation"
            or simulation_definition.get("arguments") != [assembly_definition]
        ):
            raise ValueError(
                f"Simulation output {simulation_name!r} has an invalid definition."
            )
        simulation_properties = simulation_definition.get("properties")
        required_simulation_properties = {
            "motions",
            "start_time_s",
            "end_time_s",
            "time_step_s",
            "error_tolerance",
            "frames_per_second",
            "estimated_frame_limit",
        }
        if (
            not isinstance(simulation_properties, dict)
            or not required_simulation_properties <= set(simulation_properties)
            or set(simulation_properties) - required_simulation_properties
            not in (set(), {"label"})
        ):
            raise ValueError(
                f"Simulation output {simulation_name!r} has malformed properties."
            )
        graph_motion_names = [
            str(item) for item in list(assembly_data.get("motion_outputs") or [])
        ]
        motion_definitions = simulation_properties.get("motions")
        if not isinstance(motion_definitions, list) or motion_definitions != [
            by_name[name].get("definition") for name in graph_motion_names
        ]:
            raise ValueError(
                f"Simulation output {simulation_name!r} does not consume the exact "
                "returned motion graph in declared order."
            )
        try:
            start_time = float(simulation_properties["start_time_s"])
            end_time = float(simulation_properties["end_time_s"])
            time_step = float(simulation_properties["time_step_s"])
            error_tolerance = float(simulation_properties["error_tolerance"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Simulation output {simulation_name!r} has nonnumeric parameters."
            ) from exc
        numeric_parameters = (start_time, end_time, time_step, error_tolerance)
        if (
            any(not math.isfinite(value) for value in numeric_parameters)
            or end_time <= start_time
            or time_step <= 0.0
            or not 1.0e-12 <= error_tolerance <= 1.0
        ):
            raise ValueError(
                f"Simulation output {simulation_name!r} has invalid time or tolerance "
                "parameters."
            )
        frames_per_second = simulation_properties["frames_per_second"]
        estimated_frame_limit = simulation_properties["estimated_frame_limit"]
        if (
            type(frames_per_second) is not int
            or not 1 <= frames_per_second <= 240
            or type(estimated_frame_limit) is not int
            or estimated_frame_limit
            != math.ceil((end_time - start_time) / time_step) + 2
            or not 2 <= estimated_frame_limit <= 10_000
            or estimated_frame_limit * len(components) > 100_000
        ):
            raise ValueError(
                f"Simulation output {simulation_name!r} changed its bounded frame "
                "schedule."
            )

        motion_records: list[dict[str, Any]] = []
        seen_drives: set[tuple[str, str]] = set()
        for motion_name in graph_motion_names:
            item = by_name[motion_name]
            definition = item.get("definition")
            data = item.get("assembly_data")
            if (
                not isinstance(definition, dict)
                or definition.get("domain") != "assembly"
                or definition.get("operation") != "motion"
                or definition.get("output_type") != "motion"
                or not isinstance(data, dict)
            ):
                raise ValueError(f"Motion output {motion_name!r} is malformed.")
            arguments = definition.get("arguments")
            properties = definition.get("properties")
            if (
                not isinstance(arguments, list)
                or len(arguments) != 1
                or not isinstance(properties, dict)
                or not {"formula", "motion_type"} <= set(properties)
                or set(properties) - {"formula", "motion_type"}
                not in (set(), {"label"})
            ):
                raise ValueError(
                    f"Motion output {motion_name!r} has a malformed definition."
                )
            joint_name = str(data.get("joint_output") or "")
            if joint_name not in joint_records or arguments != [
                by_name[joint_name].get("definition")
            ]:
                raise ValueError(
                    f"Motion output {motion_name!r} does not drive its declared "
                    "returned joint."
                )
            joint_type = str(joint_records[joint_name]["kind"])
            motion_type = str(properties.get("motion_type") or "")
            allowed_motion_types = {
                "revolute": {"angular"},
                "slider": {"linear"},
                "cylindrical": {"angular", "linear"},
            }.get(joint_type, set())
            if motion_type not in allowed_motion_types or bool(
                joint_records[joint_name]["suppressed"]
            ):
                raise ValueError(
                    f"Motion output {motion_name!r} cannot drive the declared "
                    f"{joint_type!r} joint."
                )
            drive = (joint_name, motion_type)
            if drive in seen_drives:
                raise ValueError(
                    f"Motion output {motion_name!r} duplicates the {motion_type} "
                    f"drive on joint {joint_name!r}."
                )
            seen_drives.add(drive)
            formula = _assembly_motion_formula(
                properties.get("formula"), f"Motion output {motion_name!r} formula"
            )
            record = {
                "motion_output": motion_name,
                "joint_output": joint_name,
                "joint_type": joint_type,
                "motion_type": motion_type,
                "native_motion_type": (
                    "Angular" if motion_type == "angular" else "Linear"
                ),
                "formula": formula,
            }
            expected_motion_data = {
                "assembly_output": str(assembly_item["name"]),
                "simulation_output": simulation_name,
                **record,
            }
            if data != expected_motion_data:
                raise ValueError(
                    f"Motion output {motion_name!r} metadata was altered after native "
                    "execution."
                )
            motion_records.append(record)

        context = f"Simulation output {simulation_name!r} trace"
        trace_path = _staged_artifact_path(
            prepared,
            simulation_item.get("artifact_path"),
            context=context,
            maximum_bytes=_MAX_ASSEMBLY_SIMULATION_TRACE_BYTES,
        )
        artifact_bytes = trace_path.stat().st_size
        artifact_digest = _sha256_file(trace_path)
        if (
            simulation_item.get("artifact_kind") != "assembly_simulation_json"
            or simulation_item.get("artifact_schema")
            != _ASSEMBLY_SIMULATION_TRACE_SCHEMA
            or simulation_item.get("artifact_sha256") != artifact_digest
            or simulation_item.get("artifact_bytes") != artifact_bytes
        ):
            raise ValueError(
                f"Simulation output {simulation_name!r} trace identity changed."
            )
        try:
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{context} is not valid UTF-8 JSON.") from exc
        if not isinstance(trace, dict) or set(trace) != {
            "schema",
            "assembly_output",
            "simulation_output",
            "component_outputs",
            "motion_outputs",
            "parameters",
            "motion_observations",
            "frames",
        }:
            raise ValueError(f"{context} has the wrong schema fields.")
        parameters = {
            "start_time_s": start_time,
            "end_time_s": end_time,
            "time_step_s": time_step,
            "error_tolerance": error_tolerance,
            "frames_per_second": frames_per_second,
        }
        if (
            trace.get("schema") != _ASSEMBLY_SIMULATION_TRACE_SCHEMA
            or trace.get("assembly_output") != str(assembly_item["name"])
            or trace.get("simulation_output") != simulation_name
            or trace.get("component_outputs") != component_names
            or trace.get("motion_outputs") != graph_motion_names
            or trace.get("parameters") != parameters
        ):
            raise ValueError(f"{context} does not match the declared graph.")
        raw_frames = trace.get("frames")
        if (
            not isinstance(raw_frames, list)
            or not 2 <= len(raw_frames) <= estimated_frame_limit
            or len(raw_frames) * len(component_names) > 100_000
        ):
            raise ValueError(f"{context} has an invalid frame or pose count.")
        frames: list[dict[str, Any]] = []
        for frame_index, raw_frame in enumerate(raw_frames):
            if not isinstance(raw_frame, dict) or set(raw_frame) != {
                "frame_index",
                "frame_kind",
                "nominal_time_s",
                "component_placements",
            }:
                raise ValueError(f"{context} frame {frame_index} is malformed.")
            expected_kind = "input" if frame_index == 0 else "solver_output"
            expected_time = (
                None
                if frame_index == 0
                else min(end_time, start_time + (frame_index - 1) * time_step)
            )
            placements = raw_frame.get("component_placements")
            if (
                raw_frame.get("frame_index") != frame_index
                or raw_frame.get("frame_kind") != expected_kind
                or raw_frame.get("nominal_time_s") != expected_time
                or not isinstance(placements, dict)
                or set(placements) != set(component_names)
            ):
                raise ValueError(
                    f"{context} frame {frame_index} changed its schedule or components."
                )
            frames.append(
                {
                    **raw_frame,
                    "component_placements": {
                        name: _assembly_compact_placement(
                            placements[name],
                            f"{context} frame {frame_index} component {name!r}",
                        )
                        for name in component_names
                    },
                }
            )
        observations = _assembly_motion_observations(
            frames, motion_records, joint_records
        )
        if trace.get("motion_observations") != observations:
            raise ValueError(
                f"{context} motion observations do not match its component poses."
            )
        for observation in observations:
            change = (
                float(observation["maximum_relative_rotation_degrees"])
                if observation["motion_type"] == "angular"
                else float(observation["maximum_relative_translation_mm"])
            )
            tolerance = 1.0e-7 if observation["motion_type"] == "angular" else 1.0e-8
            if observation["time_dependent"] and change <= tolerance:
                raise ValueError(
                    f"Motion output {observation['motion_output']!r} uses time but "
                    "has no measurable authenticated movement."
                )
        simulation_summary = {
            "simulation_output": simulation_name,
            "motion_outputs": graph_motion_names,
            "parameters": parameters,
            "native_code": 0,
            "frame_count": len(frames),
            "pose_count": len(frames) * len(component_names),
            "motion_observations": observations,
            "artifact_schema": _ASSEMBLY_SIMULATION_TRACE_SCHEMA,
            "artifact_sha256": artifact_digest,
            "artifact_bytes": artifact_bytes,
        }
        if (
            simulation_item.get("frame_count") != len(frames)
            or simulation_item.get("pose_count") != len(frames) * len(component_names)
            or simulation_item.get("assembly_data")
            != {"assembly_output": str(assembly_item["name"]), **simulation_summary}
        ):
            raise ValueError(
                f"Simulation output {simulation_name!r} summary is inconsistent."
            )
        preview_indices = sorted({0, len(frames) // 2, len(frames) - 1})
        simulation_item["simulation_trace_preview"] = [
            frames[index] for index in preview_indices
        ]

    diagnostics = diagnostics_item.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError("The solver_diagnostics output has no native diagnostics.")
    try:
        solver_code = int(diagnostics.get("solver_code"))
    except (TypeError, ValueError) as exc:
        raise ValueError("The Assembly diagnostics solver code is invalid.") from exc
    if solver_code != int(validation.get("solver_code", -998)):
        raise ValueError(
            "The Assembly solver code is inconsistent across worker outputs."
        )
    if int(diagnostics.get("component_count", -1)) != len(components):
        raise ValueError("The Assembly diagnostics component count is inconsistent.")
    if int(diagnostics.get("joint_count", -1)) != len(joints):
        raise ValueError("The Assembly diagnostics joint count is inconsistent.")
    grounded = [name for name in component_names if name in grounded_set]
    if list(diagnostics.get("grounded_components") or []) != grounded:
        raise ValueError(
            "The Assembly diagnostics grounded-component list is inconsistent."
        )
    if list(diagnostics.get("joint_outputs") or []) != joint_names:
        raise ValueError("The Assembly diagnostics joint-output list is inconsistent.")
    if diagnostics.get("component_placements") != component_placements:
        raise ValueError(
            "The Assembly diagnostics solved placements do not match component outputs."
        )
    expected_occurrence_counts = {
        name: int(data.get("occurrence_path_count", 0))
        for name, data in component_metadata.items()
        if str(data.get("hierarchy_sha256") or "")
    }
    if diagnostics.get("component_occurrence_counts") != expected_occurrence_counts:
        raise ValueError(
            "The Assembly diagnostics stable-occurrence counts do not match "
            "component outputs."
        )
    require_solved = diagnostics_properties["require_solved"]
    if diagnostics.get("require_solved") is not require_solved:
        raise ValueError(
            "The Assembly diagnostics changed the declared require_solved policy."
        )
    native = diagnostics.get("native")
    if not isinstance(native, dict):
        raise ValueError("The Assembly diagnostics have no native solver report.")
    conflicts = any(
        bool(native.get(name))
        for name in (
            "has_conflicts",
            "has_redundancies",
            "has_partial_redundancies",
            "has_malformed_constraints",
        )
    )
    dependency_issues = diagnostics.get("joint_dependency_issues")
    if not isinstance(dependency_issues, list):
        raise ValueError("The Assembly diagnostics have no joint-dependency report.")
    expected_dependency_issues = _assembly_joint_dependency_issues(joint_records)
    if dependency_issues != expected_dependency_issues:
        raise ValueError(
            "The Assembly joint-dependency report does not match the returned joint graph."
        )
    if dependency_issues != list(validation.get("joint_dependency_issues") or []):
        raise ValueError(
            "The Assembly joint-dependency report is inconsistent across worker outputs."
        )
    if simulation_summary is not None:
        if diagnostics.get("simulation") != simulation_summary:
            raise ValueError(
                "The Assembly diagnostics simulation summary is inconsistent."
            )
    elif "simulation" in diagnostics or "simulation" in validation:
        raise ValueError("The Assembly diagnostics report an undeclared simulation.")
    if exploded_view_summaries:
        if (
            diagnostics.get("exploded_views") != exploded_view_summaries
            or validation.get("exploded_views") != exploded_view_summaries
        ):
            raise ValueError(
                "The Assembly exploded-view summaries are inconsistent across "
                "worker outputs."
            )
    elif "exploded_views" in diagnostics or "exploded_views" in validation:
        raise ValueError("The Assembly diagnostics report undeclared exploded views.")
    expected_status = (
        "solved"
        if solver_code == 0 and not conflicts and not dependency_issues
        else "failed"
    )
    if diagnostics.get("status") != expected_status:
        raise ValueError(
            "The Assembly diagnostics status does not match the native solver result."
        )
    solver_verdicts = {
        0: "solved",
        -1: "solver_error",
        -2: "redundant_constraints",
        -3: "conflicting_constraints",
        -4: "over_constrained",
        -5: "malformed_constraints",
        -6: "no_grounded_component",
    }
    expected_verdict = solver_verdicts.get(solver_code, f"unknown_status_{solver_code}")
    if diagnostics.get("solver_verdict") != expected_verdict:
        raise ValueError(
            "The Assembly diagnostics verdict does not match the native solver code."
        )
    if require_solved and (
        solver_code != 0
        or conflicts
        or dependency_issues
        or diagnostics.get("status") != "solved"
    ):
        raise ValueError(
            "The Assembly worker claimed a required solution without a clean native "
            "solver result."
        )
    expected_validation = {
        "status": expected_status,
        "solver_code": solver_code,
        "solver_verdict": expected_verdict,
        "component_count": len(components),
        "joint_count": len(joints),
        "grounded_components": grounded,
        "native_diagnostics": native,
        "component_placements": component_placements,
        "component_occurrence_counts": expected_occurrence_counts,
        "joint_dependency_issues": expected_dependency_issues,
    }
    if simulation_summary is not None:
        expected_validation["simulation"] = simulation_summary
    if exploded_view_summaries:
        expected_validation["exploded_views"] = exploded_view_summaries
    for field, expected_value in expected_validation.items():
        if validation.get(field) != expected_value:
            raise ValueError(
                f"The Assembly worker validation field {field!r} is inconsistent."
            )
    for item in outputs:
        data = item.get("assembly_data")
        _validate_definition_value(
            data,
            prepared,
            f"outputs.{item['name']}.assembly_data",
        )
        encoded = json.dumps(
            data,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if len(encoded) > _STRUCTURED_DEFINITION_LIMIT:
            raise ValueError(f"Output {item['name']!r} assembly metadata is too large.")
    return dict(validation)


def _exact_mapping(
    value: Any,
    *,
    path: str,
    keys: set[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be an object.")
    if set(value) != keys:
        missing = sorted(keys - set(value))
        unexpected = sorted(set(value) - keys)
        raise ValueError(
            f"{path} has the wrong fields (missing={missing}, unexpected={unexpected})."
        )
    return dict(value)


def _sketcher_payload(
    value: Any,
    *,
    path: str,
    operation: str | None = None,
    output_type: str | None = None,
) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
    payload = _exact_mapping(
        value,
        path=path,
        keys={"domain", "operation", "output_type", "arguments", "properties"},
    )
    if payload["domain"] != "sketcher":
        raise ValueError(f"{path} belongs to a different XScript domain.")
    if operation is not None and payload["operation"] != operation:
        raise ValueError(f"{path} must come from api.{operation}.")
    if output_type is not None and payload["output_type"] != output_type:
        raise ValueError(f"{path} must have output type {output_type!r}.")
    arguments = payload["arguments"]
    properties = payload["properties"]
    if not isinstance(arguments, list) or not isinstance(properties, dict):
        raise ValueError(f"{path} arguments/properties are malformed.")
    return payload, list(arguments), dict(properties)


def _validate_sketcher_diagnostic_reference(
    value: Any,
    *,
    path: str,
    geometry_readback: list[dict[str, Any]],
    allowed_points: set[str],
) -> tuple[str, str]:
    data = _exact_mapping(
        value,
        path=path,
        keys={
            "graph_id",
            "name",
            "source_index",
            "operation",
            "construction",
            "point",
        },
    )
    source_index = data["source_index"]
    if type(source_index) is not int or not 0 <= source_index < len(geometry_readback):
        raise ValueError(f"{path}.source_index is outside the source geometry graph.")
    expected = geometry_readback[source_index]
    for field in ("graph_id", "name", "operation", "construction"):
        if data[field] != expected[field]:
            raise ValueError(f"{path}.{field} differs from the source geometry graph.")
    point = data["point"]
    if point not in allowed_points:
        raise ValueError(f"{path}.point is invalid for this diagnostic.")
    return str(data["graph_id"]), str(point)


def _validate_sketcher_underconstraint_guidance(
    value: Any,
    *,
    degrees_of_freedom: int,
    geometry_readback: list[dict[str, Any]],
) -> None:
    guidance = _exact_mapping(
        value,
        path="sketch_validation.underconstraint_guidance",
        keys={
            "status",
            "canonical_operation",
            "automatic_application",
            "workflow",
            "position_tolerance_mm",
            "angle_tolerance_degrees",
            "equality_tolerance_mm",
            "equality_geometry_limit",
            "detected_counts",
            "filtered_existing_count",
            "skipped_detectors",
            "suggestions",
            "suggestions_truncated",
            "native_error",
        },
    )
    if guidance["canonical_operation"] != "api.constraint":
        raise ValueError(
            "Sketcher guidance must use the canonical constraint operation."
        )
    if guidance["automatic_application"] is not False:
        raise ValueError("Sketcher heuristic constraints must never be auto-applied.")
    if guidance["workflow"] != [
        "connectivity",
        "orientation",
        "equality",
        "dimensions",
    ]:
        raise ValueError("Sketcher underconstraint workflow is inconsistent.")
    numeric_contract = {
        "position_tolerance_mm": _SKETCHER_SUGGESTION_POSITION_TOLERANCE_MM,
        "angle_tolerance_degrees": _SKETCHER_SUGGESTION_ANGLE_TOLERANCE_DEGREES,
        "equality_tolerance_mm": _SKETCHER_SUGGESTION_EQUALITY_TOLERANCE_MM,
    }
    for field, expected in numeric_contract.items():
        if guidance[field] != expected:
            raise ValueError(f"Sketcher guidance {field} is inconsistent.")
    if (
        guidance["equality_geometry_limit"]
        != _SKETCHER_MAX_EQUALITY_DIAGNOSTIC_GEOMETRY
    ):
        raise ValueError("Sketcher equality diagnostic limit is inconsistent.")
    counts = _exact_mapping(
        guidance["detected_counts"],
        path="sketch_validation.underconstraint_guidance.detected_counts",
        keys={"connectivity", "orientation", "equality"},
    )
    if any(type(counts[field]) is not int or counts[field] < 0 for field in counts):
        raise ValueError("Sketcher detected suggestion counts are invalid.")
    if (
        type(guidance["filtered_existing_count"]) is not int
        or guidance["filtered_existing_count"] < 0
    ):
        raise ValueError("Sketcher filtered suggestion count is invalid.")
    skipped = guidance["skipped_detectors"]
    if (
        not isinstance(skipped, list)
        or len(skipped) != len(set(skipped))
        or any(item != "equality_size_guard" for item in skipped)
    ):
        raise ValueError("Sketcher skipped-detector diagnostics are invalid.")
    suggestions = guidance["suggestions"]
    if (
        not isinstance(suggestions, list)
        or len(suggestions) > _SKETCHER_MAX_UNDERCONSTRAINT_SUGGESTIONS
    ):
        raise ValueError("Sketcher underconstraint suggestions are not bounded.")
    if not isinstance(guidance["suggestions_truncated"], bool):
        raise ValueError("Sketcher suggestion truncation metadata is invalid.")
    if (
        not isinstance(guidance["native_error"], str)
        or len(guidance["native_error"]) > 512
    ):
        raise ValueError("Sketcher suggestion native error is invalid.")

    forms = {
        ("coincident", "connectivity", "native_missing_endpoint_coincidence"): (
            2,
            {"start", "end"},
        ),
        ("horizontal", "orientation", "native_near_horizontal"): (1, {"none"}),
        ("vertical", "orientation", "native_near_vertical"): (1, {"none"}),
        ("equal", "equality", "native_equal_line_length"): (2, {"none"}),
        ("equal", "equality", "native_equal_radius"): (2, {"none"}),
    }
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    category_counts = {"connectivity": 0, "orientation": 0, "equality": 0}
    for index, raw in enumerate(suggestions):
        suggestion = _exact_mapping(
            raw,
            path=f"sketch_validation.underconstraint_guidance.suggestions[{index}]",
            keys={"kind", "category", "reason", "intent_required", "entities"},
        )
        form = (
            str(suggestion["kind"]),
            str(suggestion["category"]),
            str(suggestion["reason"]),
        )
        contract = forms.get(form)
        if contract is None or suggestion["intent_required"] is not True:
            raise ValueError("Sketcher underconstraint suggestion form is invalid.")
        expected_count, allowed_points = contract
        entities = suggestion["entities"]
        if not isinstance(entities, list) or len(entities) != expected_count:
            raise ValueError("Sketcher underconstraint suggestion arity is invalid.")
        entity_keys = tuple(
            _validate_sketcher_diagnostic_reference(
                entity,
                path=(
                    "sketch_validation.underconstraint_guidance."
                    f"suggestions[{index}].entities[{entity_index}]"
                ),
                geometry_readback=geometry_readback,
                allowed_points=allowed_points,
            )
            for entity_index, entity in enumerate(entities)
        )
        if suggestion["kind"] in {"coincident", "equal"}:
            entity_keys = tuple(sorted(entity_keys))
        key = (str(suggestion["kind"]), entity_keys)
        if key in seen:
            raise ValueError("Sketcher underconstraint suggestion is duplicated.")
        seen.add(key)
        category_counts[str(suggestion["category"])] += 1
        operations = [
            str(entity["operation"]) for entity in entities if isinstance(entity, dict)
        ]
        if suggestion["kind"] in {"horizontal", "vertical"} and operations != ["line"]:
            raise ValueError("Sketcher orientation suggestion must reference a line.")
        if suggestion["reason"] == "native_equal_line_length" and any(
            operation != "line" for operation in operations
        ):
            raise ValueError(
                "Sketcher line equality suggestion references another type."
            )
        if suggestion["reason"] == "native_equal_radius" and any(
            operation not in {"arc", "circle"} for operation in operations
        ):
            raise ValueError(
                "Sketcher radius equality suggestion references another type."
            )
    if any(category_counts[field] > counts[field] for field in category_counts):
        raise ValueError("Sketcher suggestion counts exceed native detections.")
    if guidance["filtered_existing_count"] > sum(counts.values()):
        raise ValueError("Sketcher filtered suggestions exceed native detections.")
    if (
        guidance["suggestions_truncated"]
        and len(suggestions) != _SKETCHER_MAX_UNDERCONSTRAINT_SUGGESTIONS
    ):
        raise ValueError(
            "Truncated Sketcher suggestions do not fill the bounded window."
        )

    status = guidance["status"]
    if degrees_of_freedom == 0:
        if (
            status != "not_needed"
            or suggestions
            or any(counts.values())
            or guidance["filtered_existing_count"]
            or skipped
            or guidance["native_error"]
            or guidance["suggestions_truncated"]
        ):
            raise ValueError("Fully constrained Sketcher guidance is inconsistent.")
    elif status == "available":
        if guidance["native_error"]:
            raise ValueError("Available Sketcher guidance contains a native error.")
        equality_eligible = sum(
            str(item.get("operation") or "") in {"line", "arc", "circle"}
            and str(item.get("operation") or "") != "external_geometry"
            for item in geometry_readback
        )
        expected_skipped = (
            ["equality_size_guard"]
            if equality_eligible > _SKETCHER_MAX_EQUALITY_DIAGNOSTIC_GEOMETRY
            else []
        )
        if skipped != expected_skipped:
            raise ValueError("Sketcher equality size-guard metadata is inconsistent.")
        if skipped and counts["equality"] != 0:
            raise ValueError("Skipped Sketcher equality diagnostics report detections.")
    elif status == "native_diagnostics_unavailable":
        if suggestions or not guidance["native_error"]:
            raise ValueError("Unavailable Sketcher guidance is inconsistent.")
    else:
        raise ValueError("Sketcher underconstraint guidance has an invalid status.")


def _validate_sketcher_profile_open_vertices(
    value: Any,
    *,
    open_wire_count: int,
    geometry_readback: list[dict[str, Any]],
) -> None:
    diagnostics = _exact_mapping(
        value,
        path="sketch_validation.profile_open_vertices",
        keys={
            "status",
            "match_tolerance_mm",
            "vertices",
            "truncated",
            "native_error",
        },
    )
    if (
        diagnostics["match_tolerance_mm"]
        != _SKETCHER_PROFILE_ENDPOINT_MATCH_TOLERANCE_MM
    ):
        raise ValueError("Sketcher open-vertex match tolerance is inconsistent.")
    vertices = diagnostics["vertices"]
    if (
        not isinstance(vertices, list)
        or len(vertices) > _SKETCHER_MAX_PROFILE_OPEN_VERTICES
    ):
        raise ValueError("Sketcher open-vertex diagnostics are not bounded.")
    if not isinstance(diagnostics["truncated"], bool):
        raise ValueError("Sketcher open-vertex truncation metadata is invalid.")
    if (
        not isinstance(diagnostics["native_error"], str)
        or len(diagnostics["native_error"]) > 512
    ):
        raise ValueError("Sketcher open-vertex native error is invalid.")
    for index, raw in enumerate(vertices):
        vertex = _exact_mapping(
            raw,
            path=f"sketch_validation.profile_open_vertices.vertices[{index}]",
            keys={"position_mm", "candidate_endpoints", "matches_truncated"},
        )
        position = vertex["position_mm"]
        if (
            not isinstance(position, list)
            or len(position) != 2
            or any(
                isinstance(item, bool)
                or not isinstance(item, (int, float))
                or not math.isfinite(item)
                for item in position
            )
        ):
            raise ValueError("Sketcher open-vertex position is invalid.")
        matches = vertex["candidate_endpoints"]
        if (
            not isinstance(matches, list)
            or len(matches) > _SKETCHER_MAX_PROFILE_ENDPOINT_MATCHES
        ):
            raise ValueError("Sketcher open-vertex endpoint matches are not bounded.")
        if not isinstance(vertex["matches_truncated"], bool):
            raise ValueError("Sketcher endpoint-match truncation metadata is invalid.")
        if (
            vertex["matches_truncated"]
            and len(matches) != _SKETCHER_MAX_PROFILE_ENDPOINT_MATCHES
        ):
            raise ValueError(
                "Truncated Sketcher endpoint matches do not fill the window."
            )
        seen_matches: set[tuple[str, str]] = set()
        for match_index, match in enumerate(matches):
            key = _validate_sketcher_diagnostic_reference(
                match,
                path=(
                    "sketch_validation.profile_open_vertices."
                    f"vertices[{index}].candidate_endpoints[{match_index}]"
                ),
                geometry_readback=geometry_readback,
                allowed_points={"start", "end"},
            )
            if key in seen_matches:
                raise ValueError("Sketcher open-vertex endpoint match is duplicated.")
            seen_matches.add(key)
            if bool(match["construction"]) or str(match["operation"]) not in {
                "line",
                "arc",
                "elliptic_arc",
                "hyperbolic_arc",
                "parabolic_arc",
                "bspline",
            }:
                raise ValueError("Sketcher open-vertex endpoint type is invalid.")
    status = diagnostics["status"]
    if open_wire_count == 0:
        if (
            status != "not_needed"
            or vertices
            or diagnostics["truncated"]
            or diagnostics["native_error"]
        ):
            raise ValueError("Closed Sketcher profile diagnostics are inconsistent.")
    elif status == "available":
        if diagnostics["native_error"] or not vertices:
            raise ValueError(
                "Available Sketcher open-vertex diagnostics contain an error."
            )
        if (
            diagnostics["truncated"]
            and len(vertices) != _SKETCHER_MAX_PROFILE_OPEN_VERTICES
        ):
            raise ValueError("Truncated Sketcher open vertices do not fill the window.")
    elif status == "native_diagnostics_unavailable":
        if vertices or not diagnostics["native_error"]:
            raise ValueError(
                "Unavailable Sketcher open-vertex diagnostics are inconsistent."
            )
    else:
        raise ValueError("Sketcher open-vertex diagnostics have an invalid status.")


def _validate_sketcher_execution(
    prepared: Mapping[str, Any],
    execution: Mapping[str, Any],
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Reauthorize an isolated native Sketcher solve and its exact graph."""

    if len(outputs) != 1 or str(outputs[0].get("type") or "") != "sketch":
        raise ValueError("A Sketcher candidate must contain exactly one sketch output.")
    item = outputs[0]
    _payload, arguments, properties = _sketcher_payload(
        item.get("definition"),
        path=f"outputs.{item['name']}.definition",
        operation="sketch",
        output_type="sketch",
    )
    if len(arguments) != 2:
        raise ValueError("api.sketch must serialize exactly geometry and constraints.")
    geometry = arguments[0]
    constraints = arguments[1]
    if not isinstance(geometry, list) or not 1 <= len(geometry) <= 4096:
        raise ValueError("A Sketcher definition must contain 1-4096 geometry values.")
    if not isinstance(constraints, list) or len(constraints) > 16384:
        raise ValueError("A Sketcher definition may contain at most 16384 constraints.")
    _exact_mapping(
        properties,
        path="api.sketch.properties",
        keys={
            "support",
            "map_mode",
            "attachment_offset",
            "require_fully_constrained",
            "require_closed_profile",
            "label",
        },
    )
    if not isinstance(properties["map_mode"], str) or not properties["map_mode"]:
        raise ValueError("api.sketch.map_mode must be a non-empty string.")
    if not isinstance(properties["label"], str) or len(properties["label"]) > 256:
        raise ValueError("api.sketch.label is invalid.")
    for field in ("require_fully_constrained", "require_closed_profile"):
        if not isinstance(properties[field], bool):
            raise ValueError(f"api.sketch.{field} must be a boolean.")
    attachment = _exact_mapping(
        properties["attachment_offset"],
        path="api.sketch.attachment_offset",
        keys={"position", "rotation"},
    )
    if not isinstance(attachment["position"], list) or len(attachment["position"]) != 3:
        raise ValueError(
            "api.sketch.attachment_offset.position must contain three values."
        )
    if not isinstance(attachment["rotation"], list) or len(attachment["rotation"]) != 4:
        raise ValueError(
            "api.sketch.attachment_offset.rotation must contain four values."
        )
    rotation_magnitude = math.sqrt(
        sum(float(value) ** 2 for value in attachment["rotation"])
    )
    if not math.isclose(rotation_magnitude, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValueError("api.sketch attachment quaternion is not normalized.")

    resolved_reference_metadata = {
        (
            str(value.get("document_uid") or ""),
            str(value.get("object_name") or ""),
        ): value
        for value in list(prepared.get("resolved_references") or [])
    }
    support = properties["support"]
    expected_support_validation: dict[str, Any] | None = None
    if support is not None:
        support_data = _exact_mapping(
            support,
            path="api.sketch.support",
            keys={"reference", "selection"},
        )
        reference = _exact_mapping(
            support_data["reference"],
            path="api.sketch.support.reference",
            keys={"document_uid", "object_name"},
        )
        reference_key = (str(reference["document_uid"]), str(reference["object_name"]))
        reference_metadata = resolved_reference_metadata.get(reference_key)
        if reference_metadata is None:
            raise ValueError(
                "Sketch support was not authenticated as a staged input reference."
            )
        selection = support_data["selection"]
        if not isinstance(selection, dict):
            raise ValueError("Sketch support selection must be an object.")
        selection_type = str(selection.get("type") or "")
        interface_name = ""
        if selection_type == "subelements":
            _exact_mapping(
                selection,
                path="api.sketch.support.selection",
                keys={"type", "subelements"},
            )
            if bool(reference_metadata.get("transient_topology")) or bool(
                reference_metadata.get("requires_semantic_interfaces")
            ):
                raise ValueError(
                    "A regenerating Sketch support must use a published semantic interface."
                )
            subelements = selection["subelements"]
        elif selection_type == "published_interface":
            _exact_mapping(
                selection,
                path="api.sketch.support.selection",
                keys={"type", "interface_name"},
            )
            interface_name = str(selection["interface_name"] or "")
            interfaces = reference_metadata.get("published_interfaces")
            interface = (
                interfaces.get(interface_name) if isinstance(interfaces, dict) else None
            )
            if not isinstance(interface, dict):
                raise ValueError(
                    f"Sketch support interface {interface_name!r} is not in the host contract."
                )
            subelements = interface.get("subelements")
        else:
            raise ValueError(
                f"Sketch support selection type {selection_type!r} is invalid."
            )
        if not isinstance(subelements, list) or not 1 <= len(subelements) <= 4:
            raise ValueError(
                "Sketch support must resolve to one through four subelements."
            )
        if any(
            re.fullmatch(r"(?:Face|Edge|Vertex)[1-9][0-9]*", str(value or "")) is None
            for value in subelements
        ):
            raise ValueError("Sketch support contains an invalid subelement name.")
        if len(set(str(value) for value in subelements)) != len(subelements):
            raise ValueError("Sketch support contains duplicate subelement names.")
        expected_support_validation = {
            "reference": dict(reference),
            "requested_selection": dict(selection),
            "resolved_subelements": [str(value) for value in subelements],
            "source_kind": str(reference_metadata.get("source_kind") or "native"),
            "source_revision": str(reference_metadata.get("source_revision") or ""),
            "interface_name": interface_name,
            "map_mode": properties["map_mode"],
            "attachment_offset": dict(attachment),
        }

    geometry_by_id: dict[str, dict[str, Any]] = {}
    geometry_readback_expected: list[dict[str, Any]] = []
    geometry_property_keys = {
        "point": {"construction", "name", "graph_id"},
        "line": {"construction", "name", "graph_id"},
        "arc": {"construction", "name", "graph_id"},
        "circle": {"construction", "name", "graph_id"},
        "ellipse": {"rotation_degrees", "construction", "name", "graph_id"},
        "elliptic_arc": {
            "rotation_degrees",
            "construction",
            "name",
            "graph_id",
        },
        "hyperbolic_arc": {
            "rotation_degrees",
            "construction",
            "name",
            "graph_id",
        },
        "parabolic_arc": {
            "rotation_degrees",
            "construction",
            "name",
            "graph_id",
        },
        "bspline": {
            "degree",
            "knots",
            "multiplicities",
            "weights",
            "periodic",
            "tolerance",
            "construction",
            "name",
            "graph_id",
        },
        "external_geometry": {
            "construction",
            "defining",
            "intersection",
            "name",
            "graph_id",
        },
    }
    geometry_argument_counts = {
        "point": 1,
        "line": 2,
        "arc": 3,
        "circle": 2,
        "ellipse": 3,
        "elliptic_arc": 5,
        "hyperbolic_arc": 5,
        "parabolic_arc": 4,
        "bspline": 1,
        "external_geometry": 2,
    }
    external_geometry_expected: list[dict[str, Any]] = []
    for index, raw in enumerate(geometry):
        payload, geometry_arguments, geometry_properties = _sketcher_payload(
            raw,
            path=f"api.sketch.geometry[{index}]",
            output_type="sketch_geometry",
        )
        operation = str(payload["operation"])
        if operation not in _SKETCHER_GEOMETRY_OPERATIONS:
            raise ValueError(
                f"Sketch geometry {index} has unsupported operation {operation!r}."
            )
        if len(geometry_arguments) != geometry_argument_counts[operation]:
            raise ValueError(f"api.{operation} serialized the wrong argument count.")
        _exact_mapping(
            geometry_properties,
            path=f"api.sketch.geometry[{index}].properties",
            keys=geometry_property_keys[operation],
        )
        graph_id = str(geometry_properties["graph_id"] or "")
        if not _SKETCHER_GRAPH_ID.fullmatch(graph_id) or not graph_id.startswith("g"):
            raise ValueError(
                "Sketch geometry graph ids must be positive gN identifiers."
            )
        if graph_id in geometry_by_id:
            raise ValueError(f"Sketch geometry graph id {graph_id!r} is duplicated.")
        if not isinstance(geometry_properties["construction"], bool):
            raise ValueError(
                f"Sketch geometry {graph_id!r} construction must be boolean."
            )
        if not isinstance(geometry_properties["name"], str):
            raise ValueError(f"Sketch geometry {graph_id!r} name must be a string.")
        if operation == "external_geometry":
            for field in ("defining", "intersection"):
                if not isinstance(geometry_properties[field], bool):
                    raise ValueError(
                        f"Sketch external geometry {graph_id!r} {field} must be boolean."
                    )
            if geometry_properties["construction"] is not True:
                raise ValueError("External Sketcher geometry must be profile-excluded.")
            reference = _exact_mapping(
                geometry_arguments[0],
                path=f"api.sketch.geometry[{index}].reference",
                keys={"document_uid", "object_name"},
            )
            reference_key = (
                str(reference["document_uid"]),
                str(reference["object_name"]),
            )
            reference_metadata = resolved_reference_metadata.get(reference_key)
            if reference_metadata is None:
                raise ValueError(
                    f"External geometry {graph_id!r} was not authenticated as an input."
                )
            selection = geometry_arguments[1]
            if not isinstance(selection, dict):
                raise ValueError(
                    f"External geometry {graph_id!r} selection must be an object."
                )
            selection_type = str(selection.get("type") or "")
            interface_name = ""
            if selection_type == "subelements":
                _exact_mapping(
                    selection,
                    path=f"api.sketch.geometry[{index}].selection",
                    keys={"type", "subelements"},
                )
                if bool(reference_metadata.get("transient_topology")) or bool(
                    reference_metadata.get("requires_semantic_interfaces")
                ):
                    raise ValueError(
                        f"External geometry {graph_id!r} on a regenerating source must "
                        "use a published semantic interface."
                    )
                subelements = selection["subelements"]
            elif selection_type == "published_interface":
                _exact_mapping(
                    selection,
                    path=f"api.sketch.geometry[{index}].selection",
                    keys={"type", "interface_name"},
                )
                interface_name = str(selection["interface_name"] or "")
                interfaces = reference_metadata.get("published_interfaces")
                interface = (
                    interfaces.get(interface_name)
                    if isinstance(interfaces, dict)
                    else None
                )
                if not isinstance(interface, dict):
                    raise ValueError(
                        f"External geometry interface {interface_name!r} is not in the "
                        "host reference contract."
                    )
                subelements = interface.get("subelements")
            else:
                raise ValueError(
                    f"External geometry {graph_id!r} selection type is invalid."
                )
            if (
                not isinstance(subelements, list)
                or len(subelements) != 1
                or re.fullmatch(
                    r"(?:Edge|Vertex)[1-9][0-9]*",
                    str(subelements[0] or ""),
                )
                is None
            ):
                raise ValueError(
                    f"External geometry {graph_id!r} must resolve to one EdgeN or VertexN."
                )
            external_geometry_expected.append(
                {
                    "reference": dict(reference),
                    "requested_selection": dict(selection),
                    "resolved_subelement": str(subelements[0]),
                    "source_kind": str(
                        reference_metadata.get("source_kind") or "native"
                    ),
                    "source_revision": str(
                        reference_metadata.get("source_revision") or ""
                    ),
                    "interface_name": interface_name,
                    "graph_id": graph_id,
                    "native_geometry_id": -3 - len(external_geometry_expected),
                    "defining": geometry_properties["defining"],
                    "intersection": geometry_properties["intersection"],
                }
            )
        geometry_by_id[graph_id] = payload
        geometry_readback_expected.append(
            {
                "index": index,
                "graph_id": graph_id,
                "name": geometry_properties["name"],
                "operation": operation,
                "construction": geometry_properties["construction"],
            }
        )

    constraint_readback_expected: list[dict[str, Any]] = []
    constraint_names: set[str] = set()
    constraint_property_keys = {
        "value",
        "name",
        "expression",
        "driving",
        "active",
        "virtual",
        "alignment",
        "internal_index",
        "text",
        "font",
        "text_height",
        "graph_id",
    }
    for index, raw in enumerate(constraints):
        _constraint_payload, constraint_arguments, constraint_properties = (
            _sketcher_payload(
                raw,
                path=f"api.sketch.constraints[{index}]",
                operation="constraint",
                output_type="sketch_constraint",
            )
        )
        if len(constraint_arguments) != 2 or not isinstance(
            constraint_arguments[1], list
        ):
            raise ValueError(f"Sketch constraint {index} has malformed arguments.")
        kind = str(constraint_arguments[0] or "")
        if kind not in _SKETCHER_CONSTRAINT_KINDS:
            raise ValueError(
                f"Sketch constraint {index} has unsupported kind {kind!r}."
            )
        _exact_mapping(
            constraint_properties,
            path=f"api.sketch.constraints[{index}].properties",
            keys=constraint_property_keys,
        )
        graph_id = str(constraint_properties["graph_id"] or "")
        if not _SKETCHER_GRAPH_ID.fullmatch(graph_id) or not graph_id.startswith("c"):
            raise ValueError(
                "Sketch constraint graph ids must be positive cN identifiers."
            )
        for field in ("driving", "active", "virtual", "text_height"):
            if not isinstance(constraint_properties[field], bool):
                raise ValueError(
                    f"Sketch constraint {graph_id!r} {field} must be boolean."
                )
        name = constraint_properties["name"]
        expression = constraint_properties["expression"]
        if not isinstance(name, str) or not isinstance(expression, str):
            raise ValueError(
                f"Sketch constraint {graph_id!r} name/expression is malformed."
            )
        if name and name in constraint_names:
            raise ValueError(f"Sketch constraint name {name!r} is duplicated.")
        constraint_names.add(name)
        for entity_index, entity in enumerate(constraint_arguments[1]):
            if not isinstance(entity, dict):
                raise ValueError(
                    f"Sketch constraint {graph_id!r} entity {entity_index} is malformed."
                )
            if set(entity) == {"external", "point"}:
                if entity["external"] not in {"x_axis", "y_axis", "origin"}:
                    raise ValueError(
                        f"Sketch constraint {graph_id!r} has invalid external entity."
                    )
            elif set(entity) == {"geometry", "point"}:
                nested = entity["geometry"]
                if not isinstance(nested, dict):
                    raise ValueError(
                        f"Sketch constraint {graph_id!r} geometry is malformed."
                    )
                nested_properties = nested.get("properties")
                nested_id = (
                    str(nested_properties.get("graph_id") or "")
                    if isinstance(nested_properties, dict)
                    else ""
                )
                if (
                    nested_id not in geometry_by_id
                    or nested != geometry_by_id[nested_id]
                ):
                    raise ValueError(
                        f"Sketch constraint {graph_id!r} does not reference an exact graph value."
                    )
            else:
                raise ValueError(
                    f"Sketch constraint {graph_id!r} entity fields are malformed."
                )
        constraint_readback_expected.append(
            {
                "index": index,
                "graph_id": graph_id,
                "name": name,
                "kind": kind,
                "driving": constraint_properties["driving"],
                "active": constraint_properties["active"],
                "virtual": constraint_properties["virtual"],
                "expression": expression,
                "expression_bound": bool(expression),
            }
        )

    validation = execution.get("sketch_validation")
    if not isinstance(validation, dict) or item.get("sketch_validation") != validation:
        raise ValueError("The Sketcher worker returned inconsistent native validation.")
    required_validation_keys = {
        "solver_code",
        "geometry_count",
        "native_geometry_count",
        "external_geometry_count",
        "constraint_count",
        "degrees_of_freedom",
        "fully_constrained",
        "conflicting_constraints",
        "redundant_constraints",
        "partially_redundant_constraints",
        "malformed_constraints",
        "edge_count",
        "wire_count",
        "closed_wire_count",
        "open_wire_count",
        "profile_ready",
        "construction_geometry_count",
        "geometry",
        "external_geometry",
        "constraints",
        "constraint_errors",
        "constraint_error_unavailable",
        "constraint_errors_truncated",
        "underconstraint_guidance",
        "profile_open_vertices",
        "constraint_issues",
        "requirements",
        "support",
    }
    if set(validation) != required_validation_keys:
        raise ValueError("The Sketcher native validation has an unexpected schema.")
    integer_fields = (
        "solver_code",
        "geometry_count",
        "native_geometry_count",
        "external_geometry_count",
        "constraint_count",
        "degrees_of_freedom",
        "edge_count",
        "wire_count",
        "closed_wire_count",
        "open_wire_count",
        "construction_geometry_count",
    )
    if any(type(validation.get(field)) is not int for field in integer_fields):
        raise ValueError("The Sketcher native validation contains non-integer counts.")
    if int(validation["solver_code"]) != 0:
        raise ValueError(
            "The Sketcher candidate does not have a clean native solver result."
        )
    if int(validation["geometry_count"]) != len(geometry):
        raise ValueError("The Sketcher native geometry count is inconsistent.")
    local_geometry_count = len(geometry) - len(external_geometry_expected)
    if int(validation["native_geometry_count"]) != local_geometry_count:
        raise ValueError("The Sketcher local native geometry count is inconsistent.")
    if int(validation["external_geometry_count"]) != len(external_geometry_expected):
        raise ValueError("The Sketcher external geometry count is inconsistent.")
    if int(validation["constraint_count"]) != len(constraints):
        raise ValueError("The Sketcher native constraint count is inconsistent.")
    if int(validation["degrees_of_freedom"]) < 0:
        raise ValueError("The Sketcher native DoF count is invalid.")
    for field in (
        "fully_constrained",
        "profile_ready",
        "constraint_errors_truncated",
    ):
        if not isinstance(validation[field], bool):
            raise ValueError(f"The Sketcher native {field} value must be boolean.")
    for field in (
        "conflicting_constraints",
        "redundant_constraints",
        "partially_redundant_constraints",
        "malformed_constraints",
    ):
        if validation[field] != []:
            raise ValueError(
                f"The accepted Sketcher candidate has {field.replace('_', ' ')}."
            )
    if validation["geometry"] != geometry_readback_expected:
        raise ValueError(
            "The native Sketcher geometry readback differs from the source graph."
        )
    if validation["external_geometry"] != external_geometry_expected:
        raise ValueError(
            "The native Sketcher external-geometry readback differs from the host contract."
        )
    native_constraints = validation["constraints"]
    if not isinstance(native_constraints, list) or len(native_constraints) != len(
        constraint_readback_expected
    ):
        raise ValueError(
            "The native Sketcher constraint readback has the wrong length."
        )
    for expected_readback, native_readback in zip(
        constraint_readback_expected, native_constraints
    ):
        if not isinstance(native_readback, dict):
            raise ValueError("The native Sketcher constraint readback is malformed.")
        for field, expected_value in expected_readback.items():
            if native_readback.get(field) != expected_value:
                raise ValueError(
                    f"Native Sketcher constraint {expected_readback['graph_id']!r} "
                    f"changed {field}."
                )
        if not str(native_readback.get("native_type") or ""):
            raise ValueError("A native Sketcher constraint has no type readback.")
        value = native_readback.get("value")
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(
                "A native Sketcher constraint has a non-finite value readback."
            )
    requirements = _exact_mapping(
        validation["requirements"],
        path="sketch_validation.requirements",
        keys={"fully_constrained", "closed_profile"},
    )
    if requirements != {
        "fully_constrained": properties["require_fully_constrained"],
        "closed_profile": properties["require_closed_profile"],
    }:
        raise ValueError("Sketcher validation requirements differ from api.sketch.")
    if requirements["fully_constrained"] and not validation["fully_constrained"]:
        raise ValueError(
            "The Sketcher worker did not enforce fully constrained output."
        )
    if validation["support"] != expected_support_validation:
        raise ValueError(
            "Sketcher support resolution differs from the host reference contract."
        )
    if int(validation["closed_wire_count"]) + int(validation["open_wire_count"]) != int(
        validation["wire_count"]
    ):
        raise ValueError("The Sketcher wire diagnostics are inconsistent.")
    profile_ready = bool(
        int(validation["wire_count"]) > 0
        and int(validation["closed_wire_count"]) == int(validation["wire_count"])
    )
    if validation["profile_ready"] != profile_ready:
        raise ValueError("The Sketcher profile-readiness result is inconsistent.")
    if requirements["closed_profile"] and not profile_ready:
        raise ValueError("The Sketcher worker did not enforce a closed profile.")
    if int(validation["construction_geometry_count"]) != sum(
        bool(value["construction"]) for value in geometry_readback_expected
    ):
        raise ValueError("The Sketcher construction-geometry count is inconsistent.")
    errors = validation["constraint_errors"]
    if not isinstance(errors, list) or len(errors) > min(len(constraints), 512):
        raise ValueError("The Sketcher constraint-error diagnostics are malformed.")
    seen_error_indexes: set[int] = set()
    for diagnostic in errors:
        data = _exact_mapping(
            diagnostic,
            path="sketch_validation.constraint_errors[]",
            keys={"index", "error"},
        )
        index = data["index"]
        error = data["error"]
        if type(index) is not int or not 0 <= index < len(constraints):
            raise ValueError("A Sketcher constraint-error index is out of range.")
        if index in seen_error_indexes:
            raise ValueError("A Sketcher constraint-error index is duplicated.")
        seen_error_indexes.add(index)
        if (
            isinstance(error, bool)
            or not isinstance(error, (int, float))
            or not math.isfinite(error)
        ):
            raise ValueError("A Sketcher constraint error must be finite.")
    unavailable_errors = validation["constraint_error_unavailable"]
    if not isinstance(unavailable_errors, list) or len(unavailable_errors) > min(
        len(constraints), 512
    ):
        raise ValueError("The unavailable Sketcher residual diagnostics are malformed.")
    for diagnostic in unavailable_errors:
        data = _exact_mapping(
            diagnostic,
            path="sketch_validation.constraint_error_unavailable[]",
            keys={"index", "reason", "message"},
        )
        index = data["index"]
        if type(index) is not int or not 0 <= index < len(constraints):
            raise ValueError("An unavailable Sketcher residual index is out of range.")
        if index in seen_error_indexes:
            raise ValueError(
                "A Sketcher residual index is accounted for more than once."
            )
        if data["reason"] not in {"native_error", "non_finite"}:
            raise ValueError("An unavailable Sketcher residual has an invalid reason.")
        if not isinstance(data["message"], str) or len(data["message"]) > 512:
            raise ValueError("An unavailable Sketcher residual message is invalid.")
        seen_error_indexes.add(index)
    checked_constraint_count = min(len(constraints), 512)
    if seen_error_indexes != set(range(checked_constraint_count)):
        raise ValueError(
            "Sketcher residual diagnostics do not account for every checked constraint."
        )
    if validation["constraint_errors_truncated"] != (len(constraints) > 512):
        raise ValueError("Sketcher residual truncation metadata is inconsistent.")
    _validate_sketcher_underconstraint_guidance(
        validation["underconstraint_guidance"],
        degrees_of_freedom=int(validation["degrees_of_freedom"]),
        geometry_readback=geometry_readback_expected,
    )
    _validate_sketcher_profile_open_vertices(
        validation["profile_open_vertices"],
        open_wire_count=int(validation["open_wire_count"]),
        geometry_readback=geometry_readback_expected,
    )
    constraint_issues = _exact_mapping(
        validation["constraint_issues"],
        path="sketch_validation.constraint_issues",
        keys={"conflicting", "redundant", "partially_redundant", "malformed"},
    )
    if any(constraint_issues.values()):
        raise ValueError("An accepted Sketcher candidate reports constraint issues.")
    encoded = json.dumps(
        validation,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(encoded) > _STRUCTURED_DEFINITION_LIMIT:
        raise ValueError("The Sketcher native validation is too large.")
    item["sketch_validation"] = dict(validation)
    return dict(validation)


def _validate_definition_value(
    value: Any,
    prepared: Mapping[str, Any],
    path: str,
    depth: int = 0,
) -> None:
    extra_depth = {
        "assembly": 12,
    }.get(prepared["pack"].domain, 4)
    if depth > contracts.MAX_INPUT_DEPTH + extra_depth:
        raise ValueError(f"{path} exceeds the supported definition depth.")
    if value is None or isinstance(value, bool | int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must be finite.")
        return
    if isinstance(value, str):
        if value.startswith(("/", "\\")) or _DRIVE_PATH.match(value):
            raise ValueError(f"{path} cannot contain a raw filesystem path.")
        if ".." in Path(value.replace("\\", "/")).parts:
            raise ValueError(f"{path} cannot traverse a filesystem path.")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_definition_value(item, prepared, f"{path}[{index}]", depth + 1)
        return
    if isinstance(value, dict):
        if set(value) == {"document_uid", "object_name"}:
            if str(value["document_uid"]) != str(prepared["document_uid"]):
                raise ValueError(f"{path} refers to a different document.")
            names = {
                str(item.get("name") or "") for item in prepared["document_objects"]
            }
            if str(value["object_name"]) not in names:
                raise ValueError(
                    f"{path} refers to missing object {value['object_name']!r}."
                )
            return
        for key, item in value.items():
            _validate_definition_value(item, prepared, f"{path}.{key}", depth + 1)
        return
    raise ValueError(f"{path} contains unsupported value {type(value).__name__}.")


def validate_candidate(
    prepared: Mapping[str, Any], execution: Mapping[str, Any]
) -> dict[str, Any]:
    """Import and validate detached worker values off the document thread."""

    if execution.get("ok") is not True:
        raise DomainRuntimeFailure(dict(execution))
    pack: contracts.XScriptWorkbenchPack = prepared["pack"]
    if (
        execution.get("schema") != WORKER_SCHEMA
        or execution.get("domain") != pack.domain
    ):
        raise ValueError(
            "The worker result does not match the prepared domain contract."
        )
    outputs = execution.get("outputs")
    expected = list(prepared["expected_outputs"])
    if not isinstance(outputs, list) or [item.get("name") for item in outputs] != [
        item["name"] for item in expected
    ]:
        raise ValueError(
            "Worker outputs do not exactly match the declared output order."
        )
    staging = Path(str(prepared["staging"])).resolve()
    validated: list[dict[str, Any]] = []
    for declaration, raw in zip(expected, outputs):
        if not isinstance(raw, dict) or raw.get("type") != declaration["type"]:
            raise ValueError(f"Output {declaration['name']!r} has the wrong type.")
        item = dict(raw)
        definition = item.get("definition")
        _validate_definition_value(
            definition, prepared, f"outputs.{declaration['name']}.definition"
        )
        operation_diagnostics = item.get("operation_diagnostics")
        if operation_diagnostics is not None:
            if not isinstance(operation_diagnostics, dict):
                raise ValueError(
                    f"Output {declaration['name']!r} operation diagnostics must be an object."
                )
            _validate_definition_value(
                operation_diagnostics,
                prepared,
                f"outputs.{declaration['name']}.operation_diagnostics",
            )
        encoded = json.dumps(
            definition,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if len(encoded) > _STRUCTURED_DEFINITION_LIMIT:
            raise ValueError(f"Output {declaration['name']!r} definition is too large.")
        output_type = str(item["type"])
        if item.get("artifact_kind") == "brep":
            import Part

            path = (staging / str(item.get("artifact_path") or "")).resolve()
            if staging not in path.parents or not path.is_file():
                raise ValueError(f"BREP output {declaration['name']!r} is missing.")
            shape = Part.Shape()
            shape.importBrep(str(path))
            if shape.isNull() or not shape.isValid():
                raise ValueError(f"BREP output {declaration['name']!r} is invalid.")
            reported_facts = dict(item.get("facts") or {})
            detail_limit = int(reported_facts.get("subelement_detail_limit", -1))
            if not 0 <= detail_limit <= 256:
                raise ValueError(
                    f"BREP output {declaration['name']!r} reported an invalid topology "
                    "detail limit."
                )
            facts = _detached_shape_facts(shape, max_subelements=detail_limit)
            for key in ("solids", "shells", "faces", "wires", "edges", "vertices"):
                if int(reported_facts.get(key, -1)) != int(facts[key]):
                    raise ValueError(
                        f"BREP output {declaration['name']!r} changed topology during "
                        f"artifact transfer ({key}: worker={reported_facts.get(key)!r}, "
                        f"detached={facts[key]!r})."
                    )
            facts["artifact_shape_type"] = facts["shape_type"]
            facts["shape_type"] = str(
                reported_facts.get("shape_type") or facts["shape_type"]
            )
            if output_type in _BREP_OUTPUT_TYPES:
                _validate_shape_class(output_type, facts)
            if pack.domain == "partdesign":
                data = item.get("partdesign_data")
                if not isinstance(data, dict):
                    raise ValueError(
                        f"Part Design output {declaration['name']!r} has no native "
                        "Body/feature validation evidence."
                    )
                if str(data.get("brep_sha256") or "") != _sha256_file(path):
                    raise ValueError(
                        f"Part Design output {declaration['name']!r} BREP digest changed."
                    )
                history = data.get("feature_history")
                sketches = data.get("sketches")
                interfaces = data.get("interfaces")
                if (
                    not isinstance(history, list)
                    or int(data.get("feature_count") or -1) != len(history)
                    or not isinstance(sketches, list)
                    or not isinstance(interfaces, dict)
                    or any(
                        not isinstance(sketch, dict)
                        or int(sketch.get("solver_code") or 0) != 0
                        or sketch.get("conflicting_constraints")
                        or sketch.get("redundant_constraints")
                        or sketch.get("malformed_constraints")
                        for sketch in sketches
                    )
                ):
                    raise ValueError(
                        f"Part Design output {declaration['name']!r} has malformed "
                        "native feature or sketch evidence."
                    )
            item["facts"] = facts
            item["detached_shape"] = shape
        validated.append(item)
    partdesign_validation = None
    assembly_validation = None
    sketch_validation = None
    if pack.domain == "partdesign":
        partdesign_validation = execution.get("partdesign_validation")
        if not isinstance(partdesign_validation, dict):
            raise ValueError("The Part Design worker returned no domain validation.")
        reported = partdesign_validation.get("outputs")
        if not isinstance(reported, list) or [item.get("name") for item in reported] != [
            item["name"] for item in validated
        ]:
            raise ValueError("Part Design domain validation changed output identity.")
    elif pack.domain == "assembly":
        assembly_validation = _validate_assembly_execution(
            prepared,
            execution,
            validated,
        )
    elif pack.domain == "sketcher":
        sketch_validation = _validate_sketcher_execution(
            prepared,
            execution,
            validated,
        )
    result = {
        "ok": True,
        "outputs": validated,
        "stdout": str(execution.get("stdout") or ""),
        "budget": dict(execution.get("budget") or {}),
        "process": dict(execution.get("process") or {}),
    }
    if partdesign_validation is not None:
        result["partdesign_validation"] = partdesign_validation
    if assembly_validation is not None:
        result["assembly_validation"] = assembly_validation
    if sketch_validation is not None:
        result["sketch_validation"] = sketch_validation
    return result


def _attempt_destination(prepared: Mapping[str, Any]) -> Path:
    return (
        Path(str(prepared["program_directory"]))
        / "attempts"
        / str(prepared["attempt_id"])
    )


def retain_candidate(
    prepared: Mapping[str, Any],
    *,
    status: str,
    failure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Move staging into the durable attempt history and update working state."""

    staging = Path(str(prepared["staging"]))
    destination = _attempt_destination(prepared)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if staging.exists() and not destination.exists():
        staging.replace(destination)
    manifest_path = Path(str(prepared["program_directory"])) / "program.json"
    manifest = _read_json(manifest_path, "XScript program manifest")
    candidate = dict(manifest.get("latest_candidate") or {})
    candidate.update(
        {
            "attempt_id": str(prepared["attempt_id"]),
            "revision": str(prepared["revision"]),
            "status": status,
            "completed_at": time.time(),
            "artifact_directory": str(destination),
        }
    )
    if failure:
        candidate["failure"] = {
            key: failure.get(key)
            for key in ("failure_code", "failure_stage", "error", "observed")
            if failure.get(key) not in (None, "", {}, [])
        }
    manifest["latest_candidate"] = candidate
    manifest["updated_at"] = time.time()
    _atomic_json(manifest_path, manifest)
    return {"attempt_directory": str(destination), "manifest": manifest}


def accept_candidate(
    prepared: Mapping[str, Any],
    publication: Mapping[str, Any],
) -> dict[str, Any]:
    manifest_path = Path(str(prepared["program_directory"])) / "program.json"
    manifest = _read_json(manifest_path, "XScript program manifest")
    candidate = dict(manifest.get("latest_candidate") or {})
    candidate["status"] = "accepted"
    candidate["accepted_at"] = time.time()
    manifest["latest_candidate"] = candidate
    manifest["accepted_revision"] = str(prepared["revision"])
    manifest["accepted_contract"] = {
        key: prepared[key]
        for key in ("source", "input_schema", "inputs", "expected_outputs", "revision")
    }
    if prepared.get("resolved_references"):
        manifest["accepted_contract"]["resolved_references"] = list(
            prepared["resolved_references"]
        )
        manifest["resolved_references"] = list(prepared["resolved_references"])
    else:
        manifest.pop("resolved_references", None)
    manifest["live_outputs"] = dict(publication.get("live_outputs") or {})
    manifest["updated_at"] = time.time()
    _atomic_json(manifest_path, manifest)
    domain = prepared["pack"].domain
    program_id = str(prepared["program_id"])
    revision = str(prepared["revision"])
    return {
        "ok": True,
        "program_id": program_id,
        "program_name": str(prepared["program_name"]),
        "domain": domain,
        "workbench": prepared["pack"].workbench,
        "working_revision": revision,
        "accepted_revision": revision,
        "outputs": list(publication.get("outputs") or []),
        "live_outputs": dict(publication.get("live_outputs") or {}),
        "attempt_directory": str(candidate.get("artifact_directory") or ""),
        "stdout": str(publication.get("stdout") or ""),
        "budget": dict(publication.get("budget") or {}),
        "model_state": {
            "status": "accepted",
            "accepted_is_current": True,
            "next_write_expected_revision": revision,
            "verification_call": {
                "tool": "core.inspect",
                "arguments": {
                    "scope": "program",
                    "target": program_id,
                    "path": "",
                    "offset": 0,
                    "limit": 50,
                    "attach": False,
                },
            },
            "verification_goal": (
                "Confirm accepted_revision equals working_revision and every declared "
                "output has the expected stable live identity and accepted evidence."
            ),
        },
    }


def describe_api(pack: contracts.XScriptWorkbenchPack) -> dict[str, Any]:
    adapter = contracts.get_domain_adapter(pack.domain)
    if adapter is None:
        return _failure(
            f"{pack.engine}.{pack.domain}.describe_api",
            "DOMAIN_UNAVAILABLE",
            "surface",
            f"The {pack.title} domain adapter is unavailable.",
        )
    result = adapter.describe_api()
    # Domain adapters are keyed by domain and shared across scripted engines, so
    # the adapter's own pack is always the xscript twin. Re-stamp the
    # engine-variant fields from the actual requested pack so an xscript
    # describe_api reports the ``x`` api global and the xscript program schema.
    if isinstance(result, dict) and result.get("ok"):
        result["engine"] = pack.engine
        result["program_schema"] = pack.program_schema
        result["source_globals"] = ["doc", "inputs", pack.api_global]
    return result


def capture_inspection_state(
    service: Any, tool_name: str, program_id: str
) -> dict[str, Any]:
    captured = capture_operation_state(service, tool_name, {"program_id": program_id})
    clean = str(program_id or "").strip().lower()
    if not _PROGRAM_ID.fullmatch(clean):
        _raise(tool_name, "INVALID_PROGRAM_ID", "schema", "Invalid program_id.")
    captured["program_id"] = clean
    return captured


def capture_editor_inspection_state(service: Any, domain: str, program_id: str) -> dict[str, Any]:
    """Capture the minimum live state required by the human source editor.

    Provider inspection intentionally captures the broader operation contract.
    The editor only needs one persisted manifest plus its stable live output
    identities, so it must not enumerate unrelated document objects or resolve
    input geometry merely to display source text.
    """

    clean_domain = str(domain or "").strip().lower()
    clean_program_id = str(program_id or "").strip().lower()
    from CadexModelingSurface import resolve_service_surface

    resolution = resolve_service_surface(service, service.active_workbench_name())
    tool_name = f"{resolution.engine or 'xscript'}.{clean_domain}.inspect_program"
    if not _PROGRAM_ID.fullmatch(clean_program_id):
        _raise(tool_name, "INVALID_PROGRAM_ID", "schema", "Invalid program_id.")
    doc = service._active_document()
    if doc is None:
        _raise(tool_name, "NO_DOCUMENT", "precondition", "No active FreeCAD document.")
    pack = _engine_pack(resolution.engine, clean_domain)
    if pack is None or pack.domain != clean_domain:
        _raise(
            tool_name,
            "DOMAIN_SURFACE_CHANGED",
            "surface",
            "The active workbench no longer authorizes this editor domain.",
        )
    if (
        resolution.engine != pack.engine
        or resolution.workbench != pack.workbench
        or resolution.domain != clean_domain
        or not resolution.available
    ):
        _raise(
            tool_name,
            "DOMAIN_SURFACE_CHANGED",
            "surface",
            "The active workbench and modeling engine no longer authorize this editor domain.",
            observed=resolution.summary(),
        )
    scope = service.project_scope_snapshot()
    return {
        "tool_name": tool_name,
        "pack": pack,
        "program_id": clean_program_id,
        "project_root": str(scope.get("root") or ""),
        "live_programs": _live_programs(doc, clean_domain),
    }


def complete_inspection(captured: Mapping[str, Any]) -> dict[str, Any]:
    pack: contracts.XScriptWorkbenchPack = captured["pack"]
    program_id = str(captured["program_id"])
    try:
        manifest = _load_manifest(captured["project_root"], pack, program_id)
    except Exception as exc:
        return _failure(
            str(captured["tool_name"]),
            "PROGRAM_NOT_FOUND",
            "precondition",
            str(exc),
            observed={"program_id": program_id},
        )
    live = next(
        (
            item
            for item in captured["live_programs"]
            if item["program_id"] == program_id
        ),
        None,
    )
    adapter = contracts.get_domain_adapter(pack.domain)
    assert adapter is not None
    return adapter.inspect(dict(captured), manifest | {"live_state": live})


def apply_parameter_controls(
    service: Any,
    pack: contracts.XScriptWorkbenchPack,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge-patch the UI slider metadata without rebuilding geometry.

    Controls are metadata-only: ``input_controls`` is excluded from
    ``program_revision`` so this never invalidates the working revision, and the
    source is never rerun. A dedicated entry point is required because a
    metadata-only edit_source/set_inputs would be rejected as a no-op mutation.
    """

    tool_name = f"{pack.engine}.{pack.domain}.set_parameter_controls"
    scope = service.project_scope_snapshot()
    project_root = str(scope.get("root") or "")
    if not project_root:
        _raise(
            tool_name,
            "NO_PROJECT_ROOT",
            "precondition",
            "No Cadex project directory is available for persisted programs.",
        )
    program_id = str(arguments.get("program_id") or "").strip().lower()
    if not _PROGRAM_ID.fullmatch(program_id):
        _raise(
            tool_name,
            "INVALID_PROGRAM_ID",
            "schema",
            "program_id must be a 32-character lowercase hexadecimal id.",
        )
    try:
        manifest = _load_manifest(project_root, pack, program_id)
    except Exception as exc:
        _raise(
            tool_name,
            "PROGRAM_NOT_FOUND",
            "precondition",
            str(exc),
            observed={"program_id": program_id},
        )
    current_revision = str(manifest.get("working_revision") or "")
    expected_revision = str(arguments.get("expected_revision") or "").strip()
    if expected_revision != current_revision:
        _raise(
            tool_name,
            "STALE_PROGRAM_REVISION",
            "precondition",
            f"The {pack.title} XScript program changed after inspection.",
            requested={"expected_revision": expected_revision},
            observed={"current_revision": current_revision},
            required_changes=[{"inspect_program": program_id}],
        )
    patch = arguments.get("controls_patch")
    if not isinstance(patch, dict) or not patch:
        _raise(
            tool_name,
            "EMPTY_CONTROLS_PATCH",
            "schema",
            "controls_patch must be a non-empty object.",
        )
    merged = _merge_controls_patch(dict(manifest.get("input_controls") or {}), patch)
    inputs = dict(manifest.get("inputs") or {})
    cleaned = clean_parameter_controls(tool_name, merged, inputs)
    manifest["input_controls"] = cleaned
    _atomic_json(_manifest_path(project_root, pack.domain, program_id), manifest)
    return {
        "ok": True,
        "program_id": program_id,
        "working_revision": current_revision,
        "input_controls": cleaned,
        "geometry_unchanged": True,
    }


def prepare_delete(captured: Mapping[str, Any]) -> dict[str, Any]:
    pack: contracts.XScriptWorkbenchPack = captured["pack"]
    arguments = dict(captured["arguments"])
    program_id = str(arguments.get("program_id") or "").strip().lower()
    try:
        manifest = _load_manifest(captured["project_root"], pack, program_id)
    except Exception as exc:
        _raise(
            str(captured["tool_name"]),
            "PROGRAM_NOT_FOUND",
            "precondition",
            str(exc),
        )
    expected = str(arguments.get("expected_revision") or "")
    current = str(manifest.get("working_revision") or "")
    if expected != current:
        _raise(
            str(captured["tool_name"]),
            "STALE_PROGRAM_REVISION",
            "precondition",
            "The program changed after inspection.",
            requested={"expected_revision": expected},
            observed={"current_revision": current},
        )
    directory = _program_directory(captured["project_root"], pack.domain, program_id)
    trash = directory.parent / ".trash" / f"{program_id}-{uuid.uuid4().hex}"
    trash.parent.mkdir(parents=True, exist_ok=True)
    directory.replace(trash)
    return {
        **dict(captured),
        "program_id": program_id,
        "manifest": manifest,
        "program_directory": str(directory),
        "trash_directory": str(trash),
    }


def restore_prepared_delete(prepared: Mapping[str, Any]) -> None:
    trash = Path(str(prepared["trash_directory"]))
    original = Path(str(prepared["program_directory"]))
    if trash.exists() and not original.exists():
        trash.replace(original)


def finish_delete(
    prepared: Mapping[str, Any], publication: Mapping[str, Any]
) -> dict[str, Any]:
    trash = Path(str(prepared["trash_directory"]))
    shutil.rmtree(trash)
    return {
        "ok": True,
        "program_id": str(prepared["program_id"]),
        "domain": prepared["pack"].domain,
        "deleted_objects": list(publication.get("deleted_objects") or []),
        "reason": str(prepared["arguments"].get("reason") or ""),
        "artifacts_deleted": True,
    }


@dataclass
class DeclarativeDomainAdapter:
    pack: contracts.XScriptWorkbenchPack
    production_ready: bool = False

    def describe_api(self) -> dict[str, Any]:
        api = create_domain_api(
            self.pack.domain, self.pack.api_exports, self.pack.output_types
        )
        exports = []
        for name in api.exported_names:
            member = getattr(api, name)
            exports.append(
                {
                    "name": name,
                    "signature": str(inspect.signature(member)),
                    "description": str(inspect.getdoc(member) or ""),
                }
            )
        return {
            "ok": True,
            "domain": self.pack.domain,
            "workbench": self.pack.workbench,
            "engine": self.pack.engine,
            "program_schema": self.pack.program_schema,
            "runtime_exports": exports,
            "accepted_output_types": list(self.pack.output_types),
            "source_globals": ["doc", "inputs", self.pack.api_global],
            "result_contract": (
                "Assign result to a dict whose keys exactly match expected_outputs "
                "in declared order and whose values come from this domain api."
            ),
            "instructions": self.pack.instructions,
            "model_operating_contract": {
                "context_first": (
                    "Read the injected xscript_domain context before calling a write "
                    "tool. Reuse a matching persisted program and copy candidate stable "
                    "references exactly; do not invent document_uid or object_name values."
                ),
                "authoring_sequence": [
                    {
                        "step": 1,
                        "action": "discover",
                        "instruction": (
                            "Read existing programs and domain candidates in the injected "
                            "context. Inspect a matching program before deciding to mutate it."
                        ),
                    },
                    {
                        "step": 2,
                        "action": "learn_api",
                        "instruction": (
                            "Use this describe_api response as the exact runtime contract; "
                            "never guess exports, signatures, units, or output types."
                        ),
                    },
                    {
                        "step": 3,
                        "action": "author",
                        "instruction": (
                            "Create only when no existing program owns the intent. Keep output "
                            "names semantic and stable, and make result keys exactly match "
                            "expected_outputs in the same order."
                        ),
                    },
                    {
                        "step": 4,
                        "action": "repair",
                        "instruction": (
                            "On failure, use failure_stage, observed values, native diagnostics, "
                            "retry.required_changes, and model_state. Repair the smallest exact "
                            "cause against next_write_expected_revision; the prior accepted "
                            "revision remains live."
                        ),
                    },
                    {
                        "step": 5,
                        "action": "verify",
                        "instruction": (
                            "After a successful write, call the returned verification_call and "
                            "confirm accepted_revision equals working_revision plus the domain's "
                            "accepted live evidence."
                        ),
                    },
                ],
                "mutation_selection": {
                    "edit_source": (
                        "Use only for exact source-text changes while input_schema, inputs, "
                        "and expected_outputs stay unchanged."
                    ),
                    "set_inputs": (
                        "Use only for an RFC 7396 value patch while source, input_schema, "
                        "and expected_outputs stay unchanged."
                    ),
                    "reconfigure_program": (
                        "Use when source, input_schema, inputs, or expected_outputs must be "
                        "replaced together; do not use it for a source-only or value-only edit."
                    ),
                },
                "revision_rule": (
                    "Guard every mutation with the latest working_revision returned by a write "
                    "or inspect_program. After a failed candidate this is the failed candidate "
                    "revision, not the still-live accepted_revision."
                ),
                "input_schema_templates": {
                    "no_inputs": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                    "stable_reference_property": {
                        "type": "object",
                        "x-cadex-reference": True,
                        "properties": {
                            "document_uid": {"type": "string"},
                            "object_name": {"type": "string"},
                        },
                        "required": ["document_uid", "object_name"],
                        "additionalProperties": False,
                    },
                },
            },
        }

    def validate_source(self, source: str) -> None:
        contracts.validate_program_source(source)

    def execute_candidate(
        self,
        prepared: dict[str, Any],
        *,
        cancellation_check: Callable[[], bool] | None,
    ) -> dict[str, Any]:
        return execute_candidate(prepared, cancellation_check=cancellation_check)

    def validate_result(
        self, prepared: dict[str, Any], execution: dict[str, Any]
    ) -> dict[str, Any]:
        return validate_candidate(prepared, execution)

    def publish(
        self,
        service: Any,
        prepared: dict[str, Any],
        validated: dict[str, Any],
    ) -> dict[str, Any]:
        return publish_candidate(service, prepared, validated)

    def inspect(
        self, captured: dict[str, Any], contract: dict[str, Any]
    ) -> dict[str, Any]:
        program = {
            key: contract.get(key)
            for key in (
                "program_id",
                "domain",
                "workbench",
                "label",
                "source",
                "input_schema",
                "inputs",
                "expected_outputs",
                "working_revision",
                "accepted_revision",
                "accepted_contract",
                "resolved_references",
                "live_outputs",
                "latest_candidate",
                "artifact_directory",
                "imported_from_schema",
                "migration_required",
                "migration_reason",
                "migration_action",
                "live_state",
            )
            if contract.get(key) not in (None, "", [], {})
        }
        input_controls = prune_controls(
            contract.get("input_controls"), contract.get("inputs") or {}
        )
        if input_controls:
            program["input_controls"] = input_controls
        working_revision = str(contract.get("working_revision") or "")
        accepted_revision = str(contract.get("accepted_revision") or "")
        latest_candidate = contract.get("latest_candidate")
        candidate_status = (
            str(latest_candidate.get("status") or "")
            if isinstance(latest_candidate, Mapping)
            else ""
        )
        accepted_is_current = bool(
            working_revision
            and accepted_revision
            and working_revision == accepted_revision
            and candidate_status == "accepted"
        )
        migration_required = bool(contract.get("migration_required"))
        # Adapters are shared across scripted engines, so self.pack is always the
        # xscript twin. Emit next-action hints for the engine that actually
        # served this call (xscript authors see xscript.* tools).
        engine_ns = getattr(captured.get("pack"), "engine", None) or self.pack.engine
        return {
            "ok": True,
            "program": program,
            "model_state": {
                "status": (
                    "reconfiguration_required"
                    if migration_required
                    else "accepted_current"
                    if accepted_is_current
                    else "working_candidate_not_accepted"
                ),
                "candidate_status": candidate_status,
                "accepted_is_current": accepted_is_current,
                "accepted_live_state_preserved": bool(accepted_revision),
                **({"migration_required": True} if migration_required else {}),
                "next_write_expected_revision": working_revision,
                "mutation_selection": {
                    "source_only": f"{engine_ns}.{self.pack.domain}.edit_source",
                    "input_values_only": f"{engine_ns}.{self.pack.domain}.set_inputs",
                    "contract_or_outputs": (
                        f"{engine_ns}.{self.pack.domain}.reconfigure_program"
                    ),
                },
                "instruction": (
                    "Replace the complete program contract with the domain-qualified "
                    "reconfigure_program tool. The prior accepted live objects remain "
                    "available until a valid v2 candidate is accepted."
                    if migration_required
                    else "If this candidate is not accepted, use latest_candidate.failure and "
                    "the accepted contract as the repair baseline, then make the narrowest "
                    "guarded mutation using next_write_expected_revision."
                    if not accepted_is_current
                    else "The accepted contract is current; verify domain-specific live evidence."
                ),
            },
        }

    def delete(
        self, service: Any, captured: dict[str, Any], contract: dict[str, Any]
    ) -> dict[str, Any]:
        del contract
        return delete_live_program(service, captured)


@dataclass
class PartDomainAdapter(DeclarativeDomainAdapter):
    """Production adapter for direct Part/OCC programs."""

    production_ready: bool = True

    def describe_api(self) -> dict[str, Any]:
        description = super().describe_api()
        description.update(
            {
                "api_contract": "cadex-xscript-part-api-v2",
                "units": {
                    "length": "millimetres",
                    "angle": "degrees",
                    "tolerance": "millimetres",
                },
                "coordinate_system": {
                    "handedness": "right-handed",
                    "default_axis": "+Z",
                    "vector_format": "[x, y, z]",
                },
                "evaluation_model": (
                    "API calls build an immutable declarative operation graph. Only values "
                    "reachable from result are evaluated in the isolated FreeCADCmd worker."
                ),
                "input_reference_contract": {
                    "purpose": (
                        "Use api.from_object only with a stable reference persisted in inputs. "
                        "The host snapshots that object's Shape, hashes it into the program "
                        "revision, and gives the worker only the detached BREP. A source Shape "
                        "change marks published outputs stale; regenerate with set_inputs using "
                        "the current guarded revision (the patch may repeat the current input "
                        "value)."
                    ),
                    "schema": {
                        "type": "object",
                        "x-cadex-reference": True,
                        "properties": {
                            "document_uid": {"type": "string", "minLength": 1},
                            "object_name": {"type": "string", "minLength": 1},
                        },
                        "required": ["document_uid", "object_name"],
                        "additionalProperties": False,
                    },
                    "source_example": (
                        "base = api.from_object(inputs['base'], output_type='solid')"
                    ),
                },
                "intermediate_types": ["edge"],
                "publication_types": list(self.pack.output_types),
                "accepted_output_facts": [
                    "shape_type and topology counts",
                    "length_mm, area_mm2, and volume_mm3",
                    "center_of_mass_mm when the topology defines mass properties",
                    "bounds_center_mm",
                    "axis-aligned bounds_mm",
                    "bounded 1-based face_details and edge_details for selectors",
                    "bounded operation_diagnostics such as general-fuse source fragment counts",
                ],
                "topology_selection": {
                    "index_base": 1,
                    "allowed": ["all", "non-empty arrays of positive indices"],
                    "guidance": (
                        "Use explicit indices for stable, intentional fillets, chamfers, and "
                        "thickness operations. Worker errors report the available index range. "
                        "The domain context's document_shapes contains bounded, 1-based face and "
                        "edge details plus copy-ready stable references. Re-inspect accepted "
                        "face_details and edge_details after every topology-changing regeneration "
                        "before reusing an index."
                    ),
                },
                "publication_contract": {
                    "identity": (
                        "Accepted outputs update the same document objects in place by stable "
                        "program/output identity."
                    ),
                    "whole_object_links": (
                        "Whole-object links remain attached and compatible derived engineering "
                        "consumers are explicitly marked stale for recomputation."
                    ),
                    "subelement_links": (
                        "Publication and deletion reject external Face/Edge/Vertex links because "
                        "direct Part topology indices are transient across regeneration."
                    ),
                    "protected_consumers": [
                        "FEM",
                        "CAM",
                        "TechDraw",
                        "Robot",
                        "Inspection",
                    ],
                },
                "operation_groups": {
                    "references": ["from_object"],
                    "primitives": [
                        "box",
                        "wedge",
                        "plane",
                        "prism",
                        "cylinder",
                        "cone",
                        "sphere",
                        "torus",
                    ],
                    "curves": [
                        "line",
                        "arc",
                        "circle",
                        "ellipse",
                        "bezier",
                        "bspline",
                        "nurbs_curve",
                        "helix",
                    ],
                    "topology": [
                        "wire",
                        "face",
                        "shell",
                        "solid",
                        "compound",
                        "subshape",
                        "slice",
                        "defeature",
                        "to_nurbs",
                        "reverse",
                        "sew",
                        "repair",
                    ],
                    "generators": [
                        "extrude",
                        "revolve",
                        "loft",
                        "sweep",
                        "ruled_surface",
                        "filled_surface",
                    ],
                    "booleans": [
                        "fuse",
                        "cut",
                        "common",
                        "section",
                        "general_fuse",
                    ],
                    "finishing": [
                        "fillet",
                        "chamfer",
                        "offset",
                        "offset2d",
                        "thicken",
                        "refine",
                    ],
                    "placement": ["transform", "mirror"],
                    "projection": ["project"],
                },
                "operation_selection": {
                    "existing_document_shape": (
                        "api.from_object; copy one stable reference from document_shapes "
                        "context and declare the exact source topology type"
                    ),
                    "analytic_or_regular_primitive": (
                        "the single matching primitive: api.box, api.wedge, api.plane, "
                        "api.prism, api.cylinder, api.cone, api.sphere, or api.torus"
                    ),
                    "single_curve_or_edge": (
                        "the single matching curve constructor: api.line, api.arc, "
                        "api.circle, api.ellipse, api.bezier, api.bspline, "
                        "api.nurbs_curve, or api.helix"
                    ),
                    "ordered_edge_chain_or_polyline": (
                        "api.wire; pass ordered Part edge values for curved paths or "
                        "ordered 3D points for a polygonal path"
                    ),
                    "planar_region_with_optional_holes": "api.face",
                    "faces_to_shell": "api.shell when faces already meet; api.sew when they need tolerance-based sewing",
                    "closed_shell_to_solid": "api.solid",
                    "unfused_multi_shape_result": "api.compound",
                    "one_indexed_topology_item": "api.subshape",
                    "linear_generator": "api.extrude",
                    "rotational_generator": "api.revolve",
                    "multiple_cross_sections": "api.loft",
                    "one_or_more_profiles_along_path": (
                        "api.sweep; pass one wire or an ordered wire sequence to the single "
                        "profile parameter"
                    ),
                    "straight_surface_between_two_boundaries": "api.ruled_surface",
                    "surface_spanning_ordered_boundaries": "api.filled_surface",
                    "boolean_union": "api.fuse",
                    "boolean_subtraction": "api.cut",
                    "boolean_intersection_volume": "api.common",
                    "intersection_edges_only": "api.section",
                    "all_touching_boolean_fragments_with_provenance": "api.general_fuse",
                    "parallel_planar_cross_sections": "api.slice",
                    "remove_selected_feature_faces_and_heal": "api.defeature",
                    "convert_analytic_geometry_to_nurbs": "api.to_nurbs",
                    "reverse_topology_orientation": "api.reverse",
                    "join_touching_faces_or_shells": "api.sew",
                    "repair_invalid_topology_with_bounded_tolerances": "api.repair",
                    "round_selected_edges": "api.fillet",
                    "bevel_selected_edges": "api.chamfer",
                    "three_dimensional_skin_offset": "api.offset",
                    "planar_wire_or_face_offset": "api.offset2d",
                    "remove_faces_and_make_a_thin_solid": "api.thicken",
                    "translate_rotate_or_scale": "api.transform",
                    "reflect_across_a_plane": "api.mirror",
                    "project_profile_onto_target": "api.project",
                    "remove_redundant_boolean_splitters": "api.refine",
                    "redundancy_contract": (
                        "Use only runtime_exports. api.helix(representation=...) is the one "
                        "helix operation; api.project(mode=...) is the one projection "
                        "operation; api.transform is the one translate/rotate/scale "
                        "operation. Use one n-ary fuse, cut, common, or general_fuse call "
                        "instead of avoidable chains. Boolean refine=True already removes "
                        "splitters, so do not add api.refine unless a later operation created "
                        "new redundant topology. There are no model-facing long-helix, "
                        "parallel/perspective projection, translate, rotate, scale, add, "
                        "update, or refresh aliases."
                    ),
                },
                "composition_contract": {
                    "graph_identity": (
                        "Every API call returns one immutable graph value. Bind it once and "
                        "reuse that exact variable wherever the same shape participates in "
                        "multiple downstream operations or outputs."
                    ),
                    "construction_order": [
                        "Create or snapshot the minimum source topology.",
                        "Build wires/faces and use one generator when that expresses the intent.",
                        "Apply booleans before edge finishing so edge indexes refer to the final coarse topology.",
                        "Apply fillets, chamfers, offsets, thickness, and refinement last.",
                        "Return only semantic publication outputs; edge is an intermediate type and cannot be published.",
                    ],
                    "declared_topology": (
                        "Set output_type whenever an operation can legitimately produce more "
                        "than one topology class. The worker rejects a declaration that does "
                        "not match the validated OCC result; never choose a type merely to "
                        "satisfy expected_outputs."
                    ),
                    "tolerance_policy": (
                        "Start booleans at tolerance=0. Use the smallest explicit fuzzy or "
                        "repair tolerance justified by the failure; never use a large "
                        "tolerance as a generic retry."
                    ),
                    "topology_index_lifetime": (
                        "Face/Edge indexes belong only to the exact shape facts that reported "
                        "them. Any boolean, offset, repair, transformGeometry, defeature, "
                        "fillet, chamfer, thicken, sew, or refine result requires fresh facts "
                        "before selecting another index."
                    ),
                },
                "model_verification_contract": {
                    "after_write": (
                        "Call the write response's verification_call. Confirm the accepted "
                        "and working revisions match, then verify every output's declared "
                        "shape_type, validity, topology counts, volume/area/length as "
                        "applicable, and bounds against the design intent."
                    ),
                    "selection_repair": (
                        "For an index failure, use the reported available 1-based range and "
                        "the latest accepted face_details/edge_details. Change only the exact "
                        "selector; never cycle through guessed indexes."
                    ),
                    "kernel_repair": (
                        "Read the named api.operation and exact parameter/OCC message. Repair "
                        "the smallest cause against next_write_expected_revision. The prior "
                        "accepted objects remain live while the rejected candidate is retained."
                    ),
                },
                "workbench_handoffs": {
                    "part_design": (
                        "Part publishes direct BREP, not a Body feature history. If the user "
                        "needs editable sketches and ordered Body features, ask the human to "
                        "switch to Part Design; do not imitate that API here."
                    ),
                    "sketcher": (
                        "Use Sketcher for solver-constrained 2D definitions. Part wires are "
                        "explicit geometry and carry no constraint graph."
                    ),
                    "rule": (
                        "The model cannot switch workbench or engine. Explain the required "
                        "handoff and ask the human to switch; never call or describe another "
                        "domain from this Part surface."
                    ),
                },
                "recommended_patterns": [
                    {
                        "goal": "modify an existing document solid without live-document access",
                        "source": (
                            "base = api.from_object(inputs['base'], output_type='solid')\n"
                            "result = {'Refined': api.refine(base, label='Refined')}"
                        ),
                        "input_schema_property": {
                            "base": {
                                "type": "object",
                                "x-cadex-reference": True,
                                "properties": {
                                    "document_uid": {"type": "string", "minLength": 1},
                                    "object_name": {"type": "string", "minLength": 1},
                                },
                                "required": ["document_uid", "object_name"],
                                "additionalProperties": False,
                            }
                        },
                        "expected_outputs": [{"name": "Refined", "type": "solid"}],
                    },
                    {
                        "goal": "parametric housing with a bore",
                        "source": (
                            "base = api.box(inputs['length'], inputs['width'], "
                            "inputs['height'])\n"
                            "bore = api.cylinder(inputs['bore_radius'], inputs['height'], "
                            "origin=[inputs['length']/2, inputs['width']/2, 0])\n"
                            "housing = api.cut(base, bore, label='Housing')\n"
                            "result = {'Housing': housing}"
                        ),
                        "expected_outputs": [{"name": "Housing", "type": "solid"}],
                    },
                    {
                        "goal": "solid loft between closed profiles",
                        "source": (
                            "lower = api.wire([[0,0,0],[20,0,0],[20,12,0],[0,12,0]], "
                            "closed=True)\n"
                            "upper = api.wire([[3,2,30],[17,2,30],[17,10,30],[3,10,30]], "
                            "closed=True)\n"
                            "body = api.loft([lower, upper], solid=True, "
                            "output_type='solid', label='Body')\n"
                            "result = {'Body': body}"
                        ),
                        "expected_outputs": [{"name": "Body", "type": "solid"}],
                    },
                    {
                        "goal": "variable-section solid swept along one path",
                        "source": (
                            "lower = api.wire([api.circle(inputs['lower_radius'])])\n"
                            "upper = api.wire([api.circle(inputs['upper_radius'], "
                            "center=[0,0,inputs['height']])])\n"
                            "path = api.wire([[0,0,0],[0,0,inputs['height']]])\n"
                            "body = api.sweep([lower, upper], path, solid=True, "
                            "output_type='solid', label='Variable Section Body')\n"
                            "result = {'Body': body}"
                        ),
                        "expected_outputs": [{"name": "Body", "type": "solid"}],
                    },
                ],
                "error_contract": {
                    "validation": (
                        "Source-side argument failures identify api.operation and the exact "
                        "parameter path before OCC runs and provide one exact correction."
                    ),
                    "kernel": (
                        "Worker failures identify api.operation, preserve the OCC exception "
                        "type/message, provide one actionable correction, and retain the "
                        "rejected candidate for inspection."
                    ),
                },
                "deliberate_binding_exclusions": [
                    {
                        "binding": "Part.makeShellFromWires",
                        "reason": (
                            "This FreeCAD build can terminate FreeCADCmd instead of raising a "
                            "catchable exception. Use face, shell, sew, loft, or filled_surface."
                        ),
                    },
                    {
                        "binding": "TopoShape.makeWires",
                        "reason": (
                            "This FreeCAD build can terminate FreeCADCmd. Use api.wire with "
                            "ordered edges or points."
                        ),
                    },
                    {
                        "binding": "TopoShape.removeInternalWires",
                        "reason": (
                            "This FreeCAD build can terminate FreeCADCmd. Construct explicit "
                            "outer and hole wires with api.face instead."
                        ),
                    },
                    {
                        "binding": "Part.makeThread / TopoShape.makeTube",
                        "reason": (
                            "Observed return topology and bounds are inconsistent with their "
                            "public binding documentation in this build, so they are not exposed."
                        ),
                    },
                ],
            }
        )
        return description


@dataclass
class PartDesignDomainAdapter(DeclarativeDomainAdapter):
    """Production adapter for source-parametric Part Design programs."""

    production_ready: bool = True

    def describe_api(self) -> dict[str, Any]:
        description = super().describe_api()
        description.update(
            {
                "api_contract": "cadex-xscript-partdesign-api-v2",
                "units": {"length": "millimetres", "angle": "degrees"},
                "evaluation_model": (
                    "API calls build one immutable Body/sketch/feature graph. The graph "
                    "is evaluated as native PartDesign and Sketcher objects in an isolated "
                    "FreeCADCmd document; only exact validated single-solid BREP tips cross "
                    "the publication boundary."
                ),
                "profile_contract": {
                    "geometry": (
                        "Create geometry with point/line/arc/circle/ellipse/bspline and "
                        "constraints with api.constraint, then pass those exact graph values "
                        "to api.sketch."
                    ),
                    "invariants": (
                        "Set require_fully_constrained and require_closed_profile whenever "
                        "the downstream feature depends on those invariants. Solver conflicts, "
                        "redundancy, malformed constraints, DoF, and profile readiness are "
                        "validated in the worker."
                    ),
                },
                "feature_contract": {
                    "additive": ["pad", "revolve", "loft"],
                    "subtractive": ["pocket", "groove", "loft(subtractive=True)"],
                    "transform": ["polar_pattern", "mirror"],
                    "dressup": ["fillet", "chamfer"],
                    "publication": (
                        "Return api.body(final_feature, ...) for every declared solid. "
                        "Keep result names stable across regeneration."
                    ),
                },
                "operation_selection": {
                    "profile_geometry": (
                        "Use point, line, arc, circle, ellipse, bspline, and "
                        "external_geometry only for the exact native curve type needed."
                    ),
                    "profile_constraints": (
                        "Use the single api.constraint operation for geometric and "
                        "dimensional intent; do not recreate geometry or invent native indexes."
                    ),
                    "add_material": "pad, revolve, loft(subtractive=False)",
                    "remove_material": "pocket, groove, loft(subtractive=True)",
                    "repeat_or_reflect": "polar_pattern or mirror",
                    "edge_finish": "fillet or chamfer with one geometric query",
                    "publish": "api.body",
                    "redundancy_contract": (
                        "Each native feature family has one model-facing operation. There "
                        "are no rectangle, box, add-feature, recompute, update, or output "
                        "aliases. Compose profiles from explicit geometry, reuse graph values, "
                        "and publish only the final feature through api.body."
                    ),
                },
                "semantic_interfaces": {
                    "purpose": (
                        "Declare mating, datum, load, drawing, and machining references in "
                        "api.body(interfaces=...). Origin or geometric query selections are "
                        "resolved against the accepted solid in the worker; raw FaceN/EdgeN "
                        "interface declarations are forbidden."
                    ),
                    "selection_modes": ["origin", "query"],
                },
                "publication_contract": {
                    "identity": (
                        "Each program/output pair owns one stable native publication identity "
                        "updated in place after worker validation."
                    ),
                    "shape": "exact OCC Solid containing exactly one valid solid",
                    "gui_thread": (
                        "The document thread applies detached validated shapes and metadata "
                        "only; it performs no provider wait, subprocess wait, recompute-heavy "
                        "feature construction, or artifact I/O."
                    ),
                },
                "workbench_handoffs": {
                    "sketcher": (
                        "Use Sketcher when the requested result is an independently editable "
                        "2D constraint definition rather than a Body feature history."
                    ),
                    "part": (
                        "Use Part for direct OCC construction without a PartDesign::Body "
                        "history."
                    ),
                    "assembly": (
                        "Use Assembly to link accepted components, ground instances, add "
                        "joints, and solve motion. Part Design publishes component geometry "
                        "and semantic interfaces; it does not position an assembly."
                    ),
                    "rule": (
                        "The model cannot switch workbench or engine. Explain the exact "
                        "handoff and ask the human to switch when the requested result belongs "
                        "to another domain."
                    ),
                },
                "error_contract": {
                    "source_or_contract": (
                        "Correct the exact policy, schema, graph, or output declaration named "
                        "by the failure; do not broaden the source or change unrelated inputs."
                    ),
                    "sketch": (
                        "Use the returned graph ids, constraint names, solver sets, DoF, and "
                        "profile openings to correct only the failing profile intent."
                    ),
                    "feature": (
                        "Use feature_history and native validation evidence to correct the "
                        "first invalid feature; the accepted revision remains live."
                    ),
                    "publication": (
                        "A reference-preflight or stale-consumer rejection is not permission "
                        "to delete a consumer. Preserve its semantic reference or ask the human."
                    ),
                },
                "recommended_patterns": [
                    {
                        "goal": "fully constrained parametric rectangular Body",
                        "source": (
                            "bottom = api.line([0,0], [inputs['width'],0], name='Bottom')\n"
                            "right = api.line([inputs['width'],0], "
                            "[inputs['width'],inputs['depth']], name='Right')\n"
                            "top = api.line([inputs['width'],inputs['depth']], "
                            "[0,inputs['depth']], name='Top')\n"
                            "left = api.line([0,inputs['depth']], [0,0], name='Left')\n"
                            "constraints = [\n"
                            " api.constraint('coincident',[{'geometry':bottom,'point':'end'},"
                            "{'geometry':right,'point':'start'}]),\n"
                            " api.constraint('coincident',[{'geometry':right,'point':'end'},"
                            "{'geometry':top,'point':'start'}]),\n"
                            " api.constraint('coincident',[{'geometry':top,'point':'end'},"
                            "{'geometry':left,'point':'start'}]),\n"
                            " api.constraint('coincident',[{'geometry':left,'point':'end'},"
                            "{'geometry':bottom,'point':'start'}]),\n"
                            " api.constraint('horizontal',[bottom]),\n"
                            " api.constraint('horizontal',[top]),\n"
                            " api.constraint('vertical',[right]),\n"
                            " api.constraint('vertical',[left]),\n"
                            " api.constraint('distance',[bottom],value=inputs['width'],name='Width'),\n"
                            " api.constraint('distance',[right],value=inputs['depth'],name='Depth'),\n"
                            " api.constraint('coincident',[{'geometry':bottom,'point':'start'},"
                            "'origin'],name='Anchored'),\n"
                            "]\n"
                            "profile = api.sketch([bottom,right,top,left], constraints, "
                            "require_fully_constrained=True, require_closed_profile=True, "
                            "label='Base Profile')\n"
                            "base = api.pad(profile, inputs['height'], label='Base Pad')\n"
                            "result = {'Part': api.body(base, interfaces={'Top': {"
                            "'selection': {'type':'query','element_type':'face',"
                            "'expected_count':1,'geometry_type':'plane','normal':[0,0,1]},"
                            "'description':'Top mating face'}}, label='Part')}"
                        ),
                        "expected_outputs": [{"name": "Part", "type": "solid"}],
                    }
                ],
            }
        )
        return description


@dataclass
class SketcherDomainAdapter(DeclarativeDomainAdapter):
    """Dedicated adapter for native constrained Sketcher programs."""

    production_ready: bool = True

    def describe_api(self) -> dict[str, Any]:
        description = super().describe_api()
        description.update(
            {
                "api_contract": "cadex-xscript-sketcher-api-v1",
                "units": {
                    "coordinates": "millimetres on the sketch plane",
                    "distance_constraints": "millimetres",
                    "angle_constraints": "degrees",
                    "attachment_position": "millimetres",
                },
                "evaluation_model": (
                    "API calls build one immutable geometry/constraint graph. Geometry "
                    "and constraints receive stable graph handles for that execution; "
                    "constraints must reuse the exact geometry variables included in "
                    "api.sketch. FreeCADCmd constructs a real Sketcher::SketchObject, "
                    "adds all constraints as one no-solve batch, solves once, and returns "
                    "native DoF, conflict, redundancy, residual, and profile diagnostics."
                ),
                "geometry": {
                    "point": (
                        "native construction point by default; select it with "
                        "{'geometry': point, 'point': 'point'}"
                    ),
                    "line": "finite segment with start/end point selectors",
                    "arc": "circular arc through three non-collinear points",
                    "circle": "full circle with center selector",
                    "ellipse": "full rotated ellipse with center selector",
                    "elliptic_arc": (
                        "trimmed ellipse; start/end are OCC curve parameters in radians"
                    ),
                    "hyperbolic_arc": (
                        "trimmed hyperbola; start/end are bounded dimensionless OCC parameters"
                    ),
                    "parabolic_arc": (
                        "trimmed parabola from vertex and focal length; start/end are "
                        "signed curve parameters in millimetres"
                    ),
                    "bspline": (
                        "interpolated B-spline by default; supply degree, strictly increasing "
                        "knots, OCC multiplicities, and optional positive weights for exact NURBS"
                    ),
                    "external_geometry": (
                        "native projected construction geometry linked to exactly one stable "
                        "EdgeN/VertexN or one host-authenticated published semantic interface"
                    ),
                    "construction": (
                        "Set construction=True on any geometry that should constrain the graph "
                        "without contributing to the published profile."
                    ),
                },
                "operation_selection": {
                    "isolated_reference_point": "api.point; construction=True is the default",
                    "straight_segment": "api.line",
                    "circular_arc_through_three_points": "api.arc",
                    "full_circle": "api.circle",
                    "full_ellipse": "api.ellipse",
                    "trimmed_ellipse": "api.elliptic_arc",
                    "trimmed_hyperbola": "api.hyperbolic_arc",
                    "trimmed_parabola": "api.parabolic_arc",
                    "interpolated_or_exact_nurbs_curve": "api.bspline",
                    "stable_projected_edge_or_vertex": "api.external_geometry",
                    "any_geometric_dimensional_or_annotation_relation": (
                        "api.constraint(kind, entities, ...); choose kind and the exact entity "
                        "form from constraint_forms"
                    ),
                    "published_native_sketch": (
                        "api.sketch; assemble the exact geometry variables and constraint "
                        "variables once, then return this single sketch output"
                    ),
                    "redundancy_contract": (
                        "There is one geometry operation per native curve family, one "
                        "api.constraint operation for every constraint kind, and one api.sketch "
                        "assembly operation. There are no model-facing rectangle, polyline, "
                        "lock, per-constraint, add, update, solve, or recompute aliases. Build "
                        "rectangles and polylines from named lines plus explicit coincidence "
                        "constraints. Express a fixed point with distance_x/distance_y or a "
                        "coincidence to origin, and use block only when the explicit intent is "
                        "to freeze an entire geometry. Never add both radius and diameter, "
                        "duplicate dimensions, or a reference and driving copy of the same intent."
                    ),
                },
                "entity_selectors": {
                    "whole_geometry": "Pass the geometry value directly.",
                    "point": (
                        "Pass {'geometry': value, 'point': 'point|start|end|center'}; valid "
                        "points depend on the geometry type and are checked before execution."
                    ),
                    "external": ["x_axis", "y_axis", "origin"],
                    "graph_identity": (
                        "A constraint may only reference the exact geometry values listed in "
                        "the same api.sketch call. Equivalent recreated values are rejected."
                    ),
                },
                "external_geometry_contract": {
                    "input": (
                        "Pass the source object through an x-cadex-reference input; source "
                        "code receives only its stable document_uid/object_name identity."
                    ),
                    "stable_native_selection": (
                        "Use 'EdgeN', 'VertexN', or the equivalent subelements selection only "
                        "when context marks the native source topology as non-transient."
                    ),
                    "regenerating_selection": {
                        "schema": {
                            "type": "published_interface",
                            "interface_name": "DatumEdge",
                        },
                        "rule": (
                            "A regenerating scripted source requires one named published "
                            "interface resolving to exactly one edge or vertex. Raw EdgeN/"
                            "VertexN is rejected and the error lists available interfaces."
                        ),
                    },
                    "projection_modes": {
                        "defining": (
                            "True asks Sketcher to treat the projected geometry as defining "
                            "external geometry; False is the normal dependent projection."
                        ),
                        "intersection": (
                            "True requests the native intersection projection mode. The "
                            "candidate is rejected unless FreeCAD produces exactly one native "
                            "external geometry value."
                        ),
                    },
                    "identity": (
                        "The accepted Sketcher::SketchObject owns a real native external link. "
                        "Its graph id maps deterministically to native ids -3, -4, ...; -1/-2 "
                        "remain the native sketch axes."
                    ),
                },
                "constraints": {
                    "geometric": [
                        "coincident",
                        "horizontal",
                        "vertical",
                        "parallel",
                        "perpendicular",
                        "tangent",
                        "equal",
                        "point_on_object",
                        "symmetric",
                        "block",
                    ],
                    "dimensional": [
                        "distance",
                        "distance_x",
                        "distance_y",
                        "angle",
                        "angle_via_point",
                        "radius",
                        "diameter",
                        "weight",
                        "snells_law",
                    ],
                    "advanced": ["internal_alignment", "group", "text"],
                    "internal_alignment": {
                        "ellipse": [
                            "ellipse_major_diameter",
                            "ellipse_minor_diameter",
                            "ellipse_focus1",
                            "ellipse_focus2",
                        ],
                        "hyperbola": [
                            "hyperbola_major_diameter",
                            "hyperbola_minor_diameter",
                            "hyperbola_focus",
                        ],
                        "parabola": ["parabola_focus", "parabola_focal_axis"],
                        "bspline": ["bspline_control_point", "bspline_knot_point"],
                        "index_safety": (
                            "B-spline internal_index is zero-based and checked against the "
                            "actual native pole/knot count before FreeCAD sees the constraint."
                        ),
                    },
                    "annotation_constraints": {
                        "group": (
                            "First entity must be the whole group line; remaining entities "
                            "are stored in order."
                        ),
                        "text": (
                            "First entity must be the whole group line; text and font must "
                            "be non-empty and text_height selects height versus size semantics."
                        ),
                    },
                    "state": {
                        "name": "stable identifier used by expressions and inspection",
                        "expression": (
                            "expression for a driving dimensional constraint; an expression "
                            "cannot drive a reference constraint"
                        ),
                        "driving": "False creates a reference dimension",
                        "active": "False preserves an explicitly inactive native constraint",
                        "virtual": "True places the constraint in virtual space",
                    },
                },
                "constraint_forms": {
                    "notation": {
                        "whole": "pass the geometry variable itself",
                        "point": (
                            "{'geometry': geometry_variable, 'point': "
                            "'point|start|end|center'}"
                        ),
                        "external": "'x_axis', 'y_axis', or 'origin'",
                        "dimensional_value": (
                            "pass value=...; angles use degrees and distances use millimetres"
                        ),
                    },
                    "coincident": "[point, point]",
                    "horizontal": "[whole line]",
                    "vertical": "[whole line]",
                    "parallel": "[whole line, whole line]",
                    "perpendicular": (
                        "[whole line, whole line], [point on first, whole line], or two points"
                    ),
                    "tangent": (
                        "[whole curve, whole curve], [point on first, whole curve], or two points"
                    ),
                    "distance": (
                        "[whole line] for length, or [point, point] for point distance; value required"
                    ),
                    "distance_x": "[point] from origin or [point, point]; value required",
                    "distance_y": "[point] from origin or [point, point]; value required",
                    "angle": (
                        "[whole line/arc], [whole curve, whole curve], or [point, point]; value required"
                    ),
                    "angle_via_point": (
                        "[whole curve, whole curve, point]; value required"
                    ),
                    "radius": "[whole arc/circle]; value required",
                    "diameter": "[whole arc/circle]; value required",
                    "equal": "[whole geometry, whole geometry]",
                    "point_on_object": "[point, whole geometry or axis]",
                    "symmetric": "[point, point, symmetry point or axis]",
                    "block": "[whole geometry]",
                    "weight": (
                        "[whole construction circle used as a B-spline handle]; positive value required"
                    ),
                    "snells_law": (
                        "[point, point, whole interface line]; positive ratio value required"
                    ),
                    "internal_alignment": (
                        "two entities in the alignment-specific order documented under "
                        "constraints.internal_alignment; set alignment and, for B-splines, "
                        "internal_index"
                    ),
                    "group": "[whole group line, then ordered member entities]",
                    "text": (
                        "[whole group line, then ordered member entities]; set non-empty text/font"
                    ),
                },
                "composition_contract": {
                    "graph_identity": (
                        "Bind every geometry and constraint API result once. Constraints must "
                        "reuse those exact variables, and api.sketch must receive the same "
                        "geometry values; recreating equivalent geometry creates a different "
                        "graph identity and is rejected."
                    ),
                    "authoring_order": [
                        "Create minimal named geometry at numerically sensible initial coordinates.",
                        "Add topological relations such as coincidence, point-on-object, tangent, and symmetry.",
                        "Add orientation and equality relations only where the design intent requires them.",
                        "Add the minimum named driving dimensions and one intentional anchor; coordinates alone do not constrain the solver.",
                        "Use construction geometry for references and set explicit acceptance requirements on api.sketch.",
                    ],
                    "closure": (
                        "Equal endpoint coordinates can make a visual loop but do not encode "
                        "parametric connectivity. Use explicit coincident constraints at intended "
                        "joints and require_closed_profile=True for downstream profiles."
                    ),
                    "naming": (
                        "Give semantic unique names to important geometry and every driving "
                        "dimension. Native indexes are diagnostics only; edit source by stable "
                        "graph_id/name evidence, never by guessing an index."
                    ),
                    "single_output": (
                        "One program publishes exactly one native sketch. Put multiple related "
                        "profiles in that sketch only when they share one constraint graph; "
                        "otherwise use separate programs."
                    ),
                },
                "model_verification_contract": {
                    "after_write": (
                        "Call verification_call, confirm accepted_revision equals working_revision, "
                        "then inspect solver_code, DoF, conflict sets, named constraint readback, "
                        "wire counts, profile_ready, support, and the live Sketcher::SketchObject identity."
                    ),
                    "underconstrained": (
                        "underconstraint_guidance is a bounded native heuristic, not a recipe. "
                        "Apply only the smallest intent-compatible connectivity set first and "
                        "regenerate; then consider orientation/equality one category at a time. "
                        "Finish with explicit dimensions/anchoring. Never apply every suggestion in one edit."
                    ),
                    "solver_repair": (
                        "Use constraint_issues to identify exact graph_id/name/kind records. "
                        "Repair or remove only those constraints; use driving=False when the "
                        "intent is measurement, then regenerate against next_write_expected_revision."
                    ),
                    "profile_repair": (
                        "Use profile_open_vertices to map native openings to stable graph "
                        "endpoints. Correct those source coordinates or add the intended "
                        "coincidence, then verify profile_ready rather than adding a guessed closer."
                    ),
                },
                "workbench_handoffs": {
                    "part_design": (
                        "Sketcher publishes the constrained 2D definition only. A Body feature "
                        "such as pad, pocket, revolve, or additive/subtractive feature requires "
                        "Part Design."
                    ),
                    "part": (
                        "Use Part for direct 3D BREP construction; a Sketcher program does not "
                        "extrude, fuse, fillet, or publish solids."
                    ),
                    "rule": (
                        "The model cannot switch workbench or engine. Explain the required "
                        "handoff and ask the human to switch; never call or describe another "
                        "domain from this Sketcher surface."
                    ),
                },
                "support_contract": {
                    "input": (
                        "Persist the support object as an x-cadex-reference input. The host "
                        "detaches and hashes its Shape into the candidate revision."
                    ),
                    "stable_native_selection": {
                        "type": "subelements",
                        "schema": {
                            "type": "subelements",
                            "subelements": ["Face6"],
                        },
                        "rule": (
                            "Raw FaceN/EdgeN/VertexN names are accepted only on non-scripted "
                            "native snapshots whose topology is not marked transient."
                        ),
                    },
                    "regenerating_selection": {
                        "type": "published_interface",
                        "schema": {
                            "type": "published_interface",
                            "interface_name": "TopPlane",
                        },
                        "rule": (
                            "Regenerating scripted sources require a host-authenticated named "
                            "semantic interface; raw topology is rejected."
                        ),
                    },
                    "map_mode": (
                        "Use the native attachment mode appropriate to the selected support, "
                        "for example FlatFace for a planar FaceN."
                    ),
                    "attachment_offset": (
                        "Use {'position':[x,y,z], 'rotation':[x,y,z,w]}; the quaternion is "
                        "normalized and exercised in the isolated native document."
                    ),
                },
                "acceptance_requirements": {
                    "require_fully_constrained": (
                        "Reject the candidate when native DoF is non-zero. Failure details "
                        "include remaining DoF, exact solver sets, and bounded stable-reference "
                        "underconstraint guidance."
                    ),
                    "require_closed_profile": (
                        "Reject unless every non-construction output wire is closed and at "
                        "least one wire exists. Failure details map native open vertices back "
                        "to candidate stable graph endpoints."
                    ),
                },
                "native_diagnostics": [
                    "solver_code and degrees_of_freedom",
                    "fully_constrained",
                    "conflicting, redundant, partially redundant, and malformed indexes",
                    "finite per-constraint residuals plus explicit unavailable residuals",
                    "geometry/constraint readback with names and state",
                    "bounded intent-required underconstraint suggestions with duplicate filtering",
                    "open profile vertices mapped to stable source graph endpoints",
                    "edge, wire, closed/open wire, construction, and profile counts",
                    "resolved support identity, semantic selection, and attachment",
                ],
                "publication_contract": {
                    "native_type": "Sketcher::SketchObject",
                    "identity": (
                        "The same program/output identity updates the same native sketch in "
                        "place across accepted revisions and save/reopen."
                    ),
                    "asynchronous_boundary": (
                        "Geometry construction, expression evaluation, attachment evaluation, "
                        "solver work, and profile validation occur in FreeCADCmd. Live "
                        "publication uses no-solve deletion and one no-solve constraint batch, "
                        "does not recompute, and verifies native readback before commit."
                    ),
                    "consumers": (
                        "Whole-object native links remain attached. Regeneration is rejected "
                        "while a foreign consumer holds transient Edge/Vertex references."
                    ),
                },
                "recommended_patterns": [
                    {
                        "goal": "fully constrained rectangular Part Design profile",
                        "source": (
                            "bottom = api.line([0,0], [inputs['w'],0], name='Bottom')\n"
                            "right = api.line([inputs['w'],0], [inputs['w'],inputs['h']], "
                            "name='Right')\n"
                            "top = api.line([inputs['w'],inputs['h']], [0,inputs['h']], "
                            "name='Top')\n"
                            "left = api.line([0,inputs['h']], [0,0], name='Left')\n"
                            "def p(g, which): return {'geometry':g,'point':which}\n"
                            "constraints = [\n"
                            " api.constraint('coincident',[p(bottom,'end'),p(right,'start')]),\n"
                            " api.constraint('coincident',[p(right,'end'),p(top,'start')]),\n"
                            " api.constraint('coincident',[p(top,'end'),p(left,'start')]),\n"
                            " api.constraint('coincident',[p(left,'end'),p(bottom,'start')]),\n"
                            " api.constraint('horizontal',[bottom]),\n"
                            " api.constraint('horizontal',[top]),\n"
                            " api.constraint('vertical',[right]),\n"
                            " api.constraint('vertical',[left]),\n"
                            " api.constraint('distance',[bottom],value=inputs['w'],name='Width'),\n"
                            " api.constraint('distance',[right],value=inputs['h'],name='Height'),\n"
                            " api.constraint('coincident',[p(bottom,'start'),'origin']),\n"
                            "]\n"
                            "profile = api.sketch([bottom,right,top,left], constraints, "
                            "require_fully_constrained=True, require_closed_profile=True)\n"
                            "result = {'Profile': profile}"
                        ),
                        "expected_outputs": [{"name": "Profile", "type": "sketch"}],
                    },
                    {
                        "goal": "attach to a stable native planar face",
                        "source": (
                            "circle = api.circle([0,0], inputs['radius'], "
                            "name='ProfileCircle')\n"
                            "radius = api.constraint('radius', [circle], "
                            "value=inputs['radius'], name='Radius')\n"
                            "center = api.constraint('coincident', [{"
                            "'geometry':circle,'point':'center'}, 'origin'], "
                            "name='Centered')\n"
                            "profile = api.sketch([circle], [radius, center], support={"
                            "'reference':inputs['support'],'selection':{"
                            "'type':'subelements','subelements':['Face6']}}, "
                            "map_mode='FlatFace', require_fully_constrained=True, "
                            "require_closed_profile=True, label='Attached Profile')\n"
                            "result = {'Profile': profile}"
                        ),
                        "expected_outputs": [{"name": "Profile", "type": "sketch"}],
                    },
                    {
                        "goal": "constrain local geometry to a stable external edge",
                        "source": (
                            "external = api.external_geometry(inputs['source'], 'Edge1', "
                            "name='DatumEdge')\n"
                            "line = api.line([0,0], [inputs['length'],0], name='DrivenLine')\n"
                            "constraint = api.constraint('coincident', [{"
                            "'geometry':line,'point':'start'}, {'geometry':external,"
                            "'point':'start'}], name='OnDatum')\n"
                            "profile = api.sketch([external,line], [constraint])\n"
                            "result = {'Profile': profile}"
                        ),
                        "expected_outputs": [{"name": "Profile", "type": "sketch"}],
                    },
                ],
                "error_contract": {
                    "source": (
                        "Argument failures name api.operation and the exact parameter path, "
                        "including entity-count/point-shape mismatches and graph membership."
                    ),
                    "support": (
                        "Support failures identify the stable object, requested selector, "
                        "available topology/interface names, source kind, and correction."
                    ),
                    "external_geometry": (
                        "External-reference failures distinguish input authentication, raw-"
                        "topology stability, selector bounds, native projection cardinality, "
                        "and live-link readback. Details include the graph id, source identity, "
                        "resolved subelement, available semantic interfaces, and correction."
                    ),
                    "solver": (
                        "Rejected candidates retain the failing stage, DoF, exact conflict/"
                        "redundancy/malformed graph records, constraint readback, bounded "
                        "residuals, underconstraint guidance, profile endpoint guidance, and "
                        "a correction while the accepted revision stays live."
                    ),
                },
            }
        )
        return description


@dataclass
class AssemblyDomainAdapter(DeclarativeDomainAdapter):
    """Dedicated adapter for native linked-component Assembly programs."""

    production_ready: bool = True

    def describe_api(self) -> dict[str, Any]:
        description = super().describe_api()
        description.update(
            {
                "api_contract": "cadex-xscript-assembly-api-v1",
                "units": {
                    "length": "millimetres",
                    "angle": "degrees",
                    "simulation_time": "seconds",
                    "angular_motion_formula": "radians",
                    "linear_motion_formula": "millimetres",
                },
                "coordinate_system": {
                    "handedness": "right-handed",
                    "placement": {
                        "position": "[x, y, z] in millimetres",
                        "rotation": (
                            "either normalized quaternion [x, y, z, w], or "
                            "axis [x, y, z] plus angle_degrees"
                        ),
                    },
                    "joint_axis": "local connector +Z",
                },
                "evaluation_model": (
                    "API calls build one immutable assembly graph. Component source Shapes "
                    "are authenticated snapshots of stable input references. FreeCADCmd "
                    "creates real native links, grounds components, derives connector frames, "
                    "creates native joints, solves, and derives simulations and exploded-view "
                    "moves from that exact graph. It returns placements, line endpoints, "
                    "and diagnostics. The document "
                    "thread only applies independently reauthorized, precomputed state."
                ),
                "input_reference_contract": {
                    "purpose": (
                        "Pass component sources through inputs. The host detaches each exact "
                        "Shape, hashes the BREP and semantic-interface contract into the "
                        "program revision, and marks accepted Assembly outputs stale if a "
                        "source changes. Raw document access from source is unavailable."
                    ),
                    "schema": {
                        "type": "object",
                        "x-cadex-reference": True,
                        "properties": {
                            "document_uid": {"type": "string", "minLength": 1},
                            "object_name": {"type": "string", "minLength": 1},
                        },
                        "required": ["document_uid", "object_name"],
                        "additionalProperties": False,
                    },
                    "eligible_sources": [
                        "standalone solid Part::Feature",
                        "PartDesign::Body",
                        "App::Part with solid shape",
                        "Assembly::AssemblyObject with solid aggregate shape",
                        "solid Part or Part Design XScript publication",
                    ],
                },
                "graph_contract": {
                    "component": (
                        "Create each occurrence once, set grounded=True on at least one "
                        "fixed base, and reuse that exact variable in connectors."
                    ),
                    "joint": (
                        "Each joint consumes two connector variables on two different "
                        "components. Include every joint and component in api.assembly."
                    ),
                    "result": (
                        "Return exactly one assembly and one solver_diagnostics value. Return "
                        "every component and joint in that graph exactly once under its stable "
                        "output name; do not recreate equivalent values. If motion is requested, "
                        "also return every api.motion value exactly once and exactly one "
                        "api.simulation value that consumes the returned assembly. If an "
                        "exploded presentation is requested, return each api.exploded_view "
                        "value exactly once. Every derived value must "
                        "consume that same assembly variable."
                    ),
                },
                "operation_selection": {
                    "source_occurrence": "api.component",
                    "joint_coordinate_system": "api.connector",
                    "mechanical_relationship": "api.joint",
                    "complete_mechanism_graph": "api.assembly",
                    "native_validation_and_diagnostics": "api.solve",
                    "one_driven_degree_of_freedom": "api.motion",
                    "time_series_kinematics": "api.simulation",
                    "named_disassembly_presentation": "api.exploded_view",
                    "redundancy_contract": (
                        "These are the only canonical operations. There are no aliases or "
                        "separate add/update/refresh variants. Create each immutable value once, "
                        "reuse that exact variable downstream, and return it once when its type "
                        "is publishable."
                    ),
                },
                "model_workflow": [
                    {
                        "step": 1,
                        "action": "discover",
                        "instruction": (
                            "Read component_candidates from the Assembly domain context. "
                            "Choose only entries with eligible_component_shape=true and "
                            "copy each candidate's reference object into program inputs. "
                            "Use flexible=True only when eligible_flexible_subassembly=true. "
                            "For internal connectors, require "
                            "eligible_detailed_bom_hierarchy=true and copy exact "
                            "assembly_hierarchy.occurrence_paths[].path values. Never infer a "
                            "path from labels or generated AssemblyLink child names."
                        ),
                    },
                    {
                        "step": 2,
                        "action": "plan_frames",
                        "instruction": (
                            "Choose origin connectors when source coordinate systems already "
                            "describe the intended joint. Otherwise choose FaceN/EdgeN/VertexN "
                            "from bounded facts, or a published semantic interface when the "
                            "candidate requires one. Connector local +Z is the joint axis."
                        ),
                    },
                    {
                        "step": 3,
                        "action": "author_graph",
                        "instruction": (
                            "Create each component once, ground at least one component, reuse "
                            "the same variables in connectors and joints, then return every "
                            "component and joint plus exactly one assembly and diagnostics output."
                        ),
                    },
                    {
                        "step": 4,
                        "action": "solve",
                        "instruction": (
                            "Use api.solve(model) for accepted production geometry. Use "
                            "require_solved=False only when the user explicitly wants a "
                            "diagnostic snapshot of an incomplete or conflicting mechanism."
                        ),
                    },
                    {
                        "step": 5,
                        "action": "simulate",
                        "instruction": (
                            "Only after defining a clean solvable mechanism, create one "
                            "api.motion per driven degree of freedom and one api.simulation. "
                            "Return those same variables. Angular formulas are radians, linear "
                            "formulas are millimetres, and time is seconds."
                        ),
                    },
                    {
                        "step": 6,
                        "action": "present",
                        "instruction": (
                            "After a clean solve, use one api.exploded_view call per named "
                            "presentation. Express its ordered moves with returned component "
                            "variables, using exactly one transform or radial_distance_mm per "
                            "move. Return the view variable under its stable output name."
                        ),
                    },
                    {
                        "step": 7,
                        "action": "repair",
                        "instruction": (
                            "On failure, keep expected_outputs and stable output names unchanged. "
                            "Use the failure stage, requested/observed values, available selectors, "
                            "solver diagnostics, and suggestion to make the smallest source edit "
                            "against the latest working_revision. Inspect first if the revision is "
                            "not known."
                        ),
                    },
                    {
                        "step": 8,
                        "action": "verify",
                        "instruction": (
                            "Inspect the accepted program and confirm accepted_revision equals "
                            "working_revision, every live output retains its declared identity, "
                            "and Diagnostics reports status='solved' with solver_code=0. For a "
                            "simulation, also confirm native_code=0, nonzero motion effect, and "
                            "the retained trace digest/frame count. For an exploded view, "
                            "confirm every move and component has a nonzero authenticated line "
                            "and the live native view retains the same accepted evidence."
                        ),
                    },
                ],
                "motion_and_simulation": {
                    "supported_joints": {
                        "revolute": ["angular"],
                        "slider": ["linear"],
                        "cylindrical": ["angular", "linear"],
                    },
                    "auto_selection": (
                        "motion_type='auto' selects angular for revolute and linear for "
                        "slider. Cylindrical joints require an explicit type and may have "
                        "one motion of each type."
                    ),
                    "formula": {
                        "variables": ["time", "initialValue", "pi"],
                        "functions": ["abs", "asin", "arcsin", "arctan", "cos", "sin"],
                        "operators": ["+", "-", "*", "/", "^"],
                        "examples": {
                            "quarter_turn_per_second": "initialValue + pi/2*time",
                            "ten_mm_per_second": "initialValue + 10*time",
                            "oscillation": "initialValue + 0.25*sin(2*pi*time)",
                        },
                        "security": (
                            "No attributes, indexing, imports, comprehensions, arbitrary "
                            "names, or function keywords are accepted."
                        ),
                    },
                    "trace": (
                        "The worker runs FreeCAD's native kinematic solver, authenticates every "
                        "component placement for every frame, retains the complete JSON trace as "
                        "a project attempt artifact, and publishes only its identity, motion "
                        "effects, counts, and input/middle/final preview."
                    ),
                    "failure_repair": (
                        "Failures identify the simulation and motion output, driven joint/type, "
                        "formula, native code or failed frame, observed motion magnitude, and a "
                        "direct correction. A time-dependent formula with no measurable motion "
                        "is rejected rather than silently accepted."
                    ),
                },
                "exploded_views": {
                    "graph_rule": (
                        "api.exploded_view consumes the exact returned api.assembly value and "
                        "ordered moves. Each move references one or more component variables "
                        "from that graph and has exactly one movement form. Multiple named "
                        "views are allowed; separate views are separate stable outputs."
                    ),
                    "normal_move": (
                        "Use transform for a deterministic placement composed on the left of "
                        "each component's current staged exploded placement. Components may "
                        "appear in later moves for a sequential explosion."
                    ),
                    "radial_move": (
                        "radial_distance_mm is FreeCAD's native radial control distance. The "
                        "actual displacement vector is (component_bounds_center - "
                        "assembly_bounds_center) * 4*radial_distance_mm/assembly_diagonal. "
                        "Components at the assembly centre cannot move radially and are "
                        "rejected with their exact output names."
                    ),
                    "validation": (
                        "The isolated worker creates actual ExplodedView/ExplodedViewStep "
                        "proxies and returns each final placement and explosion-line endpoint. "
                        "The host independently reloads authenticated component BREPs, derives "
                        "the solved bounds and every ordered move, and rejects altered evidence."
                    ),
                    "publication": (
                        "One stable App::FeaturePython ExplodedView lives under the native "
                        "Assembly::ViewGroup. Ordered managed ExplodedViewStep children retain "
                        "stable index identities across compatible regeneration. Publication "
                        "sets precomputed transforms/references only and never calculates an "
                        "explosion on the document thread."
                    ),
                },
                "nested_subassemblies": {
                    "selection": (
                        "Set api.component(..., flexible=True) only for an authenticated native "
                        "Assembly candidate marked eligible_flexible_subassembly. Rigid and "
                        "flexible instances use the same stable source paths."
                    ),
                    "path": (
                        "Copy the complete slash-separated path from "
                        "component_candidates[].assembly_hierarchy.occurrence_paths[].path into "
                        "api.connector(..., occurrence_path=...). Paths may be nested to the "
                        "documented depth limit and never contain generated native child names."
                    ),
                    "solve_and_publication": (
                        "The worker reconstructs every authenticated level and its native joints, "
                        "solves the parent graph, and returns per-occurrence placements. The live "
                        "publisher maps those placements back to the same stable paths while "
                        "retaining AssemblyLink identities across regeneration and reopen."
                    ),
                    "repair": (
                        "A bad path reports requested_path, failed_segment_index, and the exact "
                        "available_segments at that level. Replace only the failed segment using "
                        "one reported value and retry against the failed working_revision."
                    ),
                },
                "joint_selection_guide": {
                    "no_relative_motion": "fixed",
                    "rotate_about_one_axis": "revolute",
                    "translate_along_one_axis": "slider",
                    "rotate_and_translate_on_same_axis": "cylindrical",
                    "rotate_freely_about_one_point": "ball",
                    "maintain_axial_separation": "distance",
                    "maintain_axis_parallelism": "parallel",
                    "maintain_axis_perpendicularity": "perpendicular",
                    "maintain_axis_angle": "angle",
                    "couple_linear_rack_to_rotation": (
                        "rack_pinion plus a collinear slider on the rack"
                    ),
                    "couple_axial_translation_to_rotation": (
                        "screw plus a collinear slider on the translating component"
                    ),
                    "couple_two_rotations_with_teeth": "gears",
                    "couple_two_rotations_with_belt": "belt",
                },
                "connector_selection": {
                    "origin": "Use 'origin' for a native or v2 XScript component origin.",
                    "exact": (
                        "Use FaceN, EdgeN, or VertexN only on immutable native snapshots; "
                        "indices are 1-based and worker errors report the available range."
                    ),
                    "semantic": (
                        "Use {'type':'published_interface','interface_name':'...'} for "
                        "regenerating scripted publications. Available names and geometry "
                        "types appear in Assembly domain component_candidates context."
                    ),
                    "offset": (
                        "An optional connector-local placement is applied after FreeCAD "
                        "derives the natural JCS."
                    ),
                    "anchor": (
                        "For an immutable exact edge/face, anchor='VertexN' selects a "
                        "specific vertex on that subelement. Omit anchor for the native "
                        "edge midpoint/circle center or face center. Invalid membership "
                        "reports the selected subelement, requested vertex, available "
                        "vertex count, and a correction."
                    ),
                },
                "joint_types": {
                    "rigid_and_kinematic": [
                        "fixed",
                        "revolute",
                        "cylindrical",
                        "slider",
                        "ball",
                    ],
                    "geometric": [
                        "distance",
                        "parallel",
                        "perpendicular",
                        "angle",
                    ],
                    "coupled_motion": [
                        "rack_pinion",
                        "screw",
                        "gears",
                        "belt",
                    ],
                    "limits": {
                        "length_limits_mm": {
                            "joint_types": ["slider", "cylindrical"],
                            "form": (
                                "[minimum, maximum] or an object with minimum/maximum; "
                                "use null for one unbounded side"
                            ),
                        },
                        "angle_limits_degrees": {
                            "joint_types": ["revolute", "cylindrical"],
                            "form": (
                                "[minimum, maximum] or an object with minimum/maximum; "
                                "use null for one unbounded side"
                            ),
                        },
                    },
                    "signed_parameters": {
                        "distance_mm": (
                            "signed native distance along connector +Z; zero is valid"
                        ),
                        "pitch_radius_mm": (
                            "non-zero signed rack/pinion ratio; sign selects direction"
                        ),
                        "thread_pitch_mm": (
                            "non-zero signed screw lead; sign selects handedness/direction"
                        ),
                        "radius1_mm/radius2_mm": (
                            "strictly positive physical radii for gears and belts"
                        ),
                    },
                    "coupled_joint_dependencies": {
                        "rack_pinion": (
                            "Requires a non-suppressed Slider joint sharing the rack "
                            "component with a collinear local connector +Z axis."
                        ),
                        "screw": (
                            "Requires a non-suppressed Slider joint sharing one screw "
                            "component with a collinear local connector +Z axis."
                        ),
                        "failure": (
                            "require_solved=True rejects a missing dependency at "
                            "joint_dependency before publication and reports the joint, "
                            "components, available sliders, requirement, and exact fix."
                        ),
                    },
                },
                "capability_inventory": {
                    "component_occurrences": {
                        "status": "supported",
                        "features": [
                            "repeated links to one source",
                            "initial and solved placements",
                            "grounding",
                            "rigid native subassembly links",
                            "flexible native subassembly links with internal joints",
                            "nested flexible links with authenticated solved occurrence placements",
                            "stable source occurrence paths shared by rigid and flexible links",
                        ],
                    },
                    "joint_graph": {
                        "status": "supported",
                        "features": [
                            "all 13 native joint types",
                            "exact or semantic connector frames",
                            "vertex anchors and local offsets",
                            "one-sided or two-sided limits",
                            "suppression",
                            "native solve diagnostics",
                        ],
                    },
                    "kinematic_simulation": {
                        "status": "supported",
                        "features": [
                            "native angular and linear motion properties",
                            "revolute, slider, and dual-axis cylindrical drives",
                            "bounded native solver traces",
                            "authenticated per-frame component placements",
                            "stable motion and simulation live identities",
                        ],
                    },
                    "exploded_views": {
                        "status": "supported",
                        "features": [
                            "multiple stable named native exploded views",
                            "ordered normal and radial moves",
                            "repeated components across staged moves",
                            "authenticated final placements and line endpoints",
                            "stable native move identities across regeneration and reopen",
                        ],
                    },
                    "not_yet_provider_exposed": [],
                },
                "solver_codes": {
                    "0": "solved",
                    "-1": "solver_error",
                    "-2": "redundant_constraints",
                    "-3": "conflicting_constraints",
                    "-4": "over_constrained",
                    "-5": "malformed_constraints",
                    "-6": "no_grounded_component",
                },
                "publication_contract": {
                    "native_types": {
                        "assembly": "Assembly::AssemblyObject",
                        "component": "App::Link or Assembly::AssemblyLink for a subassembly",
                        "joint": "native JointObject in Assembly::JointGroup",
                        "motion": "stable App::FeaturePython native motion-property contract",
                        "simulation": (
                            "stable App::FeaturePython in Assembly::SimulationGroup"
                        ),
                        "exploded_view": (
                            "stable ExplodedView App::FeaturePython in Assembly::ViewGroup "
                            "with managed native ExplodedViewStep children"
                        ),
                        "diagnostics": "stable App::FeaturePython report",
                    },
                    "identity": (
                        "Program/output ids update the same assembly, component, joint, motion, "
                        "simulation, exploded-view, and diagnostics objects in place. "
                        "Compatible exploded moves retain stable index identities. A component "
                        "cannot change between App::Link and Assembly::AssemblyLink without a "
                        "new output identity."
                    ),
                    "asynchronous_boundary": (
                        "BREP transfer, connector derivation, presolve, solver work, and "
                        "kinematic trace and exploded-view generation run in the "
                        "isolated worker. Live joints receive detached precomputed JCS placements "
                        "and live simulations receive only authenticated settings and previews. "
                        "Live exploded views receive only precomputed move transforms and stable "
                        "references. Publication, recompute, and reopen never "
                        "invoke a solver, derive bounds, calculate an explosion, "
                        "recompute the document, or read an artifact."
                    ),
                },
                "workbench_handoffs": {
                    "rule": (
                        "The model cannot switch workbench or modeling engine. Finish and "
                        "inspect the Assembly graph available on this surface, then state the "
                        "exact handoff and ask the human to switch; never call another "
                        "domain's tools."
                    ),
                    "handoff_examples": {
                        "Part Design/Part": (
                            "author stable component solids, mating geometry, and semantic "
                            "connector interfaces before assembly"
                        ),
                        "Material": (
                            "apply authoritative physical materials and appearance to accepted "
                            "component references; Assembly does not infer assignments"
                        ),
                        "Robot": (
                            "author robot kinematics, waypoints, trajectories, dress-ups, and "
                            "simulation after the mechanical assembly is accepted"
                        ),
                        "FEM": (
                            "analyze accepted load paths using semantic geometry references "
                            "and solved component placement intent"
                        ),
                        "CAM": (
                            "manufacture accepted component solids; Assembly does not generate "
                            "component toolpaths"
                        ),
                        "TechDraw": (
                            "document accepted assembly/component views, dimensions, and notes"
                        ),
                    },
                    "boundary": (
                        "Assembly owns occurrences, connectors, joints, solve evidence, motion, "
                        "and exploded views. It does not author component solids, material "
                        "cards, robot trajectories, FEM loads, CAM paths, or drawing projections."
                    ),
                },
                "recommended_patterns": [
                    {
                        "goal": "grounded base and revolute arm",
                        "source": (
                            "base = api.component(inputs['base'], grounded=True, label='Base')\n"
                            "arm = api.component(inputs['arm'], placement=[0,0,20], label='Arm')\n"
                            "hinge = api.joint('revolute', api.connector(base, 'Face6'), "
                            "api.connector(arm, 'Face1'), angle_limits_degrees=[-90,90], "
                            "label='Hinge')\n"
                            "model = api.assembly([base, arm], [hinge], label='Robot Arm')\n"
                            "diagnostics = api.solve(model)\n"
                            "result = {'Model': model, 'Base': base, 'Arm': arm, "
                            "'Hinge': hinge, 'Diagnostics': diagnostics}"
                        ),
                        "expected_outputs": [
                            {"name": "Model", "type": "assembly"},
                            {"name": "Base", "type": "component_link"},
                            {"name": "Arm", "type": "component_link"},
                            {"name": "Hinge", "type": "joint"},
                            {"name": "Diagnostics", "type": "solver_diagnostics"},
                        ],
                    },
                    {
                        "goal": "publish a staged native exploded view",
                        "source": (
                            "base = api.component(inputs['base'], grounded=True, label='Base')\n"
                            "arm = api.component(inputs['arm'], label='Arm')\n"
                            "hinge = api.joint('revolute', api.connector(base), "
                            "api.connector(arm), label='Hinge')\n"
                            "model = api.assembly([base, arm], [hinge], label='Robot Arm')\n"
                            "diagnostics = api.solve(model)\n"
                            "exploded = api.exploded_view(model, "
                            "[{'components':[arm], 'transform':[0,0,40]}], "
                            "label='Service View')\n"
                            "result = {'Model':model, 'Base':base, 'Arm':arm, "
                            "'Hinge':hinge, 'Exploded':exploded, "
                            "'Diagnostics':diagnostics}"
                        ),
                        "expected_outputs": [
                            {"name": "Model", "type": "assembly"},
                            {"name": "Base", "type": "component_link"},
                            {"name": "Arm", "type": "component_link"},
                            {"name": "Hinge", "type": "joint"},
                            {"name": "Exploded", "type": "exploded_view"},
                            {"name": "Diagnostics", "type": "solver_diagnostics"},
                        ],
                    },
                    {
                        "goal": "joint to a nested occurrence in a flexible subassembly",
                        "source": (
                            "base = api.component(inputs['base'], grounded=True, label='Base')\n"
                            "drive = api.component(inputs['drive'], flexible=True, label='Drive')\n"
                            "mount = api.joint('revolute', api.connector(base), "
                            "api.connector(drive, occurrence_path='CoreOccurrence/GearOccurrence'), "
                            "angle_limits_degrees=[-120,120], label='Drive Mount')\n"
                            "model = api.assembly([base, drive], [mount], "
                            "label='Flexible Mechanism')\n"
                            "diagnostics = api.solve(model)\n"
                            "result = {'Model':model,'Base':base,'Drive':drive,"
                            "'Mount':mount,'Diagnostics':diagnostics}"
                        ),
                        "expected_outputs": [
                            {"name": "Model", "type": "assembly"},
                            {"name": "Base", "type": "component_link"},
                            {"name": "Drive", "type": "component_link"},
                            {"name": "Mount", "type": "joint"},
                            {"name": "Diagnostics", "type": "solver_diagnostics"},
                        ],
                    },
                    {
                        "goal": "simulate a revolute mechanism with a retained trace",
                        "source": (
                            "base = api.component(inputs['base'], grounded=True, label='Base')\n"
                            "arm = api.component(inputs['arm'], label='Arm')\n"
                            "hinge = api.joint('revolute', api.connector(base), "
                            "api.connector(arm), label='Hinge')\n"
                            "model = api.assembly([base, arm], [hinge], label='Driven Arm')\n"
                            "diagnostics = api.solve(model)\n"
                            "drive = api.motion(hinge, 'initialValue + pi/2*time', "
                            "label='Hinge Drive')\n"
                            "simulation = api.simulation(model, [drive], end_time_s=1, "
                            "time_step_s=0.05, label='One Second')\n"
                            "result = {'Model':model, 'Base':base, 'Arm':arm, "
                            "'Hinge':hinge, 'Drive':drive, 'Simulation':simulation, "
                            "'Diagnostics':diagnostics}"
                        ),
                        "expected_outputs": [
                            {"name": "Model", "type": "assembly"},
                            {"name": "Base", "type": "component_link"},
                            {"name": "Arm", "type": "component_link"},
                            {"name": "Hinge", "type": "joint"},
                            {"name": "Drive", "type": "motion"},
                            {"name": "Simulation", "type": "simulation"},
                            {"name": "Diagnostics", "type": "solver_diagnostics"},
                        ],
                    },
                ],
                "error_contract": {
                    "source": (
                        "Argument errors identify api.operation and the exact parameter, "
                        "including irrelevant joint parameters and invalid graph membership."
                    ),
                    "connector": (
                        "Selection failures include component output, requested subelement or "
                        "interface, available range/names, and resolved geometry types. Nested "
                        "occurrence failures include requested_path, failed_segment_index, exact "
                        "available_segments, and a copy-ready correction."
                    ),
                    "solver": (
                        "Rejected candidates retain exact solver code/verdict, native conflict, "
                        "redundancy and malformed-constraint diagnostics, component placements, "
                        "and the failing stage while the accepted revision stays live."
                    ),
                    "joint_dependency": (
                        "Rack/Pinion and Screw failures identify the coupled joint output, "
                        "its components, available Slider outputs, the native collinearity "
                        "requirement, and a directly usable api.joint('slider', ...) fix."
                    ),
                    "exploded_view": (
                        "Failures identify the stable view output, ordered move index and kind, "
                        "selected components, changed and unchanged components, native readback "
                        "stage, and a direct transform/radial correction. Failed candidates do "
                        "not replace the still-live accepted view."
                    ),
                },
            }
        )
        return description


# ---------------------------------------------------------------------------
# Project script lifecycle — ONE script composing all four capability domains
# ---------------------------------------------------------------------------

PROJECT_WORKER_SCHEMA = "cadex-xscript-project-worker-v1"
_PROJECT_OPERATIONS = frozenset({"write_script", "edit_script", "set_params"})


def parse_project_tool(tool_name: str) -> str | None:
    """Return the project lifecycle operation for xscript.project.* tools."""

    parts = str(tool_name or "").split(".")
    if len(parts) != 3 or parts[0] != "xscript" or parts[1] != "project":
        return None
    operation = parts[2]
    if operation not in _PROJECT_OPERATIONS and operation != "describe_api":
        return None
    return operation


def _project_api_contracts() -> dict[str, dict[str, list[str]]]:
    by_domain = {
        pack.domain: pack for pack in contracts.XSCRIPT_WORKBENCH_PACKS.values()
    }
    return {
        domain: {
            "exports": list(pack.api_exports),
            "output_types": list(pack.output_types),
        }
        for domain, pack in by_domain.items()
    }


def capture_project_state(
    service: Any,
    tool_name: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Capture document-affine state for one project script operation."""

    operation = parse_project_tool(tool_name)
    if operation is None:
        _raise(tool_name, "UNKNOWN_DOMAIN_TOOL", "surface", "Unknown project tool.")
    doc = service._active_document()
    if doc is None:
        _raise(tool_name, "NO_DOCUMENT", "precondition", "No active FreeCAD document.")
    scope = service.project_scope_snapshot()
    from CadexPreferences import load_settings

    settings = load_settings()
    timeout = float(getattr(settings, "scripted_timeout_seconds", 0.0) or 0.0)
    memory_mb = int(getattr(settings, "scripted_memory_limit_mb", 0) or 0)
    if timeout <= 0.0 or memory_mb <= 0:
        _raise(
            tool_name,
            "INVALID_SCRIPTED_BUDGET",
            "precondition",
            "XScript requires positive worker timeout and memory limits.",
            observed={"timeout_seconds": timeout, "memory_limit_mb": memory_mb},
        )
    try:
        import FreeCAD as App

        freecad_home = str(App.getHomePath())
    except Exception as exc:
        _raise(
            tool_name,
            "FREECAD_UNAVAILABLE",
            "precondition",
            f"FreeCAD is unavailable: {exc}",
        )
    return {
        "tool_name": tool_name,
        "operation": operation,
        "arguments": dict(arguments),
        "pack": contracts.PROJECT_PACK,
        "project_root": str(scope.get("root") or ""),
        "project_id": str(scope.get("project_id") or ""),
        "document_name": str(getattr(doc, "Name", "") or ""),
        "document_uid": str(getattr(doc, "Uid", "") or ""),
        "document_revision": str(service.provider_document_revision()),
        "document_objects": _document_objects(doc),
        "freecad_home": freecad_home,
        "timeout_seconds": timeout,
        "memory_limit_bytes": memory_mb * 1024 * 1024,
    }


def _project_param_values(
    state: Mapping[str, Any], patch: Any, tool_name: str
) -> dict[str, float]:
    """Apply one values-only RFC 7396 patch against the declared parameters."""

    declared = {
        str(spec.get("name") or ""): spec
        for spec in list(state.get("param_specs") or [])
    }
    merged = _merge_patch(dict(state.get("param_values") or {}), patch)
    cleaned: dict[str, float] = {}
    for name, value in merged.items():
        if name not in declared:
            _raise(
                tool_name,
                "UNKNOWN_PROJECT_PARAMETER",
                "precondition",
                f"The project script declares no parameter named {name!r}.",
                requested={"values": patch},
                observed={"declared": sorted(declared)},
            )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            _raise(
                tool_name,
                "INVALID_PROJECT_PARAMETER_VALUE",
                "precondition",
                f"Parameter {name!r} must be a finite number.",
                requested={name: value},
            )
        cleaned[name] = float(value)
    return cleaned


def prepare_project_candidate(captured: Mapping[str, Any]) -> dict[str, Any]:
    """Persist the working script state and stage one project candidate."""

    from CadexProject import CadexProjectScriptStore

    tool_name = str(captured["tool_name"])
    operation = str(captured["operation"])
    arguments = dict(captured["arguments"])
    project_root = str(captured["project_root"] or "")
    if not project_root:
        _raise(
            tool_name,
            "NO_PROJECT_ROOT",
            "precondition",
            "The active document has no durable Cadex project root.",
        )
    store = CadexProjectScriptStore(project_root)
    state = store.read_state()
    current_source = store.read_source()

    expected_revision = str(arguments.get("expected_revision") or "")
    working_revision = str(state.get("working_revision") or "")
    if expected_revision != working_revision:
        _raise(
            tool_name,
            "STALE_PROGRAM_REVISION",
            "precondition",
            "The project script changed after inspection.",
            requested={"expected_revision": expected_revision},
            observed={"current_revision": working_revision},
            required_changes=[{"inspect": "core.inspect scope=script"}],
        )

    param_values = dict(state.get("param_values") or {})
    if operation == "write_script":
        source = str(arguments.get("source") or "")
        if not source.strip():
            _raise(
                tool_name,
                "EMPTY_PROJECT_SCRIPT",
                "precondition",
                "write_script requires a complete non-empty script source.",
            )
    elif operation == "edit_script":
        if not current_source:
            _raise(
                tool_name,
                "NO_PROJECT_SCRIPT",
                "precondition",
                "There is no project script to edit yet; use write_script.",
            )
        try:
            source = _apply_replacements(
                current_source, arguments.get("replacements")
            )
        except ValueError as exc:
            _raise(
                tool_name,
                "REPLACEMENT_NOT_UNIQUE",
                "precondition",
                str(exc),
                requested={"replacements": arguments.get("replacements")},
            )
    elif operation == "set_params":
        if not current_source:
            _raise(
                tool_name,
                "NO_PROJECT_SCRIPT",
                "precondition",
                "There is no project script yet; use write_script first.",
            )
        source = current_source
        try:
            param_values = _project_param_values(
                state, arguments.get("values"), tool_name
            )
        except ValueError as exc:
            _raise(tool_name, "INVALID_PROJECT_PARAMETER_VALUE", "precondition", str(exc))
    else:
        _raise(tool_name, "UNKNOWN_DOMAIN_TOOL", "surface", "Unknown project tool.")

    try:
        contracts.validate_program_source(source)
    except ValueError as exc:
        _raise(
            tool_name,
            "INVALID_PROGRAM_SOURCE",
            "precondition",
            str(exc),
        )

    freecadcmd_executable = _freecadcmd(str(captured["freecad_home"]))
    # Pre-run revision over the stored spec cache; validate_project_result
    # recomputes it with the worker-collected specs and records that as the
    # durable working revision.
    revision = contracts.project_script_revision(
        source=source,
        param_specs=list(state.get("param_specs") or []),
        param_values=param_values,
    )
    attempt_id = f"{int(time.time() * 1000):013d}-{uuid.uuid4().hex[:12]}"
    staging = store.artifacts_dir(revision) / f"attempt-{attempt_id}"
    staging.mkdir(parents=True, exist_ok=False)
    module_root = Path(__file__).resolve().parent
    try:
        _stage_worker_bundle(module_root, staging, "project")
        request = {
            "schema": PROJECT_WORKER_SCHEMA,
            "source": source,
            "inputs": {},
            "param_values": param_values,
            "api_contracts": _project_api_contracts(),
            "document_name": str(captured["document_name"]),
            "document_uid": str(captured["document_uid"]),
            "document_objects": list(captured["document_objects"]),
            "max_operations": 400_000,
            "max_seconds": float(captured["timeout_seconds"]),
            "memory_limit_bytes": int(captured["memory_limit_bytes"]),
            "cpu_limit_seconds": max(1, int(float(captured["timeout_seconds"]))),
            "output_limit_bytes": 256 * 1024 * 1024,
        }
        _atomic_json(staging / "request.json", request)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    # The script file IS the working artifact: persist before execution.
    store.write(
        source=source,
        state_updates={
            "param_values": param_values,
            "working_revision": revision,
        },
    )
    return {
        "tool_name": tool_name,
        "operation": operation,
        "pack": captured["pack"],
        "program_id": "project",
        "revision": revision,
        "accepted_revision_before": str(state.get("accepted_revision") or ""),
        "accepted_contract_before": state.get("accepted_contract"),
        "accepted_digest_before": str(state.get("accepted_digest") or ""),
        "source": source,
        "param_values": param_values,
        "param_specs_before": list(state.get("param_specs") or []),
        "project_root": project_root,
        "staging": str(staging),
        "attempt_id": attempt_id,
        "freecadcmd_executable": str(freecadcmd_executable),
        "timeout_seconds": float(captured["timeout_seconds"]),
        "memory_limit_bytes": int(captured["memory_limit_bytes"]),
        "document_name": str(captured["document_name"]),
        "document_uid": str(captured["document_uid"]),
        "document_revision": str(captured["document_revision"]),
        "document_objects": list(captured["document_objects"]),
    }


def record_project_candidate_failure(
    prepared: Mapping[str, Any], failure: Mapping[str, Any]
) -> None:
    """Persist the failed candidate summary; the accepted state stays live."""

    from CadexProject import CadexProjectScriptStore

    store = CadexProjectScriptStore(str(prepared["project_root"]))
    store.write(
        state_updates={
            "latest_candidate": {
                "status": "failed",
                "revision": str(prepared["revision"]),
                "attempt_id": str(prepared["attempt_id"]),
                "failure_code": str(failure.get("failure_code") or ""),
                "error": str(failure.get("error") or ""),
            },
        }
    )


def validate_project_result(
    prepared: dict[str, Any], execution: Mapping[str, Any]
) -> dict[str, Any]:
    """Check the worker report, record the contract, persist working state."""

    from CadexProject import CadexProjectScriptStore

    tool_name = str(prepared["tool_name"])
    if execution.get("schema") != PROJECT_WORKER_SCHEMA:
        _raise(
            tool_name,
            "DOMAIN_WORKER_RESULT_INVALID",
            "postcondition",
            f"Unexpected project worker schema {execution.get('schema')!r}.",
        )
    outputs = list(execution.get("outputs") or [])
    if not outputs:
        _raise(
            tool_name,
            "DOMAIN_RESULT_INVALID",
            "postcondition",
            "The project worker returned no outputs.",
        )
    digest = str(execution.get("digest") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        _raise(
            tool_name,
            "DOMAIN_RESULT_INVALID",
            "postcondition",
            "The project worker returned no content digest.",
        )
    param_specs = list(execution.get("param_specs") or [])
    contract: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in outputs:
        if not isinstance(item, Mapping):
            _raise(
                tool_name,
                "DOMAIN_RESULT_INVALID",
                "postcondition",
                "Every project worker output must be an object.",
            )
        name = str(item.get("name") or "")
        domain = str(item.get("domain") or "")
        output_type = str(item.get("type") or "")
        if not name or name in seen or domain not in {
            "sketcher",
            "part",
            "partdesign",
            "assembly",
        }:
            _raise(
                tool_name,
                "DOMAIN_RESULT_INVALID",
                "postcondition",
                f"Project output {name!r} has an invalid identity.",
                observed={"name": name, "domain": domain, "type": output_type},
            )
        seen.add(name)
        if str(item.get("artifact_kind") or "") == "brep":
            path = _staged_artifact_path(
                prepared,
                item.get("artifact_path"),
                context=f"Project output {name!r}",
            )
            # Import the detached shape off the document thread now so
            # publication applies validated values without artifact I/O.
            import Part

            shape = Part.Shape()
            shape.importBrep(str(path))
            if shape.isNull() or not shape.isValid():
                _raise(
                    tool_name,
                    "DOMAIN_RESULT_INVALID",
                    "postcondition",
                    f"Project output {name!r} BREP artifact is invalid.",
                )
            item["detached_shape"] = shape
        contract.append({"name": name, "type": output_type, "domain": domain})

    # Durable working revision binds the worker-collected parameter specs.
    final_revision = contracts.project_script_revision(
        source=str(prepared["source"]),
        param_specs=param_specs,
        param_values=dict(prepared["param_values"]),
    )
    store = CadexProjectScriptStore(str(prepared["project_root"]))
    store.write(
        state_updates={
            "param_specs": param_specs,
            "working_revision": final_revision,
            "latest_candidate": {
                "status": "validated",
                "revision": final_revision,
                "attempt_id": str(prepared["attempt_id"]),
                "digest": digest,
                "output_count": len(contract),
            },
        }
    )
    prepared["revision"] = final_revision
    return {
        "ok": True,
        "outputs": outputs,
        "contract": contract,
        "digest": digest,
        "param_specs": param_specs,
        "validations": dict(execution.get("validations") or {}),
        "component_sources": dict(execution.get("component_sources") or {}),
        "stdout": str(execution.get("stdout") or ""),
        "budget": dict(execution.get("budget") or {}),
    }


def accept_project_candidate(
    prepared: Mapping[str, Any],
    publication: Mapping[str, Any],
    validated: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist the accepted project revision/contract/digest; return the tool payload."""

    from CadexProject import CadexProjectScriptStore

    revision = str(prepared["revision"])
    digest = str(validated["digest"])
    contract = [dict(item) for item in list(validated["contract"])]
    store = CadexProjectScriptStore(str(prepared["project_root"]))
    store.write(
        state_updates={
            "accepted_revision": revision,
            "accepted_contract": contract,
            "accepted_digest": digest,
            "latest_candidate": {
                "status": "accepted",
                "revision": revision,
                "attempt_id": str(prepared["attempt_id"]),
                "digest": digest,
                "output_count": len(contract),
            },
        }
    )
    return {
        "ok": True,
        "tool": str(prepared["tool_name"]),
        "outputs": contract,
        "live_outputs": dict(publication.get("live_outputs") or {}),
        "digest": digest,
        "revision": revision,
        "accepted_revision": revision,
        "removed": list(publication.get("removed") or []),
        "model_state": {
            "status": "accepted",
            "accepted_is_current": True,
            "next_write_expected_revision": revision,
            "verification_goal": (
                "Confirm accepted_revision equals working_revision and every "
                "declared output has a live published object."
            ),
        },
    }


def install_builtin_adapters() -> None:
    for pack in contracts.XSCRIPT_WORKBENCH_PACKS.values():
        if contracts.get_domain_adapter(pack.domain) is not None:
            continue
        if pack.domain == "partdesign":
            adapter = PartDesignDomainAdapter(pack)
        elif pack.domain == "part":
            adapter = PartDomainAdapter(pack)
        elif pack.domain == "sketcher":
            adapter = SketcherDomainAdapter(pack)
        elif pack.domain == "assembly":
            adapter = AssemblyDomainAdapter(pack)
        else:
            adapter = DeclarativeDomainAdapter(pack)
        contracts.register_domain_adapter(pack.domain, adapter)


# Publication helpers are imported late to keep worker-side imports FreeCADGui-free.
from CadexScriptedDomainPublication import (  # noqa: E402
    delete_live_program,
    publish_candidate,
    publish_project_candidate,
)
