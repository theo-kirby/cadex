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
- **Call describe_cad_api before writing your first script in a session**, \
and again with a domain name whenever you need a function's exact \
signature. It is served live by the engine, so it is the truth about the \
version you are talking to. Do not write an xscript API from memory.
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
- The user can also MEASURE a terminal by selecting a hole rim in Edit Mode \
and pressing Define Terminal. Those arrive as a fitted origin/axis/depth/\
hole_dia row in the asset's own coordinates, with the fit residual quoted. \
**Transcribe those numbers into a terminals row; do not re-derive them** \
from a bounding box or a screenshot — they were measured off the geometry \
and your estimate is not better than the fit.
- Engine rebuilds take from half a second to a few seconds. Batch value \
changes into one call rather than spamming small ones.
"""


def system_prompt():
    """The base system prompt plus the Cadex overlay."""
    from .agent import SYSTEM_PROMPT
    return SYSTEM_PROMPT + "\n\n" + CADEX_OVERLAY
