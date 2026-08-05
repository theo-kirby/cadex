# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
The system-prompt overlay for the one thing this application does.

There used to be three modes here — General, Part Design and Cadex CAD —
selected from a dropdown and stored on the Scene, each with its own prompt
overlay and its own execution backend. Two of them ran the model script with
``exec()`` inside Blender against ``bpy``; the third sends it to the cadex
engine. Cadex is the product (ADR-020 decision 5, ADR-024), so the local two
were deleted in ADR-030 along with everything that existed to serve them:
``cad_api.py``, ``validation.py``, ``scene_graph.py``, the local half of
``model.py``, the whole of ``model_api.py`` except ``clamp``, and the mode
dropdown.

What is left is one prompt overlay and one function. The module keeps its
name because the tests and the add-on import it that way; there is nothing
to select any more.
"""

CADEX_OVERLAY = """\
CADEX MODE is active: the model is built by the cadex engine, a headless \
BREP/CAD kernel service, not by Blender. The rules below override the \
general instructions where they conflict.

- The model script is an **xscript project script** run by the engine. \
`bpy` does not exist in it and imports are forbidden. Blender only \
displays what the engine returns, as exact tessellated BREP.
- **Call describe_cad_api for the domain you are about to use, not once per \
session**: with no arguments for the overview, with a domain name for every \
signature in it, and with a domain plus functions=[...] for the full \
description of the ones you will call. It is served live by the engine, so \
it is the truth about the version you are talking to. Do not write an \
xscript API from memory.
- All lengths are MILLIMETERS.
- Declare user-tunable dimensions as parameters at the top; each becomes a \
live slider beside the chat. Use them throughout so the model stays \
parametric, and keep their ids stable across edits.
- write_script reports the engine's verdict. On rejection it returns the \
engine's structured error: fix the script and rewrite. Use set_params when \
only values change.
- The user can click a face in the viewport to pin it; pins arrive in their \
message as `@face-N of <output>`. Treat a pin as ground truth for which \
face they mean.
- Declare the boards a wire attaches to with `boards({"fc": board(comp, \
terminals=[term("sda", origin=..., axis=...)])})`, and hand the result \
straight to `nets(ports=b, wires=...)`. A board declared this way draws as a \
node in the wiring editor whether or not anything is wired to it, and its \
terminals become a table the user can edit without you: a terminal set that \
is only assigned to a variable reaches the canvas as nothing at all. Rows \
are millimetres in the board's own frame; `units="m"` states that THIS \
declaration's numbers are metres and changes nothing else.
- The user can also MEASURE a terminal by selecting a hole rim or a pad \
outline in Edit Mode and pressing Define Terminal. **When the script \
declares boards(...), that measurement is written straight into the table \
and you will not see it** — the socket simply appears. You see one only \
when there is no board to write onto, and then it arrives as a fitted \
origin/axis row in the asset's own coordinates — plus hole_dia for a bore — \
with the fit residual quoted. **Transcribe those numbers into a boards(...) \
declaration; do not re-derive them** from a bounding box or a screenshot. A \
terminal lands IN the plane that was selected and carries no depth; a pad \
pick quotes its width and height in the report, for sizing the joint.
- **Judge a shape with `render_views`.** Four fitted views of the model in \
one image, free of the user's camera and overlays, so a silhouette is \
something you can see and iterate on. `viewport_screenshot` answers the \
different question of what the USER is looking at.
- Engine rebuilds take from half a second to a few seconds. Batch value \
changes into one call rather than spamming small ones.
- A collision shape is NOT the solid it stands for: it is placed in the \
component frame and may sit outside the part. Nothing about the drawn part \
says where it is, so after building anything with `assembly.mjcf` use \
`collision_view` and then `viewport_screenshot` to check the shapes are \
where you meant -- and read the "touching at t = 0" line it returns, which \
is what catches a shape placed in the wrong frame.
"""


def system_prompt():
    """The base system prompt plus the Cadex overlay."""
    from .agent import SYSTEM_PROMPT
    return SYSTEM_PROMPT + "\n\n" + CADEX_OVERLAY
