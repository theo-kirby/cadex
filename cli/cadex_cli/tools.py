# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The tool surface the model sees, generated from ``OP_ARG_SPECS``.

**Tool names are op names.** The Blender shell invented friendlier ones
(``write_script`` → ``write_cad_script`` and so on) because it had a second
vocabulary to reconcile — Blender's. The CLI has none, and a third
vocabulary would be a third thing to keep in sync with the protocol for no
benefit the model can feel.

**The schemas are generated, not written.** Every parameter's name and JSON
type comes from the engine's own ``OP_ARG_SPECS``, so a tool schema cannot
drift from the protocol: adding an argument to an op adds it here, and
removing one removes it here. What is hand-written is only the prose — the
descriptions, which the protocol does not carry.

**``expected_revision`` is not in the schemas.** The guard exists for
concurrent writers and a CLI run has exactly one writer, so
:mod:`cadex_cli.bridge` fills it in from the last reply. The model is still
shown the revision on every result — the value it would have had to guess
is reported rather than demanded.

**``display`` is not in the schemas either.** It asks the engine for
tessellation, which is what a viewport needs and nothing here has. BREP
artifacts are staged for every declared output regardless, which is what
:mod:`cadex_cli.export` reads.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

#: The ops the model may call, in the order they are listed to it.
CLI_TOOL_OPS = (
    "describe_api",
    "write_script",
    "edit_script",
    "set_params",
    "rebuild",
    "inspect",
    # A part built in another project (ADR-138). Here rather than left to the
    # `cadex link` subcommand because a turn that is told "use the sensor
    # from ../sensorA" cannot otherwise do it: nothing else in the surface
    # reaches outside this project.
    "link_part",
    # A file the caller hands over (ADR-190): a trained `.cxpolicy` and the
    # receipt it travels with, or a mesh. Here because the lifecycle audit
    # (docs/MUJOCO.md §7c, row 5) found the agent inventing a "put_asset
    # command" it did not have: nothing else in the surface writes the
    # project store from outside the script.
    "put_asset",
)

#: Filled in by the bridge from the last reply, so never asked of the model.
INJECTED_ARGS = frozenset({"expected_revision"})

#: Meaningless without a viewport (see the module docstring).
OMITTED_ARGS = frozenset({"display"})

_JSON_TYPES: dict[type, str] = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
    dict: "object",
    list: "array",
}

TOOL_DESCRIPTIONS: dict[str, str] = {
    "describe_api": (
        "Return the xscript authoring contract live from the engine: the "
        "program schema, the globals a script may use, and every domain's "
        "exported functions with their signatures. Call this before writing "
        "your first script, and again whenever you need an exact signature. "
        "Never write an xscript API from memory."
    ),
    "write_script": (
        "Replace the whole project script and rebuild. The engine parses, "
        "runs and validates it, then either accepts it or returns a "
        "structured refusal naming what went wrong. This is the tool for a "
        "shape change."
    ),
    "edit_script": (
        "Apply exact string replacements to the current script and rebuild. "
        "Every `old` must occur exactly once in the current source. Cheaper "
        "and safer than rewriting a long script for a small change."
    ),
    "set_params": (
        "Set declared parameter values, connection rows or terminal rows and "
        "re-run the unchanged script. Use this when only numbers change; it "
        "never touches the source."
    ),
    "rebuild": (
        "Re-run the accepted script into a fresh document and report the "
        "content digest. Use it to confirm the model still reproduces."
    ),
    "inspect": (
        "Read engine state. This is how you verify your work: there is no "
        "viewport here and no screenshot to look at."
    ),
    "link_part": (
        "Pull one accepted solid out of ANOTHER project directory and store "
        "it here as a .cxpart, which a script then uses with "
        "part.import_part(\"<name>.cxpart\"). It arrives as the exact solid "
        "that project accepted — not a mesh of it — so booleans, selectors "
        "and assembly.component all work on it. Call it again with the same "
        "arguments to refresh: the reply's `changed` says whether the other "
        "project moved, and a rebuild is what makes a change take effect "
        "here. Omit `output` to be told what that project declares."
    ),
    "put_asset": (
        "Copy ONE file from disk into this project's assets/ so a script can "
        "name it: a trained control policy (.cxpolicy) with the .json task "
        "and .xml model it travels with, a mesh (.stl/.obj/.ply) for "
        "mesh.import_file, or a .cxpart. A path, not bytes. The reply "
        "carries the stored name, its size and its sha256 — which is the "
        "digest assembly.policy(weights=..., sha256=...) requires; never "
        "guess it. Storing under a name that already exists replaces it. "
        "This changes no geometry by itself: a rebuild or a script change "
        "is what makes the file take effect."
    ),
}

ARG_DESCRIPTIONS: dict[tuple[str, str], str] = {
    ("write_script", "source"): (
        "The complete new script source. Lengths are millimetres. Declare "
        "user-tunable dimensions with params(name=num(...)) at the top and "
        "use them throughout, so the model stays parametric; keep parameter "
        "names stable across edits. Assign every kept value into a `result` "
        "dict, whose keys become the published output names."
    ),
    ("write_script", "replace"): (
        "Set true when you mean to drop an output the accepted revision "
        "declares. Without it a script that would remove one is refused, "
        "because write_script replaces THE whole script and losing an output "
        "by accident is easy."
    ),
    ("edit_script", "replacements"): (
        'Array of {"old": ..., "new": ...} objects, applied in order. Each '
        "`old` must occur exactly once in the current source."
    ),
    ("set_params", "values"): (
        "Object of declared parameter name to new numeric value. Values are "
        "clamped to each parameter's declared min/max. Send an empty object "
        "to change only the connections."
    ),
    ("set_params", "nets"): (
        "The COMPLETE connection table for a script that declares one with "
        'nets(...) — a list of {"name", "a", "b", "gauge_mm", "solder", '
        '"enabled"} rows, where `a` and `b` are "<port>.<terminal>" '
        "addresses. Not a patch: rows you omit are dropped, so read the "
        "current table with `inspect scope=wiring` first. Omit this argument "
        "entirely to leave the connections alone."
    ),
    ("set_params", "boards"): (
        "The COMPLETE terminal table for a script that declares one with "
        'boards(...) — a list of {"board", "name", "origin", "axis", '
        '"hole_dia", "depth"} rows, in millimetres in that board\'s own '
        "frame. `hole_dia` present means a hole, absent means a pad. Not a "
        "patch: rows you omit are dropped, so read the current table with "
        "`inspect scope=wiring` first. Omit this argument entirely to leave "
        "the terminals alone."
    ),
    ("link_part", "source_project"): (
        "Path to the OTHER project's root directory — the one that owns the "
        "part. It is never opened and never changed; only its accepted "
        "revision is read."
    ),
    ("link_part", "output"): (
        "Which of that project's declared outputs to pull. It must be a "
        "solid. Omit this to be told what it declares."
    ),
    ("link_part", "name"): (
        "Filename to store it under here, ending in .cxpart. Defaults to "
        "<output>.cxpart. Re-using a name is how a part is refreshed."
    ),
    ("inspect", "scope"): (
        "What to read. `script` is the current source, parameters and "
        "revisions; `output` is the accepted revision's per-output facts "
        "(volume, shape type, bounding box, face counts) and is the main way "
        "to check geometry; `document` lists the published objects; `object` "
        "details one of them by exact internal name; `assets` lists the "
        "importable files; `history` is the accepted-revision trail; `wiring` "
        "is the harness as a graph — every resolved terminal and the "
        "connection table over them, and the thing to read before sending "
        "`set_params` a `nets` or `boards` list; `api` is the tool surface."
    ),
    ("inspect", "target"): (
        "The exact name the scope keys on — an output name for `output`, an "
        "internal object name for `object`, a revision for `history`."
    ),
    ("inspect", "path"): (
        'A JSON-pointer-ish path into the scope\'s value, e.g. "/facts" or '
        '"/facts/volume" under output scope. Omit for the whole value.'
    ),
    ("put_asset", "source_path"): (
        "Absolute or project-relative path of the file to copy in. It must "
        "already exist on this machine; the engine reads it, never you."
    ),
    ("put_asset", "name"): (
        "The name to store it under, keeping the source file's suffix. "
        "Defaults to the source file's own name."
    ),
    ("inspect", "offset"): "Page offset for a paged scope; 0-based.",
    ("inspect", "limit"): "Page size for a paged scope; 1 to 50.",
}

#: Scopes a headless client can serve. `image` is left out: it lists the
#: reference images a *shell* stored, and nothing here can put one there.
#: `blueprint` is IN, and the asymmetry is deliberate (ADR-150): a reference
#: image is a shell-only *input*, while a blueprint sheet is a stored
#: *deliverable* of the project — a headless caller cannot render one
#: (`put_blueprint` is absent from CLI_TOOL_OPS for exactly that reason),
#: but reading and exporting what the shell stored is this client's job.
INSPECT_SCOPES = (
    "script",
    "output",
    "document",
    "object",
    "assets",
    "history",
    "wiring",
    "blueprint",
    "api",
)


def _json_type(python_type: type) -> str:
    return _JSON_TYPES.get(python_type, "string")


def _property_schema(op: str, name: str, python_type: type) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": _json_type(python_type)}
    description = ARG_DESCRIPTIONS.get((op, name))
    if description:
        schema["description"] = description
    if op == "inspect" and name == "scope":
        schema["enum"] = list(INSPECT_SCOPES)
    if op == "edit_script" and name == "replacements":
        schema["items"] = {
            "type": "object",
            "properties": {"old": {"type": "string"}, "new": {"type": "string"}},
            "required": ["old", "new"],
            "additionalProperties": False,
        }
    if op == "set_params" and name == "boards":
        schema["items"] = {
            "type": "object",
            "properties": {
                "board": {"type": "string"},
                "name": {"type": "string"},
                "origin": {"type": "array", "items": {"type": "number"}},
                "axis": {"type": "array", "items": {"type": "number"}},
                "hole_dia": {"type": ["number", "null"]},
                "depth": {"type": ["number", "null"]},
                "frame": {"type": "string", "enum": ["world", "board"]},
            },
            "required": ["board", "name", "origin", "axis"],
            "additionalProperties": False,
        }
    if op == "set_params" and name == "nets":
        schema["items"] = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "a": {"type": "string"},
                "b": {"type": "string"},
                "gauge_mm": {"type": "number"},
                "solder": {"type": "boolean"},
                "enabled": {"type": "boolean"},
            },
            "required": ["name", "a", "b", "gauge_mm"],
            "additionalProperties": False,
        }
    return schema


def tool_definitions(protocol: ModuleType) -> list[dict[str, Any]]:
    """MCP tool definitions for :data:`CLI_TOOL_OPS`, from ``OP_ARG_SPECS``."""

    definitions: list[dict[str, Any]] = []
    for op in CLI_TOOL_OPS:
        required_args, optional_args = protocol.OP_ARG_SPECS[op]
        properties: dict[str, Any] = {}
        required: list[str] = []
        for name, python_type in required_args.items():
            if name in INJECTED_ARGS or name in OMITTED_ARGS:
                continue
            properties[name] = _property_schema(op, name, python_type)
            required.append(name)
        for name, python_type in optional_args.items():
            if name in INJECTED_ARGS or name in OMITTED_ARGS:
                continue
            properties[name] = _property_schema(op, name, python_type)
        definitions.append(
            {
                "name": op,
                "description": TOOL_DESCRIPTIONS[op],
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": sorted(required),
                    "additionalProperties": False,
                },
            }
        )
    return definitions


def injects_revision(protocol: ModuleType, op: str) -> bool:
    """True when ``op`` takes an ``expected_revision`` the bridge supplies."""

    required_args, optional_args = protocol.OP_ARG_SPECS.get(op, ({}, {}))
    return "expected_revision" in required_args or "expected_revision" in optional_args
