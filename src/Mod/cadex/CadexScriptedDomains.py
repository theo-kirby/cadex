# SPDX-License-Identifier: LGPL-2.1-or-later

"""XScript domain contracts for THE project script (Phase 2.4).

The capability packs (partdesign/sketcher/part/mesh/assembly) describe the
worker execution and publication contracts of each domain. They no longer
carry a tool surface: the only mutation surface is the project pack's
``xscript.project.*`` tools (docs/DECISIONS.md ADR-013), and reads live in
``core.inspect``.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

PROGRAM_SCHEMA = "cadex-program-v2"
# The xscript engine reuses this identical v2 program shape; only the schema
# tag differs so a program manifest can be attributed to its authoring engine.
XSCRIPT_PROGRAM_SCHEMA = "cadex-xscript-program-v2"
PROGRAM_SCHEMAS = frozenset({PROGRAM_SCHEMA, XSCRIPT_PROGRAM_SCHEMA})
PROJECT_SCRIPT_SCHEMA = "cadex-xscript-project-v1"
XSCRIPT_VERSION = "2"
MAX_SOURCE_BYTES = 256_000

PROP_PROGRAM_ID = "CadexXScriptProgramId"
PROP_PROGRAM_DOMAIN = "CadexXScriptDomain"
PROP_PROGRAM_WORKBENCH = "CadexXScriptWorkbench"
PROP_PROGRAM_REVISION = "CadexXScriptRevision"
PROP_PROGRAM_OUTPUT = "CadexXScriptOutputName"

#: The project domain's tool surface: one script, whole-rewrite or targeted
#: edit, plus a values-only parameter patch. Reads live in core.inspect.
PROJECT_LIFECYCLE_OPERATIONS: tuple[str, ...] = (
    "describe_api",
    "write_script",
    "edit_script",
    "set_params",
)


@dataclass(frozen=True)
class XScriptWorkbenchPack:
    workbench: str
    domain: str
    title: str
    output_types: tuple[str, ...]
    instructions: str
    api_exports: tuple[str, ...]
    production_ready: bool = False
    # Engine descriptor. xscript is the one and only scripted modeling engine:
    # tool namespaces are ``xscript.<domain>.*``, program source receives the api
    # under the global name ``x``, and each program manifest is tagged with the
    # xscript program schema.
    engine: str = "xscript"
    api_global: str = "x"
    program_schema: str = XSCRIPT_PROGRAM_SCHEMA
    artifact_subdir: str = "xscript"
    # Only the project pack carries tool operations; capability packs are
    # execution/publication contracts with no tool surface (ADR-013).
    operations: tuple[str, ...] = ()

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(
            f"{self.engine}.{self.domain}.{operation}"
            for operation in self.operations
        )

    @property
    def surface_id(self) -> str:
        return f"{self.engine}:{self.domain}:v2"

    def summary(self, *, available: bool, reason: str = "") -> dict[str, Any]:
        return {
            "workbench": self.workbench,
            "domain": self.domain,
            "title": self.title,
            "surface_id": self.surface_id,
            "engine": self.engine,
            "program_schema": self.program_schema,
            "output_types": list(self.output_types),
            "api_exports": list(self.api_exports),
            "tool_names": list(self.tool_names),
            "available": bool(available),
            "unavailable_reason": str(reason or ""),
            "production_ready": self.production_ready,
        }


def _pack(
    workbench: str,
    domain: str,
    title: str,
    outputs: tuple[str, ...],
    instructions: str,
    api_exports: tuple[str, ...],
    *,
    production_ready: bool = False,
) -> XScriptWorkbenchPack:
    return XScriptWorkbenchPack(
        workbench=workbench,
        domain=domain,
        title=title,
        output_types=outputs,
        instructions=instructions,
        api_exports=api_exports,
        production_ready=production_ready,
    )


XSCRIPT_WORKBENCH_PACKS: dict[str, XScriptWorkbenchPack] = {
    "PartDesignWorkbench": _pack(
        "PartDesignWorkbench",
        "partdesign",
        "Part Design",
        ("solid",),
        "Author source-parametric Bodies, sketches, and Part Design features. "
        "Every published output is exactly one validated solid.",
        (
            "point",
            "line",
            "arc",
            "circle",
            "ellipse",
            "bspline",
            "external_geometry",
            "constraint",
            "sketch",
            "pad",
            "pocket",
            "revolve",
            "groove",
            "loft",
            "polar_pattern",
            "mirror",
            "fillet",
            "chamfer",
            "body",
        ),
        production_ready=True,
    ),
    "SketcherWorkbench": _pack(
        "SketcherWorkbench",
        "sketcher",
        "Sketcher",
        ("sketch",),
        "Define stable sketches with geometry, construction state, constraints, "
        "expressions, support, attachment, and profile-readiness expectations.",
        (
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
            "constraint",
            "sketch",
        ),
        production_ready=True,
    ),
    "PartWorkbench": _pack(
        "PartWorkbench",
        "part",
        "Part",
        ("solid", "shell", "face", "wire", "compound"),
        "Build direct OCC shapes and declare the exact accepted shape class for "
        "each stable output.",
        (
            "from_object",
            "box",
            "wedge",
            "plane",
            "prism",
            "cylinder",
            "cone",
            "sphere",
            "torus",
            "line",
            "arc",
            "circle",
            "ellipse",
            "bezier",
            "bspline",
            "nurbs_curve",
            "helix",
            "wire",
            "face",
            "shell",
            "solid",
            "compound",
            "subshape",
            "extrude",
            "revolve",
            "loft",
            "sweep",
            "cable",
            "bundle",
            "ruled_surface",
            "filled_surface",
            "fuse",
            "cut",
            "common",
            "section",
            "general_fuse",
            "slice",
            "defeature",
            "to_nurbs",
            "reverse",
            "sew",
            "shape_from_mesh",
            "repair",
            "fillet",
            "chamfer",
            "offset",
            "offset2d",
            "thicken",
            "transform",
            "mirror",
            "project",
            "refine",
        ),
        production_ready=True,
    ),
    "MeshWorkbench": _pack(
        "MeshWorkbench",
        "mesh",
        "Mesh",
        ("mesh",),
        "Tessellate part shapes, import STL/OBJ/PLY assets, place them with "
        "transform, apply native mesh set operations, and decimate. Every "
        "published output is exactly one validated triangle mesh.",
        (
            "from_shape",
            "import_file",
            "union",
            "difference",
            "intersection",
            "decimate",
            "transform",
        ),
        production_ready=True,
    ),
    "AssemblyWorkbench": _pack(
        "AssemblyWorkbench",
        "assembly",
        "Assembly",
        (
            "assembly",
            "component_link",
            "joint",
            "solver_diagnostics",
            "motion",
            "simulation",
            "exploded_view",
        ),
        "Define native assembly links, grounding, connector references, joints, "
        "solved placements, structured solver diagnostics, and worker-generated "
        "kinematic simulations, rigid-body dynamics runs, exploded views, and "
        "flexible source hierarchies.",
        (
            "assembly",
            "component",
            "connector",
            "joint",
            "solve",
            "motion",
            "simulation",
            "dynamics",
            "body",
            "collision",
            # Two more intermediates, and deliberately absent from
            # output_types above: like `collision`, a joint's damping and a
            # motor are arguments to a dynamics run, not things a script
            # publishes (M4).
            "joint_dynamics",
            "actuator",
            "exploded_view",
        ),
        production_ready=True,
    ),
}

#: The internal project domain: ONE project script composing every capability
#: domains in a single execution. Not a workbench pack - it is keyed by no
#: workbench and its api_exports are empty because the script receives one API
#: object per capability domain (sketcher/part/partdesign/mesh/assembly) plus the
#: params/num parameter vocabulary.
PROJECT_PACK = XScriptWorkbenchPack(
    workbench="CadexProject",
    domain="project",
    title="Project",
    output_types=tuple(
        dict.fromkeys(
            output_type
            for pack in XSCRIPT_WORKBENCH_PACKS.values()
            for output_type in pack.output_types
        )
    ),
    instructions=(
        "One project script is the sole source of truth for this document. "
        "The script runs once per change with the sketcher, part, partdesign, "
        "mesh and assembly APIs staged as same-named globals plus params/num "
        "for declaring slider parameters; assign every kept value to the "
        "result dictionary. Outputs may mix domains; assembly components take "
        "part or partdesign values created in the same script, and mesh "
        "tessellation takes part values created in the same script."
    ),
    api_exports=(),
    production_ready=True,
    program_schema=PROJECT_SCRIPT_SCHEMA,
    artifact_subdir="project",
    operations=PROJECT_LIFECYCLE_OPERATIONS,
)


def project_script_revision(
    *,
    source: str,
    param_specs: list[dict[str, Any]],
    param_values: Mapping[str, Any],
) -> str:
    """Content revision of the project script + its parameter state (D7)."""

    payload = {
        "schema": PROJECT_SCRIPT_SCHEMA,
        "domain": "project",
        "source": str(source),
        "param_specs": list(param_specs),
        "param_values": dict(param_values),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_xscript_pack(workbench: str | None) -> XScriptWorkbenchPack | None:
    return XSCRIPT_WORKBENCH_PACKS.get(str(workbench or ""))


#: Programs share one on-disk artifact tree; the authoring engine of each
#: program is recorded in its manifest schema tag.
_ARTIFACT_SUBDIR = "xscript"


def is_xscript_program_manifest(manifest: dict[str, Any]) -> bool:
    """True when a loaded program manifest was authored by the xscript engine."""

    return str((manifest or {}).get("schema") or "") == XSCRIPT_PROGRAM_SCHEMA


def _program_manifest_path(
    project_root: str, domain: str, program_id: str
) -> Path | None:
    root = Path(project_root) / _ARTIFACT_SUBDIR
    candidates = [root / domain / program_id / "program.json"]
    if domain == "partdesign":
        candidates.append(root / program_id / "program.json")
        candidates.append(root / program_id / "manifest.json")
    candidates.append(root / domain / program_id / "manifest.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _manifest_engine(project_root: str, domain: str, program_id: str) -> str:
    """Return "xscript" or "legacy" for one persisted program.

    A program whose manifest still carries the pre-resync ``PROGRAM_SCHEMA`` tag
    is reported as ``legacy`` so convert-on-open can retag it to the canonical
    ``XSCRIPT_PROGRAM_SCHEMA``. An untagged/unreadable live program is treated as
    xscript (the current engine)."""

    path = _program_manifest_path(project_root, domain, program_id)
    if path is None:
        return "xscript"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "xscript"
    return "xscript" if is_xscript_program_manifest(manifest) else "legacy"


def document_program_refs(doc: Any) -> list[tuple[str, str]]:
    """(domain, program_id) for every published scripted program in a document."""

    refs: list[tuple[str, str]] = []
    for obj in list(getattr(doc, "Objects", []) or []):
        properties = set(getattr(obj, "PropertiesList", []) or [])
        if not {PROP_PROGRAM_ID, PROP_PROGRAM_DOMAIN} <= properties:
            continue
        program_id = str(getattr(obj, PROP_PROGRAM_ID, "") or "").strip()
        domain = str(getattr(obj, PROP_PROGRAM_DOMAIN, "") or "").strip()
        if program_id and domain and (domain, program_id) not in refs:
            refs.append((domain, program_id))
    return refs


def document_engine(doc: Any, project_root: str) -> str:
    """Classify a document as plain | xscript | xscript | mixed."""

    refs = document_program_refs(doc)
    if not refs:
        return "plain"
    engines = {
        _manifest_engine(project_root, domain, program_id)
        for domain, program_id in refs
    }
    if len(engines) == 1:
        return next(iter(engines))
    return "mixed"


def retag_programs_to_xscript(
    project_root: str, refs: list[tuple[str, str]]
) -> dict[str, Any]:
    """Rewrite each program manifest's schema tag to xscript in place."""

    retagged: list[str] = []
    skipped: list[str] = []
    for domain, program_id in refs:
        path = _program_manifest_path(project_root, domain, program_id)
        if path is None:
            skipped.append(program_id)
            continue
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            skipped.append(program_id)
            continue
        if str(manifest.get("schema") or "") == XSCRIPT_PROGRAM_SCHEMA:
            continue
        manifest["schema"] = XSCRIPT_PROGRAM_SCHEMA
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(manifest, ensure_ascii=True, indent=2), encoding="utf-8"
        )
        tmp.replace(path)
        retagged.append(program_id)
    return {"retagged": retagged, "skipped": skipped}


_BLOCKED_NAMES = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "globals",
        "help",
        "input",
        "locals",
        "open",
        "vars",
    }
)
_BLOCKED_DOC_METHODS = frozenset(
    {
        "close",
        "open",
        "restore",
        "save",
        "saveAs",
        "saveCopy",
        "saveToFile",
    }
)


def validate_program_source(source: str) -> None:
    text = str(source or "")
    encoded = text.encode("utf-8")
    if not text.strip():
        raise ValueError("XScript program source is required.")
    if len(encoded) > MAX_SOURCE_BYTES:
        raise ValueError(f"XScript source exceeds {MAX_SOURCE_BYTES} UTF-8 bytes.")
    if "\x00" in text:
        raise ValueError("XScript source cannot contain NUL bytes.")
    try:
        tree = ast.parse(text, filename="<cadex-domain-xscript>", mode="exec")
    except SyntaxError as exc:
        raise ValueError(f"XScript source has invalid syntax: {exc}") from exc
    violations: list[str] = []
    for node in ast.walk(tree):
        line = int(getattr(node, "lineno", 0) or 0)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            violations.append(f"line {line}: imports are not allowed")
        elif isinstance(node, ast.Name) and node.id in _BLOCKED_NAMES:
            violations.append(f"line {line}: name {node.id!r} is not allowed")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                violations.append(f"line {line}: private attributes are not allowed")
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "doc"
                and node.attr in _BLOCKED_DOC_METHODS
            ):
                violations.append(
                    f"line {line}: document lifecycle method {node.attr!r} is not allowed"
                )
    if violations:
        raise ValueError(
            "XScript source policy violation: " + "; ".join(violations[:12])
        )


def _property_schema(description: str, **schema: Any) -> dict[str, Any]:
    return {"description": description, **schema}


def _base_tool_spec(
    pack: XScriptWorkbenchPack,
    operation: str,
    *,
    description: str,
    properties: dict[str, Any],
    required: tuple[str, ...],
    safety: str,
) -> dict[str, Any]:
    return {
        "name": f"{pack.engine}.{pack.domain}.{operation}",
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": list(required),
            "additionalProperties": False,
        },
        "safety": safety,
        "workbench": pack.workbench,
        "contextual": True,
        "requires_document": operation != "describe_api",
        "edit_modes": ["none"],
    }


def project_tool_specs() -> tuple[dict[str, Any], ...]:
    """The complete provider tool surface: the four ``xscript.project.*`` tools.

    write_script replaces the whole script, edit_script applies unique-match
    replacements, set_params patches declared parameter values, and
    describe_api returns the exact runtime contract. All reads live in
    ``core.inspect`` (scope='script' for source/params/revisions).
    """

    pack = PROJECT_PACK
    expected_revision = _property_schema(
        "Exact current working revision from core.inspect scope='script' or "
        "the previous write result. Use an empty string only when no project "
        "script exists yet.",
        type="string",
        pattern="^([0-9a-f]{64})?$",
    )
    return (
        _base_tool_spec(
            pack,
            "describe_api",
            description=(
                "Describe the project-script runtime: the sketcher, part, "
                "partdesign, mesh, and assembly APIs staged as same-named "
                "globals, the params/num parameter vocabulary, the result "
                "contract, and the revision rule."
            ),
            properties={},
            required=(),
            safety="READ",
        ),
        _base_tool_spec(
            pack,
            "write_script",
            description=(
                "Replace THE project script with a complete source, execute "
                "it in an isolated worker, validate every declared output, "
                "and publish the whole document in one transaction. The "
                "script is the sole source of truth: outputs come only from "
                "assigning result to a dict of domain-API values."
            ),
            properties={
                "source": _property_schema(
                    "Complete project script source using only the staged "
                    "sketcher/part/partdesign/mesh/assembly APIs plus "
                    "params/num.",
                    type="string",
                    minLength=1,
                    maxLength=MAX_SOURCE_BYTES,
                ),
                "expected_revision": expected_revision,
            },
            required=("source", "expected_revision"),
            safety="SAFE_WRITE",
        ),
        _base_tool_spec(
            pack,
            "edit_script",
            description=(
                "Apply exact find/replace edits to the current project "
                "script, then re-execute, validate, and publish the guarded "
                "candidate. Use for targeted source changes; every old "
                "string must occur exactly once."
            ),
            properties={
                "replacements": _property_schema(
                    "Exact source replacements; every old string must occur "
                    "exactly once in the current script.",
                    type="array",
                    minItems=1,
                    maxItems=64,
                    items={
                        "type": "object",
                        "properties": {
                            "old": {"type": "string", "minLength": 1},
                            "new": {"type": "string"},
                        },
                        "required": ["old", "new"],
                        "additionalProperties": False,
                    },
                ),
                "expected_revision": expected_revision,
            },
            required=("replacements", "expected_revision"),
            safety="SAFE_WRITE",
        ),
        _base_tool_spec(
            pack,
            "set_params",
            description=(
                "Patch the values of parameters the project script declares "
                "with params/num, then re-execute the unchanged source and "
                "publish the result. Values-only: the source, parameter "
                "declarations, and output names are untouched."
            ),
            properties={
                "values": _property_schema(
                    "RFC 7396 merge patch of declared parameter values; each "
                    "key must name a declared parameter and map to a finite "
                    "number (null restores the declared default).",
                    type="object",
                    minProperties=1,
                    additionalProperties={"type": ["number", "null"]},
                ),
                "expected_revision": expected_revision,
            },
            required=("values", "expected_revision"),
            safety="SAFE_WRITE",
        ),
    )


def register_project_tools(registry: Any) -> None:
    """Register the project pack's tools; the session runner executes them."""

    for raw_spec in project_tool_specs():
        registry.register_spec(raw_spec, None)
