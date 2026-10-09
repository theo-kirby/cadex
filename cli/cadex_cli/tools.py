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
descriptions, which the protocol does not carry — and the one exception
below.

**``describe_api``'s ``section`` is the bridge's, not the protocol's
(ADR-360).** The engine's op takes no argument and returns the whole
contract; the bridge offers ``section`` so the model can ask for one page
of it at a time, consumes it, and never sends it on. :data:`VIEW_ARGS` is
that allowlist, and the drift test reads it.

**``expected_revision`` is not in the schemas.** The guard exists for
concurrent writers and a CLI run has exactly one writer, so
:mod:`cadex_cli.bridge` fills it in from the last reply. The model is still
shown the revision on every result — the value it would have had to guess
is reported rather than demanded.

**``display`` is not in the schemas either — the bridge supplies it too.**
It asks the engine for tessellation, which no tool result carries; but the
accepted attempt it lands in is what the review dashboard draws, and an
attempt accepted *without* it left a freshly created project unreviewable
until a later public rebuild republished it (ADR-312). So every modelling
op the model calls carries the same standard request `cadex params` makes
(ADR-293), the model is never asked for it, and :mod:`cadex_cli.bridge`
drops the resulting block from what the model sees. BREP artifacts are
staged for every declared output regardless, which is what
:mod:`cadex_cli.export` reads.
"""

from __future__ import annotations

import json
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
    # `cadex link` subcommand because an agent that is told "use the sensor
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

#: Filled in by the bridge — the revision from the last reply, the display
#: request as a constant — so never asked of the model.
INJECTED_ARGS = frozenset({"expected_revision", "display"})

#: Offered to the model and consumed by the bridge (ADR-360): ``(op, name)``
#: to the JSON type and the prose. These never reach the engine, whose
#: ``OP_ARG_SPECS`` do not carry them; the drift test allows exactly these.
VIEW_ARGS: dict[tuple[str, str], tuple[type, str]] = {
    ("describe_api", "section"): (
        str,
        "One page of the contract: a domain name from the index's `domains`, "
        "or `library` for the catalog and the lib exports. Omit it for the "
        "index, which lists every export by name and names the sections.",
    ),
}

#: The tessellation request every modelling op carries: what `cadex params`
#: asks for (ADR-293), and what the review dashboard draws (ADR-312).
STANDARD_DISPLAY: dict[str, Any] = {"quality": "standard", "edges": False}

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
        "Return the xscript authoring contract live from the engine, one "
        "page at a time so each fits one tool result. Without `section`: the "
        "index — the program schema, the globals a script may use, and every "
        "domain's exports by name. With `section=<domain>` or "
        "`section=library`: that section's notes and every export's full "
        "signature with the first paragraph of its documentation; the "
        "page's `descriptions` line says which inspect scope=api path holds "
        "the rest. Call the index before writing your first script, then the "
        "section of every domain you use, and again whenever you need an "
        "exact signature. Never write an xscript API from memory."
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
        "Read engine state. This is how you verify your work in numbers; "
        "`look` is how you see it. scope=clearance is the "
        "measured fit of the accepted assembly, every pair; a build reply's "
        "`fit` block is its summary. scope=anatomy is the moving-anatomy "
        "check behind a build reply's `anatomy` block."
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

#: Tools the bridge answers itself, with no engine op behind them (ADR-406).
#: Listed after the protocol-derived ones, so CLI_TOOL_OPS stays exactly the
#: ops the engine serves and the drift test keeps meaning what it says.
BRIDGE_TOOLS: dict[str, dict[str, Any]] = {
    "look": {
        "description": (
            "SEE the accepted design: rendered images of the last accepted "
            "revision, returned to you as pictures. Each part is drawn in the "
            "appearance role you declared (`assembly.component(..., "
            "appearance='shell'|'mechanism'|'accent')`) in the assembly's "
            "`palette`; an undeclared part is bone shell if printed and "
            "graphite mechanism if purchased. Environment geometry "
            "(a floor) is left out. Views: `hero` (the presented studio shot: "
            "low, front-right, three-quarter), `iso` (front-right, from above), "
            "`iso_back` (back-left, from above), `front`, `right`, `top`. "
            "Orthographic and studio-lit so curvature reads, with a contact "
            "shadow on the floor; no edges or dimensions. Pass `focus` "
            "with component or output names to frame a close-up on them. "
            "Look after every accepted shape change and before you say a "
            "design is done: numbers prove it fits, only a look shows "
            "whether it is well designed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "views": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["hero", "iso", "iso_back", "front", "right", "top"]},
                    "description": "Which views, in order; default iso and iso_back. At most 5.",
                },
                "focus": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Names to frame the view on (component or output names from the "
                        "build reply); everything else is still drawn. Omit for the whole design."
                    ),
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    # The drawing sheet (ADR-516): the owner kept the blueprint composer as a
    # headless tool. The engine composes it; the store versions it by name.
    "draw_blueprint": {
        "description": (
            "DRAW A DIMENSIONED BLUEPRINT SHEET of the accepted design and store it "
            "with the project, versioned by `name`; the sheet comes back to you as a "
            "picture and the dashboard shows it under Drawings. Line drawings on one "
            "shared scale, up to four views (default: top, iso, front, right in the "
            "third-angle arrangement); each orthographic view carries the overall "
            "extents in mm, and every part.measurement(...) the script declares is "
            "drawn once where it reads (a design that places components lists them "
            "instead). Callouts are numbered balloons on the three-quarter view, keyed "
            "in a parts list; a title block names the sheet, version, revision, digest, "
            "date and scale. Drawing again under a stored name stores its next version, "
            "and any key you leave out is taken from that sheet's stored recipe. Draw "
            "one when a design is accepted and worth documenting, not after every edit."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The sheet's name, its identity and title, e.g. "
                    "\"gearbox overview\". At most 60 characters.",
                },
                "views": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["front", "right", "top", "iso", "iso_back"]},
                    "description": "1 to 4 distinct views, laid out row-major on a 2x2 grid.",
                },
                "callouts": {
                    "type": ["boolean", "array"],
                    "items": {"type": "string"},
                    "description": "true (default: the largest parts, up to 12), false, or "
                    "the component or output names to balloon.",
                },
                "dimensions": {
                    "type": "boolean",
                    "description": "Overall extents and declared measurements; default true.",
                },
                "notes": {
                    "type": "string",
                    "description": "A short note printed on the sheet, at most 400 characters.",
                },
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    # The training loop (ADR-464): design a task, train on it, evaluate the
    # policy against the task's success spec, revise. The same four tools for
    # every behaviour; none of them knows what is being trained.
    "train_start": {
        "description": (
            "START ONE BOUNDED TRAINING RUN on the accepted revision's task, and "
            "return at once: the run trains under a supervisor that outlives this "
            "session. The run is pre-registered before it starts -- its settings, "
            "its seed, its wall-clock budget, its stop rule and your reason are "
            "written to runs/<run>/registration.json -- so say in `reason` which "
            "measurement from the last evaluation motivated this run and what you "
            "expect to change. It trains the task AS ACCEPTED NOW: revise the "
            "reward, observations, terminations or success spec first, with "
            "edit_script, and start the run after the build is accepted. It stops "
            "at the last iteration, at `budget_s`, when the mean episode collapses, "
            "or on train_stop. One run at a time; a run's name is used once. A "
            "training seed may not be one of the task's evaluation seeds."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run": {
                    "type": "string",
                    "description": "A new short name for this run: lowercase letters, "
                    "digits, '.', '_' or '-'. It becomes runs/<run>/ in the project.",
                },
                "budget_s": {
                    "type": "number",
                    "description": "Wall-clock budget in seconds. Required: a run with "
                    "no budget is not started. The run is stopped when it runs out.",
                },
                "reason": {
                    "type": "string",
                    "description": "One or two sentences: the measurement that motivated "
                    "this run and what it is expected to change.",
                },
                "task": {
                    "type": "string",
                    "description": "Which declared task output, when the script "
                    "declares more than one.",
                },
                "settings": {
                    "type": "object",
                    "description": (
                        "The trainer's settings, all optional: iterations (200), envs "
                        "(256), seed (0), label, hidden (layer widths, [64, 64]), "
                        "unroll, epochs, learning_rate, discount, gae_lambda, clip, "
                        "entropy, value_weight, initial_std, action_filter_alpha, "
                        "command_slew_deg, goal_pool, checkpoint_every (write a "
                        "complete policy every N iterations plus the best so far, so "
                        "a stopped run still leaves one), and the warm start: "
                        "init_from (a .cxpolicy path), with init_from_parent_task and "
                        "init_from_task_change when the task changed since. A warm "
                        "start continues at its source's exploration width unless "
                        "initial_std is set."
                    ),
                },
            },
            "required": ["run", "budget_s", "reason"],
            "additionalProperties": False,
        },
    },
    "train_status": {
        "description": (
            "READ A TRAINING RUN: its state (running, finished, collapsed, failed, "
            "stopped, budget_exhausted, interrupted), the trainer's progress -- "
            "iteration, reward per step, mean episode length, exploration sigma, "
            "the curve -- its checkpoints, and when it finished the policy's path "
            "and sha256, and its task_bundle: the file a warm start from this run "
            "passes as init_from_parent_task. `wait_s` blocks until the run ends or that long passes, "
            "whichever is first. Without `run`: every run of this project and the "
            "loop's ledger of runs and evaluations, which is how a new session learns "
            "what was already tried. A reward curve is progress, never a verdict."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run": {"type": "string", "description": "The run's name. Omit for all runs."},
                "wait_s": {
                    "type": "number",
                    "description": "Wait up to this many seconds (at most 900) for the "
                    "run to end before answering. Default 0.",
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    "train_stop": {
        "description": (
            "STOP A RUNNING TRAINING RUN, with the reason. The supervisor stops the "
            "trainer and records the run as stopped; checkpoints it already wrote "
            "stay and each is a complete policy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run": {"type": "string", "description": "The run's name."},
                "reason": {"type": "string", "description": "Why it is being stopped."},
            },
            "required": ["run", "reason"],
            "additionalProperties": False,
        },
    },
    "evaluate": {
        "description": (
            "EVALUATE THE ACCEPTED POLICY against its task's success spec: one "
            "rollout per frozen evaluation seed under the spec's conditions. The "
            "reply is the verdict, pass or fail per seed and per predicate, the "
            "behaviour metrics, the reward term by term and how each episode "
            "ended, followed by FILMSTRIPS of a seed as pictures -- an overview "
            "of the whole episode and a detail sheet -- on the dark floor. It "
            "evaluates the policy the accepted script declares, so store a "
            "trained policy with put_asset and name it with assembly.policy "
            "first. Diagnose a failure from these measurements and the film "
            "before revising; the full report is evaluation.json in the project."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "policy": {
                    "type": "string",
                    "description": "Which declared policy output, when there is more than one.",
                },
                "task": {
                    "type": "string",
                    "description": "Pick the policy declared against this task output.",
                },
                "film": {
                    "type": "string",
                    "description": "Which seeds to draw: auto (the first failing seed, or "
                    "the first seed of a pass), none, or seed numbers separated by "
                    "commas. At most two are returned as pictures. Default auto.",
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
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
        "`set_params` a `nets` or `boards` list; `inventory` is what the "
        "assembly is MADE OF — one row per component with the output it "
        "places, that output's catalog family and part number when a lib.* "
        "generator built it, and the pose the solver settled on; `clearance` "
        "is the MEASURED FIT of the accepted assembly — every component "
        "pair's minimum distance (mm) and common volume (mm³), measured by "
        "the engine from the exact solids at the solved pose, with each "
        "pair's label and catalog identity — the evidence that parts fit, "
        "where a script's printout is only a claim; `contacts` is which "
        "parts' COLLISION SHAPES already touch at rest, at the pose every "
        "simulation starts from, per assembly.mjcf export — a pair you did "
        "not mean to rest together, or any `penetrating` pair, is a "
        "collision shape in the wrong place; `anatomy` is the creature's "
        "MOVING ANATOMY — per region assembly.anatomy declared, the joints "
        "that move it and which an actuator drives, its status (articulated, "
        "rigid with a reason, rigid with no reason, passive only), and every "
        "large welded piece that sticks out of its rigid body (a fused head, "
        "a rigid tail); `api` is the tool surface."
    ),
    ("inspect", "target"): (
        "The exact name the scope keys on — an output name for `output`, an "
        "internal object name for `object`, a revision for `history`, an "
        "assembly output name for `inventory`, an assembly.mjcf output "
        "name for `contacts`."
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
#: reference images the deleted shell stored (ADR-498), and nothing here can
#: put one there.
#: `blueprint` is IN, and the asymmetry is deliberate (ADR-150): a reference
#: image was a shell-only *input*, while a blueprint sheet is a stored
#: *deliverable* of the project. The model draws one with the bridge's
#: `draw_blueprint` (ADR-516), which calls `put_blueprint` itself, so that
#: op stays out of CLI_TOOL_OPS: a path to an arbitrary PNG is not a tool.
INSPECT_SCOPES = (
    "script",
    "output",
    "document",
    "object",
    "assets",
    "history",
    "wiring",
    "inventory",
    # The measured fit (ADR-346): the same published pair measurements
    # `cadex clearance` reports, offered to the model whole because the
    # `fit` block on a build reply is a summary of them.
    "clearance",
    # Which parts' collision shapes touch at rest (ADR-508): the MJCF
    # export's t=0 contacts, so the agent reads what the dashboard's
    # collision view shows without a person looking.
    "contacts",
    # The creature's moving anatomy (ADR-614): the `anatomy` block on a
    # build reply is a bounded view of exactly this scope.
    "anatomy",
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
    """MCP tool definitions for :data:`CLI_TOOL_OPS`, from ``OP_ARG_SPECS``,
    followed by :data:`BRIDGE_TOOLS`, which no engine op backs."""

    definitions: list[dict[str, Any]] = []
    for op in CLI_TOOL_OPS:
        required_args, optional_args = protocol.OP_ARG_SPECS[op]
        properties: dict[str, Any] = {}
        required: list[str] = []
        for name, python_type in required_args.items():
            if name in INJECTED_ARGS:
                continue
            properties[name] = _property_schema(op, name, python_type)
            required.append(name)
        for name, python_type in optional_args.items():
            if name in INJECTED_ARGS:
                continue
            properties[name] = _property_schema(op, name, python_type)
        for (view_op, name), (python_type, description) in VIEW_ARGS.items():
            if view_op == op:
                properties[name] = {"type": _json_type(python_type), "description": description}
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
    for name, definition in BRIDGE_TOOLS.items():
        definitions.append({"name": name, **json.loads(json.dumps(definition))})
    return definitions


def injects_revision(protocol: ModuleType, op: str) -> bool:
    """True when ``op`` takes an ``expected_revision`` the bridge supplies."""

    return _takes(protocol, op, "expected_revision")


def injects_display(protocol: ModuleType, op: str) -> bool:
    """True when ``op`` takes a ``display`` request the bridge supplies."""

    return _takes(protocol, op, "display")


def _takes(protocol: ModuleType, op: str, name: str) -> bool:
    required_args, optional_args = protocol.OP_ARG_SPECS.get(op, ({}, {}))
    return name in required_args or name in optional_args
