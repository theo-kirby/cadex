# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Mesh agent tools.

The agent never mutates the scene directly: it writes and edits the model
script (see model.py), and the scene is rebuilt from it. Definitions are
served to Claude Code through the MCP shim (see ``bridge.py``); executors run
on Blender's main thread only. Each executor returns ``(content, is_error)``
where content is a list of MCP content blocks (``{"type": "text", ...}`` or
``{"type": "image", ...}``).
"""

import json
import traceback

MAX_RESULT_CHARS = 4096

# describe_cad_api serves reference material the model asked for by name;
# truncating a domain's signatures at 4 KB would defeat its purpose. At 16 KB
# it truncated them anyway -- mid-structure, so `part` and `assembly` came
# back as unparseable blobs and half of each domain was unreachable
# (ADR-123). The default path is compact now and must never truncate: the
# largest domain it serves is `assembly` at ~19 KB (~16 KB of it signatures,
# the rest its notes), so this leaves room for the surface to grow. The cap
# survives only as a backstop on the functions=[...] path, where the model
# chose the names and can ask for fewer.
_API_DOMAIN_CHARS = 32768

# get_script serves the exact text the next edit_script has to match. A
# truncated script is worse than no script: the model cannot see that the
# half it was given is the half it needs, so it edits blind, or --
# as happened -- goes looking for the missing half by other means. Any
# real project script fits well inside this; one that does not is reported
# as truncated in a sentence rather than a marker (ADR-044).
_SCRIPT_CHARS = 65536

# Tools whose execution mutates the scene (drives per-turn undo batching).
MUTATING_TOOLS = {"write_script", "set_params", "edit_script", "rebuild_model",
                  "restore_version"}

# Tools that reach the cadex engine; these are preflighted so a missing
# engine reports itself once, in a sentence, rather than as a traceback from
# deep inside process spawning. (Before ADR-030 this set was conditional on
# the scene's mode; there is one backend now.)
_ENGINE_TOOLS = {"get_script", "write_script", "set_params",
                 "edit_script", "restore_version", "inspect_model",
                 "describe_cad_api", "scene_summary", "rebuild_model",
                 "import_geometry", "link_part", "make_blueprint"}

TOOL_DEFS = [
    {
        "name": "get_script",
        "description": (
            "Return the current model script plus the declared parameters with "
            "their current values. Call this before editing an existing model. "
            "Called with no arguments it returns the WHOLE script, which is "
            "what an edit needs. If the host refuses that result as too large, "
            "read it in windows with `offset` (1-based line) and `limit` "
            "(line count); every window states the totals and the next offset, "
            "so keep calling until it says the end is reached. Never edit the "
            "script to make it shorter so that it fits — the window moves, the "
            "script does not."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "offset": {"type": "integer",
                           "description": "First line to return, 1-based. Default 1."},
                "limit": {"type": "integer",
                          "description": "How many lines to return. Default: all of them."},
            },
        },
    },
    {
        "name": "write_script",
        "description": (
            "Replace the ENTIRE model script and rebuild the model from it. "
            "This is not 'add a part': whatever the script you pass does not "
            "build no longer exists. To add to a model that already has "
            "parts, call get_script and use edit_script. The script is an "
            "xscript project script run by the cadex engine, and the single "
            "source of truth for the model: `bpy` does not exist in it, "
            "imports are forbidden, and it must be deterministic and "
            "self-contained. Declare user-tunable parameters at the top with "
            "params() / num(); call describe_cad_api for the exact contract "
            "and the domain functions to build with. The result reports the "
            "accepted revision and its outputs — or the engine's structured "
            "refusal, which says what it objected to (fix and rewrite)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string",
                            "description": "Full Python source of the model script."},
                "replace": {
                    "type": "boolean",
                    "description": (
                        "Confirm that dropping outputs the model currently "
                        "has is intended. Without it, a script that removes "
                        "an existing output is refused and nothing changes."),
                },
            },
            "required": ["content"],
        },
    },
    {
        "name": "set_params",
        "description": (
            "Set one or more declared parameter values (the same values the "
            "user's sliders control) and rebuild the scene. Use this instead "
            "of editing the script when only values change."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "params": {
                    "type": "object",
                    "description": "Map of parameter id to new value.",
                    "additionalProperties": True,
                },
            },
            "required": ["params"],
        },
    },
    {
        "name": "edit_script",
        "description": (
            "Cadex mode only. Apply exact string replacements to the "
            "project script instead of rewriting it whole, then rebuild. "
            "Each `old` must occur EXACTLY ONCE in the script or the whole "
            "edit is refused — include enough surrounding text to be "
            "unambiguous. Prefer this over write_script for small changes: "
            "it cannot accidentally drop the parts of the script you did "
            "not mean to touch."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "replacements": {
                    "type": "array",
                    "description": "Applied in order.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "old": {"type": "string",
                                    "description": "Exact text to replace; "
                                                   "must occur exactly once."},
                            "new": {"type": "string",
                                    "description": "Replacement text."},
                        },
                        "required": ["old", "new"],
                    },
                },
            },
            "required": ["replacements"],
        },
    },
    {
        "name": "restore_version",
        "description": (
            "Cadex mode only. Put a previously accepted version of the "
            "script back, then rebuild from it. Every accepted revision is "
            "kept; list them with inspect_model scope='history', which gives "
            "each one an ordinal, a revision and the outputs it declared. "
            "This is the undo for a script that was overwritten or edited "
            "into a state you want to leave — the restored version re-runs "
            "and is re-accepted like any other script."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "version": {
                    "type": "string",
                    "description": (
                        "Ordinal (e.g. '7') or revision prefix (e.g. "
                        "'4b097c378487') from inspect_model scope='history'."),
                },
            },
            "required": ["version"],
        },
    },
    {
        "name": "rebuild_model",
        "description": (
            "Re-run the script the engine already holds, from scratch, and "
            "re-derive the declared parameters, their values and the geometry "
            "from it. Use it when the model and the engine have drifted: the "
            "scene does not match what get_script reports, the sliders show "
            "parameters the script no longer declares, or a set_params call "
            "failed for a parameter you did not send. It sends no script, so "
            "it cannot lose work — but it also cannot fix a script that is "
            "wrong; write_script does that."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "inspect_model",
        "description": (
            "Cadex mode only. Ask the engine about the model it holds: "
            "scope 'script' for the source, parameters and revisions, "
            "'document' for the published objects, 'object' with a target "
            "for one object's properties, 'output' for one accepted output's "
            "measured facts (volume, area, bounds, centre of mass, face and "
            "edge counts — omit the target to list every output), 'assets' "
            "for the external mesh files stored for mesh.import_file(), "
            "'history' for the previously accepted versions of the script "
            "(omit the target to list them, give one to read that version's "
            "source). This is engine truth, unlike the tessellated copies in "
            "the Blender scene."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {"type": "string",
                          "description": "script | document | object | output "
                                         "| assets | history"},
                "target": {"type": "string",
                           "description": "Object name for scope=object; "
                                          "output name for scope=output; "
                                          "ordinal or revision for "
                                          "scope=history."},
                "path": {"type": "string",
                         "description": "Sub-path within the scope, e.g. "
                                        "/revisions or /params."},
            },
            "required": ["scope"],
        },
    },
    {
        "name": "describe_cad_api",
        "description": (
            "Cadex mode only. Return the cadex engine's authoring contract "
            "for xscript project scripts: how a script must be shaped, and "
            "which functions each modelling domain offers. Three steps, "
            "each one narrower: no arguments returns the contract plus every "
            "domain's function names; `domain` returns every signature in "
            "that domain with a one-line summary each; `domain` plus "
            "`functions` returns the full description of just those "
            "functions, which is where the semantics are. Call it for the "
            "domain you are about to use, not once per session. This is "
            "served live by the engine, so it is always the truth about the "
            "version you are talking to — never guess an API from memory."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "One domain (e.g. part, mesh, assembly, "
                                   "partdesign, sketcher). Omit for the "
                                   "overview.",
                },
                "functions": {
                    "type": "array",
                    "description": "Names from that domain to describe in "
                                   "full. Needs `domain`.",
                    "items": {"type": "string"},
                },
            },
        },
    },
    {
        "name": "get_attached_image",
        "description": (
            "Return an image the user attached to the chat, by index. The "
            "user's message notes which indices were attached. Use attached "
            "images as visual reference for the model you build."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer",
                          "description": "Attachment index from the user's message."},
            },
            "required": ["index"],
        },
    },
    {
        "name": "scene_summary",
        "description": (
            "Return a JSON summary of the current scene: every object with its type, "
            "transform, dimensions, modifier stack and materials. Call this to verify "
            "what the model script actually built."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "viewport_screenshot",
        "description": (
            "Render the current 3D viewport to a small PNG image and return it, so you "
            "can visually verify the scene. Unavailable when Blender runs headless; "
            "fall back to scene_summary in that case."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_size": {
                    "type": "integer",
                    "description": "Longest edge of the returned image in pixels (default 768).",
                },
            },
        },
    },
    {
        "name": "render_views",
        "description": (
            "Render the MODEL from four fitted cameras -- front, right, top "
            "and a three-quarter perspective -- composited into one image, so "
            "you can judge the shape you just built. Unlike "
            "viewport_screenshot this ignores the user's camera, hides the "
            "collision cage and any overlay, and frames the Model collection "
            "itself, so it answers 'what did I build' rather than 'what is the "
            "user looking at'. Use it after any change to a silhouette, and "
            "before telling the user a shape is right. Because it hides the "
            "collision cage, checking collision shapes still goes through "
            "collision_view plus viewport_screenshot. Unavailable when "
            "Blender runs headless."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_size": {
                    "type": "integer",
                    "description": ("Longest edge of the composited image in "
                                    "pixels (default 1024; each of the four "
                                    "views gets half of it)."),
                },
            },
        },
    },
    {
        "name": "collision_view",
        "description": (
            "Show or hide the collision shapes the physics solver actually uses, "
            "drawn as wire cages on the parts they belong to. A collision shape "
            "is placed in the COMPONENT frame and may sit outside the solid it "
            "stands for, so nothing about the drawn part says where it is -- "
            "turn this on and take a viewport_screenshot to check that a foot "
            "meets the floor where it looks like it does. Also reports what is "
            "already touching at t = 0, which is what catches a collision shape "
            "placed in the wrong frame. Read-only: it draws an overlay and "
            "changes no geometry."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "show": {
                    "type": "boolean",
                    "description": "True to show, false to hide, omitted to toggle.",
                },
            },
        },
    },
    {
        "name": "section_view",
        "description": (
            "Cut the model open on a plane and take the near half away, so "
            "the inside can be seen: a bore that does not break through, a "
            "wall left too thin, a pocket that missed the boss it was meant "
            "to clear. The cut face is filled, so what you see is material. "
            "Turn it on and take a viewport_screenshot -- render_views "
            "deliberately shows the whole model instead. Read-only: it "
            "changes what is drawn, never the script or the model."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "show": {
                    "type": "boolean",
                    "description": "True to cut, false to stop, omitted to toggle.",
                },
                "axis": {
                    "type": "string",
                    "enum": ["X", "Y", "Z"],
                    "description": "Which axis the plane is square to (default Z).",
                },
                "offset": {
                    "type": "number",
                    "description": ("Where the plane sits along that axis, in "
                                    "mm. Omitted cuts through the middle of "
                                    "the model."),
                },
                "flip": {
                    "type": "boolean",
                    "description": "Keep the other half.",
                },
            },
        },
    },
    {
        "name": "exploded_view",
        "description": (
            "Spread the assembly apart along the explosion moves the script "
            "declares, from 0 (assembled) to 1 (fully exploded), with leader "
            "lines from each part back to its place. The moves come from the "
            "script's declared exploded view -- this only plays them; if the "
            "script declares none, this says so. Turn it on and take a "
            "viewport_screenshot to show how the mechanism goes together -- "
            "render_views deliberately shows the assembled model instead. "
            "Refused while a simulation is baked. Read-only: it changes what "
            "is drawn, never the script or the model."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "show": {
                    "type": "boolean",
                    "description": ("True to explode, false to reassemble, "
                                    "omitted to toggle."),
                },
                "factor": {
                    "type": "number",
                    "description": ("How far apart, 0 to 1 (default 1 when "
                                    "switching on)."),
                },
            },
        },
    },
    {
        "name": "blueprint_view",
        "description": (
            "Draw the model as white outlines on a blueprint-blue, "
            "cutting-mat-green or grey background, live in the viewport, "
            "with an optional 10 mm grid. Turn it on when the user asks for "
            "a technical-drawing look, then take a viewport_screenshot to "
            "show it. It layers over section_view and exploded_view, so a "
            "sectioned or exploded blueprint works; make_blueprint renders "
            "the four-view sheet in this style without needing this toggle. "
            "Turning it off restores the viewport exactly as it was. "
            "Read-only: it changes how the viewport draws, never the script "
            "or the model."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "show": {
                    "type": "boolean",
                    "description": ("True to style, false to restore, "
                                    "omitted to toggle."),
                },
                "theme": {
                    "type": "string",
                    "enum": ["blueprint", "cutting_mat", "grey"],
                    "description": ("The background the white lines are "
                                    "drawn on (default blueprint)."),
                },
                "grid": {
                    "type": "boolean",
                    "description": "Draw the 10 mm grid (default true).",
                },
            },
        },
    },
    {
        "name": "make_blueprint",
        "description": (
            "Render a four-view blueprint sheet of the model -- front, "
            "right, top and a three-quarter perspective, white lines on a "
            "blueprint-blue, cutting-mat-green or grey ground -- and store "
            "it in the project as a drawing attached to the accepted "
            "revision. Unlike render_views it draws the CURRENT "
            "presentation: a section cut or an exploded spread stays in the "
            "sheet, which is how you make a sectioned or exploded drawing. "
            "It does not need blueprint_view to be on. The stored sheets "
            "are listed by inspect_model scope=blueprint. Unavailable when "
            "Blender runs headless."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": ("A one-line label stored with the sheet "
                                    "(what the drawing shows)."),
                },
                "theme": {
                    "type": "string",
                    "enum": ["blueprint", "cutting_mat", "grey"],
                    "description": ("The ground the white lines are drawn "
                                    "on (default blueprint)."),
                },
                "max_size": {
                    "type": "integer",
                    "description": ("Longest edge of the sheet in pixels "
                                    "(default 1024; each view gets half)."),
                },
            },
        },
    },
    {
        "name": "export_stl",
        "description": (
            "Export model parts as STL files for 3D printing, one file per "
            "object (binary STL, 1 Blender unit = 1 STL unit). By default "
            "exports every mesh object in the Model collection to a directory "
            "beside the .blend file (or a temporary directory when unsaved). "
            "Returns the written file paths and triangle counts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "objects": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Object names to export (default: all mesh "
                                   "objects in the Model collection).",
                },
                "directory": {
                    "type": "string",
                    "description": "Output directory (created if missing).",
                },
            },
        },
    },
    {
        "name": "import_geometry",
        "description": (
            "Copy an external mesh file (STL, OBJ or PLY) from anywhere on "
            "disk into the model's asset store, so the script can import it "
            "with mesh.import_file(). Returns the stored name — pass that "
            "name, not the original path. Use this when the user points you "
            "at a component file; use inspect_model with scope 'assets' to "
            "see what is already stored (the user can also drop files in "
            "through File > Import Geometry)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string",
                         "description": "Path to the STL/OBJ/PLY file to import."},
                "name": {"type": "string",
                         "description": "Optional name to store it under "
                                        "(same format suffix; default: the "
                                        "source file's name). Re-using a "
                                        "stored name replaces that asset."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "link_part",
        "description": (
            "Bring a part built in ANOTHER Cadex model into this one. Point "
            "it at that model's .blend or .cadex folder and name the output "
            "you want; it arrives as the exact solid that model accepted — "
            "not a mesh of it — so booleans, selectors and assembly "
            "components all work on it, and the script uses it with "
            "part.import_part(). Returns the stored name; pass that name, "
            "not the path. Call it again with the same arguments to refresh: "
            "'changed' says whether the other model moved, and a rebuild is "
            "what makes a change take effect here. Omit 'output' to be told "
            "what that model publishes. Use this when the user says a part "
            "lives in another file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string",
                           "description": "Path to the other model's .blend "
                                          "file or .cadex project folder. It "
                                          "is only read, never changed."},
                "output": {"type": "string",
                           "description": "Which of that model's outputs to "
                                          "link. It must be a solid. Omit to "
                                          "be told what it publishes."},
                "name": {"type": "string",
                         "description": "Optional name to store it under, "
                                        "ending in .cxpart (default: "
                                        "<output>.cxpart). Re-using a stored "
                                        "name is how a part is refreshed."},
            },
            "required": ["source"],
        },
    },
    {
        "name": "focus_view",
        "description": (
            "Frame the named objects (or the whole scene if none are given) in the 3D "
            "viewport so the user can see them. No-op when Blender runs headless."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "objects": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
]


class Pending:
    """A tool call whose result arrives later.

    Returned by :func:`execute` instead of ``(content, is_error)`` when the
    work must not block Blender's main thread — today, the two cadex
    modeling tools, which run a user script inside the engine. The agent's
    drain loop polls it; :meth:`poll` returns None while in flight and the
    usual ``(content, is_error)`` pair when finished.
    """

    __slots__ = ("_poll",)

    def __init__(self, poll):
        self._poll = poll

    def poll(self):
        return self._poll()

    def wait(self, interval=0.01):
        """Block until the result is ready. Background mode and tests."""
        import time
        while True:
            outcome = self.poll()
            if outcome is not None:
                return outcome
            time.sleep(interval)


def list_tools():
    """Static tool definitions, safe to call from any thread."""
    return TOOL_DEFS


def _text(message):
    return [{"type": "text", "text": message}]


def _truncate(text, limit=MAX_RESULT_CHARS):
    """Cap one tool result, saying plainly how much was dropped.

    The marker has to survive being read by a model that is about to act on
    the text: "[... output truncated ...]" reads as trailing noise, while a
    count reads as a fact about the result, and one that can be checked
    against what the tool was asked for.
    """
    if len(text) > limit:
        return text[:limit] + (
            "\n[... truncated: {:d} of {:d} characters shown. This result is "
            "INCOMPLETE — do not treat it as the whole value ...]".format(
                limit, len(text)))
    return text


def execute(name, tool_input, agent=None):
    """Execute a tool on the main thread. Returns (content_blocks, is_error).
    ``agent`` is the calling Agent, for tools that need per-session state
    (attachments)."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return _text("Unknown tool: {:s}".format(name)), True
    if name in _ENGINE_TOOLS:
        from . import cadex_backend
        ok, reason, remedy = cadex_backend.preflight()
        if not ok:
            # A sentence the model can act on and relay, not a traceback
            # from deep inside process spawning -- and the same sentence in
            # the transcript, so the user is not waiting on a silence.
            _status(reason)
            return _text(reason + " " + remedy
                         + " Tell the user this; do not retry."), True
    try:
        if name in _AGENT_HANDLERS:
            return handler(tool_input, agent)
        return handler(tool_input)
    except Exception:
        return _text(_truncate(traceback.format_exc())), True


def _cancellation_check(agent):
    """The agent's per-turn cancel flag as a zero-argument predicate.

    Bound into the cadexd client, which polls it every 50 ms and forwards a
    ``cancel`` frame, so Escape during a long rebuild reaches the engine.
    """
    if agent is None:
        return None
    return agent.cancellation_check()


def execute_blocking(name, tool_input, agent=None):
    """:func:`execute`, resolving a :class:`Pending` before returning.

    For callers outside the agent's drain loop (tests, background mode).
    """
    result = execute(name, tool_input, agent=agent)
    return result.wait() if isinstance(result, Pending) else result


def _window_arg(tool_input, name):
    """One optional 1-or-more integer, or a sentence saying why it is not.

    ``bool`` is rejected on purpose: ``True`` is an ``int`` in Python and
    ``offset=true`` would silently read line one.
    """
    if name not in tool_input or tool_input[name] is None:
        return None, None
    value = tool_input[name]
    if isinstance(value, str) and value.strip().lstrip("+").isdigit():
        value = int(value.strip())
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None, ("get_script `{:s}` must be a whole number 1 or greater; "
                      "got {!r}.".format(name, tool_input[name]))
    return value, None


def _tool_get_script(tool_input):
    import bpy
    from . import cadex_backend

    tool_input = tool_input or {}
    offset, complaint = _window_arg(tool_input, "offset")
    if complaint:
        return _text(complaint), True
    limit, complaint = _window_arg(tool_input, "limit")
    if complaint:
        return _text(complaint), True

    ok, report = cadex_backend.get_script_report(
        bpy.context.scene, offset=offset, limit=limit)
    return _text(_truncate(report, _SCRIPT_CHARS)), not ok


def _deferred(started, render):
    """Wrap a cadex_backend Lifecycle (or an immediate outcome) for the agent.

    ``render(ok, report)`` turns the engine's verdict into MCP content.
    """
    from . import cadex_backend

    if not isinstance(started, cadex_backend.Lifecycle):
        return render(*started)

    def poll():
        outcome = started.poll()
        return None if outcome is None else render(*outcome)

    return Pending(poll)


def _status(message):
    """One line into the chat transcript, for the user rather than the model.

    cadex_backend's failure reports are written for the model: structured,
    detailed, and invisible to the person watching the panel. Without this a
    rejected revision looks exactly like a hang (cadex ADR-024).
    """
    try:
        from .agent import get_agent
        get_agent().history.add("status", message)
    except Exception:
        pass


def _first_line(report, limit=110):
    line = str(report or "").strip().splitlines()[0] if str(report).strip() else ""
    return line if len(line) <= limit else line[:limit - 1] + "\u2026"


def _render_write_script(ok, report):
    if not ok:
        _status("Engine rejected the script: " + _first_line(report))
        return _text(_truncate(
            "The engine REJECTED the script:\n" + report)), True
    return _text(_truncate(report)), False


def _tool_write_script(tool_input, agent=None):
    import bpy
    from . import cadex_backend

    source = tool_input.get("content", "")
    started = cadex_backend.begin_write_script(
        bpy.context.scene, source,
        replace=bool(tool_input.get("replace")),
        cancelled=_cancellation_check(agent))
    if not isinstance(started, cadex_backend.Lifecycle):
        # Keep the attempted source visible when the engine never ran -- and
        # marked as not in the model, because it is not.
        cadex_backend.mirror_script_text(source, accepted=False)
    return _deferred(started, _render_write_script)


def _render_set_params(ok, report):
    if not ok:
        _status("Engine rejected the parameter change: " + _first_line(report))
        return _text(_truncate(report)), True
    return _text(_truncate(report)), False


def _tool_set_params(tool_input, agent=None):
    import bpy
    from . import cadex_backend

    updates = tool_input.get("params") or {}
    if not isinstance(updates, dict) or not updates:
        return _text("set_params needs a non-empty `params` object."), True
    return _deferred(
        cadex_backend.begin_set_params(
            bpy.context.scene, updates,
            cancelled=_cancellation_check(agent)),
        _render_set_params)


def _render_rebuild_model(ok, report):
    if not ok:
        _status("Engine could not re-run the stored script: "
                + _first_line(report))
        return _text(_truncate(
            "The engine could not re-run the stored script:\n" + report)), True
    return _text(_truncate(report)), False


def _tool_rebuild_model(_tool_input, agent=None):
    import bpy
    from . import cadex_backend

    return _deferred(
        cadex_backend.begin_rebuild_model(
            bpy.context.scene, cancelled=_cancellation_check(agent)),
        _render_rebuild_model)


def _tool_edit_script(tool_input, agent=None):
    import bpy
    from . import cadex_backend

    return _deferred(
        cadex_backend.begin_edit_script(
            bpy.context.scene, tool_input.get("replacements"),
            cancelled=_cancellation_check(agent)),
        _render_write_script)


def _tool_restore_version(tool_input, agent=None):
    import bpy
    from . import cadex_backend

    return _deferred(
        cadex_backend.begin_restore_version(
            bpy.context.scene, tool_input.get("version", ""),
            cancelled=_cancellation_check(agent)),
        _render_write_script)


def _tool_inspect_model(tool_input):
    import bpy
    from . import cadex_backend

    scope = str(tool_input.get("scope") or "").strip()
    if scope not in {"script", "document", "object", "output", "assets",
                     "history"}:
        return _text("inspect_model scope must be script, document, object, "
                     "output, assets or history."), True
    args = {"scope": scope}
    for key in ("target", "path"):
        value = str(tool_input.get(key) or "").strip()
        if value:
            args[key] = value
    payload = cadex_backend.inspect(bpy.context.scene, args)
    if payload.get("ok") is not True:
        return _text(_truncate("The engine refused the inspection: "
                               + str(payload.get("error") or payload))), True
    return _text(_truncate(json.dumps(payload.get("value"), indent=1,
                                      sort_keys=True, default=str))), False


def _tool_describe_cad_api(tool_input):
    import bpy
    from . import cadex_backend

    ok, payload = cadex_backend.describe_api(bpy.context.scene)
    if not ok:
        return _text("The engine could not describe its API:\n"
                     + str(payload.get("error") or payload)), True
    domain = str(tool_input.get("domain") or "").strip()
    wanted = tool_input.get("functions") or []
    if isinstance(wanted, str):
        wanted = [wanted]
    if not domain:
        if wanted:
            return _text("describe_cad_api needs a `domain` alongside "
                         "`functions`."), True
        return _text(json.dumps(cadex_backend.api_overview(payload),
                                indent=1, sort_keys=True)), False
    found, block = cadex_backend.api_domain(payload, domain)
    if not found:
        return _text(block), True
    if wanted:
        # The long descriptions, for the handful of functions the model
        # named. Only this path may truncate: it chose the names, so a cut
        # result is answered by asking for fewer.
        picked, value = cadex_backend.api_functions(block, wanted)
        if not picked:
            return _text(value), True
        return _text(_truncate(json.dumps(value, indent=1, sort_keys=True),
                               _API_DOMAIN_CHARS)), False
    # Every signature in the domain, summaries only. Never truncated: a
    # severed JSON blob is what ADR-123 was about.
    return _text(json.dumps(cadex_backend.compact_domain(block),
                            indent=1, sort_keys=True)), False


def _tool_get_attached_image(tool_input, agent):
    from . import capture

    attachments = agent.attachments if agent is not None else []
    try:
        index = int(tool_input.get("index"))
    except (TypeError, ValueError):
        return _text("get_attached_image needs an integer `index`."), True
    if not 0 <= index < len(attachments):
        return _text("No attachment #{:d}; {:d} image(s) attached this "
                     "session.".format(index, len(attachments))), True
    image_b64, error = capture.image_file_png_base64(attachments[index]["path"])
    if image_b64 is None:
        return _text(error), True
    return [{"type": "image", "data": image_b64, "mimeType": "image/png"}], False


def _tool_scene_summary(_tool_input):
    """The scene, as the engine defines it.

    The Blender objects are tessellated display copies of the engine's
    outputs -- reporting them as "the scene" would invite the model to reason
    about the mirror instead of the model. So this reports engine truth, and
    says what the mirror is separately.
    """
    import bpy
    from . import cadex_backend
    ok, summary = cadex_backend.engine_summary(bpy.context.scene)
    if not ok:
        return _text(_truncate(str(summary))), True
    return _text(_truncate(json.dumps(summary, indent=1, sort_keys=True,
                                      default=str))), False


def _tool_viewport_screenshot(tool_input):
    from . import capture
    max_size = int(tool_input.get("max_size") or 768)
    image_b64, error = capture.screenshot_png_base64(max_size=max_size)
    if image_b64 is None:
        return _text(error), True
    return [{"type": "image", "data": image_b64, "mimeType": "image/png"}], False


def _tool_render_views(tool_input):
    """Four fitted views of the model, in one image (ADR-124).

    Classified exactly as ``collision_view`` was: read-only, so it is in
    neither ``MUTATING_TOOLS`` (looking at the model must not enter the undo
    stack) nor ``_ENGINE_TOOLS`` (it reads hydrated geometry that is already
    in the scene, and never speaks to cadexd).
    """

    from . import capture
    max_size = int(tool_input.get("max_size") or 1024)
    image_b64, error = capture.render_views(max_size=max_size)
    if image_b64 is None:
        return _text(error), True
    return [
        {"type": "image", "data": image_b64, "mimeType": "image/png"},
        {"type": "text", "text": "Four views of the model -- " +
                                 capture.quadrant_legend() + "."},
    ], False


def _resolve_objects(names):
    import bpy
    found, missing = [], []
    for name in names:
        obj = bpy.data.objects.get(name)
        (found if obj is not None else missing).append(obj if obj is not None else name)
    return found, missing


def _safe_filename(name):
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def _tool_export_stl(tool_input):
    import os
    import tempfile

    import bpy
    from . import model

    names = tool_input.get("objects") or []
    if names:
        objects, missing = _resolve_objects(names)
        if missing:
            return _text("Objects not found: {:s}".format(
                ", ".join(missing))), True
        non_mesh = [obj.name for obj in objects if obj.type != 'MESH']
        if non_mesh:
            return _text("Not mesh objects: {:s}".format(
                ", ".join(non_mesh))), True
    else:
        collection = bpy.data.collections.get(model.COLLECTION_NAME)
        objects = ([obj for obj in collection.all_objects if obj.type == 'MESH']
                   if collection is not None else [])
        if not objects:
            return _text("Nothing to export: no mesh objects in the Model "
                         "collection."), True

    directory = tool_input.get("directory") or ""
    if not directory:
        if bpy.data.filepath:
            directory = os.path.join(os.path.dirname(bpy.data.filepath), "stl")
        else:
            directory = os.path.join(tempfile.gettempdir(), "mesh_stl")
    directory = os.path.abspath(os.path.expanduser(directory))
    os.makedirs(directory, exist_ok=True)

    view_layer = bpy.context.view_layer
    previous_selection = [obj for obj in view_layer.objects if obj.select_get()]
    previous_active = view_layer.objects.active
    depsgraph = bpy.context.evaluated_depsgraph_get()

    lines = []
    try:
        for obj in objects:
            for other in view_layer.objects:
                other.select_set(False)
            obj.select_set(True)
            view_layer.objects.active = obj
            path = os.path.join(directory,
                                _safe_filename(obj.name) + ".stl")
            result = bpy.ops.wm.stl_export(
                filepath=path,
                export_selected_objects=True,
                apply_modifiers=True,
                global_scale=1.0,
            )
            if 'FINISHED' not in result:
                return _text("STL export failed for {:s}".format(obj.name)), True
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            mesh.calc_loop_triangles()
            triangles = len(mesh.loop_triangles)
            evaluated.to_mesh_clear()
            lines.append("{:s} -> {:s} ({:d} triangles)".format(
                obj.name, path, triangles))
    finally:
        for other in view_layer.objects:
            other.select_set(False)
        for obj in previous_selection:
            try:
                obj.select_set(True)
            except RuntimeError:
                pass
        view_layer.objects.active = previous_active

    return _text(_truncate(
        "Exported {:d} STL file(s):\n".format(len(lines)) + "\n".join(lines))), False


def _tool_import_geometry(tool_input):
    import os

    import bpy
    from . import cadex_backend

    path = str(tool_input.get("path") or "").strip()
    if not path:
        return _text("import_geometry needs the path of an STL, OBJ or PLY "
                     "file."), True
    path = os.path.abspath(os.path.expanduser(path))
    payload = cadex_backend.put_asset(bpy.context.scene, path,
                                      str(tool_input.get("name") or "").strip())
    if payload.get("ok") is not True:
        return _text(_truncate("The engine refused the import: "
                               + str(payload.get("error") or payload))), True
    stored = payload.get("assets") or []
    return _text(
        "Imported {:s} as {:s} ({:d} bytes). Reference it in the script with "
        "mesh.import_file(\"{:s}\").\nAssets now stored: {:s}".format(
            path, str(payload.get("name")), int(payload.get("bytes") or 0),
            str(payload.get("name")),
            ", ".join(str(item.get("name")) for item in stored) or "(none)"),
    ), False


def _tool_link_part(tool_input):
    import bpy
    from . import cadex_backend
    from .topbar import _link_source_from

    source = _link_source_from(tool_input.get("source"))
    if not source:
        return _text("link_part needs the path of another Cadex model — its "
                     ".blend file or its .cadex project folder."), True
    output = str(tool_input.get("output") or "").strip()
    payload = cadex_backend.link_part(
        bpy.context.scene, source, output=output,
        name=str(tool_input.get("name") or "").strip())
    if payload.get("ok") is not True:
        # The refusal for an omitted output *is* the answer to "what does
        # that model publish", so it is not framed as a failure.
        candidates = [str(item) for item in (payload.get("candidates") or [])]
        if candidates and not output:
            return _text("That model publishes: {:s}. Call link_part again "
                         "with one of them as 'output'.".format(
                             ", ".join(candidates))), False
        return _text(_truncate("The engine refused the link: "
                               + str(payload.get("error") or payload))), True
    name = str(payload.get("name") or "")
    moved = (
        "It moved from {:s} to {:s}.".format(
            str(payload.get("previous_revision") or "?")[:8],
            str(payload.get("source_revision") or "?")[:8])
        if payload.get("previous_revision")
        else "It is at revision {:s}.".format(
            str(payload.get("source_revision") or "?")[:8])
    ) if payload.get("changed") else "It had not moved; nothing changed here."
    return _text(
        "Linked {:s} from {:s} as {:s} ({:d} bytes). {:s}\nReference it in "
        "the script with part.import_part(\"{:s}\").".format(
            output or name, source, name, int(payload.get("bytes") or 0),
            moved, name)), False


def _tool_focus_view(tool_input):
    import bpy

    if bpy.app.background:
        return _text("No viewport available in background mode"), False

    names = tool_input.get("objects") or []
    if names:
        objects, missing = _resolve_objects(names)
        if not objects:
            return _text("Objects not found: {:s}".format(", ".join(missing))), True
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj in set(objects))

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type != 'WINDOW':
                    continue
                with bpy.context.temp_override(window=window, area=area, region=region):
                    if names:
                        bpy.ops.view3d.view_selected()
                    else:
                        bpy.ops.view3d.view_all()
                return _text("View framed"), False
    return _text("No 3D viewport found"), True


def _tool_collision_view(tool_input):
    """Draw the collision geometry, for the party that cannot press a button.

    Warranted as a tool rather than only a button because the agent is the
    one that catches this class of bug -- it is the caller of
    ``viewport_screenshot`` -- and a button is not reachable from there.

    Deliberately **not** in ``MUTATING_TOOLS``: a view toggle changes no
    geometry and must not enter the undo stack, or undoing a modelling
    mistake would first undo looking at it. Not in ``_ENGINE_TOOLS`` either
    -- it reads a record already cached against the accepted revision.
    """

    from . import cadex_collision

    show = tool_input.get("show")
    report = cadex_collision.toggle(None if show is None else bool(show))
    message = str(report.get("message") or "")
    if message:
        return _text(message), False
    if not report.get("shown"):
        return _text("Collision shapes hidden."), False

    lines = ["Collision shapes shown: {:d}.".format(int(report.get("shapes") or 0))]
    contacts = int(report.get("contacts") or 0)
    lines.append("Nothing is touching at t = 0." if not contacts
                 else "{:d} contact(s) already touching at t = 0.".format(contacts))
    for name in report.get("skipped") or ():
        lines.append("Not drawn, its part is not in the viewport: {:s}".format(
            str(name)))
    lines.append("Take a viewport_screenshot to see them.")
    return _text("\n".join(lines)), False


def _tool_section_view(tool_input):
    """Cut the model open, for the party that cannot press a button.

    Warranted as a tool for the reason ``collision_view`` is (ADR-091): the
    agent is the one that has to check whether a bore broke through, and it
    cannot reach a button. Same two exclusions, for the same two reasons --
    not in ``MUTATING_TOOLS``, because looking inside the model must not
    enter the undo stack; not in ``_ENGINE_TOOLS``, because it never speaks
    to the engine at all.
    """

    from . import cadex_section

    import bpy

    scene = bpy.context.scene
    group = cadex_section.settings(scene)
    if group is None:
        return _text("The section view is unavailable in this file."), True

    show = tool_input.get("show")
    want = (not group.show) if show is None else bool(show)
    if not want:
        cadex_section.toggle(False, scene=scene)
        return _text("Section view off."), False

    # Aim first, then switch on: `toggle` centres the plane on the axis it is
    # given, so an offset supplied here must be applied after that or it
    # would be overwritten by the centring.
    if "axis" in tool_input:
        group.axis = str(tool_input["axis"]).upper()
    report = cadex_section.toggle(True, scene=scene)
    if report.get("message"):
        return _text(str(report["message"])), True
    if "offset" in tool_input:
        group.offset = float(tool_input["offset"])
    if "flip" in tool_input:
        group.flip = bool(tool_input["flip"])
    report = dict(scene.get(cadex_section.SCENE_FLAG) or {})

    lines = ["Section on: cutting across {:s} at {:.2f} mm{:s}.".format(
        str(report.get("axis") or ""), float(report.get("offset") or 0.0),
        ", far half kept" if report.get("flip") else "")]
    lines.append("{:d} part(s) cut.".format(int(report.get("solids") or 0)))
    span = list(report.get("span") or ())
    if len(span) == 2:
        lines.append("The model spans {:.2f} to {:.2f} mm on that axis.".format(
            span[0], span[1]))
    if report.get("clear"):
        lines.append("The plane is off the end of the model, so nothing is "
                     "cut -- move the offset inside that span.")
    lines.append("Take a viewport_screenshot to see it.")
    return _text("\n".join(lines)), False


def _tool_exploded_view(tool_input):
    """Spread the assembly, for the party that cannot press a button.

    Warranted as a tool for the reason ``section_view`` is: the agent is
    the one that has to show the user how a mechanism goes together, and it
    cannot reach a button. Same two exclusions, for the same two reasons --
    not in ``MUTATING_TOOLS``, because looking at the assembly spread must
    not enter the undo stack; not in ``_ENGINE_TOOLS``, because it plays a
    record already cached against the accepted revision.
    """

    from . import cadex_explode

    import bpy

    scene = bpy.context.scene
    group = cadex_explode.settings(scene)
    if group is None:
        return _text("The exploded view is unavailable in this file."), True

    show = tool_input.get("show")
    want = (not group.show) if show is None else bool(show)
    if not want:
        cadex_explode.toggle(False, scene=scene)
        return _text("Exploded view off; the assembly is back together."), False

    report = cadex_explode.toggle(True, scene=scene)
    if report.get("message"):
        return _text(str(report["message"])), True
    if "factor" in tool_input:
        group.factor = max(0.0, min(1.0, float(tool_input["factor"])))
        report = dict(scene.get(cadex_explode.SCENE_FLAG) or {})
    if not report.get("shown"):
        return _text(str(report.get("reason") or "Nothing to explode.")), True

    lines = ["Exploded to factor {:.2f}: {:d} component(s) spread over "
             "{:d} stage(s), {:d} leader line(s).".format(
                 float(report.get("factor") or 0.0),
                 int(report.get("components") or 0),
                 int(report.get("stages") or 0),
                 int(report.get("lines") or 0))]
    lines.append("Take a viewport_screenshot to see it.")
    return _text("\n".join(lines)), False


def _tool_blueprint_view(tool_input):
    """Restyle the viewport as a blueprint, for the party that cannot press
    a button.

    Warranted as a tool for the reason ``section_view`` is: the agent is the
    one asked to show the user a drawing-office look, and it cannot reach a
    button. Same two exclusions, for the same two reasons -- not in
    ``MUTATING_TOOLS``, because restyling the viewport must not enter the
    undo stack; not in ``_ENGINE_TOOLS``, because it writes per-viewport
    draw state and never speaks to the engine at all.
    """

    from . import cadex_blueprint

    import bpy

    scene = bpy.context.scene
    group = cadex_blueprint.settings(scene)
    if group is None:
        return _text("The blueprint view is unavailable in this file."), True

    show = tool_input.get("show")
    want = (not group.show) if show is None else bool(show)
    if not want:
        cadex_blueprint.toggle(False, scene=scene)
        return _text("Blueprint view off; the viewport look is restored."), False

    if "theme" in tool_input:
        theme = str(tool_input["theme"])
        if theme not in cadex_blueprint.THEMES:
            return _text("Unknown theme {!r}; one of: {:s}.".format(
                theme, ", ".join(sorted(cadex_blueprint.THEMES)))), True
        group.theme = theme
    if "grid" in tool_input:
        group.grid = bool(tool_input["grid"])
    report = cadex_blueprint.toggle(True, scene=scene)
    if report.get("message"):
        return _text(str(report["message"])), True

    lines = ["Blueprint on: {:s} theme, grid {:s}, {:d} viewport(s) "
             "styled.".format(
                 str(report.get("theme") or ""),
                 "on" if report.get("grid") else "off",
                 int(report.get("viewports") or 0))]
    lines.append("Take a viewport_screenshot to see it.")
    return _text("\n".join(lines)), False


def _tool_make_blueprint(tool_input):
    """Render the four-view sheet and store it through the engine (ADR-150).

    In ``_ENGINE_TOOLS`` — it writes the project store through
    ``put_blueprint``, so a missing engine must refuse in a sentence — and
    NOT in ``MUTATING_TOOLS``, the ``import_geometry``/``link_part``
    precedent: a store write is not a scene edit and must not enter the
    undo stack.
    """

    import os

    import bpy
    from . import capture
    from . import cadex_backend
    from . import cadex_blueprint

    theme = str(tool_input.get("theme") or cadex_blueprint.DEFAULT_THEME)
    if theme not in cadex_blueprint.THEMES:
        return _text("Unknown theme {!r}; one of: {:s}.".format(
            theme, ", ".join(sorted(cadex_blueprint.THEMES)))), True
    max_size = int(tool_input.get("max_size") or 1024)

    sheet, error = capture.render_blueprint(theme=theme, max_size=max_size)
    if sheet is None:
        return _text(error), True

    scene = bpy.context.scene
    payload = cadex_backend.put_blueprint(
        scene, sheet["path"],
        label=str(tool_input.get("name") or "").strip(),
        meta={"theme": theme, "views": list(sheet.get("views") or ()),
              "size": list(sheet.get("size") or ())})
    try:
        os.remove(sheet["path"])       # the store copy is its home now
    except OSError:
        pass
    if payload.get("ok") is not True:
        return _text(_truncate("The engine refused the blueprint: "
                               + str(payload.get("error") or payload))), True

    root = cadex_backend.project_root(scene)
    stored_path = os.path.join(root, "blueprints", str(payload.get("name")))
    return [
        {"type": "image", "data": sheet["base64"], "mimeType": "image/png"},
        {"type": "text", "text":
            "Blueprint sheet stored at {:s} ({:d} bytes), attached to "
            "revision {:s}. {:s} -- {:s}.".format(
                stored_path, int(payload.get("bytes") or 0),
                str(payload.get("revision") or "?")[:12], theme,
                str(sheet.get("legend") or ""))},
    ], False


_HANDLERS = {
    "get_script": _tool_get_script,
    "write_script": _tool_write_script,
    "set_params": _tool_set_params,
    "edit_script": _tool_edit_script,
    "restore_version": _tool_restore_version,
    "rebuild_model": _tool_rebuild_model,
    "inspect_model": _tool_inspect_model,
    "describe_cad_api": _tool_describe_cad_api,
    "get_attached_image": _tool_get_attached_image,
    "scene_summary": _tool_scene_summary,
    "viewport_screenshot": _tool_viewport_screenshot,
    "render_views": _tool_render_views,
    "export_stl": _tool_export_stl,
    "import_geometry": _tool_import_geometry,
    "link_part": _tool_link_part,
    "focus_view": _tool_focus_view,
    "collision_view": _tool_collision_view,
    "section_view": _tool_section_view,
    "exploded_view": _tool_exploded_view,
    "blueprint_view": _tool_blueprint_view,
    "make_blueprint": _tool_make_blueprint,
}

# Handlers that additionally receive the calling Agent.
_AGENT_HANDLERS = {"get_attached_image", "write_script", "set_params",
                   "edit_script", "rebuild_model"}
