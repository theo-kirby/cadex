# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign Additive Pipe tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_pipe_feature


TOOL_SPEC = {
    "name": "partdesign.additive_pipe",
    "description": (
        "Create one native additive pipe by sweeping a closed profile along an exact path already "
        "owned by the same Body. Supports native orientation, transition, and multisection "
        "transformation modes for rails, ducts, tubes, ribs, and curved structural members."
    ),
    "contextual": True,
    "safety": "SAFE_WRITE",
    "workbench": "PartDesignWorkbench",
    "edit_modes": ["none"],
    "parameters": partdesign_pipe_feature.PARAMETERS,
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    return partdesign_pipe_feature.run(
        service,
        operation="additive_pipe",
        type_id="PartDesign::AdditivePipe",
        **arguments,
    )
